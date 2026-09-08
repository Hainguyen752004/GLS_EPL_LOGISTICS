"""Tep dinh kem cua don van chuyen: hop dong, bao gia da ky.

Tab "Tai lieu dinh kem" tung co mot o chon tep, va khi chon xong no bao "Da
chon hop dong/bao gia dinh kem: <ten tep>". Nhung `so-contract-file` khong
xuat hien trong bat ky tep JS nao — khong upload, khong FormData. Tep bi bo
ngay tai do, con nguoi dung thi tuong da dinh kem xong. Backend cung chua co
cho nao de chua.

Bo kiem nay chot lai cac tinh chat an toan, lam theo dung mau POD.
"""
import io
import os
import sqlite3
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from migrations import v031_sales_order_documents as v031  # noqa: E402
from migrations.runner import MIGRATIONS, required_migration_head, upgrade  # noqa: E402
from services import sales_order_document_service as svc  # noqa: E402
from services.errors import DomainError  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"noi dung anh gia lap"
JPEG = b"\xff\xd8\xff" + b"noi dung anh gia lap"
PDF = b"%PDF-1.7" + b"noi dung pdf gia lap"


def _docx():
    """Mot DOCX toi thieu that su la ZIP, de kiem magic byte `PK\\x03\\x04`."""
    bo_dem = io.BytesIO()
    with zipfile.ZipFile(bo_dem, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
    return bo_dem.getvalue()


# --- 1. Migration -------------------------------------------------------


def test_v031_da_duoc_dang_ky_trong_chuoi():
    # v031 khong con la moc CUOI (moc 032 da them sau no), nen doi ten va doi noi
    # dung phep kiem: no co mat trong chuoi, dung ngay sau moc truoc, va con moc
    # khac dung sau. Ghim `MIGRATIONS[-1]` la buoc moi moc moi phai sua lai bai
    # kiem cua ban truoc.
    assert v031 in MIGRATIONS
    ds = [m.VERSION for m in MIGRATIONS]
    i = ds.index(v031.VERSION)
    assert int(ds[i - 1].split("_")[0]) == int(v031.VERSION.split("_")[0]) - 1
    assert i < len(ds) - 1, "v031 phai con moc khac dung sau"
    assert required_migration_head() != v031.VERSION


def test_cau_lenh_postgres_khong_ket_noi():
    lenh = v031.statements("postgresql")
    assert any("CREATE TABLE IF NOT EXISTS sales_order_documents" in c for c in lenh)
    # Gioi han kich thuoc phai duoc chan o TANG CO SO DU LIEU, khong chi o tang
    # ung dung: mot duong ghi khac quen kiem se bi chan tai day.
    assert any("ck_sales_order_document_size" in c for c in lenh)
    assert any("26214400" in c for c in lenh), "25 MB, dung con so giao dien da hua"
    # Xoa don thi tep di theo, khong de lai dong mo coi.
    assert any("ON DELETE CASCADE" in c for c in lenh)
    lui = v031.statements("postgresql", direction="rollback")
    assert lui == ["DROP TABLE IF EXISTS sales_order_documents"]


def test_chay_toan_bo_chuoi_migration_len_den_v031(tmp_path):
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

    # Chay het chuoi thi phai toi dung moc ma `required_migration_head()` khai,
    # khong phai dung v031: v031 khong con la moc cuoi.
    da_ap = upgrade(str(duong_dan))
    assert da_ap[-1] == required_migration_head()
    assert v031.VERSION in da_ap, "chuoi phai di qua v031"

    ket_noi = sqlite3.connect(str(duong_dan))
    try:
        cot = {h[1] for h in ket_noi.execute('PRAGMA table_info("sales_order_documents")')}
        assert {"id", "so_id", "document_type", "file_name", "mime_type",
                "file_size", "checksum", "content", "created_by"} <= cot
    finally:
        ket_noi.close()


def test_bang_chua_dung_thi_khong_bat_loi(tmp_path):
    ket_noi = sqlite3.connect(str(tmp_path / "trong.db"), isolation_level=None)
    try:
        v031.upgrade_sqlite(ket_noi)
        v031.validate_sqlite(ket_noi)
        v031.rollback_sqlite(ket_noi)
    finally:
        ket_noi.close()


# --- 2. Kieu tep suy ra tu NOI DUNG, khong tin loi khai ------------------


@pytest.mark.parametrize("noi_dung,mong_doi", [
    (PNG, "image/png"),
    (JPEG, "image/jpeg"),
    (PDF, "application/pdf"),
])
def test_suy_ra_kieu_tu_magic_byte(noi_dung, mong_doi):
    assert svc.suy_ra_mime(noi_dung, "application/octet-stream") == mong_doi


def test_docx_nhan_ra_qua_chu_ky_zip():
    assert svc.suy_ra_mime(_docx(), None) == \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_khong_tin_kieu_do_client_khai():
    """Kieu do client khai duoc luu lai roi dung lam media_type luc phuc vu tep.

    Tin theo no cho phep nguoi gui tu chon cach trinh duyet dien giai noi dung
    minh tai len.
    """
    doc_hai = b"<html><script>alert(1)</script></html>"
    with pytest.raises(DomainError) as loi:
        svc.suy_ra_mime(doc_hai, "application/pdf")
    assert loi.value.code == "SO_DOCUMENT_TYPE_INVALID"
    # Va thong bao phai noi ro la noi dung khong khop loi khai.
    assert "không khớp" in loi.value.message


def test_kieu_la_bi_tu_choi():
    with pytest.raises(DomainError) as loi:
        svc.suy_ra_mime(b"MZ\x90\x00 mot tep exe", "application/x-msdownload")
    assert loi.value.code == "SO_DOCUMENT_TYPE_INVALID"


# --- 3. Kich thuoc --------------------------------------------------------


def test_tep_qua_lon_bi_chan():
    with pytest.raises(DomainError) as loi:
        svc.kiem_kich_thuoc(b"x" * (svc.MAX_DOCUMENT_BYTES + 1))
    assert loi.value.code == "SO_DOCUMENT_TOO_LARGE"
    assert loi.value.status_code == 413


def test_tep_rong_bi_chan():
    with pytest.raises(DomainError) as loi:
        svc.kiem_kich_thuoc(b"")
    assert loi.value.code == "SO_DOCUMENT_EMPTY"


def test_dung_bang_gioi_han_thi_nhan():
    svc.kiem_kich_thuoc(b"x" * svc.MAX_DOCUMENT_BYTES)


# --- 4. Ten tep: bo duong dan va ky tu dieu khien ------------------------


@pytest.mark.parametrize("tho,mong_doi", [
    ("hop-dong.pdf", "hop-dong.pdf"),
    # Trinh duyet gui `filename` nguyen van tu may nguoi dung, nen no co the
    # chua duong dan. Ten nay di vao header Content-Disposition luc tai ve.
    ("../../../etc/passwd", "passwd"),
    ("C:\\Users\\ke\\hop dong.docx", "hop dong.docx"),
    ('ten"co"nhay.pdf', "tenconhay.pdf"),
    ("", "tai-lieu"),
    (None, "tai-lieu"),
])
def test_ten_tep_duoc_lam_sach(tho, mong_doi):
    assert svc._ten_an_toan(tho) == mong_doi


def test_ten_tep_khong_chua_xuong_dong():
    """Xuong dong trong ten se tach duoc header HTTP thanh hai."""
    assert "\r" not in svc._ten_an_toan("a\rb.pdf")
    assert "\n" not in svc._ten_an_toan("a\nb.pdf")


# --- 5. Ghi va doc ------------------------------------------------------


@pytest.fixture()
def phien(app_client):
    """Mot phien co san mot don van chuyen de dinh kem vao."""
    import importlib

    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.SalesOrder(
            id="SO-DOC-TEST", canonical_status="draft", status="Draft",
            created_by="test", updated_by="test",
        ))
        db.commit()
    return database, models


def test_ghi_roi_doc_lai_duoc(phien):
    database, models = phien
    with database.SessionLocal() as db:
        ban_ghi, moi = svc.them_tai_lieu(
            db, "SO-DOC-TEST", file_name="hop-dong.pdf", mime_type="application/pdf",
            content=PDF, document_type="contract", note="Ban ky ngay 04/09", actor="anh-hai",
        )
        db.commit()
        assert moi is True
        assert ban_ghi.mime_type == "application/pdf"
        assert ban_ghi.file_size == len(PDF)
        assert ban_ghi.created_by == "anh-hai"

        mo_ta = svc.serialize(ban_ghi)
        # Mo ta KHONG duoc kem noi dung tep: danh sach duoc nap moi lan mo don,
        # kem noi dung nghia la keo ca chuc MB qua mang chi de hien mot cai ten.
        assert "content" not in mo_ta
        assert mo_ta["download_url"].endswith(ban_ghi.id)
        assert mo_ta["document_type_label"] == "Hợp đồng"


def test_tai_lai_cung_mot_tep_khong_tao_ban_ghi_thu_hai(phien):
    database, models = phien
    with database.SessionLocal() as db:
        dau, moi_dau = svc.them_tai_lieu(
            db, "SO-DOC-TEST", file_name="a.pdf", mime_type="application/pdf",
            content=PDF, document_type="contract", note="", actor="test",
        )
        db.commit()
        # Nguoi dung bam nham hai lan la chuyen binh thuong: tra ve ban ghi da
        # co, khong bao loi va cung khong tao ban thu hai.
        sau, moi_sau = svc.them_tai_lieu(
            db, "SO-DOC-TEST", file_name="a-copy.pdf", mime_type="application/pdf",
            content=PDF, document_type="contract", note="", actor="test",
        )
        db.commit()
        assert moi_dau is True and moi_sau is False
        assert dau.id == sau.id
        assert len(svc.danh_sach(db, "SO-DOC-TEST")) == 1


def test_don_khong_ton_tai_thi_tu_choi(phien):
    database, models = phien
    with database.SessionLocal() as db:
        with pytest.raises(DomainError) as loi:
            svc.them_tai_lieu(
                db, "SO-KHONG-CO", file_name="a.pdf", mime_type="application/pdf",
                content=PDF, document_type="contract", note="", actor="test",
            )
        assert loi.value.code == "SALES_ORDER_NOT_FOUND"


def test_loai_chung_tu_la_bi_tu_choi(phien):
    database, models = phien
    with database.SessionLocal() as db:
        with pytest.raises(DomainError) as loi:
            svc.them_tai_lieu(
                db, "SO-DOC-TEST", file_name="a.pdf", mime_type="application/pdf",
                content=PDF, document_type="ke-khai-thue", note="", actor="test",
            )
        assert loi.value.code == "SO_DOCUMENT_TYPE_UNKNOWN"


# --- 6. Cac endpoint ----------------------------------------------------


def test_tai_len_tai_ve_va_xoa_qua_api(app_client, phien):
    client, _, _ = app_client

    # Tai len
    tra_ve = client.post(
        "/api/sales-orders/SO-DOC-TEST/documents",
        files={"file": ("hop-dong.pdf", PDF, "application/pdf")},
        data={"document_type": "contract", "note": "Ban ky"},
    )
    assert tra_ve.status_code == 200, tra_ve.text
    than = tra_ve.json()
    assert than["created"] is True
    ma = than["data"]["id"]

    # Liet ke
    danh_sach = client.get("/api/sales-orders/SO-DOC-TEST/documents").json()
    assert [row["id"] for row in danh_sach] == [ma]
    assert "content" not in danh_sach[0]

    # Tai ve
    tep = client.get("/api/sales-order-documents/%s" % ma)
    assert tep.status_code == 200
    assert tep.content == PDF
    # `attachment` chu khong phai `inline`: mot PDF dung kheo duoc phuc vu
    # inline tu chinh origin cua ung dung se chay duoc JavaScript trong ngu
    # canh do.
    assert tep.headers["content-disposition"].startswith("attachment;")
    assert tep.headers["x-content-type-options"] == "nosniff"
    assert tep.headers["content-type"].startswith("application/pdf")

    # Xoa
    assert client.delete("/api/sales-order-documents/%s" % ma).status_code == 200
    assert client.get("/api/sales-orders/SO-DOC-TEST/documents").json() == []
    assert client.get("/api/sales-order-documents/%s" % ma).status_code == 404


def test_api_tu_choi_tep_gia_dang_pdf(app_client, phien):
    client, _, _ = app_client
    tra_ve = client.post(
        "/api/sales-orders/SO-DOC-TEST/documents",
        files={"file": ("gia.pdf", b"<html><script>alert(1)</script></html>", "application/pdf")},
        data={"document_type": "contract"},
    )
    assert tra_ve.status_code == 422
    assert "SO_DOCUMENT_TYPE_INVALID" in tra_ve.text


def test_api_tu_choi_khi_thieu_tep(app_client, phien):
    client, _, _ = app_client
    tra_ve = client.post(
        "/api/sales-orders/SO-DOC-TEST/documents",
        data={"document_type": "contract"},
    )
    assert tra_ve.status_code == 422
    assert "SO_DOCUMENT_REQUIRED" in tra_ve.text
