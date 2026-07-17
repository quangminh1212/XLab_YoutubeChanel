Write-Host "=== err log ==="
if (Test-Path C:\Dev\XLab_YoutubeChanel\crawl_full.err.log) { Get-Content C:\Dev\XLab_YoutubeChanel\crawl_full.err.log -Raw }
Write-Host "=== full log ==="
if (Test-Path C:\Dev\XLab_YoutubeChanel\crawl_full.log) { Get-Content C:\Dev\XLab_YoutubeChanel\crawl_full.log -Raw }
Write-Host "=== python procs ==="
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | ForEach-Object { "$($_.ProcessId) $($_.CommandLine)" }
