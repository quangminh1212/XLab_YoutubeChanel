$ErrorActionPreference = "Continue"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_proxy|run_retry') } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

# quick youtube check
try {
  $r = Invoke-WebRequest -Uri "https://www.youtube.com/" -UseBasicParsing -TimeoutSec 15
  Write-Output "YT_DIRECT=$($r.StatusCode) LEN=$($r.Content.Length)"
} catch {
  Write-Output "YT_DIRECT_FAIL=$($_.Exception.Message)"
}

Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_proxy.log" -Value "=== START $(Get-Date -Format o) ===`n" -Encoding UTF8
Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_proxy.err.log" -Value "" -Encoding UTF8

$proc = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "cmd.exe /c C:\Dev\XLab_YoutubeChanel\run_proxy_resolve.bat"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Write-Output "WMI_Return=$($proc.ReturnValue) PID=$($proc.ProcessId)"
Start-Sleep -Seconds 15
Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_proxy.log" -Tail 30
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler|run_proxy') } | ForEach-Object {
  Write-Output "PROC $($_.ProcessId) :: $($_.CommandLine)"
}
