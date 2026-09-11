import datetime as dt
import importlib
import json


DEPARTURE = "2026-08-21T08:00:00+07:00"


def _pending_do(client, workflow_builder, suffix, route_id="RT-T1"):
    workflow_builder.quotation(f"QT-{suffix}", approve=True)
    workflow_builder.delivery_order(f"DO-{suffix}", f"QT-{suffix}", route_id= route_id, pickup_window_start= "2026-08-21T07:00:00+07:00", pickup_window_end= "2026-08-21T09:00:00+07:00", delivery_window_start= "2026-08-21T10:00:00+07:00", delivery_window_end= "2026-08-21T14:00:00+07:00")


def test_create_trip_from_dos_builds_route_legs_transactionally_and_is_idempotent(
    app_client, workflow_builder
):
    client, database_file, _ = app_client
    workflow_builder.master_data()
    route = client.post("/api/routes", json={
        "id": "RT-T1",
        "name": "Kho A - Trạm B - Cảng C",
        "distance_km": 30,
        "segments_json": json.dumps([
            {"origin": "Kho A", "destination": "Trạm B", "distance_km": 10},
            {"origin": "Trạm B", "destination": "Cảng C", "distance_km": 20},
        ], ensure_ascii=False),
    })
    assert route.status_code in (200, 201), route.text
    _pending_do(client, workflow_builder, "TRIP-A")
    _pending_do(client, workflow_builder, "TRIP-B")

    payload = {
        "id": "TRIP-FROM-DO-001",
        "do_ids": ["DO-TRIP-A", "DO-TRIP-B"],
        "trip_type": "one_way",
        "planned_departure_at": DEPARTURE,
        "avg_speed_kmh": "40",
        "dwell_minutes": 15,
    }
    headers = {"Idempotency-Key": "trip-from-do-001"}
    created = client.post("/api/tms/trips/from-delivery-orders", json=payload, headers=headers)
    replayed = client.post("/api/tms/trips/from-delivery-orders", json=payload, headers=headers)

    assert created.status_code == 200, created.text
    assert replayed.status_code == 200, replayed.text
    trip = created.json()["data"]
    assert trip["id"] == "TRIP-FROM-DO-001"
    assert trip["delivery_order_ids"] == ["DO-TRIP-A", "DO-TRIP-B"]
    # Hai DO trên tuyến hai chặng (11/09): chặng 1 đi ngang (`outbound`), chặng 2 giao DO thứ
    # nhất, và DO thứ hai có chặng HẠ HÀNG riêng 0 km tại đúng điểm cuối — nên 3 chặng, tổng km
    # vẫn 30. Trước đây chặng 1 bị coi là điểm giao của DO-TRIP-A tại "Trạm B" — một điểm xe
    # chỉ đi ngang.
    assert [leg["distance_km"] for leg in trip["legs"]] == ["10.000", "20.000", "0.000"]
    assert [(leg["leg_type"], leg["do_id"], leg["destination"]) for leg in trip["legs"]] == [
        ("outbound", "DO-TRIP-A", "Trạm B"),
        ("delivery", "DO-TRIP-A", "Cảng C"),
        ("delivery", "DO-TRIP-B", "Cảng C"),
    ]
    assert trip["total_distance_km"] == "30.000"
    assert trip["planned_departure_at"].endswith("+00:00")

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.query(models.TransportTrip).filter_by(id="TRIP-FROM-DO-001").count() == 1
        assert db.query(models.FreightOrder).filter_by(id="FO-TRIP-FROM-DO-001").count() == 1
        assert db.query(models.TransportTripLeg).filter_by(trip_id="TRIP-FROM-DO-001").count() == 3


def test_create_trip_from_do_persists_delivery_stop_recipient_plan(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    route = client.post("/api/routes", json={
        "id": "RT-T1",
        "name": "Kho A - Trạm B - Cảng C",
        "distance_km": 30,
        "segments_json": json.dumps([
            {"origin": "Kho A", "destination": "Trạm B", "distance_km": 10},
            {"origin": "Trạm B", "destination": "Cảng C", "distance_km": 20},
        ], ensure_ascii=False),
    })
    assert route.status_code in (200, 201), route.text
    _pending_do(client, workflow_builder, "STOP-PLAN")

    response = client.post(
        "/api/tms/trips/from-delivery-orders",
        json={
            "id": "TRIP-STOP-PLAN",
            "do_ids": ["DO-STOP-PLAN"],
            "trip_type": "multi_stop",
            "planned_departure_at": DEPARTURE,
            "avg_speed_kmh": "40",
            "dwell_minutes": 15,
            "stop_plan": [
                {
                    "sequence_no": 1,
                    "stop_name": "Trạm B - giao chứng từ",
                    "receiver_name": "Nguyễn Văn A",
                    "receiver_phone": "0908123456",
                    "delivery_note": "Gọi bảo vệ trước khi vào cổng",
                    "dwell_minutes": 20,
                },
                {
                    "sequence_no": 2,
                    "stop_name": "Cảng C - kho nhận",
                    "receiver_name": "Trần Thị B",
                    "receiver_phone": "0911222333",
                    "delivery_note": "Giao tại cửa số 3",
                },
            ],
        },
        headers={"Idempotency-Key": "trip-stop-plan"},
    )

    legs = response.json()["data"]["legs"]
    assert legs[0]["stop_name"] == "Trạm B - giao chứng từ"
    assert legs[0]["receiver_name"] == "Nguyễn Văn A"
    assert legs[0]["receiver_phone"] == "0908123456"
    assert legs[0]["delivery_note"] == "Gọi bảo vệ trước khi vào cổng"
    assert legs[0]["dwell_minutes"] == 20
    assert legs[1]["receiver_name"] == "Trần Thị B"


def test_create_trip_from_do_rejects_bad_route_and_rolls_back(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    client.post("/api/routes", json={
        "id": "RT-T1",
        "name": "Tuyến sai tổng km",
        "distance_km": 30,
        "segments_json": json.dumps([
            {"origin": "Kho A", "destination": "Cảng C", "distance_km": 9},
        ]),
    })
    _pending_do(client, workflow_builder, "BAD-ROUTE")

    response = client.post(
        "/api/tms/trips/from-delivery-orders",
        json={
            "id": "TRIP-BAD-ROUTE",
            "do_ids": ["DO-BAD-ROUTE"],
            "trip_type": "one_way",
            "planned_departure_at": DEPARTURE,
            "avg_speed_kmh": "40",
            "dwell_minutes": 0,
        },
        headers={"Idempotency-Key": "trip-bad-route"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ROUTE_SEGMENTS_INVALID"


def test_create_trip_from_do_rejects_unknown_fields_and_naive_time(app_client):
    client, _, _ = app_client
    base = {
        "id": "TRIP-STRICT",
        "do_ids": ["DO-X"],
        "trip_type": "one_way",
        "planned_departure_at": DEPARTURE,
        "avg_speed_kmh": "40",
        "dwell_minutes": 0,
    }
    unknown = client.post(
        "/api/tms/trips/from-delivery-orders",
        json={**base, "surprise": True},
        headers={"Idempotency-Key": "trip-strict-1"},
    )
    naive = client.post(
        "/api/tms/trips/from-delivery-orders",
        json={**base, "planned_departure_at": "2026-08-21T08:00:00"},
        headers={"Idempotency-Key": "trip-strict-2"},
    )

    assert unknown.status_code == 422
    assert naive.status_code == 422
