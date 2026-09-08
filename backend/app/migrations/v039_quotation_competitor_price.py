"""Gia doi thu ma khach noi ra, luu tren tung bao gia.

VI SAO CAN MOT COT RIENG, khong nhet vao `notes_internal`.

`SPEC-quotation-page.md` muc 3.9 khai cot phai cua phieu bao gia gom "2-3 bao
gia gan nhat (gia, ma, ket qua) + GIA DOI THU NEU CO". Do la mot con so nguoi
ban doc ngay truoc khi go muc gia moi — cung voi gia thanh, no la hai dau moc
quyet dinh mot bao gia nen bao bao nhieu.

Nhet vao o ghi chu noi bo thi khong doc lai duoc bang may: khong loc duoc "cac
tuyen ta dang bao cao hon doi thu", khong dung duoc lam moc gia goi y, va khong
ai doi soat duoc sau mot quy la nhung lan mat khach co that vi gia hay khong.
Mot con so nam trong mot doan van tu do la mot con so khong ton tai voi he
thong.

COT NAY DUOC PHEP RONG, va rong la truong hop thuong gap: khach khong noi gia
doi thu thi khong ai doan ho. Giao dien chi hien dong "gia doi thu" khi co so
that, chu khong hien mot o "—" lam nguoi doc tuong da tra ma khong ra.

Don vi la VND, giong moi cot tien khac cua bang `quotations`: tien te bao gia
chi doi cach HIEN, con so luu luon la dong Viet Nam.
"""

VERSION = "039_quotation_competitor_price"

from sqlalchemy import text


BANG = "quotations"
COT = "competitor_price"


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return ["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (BANG, COT)]
    return ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s NUMERIC(18, 2)" % (BANG, COT)]


def _bang_ton_tai(connection):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % BANG)))


def _sql_bang(connection):
    dong = list(connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='%s'" % BANG))
    return (dong[0][0] or "") if dong else ""


def upgrade_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    if COT not in _sql_bang(connection):
        connection.execute("ALTER TABLE %s ADD COLUMN %s NUMERIC" % (BANG, COT))
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """De nguyen cot — bo cot trong SQLite ban cu phai dung lai ca bang."""
    return


def validate_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    if COT not in _sql_bang(connection):
        raise RuntimeError("thieu cot %s.%s" % (BANG, COT))


def validate_postgresql(connection):
    ton_tai = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = :bang
    """), {"bang": BANG}))
    if not ton_tai:
        return
    co = {r[0] for r in connection.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :bang
    """), {"bang": BANG})}
    if COT not in co:
        raise RuntimeError("thieu cot %s.%s" % (BANG, COT))
