VERSION = "015_trip_stop_recipient"

from sqlalchemy import text


ADDITIONS = {
    "stop_name": "TEXT",
    "receiver_name": "TEXT",
    "receiver_phone": "TEXT",
    "delivery_note": "TEXT",
}


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "ALTER TABLE transport_trip_legs DROP COLUMN IF EXISTS delivery_note",
            "ALTER TABLE transport_trip_legs DROP COLUMN IF EXISTS receiver_phone",
            "ALTER TABLE transport_trip_legs DROP COLUMN IF EXISTS receiver_name",
            "ALTER TABLE transport_trip_legs DROP COLUMN IF EXISTS stop_name",
        ]
    return [
        f"ALTER TABLE transport_trip_legs ADD COLUMN IF NOT EXISTS {name} {definition}"
        for name, definition in ADDITIONS.items()
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
    if not _table_exists(connection, "transport_trip_legs"):
        return
    columns = _columns(connection, "transport_trip_legs")
    for name, definition in ADDITIONS.items():
        if name not in columns:
            connection.execute(
                f'ALTER TABLE transport_trip_legs ADD COLUMN "{name}" {definition}'
            )
    validate_sqlite(connection)


def rollback_sqlite(_connection):
    return None


def validate_sqlite(connection):
    if not _table_exists(connection, "transport_trip_legs"):
        return
    missing = set(ADDITIONS) - _columns(connection, "transport_trip_legs")
    if missing:
        raise RuntimeError(f"transport_trip_legs missing stop recipient columns: {sorted(missing)}")


def validate_postgresql(connection):
    rows = connection.execute(text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'transport_trip_legs'
          AND column_name IN ('stop_name','receiver_name','receiver_phone','delivery_note')
        """
    ))
    found = {row[0] for row in rows}
    required = set(ADDITIONS)
    if found != required:
        raise RuntimeError(f"transport_trip_legs stop recipient schema mismatch: {sorted(found)}")
