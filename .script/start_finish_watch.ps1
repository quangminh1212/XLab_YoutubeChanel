$ErrorActionPreference = "Continue"
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match "finish_min1k_watch")
} | ForEach-Object {
  Write-Output "Kill old watch $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "powershell.exe -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\finish_min1k_watch.ps1"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Write-Output "WATCH_PID=$($r.ProcessId) RET=$($r.ReturnValue)"
Start-Sleep -Seconds 3
if (Test-Path C:\Dev\XLab_YoutubeChanel\.script\finish_min1k_watch.log) {
  Get-Content C:\Dev\XLab_YoutubeChanel\.script\finish_min1k_watch.log -Tail 5
}

