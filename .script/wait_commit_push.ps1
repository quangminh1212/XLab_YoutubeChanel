$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"

function Get-Status {
  $proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_proxy') }
  $running = [bool]$proc
  $saved = 0
  Get-ChildItem "Vietnam" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
    $f = Join-Path $_.FullName "channels.txt"
    if (Test-Path $f) {
      $saved += @(Get-Content $f -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
    }
  }
  $unk = 0
  if (Test-Path "Vietnam\unknown\channels.txt") {
    $unk = @(Get-Content "Vietnam\unknown\channels.txt" -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
  }
  $disc = 0
  if (Test-Path "Vietnam\_discovered.json") {
    try {
      $j = Get-Content "Vietnam\_discovered.json" -Raw | ConvertFrom-Json
      $disc = @($j.PSObject.Properties).Count
    } catch {}
  }
  $last = ""
  if (Test-Path "crawl_proxy.log") {
    $last = (Get-Content "crawl_proxy.log" | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
  }
  [pscustomobject]@{
    Running = $running
    Saved = $saved
    Unknown = $unk
    Discovered = $disc
    Last = $last
  }
}

Write-Output "Waiting for crawl to finish..."
for ($i = 0; $i -lt 40; $i++) {
  $s = Get-Status
  Write-Output ("[{0}] running={1} saved={2} unknown={3} last={4}" -f (Get-Date -Format HH:mm:ss), $s.Running, $s.Saved, $s.Unknown, $s.Last)
  if (-not $s.Running) { break }
  Start-Sleep -Seconds 30
}

$final = Get-Status
Write-Output "FINAL saved=$($final.Saved) unknown=$($final.Unknown) discovered=$($final.Discovered)"

# ensure summary exists
if (-not (Test-Path summary.json) -or $true) {
  $years = @{}
  Get-ChildItem "Vietnam" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
    $f = Join-Path $_.FullName "channels.txt"
    $n = 0
    if (Test-Path $f) {
      $n = @(Get-Content $f | Where-Object { $_.Trim() -ne "" }).Count
    }
    $years[$_.Name] = $n
  }
  $summary = @{
    VN = @{
      years = $years
      discovered = $final.Discovered
      unknown = $final.Unknown
      saved = $final.Saved
      finishedAt = (Get-Date).ToString("o")
    }
  }
  $summary | ConvertTo-Json -Depth 5 | Set-Content "summary.json" -Encoding UTF8
}

# gitignore
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
crawl_proxy.log
crawl_proxy.err.log
free_proxies_sample.txt
proxy_profile.yml
"@ -Encoding ASCII

if (-not (Test-Path "requirements.txt")) {
  Set-Content "requirements.txt" -Value "httpx==0.27.2`n" -Encoding ASCII
}

Write-Output "=== GIT COMMIT ==="
git rev-parse --show-toplevel
git status -sb
git add .gitignore crawler.py requirements.txt run.bat run_retry.bat run_proxy_resolve.bat summary.json Vietnam/ working_proxies.txt 2>$null
git status -sb
git commit -m "feat: finish Vietnam YouTube channel crawl with year buckets and proxy resolve"
git log -1 --oneline
git status -sb

Write-Output "=== GIT PUSH ==="
git push -u origin HEAD 2>&1
git status -sb
Write-Output "DONE"
