$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "HH:mm:ss"
$stateFile = "C:\Dev\XLab_YoutubeChanel\.script\crawl_min1k_state.json"
$prev = @{ done = 0; min1k = 0; saved = 0; ts = (Get-Date).ToString("o") }
if (Test-Path $stateFile) {
  try {
    $j = Get-Content $stateFile -Raw | ConvertFrom-Json
    $prev.done = [int]$j.done
    $prev.min1k = [int]$j.min1k
    $prev.saved = [int]$j.saved
    $prev.ts = [string]$j.ts
  } catch {}
}

$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_min1k') }
$status = if ($proc) { "RUNNING" } else { "NOT_RUNNING" }
$pidVal = if ($proc) { @($proc)[0].ProcessId } else { 0 }

$log = ""
if (Test-Path "C:\Dev\XLab_YoutubeChanel\crawl_min1k.log") {
  $log = Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_min1k.log" -Raw -ErrorAction SilentlyContinue
}
$phase = "init"; $done = 0; $total = 0; $min1k = 0; $below = 0; $unknown = 0; $last = ""
if ($log) {
  $lines = $log -split "`r?`n"
  $last = ($lines | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
  if ($log -match "\[search\] \[(\d+)/(\d+)\]") {
    $phase = "search"
    $done = [int]$Matches[1]; $total = [int]$Matches[2]
  }
  $m = [regex]::Matches($log, "\[enrich\] (\d+)/(\d+) min1000=(\d+) below=(\d+) unknown=(\d+)")
  if ($m.Count -gt 0) {
    $x = $m[$m.Count - 1]
    $phase = "enrich"
    $done = [int]$x.Groups[1].Value
    $total = [int]$x.Groups[2].Value
    $min1k = [int]$x.Groups[3].Value
    $below = [int]$x.Groups[4].Value
    $unknown = [int]$x.Groups[5].Value
  }
  if ($log -match "ALL DONE") { $phase = "done" }
}

# count min1000 from flat file if exists
$flat = 0
if (Test-Path "C:\Dev\XLab_YoutubeChanel\Vietnam\channels_min1000.txt") {
  $flat = @(Get-Content "C:\Dev\XLab_YoutubeChanel\Vietnam\channels_min1000.txt" | Where-Object { $_.Trim() -ne "" }).Count
}

$elapsed = 1.0
try { $elapsed = [Math]::Max(0.1, ((Get-Date) - [datetime]::Parse($prev.ts)).TotalMinutes) } catch {}
$dDelta = $done - [int]$prev.done
$mDelta = $min1k - [int]$prev.min1k
$pct = if ($total -gt 0) { [Math]::Round(100.0 * $done / $total, 1) } else { 0 }

@{ done = $done; min1k = $min1k; saved = $flat; ts = (Get-Date).ToString("o") } | ConvertTo-Json | Set-Content $stateFile -Encoding UTF8

Write-Output "=== BAO CAO GHC $ts ==="
Write-Output "may=remote-ghc status=$status pid=$pidVal phase=$phase progress=$pct%"
Write-Output "step=$done/$total min1000_run=$min1k below=$below unknown=$unknown flat_file=$flat"
Write-Output "toc_do: +$dDelta/phut ($([Math]::Round($dDelta/$elapsed,1))) | +$mDelta min1000/phut ($([Math]::Round($mDelta/$elapsed,1)))"
Write-Output "last: $last"
Write-Output "=== END ==="

