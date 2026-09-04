"""Dòng hàng hóa vận chuyển của đơn hàng vận chuyển.

Màn "Chi tiết đơn hàng" từ trước tới nay có một bảng dòng hàng đầy đủ — mã mục,
mô tả, số lượng, đơn vị tính, đơn giá cước, thành tiền — nhưng **không có bảng
nào để chứa nó**, và `saveOracleSO` cũng chỉ gửi lên đúng ba trường
`customer_id`, `route_id`, `total_amount`. Người dùng nhập xong, bấm Lưu, nhận
thông báo thành công, và không một dòng nào được ghi lại.

Bảng này làm cho màn hình đó nói thật. Quan trọng hơn: đơn vị tính của từng dòng
được quy đổi ra khối lượng và thể tích, vốn chính là hai con số mà
`vehicle_capacity_policy` dùng để chặn điều xe quá tải — nên dữ liệu người dùng
gõ vào cuối cùng cũng có tác dụng thật.
"""

VERSION = "026_sales_order_lines"

from sqlalchemy import text

TABLE = "sales_order_lines"


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [f"DROP TABLE IF EXISTS {TABLE}"]
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id VARCHAR PRIMARY KEY,
            so_id VARCHAR NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
            line_no INTEGER NOT NULL,
            description VARCHAR,
            quantity NUMERIC(24,6) NOT NULL DEFAULT 0,
            uom VARCHAR NOT NULL DEFAULT 'Tấn',
            unit_price NUMERIC(24,6) NOT NULL DEFAULT 0,
            amount NUMERIC(24,6) NOT NULL DEFAULT 0
        )
        """,
        # Mot don hang khong duoc co hai dong cung so thu tu.
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{TABLE}_so_line ON {TABLE} (so_id, line_no)",
        f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_so ON {TABLE} (so_id)",
    ]


def upgrade_sqlite(connection):
    # SQLite khong co NUMERIC(p,s) that su, nhung van chap nhan cu phap.
    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id VARCHAR PRIMARY KEY,
            so_id VARCHAR NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
            line_no INTEGER NOT NULL,
            description VARCHAR,
            quantity NUMERIC NOT NULL DEFAULT 0,
            uom VARCHAR NOT NULL DEFAULT 'Tấn',
            unit_price NUMERIC NOT NULL DEFAULT 0,
            amount NUMERIC NOT NULL DEFAULT 0
        )
    """)
    connection.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{TABLE}_so_line ON {TABLE} (so_id, line_no)")
    connection.execute(f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_so ON {TABLE} (so_id)")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    connection.execute(f"DROP TABLE IF EXISTS {TABLE}")


def _required():
    return {"id", "so_id", "line_no", "description", "quantity", "uom", "unit_price", "amount"}


def validate_sqlite(connection):
    rows = list(connection.execute(f'PRAGMA table_info("{TABLE}")'))
    # Bang chua dung thi khong co gi de kiem — dung bat loi nham luc khoi tao.
    if not rows:
        return
    columns = {row[1] for row in rows}
    if not _required() <= columns:
        raise RuntimeError("sales order line columns missing")


def validate_postgresql(connection):
    exists = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'sales_order_lines'
    """)))
    if not exists:
        return
    columns = {
        row[0] for row in connection.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'sales_order_lines'
        """))
    }
    if not _required() <= columns:
        raise RuntimeError("sales order line columns missing")
