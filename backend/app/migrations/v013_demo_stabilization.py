VERSION = "013_demo_stabilization"

import re

from sqlalchemy import text


DO_OPERATIONAL_COLUMNS = (
    "pickup_window_start",
    "pickup_window_end",
    "delivery_window_start",
    "delivery_window_end",
    "pickup_date",
    "delivery_date",
    "planned_departure_at",
    "planned_arrival_at",
    "planned_return_at",
)


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP INDEX IF EXISTS uq_delivery_pod_idempotency",
            "ALTER TABLE delivery_pod_records DROP COLUMN IF EXISTS idempotency_key",
        ]

    ddl = [
        "UPDATE delivery_orders SET canonical_status = 'pending', status = 'Chờ vận chuyển' WHERE canonical_status IN ('planned','approved','unknown')",
        "UPDATE delivery_orders SET canonical_status = 'in_transit', status = 'Đang vận chuyển' WHERE canonical_status = 'arrived'",
        "UPDATE delivery_orders SET canonical_status = 'delivered', status = 'Hoàn thành' WHERE canonical_status = 'completed'",
        "ALTER TABLE delivery_orders ALTER COLUMN canonical_status SET DEFAULT 'pending'",
        "ALTER TABLE delivery_orders DROP CONSTRAINT IF EXISTS ck_delivery_orders_canonical_status",
        "ALTER TABLE delivery_orders ADD CONSTRAINT ck_delivery_orders_canonical_status CHECK (canonical_status IN ('pending','in_transit','delivered','cancelled'))",
        "ALTER TABLE delivery_pod_records ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_pod_idempotency ON delivery_pod_records(idempotency_key) WHERE idempotency_key IS NOT NULL",
        "ALTER TABLE sales_orders ALTER COLUMN total_amount TYPE NUMERIC(24,6) USING total_amount::numeric",
        "ALTER TABLE ar_invoices ALTER COLUMN amount TYPE NUMERIC(24,6) USING amount::numeric",
        "ALTER TABLE ar_invoices ALTER COLUMN vat_pct TYPE NUMERIC(18,8) USING vat_pct::numeric",
        "ALTER TABLE ar_invoices ALTER COLUMN vat_amount TYPE NUMERIC(24,6) USING vat_amount::numeric",
        "ALTER TABLE ar_invoices ALTER COLUMN total TYPE NUMERIC(24,6) USING total::numeric",
        "ALTER TABLE delivery_pod_records ALTER COLUMN delivery_time TYPE TIMESTAMP WITH TIME ZONE USING CASE WHEN delivery_time IS NULL OR trim(delivery_time) = '' THEN NULL ELSE delivery_time::timestamptz END",
        "ALTER TABLE resource_assignments ALTER COLUMN assignment_start TYPE TIMESTAMP WITH TIME ZONE USING assignment_start AT TIME ZONE 'UTC'",
        "ALTER TABLE resource_assignments ALTER COLUMN assignment_end TYPE TIMESTAMP WITH TIME ZONE USING assignment_end AT TIME ZONE 'UTC'",
    ]
    ddl.extend(
        f"ALTER TABLE delivery_orders ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE "
        f"USING CASE WHEN {column} IS NULL OR trim({column}) = '' THEN NULL ELSE {column}::timestamptz END"
        for column in DO_OPERATIONAL_COLUMNS
    )
    return ddl


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _repair_delivery_order_default(connection):
    """Rebuild the SQLite table so its default agrees with the strict lifecycle."""
    table_info = list(connection.execute('PRAGMA table_info("delivery_orders")'))
    canonical = next((row for row in table_info if row[1] == "canonical_status"), None)
    if canonical is None or str(canonical[4] or "").strip("'") == "pending":
        return

    source = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='delivery_orders'"
    ).fetchone()[0]
    artifacts = [
        row[0]
        for row in connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE tbl_name='delivery_orders' AND type IN ('index','trigger') "
            "AND sql IS NOT NULL ORDER BY type,name"
        )
    ]
    temporary = "__v013_delivery_orders"
    create = re.sub(
        r"(?i)^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\"[^\"]+\"|\[[^]]+\]|`[^`]+`|[^\s(]+)",
        f'CREATE TABLE "{temporary}"',
        source,
        count=1,
    )
    open_at, close_at = create.find("("), create.rfind(")")
    body = create[open_at + 1:close_at]
    clauses, start, depth, quote = [], 0, 0, None
    for position, char in enumerate(body):
        if quote:
            if char == quote and (position == 0 or body[position - 1] != "\\"):
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            clauses.append(body[start:position].strip())
            start = position + 1
    clauses.append(body[start:].strip())

    canonical_at = next(
        (
            index
            for index, clause in enumerate(clauses)
            if re.match(r'(?i)^(?:"canonical_status"|canonical_status\b)', clause)
        ),
        None,
    )
    if canonical_at is None:
        raise RuntimeError("delivery_orders canonical_status default schema mismatch")
    clause, replaced = re.subn(
        r"(?i)\s+DEFAULT\s+(?:'[^']*'|\"[^\"]*\"|\([^)]*\)|[^\s,]+)",
        " DEFAULT 'pending'",
        clauses[canonical_at],
        count=1,
    )
    if replaced == 0:
        clause += " DEFAULT 'pending'"
    clauses[canonical_at] = clause
    create = create[:open_at + 1] + ", ".join(clauses) + create[close_at:]

    quoted = ",".join(f'"{row[1]}"' for row in table_info)
    connection.execute(create)
    connection.execute(
        f'INSERT INTO "{temporary}" ({quoted}) SELECT {quoted} FROM "delivery_orders"'
    )
    connection.execute('DROP TABLE "delivery_orders"')
    connection.execute(f'ALTER TABLE "{temporary}" RENAME TO "delivery_orders"')
    for sql in artifacts:
        connection.execute(sql)


def _install_delivery_status_triggers(connection):
    allowed = "'pending','in_transit','delivered','cancelled'"
    for operation in ("insert", "update"):
        connection.execute(f"DROP TRIGGER IF EXISTS ck_delivery_orders_canonical_{operation}")
    connection.execute(
        "CREATE TRIGGER ck_delivery_orders_canonical_insert BEFORE INSERT ON delivery_orders "
        f"WHEN NEW.canonical_status NOT IN ({allowed}) "
        "BEGIN SELECT RAISE(ABORT,'invalid delivery order canonical_status'); END"
    )
    connection.execute(
        "CREATE TRIGGER ck_delivery_orders_canonical_update BEFORE UPDATE OF canonical_status ON delivery_orders "
        f"WHEN NEW.canonical_status NOT IN ({allowed}) "
        "BEGIN SELECT RAISE(ABORT,'invalid delivery order canonical_status'); END"
    )


def upgrade_sqlite(connection):
    if _table_exists(connection, "delivery_orders"):
        connection.execute(
            "UPDATE delivery_orders SET canonical_status='pending', status='Chờ vận chuyển' "
            "WHERE canonical_status IN ('planned','approved','unknown')"
        )
        connection.execute(
            "UPDATE delivery_orders SET canonical_status='in_transit', status='Đang vận chuyển' "
            "WHERE canonical_status='arrived'"
        )
        connection.execute(
            "UPDATE delivery_orders SET canonical_status='delivered', status='Hoàn thành' "
            "WHERE canonical_status='completed'"
        )
        _repair_delivery_order_default(connection)
        _install_delivery_status_triggers(connection)
    if _table_exists(connection, "delivery_pod_records"):
        if "idempotency_key" not in _columns(connection, "delivery_pod_records"):
            connection.execute("ALTER TABLE delivery_pod_records ADD COLUMN idempotency_key TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_pod_idempotency "
            "ON delivery_pod_records(idempotency_key) WHERE idempotency_key IS NOT NULL"
        )
    validate_sqlite(connection)


def rollback_sqlite(connection):
    connection.execute("DROP INDEX IF EXISTS uq_delivery_pod_idempotency")


def validate_sqlite(connection):
    if _table_exists(connection, "delivery_orders"):
        canonical = next(
            (
                row
                for row in connection.execute('PRAGMA table_info("delivery_orders")')
                if row[1] == "canonical_status"
            ),
            None,
        )
        if canonical is None or str(canonical[4] or "").strip("'") != "pending":
            raise RuntimeError("delivery_orders canonical_status default schema mismatch")
    if _table_exists(connection, "delivery_pod_records"):
        if "idempotency_key" not in _columns(connection, "delivery_pod_records"):
            raise RuntimeError("delivery_pod_records idempotency schema mismatch")
        indexes = {row[1] for row in connection.execute('PRAGMA index_list("delivery_pod_records")')}
        if "uq_delivery_pod_idempotency" not in indexes:
            raise RuntimeError("delivery_pod_records idempotency index mismatch")


def validate_postgresql(connection):
    columns = connection.execute(text(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE (table_name = 'delivery_orders' AND column_name IN
          ('pickup_window_start','pickup_window_end','delivery_window_start','delivery_window_end',
           'pickup_date','delivery_date','planned_departure_at','planned_arrival_at','planned_return_at'))
           OR (table_name = 'delivery_pod_records' AND column_name IN ('delivery_time','idempotency_key'))
           OR (table_name = 'resource_assignments' AND column_name IN ('assignment_start','assignment_end'))
        """
    ))
    found = {(row[0], row[1]): row[2] for row in columns}
    for column in DO_OPERATIONAL_COLUMNS:
        if found.get(("delivery_orders", column)) != "timestamp with time zone":
            raise RuntimeError(f"delivery_orders {column} timezone schema mismatch")
    if found.get(("delivery_pod_records", "delivery_time")) != "timestamp with time zone":
        raise RuntimeError("delivery_pod_records delivery_time timezone schema mismatch")
    if ("delivery_pod_records", "idempotency_key") not in found:
        raise RuntimeError("delivery_pod_records idempotency schema mismatch")
    for column in ("assignment_start", "assignment_end"):
        if found.get(("resource_assignments", column)) != "timestamp with time zone":
            raise RuntimeError(f"resource_assignments {column} timezone schema mismatch")
