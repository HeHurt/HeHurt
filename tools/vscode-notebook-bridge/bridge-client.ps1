param(
    [ValidateSet("status", "active-notebook", "replace-cell")]
    [string]$Action = "status",

    [string]$ConnectionFile = ".codex_scratch\vscode-notebook-bridge.json",

    [string]$Uri,

    [int]$Index = -1,

    [string]$Text,

    [switch]$Save
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConnectionFile)) {
    throw "Connection file not found: $ConnectionFile"
}

$Info = Get-Content -LiteralPath $ConnectionFile -Raw | ConvertFrom-Json
$Headers = @{ Authorization = "Bearer $($Info.token)" }

if ($Action -eq "status") {
    $Result = Invoke-RestMethod "$($Info.baseUrl)/status" -Headers $Headers
    $Result | ConvertTo-Json -Depth 20
    return
}

if ($Action -eq "active-notebook") {
    $Result = Invoke-RestMethod "$($Info.baseUrl)/active-notebook" -Headers $Headers
    $Result | ConvertTo-Json -Depth 50
    return
}

if ($Action -eq "replace-cell") {
    if ($Index -lt 0) {
        throw "-Index is required for replace-cell."
    }
    if ($null -eq $Text) {
        throw "-Text is required for replace-cell."
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

    $JsonBody = $Body | ConvertTo-Json -Depth 10
    $Result = Invoke-RestMethod "$($Info.baseUrl)/replace-cell" `
        -Method Post `
        -Headers $Headers `
        -ContentType "application/json" `
        -Body $JsonBody
    $Result | ConvertTo-Json -Depth 20
    return
}
