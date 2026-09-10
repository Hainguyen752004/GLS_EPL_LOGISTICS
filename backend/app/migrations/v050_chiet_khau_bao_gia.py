"""Them cot `quotations.discount_percent` — CHIET KHAU cho khach tren bao gia.

VI SAO. Chu du an (10/09) chot bao gia co HAI ban in: ban NOI BO (du moi thong
tin: gia thanh tung khoan, bien, ghi chu noi bo) va PHIEU GUI KHACH chi gom cac
truong he thong cha cua tap doan can: trong luong, tien te, gia goc, doanh thu du
kien, gia goc SAU CHIET KHAU, doanh thu co chiet khau, ngay nhap. He thong chua
co khai niem chiet khau, nen them mot cot.

QUY UOC: `unit_price` / `selling_price` VAN LA GIA CUOI (sau chiet khau) — moi
duong phia sau (DO khoa gia, bien loi nhuan, closeout, hoa don) khong doi.
`discount_percent` (0..1) chi dung de SUY NGUOC gia goc truoc chiet khau cho
phieu gui khach: gia_goc = unit_price / (1 - discount_percent).
"""

VERSION = "050_chiet_khau_bao_gia"

from sqlalchemy import text


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return ["ALTER TABLE quotations DROP COLUMN IF EXISTS discount_percent"]
    return ["ALTER TABLE quotations ADD COLUMN IF NOT EXISTS discount_percent DOUBLE PRECISION"]


def _co_cot_sqlite(connection, bang, cot):
    return any(r[1] == cot for r in connection.execute('PRAGMA table_info("%s")' % bang))


def upgrade_sqlite(connection):
    if list(connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quotations'")) \
            and not _co_cot_sqlite(connection, "quotations", "discount_percent"):
        connection.execute("ALTER TABLE quotations ADD COLUMN discount_percent REAL")


def rollback_sqlite(connection):
    return


def validate_sqlite(connection):
    return


def validate_postgresql(connection):
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"))):
        return
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'quotations' "
            "AND column_name = 'discount_percent'"))):
        raise RuntimeError("quotations thieu cot discount_percent")
