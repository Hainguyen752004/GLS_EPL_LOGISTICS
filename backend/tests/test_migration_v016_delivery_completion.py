import sqlite3

import pytest

from migrations.runner import MIGRATIONS, dry_run, required_migration_head, upgrade


VERSION = "016_delivery_completion_closeout"
HEAD_VERSION = "026_sales_order_lines"


def _prepare_pre_v016(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE delivery_orders (id TEXT PRIMARY KEY);
            CREATE TABLE currency_definitions (code TEXT PRIMARY KEY);
            CREATE TABLE delivery_pod_records (id INTEGER PRIMARY KEY AUTOINCREMENT);
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO currency_definitions(code) VALUES ('VND');
            INSERT INTO delivery_orders(id) VALUES ('DO-1');
            INSERT INTO delivery_pod_records DEFAULT VALUES;
            INSERT INTO delivery_pod_records DEFAULT VALUES;
            """
        )
        connection.executemany(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            [(migration.VERSION,) for migration in MIGRATIONS if migration.VERSION < VERSION],
        )


def _columns(connection, table):
    return {row[1]: row[2] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def test_v016_creates_closeout_schema_constraints_and_cascades(tmp_path):
    path = tmp_path / "v016.db"
    _prepare_pre_v016(path)

    assert required_migration_head() == HEAD_VERSION
    assert upgrade(str(path)) == [VERSION, "017_driver_shift_turnaround", "018_dispatch_crew", "019_driver_availability", "020_epl_expense_vouchers", "021_vehicle_maintenance", "022_vehicle_type_capacity", "023_parking_list", "024_money_numeric", "025_vehicle_depot", HEAD_VERSION]
    assert upgrade(str(path)) == []

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {
            "delivery_order_closeouts",
            "delivery_order_charge_adjustments",
            "delivery_pod_documents",
        } <= tables
        assert {"delivery_result", "cargo_condition"} <= set(_columns(connection, "delivery_pod_records"))
        assert _columns(connection, "delivery_pod_documents")["content"] == "BLOB"

        connection.execute(
            """INSERT INTO delivery_order_closeouts(
                id, do_id, base_selling_price_snapshot, base_price_source,
                surcharge_total, final_selling_price, currency_code,
                completed_at, completed_by
            ) VALUES ('CLOSE-1','DO-1',100,'sales_order',20,120,'VND',CURRENT_TIMESTAMP,'tester')"""
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO delivery_order_closeouts(
                    id, do_id, base_selling_price_snapshot, base_price_source,
                    surcharge_total, final_selling_price, currency_code,
                    completed_at, completed_by
                ) VALUES ('CLOSE-2','DO-1',100,'sales_order',0,100,'VND',CURRENT_TIMESTAMP,'tester')"""
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO delivery_order_charge_adjustments(
                    id, closeout_id, line_no, name, original_amount, actual_amount,
                    increase_amount, created_by
                ) VALUES ('ADJ-BAD','CLOSE-1',1,'Waiting',10,9,0,'tester')"""
            )
        connection.execute(
            """INSERT INTO delivery_order_charge_adjustments(
                id, closeout_id, line_no, name, original_amount, actual_amount,
                increase_amount, created_by
            ) VALUES ('ADJ-1','CLOSE-1',1,'Waiting',10,15,5,'tester')"""
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO delivery_order_charge_adjustments(
                    id, closeout_id, line_no, name, original_amount, actual_amount,
                    increase_amount, created_by
                ) VALUES ('ADJ-2','CLOSE-1',1,'Other',0,0,0,'tester')"""
            )

        connection.execute(
            """INSERT INTO delivery_pod_documents(
                id, pod_record_id, file_name, mime_type, file_size, checksum, content, created_by
            ) VALUES ('DOC-1',1,'pod.jpg','image/jpeg',3,'sha256:a',X'010203','tester')"""
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO delivery_pod_documents(
                    id, pod_record_id, file_name, mime_type, file_size, checksum, content, created_by
                ) VALUES ('DOC-2',1,'duplicate.jpg','image/jpeg',3,'sha256:a',X'010203','tester')"""
            )
        connection.execute(
            """INSERT INTO delivery_pod_documents(
                id, pod_record_id, file_name, mime_type, file_size, checksum, content, created_by
            ) VALUES ('DOC-2',2,'other.jpg','image/jpeg',0,'sha256:a',X'','tester')"""
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO delivery_pod_documents(
                    id, pod_record_id, file_name, mime_type, file_size, checksum, content, created_by
                ) VALUES ('DOC-LARGE',2,'large.bin','application/octet-stream',10485761,'sha256:b',X'','tester')"""
            )

        connection.execute("DELETE FROM delivery_pod_records WHERE id=1")
        connection.execute("DELETE FROM delivery_order_closeouts WHERE id='CLOSE-1'")
        assert connection.execute("SELECT COUNT(*) FROM delivery_pod_documents WHERE pod_record_id=1").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM delivery_order_charge_adjustments WHERE closeout_id='CLOSE-1'").fetchone() == (0,)


def test_v016_postgresql_dry_run_uses_bytea_and_named_constraints():
    sql = dry_run("postgresql://user:pass@localhost/epl")

    assert "CREATE TABLE IF NOT EXISTS delivery_order_closeouts" in sql
    assert "CREATE TABLE IF NOT EXISTS delivery_order_charge_adjustments" in sql
    assert "CREATE TABLE IF NOT EXISTS delivery_pod_documents" in sql
    assert "content BYTEA" in sql
    assert "uq_delivery_order_closeouts_do" in sql
    assert "uq_delivery_charge_adjustment_line" in sql
    assert "uq_delivery_pod_document_checksum" in sql
    assert "ADD COLUMN IF NOT EXISTS delivery_result" in sql
    assert "ADD COLUMN IF NOT EXISTS cargo_condition" in sql
