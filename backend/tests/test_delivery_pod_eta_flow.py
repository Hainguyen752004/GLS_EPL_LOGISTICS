import datetime as dt

from conftest import dieu_phoi_qua_chuyen
from services.workflow_service import estimate_delivery_timing


def _ready_do(client, workflow_builder):
    workflow_builder.master_data()
    workflow_builder.quotation("QT-POD", approve=True)
    workflow_builder.delivery_order("DO-POD", "QT-POD", approve=True)
    workflow_builder.san_sang_dieu_phoi("DO-POD")
    return "DO-POD"


def test_duong_dieu_phoi_le_da_dong_phan_ghi(app_client, workflow_builder):
    """`PUT /api/delivery-orders/{id}/dispatch` KHONG con ghi gi.

    Duong do tung dua lenh sang `in_transit` ma khong lap chuyen, nen lenh do
    khong nop duoc POD, khong huy duoc, va xe cung to lai bi giu vinh vien —
    moi duong giai phong deu di qua chuyen. Gio no chi tra ve mot cau chi dan.
    """
    client, _, _ = app_client
    do_id = _ready_do(client, workflow_builder)
    r = client.put(f"/api/delivery-orders/{do_id}/dispatch",
                   json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"})
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "DISPATCH_VIA_TRIP_REQUIRED"
    assert "from-delivery-orders" in r.json()["detail"]["message"]
    # Va no khong doi trang thai cua lenh.
    ds = client.get("/api/delivery-orders?page=1&page_size=50").json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    assert next(x for x in ds if x["id"] == do_id)["canonical_status"] == "pending"


def test_dieu_phoi_qua_chuyen_ghi_eta_va_theo_doi(app_client, workflow_builder):
    """Dieu phoi qua chuyen phai ghi ETA va dong theo doi cho lenh giao hang."""
    client, _, _ = app_client
    do_id = _ready_do(client, workflow_builder)
    ma_trip = dieu_phoi_qua_chuyen(client, do_id)

    ds = client.get("/api/delivery-orders?page=1&page_size=50").json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    do = next(x for x in ds if x["id"] == do_id)
    assert do["canonical_status"] == "in_transit"
    assert do["vehicle_id"] == "VEH-T1"
    assert do["driver_id"] == "DRV-T1"

    tracking = client.get(f"/api/tracking/{do_id}")
    assert tracking.status_code == 200, tracking.text
    theo_doi = tracking.json()
    assert theo_doi["vehicle_id"] == "VEH-T1"
    # Quang duong con lai lay tu CHANG GIAO cua chuyen, khong bia.
    assert float(theo_doi["remaining_distance_km"]) == 10
    assert theo_doi["eta"], "phai co gio du kien den"

    chuyen = client.get(f"/api/tms/trips/{ma_trip}").json()["data"]
    assert chuyen["status"] == "in_transit"
    assert chuyen["planned_arrival_at"], "chuyen phai co gio du kien den"


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
    dieu_phoi_qua_chuyen(client, do_id)
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
    dieu_phoi_qua_chuyen(client, do_id)
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
