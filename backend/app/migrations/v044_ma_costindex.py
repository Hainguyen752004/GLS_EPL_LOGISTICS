"""Them cot `cost_index` — MA COSTINDEX cua EPL — vao hai bang dong tien.

VI SAO. Chu du an chot: khoi "Ho so da hoan tat" cua mot lenh giao hang la cho
dong nghiep (anh Khang) lay du lieu de lap phieu thu / phieu chi va ghi cong no
khach hang. Muon lap phieu thi phai co TUNG DONG thu, TUNG DONG chi, va moi
dong phai mang MA PHAN LOAI theo he thong cua ben tai chinh — anh goi no la
`costindex`. Ma nay do nguoi lam tai chinh tu dat tren cong thuc gia thanh
(Du lieu goc), roi di theo khoan muc suot luong:

    cong thuc gia thanh (theo loai xe, ghi de theo xe)
      -> bao gia
      -> chi phi thuc te cua chuyen        (`freight_charge_items.cost_index`)
      -> khoan khach tra them khi hoan tat (`delivery_order_charge_adjustments.cost_index`)
      -> ho so hoan tat                    (goi `ledger_lines`)

Truoc moc nay, ma chi ton tai o tang cong thuc (mot truong trong JSON
`cost_formulas.formula_expression`) va MAT ngay khi dong tien duoc ghi xuong
hai bang tren — nen ho so hoan tat khong co gi de tra cho ben cong no ngoai
TEN khoan muc, va ben do phai doan.

KHAC `charge_type`. `charge_type` la ma noi bo co dinh cua he (fuel / toll /
driver / yard ...), dung de nhom va tinh. `cost_index` la ma cua he ke toan ben
ngoai, do nguoi dung dat, co the doi. Hai ma song song la co chu y: mot cai cho
may cua minh, mot cai cho may cua ho.

Cot cho phep NULL: du lieu cu chua co ma, va mot khoan muc nguoi dung tu them
tren man cong thuc co the chua duoc gan ma. Ho so hoan tat noi ro "chua gan ma"
thay vi bia mot ma.
"""

VERSION = "044_ma_costindex"

from sqlalchemy import text

BANG = ("freight_charge_items", "delivery_order_charge_adjustments")


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return ["ALTER TABLE %s DROP COLUMN IF EXISTS cost_index" % b for b in BANG]
    return ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS cost_index VARCHAR(32)" % b for b in BANG]


# --------------------------------------------------------------------- SQLite --
# Nhanh SQLite giu cho du hinh voi cac moc khac; du an da ngung SQLite hoan toan.

def _co_cot_sqlite(connection, bang, cot):
    return any(r[1] == cot for r in connection.execute('PRAGMA table_info("%s")' % bang))


def upgrade_sqlite(connection):
    for b in BANG:
        if list(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % b)) \
                and not _co_cot_sqlite(connection, b, "cost_index"):
            connection.execute("ALTER TABLE %s ADD COLUMN cost_index VARCHAR(32)" % b)


def rollback_sqlite(connection):
    return


def validate_sqlite(connection):
    for b in BANG:
        if list(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % b)) \
                and not _co_cot_sqlite(connection, b, "cost_index"):
            raise RuntimeError("%s thieu cot cost_index" % b)


# ----------------------------------------------------------------- PostgreSQL --

def validate_postgresql(connection):
    for b in BANG:
        if not list(connection.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :b"""), {"b": b})):
            continue
        if not list(connection.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :b AND column_name = 'cost_index'
        """), {"b": b})):
            raise RuntimeError("%s thieu cot cost_index tren PostgreSQL" % b)
