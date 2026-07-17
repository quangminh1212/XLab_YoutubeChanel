$ErrorActionPreference = "Continue"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_min1k') } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
Set-Location "C:\Dev\XLab_YoutubeChanel\Vietnam"
Write-Output "=== BEFORE ==="
Get-ChildItem | Select-Object Name, Mode | Format-Table -AutoSize
# migrate year folders -> year files
Get-ChildItem -Directory | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $year = $_.Name
  $src = Join-Path $_.FullName "channels.txt"
  $dst = Join-Path (Get-Location) "$year.txt"
  if (Test-Path $src) {
    Copy-Item $src $dst -Force
    Write-Output "MIGRATED $year -> $year.txt"
  }
  Remove-Item $_.FullName -Recurse -Force
  Write-Output "REMOVED folder $year"
}
Write-Output "=== AFTER ==="
Get-ChildItem | Select-Object Name | Format-Table -AutoSize
