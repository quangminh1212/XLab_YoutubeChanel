$ErrorActionPreference = "Continue"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_proxy') } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Output "KILLED"
