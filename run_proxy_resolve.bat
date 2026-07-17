@echo off
cd /d C:\Dev\XLab_YoutubeChanel
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo === PROXY/DIRECT RESOLVE START %DATE% %TIME% ===>> crawl_proxy.log

REM direct-first + free proxy refill (NO --prefer-proxy)
"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --skip-search --fetch-free-proxies --max-proxies 20 --concurrency 3 --delay 0.5 --start-year 2005 --end-year 2026 >> crawl_proxy.log 2>> crawl_proxy.err.log
echo === PASS1 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_proxy.log

if exist working_proxies.txt (
  "C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --retry-unknown-only --proxy-file working_proxies.txt --fetch-free-proxies --max-proxies 15 --concurrency 2 --delay 0.7 --start-year 2005 --end-year 2026 >> crawl_proxy.log 2>> crawl_proxy.err.log
  echo === PASS2 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_proxy.log
)

"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --retry-unknown-only --fetch-free-proxies --max-proxies 20 --concurrency 2 --delay 1.0 --start-year 2005 --end-year 2026 >> crawl_proxy.log 2>> crawl_proxy.err.log
echo === ALL DONE %ERRORLEVEL% %DATE% %TIME% ===>> crawl_proxy.log
