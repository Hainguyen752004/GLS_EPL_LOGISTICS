$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$langPath = Join-Path $root 'js\lang.json'
$htmlPath = Join-Path $root 'index.html'
$jsPath = Join-Path $root 'js\app.js'

$translations = Get-Content -Raw $langPath | ConvertFrom-Json
$keys = @(
  [regex]::Matches((Get-Content -Raw $htmlPath), 'data-i18n="([^"]+)"') |
    ForEach-Object { $_.Groups[1].Value }
  [regex]::Matches((Get-Content -Raw $jsPath), "\bt\(\s*['`"]([A-Za-z0-9_]+)['`"]\)") |
    ForEach-Object { $_.Groups[1].Value }
) | Where-Object { $_ -match '^[A-Za-z][A-Za-z0-9_]*$' } | Sort-Object -Unique

$missing = $keys | Where-Object { -not ($translations.PSObject.Properties.Name -contains $_) }
if ($missing) { throw "Missing translation keys: $($missing -join ', ')" }

$incomplete = @()
foreach ($entry in $translations.PSObject.Properties) {
  foreach ($locale in @('en','vi','la')) {
    if (-not ($entry.Value.PSObject.Properties.Name -contains $locale)) {
      $incomplete += $entry.Name
      break
    }
  }
}
if ($incomplete) { throw "Incomplete locale entries: $($incomplete.Name -join ', ')" }

Write-Output "i18n check passed: $($keys.Count) referenced keys, all locales present."
