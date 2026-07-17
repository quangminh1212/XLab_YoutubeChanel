$ErrorActionPreference = "Continue"
function Log($m) { Write-Output ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) }

# Stop waiters so they don't commit incomplete mid-restart
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match "wait_min1k_finish|finish_min1k_watch")
} | ForEach-Object {
  Log "Kill waiter $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# Stop crawler / batch
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match "crawler.py|run_min1k")
} | ForEach-Object {
  Log "Kill crawler $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

# Deploy fixed crawler
Copy-Item -Force C:\Dev\XLab_YoutubeChanel\crawler.py C:\Dev\XLab_YoutubeChanel\crawler.py
Log "crawler.py updated"

# Resume bat: enrich-only then unknown retry
$bat = @'
@echo off
cd /d C:\Dev\XLab_YoutubeChanel
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo === MIN1000 RESUME %DATE% %TIME% ===>> crawl_min1k.log

"C:\Program Files\Python310\python.exe" -u crawler.py --min-subs 1000 --enrich-only --concurrency 4 --delay 0.3 --fetch-free-proxies --max-proxies 12 >> crawl_min1k.log 2>> crawl_min1k.err.log
echo === PASS1 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log

"C:\Program Files\Python310\python.exe" -u crawler.py --min-subs 1000 --enrich-only --concurrency 3 --delay 0.45 --fetch-free-proxies --max-proxies 10 >> crawl_min1k.log 2>> crawl_min1k.err.log
echo === PASS2 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log

echo === ALL DONE %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log
'@
Set-Content -Path C:\Dev\XLab_YoutubeChanel\.script\run_min1k_resume.bat -Value $bat -Encoding ASCII
Log "resume bat written"

$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "cmd.exe /c C:\Dev\XLab_YoutubeChanel\.script\run_min1k_resume.bat"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Log "RESUME_PID=$($r.ProcessId) RET=$($r.ReturnValue)"
Start-Sleep -Seconds 2

# Restart wait-commit
$w = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "powershell.exe -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_finish.ps1"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Log "WAIT_PID=$($w.ProcessId) RET=$($w.ReturnValue)"

Start-Sleep -Seconds 8
& powershell -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\check_procs.ps1
Get-Content C:\Dev\XLab_YoutubeChanel\crawl_min1k.log -Tail 12

