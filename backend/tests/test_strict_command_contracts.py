import pytest


@pytest.mark.parametrize(
    ("method", "path", "payload", "headers"),
    [
        ("post", "/api/quotations", {"customer_id": "CUS-X", "route_id": "RT-X", "approved": True}, {}),
        ("post", "/api/routes", {"name": "Tuyến X", "approved": True}, {}),
        (
            "post",
            "/api/tms/trips/from-delivery-orders",
            {
                "id": "TRIP-X", "do_ids": ["DO-X"],
                "planned_departure_at": "2026-08-20T08:00:00+07:00",
                "avg_speed_kmh": 40, "approved": True,
            },
            {"Idempotency-Key": "strict-trip"},
        ),
        (
            "put",
            "/api/tms/trips/TRIP-X/dispatch",
            {
                "vehicle_id": "VEH-X", "driver_id": "DRV-X", "expected_version": 1,
                "assignment_start": "2026-08-20T08:00:00+07:00",
                "assignment_end": "2026-08-20T10:00:00+07:00", "approved": True,
            },
            {},
        ),
        (
            "post",
            "/api/pod/DO-X",
            {
                "trip_id": "TRIP-X", "leg_id": "LEG-X", "vehicle_id": "VEH-X",
                "stop_no": 1, "delivery_time": "2026-08-20T10:00:00+07:00",
                "photo_url": "https://example.test/pod.jpg", "approved": True,
            },
            {},
        ),
        (
            "put",
            "/api/tms/finance/trips/TRIP-X/actual-cost",
            {
                "currency_code": "VND",
                "lines": [{"name": "Xăng dầu", "original_amount": 0, "actual_amount": 1}],
                "approved": True,
            },
            {"Idempotency-Key": "strict-cost"},
        ),
    ],
)
def test_commands_reject_unknown_fields(app_client, method, path, payload, headers):
    client, _, _ = app_client
    response = getattr(client, method)(path, json=payload, headers=headers)

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert any("approved" in field for field in error["fields"])
