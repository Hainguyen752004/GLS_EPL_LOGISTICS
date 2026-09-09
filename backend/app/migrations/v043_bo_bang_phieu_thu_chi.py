"""Bo hai bang phieu thu / phieu chi. Chu du an chot BO HAN.

VI SAO CHUNG TUNG CO. Toi doc yeu cau "cac chuc nang tao phieu thu phieu chi"
thanh "dung man lap phieu trong he thong nay", va dung hai bang `do_vouchers` /
`do_voucher_lines` cung bay diem cuoi `/api/do-vouchers` (moc 041).

VI SAO BO. Chu du an chot lai pham vi: phieu thu/phieu chi la viec cua DONG
NGHIEP anh — anh ay keo du lieu ve page cua minh de lap. Nguyen van: *"anh chi
can tra cai DO hoan tat va show ra duoc full chi phi cac thu thoi con lai anh
cua anh lam viec"*. Nen phan lap phieu o day la lam qua pham vi, va de lai mot
bang khong ai ghi vao thi lan sau co nguoi tuong no la nguon su that.

BA THU GIU LAI, va chung moi la phan co gia tri that cua lan lam do:

  1. Khoan muc `yard` (Phi bai & luu kho) trong `ck_freight_charge_type`
     (moc 041). Cong thuc gia thanh co khoan muc do ma danh sach `charge_type`
     khong co no, nen no roi vao `other`.
  2. Bo rang buoc CHECK TRUNG tren `charge_type` (moc 042). Tren PostgreSQL that
     co HAI rang buoc cho cung mot cot, va cai mang ten tu sinh khong co `yard`
     — nen ghi `yard` qua duoc mot cai roi vo o cai kia.
  3. `services/khoan_muc_chi_phi.py` — danh muc khoan muc va phep suy ra ma phan
     loai. Nho lam phan phieu moi tim ra `tms_cost_service` VIET CUNG
     `charge_type="other"` cho MOI dong chi phi thuc te, nen ca bon dong chi phi
     cua mot chuyen deu ra "Khoan khac" va he cong no khong tach duoc xang dau
     voi cau duong. Do dung la thu chu du an can.

LUI LAI: dung lai hai bang theo dung hinh dang cua moc 041. Lui lai KHONG lam
hien ra cac diem cuoi `/api/do-vouchers` — chung da bo khoi ma nguon, nen hai
bang dung lai se rong va khong ai ghi vao. Chi lui khi that su phai ha phien ban
xuong truoc moc nay.
"""

VERSION = "043_bo_bang_phieu_thu_chi"

from sqlalchemy import text

LOAI_PHIEU = ("thu", "chi")
TRANG_THAI = ("draft", "posted", "cancelled")
KHOAN_MUC = ("fuel", "toll", "driver", "yard", "waiting", "loading", "unloading",
             "carrier_base", "surcharge", "discount", "other")


def _lk(ds):
    return ", ".join("'%s'" % x for x in ds)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        # Dung lai dung hinh dang cua moc 041.
        return [
            """CREATE TABLE IF NOT EXISTS do_vouchers (
                   id VARCHAR(128) PRIMARY KEY,
                   voucher_no VARCHAR(128) NOT NULL,
                   kind VARCHAR(8) NOT NULL,
                   do_id VARCHAR NOT NULL REFERENCES delivery_orders(id),
                   trip_id VARCHAR(128) REFERENCES transport_trips(id),
                   voucher_date DATE NOT NULL,
                   payment_method VARCHAR(32) NOT NULL DEFAULT 'cash',
                   counterparty VARCHAR(255),
                   status VARCHAR(16) NOT NULL DEFAULT 'draft',
                   currency_code VARCHAR(8) NOT NULL DEFAULT 'VND',
                   total_amount NUMERIC(24, 6) NOT NULL DEFAULT 0,
                   note TEXT,
                   version INTEGER NOT NULL DEFAULT 1,
                   created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   created_by VARCHAR(128) NOT NULL,
                   updated_by VARCHAR(128) NOT NULL,
                   CONSTRAINT uq_do_voucher_no UNIQUE (voucher_no),
                   CONSTRAINT ck_do_voucher_kind CHECK (kind IN (%s)),
                   CONSTRAINT ck_do_voucher_status CHECK (status IN (%s)),
                   CONSTRAINT ck_do_voucher_payment CHECK (
                       payment_method IN ('cash','bank_transfer','credit','other')),
                   CONSTRAINT ck_do_voucher_total CHECK (total_amount >= 0),
                   CONSTRAINT ck_do_voucher_version CHECK (version > 0)
               )""" % (_lk(LOAI_PHIEU), _lk(TRANG_THAI)),
            """CREATE TABLE IF NOT EXISTS do_voucher_lines (
                   id VARCHAR(128) PRIMARY KEY,
                   voucher_id VARCHAR(128) NOT NULL
                       REFERENCES do_vouchers(id) ON DELETE CASCADE,
                   charge_type VARCHAR(32) NOT NULL,
                   description VARCHAR(500),
                   amount NUMERIC(24, 6) NOT NULL DEFAULT 0,
                   note TEXT,
                   CONSTRAINT ck_do_voucher_line_charge CHECK (charge_type IN (%s)),
                   CONSTRAINT ck_do_voucher_line_amount CHECK (amount >= 0)
               )""" % _lk(KHOAN_MUC),
        ]
    # Bo bang con TRUOC bang cha: `do_voucher_lines` tro vao `do_vouchers`, va
    # PostgreSQL cuong che khoa ngoai nen thu tu nguoc lai se vo.
    return [
        "DROP TABLE IF EXISTS do_voucher_lines",
        "DROP TABLE IF EXISTS do_vouchers",
    ]


# --------------------------------------------------------------------- SQLite --

def upgrade_sqlite(connection):
    connection.execute("DROP TABLE IF EXISTS do_voucher_lines")
    connection.execute("DROP TABLE IF EXISTS do_vouchers")


def rollback_sqlite(connection):
    # Khong dung lai o SQLite: `models.py` khong con khai hai lop do, nen
    # `Base.metadata.create_all` cung khong dung chung. Dung lai bang tay o day
    # se tao hai bang mà mo hinh khong biet — dung cai lech giua schema va mo
    # hinh ma ca chuoi moc nay di chua.
    return


def validate_sqlite(connection):
    for ten in ("do_vouchers", "do_voucher_lines"):
        if list(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % ten)):
            raise RuntimeError("bang %s van con" % ten)


# ----------------------------------------------------------------- PostgreSQL --

def validate_postgresql(connection):
    # Thoat som khi chua co bang nen — cung khuon voi cac moc khac.
    if not list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'freight_charge_items'
    """))):
        return

    for ten in ("do_vouchers", "do_voucher_lines"):
        if list(connection.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :t
        """), {"t": ten})):
            raise RuntimeError("bang %s van con tren PostgreSQL" % ten)

    # VA GIU LAI `yard`. Day la phan co gia tri that cua lan lam phieu; bo bang
    # phieu khong duoc keo no di theo.
    dong = list(connection.execute(text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conrelid = 'freight_charge_items'::regclass
          AND contype = 'c' AND conname = 'ck_freight_charge_type'
    """)))
    if not dong or "'yard'" not in (dong[0][0] or ""):
        raise RuntimeError(
            "khoan muc 'yard' da mat khoi ck_freight_charge_type — bo bang phieu "
            "khong duoc keo no di theo")
