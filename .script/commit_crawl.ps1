$ErrorActionPreference = "Stop"
Set-Location "C:\Dev\XLab_YoutubeChanel"

# restore requirements if missing
if (-not (Test-Path "requirements.txt")) {
  Set-Content -Path "requirements.txt" -Value "httpx==0.27.2`n" -Encoding ASCII
}

# ensure gitignore
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
"@ -Encoding ASCII

git add .gitignore crawler.py requirements.txt run.bat run_full_crawl.bat summary.json Vietnam/
git status -sb
git commit -m "feat: crawl Vietnam YouTube channels by year via Innertube"
git log -1 --oneline
git status -sb
Write-Output "COMMIT_OK"
