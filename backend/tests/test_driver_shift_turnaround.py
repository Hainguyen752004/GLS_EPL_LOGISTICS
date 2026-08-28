import datetime as dt
import importlib

import pytest


def scheduling_service():
    try:
        return importlib.import_module("services.tms_scheduling_service")
    except ModuleNotFoundError:
        pytest.fail("Missing real driver scheduling service")


def test_turnaround_uses_live_speed_then_vehicle_speed_for_return():
    service = scheduling_service()
    result = service.forecast_trip_turnaround(
        [
            {
                "sequence_no": 1,
                "leg_type": "delivery",
                "origin": "Kho A",
                "destination": "Điểm B",
                "distance_km": 120,
                "avg_speed_kmh": 40,
                "dwell_minutes": 60,
                "planned_departure_at": "2026-08-24T06:00:00+00:00",
            },
            {
                "sequence_no": 2,
                "leg_type": "empty_return",
                "origin": "Điểm B",
                "destination": "Kho A",
                "distance_km": 120,
                "avg_speed_kmh": 40,
                "dwell_minutes": 0,
            },
        ],
        latest_speed_kmh=60,
        vehicle_avg_speed_kmh=50,
        vehicle_type_avg_speed_kmh=45,
    )

    assert result["outbound_speed_kmh"] == 60
    assert result["outbound_speed_source"] == "gps_tracking"
    assert result["return_speed_kmh"] == 50
    assert result["return_speed_source"] == "vehicle"
    assert result["available_at_destination"] == dt.datetime(2026, 8, 24, 9, 0, tzinfo=dt.timezone.utc)
    assert result["available_at_origin"] == dt.datetime(2026, 8, 24, 11, 24, tzinfo=dt.timezone.utc)
    assert result["return_mode"] == "empty_return"


def test_turnaround_refuses_to_invent_missing_return_route():
    service = scheduling_service()
    result = service.forecast_trip_turnaround(
        [
            {
                "sequence_no": 1,
                "leg_type": "delivery",
                "origin": "Kho A",
                "destination": "Điểm B",
                "distance_km": 90,
                "avg_speed_kmh": 45,
                "dwell_minutes": 30,
                "planned_departure_at": "2026-08-24T06:00:00+00:00",
            }
        ],
        vehicle_type_avg_speed_kmh=45,
    )

    assert result["available_at_destination"] == dt.datetime(2026, 8, 24, 8, 30, tzinfo=dt.timezone.utc)
    assert result["available_at_origin"] is None
    assert result["return_mode"] == "missing"
    assert result["warning_code"] == "RETURN_ROUTE_REQUIRED"


def test_driver_shift_api_persists_shift_without_vehicle_and_rejects_overlap(app_client):
    client, _, _ = app_client
    assert client.post("/api/drivers", json={
        "id": "DRV-SHIFT-01",
        "name": "Tài xế lịch tuần",
        "status": "Rảnh",
    }).status_code == 200

    payload = {
        "id": "SHIFT-20260824-001",
        "driver_id": "DRV-SHIFT-01",
        "shift_type": "morning",
        "shift_start": "2026-08-24T06:00:00Z",
        "shift_end": "2026-08-24T14:00:00Z",
        "work_location": "Kho A",
        "notes": "Ưu tiên tuyến Cát Lái",
    }
    created = client.post("/api/tms/scheduling/driver-shifts", json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["data"]["vehicle_id"] is None

    loaded = client.get(
        "/api/tms/scheduling/driver-shifts",
        params={"start": "2026-08-24T00:00:00Z", "end": "2026-08-31T00:00:00Z"},
    )
    assert loaded.status_code == 200
    assert [row["id"] for row in loaded.json()["data"]] == ["SHIFT-20260824-001"]

    overlap = client.post("/api/tms/scheduling/driver-shifts", json={
        **payload,
        "id": "SHIFT-20260824-002",
        "shift_start": "2026-08-24T13:00:00Z",
        "shift_end": "2026-08-24T18:00:00Z",
    })
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "DRIVER_SHIFT_OVERLAP"


def test_driver_shift_api_persists_sick_leave_block(app_client):
    client, _, _ = app_client
    assert client.post("/api/drivers", json={
        "id": "DRV-ABSENCE-01",
        "name": "Tài xế nghỉ bệnh",
        "status": "Rảnh",
    }).status_code == 200

    created = client.post("/api/tms/scheduling/driver-shifts", json={
        "id": "ABSENCE-20260824-001",
        "driver_id": "DRV-ABSENCE-01",
        "shift_type": "custom",
        "availability_kind": "sick",
        "trip_id": "TRIP-MUST-NOT-BE-ASSIGNED",
        "shift_start": "2026-08-24T00:00:00Z",
        "shift_end": "2026-08-25T00:00:00Z",
        "notes": "Nghỉ bệnh có xác nhận",
    })

    assert created.status_code == 200, created.text
    assert created.json()["data"]["availability_kind"] == "sick"
    assert created.json()["data"]["trip_id"] is None
