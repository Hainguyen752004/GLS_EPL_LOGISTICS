import sqlite3

from migrations import v003_tms_core_planning


def test_v003_is_required_head_and_creates_tms_core_tables(tmp_path):
    assert v003_tms_core_planning.VERSION == "003_tms_core_planning"
    connection = sqlite3.connect(tmp_path / "v003.db")
    connection.execute("CREATE TABLE customers (id TEXT PRIMARY KEY)")
    connection.execute("CREATE TABLE locations (id TEXT PRIMARY KEY)")
    v003_tms_core_planning.upgrade_sqlite(connection)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"transport_demands", "freight_units", "freight_orders", "freight_order_units"} <= tables
    connection.close()


def test_v003_postgres_sql_has_capacity_and_provenance_constraints():
    sql = "\n".join(v003_tms_core_planning.statements("postgresql"))
    assert "demand_id TEXT NOT NULL UNIQUE" in sql
    assert "freight_unit_id TEXT NOT NULL UNIQUE" in sql
    assert "CHECK (max_weight_kg >= 0" in sql
