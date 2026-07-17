$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"
if (-not $env:GH_TOKEN) {
  Write-Output "Set GH_TOKEN env then re-run"
  exit 1
}
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$($env:GH_TOKEN)"))
git -c credential.helper= -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $b64" push origin master 2>&1
Write-Output "PUSH_EXIT=$LASTEXITCODE"
git status -sb
