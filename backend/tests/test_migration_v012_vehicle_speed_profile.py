import sqlite3

from migrations.runner import dry_run, required_migration_head, upgrade


def _legacy_base(path):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
        CREATE TABLE vehicles (
            id TEXT PRIMARY KEY,
            brand TEXT,
            type TEXT,
            weight_capacity REAL,
            fuel_norm REAL
        );
    """)
    connection.close()


def test_v012_adds_vehicle_speed_profile_columns_to_sqlite(tmp_path):
    db_path = tmp_path / "epl_v012.db"
    _legacy_base(db_path)
    upgrade(str(db_path))

    connection = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}
        assert "min_speed_kmh" in columns
        assert "max_speed_kmh" in columns
    finally:
        connection.close()

    assert required_migration_head() == "025_vehicle_depot"


def test_v012_postgresql_dry_run_contains_vehicle_speed_columns():
    sql = dry_run("postgresql://user:pass@localhost/epl_logistics")

    assert "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS min_speed_kmh" in sql
    assert "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS max_speed_kmh" in sql

