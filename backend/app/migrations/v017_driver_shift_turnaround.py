VERSION = "017_driver_shift_turnaround"

from sqlalchemy import text


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS driver_shift_assignments",
            "ALTER TABLE vehicle_types DROP COLUMN IF EXISTS avg_speed_kmh",
            "ALTER TABLE vehicles DROP COLUMN IF EXISTS avg_speed_kmh",
        ]
    timestamp_type = "TIMESTAMP" if dialect == "sqlite" else "TIMESTAMPTZ"
    return [
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS avg_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 45",
        "ALTER TABLE vehicle_types ADD COLUMN IF NOT EXISTS avg_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 45",
        f"""
        CREATE TABLE IF NOT EXISTS driver_shift_assignments (
            id TEXT PRIMARY KEY,
            driver_id TEXT NOT NULL REFERENCES drivers(id),
            vehicle_id TEXT REFERENCES vehicles(id),
            trip_id TEXT REFERENCES transport_trips(id),
            shift_type TEXT NOT NULL DEFAULT 'custom',
            shift_start {timestamp_type} NOT NULL,
            shift_end {timestamp_type} NOT NULL,
            work_location TEXT,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'planned',
            version INTEGER NOT NULL DEFAULT 1,
            created_at {timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at {timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_by TEXT NOT NULL DEFAULT 'system',
            CONSTRAINT ck_driver_shift_period CHECK (shift_end > shift_start),
            CONSTRAINT ck_driver_shift_type CHECK (shift_type IN ('morning','afternoon','night','office','custom')),
            CONSTRAINT ck_driver_shift_status CHECK (status IN ('planned','confirmed','cancelled'))
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_driver_shift_driver_period ON driver_shift_assignments(driver_id, shift_start, shift_end)",
        "CREATE INDEX IF NOT EXISTS ix_driver_shift_vehicle_period ON driver_shift_assignments(vehicle_id, shift_start, shift_end)",
    ]


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def upgrade_sqlite(connection):
    for table in ("vehicles", "vehicle_types"):
        if _table_exists(connection, table) and "avg_speed_kmh" not in _columns(connection, table):
            connection.execute(f'ALTER TABLE "{table}" ADD COLUMN avg_speed_kmh DOUBLE PRECISION NOT NULL DEFAULT 45')
    for sql in statements("sqlite")[2:]:
        connection.execute(sql)
    validate_sqlite(connection)


def rollback_sqlite(connection):
    if _table_exists(connection, "driver_shift_assignments"):
        connection.execute("DROP TABLE driver_shift_assignments")


def validate_sqlite(connection):
    if _table_exists(connection, "vehicles") and "avg_speed_kmh" not in _columns(connection, "vehicles"):
        raise RuntimeError("vehicles speed profile missing")
    if _table_exists(connection, "vehicle_types") and "avg_speed_kmh" not in _columns(connection, "vehicle_types"):
        raise RuntimeError("vehicle_types speed profile missing")
    required = {"id", "driver_id", "vehicle_id", "trip_id", "shift_type", "shift_start", "shift_end", "status", "version"}
    if not required <= _columns(connection, "driver_shift_assignments"):
        raise RuntimeError("driver_shift_assignments schema mismatch")


def validate_postgresql(connection):
    rows = connection.execute(text("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_name IN ('vehicles','vehicle_types','driver_shift_assignments')
    """))
    found = {(row[0], row[1]) for row in rows}
    if ("vehicles", "avg_speed_kmh") not in found or ("vehicle_types", "avg_speed_kmh") not in found:
        raise RuntimeError("vehicle speed profile missing")
    required = {"id", "driver_id", "vehicle_id", "trip_id", "shift_type", "shift_start", "shift_end", "status", "version"}
    if any(("driver_shift_assignments", column) not in found for column in required):
        raise RuntimeError("driver_shift_assignments schema mismatch")
