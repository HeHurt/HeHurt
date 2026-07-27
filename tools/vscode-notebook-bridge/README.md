# Hithium Notebook Bridge

Local VS Code extension that lets Codex or Claude Code call VS Code notebook APIs through a localhost HTTP bridge.

The bridge reads and edits the currently open VS Code notebook model. Edits made through the bridge appear in the notebook editor immediately. It does not watch disk changes or expose arbitrary file read/write APIs.

## Install

Run from the workspace root:

```powershell
.\tools\vscode-notebook-bridge\install-local.ps1
```

Then reload VS Code.

## Runtime

The extension auto-starts by default. It writes connection details to the workspace and to a per-window registry:

```text
.codex_scratch/vscode-notebook-bridge.json
%LOCALAPPDATA%\HithiumNotebookBridge\connections\<extension-host-pid>.json
```

The helper probes live registry entries, removes stale registry entries, and selects the instance whose active notebook or workspace matches `-Uri`. With no `-Uri`, it prefers the focused VS Code window.

The file contains the localhost endpoint and bearer token. Requests must use:

```text
Authorization: Bearer <token>
```

## Endpoints

```text
GET  /status
GET  /active-notebook
POST /replace-cell
POST /apply-edits
```

Example PowerShell call:

```powershell
$info = Get-Content .\.codex_scratch\vscode-notebook-bridge.json -Raw | ConvertFrom-Json
$headers = @{ Authorization = "Bearer $($info.token)" }
Invoke-RestMethod "$($info.baseUrl)/active-notebook" -Headers $headers
```

Or use the helper:

```powershell
.\tools\vscode-notebook-bridge\bridge-client.ps1 -Action status
.\tools\vscode-notebook-bridge\bridge-client.ps1 -Action active-notebook
.\tools\vscode-notebook-bridge\bridge-client.ps1 -Action active-notebook -Uri C:\path\notebook.ipynb
.\tools\vscode-notebook-bridge\bridge-client.ps1 -Action replace-cell -Uri C:\path\notebook.ipynb -Index 0 -Text "print('hello')" -Save
.\tools\vscode-notebook-bridge\bridge-client.ps1 -Action apply-edits -Uri C:\path\notebook.ipynb -EditsFile .codex_scratch\notebook-edits.json -Save
```

Replace one cell:

```powershell
$info = Get-Content .\.codex_scratch\vscode-notebook-bridge.json -Raw | ConvertFrom-Json
$headers = @{ Authorization = "Bearer $($info.token)" }
$body = @{
    uri = "file:///d%3A/Users/hez/Desktop/hithium/example.ipynb"
    index = 0
    text = "print('hello from VS Code notebook bridge')"
} | ConvertTo-Json
Invoke-RestMethod "$($info.baseUrl)/replace-cell" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## Settings

- `hithiumNotebookBridge.autoStart`: start on VS Code startup.
- `hithiumNotebookBridge.port`: localhost port, default `45451`.
- `hithiumNotebookBridge.connectionFile`: workspace-relative connection file.
- `hithiumNotebookBridge.workspaceOnly`: restrict edits to the current workspace. The explicitly active notebook is allowed when `editActiveNotebookOnly` is enabled.
- `hithiumNotebookBridge.editActiveNotebookOnly`: restrict edits to the active notebook editor.
- `hithiumNotebookBridge.saveAfterEdit`: save after successful edits.
