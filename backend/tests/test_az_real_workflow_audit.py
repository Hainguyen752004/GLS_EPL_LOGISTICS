import importlib
import json
import datetime as dt


def test_master_to_closeout_flow_writes_real_database_records(app_client, workflow_builder):
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")

    workflow_builder.master_data()
    assert client.post("/api/routes", json={
        "id": "RT-T1",
        "name": "Kho A - Cang B",
        "distance_km": 10,
        "segments_json": json.dumps([
            {"origin": "Kho A", "destination": "Cang B", "distance_km": 10},
        ]),
    }).status_code == 200
    with database.SessionLocal() as db:
        db.merge(models.CurrencyDefinition(code="VND", minor_units=0, is_active=True))
        db.merge(models.FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
        db.merge(models.Carrier(id="AZ-CARRIER", name="AZ Internal Fleet", status="active", is_internal=True))
        db.merge(models.VehicleType(id="VT-AZ", name="AZ Vehicle Type"))
        db.add(models.Role(id="AZ-FINANCE", permissions='["finance_read","finance_creator"]'))
        db.add(models.User(id="az-finance", username="az-finance", role_id="AZ-FINANCE"))
        db.add(models.DriverQualification(
            driver_id="DRV-T1",
            license_type="Hạng FC",
            valid_from=dt.datetime(2026, 1, 1),
            valid_to=dt.datetime(2027, 1, 1),
            status="active",
        ))
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.type = "VT-AZ"
        vehicle.inspection_exp = "2027-12-31"
        vehicle.insurance_date = "2027-12-31"
        vehicle.maintenance_date = "2027-12-31"
        db.commit()

    assert client.post("/api/cost-formulas", json={
        "id": "AZ-COST-FORMULA",
        "vehicle_type_id": "VT-AZ",
        "name": "AZ Cost Formula",
        "currency": "VND",
        "fuel": "6000",
        "driver": "300000",
        "toll": "100000",
        "warehouse": "50000",
        "freight_rate": "1200",
    }).status_code == 200
    assert client.post("/api/quotations", json={
        "id": "QT-AZ",
        "customer_id": "CUS-T1",
        "route_id": "RT-T1",
        "selling_price": 2500000,
        "total_cost": 500000,
        "pickup_window_start": "2026-08-21T07:00:00+07:00",
        "pickup_window_end": "2026-08-21T09:00:00+07:00",
        "delivery_window_start": "2026-08-21T11:00:00+07:00",
        "delivery_window_end": "2026-08-21T14:00:00+07:00",
    }).status_code == 200
    assert client.put("/api/quotations/QT-AZ/approve").status_code == 200
    assert client.post("/api/sales-orders", json={"id": "SO-AZ", "quotation_id": "QT-AZ"}).status_code == 200
    assert client.put("/api/sales-orders/SO-AZ/confirm").status_code == 200
    assert client.post("/api/delivery-orders", json={
        "id": "DO-AZ",
        "so_id": "SO-AZ",
        "route_id": "RT-T1",
        "pickup_window_start": "2026-08-21T07:00:00+07:00",
        "pickup_window_end": "2026-08-21T09:00:00+07:00",
        "delivery_window_start": "2026-08-21T11:00:00+07:00",
        "delivery_window_end": "2026-08-21T14:00:00+07:00",
    }).status_code == 200

    trip_response = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": "TRIP-AZ",
        "do_ids": ["DO-AZ"],
        "trip_type": "one_way",
        "planned_departure_at": "2026-08-21T08:00:00+07:00",
        "avg_speed_kmh": "40",
        "dwell_minutes": 0,
        "stop_plan": [{
            "sequence_no": 1,
            "stop_name": "Cang Cat Lai",
            "receiver_name": "Anh Nam",
            "receiver_phone": "0909000000",
            "delivery_note": "Giao hang demo A-Z",
        }],
    }, headers={"Idempotency-Key": "az-trip"})
    assert trip_response.status_code == 200, trip_response.text
    trip = trip_response.json()["data"]

    workflow_builder.driver_shift(
        "2026-08-21T07:00:00+07:00",
        "2026-08-21T14:00:00+07:00",
        vehicle_id="VEH-T1",
        id="SHIFT-AZ",
    )

    dispatch_response = client.put("/api/tms/trips/TRIP-AZ/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": trip["version"],
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })
    assert dispatch_response.status_code == 200, dispatch_response.text
    assert client.get("/api/tracking/DO-AZ").status_code == 200

    loaded_trip = client.get("/api/tms/trips/TRIP-AZ").json()["data"]
    pod_entries = []
    multipart_files = {}
    for leg in loaded_trip["legs"]:
        pod_field = f"pod_file_{leg['sequence_no']}"
        signature_field = f"signature_file_{leg['sequence_no']}"
        pod_entries.append({
            "leg_id": leg["id"],
            "vehicle_id": "VEH-T1",
            "stop_no": leg["sequence_no"],
            "delivery_time": f"2026-08-21T0{8 + leg['sequence_no']}:00:00+07:00",
            "location_text": leg["destination"],
            "receiver_name": leg.get("receiver_name") or "Anh Nam",
            "receiver_phone": leg.get("receiver_phone") or "0909000000",
            "delivery_result": "delivered_full",
            "cargo_condition": "Nguyen niem phong",
            "file_field": pod_field,
            "signature_file_field": signature_field,
            "note": "POD A-Z",
        })
        multipart_files[pod_field] = (
            f"pod-{leg['sequence_no']}.png", b"\x89PNG\r\n\x1a\n" + b"az-real-pod", "image/png",
        )
        multipart_files[signature_field] = (
            f"signature-{leg['sequence_no']}.png", b"\x89PNG\r\n\x1a\n" + b"az-real-signature", "image/png",
        )
    completion_response = client.post(
        "/api/delivery-orders/DO-AZ/complete-delivery",
        data={"payload": json.dumps({
            "trip_id": "TRIP-AZ",
            "currency_code": "VND",
            "pod_entries": pod_entries,
            "charge_adjustments": [],
        })},
        files=multipart_files,
        headers={"Idempotency-Key": "az-complete-delivery"},
    )
    assert completion_response.status_code == 200, completion_response.text
    completion = completion_response.json()["data"]
    assert completion["status"] == "delivered"
    assert completion["invoice"]["canonical_status"] == "posted"
    assert len(completion["pod_records"]) == len(loaded_trip["legs"])
    assert all(len(row["documents"]) == 2 for row in completion["pod_records"])

    cost_response = client.put("/api/tms/finance/trips/TRIP-AZ/actual-cost", json={
        "id": "COST-AZ",
        "currency_code": "VND",
        "carrier_id": "AZ-CARRIER",
        "lines": [
            {"id": "COST-AZ-FUEL", "name": "Fuel", "original_amount": "0", "actual_amount": "120000"},
            {"id": "COST-AZ-TOLL", "name": "Toll", "original_amount": "0", "actual_amount": "80000"},
        ],
    }, headers={"X-Test-Principal": "az-finance", "Idempotency-Key": "az-cost"})
    assert cost_response.status_code == 200, cost_response.text

    closeout = client.get("/api/delivery-orders/DO-AZ/closeout")
    assert closeout.status_code == 200, closeout.text
    data = closeout.json()
    assert data["status"] == "delivered"
    assert data["trip"]["status"] == "completed"
    assert len(data["pod_records"]) == len(loaded_trip["legs"])
    assert data["commercials"]["selling_price"] == 2500000.0
    assert data["commercials"]["actual_cost_total"] == 200000.0

    with database.SessionLocal() as db:
        assert db.get(models.CostFormula, "vehicle-type::VT-AZ::VND") is not None
        assert db.get(models.DeliveryOrder, "DO-AZ").canonical_status == "delivered"
        assert db.get(models.TransportTrip, "TRIP-AZ").status == "completed"
        assert db.get(models.FreightActualCost, "COST-AZ").total_amount == 200000
        assert db.query(models.DeliveryOrderCloseout).filter_by(do_id="DO-AZ").one() is not None
        assert db.query(models.DeliveryPODDocument).count() == len(loaded_trip["legs"]) * 2
        assert db.query(models.ARInvoice).filter_by(do_id="DO-AZ").one().canonical_status == "posted"
