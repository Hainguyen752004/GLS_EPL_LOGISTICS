import ast
import os
import subprocess
import sys
from pathlib import Path

from conftest import _database_fingerprint

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"


def test_sqlite_mode_requires_an_explicit_database_mode(import_database, tmp_path):
    database_file = tmp_path / "explicit.sqlite3"
    result = import_database(
        {
            "DATABASE_MODE": "sqlite",
            "DATABASE_URL": f"sqlite:///{database_file.as_posix()}",
        }
    )

    assert result.returncode == 0, result.stderr
    assert not database_file.exists()


def test_sqlite_connections_enforce_foreign_keys(tmp_path):
    database_file = tmp_path / "foreign-keys.sqlite3"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(APP_DIR),
            "DATABASE_MODE": "sqlite",
            "DATABASE_URL": f"sqlite:///{database_file.as_posix()}",
        }
    )
    script = (
        "from sqlalchemy import text; "
        "from database import engine; "
        "conn = engine.connect(); "
        "print(conn.execute(text('PRAGMA foreign_keys')).scalar()); "
        "conn.close()"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("1")


def test_postgres_configuration_does_not_connect_or_create_sqlite_fallback(tmp_path):
    fallback_file = APP_DIR / "epl_logistics.db"
    existed_before = fallback_file.exists()
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(APP_DIR),
            "DATABASE_MODE": "postgres",
            "DATABASE_URL": "postgresql://invalid:invalid@127.0.0.1:1/epl_test",
        }
    )
    script = (
        "from sqlalchemy.engine import Engine; "
        "Engine.connect=lambda self: (_ for _ in ()).throw(AssertionError('connected')); "
        "import database"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=BACKEND_DIR, env=env,
        capture_output=True, text=True, timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "invalid:invalid" not in result.stderr
    assert "SQLite" not in result.stdout
    assert fallback_file.exists() is existed_before


def test_postgres_configuration_failure_uses_sanitized_marker(import_database):
    result = import_database(
        {
            "DATABASE_MODE": "postgres",
            "DATABASE_URL": "mysql://secret-user:secret-password@db.example/epl",
        }
    )

    assert result.returncode != 0
    assert "DATABASE_UNAVAILABLE" in result.stderr
    assert "secret-user" not in result.stderr
    assert "secret-password" not in result.stderr


def test_invalid_database_mode_is_rejected(import_database):
    result = import_database(
        {"DATABASE_MODE": "automatic", "DATABASE_URL": "sqlite:///:memory:"}
    )

    assert result.returncode != 0
    assert "DATABASE_MODE" in result.stderr


def test_missing_database_mode_is_rejected(import_database):
    result = import_database(
        {"DATABASE_MODE": None, "DATABASE_URL": "sqlite:///:memory:"}
    )

    assert result.returncode != 0
    assert "DATABASE_MODE" in result.stderr


def test_database_logs_are_cp1252_safe(import_database, tmp_path):
    result = import_database(
        {
            "DATABASE_MODE": "sqlite",
            "DATABASE_URL": f"sqlite:///{(tmp_path / 'logging.sqlite3').as_posix()}",
            "PYTHONIOENCODING": "cp1252:strict",
        }
    )

    assert result.returncode == 0, result.stderr


def test_startup_does_not_seed_or_reset_data():
    source = (APP_DIR / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    startup = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "on_startup"
    )
    called_names = {
        node.func.id
        for node in ast.walk(startup)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "seed_full_demo_data" not in called_names
    assert "clear_orders" not in called_names


def test_startup_executes_without_seed_or_reset_side_effects():
    source = (APP_DIR / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    startup = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef)
        and node.name == "on_startup"
    )
    calls = []
    namespace = {
        "app": type("App", (), {"on_event": lambda self, _name: lambda fn: fn})(),
        "auto_migrate_db": lambda: calls.append("migrate"),
        "_start_currency_reference_scheduler": lambda: calls.append("currency_scheduler"),
        "print": lambda *_args, **_kwargs: None,
    }
    exec(compile(ast.Module(body=[startup], type_ignores=[]), "main.py", "exec"), namespace)

    namespace["on_startup"]()
    assert calls == ["migrate", "currency_scheduler"]


def test_destructive_seed_and_reset_routes_are_not_exposed():
    source = (APP_DIR / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    route_paths = {
        decorator.args[0].value
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        and decorator.args
        and isinstance(decorator.args[0], ast.Constant)
        and isinstance(decorator.func, ast.Attribute)
    }

    assert "/api/reset-orders" not in route_paths
    assert "/api/seed-demo-data" not in route_paths


def test_main_has_no_seed_or_reset_imports():
    source = (APP_DIR / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "seed_full_demo" not in imported_modules
    assert "clear_sample_data" not in imported_modules


def test_config_does_not_search_above_project_root():
    source = (APP_DIR / "config.py").read_text(encoding="utf-8")
    assert '"..", "..", "..", ".env"' not in source


def test_http_database_requests_are_isolated(app_client):
    client, database_file, real_before = app_client

    response = client.get("/api/vehicles")

    assert response.status_code == 200
    assert response.json() == []
    assert database_file.exists()
    assert _database_fingerprint(APP_DIR / "epl_logistics.db") == real_before


def test_postgres_alias_is_rejected_with_stable_config_error(import_database):
    result = import_database({"DATABASE_MODE": "postgres", "DATABASE_URL": "postgres://host/epl"})
    assert result.returncode != 0
    assert "DATABASE_UNAVAILABLE" in result.stderr
