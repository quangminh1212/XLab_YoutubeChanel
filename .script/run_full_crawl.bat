@echo off
cd /d C:\Dev\XLab_YoutubeChanel
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
"C:\Program Files\Python310\python.exe" -u crawler.py --countries VN --max-pages-per-query 8 --concurrency 5 --delay 0.25 --start-year 2005 --end-year 2026 >> crawl_full.log 2>> crawl_full.err.log
echo EXIT_CODE=%ERRORLEVEL%>> crawl_full.log
