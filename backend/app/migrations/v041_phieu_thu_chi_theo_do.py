"""Phieu thu va phieu chi, gan vao LENH GIAO HANG va tach theo KHOAN MUC.

CHU DU AN MO TA VIEC NAY nhu sau: *"cac chuc nang tao phieu thu phieu chi, vi du
chi cho cai DO 1 thi can nhung gi la phieu chi xang dau cac thu"*. Va anh chot
gan vao DO, theo dung ba tang cua he thong ma anh tu dinh nghia:

    Bao gia (QT) = thoa thuan voi khach: tuyen nao, loai xe gi, gia bao nhieu.
    DO           = mot lenh giao hang cu the: lo hang nay, lay ngay nay, giao
                   truoc gio nay. DO la thu khach yeu cau.
    Trip         = mot chuyen xe that: xe nao, tai xe nao, chay luc nao. Trip la
                   thu cong ty to chuc de thuc hien DO.

Cong no khach di theo DO, nen phieu di theo DO.

BA THU MOC NAY LAM:

  1. `do_vouchers` — phieu thu / phieu chi, mot BAN GHI DAU. Gan vao `do_id`;
     `trip_id` de tuy chon vi mot phan chi phi (xang dau, BOT) phat sinh o tang
     chuyen roi moi phan bo ve DO.
  2. `do_voucher_lines` — cac dong cua phieu, moi dong mot KHOAN MUC. Dung
     `charge_type` GIONG HET `freight_charge_items` (cung danh sach gia tri),
     nen he cong no doi chieu duoc hai ben ma khong phai anh xa.
  3. Them `yard` vao `ck_freight_charge_type`. Cong thuc gia thanh co khoan muc
     "Phi bai & luu kho" (key `yard`) ma danh sach `charge_type` KHONG co no —
     nen khoan muc do roi vao `other` va he cong no khong tach ra duoc. Chu du
     an da chot: "c) dung nhe".

VI SAO DUNG DAU-DONG chu khong phai mot bang phang. Chu du an chot hinh dang
phieu la "ca hai, nguoi dung chon": co luc tach RIENG tung khoan muc thanh tung
phieu (phieu chi xang dau, phieu chi phu cap tai xe), co luc GOP nhieu khoan muc
vao mot phieu khi tra cung mot lan cho cung mot nguoi. Dau-dong lam duoc ca hai:
mot dong la phieu theo tung khoan muc, nhieu dong la phieu gop.

VA VI SAO KHONG MO RONG `epl_expense_vouchers` DA CO. Bang do la mot chung tu
KHAC: mot phieu cho MOI CHUYEN (`UniqueConstraint("trip_id")`), mang nguoi quan
ly xe, so hop dong, so may, nguoi kiem — no la BANG KE CHI PHI CHUYEN de in cho
tai xe va quan ly, va man Bao cao van tai dang dung no
(`/api/tms/reporting/expense-vouchers`). Nhoi hai khai niem vao mot bang thi ca
hai deu mo ho. Hai bang song song, va chu thich o day noi ro quan he de lan sau
khong ai lan.

LUI LAI: bo hai bang moi va tra `charge_type` ve danh sach khong co `yard`.
Truoc khi that lai rang buoc phai doi cac dong dang o `yard` sang `other`, khong
thi lenh ADD CONSTRAINT vo — cung khuon voi moc 032 va 040.
"""

VERSION = "041_phieu_thu_chi_theo_do"

from sqlalchemy import text


#: Danh sach khoan muc, dung bang `models.FreightChargeItem`. Doi o day thi phai
#: doi ca o do.
KHOAN_MUC = ("fuel", "toll", "driver", "yard", "waiting", "loading", "unloading",
             "carrier_base", "surcharge", "discount", "other")
KHOAN_MUC_CU = ("fuel", "toll", "driver", "waiting", "loading", "unloading",
                "carrier_base", "surcharge", "discount", "other")

#: `thu` = tien thu ve tu khach. `chi` = tien tra ra.
LOAI_PHIEU = ("thu", "chi")
TRANG_THAI = ("draft", "posted", "cancelled")

RB_CHARGE = "ck_freight_charge_type"


def _lk(ds):
    return ", ".join("'%s'" % x for x in ds)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return [
            "DROP TABLE IF EXISTS do_voucher_lines",
            "DROP TABLE IF EXISTS do_vouchers",
            # Doi du lieu TRUOC khi that lai rang buoc.
            "UPDATE freight_charge_items SET charge_type = 'other' WHERE charge_type = 'yard'",
            "ALTER TABLE freight_charge_items DROP CONSTRAINT IF EXISTS %s" % RB_CHARGE,
            "ALTER TABLE freight_charge_items ADD CONSTRAINT %s"
            " CHECK (charge_type IN (%s))" % (RB_CHARGE, _lk(KHOAN_MUC_CU)),
        ]
    return [
        "ALTER TABLE freight_charge_items DROP CONSTRAINT IF EXISTS %s" % RB_CHARGE,
        "ALTER TABLE freight_charge_items ADD CONSTRAINT %s"
        " CHECK (charge_type IN (%s))" % (RB_CHARGE, _lk(KHOAN_MUC)),
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
        "CREATE INDEX IF NOT EXISTS ix_do_vouchers_do ON do_vouchers (do_id, kind)",
        "CREATE INDEX IF NOT EXISTS ix_do_vouchers_trip ON do_vouchers (trip_id)",
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
        "CREATE INDEX IF NOT EXISTS ix_do_voucher_lines_voucher"
        " ON do_voucher_lines (voucher_id)",
        "CREATE INDEX IF NOT EXISTS ix_do_voucher_lines_charge"
        " ON do_voucher_lines (charge_type)",
    ]


# --------------------------------------------------------------------- SQLite --

def _co_bang(connection, ten):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % ten)))


def upgrade_sqlite(connection):
    """SQLite duoc dung lai tu `models.py`, nen hai bang moi da co san o do.

    Chi tao khi CHUA co — mot SQLite dung tu chuoi moc (khong phai tu mo hinh)
    thi khong co chung. Cau CREATE khong khai FOREIGN KEY: SQLite khong cuong
    che khoa ngoai o day (bo nang cap con chu dong `PRAGMA foreign_keys=OFF`),
    nen khai chung chi lam cau lenh dai chu khong them bao dam nao.

    KHONG dat rang buoc CHECK cho `charge_type` o SQLite: `models.py` da khai
    `CheckConstraint` cho bang do, nen SQLite dung tu mo hinh co ngay danh sach
    moi. Dat them mot rang buoc chi co o SQLite se lam SQLite nghiem ngat hon
    PostgreSQL — dung nguoc voi van de ma moc 040 di chua.
    """
    if not _co_bang(connection, "do_vouchers"):
        connection.execute("""CREATE TABLE do_vouchers (
            id VARCHAR(128) PRIMARY KEY,
            voucher_no VARCHAR(128) NOT NULL UNIQUE,
            kind VARCHAR(8) NOT NULL,
            do_id VARCHAR NOT NULL,
            trip_id VARCHAR(128),
            voucher_date DATE NOT NULL,
            payment_method VARCHAR(32) NOT NULL DEFAULT 'cash',
            counterparty VARCHAR(255),
            status VARCHAR(16) NOT NULL DEFAULT 'draft',
            currency_code VARCHAR(8) NOT NULL DEFAULT 'VND',
            total_amount NUMERIC(24, 6) NOT NULL DEFAULT 0,
            note TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            created_by VARCHAR(128) NOT NULL,
            updated_by VARCHAR(128) NOT NULL)""")
    if not _co_bang(connection, "do_voucher_lines"):
        connection.execute("""CREATE TABLE do_voucher_lines (
            id VARCHAR(128) PRIMARY KEY,
            voucher_id VARCHAR(128) NOT NULL,
            charge_type VARCHAR(32) NOT NULL,
            description VARCHAR(500),
            amount NUMERIC(24, 6) NOT NULL DEFAULT 0,
            note TEXT)""")


def rollback_sqlite(connection):
    connection.execute("DROP TABLE IF EXISTS do_voucher_lines")
    connection.execute("DROP TABLE IF EXISTS do_vouchers")


def validate_sqlite(connection):
    for ten in ("do_vouchers", "do_voucher_lines"):
        if not _co_bang(connection, ten):
            raise RuntimeError("thieu bang %s" % ten)


# ----------------------------------------------------------------- PostgreSQL --

def validate_postgresql(connection):
    # Thoat som khi bang nen chua co — cung khuon voi cac moc khac. Hai bai kiem
    # chay moc nay qua mot co may Postgres GIA LAP chi ghi lai cau SQL.
    if not list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'freight_charge_items'
    """))):
        return

    for ten in ("do_vouchers", "do_voucher_lines"):
        if not list(connection.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :t
        """), {"t": ten})):
            raise RuntimeError("thieu bang %s tren PostgreSQL" % ten)

    dong = list(connection.execute(text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conrelid = 'freight_charge_items'::regclass
          AND contype = 'c' AND conname = :ten
    """), {"ten": RB_CHARGE}))
    if not dong:
        raise RuntimeError("thieu rang buoc %s" % RB_CHARGE)
    dinh_nghia = dong[0][0] or ""
    for km in KHOAN_MUC:
        if "'%s'" % km not in dinh_nghia:
            raise RuntimeError("rang buoc %s chua cho phep %r: %s"
                               % (RB_CHARGE, km, dinh_nghia))
