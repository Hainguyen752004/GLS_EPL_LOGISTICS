param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== EPL DEMO HEALTH CHECK ===" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl"
Write-Host ""

function Check-Url {
  param(
    [string]$Name,
    [string]$Url
  )
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    Write-Host "[OK] $Name -> HTTP $($response.StatusCode)" -ForegroundColor Green
    return $true
  } catch {
    Write-Host "[FAIL] $Name -> $($_.Exception.Message)" -ForegroundColor Red
    return $false
  }
}

$healthOk = Check-Url -Name "API health" -Url "$BaseUrl/api/health"

if (-not $healthOk) {
  Write-Host ""
  Write-Host "Server chua chay hoac bi loi. Chay lenh nay:" -ForegroundColor Yellow
  Write-Host "cd D:\Demo_Lao\EPL_System"
  Write-Host ".\RUN_DEMO_3_GIO.ps1 -StartServer"
  exit 1
}

$dataOk = Check-Url -Name "Data payload" -Url "$BaseUrl/api/data/all"

Write-Host ""
Write-Host "Browser checklist:" -ForegroundColor Yellow
Write-Host "1. Open $BaseUrl"
Write-Host "2. Press Ctrl + F5"
Write-Host "3. Go to Master Data -> Finance tabs and Overview -> Shipment 360"

if ($dataOk) {
  Write-Host ""
  Write-Host "Demo health check passed. Anh co the rehearsal theo DEMO_CHEAT_SHEET_1_TRANG.md" -ForegroundColor Green
} else {
  Write-Host ""
  Write-Host "API health OK nhung /api/data/all fail. Kiem tra PostgreSQL/.env hoac chay seed lai." -ForegroundColor Yellow
  exit 2
}
