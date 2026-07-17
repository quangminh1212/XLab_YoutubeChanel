$ErrorActionPreference = "Continue"
Write-Output "=== Clash install ==="
Get-ChildItem "C:\Program Files\Clash for Windows" -ErrorAction SilentlyContinue | Select-Object Name
Get-ChildItem "$env:USERPROFILE\.config\clash*" -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object FullName
Get-ChildItem "$env:USERPROFILE\AppData\Roaming\clash*" -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 40 FullName
Get-ChildItem "$env:USERPROFILE\AppData\Local" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'clash|Clash' } | ForEach-Object { $_.FullName }
# common clash data paths
$paths = @(
  "$env:USERPROFILE\.config\clash",
  "$env:USERPROFILE\AppData\Roaming\clash_win",
  "$env:USERPROFILE\AppData\Roaming\Clash for Windows",
  "C:\Program Files\Clash for Windows\data",
  "C:\Users\GHC\Documents\clash"
)
foreach ($p in $paths) {
  if (Test-Path $p) {
    Write-Output "FOUND $p"
    Get-ChildItem $p -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 30 FullName
  }
}
Write-Output "=== Clash process ==="
Get-Process | Where-Object { $_.Name -match 'Clash|clash' } | Format-Table Id,Name -AutoSize
Write-Output "=== Test common proxy ports ==="
foreach ($port in 7890,7891,7892,1080,10808,10809,9090,20171,20170) {
  $tcp = Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet
  if ($tcp) { Write-Output "OPEN 127.0.0.1:$port" }
}
Write-Output "=== SSH to VPS? ==="
# try batchmode connect
ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new hakinet@36.50.26.247 "echo VPS_OK; hostname; whoami" 2>&1
Write-Output "=== DONE ==="
