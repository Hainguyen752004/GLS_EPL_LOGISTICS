VERSION = "009_delivery_pod_eta"

from sqlalchemy import text


DO_COLUMNS = {
    "planned_departure_at": "TEXT",
    "planned_arrival_at": "TEXT",
    "planned_return_at": "TEXT",
    "avg_speed_kmh": "DOUBLE PRECISION",
    "max_speed_kmh": "DOUBLE PRECISION",
    "return_speed_kmh": "DOUBLE PRECISION",
    "load_minutes": "INTEGER DEFAULT 0",
    "unload_minutes": "INTEGER DEFAULT 0",
    "return_distance_km": "DOUBLE PRECISION",
}

TRACKING_COLUMNS = {
    "planned_return_at": "TEXT",
}


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS delivery_pod_records",
            *[f"ALTER TABLE vehicle_tracking DROP COLUMN IF EXISTS {column}" for column in TRACKING_COLUMNS],
            *[f"ALTER TABLE delivery_orders DROP COLUMN IF EXISTS {column}" for column in DO_COLUMNS],
        ]
    add_do = [f"ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS {column} {definition}" for column, definition in DO_COLUMNS.items()]
    add_tracking = [f"ALTER TABLE vehicle_tracking ADD COLUMN IF NOT EXISTS {column} {definition}" for column, definition in TRACKING_COLUMNS.items()]
    return [
        *add_do,
        *add_tracking,
        """
        CREATE TABLE IF NOT EXISTS delivery_pod_records (
            id SERIAL PRIMARY KEY,
            do_id TEXT NOT NULL REFERENCES delivery_orders(id),
            vehicle_id TEXT NOT NULL REFERENCES vehicles(id),
            driver_id TEXT REFERENCES drivers(id),
            stop_no INTEGER NOT NULL DEFAULT 1,
            location_text TEXT,
            receiver_name TEXT,
            receiver_phone TEXT,
            delivery_time TEXT,
            photo_url TEXT,
            signature_url TEXT,
            note TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system',
            CONSTRAINT uq_delivery_pod_vehicle_stop UNIQUE (do_id, vehicle_id, stop_no),
            CONSTRAINT ck_delivery_pod_stop_positive CHECK (stop_no > 0)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_delivery_pod_records_do_id ON delivery_pod_records(do_id, stop_no)",
    ]


def _table_exists(connection, table):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _add_missing_columns(connection, table, columns):
    if not _table_exists(connection, table):
        return
    existing = _columns(connection, table)
    for column, definition in columns.items():
        if column not in existing:
            connection.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')


def upgrade_sqlite(connection):
    _add_missing_columns(connection, "delivery_orders", DO_COLUMNS)
    if not _table_exists(connection, "vehicle_tracking"):
        connection.execute(
            """
            CREATE TABLE vehicle_tracking (
                do_id TEXT PRIMARY KEY REFERENCES delivery_orders(id),
                vehicle_id TEXT REFERENCES vehicles(id),
                lat REAL,
                lng REAL,
                speed_kmh REAL DEFAULT 0,
                remaining_distance_km REAL DEFAULT 0,
                eta TEXT,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    _add_missing_columns(connection, "vehicle_tracking", TRACKING_COLUMNS)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_pod_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            do_id TEXT NOT NULL REFERENCES delivery_orders(id),
            vehicle_id TEXT NOT NULL REFERENCES vehicles(id),
            driver_id TEXT REFERENCES drivers(id),
            stop_no INTEGER NOT NULL DEFAULT 1,
            location_text TEXT,
            receiver_name TEXT,
            receiver_phone TEXT,
            delivery_time TEXT,
            photo_url TEXT,
            signature_url TEXT,
            note TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system',
            CONSTRAINT uq_delivery_pod_vehicle_stop UNIQUE (do_id, vehicle_id, stop_no),
            CONSTRAINT ck_delivery_pod_stop_positive CHECK (stop_no > 0)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS ix_delivery_pod_records_do_id ON delivery_pod_records(do_id, stop_no)")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    if _table_exists(connection, "delivery_pod_records"):
        connection.execute("DROP TABLE delivery_pod_records")


def validate_sqlite(connection):
    if not _table_exists(connection, "delivery_pod_records"):
        raise RuntimeError("delivery_pod_records table missing")
    if not set(DO_COLUMNS) <= _columns(connection, "delivery_orders"):
        raise RuntimeError("delivery_orders ETA schema mismatch")
    if not set(TRACKING_COLUMNS) <= _columns(connection, "vehicle_tracking"):
        raise RuntimeError("vehicle_tracking return ETA schema mismatch")
    required = {"id", "do_id", "vehicle_id", "driver_id", "stop_no", "delivery_time", "photo_url", "signature_url", "note"}
    if not required <= _columns(connection, "delivery_pod_records"):
        raise RuntimeError("delivery_pod_records schema mismatch")


def validate_postgresql(connection):
    result = connection.execute(text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_name IN ('delivery_orders','vehicle_tracking','delivery_pod_records')
        """
    ))
    rows = result.fetchall() if hasattr(result, "fetchall") else list(result)
    found = {(row[0], row[1]) for row in rows}
    for column in DO_COLUMNS:
        if ("delivery_orders", column) not in found:
            raise RuntimeError("delivery_orders ETA schema mismatch")
    for column in TRACKING_COLUMNS:
        if ("vehicle_tracking", column) not in found:
            raise RuntimeError("vehicle_tracking return ETA schema mismatch")
    for column in ("id", "do_id", "vehicle_id", "driver_id", "stop_no", "delivery_time", "photo_url", "signature_url", "note"):
        if ("delivery_pod_records", column) not in found:
            raise RuntimeError("delivery_pod_records schema mismatch")
