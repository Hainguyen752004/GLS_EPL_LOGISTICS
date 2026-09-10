import datetime as dt
import math
import threading
import importlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from database import Base
from models import (
    AuditLog,
    Driver,
    DeliveryOrder,
    FreightOrder,
    FreightOrderLegacyLink,
    Location,
    POD,
    ResourceAssignment,
    TransportEvent,
    TransportEventDocument,
    Vehicle,
    VehicleTracking,
)
from database import get_db
from routes.tms_planning_routes import router
from services.errors import DomainError
from services import tms_execution_service as service


NOW = dt.datetime.utcnow().replace(microsecond=0) - dt.timedelta(hours=1)


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Location(id="A", name="Kho A"),
        Location(id="B", name="Kho B"),
        Vehicle(id="51C-001", type="Truck"),
        Driver(id="DRV-001", name="Tai xe Mot"),
    ])
    # Dia diem vao TRUOC: `FreightOrder` chi khai cot `ForeignKey` tran, khong
    # khai `relationship()`, va SQLAlchemy xep thu tu chen theo relationship —
    # thieu luot nay thi no xep theo ten bang va `freight_orders` di truoc
    # `locations`. SQLite tat khoa ngoai nen chuyen nay an rat lau.
    session.flush()
    session.add(FreightOrder(
        id="FO-EXEC-1", pickup_location_id="A", delivery_location_id="B",
        pickup_window_start=NOW, pickup_window_end=NOW + dt.timedelta(hours=1),
        delivery_window_start=NOW + dt.timedelta(hours=4),
        delivery_window_end=NOW + dt.timedelta(hours=8),
        total_weight_kg=1, total_volume_m3=1, total_pallet_count=1,
        max_weight_kg=2, max_volume_m3=2, max_pallet_count=2,
        status="dispatched", version=2,
    ))
    session.flush()
    session.add(ResourceAssignment(
        freight_order_id="FO-EXEC-1", vehicle_id="51C-001", driver_id="DRV-001",
        assignment_start=NOW - dt.timedelta(hours=1),
        assignment_end=NOW + dt.timedelta(hours=10), status="active",
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def payload(event_type="check_in", version=2, event_time=NOW, **overrides):
    value = {
        "event_type": event_type,
        "event_time": event_time,
        "expected_version": version,
        "vehicle_id": "51C-001",
        "driver_id": "DRV-001",
        "lat": 10.8231,
        "lng": 106.6297,
        "speed_kmh": 0,
        "distance_km": 0,
        "location_text": "Kho A",
        "source": "device",
        "device_id": "GPS-51C-001",
        "reason": None,
        "note": None,
        "documents": [],
    }
    value.update(overrides)
    return value


def assert_error(db, code, data, actor="dispatcher"):
    before = db.get(FreightOrder, "FO-EXEC-1")
    old_state = (before.status, before.version)
    old_audits = db.scalar(select(func.count()).select_from(AuditLog))
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", data, f"key-{code}", actor)
    assert error.value.code == code
    assert any(ch in error.value.message for ch in "ăâđêôơưáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ")
    db.expire_all()
    order = db.get(FreightOrder, "FO-EXEC-1")
    assert (order.status, order.version) == old_state
    assert db.scalar(select(func.count()).select_from(AuditLog)) == old_audits


def record_main_sequence(db, through="unloading"):
    sequence = ["check_in", "pickup", "departure", "arrival", "unloading"]
    version = 2
    for index, event_type in enumerate(sequence):
        service.record_event(
            db, "FO-EXEC-1",
            payload(event_type, version, NOW + dt.timedelta(minutes=index)),
            f"key-{event_type}", "dispatcher",
        )
        version += 1
        if event_type == through:
            break


def test_first_event_requires_dispatched_order_and_active_assignment(db):
    event = service.record_event(db, "FO-EXEC-1", payload(), "key-first", "dispatcher")
    assert event.event_type == "check_in"
    assert event.recorded_by == "dispatcher"
    assert db.get(FreightOrder, "FO-EXEC-1").status == "checked_in"
    assert db.get(FreightOrder, "FO-EXEC-1").version == 3
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1

    assignment = db.scalar(select(ResourceAssignment))
    assignment.status = "inactive"
    db.get(FreightOrder, "FO-EXEC-1").status = "dispatched"
    db.get(FreightOrder, "FO-EXEC-1").version = 2
    db.query(TransportEvent).delete()
    db.query(AuditLog).delete()
    db.flush()
    assert_error(db, "ACTIVE_ASSIGNMENT_REQUIRED", payload())


def test_audit_uses_request_ip_from_session_context(db):
    db.info["audit_ip"] = "203.0.113.17"
    service.record_event(db, "FO-EXEC-1", payload(), "key-audit-ip", "dispatcher")
    audit = db.scalar(select(AuditLog))
    assert audit.ip_address == "203.0.113.17"


def test_same_idempotency_key_and_payload_replays_without_mutation_or_extra_audit(db):
    data = payload()
    original = service.record_event(db, "FO-EXEC-1", data, "key-replay", "dispatcher")
    replay = service.record_event(db, "FO-EXEC-1", data, "key-replay", "dispatcher")
    assert replay.id == original.id
    assert db.get(FreightOrder, "FO-EXEC-1").version == 3
    assert db.scalar(select(func.count()).select_from(TransportEvent)) == 1
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_same_idempotency_key_with_different_payload_is_stable_conflict_and_session_usable(db):
    service.record_event(db, "FO-EXEC-1", payload(), "key-reused", "dispatcher")
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", payload(note="khác"), "key-reused", "dispatcher")
    assert error.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert db.scalar(select(func.count()).select_from(TransportEvent)) == 1
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def _hide_first_idempotency_lookup(db, monkeypatch):
    original_scalar = db.scalar
    lookup_count = 0

    def scalar(statement, *args, **kwargs):
        nonlocal lookup_count
        sql = str(statement)
        if "transport_events" in sql and "idempotency_key" in sql:
            lookup_count += 1
            if lookup_count == 1:
                return None
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(db, "scalar", scalar)
    return lambda: lookup_count


def test_post_lock_idempotency_recheck_replays_newly_visible_same_hash(db, monkeypatch):
    data = payload()
    original = service.record_event(db, "FO-EXEC-1", data, "key-post-lock", "dispatcher")
    lookup_count = _hide_first_idempotency_lookup(db, monkeypatch)
    replay = service.record_event(db, "FO-EXEC-1", data, "key-post-lock", "dispatcher")
    assert replay.id == original.id
    assert lookup_count() >= 2
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_post_lock_idempotency_recheck_rejects_newly_visible_different_hash(db, monkeypatch):
    service.record_event(db, "FO-EXEC-1", payload(), "key-post-lock", "dispatcher")
    lookup_count = _hide_first_idempotency_lookup(db, monkeypatch)
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", payload(note="payload khác"), "key-post-lock", "dispatcher")
    assert error.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert lookup_count() >= 2
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


@pytest.mark.parametrize("data,code", [
    (payload("departure"), "EVENT_SEQUENCE_INVALID"),
    (payload(vehicle_id="51C-999"), "ASSIGNMENT_MISMATCH"),
    (payload(driver_id="DRV-999"), "ASSIGNMENT_MISMATCH"),
    (payload(version=1), "VERSION_CONFLICT"),
])
def test_rejected_transition_does_not_mutate_or_audit(db, data, code):
    assert_error(db, code, data)


@pytest.mark.parametrize("version", [True, 1.0, 0, -1])
def test_expected_version_must_be_a_positive_integer(db, version):
    assert_error(db, "EXPECTED_VERSION_INVALID", payload(version=version))


def test_event_time_must_be_within_active_assignment_inclusively(db):
    assignment = db.scalar(select(ResourceAssignment))
    assignment.assignment_start = NOW
    assignment.assignment_end = NOW
    db.flush()
    event = service.record_event(db, "FO-EXEC-1", payload(event_time=NOW), "key-boundary", "dispatcher")
    assert event.event_time == NOW


def test_event_time_outside_active_assignment_is_rejected(db):
    assignment = db.scalar(select(ResourceAssignment))
    assignment.assignment_start = NOW + dt.timedelta(seconds=1)
    db.flush()
    assert_error(db, "ASSIGNMENT_TIME_INVALID", payload(event_time=NOW))


def test_duplicate_main_event_and_time_regression_are_rejected(db):
    service.record_event(db, "FO-EXEC-1", payload(), "key-first", "dispatcher")
    assert_error(db, "EVENT_ALREADY_RECORDED", payload("check_in", 3, NOW + dt.timedelta(minutes=1)))
    assert_error(db, "EVENT_TIME_REGRESSION", payload("pickup", 3, NOW - dt.timedelta(seconds=1)))


def test_next_transition_requires_order_status_to_match_prior_main_event(db):
    service.record_event(db, "FO-EXEC-1", payload(), "key-first", "dispatcher")
    order = db.get(FreightOrder, "FO-EXEC-1")
    order.status = "dispatched"
    db.flush()
    assert_error(db, "EVENT_SEQUENCE_INVALID", payload("pickup", 3, NOW + dt.timedelta(minutes=1)))


def test_exception_cannot_precede_latest_main_event(db):
    service.record_event(db, "FO-EXEC-1", payload(), "key-first", "dispatcher")
    assert_error(
        db, "EVENT_TIME_REGRESSION",
        payload("incident", 3, NOW - dt.timedelta(seconds=1), reason="Sự cố đến muộn"),
    )


def test_exception_requires_active_execution_and_reason_without_advancing_state(db):
    event = service.record_event(
        db, "FO-EXEC-1", payload("incident", reason="Lốp xe bị hỏng"), "key-incident", "dispatcher"
    )
    order = db.get(FreightOrder, "FO-EXEC-1")
    assert event.event_type == "incident"
    assert (order.status, order.version) == ("dispatched", 2)
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1
    assert_error(db, "EVENT_REASON_REQUIRED", payload("delay", reason=""))
    order.status = "delivered"
    db.flush()
    assert_error(db, "FREIGHT_ORDER_NOT_EXECUTING", payload("route_deviation", reason="Đi sai tuyến"))


def test_manual_source_uses_trusted_actor_and_requires_actor(db):
    event = service.record_event(
        db, "FO-EXEC-1", payload(source="manual", device_id=None, reason="Nhập tại cổng"),
        "key-manual", "trusted-principal",
    )
    assert event.recorded_by == "trusted-principal"
    assert_error(db, "ACTOR_REQUIRED", payload("pickup", 3, source="manual", device_id=None), actor="")


@pytest.mark.parametrize("field,value", [
    ("lat", math.nan), ("lat", math.inf), ("lat", -91), ("lat", 91),
    ("lng", math.nan), ("lng", -181), ("lng", 181),
])
def test_coordinate_validation_rejects_non_finite_or_out_of_range(db, field, value):
    assert_error(db, "COORDINATE_INVALID", payload(**{field: value}))


@pytest.mark.parametrize("field", ["speed_kmh", "distance_km"])
def test_gps_validation_rejects_negative_measurements(db, field):
    assert_error(db, "GPS_VALUE_INVALID", payload(**{field: -0.01}))


@pytest.mark.parametrize("field,code", [
    ("lat", "COORDINATE_INVALID"), ("lng", "COORDINATE_INVALID"),
    ("speed_kmh", "GPS_VALUE_INVALID"), ("distance_km", "GPS_VALUE_INVALID"),
])
def test_gps_values_reject_boolean_inputs(db, field, code):
    assert_error(db, code, payload(**{field: True}))


def test_source_validation_requires_device_id(db):
    assert_error(db, "DEVICE_ID_REQUIRED", payload(device_id=""))


def test_future_event_validation_uses_configured_tolerance(db, monkeypatch):
    monkeypatch.setenv("TMS_EVENT_FUTURE_TOLERANCE_SECONDS", "300")
    assert_error(db, "EVENT_TIME_FUTURE", payload(event_time=dt.datetime.utcnow() + dt.timedelta(seconds=301)))


def test_malformed_future_tolerance_uses_safe_default(db, monkeypatch):
    monkeypatch.setenv("TMS_EVENT_FUTURE_TOLERANCE_SECONDS", "not-an-integer")
    event = service.record_event(db, "FO-EXEC-1", payload(), "key-safe-config", "dispatcher")
    assert event.event_type == "check_in"


@pytest.mark.parametrize("documents", [
    [{"document_type": "photo", "storage_url": "", "checksum": "sha256:x"}],
    [{"document_type": "photo", "storage_url": "https://store/photo.jpg", "checksum": ""}],
    [{"storage_url": "https://store/photo.jpg", "checksum": "sha256:x"}],
])
def test_every_event_document_requires_type_url_and_checksum(db, documents):
    assert_error(db, "EVENT_DOCUMENT_INVALID", payload(documents=documents))


@pytest.mark.parametrize("documents", [{}, "", 0, False])
def test_falsey_non_list_document_shapes_are_rejected(db, documents):
    assert_error(db, "EVENT_DOCUMENT_INVALID", payload(documents=documents))


def test_extra_malformed_document_invalidates_delivered_even_with_valid_pod(db):
    record_main_sequence(db)
    documents = [
        {"document_type": "pod", "storage_url": "https://store/pod.jpg", "checksum": "sha256:pod"},
        {"document_type": "photo", "storage_url": "", "checksum": "sha256:photo"},
    ]
    assert_error(
        db, "EVENT_DOCUMENT_INVALID",
        payload("delivered", 7, NOW + dt.timedelta(minutes=6), documents=documents),
    )


@pytest.mark.parametrize("document", [
    None,
    {"document_type": "pod", "storage_url": "", "checksum": "sha256:x"},
    {"document_type": "pod", "storage_url": "https://store/pod.jpg", "checksum": ""},
])
def test_delivered_requires_valid_pod_document(db, document):
    record_main_sequence(db)
    documents = [] if document is None else [document]
    assert_error(
        db, "POD_DOCUMENT_REQUIRED",
        payload("delivered", 7, NOW + dt.timedelta(minutes=6), documents=documents),
    )


def test_delivered_persists_pod_metadata_and_advances_state_once(db):
    record_main_sequence(db)
    event = service.record_event(db, "FO-EXEC-1", payload(
        "delivered", 7, NOW + dt.timedelta(minutes=6),
        documents=[{
            "document_type": "pod", "storage_url": "https://store/pod.jpg",
            "file_name": "pod.jpg", "mime_type": "image/jpeg", "checksum": "sha256:abc",
        }],
    ), "key-delivered", "dispatcher")
    assert db.get(FreightOrder, "FO-EXEC-1").status == "delivered"
    assert db.get(FreightOrder, "FO-EXEC-1").version == 8
    document = db.scalar(select(TransportEventDocument).where(TransportEventDocument.event_id == event.id))
    assert document.storage_url == "https://store/pod.jpg"
    assert document.uploaded_by == "dispatcher"
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 6


def test_list_events_is_stably_ordered(db):
    service.record_event(db, "FO-EXEC-1", payload("incident", event_time=NOW, reason="Sự cố"), "key-z", "dispatcher")
    service.record_event(db, "FO-EXEC-1", payload("check_in", event_time=NOW), "key-a", "dispatcher")
    events = service.list_events(db, "FO-EXEC-1")
    assert [event.id for event in events] == sorted(
        [event.id for event in events], key=lambda event_id: next(
            (event.event_time, event.recorded_at, event.id) for event in events if event.id == event_id
        )
    )


def test_link_legacy_delivery_order_writes_audit_with_actor_and_ip(db):
    # LENH GIAO HANG PHAI CO THAT.
    #
    # Ban truoc noi thang `FO-EXEC-1` voi `DO-LEGACY-1` ma khong tao lenh giao
    # hang nao — mot lien ket tro vao chỗ trống. Chay duoc tren SQLite vi khoa
    # ngoai bi tat; `freight_order_legacy_links_delivery_order_id_fkey` tren
    # PostgreSQL tu choi.
    #
    # Va PostgreSQL dung: mot lien ket "don cu" tro vao mot don khong ton tai
    # thi khong bat che gi. Rang buoc do la phep kiem duy nhat dang bao ve
    # `link_legacy_delivery_order` — ham do khong tu kiem lenh giao hang co that
    # hay khong.
    from models import DeliveryOrder
    db.add(DeliveryOrder(id="DO-LEGACY-1", customer_id=None,
                         canonical_status="pending", status="Cho van chuyen"))
    db.flush()

    db.info["audit_ip"] = "198.51.100.8"
    link = service.link_legacy_delivery_order(db, "FO-EXEC-1", "DO-LEGACY-1", "integrator")
    assert isinstance(link, FreightOrderLegacyLink)
    audit = db.scalar(select(AuditLog))
    assert (audit.user_id, audit.ip_address) == ("integrator", "198.51.100.8")
    assert (audit.action, audit.table_name, audit.record_id) == (
        "LINK_LEGACY_DELIVERY_ORDER", "freight_order_legacy_links", "FO-EXEC-1"
    )


def test_transition_lock_compiles_to_postgresql_for_update():
    sql = str(service.freight_order_for_update("FO-1").compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    ))
    assert "FOR UPDATE" in sql


def test_projection_requires_explicit_legacy_link(db):
    service.record_event(db, "FO-EXEC-1", payload(), "key-no-link", "dispatcher")
    assert db.scalar(select(func.count()).select_from(VehicleTracking)) == 0
    assert service.latest_position(db, "FO-EXEC-1").lat == 10.8231


def test_linked_event_projects_tracking_eta_after_event_flush(db):
    db.add(DeliveryOrder(id="DO-LEGACY-1"))
    db.flush()
    service.link_legacy_delivery_order(db, "FO-EXEC-1", "DO-LEGACY-1", "integrator")
    service.record_event(db, "FO-EXEC-1", payload(distance_km=12.5, eta="2026-08-11T12:30:00"), "key-projection", "dispatcher")
    tracking = db.get(VehicleTracking, "DO-LEGACY-1")
    assert (tracking.vehicle_id, tracking.lat, tracking.remaining_distance_km) == ("51C-001", 10.8231, 12.5)
    assert tracking.last_update == NOW
    assert tracking.eta == "2026-08-11T12:30:00"
    db.expire_all()
    persisted = db.scalar(select(TransportEvent).where(TransportEvent.idempotency_key == "key-projection"))
    assert persisted.eta == "2026-08-11T12:30:00"
    db.delete(db.get(VehicleTracking, "DO-LEGACY-1"))
    db.flush()
    assignment = db.scalar(select(ResourceAssignment))
    service._project_legacy(db, persisted, assignment, [])
    db.flush()
    assert db.get(VehicleTracking, "DO-LEGACY-1").eta == "2026-08-11T12:30:00"


@pytest.mark.parametrize("key", ["", "   "])
def test_idempotency_key_must_be_nonblank(db, key):
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", payload(), key, "dispatcher")
    assert (error.value.code, error.value.status_code) == ("IDEMPOTENCY_KEY_REQUIRED", 422)
    assert "khóa" in error.value.message.lower()


def test_linked_delivered_event_does_not_dual_write_legacy_pod(db):
    db.add(DeliveryOrder(id="DO-LEGACY-1"))
    db.flush()
    service.link_legacy_delivery_order(db, "FO-EXEC-1", "DO-LEGACY-1", "integrator")
    record_main_sequence(db)
    service.record_event(db, "FO-EXEC-1", payload(
        "delivered", 7, NOW + dt.timedelta(minutes=6), note="Giao đủ",
        documents=[{"document_type": "pod", "storage_url": "https://store/pod.jpg", "checksum": "sha256:pod"}],
    ), "key-pod-projection", "dispatcher")
    assert db.get(POD, "DO-LEGACY-1") is None


def test_projection_failure_rolls_back_whole_command(db, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("projection failed")
    monkeypatch.setattr(service, "_project_legacy", fail)
    with pytest.raises(RuntimeError):
        service.record_event(db, "FO-EXEC-1", payload(), "key-rollback", "dispatcher")
        db.commit()
    db.rollback()
    assert db.scalar(select(func.count()).select_from(TransportEvent)) == 0
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 0
    assert (db.get(FreightOrder, "FO-EXEC-1").status, db.get(FreightOrder, "FO-EXEC-1").version) == ("dispatched", 2)


def test_delivered_projection_failure_rolls_back_document_tracking_and_pod(db, monkeypatch):
    db.add(DeliveryOrder(id="DO-LEGACY-1"))
    db.flush()
    service.link_legacy_delivery_order(db, "FO-EXEC-1", "DO-LEGACY-1", "integrator")
    record_main_sequence(db)
    db.commit()
    baseline_events = db.scalar(select(func.count()).select_from(TransportEvent))
    baseline_audits = db.scalar(select(func.count()).select_from(AuditLog))
    baseline_tracking_time = db.get(VehicleTracking, "DO-LEGACY-1").last_update
    original = service._project_legacy
    def fail_after_projection(*args, **kwargs):
        original(*args, **kwargs)
        args[0].flush()
        raise RuntimeError("forced after all projections")
    monkeypatch.setattr(service, "_project_legacy", fail_after_projection)
    with pytest.raises(RuntimeError):
        service.record_event(db, "FO-EXEC-1", payload(
            "delivered", 7, NOW + dt.timedelta(minutes=6),
            documents=[{"document_type": "pod", "storage_url": "https://store/pod.jpg", "checksum": "sha256:pod"}],
        ), "key-atomic-delivery", "dispatcher")
    db.rollback()
    assert db.scalar(select(func.count()).select_from(TransportEvent)) == baseline_events
    assert db.scalar(select(func.count()).select_from(TransportEventDocument)) == 0
    assert db.get(VehicleTracking, "DO-LEGACY-1").last_update == baseline_tracking_time
    assert db.get(POD, "DO-LEGACY-1") is None
    assert db.scalar(select(func.count()).select_from(AuditLog)) == baseline_audits
    assert (db.get(FreightOrder, "FO-EXEC-1").status, db.get(FreightOrder, "FO-EXEC-1").version) == ("unloading", 7)


def test_sqlite_concurrent_different_keys_allow_one_transition_and_reject_stale_version(db):
    sessions = sessionmaker(bind=db.get_bind())
    barrier = threading.Barrier(2)
    outcomes = []
    def write(key):
        session = sessions()
        try:
            barrier.wait()
            service.record_event(session, "FO-EXEC-1", payload(), key, "dispatcher")
            session.commit()
            outcomes.append("success")
        except DomainError as error:
            session.rollback()
            outcomes.append(error.code)
        finally:
            session.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, key) for key in ("writer-one", "writer-two")]
        for future in futures:
            future.result()
    db.expire_all()
    assert sorted(outcomes) == ["VERSION_CONFLICT", "success"]
    assert db.scalar(select(func.count()).select_from(TransportEvent)) == 1
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_sqlite_concurrent_same_key_has_one_event_and_audit_with_replay(db):
    sessions = sessionmaker(bind=db.get_bind())
    barrier = threading.Barrier(2)
    results = []
    def write():
        session = sessions()
        try:
            barrier.wait()
            event = service.record_event(session, "FO-EXEC-1", payload(), "same-concurrent-key", "dispatcher")
            session.commit()
            results.append(event.id)
        finally:
            session.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write) for _ in range(2)]
        for future in futures:
            future.result()
    db.expire_all()
    assert len(set(results)) == 1
    assert db.scalar(select(func.count()).select_from(TransportEvent)) == 1
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


@pytest.fixture
def api_client(db):
    app = FastAPI()
    @app.middleware("http")
    async def trusted_principal(request: Request, call_next):
        request.state.principal = "trusted-user"
        return await call_next(request)
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client


def test_api_event_contract_and_trusted_actor(api_client, db):
    missing = api_client.post("/api/tms/freight-orders/FO-EXEC-1/events", json={})
    assert missing.status_code == 422
    assert missing.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    response = api_client.post(
        "/api/tms/freight-orders/FO-EXEC-1/events", json={**payload(), "event_time": NOW.isoformat()},
        headers={"Idempotency-Key": "api-key", "X-User-Id": "spoofed"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Đã ghi nhận sự kiện vận tải."
    assert response.json()["data"]["recorded_by"] == "trusted-user"
    assert db.scalar(select(AuditLog)).user_id == "trusted-user"
    history = api_client.get("/api/tms/freight-orders/FO-EXEC-1/events")
    assert history.status_code == 200 and history.json()["data"][0]["event_type"] == "check_in"
    position = api_client.get("/api/tms/freight-orders/FO-EXEC-1/latest-position")
    assert position.status_code == 200 and position.json()["data"]["lat"] == 10.8231


def test_api_blank_idempotency_key_has_stable_vietnamese_error(api_client):
    response = api_client.post("/api/tms/freight-orders/FO-EXEC-1/events", json={**payload(), "event_time": NOW.isoformat()}, headers={"Idempotency-Key": " "})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert "khóa" in response.json()["detail"]["message"].lower()


def test_api_latest_position_not_found_is_stable_404(api_client):
    response = api_client.get("/api/tms/freight-orders/FO-EXEC-1/latest-position")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "POSITION_NOT_FOUND"


def test_api_idempotency_reuse_is_exact_409_without_secret_leak(api_client):
    body = {**payload(), "event_time": NOW.isoformat()}
    assert api_client.post("/api/tms/freight-orders/FO-EXEC-1/events", json=body, headers={"Idempotency-Key": "reuse"}).status_code == 200
    response = api_client.post(
        "/api/tms/freight-orders/FO-EXEC-1/events", json={**body, "note": "changed"},
        headers={"Idempotency-Key": "reuse"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    rendered = response.text.lower()
    assert "postgresql://" not in rendered and "select " not in rendered and "traceback" not in rendered


def test_api_history_is_ordered_by_event_time(api_client):
    later = {**payload("incident", event_time=NOW + dt.timedelta(minutes=1), reason="Trễ"), "event_time": (NOW + dt.timedelta(minutes=1)).isoformat()}
    earlier = {**payload("check_in", event_time=NOW), "event_time": NOW.isoformat()}
    assert api_client.post("/api/tms/freight-orders/FO-EXEC-1/events", json=later, headers={"Idempotency-Key": "later"}).status_code == 200
    assert api_client.post("/api/tms/freight-orders/FO-EXEC-1/events", json=earlier, headers={"Idempotency-Key": "earlier"}).status_code == 200
    response = api_client.get("/api/tms/freight-orders/FO-EXEC-1/events")
    assert [item["event_type"] for item in response.json()["data"]] == ["check_in", "incident"]


def test_api_normalizes_integrity_error_without_database_details(api_client, monkeypatch):
    def fail(*args, **kwargs):
        raise IntegrityError("INSERT secret", {"url": "postgresql://user:pass@db/epl"}, Exception("constraint"))
    monkeypatch.setattr(service, "record_event", fail)
    response = api_client.post(
        "/api/tms/freight-orders/FO-EXEC-1/events", json={}, headers={"Idempotency-Key": "integrity"}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EXECUTION_CONFLICT"
    assert "postgresql://" not in response.text.lower() and "insert secret" not in response.text.lower()


def test_api_has_no_event_mutation_routes():
    event_paths = [route for route in router.routes if route.path.endswith("/events")]
    assert {method for route in event_paths for method in route.methods} == {"GET", "POST"}


def test_all_execution_endpoints_require_trusted_principal(db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        calls = [
            client.get("/api/tms/freight-orders/FO-EXEC-1/events"),
            client.post("/api/tms/freight-orders/FO-EXEC-1/events", json={}, headers={"Idempotency-Key": "key"}),
            client.get("/api/tms/freight-orders/FO-EXEC-1/latest-position"),
            client.post("/api/tms/freight-orders/FO-EXEC-1/legacy-link", json={"delivery_order_id": "DO-1"}),
        ]
    for response in calls:
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
        assert "đăng nhập" in response.json()["detail"]["message"].lower()


def test_production_app_bearer_auth_allows_valid_token_only(db, monkeypatch):
    """Khi cong kiem token duoc BAT, chi dung token moi qua duoc.

    Cong nay mac dinh TAT vi he thong la mot module ben trong he thong lon hon
    va viec dang nhap do he thong cha lo (xem auth_middleware). Test nay bat co
    len de kiem chinh che do chan, nen no van la bang chung rang lop chan con
    nguyen ven khi trien khai doc lap.
    """
    monkeypatch.setenv("EPL_TMS_API_TOKEN", "top-secret-token")
    monkeypatch.setenv("EPL_TMS_API_PRINCIPAL", "production-tms")
    monkeypatch.setenv("EPL_REQUIRE_API_TOKEN", "1")
    main = importlib.import_module("main")
    current_database = importlib.import_module("database")
    main.app.dependency_overrides[current_database.get_db] = lambda: db
    try:
        client = TestClient(main.app)
        valid = client.get(
            "/api/tms/freight-orders/FO-EXEC-1/events",
            headers={"Authorization": "Bearer top-secret-token"},
        )
        invalid = client.get(
            "/api/tms/freight-orders/FO-EXEC-1/events",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert valid.status_code == 200
        assert invalid.status_code == 401
        assert invalid.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    finally:
        main.app.dependency_overrides.clear()


@pytest.mark.parametrize("body", [
    {}, {"delivery_order_id": ""}, {"delivery_order_id": "   "},
    {"delivery_order_id": "x" * 129}, {"delivery_order_id": 123},
    {"delivery_order_id": "DO-1", "extra": True},
])
def test_legacy_link_body_is_exact_and_bounded(api_client, body):
    response = api_client.post("/api/tms/freight-orders/FO-EXEC-1/legacy-link", json=body)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "LEGACY_LINK_PAYLOAD_INVALID"
    assert "không hợp lệ" in response.json()["detail"]["message"].lower()


@pytest.mark.parametrize("field,value", [
    ("event_type", "x" * 65), ("source", "x" * 33), ("device_id", "x" * 129),
    ("location_text", "x" * 501), ("eta", "not-a-date"), ("reason", "x" * 2001),
    ("note", "x" * 4001), ("unexpected", "value"),
])
def test_event_payload_shape_and_lengths_have_stable_validation(db, field, value):
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", payload(**{field: value}), "bounded-key", "dispatcher")
    assert (error.value.code, error.value.status_code) == ("EVENT_PAYLOAD_INVALID", 422)
    assert "không hợp lệ" in error.value.message.lower()


def test_idempotency_key_max_length_is_enforced(db):
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", payload(), "k" * 129, "dispatcher")
    assert error.value.code == "IDEMPOTENCY_KEY_INVALID"


@pytest.mark.parametrize("documents", [
    [{"document_type": "pod", "storage_url": "https://x", "checksum": "x"}] * 11,
    [{"document_type": "x" * 65, "storage_url": "https://x", "checksum": "x"}],
    [{"document_type": "pod", "storage_url": "x" * 2049, "checksum": "x"}],
    [{"document_type": "pod", "storage_url": "https://x", "file_name": "x" * 256, "checksum": "x"}],
    [{"document_type": "pod", "storage_url": "https://x", "mime_type": "x" * 129, "checksum": "x"}],
    [{"document_type": "pod", "storage_url": "https://x", "checksum": "x" * 129}],
    [{"document_type": "pod", "storage_url": "https://x", "checksum": "x", "extra": 1}],
])
def test_document_bounds_and_extra_fields_are_rejected(db, documents):
    with pytest.raises(DomainError) as error:
        service.record_event(db, "FO-EXEC-1", payload(documents=documents), "document-bounds", "dispatcher")
    assert error.value.code == "EVENT_DOCUMENT_INVALID"
