"""Bai, to va mau xoay ca cua tai xe.

VI SAO CAN. Man "Sap lich xe va tai xe" lam theo ban mau
`nhap_UI__duan/shift-schedule-v5-staff-vehicle.html` xep lich theo mot thu tu
ba tang: BAI -> TO -> NGUOI. Bang `vehicles` da co `depot`/`depot_code` tu moc
025, nhung bang `drivers` thi khong co gi ca — khong bai, khong to, khong mau
xoay. Hau qua thuc te o quy mo cua du an (~500 xe, hang tram tai xe, nhieu bai):
mot man xep ca chi co the hien MOT danh sach phang hang tram nguoi, va nguoi
truc bai Song Than phai cuon qua tai xe cua muoi bon bai khac de tim nguoi cua
minh. Do khong phai mot man dung duoc.

Ba cot, va vi sao tung cot can that:

  · `depot_code` — bai ma tai xe thuoc ve. Khop voi `vehicles.depot_code` de
    mot bai xem duoc ca nguoi VA xe cua minh trong cung mot man. Suy tu
    `assigned_vehicle` thi khong dung: mot tai xe co the chua gan xe, hoac gan
    xe cua bai khac trong mot ngay dieu chuyen.
  · `team_code` — to (ca doi truc). To la don vi XEP CA that: ca sang cua bai
    do to A truc, khong phai do "12 nguoi nao cung duoc". Thieu cot nay thi
    con so "can 12 nguoi ca sang" khong gan vao dau duoc.
  · `rotation_pattern` — mau xoay ca, viet nhu `SSCCDD--` (S sang, C chieu,
    D dem, `-` nghi). Day la thu ma chuc nang sinh lich theo mau doc de sinh
    ca cho ca thang. Truoc day mau xoay chi ton tai trong dau nguoi xep lich.

Ca ba cot de RONG duoc. Bo du lieu dang chay co tai xe chua khai bai va to, va
bat buoc o tang co so du lieu thi moi ban ghi cu deu vo. Man hinh xu ly bang
mot nhom "chua phan to" hien thi ro, chu khong bang mot gia tri mac dinh bia ra
— dat sang tai xe vao "To A" thi con so do phu cua to A sai, va sai theo huong
NGUY HIEM: bao la du nguoi trong khi khong ai truc.
"""

VERSION = "034_driver_depot_team_pattern"

from sqlalchemy import text


BANG = "drivers"
COT = ("depot_code", "team_code", "rotation_pattern")


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        # Lui moc nay lam MAT phan to cua tai xe — lich da xep van con, nhung
        # khong con biet ai thuoc to nao. Chi dung khi buoc phai lui ban phat
        # hanh.
        return ["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (BANG, c) for c in COT]
    cau = ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s VARCHAR" % (BANG, c) for c in COT]
    # Bo loc chinh cua man la bai roi to, tren hang tram tai xe — nen hai cot do
    # can chi muc. `rotation_pattern` khong loc theo nen khong can.
    cau.append("CREATE INDEX IF NOT EXISTS ix_drivers_depot_code ON %s (depot_code)" % BANG)
    cau.append("CREATE INDEX IF NOT EXISTS ix_drivers_team_code ON %s (team_code)" % BANG)
    return cau


def _bang_ton_tai(connection):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % BANG)))


def _cot_hien_co(connection):
    dong = list(connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='%s'" % BANG))
    return dong[0][0] or "" if dong else ""


def upgrade_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    # `ADD COLUMN IF NOT EXISTS` khong co trong SQLite, nen phai tu kiem tung
    # cot — them lai mot cot da co thi SQLite nem loi va ca chuoi moc vo.
    sql = _cot_hien_co(connection)
    for c in COT:
        if c not in sql:
            connection.execute("ALTER TABLE %s ADD COLUMN %s TEXT" % (BANG, c))
    connection.execute("CREATE INDEX IF NOT EXISTS ix_drivers_depot_code ON %s (depot_code)" % BANG)
    connection.execute("CREATE INDEX IF NOT EXISTS ix_drivers_team_code ON %s (team_code)" % BANG)
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """SQLite khong bo duoc cot bang ALTER TABLE o cac ban cu.

    De nguyen ba cot: mot cot du khong lam vo gi, con dung lai ca bang `drivers`
    de chep du lieu sang thi rui ro hon nhieu so voi cai duoc — nhieu bang tro
    khoa ngoai vao day.
    """
    return


def validate_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    sql = _cot_hien_co(connection)
    thieu = [c for c in COT if c not in sql]
    if thieu:
        raise RuntimeError("thieu cot %s.%s" % (BANG, ", ".join(thieu)))


def validate_postgresql(connection):
    # Thoat som khi bang chua co — cung khuon voi cac moc khac: hai bai kiem
    # chay moc nay qua mot co may PostgreSQL GIA LAP chi ghi lai cau SQL chu
    # khong tra ve du lieu.
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
