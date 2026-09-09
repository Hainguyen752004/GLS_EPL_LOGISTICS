"""Bo rang buoc CHECK TRUNG tren `freight_charge_items.charge_type`.

LOI DA DO DUOC. Moc 041 noi `ck_freight_charge_type` de cho phep khoan muc
`yard` (Phi bai & luu kho). Nhung ghi `yard` van vo, va loi bi che thanh mot
thong bao khong lien quan: "Xung dot khi ghi nhan yeu cau"
(`IDEMPOTENCY_CONFLICT`) — vi `record_idempotent` bat `IntegrityError` roi doan
la trung khoa idempotency, trong khi that ra la mot rang buoc KHAC vo.

Doc `pg_constraint` ra thi tren PostgreSQL that co HAI rang buoc CHECK cho cung
mot cot:

    ck_freight_charge_type                    CHECK (charge_type = ANY (ARRAY[
                                              'fuel','toll','driver','yard',...]))
    freight_charge_items_charge_type_check    CHECK (charge_type = ANY (ARRAY[
                                              'fuel','toll','driver','waiting',...]))

Cai thu hai mang TEN TU SINH cua PostgreSQL — dau vet cua mot lan khai
`CheckConstraint` khong dat ten o mot moc cu. Moc 041 chi sua cai CO TEN, nen
cai kia van chan `yard`.

Hai rang buoc cho cung mot luat la ban than no da la loi: sua mot cai thi cai
kia am tham thang, va khong ai doc `models.py` ma biet duoc rang co cai thu hai.
`models.py` chi khai MOT `CheckConstraint` cho cot nay, va no da co ten
(`ck_freight_charge_type`) — nen cai ten tu sinh la thua han.

Moc nay BO cai trung. Luat van duoc cuong che bang `ck_freight_charge_type`,
tuc khong co khoang nao khong duoc bao ve.

LUI LAI: dung lai rang buoc trung theo danh sach CU (khong co `yard`), va phai
doi cac dong dang o `yard` sang `other` truoc — khong thi lenh ADD CONSTRAINT
vo. Nhung luu y: lui lai la lam vo lai duong ghi `yard`. Chi lui khi that su
phai ha phien ban.
"""

VERSION = "042_bo_rang_buoc_charge_type_trung"

from sqlalchemy import text

#: Ten tu sinh cua PostgreSQL cho `CheckConstraint` khong dat ten tren cot nay.
RB_TRUNG = "freight_charge_items_charge_type_check"

#: Rang buoc CO TEN, la cai duy nhat con lai sau moc nay. Danh sach phai giong
#: `models.FreightChargeItem` va giong moc 041.
RB_GIU = "ck_freight_charge_type"

KHOAN_MUC_CU = ("fuel", "toll", "driver", "waiting", "loading", "unloading",
                "carrier_base", "surcharge", "discount", "other")


def _lk(ds):
    return ", ".join("'%s'" % x for x in ds)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        # SQLite khong co rang buoc trung nay: no duoc dung lai tu `models.py`,
        # ma `models.py` chi khai MOT CheckConstraint co ten.
        return []
    if direction == "rollback":
        return [
            "UPDATE freight_charge_items SET charge_type = 'other' WHERE charge_type = 'yard'",
            "ALTER TABLE freight_charge_items ADD CONSTRAINT %s"
            " CHECK (charge_type IN (%s))" % (RB_TRUNG, _lk(KHOAN_MUC_CU)),
        ]
    return [
        "ALTER TABLE freight_charge_items DROP CONSTRAINT IF EXISTS %s" % RB_TRUNG,
    ]


def upgrade_sqlite(connection):
    return


def rollback_sqlite(connection):
    return


def validate_sqlite(connection):
    return


def validate_postgresql(connection):
    # Thoat som khi bang chua co — cung khuon voi cac moc khac trong du an.
    if not list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'freight_charge_items'
    """))):
        return

    # 1. Rang buoc trung phai KHONG con.
    if list(connection.execute(text("""
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'freight_charge_items'::regclass AND conname = :ten
    """), {"ten": RB_TRUNG})):
        raise RuntimeError("rang buoc trung %s van con" % RB_TRUNG)

    # 2. Va rang buoc CO TEN phai con, khong thi ta vua bo het moi bao ve.
    dong = list(connection.execute(text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conrelid = 'freight_charge_items'::regclass AND conname = :ten
    """), {"ten": RB_GIU}))
    if not dong:
        raise RuntimeError(
            "da bo %s ma %s cung khong co — cot charge_type gio khong duoc bao ve"
            % (RB_TRUNG, RB_GIU))
    if "'yard'" not in (dong[0][0] or ""):
        raise RuntimeError("%s chua cho phep 'yard'" % RB_GIU)

    # 3. Va khong con rang buoc CHECK nao khac noi ve `charge_type` — dem lai
    #    cho chac, vi dung van de moc nay di chua la "co mot cai thu hai ma
    #    khong ai biet".
    con_lai = [r[0] for r in connection.execute(text("""
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'freight_charge_items'::regclass AND contype = 'c'
          AND pg_get_constraintdef(oid) LIKE '%%charge_type%%'
    """))]
    khong_mong_doi = [x for x in con_lai
                      if x not in (RB_GIU, "freight_charge_items_check")]
    if khong_mong_doi:
        raise RuntimeError(
            "con rang buoc CHECK khac noi ve charge_type: %s — moi cai la mot cho "
            "co the chan mot khoan muc moi ma khong ai biet" % ", ".join(khong_mong_doi))
