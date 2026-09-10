# -*- coding: utf-8 -*-
"""Trạng thái vận hành của xe / tài xế là MÃ CHUẨN, cập nhật theo lịch và đặt tay được.

Chủ dự án nhìn cột `vehicles.status` ("Sẵn sàng", "Đang thực hiện TRIP-…") và
nói: *"cái nhãn thì hardcode quá — thay bằng loại gì có thể update được thông
tin xe không"*. Mốc 045 trả lời: một cột mã riêng, hệ thống ghi theo lịch (điều
xe, xe về, huỷ chuyến) và người dùng đặt tay được (đưa xe ra khỏi đội / đưa lại).
Chữ hiện ra do lang.json quyết theo mã.

Năm điều khoá lại:
1. Điều xe → `on_trip` kèm mã chuyến; huỷ chuyến → `available`. Không ai ghi cứng.
2. `GET /api/vehicles` trả MÃ, không chỉ nhãn.
3. Đưa xe ra khỏi đội (đặt tay, có lý do) → cửa điều phối chặn bằng một trường
   thật (`VEHICLE_OUT_OF_SERVICE`), không phải so chuỗi.
4. Không đặt tay được `on_trip` / `maintenance` — đó là thứ lịch nói.
5. Không đưa ra khỏi đội một xe đang chạy chuyến.
"""
import importlib

from conftest import API_TEST_HEADERS, dieu_phoi_qua_chuyen


def _xe(client, ma):
    ds = client.get("/api/vehicles").json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    return next(x for x in ds if x["id"] == ma)


def _tai_xe(client, ma):
    return next(x for x in client.get("/api/drivers").json() if x["id"] == ma)


def _do(client, workflow_builder, hau_to):
    workflow_builder.master_data()
    workflow_builder.quotation(f"QT-{hau_to}", approve=True)
    workflow_builder.delivery_order(f"DO-{hau_to}", f"QT-{hau_to}", approve=True)
    return f"DO-{hau_to}"


def test_ma_trang_thai_di_theo_lich_dieu_xe_va_huy_chuyen(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do(client, workflow_builder, "MA1")
    assert _xe(client, "VEH-T1")["operational_status"] == "available"
    assert _tai_xe(client, "DRV-T1")["operational_status"] == "available"

    ma_trip = dieu_phoi_qua_chuyen(client, do_id)

    # Điều xe -> on_trip, kèm mã chuyến đang giữ. Khung giờ dự kiến (2026-08-12) đã
    # TRÔI QUA so với "bây giờ", nhưng chuyến chưa hoàn tất thì xe VẪN đang bị
    # giữ — xe về trễ không làm xe thành rảnh. GET phải nói on_trip.
    assert _xe(client, "VEH-T1")["operational_status"] == "on_trip"
    assert _xe(client, "VEH-T1")["operational_ref"] == ma_trip
    assert _tai_xe(client, "DRV-T1")["operational_status"] == "on_trip"
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        xe = db.get(models.Vehicle, "VEH-T1")
        assert xe.operational_status == "on_trip", xe.operational_status
        assert xe.operational_ref == ma_trip
        assert xe.operational_updated_at is not None
        tx = db.get(models.Driver, "DRV-T1")
        assert tx.operational_status == "on_trip"
        assert tx.operational_ref == ma_trip
        assert tx.assigned_vehicle == "VEH-T1"
        # Nhãn cũ VẪN được chiếu — cho chỗ hiển thị chưa đổi — nhưng chiếu từ mã.
        assert ma_trip in (xe.status or "")

    # Huỷ chuyến -> available, không còn ref.
    tra = client.get(f"/api/tms/trips/{ma_trip}")
    pb = int((tra.json()["data"] or {}).get("version") or 1)
    r = client.post(f"/api/tms/trips/{ma_trip}/cancel",
                    json={"expected_version": pb, "reason": "Khách huỷ"},
                    headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-ma1"})
    assert r.status_code == 200, r.text
    with database.SessionLocal() as db:
        xe = db.get(models.Vehicle, "VEH-T1")
        assert xe.operational_status == "available"
        assert xe.operational_ref is None
        tx = db.get(models.Driver, "DRV-T1")
        assert tx.operational_status == "available"
        assert tx.assigned_vehicle == "Chưa gán"
    assert _xe(client, "VEH-T1")["operational_status"] == "available"


def test_dua_xe_ra_khoi_doi_thi_khong_dieu_duoc_va_dua_lai_thi_dieu_duoc(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do(client, workflow_builder, "MA2")

    # Thiếu lý do: chặn.
    r = client.put("/api/vehicles/VEH-T1/operational-status",
                   json={"status": "out_of_service", "note": " "}, headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "OPERATIONAL_NOTE_REQUIRED"

    r = client.put("/api/vehicles/VEH-T1/operational-status",
                   json={"status": "out_of_service", "note": "Hỏng hộp số, chờ phụ tùng"},
                   headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["operational_status"] == "out_of_service"
    xe = _xe(client, "VEH-T1")
    assert xe["operational_status"] == "out_of_service"
    assert xe["operational_note"] == "Hỏng hộp số, chờ phụ tùng"

    # Cửa điều phối chặn bằng TRƯỜNG THẬT, câu báo lỗi nêu lý do đã ghi.
    import datetime as dt
    import pytest
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    dau = dt.datetime(2026, 8, 12, 1, 0, tzinfo=dt.timezone.utc)
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        do.pickup_window_start = dau
        do.pickup_window_end = dau + dt.timedelta(hours=3)
        do.delivery_window_start = dau + dt.timedelta(hours=3)
        do.delivery_window_end = dau + dt.timedelta(hours=12)
        db.commit()
    from conftest import san_sang_dieu_phoi
    san_sang_dieu_phoi(client, do_id)
    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": "TRIP-MA2", "do_ids": [do_id], "trip_type": "one_way",
        "planned_departure_at": dau.isoformat(), "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={**API_TEST_HEADERS, "Idempotency-Key": "trip-ma2"})
    assert r.status_code in (200, 201), r.text
    pb = int((r.json().get("data") or {}).get("version") or 1)
    than = {"vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
            "expected_version": pb, "assignment_start": dau.isoformat(),
            "assignment_end": (dau + dt.timedelta(hours=12)).isoformat()}
    r = client.put("/api/tms/trips/TRIP-MA2/dispatch", json=than, headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "VEHICLE_OUT_OF_SERVICE"
    assert "Hỏng hộp số" in r.json()["detail"]["message"]

    # Đưa lại hoạt động -> điều được.
    r = client.put("/api/vehicles/VEH-T1/operational-status",
                   json={"status": "available"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert _xe(client, "VEH-T1")["operational_status"] == "available"
    r = client.put("/api/tms/trips/TRIP-MA2/dispatch", json=than, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text


def test_khong_dat_tay_duoc_trang_thai_do_lich_quyet(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    for tt in ("on_trip", "maintenance", "busy", "Sẵn sàng"):
        r = client.put("/api/vehicles/VEH-T1/operational-status",
                       json={"status": tt, "note": "x"}, headers=API_TEST_HEADERS)
        assert r.status_code == 422, (tt, r.text)
        assert r.json()["detail"]["code"] == "OPERATIONAL_STATUS_NOT_MANUAL"
    r = client.put("/api/drivers/DRV-T1/operational-status",
                   json={"status": "on_trip"}, headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text


def test_khong_dua_ra_khoi_doi_xe_dang_chay_chuyen(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do(client, workflow_builder, "MA4")
    # Khung giờ của hàm dùng chung là 2026-08-12 — "bây giờ" của bài kiểm là ngày
    # chạy thật, nên phân công đó không "đang mở" lúc này. Dùng khung phủ hiện tại.
    import datetime as dt
    bay_gio = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    dieu_phoi_qua_chuyen(client, do_id, khung_gio=(bay_gio - dt.timedelta(hours=1),
                                                    bay_gio + dt.timedelta(hours=11)))
    r = client.put("/api/vehicles/VEH-T1/operational-status",
                   json={"status": "out_of_service", "note": "thử"}, headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "VEHICLE_ON_TRIP"
    r = client.put("/api/drivers/DRV-T1/operational-status",
                   json={"status": "inactive", "note": "thử"}, headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "DRIVER_ON_TRIP"
    # GET đọc "bây giờ" -> on_trip.
    assert _xe(client, "VEH-T1")["operational_status"] == "on_trip"
    assert _tai_xe(client, "DRV-T1")["operational_status"] == "on_trip"


def test_tai_xe_nghi_viec_thi_khong_dieu_duoc(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do(client, workflow_builder, "MA5")
    r = client.put("/api/drivers/DRV-T1/operational-status",
                   json={"status": "inactive", "note": "Đã nghỉ việc từ 1/9"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert _tai_xe(client, "DRV-T1")["operational_status"] == "inactive"
    import pytest
    with pytest.raises(AssertionError) as loi:
        dieu_phoi_qua_chuyen(client, do_id)
    assert "DRIVER_UNAVAILABLE" in str(loi.value)
    assert "nghỉ việc" in str(loi.value)
