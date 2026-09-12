# -*- coding: utf-8 -*-
"""Lệnh vận chuyển DÙNG LẠI phải làm mới khung giờ theo DO — và chỉ khi không còn chuyến sống.

LỖI ĐÃ ĐO TRÊN DỮ LIỆU THẬT (12/09/2026). Lệnh vận chuyển (`freight_orders`) được dùng lại cho
cùng một DO. Lập chuyến lần đầu, nó chốt khung giờ theo DO lúc ấy. Nhưng khi điều độ **huỷ
chuyến, dời ngày lấy hàng trên DO, rồi lập chuyến mới**, nhánh dùng-lại không cập nhật gì cả —
lệnh vận chuyển vẫn giữ khung cũ.

Hậu quả: bước điều xe bị chặn bằng `ASSIGNMENT_OUTSIDE_WINDOW` ("Thời gian điều phối phải nằm
trong khung lấy và giao hàng của chuyến") trong khi màn hình DO ghi đúng ngày mới. Người điều
độ không có cách nào nhìn ra, vì khung sai nằm ở một bản ghi họ không thấy. Đã vấp thật khi
gieo tuyến Viêng Chăn → Cảng Cửa Lò và phải sửa tay trong cơ sở dữ liệu mới đi tiếp được.

Bài này khoá hai nửa, và nửa thứ hai mới là nửa dễ làm hỏng:
  1. Mọi chuyến đã huỷ → lệnh vận chuyển nhận khung MỚI của DO, và trạng thái về `planned`.
  2. Còn một chuyến SỐNG trên lệnh đó → KHÔNG được viết đè: chuyến ấy đã lấy khung cũ làm cơ
     sở cho phân công và cho các mốc đã ghi.
"""
import datetime as dt
import json

import pytest
from sqlalchemy.orm import sessionmaker

from database import Base
from models import DeliveryOrder, FreightOrder, Location, Route, TransportTrip, Vehicle
from services import tms_trip_service as trip_service

NOW = dt.datetime(2026, 8, 13, 8, 0, tzinfo=dt.timezone.utc)


def _san(engine):
    db = sessionmaker(bind=engine)()
    db.add_all([
        Location(id="LOC-A", name="Kho A"),
        Location(id="LOC-B", name="Diem B"),
        Vehicle(id="VH-A", type="Truck", status="San sang"),
    ])
    db.flush()
    db.add(Route(id="RT-1", name="Kho A → Điểm B", distance_km=120,
                 segments_json=json.dumps([{"origin": "Kho A", "destination": "Điểm B",
                                            "distance_km": 120}])))
    db.flush()   # DO trỏ khoá ngoại vào tuyến: tuyến phải xuống CSDL trước
    db.add(DeliveryOrder(
        id="DO-1", route_id="RT-1", origin="Kho A", destination="Điểm B",
        canonical_status="pending", weight_kg=100, volume_m3=1, pallet_count=1,
        pickup_window_start=NOW, pickup_window_end=NOW + dt.timedelta(hours=1),
        delivery_window_start=NOW + dt.timedelta(hours=4),
        delivery_window_end=NOW + dt.timedelta(hours=8)))
    db.commit()
    return db


def _lap(db, ma_trip):
    return trip_service.create_trip_from_delivery_orders(db, {
        "id": ma_trip, "do_ids": ["DO-1"], "trip_type": "one_way",
        "planned_departure_at": NOW, "avg_speed_kmh": "60", "dwell_minutes": 30,
    }, actor="dispatcher")


def _doi_khung_do(db, lech_ngay):
    """Khách dời lịch: đẩy cả bốn mốc của DO đi `lech_ngay` ngày."""
    do = db.get(DeliveryOrder, "DO-1")
    d = dt.timedelta(days=lech_ngay)
    do.pickup_window_start += d
    do.pickup_window_end += d
    do.delivery_window_start += d
    do.delivery_window_end += d
    db.flush()


def _khung(fo):
    return (fo.pickup_window_start, fo.pickup_window_end,
            fo.delivery_window_start, fo.delivery_window_end)


def test_huy_chuyen_roi_lap_lai_thi_lenh_van_chuyen_nhan_khung_moi(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    db = _san(engine)

    t1 = _lap(db, "TRIP-1")
    fo_id = t1["freight_order_id"]
    fo = db.get(FreightOrder, fo_id)
    khung_cu = _khung(fo)
    assert khung_cu[0] == NOW.replace(tzinfo=None), "khung ban đầu phải theo DO, lưu UTC trần"

    # Chuyến đó bị huỷ, rồi khách dời lịch 3 ngày.
    trip_service.cancel_trip(db, "TRIP-1", {"expected_version": t1["version"],
                                            "reason": "Khách dời ngày lấy hàng"}, actor="dispatcher")
    fo.status = "dispatched"          # chuyến trước đã điều rồi mới huỷ
    db.flush()
    _doi_khung_do(db, 3)

    t2 = _lap(db, "TRIP-2")
    assert t2["freight_order_id"] == fo_id, "cùng một DO thì dùng lại đúng lệnh vận chuyển đó"

    db.refresh(fo)
    do = db.get(DeliveryOrder, "DO-1")
    assert _khung(fo) == (do.pickup_window_start.replace(tzinfo=None),
                          do.pickup_window_end.replace(tzinfo=None),
                          do.delivery_window_start.replace(tzinfo=None),
                          do.delivery_window_end.replace(tzinfo=None)), \
        "lệnh vận chuyển vẫn giữ khung cũ — điều xe sẽ bị chặn ASSIGNMENT_OUTSIDE_WINDOW"
    assert _khung(fo) != khung_cu
    assert fo.status == "planned", "mọi chuyến đã huỷ thì lệnh vận chuyển về lại bản kế hoạch"
    db.close()
    engine.dispose()


def test_con_chuyen_song_thi_KHONG_viet_de_khung_cua_lenh_van_chuyen(tmp_path, may_kiem):
    """Nửa quan trọng hơn: một chuyến đang sống đã lấy khung đó làm cơ sở cho phân công và cho
    mọi mốc đã ghi. Viết đè là đổi luật giữa cuộc, và các mốc đã ghi thành nằm ngoài khung của
    chính chúng."""
    engine = may_kiem()
    Base.metadata.create_all(engine)
    db = _san(engine)

    t1 = _lap(db, "TRIP-1")
    fo = db.get(FreightOrder, t1["freight_order_id"])
    khung_cu = _khung(fo)

    # TRIP-1 vẫn sống (chưa huỷ). Khách dời lịch, rồi lập thêm một chuyến nữa cho cùng DO.
    _doi_khung_do(db, 3)
    _lap(db, "TRIP-2")

    db.refresh(fo)
    assert _khung(fo) == khung_cu, "còn chuyến sống mà đã viết đè khung của lệnh vận chuyển"
    db.close()
    engine.dispose()


def test_huy_het_roi_lap_lai_thi_khoi_luong_cung_theo_DO_moi(tmp_path, may_kiem):
    """Khung giờ không phải thứ duy nhất đi theo DO: khai lại khối lượng thì sức chở phải theo,
    nếu không cửa gác `CAPACITY_EXCEEDED` đo trên một con số đã cũ."""
    engine = may_kiem()
    Base.metadata.create_all(engine)
    db = _san(engine)

    t1 = _lap(db, "TRIP-1")
    fo = db.get(FreightOrder, t1["freight_order_id"])
    assert float(fo.total_weight_kg) == 100

    trip_service.cancel_trip(db, "TRIP-1", {"expected_version": t1["version"],
                                            "reason": "Khách khai lại hàng"}, actor="dispatcher")
    do = db.get(DeliveryOrder, "DO-1")
    do.weight_kg = 4200
    do.volume_m3 = 12
    db.flush()

    _lap(db, "TRIP-2")
    db.refresh(fo)
    assert float(fo.total_weight_kg) == 4200
    assert float(fo.total_volume_m3) == 12
    assert float(fo.max_weight_kg) == 4200
    db.close()
    engine.dispose()
