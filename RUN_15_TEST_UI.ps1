param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Continue"
$runnerUrl = "$BaseUrl/static/test_15_button_flow_runner.html"

Write-Host ""
Write-Host "EPL Logistics - Mo man hinh chay 5,000 kich ban" -ForegroundColor Cyan
Write-Host "URL: $runnerUrl" -ForegroundColor Gray
Write-Host ""

try {
    $healthUrl = "$BaseUrl/api/data/all"
    Invoke-WebRequest -Uri $healthUrl -Method GET -TimeoutSec 5 | Out-Null
    Write-Host "Backend dang chay OK. Dang mo trinh duyet..." -ForegroundColor Green
}
catch {
    Write-Host "Chua goi duoc backend o $BaseUrl" -ForegroundColor Yellow
    Write-Host "Neu server chua chay, anh mo PowerShell khac va chay:" -ForegroundColor Yellow
    Write-Host 'cd D:\Demo_Lao\EPL_System\backend\app' -ForegroundColor White
    Write-Host '$env:EPL_ENV_FILE="D:\Demo_Lao\.env"' -ForegroundColor White
    Write-Host '$env:DATABASE_MODE="postgres"' -ForegroundColor White
    Write-Host 'C:\Users\zinnn\miniconda3\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload' -ForegroundColor White
    Write-Host ""
    Write-Host "Van se mo trang test, sau khi backend len anh bam F5 roi Chay 15 test." -ForegroundColor Yellow
}

Start-Process $runnerUrl
