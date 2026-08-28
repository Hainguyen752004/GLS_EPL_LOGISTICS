param(
  [switch]$SeedData,
  [switch]$StartServer,
  [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendApp = Join-Path $ProjectRoot "backend\app"
$EnvFile = "D:\Demo_Lao\.env"
$PythonExe = "C:\Users\zinnn\miniconda3\python.exe"
$DemoUrl = "http://127.0.0.1:8000"

Write-Host ""
Write-Host "=== EPL LOGISTICS - DEMO 3H ===" -ForegroundColor Cyan
Write-Host "Project : $ProjectRoot"
Write-Host "ENV     : $EnvFile"
Write-Host "URL     : $DemoUrl"
Write-Host ""

if (!(Test-Path $EnvFile)) {
  Write-Host "Cannot find D:\Demo_Lao\.env. Check DB config before demo." -ForegroundColor Red
  exit 1
}

$env:EPL_ENV_FILE = $EnvFile

Write-Host "Pre-demo checklist:" -ForegroundColor Yellow
Write-Host "1. PostgreSQL is running if .env points to PostgreSQL."
Write-Host "2. Press Ctrl + F5 in browser to load latest JS."
Write-Host "3. Open Master Data first, then Overview / Control Tower."
Write-Host ""

if ($SeedData) {
  Write-Host "Seeding PostgreSQL demo data..." -ForegroundColor Cyan
  Push-Location $ProjectRoot
  & $PythonExe "backend\scripts\seed_demo_master_data.py"
  Pop-Location
  Write-Host "Seed finished. Main demo DO: DEMO-DO-2026-001" -ForegroundColor Green
  Write-Host ""
}

if ($OpenBrowser) {
  Write-Host "Opening browser: $DemoUrl" -ForegroundColor Cyan
  Start-Process $DemoUrl
}

Write-Host "Server command:" -ForegroundColor Yellow
Write-Host "cd $BackendApp"
Write-Host '$env:EPL_ENV_FILE="D:\Demo_Lao\.env"'
Write-Host "$PythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"
Write-Host ""

if ($StartServer) {
  Write-Host "Starting server. Keep this window open; press Ctrl+C to stop." -ForegroundColor Green
  Push-Location $BackendApp
  & $PythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
  Pop-Location
} else {
  Write-Host "To start server now:" -ForegroundColor Cyan
  Write-Host ".\RUN_DEMO_3_GIO.ps1 -StartServer"
  Write-Host ""
  Write-Host "To seed demo data and start server:" -ForegroundColor Cyan
  Write-Host ".\RUN_DEMO_3_GIO.ps1 -SeedData -StartServer -OpenBrowser"
}
