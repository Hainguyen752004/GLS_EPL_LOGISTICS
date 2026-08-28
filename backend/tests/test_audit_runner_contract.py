from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "RUN_AZ_AUDIT.ps1"
LIBRARY = ROOT / "scripts" / "audit-lib.ps1"


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    assert executable is not None, "PowerShell is required for the audit runner contract tests"
    return executable


def _powershell_args(*args: str) -> list[str]:
    return [_powershell(), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", *args]


def _resolver_environment(**updates: str | None) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("EPL_PYTHON", "VIRTUAL_ENV", "PYTHONHOME"):
        environment.pop(name, None)
    for name, value in updates.items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return environment


def _resolve_python(environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _powershell_args("-File", str(LIBRARY), "-ResolvePython"),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _assert_only_resolved_path(
    result: subprocess.CompletedProcess[str], expected: Path
) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert len(lines) == 1, result.stdout
    assert os.path.normcase(os.path.abspath(lines[0])) == os.path.normcase(
        os.path.abspath(expected)
    )


@pytest.fixture
def virtual_environment(tmp_path: Path) -> Path:
    target = tmp_path / "venv"
    venv.EnvBuilder(with_pip=False).create(target)
    return target


def _write_cmd(path: Path, lines: list[str]) -> None:
    path.write_text("@echo off\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def test_native_failure_exits_with_same_code_and_never_prints_pass():
    result = subprocess.run(
        _powershell_args("-File", str(RUNNER), "-ContractProbeExitCode", "7"),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 7, output
    assert "A-Z AUDIT FAILED" in output
    assert "A-Z AUDIT PASSED" not in output
    assert "A-Z AUDIT FINISHED" not in output


def test_native_failure_keeps_code_when_native_errors_are_terminating():
    command = "; ".join(
        [
            "$PSNativeCommandUseErrorActionPreference = $true",
            '$ErrorActionPreference = "Stop"',
            f"& {_ps_quote(str(RUNNER))} -ContractProbeExitCode 7",
            "exit $LASTEXITCODE",
        ]
    )
    result = subprocess.run(
        _powershell_args("-Command", command),
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 7, output
    assert "A-Z AUDIT FAILED" in output
    assert "A-Z AUDIT PASSED" not in output
    library_source = LIBRARY.read_text(encoding="utf-8")
    assert "$PSNativeCommandUseErrorActionPreference = $false" in library_source


def test_resolver_prefers_valid_absolute_epl_python(virtual_environment: Path):
    explicit = Path(sys.executable).resolve()
    environment = _resolver_environment(
        EPL_PYTHON=str(explicit),
        VIRTUAL_ENV=str(virtual_environment),
        PATH="",
    )

    _assert_only_resolved_path(_resolve_python(environment), explicit)


def test_resolver_uses_virtual_environment_before_path(virtual_environment: Path):
    expected = virtual_environment / "Scripts" / "python.exe"
    environment = _resolver_environment(
        VIRTUAL_ENV=str(virtual_environment),
        PATH=str(Path(sys.executable).resolve().parent),
    )

    _assert_only_resolved_path(_resolve_python(environment), expected)


def test_resolver_falls_back_to_get_command_python():
    expected = Path(sys.executable).resolve()
    environment = _resolver_environment(PATH=str(expected.parent))

    _assert_only_resolved_path(_resolve_python(environment), expected)


@pytest.mark.parametrize("explicit", ["python.exe", "Z:\\missing\\python.exe"])
def test_explicit_invalid_epl_python_fails_without_fallback(explicit: str):
    environment = _resolver_environment(
        EPL_PYTHON=explicit,
        PATH=str(Path(sys.executable).resolve().parent),
    )

    result = _resolve_python(environment)

    assert result.returncode != 0
    assert result.stdout == ""


def test_explicit_rooted_path_without_drive_qualification_is_rejected():
    with tempfile.TemporaryDirectory(dir=ROOT) as temporary_directory:
        fake_python = Path(temporary_directory) / "python.cmd"
        _write_cmd(fake_python, ["exit /b 0"])
        qualified = str(fake_python.resolve())
        assert qualified[1:3] == ":\\"
        rooted_without_drive = qualified[2:]
        environment = _resolver_environment(
            EPL_PYTHON=rooted_without_drive,
            PATH=str(Path(sys.executable).resolve().parent),
        )

        result = _resolve_python(environment)

    assert result.returncode != 0
    assert result.stdout == ""


def test_explicit_python_that_fails_version_check_does_not_fallback(tmp_path: Path):
    invalid = tmp_path / "invalid-python.cmd"
    _write_cmd(invalid, ["exit /b 23"])
    environment = _resolver_environment(
        EPL_PYTHON=str(invalid.resolve()),
        PATH=str(Path(sys.executable).resolve().parent),
    )

    result = _resolve_python(environment)

    assert result.returncode != 0
    assert result.stdout == ""


def test_resolver_fails_when_all_candidates_are_absent_or_invalid(tmp_path: Path):
    environment = _resolver_environment(
        VIRTUAL_ENV=str(tmp_path / "broken-venv"),
        PATH="",
    )

    result = _resolve_python(environment)

    assert result.returncode != 0
    assert result.stdout == ""


def test_runner_uses_checked_commands_and_has_no_forbidden_interpreters():
    runner_source = RUNNER.read_text(encoding="utf-8")
    library_source = LIBRARY.read_text(encoding="utf-8")
    combined_source_lower = (runner_source + library_source).lower()

    assert "a-z audit finished" not in combined_source_lower
    assert "miniconda" not in combined_source_lower
    assert not re.search(
        r"(?m)^\s*(?:node|python|py(?:\.exe)?)\s", combined_source_lower
    )
    assert runner_source.count("Invoke-CheckedNative") >= 11
    assert "Invoke-CheckedNative -FilePath $resolved" in library_source
    assert not re.search(r"(?m)^\s*&\s+\$resolved\b", library_source)


def test_runner_runs_python_stages_in_order_and_preserves_epl_env_file(tmp_path: Path):
    command_dir = tmp_path / "commands"
    command_dir.mkdir()
    log = tmp_path / "audit.log"
    python = command_dir / "audit-python.cmd"
    node = command_dir / "node.cmd"
    _write_cmd(
        python,
        [
            'if "%~1"=="--version" exit /b 0',
            'echo python^|%EPL_ENV_FILE%^|%*>>"%AUDIT_TEST_LOG%"',
            "exit /b 0",
        ],
    )
    _write_cmd(node, ['echo node^|%*>>"%AUDIT_TEST_LOG%"', "exit /b 0"])
    sentinel_env_file = str(tmp_path / "caller.env")
    environment = _resolver_environment(
        EPL_PYTHON=str(python.resolve()),
        EPL_ENV_FILE=sentinel_env_file,
        AUDIT_TEST_LOG=str(log),
        PATH=str(command_dir),
    )

    result = subprocess.run(
        _powershell_args("-File", str(RUNNER)),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "A-Z AUDIT PASSED" in output
    assert "A-Z AUDIT FINISHED" not in output
    python_calls = [
        line for line in log.read_text(encoding="utf-8").splitlines() if line.startswith("python|")
    ]
    assert len(python_calls) == 3
    assert all(f"python|{sentinel_env_file}|" in line for line in python_calls)
    assert "-m py_compile" in python_calls[0]
    assert "-m pytest" in python_calls[1]
    assert "backend\\tests\\az_postgres_audit.py" in python_calls[2]


def test_runner_stops_on_first_node_failure_and_propagates_code(tmp_path: Path):
    command_dir = tmp_path / "commands"
    command_dir.mkdir()
    python = command_dir / "audit-python.cmd"
    node = command_dir / "node.cmd"
    _write_cmd(python, ['if "%~1"=="--version" exit /b 0', "exit /b 0"])
    _write_cmd(node, ["exit /b 9"])
    environment = _resolver_environment(
        EPL_PYTHON=str(python.resolve()),
        PATH=str(command_dir),
    )

    result = subprocess.run(
        _powershell_args("-File", str(RUNNER)),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 9, output
    assert "A-Z AUDIT FAILED" in output
    assert "A-Z AUDIT PASSED" not in output


def test_invalid_explicit_python_reports_safe_resolution_reason(tmp_path: Path):
    secret = "DO_NOT_LEAK_EPL_PYTHON_VALUE"
    environment = _resolver_environment(
        EPL_PYTHON=str(tmp_path / secret / "python.exe"),
        PATH=str(Path(sys.executable).resolve().parent),
    )

    result = subprocess.run(
        _powershell_args("-File", str(RUNNER)),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "A-Z AUDIT FAILED" in output
    assert "Python interpreter resolution failed" in output
    assert secret not in output


def test_missing_node_reports_safe_command_reason_without_environment_values():
    secret = "DO_NOT_LEAK_ENV_FILE_VALUE"
    environment = _resolver_environment(
        EPL_PYTHON=str(Path(sys.executable).resolve()),
        EPL_ENV_FILE=secret,
        PATH="",
    )

    result = subprocess.run(
        _powershell_args("-File", str(RUNNER)),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "A-Z AUDIT FAILED" in output
    assert "node" in output.lower()
    assert "could not be started" in output.lower()
    assert secret not in output
