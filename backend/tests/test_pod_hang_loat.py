"""Duong doc POD HANG LOAT: `GET /api/pod-records?do_ids=...`.

Vi sao duong nay ton tai. Bang chuyen o man Giao hang & van chuyen phai hien "da
ky POD may tren tong bao nhieu don" cho TUNG dong. Truoc day chi co duong theo
mot don (`GET /api/pod/{do_id}`), nen ve mot bang N dong phai goi N lan — o quy
mo hang nghin chuyen thi man hinh khong mo duoc.

Con so do khong phai trang tri: thieu POD tren mot don la ca chuyen khong doi
soat duoc va hoa don treo. Nen no phai doc duoc ngay tren bang.

Ba dieu bai kiem nay khoa lai:

  1. Mot loi goi tra ve POD cua NHIEU don, va tung dong phai co `do_id` — ben
     goi nhom theo don, va mot dong khong biet no thuoc don nao thi khong nhom
     duoc.
  2. Khong don nao co POD thi tra ve DANH SACH RONG, KHONG bao 404. Day la
     duong doc hang loat: "khong don nao trong lo nay co POD" la mot cau tra
     loi hop le, con bao loi thi ben goi phai bat ngoai le cho mot tinh huong
     binh thuong. (Duong theo mot don thi 404 dung nghia "don nay chua ky", nen
     no giu nguyen 404 — bai kiem cung khoa cho khac biet do.)
  3. Co TRAN so don moi lan goi. Khong co tran thi mot ben goi vo tinh gui ca
     nghin ma se bien mot duong doc thanh mot duong lam nghen may chu.
"""

import pytest

from fastapi.testclient import TestClient

from main import app
from database import Base, SessionLocal, engine
from services import demo_seed_service as seed_service
from services import workflow_service as svc
from services.workflow_service import DomainError


def _bao_dam_co_bang():
    """Bao dam co so du lieu cua bo kiem da co bang truoc khi dung `SessionLocal`.

    VI SAO CAN. Bai kiem nay dung THANG `SessionLocal()` — phien lam viec cua
    ung dung — chu khong dung mot co so du lieu rieng trong `tmp_path`. Conftest
    tro co so du lieu do sang mot tep SQLite tam nhung KHONG tao bang, va mot
    bai kiem khac (`app_client`) xoa moi module trong `app/` khoi `sys.modules`
    roi nap lai chung voi mot duong dan khac. Ket qua: chay rieng tep nay thi
    xanh, chay cung ca bo thi vo voi "no such table: delivery_pod_records".

    Mot bai kiem do theo THU TU CHAY con te hon khong co bai kiem: no do khi
    khong co loi nao, nen lan sau ai cung bo qua mau do — va luc do mot loi
    that di qua ma khong ai thay.
    """
    Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="module")
def may():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def da_nap():
    _bao_dam_co_bang()
    db = SessionLocal()
    try:
        seed_service.seed_demo(db, reset=True, verify=True)
    finally:
        db.close()


def test_tra_ve_pod_cua_nhieu_don_va_moi_dong_co_ma_don(may, da_nap):
    # `DEMO-DO-2026-003` la truong hop "da giao xong va da ky POD".
    # `DEMO-DO-2026-004` la truong hop "xe da den noi nhung CHUA ky POD" — dung
    # cap doi de thay duong nay phan biet duoc hai tinh huong trong CUNG mot
    # loi goi, khong phai hai loi goi.
    tra = may.get("/api/pod-records", params={
        "do_ids": "DEMO-DO-2026-003,DEMO-DO-2026-004",
    })
    assert tra.status_code == 200, tra.text
    goi = tra.json()
    assert "records" in goi

    theo_don = {}
    for dong in goi["records"]:
        assert dong.get("do_id"), "moi dong POD phai co `do_id` de ben goi nhom duoc"
        theo_don.setdefault(dong["do_id"], []).append(dong)

    assert "DEMO-DO-2026-003" in theo_don, "don da ky POD phai co trong ket qua"
    # Don CHUA ky thi khong co khoa — de ben goi phan biet "chua ky" voi "khong
    # hoi den". Neu tra ve khoa rong thi hai tinh huong do lan nhau.
    assert "DEMO-DO-2026-004" not in theo_don
    assert goi["do_count"] == len(theo_don)


def test_khong_don_nao_co_pod_thi_tra_ve_rong_chu_khong_404(may, da_nap):
    tra = may.get("/api/pod-records", params={"do_ids": "KHONG-CO-DON-NAY"})
    assert tra.status_code == 200, (
        "duong doc hang loat khong duoc bao 404: 'khong don nao co POD' la mot "
        "cau tra loi hop le, khong phai mot loi"
    )
    assert tra.json()["records"] == []
    assert tra.json()["do_count"] == 0


def test_khong_co_tham_so_thi_tra_ve_rong(may, da_nap):
    tra = may.get("/api/pod-records")
    assert tra.status_code == 200, tra.text
    assert tra.json()["records"] == []


def test_duong_theo_mot_don_van_bao_404(may, da_nap):
    """Cho khac biet phai duoc giu.

    Duong theo MOT don bao 404 khi chua ky, va dieu do dung: ben goi hoi ve mot
    don cu the va can biet don do chua co POD. Duong hang loat thi khong, vi no
    hoi ve mot LO. Neu ai do dong nhat hai hanh vi thi mot trong hai ben goi se
    vo, nen khoa lai o day.
    """
    assert may.get("/api/pod/KHONG-CO-DON-NAY").status_code == 404


def test_co_tran_so_don_moi_lan_goi():
    _bao_dam_co_bang()
    db = SessionLocal()
    try:
        qua_nhieu = ["DO-%05d" % i for i in range(svc.POD_HANG_LOAT_TOI_DA + 1)]
        with pytest.raises(DomainError) as loi:
            svc.list_pod_records_for_dos(db, qua_nhieu)
        assert loi.value.code == "TOO_MANY_DELIVERY_ORDERS"
        # Dung dung tran thi phai chay duoc — tran la gioi han tren, khong phai
        # mot con so ma chinh no cung bi chan.
        vua_du = qua_nhieu[:svc.POD_HANG_LOAT_TOI_DA]
        assert isinstance(svc.list_pod_records_for_dos(db, vua_du), dict)
    finally:
        db.close()


def test_ma_trung_va_ma_rong_khong_lam_vo_tran():
    """Loc trung va loc rong TRUOC khi do tran.

    Mot ben goi gom ma tu nhieu chuyen thi de co ma trung (nhieu chuyen cung
    cho mot don) va de co chuoi rong (`"a,,b"`). Neu dem ca chung vao tran thi
    mot lo hop le bi tu choi vi nhung ma khong ton tai.
    """
    _bao_dam_co_bang()
    db = SessionLocal()
    try:
        assert svc.list_pod_records_for_dos(db, []) == {}
        assert svc.list_pod_records_for_dos(db, ["", "  ", None]) == {}
        # Cung mot ma lap lai nhieu hon tran, sau khi loc trung chi con MOT.
        lap = ["DEMO-DO-2026-003"] * (svc.POD_HANG_LOAT_TOI_DA + 50)
        ket = svc.list_pod_records_for_dos(db, lap)
        assert isinstance(ket, dict)
    finally:
        db.close()
