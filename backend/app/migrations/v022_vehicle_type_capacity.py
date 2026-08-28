VERSION = "022_vehicle_type_capacity"

from sqlalchemy import text


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "ALTER TABLE vehicle_types DROP COLUMN IF EXISTS pallet_capacity",
            "ALTER TABLE vehicle_types DROP COLUMN IF EXISTS volume_capacity_m3",
        ]
    return [
        "ALTER TABLE vehicle_types ADD COLUMN IF NOT EXISTS volume_capacity_m3 FLOAT NOT NULL DEFAULT 30",
        "ALTER TABLE vehicle_types ADD COLUMN IF NOT EXISTS pallet_capacity INTEGER NOT NULL DEFAULT 0",
    ]


def upgrade_sqlite(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicle_types")')}
    if not columns:
        return
    if "volume_capacity_m3" not in columns:
        connection.execute("ALTER TABLE vehicle_types ADD COLUMN volume_capacity_m3 FLOAT NOT NULL DEFAULT 30")
    if "pallet_capacity" not in columns:
        connection.execute("ALTER TABLE vehicle_types ADD COLUMN pallet_capacity INTEGER NOT NULL DEFAULT 0")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicle_types")')}
    if not columns:
        return
    if "pallet_capacity" in columns:
        connection.execute("ALTER TABLE vehicle_types DROP COLUMN pallet_capacity")
    if "volume_capacity_m3" in columns:
        connection.execute("ALTER TABLE vehicle_types DROP COLUMN volume_capacity_m3")


def validate_sqlite(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicle_types")')}
    if not columns:
        return
    if columns and not {"volume_capacity_m3", "pallet_capacity"} <= columns:
        raise RuntimeError("vehicle type capacity columns missing")


def validate_postgresql(connection):
    columns = {
        row[0] for row in connection.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'vehicle_types'
        """))
    }
    if columns and not {"volume_capacity_m3", "pallet_capacity"} <= columns:
        raise RuntimeError("vehicle type capacity columns missing")
