$ErrorActionPreference = "Continue"
$proc = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'crawler.py' }
if ($proc) {
    Write-Output "STATUS=RUNNING PID=$($proc.ProcessId)"
} else {
    Write-Output "STATUS=NOT_RUNNING"
}

$logPath = "C:\Dev\XLab_YoutubeChanel\crawl_full.log"
if (Test-Path $logPath) {
    $lines = Get-Content $logPath
    Write-Output "LOG_LINES=$($lines.Count)"
    Write-Output "--- tail ---"
    $lines | Select-Object -Last 15 | ForEach-Object { Write-Output $_ }
} else {
    Write-Output "NO_LOG"
}

$channels = 0
$byYear = @{}
$vn = "C:\Dev\XLab_YoutubeChanel\Vietnam"
if (Test-Path $vn) {
    Get-ChildItem $vn -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $f = Join-Path $_.FullName "channels.txt"
        if (Test-Path $f) {
            $n = @(Get-Content $f -ErrorAction SilentlyContinue | Where-Object { $_.Trim() -ne "" }).Count
            if ($n -gt 0) { $byYear[$_.Name] = $n }
            $channels += $n
        }
    }
}
Write-Output "CHANNELS_SAVED=$channels"
if ($byYear.Count -gt 0) {
    $byYear.GetEnumerator() | Sort-Object Name | ForEach-Object {
        Write-Output ("YEAR {0}: {1}" -f $_.Key, $_.Value)
    }
}

$errPath = "C:\Dev\XLab_YoutubeChanel\crawl_full.err.log"
if (Test-Path $errPath) {
    $err = Get-Content $errPath -Raw -ErrorAction SilentlyContinue
    if ($err -and $err.Trim()) {
        Write-Output "HAS_ERR"
        $len = [Math]::Min(400, $err.Length)
        Write-Output $err.Substring(0, $len)
    }
}
