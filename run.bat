@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
"C:\Program Files\Python310\python.exe" crawler.py --countries VN --max-pages-per-query 8 --concurrency 5 --delay 0.25 %*
