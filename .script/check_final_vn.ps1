$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"

$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_retry') }
if ($proc) {
  Write-Output "STATUS=RUNNING"
  @($proc) | ForEach-Object { Write-Output "PID=$($_.ProcessId) CMD=$($_.CommandLine)" }
} else {
  Write-Output "STATUS=NOT_RUNNING"
}

Write-Output "--- summary ---"
if (Test-Path summary.json) { Get-Content summary.json -Raw }

$channels = 0
$years = @{}
Get-ChildItem Vietnam -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  $n = 0
  if (Test-Path $f) {
    $n = @(Get-Content $f -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
  }
  $years[$_.Name] = $n
  $channels += $n
}
Write-Output "CHANNELS_SAVED=$channels"
$years.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Output ("YEAR {0}: {1}" -f $_.Key, $_.Value) }

$unk = 0
$uf = "Vietnam\unknown\channels.txt"
if (Test-Path $uf) {
  $unk = @(Get-Content $uf | Where-Object { $_.Trim() -ne "" }).Count
}
Write-Output "UNKNOWN_FILE=$unk"

$disc = 0
if (Test-Path "Vietnam\_discovered.json") {
  $j = Get-Content "Vietnam\_discovered.json" -Raw | ConvertFrom-Json
  $disc = @($j.PSObject.Properties).Count
}
Write-Output "DISCOVERED_CACHE=$disc"

Write-Output "--- log tail ---"
$log = if (Test-Path crawl_retry.log) { "crawl_retry.log" } elseif (Test-Path crawl_full.log) { "crawl_full.log" } else { $null }
if ($log) {
  Write-Output "LOG=$log"
  Get-Content $log -Tail 25
}

Write-Output "--- git ---"
git log -1 --oneline
git status -sb
