$ErrorActionPreference = "Continue"
# kill stuck crawler
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_retry') } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

Add-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_retry.log" -Value "`n=== RESTART FAST RESOLVE $(Get-Date -Format o) ===`n" -Encoding UTF8
Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_retry.err.log" -Value "" -Encoding UTF8

$proc = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "cmd.exe /c C:\Dev\XLab_YoutubeChanel\run_retry.bat"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Write-Output "WMI_Return=$($proc.ReturnValue) PID=$($proc.ProcessId)"
Start-Sleep -Seconds 8
Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_retry.log" -Tail 20
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler|run_retry') } | ForEach-Object {
  Write-Output "PROC $($_.ProcessId) :: $($_.CommandLine)"
}
