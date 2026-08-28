VERSION = "004_tms_tendering"


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return ["DROP TABLE IF EXISTS tender_offers", "DROP TABLE IF EXISTS tenders", "DROP TABLE IF EXISTS carriers"]
    return [
        """CREATE TABLE IF NOT EXISTS carriers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, tax_code TEXT, contact_person TEXT,
            phone TEXT, email TEXT, status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by TEXT NOT NULL DEFAULT 'system'
        )""",
        """CREATE TABLE IF NOT EXISTS tenders (
            id TEXT PRIMARY KEY, freight_order_id TEXT NOT NULL UNIQUE REFERENCES freight_orders(id),
            response_deadline TIMESTAMP NOT NULL, status TEXT NOT NULL DEFAULT 'published',
            awarded_offer_id TEXT, awarded_carrier_id TEXT REFERENCES carriers(id), version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system', updated_by TEXT NOT NULL DEFAULT 'system'
        )""",
        """CREATE TABLE IF NOT EXISTS tender_offers (
            id TEXT PRIMARY KEY, tender_id TEXT NOT NULL REFERENCES tenders(id),
            carrier_id TEXT NOT NULL REFERENCES carriers(id), amount NUMERIC(18,2) NOT NULL,
            currency_code TEXT NOT NULL DEFAULT 'VND', note TEXT, status TEXT NOT NULL DEFAULT 'offered',
            submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, submitted_by TEXT NOT NULL DEFAULT 'system',
            CONSTRAINT uq_tender_carrier_offer UNIQUE (tender_id, carrier_id), CHECK (amount > 0)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_tenders_status ON tenders(status)",
        "CREATE INDEX IF NOT EXISTS ix_tender_offers_tender ON tender_offers(tender_id)",
    ]


def upgrade_sqlite(connection):
    for sql in statements("sqlite", "upgrade"):
        connection.execute(sql)


def rollback_sqlite(connection):
    for sql in statements("sqlite", "rollback"):
        connection.execute(sql)
