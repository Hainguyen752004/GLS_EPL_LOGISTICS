VERSION = "016_delivery_completion_closeout"

from sqlalchemy import text


POD_ADDITIONS = {
    "delivery_result": "TEXT",
    "cargo_condition": "TEXT",
}

REQUIRED_COLUMNS = {
    "delivery_order_closeouts": {
        "id", "do_id", "base_selling_price_snapshot", "base_price_source",
        "base_price_source_id", "surcharge_total", "final_selling_price",
        "currency_code", "completed_at", "completed_by", "created_at",
    },
    "delivery_order_charge_adjustments": {
        "id", "closeout_id", "line_no", "name", "original_amount",
        "actual_amount", "increase_amount", "note", "created_at", "created_by",
    },
    "delivery_pod_documents": {
        "id", "pod_record_id", "file_name", "mime_type", "file_size",
        "checksum", "content", "created_at", "created_by",
    },
}

REQUIRED_CONSTRAINTS = {
    "pk_delivery_order_closeouts", "uq_delivery_order_closeouts_do",
    "fk_delivery_order_closeouts_do", "fk_delivery_order_closeouts_currency",
    "ck_delivery_closeout_base_price", "ck_delivery_closeout_surcharge",
    "ck_delivery_closeout_final_price", "pk_delivery_order_charge_adjustments",
    "uq_delivery_charge_adjustment_line", "fk_delivery_charge_adjustment_closeout",
    "ck_delivery_charge_line_positive", "ck_delivery_charge_original_amount",
    "ck_delivery_charge_actual_amount", "ck_delivery_charge_increase_amount",
    "pk_delivery_pod_documents", "uq_delivery_pod_document_checksum",
    "fk_delivery_pod_document_record", "ck_delivery_pod_document_size",
}


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS delivery_pod_documents",
            "DROP TABLE IF EXISTS delivery_order_charge_adjustments",
            "DROP TABLE IF EXISTS delivery_order_closeouts",
            "ALTER TABLE delivery_pod_records DROP COLUMN IF EXISTS cargo_condition",
            "ALTER TABLE delivery_pod_records DROP COLUMN IF EXISTS delivery_result",
        ]
    timestamp_type = "TIMESTAMP" if dialect == "sqlite" else "TIMESTAMPTZ"
    binary_type = "BLOB" if dialect == "sqlite" else "BYTEA"
    size_type = "INTEGER" if dialect == "sqlite" else "BIGINT"
    return [
        *[
            f"ALTER TABLE delivery_pod_records ADD COLUMN IF NOT EXISTS {name} {definition}"
            for name, definition in POD_ADDITIONS.items()
        ],
        """
        CREATE TABLE IF NOT EXISTS delivery_order_closeouts (
            id TEXT CONSTRAINT pk_delivery_order_closeouts PRIMARY KEY,
            do_id TEXT NOT NULL,
            base_selling_price_snapshot NUMERIC(24,6) NOT NULL,
            base_price_source TEXT NOT NULL,
            base_price_source_id TEXT,
            surcharge_total NUMERIC(24,6) NOT NULL DEFAULT 0,
            final_selling_price NUMERIC(24,6) NOT NULL,
            currency_code TEXT NOT NULL,
            completed_at {timestamp_type} NOT NULL,
            completed_by TEXT NOT NULL,
            created_at {timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_delivery_order_closeouts_do UNIQUE (do_id),
            CONSTRAINT fk_delivery_order_closeouts_do FOREIGN KEY (do_id) REFERENCES delivery_orders(id),
            CONSTRAINT fk_delivery_order_closeouts_currency FOREIGN KEY (currency_code) REFERENCES currency_definitions(code),
            CONSTRAINT ck_delivery_closeout_base_price CHECK (base_selling_price_snapshot >= 0),
            CONSTRAINT ck_delivery_closeout_surcharge CHECK (surcharge_total >= 0),
            CONSTRAINT ck_delivery_closeout_final_price CHECK (final_selling_price = base_selling_price_snapshot + surcharge_total)
        )
        """.format(timestamp_type=timestamp_type),
        """
        CREATE TABLE IF NOT EXISTS delivery_order_charge_adjustments (
            id TEXT CONSTRAINT pk_delivery_order_charge_adjustments PRIMARY KEY,
            closeout_id TEXT NOT NULL,
            line_no INTEGER NOT NULL,
            name TEXT NOT NULL,
            original_amount NUMERIC(24,6) NOT NULL,
            actual_amount NUMERIC(24,6) NOT NULL,
            increase_amount NUMERIC(24,6) NOT NULL,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            CONSTRAINT uq_delivery_charge_adjustment_line UNIQUE (closeout_id, line_no),
            CONSTRAINT fk_delivery_charge_adjustment_closeout FOREIGN KEY (closeout_id) REFERENCES delivery_order_closeouts(id) ON DELETE CASCADE,
            CONSTRAINT ck_delivery_charge_line_positive CHECK (line_no > 0),
            CONSTRAINT ck_delivery_charge_original_amount CHECK (original_amount >= 0),
            CONSTRAINT ck_delivery_charge_actual_amount CHECK (actual_amount >= original_amount),
            CONSTRAINT ck_delivery_charge_increase_amount CHECK (increase_amount = actual_amount - original_amount)
        )
        """.format(timestamp_type=timestamp_type),
        """
        CREATE TABLE IF NOT EXISTS delivery_pod_documents (
            id TEXT CONSTRAINT pk_delivery_pod_documents PRIMARY KEY,
            pod_record_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            file_size {size_type} NOT NULL,
            checksum TEXT NOT NULL,
            content {binary_type} NOT NULL,
            created_at {timestamp_type} NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            CONSTRAINT uq_delivery_pod_document_checksum UNIQUE (pod_record_id, checksum),
            CONSTRAINT fk_delivery_pod_document_record FOREIGN KEY (pod_record_id) REFERENCES delivery_pod_records(id) ON DELETE CASCADE,
            CONSTRAINT ck_delivery_pod_document_size CHECK (file_size >= 0 AND file_size <= 10485760)
        )
        """.format(size_type=size_type, binary_type=binary_type, timestamp_type=timestamp_type),
    ]


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _unique_columns(connection, table):
    result = set()
    for row in connection.execute(f'PRAGMA index_list("{table}")'):
        if row[2]:
            result.add(tuple(item[2] for item in connection.execute(f'PRAGMA index_info("{row[1]}")')))
    return result


def _foreign_keys(connection, table):
    return {(row[3], row[2], row[4], row[6].upper()) for row in connection.execute(f'PRAGMA foreign_key_list("{table}")')}


def upgrade_sqlite(connection):
    if not _table_exists(connection, "delivery_pod_records"):
        raise RuntimeError("delivery_pod_records table missing")
    columns = _columns(connection, "delivery_pod_records")
    for name, definition in POD_ADDITIONS.items():
        if name not in columns:
            connection.execute(f'ALTER TABLE delivery_pod_records ADD COLUMN "{name}" {definition}')
    connection.execute(statements("sqlite")[2])
    connection.execute(statements("sqlite")[3])
    connection.execute(statements("sqlite")[4])
    validate_sqlite(connection)


def rollback_sqlite(connection):
    for table in ("delivery_pod_documents", "delivery_order_charge_adjustments", "delivery_order_closeouts"):
        if _table_exists(connection, table):
            connection.execute(f'DROP TABLE "{table}"')


def validate_sqlite(connection):
    if not set(POD_ADDITIONS) <= _columns(connection, "delivery_pod_records"):
        raise RuntimeError("delivery_pod_records completion schema mismatch")
    for table, required in REQUIRED_COLUMNS.items():
        if not required <= _columns(connection, table):
            raise RuntimeError(f"{table} schema mismatch")
    if ("do_id",) not in _unique_columns(connection, "delivery_order_closeouts"):
        raise RuntimeError("delivery_order_closeouts schema mismatch")
    if ("closeout_id", "line_no") not in _unique_columns(connection, "delivery_order_charge_adjustments"):
        raise RuntimeError("delivery_order_charge_adjustments schema mismatch")
    if ("pod_record_id", "checksum") not in _unique_columns(connection, "delivery_pod_documents"):
        raise RuntimeError("delivery_pod_documents schema mismatch")
    if ("closeout_id", "delivery_order_closeouts", "id", "CASCADE") not in _foreign_keys(connection, "delivery_order_charge_adjustments"):
        raise RuntimeError("delivery_order_charge_adjustments schema mismatch")
    if ("pod_record_id", "delivery_pod_records", "id", "CASCADE") not in _foreign_keys(connection, "delivery_pod_documents"):
        raise RuntimeError("delivery_pod_documents schema mismatch")


def validate_postgresql(connection):
    rows = connection.execute(text(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_name IN ('delivery_order_closeouts','delivery_order_charge_adjustments',
                             'delivery_pod_documents','delivery_pod_records')
        """
    ))
    found = {(row[0], row[1]): row[2] for row in rows}
    for table, columns in REQUIRED_COLUMNS.items():
        if any((table, column) not in found for column in columns):
            raise RuntimeError(f"{table} schema mismatch")
    if any(("delivery_pod_records", column) not in found for column in POD_ADDITIONS):
        raise RuntimeError("delivery_pod_records completion schema mismatch")
    if found.get(("delivery_pod_documents", "content")) != "bytea":
        raise RuntimeError("delivery_pod_documents content type mismatch")
    constraints = {row[0] for row in connection.execute(text(
        """
        SELECT conname
        FROM pg_constraint
        WHERE conrelid IN ('delivery_order_closeouts'::regclass,
                           'delivery_order_charge_adjustments'::regclass,
                           'delivery_pod_documents'::regclass)
        """
    ))}
    if not REQUIRED_CONSTRAINTS <= constraints:
        raise RuntimeError("delivery completion constraints mismatch")
