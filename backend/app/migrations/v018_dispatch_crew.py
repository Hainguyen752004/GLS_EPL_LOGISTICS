VERSION = "018_dispatch_crew"

from sqlalchemy import text


COLUMNS = (
    ("transport_trips", "co_driver_id"),
    ("resource_assignments", "co_driver_id"),
)


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP INDEX IF EXISTS ix_resource_assignment_co_driver_period",
            "ALTER TABLE resource_assignments DROP COLUMN IF EXISTS co_driver_id",
            "ALTER TABLE transport_trips DROP COLUMN IF EXISTS co_driver_id",
        ]
    return [
        "ALTER TABLE transport_trips ADD COLUMN IF NOT EXISTS co_driver_id TEXT REFERENCES drivers(id)",
        "ALTER TABLE resource_assignments ADD COLUMN IF NOT EXISTS co_driver_id TEXT REFERENCES drivers(id)",
        "CREATE INDEX IF NOT EXISTS ix_resource_assignment_co_driver_period ON resource_assignments(co_driver_id, assignment_start, assignment_end)",
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
    for table, column in COLUMNS:
        if _table_exists(connection, table) and column not in _columns(connection, table):
            connection.execute(
                f'ALTER TABLE "{table}" ADD COLUMN {column} TEXT REFERENCES drivers(id)'
            )
    if _table_exists(connection, "resource_assignments"):
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_resource_assignment_co_driver_period "
            "ON resource_assignments(co_driver_id, assignment_start, assignment_end)"
        )
    validate_sqlite(connection)


def rollback_sqlite(connection):
    connection.execute("DROP INDEX IF EXISTS ix_resource_assignment_co_driver_period")
    for table, column in reversed(COLUMNS):
        if column in _columns(connection, table):
            connection.execute(f'ALTER TABLE "{table}" DROP COLUMN {column}')


def validate_sqlite(connection):
    for table, column in COLUMNS:
        if _table_exists(connection, table) and column not in _columns(connection, table):
            raise RuntimeError(f"{table}.{column} missing")


def validate_postgresql(connection):
    rows = connection.execute(text("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_name IN ('transport_trips', 'resource_assignments')
          AND column_name = 'co_driver_id'
    """))
    found = {(row[0], row[1]) for row in rows}
    for table, column in COLUMNS:
        if (table, column) not in found:
            raise RuntimeError(f"{table}.{column} missing")
