VERSION = "023_parking_list"

from sqlalchemy import text


CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS parking_lists (
        id VARCHAR(128) PRIMARY KEY,
        do_id VARCHAR NOT NULL REFERENCES delivery_orders(id),
        so_id VARCHAR REFERENCES sales_orders(id),
        trip_id VARCHAR(128) REFERENCES transport_trips(id),
        version INTEGER NOT NULL DEFAULT 1,
        customer_id VARCHAR REFERENCES customers(id),
        store_id VARCHAR(128),
        store_name VARCHAR(255),
        route_code VARCHAR(128),
        route_name VARCHAR(500),
        wave VARCHAR(64),
        gate VARCHAR(64),
        box_count INTEGER NOT NULL DEFAULT 1,
        total_pieces INTEGER NOT NULL DEFAULT 0,
        total_weight_kg FLOAT NOT NULL DEFAULT 0,
        total_cube_m3 FLOAT NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'ready',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(128) NOT NULL DEFAULT 'system',
        updated_by VARCHAR(128) NOT NULL DEFAULT 'system',
        CONSTRAINT uq_parking_list_do_version UNIQUE (do_id, version),
        CONSTRAINT ck_parking_list_status CHECK (
            status IN ('draft','ready','parked','gate_in','loaded','dispatched','delivered','cancelled')
        )
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_parking_lists_do_id ON parking_lists(do_id)",
    "CREATE INDEX IF NOT EXISTS ix_parking_list_status_created ON parking_lists(status, created_at)",
    """
    CREATE TABLE IF NOT EXISTS parking_list_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parking_list_id VARCHAR(128) NOT NULL REFERENCES parking_lists(id) ON DELETE CASCADE,
        source_detail_id INTEGER,
        barcode VARCHAR(128),
        item_id_laos VARCHAR(128),
        item_id_thai VARCHAR(128),
        sku VARCHAR(128),
        description VARCHAR(500),
        case_qty INTEGER NOT NULL DEFAULT 0,
        piece_qty INTEGER NOT NULL DEFAULT 0,
        uom VARCHAR(32),
        weight_kg FLOAT NOT NULL DEFAULT 0,
        cube_m3 FLOAT NOT NULL DEFAULT 0,
        note TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_parking_list_items_list_id ON parking_list_items(parking_list_id)",
    """
    CREATE TABLE IF NOT EXISTS parking_labels (
        id VARCHAR(128) PRIMARY KEY,
        parking_list_id VARCHAR(128) NOT NULL REFERENCES parking_lists(id) ON DELETE CASCADE,
        package_no INTEGER NOT NULL,
        package_total INTEGER NOT NULL,
        qr_token VARCHAR(128) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'ready',
        printed_at TIMESTAMP,
        reprint_count INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT uq_parking_label_package UNIQUE (parking_list_id, package_no),
        CONSTRAINT uq_parking_label_qr_token UNIQUE (qr_token)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_parking_labels_list_id ON parking_labels(parking_list_id)",
    """
    CREATE TABLE IF NOT EXISTS parking_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parking_list_id VARCHAR(128) NOT NULL REFERENCES parking_lists(id) ON DELETE CASCADE,
        event_type VARCHAR(32) NOT NULL,
        occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actor VARCHAR(128) NOT NULL DEFAULT 'system',
        note TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_parking_events_list_id ON parking_events(parking_list_id)",
]


def _postgres_sql(sql):
    return sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS parking_events",
            "DROP TABLE IF EXISTS parking_labels",
            "DROP TABLE IF EXISTS parking_list_items",
            "DROP TABLE IF EXISTS parking_lists",
        ]
    if dialect == "postgresql":
        return [_postgres_sql(sql) for sql in CREATE_TABLES]
    return CREATE_TABLES


def upgrade_sqlite(connection):
    for sql in CREATE_TABLES:
        connection.execute(sql)
    validate_sqlite(connection)


def rollback_sqlite(connection):
    for sql in statements("sqlite", "rollback"):
        connection.execute(sql)


def validate_sqlite(connection):
    expected = {"parking_lists", "parking_list_items", "parking_labels", "parking_events"}
    actual = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'parking%'"
        )
    }
    if not expected <= actual:
        raise RuntimeError("parking list tables missing")


def validate_postgresql(connection):
    expected = {"parking_lists", "parking_list_items", "parking_labels", "parking_events"}
    actual = {
        row[0]
        for row in connection.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name LIKE 'parking%'
        """))
    }
    if not expected <= actual:
        raise RuntimeError("parking list tables missing")
