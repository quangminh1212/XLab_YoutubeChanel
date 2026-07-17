Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match "wait_min1k|finish_min1k|crawler.py|run_min1k")
} | ForEach-Object {
  Write-Output ("PID={0} CMD={1}" -f $_.ProcessId, $_.CommandLine.Substring(0, [Math]::Min(120, $_.CommandLine.Length)))
}
if (Test-Path C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log) {
  Write-Output "--- wait tail ---"
  Get-Content C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log -Tail 3
}

