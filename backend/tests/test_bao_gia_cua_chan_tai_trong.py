# -*- coding: utf-8 -*-
"""CUA CHAN TAI TRONG cua buoc bao gia — mot lo that da bit lai.

VI SAO CAN NHUNG BAI NAY. Cua chan `require_quotation_vehicle_capacity` da co
tu truoc va duoc goi o ba cho (tao, sua, duyet). Nhung no tra loai xe ra bang
`find_vehicle_type(data["cargo_type"])`, va do la cach dung voi man Bao gia CU:
man do dung MOT o vua chon loai hang vua chon loai xe.

Man Bao gia MOI tach hai thu ra — `cargo_type` giu loai HANG ("Hang kho",
"Kien roi"), loai xe nam trong `vehicle_type_id`. Nen cua chan khong tra ra loai
xe nao va LANG LE `return None`. Da do bang cach goi thang
`POST /api/quotations` voi `vehicle_type_id=<xe lanh 5 tan>` va 20.000 kg: may
chu NHAN. Cung lo hang do gui qua `cargo_type` thi bi chan 409 dung nhu mong doi.

Mot cua chan CO MA KHONG BAT thi te hon khong co: no lam moi nguoi tin rang
duong nay da duoc kiem.

Hai bai duoi day chot hai mat cua cai lo do, va mot bai thu ba chot chieu nguoc
lai (lo hang vua xe thi KHONG bi chan oan) — thieu bai thu ba thi hai bai tren
van xanh ke ca khi cua chan chan tat ca.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Customer, Location, Quotation, Route, VehicleType
from services.errors import DomainError


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'bao_gia_suc_cho.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([Location(id="L-A", name="Kho A"), Location(id="L-B", name="Kho B")])
    session.add(Customer(id="CUS-SC", name="Khach kiem suc cho"))
    session.add(Route(id="RT-SC", name="Tuyen kiem suc cho", distance_km=100, segments_json="[]"))
    # Xe lanh nho: 5 tan / 22 m3 / 8 pallet — dung con so cua bo du lieu demo.
    session.add(VehicleType(id="VT-NHO", name="Xe lanh 5 tan", max_weight=5000,
                            volume_capacity_m3=22, pallet_capacity=8))
    session.add(VehicleType(id="VT-LON", name="Dau keo 40", max_weight=30000,
                            volume_capacity_m3=67, pallet_capacity=24))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _bao_gia(db, loai_xe, **ghi_de):
    """Mot bao gia SAN SANG GUI: co han, co ca gia thanh lan cuoc thu.

    Phai co du hai con so vi `kiem_bao_gia_truoc_khi_duyet` chay TRUOC cua chan
    tai trong — thu tu do co chu y: het han va lo la hai ly do nguoi dung sua
    duoc ngay tren form, con tai trong thi phai doi loai xe. Thieu gia thanh thi
    bai kiem dung o `QUOTATION_MARGIN_UNKNOWN` va khong bao gio cham tay vao cua
    chan can kiem.
    """
    goi = dict(
        id="QT-SC-1", customer_id="CUS-SC", route_id="RT-SC",
        vehicle_type_id=loai_xe, cargo_type="Hang kho",
        weight_kg=20000, volume_m3=40, pallet_count=20,
        total_cost=5000000, selling_price=9000000,
        valid_to=(dt.date.today() + dt.timedelta(days=30)).isoformat(),
        canonical_status="draft", status="Nhap",
    )
    goi.update(ghi_de)
    q = Quotation(**goi)
    db.add(q)
    db.flush()
    return q


def test_tao_bao_gia_bi_chan_khi_loai_xe_gui_qua_vehicle_type_id_khong_du_tai(db):
    """Cai lo chinh: man moi gui loai xe trong `vehicle_type_id`."""
    from services.vehicle_recommendation_service import require_quotation_vehicle_capacity
    with pytest.raises(Exception) as loi:
        require_quotation_vehicle_capacity(db, {
            "vehicle_type_id": "VT-NHO",
            "cargo_type": "Hang kho",          # loai HANG, khong phai loai xe
            "weight_kg": 20000, "volume_m3": 40, "pallet_count": 20,
        })
    assert getattr(loi.value, "code", None) == "CAPACITY_EXCEEDED"
    # Thong bao phai NOI RO CON SO cua ca ba chieu vuot, khong noi chung.
    chu = str(getattr(loi.value, "message", loi.value))
    assert "20000/5000" in chu
    assert "40/22" in chu
    assert "20/8" in chu


def test_duong_cu_qua_cargo_type_van_chan(db):
    """Sua cho man moi KHONG duoc lam vo duong cu.

    Du lieu cu va man cu van dat ten loai xe trong `cargo_type`.
    """
    from services.vehicle_recommendation_service import require_quotation_vehicle_capacity
    with pytest.raises(Exception) as loi:
        require_quotation_vehicle_capacity(db, {
            "cargo_type": "Xe lanh 5 tan",
            "weight_kg": 20000, "volume_m3": 40, "pallet_count": 20,
        })
    assert getattr(loi.value, "code", None) == "CAPACITY_EXCEEDED"


def test_lo_hang_vua_xe_thi_khong_bi_chan(db):
    """Chieu nguoc lai. Thieu bai nay thi hai bai tren van xanh ke ca khi cua
    chan chan TAT CA moi bao gia."""
    from services.vehicle_recommendation_service import require_quotation_vehicle_capacity
    loai_xe = require_quotation_vehicle_capacity(db, {
        "vehicle_type_id": "VT-LON",
        "weight_kg": 20000, "volume_m3": 40, "pallet_count": 20,
    })
    assert loai_xe is not None and loai_xe.id == "VT-LON"


def test_gui_khach_chan_khi_suc_cho_bi_ha_sau_khi_da_nhap(db):
    """Cua chan phai ap lai o DIEM KHONG QUAY LAI DUOC, khong chi luc nhap.

    Suc cho la DU LIEU GOC. Nguoi dung ha `max_weight` cua mot loai xe o man Du
    lieu goc thi moi ban nhap dang cho gui deu doi trang thai ma khong ai cham
    vao chung. Neu chi kiem luc tao/sua thi nhung ban nhap do di thang ra khach.
    """
    from services import bao_gia_service
    q = _bao_gia(db, "VT-LON")          # 20 tan tren dau keo 30 tan: vua

    # Nguoi dung ha suc cho loai xe do xuong 1 tan.
    db.query(VehicleType).filter(VehicleType.id == "VT-LON").first().max_weight = 1000
    db.flush()

    with pytest.raises(Exception) as loi:
        bao_gia_service.gui_khach(db, q.id, "nguoi-ban")
    assert getattr(loi.value, "code", None) == "CAPACITY_EXCEEDED"
    # Va bao gia PHAI o nguyen trang thai nhap — chan nghia la khong doi gi.
    db.refresh(q)
    assert q.canonical_status == "draft"


def test_gui_khach_di_duoc_khi_loai_xe_du_tai(db):
    """Chieu nguoc lai cho duong gui: du tai thi gui duoc."""
    from services import bao_gia_service
    q = _bao_gia(db, "VT-LON")
    ket_qua = bao_gia_service.gui_khach(db, q.id, "nguoi-ban")
    assert ket_qua.canonical_status in ("sent", "pending_approval")


def test_duyet_noi_bo_cung_chan(db):
    """Duong duyet noi bo la duong con lai di ra khoi ban nhap — cung phai chan."""
    from services import bao_gia_service
    q = _bao_gia(db, "VT-LON", canonical_status="pending_approval", status="Cho duyet noi bo")
    db.query(VehicleType).filter(VehicleType.id == "VT-LON").first().max_weight = 1000
    db.flush()
    with pytest.raises(Exception) as loi:
        bao_gia_service.duyet_noi_bo(db, q.id, "truong-phong")
    assert getattr(loi.value, "code", None) == "CAPACITY_EXCEEDED"
