# -*- coding: utf-8 -*-
"""Bộ kiểm đơn vị — phép tính phiếu và phân quyền. Không cần máy chủ, không cần DB.

    python kiem/test_tinh_toan.py

Số kiểm chép từ Excel `ຂົນສົ່ງ EPL.xlsx` (phiếu T4-0428-08/EPL) và từ bản mẫu (xe liên kết
T4-0430-08/EPL) — đây là các con số bên Lào đã nhìn và gật đầu, nên chúng là chuẩn.
"""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://x:y@localhost/khong_dung")   # database.py chỉ dựng engine, không nối

from services import tinh_toan as T  # noqa: E402
from services.phan_quyen import chuyen_muc, duoc_sua_muc  # noqa: E402
from fastapi import HTTPException  # noqa: E402


def phieu(**k):
    p = types.SimpleNamespace(company="EPL", weight_origin=None, weight_dest=None, price_usd=0, hire_price_usd=None,
                              fee_pct=2, over_limit_t=40, over_price_usd=1, rate_usd=22000, rate_thb=700, rate_vnd=1.2)
    for a, b in k.items():
        setattr(p, a, b)
    return p


def dong(section, qty, unit_price, currency="LAK", paid_by_epl=True):
    return types.SimpleNamespace(section=section, qty=qty, unit_price=unit_price, currency=currency, paid_by_epl=paid_by_epl)


class PhieuXeEPL(unittest.TestCase):
    """T4-0428-08/EPL — dòng thật trong sheet ໜ້າລາຍງານຂົນສົ່ງ."""

    def setUp(self):
        self.p = phieu(weight_origin=42.06, weight_dest=41.30, price_usd=41)
        self.chi = [dong("fuel", 100, 30000), dong("fuel", 750, 28000, "VND"),
                    dong("travel", 1, 60000), dong("travel", 1, 430000), dong("travel", 1, 620000), dong("travel", 1, 1500000),
                    dong("travel", 1, 1833500), dong("travel", 1, 1800000), dong("travel", 1, 150000)]

    def test_thanh_tien_theo_can_cuoi(self):
        k = T.tinh_phieu(self.p, self.chi)
        self.assertEqual(k["tan_tinh"], 41.30)
        self.assertEqual(k["doanh_thu_usd"], 1693.30)          # ô "ມູນຄ່າ" trong Excel

    def test_chi_quy_ve_lak_dung_ty_gia_tren_phieu(self):
        k = T.tinh_phieu(self.p, self.chi)
        self.assertEqual(k["chi"]["fuel"], 100 * 30000 + 750 * 28000 * 1.2)   # 28.200.000 — mục III Excel
        self.assertEqual(k["chi"]["travel"], 6393500)                          # mục IV Excel: ລວມ 6.393.500
        self.assertEqual(k["tong_chi_lak"], 34593500)

    def test_hao_hut_phan_tram(self):
        k = T.tinh_phieu(self.p, self.chi)
        self.assertEqual(k["hao_hut_pct"], round((42.06 - 41.30) / 42.06 * 100, 2))   # 1,81% > 1,5% → cờ đỏ

    def test_chua_can_cuoi_thi_dung_tan_dau(self):
        p = phieu(weight_origin=41.90, weight_dest=None, price_usd=41)
        k = T.tinh_phieu(p, [])
        self.assertEqual(k["tan_tinh"], 41.90)
        self.assertIsNone(k["hao_hut_pct"])

    def test_tien_te_la_cua_tung_dong(self):
        """Dòng VND nhân 1,2 · dòng THB nhân 700 · dòng USD nhân 22.000 — không dồn về một tỷ giá."""
        p = phieu(price_usd=1, weight_origin=1)
        k = T.tinh_phieu(p, [dong("other", 1, 1000, "VND"), dong("other", 1, 10, "THB"), dong("other", 1, 1, "USD"), dong("other", 1, 5, "LAK")])
        self.assertEqual(k["chi"]["other"], round(1200 + 7000 + 22000 + 5))


class PhieuXeLienKet(unittest.TestCase):
    """T4-0430-08/EPL — xe ຮ່ວມ-07: nhận 41, thuê lại 40,5, cân 40,50 t."""

    def setUp(self):
        self.p = phieu(company="joint", weight_origin=41.00, weight_dest=40.50, price_usd=41, hire_price_usd=40.5)
        self.chi = [dong("fuel", 150, 30000), dong("fuel", 600, 28000, "VND", paid_by_epl=False),
                    dong("travel", 1, 1833500), dong("travel", 1, 620000), dong("travel", 1, 430000, paid_by_epl=False)]

    def test_bang_thanh_toan_chu_xe(self):
        k = T.tinh_phieu(self.p, self.chi)
        self.assertEqual(k["tien_thue_usd"], 1640.25)
        self.assertEqual(k["phi_usd"], 32.80)                   # 2%
        self.assertEqual(k["vuot_tan"], 0.5)
        self.assertEqual(k["tru_vuot_usd"], 0.5)                # 1 USD/tấn vượt 40
        self.assertEqual(k["ung_truoc_usd"], round((150 * 30000 + 1833500 + 620000) / 22000, 2))   # 316,07
        self.assertEqual(k["tra_chu_xe_usd"], round(1640.25 - 32.80 - 0.5 - 316.07, 2))            # 1.290,88

    def test_dong_chu_xe_tu_tra_khong_tinh_vao_ung(self):
        """600 lít đổ ở VN và 430.000 tiền đi VN là chủ xe tự trả — không được trừ vào tiền trả chủ xe."""
        k = T.tinh_phieu(self.p, self.chi)
        self.assertNotIn(600 * 28000 * 1.2, [k["chi"]["fuel"]])
        self.assertEqual(k["chu_xe_tu_tra_lak"], round(600 * 28000 * 1.2 + 430000))

    def test_lai_epl_la_chenh_gia(self):
        k = T.tinh_phieu(self.p, self.chi)
        self.assertEqual(k["lai_usd"], round((41 - 40.5) * 40.5, 2))    # 20,25
        self.assertEqual(k["giu_lai_usd"], round(32.80 + 0.5, 2))

    def test_khong_khai_gia_thue_thi_lay_gia_nhan(self):
        p = phieu(company="joint", weight_origin=40, weight_dest=40, price_usd=41, hire_price_usd=None)
        k = T.tinh_phieu(p, [])
        self.assertEqual(k["gia_thue_usd"], 41)
        self.assertEqual(k["lai_usd"], 0)


class PhanQuyen(unittest.TestCase):
    def test_bai_chi_sua_khi_cho_hoac_da_nhap(self):
        self.assertTrue(duoc_sua_muc("yard", "fuel", "wait"))
        self.assertTrue(duoc_sua_muc("yard", "fuel", "entered"))
        self.assertFalse(duoc_sua_muc("yard", "fuel", "verified"))
        self.assertTrue(duoc_sua_muc("admin", "fuel", "paid"))

    def test_ke_toan_khong_sua_noi_dung(self):
        self.assertFalse(duoc_sua_muc("acct", "travel", "wait"))

    def test_chuoi_duyet_muc_chi(self):
        self.assertEqual(chuyen_muc("yard", "travel", "wait", "send"), "entered")
        self.assertEqual(chuyen_muc("acct", "travel", "entered", "verify"), "verified")
        self.assertEqual(chuyen_muc("acct", "travel", "verified", "book"), "booked")
        self.assertEqual(chuyen_muc("cash", "travel", "booked", "pay"), "paid")

    def test_nhien_lieu_di_qua_kho_va_quy_vieng_chan(self):
        self.assertEqual(chuyen_muc("fuel", "fuel", "entered", "verify"), "verified")
        self.assertEqual(chuyen_muc("treasury", "fuel", "booked", "pay"), "paid")
        with self.assertRaises(HTTPException) as c:
            chuyen_muc("acct", "fuel", "entered", "verify")         # kế toán thu/chi không kiểm nhiên liệu
        self.assertEqual(c.exception.status_code, 403)
        with self.assertRaises(HTTPException) as c:
            chuyen_muc("cash", "fuel", "booked", "pay")             # tiền mặt lẻ không chi nhiên liệu
        self.assertEqual(c.exception.status_code, 403)

    def test_sai_buoc_bat_409(self):
        with self.assertRaises(HTTPException) as c:
            chuyen_muc("acct", "travel", "wait", "verify")          # chưa gửi mà đã kiểm
        self.assertEqual(c.exception.status_code, 409)
        with self.assertRaises(HTTPException) as c:
            chuyen_muc("acct", "info", "verified", "book")          # mục I không có bước ghi sổ
        self.assertEqual(c.exception.status_code, 403)

    def test_tra_lai_va_mo_khoa(self):
        self.assertEqual(chuyen_muc("acct", "travel", "verified", "return"), "wait")
        self.assertEqual(chuyen_muc("admin", "travel", "paid", "unlock"), "entered")
        with self.assertRaises(HTTPException):
            chuyen_muc("yard", "travel", "paid", "unlock")


if __name__ == "__main__":
    unittest.main(verbosity=2)
