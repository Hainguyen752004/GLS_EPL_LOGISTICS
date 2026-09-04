import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, TimeoutError

from runtime_state import RuntimeState
from routes import health_routes
from migrations.runner import required_migration_head


REQUIRED = {
    "customers", "routes", "vehicles", "drivers", "quotations",
    "sales_orders", "delivery_orders",
    "transport_demands", "freight_units", "freight_orders", "freight_order_units",
    "carriers", "tenders", "tender_offers",
    "driver_qualifications", "warehouse_appointments", "resource_assignments",
    "transport_events", "transport_event_documents", "freight_order_legacy_links",
    "currency_definitions", "currency_rate_history", "tax_codes", "finance_control_config",
    "freight_actual_costs", "freight_charge_items", "freight_cost_documents",
    "ap_invoices", "ap_invoice_lines", "freight_settlements", "settlement_payments",
    "delivery_pod_records", "delivery_order_closeouts",
    "delivery_order_charge_adjustments", "delivery_pod_documents",
    "transport_trips", "trip_delivery_orders", "transport_trip_legs",
    "driver_shift_assignments", "epl_expense_vouchers",
}


def test_required_migration_head_is_exposed_by_runner():
    assert required_migration_head() == "025_vehicle_depot"


class Checker:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def check(self):
        self.calls += 1
        if self.error:
            raise self.error


def client_for(checker, state=None):
    app = FastAPI()
    app.include_router(health_routes.router)
    app.dependency_overrides[health_routes.get_database_checker] = lambda: checker
    app.dependency_overrides[health_routes.get_runtime_state] = lambda: state or RuntimeState()
    return TestClient(app)


def test_database_health_is_exact_success_after_checker_passes():
    checker = Checker()
    with client_for(checker) as client:
        response = client.get("/api/health/database")
    assert checker.calls == 1
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "postgresql"}


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError("postgresql://user:password@secret/db SELECT 1"), "DATABASE_TIMEOUT"),
        (OperationalError("auth", {}, type("Auth", (Exception,), {"pgcode": "28P01"})()), "DATABASE_AUTH_FAILED"),
        (health_routes.DatabaseSchemaError("missing table customers"), "DATABASE_SCHEMA_INVALID"),
        (RuntimeError("postgresql://user:password@secret/db"), "DATABASE_UNAVAILABLE"),
    ],
)
def test_database_health_failures_are_stable_sanitized_and_correlated(error, code, caplog):
    caplog.set_level(logging.WARNING)
    with client_for(Checker(error)) as client:
        response = client.get("/api/health/database")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == code
    assert detail["message"]
    assert any(ch in detail["message"] for ch in "ăâđêôơư")
    assert detail["correlation_id"] in caplog.text
    combined = response.text + caplog.text
    for secret in ("SELECT 1", "postgresql://", "password", "secret", "user"):
        assert secret not in combined


def test_startup_migration_failure_remains_unready_even_when_checker_passes():
    state = RuntimeState()
    state.record_migration_failure()
    with client_for(Checker(), state) as client:
        response = client.get("/api/health/database")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DATABASE_SCHEMA_INVALID"
    assert state.migration_failed is True


def test_runtime_state_only_explicit_migration_success_clears_failure():
    state = RuntimeState()
    state.record_migration_failure("startup-correlation")
    state.record_database_success()
    assert state.migration_failed is True
    assert state.migration_failure_correlation_id == "startup-correlation"
    state.record_migration_success()
    assert state.migration_failed is False
    assert state.migration_failure_correlation_id is None


def test_startup_failure_correlation_id_is_reused_by_readiness(monkeypatch, caplog):
    import main

    state = RuntimeState()
    secret = "postgresql://secret-user:secret-pass@private-host/epl?token=hidden"
    monkeypatch.setattr(main, "runtime_state", state)
    monkeypatch.setattr(
        main, "auto_migrate_db", lambda: (_ for _ in ()).throw(RuntimeError(secret))
    )
    caplog.set_level(logging.WARNING)

    # Fail-fast là mặc định nên lỗi bật ra ngoài, nhưng correlation id vẫn phải
    # được ghi lại trước đó để probe readiness truy vết bằng đúng một mã.
    with pytest.raises(RuntimeError):
        main.on_startup()
    startup_id = state.migration_failure_correlation_id
    assert startup_id
    with client_for(Checker(), state) as client:
        response = client.get("/api/health/database")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "DATABASE_SCHEMA_INVALID",
        "message": "Lược đồ cơ sở dữ liệu chưa sẵn sàng.",
        "correlation_id": startup_id,
    }
    assert caplog.text.count(startup_id) >= 2
    for value in ("secret-user", "secret-pass", "private-host", "token", "hidden", secret):
        assert value not in caplog.text + response.text


def test_checker_validates_query_migration_head_and_all_required_tables():
    class Result:
        def __init__(self, rows=()): self.rows = rows
        def scalar_one(self): return 1
        def __iter__(self): return iter(self.rows)

    class Connection:
        def __init__(self, versions, tables): self.versions, self.tables, self.sql, self.closed = versions, tables, [], False
        def execute(self, statement):
            assert not self.closed, "readiness queried a closed connection"
            sql = str(statement); self.sql.append(sql)
            if sql == "SELECT 1": return Result()
            if sql == "SELECT version FROM schema_migrations": return Result([(v,) for v in self.versions])
            if "information_schema.columns" in sql:
                if "co_driver_id" in sql:
                    return Result([
                        ("transport_trips", "co_driver_id"),
                        ("resource_assignments", "co_driver_id"),
                    ])
                if "driver_shift_assignments" in sql:
                    if "availability_kind" in sql:
                        return Result([(1,)])
                    required = {"id", "driver_id", "vehicle_id", "trip_id", "shift_type", "shift_start", "shift_end", "status", "version"}
                    rows = [("driver_shift_assignments", column) for column in required]
                    rows.extend([("vehicles", "avg_speed_kmh"), ("vehicle_types", "avg_speed_kmh")])
                    return Result(rows)
                if "delivery_order_closeouts" in sql:
                    rows = []
                    for table, columns in health_routes.v016_delivery_completion_closeout.REQUIRED_COLUMNS.items():
                        for column in columns:
                            data_type = "bytea" if (table, column) == ("delivery_pod_documents", "content") else "numeric" if "amount" in column or "price" in column or "surcharge" in column else "text"
                            rows.append((table, column, data_type))
                    rows.extend(("delivery_pod_records", column, "text") for column in health_routes.v016_delivery_completion_closeout.POD_ADDITIONS)
                    return Result(rows)
                if "transport_trip_legs" in sql and "stop_name" in sql:
                    return Result([(column,) for column in health_routes.v015_trip_stop_recipient.ADDITIONS])
                if "vehicles" in sql and "min_speed_kmh" in sql:
                    return Result([("vehicles", "min_speed_kmh"), ("vehicles", "max_speed_kmh")])
                if "transport_trips" in sql:
                    rows = []
                    rows.extend((table, column) for table, columns in {
                        "transport_trips": {"id", "freight_order_id", "trip_type", "status", "planned_return_at", "version"},
                        "trip_delivery_orders": {"trip_id", "do_id", "allocation_sequence"},
                        "transport_trip_legs": {"id", "trip_id", "do_id", "sequence_no", "leg_type", "distance_km", "avg_speed_kmh"},
                        "resource_assignments": {"trip_id", "leg_id"},
                        "transport_events": {"trip_id", "leg_id"},
                        "delivery_pod_records": {"trip_id", "leg_id"},
                        "freight_actual_costs": {"trip_id", "leg_id"},
                    }.items() for column in columns)
                    return Result(rows)
                if "drivers" in sql and "photo_url" in sql:
                    return Result([("drivers", "photo_url"), ("vehicles", "image_url")])
                if "delivery_pod_records" in sql:
                    return Result(
                        [(table, column) for table, columns in {
                            "delivery_orders": health_routes.v009_delivery_pod_eta.DO_COLUMNS,
                            "vehicle_tracking": health_routes.v009_delivery_pod_eta.TRACKING_COLUMNS,
                            "delivery_pod_records": {
                                "id": None, "do_id": None, "vehicle_id": None, "driver_id": None,
                                "stop_no": None, "delivery_time": None, "photo_url": None,
                                "signature_url": None, "note": None,
                            },
                        }.items() for column in columns]
                    )
                if "quotations" in sql and "sales_orders" in sql and "delivery_orders" in sql:
                    return Result(
                        [(table, column) for table, columns in {
                            "quotations": health_routes.v010_route_context_flow.QUOTE_COLUMNS,
                            "sales_orders": health_routes.v010_route_context_flow.SO_COLUMNS,
                            "delivery_orders": health_routes.v010_route_context_flow.DO_COLUMNS,
                        }.items() for column in columns]
                    )
                if "idempotency_records" in sql:
                    return Result([(table, column)
                                   for table, columns in health_routes.v007_tms_freight_settlement.REQUIRED_COLUMNS.items()
                                   for column in columns])
                types = {"TEXT": "text", "TIMESTAMP": "timestamp without time zone", "DOUBLE PRECISION": "double precision", "INTEGER": "integer"}
                return Result([(table, column, types[meta[0]], "NO" if meta[1] or meta[3] else "YES", meta[2],
                                "YES" if (table, column) == ("transport_event_documents", "id") else "NO")
                               for table, columns in health_routes.v006_tms_execution_events._SQLITE_META.items() for column, meta in columns.items()])
            if "information_schema.table_constraints" in sql:
                if "settlement_payments" in sql:
                    return Result([
                        ("settlement_payments", "amount > 0"),
                        ("settlement_payments", "status IN ('posted','reversed')"),
                        ("settlement_payments", "reversal_of_payment_id IS NULL OR reversal_of_payment_id <> id"),
                    ])
                rows = [
                    ("transport_events", "te_pk", "PRIMARY KEY", "id", "transport_events", "id", None),
                    ("transport_events", "te_uq", "UNIQUE", "freight_order_id,idempotency_key", "transport_events", "freight_order_id,idempotency_key", None),
                    ("transport_events", "te_fk", "FOREIGN KEY", "freight_order_id", "freight_orders", "id", None),
                    ("transport_event_documents", "ted_pk", "PRIMARY KEY", "id", "transport_event_documents", "id", None),
                    ("transport_event_documents", "ted_fk", "FOREIGN KEY", "event_id", "transport_events", "id", None),
                    ("freight_order_legacy_links", "fol_pk", "PRIMARY KEY", "freight_order_id", "freight_order_legacy_links", "freight_order_id", None),
                    ("freight_order_legacy_links", "fol_uq", "UNIQUE", "delivery_order_id", "freight_order_legacy_links", "delivery_order_id", None),
                    ("freight_order_legacy_links", "fol_fk1", "FOREIGN KEY", "freight_order_id", "freight_orders", "id", None),
                    ("freight_order_legacy_links", "fol_fk2", "FOREIGN KEY", "delivery_order_id", "delivery_orders", "id", None),
                ]
                clauses = [
                    "event_type IN ('check_in','pickup','departure','arrival','unloading','delivered','incident','delay','route_deviation')",
                    "source IN ('device','manual')", "lat IS NULL OR lat >= -90 AND lat <= 90",
                    "lng IS NULL OR lng >= -180 AND lng <= 180", "speed_kmh IS NULL OR speed_kmh >= 0",
                    "distance_km IS NULL OR distance_km >= 0",
                ]
                rows.extend(("transport_events", f"te_check_{i}", "CHECK", None, None, None, clause)
                            for i, clause in enumerate(clauses))
                return Result(rows)
            if "pg_constraint" in sql:
                return Result([(name,) for name in health_routes.v016_delivery_completion_closeout.REQUIRED_CONSTRAINTS])
            if "pg_indexes" in sql:
                return Result([
                    ("ix_transport_events_order_time", "CREATE INDEX ON transport_events (freight_order_id, event_time, recorded_at)"),
                    ("ix_transport_event_documents_event", "CREATE INDEX ON transport_event_documents (event_id)"),
                    ("uq_idempotency_scope", "CREATE UNIQUE INDEX uq_idempotency_scope ON idempotency_records (actor, method, path, idempotency_key)"),
                    ("uq_settlement_payment_reversal_of", "CREATE UNIQUE INDEX ON settlement_payments (reversal_of_payment_id)"),
                    ("uq_settlement_payment_reversed_by", "CREATE UNIQUE INDEX ON settlement_payments (reversed_by_payment_id)"),
                    ("uq_active_cost_freight_order", "CREATE UNIQUE INDEX ON freight_actual_costs (freight_order_id) WHERE is_active"),
                    ("uq_active_ap_cost", "CREATE UNIQUE INDEX ON ap_invoices (cost_id) WHERE is_active"),
                ])
            return Result([(t,) for t in self.tables | {"schema_migrations"}])
        def __enter__(self): return self
        def __exit__(self, *_): self.closed = True; return False

    class Engine:
        def __init__(self, connection): self.connection_obj = connection
        def connect(self): return self.connection_obj

    connection = Connection({required_migration_head()}, REQUIRED)
    health_routes.DatabaseReadinessChecker(Engine(connection)).check()
    assert connection.sql[0] == "SELECT 1"

    with pytest.raises(health_routes.DatabaseSchemaError):
        health_routes.DatabaseReadinessChecker(Engine(Connection(set(), REQUIRED))).check()
    with pytest.raises(health_routes.DatabaseSchemaError):
        health_routes.DatabaseReadinessChecker(Engine(Connection({required_migration_head()}, REQUIRED - {"customers"}))).check()


def test_checker_classifies_missing_migration_table_without_querying_it():
    class Result:
        def __init__(self, rows=()): self.rows = rows
        def scalar_one(self): return 1
        def __iter__(self): return iter(self.rows)
    class Connection:
        def __init__(self): self.sql = []
        def execute(self, statement):
            sql = str(statement); self.sql.append(sql)
            if sql == "SELECT 1": return Result()
            return Result([(table,) for table in REQUIRED])
        def __enter__(self): return self
        def __exit__(self, *_): return False
    connection = Connection()
    with pytest.raises(health_routes.DatabaseSchemaError):
        health_routes.DatabaseReadinessChecker(type("Engine", (), {"connect": lambda self: connection})()).check()
    assert "SELECT version FROM schema_migrations" not in connection.sql


def test_checker_rejects_v006_schema_drift(monkeypatch):
    class Result:
        def __init__(self, rows=()): self.rows = rows
        def scalar_one(self): return 1
        def __iter__(self): return iter(self.rows)
    class Connection:
        def execute(self, statement):
            sql = str(statement)
            if sql == "SELECT 1": return Result()
            if sql == "SELECT version FROM schema_migrations": return Result([(required_migration_head(),)])
            return Result([(table,) for table in REQUIRED | {"schema_migrations"}])
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(health_routes.v006_tms_execution_events, "validate_postgresql",
                        lambda _connection: (_ for _ in ()).throw(RuntimeError("drift")))
    with pytest.raises(health_routes.DatabaseSchemaError):
        health_routes.DatabaseReadinessChecker(
            type("Engine", (), {"connect": lambda self: Connection()})()
        ).check()


@pytest.mark.parametrize("original", [
    type("QueryTimeout", (Exception,), {"pgcode": "57014"})(),
    type("SocketTimeout", (Exception,), {"errno": 110})(),
    TimeoutError("pool timed out"),
])
def test_structured_operational_timeouts_are_classified_without_message_matching(original):
    error = OperationalError("safe", {}, original)
    assert health_routes._failure(error)[0] == "DATABASE_TIMEOUT"


def test_arbitrary_programming_error_is_unavailable_not_schema_invalid():
    from sqlalchemy.exc import ProgrammingError
    error = ProgrammingError("SELECT broken", {}, Exception("developer typo"))
    assert health_routes._failure(error)[0] == "DATABASE_UNAVAILABLE"


def test_auto_migrate_delegates_runner_and_clears_state_only_on_success(monkeypatch):
    """Database đã có lịch sử migration thì đi qua upgrade().

    URL truyền cho runner phải lấy từ chính engine, KHÔNG phải DATABASE_URL
    thô: ở chế độ sqlite mà biến đó trống thì engine tự tính đường dẫn, còn
    upgrade("") lại mở một database tạm rồi vứt đi mà không báo lỗi.
    """
    import database
    state = RuntimeState()
    state.record_migration_failure()
    calls = []
    monkeypatch.setattr(database, "_needs_baseline", lambda: False)
    monkeypatch.setattr(database, "upgrade", lambda url, engine=None: calls.append((url, engine)))
    monkeypatch.setattr(database, "runtime_state", state)
    database.auto_migrate_db()
    expected_url = database.engine.url.render_as_string(hide_password=False)
    assert calls == [(expected_url, database.engine)]
    assert state.migration_failed is False

    state.record_migration_failure()
    monkeypatch.setattr(database, "upgrade", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    with pytest.raises(RuntimeError):
        database.auto_migrate_db()
    assert state.migration_failed is True


def test_new_database_is_baselined_instead_of_running_history(monkeypatch):
    """Cài đặt mới: dựng lược đồ từ model rồi đánh mốc, KHÔNG chạy migration cũ.

    Các migration lịch sử là lệnh sửa bảng — v001 ALTER những bảng được giả
    định đã tồn tại, v006 đòi bảng TMS khớp đúng DDL viết tay của nó — nên
    chúng không thể dựng lược đồ trên một database trắng. Đây từng là lý do
    đường khởi tạo mới luôn thất bại và lỗi bị nuốt im lặng.
    """
    import database
    state = RuntimeState()
    state.record_migration_failure()
    upgrades = []
    baselines = []
    created = []

    monkeypatch.setattr(database, "_needs_baseline", lambda: True)
    monkeypatch.setattr(database, "upgrade", lambda *_a, **_k: upgrades.append(1))
    monkeypatch.setattr(database, "runtime_state", state)
    monkeypatch.setattr(database.Base.metadata, "create_all", lambda bind=None: created.append(bind))

    import migrations.runner as runner
    monkeypatch.setattr(runner, "baseline", lambda url, engine=None: baselines.append(url) or ["001", "002"])

    completed = database.auto_migrate_db()

    assert created == [database.engine], "phải dựng lược đồ từ model"
    assert len(baselines) == 1, "phải đánh mốc đúng một lần"
    assert upgrades == [], "KHÔNG được chạy migration lịch sử trên database mới"
    assert completed == ["001", "002"]
    assert state.migration_failed is False
