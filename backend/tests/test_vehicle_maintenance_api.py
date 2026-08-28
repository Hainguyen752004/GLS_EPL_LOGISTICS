import datetime as dt
import importlib


def _create_vehicle(client, vehicle_id="VEH-MAINT-01"):
    response = client.post(
        "/api/vehicles",
        json={
            "id": vehicle_id,
            "brand": "Isuzu",
            "type": "Container 20FT",
            "weight_capacity": 28000,
            "maintenance_date": "2027-01-01",
            "inspection_exp": "2027-01-01",
            "insurance_date": "2027-01-01",
        },
    )
    assert response.status_code == 200, response.text


def _maintenance_payload():
    return {
        "request_no": "MR-2026-0001",
        "category": "corrective",
        "priority": "high",
        "planned_start": "2026-08-21T08:00:00+07:00",
        "planned_end": "2026-08-21T17:00:00+07:00",
        "description": "Thay bo phanh va kiem tra he thong dau",
        "workshop": "EPL Workshop",
        "odometer_km": 125000,
        "currency_code": "VND",
        "cost_lines": [
            {
                "category": "parts",
                "description": "Bo phanh",
                "quantity": 2,
                "unit": "bo",
                "estimated_unit_cost": 750000,
            },
            {
                "category": "labor",
                "description": "Cong sua chua",
                "quantity": 1,
                "unit": "lan",
                "estimated_unit_cost": 450000,
            },
        ],
    }


def test_vehicle_maintenance_request_persists_server_totals_and_transitions(app_client):
    client, _, _ = app_client
    _create_vehicle(client)

    created = client.post(
        "/api/vehicles/VEH-MAINT-01/maintenance-requests",
        json=_maintenance_payload(),
        headers={"X-User-Id": "fleet-user"},
    )
    assert created.status_code == 201, created.text
    request = created.json()["data"]
    assert request["status"] == "requested"
    assert request["estimated_total"] == "1950000.000000"
    assert len(request["cost_lines"]) == 2

    approved = client.post(
        f"/api/vehicle-maintenance-requests/{request['id']}/approve",
        json={"expected_version": 1},
        headers={"X-User-Id": "fleet-manager", "Idempotency-Key": "approve-maint-1"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "approved"

    started = client.post(
        f"/api/vehicle-maintenance-requests/{request['id']}/start",
        json={"expected_version": 2, "actual_start": "2026-08-21T08:15:00+07:00"},
        headers={"X-User-Id": "fleet-manager", "Idempotency-Key": "start-maint-1"},
    )
    assert started.status_code == 200, started.text

    completed = client.post(
        f"/api/vehicle-maintenance-requests/{request['id']}/complete",
        json={
            "expected_version": 3,
            "actual_end": "2026-08-21T16:30:00+07:00",
            "next_maintenance_date": "2027-02-15",
            "actual_cost_lines": [
                {"line_id": request["cost_lines"][0]["id"], "actual_unit_cost": 800000},
                {"line_id": request["cost_lines"][1]["id"], "actual_unit_cost": 500000},
            ],
        },
        headers={"X-User-Id": "fleet-manager", "Idempotency-Key": "complete-maint-1"},
    )
    assert completed.status_code == 200, completed.text
    result = completed.json()["data"]
    assert result["status"] == "completed"
    assert result["actual_total"] == "2100000.000000"

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.get(models.Vehicle, "VEH-MAINT-01").maintenance_date == "2027-02-15"


def test_approved_maintenance_blocks_overlapping_trip_dispatch(app_client, workflow_builder):
    client, _, _ = app_client
    from test_dispatch_command_contract import _create_ready_trip

    _create_ready_trip(client, workflow_builder)
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

    payload = _maintenance_payload()
    payload["request_no"] = "MR-OVERLAP-01"
    created = client.post("/api/vehicles/VEH-T1/maintenance-requests", json=payload)
    request_id = created.json()["data"]["id"]
    assert client.post(
        f"/api/vehicle-maintenance-requests/{request_id}/approve",
        json={"expected_version": 1},
        headers={"Idempotency-Key": "approve-overlap"},
    ).status_code == 200

    dispatched = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })
    assert dispatched.status_code == 409, dispatched.text
    assert dispatched.json()["detail"]["code"] == "VEHICLE_MAINTENANCE_OVERLAP"

    with database.SessionLocal() as db:
        assert db.get(models.TransportTrip, "TRIP-DISPATCH-001").status == "planned"
        assert db.query(models.ResourceAssignment).filter_by(trip_id="TRIP-DISPATCH-001").count() == 0


def test_maintenance_during_return_leg_blocks_trip_dispatch(app_client, workflow_builder):
    client, _, _ = app_client
    from test_dispatch_command_contract import _create_ready_trip

    _create_ready_trip(client, workflow_builder)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.inspection_exp = "2027-01-01"
        vehicle.insurance_date = "2027-01-01"
        vehicle.maintenance_date = "2027-01-01"
        trip = db.get(models.TransportTrip, "TRIP-DISPATCH-001")
        trip.planned_return_at = dt.datetime(2026, 8, 22, 10, 0, tzinfo=dt.timezone.utc)
        driver = db.get(models.Driver, "DRV-T1")
        db.add(models.DriverQualification(
            driver_id=driver.id,
            license_type=driver.license_type,
            valid_from=dt.datetime(2025, 1, 1),
            valid_to=dt.datetime(2027, 1, 1),
            status="active",
        ))
        db.add(models.VehicleMaintenanceRequest(
            id="MR-RETURN-LOCK",
            request_no="MR-RETURN-LOCK",
            vehicle_id="VEH-T1",
            category="corrective",
            priority="high",
            planned_start=dt.datetime(2026, 8, 22, 1, 0, tzinfo=dt.timezone.utc),
            planned_end=dt.datetime(2026, 8, 22, 4, 0, tzinfo=dt.timezone.utc),
            description="Sua chua trong luc xe chua quay ve",
            status="approved",
        ))
        db.commit()

    dispatched = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert dispatched.status_code == 409, dispatched.text
    assert dispatched.json()["detail"]["code"] == "VEHICLE_MAINTENANCE_OVERLAP"
