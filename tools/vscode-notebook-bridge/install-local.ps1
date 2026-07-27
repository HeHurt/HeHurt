param(
    [string]$CodeCli,

    [switch]$CopyOnly,

    [string]$ExtensionsRoot = "$env:USERPROFILE\.vscode\extensions"
)

$ErrorActionPreference = "Stop"

$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Manifest = Get-Content -LiteralPath (Join-Path $Source "package.json") -Raw | ConvertFrom-Json
$ExtensionId = "$($Manifest.publisher).$($Manifest.name)-$($Manifest.version)"

function New-LocalVsix {
    param([string]$ExtensionSource, $PackageManifest, [string]$Destination)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $TempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    $Stage = Join-Path $TempRoot ("hithium-notebook-bridge-" + [System.Guid]::NewGuid().ToString("N"))
    $StageFull = [System.IO.Path]::GetFullPath($Stage)
    if (-not $StageFull.StartsWith($TempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to create VSIX stage outside the temporary directory: $StageFull"
    }

    try {
        $ExtensionStage = Join-Path $StageFull "extension"
        New-Item -ItemType Directory -Force -Path $ExtensionStage | Out-Null
        $Files = @{
            "package.json" = "package.json"
            "extension.js" = "extension.js"
            "bridge-client.ps1" = "bridge-client.ps1"
            "install-local.ps1" = "install-local.ps1"
            "README.md" = "readme.md"
        }
        foreach ($Item in $Files.GetEnumerator()) {
            Copy-Item -LiteralPath (Join-Path $ExtensionSource $Item.Key) `
                -Destination (Join-Path $ExtensionStage $Item.Value) -Force
        }

        $Description = [System.Security.SecurityElement]::Escape([string]$PackageManifest.description)
        $VsixManifest = @"
<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="$($PackageManifest.name)" Version="$($PackageManifest.version)" Publisher="$($PackageManifest.publisher)" />
    <DisplayName>$($PackageManifest.displayName)</DisplayName>
    <Description xml:space="preserve">$Description</Description>
    <Tags></Tags>
    <Categories>Other</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="$($PackageManifest.engines.vscode)" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.EnabledApiProposals" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExecutesCode" Value="true" />
      <Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true" />
      <Property Id="Microsoft.VisualStudio.Services.Content.Pricing" Value="Free" />
    </Properties>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code" /></Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/readme.md" Addressable="true" />
  </Assets>
</PackageManifest>
"@
        $ContentTypes = @"
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="js" ContentType="application/javascript"/><Default Extension="json" ContentType="application/json"/><Default Extension="md" ContentType="text/markdown"/><Default Extension="ps1" ContentType="application/octet-stream"/><Default Extension="vsixmanifest" ContentType="text/xml"/></Types>
"@
        $Utf8 = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText((Join-Path $StageFull "extension.vsixmanifest"), $VsixManifest, $Utf8)
        [System.IO.File]::WriteAllText((Join-Path $StageFull "[Content_Types].xml"), $ContentTypes, $Utf8)

        if (Test-Path -LiteralPath $Destination) {
            Remove-Item -LiteralPath $Destination -Force
        }
        [System.IO.Compression.ZipFile]::CreateFromDirectory($StageFull, $Destination)
    }
    finally {
        if (Test-Path -LiteralPath $StageFull) {
            Remove-Item -LiteralPath $StageFull -Recurse -Force
        }
    }
}

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
        $Vsix = Join-Path $Source "$($Manifest.name)-$($Manifest.version).vsix"
        New-LocalVsix $Source $Manifest $Vsix
        & $CodeCli --install-extension $Vsix --force
        if ($LASTEXITCODE -ne 0) {
            throw "VSIX installation failed with exit code $LASTEXITCODE."
        }
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
