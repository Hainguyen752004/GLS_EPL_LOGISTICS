# -*- coding: utf-8 -*-
"""Huỷ chuyến vận tải: trả xe, tổ lái và lệnh giao hàng về đúng chỗ.

LỖ HỔNG ĐO ĐƯỢC KHI RÀ SOÁT TRỌN LUỒNG: **không một chỗ nào trong mã nguồn ghi
trạng thái huỷ cho một chuyến**, và không điểm cuối nào cho phép. Nhưng cửa chặn
huỷ lệnh giao hàng lại từ chối khi còn chuyến chưa `completed`/`cancelled` — nên
nhánh `cancelled` của cửa đó không bao giờ tới được. Khách huỷ hàng sau khi đã
lập chuyến thì:

  · huỷ lệnh giao hàng  -> 409 và được chỉ sang màn Chuyến,
  · màn Chuyến          -> không có nút huỷ nào,
  · đường duy nhất còn lại là XOÁ CỨNG lệnh giao hàng trong khi bảng thành viên
    chuyến vẫn trỏ vào nó.

Bốn điều bài kiểm này khoá lại:

1. Huỷ được một chuyến đã điều xe, và **xe cùng tổ lái về sẵn sàng**.
2. Lệnh giao hàng **về `pending`**, không bị xoá — hàng của khách vẫn còn đó.
3. Sau khi huỷ chuyến thì **huỷ được lệnh giao hàng** (nhánh từng không tới được).
4. Chuyến đã có POD hoặc đã giao xong thì **không huỷ được**.
"""
import datetime as dt
import importlib

from conftest import API_TEST_HEADERS

GIO_TAI_CHINH = dict(API_TEST_HEADERS)
GIO_TAI_CHINH["X-Finance-Role"] = "finance_manager"


def _mot_chuyen_da_dieu(client, workflow_builder, hau_to="HUY", dieu_xe=True):
    """Dựng một chuyến qua ĐÚNG đường chuẩn, trả về (mã DO, mã chuyến).

    `dieu_xe=False` thì dừng ở bước ĐÃ LẬP CHUYẾN, chưa gán xe — đúng tình huống
    mà bản rà soát nêu: lập chuyến xong thì khách huỷ hàng.
    """
    workflow_builder.master_data()
    workflow_builder.quotation(f"QT-{hau_to}", approve=True)
    do_id = f"DO-{hau_to}"
    workflow_builder.delivery_order(do_id, f"QT-{hau_to}", approve=True)
    workflow_builder.san_sang_dieu_phoi(do_id)

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    # Khung giờ của lệnh: bước lập chuyến đòi đủ bốn mốc và đòi chúng giao nhau.
    dau = dt.datetime(2026, 6, 1, 1, 0, tzinfo=dt.timezone.utc)
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        do.pickup_window_start = dau
        do.pickup_window_end = dau + dt.timedelta(hours=3)
        do.delivery_window_start = dau + dt.timedelta(hours=3)
        do.delivery_window_end = dau + dt.timedelta(hours=12)
        tuyen = db.get(models.Route, do.route_id)
        tuyen.distance_km = 40
        tuyen.segments_json = (
            '[{"origin": "Kho A", "destination": "Kho B", "distance_km": 40}]'
        )
        db.commit()

    ma_trip = f"TRIP-{hau_to}"
    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": ma_trip, "do_ids": [do_id], "trip_type": "one_way",
        "planned_departure_at": dau.isoformat(), "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={**API_TEST_HEADERS, "Idempotency-Key": f"trip-{hau_to}"})
    assert r.status_code in (200, 201), r.text
    phien_ban = int((r.json().get("data") or {}).get("version") or 1)

    if not dieu_xe:
        return do_id, ma_trip

    r = client.put(f"/api/tms/trips/{ma_trip}/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": phien_ban,
        "assignment_start": dau.isoformat(),
        "assignment_end": (dau + dt.timedelta(hours=12)).isoformat(),
    }, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    return do_id, ma_trip


def _phien_ban_chuyen(client, ma_trip):
    r = client.get(f"/api/tms/trips/{ma_trip}", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    return int((r.json()["data"] or {}).get("version") or 1)


def test_huy_chuyen_tra_xe_to_lai_va_lenh_ve_cho_dieu_phoi(app_client, workflow_builder):
    client, _, _ = app_client
    do_id, ma_trip = _mot_chuyen_da_dieu(client, workflow_builder)

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.get(models.TransportTrip, ma_trip).status == "in_transit"
        assert db.get(models.DeliveryOrder, do_id).canonical_status == "in_transit"
        # Xe và tổ lái đang bị giữ — đúng, chuyến đang chạy.
        assert db.get(models.Vehicle, "VEH-T1").status != "Sẵn sàng"

    r = client.post(f"/api/tms/trips/{ma_trip}/cancel", json={
        "expected_version": _phien_ban_chuyen(client, ma_trip),
        "reason": "Khách rút hàng vì kho bên nhận đầy",
    }, headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-chuyen-1"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "cancelled"

    with database.SessionLocal() as db:
        # 1. Xe và tổ lái VỀ SẴN SÀNG — không bị giữ qua buổi demo.
        assert db.get(models.Vehicle, "VEH-T1").status == "Sẵn sàng"
        tx = db.get(models.Driver, "DRV-T1")
        assert "Rảnh" in tx.status or "sẵn sàng" in tx.status.lower(), tx.status
        assert tx.assigned_vehicle in (None, "", "Chưa gán")

        # 2. Lệnh giao hàng VỀ CHỜ ĐIỀU PHỐI, không bị xoá.
        do = db.get(models.DeliveryOrder, do_id)
        assert do is not None, "huỷ chuyến không được xoá lệnh giao hàng của khách"
        assert do.canonical_status == "pending"
        assert do.vehicle_id in (None, "")
        assert do.driver_id in (None, "")

        # 3. Phân công và chặng đều đóng, nên lịch xe sạch.
        assignments = db.query(models.ResourceAssignment).filter(
            models.ResourceAssignment.trip_id == ma_trip).all()
        assert assignments and all(a.status == "cancelled" for a in assignments)
        legs = db.query(models.TransportTripLeg).filter(
            models.TransportTripLeg.trip_id == ma_trip).all()
        assert legs and all(leg.status == "cancelled" for leg in legs)

    # 4. Lịch xe không còn giữ khoảng của chuyến đã huỷ.
    r = client.get("/api/tms/scheduling/vehicle-availability",
                   params={"start": "2026-06-01T00:00:00+00:00",
                           "end": "2026-06-02T00:00:00+00:00"},
                   headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    dong = r.json()
    dong = dong.get("data") if isinstance(dong, dict) else dong
    assert all(x.get("trip_id") != ma_trip for x in (dong or [])), dong


def test_sau_khi_huy_chuyen_thi_huy_duoc_lenh_giao_hang(app_client, workflow_builder):
    """Nhánh từng KHÔNG BAO GIỜ tới được của cửa chặn huỷ lệnh giao hàng."""
    client, _, _ = app_client
    # Dừng ở bước ĐÃ LẬP CHUYẾN, chưa gán xe: lệnh còn `pending`, nên cửa chặn
    # huỷ lệnh chạy tới đúng nhánh "còn chuyến sống" thay vì bị chặn sớm hơn bởi
    # bảng chuyển trạng thái.
    do_id, ma_trip = _mot_chuyen_da_dieu(client, workflow_builder, hau_to="HUY2",
                                         dieu_xe=False)

    # Còn chuyến sống thì huỷ lệnh bị chặn, và câu báo lỗi phải CHỈ ĐÚNG đường ra.
    r = client.put(f"/api/delivery-orders/{do_id}/status",
                   json={"status": "cancelled", "reason": "khách huỷ (kiểm)"}, headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text
    loi = r.json()["detail"]
    assert loi["code"] == "ACTIVE_TRIP_EXISTS"
    assert ma_trip in loi["message"], loi["message"]
    assert "cancel" in loi["message"], "câu báo lỗi phải nói rõ đường huỷ chuyến"

    r = client.post(f"/api/tms/trips/{ma_trip}/cancel", json={
        "expected_version": _phien_ban_chuyen(client, ma_trip),
        "reason": "Khách huỷ đơn",
    }, headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-chuyen-2"})
    assert r.status_code == 200, r.text

    r = client.put(f"/api/delivery-orders/{do_id}/status",
                   json={"status": "cancelled", "reason": "khách huỷ (kiểm)"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["canonical_status"] == "cancelled"


def test_huy_chuyen_doi_ly_do_va_dung_phien_ban(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip = _mot_chuyen_da_dieu(client, workflow_builder, hau_to="HUY3")
    pb = _phien_ban_chuyen(client, ma_trip)

    # Thiếu lý do: chặn. Người đọc sổ sau này cần biết vì sao xe không chạy.
    r = client.post(f"/api/tms/trips/{ma_trip}/cancel",
                    json={"expected_version": pb, "reason": "  "},
                    headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-thieu-ly-do"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "TRIP_CANCEL_REASON_REQUIRED"

    # Sai phiên bản: chặn, để hai người không ghi đè nhau.
    r = client.post(f"/api/tms/trips/{ma_trip}/cancel",
                    json={"expected_version": pb + 5, "reason": "Khách huỷ"},
                    headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-sai-phien-ban"})
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "VERSION_CONFLICT"

    # Thân có trường lạ: chặn — huỷ chuyến không được âm thầm đổi thứ khác.
    r = client.post(f"/api/tms/trips/{ma_trip}/cancel",
                    json={"expected_version": pb, "reason": "Khách huỷ", "status": "completed"},
                    headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-them-truong"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "TRIP_CANCEL_PAYLOAD_INVALID"

    # Huỷ hai lần cho cùng kết quả: bấm hai lần không phải một lỗi.
    r = client.post(f"/api/tms/trips/{ma_trip}/cancel",
                    json={"expected_version": pb, "reason": "Khách huỷ"},
                    headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-lan-1"})
    assert r.status_code == 200, r.text
    r2 = client.post(f"/api/tms/trips/{ma_trip}/cancel",
                     json={"expected_version": _phien_ban_chuyen(client, ma_trip),
                           "reason": "Khách huỷ"},
                     headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-lan-2"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["status"] == "cancelled"


def test_khong_huy_duoc_chuyen_da_giao_xong(app_client, workflow_builder):
    """POD là bằng chứng của một lần giao thật — huỷ lúc đó là xoá dấu vết."""
    client, _, _ = app_client
    do_id, ma_trip = _mot_chuyen_da_dieu(client, workflow_builder, hau_to="HUY4")

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        # `id` cua bang POD la so tu tang — dung tu dat.
        db.add(models.DeliveryPODRecord(
            do_id=do_id, stop_no=1, vehicle_id="VEH-T1",
            receiver_name="Người nhận", delivery_result="delivered_full",
            delivery_time=dt.datetime(2026, 6, 1, 8, 0, tzinfo=dt.timezone.utc),
        ))
        db.commit()

    r = client.post(f"/api/tms/trips/{ma_trip}/cancel", json={
        "expected_version": _phien_ban_chuyen(client, ma_trip),
        "reason": "Thử huỷ sau khi đã có POD",
    }, headers={**API_TEST_HEADERS, "Idempotency-Key": "huy-co-pod"})
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "TRIP_HAS_POD"

    with database.SessionLocal() as db:
        assert db.get(models.TransportTrip, ma_trip).status == "in_transit"
