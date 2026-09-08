"""Bao gia cuoc theo luong moi: QT -> DO, bo han buoc SO.

VI SAO MOC NAY LON. Chu du an doi luong nghiep vu: *"lan nay se khong co du SO
nao o day nua... tu gio chung ta se di tu QT sang cai DO luon"*. Bao gia tro
thanh CHUNG TU THUONG MAI DAU VAO DUY NHAT cua van hanh — no khoa gia cuoc cho
tung chuyen, va DO ke thua chu khong nhap lai. Bang `quotations` hien tai duoc
dung cho mot man bao gia don gian hon nhieu, nen thieu gan het nhung gi luong
moi can.

BON NHOM THAY DOI:

1. DON VI TINH CUOC. Chot voi chu du an sau khi ban lai bai toan mo da: bao gia
   theo don vi cua KHACH (chuyen / tan / m3 / kg), nhung DO luon khoa mot con so
   `d/chuyen`. Ly do khong phai cho gon: neu co so du lieu luu d/kg thi moi con
   so phia sau phu thuoc trong luong CAN THUC TE, ma can thuc te luon khac can
   khai — nghia la gia khach da dong y se tu doi sau khi xe chay. Nen:
     · `price_basis` + `unit_price` = bao gia the nao (de in PDF va doi soat),
     · `min_qty_per_trip` = muc toi thieu tinh tien moi chuyen, thu chan mo da
       xuc thieu tai lam mot chuyen lai thanh lo,
     · `selling_price` (da co) = con so d/chuyen ma DO se khoa.

2. MOT SO NGUOI DUNG PHAI KHAI MA BANG CHUA CO CHO CHUA. `quote_no` (ma cap luc
   GUI, khac khoa chinh — spec doi "nhap chua co ma" ma khoa chinh thi khong the
   rong), loai xe da chon, tien te va TY GIA LUC GUI, dieu khoan thanh toan,
   nguoi ban, so chuyen/thang, phu phi cho, gia tri hang, quy cach xep chong va
   niem phong, nguoi nhan tai diem giao, va BA o ghi chu tach roi (gui khach —
   in tren PDF; cho van hanh — hien tren lenh tai xe; noi bo — khong in). Ba o
   ghi chu do truoc day dung MOT cot `notes`, nen ghi chu noi bo in ra cho khach.

3. BA BANG MOI. `quotation_items` (moi dong mot loai hang: ten, so luong, DVT,
   ghi chu — KHONG co don gia va thanh tien, vi minh la don vi van chuyen, chi
   tinh cuoc chu khong tinh tien hang), `quotation_attachments` (chung tu di
   theo DO xuong van hanh va ke toan), `quotation_versions` (moi lan sua gia sau
   khi da gui thi tang phien ban — de con doi soat duoc voi ban khach da nhan).

4. HAI CHO O BANG KHAC, de giao dien khong phai tu tinh:
     · `routes.bot_fee` — BOT thuoc DUONG, khong thuoc xe. Truoc day phi cau
       duong chi co trong cong thuc theo loai xe, nen hai tuyen dai ngan khac
       nhau cung mot muc BOT.
     · `vehicle_types.dep_cost_per_km` — khau hao va bao duong tren 1 km. Day la
       cau phan giá thành duy nhat trong spec ma he thong chua co, va thieu no
       thi bien loi nhuan cao gia tao.
     · `delivery_orders`: `quotation_id`, `unit_price` (gia KHOA), `price_basis`,
       `billed_qty`, `driver_note`. Khong co `quotation_id` thi duong chot gia o
       `delivery_completion_service` — von lan theo DO -> SO -> bao gia — tra ve
       BASE_PRICE_MISSING trong luong moi, tuc hoan tat giao hang vo hoan toan.
     · `delivery_pod_records.actual_qty` — SO CAN THUC TE luc ky POD. Cuoc theo
       tan khong xuat duoc hoa don dung neu khong co cho ghi so can; truoc day
       ca he thong khong co mot cot nao chua no.

Moi cot moi de RONG duoc, va cac bang moi khong bat buoc co dong — bo du lieu
dang chay khong co gi phai nap lai.
"""

VERSION = "038_bao_gia_theo_spec_moi"

from sqlalchemy import text


#: Cot them vao bang da co: (bang, cot, kieu PostgreSQL, kieu SQLite)
COT_THEM = [
    # --- quotations: don vi tinh cuoc ---
    ("quotations", "price_basis", "VARCHAR", "TEXT"),
    ("quotations", "unit_price", "DOUBLE PRECISION", "REAL"),
    ("quotations", "min_qty_per_trip", "DOUBLE PRECISION", "REAL"),
    # --- quotations: cac o nguoi dung phai khai ---
    ("quotations", "quote_no", "VARCHAR", "TEXT"),
    ("quotations", "vehicle_type_id", "VARCHAR", "TEXT"),
    ("quotations", "currency_code", "VARCHAR", "TEXT"),
    ("quotations", "fx_rate", "DOUBLE PRECISION", "REAL"),
    ("quotations", "payment_terms", "VARCHAR", "TEXT"),
    ("quotations", "sales_rep", "VARCHAR", "TEXT"),
    ("quotations", "trips_per_month", "INTEGER", "INTEGER"),
    ("quotations", "waiting_surcharge", "DOUBLE PRECISION", "REAL"),
    ("quotations", "cargo_value", "DOUBLE PRECISION", "REAL"),
    ("quotations", "stacking", "VARCHAR", "TEXT"),
    ("quotations", "sealing", "VARCHAR", "TEXT"),
    ("quotations", "recipient_contact", "VARCHAR", "TEXT"),
    ("quotations", "notes_customer", "TEXT", "TEXT"),
    ("quotations", "notes_ops", "TEXT", "TEXT"),
    ("quotations", "notes_internal", "TEXT", "TEXT"),
    ("quotations", "bot_fee", "DOUBLE PRECISION", "REAL"),
    ("quotations", "cost_breakdown_json", "TEXT", "TEXT"),
    ("quotations", "target_margin", "DOUBLE PRECISION", "REAL"),
    ("quotations", "sent_at", "TIMESTAMP", "TIMESTAMP"),
    ("quotations", "accepted_at", "TIMESTAMP", "TIMESTAMP"),
    ("quotations", "closed_at", "TIMESTAMP", "TIMESTAMP"),
    ("quotations", "close_reason", "TEXT", "TEXT"),
    # --- nguon giá thành ---
    ("routes", "bot_fee", "DOUBLE PRECISION", "REAL"),
    ("vehicle_types", "dep_cost_per_km", "DOUBLE PRECISION", "REAL"),
    # --- delivery_orders: ke thua tu bao gia ---
    ("delivery_orders", "quotation_id", "VARCHAR", "TEXT"),
    ("delivery_orders", "unit_price", "DOUBLE PRECISION", "REAL"),
    ("delivery_orders", "price_basis", "VARCHAR", "TEXT"),
    ("delivery_orders", "billed_qty", "DOUBLE PRECISION", "REAL"),
    ("delivery_orders", "driver_note", "TEXT", "TEXT"),
    # --- POD: so can thuc te ---
    ("delivery_pod_records", "actual_qty", "DOUBLE PRECISION", "REAL"),
    ("delivery_pod_records", "actual_qty_uom", "VARCHAR", "TEXT"),
]

#: Chi muc: hai duong loc chinh cua man danh sach bao gia, va duong lan tu DO ve
#: bao gia ma buoc chot gia dung.
CHI_MUC = [
    ("ix_quotations_quote_no", "quotations", "quote_no"),
    ("ix_delivery_orders_quotation_id", "delivery_orders", "quotation_id"),
]

BANG_MOI_PG = [
    """
    CREATE TABLE IF NOT EXISTS quotation_items (
        id VARCHAR PRIMARY KEY,
        quotation_id VARCHAR NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
        line_no INTEGER NOT NULL DEFAULT 1,
        name VARCHAR,
        quantity DOUBLE PRECISION NOT NULL DEFAULT 0,
        uom VARCHAR NOT NULL DEFAULT 'Chuyến',
        note VARCHAR,
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        CONSTRAINT ck_quotation_items_qty CHECK (quantity >= 0)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_quotation_items_quotation ON quotation_items (quotation_id)",
    """
    CREATE TABLE IF NOT EXISTS quotation_attachments (
        id VARCHAR PRIMARY KEY,
        quotation_id VARCHAR NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
        doc_type VARCHAR NOT NULL DEFAULT 'Khác',
        file_name VARCHAR NOT NULL,
        storage_url TEXT NOT NULL,
        mime_type VARCHAR,
        size_bytes BIGINT,
        note VARCHAR,
        uploaded_at TIMESTAMP NOT NULL DEFAULT now(),
        uploaded_by VARCHAR NOT NULL DEFAULT 'system'
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_quotation_attachments_quotation ON quotation_attachments (quotation_id)",
    """
    CREATE TABLE IF NOT EXISTS quotation_versions (
        id VARCHAR PRIMARY KEY,
        quotation_id VARCHAR NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        selling_price DOUBLE PRECISION,
        unit_price DOUBLE PRECISION,
        price_basis VARCHAR,
        total_cost DOUBLE PRECISION,
        currency_code VARCHAR,
        fx_rate DOUBLE PRECISION,
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT now(),
        created_by VARCHAR NOT NULL DEFAULT 'system',
        CONSTRAINT uq_quotation_versions UNIQUE (quotation_id, version)
    )
    """,
]

BANG_MOI_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS quotation_items (
        id TEXT PRIMARY KEY,
        quotation_id TEXT NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
        line_no INTEGER NOT NULL DEFAULT 1,
        name TEXT,
        quantity REAL NOT NULL DEFAULT 0,
        uom TEXT NOT NULL DEFAULT 'Chuyến',
        note TEXT,
        created_at TIMESTAMP,
        CHECK (quantity >= 0)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_quotation_items_quotation ON quotation_items (quotation_id)",
    """
    CREATE TABLE IF NOT EXISTS quotation_attachments (
        id TEXT PRIMARY KEY,
        quotation_id TEXT NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
        doc_type TEXT NOT NULL DEFAULT 'Khác',
        file_name TEXT NOT NULL,
        storage_url TEXT NOT NULL,
        mime_type TEXT,
        size_bytes INTEGER,
        note TEXT,
        uploaded_at TIMESTAMP,
        uploaded_by TEXT NOT NULL DEFAULT 'system'
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_quotation_attachments_quotation ON quotation_attachments (quotation_id)",
    """
    CREATE TABLE IF NOT EXISTS quotation_versions (
        id TEXT PRIMARY KEY,
        quotation_id TEXT NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        selling_price REAL,
        unit_price REAL,
        price_basis TEXT,
        total_cost REAL,
        currency_code TEXT,
        fx_rate REAL,
        note TEXT,
        created_at TIMESTAMP,
        created_by TEXT NOT NULL DEFAULT 'system',
        UNIQUE (quotation_id, version)
    )
    """,
]


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        cau = ["DROP TABLE IF EXISTS %s" % b
               for b in ("quotation_versions", "quotation_attachments", "quotation_items")]
        cau += ["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (b, c)
                for b, c, _, _ in COT_THEM]
        return cau
    cau = list(BANG_MOI_PG)
    cau += ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s %s" % (b, c, kieu)
            for b, c, kieu, _ in COT_THEM]
    cau += ["CREATE INDEX IF NOT EXISTS %s ON %s (%s)" % (t, b, c) for t, b, c in CHI_MUC]
    return cau


def _bang_ton_tai(connection, ten):
    return bool(list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % ten)))


def _sql_bang(connection, ten):
    dong = list(connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='%s'" % ten))
    return (dong[0][0] or "") if dong else ""


def upgrade_sqlite(connection):
    for cau in BANG_MOI_SQLITE:
        connection.execute(cau)
    # `ADD COLUMN IF NOT EXISTS` khong co trong SQLite nen phai tu kiem tung cot.
    for bang, cot, _, kieu in COT_THEM:
        if not _bang_ton_tai(connection, bang):
            continue
        if cot not in _sql_bang(connection, bang):
            connection.execute("ALTER TABLE %s ADD COLUMN %s %s" % (bang, cot, kieu))
    for ten, bang, cot in CHI_MUC:
        if _bang_ton_tai(connection, bang):
            connection.execute("CREATE INDEX IF NOT EXISTS %s ON %s (%s)" % (ten, bang, cot))
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """Bo ba bang moi; de nguyen cac cot da them.

    Bo mot cot trong SQLite ban cu phai dung lai ca bang roi chep du lieu sang.
    Bang `quotations` va `delivery_orders` co rat nhieu bang tro khoa ngoai vao,
    nen dung lai chung rui ro hon nhieu so voi cai duoc tu viec don may cot du.
    """
    for ten in ("quotation_versions", "quotation_attachments", "quotation_items"):
        connection.execute("DROP TABLE IF EXISTS %s" % ten)


def validate_sqlite(connection):
    for ten in ("quotation_items", "quotation_attachments", "quotation_versions"):
        if not _bang_ton_tai(connection, ten):
            raise RuntimeError("thieu bang %s" % ten)
    thieu = []
    for bang, cot, _, _ in COT_THEM:
        if not _bang_ton_tai(connection, bang):
            continue
        if cot not in _sql_bang(connection, bang):
            thieu.append("%s.%s" % (bang, cot))
    if thieu:
        raise RuntimeError("thieu cot " + ", ".join(thieu))


def validate_postgresql(connection):
    co_bang = {r[0] for r in connection.execute(text("""
        SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'
    """))}
    # THOAT SOM khi khong doc duoc schema.
    #
    # Hai bai kiem chay ca chuoi moc qua mot co may PostgreSQL GIA LAP: no ghi
    # lai cau SQL de doi chieu nhung khong tra ve du lieu nao. Voi no thi moi
    # truy van `information_schema` deu rong, va mot phep kiem "thieu bang" se
    # nem loi cho MOI moc — bao la schema sai trong khi that ra chua co ai doc
    # duoc schema. Cac moc khac trong du an deu thoat som o dung cho nay.
    if not co_bang:
        return
    for ten in ("quotation_items", "quotation_attachments", "quotation_versions"):
        if ten not in co_bang:
            raise RuntimeError("thieu bang %s" % ten)
    co_cot = set()
    for r in connection.execute(text("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_schema = 'public'
    """)):
        co_cot.add((r[0], r[1]))
    thieu = ["%s.%s" % (b, c) for b, c, _, _ in COT_THEM
             if b in co_bang and (b, c) not in co_cot]
    if thieu:
        raise RuntimeError("thieu cot " + ", ".join(thieu))
