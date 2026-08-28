VERSION = "011_transport_trips"

from sqlalchemy import text


LINEAGE_COLUMNS = {
    "resource_assignments": {
        "trip_id": "TEXT REFERENCES transport_trips(id)",
        "leg_id": "TEXT REFERENCES transport_trip_legs(id)",
    },
    "transport_events": {
        "trip_id": "TEXT REFERENCES transport_trips(id)",
        "leg_id": "TEXT REFERENCES transport_trip_legs(id)",
    },
    "delivery_pod_records": {
        "trip_id": "TEXT REFERENCES transport_trips(id)",
        "leg_id": "TEXT REFERENCES transport_trip_legs(id)",
    },
    "freight_actual_costs": {
        "trip_id": "TEXT REFERENCES transport_trips(id)",
        "leg_id": "TEXT REFERENCES transport_trip_legs(id)",
    },
}


def _trip_tables(identity="SERIAL"):
    return [
        """
        CREATE TABLE IF NOT EXISTS transport_trips (
            id TEXT PRIMARY KEY,
            freight_order_id TEXT NOT NULL REFERENCES freight_orders(id),
            trip_type TEXT NOT NULL DEFAULT 'one_way',
            status TEXT NOT NULL DEFAULT 'draft',
            vehicle_id TEXT REFERENCES vehicles(id),
            driver_id TEXT REFERENCES drivers(id),
            planned_departure_at TIMESTAMP WITH TIME ZONE,
            planned_arrival_at TIMESTAMP WITH TIME ZONE,
            planned_return_at TIMESTAMP WITH TIME ZONE,
            actual_departure_at TIMESTAMP WITH TIME ZONE,
            actual_arrival_at TIMESTAMP WITH TIME ZONE,
            actual_return_at TIMESTAMP WITH TIME ZONE,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_by TEXT NOT NULL DEFAULT 'system',
            CONSTRAINT ck_transport_trip_type CHECK (trip_type IN ('one_way','round_trip','backhaul','multi_stop')),
            CONSTRAINT ck_transport_trip_status CHECK (status IN ('draft','planned','dispatched','in_transit','completed','settled','cancelled')),
            CONSTRAINT ck_transport_trip_version CHECK (version > 0)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS trip_delivery_orders (
            trip_id TEXT NOT NULL REFERENCES transport_trips(id) ON DELETE CASCADE,
            do_id TEXT NOT NULL REFERENCES delivery_orders(id),
            allocation_sequence INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT NOT NULL DEFAULT 'system',
            PRIMARY KEY (trip_id, do_id)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS transport_trip_legs (
            id TEXT PRIMARY KEY,
            trip_id TEXT NOT NULL REFERENCES transport_trips(id) ON DELETE CASCADE,
            do_id TEXT,
            sequence_no INTEGER NOT NULL,
            leg_type TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            distance_km NUMERIC(18,3) NOT NULL DEFAULT 0,
            avg_speed_kmh NUMERIC(18,8) NOT NULL,
            dwell_minutes INTEGER NOT NULL DEFAULT 0,
            planned_departure_at TIMESTAMP WITH TIME ZONE,
            planned_arrival_at TIMESTAMP WITH TIME ZONE,
            actual_departure_at TIMESTAMP WITH TIME ZONE,
            actual_arrival_at TIMESTAMP WITH TIME ZONE,
            status TEXT NOT NULL DEFAULT 'planned',
            allocated_cost NUMERIC(24,6) NOT NULL DEFAULT 0,
            allocated_revenue NUMERIC(24,6) NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_transport_trip_leg_sequence UNIQUE (trip_id, sequence_no),
            CONSTRAINT fk_trip_leg_delivery_order_membership FOREIGN KEY (trip_id, do_id) REFERENCES trip_delivery_orders(trip_id, do_id),
            CONSTRAINT ck_transport_trip_leg_sequence_positive CHECK (sequence_no > 0),
            CONSTRAINT ck_transport_trip_leg_type CHECK (leg_type IN ('outbound','pickup','delivery','empty_return','backhaul','warehouse_transfer')),
            CONSTRAINT ck_transport_trip_leg_status CHECK (status IN ('planned','ready','in_transit','arrived','completed','cancelled')),
            CONSTRAINT ck_transport_trip_leg_metrics CHECK (distance_km >= 0 AND avg_speed_kmh > 0 AND dwell_minutes >= 0)
        )
        """,
    ]


def statements(_dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "DROP INDEX IF EXISTS uq_active_cost_trip",
            "DROP INDEX IF EXISTS uq_legacy_active_cost_freight_order",
            "DROP INDEX IF EXISTS uq_active_assignment_trip",
            "DROP INDEX IF EXISTS uq_legacy_assignment_freight_order",
            "DROP INDEX IF EXISTS uq_trip_delivery_pod_vehicle_stop",
            "DROP INDEX IF EXISTS uq_legacy_delivery_pod_vehicle_stop",
            *[f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}" for table, columns in LINEAGE_COLUMNS.items() for column in columns],
            "DROP TABLE IF EXISTS transport_trip_legs",
            "DROP TABLE IF EXISTS trip_delivery_orders",
            "DROP TABLE IF EXISTS transport_trips",
        ]
    ddl = _trip_tables()
    for table, columns in LINEAGE_COLUMNS.items():
        ddl.extend([f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}" for column, definition in columns.items()])
    ddl.extend([
        "DROP INDEX IF EXISTS uq_active_cost_freight_order",
        "ALTER TABLE resource_assignments DROP CONSTRAINT IF EXISTS resource_assignments_freight_order_id_key",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_legacy_assignment_freight_order ON resource_assignments(freight_order_id) WHERE trip_id IS NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_assignment_trip ON resource_assignments(trip_id) WHERE trip_id IS NOT NULL AND status = 'active'",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_legacy_delivery_pod_vehicle_stop ON delivery_pod_records(do_id, vehicle_id, stop_no) WHERE trip_id IS NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_delivery_pod_vehicle_stop ON delivery_pod_records(trip_id, leg_id, do_id, vehicle_id, stop_no) WHERE trip_id IS NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_legacy_active_cost_freight_order ON freight_actual_costs(freight_order_id) WHERE trip_id IS NULL AND is_active = true",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_cost_trip ON freight_actual_costs(trip_id) WHERE trip_id IS NOT NULL AND is_active = true",
        "CREATE INDEX IF NOT EXISTS ix_transport_trips_order_status ON transport_trips(freight_order_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_transport_trip_legs_trip_sequence ON transport_trip_legs(trip_id, sequence_no)",
    ])
    return ddl


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
            connection.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition.replace(" REFERENCES transport_trips(id)", "").replace(" REFERENCES transport_trip_legs(id)", "")}')


def upgrade_sqlite(connection):
    for sql in _trip_tables("INTEGER PRIMARY KEY AUTOINCREMENT"):
        connection.execute(sql.replace("TIMESTAMP WITH TIME ZONE", "TIMESTAMP"))
    for table, columns in LINEAGE_COLUMNS.items():
        _add_missing_columns(connection, table, columns)
    connection.execute("DROP INDEX IF EXISTS uq_active_cost_freight_order")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_legacy_assignment_freight_order ON resource_assignments(freight_order_id) WHERE trip_id IS NULL")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_active_assignment_trip ON resource_assignments(trip_id) WHERE trip_id IS NOT NULL AND status = 'active'")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_legacy_delivery_pod_vehicle_stop ON delivery_pod_records(do_id, vehicle_id, stop_no) WHERE trip_id IS NULL")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_trip_delivery_pod_vehicle_stop ON delivery_pod_records(trip_id, leg_id, do_id, vehicle_id, stop_no) WHERE trip_id IS NOT NULL")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_legacy_active_cost_freight_order ON freight_actual_costs(freight_order_id) WHERE trip_id IS NULL AND is_active = 1")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_active_cost_trip ON freight_actual_costs(trip_id) WHERE trip_id IS NOT NULL AND is_active = 1")
    connection.execute("CREATE INDEX IF NOT EXISTS ix_transport_trips_order_status ON transport_trips(freight_order_id, status)")
    connection.execute("CREATE INDEX IF NOT EXISTS ix_transport_trip_legs_trip_sequence ON transport_trip_legs(trip_id, sequence_no)")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    for table in ("transport_trip_legs", "trip_delivery_orders", "transport_trips"):
        if _table_exists(connection, table):
            connection.execute(f'DROP TABLE "{table}"')


def validate_sqlite(connection):
    required = {
        "transport_trips": {"id", "freight_order_id", "trip_type", "status", "planned_return_at", "version"},
        "trip_delivery_orders": {"trip_id", "do_id", "allocation_sequence"},
        "transport_trip_legs": {"id", "trip_id", "do_id", "sequence_no", "leg_type", "distance_km", "avg_speed_kmh"},
    }
    for table, columns in required.items():
        if not columns <= _columns(connection, table):
            raise RuntimeError(f"{table} schema mismatch")
    for table, columns in LINEAGE_COLUMNS.items():
        if _table_exists(connection, table) and not set(columns) <= _columns(connection, table):
            raise RuntimeError(f"{table} trip lineage schema mismatch")


def validate_postgresql(connection):
    rows = connection.execute(text(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_name IN ('transport_trips','trip_delivery_orders','transport_trip_legs',
                             'resource_assignments','transport_events','delivery_pod_records','freight_actual_costs')
        """
    ))
    found = {(row[0], row[1]) for row in rows}
    required = {
        "transport_trips": {"id", "freight_order_id", "trip_type", "status", "planned_return_at", "version"},
        "trip_delivery_orders": {"trip_id", "do_id", "allocation_sequence"},
        "transport_trip_legs": {"id", "trip_id", "do_id", "sequence_no", "leg_type", "distance_km", "avg_speed_kmh"},
        **{table: set(columns) for table, columns in LINEAGE_COLUMNS.items()},
    }
    for table, columns in required.items():
        for column in columns:
            if (table, column) not in found:
                raise RuntimeError(f"{table} schema mismatch")
