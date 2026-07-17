$ErrorActionPreference = "Continue"
$out = "C:\Dev\XLab_YoutubeChanel\.script\finish_min1k_watch.log"
function W($m) {
  $l = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m
  Add-Content $out $l -Encoding UTF8
  Write-Output $l
}
Set-Content $out "=== WATCH START $(Get-Date -Format o) ===" -Encoding UTF8
W "watch start"

for ($i = 0; $i -lt 200; $i++) {
  $mon = & powershell -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\monitor_min1k.ps1 2>&1 | Out-String
  W ("POLL $i`n" + $mon.Trim())

  if ($mon -match "phase=done") {
    W "DETECTED_DONE"
    break
  }

  if ($mon -match "status=NOT_RUNNING") {
    Start-Sleep -Seconds 25
    $mon2 = & powershell -NoProfile -NonInteractive -File C:\Dev\XLab_YoutubeChanel\.script\monitor_min1k.ps1 2>&1 | Out-String
    W ("RECHECK`n" + $mon2.Trim())
    if ($mon2 -match "status=NOT_RUNNING") {
      $tail = ""
      if (Test-Path "C:\Dev\XLab_YoutubeChanel\crawl_min1k.log") {
        $tail = (Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_min1k.log" -Tail 40) -join "`n"
      }
      if ($tail -match "ALL DONE" -or $tail -match "PASS2 EXIT" -or $mon2 -match "phase=done") {
        W "LOG_DONE"
        break
      }
      # process gone between passes or finished â€” give wait script time
      Start-Sleep -Seconds 90
      if (-not (Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and ($_.CommandLine -match "crawler.py|run_min1k")
      })) {
        W "PROCESS_GONE"
        break
      }
    }
  }

  Start-Sleep -Seconds 300
}

for ($j = 0; $j -lt 40; $j++) {
  if (Test-Path "C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log") {
    $w = Get-Content "C:\Dev\XLab_YoutubeChanel\.script\wait_min1k_out.log" -Raw
    if ($w -match "COMMIT_DONE|WAIT_SCRIPT_COMPLETE") {
      W "WAIT_COMMIT_OK"
      break
    }
  }
  Start-Sleep -Seconds 15
}

Set-Location "C:\Dev\XLab_YoutubeChanel"
git status -sb | Out-String | ForEach-Object { W $_ }
git log -3 --oneline | Out-String | ForEach-Object { W $_ }
W "WATCH_COMPLETE"

