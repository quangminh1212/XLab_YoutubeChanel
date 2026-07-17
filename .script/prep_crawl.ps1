$ErrorActionPreference = "Stop"
Set-Location "C:\Dev\XLab_YoutubeChanel"
& "C:\Program Files\Python310\python.exe" -m pip install -q httpx==0.27.2
New-Item -ItemType Directory -Force -Path "Vietnam" | Out-Null
2005..2026 | ForEach-Object {
  $d = Join-Path "Vietnam" $_.ToString()
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  $f = Join-Path $d "channels.txt"
  if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f | Out-Null }
}
Write-Host "STRUCTURE_OK"
Get-ChildItem Vietnam -Directory | Measure-Object | ForEach-Object { "years=$($_.Count)" }
& "C:\Program Files\Python310\python.exe" -c "import httpx; print('httpx', httpx.__version__)"
