VERSION = "019_driver_availability"

from sqlalchemy import text


TABLE = "driver_shift_assignments"
COLUMN = "availability_kind"


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            f"ALTER TABLE {TABLE} DROP COLUMN IF EXISTS {COLUMN}",
        ]
    return [
        f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {COLUMN} TEXT NOT NULL DEFAULT 'work'",
        f"ALTER TABLE {TABLE} ADD CONSTRAINT ck_driver_shift_availability_kind "
        f"CHECK ({COLUMN} IN ('work','leave','sick','off','unavailable'))",
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
    if _table_exists(connection, TABLE) and COLUMN not in _columns(connection, TABLE):
        connection.execute(
            f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} TEXT NOT NULL DEFAULT 'work'"
        )
    validate_sqlite(connection)


def rollback_sqlite(connection):
    if _table_exists(connection, TABLE) and COLUMN in _columns(connection, TABLE):
        connection.execute(f"ALTER TABLE {TABLE} DROP COLUMN {COLUMN}")


def validate_sqlite(connection):
    if _table_exists(connection, TABLE) and COLUMN not in _columns(connection, TABLE):
        raise RuntimeError(f"{TABLE}.{COLUMN} missing")


def validate_postgresql(connection):
    rows = connection.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'driver_shift_assignments'
          AND column_name = 'availability_kind'
    """))
    if not list(rows):
        raise RuntimeError(f"{TABLE}.{COLUMN} missing")
