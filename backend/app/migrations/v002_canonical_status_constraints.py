VERSION = "002_canonical_status_constraints"

ALLOWED_STATUSES = {
    "quotations": ("draft", "sent", "approved", "cancelled", "unknown"),
    "sales_orders": ("draft", "confirmed", "pending", "in_transit", "completed", "cancelled", "unknown"),
    "delivery_orders": ("planned", "approved", "pending", "in_transit", "arrived", "delivered", "completed", "cancelled", "unknown"),
    "ar_invoices": ("posted", "reversed", "cancelled", "unknown"),
}


def _quoted(statuses):
    return ",".join(f"'{status}'" for status in statuses)


def statements(dialect, direction):
    if dialect == "sqlite":
        return []
    result = []
    for table, statuses in ALLOWED_STATUSES.items():
        constraint = f"ck_{table}_canonical_status"
        result.append(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}")
        if direction == "upgrade":
            result.append(
                f"ALTER TABLE {table} ADD CONSTRAINT {constraint} "
                f"CHECK (canonical_status IN ({_quoted(statuses)}))"
            )
    return result


def _install_sqlite_triggers(connection, allowed_by_table):
    for table, statuses in allowed_by_table.items():
        allowed = _quoted(statuses)
        for operation in ("insert", "update"):
            connection.execute(f'DROP TRIGGER IF EXISTS "ck_{table}_canonical_{operation}"')
        connection.execute(
            f"CREATE TRIGGER ck_{table}_canonical_insert BEFORE INSERT ON {table} "
            f"WHEN NEW.canonical_status NOT IN ({allowed}) "
            "BEGIN SELECT RAISE(ABORT,'invalid canonical_status'); END"
        )
        connection.execute(
            f"CREATE TRIGGER ck_{table}_canonical_update BEFORE UPDATE OF canonical_status ON {table} "
            f"WHEN NEW.canonical_status NOT IN ({allowed}) "
            "BEGIN SELECT RAISE(ABORT,'invalid canonical_status'); END"
        )


def upgrade_sqlite(connection):
    _install_sqlite_triggers(connection, ALLOWED_STATUSES)


def rollback_sqlite(connection):
    legacy = ("draft", "sent", "approved", "confirmed", "pending", "in_transit", "completed", "posted", "reversed", "cancelled", "unknown")
    _install_sqlite_triggers(connection, {table: legacy for table in ALLOWED_STATUSES})
