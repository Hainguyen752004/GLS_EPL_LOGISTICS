# -*- coding: utf-8 -*-
"""Trễ hạn của một chuyến đo theo HẠN KHÁCH, không theo kế hoạch nội bộ.

LỖI ĐO ĐƯỢC TRÊN DỮ LIỆU DEMO (10/09): sáu chuyến đã hoàn tất, giao xong lúc
23:09 trong khi khách cho phép đến 06:29 sáng hôm sau — vẫn bị bảng Chuyến gán
"trễ hạn". Vì bảng so `actual_arrival_at` với `trip.planned_arrival_at`, mà mốc
đó là KẾ HOẠCH do hệ thống tính lúc lập chuyến (xuất bến + km/vận tốc + giờ
dừng), không phải hạn với khách. Hạn với khách nằm trên DO:
`delivery_window_end`.

Bài kiểm khoá ba điều, ngay ở bộ tuần tự hoá chuyến để mọi màn đọc chung:

1. `delivery_due_at` = khung giao muộn nhất của các DO trên chuyến.
2. Tới nơi SAU kế hoạch nhưng TRONG hạn khách -> `is_late=False`,
   `behind_plan_minutes` > 0 (chỉ là lệch kế hoạch).
3. Tới nơi SAU hạn khách -> `is_late=True`, `late_minutes` đúng số phút.
"""
import datetime as dt
import importlib

from conftest import dieu_phoi_qua_chuyen

DAU = dt.datetime(2026, 7, 1, 1, 0, tzinfo=dt.timezone.utc)
HAN_KHACH = dt.datetime(2026, 7, 1, 13, 0, tzinfo=dt.timezone.utc)


def _chuyen(client, workflow_builder, hau_to):
    workflow_builder.master_data()
    workflow_builder.quotation(f"QT-{hau_to}", approve=True)
    do_id = f"DO-{hau_to}"
    workflow_builder.delivery_order(do_id, f"QT-{hau_to}", approve=True)
    ma_trip = dieu_phoi_qua_chuyen(client, do_id, ma_trip=f"TRIP-{hau_to}",
                                   khung_gio=(DAU, HAN_KHACH))
    return do_id, ma_trip


def _tuan_tu_hoa(ma_trip, toi_luc):
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    tms = importlib.import_module("services.tms_trip_service")
    with database.SessionLocal() as db:
        trip = db.get(models.TransportTrip, ma_trip)
        trip.actual_arrival_at = toi_luc
        db.commit()
        return tms.serialize_trip(db, trip)


def test_han_cua_chuyen_la_khung_giao_cua_khach(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip = _chuyen(client, workflow_builder, "HK1")
    p = _tuan_tu_hoa(ma_trip, None)
    assert p["delivery_due_at"] is not None
    assert dt.datetime.fromisoformat(p["delivery_due_at"]) == HAN_KHACH
    # Kế hoạch nội bộ phải SỚM hơn hạn khách — nếu không thì bài kiểm dưới vô nghĩa.
    assert dt.datetime.fromisoformat(p["planned_arrival_at"]) < HAN_KHACH
    assert p["is_late"] is False and p["late_minutes"] is None


def test_toi_sau_ke_hoach_nhung_trong_han_khach_khong_tre(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip = _chuyen(client, workflow_builder, "HK2")
    p0 = _tuan_tu_hoa(ma_trip, None)
    ke_hoach = dt.datetime.fromisoformat(p0["planned_arrival_at"])
    toi = ke_hoach + dt.timedelta(minutes=90)          # chậm kế hoạch 90'
    assert toi < HAN_KHACH
    p = _tuan_tu_hoa(ma_trip, toi)
    assert p["is_late"] is False, p
    assert p["late_minutes"] == 0
    assert p["behind_plan_minutes"] == 90


def test_toi_sau_han_khach_moi_la_tre(app_client, workflow_builder):
    client, _, _ = app_client
    _, ma_trip = _chuyen(client, workflow_builder, "HK3")
    p = _tuan_tu_hoa(ma_trip, HAN_KHACH + dt.timedelta(minutes=25))
    assert p["is_late"] is True, p
    assert p["late_minutes"] == 25
