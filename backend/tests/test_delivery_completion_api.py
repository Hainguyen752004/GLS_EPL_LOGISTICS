from decimal import Decimal
import datetime as dt
import importlib
import json

import pytest
from pydantic import ValidationError

# Upload POD giờ được xác thực bằng magic byte (xem workflow_routes.py
# ::_verified_mime_type), nên fixture phải là nội dung PNG thật chứ không phải
# chuỗi tùy ý. Tám byte đầu là chữ ký PNG; phần đuôi giữ nguyên để các assert
# phân biệt được tệp POD với ảnh chữ ký.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
POD_BYTES = PNG_MAGIC + b"real-pod-bytes"
SIGNATURE_BYTES = PNG_MAGIC + b"real-signature-bytes"


def _valid_payload():
    return {
        "trip_id": "TRIP-001",
        "currency_code": "vnd",
        "pod_entries": [{
            "leg_id": "LEG-DELIVERY-001",
            "vehicle_id": "51C-268.89",
            "stop_no": 1,
            "location_text": "Cang Cat Lai",
            "receiver_name": "Nguyen Van An",
            "receiver_phone": "0908123456",
            "delivery_time": "2026-08-22T14:30:00+07:00",
            "delivery_result": "delivered_full",
            "cargo_condition": "Nguyen niem phong",
            "file_field": "pod_file_LEG-DELIVERY-001",
            "signature_file_field": "signature_file_LEG-DELIVERY-001",
            "note": "Giao du hang",
        }],
        "charge_adjustments": [{
            "name": "Phi cho boc do",
            "original_amount": "0",
            "actual_amount": "350000",
            "note": "Cho them 90 phut",
        }],
    }


def test_delivery_completion_schema_normalizes_currency_and_amounts():
    from schemas.delivery_completion import DeliveryCompletionRequest

    payload = DeliveryCompletionRequest.model_validate(_valid_payload())

    assert payload.currency_code == "VND"
    assert payload.charge_adjustments[0].increase_amount == Decimal("350000")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pod_entries", []),
        ("pod_entries", _valid_payload()["pod_entries"] * 101),
        ("charge_adjustments", _valid_payload()["charge_adjustments"] * 101),
    ],
)
def test_delivery_completion_schema_enforces_collection_limits(field, value):
    from schemas.delivery_completion import DeliveryCompletionRequest

    data = _valid_payload()
    data[field] = value
    with pytest.raises(ValidationError):
        DeliveryCompletionRequest.model_validate(data)


def test_delivery_completion_schema_rejects_duplicate_delivery_legs():
    from schemas.delivery_completion import DeliveryCompletionRequest

    data = _valid_payload()
    data["pod_entries"] = data["pod_entries"] * 2
    with pytest.raises(ValidationError, match="leg_id"):
        DeliveryCompletionRequest.model_validate(data)


def test_delivery_completion_schema_allows_lower_actual_without_customer_surcharge():
    from schemas.delivery_completion import DeliveryCompletionRequest

    data = _valid_payload()
    data["charge_adjustments"][0].update({
        "original_amount": "500000",
        "actual_amount": "350000",
    })
    payload = DeliveryCompletionRequest.model_validate(data)
    assert payload.charge_adjustments[0].increase_amount == Decimal("0")


def test_delivery_completion_schema_requires_unique_file_mapping():
    from schemas.delivery_completion import DeliveryCompletionRequest

    data = _valid_payload()
    second = dict(data["pod_entries"][0])
    second.update({"leg_id": "LEG-DELIVERY-002", "stop_no": 2})
    data["pod_entries"].append(second)
    with pytest.raises(ValidationError, match="file_field"):
        DeliveryCompletionRequest.model_validate(data)


def test_delivery_completion_schema_requires_unique_signature_mapping():
    from schemas.delivery_completion import DeliveryCompletionRequest

    data = _valid_payload()
    second = dict(data["pod_entries"][0])
    second.update({
        "leg_id": "LEG-DELIVERY-002",
        "stop_no": 2,
        "file_field": "pod_file_LEG-DELIVERY-002",
    })
    data["pod_entries"].append(second)
    with pytest.raises(ValidationError, match="signature_file_field"):
        DeliveryCompletionRequest.model_validate(data)


def test_delivery_completion_schema_rejects_signature_and_pod_field_collision():
    from schemas.delivery_completion import DeliveryCompletionRequest

    data = _valid_payload()
    data["pod_entries"][0]["signature_file_field"] = data["pod_entries"][0]["file_field"]
    with pytest.raises(ValidationError, match="upload field"):
        DeliveryCompletionRequest.model_validate(data)


def test_delivery_completion_schema_rejects_partial_or_rejected_result():
    from schemas.delivery_completion import DeliveryCompletionRequest

    for result in ("delivered_partial", "rejected"):
        data = _valid_payload()
        data["pod_entries"][0]["delivery_result"] = result
        with pytest.raises(ValidationError):
            DeliveryCompletionRequest.model_validate(data)


def test_delivery_completion_models_map_commercial_and_pod_tables():
    from models import (
        DeliveryOrderChargeAdjustment,
        DeliveryOrderCloseout,
        DeliveryPODDocument,
        DeliveryPODRecord,
    )

    assert DeliveryOrderCloseout.__tablename__ == "delivery_order_closeouts"
    assert DeliveryOrderChargeAdjustment.__tablename__ == "delivery_order_charge_adjustments"
    assert DeliveryPODDocument.__tablename__ == "delivery_pod_documents"
    assert "delivery_result" in DeliveryPODRecord.__table__.c
    assert "cargo_condition" in DeliveryPODRecord.__table__.c


def test_complete_delivery_http_persists_pod_surcharges_and_final_price(
    app_client, workflow_builder
):
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    workflow_builder.master_data()
    with database.SessionLocal() as db:
        db.merge(models.CurrencyDefinition(code="VND", minor_units=0, is_active=True))
        route = db.get(models.Route, "RT-T1")
        route.segments_json = json.dumps([
            {"origin": "Kho A", "destination": "Cang Cat Lai", "distance_km": 10},
        ])
        vehicle = db.get(models.Vehicle, "VEH-T1")
        db.merge(models.VehicleType(id="VT-T1", name="Xe tải"))
        vehicle.type = "VT-T1"
        vehicle.inspection_exp = "2027-12-31"
        vehicle.insurance_date = "2027-12-31"
        vehicle.maintenance_date = "2027-12-31"
        driver = db.get(models.Driver, "DRV-T1")
        driver.role = "Lái xe chính"
        db.merge(models.CostFormula(
            id="vehicle-type::VT-T1::VND",
            name="Xe tải",
            formula_expression=json.dumps({
                "vehicle_type_id": "VT-T1",
                "currency": "VND",
                "components": {"fuel": "0", "driver": "0", "toll": "0", "warehouse": "0", "freight_rate": "0"},
                "tokens": [],
            }),
        ))
        db.add(models.Driver(
            id="CODRV-COMPLETE", name="Phụ xe hoàn tất", role="Phụ xe",
            status="Rảnh - sẵn sàng", assigned_vehicle="Chưa gán",
        ))
        db.add(models.DriverQualification(
            driver_id="DRV-T1", license_type=driver.license_type,
            valid_from=dt.datetime(2026, 1, 1), valid_to=dt.datetime(2027, 1, 1),
            status="active",
        ))
        for shift_id, crew_id in (
            ("SHIFT-COMPLETE-DRIVER", "DRV-T1"),
            ("SHIFT-COMPLETE-CODRIVER", "CODRV-COMPLETE"),
        ):
            db.add(models.DriverShiftAssignment(
                id=shift_id,
                driver_id=crew_id,
                shift_type="custom",
                availability_kind="work",
                shift_start=dt.datetime(2026, 8, 22, 0, 0, tzinfo=dt.timezone.utc),
                shift_end=dt.datetime(2026, 8, 22, 8, 0, tzinfo=dt.timezone.utc),
                status="confirmed",
            ))
        db.commit()

    assert client.post("/api/quotations", json={
        "id": "QT-COMPLETE", "customer_id": "CUS-T1", "route_id": "RT-T1",
        "selling_price": 4_200_000,
        "pickup_window_start": "2026-08-22T07:00:00+07:00",
        "pickup_window_end": "2026-08-22T09:00:00+07:00",
        "delivery_window_start": "2026-08-22T11:00:00+07:00",
        "delivery_window_end": "2026-08-22T14:00:00+07:00",
    }).status_code == 200
    assert client.put("/api/quotations/QT-COMPLETE/approve").status_code == 200
    assert client.post("/api/sales-orders", json={
        "id": "SO-COMPLETE", "quotation_id": "QT-COMPLETE",
    }).status_code == 200
    assert client.put("/api/sales-orders/SO-COMPLETE/confirm").status_code == 200
    assert client.post("/api/delivery-orders", json={
        "id": "DO-COMPLETE", "so_id": "SO-COMPLETE", "route_id": "RT-T1",
        "pickup_window_start": "2026-08-22T07:00:00+07:00",
        "pickup_window_end": "2026-08-22T09:00:00+07:00",
        "delivery_window_start": "2026-08-22T11:00:00+07:00",
        "delivery_window_end": "2026-08-22T14:00:00+07:00",
    
        "packaging_spec": "Container nguyên khối",
        "seal_no": "SL-TEST-0001",
    }).status_code == 200
    created = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": "TRIP-COMPLETE", "do_ids": ["DO-COMPLETE"], "trip_type": "one_way",
        "planned_departure_at": "2026-08-22T08:00:00+07:00",
        "avg_speed_kmh": "40", "dwell_minutes": 0,
        "stop_plan": [{"sequence_no": 1, "stop_name": "Cang Cat Lai"}],
    }, headers={"Idempotency-Key": "trip-complete"})
    assert created.status_code == 200, created.text
    dispatched = client.put("/api/tms/trips/TRIP-COMPLETE/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1",
        "co_driver_id": "CODRV-COMPLETE",
        "expected_version": created.json()["data"]["version"],
        "assignment_start": "2026-08-22T08:00:00+07:00",
        "assignment_end": "2026-08-22T14:00:00+07:00",
    })
    assert dispatched.status_code == 200, dispatched.text
    trip = client.get("/api/tms/trips/TRIP-COMPLETE").json()["data"]
    delivery_legs = [leg for leg in trip["legs"] if leg["leg_type"] == "delivery"]
    assert delivery_legs
    pod_entries = []
    multipart_files = {}
    for leg in delivery_legs:
        field = f"pod_file_{leg['id']}"
        signature_field = f"signature_file_{leg['id']}"
        pod_entries.append({
            "leg_id": leg["id"], "vehicle_id": "VEH-T1",
            "stop_no": leg["sequence_no"], "location_text": leg["destination"],
            "receiver_name": "Nguyen Van An", "receiver_phone": "0908123456",
            "delivery_time": "2026-08-22T14:30:00+07:00",
            "delivery_result": "delivered_full", "cargo_condition": "Nguyen niem phong",
            "file_field": field, "signature_file_field": signature_field,
            "note": "Giao du hang",
        })
        multipart_files[field] = (f"{leg['id']}.png", POD_BYTES, "image/png")
        multipart_files[signature_field] = (
            f"signature-{leg['id']}.png", SIGNATURE_BYTES, "image/png"
        )
    payload = {
        "trip_id": "TRIP-COMPLETE", "currency_code": "VND",
        "pod_entries": pod_entries,
        "charge_adjustments": [
            {"name": "Phi cho boc do", "original_amount": "0", "actual_amount": "350000"},
            {"name": "Phi cau duong", "original_amount": "0", "actual_amount": "120000"},
        ],
    }
    response = client.post(
        "/api/delivery-orders/DO-COMPLETE/complete-delivery",
        data={"payload": json.dumps(payload)}, files=multipart_files,
        headers={"Idempotency-Key": "complete-do-001"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["commercials"]["base_selling_price"] == 4_200_000
    assert data["commercials"]["customer_surcharge_total"] == 470_000
    assert data["commercials"]["final_selling_price"] == 4_670_000
    replay = client.post(
        "/api/delivery-orders/DO-COMPLETE/complete-delivery",
        data={"payload": json.dumps(payload)}, files=multipart_files,
        headers={"Idempotency-Key": "complete-do-001"},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["commercials"]["final_selling_price"] == 4_670_000
    closeout_response = client.get("/api/delivery-orders/DO-COMPLETE/closeout")
    assert closeout_response.status_code == 200, closeout_response.text
    closeout_data = closeout_response.json()
    assert closeout_data["commercials"]["base_selling_price"] == 4_200_000
    assert closeout_data["commercials"]["customer_surcharge_total"] == 470_000
    assert closeout_data["commercials"]["final_selling_price"] == 4_670_000
    assert len(closeout_data["customer_charge_adjustments"]) == 2
    assert len(closeout_data["pod_documents"]) == len(delivery_legs) * 2
    assert closeout_data["status"] == "delivered"
    assert closeout_data["trip"]["status"] == "completed"
    assert closeout_data["invoice"]["canonical_status"] == "posted"
    assert closeout_data["invoice"]["amount"] == 4_670_000
    with database.SessionLocal() as db:
        co_driver = db.get(models.Driver, "CODRV-COMPLETE")
        assignment = db.query(models.ResourceAssignment).filter_by(trip_id="TRIP-COMPLETE").one()
        assert assignment.co_driver_id == "CODRV-COMPLETE"
        assert assignment.status == "completed"
        assert co_driver.status == "🟢 Rảnh (Sẵn sàng)"
        assert co_driver.assigned_vehicle == "Chưa gán"
    assert closeout_data["resource_release"] == {
        "assignment_status": "completed",
        "vehicle_status": "Sẵn sàng",
        "driver_status": "🟢 Rảnh (Sẵn sàng)",
    }
    downloaded_documents = {
        document["file_name"]: client.get(document["download_url"])
        for document in closeout_data["pod_documents"]
    }
    assert any(response.content == POD_BYTES for response in downloaded_documents.values())
    assert any(response.content == SIGNATURE_BYTES for response in downloaded_documents.values())
    assert all(response.status_code == 200 for response in downloaded_documents.values())
    assert all(response.headers["content-type"] == "image/png" for response in downloaded_documents.values())

    with database.SessionLocal() as db:
        completed_delivery = db.get(models.DeliveryOrder, "DO-COMPLETE")
        assert completed_delivery.canonical_status == "delivered"
        # "Đã giao" mo ho nen da doi thanh "Đã hoàn tất". Chu du an chi ra:
        # xe toi diem giao ma chua ky POD thi theo cach hieu thuong cung la
        # "da giao", nhung luc do chua co gi xac nhan. Moc nay la DA ky POD,
        # DA chot gia, DA hach toan — con moc "toi bai chua ky" la `arrived`
        # ("Đã đến nơi — chờ POD").
        assert completed_delivery.status == "Đã hoàn tất"
        assert db.get(models.TransportTrip, "TRIP-COMPLETE").status == "completed"
        assert db.get(models.FreightOrder, "FO-TRIP-COMPLETE").status == "delivered"
        assignment = db.query(models.ResourceAssignment).filter_by(trip_id="TRIP-COMPLETE").one()
        assert assignment.status == "completed"
        assert db.get(models.Vehicle, "VEH-T1").status == "Sẵn sàng"
        driver = db.get(models.Driver, "DRV-T1")
        assert driver.status == "🟢 Rảnh (Sẵn sàng)"
        assert driver.assigned_vehicle == "Chưa gán"
        closeout = db.query(models.DeliveryOrderCloseout).filter_by(do_id="DO-COMPLETE").one()
        assert closeout.final_selling_price == Decimal("4670000")
        documents = db.query(models.DeliveryPODDocument).all()
        assert {document.content for document in documents} == {
            POD_BYTES, SIGNATURE_BYTES
        }
        assert db.query(models.DeliveryOrderCloseout).count() == 1
        assert db.query(models.DeliveryPODRecord).count() == len(delivery_legs)
        assert db.query(models.ARInvoice).filter_by(do_id="DO-COMPLETE").one().amount == Decimal("4670000")
        assert db.query(models.FreightActualCost).count() == 0
