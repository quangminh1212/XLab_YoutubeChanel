@echo off
setlocal

if "%YOUTUBE_API_KEY%"=="" (
  echo Missing YOUTUBE_API_KEY environment variable.
  exit /b 1
)

python crawler.py --api-key "%YOUTUBE_API_KEY%" %*
