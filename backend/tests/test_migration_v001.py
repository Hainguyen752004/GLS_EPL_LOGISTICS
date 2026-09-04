import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from migrations.runner import dry_run, rollback, upgrade
from migrations import v001_workflow

EXPECTED_MIGRATIONS = [
    "001_workflow", "002_canonical_status_constraints", "003_tms_core_planning",
    "004_tms_tendering", "005_tms_dispatch_eligibility", "006_tms_execution_events",
    "007_tms_freight_settlement", "008_driver_vehicle_images", "009_delivery_pod_eta",
    "010_route_context_flow", "011_transport_trips", "012_vehicle_speed_profile",
    "013_demo_stabilization", "014_trip_cost_rows", "015_trip_stop_recipient",
    "016_delivery_completion_closeout", "017_driver_shift_turnaround", "018_dispatch_crew",
    "019_driver_availability", "020_epl_expense_vouchers", "021_vehicle_maintenance",
    "022_vehicle_type_capacity", "023_parking_list", "024_money_numeric", "025_vehicle_depot", "026_sales_order_lines", "027_vehicle_cost_overrides", "028_shipping_spec",
]


def _postgres_v006_validation_rows(sql):
    from migrations import v006_tms_execution_events
    from migrations import v007_tms_freight_settlement
    from migrations import v009_delivery_pod_eta
    from migrations import v010_route_context_flow
    from migrations import v011_transport_trips
    from migrations import v012_vehicle_speed_profile
    from migrations import v013_demo_stabilization
    from migrations import v014_trip_cost_rows
    from migrations import v015_trip_stop_recipient
    from migrations import v016_delivery_completion_closeout
    from migrations import v017_driver_shift_turnaround
    if "information_schema.tables" in sql and "parking%" in sql:
        return [("parking_lists",), ("parking_list_items",), ("parking_labels",), ("parking_events",)]
    if "information_schema.columns" in sql and "table_name = 'vehicle_types'" in sql:
        return [("volume_capacity_m3",), ("pallet_capacity",)]
    if "'depot'" in sql and "information_schema.columns" in sql:
        return [("depot",), ("depot_code",)]
    if "table_name = 'vehicles'" in sql and "information_schema.tables" in sql:
        return [(1,)]
    if "information_schema.tables" in sql and "vehicle_maintenance_requests" in sql:
        return [("vehicle_maintenance_requests",), ("vehicle_maintenance_cost_lines",)]
    if "information_schema.tables" in sql and "epl_expense_vouchers" in sql:
        return [(1,)]
    if "information_schema.columns" in sql and "delivery_order_closeouts" in sql:
        rows = [
            (table, column, "bytea" if (table, column) == ("delivery_pod_documents", "content") else "text")
            for table, columns in v016_delivery_completion_closeout.REQUIRED_COLUMNS.items()
            for column in columns
        ]
        rows.extend(
            ("delivery_pod_records", column, "text")
            for column in v016_delivery_completion_closeout.POD_ADDITIONS
        )
        return rows
    if "information_schema.columns" in sql and "driver_shift_assignments" in sql:
        required = {"id", "driver_id", "vehicle_id", "trip_id", "shift_type", "shift_start", "shift_end", "status", "version", "availability_kind"}
        rows = [("driver_shift_assignments", column) for column in required]
        rows.extend([("vehicles", "avg_speed_kmh"), ("vehicle_types", "avg_speed_kmh")])
        return rows
    if "FROM pg_constraint" in sql and "delivery_order_closeouts" in sql:
        return [(name,) for name in v016_delivery_completion_closeout.REQUIRED_CONSTRAINTS]
    if "pg_indexes" in sql:
        return [
            ("ix_transport_events_order_time", "INDEX (freight_order_id, event_time, recorded_at)"),
            ("ix_transport_event_documents_event", "INDEX (event_id)"),
            ("uq_idempotency_scope", "CREATE UNIQUE INDEX uq_idempotency_scope ON idempotency_records (actor, method, path, idempotency_key)"),
            ("uq_settlement_payment_reversal_of", "CREATE UNIQUE INDEX ON settlement_payments (reversal_of_payment_id)"),
            ("uq_settlement_payment_reversed_by", "CREATE UNIQUE INDEX ON settlement_payments (reversed_by_payment_id)"),
            ("uq_active_cost_freight_order", "CREATE UNIQUE INDEX ON freight_actual_costs (freight_order_id) WHERE is_active"),
            ("uq_active_ap_cost", "CREATE UNIQUE INDEX ON ap_invoices (cost_id) WHERE is_active"),
        ]
    if "idempotency_records" in sql:
        rows = []
        for table, columns in v007_tms_freight_settlement.REQUIRED_COLUMNS.items():
            rows.extend((table, column) for column in columns)
        return rows
    if "information_schema.columns" in sql and "drivers" in sql and "photo_url" in sql:
        return [("drivers", "photo_url"), ("vehicles", "image_url")]
    if "information_schema.columns" in sql and "co_driver_id" in sql:
        return [
            ("transport_trips", "co_driver_id"),
            ("resource_assignments", "co_driver_id"),
        ]
    if "information_schema.columns" in sql and "transport_trips" in sql:
        required = {
            "transport_trips": {"id", "freight_order_id", "trip_type", "status", "planned_return_at", "version"},
            "trip_delivery_orders": {"trip_id", "do_id", "allocation_sequence"},
            "transport_trip_legs": {"id", "trip_id", "do_id", "sequence_no", "leg_type", "distance_km", "avg_speed_kmh"},
            **{table: set(columns) for table, columns in v011_transport_trips.LINEAGE_COLUMNS.items()},
        }
        return [(table, column) for table, columns in required.items() for column in columns]
    if "information_schema.columns" in sql and "transport_trip_legs" in sql and "stop_name" in sql:
        return [(column,) for column in v015_trip_stop_recipient.ADDITIONS]
    if "information_schema.columns" in sql and "vehicles" in sql and "min_speed_kmh" in sql:
        return [("vehicles", column) for column in v012_vehicle_speed_profile.VEHICLE_SPEED_COLUMNS]
    if "information_schema.columns" in sql and "assignment_start" in sql and "idempotency_key" in sql:
        rows = [
            ("delivery_orders", column, "timestamp with time zone")
            for column in v013_demo_stabilization.DO_OPERATIONAL_COLUMNS
        ]
        rows.extend([
            ("delivery_pod_records", "delivery_time", "timestamp with time zone"),
            ("delivery_pod_records", "idempotency_key", "character varying"),
            ("resource_assignments", "assignment_start", "timestamp with time zone"),
            ("resource_assignments", "assignment_end", "timestamp with time zone"),
        ])
        return rows
    if "information_schema.columns" in sql and "freight_charge_items" in sql and "original_amount" in sql:
        return [(column,) for column in {
            "original_amount", "actual_amount", "increase_amount", "note"
        }]
    if "information_schema.columns" in sql and "delivery_pod_records" in sql:
        return [(table, column) for table, columns in {
            "delivery_orders": v009_delivery_pod_eta.DO_COLUMNS,
            "vehicle_tracking": v009_delivery_pod_eta.TRACKING_COLUMNS,
            "delivery_pod_records": {
                "id": None, "do_id": None, "vehicle_id": None, "driver_id": None,
                "stop_no": None, "delivery_time": None, "photo_url": None,
                "signature_url": None, "note": None,
            },
        }.items() for column in columns]
    if "information_schema.columns" in sql and "quotations" in sql and "sales_orders" in sql and "delivery_orders" in sql:
        return [(table, column) for table, columns in {
            "quotations": v010_route_context_flow.QUOTE_COLUMNS,
            "sales_orders": v010_route_context_flow.SO_COLUMNS,
            "delivery_orders": v010_route_context_flow.DO_COLUMNS,
        }.items() for column in columns]
    if "information_schema.columns" in sql:
        types = {"TEXT": "text", "TIMESTAMP": "timestamp without time zone", "DOUBLE PRECISION": "double precision", "INTEGER": "integer"}
        return [(table, column, types[meta[0]], "NO" if meta[1] or meta[3] else "YES", meta[2],
                 "YES" if (table, column) == ("transport_event_documents", "id") else "NO")
                for table, columns in v006_tms_execution_events._SQLITE_META.items() for column, meta in columns.items()]
    if "information_schema.table_constraints" in sql:
        if "settlement_payments" in sql:
            return [
                ("settlement_payments", "amount > 0"),
                ("settlement_payments", "status IN ('posted','reversed')"),
                ("settlement_payments", "reversal_of_payment_id IS NULL OR reversal_of_payment_id <> id"),
            ]
        key = lambda table, name, kind, source, target, target_col: (table, name, kind, source, target, target_col, None)
        rows = [
            key("transport_events", "te_pk", "PRIMARY KEY", "id", "transport_events", "id"),
            key("transport_events", "te_uq", "UNIQUE", "freight_order_id,idempotency_key", "transport_events", "freight_order_id,idempotency_key"),
            key("transport_events", "te_fk", "FOREIGN KEY", "freight_order_id", "freight_orders", "id"),
            key("transport_event_documents", "ted_pk", "PRIMARY KEY", "id", "transport_event_documents", "id"),
            key("transport_event_documents", "ted_fk", "FOREIGN KEY", "event_id", "transport_events", "id"),
            key("freight_order_legacy_links", "fol_pk", "PRIMARY KEY", "freight_order_id", "freight_order_legacy_links", "freight_order_id"),
            key("freight_order_legacy_links", "fol_uq", "UNIQUE", "delivery_order_id", "freight_order_legacy_links", "delivery_order_id"),
            key("freight_order_legacy_links", "fol_fk1", "FOREIGN KEY", "freight_order_id", "freight_orders", "id"),
            key("freight_order_legacy_links", "fol_fk2", "FOREIGN KEY", "delivery_order_id", "delivery_orders", "id"),
        ]
        clauses = [
            "event_type IN ('check_in','pickup','departure','arrival','unloading','delivered','incident','delay','route_deviation')",
            "source IN ('device','manual')", "lat IS NULL OR lat >= -90 AND lat <= 90",
            "lng IS NULL OR lng >= -180 AND lng <= 180", "speed_kmh IS NULL OR speed_kmh >= 0",
            "distance_km IS NULL OR distance_km >= 0",
        ]
        rows.extend(("transport_events", f"te_check_{i}", "CHECK", None, None, None, clause)
                    for i, clause in enumerate(clauses))
        return rows
    return None


def _legacy(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
        """
    )
    connection.commit()
    return connection


def _columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def test_upgrade_and_rollback_sqlite_are_recorded_and_idempotent(tmp_path):
    path = tmp_path / "workflow.sqlite3"
    connection = _legacy(path)
    connection.close()

    assert upgrade(str(path)) == EXPECTED_MIGRATIONS
    assert upgrade(str(path)) == []
    with sqlite3.connect(path) as migrated:
        assert migrated.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall() == [(version,) for version in EXPECTED_MIGRATIONS]
        assert "quotation_id" in _columns(migrated, "sales_orders")
        assert "migration_quarantine" in {r[0] for r in migrated.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert rollback(str(path), restore_from="verified-backup") == list(reversed(EXPECTED_MIGRATIONS))
    with sqlite3.connect(path) as reverted:
        assert reverted.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 0
        assert "quotation_id" not in _columns(reverted, "sales_orders")


def test_upgrade_backfills_only_unambiguous_customer_chain(tmp_path):
    path = tmp_path / "valid.sqlite3"
    db = _legacy(path)
    db.executescript(
        """
        INSERT INTO quotations VALUES ('Q1','C1','Approved');
        INSERT INTO sales_orders VALUES ('S1','C1','Confirmed');
        INSERT INTO delivery_orders VALUES ('D1','S1','C1','Completed');
        INSERT INTO ar_invoices VALUES ('I1','D1','C1',100,10,10,110,'Posted');
        INSERT INTO gl_transactions(invoice_id,date,account_code,debit,credit) VALUES ('I1','2026-01-01','131',110,0);
        """
    )
    db.commit(); db.close()

    upgrade(str(path))
    with sqlite3.connect(path) as migrated:
        assert migrated.execute("SELECT quotation_id FROM sales_orders WHERE id='S1'").fetchone() == (None,)
        assert migrated.execute("SELECT reason FROM migration_quarantine").fetchone() == ("unmatched quotation chain",)
        assert migrated.execute("SELECT currency_code,tax_rate_snapshot FROM ar_invoices WHERE id='I1'").fetchone() == ("VND", 10.0)
        assert migrated.execute("SELECT invoice_id FROM journal_batches").fetchall() == [("I1",)]
        assert migrated.execute("SELECT account_code,debit,credit FROM journal_lines").fetchall() == [("131", 110, 0)]


def test_ambiguous_backfill_is_quarantined_as_json(tmp_path):
    path = tmp_path / "ambiguous.sqlite3"
    db = _legacy(path)
    db.executescript("INSERT INTO quotations VALUES ('Q1','C1','Approved'); INSERT INTO quotations VALUES ('Q2','C1','Approved'); INSERT INTO sales_orders VALUES ('S1','C1','Confirmed');")
    db.commit(); db.close()

    upgrade(str(path))
    with sqlite3.connect(path) as migrated:
        assert migrated.execute("SELECT quotation_id FROM sales_orders WHERE id='S1'").fetchone() == (None,)
        payload = migrated.execute("SELECT payload_json FROM migration_quarantine").fetchone()[0]
        assert json.loads(payload)["candidate_ids"] == ["Q1", "Q2"]


def test_chain_constraints_and_new_accounting_tables(tmp_path):
    path = tmp_path / "constraints.sqlite3"
    db = _legacy(path); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as migrated:
        migrated.execute("PRAGMA foreign_keys=ON")
        tables = {r[0] for r in migrated.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"idempotency_records", "accounting_periods", "account_mappings", "journal_batches", "journal_lines"} <= tables
        migrated.execute("INSERT INTO quotations(id,customer_id,status) VALUES ('Q1','C1','approved')")
        migrated.execute("INSERT INTO sales_orders(id,customer_id,status,quotation_id) VALUES ('S1','C1','confirmed','Q1')")
        with pytest.raises(sqlite3.IntegrityError):
            migrated.execute("INSERT INTO sales_orders(id,customer_id,status,quotation_id) VALUES ('S2','C1','confirmed','Q1')")
        migrated.execute("INSERT INTO delivery_orders(id,so_id,customer_id,status) VALUES ('D1','S1','C1','Hoàn thành')")
        with pytest.raises(sqlite3.IntegrityError):
            migrated.execute("INSERT INTO delivery_orders(id,so_id,customer_id,status) VALUES ('D2','S1','C1','Hoàn thành')")
        migrated.execute("INSERT INTO ar_invoices(id,do_id,customer_id,status,is_active) VALUES ('I1','D1','C1','posted',1)")
        with pytest.raises(sqlite3.IntegrityError):
            migrated.execute("INSERT INTO ar_invoices(id,do_id,customer_id,status,is_active) VALUES ('I2','D1','C1','posted',1)")


def test_postgres_dry_run_is_valid_offline_ddl():
    ddl = dry_run("postgresql://ignored/never-connect")
    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in ddl
    assert "CREATE UNIQUE INDEX" in ddl
    assert "WHERE is_active = TRUE" in ddl
    assert "ADD COLUMN IF NOT EXISTS canonical_status TEXT" in ddl
    assert "ADD COLUMN IF NOT EXISTS currency_code TEXT" in ddl
    assert "AUTOINCREMENT" not in ddl
    assert "PRAGMA" not in ddl


def test_cli_dry_run_does_not_create_database(tmp_path):
    path = tmp_path / "never.sqlite3"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "app")
    result = subprocess.run(
        [sys.executable, "-m", "migrations.runner", "upgrade", "--database-url", str(path), "--dry-run"],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True,
        text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert "schema_migrations" in result.stdout
    assert not path.exists()


def test_injected_failure_rolls_back_schema_and_migration_marker(tmp_path):
    path = tmp_path / "atomic.sqlite3"
    db = _legacy(path); db.close()
    with pytest.raises(RuntimeError, match="injected"):
        upgrade(str(path), failure_hook=lambda: (_ for _ in ()).throw(RuntimeError("injected")))
    with sqlite3.connect(path) as connection:
        assert "quotation_id" not in _columns(connection, "sales_orders")
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='schema_migrations'").fetchone() is None


def test_rollback_refuses_populated_new_structures_without_restore_guard(tmp_path):
    path = tmp_path / "guard.sqlite3"
    db = _legacy(path); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO accounting_periods VALUES ('2026-01','2026-01-01','2026-01-31','open',NULL,NULL)")
        connection.commit()
    with pytest.raises(RuntimeError, match="restore-from"):
        rollback(str(path))
    assert rollback(str(path), restore_from="verified-backup") == list(reversed(EXPECTED_MIGRATIONS))


def test_status_mapping_and_audit_backfill_are_controlled(tmp_path):
    path = tmp_path / "status.sqlite3"
    db = _legacy(path)
    db.execute("INSERT INTO sales_orders VALUES ('S1','C1','In Transit')")
    db.commit(); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT canonical_status,created_at,updated_at,created_by,updated_by,version FROM sales_orders").fetchone()
        assert row[0] == "in_transit"
        assert all(value is not None for value in row)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE sales_orders SET canonical_status='anything' WHERE id='S1'")


def test_orm_metadata_contains_migrated_schema():
    import models
    required = {"idempotency_records", "accounting_periods", "account_mappings", "journal_batches", "journal_lines", "migration_quarantine"}
    assert required <= set(models.Base.metadata.tables)
    assert {"quotation_id", "canonical_status", "created_at", "updated_at", "created_by", "updated_by", "version", "currency_code", "exchange_rate_snapshot", "tax_rate_snapshot"} <= set(models.SalesOrder.__table__.columns.keys())


def test_postgres_v001_add_columns_are_idempotent_for_partially_migrated_database():
    from migrations import v001_workflow
    alter_adds = [sql for sql in v001_workflow.statements("postgresql", "upgrade")
                  if sql.startswith("ALTER TABLE") and " ADD COLUMN " in sql]
    assert alter_adds
    assert all(" ADD COLUMN IF NOT EXISTS " in sql for sql in alter_adds)


def test_postgres_upgrade_and_rollback_execute_through_supplied_engine():
    class Connection:
        def __init__(self, applied): self.applied, self.sql = applied, []
        def execute(self, statement, params=None):
            sql = str(statement); self.sql.append(sql)
            validation = _postgres_v006_validation_rows(sql)
            if validation is not None: return validation
            return [(value,) for value in self.applied] if sql.startswith("SELECT version") else []
    class Begin:
        def __init__(self, connection): self.connection = connection
        def __enter__(self): return self.connection
        def __exit__(self, *_args): return False
    class Engine:
        def __init__(self, applied): self.connection = Connection(applied)
        def begin(self): return Begin(self.connection)

    up = Engine(set())
    assert upgrade("postgresql://not-connected/epl", engine=up) == EXPECTED_MIGRATIONS
    assert any("CREATE UNIQUE INDEX" in sql for sql in up.connection.sql)
    assert any(sql.startswith("UPDATE sales_orders s SET quotation_id") for sql in up.connection.sql)
    assert any(sql.startswith("INSERT INTO migration_quarantine") for sql in up.connection.sql)
    assert any(sql.startswith("INSERT INTO journal_lines") for sql in up.connection.sql)
    down = Engine({"001_workflow"})
    assert rollback("postgresql://not-connected/epl", restore_from="verified", engine=down) == ["001_workflow"]
    assert any("DROP COLUMN quotation_id" in sql for sql in down.connection.sql)


def test_postgres_advisory_lock_precedes_migration_read_and_second_runner_is_idempotent():
    import concurrent.futures
    import threading

    class Connection:
        def __init__(self, applied, lock): self.applied, self.lock, self.sql, self.locked = applied, lock, [], False
        def execute(self, statement, params=None):
            sql = str(statement); self.sql.append(sql)
            if "pg_advisory_xact_lock" in sql:
                self.lock.acquire(); self.locked = True
            if sql.startswith("SELECT version"):
                return [(version,) for version in self.applied]
            validation = _postgres_v006_validation_rows(sql)
            if validation is not None:
                return validation
            if sql.startswith("INSERT INTO schema_migrations"):
                self.applied.add(params["version"])
            return []
    class Begin:
        def __init__(self, connection): self.connection = connection
        def __enter__(self): return self.connection
        def __exit__(self, *_):
            if self.connection.locked: self.connection.lock.release()
            return False
    class Engine:
        def __init__(self): self.applied = set(); self.connections = []; self.lock = threading.Lock()
        def begin(self):
            connection = Connection(self.applied, self.lock); self.connections.append(connection)
            return Begin(connection)

    engine = Engine()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda _: upgrade("postgresql://offline/epl", engine=engine), range(2)
        ))
    assert sorted(results, key=len) == [[], EXPECTED_MIGRATIONS]
    for connection in engine.connections:
        lock_at = next(i for i, sql in enumerate(connection.sql) if "pg_advisory_xact_lock" in sql)
        read_at = next(i for i, sql in enumerate(connection.sql) if sql.startswith("SELECT version"))
        assert lock_at < read_at


def test_exact_document_suffix_and_customer_is_valid_backfill_provenance(tmp_path):
    path = tmp_path / "provenance.sqlite3"
    db = _legacy(path)
    db.executescript("INSERT INTO quotations VALUES ('QT-2026-007','C1','Approved'); INSERT INTO sales_orders VALUES ('SO-2026-007','C1','Confirmed');")
    db.commit(); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT quotation_id FROM sales_orders").fetchone() == ("QT-2026-007",)
        assert connection.execute("SELECT COUNT(*) FROM migration_quarantine").fetchone() == (0,)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE sales_orders SET quotation_id='QT-X'",
        "UPDATE sales_orders SET canonical_status='cancelled'",
        "UPDATE sales_orders SET updated_by='human'",
        "UPDATE sales_orders SET version=2",
        "UPDATE sales_orders SET currency_code='USD'",
        "UPDATE sales_orders SET exchange_rate_snapshot=25000",
        "UPDATE sales_orders SET tax_rate_snapshot=7",
        "UPDATE ar_invoices SET reversal_of_invoice_id='I0'",
        "UPDATE ar_invoices SET is_active=0",
    ],
)
def test_rollback_guard_detects_valuable_added_column_values(tmp_path, sql):
    path = tmp_path / "valuable.sqlite3"
    db = _legacy(path)
    db.executescript("INSERT INTO quotations VALUES ('QT-X','C1','Approved'); INSERT INTO sales_orders VALUES ('SO-X','C1','Confirmed'); INSERT INTO delivery_orders VALUES ('D1','SO-X','C1','Completed'); INSERT INTO ar_invoices VALUES ('I0','D1','C1',1,10,0.1,1.1,'Posted'); INSERT INTO ar_invoices VALUES ('I1',NULL,'C1',1,10,0.1,1.1,'Posted');")
    db.commit(); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as connection:
        connection.execute(sql); connection.commit()
    with pytest.raises(RuntimeError, match="restore-from"):
        rollback(str(path))


def test_upgrade_migrates_copy_of_actual_legacy_database(tmp_path):
    source = Path(__file__).resolve().parents[1] / "app" / "epl_logistics.db"
    copy = tmp_path / "actual-copy.sqlite3"
    shutil.copy2(source, copy)
    assert upgrade(str(copy)) == EXPECTED_MIGRATIONS
    with sqlite3.connect(copy) as connection:
        assert "quotation_id" in _columns(connection, "sales_orders")
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_sqlite_rebuild_preserves_user_indexes_and_triggers(tmp_path):
    path = tmp_path / "artifacts.sqlite3"
    db = _legacy(path)
    db.executescript("CREATE TABLE changes(value TEXT); CREATE INDEX user_so_customer ON sales_orders(customer_id); CREATE TRIGGER user_so_insert AFTER INSERT ON sales_orders BEGIN INSERT INTO changes VALUES (NEW.id); END;")
    db.commit(); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as connection:
        artifacts = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('index','trigger')")}
        assert {"user_so_customer", "user_so_insert"} <= artifacts
        connection.execute("INSERT INTO sales_orders(id,customer_id,status) VALUES ('SO-2026-001','C','Draft')")
        assert connection.execute("SELECT value FROM changes").fetchall() == [("SO-2026-001",)]


@pytest.mark.parametrize("url", ["mysql://host/db", "postgres://host/db", "sqltie:///typo.db", "SQLITE:///case.db"])
def test_database_url_rejects_unsupported_typo_and_case_variants(url):
    with pytest.raises(ValueError):
        dry_run(url)


def test_rollback_unmigrated_database_is_noop(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    db = _legacy(path); db.close()
    assert rollback(str(path)) == []


def test_orm_unique_constraints_and_defaults_match_migration():
    import models
    assert models.DeliveryOrder.__table__.c.so_id.unique is True
    active = next(index for index in models.ARInvoice.__table__.indexes if index.name == "uq_active_invoice_do")
    assert active.unique is True
    assert str(active.dialect_options["sqlite"]["where"]) == "ar_invoices.is_active IS true"
    assert models.SalesOrder.__table__.c.canonical_status.default.arg == "draft"
    assert models.DeliveryOrder.__table__.c.canonical_status.default.arg == "pending"
    assert models.ARInvoice.__table__.c.canonical_status.default.arg == "posted"


def test_normalized_suffix_collision_quarantines_all_claiming_orders(tmp_path):
    path = tmp_path / "suffix-collision.sqlite3"
    db = _legacy(path)
    db.executescript("INSERT INTO quotations VALUES ('QT-2026-007','C1','Approved'); INSERT INTO sales_orders VALUES ('SO-2026-007','C1','Confirmed'); INSERT INTO sales_orders VALUES ('SO-2026-7','C1','Confirmed');")
    db.commit(); db.close(); upgrade(str(path))
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT id,quotation_id FROM sales_orders ORDER BY id").fetchall() == [("SO-2026-007", None), ("SO-2026-7", None)]
        assert connection.execute("SELECT entity_id,reason FROM migration_quarantine ORDER BY entity_id").fetchall() == [("SO-2026-007", "quotation provenance collision"), ("SO-2026-7", "quotation provenance collision")]


def test_postgres_provenance_sql_checks_reverse_uniqueness():
    ddl = dry_run("postgresql://ignored/never-connect")
    assert "FROM sales_orders s2" in ddl
    assert "quotation provenance collision" in ddl


def test_unmatched_quarantine_blocks_rollback_without_restore(tmp_path):
    path = tmp_path / "quarantine-guard.sqlite3"
    db = _legacy(path)
    db.execute("INSERT INTO sales_orders VALUES ('SO-NO-PROVENANCE','C1','Confirmed')")
    db.commit(); db.close(); upgrade(str(path))
    with pytest.raises(RuntimeError, match="restore-from"):
        rollback(str(path))
    assert rollback(str(path), restore_from="verified") == list(reversed(EXPECTED_MIGRATIONS))


def test_compact_create_table_identifiers_rebuild_successfully(tmp_path):
    path = tmp_path / "compact.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript("CREATE TABLE quotations(id TEXT PRIMARY KEY,customer_id TEXT,status TEXT); CREATE TABLE sales_orders(id TEXT PRIMARY KEY,customer_id TEXT,status TEXT); CREATE TABLE delivery_orders(id TEXT PRIMARY KEY,so_id TEXT,customer_id TEXT,status TEXT); CREATE TABLE ar_invoices(id TEXT PRIMARY KEY,do_id TEXT,customer_id TEXT,amount REAL,vat_pct REAL,vat_amount REAL,total REAL,status TEXT); CREATE TABLE gl_transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,invoice_id TEXT,date TEXT,account_code TEXT,debit REAL,credit REAL);")
    connection.close()
    assert upgrade(str(path)) == EXPECTED_MIGRATIONS
    with sqlite3.connect(path) as migrated:
        assert "quotation_id" in _columns(migrated, "sales_orders")


@pytest.mark.parametrize(
    ("table", "statuses"),
    [
        ("quotations", ("draft", "sent", "approved", "unknown")),
        ("sales_orders", ("draft", "confirmed", "unknown")),
        ("delivery_orders", ("pending", "in_transit", "delivered", "cancelled")),
    ],
)
def test_fresh_schema_accepts_workflow_canonical_statuses_and_rejects_invalid(tmp_path, table, statuses):
    path = tmp_path / f"fresh-{table}.sqlite3"
    db = _legacy(path); db.close()
    upgrade(str(path))
    with sqlite3.connect(path) as connection:
        for index, status in enumerate(statuses):
            connection.execute(
                f'INSERT INTO "{table}"(id,status,canonical_status) VALUES (?,?,?)',
                (f"{table}-{index}", status, status),
            )
        with pytest.raises(sqlite3.IntegrityError, match="invalid .*canonical_status"):
            connection.execute(
                f'INSERT INTO "{table}"(id,status,canonical_status) VALUES (?,?,?)',
                (f"{table}-invalid", "invented", "invented"),
            )


def test_already_v001_schema_gets_idempotent_status_constraint_repair(tmp_path):
    path = tmp_path / "already-v001.sqlite3"
    connection = _legacy(path)
    connection.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    v001_workflow.upgrade_sqlite(connection)
    connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (v001_workflow.VERSION,))
    connection.commit(); connection.close()

    assert upgrade(str(path)) == EXPECTED_MIGRATIONS[1:]
    assert upgrade(str(path)) == []
    with sqlite3.connect(path) as repaired:
        for status in ("pending", "in_transit", "delivered", "cancelled"):
            repaired.execute(
                "INSERT INTO delivery_orders(id,status,canonical_status) VALUES (?,?,?)",
                (f"DO-{status}", status, status),
            )
        with pytest.raises(sqlite3.IntegrityError, match="invalid .*canonical_status"):
            repaired.execute(
                "INSERT INTO delivery_orders(id,status,canonical_status) VALUES ('DO-bad','bad','bad')"
            )


def test_postgres_status_constraints_are_entity_specific_and_strict():
    ddl = dry_run("postgresql://ignored/never-connect")
    assert "002_canonical_status_constraints" not in ddl
    assert "CHECK (canonical_status IN ('pending','in_transit','delivered','cancelled'))" in ddl
    assert "CHECK (canonical_status IN ('draft','sent','approved','cancelled','unknown'))" in ddl
    assert "DROP CONSTRAINT IF EXISTS ck_delivery_orders_canonical_status" in ddl


def test_delivery_order_default_matches_strict_lifecycle_after_stabilization(tmp_path):
    path = tmp_path / "delivery-default.sqlite3"
    connection = _legacy(path)
    connection.close()

    upgrade(str(path))

    with sqlite3.connect(path) as migrated:
        default = next(
            row[4]
            for row in migrated.execute('PRAGMA table_info("delivery_orders")')
            if row[1] == "canonical_status"
        )
        assert default.strip("'") == "pending"
        migrated.execute(
            "INSERT INTO delivery_orders(id,status) VALUES ('DO-DEFAULT','Chờ vận chuyển')"
        )
        assert migrated.execute(
            "SELECT canonical_status FROM delivery_orders WHERE id='DO-DEFAULT'"
        ).fetchone() == ("pending",)
