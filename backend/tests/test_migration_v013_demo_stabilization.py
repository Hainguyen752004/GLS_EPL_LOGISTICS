import sqlite3

import pytest
from sqlalchemy import DateTime, Numeric, create_engine

from migrations.runner import MIGRATIONS, required_migration_head, upgrade
from models import ARInvoice, Base, DeliveryOrder, DeliveryPODRecord, SalesOrder


def _create_schema(database):
    engine = create_engine(f"sqlite:///{database}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.executemany(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            [(migration.VERSION,) for migration in MIGRATIONS if migration.VERSION < "013_demo_stabilization"],
        )
        connection.execute("DROP INDEX IF EXISTS uq_delivery_pod_idempotency")
        connection.execute("ALTER TABLE delivery_pod_records DROP COLUMN idempotency_key")
        connection.commit()


def test_v013_is_current_and_upgrade_is_idempotent(tmp_path):
    database = tmp_path / "v013.db"
    _create_schema(database)

    assert required_migration_head() == "024_money_numeric"
    assert upgrade(str(database)) == ["013_demo_stabilization", "014_trip_cost_rows", "015_trip_stop_recipient", "016_delivery_completion_closeout", "017_driver_shift_turnaround", "018_dispatch_crew", "019_driver_availability", "020_epl_expense_vouchers", "021_vehicle_maintenance", "022_vehicle_type_capacity", "023_parking_list", "024_money_numeric"]
    assert upgrade(str(database)) == []

    with sqlite3.connect(database) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations WHERE version IN ('013_demo_stabilization','014_trip_cost_rows','015_trip_stop_recipient','016_delivery_completion_closeout','017_driver_shift_turnaround') ORDER BY version"
        ).fetchall()
        assert versions == [("013_demo_stabilization",), ("014_trip_cost_rows",), ("015_trip_stop_recipient",), ("016_delivery_completion_closeout",), ("017_driver_shift_turnaround",)]


def test_v013_rejects_legacy_delivery_approval_status(tmp_path):
    database = tmp_path / "do-status.db"
    _create_schema(database)
    upgrade(str(database))

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError, match="canonical_status"):
            connection.execute(
                "INSERT INTO delivery_orders(id, canonical_status, status) VALUES ('DO-BAD', 'approved', 'Đã duyệt')"
            )


def test_v013_models_use_timezone_money_and_pod_idempotency():
    operational_columns = (
        DeliveryOrder.pickup_window_start,
        DeliveryOrder.pickup_window_end,
        DeliveryOrder.delivery_window_start,
        DeliveryOrder.delivery_window_end,
        DeliveryOrder.pickup_date,
        DeliveryOrder.delivery_date,
        DeliveryOrder.planned_departure_at,
        DeliveryOrder.planned_arrival_at,
        DeliveryOrder.planned_return_at,
        DeliveryPODRecord.delivery_time,
    )
    assert all(isinstance(column.type, DateTime) and column.type.timezone for column in operational_columns)
    assert isinstance(SalesOrder.total_amount.type, Numeric)
    assert isinstance(ARInvoice.amount.type, Numeric)
    assert isinstance(ARInvoice.vat_amount.type, Numeric)
    assert isinstance(ARInvoice.total.type, Numeric)
    assert DeliveryPODRecord.idempotency_key.property.columns[0].nullable is True


def test_v013_sqlite_has_pod_idempotency_unique_index(tmp_path):
    database = tmp_path / "pod-idempotency.db"
    _create_schema(database)
    upgrade(str(database))

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info("delivery_pod_records")')}
        indexes = {row[1] for row in connection.execute('PRAGMA index_list("delivery_pod_records")')}

    assert "idempotency_key" in columns
    assert "uq_delivery_pod_idempotency" in indexes
