"""Vi tri MO PHONG cua xe dang chay, tinh doc theo tuyen.

VAN DE DA CO. Thap kiem soat so moc GPS voi gio hien tai va coi cu hon muoi lam
phut la "mat tin hieu". Bo du lieu mau ghi mot moc GPS luc NAP, nen sau muoi lam
phut ngoi xem la ca hai xe deu chuyen thanh "GPS cu" va hai diem tren ban do
dung yen mot cho. Do duoc tren man hinh that: dai so lieu bao "GPS thieu / cu
2", hai diem to xam. Voi mot ban demo thi do la mot man hinh chet, va nap lai du
lieu khong sua duoc — bao nhieu lan nap cung se cu di sau muoi lam phut.

Nen vi tri duoc TINH tai luc doc: xe di duoc bao nhieu phan tuyen thi dat diem o
dung cho do tren duong gap khuc cua tuyen.

Tep nay khoa bon dieu quan trong nhat:

  1. Diem nam DUNG TREN tuyen, khong nhay ra ngoai hanh lang.
  2. Can theo DO DAI tung chang, khong chia deu theo so chang.
  3. Don DA DEN NOI thi ghim o diem cuoi, toc do 0.
  4. Thieu du lieu thi tra ve `None` — noi "khong biet" chu khong doan bua.
"""

import datetime as dt

from services import gps_simulation as mp


class ChuyenGia:
    def __init__(self, di, den, thuc=None):
        self.planned_departure_at = di
        self.planned_arrival_at = den
        self.actual_departure_at = thuc


def _gio(h, m=0):
    return dt.datetime(2026, 9, 8, h, m, tzinfo=dt.timezone.utc)


# Hai chang co DO DAI RAT KHAC NHAU — co y, de bat loi chia deu theo so chang.
# Chang dau 30 km, chang sau 10 km.
CHANG = [
    {"from_lat": 10.0, "from_lng": 106.0, "to_lat": 10.3, "to_lng": 106.0, "dist_km": 30},
    {"from_lat": 10.3, "from_lng": 106.0, "to_lat": 10.4, "to_lng": 106.0, "dist_km": 10},
]


def test_chua_khoi_hanh_thi_dung_o_diem_dau():
    trip = ChuyenGia(_gio(8), _gio(10))
    v = mp.vi_tri_mo_phong(trip, CHANG, _gio(7))
    assert v is not None
    assert abs(v["lat"] - 10.0) < 1e-6, "chua chay thi phai o diem lay hang"
    assert v["phan_tram"] == 0.0


def test_giua_duong_thi_diem_nam_tren_tuyen_va_CAN_THEO_DO_DAI():
    """Nua thoi gian thi da di 20 km tren 40 km, tuc DANG o chang DAU.

    Day la phep kiem quan trong nhat cua tep. Neu chia deu theo SO CHANG thi nua
    thoi gian se roi vao dung diem noi hai chang (10.3) — sai 0.1 do, khoang 11
    km. Tren ban do la diem nhay vuot qua ca mot chang, va nguoi xem thay ngay
    la xe "teleport".
    """
    trip = ChuyenGia(_gio(8), _gio(10))
    v = mp.vi_tri_mo_phong(trip, CHANG, _gio(9))
    assert v["phan_tram"] == 50.0
    # 50% cua 40 km = 20 km, tuc 2/3 chang dau (30 km) -> lat = 10.0 + 0.3*(2/3)
    assert abs(v["lat"] - 10.2) < 1e-6, "phai can theo do dai chang, khong chia deu"
    assert abs(v["lng"] - 106.0) < 1e-6, "diem phai nam DUNG tren tuyen"
    assert v["con_lai_km"] == 20.0


def test_qua_gio_du_kien_thi_ghim_o_diem_cuoi_khong_troi_ra_ngoai():
    trip = ChuyenGia(_gio(8), _gio(10))
    v = mp.vi_tri_mo_phong(trip, CHANG, _gio(14))
    assert v["phan_tram"] == 100.0
    assert abs(v["lat"] - 10.4) < 1e-6, "khong duoc troi qua diem giao"
    assert v["con_lai_km"] == 0.0


def test_don_DA_DEN_NOI_thi_ghim_diem_cuoi_va_toc_do_0():
    """Xe da den noi thi dang do o cong cang cho ky nhan.

    De no van "dang chay" o giua duong la noi sai trang thai — nguoi truc nhin
    ban do se tuong xe con tren duong va khong di doi POD.
    """
    trip = ChuyenGia(_gio(8), _gio(14))
    v = mp.vi_tri_mo_phong(trip, CHANG, _gio(9), trang_thai_don="arrived")
    assert v["phan_tram"] == 100.0
    assert abs(v["lat"] - 10.4) < 1e-6
    assert v["speed_kmh"] == 0.0


def test_toc_do_suy_tu_KHUNG_GIO_that_chu_khong_dat_co_dinh():
    """Mot tuyen 40 km trong hai gio ra 20 km/h.

    Dat mot con so co dinh thi mot chuyen 112 km va mot chuyen 44 km hien cung
    mot toc do, va con so do noi sai ve ca hai.
    """
    trip = ChuyenGia(_gio(8), _gio(10))
    v = mp.vi_tri_mo_phong(trip, CHANG, _gio(9))
    assert v["speed_kmh"] == 20.0


def test_uu_tien_gio_xuat_ben_THUC_TE_hon_gio_ke_hoach():
    """Xe di muon mot gio thi tien do phai tinh tu luc no THUC SU di.

    Tinh tu gio ke hoach thi mot xe vua roi ben da bi ve o giua duong.
    """
    trip = ChuyenGia(_gio(8), _gio(12), thuc=_gio(10))
    v = mp.vi_tri_mo_phong(trip, CHANG, _gio(11))
    assert v["phan_tram"] == 50.0, "phai tinh tu 10h, khong phai tu 8h"


def test_thieu_toa_do_hoac_thieu_moc_thi_tra_ve_None():
    """Khong doan bua mot diem giua ban do.

    Mot diem sai cho con te hon khong co diem: nguoi truc se goi tai xe hoi vi
    sao xe o cho do, va cau tra loi la khong ai dat no o do ca.
    """
    trip = ChuyenGia(_gio(8), _gio(10))
    assert mp.vi_tri_mo_phong(trip, [], _gio(9)) is None
    assert mp.vi_tri_mo_phong(trip, [{"dist_km": 10}], _gio(9)) is None
    assert mp.vi_tri_mo_phong(ChuyenGia(None, None), CHANG, _gio(9)) is None
    # Khung gio dai bang khong thi khong chia duoc.
    assert mp.vi_tri_mo_phong(ChuyenGia(_gio(8), _gio(8)), CHANG, _gio(9)) is None


def test_chang_thieu_toa_do_thi_BO_QUA_chang_do_chu_khong_bo_ca_tuyen():
    """Mot tuyen bon chang ma thieu toa do mot chang van ve duoc phan con lai.

    Bo het thi khong con gi de ve, va man hinh mat luon ca nhung chang co du
    du lieu.
    """
    lech = [CHANG[0], {"dist_km": 5}, CHANG[1]]
    v = mp.vi_tri_mo_phong(ChuyenGia(_gio(8), _gio(10)), lech, _gio(9))
    assert v is not None
    assert abs(v["lng"] - 106.0) < 1e-6


def test_moc_tra_ve_luon_la_BAY_GIO_va_duoc_danh_dau_mo_phong():
    """Hai co nay la phan trung thuc cua ca tinh nang.

    `quan_sat_luc` la bay gio vi vi tri duoc TINH bay gio — de moc cu thi thap
    kiem soat lai bao "GPS cu" va ta quay lai dung cho da xuat phat. Va
    `mo_phong` phai co, de giao dien danh dau rieng: mot diem mo phong ma man
    hinh bao la GPS thiet bi thi nguoi truc tin vao mot vi tri khong ai do duoc.
    """
    luc = _gio(9)
    v = mp.vi_tri_mo_phong(ChuyenGia(_gio(8), _gio(10)), CHANG, luc)
    assert v["quan_sat_luc"] == luc
    assert v["mo_phong"] is True
