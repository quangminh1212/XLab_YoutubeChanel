$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"

# gitignore
Set-Content -Path ".gitignore" -Value @"
__pycache__/
*.pyc
.venv/
venv/
.env
*.log
smoke_test.log
crawl_full.log
crawl_full.err.log
crawl_retry.log
crawl_retry.err.log
crawl_proxy.log
crawl_proxy.err.log
crawl_min1k.log
crawl_min1k.err.log
free_proxies_sample.txt
proxy_profile.yml
"@ -Encoding ASCII

git add -A
git status -sb
git commit -m "refactor: store Vietnam channels as one file per year (YYYY.txt)"
git log -1 --oneline
git status -sb
Write-Output "COMMIT_OK"
