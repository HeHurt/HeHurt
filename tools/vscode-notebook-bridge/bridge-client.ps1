param(
    [ValidateSet("status", "active-notebook", "replace-cell", "apply-edits")]
    [string]$Action = "status",

    [string]$ConnectionFile,

    [string]$Uri,

    [int]$Index = -1,

    [AllowNull()]
    [string]$Text,

    [string]$TextFile,

    [string]$EditsFile,

    [switch]$Save
)

$ErrorActionPreference = "Stop"

function Convert-ToFilePath {
    param([string]$Value)

    if (-not $Value) {
        return $null
    }
    if ($Value -match '^file:') {
        return [System.IO.Path]::GetFullPath(([System.Uri]$Value).LocalPath)
    }
    if ($Value -match '^[a-z]:[\\/]' -or $Value.StartsWith('\\')) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    if ($Value -match '^[a-z][a-z0-9+.-]*:') {
        return $null
    }
    return [System.IO.Path]::GetFullPath($Value)
}

function Test-PathWithin {
    param([string]$Target, [string]$Root)

    if (-not $Target -or -not $Root) {
        return $false
    }
    $TargetFull = [System.IO.Path]::GetFullPath($Target).TrimEnd('\')
    $RootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $TargetFull.Equals($RootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $TargetFull.StartsWith("$RootFull\", [System.StringComparison]::OrdinalIgnoreCase)
}

function Add-CandidatePath {
    param(
        [System.Collections.Generic.HashSet[string]]$Paths,
        [string]$Candidate
    )

    if ($Candidate -and (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        [void]$Paths.Add([System.IO.Path]::GetFullPath($Candidate))
    }
}

function Add-AncestorConnectionFiles {
    param(
        [System.Collections.Generic.HashSet[string]]$Paths,
        [string]$StartPath
    )

    if (-not $StartPath) {
        return
    }
    $Current = if (Test-Path -LiteralPath $StartPath -PathType Leaf) {
        Split-Path -Parent ([System.IO.Path]::GetFullPath($StartPath))
    }
    else {
        [System.IO.Path]::GetFullPath($StartPath)
    }

    while ($Current) {
        Add-CandidatePath $Paths (Join-Path $Current ".codex_scratch\vscode-notebook-bridge.json")
        $Parent = Split-Path -Parent $Current
        if (-not $Parent -or $Parent -eq $Current) {
            break
        }
        $Current = $Parent
    }
}

function Get-LiveConnections {
    param([string]$ExplicitFile, [string]$TargetPath)

    $Paths = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $RegistryRoot = Join-Path $env:LOCALAPPDATA "HithiumNotebookBridge\connections"

    if ($ExplicitFile) {
        if (-not (Test-Path -LiteralPath $ExplicitFile -PathType Leaf)) {
            throw "Connection file not found: $ExplicitFile"
        }
        Add-CandidatePath $Paths $ExplicitFile
    }
    else {
        if (Test-Path -LiteralPath $RegistryRoot -PathType Container) {
            Get-ChildItem -LiteralPath $RegistryRoot -Filter "*.json" -File | ForEach-Object {
                Add-CandidatePath $Paths $_.FullName
            }
        }
        Add-AncestorConnectionFiles $Paths (Get-Location).Path
        Add-AncestorConnectionFiles $Paths $TargetPath
    }

    $Connections = @()
    $SeenEndpoints = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($ConnectionPath in $Paths) {
        try {
            $Info = Get-Content -LiteralPath $ConnectionPath -Raw | ConvertFrom-Json
            $EndpointKey = "$($Info.baseUrl)|$($Info.token)"
            if (-not $Info.baseUrl -or -not $Info.token -or -not $SeenEndpoints.Add($EndpointKey)) {
                continue
            }
            $Headers = @{ Authorization = "Bearer $($Info.token)" }
            $Status = Invoke-RestMethod "$($Info.baseUrl)/status" -Headers $Headers -TimeoutSec 2
            $Connections += [PSCustomObject]@{
                File = $ConnectionPath
                Info = $Info
                Headers = $Headers
                Status = $Status
                Score = 0
            }
        }
        catch {
            if (-not $ExplicitFile -and (Test-PathWithin $ConnectionPath $RegistryRoot)) {
                Remove-Item -LiteralPath $ConnectionPath -Force -ErrorAction SilentlyContinue
            }
            elseif ($ExplicitFile) {
                throw "Bridge connection is not live: $ConnectionPath. $($_.Exception.Message)"
            }
        }
    }
    return @($Connections)
}

function Resolve-BridgeConnection {
    param([string]$ExplicitFile, [string]$TargetUri)

    $TargetPath = Convert-ToFilePath $TargetUri
    $Connections = @(Get-LiveConnections $ExplicitFile $TargetPath)
    if ($Connections.Count -eq 0) {
        throw "No live VS Code Notebook Bridge instance was found. Reload VS Code after installing the extension."
    }

    $CurrentPath = [System.IO.Path]::GetFullPath((Get-Location).Path)
    foreach ($Candidate in $Connections) {
        $ActivePath = Convert-ToFilePath $Candidate.Status.activeNotebook.path
        $WorkspaceFolders = @($Candidate.Status.workspaceFolders)

        if ($TargetPath -and $ActivePath -and $TargetPath.Equals($ActivePath, [System.StringComparison]::OrdinalIgnoreCase)) {
            $Candidate.Score += 50000
        }
        if ($TargetPath -and ($WorkspaceFolders | Where-Object { Test-PathWithin $TargetPath $_ })) {
            $Candidate.Score += 5000
        }
        if ($Candidate.Status.window.focused) {
            $Candidate.Score += 10000
        }
        if ($WorkspaceFolders | Where-Object { Test-PathWithin $CurrentPath $_ }) {
            $Candidate.Score += 1000
        }
        if ($Candidate.Status.activeNotebook) {
            $Candidate.Score += 100
        }
    }

    $Ranked = @($Connections | Sort-Object -Property `
        @{ Expression = "Score"; Descending = $true }, `
        @{ Expression = { $_.Status.bridge.startedAt }; Descending = $true })
    if (-not $TargetPath -and $Ranked.Count -gt 1 -and $Ranked[0].Score -eq $Ranked[1].Score) {
        $Choices = $Ranked | ForEach-Object {
            "$($_.Info.baseUrl) active=$($_.Status.activeNotebook.path) focused=$($_.Status.window.focused)"
        }
        throw "Multiple live bridge instances are equally likely. Pass -Uri. Candidates: $($Choices -join '; ')"
    }
    return $Ranked[0]
}

function Write-JsonResult {
    param($Value, [int]$Depth = 20)
    $Value | ConvertTo-Json -Depth $Depth
}

function Invoke-JsonPost {
    param($Bridge, [string]$Endpoint, $Body)

    $JsonBody = $Body | ConvertTo-Json -Depth 30
    $Utf8Body = [System.Text.Encoding]::UTF8.GetBytes($JsonBody)
    return Invoke-RestMethod "$($Bridge.Info.baseUrl)/$Endpoint" `
        -Method Post `
        -Headers $Bridge.Headers `
        -ContentType "application/json; charset=utf-8" `
        -Body $Utf8Body
}

$Bridge = Resolve-BridgeConnection $ConnectionFile $Uri

if ($Action -eq "status") {
    Write-JsonResult $Bridge.Status 20
    return
}

if ($Action -eq "active-notebook") {
    $Result = Invoke-RestMethod "$($Bridge.Info.baseUrl)/active-notebook" -Headers $Bridge.Headers
    $ExpectedPath = Convert-ToFilePath $Uri
    $ActualPath = Convert-ToFilePath $Result.notebook.path
    if ($ExpectedPath -and (-not $ActualPath -or -not $ExpectedPath.Equals($ActualPath, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "The selected VS Code window does not have the requested notebook active: $Uri"
    }
    Write-JsonResult $Result 50
    return
}

if ($Action -eq "replace-cell") {
    if ($Index -lt 0) {
        throw "-Index is required for replace-cell."
    }
    if ($TextFile) {
        $Text = [System.IO.File]::ReadAllText($TextFile, [System.Text.Encoding]::UTF8)
    }
    elseif (-not $PSBoundParameters.ContainsKey("Text")) {
        throw "-Text or -TextFile is required for replace-cell."
    }

    $Body = @{
        index = $Index
        text = $Text
    }
    if ($Save.IsPresent) {
        $Body.save = $true
    }
    if ($Uri) {
        $Body.uri = $Uri
    }

    $Result = Invoke-JsonPost $Bridge "replace-cell" $Body
    Write-JsonResult $Result 20
    return
}

if ($Action -eq "apply-edits") {
    if (-not $EditsFile) {
        throw "-EditsFile is required for apply-edits. The file must contain a JSON array of {index,text} objects."
    }
    $EditsJson = [System.IO.File]::ReadAllText($EditsFile, [System.Text.Encoding]::UTF8)
    $Edits = @($EditsJson | ConvertFrom-Json)
    $Body = @{ edits = $Edits }
    if ($Save.IsPresent) {
        $Body.save = $true
    }
    if ($Uri) {
        $Body.uri = $Uri
    }

    $Result = Invoke-JsonPost $Bridge "apply-edits" $Body
    Write-JsonResult $Result 20
    return
}
