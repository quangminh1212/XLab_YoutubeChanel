$ErrorActionPreference = "Continue"
# kill old crawler if any
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'crawler.py|run_retry|run_full_crawl' } | ForEach-Object {
  Write-Output "Kill $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

# bootstrap discovered from existing year files
$boot = @'
import json, re
from pathlib import Path
root = Path(r"C:\Dev\XLab_YoutubeChanel\Vietnam")
disc = {}
for year_dir in root.iterdir():
    if not year_dir.is_dir() or not year_dir.name.isdigit():
        continue
    f = year_dir / "channels.txt"
    if not f.exists():
        continue
    for line in f.read_text(encoding="utf-8").splitlines():
        if " | " not in line:
            continue
        title, url = line.rsplit(" | ", 1)
        m = re.search(r"/channel/(UC[\w-]+)", url)
        if m:
            disc[m.group(1)] = title.strip()
out = root / "_discovered.json"
out.write_text(json.dumps(disc, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
print(f"bootstrapped_discovered={len(disc)}")
'@
$boot | Set-Content -Path "C:\Users\GHC\boot_discovered.py" -Encoding UTF8
& "C:\Program Files\Python310\python.exe" "C:\Users\GHC\boot_discovered.py"

Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_retry.log" -Value "=== RETRY START $(Get-Date -Format o) ===`n" -Encoding UTF8
Set-Content -Path "C:\Dev\XLab_YoutubeChanel\crawl_retry.err.log" -Value "" -Encoding UTF8

$proc = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = "cmd.exe /c C:\Dev\XLab_YoutubeChanel\run_retry.bat"
  CurrentDirectory = "C:\Dev\XLab_YoutubeChanel"
}
Write-Output "WMI_Return=$($proc.ReturnValue) PID=$($proc.ProcessId)"
Start-Sleep -Seconds 10
Get-Content "C:\Dev\XLab_YoutubeChanel\crawl_retry.log" -Tail 15
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'crawler|run_retry' } | ForEach-Object {
  Write-Output "PROC $($_.ProcessId) :: $($_.CommandLine)"
}
