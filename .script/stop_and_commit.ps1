$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"

Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_retry') } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# counts
$saved = 0
Get-ChildItem Vietnam -Directory | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  if (Test-Path $f) {
    $saved += @(Get-Content $f | Where-Object { $_.Trim() -ne "" }).Count
  }
}
$unk = 0
if (Test-Path "Vietnam\unknown\channels.txt") {
  $unk = @(Get-Content "Vietnam\unknown\channels.txt" | Where-Object { $_.Trim() -ne "" }).Count
}
$disc = 0
if (Test-Path "Vietnam\_discovered.json") {
  $j = Get-Content "Vietnam\_discovered.json" -Raw | ConvertFrom-Json
  $disc = @($j.PSObject.Properties).Count
}
Write-Output "SAVED=$saved UNKNOWN=$unk DISCOVERED=$disc"

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
crawl_retry.log
crawl_retry.err.log
"@ -Encoding ASCII

git add .gitignore crawler.py run.bat run_retry.bat requirements.txt summary.json Vietnam/
git status -sb
git commit -m "feat: deep VN search cache + unknown queue; pause year resolve after YouTube 429"
git log -1 --oneline
git status -sb
Write-Output "DONE"
