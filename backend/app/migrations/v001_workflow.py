import json
import re

VERSION = "001_workflow"

AUDIT_COLUMNS = (
    ("canonical_status", "TEXT NOT NULL DEFAULT 'unknown'"), ("created_at", "TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:00'"),
    ("updated_at", "TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:00'"), ("created_by", "TEXT NOT NULL DEFAULT 'migration'"),
    ("updated_by", "TEXT NOT NULL DEFAULT 'migration'"), ("version", "INTEGER NOT NULL DEFAULT 1"),
)

STATUS_MAP = {
    "draft": "draft", "sent": "sent", "approved": "approved",
    "confirmed": "confirmed", "pending approval": "pending",
    "pending": "pending", "in transit": "in_transit", "completed": "completed",
    "posted": "posted", "reversed": "reversed", "cancelled": "cancelled",
}


def _columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _add(connection, table, name, definition):
    if name not in _columns(connection, table):
        connection.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')


def _rebuild_with_additions(connection, table, additions):
    """SQLite cannot safely add constrained columns; rebuild within caller's transaction."""
    present = _columns(connection, table)
    additions = [(name, definition) for name, definition in additions if name not in present]
    if not additions:
        return
    source = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
    artifacts = [row[0] for row in connection.execute("SELECT sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') AND sql IS NOT NULL ORDER BY type,name", (table,))]
    temporary = f"__v001_{table}"
    create = re.sub(r"(?i)^CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\"[^\"]+\"|\[[^]]+\]|`[^`]+`|[^\s(]+)", f'CREATE TABLE "{temporary}"', source, count=1)
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
            clauses.append(body[start:position].strip()); start = position + 1
    clauses.append(body[start:].strip())
    constraint_at = next((i for i, clause in enumerate(clauses) if re.match(r"(?i)^(CONSTRAINT\s+\S+\s+)?(PRIMARY|FOREIGN|UNIQUE|CHECK)\b", clause)), len(clauses))
    added = [f'"{name}" {definition}' for name, definition in additions]
    create = create[:open_at + 1] + ", ".join(clauses[:constraint_at] + added + clauses[constraint_at:]) + create[close_at:]
    old_names = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
    quoted = ",".join(f'"{name}"' for name in old_names)
    connection.execute(create)
    connection.execute(f'INSERT INTO "{temporary}" ({quoted}) SELECT {quoted} FROM "{table}"')
    connection.execute(f'DROP TABLE "{table}"')
    connection.execute(f'ALTER TABLE "{temporary}" RENAME TO "{table}"')
    for sql in artifacts:
        connection.execute(sql)


def statements(dialect, direction):
    if direction == "rollback":
        result = ["DROP INDEX IF EXISTS uq_active_invoice_do", "DROP INDEX IF EXISTS uq_delivery_orders_so", "DROP INDEX IF EXISTS uq_sales_orders_quotation", "DROP TABLE IF EXISTS journal_lines", "DROP TABLE IF EXISTS journal_batches", "DROP TABLE IF EXISTS account_mappings", "DROP TABLE IF EXISTS accounting_periods", "DROP TABLE IF EXISTS idempotency_records", "DROP TABLE IF EXISTS migration_quarantine"]
        for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
            result.extend(f"ALTER TABLE {table} DROP COLUMN {name}" for name, _ in reversed(AUDIT_COLUMNS))
        result.extend(("ALTER TABLE ar_invoices DROP COLUMN tax_rate_snapshot", "ALTER TABLE ar_invoices DROP COLUMN exchange_rate_snapshot", "ALTER TABLE ar_invoices DROP COLUMN currency_code", "ALTER TABLE ar_invoices DROP COLUMN reversal_of_invoice_id", "ALTER TABLE ar_invoices DROP COLUMN is_active", "ALTER TABLE sales_orders DROP COLUMN tax_rate_snapshot", "ALTER TABLE sales_orders DROP COLUMN exchange_rate_snapshot", "ALTER TABLE sales_orders DROP COLUMN currency_code", "ALTER TABLE sales_orders DROP COLUMN quotation_id"))
        return result
    boolean = "BOOLEAN NOT NULL DEFAULT TRUE" if dialect == "postgresql" else "INTEGER NOT NULL DEFAULT 1"
    pk = "BIGSERIAL PRIMARY KEY" if dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    active = "TRUE" if dialect == "postgresql" else "1"
    add_column = "ADD COLUMN IF NOT EXISTS" if dialect == "postgresql" else "ADD COLUMN"
    ddl = [
        f"ALTER TABLE sales_orders {add_column} quotation_id TEXT REFERENCES quotations(id)",
        f"ALTER TABLE ar_invoices {add_column} is_active {boolean}",
        f"ALTER TABLE ar_invoices {add_column} reversal_of_invoice_id TEXT REFERENCES ar_invoices(id)",
        f"ALTER TABLE ar_invoices {add_column} currency_code TEXT NOT NULL DEFAULT 'VND'",
        f"ALTER TABLE ar_invoices {add_column} exchange_rate_snapshot NUMERIC NOT NULL DEFAULT 1",
        f"ALTER TABLE ar_invoices {add_column} tax_rate_snapshot NUMERIC",
        f"CREATE TABLE IF NOT EXISTS migration_quarantine (id {pk}, migration_version TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, reason TEXT NOT NULL, payload_json TEXT NOT NULL, quarantined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS idempotency_records (idempotency_key TEXT PRIMARY KEY, operation TEXT NOT NULL, request_hash TEXT NOT NULL, response_json TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS accounting_periods (id TEXT PRIMARY KEY, starts_at TIMESTAMP NOT NULL, ends_at TIMESTAMP NOT NULL, status TEXT NOT NULL, closed_at TIMESTAMP, closed_by TEXT)",
        "CREATE TABLE IF NOT EXISTS account_mappings (mapping_key TEXT PRIMARY KEY, account_code TEXT NOT NULL, effective_from TIMESTAMP, effective_to TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS journal_batches (id TEXT PRIMARY KEY, invoice_id TEXT NOT NULL REFERENCES ar_invoices(id), status TEXT NOT NULL, posted_at TIMESTAMP, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(invoice_id))",
        f"CREATE TABLE IF NOT EXISTS journal_lines (id {pk}, batch_id TEXT NOT NULL REFERENCES journal_batches(id), account_code TEXT NOT NULL, debit NUMERIC NOT NULL DEFAULT 0, credit NUMERIC NOT NULL DEFAULT 0, currency_code TEXT NOT NULL DEFAULT 'VND', exchange_rate_snapshot NUMERIC NOT NULL DEFAULT 1)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_orders_quotation ON sales_orders(quotation_id) WHERE quotation_id IS NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_orders_so ON delivery_orders(so_id) WHERE so_id IS NOT NULL",
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_active_invoice_do ON ar_invoices(do_id) WHERE is_active = {active}",
    ]
    for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
        ddl.extend(
            f"ALTER TABLE {table} {add_column} {name} {definition}"
            for name, definition in AUDIT_COLUMNS
        )
    ddl.extend((
        f"ALTER TABLE sales_orders {add_column} currency_code TEXT NOT NULL DEFAULT 'VND'",
        f"ALTER TABLE sales_orders {add_column} exchange_rate_snapshot NUMERIC NOT NULL DEFAULT 1",
        f"ALTER TABLE sales_orders {add_column} tax_rate_snapshot NUMERIC",
    ))
    if dialect == "postgresql":
        indexes = [sql for sql in ddl if sql.startswith("CREATE UNIQUE INDEX")]
        ddl = [sql for sql in ddl if not sql.startswith("CREATE UNIQUE INDEX")]
        case = "CASE lower(trim(status)) WHEN 'draft' THEN 'draft' WHEN 'sent' THEN 'sent' WHEN 'approved' THEN 'approved' WHEN 'confirmed' THEN 'confirmed' WHEN 'pending approval' THEN 'pending' WHEN 'pending' THEN 'pending' WHEN 'in transit' THEN 'in_transit' WHEN 'completed' THEN 'completed' WHEN 'posted' THEN 'posted' WHEN 'reversed' THEN 'reversed' WHEN 'cancelled' THEN 'cancelled' ELSE 'unknown' END"
        for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
            ddl.append(f"UPDATE {table} SET canonical_status={case}, created_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP, created_by='migration', updated_by='migration'")
        ddl.extend((
            "UPDATE ar_invoices SET tax_rate_snapshot=vat_pct WHERE tax_rate_snapshot IS NULL",
            "INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) SELECT '001_workflow','sales_order',s.id,'quotation provenance collision',json_build_object('quotation_id',q.id)::text FROM sales_orders s JOIN quotations q ON q.customer_id=s.customer_id AND lower(trim(q.status))='approved' AND substring(s.id from '^SO-([0-9]{4})-[0-9]+$')=substring(q.id from '^QT-([0-9]{4})-[0-9]+$') AND cast(substring(s.id from '^SO-[0-9]{4}-([0-9]+)$') AS BIGINT)=cast(substring(q.id from '^QT-[0-9]{4}-([0-9]+)$') AS BIGINT) WHERE (SELECT count(*) FROM sales_orders s2 WHERE s2.customer_id=q.customer_id AND substring(s2.id from '^SO-([0-9]{4})-[0-9]+$')=substring(q.id from '^QT-([0-9]{4})-[0-9]+$') AND cast(substring(s2.id from '^SO-[0-9]{4}-([0-9]+)$') AS BIGINT)=cast(substring(q.id from '^QT-[0-9]{4}-([0-9]+)$') AS BIGINT))>1",
            "UPDATE sales_orders s SET quotation_id=q.id FROM quotations q WHERE s.quotation_id IS NULL AND q.customer_id=s.customer_id AND lower(trim(q.status))='approved' AND substring(s.id from '^SO-([0-9]{4})-[0-9]+$')=substring(q.id from '^QT-([0-9]{4})-[0-9]+$') AND cast(substring(s.id from '^SO-[0-9]{4}-([0-9]+)$') AS BIGINT)=cast(substring(q.id from '^QT-[0-9]{4}-([0-9]+)$') AS BIGINT) AND (SELECT count(*) FROM quotations q2 WHERE q2.customer_id=s.customer_id AND lower(trim(q2.status))='approved' AND substring(q2.id from '^QT-([0-9]{4})-[0-9]+$')=substring(s.id from '^SO-([0-9]{4})-[0-9]+$') AND cast(substring(q2.id from '^QT-[0-9]{4}-([0-9]+)$') AS BIGINT)=cast(substring(s.id from '^SO-[0-9]{4}-([0-9]+)$') AS BIGINT))=1 AND (SELECT count(*) FROM sales_orders s2 WHERE s2.customer_id=q.customer_id AND substring(s2.id from '^SO-([0-9]{4})-[0-9]+$')=substring(q.id from '^QT-([0-9]{4})-[0-9]+$') AND cast(substring(s2.id from '^SO-[0-9]{4}-([0-9]+)$') AS BIGINT)=cast(substring(q.id from '^QT-[0-9]{4}-([0-9]+)$') AS BIGINT))=1",
            "INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) SELECT '001_workflow','sales_order',s.id,'unmatched quotation chain',json_build_object('customer_id',s.customer_id)::text FROM sales_orders s WHERE s.quotation_id IS NULL AND NOT EXISTS (SELECT 1 FROM migration_quarantine mq WHERE mq.migration_version='001_workflow' AND mq.entity_type='sales_order' AND mq.entity_id=s.id)",
            "INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) SELECT '001_workflow','sales_order',so_id,'ambiguous delivery chain',json_build_object('delivery_order_ids',json_agg(id ORDER BY id))::text FROM delivery_orders WHERE so_id IS NOT NULL GROUP BY so_id HAVING count(*)>1",
            "WITH ambiguous AS MATERIALIZED (SELECT so_id FROM delivery_orders WHERE so_id IS NOT NULL GROUP BY so_id HAVING count(*)>1) UPDATE delivery_orders SET so_id=NULL WHERE so_id IN (SELECT so_id FROM ambiguous)",
            "INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) SELECT '001_workflow','delivery_order',do_id,'ambiguous active invoice chain',json_build_object('invoice_ids',json_agg(id ORDER BY id))::text FROM ar_invoices WHERE do_id IS NOT NULL AND is_active=TRUE GROUP BY do_id HAVING count(*)>1",
            "WITH ambiguous AS MATERIALIZED (SELECT do_id FROM ar_invoices WHERE do_id IS NOT NULL AND is_active=TRUE GROUP BY do_id HAVING count(*)>1) UPDATE ar_invoices SET is_active=FALSE WHERE do_id IN (SELECT do_id FROM ambiguous)",
            "INSERT INTO journal_batches(id,invoice_id,status,posted_at) SELECT 'MIG-'||i.id,i.id,'posted',CURRENT_TIMESTAMP FROM ar_invoices i WHERE EXISTS (SELECT 1 FROM gl_transactions g WHERE g.invoice_id=i.id) ON CONFLICT (invoice_id) DO NOTHING",
            "INSERT INTO journal_lines(batch_id,account_code,debit,credit) SELECT 'MIG-'||g.invoice_id,g.account_code,coalesce(g.debit,0),coalesce(g.credit,0) FROM gl_transactions g JOIN ar_invoices i ON i.id=g.invoice_id",
            "INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) SELECT '001_workflow','gl_transaction',g.invoice_id,'missing invoice',json_build_object('invoice_id',g.invoice_id)::text FROM gl_transactions g LEFT JOIN ar_invoices i ON i.id=g.invoice_id WHERE g.invoice_id IS NOT NULL AND i.id IS NULL GROUP BY g.invoice_id",
        ))
        ddl.extend(indexes)
    return ddl


def upgrade_sqlite(connection):
    per_table = {
        "quotations": list(AUDIT_COLUMNS),
        "sales_orders": [("quotation_id", "TEXT REFERENCES quotations(id)"), *AUDIT_COLUMNS, ("currency_code", "TEXT NOT NULL DEFAULT 'VND'"), ("exchange_rate_snapshot", "REAL NOT NULL DEFAULT 1"), ("tax_rate_snapshot", "REAL")],
        "delivery_orders": list(AUDIT_COLUMNS),
        "ar_invoices": [*AUDIT_COLUMNS, ("is_active", "INTEGER NOT NULL DEFAULT 1"), ("reversal_of_invoice_id", "TEXT REFERENCES ar_invoices(id)"), ("currency_code", "TEXT NOT NULL DEFAULT 'VND'"), ("exchange_rate_snapshot", "REAL NOT NULL DEFAULT 1"), ("tax_rate_snapshot", "REAL")],
    }
    for table, additions in per_table.items():
        _rebuild_with_additions(connection, table, additions)
    for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
        rows = connection.execute(f'SELECT id,status FROM "{table}"').fetchall()
        for entity_id, status in rows:
            canonical = STATUS_MAP.get((status or "").strip().lower(), "unknown")
            connection.execute(f'UPDATE "{table}" SET canonical_status=?,created_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP,created_by=coalesce(created_by,\'migration\'),updated_by=coalesce(updated_by,\'migration\') WHERE id=?', (canonical, entity_id))
    connection.execute("UPDATE ar_invoices SET tax_rate_snapshot=vat_pct WHERE tax_rate_snapshot IS NULL")
    deferred_indexes = []
    for sql in statements("sqlite", "upgrade"):
        if sql.startswith("CREATE UNIQUE INDEX"):
            deferred_indexes.append(sql)
        elif not sql.startswith("ALTER TABLE"):
            connection.execute(sql)
    for so_id, count in connection.execute("SELECT so_id,COUNT(*) FROM delivery_orders WHERE so_id IS NOT NULL GROUP BY so_id HAVING COUNT(*)>1").fetchall():
        ids = [row[0] for row in connection.execute("SELECT id FROM delivery_orders WHERE so_id=? ORDER BY id", (so_id,))]
        connection.execute("INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) VALUES (?,?,?,?,?)", (VERSION, "sales_order", so_id, "ambiguous delivery chain", json.dumps({"delivery_order_ids": ids})))
        connection.execute("UPDATE delivery_orders SET so_id=NULL WHERE so_id=?", (so_id,))
    for do_id, count in connection.execute("SELECT do_id,COUNT(*) FROM ar_invoices WHERE do_id IS NOT NULL AND is_active=1 GROUP BY do_id HAVING COUNT(*)>1").fetchall():
        ids = [row[0] for row in connection.execute("SELECT id FROM ar_invoices WHERE do_id=? ORDER BY id", (do_id,))]
        connection.execute("INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) VALUES (?,?,?,?,?)", (VERSION, "delivery_order", do_id, "ambiguous active invoice chain", json.dumps({"invoice_ids": ids})))
        connection.execute("UPDATE ar_invoices SET is_active=0 WHERE do_id=?", (do_id,))
    for sql in deferred_indexes:
        connection.execute(sql)
    allowed = "'draft','sent','approved','confirmed','pending','in_transit','completed','posted','reversed','cancelled','unknown'"
    for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
        connection.execute(f"CREATE TRIGGER ck_{table}_canonical_insert BEFORE INSERT ON {table} WHEN NEW.canonical_status NOT IN ({allowed}) BEGIN SELECT RAISE(ABORT,'invalid canonical_status'); END")
        connection.execute(f"CREATE TRIGGER ck_{table}_canonical_update BEFORE UPDATE OF canonical_status ON {table} WHEN NEW.canonical_status NOT IN ({allowed}) BEGIN SELECT RAISE(ABORT,'invalid canonical_status'); END")
    rows = connection.execute("SELECT id, customer_id FROM sales_orders WHERE quotation_id IS NULL").fetchall()
    claims = {}
    for order_id, customer_id in rows:
        candidates = [r[0] for r in connection.execute("SELECT id FROM quotations WHERE customer_id=? AND lower(trim(status))='approved' ORDER BY id", (customer_id,))]
        order_match = re.fullmatch(r"SO-(\d{4})-(\d+)", order_id or "", re.IGNORECASE)
        proven = []
        if order_match:
            suffix = (order_match.group(1), int(order_match.group(2)))
            for candidate in candidates:
                quote_match = re.fullmatch(r"QT-(\d{4})-(\d+)", candidate or "", re.IGNORECASE)
                if quote_match and (quote_match.group(1), int(quote_match.group(2))) == suffix:
                    proven.append(candidate)
        if len(proven) == 1:
            claims.setdefault(proven[0], []).append(order_id)
        else:
            reason = "ambiguous quotation chain" if len(proven) > 1 or len(candidates) > 1 else "unmatched quotation chain"
            connection.execute("INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) VALUES (?,?,?,?,?)", (VERSION, "sales_order", order_id, reason, json.dumps({"candidate_ids": candidates, "provenance_matches": proven})))
    for quotation_id, order_ids in claims.items():
        if len(order_ids) == 1:
            connection.execute("UPDATE sales_orders SET quotation_id=? WHERE id=?", (quotation_id, order_ids[0]))
        else:
            for order_id in sorted(order_ids):
                connection.execute("INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) VALUES (?,?,?,?,?)", (VERSION, "sales_order", order_id, "quotation provenance collision", json.dumps({"quotation_id": quotation_id, "claiming_order_ids": sorted(order_ids)})))
    invoice_ids = [row[0] for row in connection.execute("SELECT DISTINCT g.invoice_id FROM gl_transactions g JOIN ar_invoices i ON i.id=g.invoice_id WHERE g.invoice_id IS NOT NULL ORDER BY g.invoice_id")]
    for invoice_id in invoice_ids:
        batch_id = f"MIG-{invoice_id}"
        connection.execute("INSERT INTO journal_batches(id,invoice_id,status,posted_at) VALUES (?,?,?,CURRENT_TIMESTAMP)", (batch_id, invoice_id, "posted"))
        connection.execute("INSERT INTO journal_lines(batch_id,account_code,debit,credit) SELECT ?,account_code,coalesce(debit,0),coalesce(credit,0) FROM gl_transactions WHERE invoice_id=? ORDER BY id", (batch_id, invoice_id))
    orphan_ids = [row[0] for row in connection.execute("SELECT DISTINCT g.invoice_id FROM gl_transactions g LEFT JOIN ar_invoices i ON i.id=g.invoice_id WHERE g.invoice_id IS NOT NULL AND i.id IS NULL ORDER BY g.invoice_id")]
    for invoice_id in orphan_ids:
        connection.execute("INSERT INTO migration_quarantine(migration_version,entity_type,entity_id,reason,payload_json) VALUES (?,?,?,?,?)", (VERSION, "gl_transaction", invoice_id, "missing invoice", json.dumps({"invoice_id": invoice_id})))


def rollback_sqlite(connection):
    for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
        connection.execute(f'DROP TRIGGER IF EXISTS "ck_{table}_canonical_insert"')
        connection.execute(f'DROP TRIGGER IF EXISTS "ck_{table}_canonical_update"')
    for index in ("uq_sales_orders_quotation", "uq_delivery_orders_so", "uq_active_invoice_do"):
        connection.execute(f'DROP INDEX IF EXISTS "{index}"')
    for table in ("journal_lines", "journal_batches", "account_mappings", "accounting_periods", "idempotency_records", "migration_quarantine"):
        connection.execute(f'DROP TABLE IF EXISTS "{table}"')
    additions = {
        "sales_orders": ("quotation_id", "currency_code", "exchange_rate_snapshot", "tax_rate_snapshot"),
        "ar_invoices": ("is_active", "reversal_of_invoice_id", "currency_code", "exchange_rate_snapshot", "tax_rate_snapshot"),
    }
    for table in ("quotations", "sales_orders", "delivery_orders", "ar_invoices"):
        additions[table] = additions.get(table, ()) + tuple(name for name, _ in AUDIT_COLUMNS)
    for table, names in additions.items():
        present = _columns(connection, table)
        for name in reversed(names):
            if name in present:
                connection.execute(f'ALTER TABLE "{table}" DROP COLUMN "{name}"')
