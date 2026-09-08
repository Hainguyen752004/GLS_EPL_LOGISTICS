"""Toa do cua dia diem — cot that tren bang `locations`.

VI SAO CAN. So do lo trinh cua man Tuyen duong ve duoc hay khong phu thuoc mot
dieu duy nhat: co biet diem di va diem den o dau. Truoc day cau tra loi nam o
HAI CHO, va ca hai deu sai cho:

  · Mot bang Python cung trong `tracking_control_service.py`. Bang do chi biet
    muoi bon dia diem cua bo du lieu demo. Nguoi dung tao mot tuyen moi voi mot
    kho moi thi khong co dong nao noi ve no, va ban do trang tron — ma khong
    the sua duoc tru khi sua ma nguon va phat hanh lai.
  · Mot loi goi ra `nominatim.openstreetmap.org` TU TRINH DUYET nguoi dung. Do
    duoc tren may that: host do KHONG TOI DUOC tu mang cua du an, nen duong nay
    luon that bai va man hinh bao "Khong xac dinh duoc toa do tuyen duong".

Toa do cua mot dia diem la DU LIEU GOC cua dia diem do — cung loai voi dia chi
va loai kho. No phai nam tren bang `locations`, sua duoc, va tra ve tu may chu.
Khi tra duoc bang mot dich vu ngoai thi ghi lai vao day, nen lan sau khong can
mang nua.

Hai cot de RONG duoc: bo du lieu dang chay co dia diem chua biet toa do, va man
hinh phai noi ro "chua biet toa do diem nay" chu khong duoc dat mot cap (0, 0)
— cap do se dat dia diem ra ngoai khoi bo bien chau Phi.
"""

VERSION = "036_location_coordinates"

from sqlalchemy import text


BANG = "locations"
COT = ("latitude", "longitude")


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return ["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (BANG, c) for c in COT]
    return ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s DOUBLE PRECISION" % (BANG, c)
            for c in COT]


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
    sql = _sql_bang(connection)
    for c in COT:
        if c not in sql:
            connection.execute("ALTER TABLE %s ADD COLUMN %s REAL" % (BANG, c))
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """De nguyen hai cot — bo cot trong SQLite ban cu phai dung lai ca bang."""
    return


def validate_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    sql = _sql_bang(connection)
    thieu = [c for c in COT if c not in sql]
    if thieu:
        raise RuntimeError("thieu cot %s.%s" % (BANG, ", ".join(thieu)))


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
    thieu = [c for c in COT if c not in co]
    if thieu:
        raise RuntimeError("thieu cot %s.%s" % (BANG, ", ".join(thieu)))
