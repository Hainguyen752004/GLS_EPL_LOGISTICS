"""Cot ghi chu cho bao gia, don van chuyen va lenh giao hang.

Ba man hinh deu co mot o Ghi chu lon (textarea 4-5 dong) kem placeholder rat
cu the — `qt-notes` goi y "Bao gia chua bao gom thue VAT 10%, co hieu luc trong
30 ngay, thanh toan truoc 50%". Nhung khong mot bang nao co cot de chua, va
khong mot payload nao gui chung len.

He qua: nguoi dung go dieu kien bao gia vao do, bam Luu, va noi dung bien mat
khong mot loi nao.
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from migrations import v030_workflow_notes as v030  # noqa: E402
from migrations.runner import MIGRATIONS, required_migration_head, upgrade  # noqa: E402

BANG = ("quotations", "sales_orders", "delivery_orders")


def test_v030_la_moc_head_dang_ky():
    # v030 khong con la moc CUOI (v031 da them sau no), nen chi kiem no co
    # mat va nam dung cho trong chuoi.
    assert v030 in MIGRATIONS
    # Kiem VI TRI theo CHUOI SO, khong theo khoang cach tu cuoi.
    #
    # Ban truoc dung `len(MIGRATIONS) - 3`, nen moi lan them mot moc moi la bai
    # nay do — va do vi mot ly do khong lien quan gi toi dieu no muon giu. Da xay
    # ra that khi them moc 032. Dieu CAN giu la: moc nay co mat trong chuoi, dung
    # ngay sau moc truoc no, va khong con la moc cuoi.
    ds = [m.VERSION for m in MIGRATIONS]
    i = ds.index(v030.VERSION)
    assert int(ds[i - 1].split("_")[0]) == int(v030.VERSION.split("_")[0]) - 1
    assert i < len(ds) - 1, "v030 phai con moc khac dung sau"
    assert required_migration_head() != v030.VERSION


def test_cau_lenh_postgres_khong_ket_noi_va_dung_if_not_exists():
    lenh = v030.statements("postgresql")
    # TEXT chu khong phai VARCHAR: day la o nhap nhieu dong, khong co gioi han
    # do dai tu nhien nao.
    assert lenh == [
        "ALTER TABLE quotations ADD COLUMN IF NOT EXISTS notes TEXT",
        "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS notes TEXT",
        "ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS notes TEXT",
    ]
    lui = v030.statements("postgresql", direction="rollback")
    assert all("DROP COLUMN IF EXISTS notes" in cau for cau in lui)
    assert len(lui) == 3


def _cot(ket_noi, bang):
    return {hang[1] for hang in ket_noi.execute(f'PRAGMA table_info("{bang}")')}


def test_them_cot_roi_lui_lai_duoc(tmp_path):
    ket_noi = sqlite3.connect(str(tmp_path / "notes.db"), isolation_level=None)
    try:
        for bang in BANG:
            ket_noi.execute(f"CREATE TABLE {bang} (id VARCHAR PRIMARY KEY)")

        v030.upgrade_sqlite(ket_noi)
        for bang in BANG:
            assert "notes" in _cot(ket_noi, bang)

        # Chay lai lan hai khong duoc no loi.
        v030.upgrade_sqlite(ket_noi)

        # Ghi chu dai nhieu dong phai doc lai duoc nguyen van, khong bi cat.
        dai = ("Bao gia chua bao gom thue VAT 10%.\n"
               "Co hieu luc trong 30 ngay.\n"
               "Thanh toan truoc 50%.\n") * 40
        ket_noi.execute("INSERT INTO quotations (id, notes) VALUES ('QT-1', ?)", (dai,))
        assert list(ket_noi.execute("SELECT notes FROM quotations"))[0][0] == dai

        v030.rollback_sqlite(ket_noi)
        for bang in BANG:
            assert "notes" not in _cot(ket_noi, bang)
    finally:
        ket_noi.close()


def test_bang_chua_dung_thi_khong_bat_loi(tmp_path):
    """Luc khoi tao co so du lieu moi, bang co the chua ton tai."""
    ket_noi = sqlite3.connect(str(tmp_path / "trong.db"), isolation_level=None)
    try:
        v030.upgrade_sqlite(ket_noi)
        v030.validate_sqlite(ket_noi)
        v030.rollback_sqlite(ket_noi)
    finally:
        ket_noi.close()


def test_kiem_tra_bat_duoc_cot_bi_thieu(tmp_path):
    ket_noi = sqlite3.connect(str(tmp_path / "thieu.db"), isolation_level=None)
    try:
        ket_noi.execute("CREATE TABLE sales_orders (id VARCHAR PRIMARY KEY)")
        with pytest.raises(RuntimeError, match="notes"):
            v030.validate_sqlite(ket_noi)
    finally:
        ket_noi.close()


def test_chay_toan_bo_chuoi_migration_len_den_v030(tmp_path):
    """v030 phai chay duoc trong ca chuoi, khong chi rieng le."""
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

    assert v030.VERSION in upgrade(str(duong_dan))

    ket_noi = sqlite3.connect(str(duong_dan))
    try:
        for bang in BANG:
            cot = _cot(ket_noi, bang)
            assert "notes" in cot
        # Cot cua cac migration truoc phai con nguyen.
        assert {"cargo_type", "seal_weight", "weight_kg"} <= _cot(ket_noi, "sales_orders")
    finally:
        ket_noi.close()


def test_ba_o_ghi_chu_duoc_luu_va_doc_lai():
    """Ba truong nay phai co mat trong schema, khong thi payload bi tu choi.

    `payment_terms` va `sales_rep` da co cot trong bang tu lau nhung schema
    chua bao gio nhan chung, nen hai o do tren man hinh khong bao gio duoc luu.
    """
    from schemas.workflow import (
        QuotationCreateRequest,
        SalesOrderCreateRequest,
        SalesOrderUpdateRequest,
    )

    assert "notes" in QuotationCreateRequest.model_fields
    for lop in (SalesOrderCreateRequest, SalesOrderUpdateRequest):
        for truong in ("notes", "payment_terms", "sales_rep"):
            assert truong in lop.model_fields, f"{lop.__name__} thieu {truong}"

    # Va service phai ghi chung vao ban ghi.
    import inspect

    from services import workflow_service

    nguon = inspect.getsource(workflow_service)
    assert "notes=data.get(\"notes\")" in nguon
    assert "payment_terms=data.get(\"payment_terms\")" in nguon
    assert "sales_rep=data.get(\"sales_rep\")" in nguon
    # Sua don hang cung phai ghi ba truong do.
    assert '("notes", "payment_terms", "sales_rep")' in nguon


def test_ghi_chu_cua_don_KHONG_ke_thua_tu_bao_gia():
    """Ghi chu bao gia va ghi chu don hang la hai thu khac nhau.

    Ghi chu bao gia la dieu kien CHAO KHACH ("chua gom VAT, hieu luc 30 ngay").
    Ghi chu don hang la luu y DIEU PHOI. Ke thua sang la dua dieu kien thuong
    mai vao cho lam viec cua doi xe.
    """
    import inspect

    from services import workflow_service

    nguon = inspect.getsource(workflow_service)
    # Khac voi `packaging_spec=q.packaging_spec` (co ke thua), ghi chu doc tu
    # payload cua chinh don hang.
    assert "notes=q.notes" not in nguon
    assert "packaging_spec=q.packaging_spec" in nguon
    # Va `notes` KHONG duoc nam trong danh sach ke thua quy cach van chuyen.
    assert "notes" not in workflow_service.SHIPPING_SPEC_FIELDS
