VERSION = "008_driver_vehicle_images"

from sqlalchemy import text


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "ALTER TABLE drivers DROP COLUMN IF EXISTS photo_url",
            "ALTER TABLE vehicles DROP COLUMN IF EXISTS image_url",
        ]
    return [
        "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS photo_url TEXT",
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS image_url TEXT",
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
    if _table_exists(connection, "drivers") and "photo_url" not in _columns(connection, "drivers"):
        connection.execute('ALTER TABLE drivers ADD COLUMN photo_url TEXT')
    if _table_exists(connection, "vehicles") and "image_url" not in _columns(connection, "vehicles"):
        connection.execute('ALTER TABLE vehicles ADD COLUMN image_url TEXT')
    validate_sqlite(connection)


def rollback_sqlite(connection):
    if _table_exists(connection, "drivers") and "photo_url" in _columns(connection, "drivers"):
        connection.execute('ALTER TABLE drivers DROP COLUMN photo_url')
    if _table_exists(connection, "vehicles") and "image_url" in _columns(connection, "vehicles"):
        connection.execute('ALTER TABLE vehicles DROP COLUMN image_url')


def validate_sqlite(connection):
    if _table_exists(connection, "drivers") and "photo_url" not in _columns(connection, "drivers"):
        raise RuntimeError("drivers photo_url schema mismatch")
    if _table_exists(connection, "vehicles") and "image_url" not in _columns(connection, "vehicles"):
        raise RuntimeError("vehicles image_url schema mismatch")


def validate_postgresql(connection):
    result = connection.execute(text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_name IN ('drivers','vehicles')
          AND column_name IN ('photo_url','image_url')
        """
    ))
    rows = result.fetchall() if hasattr(result, "fetchall") else list(result)
    found = {(row[0], row[1]) for row in rows}
    if ("drivers", "photo_url") not in found:
        raise RuntimeError("drivers photo_url schema mismatch")
    if ("vehicles", "image_url") not in found:
        raise RuntimeError("vehicles image_url schema mismatch")
