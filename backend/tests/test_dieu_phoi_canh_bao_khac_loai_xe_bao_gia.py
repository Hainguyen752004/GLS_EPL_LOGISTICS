# -*- coding: utf-8 -*-
"""Điều phối xe KHÁC loại xe của báo giá: cảnh báo và bắt xác nhận, không chặn cứng.

Lỗ hổng đo được khi rà (10/09): báo giá khoá giá theo LOẠI XE (khách mua "một đầu
kéo 20'"), nhưng cửa điều phối chỉ kiểm xe ĐỦ TẢI — nên một chiếc 40' điều cho
DO báo giá 20' đi qua im lặng: khách vẫn trả giá 20', hồ sơ hoàn tất tính chi
theo công thức 40', công ty gánh phần lệch mà không ai thấy.

Chủ dự án duyệt cách sửa: **khác loại → 409 kèm lời giải thích, gửi lại với
`confirm_vehicle_type_mismatch=true` thì đi tiếp** (có lúc cố ý lên loại to hơn
để gộp chuyến). Ba điều khoá lại:

1. khác loại, chưa xác nhận → 409 `VEHICLE_TYPE_MISMATCH`, chuyến vẫn `planned`;
2. khác loại, đã xác nhận → điều được, có dòng nhật ký
   `DISPATCH_TRIP_VEHICLE_TYPE_OVERRIDE`;
3. đúng loại → đi thẳng, không hỏi.
"""
import datetime as dt
import importlib

from conftest import API_TEST_HEADERS

DAU = dt.datetime(2026, 7, 10, 1, 0, tzinfo=dt.timezone.utc)
CUOI = dt.datetime(2026, 7, 10, 13, 0, tzinfo=dt.timezone.utc)


def _dung(client, workflow_builder, hau_to, loai_xe_that):
    """Báo giá chốt loại VT-20; xe VEH-T1 thuộc `loai_xe_that`. Trả (mã DO, mã trip, version)."""
    workflow_builder.master_data()
    workflow_builder.quotation(f"QT-{hau_to}", approve=True)
    do_id = f"DO-{hau_to}"
    workflow_builder.delivery_order(do_id, f"QT-{hau_to}", approve=True)

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        for ma, ten in (("VT-20", "Đầu kéo 20'"), ("VT-40", "Đầu kéo 40'")):
            if db.get(models.VehicleType, ma) is None:
                db.add(models.VehicleType(id=ma, name=ten, max_weight=30000,
                                          volume_capacity_m3=70, pallet_capacity=30))
        db.flush()
        q = db.get(models.Quotation, f"QT-{hau_to}")
        q.vehicle_type_id = "VT-20"
        do = db.get(models.DeliveryOrder, do_id)
        do.quotation_id = q.id
        do.pickup_window_start, do.pickup_window_end = DAU, DAU + dt.timedelta(hours=3)
        do.delivery_window_start, do.delivery_window_end = DAU + dt.timedelta(hours=3), CUOI
        xe = db.get(models.Vehicle, "VEH-T1")
        xe.type = loai_xe_that
        tuyen = db.get(models.Route, do.route_id)
        tuyen.distance_km = 40
        tuyen.segments_json = '[{"origin": "Kho A", "destination": "Kho B", "distance_km": 40}]'
        db.commit()

    workflow_builder.san_sang_dieu_phoi(do_id)
    ma_trip = f"TRIP-{hau_to}"
    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": ma_trip, "do_ids": [do_id], "trip_type": "one_way",
        "planned_departure_at": DAU.isoformat(), "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={**API_TEST_HEADERS, "Idempotency-Key": f"trip-{hau_to}"})
    assert r.status_code in (200, 201), r.text
    return do_id, ma_trip, int((r.json().get("data") or {}).get("version") or 1)


def _dieu(client, ma_trip, phien_ban, xac_nhan=None):
    than = {
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": phien_ban,
        "assignment_start": DAU.isoformat(), "assignment_end": CUOI.isoformat(),
    }
    if xac_nhan is not None:
        than["confirm_vehicle_type_mismatch"] = xac_nhan
    return client.put(f"/api/tms/trips/{ma_trip}/dispatch", json=than, headers=API_TEST_HEADERS)


def test_khac_loai_xe_thi_409_va_chuyen_van_cho(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip, v = _dung(client, workflow_builder, "LX1", loai_xe_that="VT-40")
    r = _dieu(client, ma_trip, v)
    assert r.status_code == 409, r.text
    chi_tiet = r.json()["detail"]
    assert chi_tiet["code"] == "VEHICLE_TYPE_MISMATCH"
    assert "20'" in chi_tiet["message"] and "40'" in chi_tiet["message"], chi_tiet["message"]
    trip = client.get(f"/api/tms/trips/{ma_trip}", headers=API_TEST_HEADERS).json()["data"]
    assert trip["status"] == "planned" and trip["vehicle_id"] is None


def test_khac_loai_xe_nhung_da_xac_nhan_thi_dieu_duoc_va_co_nhat_ky(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip, v = _dung(client, workflow_builder, "LX2", loai_xe_that="VT-40")
    r = _dieu(client, ma_trip, v, xac_nhan=True)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "in_transit"
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.query(models.AuditLog).filter(
            models.AuditLog.action == "DISPATCH_TRIP_VEHICLE_TYPE_OVERRIDE",
            models.AuditLog.record_id == ma_trip).count() == 1


def test_dung_loai_xe_thi_di_thang_khong_hoi(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip, v = _dung(client, workflow_builder, "LX3", loai_xe_that="Đầu kéo 20'")  # ghi TÊN, xe cũ còn lưu tên
    r = _dieu(client, ma_trip, v)
    assert r.status_code == 200, r.text
