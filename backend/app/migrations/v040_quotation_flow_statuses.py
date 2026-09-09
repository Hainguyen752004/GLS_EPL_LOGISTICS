"""Bon trang thai cua luong bao gia MOI phai duoc CO SO DU LIEU cho phep.

LOI DA DO DUOC TREN POSTGRESQL THAT, bang giao dich roi hoan tac (khong ghi gi):

    ✓ draft, sent, approved, cancelled   ghi duoc
    ✗ pending_approval  BI RANG BUOC CHAN
    ✗ accepted          BI RANG BUOC CHAN
    ✗ split             BI RANG BUOC CHAN
    ✗ rejected          BI RANG BUOC CHAN
    ✗ expired           BI RANG BUOC CHAN

Rang buoc `ck_quotations_canonical_status` tren PostgreSQL that chi cho nam gia
tri: draft, sent, approved, cancelled, unknown. Nhung ma nguon cua luong bao gia
moi GHI THEM bon gia tri: `pending_approval` (gui khach khi bien duoi nguong),
`accepted` (khach chap nhan), `rejected` (khach tu choi), `split` (da tach ra
lenh giao hang).

Nghia la BON BUOC XUONG SONG cua luong deu vo tren co so du lieu that. Va 8
trong 10 case demo (7 `split` + 1 `pending_approval`) khong ton tai duoc tren
PostgreSQL.

VI SAO CHI LO RA TREN POSTGRESQL, va vi sao no vo hinh lau hon lan truoc:

  · Lan truoc (`032_delivery_order_arrived_status`) thi `models.py` CO khai
    `CheckConstraint`, nen SQLite dung tu mo hinh co ngay rang buoc moi va chi
    PostgreSQL bi troi.
  · Lan nay `models.py` KHONG khai `CheckConstraint` nao cho `quotations`. Nen
    SQLite khong co rang buoc gi ca va nhan MOI gia tri. Ca hai ben deu "chay
    tron", chi khac la mot ben khong kiem gi con ben kia kiem theo mot danh
    sach da cu. Khong mot bai kiem nao chay tren SQLite co the phat hien ra.

Moc nay dua rang buoc ve dung tap gia tri ma ma nguon that su ghi, cong thoi
`expired` va `unknown`:

  · `expired` — bao gia het han. Chua co duong nao ghi, nhung no la mot moc that
    trong luong (`khach_chap_nhan` chan bao gia het han) va se co, nen mo san
    thay vi cho no vo mot lan nua.
  · `unknown` — giu lai vi du lieu cu dang co the dung, va bo no di la mot phep
    lui khong can thiet.

VA BO SUNG `items.notes`: cot do co trong `models.py` ("O Ghi chu tren man bao
gia") ma KHONG co tren PostgreSQL — mot cho troi nua, tim ra trong cung lan doi
chieu. Chua co duong nao ghi vao no, nen no chua gay loi; nhung de nguyen thi
lan dau co nguoi ghi la vo.

LUI LAI: doi cac dong dang o bon trang thai moi ve `draft` truoc, khong thi rang
buoc cu khong dat duoc va lenh ADD CONSTRAINT se vo. `draft` la lua chon an toan
nhat trong so cac gia tri con lai: no noi "chua di dau ca", con `sent` hay
`approved` thi khang dinh mot viec da xay ra. Luu y that: mot lan lui se LAM MAT
thong tin — mot bao gia da tach ra lenh giao hang tro thanh ban nhap. Do la ly
do phep lui o day chi nen dung khi that su phai ha phien ban.
"""

VERSION = "040_quotation_flow_statuses"

from sqlalchemy import text


#: Tap gia tri ma nguon THAT SU ghi, cong `expired` va `unknown`.
#:
#: Doc ra bang cach quet cac phep gan `canonical_status = "..."` trong
#: `bao_gia_service.py` va `workflow_service.py`. Them mot trang thai bao gia
#: moi thi PHAI them vao day, khong thi no vo tren PostgreSQL.
TRANG_THAI = (
    "draft",
    "pending_approval",
    "sent",
    "approved",
    "accepted",
    "rejected",
    "split",
    "expired",
    "cancelled",
    "unknown",
)

#: Nam gia tri cua rang buoc cu tren PostgreSQL, do duoc bang
#: `pg_get_constraintdef`.
TRANG_THAI_CU = ("draft", "sent", "approved", "cancelled", "unknown")

#: Bon gia tri chi ton tai o ban moi — phai doi ve `draft` truoc khi lui.
CHI_CO_O_BAN_MOI = tuple(x for x in TRANG_THAI if x not in TRANG_THAI_CU)

RANG_BUOC = "ck_quotations_canonical_status"


def _lieu_ke(ds):
    return ", ".join("'%s'" % x for x in ds)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        # SQLite di qua `upgrade_sqlite` / `rollback_sqlite` ben duoi: no khong
        # sua duoc CHECK bang ALTER TABLE, va cot thi phai kiem truoc khi them.
        return []
    if direction == "rollback":
        return [
            "UPDATE quotations SET canonical_status = 'draft'"
            " WHERE canonical_status IN (%s)" % _lieu_ke(CHI_CO_O_BAN_MOI),
            "ALTER TABLE quotations DROP CONSTRAINT IF EXISTS %s" % RANG_BUOC,
            "ALTER TABLE quotations ADD CONSTRAINT %s"
            " CHECK (canonical_status IN (%s))" % (RANG_BUOC, _lieu_ke(TRANG_THAI_CU)),
            "ALTER TABLE items DROP COLUMN IF EXISTS notes",
        ]
    return [
        "ALTER TABLE quotations DROP CONSTRAINT IF EXISTS %s" % RANG_BUOC,
        "ALTER TABLE quotations ADD CONSTRAINT %s"
        " CHECK (canonical_status IN (%s))" % (RANG_BUOC, _lieu_ke(TRANG_THAI)),
        "ALTER TABLE items ADD COLUMN IF NOT EXISTS notes TEXT",
    ]


# --------------------------------------------------------------------- SQLite --

def _co_bang(connection, ten):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % ten
    )))


def _co_cot(connection, bang, cot):
    return any(hang[1] == cot for hang in connection.execute("PRAGMA table_info(%s)" % bang))


def upgrade_sqlite(connection):
    """Tren SQLite chi con viec them cot `items.notes` neu thieu.

    Khong dat CHECK hay TRIGGER cho `quotations.canonical_status` o day, va do
    la mot lua chon co y: `models.py` khong khai `CheckConstraint` cho bang do,
    nen dat mot rang buoc chi co o SQLite se lam SQLite NGHIEM NGAT HON
    PostgreSQL — dung nguoc lai voi van de moc nay di chua. Cho nao la nguon su
    that thi chi co mot cho, va o day nguon do la `models.py`.
    """
    if _co_bang(connection, "items") and not _co_cot(connection, "items", "notes"):
        connection.execute("ALTER TABLE items ADD COLUMN notes TEXT")


def rollback_sqlite(connection):
    # SQLite truoc phien ban 3.35 khong co `DROP COLUMN`, va bo mot cot chi de
    # lui lai thi khong dang rui ro. De nguyen cot: no rong va vo hai.
    return


def validate_sqlite(connection):
    if _co_bang(connection, "items"):
        if not _co_cot(connection, "items", "notes"):
            raise RuntimeError("items van thieu cot notes")


# ----------------------------------------------------------------- PostgreSQL --

def validate_postgresql(connection):
    # Thoat som khi bang chua co — cung khuon voi cac moc khac trong du an. Hai
    # bai kiem chay moc nay qua mot co may Postgres GIA LAP: no chi ghi lai cau
    # SQL, khong tra ve du lieu, nen truy van `information_schema` tra ve rong
    # va phep kiem nhuong duong.
    ton_tai = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'quotations'
    """)))
    if not ton_tai:
        return

    dong = list(connection.execute(text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conrelid = 'quotations'::regclass AND contype = 'c' AND conname = :ten
    """), {"ten": RANG_BUOC}))
    if not dong:
        raise RuntimeError("thieu rang buoc %s" % RANG_BUOC)
    dinh_nghia = dong[0][0] or ""
    for tt in TRANG_THAI:
        if "'%s'" % tt not in dinh_nghia:
            raise RuntimeError(
                "rang buoc %s chua cho phep %r: %s" % (RANG_BUOC, tt, dinh_nghia)
            )

    co_cot = list(connection.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'items' AND column_name = 'notes'
    """)))
    if not co_cot:
        raise RuntimeError("items van thieu cot notes tren PostgreSQL")
