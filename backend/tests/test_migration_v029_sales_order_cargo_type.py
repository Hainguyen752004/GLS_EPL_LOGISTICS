"""Cot loai phuong tien tren don van chuyen.

Cuoc mot chuyen tinh bang cong thuc cua LOAI XE: moi loai xe co don gia xang
dau, phu cap, cuoc theo kg rieng. Bao gia co `cargo_type`, con `sales_orders`
thi khong co cot nao — nen don van chuyen khong biet minh thuoc loai xe nao va
khong the ap lai cong thuc theo tai trong thuc te cua don.

He qua truoc day: man don van chuyen tinh tien bang `so km x 6250 + 800000`, hai
con so khong co nguon nao va khong dinh gi den cong thuc da cau hinh.
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from migrations import v029_sales_order_cargo_type as v029  # noqa: E402
from migrations.runner import MIGRATIONS, required_migration_head, upgrade  # noqa: E402


def test_v029_da_duoc_dang_ky_trong_chuoi():
    # v029 khong con la moc CUOI (v030 da them sau no), nen chi kiem no co mat
    # va nam dung cho trong chuoi. Chot `MIGRATIONS[-1]` la buoc moi migration
    # moi phai sua lai bai kiem cua ban truoc.
    assert v029 in MIGRATIONS
    assert MIGRATIONS.index(v029) == len(MIGRATIONS) - 2
    assert required_migration_head() != v029.VERSION


def test_cau_lenh_postgres_khong_ket_noi_va_dung_if_not_exists():
    lenh = v029.statements("postgresql")
    assert lenh == ["ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS cargo_type VARCHAR"]

    # Chay lai migration khong duoc no loi: IF NOT EXISTS o chieu len va
    # IF EXISTS o chieu lui.
    lui = v029.statements("postgresql", direction="rollback")
    assert lui == ["ALTER TABLE sales_orders DROP COLUMN IF EXISTS cargo_type"]


def _cot(ket_noi, bang="sales_orders"):
    return {hang[1] for hang in ket_noi.execute(f'PRAGMA table_info("{bang}")')}


def test_them_cot_roi_lui_lai_duoc(tmp_path):
    ket_noi = sqlite3.connect(str(tmp_path / "cargo_type.db"), isolation_level=None)
    try:
        ket_noi.execute("CREATE TABLE sales_orders (id VARCHAR PRIMARY KEY, weight_kg FLOAT)")

        v029.upgrade_sqlite(ket_noi)
        assert "cargo_type" in _cot(ket_noi)

        # Chay lai lan hai khong duoc no loi.
        v029.upgrade_sqlite(ket_noi)

        # Gia tri ghi vao doc lai duoc, khong bi cat.
        ket_noi.execute(
            "INSERT INTO sales_orders (id, weight_kg, cargo_type) VALUES ('SO-1', 3000, 'Xe tai 5 tan')"
        )
        assert list(ket_noi.execute("SELECT cargo_type FROM sales_orders"))[0][0] == "Xe tai 5 tan"

        v029.rollback_sqlite(ket_noi)
        assert "cargo_type" not in _cot(ket_noi)
    finally:
        ket_noi.close()


def test_bang_chua_dung_thi_khong_bat_loi(tmp_path):
    """Luc khoi tao co so du lieu moi, bang co the chua ton tai."""
    ket_noi = sqlite3.connect(str(tmp_path / "trong.db"), isolation_level=None)
    try:
        v029.upgrade_sqlite(ket_noi)
        v029.validate_sqlite(ket_noi)
        v029.rollback_sqlite(ket_noi)
    finally:
        ket_noi.close()


def test_kiem_tra_bat_duoc_cot_bi_thieu(tmp_path):
    ket_noi = sqlite3.connect(str(tmp_path / "thieu.db"), isolation_level=None)
    try:
        ket_noi.execute("CREATE TABLE sales_orders (id VARCHAR PRIMARY KEY)")
        with pytest.raises(RuntimeError, match="cargo_type"):
            v029.validate_sqlite(ket_noi)
    finally:
        ket_noi.close()


def test_chay_toan_bo_chuoi_migration_qua_v029(tmp_path):
    """v029 phai chay duoc trong ca chuoi, khong chi rieng le.

    Dung cac bang goc giong test_migration_v006: v001 xay lai lai bang co san
    nen no khong chay tren mot tep hoan toan trong.
    """
    duong_dan = tmp_path / "day_du.db"
    ket_noi = sqlite3.connect(duong_dan)
    ket_noi.executescript("""
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
    """)
    ket_noi.close()

    da_chay = upgrade(str(duong_dan))
    assert v029.VERSION in da_chay
    assert da_chay[-1] == required_migration_head()

    ket_noi = sqlite3.connect(str(duong_dan))
    try:
        cot = _cot(ket_noi)
        assert "cargo_type" in cot
        # Cot cua cac migration truoc phai con nguyen.
        assert {"weight_kg", "route_id", "seal_weight"} <= cot
    finally:
        ket_noi.close()


def test_ke_thua_tu_bao_gia_sang_don_hang():
    """Loai phuong tien da chao cho khach phai di theo sang don hang.

    Cung mot le voi quy cach van chuyen: bat khai lai la vua mat cong vua de
    lech voi cai da chao.
    """
    from services.workflow_service import SHIPPING_SPEC_FIELDS, _inherit_shipping_spec

    assert "cargo_type" in SHIPPING_SPEC_FIELDS

    class Gia:
        def __init__(self, **kwargs):
            for khoa, gia_tri in kwargs.items():
                setattr(self, khoa, gia_tri)

    bao_gia = Gia(cargo_type="Xe tai 5 tan", carrier_name="EPL", delivery_method=None,
                  seal_weight=None, temperature_requirement=None, cargo_insurance=None,
                  warehouse_owner=None)
    don = Gia(cargo_type=None, carrier_name=None, delivery_method=None, seal_weight=None,
              temperature_requirement=None, cargo_insurance=None, warehouse_owner=None)
    _inherit_shipping_spec(don, bao_gia)
    assert don.cargo_type == "Xe tai 5 tan"

    # Da nhap tren don thi KHONG ghi de: loai xe thuc te dieu di co the khac
    # loai xe luc chao gia.
    don_da_sua = Gia(cargo_type="Xe dau keo 40 tan", carrier_name=None, delivery_method=None,
                     seal_weight=None, temperature_requirement=None, cargo_insurance=None,
                     warehouse_owner=None)
    _inherit_shipping_spec(don_da_sua, bao_gia)
    assert don_da_sua.cargo_type == "Xe dau keo 40 tan"
