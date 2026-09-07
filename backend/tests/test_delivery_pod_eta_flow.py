import datetime as dt

from services.workflow_service import estimate_delivery_timing


def _ready_do(client, workflow_builder):
    workflow_builder.master_data()
    workflow_builder.quotation("QT-POD", approve=True)
    workflow_builder.sales_order("SO-POD", "QT-POD", confirm=True)
    workflow_builder.delivery_order("DO-POD", "SO-POD", approve=True)
    return "DO-POD"


def test_dispatch_sets_planned_eta_return_and_remaining_distance(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _ready_do(client, workflow_builder)

    response = client.put(
        f"/api/delivery-orders/{do_id}/dispatch",
        json={
            "vehicle_id": "VEH-T1",
            "driver_id": "DRV-T1",
            "departure_at": "2026-08-12T08:00:00+07:00",
            "avg_speed_kmh": 50,
            "return_speed_kmh": 40,
            "load_minutes": 30,
            "unload_minutes": 45,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["planned_departure_at"] == "2026-08-12T01:00:00Z"
    assert data["planned_arrival_at"] == "2026-08-12T01:42:00Z"
    assert data["planned_return_at"] == "2026-08-12T02:42:00Z"
    assert data["avg_speed_kmh"] == 50

    tracking = client.get(f"/api/tracking/{do_id}")
    assert tracking.status_code == 200
    tracking_data = tracking.json()
    assert tracking_data["remaining_distance_km"] == 10
    assert tracking_data["eta"] == "2026-08-12T01:42:00Z"
    assert tracking_data["planned_return_at"] == "2026-08-12T02:42:00Z"


def test_moc_arrived_ghi_duoc_nhung_pod_le_van_bi_tu_choi(app_client, workflow_builder):
    """Ban truoc bai nay khang dinh lenh `Arrived` bi tu choi bang 409.

    Do la vi `arrived` chua co duong nao dat, du migration v002 da cho no la
    trang thai hop le — nen bai kiem dang khoa dung cai THIEU. Chu du an chi
    ra cho hut: xe toi bai roi ma man hinh van ghi "Dang van chuyen", khong
    phan biet duoc con tren duong hay da toi cho boc do.

    Nay ghi moc `arrived` duoc. Nhung hai chot khac VAN nguyen:
      · nop POD le qua `/api/pod/{do_id}` van bi tu choi — hoan tat giao doi
        POD, anh ky nhan va chot gia trong CUNG mot giao dich;
      · va `arrived` KHONG mo quyet toan chi phi (kiem o
        `test_moc_da_den_noi.py`).
    """
    client, _, _ = app_client
    do_id = _ready_do(client, workflow_builder)
    assert client.put(f"/api/delivery-orders/{do_id}/dispatch", json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"}).status_code == 200
    ghi_moc = client.put(f"/api/delivery-orders/{do_id}/status", json={"status": "Arrived"})
    assert ghi_moc.status_code == 200, ghi_moc.text
    # Ghi lai lan hai thi phai bi tu choi, khong duoc bao thanh cong.
    assert client.put(f"/api/delivery-orders/{do_id}/status", json={"status": "Arrived"}).status_code == 409

    first = client.post(f"/api/pod/{do_id}", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "stop_no": 1,
        "location_text": "Kho A",
        "receiver_name": "Anh Nam",
        "delivery_time": "2026-08-12T10:00:00",
        "photo_url": "/uploads/pod-a.jpg",
        "signature_url": "/uploads/sign-a.jpg",
        "note": "Giao đủ kiện 1",
    })
    assert first.status_code == 422


def test_delivered_requires_pod_record_for_assigned_vehicle(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _ready_do(client, workflow_builder)
    assert client.put(f"/api/delivery-orders/{do_id}/dispatch", json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"}).status_code == 200
    blocked = client.put(f"/api/delivery-orders/{do_id}/status", json={"status": "Delivered"})
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "ATOMIC_COMPLETION_REQUIRED"

    assert client.post(f"/api/pod/{do_id}", json={
        "vehicle_id": "VEH-T1",
        "driver_id": "DRV-T1",
        "receiver_name": "Anh Nam",
        "photo_url": "/uploads/pod.jpg",
    }).status_code == 422

    still_blocked = client.put(f"/api/delivery-orders/{do_id}/status", json={"status": "Delivered"})
    assert still_blocked.status_code == 409
    assert still_blocked.json()["detail"]["code"] == "ATOMIC_COMPLETION_REQUIRED"


def test_estimate_delivery_timing_calculates_return_time():
    result = estimate_delivery_timing(
        distance_km=200,
        departure_at=dt.datetime(2026, 8, 12, 8, 0),
        avg_speed_kmh=50,
        load_minutes=60,
        unload_minutes=90,
        return_speed_kmh=40,
    )

    assert result["planned_arrival_at"] == dt.datetime(2026, 8, 12, 13, 0)
    assert result["planned_return_at"] == dt.datetime(2026, 8, 12, 19, 30)
