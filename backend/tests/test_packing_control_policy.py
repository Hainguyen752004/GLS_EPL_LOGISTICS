"""Cua chan xuat ben theo LOAI HANG, khong theo "co lap phieu hay khong".

LO HONG DA CO. `require_loaded_for_dispatch` truoc day chi soi nhung Packing
List DA TON TAI: don khong co phieu thi di qua tu do. Nghia la quy tac "phai
quet du kien" bi tat bang cach KHONG lap phieu — mot cua ma ai cung tat duoc
thi khong phai cua. O quy mo nam tram xe, dieu phoi vien dang gap se bo buoc
lap phieu, va he thong khong con biet hang co du hay khong.

VI SAO KHONG AP CHO MOI DON. Container nguyen khoi la MOT don vi niem phong:
kiem la kiem SO NIEM PHONG, khong phai quet hai muoi hai nhan kien ben trong —
xe khong mo cont ra de dem. Bat in nhan cho hang nguyen cont la viec vo nghia,
va nguoi van hanh se lach bang cach lap mot phieu mot kien gia; luc do con so
"da quet du kien" khong con noi len dieu gi, va do la ket cuc te nhat: mot phep
kiem van xanh trong khi khong ai kiem gi.

Nen quy tac chia hai duong, do DU LIEU quyet chu khong do nguoi bam. Tep nay
khoa ca hai duong, va khoa luon huong doan khi du lieu thieu.
"""

import pytest

from services import packing_control_policy as chinh_sach
from services.errors import DomainError


class DonGia:
    """Mot lenh giao hang gia, chi co dung nhung truong chinh sach doc tới."""

    def __init__(self, ma="DO-TEST-1", quy_cach="", niem_phong=None):
        self.id = ma
        self.packaging_spec = quy_cach
        self.seal_no = niem_phong


# --- Phan loai quy cach -------------------------------------------------

@pytest.mark.parametrize("quy_cach", [
    "Container nguyên khối",
    "container nguyen khoi",
    "Cont 40 nguyên khối",
    "FCL 20'",
    "Hàng nguyên cont",
])
def test_hang_nguyen_khoi_khong_phai_dem_kien(quy_cach):
    don = DonGia(quy_cach=quy_cach)
    assert chinh_sach.la_nguyen_khoi(quy_cach)
    assert chinh_sach.phai_quet_kien(don) is False


@pytest.mark.parametrize("quy_cach", [
    "Thùng carton (tiêu chuẩn)",
    "Pallet gỗ",
    "Pallet quấn màng PE",
    "Hàng lẻ LCL",
    "Kiện rời",
])
def test_hang_dem_duoc_theo_kien_thi_phai_quet(quy_cach):
    assert chinh_sach.phai_quet_kien(DonGia(quy_cach=quy_cach)) is True


@pytest.mark.parametrize("quy_cach", ["", None, "   ", "Không rõ", "Loại mới chưa đặt tên"])
def test_quy_cach_thieu_hoac_la_thi_NGHIENG_VE_PHIA_CAN_KIEM(quy_cach):
    """Khong nhan ra quy cach thi coi la CAN dem kien.

    Doan sai theo huong "khong can kiem" thi hang di ma khong ai dem, va khong
    ai biet la da khong dem. Doan sai theo huong "can kiem" thi nguoi dung bi
    hoi them mot buoc va ho sua duoc quy cach ngay tren don. Cai sai thu hai re
    hon nhieu, nen mac dinh phai nghieng ve phia do.
    """
    assert chinh_sach.phai_quet_kien(DonGia(quy_cach=quy_cach)) is True


# --- Cua chan xuat ben --------------------------------------------------

def test_hang_dem_kien_KHONG_CO_phieu_thi_bi_chan():
    """Day chinh la lo hong cu: khong co phieu thi truoc day di qua tu do."""
    don = DonGia("DO-1", "Pallet quấn màng PE")
    with pytest.raises(DomainError) as loi:
        chinh_sach.kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau=False)
    assert loi.value.code == "PACKING_LIST_REQUIRED"
    # Loi phai noi RO don nao va vi sao, khong chi "khong hop le": nguoi dieu
    # phoi dang co bay don tren man, ho can biet phai di lap phieu cho don nao.
    assert "DO-1" in loi.value.message
    assert "Pallet" in loi.value.message


def test_hang_dem_kien_DA_quet_du_thi_di_qua():
    don = DonGia("DO-1", "Thùng carton (tiêu chuẩn)")
    chinh_sach.kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau=True)


def test_hang_nguyen_khoi_khong_can_phieu_nhung_PHAI_co_niem_phong():
    don = DonGia("DO-2", "Container nguyên khối", niem_phong=None)
    with pytest.raises(DomainError) as loi:
        chinh_sach.kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau=False)
    assert loi.value.code == "SEAL_NUMBER_REQUIRED"
    assert "DO-2" in loi.value.message


def test_hang_nguyen_khoi_co_niem_phong_thi_di_qua_KHONG_can_phieu():
    """Do la ca y nghia cua huong nay: cont niem phong khong phai dem kien."""
    don = DonGia("DO-2", "Container nguyên khối", niem_phong="SL-4471")
    chinh_sach.kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau=False)


def test_niem_phong_chi_co_khoang_trang_thi_khong_tinh_la_co():
    """Mot o dien toan khoang trang la chua dien, khong phai da dien."""
    don = DonGia("DO-2", "Container nguyên khối", niem_phong="   ")
    assert chinh_sach.so_niem_phong(don) == ""
    with pytest.raises(DomainError) as loi:
        chinh_sach.kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau=False)
    assert loi.value.code == "SEAL_NUMBER_REQUIRED"


def test_hai_ma_loi_PHAI_khac_nhau():
    """Ba viec phai lam la ba viec khac nhau, nen ma loi phai khac nhau.

    Tang giao dien dua vao MA LOI de dan nguoi dung tới dung cho: lap phieu,
    quet tiep, hay dien so niem phong. Dung chung mot ma cho ca ba thi giao dien
    chi con dan duoc tới mot cho, va hai trong ba lan la dan sai.
    """
    ma = set()
    for don in (DonGia("A", "Pallet gỗ"), DonGia("B", "Container nguyên khối")):
        with pytest.raises(DomainError) as loi:
            chinh_sach.kiem_dieu_kien_xuat_ben(don, phieu_dat_yeu_cau=False)
        ma.add(loi.value.code)
    assert ma == {"PACKING_LIST_REQUIRED", "SEAL_NUMBER_REQUIRED"}
