VERSION = "012_vehicle_speed_profile"

from sqlalchemy import text


VEHICLE_SPEED_COLUMNS = {
    "min_speed_kmh": "REAL DEFAULT 35",
    "max_speed_kmh": "REAL DEFAULT 80",
}


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "ALTER TABLE vehicles DROP COLUMN IF EXISTS max_speed_kmh",
            "ALTER TABLE vehicles DROP COLUMN IF EXISTS min_speed_kmh",
        ]
    return [
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS min_speed_kmh DOUBLE PRECISION DEFAULT 35",
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS max_speed_kmh DOUBLE PRECISION DEFAULT 80",
    ]


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def upgrade_sqlite(connection):
    if _table_exists(connection, "vehicles"):
        existing = _columns(connection, "vehicles")
        for column, definition in VEHICLE_SPEED_COLUMNS.items():
            if column not in existing:
                connection.execute(f'ALTER TABLE vehicles ADD COLUMN {column} {definition}')
    validate_sqlite(connection)


def rollback_sqlite(connection):
    if not _table_exists(connection, "vehicles"):
        return
    existing = _columns(connection, "vehicles")
    for column in ("max_speed_kmh", "min_speed_kmh"):
        if column in existing:
            connection.execute(f'ALTER TABLE vehicles DROP COLUMN {column}')


def validate_sqlite(connection):
    if _table_exists(connection, "vehicles"):
        columns = _columns(connection, "vehicles")
        if not set(VEHICLE_SPEED_COLUMNS) <= columns:
            raise RuntimeError("vehicles speed profile schema mismatch")


def validate_postgresql(connection):
    result = connection.execute(text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_name = 'vehicles'
          AND column_name IN ('min_speed_kmh','max_speed_kmh')
        """
    ))
    rows = result.fetchall() if hasattr(result, "fetchall") else list(result)
    found = {(row[0], row[1]) for row in rows}
    if ("vehicles", "min_speed_kmh") not in found:
        raise RuntimeError("vehicles min_speed_kmh schema mismatch")
    if ("vehicles", "max_speed_kmh") not in found:
        raise RuntimeError("vehicles max_speed_kmh schema mismatch")
