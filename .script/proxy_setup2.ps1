$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

Write-Output "=== Test subscription ==="
$subUrl = "https://go.4g.edu.vn/api/v1/client/subscribe?token=40b655b52cd611fbe9288a79dbde0b4e&flag=clashpc"
try {
  $r = Invoke-WebRequest -Uri $subUrl -UseBasicParsing -TimeoutSec 25
  Write-Output "SUB_STATUS=$($r.StatusCode)"
  Write-Output "SUB_LEN=$($r.Content.Length)"
  $snippet = $r.Content.Substring(0, [Math]::Min(800, $r.Content.Length))
  # redact long tokens in output somewhat
  Write-Output $snippet
  $out = "C:\Dev\XLab_YoutubeChanel\proxy_profile.yml"
  Set-Content -Path $out -Value $r.Content -Encoding UTF8
  Write-Output "SAVED=$out"
} catch {
  Write-Output "SUB_ERR=$($_.Exception.Message)"
}

Write-Output "=== winget ==="
try { winget --version } catch { Write-Output "no winget" }
try {
  winget search "Cloudflare WARP" --accept-source-agreements 2>&1 | Select-Object -First 15
} catch { Write-Output "winget search fail" }

Write-Output "=== Download free proxy sample ==="
$proxyApis = @(
  "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
  "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
)
$dir = "C:\Dev\XLab_YoutubeChanel"
foreach ($api in $proxyApis) {
  try {
    $p = Invoke-WebRequest -Uri $api -UseBasicParsing -TimeoutSec 20
    $lines = ($p.Content -split "`n" | Where-Object { $_.Trim() -match '^\d+\.\d+\.\d+\.\d+:\d+$' } | Select-Object -First 30)
    Write-Output "API_OK count=$($lines.Count) from $api"
    if ($lines.Count -gt 0) {
      $lines | Set-Content -Path "$dir\free_proxies_sample.txt" -Encoding ASCII
      break
    }
  } catch {
    Write-Output "API_FAIL $api :: $($_.Exception.Message)"
  }
}

Write-Output "=== Test direct youtube after ban ==="
try {
  $y = Invoke-WebRequest -Uri "https://www.youtube.com/" -UseBasicParsing -TimeoutSec 15 -MaximumRedirection 0 -ErrorAction SilentlyContinue
  Write-Output "YT_STATUS=$($y.StatusCode) LEN=$($y.Content.Length)"
} catch {
  if ($_.Exception.Response) {
    Write-Output "YT_STATUS=$([int]$_.Exception.Response.StatusCode)"
  } else {
    Write-Output "YT_ERR=$($_.Exception.Message)"
  }
}

Write-Output "DONE"
