import sqlite3

from sqlalchemy import create_engine

from migrations.runner import MIGRATIONS, required_migration_head, upgrade
from models import Base


def test_v014_adds_delivery_cost_row_columns_and_is_idempotent(tmp_path):
    database = tmp_path / "v014.db"
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
            [(migration.VERSION,) for migration in MIGRATIONS if migration.VERSION < "014_trip_cost_rows"],
        )
        for column in ("note", "increase_amount", "actual_amount", "original_amount"):
            connection.execute(f'ALTER TABLE freight_charge_items DROP COLUMN "{column}"')
        connection.commit()

    assert required_migration_head() == "022_vehicle_type_capacity"
    assert upgrade(str(database)) == ["014_trip_cost_rows", "015_trip_stop_recipient", "016_delivery_completion_closeout", "017_driver_shift_turnaround", "018_dispatch_crew", "019_driver_availability", "020_epl_expense_vouchers", "021_vehicle_maintenance", "022_vehicle_type_capacity"]
    assert upgrade(str(database)) == []

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info("freight_charge_items")')}
    assert {"original_amount", "actual_amount", "increase_amount", "note"} <= columns
