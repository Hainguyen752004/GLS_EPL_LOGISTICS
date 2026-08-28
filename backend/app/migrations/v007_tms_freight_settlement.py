VERSION = "007_tms_freight_settlement"

FINANCE_TABLES = {
    "currency_definitions", "currency_rate_history", "tax_codes", "finance_control_config",
    "freight_actual_costs", "freight_charge_items", "freight_cost_documents",
    "ap_invoices", "ap_invoice_lines", "freight_settlements", "settlement_payments",
}

REQUIRED_COLUMNS = {
    "idempotency_records": {"id", "actor", "method", "path", "idempotency_key", "operation", "request_hash", "response_json", "status", "created_at"},
    "journal_batches": {"id", "invoice_id", "source_type", "source_id", "status", "posted_at", "created_at"},
    "journal_lines": {"id", "batch_id", "account_code", "debit", "credit", "currency_code", "exchange_rate_snapshot",
                      "transaction_amount", "transaction_currency", "exchange_rate", "functional_debit", "functional_credit"},
    "finance_control_config": {"id", "functional_currency", "enforce_creator_approver_sod", "require_distinct_poster",
                               "distance_variance_threshold", "document_https_hosts", "created_at", "updated_at"},
    "freight_actual_costs": {"id", "freight_order_id", "carrier_id", "currency_code", "functional_currency",
                             "exchange_rate_snapshot", "exchange_rate_date", "exchange_rate_source",
                             "planned_distance_km", "actual_distance_km", "distance_status",
                             "distance_variance_percent", "distance_variance_warning",
                             "subtotal_amount", "tax_amount", "total_amount", "status", "is_active", "version",
                             "reversal_of_cost_id", "reversed_by_cost_id", "reversal_reason",
                             "created_at", "updated_at", "submitted_at", "approved_at", "reversed_at",
                             "created_by", "updated_by", "submitted_by", "approved_by", "reversed_by"},
    "freight_charge_items": {"id", "cost_id", "charge_type", "description", "quantity", "unit_price",
                             "tax_code", "tax_rate_snapshot", "tax_mode", "net_amount", "tax_amount",
                             "total_amount", "rounding_adjustment", "created_at", "updated_at", "created_by", "updated_by"},
    "freight_cost_documents": {"id", "cost_id", "document_type", "storage_url", "file_name", "mime_type",
                               "checksum", "vendor_invoice_no", "document_date", "created_at", "updated_at", "created_by", "updated_by"},
    "ap_invoices": {"id", "cost_id", "carrier_id", "carrier_name_snapshot", "carrier_tax_code_snapshot",
                    "vendor_invoice_no", "normalized_vendor_invoice_no", "document_kind", "invoice_date", "due_date",
                    "currency_code", "functional_currency", "exchange_rate_snapshot", "exchange_rate_date",
                    "exchange_rate_source", "subtotal_amount", "tax_amount", "total_amount",
                    "functional_subtotal_amount", "functional_tax_amount", "functional_total_amount",
                    "status", "is_active", "version", "reversal_of_ap_id", "reversed_by_ap_id", "reversal_reason",
                    "posting_reference", "created_at", "updated_at", "submitted_at", "approved_at", "posted_at",
                    "reversed_at", "created_by", "updated_by", "submitted_by", "approved_by", "posted_by", "reversed_by"},
    "ap_invoice_lines": {"id", "ap_invoice_id", "charge_item_id", "charge_type", "description", "quantity", "unit_price",
                         "currency_code", "tax_code", "tax_rate_snapshot", "tax_mode", "account_mapping_key",
                         "account_code_snapshot", "net_amount", "tax_amount", "total_amount", "rounding_adjustment"},
    "freight_settlements": {"id", "ap_invoice_id", "settlement_period", "currency_code", "functional_currency",
                            "approved_amount", "paid_amount", "remaining_amount", "status", "version",
                            "created_at", "updated_at", "created_by", "updated_by"},
    "settlement_payments": {"id", "settlement_id", "amount", "currency_code", "functional_currency",
                            "exchange_rate_snapshot", "exchange_rate_date", "exchange_rate_source", "functional_amount",
                            "posting_date", "payment_method", "reference_no", "status", "posting_reference",
                            "reversal_of_payment_id", "reversed_by_payment_id", "created_at", "created_by"},
}


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS settlement_payments",
            "DROP TABLE IF EXISTS freight_settlements",
            "DROP TABLE IF EXISTS ap_invoice_lines",
            "DROP TABLE IF EXISTS ap_invoices",
            "DROP TABLE IF EXISTS freight_cost_documents",
            "DROP TABLE IF EXISTS freight_charge_items",
            "DROP TABLE IF EXISTS freight_actual_costs",
            "DROP TABLE IF EXISTS tax_codes",
            "DROP TABLE IF EXISTS currency_rate_history",
            "DROP TABLE IF EXISTS finance_control_config",
            "DROP TABLE IF EXISTS currency_definitions",
        ]
    prefix = []
    if _dialect == "postgresql":
        prefix = [
            "ALTER TABLE carriers ADD COLUMN IF NOT EXISTS is_internal BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE idempotency_records DROP CONSTRAINT IF EXISTS idempotency_records_pkey",
            "ALTER TABLE idempotency_records ADD COLUMN IF NOT EXISTS id INTEGER GENERATED BY DEFAULT AS IDENTITY",
            "ALTER TABLE idempotency_records ADD COLUMN IF NOT EXISTS actor TEXT",
            "ALTER TABLE idempotency_records ADD COLUMN IF NOT EXISTS method TEXT",
            "ALTER TABLE idempotency_records ADD COLUMN IF NOT EXISTS path TEXT",
            "ALTER TABLE idempotency_records ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed'",
            "UPDATE idempotency_records SET actor=coalesce(actor,'legacy'), method=coalesce(method,'LEGACY'), path=coalesce(path,operation,''), response_json=coalesce(response_json,'{}')",
            "ALTER TABLE idempotency_records ALTER COLUMN actor SET NOT NULL",
            "ALTER TABLE idempotency_records ALTER COLUMN method SET NOT NULL",
            "ALTER TABLE idempotency_records ALTER COLUMN path SET NOT NULL",
            "ALTER TABLE idempotency_records ALTER COLUMN response_json SET NOT NULL",
            "ALTER TABLE idempotency_records ADD CONSTRAINT idempotency_records_pkey PRIMARY KEY (id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_idempotency_scope ON idempotency_records(actor, method, path, idempotency_key)",
            "ALTER TABLE journal_batches ALTER COLUMN invoice_id DROP NOT NULL",
            "ALTER TABLE journal_batches ADD COLUMN IF NOT EXISTS source_type TEXT",
            "ALTER TABLE journal_batches ADD COLUMN IF NOT EXISTS source_id TEXT",
            "UPDATE journal_batches SET source_type=coalesce(source_type,'ar_invoice'), source_id=coalesce(source_id,invoice_id) WHERE invoice_id IS NOT NULL",
            "ALTER TABLE journal_batches ADD CONSTRAINT ck_journal_source_type CHECK (source_type IS NULL OR source_type IN ('ar_invoice','ap_invoice','ap_payment','ap_reversal','payment_reversal'))",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_source ON journal_batches(source_type, source_id)",
            "ALTER TABLE journal_lines ADD COLUMN IF NOT EXISTS transaction_amount NUMERIC(24,6) NOT NULL DEFAULT 0",
            "ALTER TABLE journal_lines ADD COLUMN IF NOT EXISTS transaction_currency TEXT NOT NULL DEFAULT 'VND'",
            "ALTER TABLE journal_lines ADD COLUMN IF NOT EXISTS exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1",
            "ALTER TABLE journal_lines ADD COLUMN IF NOT EXISTS functional_debit NUMERIC(24,6) NOT NULL DEFAULT 0",
            "ALTER TABLE journal_lines ADD COLUMN IF NOT EXISTS functional_credit NUMERIC(24,6) NOT NULL DEFAULT 0",
            "UPDATE journal_lines SET transaction_amount=CASE WHEN debit > 0 THEN debit ELSE credit END, transaction_currency=currency_code, exchange_rate=exchange_rate_snapshot, functional_debit=debit, functional_credit=credit",
        ]
    return prefix + _core_statements(_dialect)


def _core_statements(dialect):
    identity = "INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY" if dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    bool_type = "BOOLEAN" if dialect == "postgresql" else "INTEGER"
    true_value = "TRUE" if dialect == "postgresql" else "1"
    false_value = "FALSE" if dialect == "postgresql" else "0"
    return [
        """CREATE TABLE IF NOT EXISTS currency_definitions (
            code TEXT PRIMARY KEY,
            minor_units INTEGER NOT NULL CHECK (minor_units >= 0 AND minor_units <= 6),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS currency_rate_history (
            id {identity},
            currency_code TEXT NOT NULL REFERENCES currency_definitions(code),
            functional_currency TEXT NOT NULL REFERENCES currency_definitions(code),
            rate_date DATE NOT NULL,
            rate NUMERIC(18,8) NOT NULL CHECK (rate > 0),
            source TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_currency_rate_history UNIQUE (currency_code, functional_currency, rate_date, source)
        )""".format(identity=identity),
        """CREATE TABLE IF NOT EXISTS tax_codes (
            id {identity},
            code TEXT NOT NULL,
            rate NUMERIC(18,8) NOT NULL CHECK (rate >= 0),
            mode TEXT NOT NULL CHECK (mode IN ('exclusive','inclusive','exempt')),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            effective_from DATE NOT NULL,
            effective_to DATE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (effective_to IS NULL OR effective_from <= effective_to),
            CONSTRAINT uq_tax_code_effective_from UNIQUE (code, effective_from)
        )""".format(identity=identity),
        """CREATE TABLE IF NOT EXISTS finance_control_config (
            id TEXT PRIMARY KEY DEFAULT 'GLOBAL',
            functional_currency TEXT NOT NULL DEFAULT 'VND' REFERENCES currency_definitions(code),
            enforce_creator_approver_sod BOOLEAN NOT NULL DEFAULT TRUE,
            require_distinct_poster BOOLEAN NOT NULL DEFAULT TRUE,
            distance_variance_threshold NUMERIC(18,8) NOT NULL DEFAULT 0 CHECK (distance_variance_threshold >= 0),
            document_https_hosts TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (id = 'GLOBAL')
        )""",
        """CREATE TABLE IF NOT EXISTS freight_actual_costs (
            id TEXT PRIMARY KEY,
            freight_order_id TEXT NOT NULL REFERENCES freight_orders(id),
            carrier_id TEXT NOT NULL REFERENCES carriers(id),
            currency_code TEXT NOT NULL REFERENCES currency_definitions(code),
            functional_currency TEXT NOT NULL REFERENCES currency_definitions(code),
            exchange_rate_snapshot NUMERIC(18,8) NOT NULL DEFAULT 1,
            exchange_rate_date DATE NOT NULL,
            exchange_rate_source TEXT NOT NULL,
            planned_distance_km NUMERIC(18,3) NOT NULL DEFAULT 0,
            actual_distance_km NUMERIC(18,3) NOT NULL DEFAULT 0,
            distance_status TEXT NOT NULL DEFAULT 'insufficient_gps_data',
            distance_variance_percent NUMERIC(18,8),
            distance_variance_warning BOOLEAN NOT NULL DEFAULT FALSE,
            subtotal_amount NUMERIC(24,6) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(24,6) NOT NULL DEFAULT 0,
            total_amount NUMERIC(24,6) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            version INTEGER NOT NULL DEFAULT 1,
            reversal_of_cost_id TEXT UNIQUE REFERENCES freight_actual_costs(id),
            reversed_by_cost_id TEXT UNIQUE REFERENCES freight_actual_costs(id) DEFERRABLE INITIALLY DEFERRED,
            reversal_reason TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            approved_at TIMESTAMP,
            reversed_at TIMESTAMP,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            submitted_by TEXT,
            approved_by TEXT,
            reversed_by TEXT,
            CHECK (status IN ('draft','submitted','approved','reversed')),
            CHECK (planned_distance_km >= 0 AND actual_distance_km >= 0),
            CHECK (version > 0),
            CHECK ((status = 'reversed' AND is_active = FALSE) OR (status <> 'reversed' AND is_active = TRUE)),
            CHECK (reversal_of_cost_id IS NULL OR reversal_of_cost_id <> id),
            CHECK (reversal_of_cost_id IS NULL OR (status = 'reversed' AND is_active = FALSE AND length(trim(reversal_reason)) > 0 AND subtotal_amount <= 0 AND tax_amount <= 0 AND total_amount <= 0)),
            CHECK (status <> 'reversed' OR reversal_of_cost_id IS NOT NULL OR reversed_by_cost_id IS NOT NULL)
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_cost_freight_order ON freight_actual_costs(freight_order_id) WHERE is_active = {true_value}".format(true_value=true_value),
        """CREATE TABLE IF NOT EXISTS freight_charge_items (
            id TEXT PRIMARY KEY,
            cost_id TEXT NOT NULL REFERENCES freight_actual_costs(id) ON DELETE CASCADE,
            charge_type TEXT NOT NULL CHECK (charge_type IN ('fuel','toll','driver','waiting','loading','unloading','carrier_base','surcharge','discount','other')),
            description TEXT,
            quantity NUMERIC(18,4) NOT NULL CHECK (quantity >= 0),
            unit_price NUMERIC(24,6) NOT NULL,
            tax_code TEXT NOT NULL,
            tax_rate_snapshot NUMERIC(18,8) NOT NULL,
            tax_mode TEXT NOT NULL,
            net_amount NUMERIC(24,6) NOT NULL,
            tax_amount NUMERIC(24,6) NOT NULL,
            total_amount NUMERIC(24,6) NOT NULL,
            rounding_adjustment NUMERIC(24,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            CHECK (charge_type = 'discount' OR unit_price >= 0)
        )""",
        """CREATE TABLE IF NOT EXISTS freight_cost_documents (
            id TEXT PRIMARY KEY,
            cost_id TEXT NOT NULL REFERENCES freight_actual_costs(id) ON DELETE CASCADE,
            document_type TEXT NOT NULL,
            storage_url TEXT NOT NULL,
            file_name TEXT,
            mime_type TEXT,
            checksum TEXT NOT NULL,
            vendor_invoice_no TEXT,
            document_date DATE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            CONSTRAINT uq_freight_cost_document_checksum UNIQUE (cost_id, checksum)
        )""",
        """CREATE TABLE IF NOT EXISTS ap_invoices (
            id TEXT PRIMARY KEY,
            cost_id TEXT NOT NULL REFERENCES freight_actual_costs(id),
            carrier_id TEXT NOT NULL REFERENCES carriers(id),
            carrier_name_snapshot TEXT NOT NULL,
            carrier_tax_code_snapshot TEXT,
            vendor_invoice_no TEXT NOT NULL,
            normalized_vendor_invoice_no TEXT NOT NULL,
            document_kind TEXT NOT NULL DEFAULT 'invoice',
            invoice_date DATE NOT NULL,
            due_date DATE,
            currency_code TEXT NOT NULL REFERENCES currency_definitions(code),
            functional_currency TEXT NOT NULL REFERENCES currency_definitions(code),
            exchange_rate_snapshot NUMERIC(18,8) NOT NULL,
            exchange_rate_date DATE NOT NULL,
            exchange_rate_source TEXT NOT NULL,
            subtotal_amount NUMERIC(24,6) NOT NULL,
            tax_amount NUMERIC(24,6) NOT NULL,
            total_amount NUMERIC(24,6) NOT NULL,
            functional_subtotal_amount NUMERIC(24,6) NOT NULL,
            functional_tax_amount NUMERIC(24,6) NOT NULL,
            functional_total_amount NUMERIC(24,6) NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            version INTEGER NOT NULL DEFAULT 1,
            reversal_of_ap_id TEXT UNIQUE REFERENCES ap_invoices(id),
            reversed_by_ap_id TEXT UNIQUE REFERENCES ap_invoices(id) DEFERRABLE INITIALLY DEFERRED,
            reversal_reason TEXT,
            posting_reference TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            approved_at TIMESTAMP,
            posted_at TIMESTAMP,
            reversed_at TIMESTAMP,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            submitted_by TEXT,
            approved_by TEXT,
            posted_by TEXT,
            reversed_by TEXT,
            CONSTRAINT uq_ap_vendor_document UNIQUE (carrier_id, normalized_vendor_invoice_no, document_kind),
            CHECK (document_kind IN ('invoice','credit_memo')),
            CHECK (status IN ('draft','submitted','approved','posted','partially_paid','paid','reversed')),
            CHECK (version > 0),
            CHECK (reversal_of_ap_id IS NULL OR reversal_of_ap_id <> id),
            CHECK (document_kind <> 'credit_memo' OR (subtotal_amount <= 0 AND tax_amount <= 0 AND total_amount <= 0))
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_ap_cost ON ap_invoices(cost_id) WHERE is_active = {true_value}".format(true_value=true_value),
        """CREATE TABLE IF NOT EXISTS ap_invoice_lines (
            id TEXT PRIMARY KEY,
            ap_invoice_id TEXT NOT NULL REFERENCES ap_invoices(id) ON DELETE CASCADE,
            charge_item_id TEXT NOT NULL REFERENCES freight_charge_items(id),
            charge_type TEXT NOT NULL,
            description TEXT,
            quantity NUMERIC(18,4) NOT NULL,
            unit_price NUMERIC(24,6) NOT NULL,
            currency_code TEXT NOT NULL,
            tax_code TEXT NOT NULL,
            tax_rate_snapshot NUMERIC(18,8) NOT NULL,
            tax_mode TEXT NOT NULL CHECK (tax_mode IN ('exclusive','inclusive','exempt')),
            account_mapping_key TEXT NOT NULL,
            account_code_snapshot TEXT,
            net_amount NUMERIC(24,6) NOT NULL,
            tax_amount NUMERIC(24,6) NOT NULL,
            total_amount NUMERIC(24,6) NOT NULL,
            rounding_adjustment NUMERIC(24,6) NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS freight_settlements (
            id TEXT PRIMARY KEY,
            ap_invoice_id TEXT NOT NULL UNIQUE REFERENCES ap_invoices(id),
            settlement_period TEXT NOT NULL,
            currency_code TEXT NOT NULL REFERENCES currency_definitions(code),
            functional_currency TEXT NOT NULL REFERENCES currency_definitions(code),
            approved_amount NUMERIC(24,6) NOT NULL,
            paid_amount NUMERIC(24,6) NOT NULL DEFAULT 0,
            remaining_amount NUMERIC(24,6) NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            CHECK (status IN ('open','partially_paid','paid','reversed')),
            CHECK (version > 0),
            CHECK (approved_amount >= 0 AND paid_amount >= 0 AND remaining_amount >= 0),
            CHECK (paid_amount <= approved_amount)
        )""",
        """CREATE TABLE IF NOT EXISTS settlement_payments (
            id TEXT PRIMARY KEY,
            settlement_id TEXT NOT NULL REFERENCES freight_settlements(id),
            amount NUMERIC(24,6) NOT NULL CHECK (amount > 0),
            currency_code TEXT NOT NULL REFERENCES currency_definitions(code),
            functional_currency TEXT NOT NULL REFERENCES currency_definitions(code),
            exchange_rate_snapshot NUMERIC(18,8) NOT NULL,
            exchange_rate_date DATE NOT NULL,
            exchange_rate_source TEXT NOT NULL,
            functional_amount NUMERIC(24,6) NOT NULL,
            posting_date DATE NOT NULL,
            payment_method TEXT NOT NULL,
            reference_no TEXT,
            status TEXT NOT NULL DEFAULT 'posted',
            posting_reference TEXT,
            reversal_of_payment_id TEXT UNIQUE REFERENCES settlement_payments(id),
            reversed_by_payment_id TEXT UNIQUE REFERENCES settlement_payments(id) DEFERRABLE INITIALLY DEFERRED,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL,
            CHECK (status IN ('posted','reversed')),
            CHECK (reversal_of_payment_id IS NULL OR reversal_of_payment_id <> id)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_freight_charge_items_cost ON freight_charge_items(cost_id)",
        "CREATE INDEX IF NOT EXISTS ix_ap_invoice_lines_invoice ON ap_invoice_lines(ap_invoice_id)",
        "CREATE INDEX IF NOT EXISTS ix_settlement_payments_settlement ON settlement_payments(settlement_id)",
        "CREATE INDEX IF NOT EXISTS ix_tax_codes_code_effective ON tax_codes(code, effective_from, effective_to)",
    ]


def upgrade_sqlite(connection):
    if _sqlite_table_exists(connection, "carriers") and "is_internal" not in _sqlite_columns(connection, "carriers"):
        connection.execute("ALTER TABLE carriers ADD COLUMN is_internal INTEGER NOT NULL DEFAULT 0")
    _upgrade_idempotency_sqlite(connection)
    _upgrade_journal_sqlite(connection)
    for sql in _core_statements("sqlite"):
        connection.execute(sql)
    validate_sqlite(connection)


def rollback_sqlite(connection):
    for sql in statements("sqlite", "rollback"):
        connection.execute(sql)


def pre_rollback_validate(connection, _dialect, restore_from):
    if restore_from:
        return
    populated = any(
        connection.execute(f'SELECT EXISTS(SELECT 1 FROM "{table}" LIMIT 1)').fetchone()[0]
        for table in FINANCE_TABLES
        if _sqlite_table_exists(connection, table)
    )
    ap_journal = False
    if _sqlite_table_exists(connection, "journal_batches") and "source_type" in _sqlite_columns(connection, "journal_batches"):
        ap_journal = bool(connection.execute(
            "SELECT EXISTS(SELECT 1 FROM journal_batches WHERE source_type IN ('ap_invoice','ap_payment','ap_reversal','payment_reversal') LIMIT 1)"
        ).fetchone()[0])
    if populated or ap_journal:
        raise RuntimeError("destructive rollback refused: supply --restore-from")


def validate_sqlite(connection):
    for table, required in REQUIRED_COLUMNS.items():
        if not _sqlite_table_exists(connection, table):
            raise RuntimeError(f"{table} schema mismatch")
        if not required <= _sqlite_columns(connection, table):
            raise RuntimeError(f"{table} schema mismatch")
    _validate_sqlite_idempotency(connection)
    _validate_sqlite_settlement_payments(connection)


def validate_postgresql(connection):
    rows = list(connection.execute(
        __import__("sqlalchemy").text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name IN "
            "('idempotency_records','journal_batches','journal_lines','finance_control_config',"
            "'freight_actual_costs','freight_charge_items','freight_cost_documents','ap_invoices',"
            "'ap_invoice_lines','freight_settlements','settlement_payments')"
        )
    ))
    by_table = {}
    for table, column in rows:
        by_table.setdefault(table, set()).add(column)
    for table, required in REQUIRED_COLUMNS.items():
        if not required <= by_table.get(table, set()):
            raise RuntimeError(f"{table} schema mismatch")
    _validate_postgresql_finance_indexes(connection)
    _validate_postgresql_settlement_payment_checks(connection)


def _validate_postgresql_finance_indexes(connection):
    indexes = {row[0]: row[1].lower() for row in connection.execute(
        __import__("sqlalchemy").text(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public' "
            "AND tablename IN ('idempotency_records','settlement_payments','freight_actual_costs','ap_invoices')"
        )
    )}
    index_text = "\n".join(indexes.values())
    if ("unique" not in index_text
            or "idempotency_records" not in index_text
            or not all(column in index_text for column in ("actor", "method", "path", "idempotency_key"))):
        raise RuntimeError("idempotency_records schema mismatch")
    payment_unique_sets = (
        ("settlement_payments", "reversal_of_payment_id"),
        ("settlement_payments", "reversed_by_payment_id"),
    )
    for table, column in payment_unique_sets:
        if table not in index_text or column not in index_text or "unique" not in index_text:
            raise RuntimeError("settlement_payments schema mismatch")
    if "freight_actual_costs" not in index_text or "freight_order_id" not in index_text or "is_active" not in index_text:
        raise RuntimeError("freight_actual_costs schema mismatch")
    if "ap_invoices" not in index_text or "cost_id" not in index_text or "is_active" not in index_text:
        raise RuntimeError("ap_invoices schema mismatch")


def _validate_postgresql_settlement_payment_checks(connection):
    checks = [
        (row[0], (row[1] or "").lower())
        for row in connection.execute(
            __import__("sqlalchemy").text(
                "SELECT tc.table_name, cc.check_clause FROM information_schema.table_constraints tc "
                "JOIN information_schema.check_constraints cc "
                "ON cc.constraint_schema=tc.constraint_schema AND cc.constraint_name=tc.constraint_name "
                "WHERE tc.table_schema='public' AND tc.table_name='settlement_payments'"
            )
        )
    ]
    ddl = "\n".join(clause for _table, clause in checks)
    required = (
        "amount >",
        "status",
        "posted",
        "reversed",
        "reversal_of_payment_id",
        "<> id",
    )
    if any(item not in ddl for item in required):
        raise RuntimeError("settlement_payments schema mismatch")


def _sqlite_table_exists(connection, table):
    return bool(connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone())


def _sqlite_columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _sqlite_column_meta(connection, table):
    return {row[1]: {"type": row[2], "notnull": bool(row[3]), "pk": row[5]}
            for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _sqlite_unique_index_columns(connection, table):
    unique_sets = []
    for index in connection.execute(f'PRAGMA index_list("{table}")'):
        if not index[2]:
            continue
        columns = tuple(row[2] for row in connection.execute(f'PRAGMA index_info("{index[1]}")'))
        unique_sets.append(columns)
    return set(unique_sets)


def _sqlite_table_sql(connection, table):
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return (row[0] or "").lower() if row else ""


def _validate_sqlite_idempotency(connection):
    meta = _sqlite_column_meta(connection, "idempotency_records")
    for column in ("actor", "method", "path", "idempotency_key", "request_hash", "response_json"):
        if not meta.get(column, {}).get("notnull"):
            raise RuntimeError("idempotency_records schema mismatch")
    if ("actor", "method", "path", "idempotency_key") not in _sqlite_unique_index_columns(connection, "idempotency_records"):
        raise RuntimeError("idempotency_records schema mismatch")


def _validate_sqlite_settlement_payments(connection):
    meta = _sqlite_column_meta(connection, "settlement_payments")
    for column in ("amount", "settlement_id", "currency_code", "functional_currency", "exchange_rate_snapshot",
                   "exchange_rate_date", "exchange_rate_source", "functional_amount", "posting_date",
                   "payment_method", "status", "created_by"):
        if not meta.get(column, {}).get("notnull"):
            raise RuntimeError("settlement_payments schema mismatch")
    unique_sets = _sqlite_unique_index_columns(connection, "settlement_payments")
    if ("reversal_of_payment_id",) not in unique_sets or ("reversed_by_payment_id",) not in unique_sets:
        raise RuntimeError("settlement_payments schema mismatch")
    ddl = _sqlite_table_sql(connection, "settlement_payments")
    required_fragments = (
        "check (amount > 0)",
        "check (status in ('posted','reversed'))",
        "check (reversal_of_payment_id is null or reversal_of_payment_id <> id)",
    )
    if not all(fragment in ddl for fragment in required_fragments):
        raise RuntimeError("settlement_payments schema mismatch")


def _upgrade_idempotency_sqlite(connection):
    if not _sqlite_table_exists(connection, "idempotency_records"):
        connection.execute("""CREATE TABLE idempotency_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            operation TEXT NOT NULL DEFAULT '',
            request_hash TEXT NOT NULL,
            response_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_idempotency_scope UNIQUE (actor, method, path, idempotency_key)
        )""")
        return
    if REQUIRED_COLUMNS["idempotency_records"] <= _sqlite_columns(connection, "idempotency_records"):
        return
    connection.execute("ALTER TABLE idempotency_records RENAME TO idempotency_records_legacy_v007")
    connection.execute("""CREATE TABLE idempotency_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT NOT NULL,
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        operation TEXT NOT NULL DEFAULT '',
        request_hash TEXT NOT NULL,
        response_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'completed',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_idempotency_scope UNIQUE (actor, method, path, idempotency_key)
    )""")
    connection.execute("""INSERT INTO idempotency_records
        (actor, method, path, idempotency_key, operation, request_hash, response_json, status, created_at)
        SELECT 'legacy', 'LEGACY', coalesce(operation,''), idempotency_key, coalesce(operation,''),
               request_hash, coalesce(response_json, '{}'), 'completed', created_at
        FROM idempotency_records_legacy_v007""")
    connection.execute("DROP TABLE idempotency_records_legacy_v007")


def _upgrade_journal_sqlite(connection):
    if _sqlite_table_exists(connection, "journal_batches") and not REQUIRED_COLUMNS["journal_batches"] <= _sqlite_columns(connection, "journal_batches"):
        connection.execute("ALTER TABLE journal_batches RENAME TO journal_batches_legacy_v007")
        connection.execute("""CREATE TABLE journal_batches (
            id TEXT PRIMARY KEY,
            invoice_id TEXT REFERENCES ar_invoices(id),
            source_type TEXT,
            source_id TEXT,
            status TEXT NOT NULL,
            posted_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_journal_source UNIQUE (source_type, source_id),
            CHECK (source_type IS NULL OR source_type IN ('ar_invoice','ap_invoice','ap_payment','ap_reversal','payment_reversal'))
        )""")
        connection.execute("""INSERT INTO journal_batches(id, invoice_id, source_type, source_id, status, posted_at, created_at)
            SELECT id, invoice_id, 'ar_invoice', invoice_id, status, posted_at, created_at
            FROM journal_batches_legacy_v007""")
        connection.execute("DROP TABLE journal_batches_legacy_v007")
    elif not _sqlite_table_exists(connection, "journal_batches"):
        connection.execute("""CREATE TABLE journal_batches (
            id TEXT PRIMARY KEY,
            invoice_id TEXT REFERENCES ar_invoices(id),
            source_type TEXT,
            source_id TEXT,
            status TEXT NOT NULL,
            posted_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_journal_source UNIQUE (source_type, source_id),
            CHECK (source_type IS NULL OR source_type IN ('ar_invoice','ap_invoice','ap_payment','ap_reversal','payment_reversal'))
        )""")
    else:
        connection.execute(
            "UPDATE journal_batches SET source_type='ar_invoice', source_id=invoice_id "
            "WHERE invoice_id IS NOT NULL AND (source_type IS NULL OR source_id IS NULL)"
        )
    if _sqlite_table_exists(connection, "journal_lines") and not REQUIRED_COLUMNS["journal_lines"] <= _sqlite_columns(connection, "journal_lines"):
        connection.execute("ALTER TABLE journal_lines RENAME TO journal_lines_legacy_v007")
        connection.execute("""CREATE TABLE journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL REFERENCES journal_batches(id),
            account_code TEXT NOT NULL,
            debit NUMERIC NOT NULL DEFAULT 0,
            credit NUMERIC NOT NULL DEFAULT 0,
            currency_code TEXT NOT NULL DEFAULT 'VND',
            exchange_rate_snapshot NUMERIC NOT NULL DEFAULT 1,
            transaction_amount NUMERIC(24,6) NOT NULL DEFAULT 0,
            transaction_currency TEXT NOT NULL DEFAULT 'VND',
            exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
            functional_debit NUMERIC(24,6) NOT NULL DEFAULT 0,
            functional_credit NUMERIC(24,6) NOT NULL DEFAULT 0
        )""")
        connection.execute("""INSERT INTO journal_lines
            (id, batch_id, account_code, debit, credit, currency_code, exchange_rate_snapshot,
             transaction_amount, transaction_currency, exchange_rate, functional_debit, functional_credit)
            SELECT id, batch_id, account_code, debit, credit, currency_code, exchange_rate_snapshot,
                   CASE WHEN debit > 0 THEN debit ELSE credit END, currency_code, exchange_rate_snapshot, debit, credit
            FROM journal_lines_legacy_v007""")
        connection.execute("DROP TABLE journal_lines_legacy_v007")
    elif not _sqlite_table_exists(connection, "journal_lines"):
        connection.execute("""CREATE TABLE journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL REFERENCES journal_batches(id),
            account_code TEXT NOT NULL,
            debit NUMERIC NOT NULL DEFAULT 0,
            credit NUMERIC NOT NULL DEFAULT 0,
            currency_code TEXT NOT NULL DEFAULT 'VND',
            exchange_rate_snapshot NUMERIC NOT NULL DEFAULT 1,
            transaction_amount NUMERIC(24,6) NOT NULL DEFAULT 0,
            transaction_currency TEXT NOT NULL DEFAULT 'VND',
            exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
            functional_debit NUMERIC(24,6) NOT NULL DEFAULT 0,
            functional_credit NUMERIC(24,6) NOT NULL DEFAULT 0
        )""")
    else:
        connection.execute("""UPDATE journal_lines
            SET transaction_amount=CASE WHEN debit > 0 THEN debit ELSE credit END,
                transaction_currency=currency_code,
                exchange_rate=exchange_rate_snapshot,
                functional_debit=debit,
                functional_credit=credit
            WHERE transaction_amount = 0 AND functional_debit = 0 AND functional_credit = 0
              AND (debit > 0 OR credit > 0)
        """)
