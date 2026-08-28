VERSION = "020_epl_expense_vouchers"

from sqlalchemy import text


TABLE = "epl_expense_vouchers"


def _create_sql():
    return f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id VARCHAR(128) PRIMARY KEY,
            trip_id VARCHAR(128) NOT NULL UNIQUE REFERENCES transport_trips(id),
            cost_id VARCHAR(128) NOT NULL REFERENCES freight_actual_costs(id),
            do_id VARCHAR REFERENCES delivery_orders(id),
            voucher_no VARCHAR(128) NOT NULL UNIQUE,
            voucher_date DATE NOT NULL,
            vehicle_manager VARCHAR(255),
            payment_method VARCHAR(32) NOT NULL DEFAULT 'cash',
            contract_no VARCHAR(128),
            machine_numbers VARCHAR(500),
            checked_by VARCHAR(255),
            note TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(128) NOT NULL,
            updated_by VARCHAR(128) NOT NULL,
            CONSTRAINT ck_epl_expense_voucher_payment_method
                CHECK (payment_method IN ('cash','bank_transfer','credit','other')),
            CONSTRAINT ck_epl_expense_voucher_version CHECK (version > 0)
        )
    """


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [f"DROP TABLE IF EXISTS {TABLE}"]
    return [_create_sql()]


def upgrade_sqlite(connection):
    connection.execute(_create_sql())
    validate_sqlite(connection)


def rollback_sqlite(connection):
    connection.execute(f"DROP TABLE IF EXISTS {TABLE}")


def validate_sqlite(connection):
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)
    ).fetchone()
    if not exists:
        raise RuntimeError(f"{TABLE} missing")


def validate_postgresql(connection):
    rows = connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'epl_expense_vouchers'
    """))
    if not list(rows):
        raise RuntimeError(f"{TABLE} missing")
