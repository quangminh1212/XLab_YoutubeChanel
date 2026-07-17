$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
Set-Location "C:\Dev\XLab_YoutubeChanel"
$py = "C:\Program Files\Python310\python.exe"
& $py crawler.py --countries VN --queries vietnam vlog gaming --max-pages-per-query 2 --concurrency 3 --delay 0.2 2>&1 | Tee-Object -FilePath smoke_test.log
Write-Host "EXIT=$LASTEXITCODE"
if (Test-Path summary.json) { Get-Content summary.json }
Write-Host "--- non-empty years ---"
Get-ChildItem -Path Vietnam -Recurse -Filter channels.txt | Where-Object { $_.Length -gt 5 } | ForEach-Object {
  $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines
  Write-Host "$($_.FullName) lines=$lines"
}
Write-Host "--- sample lines ---"
Get-ChildItem -Path Vietnam -Recurse -Filter channels.txt | Where-Object { $_.Length -gt 5 } | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName -TotalCount 5 }
