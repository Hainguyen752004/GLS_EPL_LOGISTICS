# -*- coding: utf-8 -*-
"""Một chuyến nhiều ngày phải KHOÁ lịch xe, tài xế và phụ xe TRỌN hành trình.

Câu hỏi của chủ dự án: *"một chiếc xe bị điều đi, ví dụ chuyến 3 ngày từ 7 giờ
sáng ngày 1 đến 3 giờ chiều ngày 3 nó mới về, thì trong khoảng nó đi có báo khoá
lịch không cho sắp xếp chưa — cả bên tài xế và phụ xế cũng tương tự"*.

Đo trước khi sửa: bảng xếp ca đọc `planned_arrival_at` (giờ TỚI NƠI GIAO) làm
mốc kết thúc, nên chặng về không khoá — xe và tổ lái hiện "rảnh" trong khi
đang trên đường về. Cửa GHI (lưu ca tay) thì đã chặn đúng theo phân công
`ResourceAssignment` [xuất bến, về bãi).

Bài kiểm dựng đúng ví dụ của anh (giờ Việt Nam, +07):
  · xuất bến 07:00 ngày 24/08, tới nơi 10:00 ngày 25/08, về bãi 15:00 ngày 26/08
và khoá lại:
  1. lưới XE: ngày 24 (ca sáng/chiều/đêm), cả ngày 25, ngày 26 ca sáng + chiều
     là ô Trip; ca đêm ngày 26 và ngày 27 rảnh;
  2. lưới NGƯỜI: tài xế VÀ phụ xe cùng những ô đó ở trạng thái `lock`;
  3. lưu ca tay cho phụ xe / gán xe ngày 26 (ngày về) bị từ chối.
"""
import datetime as dt

import pytest
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (Driver, FreightOrder, Location, ResourceAssignment, TransportTrip,
                    Vehicle)
from services import sap_lich_service, tms_scheduling_service

# 07:00 +07 = 00:00 UTC; 15:00 +07 = 08:00 UTC.
DI = dt.datetime(2026, 8, 24, 0, 0)
TOI = dt.datetime(2026, 8, 25, 3, 0)
VE = dt.datetime(2026, 8, 26, 8, 0)


@pytest.fixture
def db(may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Vehicle(id="VEH-3N", type="Truck", status="busy"),
        Driver(id="DRV-LAI", name="Tài xế chính", status="busy"),
        Driver(id="DRV-PHU", name="Phụ xe", status="busy"),
        Location(id="SC-A", name="Kho A"),
        Location(id="SC-B", name="Kho B"),
    ])
    session.flush()
    session.add(FreightOrder(
        id="FO-3N", pickup_location_id="SC-A", delivery_location_id="SC-B",
        pickup_window_start=DI, pickup_window_end=DI + dt.timedelta(hours=3),
        delivery_window_start=TOI - dt.timedelta(hours=2), delivery_window_end=VE,
        total_weight_kg=1000, total_volume_m3=5, total_pallet_count=2,
        max_weight_kg=3000, max_volume_m3=20, max_pallet_count=10, status="dispatched",
    ))
    session.flush()
    session.add(TransportTrip(
        id="TRIP-3N", freight_order_id="FO-3N", trip_type="round_trip", status="in_transit",
        vehicle_id="VEH-3N", driver_id="DRV-LAI", co_driver_id="DRV-PHU",
        planned_departure_at=DI, planned_arrival_at=TOI, planned_return_at=VE,
    ))
    session.flush()
    session.add(ResourceAssignment(
        freight_order_id="FO-3N", trip_id="TRIP-3N", vehicle_id="VEH-3N",
        driver_id="DRV-LAI", co_driver_id="DRV-PHU",
        assignment_start=DI, assignment_end=VE, status="active",
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _o(cac_ngay, ngay, ca):
    d = next(x for x in cac_ngay if x["ngay"] == ngay)
    return next(o for o in d["cac_o"] if o["ca"] == ca)


# Ô phải khoá (ngày, ca) và ô phải rảnh, theo ví dụ 07:00 ngày 1 -> 15:00 ngày 3.
KHOA = [("2026-08-24", "morning"), ("2026-08-24", "afternoon"), ("2026-08-24", "night"),
        ("2026-08-25", "morning"), ("2026-08-25", "afternoon"), ("2026-08-25", "night"),
        ("2026-08-26", "morning"), ("2026-08-26", "afternoon")]
RANH = [("2026-08-26", "night"), ("2026-08-27", "morning"), ("2026-08-23", "afternoon")]


def test_luoi_xe_khoa_den_luc_xe_ve_bai(db):
    bang = sap_lich_service.bang_sap_lich(db, "2026-08-23", 7)
    xe = next(v for v in bang["xe"] if v["vehicle_id"] == "VEH-3N")
    for ngay, ca in KHOA:
        o = _o(xe["cac_ngay"], ngay, ca)
        assert o["trip_id"] == "TRIP-3N", (ngay, ca, o)
    for ngay, ca in RANH:
        assert _o(xe["cac_ngay"], ngay, ca)["trip_id"] is None, (ngay, ca)


@pytest.mark.parametrize("ma_nguoi", ["DRV-LAI", "DRV-PHU"])
def test_luoi_nguoi_khoa_ca_tai_xe_va_phu_xe_tron_hanh_trinh(db, ma_nguoi):
    bang = sap_lich_service.bang_sap_lich(db, "2026-08-23", 7)
    nguoi = next(p for p in bang["nhan_su"] if p["driver_id"] == ma_nguoi)
    for ngay, ca in KHOA:
        o = _o(nguoi["cac_ngay"], ngay, ca)
        assert o["trang_thai"] == "lock" and o["trip_id"] == "TRIP-3N", (ma_nguoi, ngay, ca, o)
    for ngay, ca in RANH:
        assert _o(nguoi["cac_ngay"], ngay, ca)["trang_thai"] != "lock", (ma_nguoi, ngay, ca)


@pytest.mark.parametrize("ma_nguoi", ["DRV-LAI", "DRV-PHU"])
def test_khong_xep_duoc_ca_cho_to_lai_trong_ngay_xe_dang_ve(db, ma_nguoi):
    with pytest.raises(Exception) as loi:
        tms_scheduling_service.save_driver_shift(db, {
            "id": f"CA-{ma_nguoi}", "driver_id": ma_nguoi, "shift_type": "morning",
            "shift_start": "2026-08-25T23:00:00Z", "shift_end": "2026-08-26T07:00:00Z",
            "status": "planned",
        })
    assert getattr(loi.value, "code", None) == "DRIVER_ACTIVE_TRIP_OVERLAP"


def test_khong_gan_duoc_xe_cho_nguoi_khac_truoc_khi_xe_ve(db):
    db.add(Driver(id="DRV-KHAC", name="Người khác", status="ready"))
    db.commit()
    with pytest.raises(Exception) as loi:
        tms_scheduling_service.save_driver_shift(db, {
            "id": "CA-XE-VE", "driver_id": "DRV-KHAC", "vehicle_id": "VEH-3N",
            "shift_type": "morning",
            "shift_start": "2026-08-25T23:00:00Z", "shift_end": "2026-08-26T07:00:00Z",
            "status": "planned",
        })
    assert getattr(loi.value, "code", None) == "VEHICLE_ACTIVE_TRIP_OVERLAP"
