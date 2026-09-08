"""Trang thai `arrived` cua lenh giao hang phai duoc CO SO DU LIEU cho phep.

LOI DA XAY RA THAT. Nap du lieu mau vao PostgreSQL that thi bao:

    CheckViolation: new row for relation "delivery_orders" violates check
    constraint "ck_delivery_orders_canonical_status"
    DETAIL: Failing row contains (DEMO-DO-2026-004, arrived, ...)

Vi sao chi lo ra tren PostgreSQL:

  · `models.py` khai `canonical_status IN ('pending','in_transit','arrived',
    'delivered','cancelled')`. SQLite trong may kiem duoc DUNG LAI tu mo hinh
    (`Base.metadata.create_all`), nen no co ngay rang buoc moi.
  · PostgreSQL that thi nang cap TUNG BUOC. Rang buoc do sinh o moc
    `013_demo_stabilization` voi BON trang thai, va khi `arrived` duoc them vao
    mo hinh thi KHONG CO moc nao sua rang buoc theo. Schema troi khoi mo hinh
    mot cach im lang.

Hau qua: moi duong ghi `arrived` deu vo tren co so du lieu that — ke ca duong
that ma nguoi dieu phoi bam ("ghi xe da den noi"), khong chi bo nap du lieu mau.
Va vi tang ung dung cho phep, loi chi lo ra o dong ghi cuoi cung, duoi dang mot
loi rang buoc kho doc.

Moc nay dua rang buoc ve dung bang mo hinh. `arrived` la mot moc THAT trong
luong: xe da den noi nhung CHUA ky POD — va dung o moc do thi tien chua duoc
chot, nen no khong the gop vao `in_transit` hay `delivered`.

LUI LAI: quay ve bon trang thai, nhung phai doi cac dong dang o `arrived` sang
`in_transit` truoc, khong thi rang buoc cu khong dat duoc. `in_transit` la lua
chon an toan hon `delivered`: no noi "chua xong", con `delivered` thi noi "xong
roi" — dat sai sang `delivered` la mo cho chot tien cho mot chuyen chua ky POD.
"""

VERSION = "032_delivery_order_arrived_status"

from sqlalchemy import text


#: Nam trang thai, dung bang `models.py`. Doi o day thi phai doi ca o do.
TRANG_THAI = ("pending", "in_transit", "arrived", "delivered", "cancelled")
TRANG_THAI_CU = ("pending", "in_transit", "delivered", "cancelled")

RANG_BUOC = "ck_delivery_orders_canonical_status"


def _lieu_ke(ds):
    return ", ".join("'%s'" % x for x in ds)


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            # Doi cac dong dang o `arrived` truoc, khong thi rang buoc cu khong
            # dat duoc va lenh ADD CONSTRAINT se vo.
            "UPDATE delivery_orders SET canonical_status = 'in_transit'"
            " WHERE canonical_status = 'arrived'",
            "ALTER TABLE delivery_orders DROP CONSTRAINT IF EXISTS %s" % RANG_BUOC,
            "ALTER TABLE delivery_orders ADD CONSTRAINT %s"
            " CHECK (canonical_status IN (%s))" % (RANG_BUOC, _lieu_ke(TRANG_THAI_CU)),
        ]
    return [
        "ALTER TABLE delivery_orders DROP CONSTRAINT IF EXISTS %s" % RANG_BUOC,
        "ALTER TABLE delivery_orders ADD CONSTRAINT %s"
        " CHECK (canonical_status IN (%s))" % (RANG_BUOC, _lieu_ke(TRANG_THAI)),
    ]


def _bang_ton_tai(connection):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='delivery_orders'"
    )))


def _dat_lai_trigger(connection, ds_trang_thai):
    """Dung lai hai TRIGGER kiem `canonical_status` cua SQLite.

    SQLite khong sua duoc CHECK bang ALTER TABLE, nen moc `013_demo_stabilization`
    thay CHECK bang hai TRIGGER `RAISE(ABORT,...)`. Chung khai BON trang thai —
    dung y luc do, nhung `arrived` sinh sau, va khong moc nao dung lai chung.

    Nen tren mot SQLite dung tu chuoi moc (khong phai tu `models.py`), moi dong
    ghi `arrived` bi TRIGGER chan — CUNG mot lo hong nhu tren PostgreSQL, chi
    khac hinh dang. Ham nay bit not cai con lai.
    """
    cho_phep = ",".join("'%s'" % x for x in ds_trang_thai)
    for phep in ("insert", "update"):
        connection.execute(
            "DROP TRIGGER IF EXISTS ck_delivery_orders_canonical_%s" % phep)
    connection.execute(
        "CREATE TRIGGER ck_delivery_orders_canonical_insert"
        " BEFORE INSERT ON delivery_orders"
        " WHEN NEW.canonical_status NOT IN (%s)"
        " BEGIN SELECT RAISE(ABORT,'invalid delivery order canonical_status'); END"
        % cho_phep
    )
    connection.execute(
        "CREATE TRIGGER ck_delivery_orders_canonical_update"
        " BEFORE UPDATE OF canonical_status ON delivery_orders"
        " WHEN NEW.canonical_status NOT IN (%s)"
        " BEGIN SELECT RAISE(ABORT,'invalid delivery order canonical_status'); END"
        % cho_phep
    )


def upgrade_sqlite(connection):
    """Mo `arrived` tren SQLite bang cach dung lai hai TRIGGER cua moc 013.

    Con CHECK trong cau CREATE TABLE thi khong sua: doi no phai dung lai ca bang
    roi chep du lieu sang, va o day khong can — SQLite dung tu `models.py`
    (bai kiem, ban chay tam) von da khai du nam trang thai, con SQLite dung tu
    chuoi moc thi khong co CHECK do, chi co TRIGGER.
    """
    if not _bang_ton_tai(connection):
        return
    _dat_lai_trigger(connection, TRANG_THAI)
    validate_sqlite(connection)


def rollback_sqlite(connection):
    if not _bang_ton_tai(connection):
        return
    # Doi du lieu TRUOC khi that lai trigger, cung ly do nhu ben PostgreSQL:
    # thu tu nguoc lai thi mot dong `arrived` con sot se vo o lan ghi ke tiep.
    connection.execute(
        "UPDATE delivery_orders SET canonical_status = 'in_transit'"
        " WHERE canonical_status = 'arrived'"
    )
    _dat_lai_trigger(connection, TRANG_THAI_CU)


def validate_sqlite(connection):
    co_bang = list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='delivery_orders'"
    ))
    if not co_bang:
        return
    sql = list(connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='delivery_orders'"
    ))
    ma = (sql[0][0] or "") if sql else ""
    # Bang co the khong khai CHECK nao (ban dung tu mo hinh cu). Chi bao loi khi
    # CO khai ma lai THIEU `arrived` — do moi la cho se chan dong ghi.
    if "canonical_status" in ma and "CHECK" in ma.upper() and "arrived" not in ma:
        raise RuntimeError(
            "delivery_orders con rang buoc CHECK khong cho phep 'arrived'"
        )
    # Va kiem ca hai TRIGGER — day moi la cho that su chan dong ghi tren mot
    # SQLite dung tu chuoi moc.
    for ten, sql in connection.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='trigger'"
        " AND name LIKE 'ck_delivery_orders_canonical_%'"
    ):
        if "arrived" not in (sql or ""):
            raise RuntimeError("trigger %s khong cho phep 'arrived'" % ten)


def validate_postgresql(connection):
    # Thoat som khi bang chua co — cung khuon voi cac moc khac trong du an.
    #
    # Hai bai kiem chay moc nay qua mot co may Postgres GIA LAP: no chi ghi lai
    # cau SQL, khong tra ve du lieu. Truy van `information_schema.tables` o day
    # tra ve rong trong moi truong do, nen phep kiem nhuong duong — con tren co
    # so du lieu that thi bang co that va phep kiem chay day du.
    ton_tai = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'delivery_orders'
    """)))
    if not ton_tai:
        return

    dong = list(connection.execute(text("""
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = 'delivery_orders'::regclass
          AND contype = 'c'
          AND conname = :ten
    """), {"ten": RANG_BUOC}))
    if not dong:
        raise RuntimeError("thieu rang buoc %s" % RANG_BUOC)
    dinh_nghia = dong[0][0] or ""
    for tt in TRANG_THAI:
        if "'%s'" % tt not in dinh_nghia:
            raise RuntimeError(
                "rang buoc %s chua cho phep %r: %s" % (RANG_BUOC, tt, dinh_nghia)
            )
