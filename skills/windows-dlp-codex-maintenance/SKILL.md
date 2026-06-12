---
name: windows-dlp-codex-maintenance
description: Use on this Windows machine for company DLP/encryption and local tooling maintenance: Codex/Codex.exe update issues, VS Code vs Codex vs GitHub Copilot differences, git failures caused by encrypted files or filters, NAS/workspace path visibility, Code.exe file-reading bridge checks, and IT-ready evidence collection.
---

# Windows DLP And Codex Maintenance

Use this skill when the user reports that company encryption, DLP, network policy, or Windows packaging is blocking Codex, VS Code, Git, COMSOL, NAS, or update flows.

## First Principle

Identify the surface before fixing it. On this machine, "Codex" can mean:

- Desktop app: WindowsApps `OpenAI.Codex` package.
- PATH CLI: Winget portable `codex.exe`.
- VS Code bundled CLI: under `.vscode\extensions\openai.chatgpt-*\bin\windows-x86_64\`.

Do not modify the VS Code bundled `codex.exe` unless the user explicitly targets the VS Code extension.

## First-Pass Commands

Run read-only probes before changing anything:

```powershell
where.exe codex
codex --version
winget list --id OpenAI.Codex --exact
Get-Process Codex,codex -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path
(Get-AppxPackage -Name OpenAI.Codex) | Format-List PackageFullName,Version,InstallLocation
```

For git/DLP:

```powershell
git status --short
git diff --stat
git config --show-origin --get-regexp "filter|core.autocrlf|core.safecrlf"
```

For encrypted file readability:

```powershell
Get-Content -LiteralPath <path> -TotalCount 5
```

If the result shows `%TSD-Header-###%` or unreadable DLP bytes but VS Code can display the file, test the `Code.exe` bridge instead of repeatedly trying encodings.

## Code.exe Read Bridge

When an encrypted workspace file is readable in VS Code but not from PowerShell/Python/Java:

```powershell
$env:ELECTRON_RUN_AS_NODE='1'
& 'D:\软件安装\Microsoft VS Code\Code.exe' -e "const fs=require('fs'); const p='<file>'; const s=fs.readFileSync(p,'utf8'); console.log(s.slice(0,200));"
```

Interpretation:

- Plain source text: editor/workspace channel can read the file. Use it as evidence, but still test the actual process chain that must run the workflow.
- `%TSD-Header-###%`: the process is not released by DLP.
- Works in Code.exe but not in COMSOL/Python/Git: prepare IT evidence listing each executable path that needs release.

## Update Routing

- If the GUI says an update is required, verify the desktop AppX package, not only terminal `codex`.
- If terminal behavior is wrong, trust `codex --version` more than stale `winget list` after manual replacement.
- If `winget upgrade` fails with `InternetOpenUrl() failed. 0x80072f19`, use a verified download/hash/extract path rather than retrying blindly.
- If Store/App Installer fails with `Open failed`, `0x80070057`, or `0x80D02002`, treat it as company Store/HTTPS inspection policy until proven otherwise.
- If `Add-AppxPackage` fails with `0x80073D02`, close Store/package-manager processes and retry.

## Git/DLP Workflow

For git failures in encrypted workspaces:

1. Capture the exact `git status`, `git diff --stat`, and failing clean/smudge filter error.
2. Identify whether the failure is from repository filters, encrypted file bytes, path length, or file locks.
3. Prefer fixing the filter or ignore/tracking state over deleting files.
4. Never use `git reset --hard` or `git checkout --` unless explicitly requested.
5. If the user asks to "取消跟踪", use non-destructive untracking such as `git rm --cached` only for confirmed targets.

## IT Evidence Pack

When escalation is needed, provide:

- File path and whether VS Code, PowerShell, Python, Git, Java, COMSOL can read it.
- Executable full paths that need DLP release.
- Minimal reproduction commands.
- Exact error codes and timestamps.
- Why the release is needed for work, without exposing confidential file contents.

## Output Shape

Return:

- Which surface is affected.
- Evidence collected.
- Recommended local fix or IT request.
- What not to touch.
