$ErrorActionPreference = "Continue"
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match 'wait_min1k_finish')
} | ForEach-Object {
  Write-Output "Kill wait $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "powershell.exe -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_finish.ps1"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Write-Output "WAIT_PID=$($r.ProcessId) RET=$($r.ReturnValue)"
Start-Sleep -Seconds 4
if (Test-Path C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log) {
  Get-Content C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log -Tail 10
}
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match 'wait_min1k|crawler')
} | ForEach-Object {
  Write-Output ("PROC {0}" -f $_.ProcessId)
}

