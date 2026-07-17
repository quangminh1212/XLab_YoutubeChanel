# Minute monitor for retry crawl on remote GHC
$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "HH:mm:ss"
$stateFile = "C:\Users\GHC\crawl_retry_state.json"
$prev = @{ channels = 0; unique = 0; queryIdx = 0; resolveDone = 0; unknown = 0; phase = "init"; ts = (Get-Date).ToString("o") }
if (Test-Path $stateFile) {
  try {
    $j = Get-Content $stateFile -Raw | ConvertFrom-Json
    $prev.channels = [int]$j.channels
    $prev.unique = [int]$j.unique
    $prev.queryIdx = [int]$j.queryIdx
    $prev.resolveDone = [int]$j.resolveDone
    $prev.unknown = [int]$j.unknown
    $prev.phase = [string]$j.phase
    $prev.ts = [string]$j.ts
  } catch {}
}

$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_retry') }
$status = if ($proc) { "RUNNING" } else { "NOT_RUNNING" }
$pidVal = if ($proc) { @($proc)[0].ProcessId } else { 0 }

$logPath = "C:\Dev\XLab_YoutubeChanel\crawl_retry.log"
$logText = ""
if (Test-Path $logPath) { $logText = Get-Content $logPath -Raw -ErrorAction SilentlyContinue }

$queryIdx = 0; $queryTotal = 0; $unique = 0; $phase = "search"
$resolveDone = 0; $resolveTotal = 0; $unknown = 0; $lastLine = ""
if ($logText) {
  $lines = $logText -split "`r?`n"
  $lastLine = ($lines | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
  $m = [regex]::Matches($logText, "\[VN\] \[(\d+)/(\d+)\] .* unique=(\d+)")
  if ($m.Count -gt 0) {
    $last = $m[$m.Count - 1]
    $queryIdx = [int]$last.Groups[1].Value
    $queryTotal = [int]$last.Groups[2].Value
    $unique = [int]$last.Groups[3].Value
    $phase = "search"
  }
  if ($logText -match "retry-unknown-only todo=(\d+)") {
    $phase = "retry"
    $resolveTotal = [int]$Matches[1]
  }
  if ($logText -match "resolve years for (\d+)") {
    $resolveTotal = [int]$Matches[1]
    if ($phase -ne "retry") { $phase = "resolve" }
  }
  $m2 = [regex]::Matches($logText, "year-resolve (\d+)/(\d+) unknown=(\d+)")
  if ($m2.Count -gt 0) {
    $last2 = $m2[$m2.Count - 1]
    $resolveDone = [int]$last2.Groups[1].Value
    $resolveTotal = [int]$last2.Groups[2].Value
    $unknown = [int]$last2.Groups[3].Value
    if ($phase -eq "search" -and $queryIdx -ge $queryTotal -and $queryTotal -gt 0) { $phase = "resolve" }
  }
  if ($logText -match "ALL DONE") { $phase = "done" }
  elseif ($logText -match "Saved summary" -and $status -eq "NOT_RUNNING") { $phase = "done" }
}

$channels = 0
$yearsFilled = 0
$unknownFile = 0
$vn = "C:\Dev\XLab_YoutubeChanel\Vietnam"
if (Test-Path $vn) {
  Get-ChildItem $vn -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
    $f = Join-Path $_.FullName "channels.txt"
    if (Test-Path $f) {
      $n = @(Get-Content $f -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
      $channels += $n
      if ($n -gt 0) { $yearsFilled++ }
    }
  }
  $uf = Join-Path $vn "unknown\channels.txt"
  if (Test-Path $uf) {
    $unknownFile = @(Get-Content $uf -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
  }
}

$elapsedMin = 1.0
try {
  $prevDt = [datetime]::Parse($prev.ts)
  $elapsedMin = [Math]::Max(0.1, ((Get-Date) - $prevDt).TotalMinutes)
} catch {}

$chDelta = $channels - [int]$prev.channels
$uqDelta = $unique - [int]$prev.unique
$qDelta = $queryIdx - [int]$prev.queryIdx
$rDelta = $resolveDone - [int]$prev.resolveDone
$chSpeed = [Math]::Round($chDelta / $elapsedMin, 1)
$uqSpeed = [Math]::Round($uqDelta / $elapsedMin, 1)
$qSpeed = [Math]::Round($qDelta / $elapsedMin, 2)
$rSpeed = [Math]::Round($rDelta / $elapsedMin, 1)

$pct = 0
if ($phase -eq "search" -and $queryTotal -gt 0) { $pct = [Math]::Round(100.0 * $queryIdx / $queryTotal, 1) }
elseif (($phase -eq "resolve" -or $phase -eq "retry") -and $resolveTotal -gt 0) { $pct = [Math]::Round(100.0 * $resolveDone / $resolveTotal, 1) }
elseif ($phase -eq "done") { $pct = 100 }

$state = [ordered]@{
  channels = $channels; unique = $unique; queryIdx = $queryIdx
  resolveDone = $resolveDone; unknown = $unknown; phase = $phase
  ts = (Get-Date).ToString("o")
}
$state | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8

Write-Output "=== BAO CAO GHC $ts ==="
Write-Output "may=remote-ghc status=$status pid=$pidVal"
Write-Output "phase=$phase progress=$pct%"
if ($phase -eq "search") {
  Write-Output "query=$queryIdx/$queryTotal unique=$unique"
  Write-Output "toc_do: +$qDelta q/phut ($qSpeed) | +$uqDelta unique/phut ($uqSpeed)"
} elseif ($phase -eq "resolve" -or $phase -eq "retry") {
  Write-Output "year_resolve=$resolveDone/$resolveTotal unknown_run=$unknown unknown_file=$unknownFile"
  Write-Output "toc_do: +$rDelta resolve/phut ($rSpeed) | +$chDelta kenh_luu/phut ($chSpeed)"
} else {
  Write-Output "channels_saved=$channels unknown_file=$unknownFile"
}
Write-Output "channels_saved_total=$channels years_with_data=$yearsFilled unknown_file=$unknownFile"
Write-Output "last: $lastLine"
Write-Output "=== END ==="
