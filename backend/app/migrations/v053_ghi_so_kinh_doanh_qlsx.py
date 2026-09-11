"""Bang `sales_order_pushes` — ket qua GHI SO KINH DOANH mot DO da giao sang QLSX.

VI SAO. Chu du an va anh Khang (ben cong no) chot ngay 11/09/2026: sau khi DO hoan
tat, tren ho so co them nut "Ghi so kinh doanh" goi
`POST /api/v1/integrations/logistics/sales-orders` cua QLSX de tao don hang ban
va ghi cong no. Hop dong QLSX doi Idempotency-Key ON DINH theo DO, va noi ro:
timeout khong chung minh that bai — phai gui lai CUNG key va CUNG body. Nen ben
nay phai LUU body da gui va key da dung; khong luu la lan gui lai tao key moi va
an 409 vi cung DO khac key.

MOT DONG MOT DO: khoa `doId` ben QLSX la duy nhat trong bang tich hop, khong co
API update/delete. Bang nay phan anh dung dieu do — `do_id` la khoa chinh.
"""

VERSION = "053_ghi_so_kinh_doanh_qlsx"

from sqlalchemy import text

TAO_BANG = """
CREATE TABLE IF NOT EXISTS sales_order_pushes (
    do_id VARCHAR PRIMARY KEY REFERENCES delivery_orders(id),
    idempotency_key VARCHAR(100) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'failed',
    http_status INTEGER,
    request_body TEXT NOT NULL,
    response_body TEXT,
    replayed BOOLEAN DEFAULT FALSE,
    order_id INTEGER,
    order_code VARCHAR(64),
    order_status VARCHAR(16),
    retk_auto_id INTEGER,
    retk_code VARCHAR(64),
    item_code VARCHAR(128),
    currency VARCHAR(3),
    total_amount NUMERIC(24, 6),
    initial_debt_amount NUMERIC(24, 6),
    error_code VARCHAR(64),
    error_message TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    pushed_by VARCHAR(255),
    first_attempt_at TIMESTAMPTZ,
    last_attempt_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ
)
"""


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return ["DROP TABLE IF EXISTS sales_order_pushes"]
    return [TAO_BANG,
            "CREATE INDEX IF NOT EXISTS ix_sales_order_pushes_status ON sales_order_pushes(status)"]


def upgrade_sqlite(connection):
    # Du an chi con PostgreSQL; giu ham cho runner khong vo.
    return


def rollback_sqlite(connection):
    return


def validate_sqlite(connection):
    return


def validate_postgresql(connection):
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"))):
        return
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_order_pushes'"))):
        raise RuntimeError("thieu bang sales_order_pushes")
