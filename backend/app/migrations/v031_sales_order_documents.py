"""Tep dinh kem cua don van chuyen (hop dong, bao gia da ky).

Tab "Tai lieu dinh kem" cua don van chuyen tung co mot o chon tep, va khi chon
xong no bao "Da chon hop dong/bao gia dinh kem: <ten tep>". Nhung
`so-contract-file` khong xuat hien trong bat ky tep JS nao — khong upload,
khong FormData, khong gan vao don. Tep bi bo ngay tai do, con nguoi dung thi
tuong da dinh kem xong. Backend cung chua co cho nao de chua.

Bang nay lam theo dung mau cua `delivery_pod_documents`, ke ca cac rang buoc:

  · `file_size` bi chan o TANG CO SO DU LIEU (CheckConstraint), khong chi o
    tang ung dung. Mot duong ghi khac quen kiem se bi chan tai day.
  · `checksum` duy nhat trong pham vi mot don: tai lai cung mot tep khong tao
    ra ban ghi thu hai.
  · `ON DELETE CASCADE`: xoa don thi tep di theo, khong de lai dong mo coi.

Gioi han 25 MB — dung con so ma chinh giao dien da hua voi nguoi dung ("PDF,
DOCX, PNG, JPG - Toi da 25MB").
"""

VERSION = "031_sales_order_documents"

from sqlalchemy import text

#: 25 MB, dung con so giao dien da hua.
MAX_BYTES = 25 * 1024 * 1024

DDL_POSTGRES = """
CREATE TABLE IF NOT EXISTS sales_order_documents (
    id VARCHAR(128) PRIMARY KEY,
    so_id VARCHAR NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    document_type VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_size INTEGER NOT NULL,
    checksum VARCHAR(128) NOT NULL,
    content BYTEA NOT NULL,
    note VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT ck_sales_order_document_size CHECK (file_size >= 0 AND file_size <= %d),
    CONSTRAINT uq_sales_order_document_checksum UNIQUE (so_id, checksum)
)
""" % MAX_BYTES

DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS sales_order_documents (
    id VARCHAR(128) PRIMARY KEY,
    so_id VARCHAR NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    document_type VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_size INTEGER NOT NULL,
    checksum VARCHAR(128) NOT NULL,
    content BLOB NOT NULL,
    note VARCHAR(500),
    created_at TIMESTAMP NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    CONSTRAINT ck_sales_order_document_size CHECK (file_size >= 0 AND file_size <= %d),
    CONSTRAINT uq_sales_order_document_checksum UNIQUE (so_id, checksum)
)
""" % MAX_BYTES

INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_sales_order_documents_so_id"
    " ON sales_order_documents (so_id)"
)


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return ["DROP TABLE IF EXISTS sales_order_documents"]
    return [DDL_POSTGRES.strip(), INDEX_SQL]


def upgrade_sqlite(connection):
    # Bang `sales_orders` phai co truoc, vi cot `so_id` tro vao no.
    co_bang = list(connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sales_orders'"
    ))
    if not co_bang:
        return
    connection.execute(DDL_SQLITE.strip())
    connection.execute(INDEX_SQL)
    validate_sqlite(connection)


def rollback_sqlite(connection):
    connection.execute("DROP TABLE IF EXISTS sales_order_documents")


def _sqlite_columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def validate_sqlite(connection):
    cot = _sqlite_columns(connection, "sales_order_documents")
    # Bang chua dung thi khong co gi de kiem — dung bat loi luc khoi tao.
    if not cot:
        return
    can = {"id", "so_id", "document_type", "file_name", "mime_type",
           "file_size", "checksum", "content", "created_at", "created_by"}
    if not can <= cot:
        raise RuntimeError("sales_order_documents columns missing: %s" % sorted(can - cot))


def validate_postgresql(connection):
    ton_tai = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'sales_orders'
    """)))
    if not ton_tai:
        return
    cot = {
        row[0] for row in connection.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'sales_order_documents'
        """))
    }
    if not cot:
        raise RuntimeError("sales_order_documents table missing")
    can = {"id", "so_id", "document_type", "file_name", "mime_type",
           "file_size", "checksum", "content", "created_at", "created_by"}
    if not can <= cot:
        raise RuntimeError("sales_order_documents columns missing: %s" % sorted(can - cot))
