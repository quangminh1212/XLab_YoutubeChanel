$ErrorActionPreference = "Continue"
$log = "C:\Dev\XLab_YoutubeChanel\crawl_full.log"
$py = "C:\Program Files\Python310\python.exe"
$work = "C:\Dev\XLab_YoutubeChanel"
# stop previous crawler if any
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -match 'crawler.py' } | ForEach-Object {
  Write-Host "Killing old PID $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
$arg = "crawler.py --countries VN --max-pages-per-query 8 --concurrency 5 --delay 0.25 --start-year 2005 --end-year 2026"
$p = Start-Process -FilePath $py -ArgumentList $arg -WorkingDirectory $work -RedirectStandardOutput $log -RedirectStandardError "$work\crawl_full.err.log" -PassThru -WindowStyle Hidden
Write-Host "STARTED_PID=$($p.Id)"
Write-Host "LOG=$log"
Start-Sleep -Seconds 8
if (Test-Path $log) { Get-Content $log -Tail 20 }
