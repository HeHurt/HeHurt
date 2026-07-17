param(
    [string]$CodeCli,

    [switch]$CopyOnly,

    [string]$ExtensionsRoot = "$env:USERPROFILE\.vscode\extensions"
)

$ErrorActionPreference = "Stop"

$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Manifest = Get-Content -LiteralPath (Join-Path $Source "package.json") -Raw | ConvertFrom-Json
$ExtensionId = "$($Manifest.publisher).$($Manifest.name)-$($Manifest.version)"

if (-not $CopyOnly) {
    if (-not $CodeCli) {
        $Command = Get-Command code.cmd -ErrorAction SilentlyContinue
        if ($Command) {
            $CodeCli = $Command.Source
        }
    }

    if (-not $CodeCli) {
        $Candidates = @(
            "D:\软件安装\Microsoft VS Code\bin\code.cmd",
            "$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd",
            "$env:ProgramFiles\Microsoft VS Code\bin\code.cmd"
        )
        $CodeCli = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }

    if (-not $CodeCli) {
        throw "Could not find code.cmd. Pass -CodeCli or use -CopyOnly."
    }

    Push-Location $Source
    try {
        npx --yes @vscode/vsce package --no-dependencies --allow-missing-repository
        $Vsix = Join-Path $Source "$($Manifest.name)-$($Manifest.version).vsix"
        & $CodeCli --install-extension $Vsix --force
    }
    finally {
        Pop-Location
    }

    Write-Host "Installed $($Manifest.publisher).$($Manifest.name)@$($Manifest.version) with:"
    Write-Host "  $CodeCli"
    Write-Host ""
    Write-Host "Reload VS Code, then run 'Notebook Bridge: Show Status' from the Command Palette."
    return
}

$Destination = Join-Path $ExtensionsRoot $ExtensionId

$RootFull = [System.IO.Path]::GetFullPath($ExtensionsRoot)
$DestinationFull = [System.IO.Path]::GetFullPath($Destination)

if (-not $DestinationFull.StartsWith($RootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to install outside the VS Code extensions root: $DestinationFull"
}

New-Item -ItemType Directory -Force -Path $RootFull | Out-Null

if (Test-Path -LiteralPath $DestinationFull) {
    Remove-Item -LiteralPath $DestinationFull -Recurse -Force
}

Copy-Item -LiteralPath $Source -Destination $DestinationFull -Recurse -Force

Write-Host "Copied $ExtensionId to:"
Write-Host "  $DestinationFull"
Write-Host ""
Write-Host "Manual copy may not register with all VS Code profiles. Prefer the default VSIX install path."
