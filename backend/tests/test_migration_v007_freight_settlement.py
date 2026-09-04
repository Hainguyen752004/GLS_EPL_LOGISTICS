import sqlite3
import subprocess
import sys

import pytest

from migrations.runner import required_migration_head, rollback, upgrade


def _legacy_base(path):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
    """)
    connection.close()


def test_v007_is_head_and_creates_finance_schema(tmp_path):
    path = tmp_path / "v007.db"
    _legacy_base(path)

    assert upgrade(str(path))[-1] == "028_shipping_spec"
    assert required_migration_head() == "028_shipping_spec"

    with sqlite3.connect(path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {
            "currency_definitions", "currency_rate_history", "tax_codes", "finance_control_config",
            "freight_actual_costs", "freight_charge_items", "freight_cost_documents",
            "ap_invoices", "ap_invoice_lines", "freight_settlements", "settlement_payments",
        } <= tables
        assert "document_https_hosts" in {row[1] for row in connection.execute('PRAGMA table_info("finance_control_config")')}
        assert "is_internal" in {row[1] for row in connection.execute('PRAGMA table_info("carriers")')}
        assert "reversed_by_cost_id" in {row[1] for row in connection.execute('PRAGMA table_info("freight_actual_costs")')}
        assert "reversed_by_ap_id" in {row[1] for row in connection.execute('PRAGMA table_info("ap_invoices")')}
        assert connection.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone() == ("028_shipping_spec",)


def test_v007_backfills_scoped_idempotency_and_multisource_journals(tmp_path):
    path = tmp_path / "backfill.db"
    _legacy_base(path)
    upgrade(str(path))
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO idempotency_records(actor,method,path,idempotency_key,operation,request_hash,response_json) "
            "VALUES ('legacy','LEGACY','POST:/legacy','legacy-key','POST:/legacy','hash','{\"id\":\"old\"}')"
        )
        connection.execute("INSERT INTO journal_batches(id, invoice_id, status) VALUES ('JB-AR-1','INV-1','posted')")
        connection.execute(
            "INSERT INTO journal_lines(batch_id, account_code, debit, credit, currency_code, exchange_rate_snapshot) "
            "VALUES ('JB-AR-1','131',100,0,'VND',1)"
        )
        connection.commit()
        connection.execute("DELETE FROM schema_migrations WHERE version='007_tms_freight_settlement'")
        from migrations import v007_tms_freight_settlement
        v007_tms_freight_settlement.upgrade_sqlite(connection)

        idempotency_columns = {row[1] for row in connection.execute('PRAGMA table_info("idempotency_records")')}
        assert {"id", "actor", "method", "path", "idempotency_key", "request_hash", "response_json", "status"} <= idempotency_columns
        assert connection.execute(
            "SELECT actor,method,path,idempotency_key,response_json FROM idempotency_records WHERE idempotency_key='legacy-key'"
        ).fetchone() == ("legacy", "LEGACY", "POST:/legacy", "legacy-key", '{"id":"old"}')

        assert connection.execute(
            "SELECT invoice_id,source_type,source_id FROM journal_batches WHERE id='JB-AR-1'"
        ).fetchone() == ("INV-1", "ar_invoice", "INV-1")
        assert connection.execute(
            "SELECT transaction_amount,transaction_currency,exchange_rate,functional_debit,functional_credit FROM journal_lines WHERE batch_id='JB-AR-1'"
        ).fetchone() == (100, "VND", 1, 100, 0)


def test_v007_refuses_destructive_rollback_with_finance_data(tmp_path):
    path = tmp_path / "rollback-refuse.db"
    _legacy_base(path)
    upgrade(str(path))
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO currency_definitions(code,minor_units) VALUES ('VND',0)")
        connection.commit()
    with pytest.raises(RuntimeError, match="restore-from"):
        rollback(str(path))


def test_v007_postgresql_dry_run_is_offline_and_contains_core_ddl():
    result = subprocess.run(
        [sys.executable, "-m", "migrations.runner", "upgrade", "--database-url", "postgresql://not-connected/epl", "--dry-run"],
        cwd="backend/app",
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    assert "007_tms_freight_settlement" not in result.stderr
    assert "CREATE TABLE IF NOT EXISTS freight_actual_costs" in result.stdout
    assert "ALTER TABLE journal_batches" in result.stdout
    assert "uq_idempotency_scope" in result.stdout


def test_v007_sqlite_validation_rejects_missing_idempotency_scope_unique(tmp_path):
    path = tmp_path / "bad-idempotency.db"
    _legacy_base(path)
    upgrade(str(path))
    from migrations import v007_tms_freight_settlement

    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE idempotency_records RENAME TO idempotency_records_good")
        connection.execute("""CREATE TABLE idempotency_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            operation TEXT NOT NULL DEFAULT '',
            request_hash TEXT NOT NULL,
            response_json TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")

        with pytest.raises(RuntimeError, match="idempotency_records schema mismatch"):
            v007_tms_freight_settlement.validate_sqlite(connection)


def test_v007_sqlite_validation_rejects_missing_payment_reversal_unique_and_positive_check(tmp_path):
    path = tmp_path / "bad-payment.db"
    _legacy_base(path)
    upgrade(str(path))
    from migrations import v007_tms_freight_settlement

    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE settlement_payments RENAME TO settlement_payments_good")
        connection.execute("""CREATE TABLE settlement_payments (
            id TEXT PRIMARY KEY,
            settlement_id TEXT NOT NULL REFERENCES freight_settlements(id),
            amount NUMERIC(24,6) NOT NULL,
            currency_code TEXT NOT NULL REFERENCES currency_definitions(code),
            functional_currency TEXT NOT NULL REFERENCES currency_definitions(code),
            exchange_rate_snapshot NUMERIC(18,8) NOT NULL,
            exchange_rate_date DATE NOT NULL,
            exchange_rate_source TEXT NOT NULL,
            functional_amount NUMERIC(24,6) NOT NULL,
            posting_date DATE NOT NULL,
            payment_method TEXT NOT NULL,
            reference_no TEXT,
            status TEXT NOT NULL DEFAULT 'posted',
            posting_reference TEXT,
            reversal_of_payment_id TEXT REFERENCES settlement_payments(id),
            reversed_by_payment_id TEXT REFERENCES settlement_payments(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL
        )""")

        with pytest.raises(RuntimeError, match="settlement_payments schema mismatch"):
            v007_tms_freight_settlement.validate_sqlite(connection)


def test_v007_postgresql_validation_rejects_missing_finance_indexes_and_checks():
    from migrations import v007_tms_freight_settlement

    class Result:
        def __init__(self, rows=()):
            self.rows = rows
        def __iter__(self):
            return iter(self.rows)

    class Connection:
        def execute(self, statement):
            sql = str(statement)
            if "information_schema.columns" in sql:
                return Result([(table, column) for table, columns in v007_tms_freight_settlement.REQUIRED_COLUMNS.items()
                               for column in columns])
            if "information_schema.table_constraints" in sql:
                return Result([])
            if "pg_indexes" in sql:
                return Result([])
            return Result([])

    with pytest.raises(RuntimeError, match="idempotency_records schema mismatch"):
        v007_tms_freight_settlement.validate_postgresql(Connection())

