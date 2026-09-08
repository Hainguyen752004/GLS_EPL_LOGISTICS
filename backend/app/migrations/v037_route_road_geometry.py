"""Hinh duong BO that cua tuyen, luu lai de khong phai lay lai.

VI SAO CAN. So do lo trinh truoc day ve mot DUONG THANG noi cac diem tram. Chu
du an noi thang: *"tui muon cai tuyen duong di la su that nen ve cai duong thang
mang di demo ky lam"*. Va anh dung: mot duong thang tu Long An sang Cai Mep di
xuyen qua song, qua khu dan cu, va noi sai ca hai dieu quan trong nhat cua mot
tuyen — xe di duong nao, va dai bao nhieu.

Hinh duong bo that thi lay duoc tu mot dich vu dan duong, nhung KHONG LAY LAI
MOI LAN VE:

  · Mot tuyen bon diem tra ve hon hai nghin diem hinh. Lay lai moi lan mo man
    la mot giay cho va mot loi goi ra ngoai cho mot thu khong bao gio doi.
  · Dich vu do co the khong toi duoc — dung tinh huong da lam ban do trang.
    Luu lai thi tuyen da tung ve duoc se ve duoc mai, ke ca khi mat mang.

Hai cot:

  · `road_geometry_json` — hinh duong bo da luu, kem DAU VAN cua danh sach diem.
    Dau van la de biet khi nao phai lay lai: nguoi dung them mot chang thi hinh
    cu khong con dung, va ve lai hinh cu la ve mot tuyen khong con ton tai.
  · `road_distance_km` — do dai duong BO that. Khac `distance_km`, la con so
    NGUOI DUNG KHAI. Giu ca hai chu khong ghi de: con so nguoi khai la thu dang
    nuoi phep tinh gia cuoc va ETA, thay no bang mot con so may lay ve la doi
    tien tren nhung don da chot. Chenh lech giua hai con so thi man hinh noi ra
    de nguoi dung tu quyet.

Ca hai de RONG duoc: tuyen chua tung mo thi chua co hinh, va giao dien phai ve
duoc duong noi diem KEM MOT LOI NOI RO rang day chua phai duong bo that.
"""

VERSION = "037_route_road_geometry"

from sqlalchemy import text


BANG = "routes"
COT_JSON = "road_geometry_json"
COT_KM = "road_distance_km"


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return ["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (BANG, c)
                for c in (COT_JSON, COT_KM)]
    return [
        "ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s TEXT" % (BANG, COT_JSON),
        "ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s DOUBLE PRECISION" % (BANG, COT_KM),
    ]


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
    if COT_JSON not in sql:
        connection.execute("ALTER TABLE %s ADD COLUMN %s TEXT" % (BANG, COT_JSON))
    if COT_KM not in sql:
        connection.execute("ALTER TABLE %s ADD COLUMN %s REAL" % (BANG, COT_KM))
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """De nguyen hai cot — bo cot trong SQLite ban cu phai dung lai ca bang."""
    return


def validate_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    sql = _sql_bang(connection)
    thieu = [c for c in (COT_JSON, COT_KM) if c not in sql]
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
    thieu = [c for c in (COT_JSON, COT_KM) if c not in co]
    if thieu:
        raise RuntimeError("thieu cot %s.%s" % (BANG, ", ".join(thieu)))
