$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "HH:mm:ss"
$stateFile = "C:\Users\GHC\crawl_proxy_state.json"
$prev = @{ saved = 0; ok = 0; done = 0; unknown = 0; proxies = 0; ts = (Get-Date).ToString("o") }
if (Test-Path $stateFile) {
  try {
    $j = Get-Content $stateFile -Raw | ConvertFrom-Json
    $prev.saved = [int]$j.saved
    $prev.ok = [int]$j.ok
    $prev.done = [int]$j.done
    $prev.unknown = [int]$j.unknown
    $prev.proxies = [int]$j.proxies
    $prev.ts = [string]$j.ts
  } catch {}
}

$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_proxy') }
$status = if ($proc) { "RUNNING" } else { "NOT_RUNNING" }
$pidVal = if ($proc) { @($proc)[0].ProcessId } else { 0 }

$log = ""
if (Test-Path "C:\Dev\XLab_YoutubeChanel\crawl_proxy.log") {
  $log = Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_proxy.log" -Raw -ErrorAction SilentlyContinue
}

$done = 0; $total = 0; $ok = 0; $unknown = 0; $proxies = 0; $phase = "init"; $last = ""
if ($log) {
  $lines = $log -split "`r?`n"
  $last = ($lines | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
  if ($log -match "working=(\d+)") { $proxies = [int]$Matches[1] }
  if ($log -match "pool size=(\d+)") { $proxies = [int]$Matches[1] }
  $m = [regex]::Matches($log, "year-resolve (\d+)/(\d+) ok=(\d+) unknown=(\d+)")
  if ($m.Count -gt 0) {
    $x = $m[$m.Count - 1]
    $done = [int]$x.Groups[1].Value
    $total = [int]$x.Groups[2].Value
    $ok = [int]$x.Groups[3].Value
    $unknown = [int]$x.Groups[4].Value
    $phase = "resolve"
  } elseif ($log -match "probing youtube") {
    $phase = "probe_proxy"
  } elseif ($log -match "ALL DONE") {
    $phase = "done"
  } elseif ($log -match "resolve todo=") {
    $phase = "resolve"
  }
}

$saved = 0
Get-ChildItem "C:\Dev\XLab_YoutubeChanel\Vietnam" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  if (Test-Path $f) {
    $saved += @(Get-Content $f -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
  }
}
$unkFile = 0
$uf = "C:\Dev\XLab_YoutubeChanel\Vietnam\unknown\channels.txt"
if (Test-Path $uf) {
  $unkFile = @(Get-Content $uf -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
}

$elapsed = 1.0
try { $elapsed = [Math]::Max(0.1, ((Get-Date) - [datetime]::Parse($prev.ts)).TotalMinutes) } catch {}
$savedDelta = $saved - [int]$prev.saved
$okDelta = $ok - [int]$prev.ok
$doneDelta = $done - [int]$prev.done
$pct = if ($total -gt 0) { [Math]::Round(100.0 * $done / $total, 1) } else { 0 }

$state = [ordered]@{ saved = $saved; ok = $ok; done = $done; unknown = $unknown; proxies = $proxies; ts = (Get-Date).ToString("o") }
$state | ConvertTo-Json | Set-Content $stateFile -Encoding UTF8

Write-Output "=== BAO CAO GHC $ts ==="
Write-Output "may=remote-ghc status=$status pid=$pidVal phase=$phase"
Write-Output "proxies_working=$proxies progress=$pct% resolve=$done/$total ok=$ok unknown_run=$unknown"
Write-Output "saved=$saved unknown_file=$unkFile"
Write-Output "toc_do: +$doneDelta resolve/phut ($([Math]::Round($doneDelta/$elapsed,1))) | +$okDelta ok/phut ($([Math]::Round($okDelta/$elapsed,1))) | +$savedDelta saved/phut ($([Math]::Round($savedDelta/$elapsed,1)))"
Write-Output "last: $last"
Write-Output "=== END ==="
