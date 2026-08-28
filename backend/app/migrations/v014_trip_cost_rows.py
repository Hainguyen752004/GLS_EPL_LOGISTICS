VERSION = "014_trip_cost_rows"

from sqlalchemy import text


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "ALTER TABLE freight_charge_items DROP COLUMN IF EXISTS note",
            "ALTER TABLE freight_charge_items DROP COLUMN IF EXISTS increase_amount",
            "ALTER TABLE freight_charge_items DROP COLUMN IF EXISTS actual_amount",
            "ALTER TABLE freight_charge_items DROP COLUMN IF EXISTS original_amount",
        ]
    return [
        "ALTER TABLE freight_charge_items ADD COLUMN IF NOT EXISTS original_amount NUMERIC(24,6) NOT NULL DEFAULT 0",
        "ALTER TABLE freight_charge_items ADD COLUMN IF NOT EXISTS actual_amount NUMERIC(24,6) NOT NULL DEFAULT 0",
        "ALTER TABLE freight_charge_items ADD COLUMN IF NOT EXISTS increase_amount NUMERIC(24,6) NOT NULL DEFAULT 0",
        "ALTER TABLE freight_charge_items ADD COLUMN IF NOT EXISTS note TEXT",
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
    if not _table_exists(connection, "freight_charge_items"):
        return
    columns = _columns(connection, "freight_charge_items")
    additions = {
        "original_amount": "NUMERIC(24,6) NOT NULL DEFAULT 0",
        "actual_amount": "NUMERIC(24,6) NOT NULL DEFAULT 0",
        "increase_amount": "NUMERIC(24,6) NOT NULL DEFAULT 0",
        "note": "TEXT",
    }
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(
                f'ALTER TABLE freight_charge_items ADD COLUMN "{name}" {definition}'
            )
    validate_sqlite(connection)


def rollback_sqlite(_connection):
    return None


def validate_sqlite(connection):
    if not _table_exists(connection, "freight_charge_items"):
        return
    required = {"original_amount", "actual_amount", "increase_amount", "note"}
    missing = required - _columns(connection, "freight_charge_items")
    if missing:
        raise RuntimeError(f"freight_charge_items missing columns: {sorted(missing)}")


def validate_postgresql(connection):
    rows = connection.execute(text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'freight_charge_items'
          AND column_name IN ('original_amount','actual_amount','increase_amount','note')
        """
    ))
    found = {row[0] for row in rows}
    required = {"original_amount", "actual_amount", "increase_amount", "note"}
    if found != required:
        raise RuntimeError(f"freight_charge_items cost row schema mismatch: {sorted(found)}")
