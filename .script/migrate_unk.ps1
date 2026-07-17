$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel\Vietnam"
if (Test-Path "unknown\channels.txt") {
  Copy-Item "unknown\channels.txt" "unknown.txt" -Force
  Remove-Item "unknown" -Recurse -Force
  Write-Output "MIGRATED unknown/"
}
Get-ChildItem | Select-Object Name | Format-Table -AutoSize
