$ErrorActionPreference = "Continue"
& powershell -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\monitor_min1k.ps1
$p = "C:\Dev\XLab_YoutubeChanel\Vietnam\_enriched.json"
if (Test-Path $p) {
  $j = Get-Content $p -Raw | ConvertFrom-Json
  $n = @($j.PSObject.Properties).Count
  Write-Output "enriched_cache_keys=$n size=$((Get-Item $p).Length)"
  $withSubs = 0
  foreach ($prop in $j.PSObject.Properties) {
    $v = $prop.Value
    if ($null -ne $v.subscribers) { $withSubs++ }
  }
  Write-Output "enriched_with_subs=$withSubs"
}
Write-Output "--- log tail ---"
Get-Content C:\Dev\XLab_YoutubeChanel\crawl_min1k.log -Tail 8

