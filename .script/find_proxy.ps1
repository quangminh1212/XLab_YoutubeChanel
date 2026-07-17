$ErrorActionPreference = "Continue"
Write-Output "=== ENV ==="
Get-ChildItem Env: | Where-Object { $_.Name -match 'PROXY|proxy|VPN' } | ForEach-Object { "$($_.Name)=$($_.Value)" }
Write-Output "=== LISTEN ports common proxy ==="
netstat -ano | Select-String "LISTENING" | Select-String ":7890|:1080|:10808|:9050|:2080|:8080|:8118|:8888|:1087|:20170|:20171|:3128|:10809|:51837"
Write-Output "=== processes ==="
Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'clash|v2ray|xray|sing-box|tor|outline|warp|wireguard|openvpn|proxifier|ss-local|hysteria|naive' -or
  ($_.CommandLine -and $_.CommandLine -match 'socks|proxy|clash|v2ray|xray|tor')
} | ForEach-Object { "$($_.ProcessId) $($_.Name) $($_.CommandLine)" }
Write-Output "=== ssh config hosts ==="
if (Test-Path "$env:USERPROFILE\.ssh\config") { Get-Content "$env:USERPROFILE\.ssh\config" }
Write-Output "=== VPS folder ==="
if (Test-Path C:\Dev\VPS) { Get-ChildItem C:\Dev\VPS -Recurse -Depth 2 -File -ErrorAction SilentlyContinue | Select-Object -First 30 FullName }
Write-Output "=== winget/choco proxy tools? ==="
where.exe tor 2>$null
where.exe clash 2>$null
where.exe openvpn 2>$null
Test-Path "C:\Program Files\Tor Browser"
Test-Path "C:\Program Files\WireGuard"
Test-Path "C:\Program Files\OpenVPN"
Get-ChildItem "C:\Program Files" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Clash|V2Ray|Xray|Tor|WireGuard|OpenVPN|Outline|Cloudflare' } | ForEach-Object { $_.FullName }
