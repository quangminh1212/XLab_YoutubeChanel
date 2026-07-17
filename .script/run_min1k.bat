@echo off
cd /d C:\Dev\XLab_YoutubeChanel
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo === MIN1000 CRAWL START %DATE% %TIME% ===>> crawl_min1k.log

REM Pass 1: enrich existing + expanded search, filter >=1000
"C:\Program Files\Python310\python.exe" -u crawler.py --min-subs 1000 --max-pages-per-query 10 --concurrency 4 --delay 0.35 --fetch-free-proxies --max-proxies 20 --extra-bigrams >> crawl_min1k.log 2>> crawl_min1k.err.log
echo === PASS1 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log

REM Pass 2: enrich-only retry unknowns
"C:\Program Files\Python310\python.exe" -u crawler.py --min-subs 1000 --enrich-only --concurrency 3 --delay 0.5 --fetch-free-proxies --max-proxies 15 >> crawl_min1k.log 2>> crawl_min1k.err.log
echo === PASS2 EXIT %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log

echo === ALL DONE %ERRORLEVEL% %DATE% %TIME% ===>> crawl_min1k.log
