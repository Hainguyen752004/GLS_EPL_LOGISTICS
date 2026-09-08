"""So niem phong cua lenh giao hang.

VI SAO CAN COT NAY. Quy tac kiem soat hang moi chia lam hai duong: hang dem
duoc theo kien thi phai quet du kien qua Packing List; hang NGUYEN KHOI thi
khong dem kien — mot container niem phong la mot don vi, xe khong mo ra de dem.
Nhung khong dem kien thi phai co MOT bang chung khac cho biet hang khong bi mo
tren duong, va bang chung do la SO NIEM PHONG.

Bang `delivery_orders` truoc day chi co `seal_weight` — do la TRONG TAI niem
phong, mot con so, khong phai so hieu. Khong the dung no de doi chieu khi xe
den noi. Nen phai co `seal_no` that.

Cot de RONG duoc: khong phai don nao cung la hang nguyen khoi, va bat buoc o
tang co so du lieu thi moi don le cung phai dien mot o vo nghia. Cho bat buoc
nam o tang nghiep vu (`packing_control_policy`), noi biet don nay thuoc loai
nao.
"""

VERSION = "033_delivery_order_seal_no"

from sqlalchemy import text


BANG = "delivery_orders"
COT = "seal_no"


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        # PostgreSQL bo duoc cot; lui mot mocc lam MAT du lieu niem phong da ghi,
        # nen day la duong chi dung khi buoc phai lui han ban phat hanh.
        return ["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (BANG, COT)]
    return ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s VARCHAR" % (BANG, COT)]


def _co_cot(connection):
    dong = list(connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='%s'" % BANG))
    return bool(dong) and COT in (dong[0][0] or "")


def _bang_ton_tai(connection):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % BANG)))


def upgrade_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    # `ADD COLUMN IF NOT EXISTS` khong co trong SQLite, nen phai tu kiem truoc —
    # them lai mot cot da co thi SQLite nem loi va ca chuoi moc vo.
    if not _co_cot(connection):
        connection.execute("ALTER TABLE %s ADD COLUMN %s TEXT" % (BANG, COT))
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """SQLite khong bo duoc cot bang ALTER TABLE o cac ban cu.

    Bo mot cot trong SQLite phai dung lai ca bang roi chep du lieu sang. O day
    khong lam viec do va de nguyen cot: mot cot du khong lam vo gi ca, con dung
    lai ca bang `delivery_orders` — bang co nhieu khoa ngoai tro vao nhat — thi
    rui ro hon nhieu so voi cai duoc.
    """
    return


def validate_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    if not _co_cot(connection):
        raise RuntimeError("thieu cot %s.%s" % (BANG, COT))


def validate_postgresql(connection):
    # Thoat som khi bang chua co — cung khuon voi cac moc khac trong du an: hai
    # bai kiem chay moc nay qua mot co may PostgreSQL GIA LAP chi ghi lai cau
    # SQL chu khong tra ve du lieu.
    ton_tai = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = :bang
    """), {"bang": BANG}))
    if not ton_tai:
        return
    dong = list(connection.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :bang AND column_name = :cot
    """), {"bang": BANG, "cot": COT}))
    if not dong:
        raise RuntimeError("thieu cot %s.%s" % (BANG, COT))
