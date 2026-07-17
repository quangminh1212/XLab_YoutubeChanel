$ErrorActionPreference = "Continue"
# clear old logs partially keep structure
Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_full.log" -Value "=== FULL CRAWL START $(Get-Date -Format o) ===`n" -Encoding UTF8
Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_full.err.log" -Value "" -Encoding UTF8
# Detached via WMI so SSH disconnect does not kill it
$cmd = 'cmd.exe'
$args = '/c C:\Dev\XLab_YoutubeChanel\run_full_crawl.bat'
$proc = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "$cmd $args"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Write-Host "WMI_Return=$($proc.ReturnValue) PID=$($proc.ProcessId)"
Start-Sleep -Seconds 12
Write-Host "=== log tail ==="
Get-Content C:\Dev\XLab_YoutubeChanel\crawl_full.log -Tail 15
Write-Host "=== procs ==="
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'crawler.py|run_full_crawl') } | ForEach-Object { "$($_.ProcessId) :: $($_.CommandLine)" }
