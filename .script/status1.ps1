$ErrorActionPreference = "Continue"
Set-Content -Path "C:\Dev\XLab_YoutubeChanel\.gitignore" -Value @"
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
# quick status
$p = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -match 'crawler.py' }
if ($p) { "RUNNING pid=$($p.ProcessId)" } else { "NOT_RUNNING" }
if (Test-Path C:\Dev\XLab_YoutubeChanel\crawl_full.log) {
  Get-Content C:\Dev\XLab_YoutubeChanel\crawl_full.log -Tail 8
}
