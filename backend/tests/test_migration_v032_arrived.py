"""Ràng buộc CHECK của `delivery_orders` phải khớp với `models.py`.

LỖI ĐÃ XẢY RA THẬT, và chỉ xảy ra trên PostgreSQL. Nạp dữ liệu mẫu vào cơ sở dữ
liệu thật thì báo:

    CheckViolation: new row for relation "delivery_orders" violates check
    constraint "ck_delivery_orders_canonical_status"
    DETAIL: Failing row contains (DEMO-DO-2026-004, arrived, ...)

Vì sao chỉ lộ ra ở đó:

  · SQLite trong máy kiểm được DỰNG LẠI từ `models.py`
    (`Base.metadata.create_all`), nên nó luôn có ràng buộc mới nhất.
  · PostgreSQL thật thì nâng cấp TỪNG BƯỚC. Ràng buộc đó sinh ở mốc
    `013_demo_stabilization` với BỐN trạng thái, và khi `arrived` được thêm vào
    `models.py` thì KHÔNG có mốc nào sửa ràng buộc theo. Schema trôi khỏi mô
    hình một cách im lặng.

Hậu quả không chỉ ở dữ liệu mẫu: MỌI đường ghi `arrived` đều vỡ trên cơ sở dữ
liệu thật — kể cả đường thật mà người điều phối bấm ("ghi xe đã đến nơi").

Bài kiểm này khóa hai chiều để chuyện đó không lặp lại:

  1. Danh sách trạng thái trong mốc `032` và trong `models.py` phải GIỐNG NHAU.
     Sửa một chỗ mà quên chỗ kia thì bài đỏ ngay, chứ không đợi tới lúc một dòng
     `arrived` bị chặn trên máy khách.
  2. Trên SQLite dựng từ mốc, một dòng `arrived` phải ghi được.
"""

import importlib
import sqlite3

from migrations.runner import upgrade, required_migration_head
from migrations import v032_delivery_order_arrived_status as v032


def test_moc_nay_da_duoc_dang_ky_trong_chuoi():
    # v032 KHONG con la moc cuoi (moc 033 da them sau no). Doi phep kiem sang
    # dieu that su can giu: moc nay CO trong chuoi, va chuoi con di qua no.
    #
    # Ban truoc ghim `required_migration_head() == v032.VERSION`, va no do ngay
    # khi moc 033 duoc them — do vi mot ly do khong lien quan gi toi dieu bai
    # kiem nay bao ve, la rang buoc `arrived` phai khop giua moc va `models.py`.
    # So bang CHUOI `VERSION`, khong bang dinh danh module (`v032 in MIGRATIONS`).
    #
    # Cung mot moc nap qua hai duong nhap khac nhau — `from migrations import
    # v032_...` o day, con `from . import v032_...` trong `runner.py` — co the
    # tao ra HAI doi tuong module khac nhau, va phep so dinh danh that bai. Bai
    # nay da do dung vi ly do do khi chay cung cac bai moc khac, trong khi chay
    # rieng thi xanh: mot bai kiem chi do theo THU TU chay la bai kiem khong tin
    # duoc.
    from migrations.runner import MIGRATIONS
    ds = [m.VERSION for m in MIGRATIONS]
    assert v032.VERSION in ds, "moc 032 phai duoc dang ky trong chuoi"
    assert required_migration_head() == ds[-1]


def test_danh_sach_trang_thai_khop_voi_models():
    """Mốc và mô hình phải khai CÙNG một bộ trạng thái.

    Đây là phép kiểm quan trọng nhất trong tệp này: chính chỗ lệch giữa hai nơi
    đó đã làm vỡ mọi đường ghi `arrived` trên cơ sở dữ liệu thật.
    """
    models = importlib.import_module("models")

    khai = ""
    for rang_buoc in models.DeliveryOrder.__table__.constraints:
        # `sqltext` là một mệnh đề SQLAlchemy, và truthiness của nó KHÔNG được
        # định nghĩa — `clause or ""` ném TypeError. Nên phải `str()` trước.
        sqltext = getattr(rang_buoc, "sqltext", None)
        sql = str(sqltext) if sqltext is not None else ""
        if "canonical_status" in sql and "IN" in sql:
            khai = sql
            break
    assert khai, "models.py không còn ràng buộc CHECK cho canonical_status"

    thieu = [tt for tt in v032.TRANG_THAI if "'%s'" % tt not in khai]
    assert not thieu, (
        "mốc 032 cho phép %s mà models.py thiếu: %s" % (list(v032.TRANG_THAI), thieu))

    # Và ngược lại: models.py không được có trạng thái mà mốc chưa cho phép —
    # đó đúng là hình dạng của lỗi đã xảy ra.
    import re
    trong_models = set(re.findall(r"'([a-z_]+)'", khai))
    du = sorted(trong_models - set(v032.TRANG_THAI))
    assert not du, (
        "models.py cho phép %s mà mốc 032 chưa mở trên PostgreSQL — "
        "mọi dòng ghi các trạng thái đó sẽ bị chặn" % du)


def test_cau_sql_cua_moc_co_du_nam_trang_thai():
    cau = v032.statements("postgresql", "upgrade")
    assert any("DROP CONSTRAINT" in c for c in cau), "phải bỏ ràng buộc cũ trước"
    them = [c for c in cau if "ADD CONSTRAINT" in c]
    assert len(them) == 1, "phải thêm lại đúng một ràng buộc"
    for tt in v032.TRANG_THAI:
        assert "'%s'" % tt in them[0], "câu SQL thiếu trạng thái %r" % tt


def test_lui_lai_doi_cac_dong_arrived_truoc_khi_that_rang_buoc():
    """Lùi mốc phải đổi dữ liệu TRƯỚC, không thì lệnh thắt ràng buộc vỡ.

    Ràng buộc cũ chỉ có bốn trạng thái. Nếu còn dòng nào đang ở `arrived` thì
    `ADD CONSTRAINT` bị từ chối, và cả phép lùi vỡ giữa đường.
    """
    cau = v032.statements("postgresql", "rollback")
    i_update = next(i for i, c in enumerate(cau) if c.startswith("UPDATE delivery_orders"))
    i_add = next(i for i, c in enumerate(cau) if "ADD CONSTRAINT" in c)
    assert i_update < i_add, "phải đổi dữ liệu trước khi thắt lại ràng buộc"
    # Đổi sang `in_transit`, không phải `delivered`: `delivered` nói "xong rồi",
    # và đặt sai sang đó là mở cho chốt tiền một chuyến chưa ký POD.
    assert "'in_transit'" in cau[i_update]
    assert "'delivered'" not in cau[i_update]


def test_sqlite_dung_tu_moc_ghi_duoc_dong_arrived(tmp_path):
    """Trên SQLite dựng từ mốc, một dòng `arrived` phải ghi được.

    SQLite không sửa được CHECK bằng ALTER TABLE, nên mốc này không làm gì ở đó —
    và bài kiểm giữ cho giả định đó đúng: schema SQLite phải vốn đã cho phép
    `arrived`, không thì phải làm thêm việc.
    """
    tep = tmp_path / "arrived.sqlite3"
    # Dựng năm bảng nền TRƯỚC, đúng như `test_migration_v001._legacy` làm. Chạy
    # `upgrade` trên một tệp rỗng thì vỡ ngay ở một mốc cố thêm cột vào bảng
    # chưa tồn tại — chuỗi mốc của dự án vốn bắt đầu từ một cơ sở dữ liệu cũ,
    # không từ chỗ trắng.
    goc = sqlite3.connect(tep)
    goc.executescript(
        """
        CREATE TABLE quotations (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE sales_orders (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT);
        CREATE TABLE delivery_orders (id TEXT PRIMARY KEY, so_id TEXT, customer_id TEXT, status TEXT);
        CREATE TABLE ar_invoices (id TEXT PRIMARY KEY, do_id TEXT, customer_id TEXT, amount REAL, vat_pct REAL, vat_amount REAL, total REAL, status TEXT);
        CREATE TABLE gl_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, date TEXT, account_code TEXT, debit REAL, credit REAL);
        """
    )
    goc.commit()
    goc.close()

    upgrade(str(tep))

    with sqlite3.connect(tep) as ket_noi:
        ket_noi.execute("PRAGMA foreign_keys = OFF")
        ket_noi.execute(
            "INSERT INTO delivery_orders(id, canonical_status) VALUES ('DO-ARR-01', 'arrived')")
        ket_noi.commit()
        assert ket_noi.execute(
            "SELECT canonical_status FROM delivery_orders WHERE id='DO-ARR-01'"
        ).fetchone()[0] == "arrived"
