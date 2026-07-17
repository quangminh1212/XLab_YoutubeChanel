$ErrorActionPreference = "Continue"
Set-Location "C:\Dev\XLab_YoutubeChanel"

Write-Output "=== REPO ==="
git log -1 --oneline
git status -sb
git rev-parse HEAD

Write-Output "=== STRUCTURE ==="
Get-ChildItem Vietnam -Force | ForEach-Object { $_.Name }

Write-Output "=== BY YEAR ==="
$total = 0
$yearsFilled = 0
$emptyYears = @()
Get-ChildItem Vietnam -Directory | Where-Object { $_.Name -match '^\d{4}$' } | Sort-Object Name | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  $lines = @()
  if (Test-Path $f) {
    $lines = @(Get-Content $f -Encoding UTF8 | Where-Object { $_.Trim() -ne "" })
  }
  $n = $lines.Count
  $total += $n
  if ($n -gt 0) { $yearsFilled++ } else { $emptyYears += $_.Name }
  Write-Output ("YEAR {0}: {1}" -f $_.Name, $n)
}
Write-Output "TOTAL_SAVED=$total"
Write-Output "YEARS_FILLED=$yearsFilled"
Write-Output ("EMPTY_YEARS={0}" -f ($emptyYears -join ","))

Write-Output "=== UNKNOWN ==="
$unk = 0
$unkPath = "Vietnam\unknown\channels.txt"
if (Test-Path $unkPath) {
  $unkLines = @(Get-Content $unkPath -Encoding UTF8 | Where-Object { $_.Trim() -ne "" })
  $unk = $unkLines.Count
  Write-Output "UNKNOWN_COUNT=$unk"
  $unkLines | Select-Object -First 15 | ForEach-Object { Write-Output "UNK: $_" }
} else {
  Write-Output "UNKNOWN_COUNT=0"
}

Write-Output "=== DISCOVERED CACHE ==="
$disc = 0
$discIds = @{}
if (Test-Path "Vietnam\_discovered.json") {
  $j = Get-Content "Vietnam\_discovered.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  $props = @($j.PSObject.Properties)
  $disc = $props.Count
  foreach ($p in $props) { $discIds[$p.Name] = [string]$p.Value }
  Write-Output "DISCOVERED=$disc"
} else {
  Write-Output "DISCOVERED=0"
}

Write-Output "=== DEDUPE / FORMAT CHECK ==="
$allUrls = New-Object System.Collections.Generic.HashSet[string]
$dup = 0
$badFmt = 0
$ids = New-Object System.Collections.Generic.HashSet[string]
$yearIds = New-Object System.Collections.Generic.HashSet[string]
Get-ChildItem Vietnam -Directory | Where-Object { $_.Name -match '^\d{4}$' } | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  if (-not (Test-Path $f)) { return }
  foreach ($line in Get-Content $f -Encoding UTF8) {
    if ($line.Trim() -eq "") { continue }
    if ($line -notmatch ' \| https://www\.youtube\.com/channel/(UC[\w-]+)\s*$') {
      $badFmt++
      if ($badFmt -le 5) { Write-Output "BADFMT: $line" }
      continue
    }
    $url = ($line -split ' \| ', 2)[1].Trim()
    $id = $Matches[1]
    if (-not $allUrls.Add($url)) { $dup++ }
    [void]$ids.Add($id)
    [void]$yearIds.Add($id)
  }
}
Write-Output "UNIQUE_URLS=$($allUrls.Count)"
Write-Output "UNIQUE_IDS=$($ids.Count)"
Write-Output "DUP_URLS=$dup"
Write-Output "BAD_FORMAT=$badFmt"

# discovered not in year files
$missingYear = 0
$missingSamples = @()
foreach ($id in $discIds.Keys) {
  if (-not $yearIds.Contains($id)) {
    $missingYear++
    if ($missingSamples.Count -lt 10) {
      $missingSamples += ("{0} | https://www.youtube.com/channel/{1}" -f $discIds[$id], $id)
    }
  }
}
Write-Output "DISCOVERED_WITHOUT_YEAR=$missingYear"
$missingSamples | ForEach-Object { Write-Output "NOYEAR: $_" }

# unknown overlap with saved
$unkOnly = 0
if (Test-Path $unkPath) {
  foreach ($line in Get-Content $unkPath -Encoding UTF8) {
    if ($line -match '/channel/(UC[\w-]+)') {
      if (-not $yearIds.Contains($Matches[1])) { $unkOnly++ }
    }
  }
}
Write-Output "UNKNOWN_NOT_IN_SAVED=$unkOnly"

Write-Output "=== SAMPLE LINES ==="
Get-ChildItem Vietnam -Directory | Where-Object { $_.Name -match '^\d{4}$' } | Sort-Object Name | Select-Object -Last 3 | ForEach-Object {
  $f = Join-Path $_.FullName "channels.txt"
  Write-Output ("--- {0} ---" -f $_.Name)
  if (Test-Path $f) { Get-Content $f -Encoding UTF8 -TotalCount 3 }
}

Write-Output "=== SUMMARY.JSON ==="
if (Test-Path summary.json) { Get-Content summary.json -Raw -Encoding UTF8 }

Write-Output "=== COVERAGE ASSESSMENT INPUTS ==="
Write-Output "saved_with_year=$($ids.Count)"
Write-Output "discovered_total=$disc"
Write-Output "coverage_of_discovered_pct=$(if ($disc -gt 0) { [Math]::Round(100.0 * $ids.Count / $disc, 2) } else { 0 })"
Write-Output "AUDIT_DONE"
