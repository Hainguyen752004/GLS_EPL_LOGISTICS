param(
    [int]$ContractProbeExitCode
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot\scripts\audit-lib.ps1"

Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
if ([string]::IsNullOrWhiteSpace($env:EPL_ENV_FILE)) {
    $env:EPL_ENV_FILE = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
}

try {
    if ($PSBoundParameters.ContainsKey("ContractProbeExitCode")) {
        $powerShellExecutable = (Get-Process -Id $PID).Path
        Invoke-CheckedNative -FilePath $powerShellExecutable -ArgumentList @(
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "exit $ContractProbeExitCode"
        ) -CommandLabel "PowerShell contract probe"
        Write-Host "A-Z AUDIT PASSED" -ForegroundColor Green
        exit 0
    }

    $pythonExecutable = Resolve-EplPython

    Write-Host ""
    Write-Host "=== EPL A-Z AUDIT: FRONTEND ===" -ForegroundColor Cyan
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("--check", "frontend\js\app.js") -CommandLabel "node frontend syntax check"
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("--check", "frontend\js\workflow-ui-utils.js") -CommandLabel "node frontend utility syntax check"
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("frontend\tests\workflow-ui-utils.test.js") -CommandLabel "node workflow utility tests"
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("frontend\tests\route-map-utils.test.js") -CommandLabel "node route map tests"
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("frontend\tests\route-segment-distance-realtime.test.js") -CommandLabel "node route distance tests"
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("frontend\tests\stress-runner-config.test.js") -CommandLabel "node stress runner tests"
    Invoke-CheckedNative -FilePath "node" -ArgumentList @("frontend\tests\vietnamese-source-clean.test.js") -CommandLabel "node source-clean tests"

    Write-Host ""
    Write-Host "=== EPL A-Z AUDIT: BACKEND UNIT/FLOW ===" -ForegroundColor Cyan
    Invoke-CheckedNative -FilePath $pythonExecutable -ArgumentList @(
        "-m",
        "py_compile",
        "backend\app\main.py",
        "backend\app\models.py",
        "backend\app\routes\workflow_routes.py",
        "backend\app\services\workflow_service.py",
        "backend\app\services\errors.py"
    ) -CommandLabel "Python compile stage"
    Invoke-CheckedNative -FilePath $pythonExecutable -ArgumentList @(
        "-m",
        "pytest",
        "backend\tests\test_workflow_delete_guards.py",
        "backend\tests\test_vietnamese_source_clean.py",
        "-q"
    ) -CommandLabel "Python backend pytest stage"

    Write-Host ""
    Write-Host "=== EPL A-Z AUDIT: POSTGRESQL REAL DATA ===" -ForegroundColor Cyan
    Invoke-CheckedNative -FilePath $pythonExecutable -ArgumentList @(
        "backend\tests\az_postgres_audit.py"
    ) -CommandLabel "Python PostgreSQL audit stage"

    Write-Host ""
    Write-Host "A-Z AUDIT PASSED" -ForegroundColor Green
    exit 0
}
catch {
    $safeMessage = "Audit failed for an unexpected internal reason."
    if ($_.Exception.Data["AuditSafe"] -eq $true) {
        $safeMessage = $_.Exception.Message
    }
    Write-Host "A-Z AUDIT FAILED: $safeMessage" -ForegroundColor Red
    $nativeExitCode = $_.Exception.Data["ExitCode"]
    if ($null -eq $nativeExitCode) {
        $nativeExitCode = 1
    }
    exit $nativeExitCode
}
