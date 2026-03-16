param(
    [string]$Root = ".",
    [switch]$Apply,
    [switch]$DeleteCopyFiles,
    [switch]$ClearNotebookOutputs,
    [int]$LargeFileMB = 100,
    [int]$TopN = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToMB([long]$Bytes) {
    [math]::Round($Bytes / 1MB, 2)
}

function Convert-ToGB([long]$Bytes) {
    [math]::Round($Bytes / 1GB, 2)
}

function Get-DirSizeBytes([string]$Path) {
    $measure = Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum

    $sum = 0L
    if ($null -ne $measure) {
        $sumProp = $measure.PSObject.Properties["Sum"]
        if ($null -ne $sumProp -and $null -ne $sumProp.Value) {
            $sum = [long]$sumProp.Value
        }
    }

    $sum
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

$RootPath = (Resolve-Path -LiteralPath $Root).Path
Set-Location -LiteralPath $RootPath

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportDir = Join-Path $RootPath "tools/workspace_health/reports/$timestamp"
Ensure-Dir -Path $reportDir

Write-Host "=== Hithium Workspace Health Check ===" -ForegroundColor Cyan
Write-Host "Root: $RootPath"
Write-Host "Mode: $(if ($Apply) { 'APPLY' } else { 'DRY-RUN' })"
Write-Host "Report: $reportDir"
Write-Host ""

$topItems = Get-ChildItem -LiteralPath $RootPath -Force
$topSummary = foreach ($item in $topItems) {
    if ($item.PSIsContainer) {
        $bytes = Get-DirSizeBytes -Path $item.FullName
        [PSCustomObject]@{ Name=$item.Name; Type='Dir'; SizeGB=(Convert-ToGB $bytes); FullPath=$item.FullName }
    } else {
        [PSCustomObject]@{ Name=$item.Name; Type='File'; SizeGB=(Convert-ToGB $item.Length); FullPath=$item.FullName }
    }
}
$topSummary = $topSummary | Sort-Object SizeGB -Descending
$topSummary | Export-Csv -Path (Join-Path $reportDir "top_level_size.csv") -NoTypeInformation -Encoding UTF8
Write-Host "[1] Top-level size (Top 10):" -ForegroundColor Yellow
$topSummary | Select-Object -First 10 Name, Type, SizeGB | Format-Table -AutoSize

$cacheNames = @("__pycache__", ".ipynb_checkpoints", "csv_output", "output", "processed_curves")
$cacheDirs = Get-ChildItem -LiteralPath $RootPath -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $cacheNames -contains $_.Name }
$cacheSummary = foreach ($dir in $cacheDirs) {
    $bytes = Get-DirSizeBytes -Path $dir.FullName
    [PSCustomObject]@{ Dir=$dir.FullName; SizeMB=(Convert-ToMB $bytes) }
}
$cacheSummary = $cacheSummary | Sort-Object SizeMB -Descending
$cacheSummary | Export-Csv -Path (Join-Path $reportDir "cache_dirs.csv") -NoTypeInformation -Encoding UTF8
$cacheTotalMB = if ($cacheSummary) { [math]::Round((($cacheSummary | Measure-Object SizeMB -Sum).Sum),2) } else { 0 }
Write-Host "[2] Cache dirs total: $cacheTotalMB MB" -ForegroundColor Yellow

$copyPattern = '(?i)(copy|副本|备份| - 副本)'
$copyFiles = Get-ChildItem -LiteralPath $RootPath -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $copyPattern }
$copySummary = $copyFiles | Sort-Object Length -Descending | Select-Object @{Name='SizeMB';Expression={Convert-ToMB $_.Length}}, FullName
$copySummary | Export-Csv -Path (Join-Path $reportDir "copy_files.csv") -NoTypeInformation -Encoding UTF8
$copyTotalMB = if ($copyFiles) { Convert-ToMB (($copyFiles | Measure-Object Length -Sum).Sum) } else { 0 }
Write-Host "[3] Copy files: $($copyFiles.Count), total $copyTotalMB MB" -ForegroundColor Yellow

$thresholdBytes = $LargeFileMB * 1MB
$largeFiles = Get-ChildItem -LiteralPath $RootPath -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -ge $thresholdBytes } |
    Sort-Object Length -Descending |
    Select-Object -First $TopN @{Name='SizeMB';Expression={Convert-ToMB $_.Length}}, FullName
$largeFiles | Export-Csv -Path (Join-Path $reportDir "large_files_top.csv") -NoTypeInformation -Encoding UTF8
Write-Host "[4] Large files >= $LargeFileMB MB (Top $TopN) exported" -ForegroundColor Yellow

$largeNbs = Get-ChildItem -LiteralPath $RootPath -Recurse -File -Filter *.ipynb -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending |
    Select-Object -First $TopN @{Name='SizeMB';Expression={Convert-ToMB $_.Length}}, FullName
$largeNbs | Export-Csv -Path (Join-Path $reportDir "notebooks_top.csv") -NoTypeInformation -Encoding UTF8

$gitDir = Join-Path $RootPath ".git"
$gitGB = if (Test-Path -LiteralPath $gitDir) { Convert-ToGB (Get-DirSizeBytes -Path $gitDir) } else { 0 }
"GitDirGB,$gitGB" | Out-File -FilePath (Join-Path $reportDir "git_size.csv") -Encoding UTF8
Write-Host "[5] .git size: $gitGB GB" -ForegroundColor Yellow

if ($Apply) {
    Write-Host ""
    Write-Host "Start cleanup..." -ForegroundColor Magenta

    foreach ($dir in $cacheDirs) {
        if (Test-Path -LiteralPath $dir.FullName) {
            Remove-Item -LiteralPath $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Deleted cache dir: $($dir.FullName)"
        }
    }

    if ($DeleteCopyFiles) {
        foreach ($file in $copyFiles) {
            if (Test-Path -LiteralPath $file.FullName) {
                Remove-Item -LiteralPath $file.FullName -Force -ErrorAction SilentlyContinue
                Write-Host "Deleted copy file: $($file.FullName)"
            }
        }
    }

    if ($ClearNotebookOutputs) {
        $hasJupyter = Get-Command jupyter -ErrorAction SilentlyContinue
        if ($hasJupyter) {
            $notebooks = Get-ChildItem -LiteralPath $RootPath -Recurse -File -Filter *.ipynb -ErrorAction SilentlyContinue
            foreach ($nb in $notebooks) {
                jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace "$($nb.FullName)" *> $null
                Write-Host "Cleared output: $($nb.FullName)"
            }
        } else {
            Write-Warning "jupyter not found, skip notebook output clearing."
        }
    }

    Write-Host "Cleanup finished." -ForegroundColor Green
}

$summaryLines = @(
    "Workspace health summary:",
    "- Top-level size report: top_level_size.csv",
    "- Cache dirs report: cache_dirs.csv",
    "- Copy files report: copy_files.csv",
    "- Large files report: large_files_top.csv",
    "- Notebook size report: notebooks_top.csv",
    "- Git size report: git_size.csv",
    "",
    "Suggested actions:",
    "1. Review reports first, then decide whether to run with -Apply",
    "2. Move raw experiment data (csv/xlsx/dat) outside repo and keep a manifest index",
    "3. Clear notebook outputs before commit",
    "4. Run git gc first; if still large, use git filter-repo to rewrite history"
)
$summaryLines | Out-File -FilePath (Join-Path $reportDir "README.txt") -Encoding UTF8

Write-Host ""
Write-Host "Done. Report directory: $reportDir" -ForegroundColor Green
