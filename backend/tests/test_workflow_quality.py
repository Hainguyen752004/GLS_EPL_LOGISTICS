import sqlite3
import json
from types import SimpleNamespace
import pytest

from services.errors import DomainError
from routes.workflow_routes import _execute
from models import IdempotencyRecord
from conftest import (bao_gia_hop_le, dieu_phoi_qua_chuyen, ket_noi_du_lieu,
                      san_sang_dieu_phoi)


def _khung_gio_va_trip(client, do_id, ma_trip):
    """Dat khung gio cho mot lenh roi LAP CHUYEN cho no, chua dieu xe.

    Dung cho phep do tranh chap: hai chuyen cung xin mot xe trong cung khung gio.
    """
    import datetime as _dt
    import importlib as _importlib
    database = _importlib.import_module("database")
    models = _importlib.import_module("models")
    dau = _dt.datetime(2026, 8, 12, 1, 0, tzinfo=_dt.timezone.utc)
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        do.pickup_window_start = dau
        do.pickup_window_end = dau + _dt.timedelta(hours=3)
        do.delivery_window_start = dau + _dt.timedelta(hours=3)
        do.delivery_window_end = dau + _dt.timedelta(hours=12)
        db.commit()
    san_sang_dieu_phoi(client, do_id)
    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": ma_trip, "do_ids": [do_id], "trip_type": "one_way",
        "planned_departure_at": dau.isoformat(), "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={"Idempotency-Key": f"lap-{ma_trip}"})
    assert r.status_code in (200, 201), r.text
    return ma_trip


def _audit_rows(path, record_id):
    with ket_noi_du_lieu(path) as connection:
        return connection.execute("SELECT user_id, ip_address, action FROM audit_logs WHERE record_id=? ORDER BY id", (record_id,)).fetchall()


def test_spoofed_actor_header_is_ignored_and_client_ip_is_audited(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.customer(); workflow_builder.route()
    response = client.post("/api/quotations", json=bao_gia_hop_le(id="QT-ACTOR"), headers={"X-User-Id": "spoofed"})
    assert response.status_code == 200
    assert response.json()["data"]["created_by"] == "test-user"
    user, ip, action = _audit_rows(database_file, "QT-ACTOR")[-1]
    assert user == "test-user"
    assert ip and ip != "127.0.0.1"


def test_create_idempotency_replays_and_payload_mismatch_conflicts(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.customer(); workflow_builder.route()
    headers = {"Idempotency-Key": "create-one"}
    payload = {"id": "QT-IDEM", "customer_id": "CUS-T1", "route_id": "RT-T1", "selling_price": 10}
    first = client.post("/api/quotations", json=payload, headers=headers)
    retry = client.post("/api/quotations", json=payload, headers=headers)
    conflict = client.post("/api/quotations", json={**payload, "selling_price": 11}, headers=headers)
    assert retry.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert len(_audit_rows(database_file, "QT-IDEM")) == 1


def test_dispatch_retries_are_idempotent(app_client, workflow_builder):
    """Bam dieu phoi hai lan chi ghi MOT lan — do tren duong CHUYEN.

    Truoc day bai nay do tren `PUT /api/delivery-orders/{id}/dispatch`. Duong do
    da dong phan ghi (no khong lap chuyen nen lenh di qua no khong co duong ra),
    va dieu phoi that di qua chuyen — nen phep do phai chuyen theo.
    """
    client, database_file, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-I", approve=True)
    workflow_builder.delivery_order("DO-I", "QT-I", approve=True)
    ma_trip = dieu_phoi_qua_chuyen(client, "DO-I")

    # Dieu phoi lai chinh chuyen do: bi tu choi vi chuyen khong con `planned`.
    tra = client.get(f"/api/tms/trips/{ma_trip}")
    pb = int((tra.json()["data"] or {}).get("version") or 1)
    lai = client.put(f"/api/tms/trips/{ma_trip}/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": pb,
        "assignment_start": "2026-08-12T01:00:00+00:00",
        "assignment_end": "2026-08-12T13:00:00+00:00",
    })
    assert lai.status_code == 409, lai.text
    assert lai.json()["detail"]["code"] == "INVALID_TRANSITION"

    # Va chi co MOT phan cong dang mo cho chuyen do.
    import importlib as _importlib
    database = _importlib.import_module("database")
    models = _importlib.import_module("models")
    with database.SessionLocal() as db:
        so_phan_cong = db.query(models.ResourceAssignment).filter(
            models.ResourceAssignment.trip_id == ma_trip,
            models.ResourceAssignment.status == "active",
        ).count()
    assert so_phan_cong == 1


def test_duplicate_id_and_invalid_financial_values_are_stable(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.customer(); workflow_builder.route()
    payload = {"id": "QT-DUP", "customer_id": "CUS-T1", "route_id": "RT-T1"}
    assert client.post("/api/quotations", json=payload).status_code == 200
    duplicate = client.post("/api/quotations", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "DUPLICATE_RECORD"
    for value in (-1, "nan", "Infinity", "bad"):
        response = client.post("/api/quotations", json={**payload, "id": f"QT-{value}", "selling_price": value})
        assert response.status_code == 422
        assert response.json()["error"]["code"] in {"INVALID_VALUE", "VALIDATION_ERROR"}
    assert client.post("/api/quotations", json=[]).status_code == 422


def test_sequential_sqlite_resource_guard_has_one_winner_and_one_audit(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.master_data()
    for suffix in ("A", "B"):
        workflow_builder.quotation(f"QT-{suffix}", approve=True)
        workflow_builder.delivery_order(f"DO-{suffix}", f"QT-{suffix}", approve=True)
    # Hai chuyen, CUNG mot xe va cung mot to lai, CUNG khung gio: chi mot ben
    # thang. Cua chan la LICH XE (phan cong dang mo chong khung), khong phai
    # nhan trang thai — xem `services/lich_xe.py`.
    dieu_phoi_qua_chuyen(client, "DO-A")
    _khung_gio_va_trip(client, "DO-B", "TRIP-B")
    tra = client.get("/api/tms/trips/TRIP-B")
    loser = client.put("/api/tms/trips/TRIP-B/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": int((tra.json()["data"] or {}).get("version") or 1),
        "assignment_start": "2026-08-12T01:00:00+00:00",
        "assignment_end": "2026-08-12T13:00:00+00:00",
    })
    assert loser.status_code == 409, loser.text
    # Chuyen A DANG CHAY (chua hoan tat) nen xe bi giu bat ke gio du kien —
    # cua "dang giu" (RESOURCE_BUSY) bat truoc cua "chong khung gio"
    # (RESOURCE_TIME_OVERLAP). Ca hai deu la lich, khong phai nhan.
    assert loser.json()["detail"]["code"] in {"RESOURCE_BUSY", "RESOURCE_TIME_OVERLAP"}
    # Cau bao loi phai NOI RO ai dang giu, khong chi noi "dang bi chiem".
    assert "TRIP-DO-A" in loser.json()["detail"]["message"], loser.json()["detail"]["message"]
    rows = _audit_rows(database_file, "DO-A") + _audit_rows(database_file, "DO-B")
    assert [row[2] for row in rows].count("DISPATCH_DELIVERY") == 0


def test_domain_conflict_rechecks_committed_idempotency_winner_before_returning_409():
    response = {"message": "Thao tác thành công", "data": {"id": "DO-RACE"}}

    class RaceSession:
        def __init__(self):
            self.info = {}
            self.rolled_back = False

        def get(self, model, key):
            assert model is IdempotencyRecord
            if not self.rolled_back:
                return None
            return SimpleNamespace(
                operation="PUT:/api/delivery-orders/DO-RACE/dispatch:system",
                request_hash="44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                response_json=json.dumps(response, ensure_ascii=False),
            )

        def rollback(self):
            self.rolled_back = True

    request = SimpleNamespace(
        headers={"Idempotency-Key": "same-key"},
        method="PUT",
        url=SimpleNamespace(path="/api/delivery-orders/DO-RACE/dispatch"),
        state=SimpleNamespace(principal="system"),
        client=SimpleNamespace(host="testclient"),
    )
    session = RaceSession()

    def losing_callback(_actor):
        raise DomainError("INVALID_TRANSITION", "Yêu cầu đến sau đã thấy trạng thái mới.", 409)

    assert _execute(request, session, {}, losing_callback) == response
    assert session.rolled_back is True


def test_workflow_mutations_require_trusted_principal_and_corrupt_replay_is_stable():
    from fastapi import HTTPException
    from routes.workflow_routes import _actor, _replay_response

    request = SimpleNamespace(state=SimpleNamespace(principal=None))
    with pytest.raises(HTTPException) as unauthenticated:
        _actor(request)
    assert unauthenticated.value.status_code == 401
    assert unauthenticated.value.detail["code"] == "AUTHENTICATION_REQUIRED"

    for payload in (None, "null", "[]", "{}", '{"message": 1, "data": {}}'):
        with pytest.raises(HTTPException) as corrupt:
            _replay_response(SimpleNamespace(response_json=payload))
        assert corrupt.value.status_code == 409
        assert corrupt.value.detail["code"] == "IDEMPOTENCY_RECORD_CORRUPT"


def test_closeout_requires_authentication_with_readable_vietnamese_message():
    from fastapi import HTTPException
    from main import _require_api_principal

    request = SimpleNamespace(state=SimpleNamespace(principal=None))
    with pytest.raises(HTTPException) as unauthenticated:
        _require_api_principal(request)

    assert unauthenticated.value.status_code == 401
    assert unauthenticated.value.detail["code"] == "AUTHENTICATION_REQUIRED"
    assert unauthenticated.value.detail["message"] == "Vui lòng đăng nhập."


def test_delete_guards_lock_quotation_and_delivery_order_rows():
    from services import workflow_service

    source = open(workflow_service.__file__, encoding="utf-8").read()
    for function_name in ("delete_quotation", "delete_delivery_order"):
        start = source.index(f"def {function_name}(")
        next_def = source.find("\ndef ", start + 1)
        body = source[start : next_def if next_def >= 0 else len(source)]
        assert ".with_for_update().first()" in body, f"{function_name} must lock before checking status"
