$ErrorActionPreference = "Continue"
$outLog = "C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log"
function W($m) {
  $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m
  Add-Content -Path $outLog -Value $line -Encoding UTF8
  Write-Output $line
}
Set-Location "C:\Dev\XLab_YoutubeChanel"
Set-Content -Path $outLog -Value "=== WAIT START $(Get-Date -Format o) ===" -Encoding UTF8

function Running {
  return [bool]@(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_min1k')
  })
}
function LastLog {
  if (Test-Path "crawl_min1k.log") {
    return (Get-Content "crawl_min1k.log" | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
  }
  return ""
}
function Counts {
  $min1k = 0
  if (Test-Path "Vietnam\channels_min1000.txt") {
    $min1k = @(Get-Content "Vietnam\channels_min1000.txt" | Where-Object { $_.Trim() -ne "" }).Count
  }
  $yearTotal = 0
  Get-ChildItem "Vietnam\*.txt" -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}\.txt$' } | ForEach-Object {
    $yearTotal += @(Get-Content $_.FullName | Where-Object { $_.Trim() -ne "" }).Count
  }
  return @{ Min1k = $min1k; YearTotal = $yearTotal }
}

W "waiting for crawler..."
for ($i = 0; $i -lt 800; $i++) {
  $run = Running
  $last = LastLog
  $c = Counts
  W ("run={0} min1k={1} years={2} last={3}" -f $run, $c.Min1k, $c.YearTotal, $last)
  if (-not $run) {
    Start-Sleep -Seconds 8
    if (-not (Running)) { break }
  }
  Start-Sleep -Seconds 45
}

$c = Counts
W ("FINAL min1k={0} years={1}" -f $c.Min1k, $c.YearTotal)
if (Test-Path summary.json) {
  W "SUMMARY:"
  Add-Content -Path $outLog -Value (Get-Content summary.json -Raw) -Encoding UTF8
}

# merge gitignore (do not wipe project rules)
$giPath = ".gitignore"
$need = @(
  "__pycache__/",
  "*.pyc",
  ".venv/",
  "venv/",
  ".env",
  "*.log",
  ".script/*.log",
  ".script/*_state.json",
  "working_proxies.txt",
  "free_proxies_sample.txt",
  "proxy_profile.yml"
)
$existing = @()
if (Test-Path $giPath) { $existing = Get-Content $giPath }
$all = @($existing + $need | Where-Object { $_ -and $_.Trim() -ne "" } | Select-Object -Unique)
Set-Content -Path $giPath -Value ($all -join "`n") -Encoding ASCII

git add -A
git status -sb | Out-String | ForEach-Object { W $_ }
git commit -m "feat: crawl Vietnam YouTube channels with 1000+ subscribers by year files"
git log -1 --oneline | ForEach-Object { W $_ }
W "COMMIT_DONE"
W "WAIT_SCRIPT_COMPLETE"
