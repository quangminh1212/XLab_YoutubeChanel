$ErrorActionPreference = "Continue"
Write-Output "=== LOG TAIL ==="
Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_retry.log" -Tail 40
Write-Output "=== PROCS ==="
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler|run_retry') } | ForEach-Object {
  Write-Output ("{0} :: {1}" -f $_.ProcessId, $_.CommandLine)
}
Write-Output "=== ERR ==="
$err = "C:\Dev\XLab_YoutubeChanel\crawl_retry.err.log"
if ((Test-Path $err) -and (Get-Item $err).Length -gt 0) {
  Get-Content $err -Tail 20
} else {
  Write-Output "(empty)"
}
Write-Output "=== COUNTS ==="
$ch = 0
Get-ChildItem "C:\Dev\XLab_YoutubeChanel\Vietnam" -Directory | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  if (Test-Path $f) {
    $ch += @(Get-Content $f | Where-Object { $_.Trim() -ne "" }).Count
  }
}
Write-Output "SAVED=$ch"
$uf = "C:\Dev\XLab_YoutubeChanel\Vietnam\unknown\channels.txt"
if (Test-Path $uf) {
  Write-Output ("UNKNOWN={0}" -f @(Get-Content $uf | Where-Object { $_.Trim() -ne "" }).Count)
} else {
  Write-Output "UNKNOWN=0"
}
