param(
  [Parameter(Mandatory = $true)][string]$Source,
  [Parameter(Mandatory = $true)][string]$Destination
)

$app = New-Object -ComObject PowerPoint.Application
$before = @($app.Presentations | ForEach-Object { $_.FullName })
Write-Output ('Before: ' + ($before -join ' | '))
$opened = $null
try {
  $opened = $app.Presentations.Open($Source, $true, $false, $false)
  $opened.SaveCopyAs($Destination, 24)
  Write-Output ("Saved: $Destination")
}
finally {
  if ($null -ne $opened) {
    $opened.Close()
  }
  $after = @($app.Presentations | ForEach-Object { $_.FullName })
  Write-Output ('After: ' + ($after -join ' | '))
  [Runtime.InteropServices.Marshal]::ReleaseComObject($opened) | Out-Null
  [Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
