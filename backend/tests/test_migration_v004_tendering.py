import sqlite3

from migrations import v004_tms_tendering


def test_v004_creates_tender_tables(tmp_path):
    connection = sqlite3.connect(tmp_path / "v004.db")
    connection.execute("CREATE TABLE freight_orders (id TEXT PRIMARY KEY)")
    v004_tms_tendering.upgrade_sqlite(connection)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"carriers", "tenders", "tender_offers"} <= tables
    connection.close()


def test_v004_enforces_one_offer_per_carrier_and_positive_amount():
    sql = "\n".join(v004_tms_tendering.statements("postgresql"))
    assert "UNIQUE (tender_id, carrier_id)" in sql
    assert "CHECK (amount > 0)" in sql
