"""Toa do dia diem — ba tang tra, va chot chan mot toa do SAI CHO.

VAN DE DA CO. So do lo trinh cua man Tuyen duong ve duoc hay khong phu thuoc
mot dieu: co biet diem di va diem den o dau. Truoc day cau tra loi nam o hai
cho, va ca hai sai cho: mot bang Python cung (chi biet muoi bon dia diem cua bo
du lieu demo), va mot loi goi ra `nominatim.openstreetmap.org` TU TRINH DUYET.
Do duoc tren mang cua du an: host do khong toi duoc, nen o ban do trang tron.

Tep nay khoa bon dieu, va dieu thu tu la dieu quan trong nhat:

  1. Toa do doc tu bang `locations` truoc moi thu khac.
  2. Bang moi trong ma nguon duoc GHI vao `locations` lan dau dung, nen tu do
     no la du lieu sua duoc chu khong phai mot dong trong ma nguon.
  3. Toa do nguoi dung da khai TAY khong bao gio bi may ghi de.
  4. Mot toa do do dich vu ngoai DOAN ma khong khop so km nguoi dung khai thi
     bi LOAI, va ten diem do duoc noi ra.

Diem 4 la mot loi da xay ra that: ten noi bo "Bai tap ket noi bo so 7 EPL"
duoc mot dich vu tra toa do nhan va tra ve mot diem o Bac Ninh — nam TRONG Viet
Nam nen phep kiem hop ranh khong bat duoc — va ban do dat mot chang 12 km thanh
mot duong 1.600 km chay suot ca nuoc. Mot diem sai cho ma khong canh bao gi te
hon han mot o ban do trong: nguoi dung tin vao no.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Location
from services import toa_do_diem


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'toado.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Location(id="LOC-CATLAI", name="Cảng Cát Lái, TP. Thủ Đức", type="Port"),
        Location(id="LOC-SONGTHAN", name="Bãi Sóng Thần", type="Warehouse"),
        Location(id="LOC-RIENG", name="Kho Riêng Của Đội", type="Warehouse",
                 latitude=10.5, longitude=106.5),
    ])
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_bang_dia_diem_duoc_doc_TRUOC_moi_thu_khac(db):
    """Nguoi khai thang mau, va thang ca dich vu ngoai.

    Khong co thu tu nay thi mot toa do nguoi dung sua tay se bi mot con so may
    doan de len, va ho khong hieu vi sao sua khong an.
    """
    diem, nguon = toa_do_diem.toa_do_day_du(db, "Kho Riêng Của Đội", cho_phep_ngoai=False)
    assert diem == (10.5, 106.5)
    assert nguon == "bang"


def test_bang_moi_duoc_GHI_vao_bang_dia_diem_lan_dau_dung(db):
    """Bang moi trong ma nguon khong phai co che — no chi la diem khoi dau.

    Ghi vao `locations` thi tu lan sau toa do do sua duoc nhu moi du lieu goc
    khac, khong con phai sua ma nguon va phat hanh lai.
    """
    truoc = db.get(Location, "LOC-SONGTHAN")
    assert truoc.latitude is None, "bo du lieu thu phai bat dau tu o trong"

    diem, nguon = toa_do_diem.toa_do_day_du(db, "Bãi Sóng Thần", cho_phep_ngoai=False)
    assert nguon == "moi"
    assert diem == toa_do_diem.DIEM_THAM_CHIEU["bai song than"]

    sau = db.get(Location, "LOC-SONGTHAN")
    assert (sau.latitude, sau.longitude) == diem, "phai ghi lai vao bang dia diem"


def test_diem_khong_ai_biet_thi_tra_None_chu_khong_doan(db):
    """Khong doan bua mot diem giua ban do.

    `cho_phep_ngoai=False` de bai kiem khong goi ra Internet — mot bai kiem phu
    thuoc mang la mot bai kiem do ngau nhien.
    """
    diem, nguon = toa_do_diem.toa_do_day_du(db, "Kho Không Ai Từng Nghe", cho_phep_ngoai=False)
    assert diem is None and nguon is None


def test_toa_do_KHAI_TAY_khong_bi_ghi_de(db):
    chang = [{
        "from": "Bãi Sóng Thần", "to": "Cảng Cát Lái", "dist_km": 31,
        # Nguoi dung tu dat diem di lech mot chut — day la quyet dinh cua ho.
        "from_lat": 10.8000, "from_lng": 106.7000,
    }]
    ra, thieu = toa_do_diem.gan_toa_do_cho_chang_db(db, chang, cho_phep_ngoai=False)
    assert (ra[0]["from_lat"], ra[0]["from_lng"]) == (10.8000, 106.7000)
    assert thieu == []


def test_toa_do_DICH_VU_NGOAI_khong_khop_KM_thi_bi_loai(db, monkeypatch):
    """PHEP KIEM QUAN TRONG NHAT CUA TEP.

    Mot chang khai 12 km ma hai diem cach nhau 1.600 km thi mot trong hai diem
    sai. Doi chieu voi con so KM NGUOI DUNG KHAI — khong voi mot danh sach ten
    — nen phep kiem nay dung cho ca nhung dia diem chua ai nghe ten.
    """
    # Gia lap dich vu ngoai tra ve mot diem o Bac Ninh, dung nhu da xay ra that.
    monkeypatch.setattr(toa_do_diem, "tra_ngoai",
                        lambda nhan, ghi_log=None: (21.0380762, 106.2671152))
    chang = [{"from": "Bãi tập kết nội bộ số 7 EPL", "to": "Cảng Cát Lái", "dist_km": 12}]
    ra, thieu = toa_do_diem.gan_toa_do_cho_chang_db(db, chang, cho_phep_ngoai=True)

    assert "from_lat" not in ra[0], "diem vo ly phai bi loai, khong duoc ve len ban do"
    assert thieu == ["Bãi tập kết nội bộ số 7 EPL"], "phai NOI RA diem nao chua biet"
    # Diem tot cua chang van phai duoc giu: bo ca hai thi mot ten sai lam mat
    # luon diem dung ben canh.
    assert ra[0]["to_lat"] == toa_do_diem.DIEM_THAM_CHIEU["cang cat lai"][0]


def test_toa_do_vo_ly_bi_XOA_khoi_bang_dia_diem(db, monkeypatch):
    """Khong xoa thi phep kiem km chi cuu duoc lan dau.

    Toa do sai da ghi vao `locations` se duoc tra ve o tang 1 tu lan sau — tang
    duoc TIN va khong bi kiem lai nua.
    """
    monkeypatch.setattr(toa_do_diem, "tra_ngoai",
                        lambda nhan, ghi_log=None: (21.0380762, 106.2671152))
    db.add(Location(id="LOC-BAI7", name="Bãi tập kết nội bộ số 7 EPL", type="Warehouse"))
    db.commit()

    chang = [{"from": "Bãi tập kết nội bộ số 7 EPL", "to": "Cảng Cát Lái", "dist_km": 12}]
    toa_do_diem.gan_toa_do_cho_chang_db(db, chang, cho_phep_ngoai=True)

    sau = db.get(Location, "LOC-BAI7")
    assert sau.latitude is None and sau.longitude is None, \
        "toa do vo ly phai bi xoa, neu khong lan sau no duoc tin o tang 1"


def test_chang_DAI_THAT_thi_van_qua_phep_kiem_km(db, monkeypatch):
    """Phep kiem khong duoc chan mot tuyen dai co that.

    Da Nang -> Quy Nhon la 300 km duong bo va khoang 190 km duong chim bay —
    phai qua. Mot phep kiem chan ca truong hop dung thi nguoi dung se tat no.
    """
    diem = {"Cảng Tiên Sa, Đà Nẵng": (16.119709, 108.2171737),
            "Cảng Quy Nhơn": (13.7787437, 109.2424598)}
    monkeypatch.setattr(toa_do_diem, "tra_ngoai", lambda nhan, ghi_log=None: diem.get(nhan))
    chang = [{"from": "Cảng Tiên Sa, Đà Nẵng", "to": "Cảng Quy Nhơn", "dist_km": 300}]
    ra, thieu = toa_do_diem.gan_toa_do_cho_chang_db(db, chang, cho_phep_ngoai=True)
    assert thieu == []
    assert ra[0]["from_lat"] == pytest.approx(16.119709)
    assert ra[0]["to_lat"] == pytest.approx(13.7787437)


def test_khong_khai_km_thi_khong_co_gi_doi_chieu_nen_van_nhan(db, monkeypatch):
    """Chang khong khai km thi phep kiem phai IM, khong duoc chan.

    Chan khi thieu du lieu doi chieu la bien mot phep kiem thanh mot rao can:
    nguoi dung chua kip nhap km da khong ve duoc ban do.
    """
    monkeypatch.setattr(toa_do_diem, "tra_ngoai",
                        lambda nhan, ghi_log=None: (21.0380762, 106.2671152))
    chang = [{"from": "Một chỗ nào đó", "to": "Cảng Cát Lái"}]
    ra, thieu = toa_do_diem.gan_toa_do_cho_chang_db(db, chang, cho_phep_ngoai=True)
    assert ra[0].get("from_lat") is not None
    assert thieu == []


def test_toa_do_ngoai_Viet_Nam_bi_chan(db):
    """Mot dich vu tra toa do co the tra ve mot diem o nuoc khac cho mot ten
    trung. Chan o tang thap nhat, truoc moi phep kiem khac."""
    assert toa_do_diem._trong_viet_nam((10.7567, 106.7828)) is True
    assert toa_do_diem._trong_viet_nam((38.7223, -9.1393)) is False  # Lisbon
    assert toa_do_diem._trong_viet_nam(None) is False


def test_chuan_hoa_bo_dau_va_dau_cau(db):
    """"Cảng Cát Lái, TP. Thủ Đức" phai ra cung khoa voi cach viet khong dau.

    Khong co buoc nay thi moi dau phay trong du lieu nhap tay lai lam mat mot
    diem tren ban do.
    """
    assert toa_do_diem.chuan_hoa("Cảng Cát Lái, TP. Thủ Đức") == "cang cat lai tp thu duc"
    assert toa_do_diem.chuan_hoa("  Bãi   Sóng Thần  ") == "bai song than"
    assert toa_do_diem.chuan_hoa(None) == ""
