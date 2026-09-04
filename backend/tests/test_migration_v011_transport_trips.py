import sqlite3
import subprocess
import sys

from migrations.runner import required_migration_head, upgrade


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


def test_v011_is_head_and_creates_trip_schema_with_lineage(tmp_path):
    path = tmp_path / "v011.db"
    _legacy_base(path)

    assert upgrade(str(path))[-1] == "028_shipping_spec"
    assert required_migration_head() == "028_shipping_spec"

    with sqlite3.connect(path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"transport_trips", "trip_delivery_orders", "transport_trip_legs"} <= tables
        for table in ("resource_assignments", "transport_events", "delivery_pod_records", "freight_actual_costs"):
            columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
            assert {"trip_id", "leg_id"} <= columns
        indexes = {row[1] for row in connection.execute("PRAGMA index_list('freight_actual_costs')")}
        assert {"uq_legacy_active_cost_freight_order", "uq_active_cost_trip"} <= indexes


def test_v011_postgresql_dry_run_contains_trip_ddl_offline():
    result = subprocess.run(
        [sys.executable, "-m", "migrations.runner", "upgrade", "--database-url", "postgresql://not-connected/epl", "--dry-run"],
        cwd="backend/app",
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    assert "CREATE TABLE IF NOT EXISTS transport_trips" in result.stdout
    assert "CREATE TABLE IF NOT EXISTS trip_delivery_orders" in result.stdout
    assert "CREATE TABLE IF NOT EXISTS transport_trip_legs" in result.stdout
    assert "uq_active_cost_trip" in result.stdout

