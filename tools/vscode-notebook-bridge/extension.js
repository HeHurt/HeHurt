"use strict";

const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const path = require("path");
const vscode = require("vscode");
const manifest = require("./package.json");

let output;
let server;
let token;
let connection;
let startedAt;
const writtenConnectionFiles = new Set();

function activate(context) {
  output = vscode.window.createOutputChannel("Hithium Notebook Bridge");
  token = crypto.randomBytes(32).toString("hex");

  context.subscriptions.push(
    output,
    vscode.commands.registerCommand("hithiumNotebookBridge.start", () => startBridge(context)),
    vscode.commands.registerCommand("hithiumNotebookBridge.stop", stopBridge),
    vscode.commands.registerCommand("hithiumNotebookBridge.restart", async () => {
      await stopBridge();
      await startBridge(context);
    }),
    vscode.commands.registerCommand("hithiumNotebookBridge.showStatus", showStatus),
    vscode.commands.registerCommand("hithiumNotebookBridge.copyConnection", copyConnection),
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
      writeConnectionFiles(context).catch((error) => {
        log(`Failed to refresh connection files: ${formatError(error)}`);
      });
    })
  );

  if (getConfig().get("autoStart", true)) {
    startBridge(context).catch((error) => {
      log(`Auto-start failed: ${formatError(error)}`);
      vscode.window.showWarningMessage(`Notebook Bridge failed to start: ${formatError(error)}`);
    });
  }
}

async function deactivate() {
  await stopBridge();
}

async function startBridge(context) {
  if (server) {
    await writeConnectionFiles(context);
    return connection;
  }

  const configuredPort = getConfig().get("port", 45451);
  const app = createServer(context);

  try {
    const actualPort = await listen(app, configuredPort);
    server = app;
    startedAt = new Date().toISOString();
    connection = makeConnection(actualPort, context);
    await writeConnectionFiles(context);
    log(`Started on ${connection.baseUrl}`);
    log(`Registry file: ${connection.registryFile}`);
    log(`Workspace connection file: ${connection.connectionFile || "(no workspace)"}`);
    return connection;
  } catch (error) {
    if (configuredPort !== 0 && error && error.code === "EADDRINUSE") {
      log(`Port ${configuredPort} is in use; retrying with a random local port.`);
      const fallback = createServer(context);
      const actualPort = await listen(fallback, 0);
      server = fallback;
      startedAt = new Date().toISOString();
      connection = makeConnection(actualPort, context);
      await writeConnectionFiles(context);
      log(`Started on ${connection.baseUrl}`);
      log(`Registry file: ${connection.registryFile}`);
      log(`Workspace connection file: ${connection.connectionFile || "(no workspace)"}`);
      return connection;
    }
    throw error;
  }
}

function createServer(context) {
  return http.createServer((request, response) => {
    handleRequest(context, request, response).catch((error) => {
      sendJson(response, error.statusCode || 500, {
        ok: false,
        error: error.message || String(error)
      });
    });
  });
}

function listen(app, port) {
  return new Promise((resolve, reject) => {
    app.once("error", reject);
    app.listen(port, "127.0.0.1", () => {
      app.off("error", reject);
      const address = app.address();
      resolve(address.port);
    });
  });
}

async function stopBridge() {
  if (!server) {
    return;
  }

  const currentToken = token;
  await new Promise((resolve) => server.close(resolve));
  await removeOwnedConnectionFiles(currentToken);
  server = undefined;
  connection = undefined;
  startedAt = undefined;
  log("Stopped.");
}

async function handleRequest(context, request, response) {
  const url = new URL(request.url || "/", "http://127.0.0.1");

  if (!isAuthorized(request)) {
    sendJson(response, 401, { ok: false, error: "Missing or invalid bearer token." });
    return;
  }

  if (request.method === "GET" && url.pathname === "/status") {
    sendJson(response, 200, getStatusPayload(context));
    return;
  }

  if (request.method === "GET" && url.pathname === "/active-notebook") {
    const editor = getActiveNotebookEditorOrThrow();
    ensureNotebookAllowed(editor.notebook.uri, editor.notebook.uri);
    sendJson(response, 200, { ok: true, notebook: serializeNotebook(editor.notebook, editor) });
    return;
  }

  if (request.method === "POST" && url.pathname === "/replace-cell") {
    const body = await readJsonBody(request);
    const notebook = getTargetNotebookOrThrow(body);
    const result = await replaceCellTexts(notebook, [{ index: body.index, text: body.text }], body);
    sendJson(response, 200, { ok: true, result });
    return;
  }

  if (request.method === "POST" && url.pathname === "/apply-edits") {
    const body = await readJsonBody(request);
    const notebook = getTargetNotebookOrThrow(body);
    const edits = Array.isArray(body.edits) ? body.edits : [];
    const result = await replaceCellTexts(notebook, edits, body);
    sendJson(response, 200, { ok: true, result });
    return;
  }

  sendJson(response, 404, {
    ok: false,
    error: "Unknown endpoint.",
    endpoints: ["GET /status", "GET /active-notebook", "POST /replace-cell", "POST /apply-edits"]
  });
}

function isAuthorized(request) {
  const header = request.headers.authorization || "";
  return header === `Bearer ${token}`;
}

function readJsonBody(request) {
  const limit = getConfig().get("maxBodyBytes", 10485760);
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];

    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > limit) {
        reject(httpError(413, `Request body is larger than ${limit} bytes.`));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });

    request.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8");
        resolve(raw ? JSON.parse(raw) : {});
      } catch (error) {
        reject(httpError(400, `Invalid JSON body: ${formatError(error)}`));
      }
    });

    request.on("error", reject);
  });
}

function getActiveNotebookEditorOrThrow() {
  const editor = vscode.window.activeNotebookEditor;
  if (!editor) {
    throw httpError(404, "No active notebook editor.");
  }
  return editor;
}

function getTargetNotebookOrThrow(body) {
  const editor = getActiveNotebookEditorOrThrow();
  const activeNotebook = editor.notebook;
  const uriInput = body.uri || body.notebookUri || body.path;

  if (!uriInput) {
    ensureNotebookAllowed(activeNotebook.uri, activeNotebook.uri);
    return activeNotebook;
  }

  const targetUri = parseUriInput(uriInput);
  if (!targetUri) {
    throw httpError(400, "Invalid notebook uri/path.");
  }

  if (getConfig().get("editActiveNotebookOnly", true) && !sameUri(activeNotebook.uri, targetUri)) {
    throw httpError(409, "Requested notebook is not the active notebook editor.");
  }

  const notebook = vscode.workspace.notebookDocuments.find((candidate) => sameUri(candidate.uri, targetUri));
  if (!notebook) {
    throw httpError(404, "Requested notebook is not open in VS Code.");
  }

  ensureNotebookAllowed(notebook.uri, activeNotebook.uri);
  return notebook;
}

async function replaceCellTexts(notebook, edits, body) {
  if (!Array.isArray(edits) || edits.length === 0) {
    throw httpError(400, "No edits were provided.");
  }

  const seen = new Set();
  const workspaceEdit = new vscode.WorkspaceEdit();
  const applied = [];

  for (const item of edits) {
    const index = toCellIndex(item.index, notebook.cellCount);
    if (seen.has(index)) {
      throw httpError(400, `Duplicate edit for cell ${index}.`);
    }
    seen.add(index);

    if (typeof item.text !== "string") {
      throw httpError(400, `Edit for cell ${index} must include a string text field.`);
    }

    const cell = notebook.cellAt(index);
    const document = cell.document;
    const currentText = document.getText();
    const range = new vscode.Range(document.positionAt(0), document.positionAt(currentText.length));
    workspaceEdit.replace(document.uri, range, item.text);
    applied.push({
      index,
      kind: cellKindName(cell.kind),
      oldLength: currentText.length,
      newLength: item.text.length
    });
  }

  const ok = await vscode.workspace.applyEdit(workspaceEdit);
  if (!ok) {
    throw httpError(500, "VS Code rejected the workspace edit.");
  }

  const shouldSave = typeof body.save === "boolean"
    ? body.save
    : getConfig().get("saveAfterEdit", false);
  if (shouldSave && typeof notebook.save === "function") {
    await notebook.save();
  }

  return {
    uri: notebook.uri.toString(),
    path: notebook.uri.fsPath || undefined,
    editedCells: applied,
    saved: Boolean(shouldSave)
  };
}

function serializeNotebook(notebook, editor) {
  const selectedCellIndices = getSelectedCellIndices(editor);
  const cells = [];

  for (let index = 0; index < notebook.cellCount; index += 1) {
    const cell = notebook.cellAt(index);
    cells.push({
      index,
      kind: cellKindName(cell.kind),
      languageId: cell.document.languageId,
      text: cell.document.getText(),
      metadata: safeJson(cell.metadata),
      outputCount: cell.outputs ? cell.outputs.length : 0,
      selected: selectedCellIndices.includes(index)
    });
  }

  return {
    uri: notebook.uri.toString(),
    path: notebook.uri.fsPath || undefined,
    notebookType: notebook.notebookType,
    version: notebook.version,
    isDirty: notebook.isDirty,
    isUntitled: notebook.isUntitled,
    selectedCellIndices,
    metadata: safeJson(notebook.metadata),
    cellCount: notebook.cellCount,
    cells
  };
}

function getSelectedCellIndices(editor) {
  const indices = [];
  const selections = editor.selections || [];
  for (const range of selections) {
    for (let index = range.start; index < range.end; index += 1) {
      if (!indices.includes(index)) {
        indices.push(index);
      }
    }
  }
  return indices.sort((a, b) => a - b);
}

function getStatusPayload(context) {
  const editor = vscode.window.activeNotebookEditor;
  return {
    ok: true,
    bridge: {
      running: Boolean(server),
      startedAt,
      baseUrl: connection ? connection.baseUrl : undefined,
      connectionFile: connection ? connection.connectionFile : getConnectionFilePath(context),
      registryFile: connection ? connection.registryFile : getRegistryFilePath(context),
      processId: process.pid,
      version: manifest.version,
      workspaceOnly: getConfig().get("workspaceOnly", true),
      editActiveNotebookOnly: getConfig().get("editActiveNotebookOnly", true)
    },
    window: {
      focused: vscode.window.state.focused
    },
    activeNotebook: editor ? {
      uri: editor.notebook.uri.toString(),
      path: editor.notebook.uri.fsPath || undefined,
      notebookType: editor.notebook.notebookType,
      cellCount: editor.notebook.cellCount,
      selectedCellIndices: getSelectedCellIndices(editor)
    } : undefined,
    workspaceFolders: (vscode.workspace.workspaceFolders || []).map((folder) => folder.uri.fsPath || folder.uri.toString())
  };
}

function makeConnection(port, context) {
  const baseUrl = `http://127.0.0.1:${port}`;
  return {
    ok: true,
    name: "hithium-notebook-bridge",
    version: manifest.version,
    processId: process.pid,
    baseUrl,
    token,
    authHeader: `Bearer ${token}`,
    connectionFile: getConnectionFilePath(context),
    registryFile: getRegistryFilePath(context),
    startedAt,
    endpoints: {
      status: `${baseUrl}/status`,
      activeNotebook: `${baseUrl}/active-notebook`,
      replaceCell: `${baseUrl}/replace-cell`,
      applyEdits: `${baseUrl}/apply-edits`
    }
  };
}

async function writeConnectionFiles(context) {
  if (!connection) {
    return;
  }

  connection.connectionFile = getConnectionFilePath(context);
  connection.registryFile = getRegistryFilePath(context);
  const filePaths = [connection.registryFile, connection.connectionFile].filter(Boolean);

  for (const filePath of filePaths) {
    await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
    await fs.promises.writeFile(filePath, `${JSON.stringify(connection, null, 2)}\n`, "utf8");
    writtenConnectionFiles.add(filePath);
  }
}

function getConnectionFilePath(context) {
  const folders = vscode.workspace.workspaceFolders || [];
  if (folders.length === 0) {
    return undefined;
  }
  const relativePath = getConfig().get("connectionFile", ".codex_scratch/vscode-notebook-bridge.json");
  if (path.isAbsolute(relativePath)) {
    return path.normalize(relativePath);
  }
  return path.join(folders[0].uri.fsPath, relativePath);
}

function getRegistryFilePath(context) {
  const root = process.env.LOCALAPPDATA || context.globalStorageUri.fsPath;
  return path.join(root, "HithiumNotebookBridge", "connections", `${process.pid}.json`);
}

async function removeOwnedConnectionFiles(expectedToken) {
  const filePaths = Array.from(writtenConnectionFiles);
  writtenConnectionFiles.clear();

  for (const filePath of filePaths) {
    try {
      const raw = await fs.promises.readFile(filePath, "utf8");
      const current = JSON.parse(raw);
      if (current.token === expectedToken) {
        await fs.promises.unlink(filePath);
      }
    } catch (error) {
      if (!error || error.code !== "ENOENT") {
        log(`Failed to remove connection file ${filePath}: ${formatError(error)}`);
      }
    }
  }
}

function parseUriInput(input) {
  if (typeof input !== "string" || !input.trim()) {
    return undefined;
  }
  const value = input.trim();
  if (/^[a-z]:[\\/]/i.test(value) || value.startsWith("\\\\")) {
    return vscode.Uri.file(value);
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) {
    return vscode.Uri.parse(value);
  }
  return vscode.Uri.file(value);
}

function sameUri(left, right) {
  if (!left || !right) {
    return false;
  }
  if (left.toString() === right.toString()) {
    return true;
  }
  if (left.fsPath && right.fsPath) {
    return normalizePath(left.fsPath) === normalizePath(right.fsPath);
  }
  return false;
}

function normalizePath(value) {
  return path.normalize(value).toLowerCase();
}

function ensureNotebookAllowed(uri, activeNotebookUri) {
  if (
    getConfig().get("editActiveNotebookOnly", true)
    && activeNotebookUri
    && sameUri(uri, activeNotebookUri)
  ) {
    return;
  }

  ensureWorkspaceAllowed(uri);
}

function ensureWorkspaceAllowed(uri) {
  if (!getConfig().get("workspaceOnly", true)) {
    return;
  }

  if (!uri || uri.scheme !== "file" || !uri.fsPath) {
    throw httpError(403, "Only file-backed workspace notebooks are allowed.");
  }

  const folders = vscode.workspace.workspaceFolders || [];
  const target = normalizePath(uri.fsPath);
  const allowed = folders.some((folder) => {
    const root = normalizePath(folder.uri.fsPath);
    return target === root || target.startsWith(`${root}${path.sep}`);
  });

  if (!allowed) {
    throw httpError(403, "Notebook is outside the current VS Code workspace.");
  }
}

function toCellIndex(value, cellCount) {
  const index = Number(value);
  if (!Number.isInteger(index) || index < 0 || index >= cellCount) {
    throw httpError(400, `Cell index must be an integer from 0 to ${cellCount - 1}.`);
  }
  return index;
}

function cellKindName(kind) {
  return kind === vscode.NotebookCellKind.Code ? "code" : "markdown";
}

function safeJson(value) {
  try {
    return JSON.parse(JSON.stringify(value || {}));
  } catch (_error) {
    return {};
  }
}

function showStatus() {
  const status = getStatusPayload({ extensionUri: undefined });
  output.show(true);
  log(JSON.stringify(status, null, 2));
  vscode.window.showInformationMessage(server ? "Notebook Bridge is running." : "Notebook Bridge is stopped.");
}

async function copyConnection() {
  if (!connection) {
    vscode.window.showWarningMessage("Notebook Bridge is not running.");
    return;
  }
  await vscode.env.clipboard.writeText(JSON.stringify(connection, null, 2));
  vscode.window.showInformationMessage("Notebook Bridge connection copied to clipboard.");
}

function sendJson(response, statusCode, payload) {
  response.statusCode = statusCode;
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.setHeader("cache-control", "no-store");
  response.end(`${JSON.stringify(payload, null, 2)}\n`);
}

function httpError(statusCode, message) {
  const error = new Error(message);
  error.statusCode = statusCode;
  return error;
}

function getConfig() {
  return vscode.workspace.getConfiguration("hithiumNotebookBridge");
}

function log(message) {
  if (output) {
    try {
      output.appendLine(`[${new Date().toISOString()}] ${message}`);
    } catch (_error) {
      // The output channel may already be disposed during extension shutdown.
    }
  }
}

function formatError(error) {
  return error && error.message ? error.message : String(error);
}

module.exports = {
  activate,
  deactivate
};
