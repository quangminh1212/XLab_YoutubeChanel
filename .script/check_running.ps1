$ErrorActionPreference = "Continue"
Write-Output "=== PROCS ==="
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match 'crawler|run_min1k|wait_min1k')
} | ForEach-Object {
  Write-Output ("{0} :: {1}" -f $_.ProcessId, $_.CommandLine)
}
Write-Output "=== LOG TAIL ==="
if (Test-Path C:\Dev\XLab_YoutubeChanel\crawl_min1k.log) {
  Get-Content C:\Dev\XLab_YoutubeChanel\crawl_min1k.log -Tail 10
}
Write-Output "=== WAIT OUT ==="
if (Test-Path C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log) {
  Get-Content C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log -Tail 10
} else { "no wait out" }

