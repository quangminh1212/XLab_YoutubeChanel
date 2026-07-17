@echo off
cd /d C:\Dev\XLab_YoutubeChanel
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo === FAST RESOLVE START %DATE% %TIME% ===>> crawl_retry.log
"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --skip-search --concurrency 8 --delay 0.15 --start-year 2005 --end-year 2026 >> crawl_retry.log 2>> crawl_retry.err.log
echo === RESOLVE EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_retry.log
"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --retry-unknown-only --concurrency 6 --delay 0.25 --start-year 2005 --end-year 2026 >> crawl_retry.log 2>> crawl_retry.err.log
echo === RETRY1 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_retry.log
"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --retry-unknown-only --concurrency 4 --delay 0.4 --start-year 2005 --end-year 2026 >> crawl_retry.log 2>> crawl_retry.err.log
echo === RETRY2 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_retry.log
"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --retry-unknown-only --concurrency 3 --delay 0.6 --start-year 2005 --end-year 2026 >> crawl_retry.log 2>> crawl_retry.err.log
echo === ALL DONE %ERRORLEVEL% %DATE% %TIME% ===>> crawl_retry.log
