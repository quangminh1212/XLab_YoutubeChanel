$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
Set-Location "C:\Dev\XLab_YoutubeChanel"
# clear previous partial year data for clean smoke
Remove-Item -Recurse -Force Vietnam -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path Vietnam | Out-Null
$py = "C:\Program Files\Python310\python.exe"
& $py crawler.py --countries VN --queries vietnam vlog gaming --max-pages-per-query 1 --concurrency 4 --delay 0.2 --no-resume 2>&1 | Tee-Object -FilePath smoke_test.log
Write-Host "EXIT=$LASTEXITCODE"
Get-Content summary.json
$total = 0
Get-ChildItem Vietnam -Recurse -Filter channels.txt | ForEach-Object {
  $n = @(Get-Content $_.FullName | Where-Object { $_.Trim() -ne "" }).Count
  if ($n -gt 0) { Write-Host "$($_.Directory.Name): $n"; $total += $n }
}
Write-Host "TOTAL=$total"
