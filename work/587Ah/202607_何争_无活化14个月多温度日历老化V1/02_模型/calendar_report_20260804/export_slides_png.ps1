param(
  [Parameter(Mandatory = $true)][string]$Source,
  [Parameter(Mandatory = $true)][string]$OutputDir
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$app = New-Object -ComObject PowerPoint.Application
$before = @($app.Presentations | ForEach-Object { $_.FullName })
Write-Output ('Before: ' + ($before -join ' | '))
$opened = $null
try {
  $opened = $app.Presentations.Open($Source, $true, $false, $false)
  $opened.Export($OutputDir, 'PNG', 1920, 1080)
  Write-Output ("Exported $($opened.Slides.Count) slides to $OutputDir")
}
finally {
  if ($null -ne $opened) { $opened.Close() }
  $after = @($app.Presentations | ForEach-Object { $_.FullName })
  Write-Output ('After: ' + ($after -join ' | '))
  if ($null -ne $opened) { [Runtime.InteropServices.Marshal]::ReleaseComObject($opened) | Out-Null }
  [Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
