$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"
Write-Output "=== SUMMARY ==="
if (Test-Path summary.json) { Get-Content summary.json -Raw }
Write-Output "=== BY YEAR ==="
$total = 0
Get-ChildItem Vietnam -Directory | Sort-Object Name | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  $n = 0
  if (Test-Path $f) {
    $n = @(Get-Content $f | Where-Object { $_.Trim() -ne "" }).Count
  }
  $total += $n
  Write-Output ("{0}: {1}" -f $_.Name, $n)
}
Write-Output "TOTAL_CHANNELS=$total"
Write-Output "=== SAMPLE ==="
$sample = Get-ChildItem Vietnam -Recurse -Filter channels.txt | Where-Object { $_.Length -gt 20 } | Select-Object -First 1
if ($sample) { Get-Content $sample.FullName -TotalCount 3 }
Write-Output "=== LOG TAIL ==="
if (Test-Path crawl_full.log) { Get-Content crawl_full.log -Tail 30 }
Write-Output "=== GIT STATUS ==="
git status -sb
git remote -v
