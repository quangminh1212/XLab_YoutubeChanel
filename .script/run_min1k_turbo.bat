@echo off
cd /d C:\Dev\XLab_YoutubeChanel
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo === MIN1000 TURBO START %DATE% %TIME% ===>> crawl_min1k.log

REM Pass1: high concurrency (I/O bound). Avoid free-proxy startup stall.
"C:\Program Files\Python310\python.exe" -u crawler.py --min-subs 1000 --enrich-only --concurrency 24 --delay 0.05 --batch-size 96 --max-proxies 10 >> crawl_min1k.log 2>> crawl_min1k.err.log
echo === PASS1 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log

REM Pass2: retry remaining none/missing with proxies
"C:\Program Files\Python310\python.exe" -u crawler.py --min-subs 1000 --enrich-only --concurrency 12 --delay 0.12 --batch-size 64 --fetch-free-proxies --max-proxies 12 >> crawl_min1k.log 2>> crawl_min1k.err.log
echo === PASS2 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log

echo === ALL DONE %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log
