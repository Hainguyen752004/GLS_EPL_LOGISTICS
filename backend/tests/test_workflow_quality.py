import sqlite3
import json
from types import SimpleNamespace
import pytest

from services.errors import DomainError
from routes.workflow_routes import _execute
from models import IdempotencyRecord


def _audit_rows(path, record_id):
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT user_id, ip_address, action FROM audit_logs WHERE record_id=? ORDER BY id", (record_id,)).fetchall()


def test_spoofed_actor_header_is_ignored_and_client_ip_is_audited(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.customer(); workflow_builder.route()
    response = client.post("/api/quotations", json={"id": "QT-ACTOR", "customer_id": "CUS-T1", "route_id": "RT-T1"}, headers={"X-User-Id": "spoofed"})
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
    client, database_file, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-I", approve=True)
    workflow_builder.sales_order("SO-I", "QT-I", confirm=True)
    workflow_builder.delivery_order("DO-I", "SO-I", approve=True)
    dispatch_headers = {"Idempotency-Key": "dispatch-one"}
    payload = {"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"}
    first = client.put("/api/delivery-orders/DO-I/dispatch", json=payload, headers=dispatch_headers)
    assert client.put("/api/delivery-orders/DO-I/dispatch", json=payload, headers=dispatch_headers).json() == first.json()
    assert [row[2] for row in _audit_rows(database_file, "DO-I")].count("DISPATCH_DELIVERY") == 1


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
        workflow_builder.sales_order(f"SO-{suffix}", f"QT-{suffix}", confirm=True)
        workflow_builder.delivery_order(f"DO-{suffix}", f"SO-{suffix}", approve=True)
    payload = {"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"}
    assert client.put("/api/delivery-orders/DO-A/dispatch", json=payload).status_code == 200
    loser = client.put("/api/delivery-orders/DO-B/dispatch", json=payload)
    assert loser.status_code == 409
    assert loser.json()["detail"]["code"] in {"VEHICLE_BUSY", "DRIVER_BUSY", "RESOURCE_BUSY"}
    rows = _audit_rows(database_file, "DO-A") + _audit_rows(database_file, "DO-B")
    assert [row[2] for row in rows].count("DISPATCH_DELIVERY") == 1


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


def test_delete_guards_lock_quotation_sales_order_and_delivery_order_rows():
    from services import workflow_service

    source = open(workflow_service.__file__, encoding="utf-8").read()
    for function_name in ("delete_quotation", "delete_sales_order", "delete_delivery_order"):
        start = source.index(f"def {function_name}(")
        next_def = source.find("\ndef ", start + 1)
        body = source[start : next_def if next_def >= 0 else len(source)]
        assert ".with_for_update().first()" in body, f"{function_name} must lock before checking status"
