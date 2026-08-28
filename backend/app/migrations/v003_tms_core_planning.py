VERSION = "003_tms_core_planning"


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS freight_order_units",
            "DROP TABLE IF EXISTS freight_orders",
            "DROP TABLE IF EXISTS freight_units",
            "DROP TABLE IF EXISTS transport_demands",
        ]
    return [
        """CREATE TABLE IF NOT EXISTS transport_demands (
            id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
            pickup_location_id TEXT NOT NULL REFERENCES locations(id), delivery_location_id TEXT NOT NULL REFERENCES locations(id),
            pickup_window_start TIMESTAMP NOT NULL, pickup_window_end TIMESTAMP NOT NULL,
            delivery_window_start TIMESTAMP NOT NULL, delivery_window_end TIMESTAMP NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL DEFAULT 0, volume_m3 DOUBLE PRECISION NOT NULL DEFAULT 0,
            pallet_count INTEGER NOT NULL DEFAULT 0, service_requirements TEXT,
            status TEXT NOT NULL DEFAULT 'draft', version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system', updated_by TEXT NOT NULL DEFAULT 'system',
            CHECK (weight_kg >= 0 AND volume_m3 >= 0 AND pallet_count >= 0),
            CHECK (pickup_window_start < pickup_window_end AND delivery_window_start < delivery_window_end)
        )""",
        """CREATE TABLE IF NOT EXISTS freight_units (
            id TEXT PRIMARY KEY, demand_id TEXT NOT NULL UNIQUE REFERENCES transport_demands(id),
            pickup_location_id TEXT NOT NULL REFERENCES locations(id), delivery_location_id TEXT NOT NULL REFERENCES locations(id),
            pickup_window_start TIMESTAMP NOT NULL, pickup_window_end TIMESTAMP NOT NULL,
            delivery_window_start TIMESTAMP NOT NULL, delivery_window_end TIMESTAMP NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL DEFAULT 0, volume_m3 DOUBLE PRECISION NOT NULL DEFAULT 0,
            pallet_count INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'open', version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by TEXT NOT NULL DEFAULT 'system',
            CHECK (weight_kg >= 0 AND volume_m3 >= 0 AND pallet_count >= 0)
        )""",
        """CREATE TABLE IF NOT EXISTS freight_orders (
            id TEXT PRIMARY KEY, pickup_location_id TEXT NOT NULL REFERENCES locations(id),
            delivery_location_id TEXT NOT NULL REFERENCES locations(id),
            pickup_window_start TIMESTAMP NOT NULL, pickup_window_end TIMESTAMP NOT NULL,
            delivery_window_start TIMESTAMP NOT NULL, delivery_window_end TIMESTAMP NOT NULL,
            total_weight_kg DOUBLE PRECISION NOT NULL DEFAULT 0, total_volume_m3 DOUBLE PRECISION NOT NULL DEFAULT 0,
            total_pallet_count INTEGER NOT NULL DEFAULT 0, max_weight_kg DOUBLE PRECISION NOT NULL,
            max_volume_m3 DOUBLE PRECISION NOT NULL, max_pallet_count INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned', version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system', updated_by TEXT NOT NULL DEFAULT 'system',
            CHECK (total_weight_kg >= 0 AND total_volume_m3 >= 0 AND total_pallet_count >= 0),
            CHECK (max_weight_kg >= 0 AND max_volume_m3 >= 0 AND max_pallet_count >= 0)
        )""",
        """CREATE TABLE IF NOT EXISTS freight_order_units (
            freight_order_id TEXT NOT NULL REFERENCES freight_orders(id),
            freight_unit_id TEXT NOT NULL UNIQUE REFERENCES freight_units(id),
            PRIMARY KEY (freight_order_id, freight_unit_id)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_transport_demands_status ON transport_demands(status)",
        "CREATE INDEX IF NOT EXISTS ix_freight_units_status ON freight_units(status)",
        "CREATE INDEX IF NOT EXISTS ix_freight_orders_status ON freight_orders(status)",
    ]


def upgrade_sqlite(connection):
    for sql in statements("sqlite", "upgrade"):
        connection.execute(sql)


def rollback_sqlite(connection):
    for sql in statements("sqlite", "rollback"):
        connection.execute(sql)
