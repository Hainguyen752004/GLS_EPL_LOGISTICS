"""Moc ghi qua API phai GAN vao chuyen, khong duoc de mo côi.

LOI DA XAY RA THAT, va no am tham. Bang `transport_events` co cot `trip_id`, va
cac man hinh doc su kien THEO CHUYEN — thap kiem soat cua man "Theo doi va kiem
soat" gom su kien bang `TransportEvent.trip_id.in_(...)`. Nhung duong ghi su kien
(`record_event`) khong dien cot do, nen moi moc ghi tu giao dien deu co `trip_id`
rong.

Hau qua do duoc tren man hinh that: bam nut "Ghi mốc: Đến điểm giao" thi don DOI
trang thai sang `arrived` dung nhu mong doi va nut POD mo ra — nhung buoc "Đến
điểm giao" tren truc tien do van hien la "dang cho ghi". Nguoi truc bam lai, va
lan nay may chu tra ve EVENT_ALREADY_RECORDED. Tu goc nhin cua ho thi he thong
tu mau thuan: no vua noi chua ghi, vua noi da ghi.

Nen tep nay khoa ba dieu:

  1. Ghi mot moc thi `trip_id` duoc dien, va dien dung chuyen cua lenh.
  2. Chuyen da huy thi KHONG duoc chon.
  3. Lenh chua co chuyen nao thi van ghi duoc moc, `trip_id` de rong.
"""

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    Driver,
    FreightOrder,
    Location,
    ResourceAssignment,
    TransportTrip,
    Vehicle,
)
from services import tms_execution_service as service


LUC = dt.datetime.utcnow().replace(microsecond=0) - dt.timedelta(hours=1)


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Location(id="A", name="Kho A"),
        Location(id="B", name="Kho B"),
        Vehicle(id="51C-001", type="Truck"),
        Driver(id="DRV-001", name="Tai xe Mot"),
    ])
    # Dữ liệu gốc phải VÀO TRƯỚC: `FreightOrder.pickup_location_id` khai
    # `ForeignKey` mà không khai `relationship()`, và SQLAlchemy xếp thứ tự chèn
    # theo relationship chứ không theo cột khoá ngoại trần — thiếu nó thì nó xếp
    # theo tên bảng và `freight_orders` đi trước `locations`.
    session.flush()
    session.add(FreightOrder(
        id="FO-GAN-1", pickup_location_id="A", delivery_location_id="B",
        pickup_window_start=LUC, pickup_window_end=LUC + dt.timedelta(hours=1),
        delivery_window_start=LUC + dt.timedelta(hours=4),
        delivery_window_end=LUC + dt.timedelta(hours=8),
        total_weight_kg=1, total_volume_m3=1, total_pallet_count=1,
        max_weight_kg=2, max_volume_m3=2, max_pallet_count=2,
        status="dispatched", version=2,
    ))
    session.flush()
    session.add(ResourceAssignment(
        freight_order_id="FO-GAN-1", vehicle_id="51C-001", driver_id="DRV-001",
        assignment_start=LUC - dt.timedelta(hours=1),
        assignment_end=LUC + dt.timedelta(hours=10), status="active",
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _chuyen(db, ma, trang_thai="in_transit", lech_phut=0):
    db.add(TransportTrip(
        id=ma, freight_order_id="FO-GAN-1", trip_type="one_way", status=trang_thai,
        created_at=LUC + dt.timedelta(minutes=lech_phut),
    ))
    db.commit()


def _moc(loai="check_in"):
    return {
        "event_type": loai, "event_time": LUC, "expected_version": 2,
        "vehicle_id": "51C-001", "driver_id": "DRV-001",
        "lat": 10.8231, "lng": 106.6297, "speed_kmh": 0, "distance_km": 0,
        "location_text": "Kho A", "source": "manual", "device_id": None,
        "reason": None, "note": None, "documents": [],
    }


def test_moc_ghi_qua_api_duoc_gan_vao_chuyen_cua_lenh(db):
    """Phep kiem chinh: khong co dong nay thi truc tien do khong thay moc vua ghi."""
    _chuyen(db, "TRIP-GAN-1")
    su_kien = service.record_event(db, "FO-GAN-1", _moc(), "khoa-1", "dispatcher")
    assert su_kien.trip_id == "TRIP-GAN-1", "moc phai noi ra no thuoc chuyen nao"


def test_chuyen_DA_HUY_thi_khong_duoc_chon(db):
    """Gan vao chuyen da huy con te hon de rong: no bao mot chuyen khong con chay."""
    _chuyen(db, "TRIP-HUY", trang_thai="cancelled", lech_phut=10)
    _chuyen(db, "TRIP-DANG-CHAY", trang_thai="in_transit", lech_phut=0)
    su_kien = service.record_event(db, "FO-GAN-1", _moc(), "khoa-2", "dispatcher")
    assert su_kien.trip_id == "TRIP-DANG-CHAY"


def test_nhieu_chuyen_thi_lay_chuyen_MOI_NHAT(db):
    """Chay lai hoac doi xe thi lenh co nhieu chuyen; moc thuoc chuyen dang chay."""
    _chuyen(db, "TRIP-CU", lech_phut=0)
    _chuyen(db, "TRIP-MOI", lech_phut=30)
    su_kien = service.record_event(db, "FO-GAN-1", _moc(), "khoa-3", "dispatcher")
    assert su_kien.trip_id == "TRIP-MOI"


def test_lenh_chua_co_chuyen_thi_van_ghi_duoc_moc(db):
    """Cot la co the rong, nen thieu chuyen KHONG duoc lam vo duong ghi su kien.

    Neu ham nay nem loi khi khong tim thay chuyen thi mot lenh vua phan cong ma
    chua len chuyen se khong check-in duoc — chan dung ca luong tu buoc dau.
    """
    su_kien = service.record_event(db, "FO-GAN-1", _moc(), "khoa-4", "dispatcher")
    assert su_kien.trip_id is None


def test_moc_ARRIVAL_dua_DO_sang_ARRIVED_qua_duong_chuyen_lap_tu_DO(db):
    """Xe bao "arrival" thi DO cua chuyen phai sang `arrived` — qua `trip_delivery_orders`.

    LOI DA DO DUOC khi gieo du lieu demo: ghi du 4 moc (co `arrival`) cho mot
    chuyen lap tu lenh giao hang, DO van `in_transit`. `_dong_bo_moc_do` chi tra
    DO qua `freight_order_legacy_links` — cau noi cho don CU — trong khi moi
    chuyen lap tu DO noi qua `transport_trips.freight_order_id` ->
    `trip_delivery_orders`. Tuc duong "GPS tu bao den noi" chua bao gio chay
    trong luong that, va hang doi "da den, cho POD" cua man Hoan tat luon trong.
    """
    from models import DeliveryOrder, TripDeliveryOrder

    db.add(DeliveryOrder(id="DO-GAN-1", canonical_status="in_transit", status="Đang vận chuyển",
                         vehicle_id="51C-001", driver_id="DRV-001"))
    db.flush()
    _chuyen(db, "TRIP-GAN-DEN")
    db.add(TripDeliveryOrder(trip_id="TRIP-GAN-DEN", do_id="DO-GAN-1"))
    db.commit()

    # Di dung TRINH TU moc cua chuyen hang (`EVENT_SEQUENCE_INVALID` neu nhay
    # coc), va moi moc lam phien ban lenh tang — doc lai phien ban sau tung moc.
    # Ba moc truoc `arrival` KHONG duoc dong DO.
    for i, loai in enumerate(("check_in", "pickup", "departure")):
        moc = _moc(loai)
        moc["expected_version"] = db.get(FreightOrder, "FO-GAN-1").version
        service.record_event(db, "FO-GAN-1", moc, "khoa-den-%d" % i, "dispatcher")
        db.commit()
        assert db.get(DeliveryOrder, "DO-GAN-1").canonical_status == "in_transit", loai

    moc = _moc("arrival")
    moc["expected_version"] = db.get(FreightOrder, "FO-GAN-1").version
    service.record_event(db, "FO-GAN-1", moc, "khoa-den-9", "dispatcher")
    db.commit()
    do = db.get(DeliveryOrder, "DO-GAN-1")
    assert do.canonical_status == "arrived", do.canonical_status
    assert do.status == "Đã đến nơi — chờ POD"
