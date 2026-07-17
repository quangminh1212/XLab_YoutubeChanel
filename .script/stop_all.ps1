$ErrorActionPreference = "Continue"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_proxy|run_retry|run_full') } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId) :: $($_.CommandLine)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
$left = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_proxy') }
if ($left) { "STILL_RUNNING" } else { "STOPPED" }
$saved=0
Get-ChildItem C:\Dev\XLab_YoutubeChanel\Vietnam -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  if (Test-Path $f) { $saved += @(Get-Content $f | Where-Object { $_.Trim() -ne "" }).Count }
}
$unk=0
if (Test-Path C:\Dev\XLab_YoutubeChanel\Vietnam\unknown\channels.txt) {
  $unk = @(Get-Content C:\Dev\XLab_YoutubeChanel\Vietnam\unknown\channels.txt | Where-Object { $_.Trim() -ne "" }).Count
}
$disc=0
if (Test-Path C:\Dev\XLab_YoutubeChanel\Vietnam\_discovered.json) {
  $j = Get-Content C:\Dev\XLab_YoutubeChanel\Vietnam\_discovered.json -Raw | ConvertFrom-Json
  $disc = @($j.PSObject.Properties).Count
}
Write-Output "SAVED=$saved UNKNOWN=$unk DISCOVERED=$disc"
