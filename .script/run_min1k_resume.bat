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
