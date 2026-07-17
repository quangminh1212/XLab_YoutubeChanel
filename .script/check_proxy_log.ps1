$ErrorActionPreference = "Continue"
Write-Output "=== log tail ==="
Get-Content C:\Dev\XLab_YoutubeChanel\crawl_proxy.log -Tail 40
Write-Output "=== err ==="
if ((Get-Item C:\Dev\XLab_YoutubeChanel\crawl_proxy.err.log -ErrorAction SilentlyContinue).Length -gt 0) {
  Get-Content C:\Dev\XLab_YoutubeChanel\crawl_proxy.err.log -Tail 20
} else { "(empty)" }
Write-Output "=== working proxies ==="
if (Test-Path C:\Dev\XLab_YoutubeChanel\working_proxies.txt) {
  Get-Content C:\Dev\XLab_YoutubeChanel\working_proxies.txt
} else { "none" }
Write-Output "=== counts ==="
$saved=0
Get-ChildItem C:\Dev\XLab_YoutubeChanel\Vietnam -Directory | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  if (Test-Path $f) { $saved += @(Get-Content $f | Where-Object { $_.Trim() -ne "" }).Count }
}
$unk=0
if (Test-Path C:\Dev\XLab_YoutubeChanel\Vietnam\unknown\channels.txt) {
  $unk = @(Get-Content C:\Dev\XLab_YoutubeChanel\Vietnam\unknown\channels.txt | Where-Object { $_.Trim() -ne "" }).Count
}
Write-Output "SAVED=$saved UNKNOWN=$unk"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'crawler' } | ForEach-Object { "PROC $($_.ProcessId)" }
