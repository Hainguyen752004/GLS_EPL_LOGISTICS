"""So km dong ho va moc bao duong ke tiep cua xe.

VI SAO CAN. Man "Sap lich xe va tai xe" co mot thanh nho duoi bien so tra loi
cau hoi "xe nay con bao nhieu km den ky bao duong". Do la cach doi xe THAT lap
lich bao duong: khong ai bao duong theo ngay lich, ho bao duong theo km chay.
Bang `vehicles` truoc day chi co `maintenance_date` — MOT CHUOI NGAY, va la ngay
bao duong gan nhat chu khong phai moc ke tiep. Voi mot chiec xe chay 400 km mot
ngay thi mot ngay lich noi khong duoc gi ca.

Hai cot, va vi sao phai la hai:

  · `odometer_km` — so km dong ho HIEN TAI. Day la con so duy nhat doc duoc tu
    xe, va no la goc cua moi phep tinh con lai.
  · `next_service_odometer_km` — moc dong ho cua ky bao duong KE TIEP. Luu moc
    tuyet doi chu khong luu "chu ky 5.000 km": chu ky thi phai biet lan bao
    duong truoc o km bao nhieu moi tinh duoc, va con so do khong con sau khi
    ky bao duong duoc dong. Luu moc ke tiep thi "con lai" la mot phep tru.

Ca hai de RONG duoc, va man hinh PHAI xu ly duoc o rong bang cach noi "chua khai
so km" chu khong ve mot thanh 0%. Mot thanh do rong doc ra nhu "xe den han bao
duong gap", va nguoi dieu do se goi xe ve garage trong khi khong ai biet no da
chay bao nhieu.

Khong dat gia tri mac dinh: mot so km bia ra thi te hon mot o trong, vi o trong
thi nguoi dung biet la chua co du lieu.
"""

VERSION = "035_vehicle_odometer"

from sqlalchemy import text


BANG = "vehicles"
COT = ("odometer_km", "next_service_odometer_km")


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
    # `ADD COLUMN IF NOT EXISTS` khong co trong SQLite nen phai tu kiem tung cot.
    sql = _sql_bang(connection)
    for c in COT:
        if c not in sql:
            connection.execute("ALTER TABLE %s ADD COLUMN %s REAL" % (BANG, c))
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """De nguyen hai cot.

    Bo mot cot trong SQLite ban cu phai dung lai ca bang roi chep du lieu sang.
    Bang `vehicles` co rat nhieu bang tro khoa ngoai vao, nen dung lai no rui ro
    hon nhieu so voi cai duoc tu viec don hai cot du.
    """
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
