param(
    [switch]$ResolvePython
)

$ErrorActionPreference = "Stop"

function New-AuditFailureException {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [int]$ExitCode = 1
    )

    $exception = [System.Exception]::new($Message)
    $exception.Data["AuditSafe"] = $true
    $exception.Data["ExitCode"] = $ExitCode
    return $exception
}

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$ArgumentList = @(),

        [string]$CommandLabel = "native command",

        [switch]$SuppressOutput
    )

    $nativePreferenceVariable = Get-Variable `
        -Name "PSNativeCommandUseErrorActionPreference" `
        -ErrorAction SilentlyContinue
    $hadNativePreference = $null -ne $nativePreferenceVariable
    if ($hadNativePreference) {
        $originalNativePreference = $nativePreferenceVariable.Value
    }

    $global:LASTEXITCODE = 0
    $invocationError = $null
    try {
        $PSNativeCommandUseErrorActionPreference = $false
        try {
            if ($SuppressOutput) {
                & $FilePath @ArgumentList *> $null
            }
            else {
                & $FilePath @ArgumentList
            }
        }
        catch {
            $invocationError = $_
        }
        $nativeExitCode = $LASTEXITCODE
    }
    finally {
        if ($hadNativePreference) {
            $PSNativeCommandUseErrorActionPreference = $originalNativePreference
        }
        else {
            Remove-Variable `
                -Name "PSNativeCommandUseErrorActionPreference" `
                -Scope Local `
                -ErrorAction SilentlyContinue
        }
    }

    if ($null -ne $invocationError -and $nativeExitCode -eq 0) {
        throw (New-AuditFailureException `
            -Message "$CommandLabel could not be started." `
            -ExitCode 1)
    }
    if ($nativeExitCode -ne 0) {
        throw (New-AuditFailureException `
            -Message "$CommandLabel failed with exit code $nativeExitCode." `
            -ExitCode $nativeExitCode)
    }
}

function Test-FullyQualifiedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path -match "^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)"
}

function Get-ValidatedPythonPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate
    )

    if (-not (Test-FullyQualifiedPath -Path $Candidate)) {
        return $null
    }
    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        return $null
    }

    $resolved = (Resolve-Path -LiteralPath $Candidate).ProviderPath
    try {
        Invoke-CheckedNative -FilePath $resolved -ArgumentList @("--version") -CommandLabel "Python interpreter validation" -SuppressOutput
    }
    catch {
        return $null
    }

    return $resolved
}

function Resolve-EplPython {
    if (-not [string]::IsNullOrWhiteSpace($env:EPL_PYTHON)) {
        $explicit = Get-ValidatedPythonPath -Candidate $env:EPL_PYTHON
        if ($null -eq $explicit) {
            throw (New-AuditFailureException -Message (
                "Python interpreter resolution failed: EPL_PYTHON must be a drive-qualified " +
                "or UNC path to an existing executable that passes --version."
            ))
        }
        return $explicit
    }

    if (-not [string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        $virtualEnvironmentPython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
        $validatedVirtualEnvironmentPython = Get-ValidatedPythonPath -Candidate $virtualEnvironmentPython
        if ($null -ne $validatedVirtualEnvironmentPython) {
            return $validatedVirtualEnvironmentPython
        }
    }

    $pythonCommand = Get-Command "python" -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $pythonCommand) {
        $commandPython = Get-ValidatedPythonPath -Candidate $pythonCommand.Path
        if ($null -ne $commandPython) {
            return $commandPython
        }
    }

    throw (New-AuditFailureException -Message (
        "Python interpreter resolution failed: no valid interpreter was found in " +
        "EPL_PYTHON, VIRTUAL_ENV, or Get-Command python."
    ))
}

if ($ResolvePython) {
    try {
        [Console]::Out.WriteLine((Resolve-EplPython))
        exit 0
    }
    catch {
        $safeMessage = "Python interpreter resolution failed."
        if ($_.Exception.Data["AuditSafe"] -eq $true) {
            $safeMessage = $_.Exception.Message
        }
        [Console]::Error.WriteLine($safeMessage)
        exit 1
    }
}
