VERSION = "010_route_context_flow"

from sqlalchemy import text


QUOTE_COLUMNS = {
    "origin": "TEXT",
    "destination": "TEXT",
    "pickup_window_start": "TEXT",
    "pickup_window_end": "TEXT",
    "delivery_window_start": "TEXT",
    "delivery_window_end": "TEXT",
    "weight_kg": "DOUBLE PRECISION DEFAULT 0",
    "pallet_count": "INTEGER DEFAULT 0",
}

SO_COLUMNS = {
    "route_id": "TEXT",
    **QUOTE_COLUMNS,
}

POSTGRES_SO_COLUMNS = {
    "route_id": "TEXT REFERENCES routes(id)",
    **QUOTE_COLUMNS,
}

DO_COLUMNS = {
    "origin": "TEXT",
    "destination": "TEXT",
    "pickup_window_start": "TEXT",
    "pickup_window_end": "TEXT",
    "delivery_window_start": "TEXT",
    "delivery_window_end": "TEXT",
    "weight_kg": "DOUBLE PRECISION DEFAULT 0",
    "pallet_count": "INTEGER DEFAULT 0",
}


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            *[f"ALTER TABLE delivery_orders DROP COLUMN IF EXISTS {column}" for column in DO_COLUMNS],
            *[f"ALTER TABLE sales_orders DROP COLUMN IF EXISTS {column}" for column in SO_COLUMNS],
            *[f"ALTER TABLE quotations DROP COLUMN IF EXISTS {column}" for column in QUOTE_COLUMNS],
        ]
    return [
        *[f"ALTER TABLE quotations ADD COLUMN IF NOT EXISTS {column} {definition}" for column, definition in QUOTE_COLUMNS.items()],
        *[f"ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS {column} {definition}" for column, definition in POSTGRES_SO_COLUMNS.items()],
        *[f"ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS {column} {definition}" for column, definition in DO_COLUMNS.items()],
        "UPDATE quotations q SET origin = COALESCE(NULLIF(q.origin,''), r.name), destination = COALESCE(NULLIF(q.destination,''), r.name) FROM routes r WHERE q.route_id = r.id",
        "UPDATE sales_orders s SET route_id = COALESCE(s.route_id, q.route_id), origin = COALESCE(NULLIF(s.origin,''), NULLIF(q.origin,''), r.name), destination = COALESCE(NULLIF(s.destination,''), NULLIF(q.destination,''), r.name), pickup_window_start = COALESCE(s.pickup_window_start, q.pickup_window_start), pickup_window_end = COALESCE(s.pickup_window_end, q.pickup_window_end), delivery_window_start = COALESCE(s.delivery_window_start, q.delivery_window_start), delivery_window_end = COALESCE(s.delivery_window_end, q.delivery_window_end), weight_kg = COALESCE(s.weight_kg, q.weight_kg, 0), pallet_count = COALESCE(s.pallet_count, q.pallet_count, 0) FROM quotations q LEFT JOIN routes r ON q.route_id = r.id WHERE s.quotation_id = q.id",
        "UPDATE delivery_orders d SET origin = COALESCE(NULLIF(d.origin,''), NULLIF(s.origin,''), r.name), destination = COALESCE(NULLIF(d.destination,''), NULLIF(s.destination,''), r.name), pickup_window_start = COALESCE(d.pickup_window_start, s.pickup_window_start), pickup_window_end = COALESCE(d.pickup_window_end, s.pickup_window_end), delivery_window_start = COALESCE(d.delivery_window_start, s.delivery_window_start), delivery_window_end = COALESCE(d.delivery_window_end, s.delivery_window_end), weight_kg = COALESCE(d.weight_kg, s.weight_kg, 0), pallet_count = COALESCE(d.pallet_count, s.pallet_count, 0) FROM sales_orders s LEFT JOIN routes r ON s.route_id = r.id WHERE d.so_id = s.id",
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
    _add_missing_columns(connection, "quotations", QUOTE_COLUMNS)
    _add_missing_columns(connection, "sales_orders", SO_COLUMNS)
    _add_missing_columns(connection, "delivery_orders", DO_COLUMNS)
    if _table_exists(connection, "quotations") and _table_exists(connection, "routes"):
        connection.execute(
            """
            UPDATE quotations
               SET origin = COALESCE(NULLIF(origin,''), (SELECT name FROM routes WHERE routes.id = quotations.route_id)),
                   destination = COALESCE(NULLIF(destination,''), (SELECT name FROM routes WHERE routes.id = quotations.route_id))
            """
        )
    if _table_exists(connection, "sales_orders") and _table_exists(connection, "quotations"):
        connection.execute(
            """
            UPDATE sales_orders
               SET route_id = COALESCE(route_id, (SELECT route_id FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   origin = COALESCE(NULLIF(origin,''), (SELECT NULLIF(origin,'') FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   destination = COALESCE(NULLIF(destination,''), (SELECT NULLIF(destination,'') FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   pickup_window_start = COALESCE(pickup_window_start, (SELECT pickup_window_start FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   pickup_window_end = COALESCE(pickup_window_end, (SELECT pickup_window_end FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   delivery_window_start = COALESCE(delivery_window_start, (SELECT delivery_window_start FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   delivery_window_end = COALESCE(delivery_window_end, (SELECT delivery_window_end FROM quotations WHERE quotations.id = sales_orders.quotation_id)),
                   weight_kg = COALESCE(weight_kg, (SELECT weight_kg FROM quotations WHERE quotations.id = sales_orders.quotation_id), 0),
                   pallet_count = COALESCE(pallet_count, (SELECT pallet_count FROM quotations WHERE quotations.id = sales_orders.quotation_id), 0)
            """
        )
    if _table_exists(connection, "delivery_orders") and _table_exists(connection, "sales_orders"):
        connection.execute(
            """
            UPDATE delivery_orders
               SET origin = COALESCE(NULLIF(origin,''), (SELECT NULLIF(origin,'') FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id)),
                   destination = COALESCE(NULLIF(destination,''), (SELECT NULLIF(destination,'') FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id)),
                   pickup_window_start = COALESCE(pickup_window_start, (SELECT pickup_window_start FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id)),
                   pickup_window_end = COALESCE(pickup_window_end, (SELECT pickup_window_end FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id)),
                   delivery_window_start = COALESCE(delivery_window_start, (SELECT delivery_window_start FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id)),
                   delivery_window_end = COALESCE(delivery_window_end, (SELECT delivery_window_end FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id)),
                   weight_kg = COALESCE(weight_kg, (SELECT weight_kg FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id), 0),
                   pallet_count = COALESCE(pallet_count, (SELECT pallet_count FROM sales_orders WHERE sales_orders.id = delivery_orders.so_id), 0)
            """
        )
    validate_sqlite(connection)


def rollback_sqlite(connection):
    # Keep columns on SQLite rollback to avoid destructive table rebuilds for demo data.
    return


def validate_sqlite(connection):
    for table, columns in (("quotations", QUOTE_COLUMNS), ("sales_orders", SO_COLUMNS), ("delivery_orders", DO_COLUMNS)):
        if _table_exists(connection, table) and not set(columns) <= _columns(connection, table):
            raise RuntimeError(f"{table} route context schema mismatch")


def validate_postgresql(connection):
    result = connection.execute(text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_name IN ('quotations','sales_orders','delivery_orders')
        """
    ))
    rows = result.fetchall() if hasattr(result, "fetchall") else list(result)
    found = {(row[0], row[1]) for row in rows}
    for table, columns in (("quotations", QUOTE_COLUMNS), ("sales_orders", SO_COLUMNS), ("delivery_orders", DO_COLUMNS)):
        for column in columns:
            if (table, column) not in found:
                raise RuntimeError(f"{table} route context schema mismatch")
