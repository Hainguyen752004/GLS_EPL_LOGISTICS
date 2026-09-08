import datetime as dt
import importlib
import json


def _create_ready_trip(client, workflow_builder):
    workflow_builder.master_data()
    client.post("/api/routes", json={
        "id": "RT-T1",
        "name": "Kho A - Cảng B",
        "distance_km": 10,
        "segments_json": json.dumps([
            {"origin": "Kho A", "destination": "Cảng B", "distance_km": 10},
        ]),
    })
    workflow_builder.quotation("QT-DISPATCH-TRIP", approve=True)
    workflow_builder.sales_order("SO-DISPATCH-TRIP", "QT-DISPATCH-TRIP", confirm=True)
    created_do = client.post("/api/delivery-orders", json={
        "id": "DO-DISPATCH-TRIP",
        "so_id": "SO-DISPATCH-TRIP",
        "route_id": "RT-T1",
        "pickup_window_start": "2026-08-21T07:00:00+07:00",
        "pickup_window_end": "2026-08-21T09:00:00+07:00",
        "delivery_window_start": "2026-08-21T10:00:00+07:00",
        "delivery_window_end": "2026-08-21T14:00:00+07:00",
    
        "packaging_spec": "Container nguyên khối",
        "seal_no": "SL-TEST-0001",
    })
    assert created_do.status_code == 200, created_do.text
    created_trip = client.post(
        "/api/tms/trips/from-delivery-orders",
        json={
            "id": "TRIP-DISPATCH-001",
            "do_ids": ["DO-DISPATCH-TRIP"],
            "trip_type": "one_way",
            "planned_departure_at": "2026-08-21T08:00:00+07:00",
            "avg_speed_kmh": "40",
            "dwell_minutes": 0,
        },
        headers={"Idempotency-Key": "trip-for-dispatch"},
    )
    assert created_trip.status_code == 200, created_trip.text
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.DriverShiftAssignment(
            id="SHIFT-DISPATCH-DEFAULT",
            driver_id="DRV-T1",
            shift_type="custom",
            availability_kind="work",
            shift_start=dt.datetime(2026, 8, 21, 0, 0, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 8, 22, 0, 0, tzinfo=dt.timezone.utc),
            status="confirmed",
        ))
        db.commit()


def test_dispatch_trip_requires_work_schedule_covering_entire_assignment(app_client, workflow_builder):
    client, _, _ = app_client
    _create_ready_trip(client, workflow_builder)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.query(models.DriverShiftAssignment).delete()
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

    response = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "DRIVER_WORK_SCHEDULE_REQUIRED"


def test_dispatch_trip_assigns_resources_and_moves_linked_do_atomically(app_client, workflow_builder):
    client, _, _ = app_client
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

    response = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "in_transit"
    with database.SessionLocal() as db:
        delivery = db.get(models.DeliveryOrder, "DO-DISPATCH-TRIP")
        assignment = db.query(models.ResourceAssignment).filter_by(trip_id="TRIP-DISPATCH-001").one()
        assert delivery.canonical_status == "in_transit"
        assert delivery.vehicle_id == "VEH-T1"
        assert assignment.driver_id == "DRV-T1"


def test_dispatch_trip_locks_resources_until_planned_return(app_client, workflow_builder):
    client, _, _ = app_client
    _create_ready_trip(client, workflow_builder)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    planned_return = dt.datetime(2026, 8, 23, 9, 30, tzinfo=dt.timezone.utc)
    with database.SessionLocal() as db:
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.inspection_exp = "2027-01-01"
        vehicle.insurance_date = "2027-01-01"
        vehicle.maintenance_date = "2027-01-01"
        trip = db.get(models.TransportTrip, "TRIP-DISPATCH-001")
        trip.planned_return_at = planned_return
        shift = db.get(models.DriverShiftAssignment, "SHIFT-DISPATCH-DEFAULT")
        shift.shift_end = dt.datetime(2026, 8, 24, 0, 0, tzinfo=dt.timezone.utc)
        driver = db.get(models.Driver, "DRV-T1")
        db.add(models.DriverQualification(
            driver_id=driver.id,
            license_type=driver.license_type,
            valid_from=dt.datetime(2025, 1, 1),
            valid_to=dt.datetime(2027, 1, 1),
            status="active",
        ))
        db.commit()

    response = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert response.status_code == 200, response.text
    with database.SessionLocal() as db:
        assignment = db.query(models.ResourceAssignment).filter_by(
            trip_id="TRIP-DISPATCH-001"
        ).one()
        assert assignment.assignment_end == planned_return.replace(tzinfo=None)


def test_dispatch_trip_persists_and_locks_optional_co_driver(app_client, workflow_builder):
    client, _, _ = app_client
    _create_ready_trip(client, workflow_builder)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.inspection_exp = "2027-01-01"
        vehicle.insurance_date = "2027-01-01"
        vehicle.maintenance_date = "2027-01-01"
        driver = db.get(models.Driver, "DRV-T1")
        driver.role = "Lái xe chính"
        co_driver = models.Driver(
            id="CODRV-T1", name="Phụ xe Test", role="Phụ xe",
            status="Rảnh - sẵn sàng", assigned_vehicle="Chưa gán",
        )
        db.add(co_driver)
        db.add(models.DriverShiftAssignment(
            id="SHIFT-DISPATCH-CODRIVER",
            driver_id="CODRV-T1",
            shift_type="custom",
            availability_kind="work",
            shift_start=dt.datetime(2026, 8, 21, 0, 0, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 8, 22, 0, 0, tzinfo=dt.timezone.utc),
            status="confirmed",
        ))
        db.add(models.DriverQualification(
            driver_id=driver.id,
            license_type=driver.license_type,
            valid_from=dt.datetime(2025, 1, 1),
            valid_to=dt.datetime(2027, 1, 1),
            status="active",
        ))
        db.commit()

    response = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "co_driver_id": "CODRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert response.status_code == 200, response.text
    with database.SessionLocal() as db:
        trip = db.get(models.TransportTrip, "TRIP-DISPATCH-001")
        delivery = db.get(models.DeliveryOrder, "DO-DISPATCH-TRIP")
        assignment = db.query(models.ResourceAssignment).filter_by(trip_id=trip.id).one()
        co_driver = db.get(models.Driver, "CODRV-T1")
        assert trip.co_driver_id == "CODRV-T1"
        assert delivery.co_driver == "CODRV-T1"
        assert assignment.co_driver_id == "CODRV-T1"
        assert "TRIP-DISPATCH-001" in co_driver.status
        assert co_driver.assigned_vehicle == "VEH-T1"


def test_dispatch_trip_rejects_same_person_as_main_and_co_driver(app_client):
    client, _, _ = app_client
    response = client.put("/api/tms/trips/TRIP-X/dispatch", json={
        "vehicle_id": "VEH-X",
        "driver_id": "DRV-X",
        "co_driver_id": "DRV-X",
        "expected_version": 1,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })
    assert response.status_code == 422


def test_dispatch_trip_rejects_unknown_fields_and_naive_time(app_client):
    client, _, _ = app_client
    base = {
        "vehicle_id": "VEH-X",
        "driver_id": "DRV-X",
        "expected_version": 1,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    }
    unknown = client.put("/api/tms/trips/TRIP-X/dispatch", json={**base, "approved": True})
    naive = client.put("/api/tms/trips/TRIP-X/dispatch", json={
        **base, "assignment_start": "2026-08-21T08:00:00",
    })
    assert unknown.status_code == 422
    assert naive.status_code == 422


def test_dispatch_trip_rejects_vehicle_that_differs_from_planned_driver_shift(app_client, workflow_builder):
    client, _, _ = app_client
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
        db.add(models.Vehicle(
            id="VEH-SHIFT-OTHER",
            type=vehicle.type,
            weight_capacity=vehicle.weight_capacity,
            volume_capacity_m3=vehicle.volume_capacity_m3,
            pallet_capacity=vehicle.pallet_capacity,
            status="Sẵn sàng",
        ))
        db.flush()
        db.add(models.DriverShiftAssignment(
            id="SHIFT-DISPATCH-MISMATCH",
            driver_id=driver.id,
            vehicle_id="VEH-SHIFT-OTHER",
            shift_type="morning",
            shift_start=dt.datetime(2026, 8, 21, 0, 0, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 8, 21, 7, 0, tzinfo=dt.timezone.utc),
            status="confirmed",
        ))
        db.commit()

    response = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "SHIFT_VEHICLE_MISMATCH"


def test_dispatch_trip_rejects_driver_with_sick_leave_block(app_client, workflow_builder):
    client, _, _ = app_client
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
        db.add(models.DriverShiftAssignment(
            id="ABSENCE-DISPATCH-SICK",
            driver_id=driver.id,
            shift_type="custom",
            availability_kind="sick",
            shift_start=dt.datetime(2026, 8, 21, 0, 0, tzinfo=dt.timezone.utc),
            shift_end=dt.datetime(2026, 8, 22, 0, 0, tzinfo=dt.timezone.utc),
            status="confirmed",
        ))
        db.commit()

    response = client.put("/api/tms/trips/TRIP-DISPATCH-001/dispatch", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "expected_version": 2,
        "assignment_start": "2026-08-21T08:00:00+07:00",
        "assignment_end": "2026-08-21T12:00:00+07:00",
    })

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "DRIVER_UNAVAILABLE"
