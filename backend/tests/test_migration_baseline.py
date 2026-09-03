"""Đường khởi tạo database mới.

Các migration lịch sử là lệnh SỬA bảng: v001 ALTER những bảng được giả định đã
tồn tại, v006 đòi bảng TMS khớp đúng DDL viết tay của nó. Nên chúng không thể
dựng lược đồ từ đầu — trước đây điều này khiến auto_migrate_db() luôn thất bại
trên database mới, và lỗi bị nuốt im lặng nên không ai thấy.

Cách xử lý: database mới thì dựng lược đồ từ model rồi ĐÁNH MỐC lịch sử
migration là đã xong. Các migration về sau chạy bình thường.
"""

import importlib
import sqlite3
import sys

import pytest


def _fresh_database(tmp_path, monkeypatch, name="probe.sqlite3"):
    """Nạp lại module database trỏ vào một file SQLite dùng một lần."""
    for module in list(sys.modules):
        if module in ("database", "models", "config") or module.startswith("migrations"):
            del sys.modules[module]
    path = tmp_path / name
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    monkeypatch.setenv("EPL_ENV_FILE", str(tmp_path / "no-env-file"))
    return importlib.import_module("database"), path


def test_virgin_database_is_built_from_models_and_stamped(tmp_path, monkeypatch):
    database, path = _fresh_database(tmp_path, monkeypatch)
    runner = importlib.import_module("migrations.runner")

    completed = database.auto_migrate_db()

    assert len(completed) == len(runner.MIGRATIONS)
    applied = runner.applied_versions(f"sqlite:///{path.as_posix()}")
    assert runner.required_migration_head() in applied, (
        "probe readiness kiểm head trong schema_migrations, nên phải có mặt"
    )
    # Lược đồ phải thực sự được dựng, không chỉ đánh mốc rỗng.
    tables = set(database.inspect(database.engine).get_table_names())
    assert "quotations" in tables and "transport_trips" in tables
    assert "schema_migrations" in tables


def test_second_startup_on_the_same_database_does_nothing(tmp_path, monkeypatch):
    """Khởi động lại phải là lệnh rỗng, không đánh mốc lại."""
    database, _ = _fresh_database(tmp_path, monkeypatch)
    database.auto_migrate_db()

    assert database.auto_migrate_db() == []


def test_model_built_database_without_history_is_only_stamped(tmp_path, monkeypatch):
    """create_all rồi mới khởi động: chỉ cần đánh mốc, không chạy migration cũ.

    Đây đúng là trạng thái mà bộ test và các script seed để lại.
    """
    database, path = _fresh_database(tmp_path, monkeypatch)
    importlib.import_module("models")
    database.Base.metadata.create_all(bind=database.engine)
    runner = importlib.import_module("migrations.runner")
    assert runner.applied_versions(f"sqlite:///{path.as_posix()}") is None

    assert database._needs_baseline() is True
    completed = database.auto_migrate_db()

    assert len(completed) == len(runner.MIGRATIONS)


def test_legacy_database_missing_v001_columns_runs_the_history(tmp_path, monkeypatch):
    """Database cũ từ thời chưa có migration PHẢI đi qua upgrade().

    Đánh mốc một database như vậy sẽ bỏ sót mọi bước migration mà nó thực sự
    cần, nên đây là nhánh nguy hiểm nhất và phải phân biệt cho đúng.
    """
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    # quotations thiếu canonical_status — cột do v001 sinh ra.
    connection.execute("CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT)")
    connection.commit()
    connection.close()

    database, _ = _fresh_database(tmp_path, monkeypatch, "legacy.sqlite3")

    assert database._needs_baseline() is False, (
        "database cũ phải chạy migration lịch sử, không được đánh mốc"
    )


def test_baseline_refuses_a_database_that_already_has_history(tmp_path, monkeypatch):
    database, path = _fresh_database(tmp_path, monkeypatch)
    database.auto_migrate_db()
    runner = importlib.import_module("migrations.runner")

    with pytest.raises(RuntimeError) as excinfo:
        runner.baseline(f"sqlite:///{path.as_posix()}")

    assert "upgrade()" in str(excinfo.value)


def test_applied_versions_reports_none_when_table_is_absent(tmp_path, monkeypatch):
    """Phân biệt "chưa có lịch sử" với "có lịch sử nhưng rỗng"."""
    _fresh_database(tmp_path, monkeypatch, "empty.sqlite3")
    runner = importlib.import_module("migrations.runner")
    path = tmp_path / "empty.sqlite3"
    sqlite3.connect(path).close()

    assert runner.applied_versions(f"sqlite:///{path.as_posix()}") is None
