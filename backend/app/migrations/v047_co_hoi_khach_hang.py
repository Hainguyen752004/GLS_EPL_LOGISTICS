"""Bang `crm_opportunities` — CO HOI KHACH HANG (CRM-01) dung TRUOC bao gia.

VI SAO. Tai lieu pham vi (`EPL_Logistics_Functional_Scope_EN.docx`) mo dau chuoi
van hanh bang "Lead / Customer -> Quotation -> ..." va tach hai chuc nang:

    CRM-01 Lead / Opportunity : ghi nhan yeu cau cua khach, hoi gia le, san luong
                                tiem nang — TRUOC khi co bao gia.
    CRM-02 Customer Profile   : ho so khach, lich su giao dich, SLA.

He chua co bang nao cho CRM-01. Khoi "Kanban co hoi" cu ve tu bang don hang
(SO) — buoc da bo — nen no dem bao gia va goi la "hop dong da chot". Chu du an
xac nhan lam CRM-01 that: mot MAN RIENG, BANG RIENG, dung truoc Bao gia; tu co
hoi bam "Lap bao gia" thi sinh mot bao gia NHAP ke thua khach, tuyen, hang, san
luong — roi bao gia di tiep dung luong QT -> DO -> Trip.

`stage` la MA CHUAN (khong phai nhan chu), chu hien lay tu giao dien:
    new | contacted | negotiating | quoted | won | lost
`quoted` duoc dat khi lap bao gia (mang `quotation_id`); `won` do he dat khi
bao gia do duoc khach chap nhan (xem `bao_gia_service.chap_nhan_va_sinh_do`);
`lost` phai co `lost_reason`.

Khach co the CHUA co trong `customers` (moi hoi gia lan dau): luu `prospect_name`
va lien he; luc lap bao gia moi tao ban ghi khach.
"""

VERSION = "047_co_hoi_khach_hang"

from sqlalchemy import text

BANG = "crm_opportunities"

TAO = """
CREATE TABLE IF NOT EXISTS crm_opportunities (
    id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR REFERENCES customers(id),
    prospect_name VARCHAR(255),
    contact_name VARCHAR(255),
    contact_phone VARCHAR(64),
    contact_email VARCHAR(255),
    source VARCHAR(32) NOT NULL DEFAULT 'other',
    route_id VARCHAR REFERENCES routes(id),
    origin_text VARCHAR(255),
    destination_text VARCHAR(255),
    cargo_type VARCHAR(255),
    est_weight_kg DOUBLE PRECISION NOT NULL DEFAULT 0,
    est_trips_per_month INTEGER NOT NULL DEFAULT 0,
    expected_start VARCHAR(32),
    expected_price NUMERIC(24, 6),
    stage VARCHAR(20) NOT NULL DEFAULT 'new',
    owner VARCHAR(128),
    notes TEXT,
    lost_reason TEXT,
    quotation_id VARCHAR REFERENCES quotations(id),
    next_action_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(128) NOT NULL DEFAULT 'system',
    updated_by VARCHAR(128) NOT NULL DEFAULT 'system',
    version INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT ck_crm_opportunity_stage CHECK
        (stage IN ('new','contacted','negotiating','quoted','won','lost')),
    CONSTRAINT ck_crm_opportunity_version CHECK (version > 0)
)
"""

CHI_MUC = (
    "CREATE INDEX IF NOT EXISTS ix_crm_opportunity_stage ON crm_opportunities (stage)",
    "CREATE INDEX IF NOT EXISTS ix_crm_opportunity_customer ON crm_opportunities (customer_id)",
    "CREATE INDEX IF NOT EXISTS ix_crm_opportunity_quotation ON crm_opportunities (quotation_id)",
)


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return ["DROP TABLE IF EXISTS crm_opportunities"]
    return [TAO] + list(CHI_MUC)


# --------------------------------------------------------------------- SQLite --
# Giu cho du hinh voi cac moc khac; du an da ngung SQLite hoan toan.

def upgrade_sqlite(connection):
    # `connection` la sqlite3.Connection tho (xem runner.upgrade), khong phai
    # SQLAlchemy — nen dung SQL chu khong dung Table.create().
    sql = (TAO.replace("TIMESTAMPTZ", "TIMESTAMP").replace("NOW()", "CURRENT_TIMESTAMP")
           .replace("DOUBLE PRECISION", "REAL"))
    connection.execute(sql)
    for cm in CHI_MUC:
        connection.execute(cm)


def rollback_sqlite(connection):
    connection.execute("DROP TABLE IF EXISTS %s" % BANG)


def validate_sqlite(connection):
    return


# ----------------------------------------------------------------- PostgreSQL --

def validate_postgresql(connection):
    # Bo kiem `test_migration_v001` dua vao mot engine GIA chi ghi lai SQL va tra
    # rong cho moi truy van — nen truoc khi ket luan "thieu bang", xac nhan day
    # la co so du lieu that bang bang `schema_migrations` (runner vua tao no).
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"))):
        return
    # Khong loc theo schema: bo kiem chay tren schema rieng moi phien (cung cach v011).
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :b"), {"b": BANG})):
        raise RuntimeError("thieu bang %s" % BANG)
