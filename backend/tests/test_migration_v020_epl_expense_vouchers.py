import sqlite3

import pytest

from migrations import v020_epl_expense_vouchers
from migrations.runner import required_migration_head


def _base(connection):
    connection.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE transport_trips (id TEXT PRIMARY KEY);
        CREATE TABLE freight_actual_costs (id TEXT PRIMARY KEY);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY);
        INSERT INTO transport_trips(id) VALUES ('TRIP-1'), ('TRIP-2');
        INSERT INTO freight_actual_costs(id) VALUES ('COST-1'), ('COST-2');
        INSERT INTO delivery_orders(id) VALUES ('DO-1');
        """
    )


def test_v020_creates_real_expense_voucher_constraints(tmp_path):
    connection = sqlite3.connect(tmp_path / "v020.db")
    _base(connection)
    v020_epl_expense_vouchers.upgrade_sqlite(connection)

    connection.execute(
        """INSERT INTO epl_expense_vouchers(
            id, trip_id, cost_id, do_id, voucher_no, voucher_date,
            payment_method, created_by, updated_by
        ) VALUES ('V-1','TRIP-1','COST-1','DO-1','PC-001','2026-08-24','cash','tester','tester')"""
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """INSERT INTO epl_expense_vouchers(
                id, trip_id, cost_id, voucher_no, voucher_date,
                payment_method, created_by, updated_by
            ) VALUES ('V-2','TRIP-1','COST-2','PC-002','2026-08-24','cash','tester','tester')"""
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """INSERT INTO epl_expense_vouchers(
                id, trip_id, cost_id, voucher_no, voucher_date,
                payment_method, created_by, updated_by
            ) VALUES ('V-3','TRIP-2','COST-2','PC-003','2026-08-24','invalid','tester','tester')"""
        )
    connection.close()


def test_v020_is_current_head_and_rolls_back(tmp_path):
    connection = sqlite3.connect(tmp_path / "rollback.db")
    _base(connection)
    v020_epl_expense_vouchers.upgrade_sqlite(connection)
    assert required_migration_head() == "029_sales_order_cargo_type"
    v020_epl_expense_vouchers.rollback_sqlite(connection)
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='epl_expense_vouchers'"
    ).fetchone() is None
    connection.close()
