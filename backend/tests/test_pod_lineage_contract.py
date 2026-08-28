import datetime as dt
import importlib
import json
from decimal import Decimal


def _dispatch_trip(client, workflow_builder):
    workflow_builder.master_data()
    assert client.post("/api/routes", json={
        "id": "RT-POD-LINEAGE",
        "name": "Kho A - Cảng B",
        "distance_km": 10,
        "segments_json": json.dumps([
            {"origin": "Kho A", "destination": "Cảng B", "distance_km": 10},
        ]),
    }).status_code == 200
    workflow_builder.quotation("QT-POD-LINEAGE", approve=False)
    assert client.put("/api/quotations/QT-POD-LINEAGE", json={
        "selling_price": 2_500_000,
    }).status_code == 200
    assert client.put("/api/quotations/QT-POD-LINEAGE/approve").status_code == 200
    workflow_builder.sales_order("SO-POD-LINEAGE", "QT-POD-LINEAGE", confirm=True)
    assert client.post("/api/delivery-orders", json={
        "id": "DO-POD-LINEAGE",
        "so_id": "SO-POD-LINEAGE",
        "route_id": "RT-POD-LINEAGE",
        "pickup_window_start": "2026-08-21T07:00:00+07:00",
        "pickup_window_end": "2026-08-21T09:00:00+07:00",
        "delivery_window_start": "2026-08-21T10:00:00+07:00",
        "delivery_window_end": "2026-08-21T14:00:00+07:00",
    }).status_code == 200
    assert client.post("/api/tms/trips/from-delivery-orders", json={
        "id": "TRIP-POD-001",
        "do_ids": ["DO-POD-LINEAGE"],
        "trip_type": "one_way",
        "planned_departure_at": "2026-08-21T08:00:00+07:00",
        "avg_speed_kmh": "40",
        "dwell_minutes": 0,
    }, headers={"Idempotency-Key": "trip-pod-001"}).status_code == 200
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.inspection_exp = "2027-01-01"
        vehicle.insurance_date = "2027-01-01"
        vehicle.maintenance_date = "2027-01-01"
        driver = db.get(models.Driver, "DRV-T1")
        db.add(models.DriverQualification(
            driver_id=driver.id,
            license_type=driver.license_type,
            valid_from=dt.datetime(2025, 1, 1),
            valid_to=dt.datetime(2027, 1, 1),
            status="active",
        ))
        db.commit()
    workflow_builder.driver_shift(
        "2026-08-21T07:00:00+07:00",
        "2026-08-21T14:00:00+07:00",
        vehicle_id="VEH-T1",
        id="SHIFT-POD-LINEAGE",
    )
    dispatched = client.put("/api/tms/trips/TRIP-POD-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })
    assert dispatched.status_code == 200, dispatched.text


def test_legacy_pod_write_is_blocked_in_favor_of_atomic_completion(app_client, workflow_builder):
    client, _, _ = app_client
    _dispatch_trip(client, workflow_builder)
    payload = {
        "trip_id": "TRIP-POD-001",
        "leg_id": "TRIP-POD-001-LEG-001",
        "vehicle_id": "VEH-T1",
        "stop_no": 1,
        "delivery_time": "2026-08-21T11:00:00+07:00",
        "location_text": "Cảng B",
        "receiver_name": "Nguyễn Văn Nhận",
        "photo_url": "https://example.test/pod.jpg",
        "note": "Đã giao đủ hàng",
        "status": "completed",
    }
    headers = {"Idempotency-Key": "pod-trip-001-stop-1"}
    first = client.post("/api/pod/DO-POD-LINEAGE", json=payload, headers=headers)
    assert first.status_code == 409, first.text
    assert first.json()["detail"]["code"] == "ATOMIC_COMPLETION_REQUIRED"
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.query(models.DeliveryPODRecord).count() == 0
        assert db.query(models.POD).count() == 0
        assert db.get(models.DeliveryOrder, "DO-POD-LINEAGE").canonical_status == "in_transit"
        assert db.get(models.TransportTrip, "TRIP-POD-001").status == "in_transit"


def test_pod_rejects_missing_lineage_unknown_fields_and_naive_time(app_client):
    client, _, _ = app_client
    base = {
        "trip_id": "TRIP-X",
        "leg_id": "LEG-X",
        "vehicle_id": "VEH-X",
        "stop_no": 1,
        "delivery_time": "2026-08-21T11:00:00+07:00",
        "photo_url": "https://example.test/pod.jpg",
    }
    assert client.post("/api/pod/DO-X", json={**base, "approved": True}).status_code == 422
    assert client.post("/api/pod/DO-X", json={
        **base, "delivery_time": "2026-08-21T11:00:00",
    }).status_code == 422


def test_trip_cost_rows_are_user_defined_decimal_and_transactional(app_client, workflow_builder):
    client, _, _ = app_client
    _dispatch_trip(client, workflow_builder)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add_all([
            models.CurrencyDefinition(code="VND", minor_units=0),
            models.FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
            models.Carrier(id="INTERNAL", name="Đội xe nội bộ", is_internal=True),
            models.Role(id="FINANCE", permissions=json.dumps(["finance_creator", "finance_read"])),
            models.User(id="test-user", username="test-user", role_id="FINANCE"),
        ])
        db.commit()
    completion_payload = {
        "trip_id": "TRIP-POD-001",
        "currency_code": "VND",
        "pod_entries": [{
            "leg_id": "TRIP-POD-001-LEG-001",
            "vehicle_id": "VEH-T1",
            "stop_no": 1,
            "delivery_time": "2026-08-21T11:00:00+07:00",
            "location_text": "Cang B",
            "receiver_name": "Nguoi nhan",
            "receiver_phone": "0909000000",
            "delivery_result": "delivered_full",
            "cargo_condition": "Nguyen niem phong",
            "file_field": "pod_file_1",
            "signature_file_field": "signature_file_1",
        }],
        "charge_adjustments": [],
    }
    completion = client.post(
        "/api/delivery-orders/DO-POD-LINEAGE/complete-delivery",
        data={"payload": json.dumps(completion_payload)},
        files={
            "pod_file_1": ("pod.png", b"pod", "image/png"),
            "signature_file_1": ("signature.png", b"signature", "image/png"),
        },
        headers={"Idempotency-Key": "pod-for-cost"},
    )
    assert completion.status_code == 200, completion.text
    payload = {
        "currency_code": "VND",
        "lines": [
            {
                "name": "Giá dầu tăng",
                "original_amount": "1000.25",
                "actual_amount": "1500.75",
                "note": "Theo hóa đơn cây dầu",
            },
            {
                "name": "Phí chờ phát sinh",
                "original_amount": "0",
                "actual_amount": "200.10",
            },
        ],
    }
    headers = {"Idempotency-Key": "trip-cost-001"}
    first = client.put("/api/tms/finance/trips/TRIP-POD-001/actual-cost", json=payload, headers=headers)
    replay = client.put("/api/tms/finance/trips/TRIP-POD-001/actual-cost", json=payload, headers=headers)
    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    loaded = client.get("/api/tms/finance/trips/TRIP-POD-001/actual-cost")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["data"]["trip_id"] == "TRIP-POD-001"
    assert loaded.json()["data"]["lines"][0] == {
        "id": loaded.json()["data"]["lines"][0]["id"],
        "name": "Giá dầu tăng",
        "original_amount": 1000.25,
        "actual_amount": 1500.75,
        "increase_amount": 500.5,
        "note": "Theo hóa đơn cây dầu",
    }
    with database.SessionLocal() as db:
        cost = db.query(models.FreightActualCost).filter_by(trip_id="TRIP-POD-001", is_active=True).one()
        assert cost.total_amount == Decimal("700.600000")
        assert len(cost.items) == 2
        assert cost.items[0].increase_amount == Decimal("500.500000")
    assert client.put(
        "/api/tms/finance/trips/TRIP-POD-001/actual-cost",
        json={**payload, "approved": True},
        headers={"Idempotency-Key": "trip-cost-extra"},
    ).status_code == 422
    invalid = {**payload, "lines": [{
        "name": "Sai chênh lệch", "original_amount": "200", "actual_amount": "100"
    }]}
    assert client.put(
        "/api/tms/finance/trips/TRIP-POD-001/actual-cost",
        json=invalid,
        headers={"Idempotency-Key": "trip-cost-invalid"},
    ).status_code == 422
