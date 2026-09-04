"""Quy cách và điều kiện vận chuyển, kế thừa từ báo giá cước sang đơn hàng.

Tab "Quy cách vận chuyển & Yêu cầu kỹ thuật" của đơn hàng vận chuyển có sáu ô
nhập — đơn vị vận chuyển, phương thức giao, trọng tải niêm phong, yêu cầu nhiệt
độ, bảo hiểm hàng hóa, người phụ trách kho — nhưng **không có cột nào để chứa**.
`saveOracleSO` cũng không gửi chúng lên. Và bản thân các ô nhập còn bị bản dịch
xóa mất (`data-i18n` nằm trên thẻ `<label>` bọc `<input>`, và mã dịch gán
`innerHTML`), nên người dùng không bao giờ điền được.

Ba tầng cùng hỏng một chỗ. Bảng này lo tầng lưu trữ.

Đặt cả trên `quotations` lẫn `sales_orders`: đây là điều kiện chào cho khách ở
bước báo giá, và phải đi theo sang đơn hàng khi chốt — không phải khai lại.
"""

VERSION = "028_shipping_spec"

from sqlalchemy import text

COLUMNS = (
    "carrier_name",
    "delivery_method",
    "seal_weight",
    "temperature_requirement",
    "cargo_insurance",
    "warehouse_owner",
)

TABLES = ("quotations", "sales_orders")


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}"
            for table in TABLES
            for column in reversed(COLUMNS)
        ]
    return [
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} VARCHAR"
        for table in TABLES
        for column in COLUMNS
    ]


def _sqlite_columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def upgrade_sqlite(connection):
    for table in TABLES:
        columns = _sqlite_columns(connection, table)
        if not columns:
            continue
        for column in COLUMNS:
            if column not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    for table in TABLES:
        columns = _sqlite_columns(connection, table)
        if not columns:
            continue
        for column in reversed(COLUMNS):
            if column in columns:
                connection.execute(f"ALTER TABLE {table} DROP COLUMN {column}")


def validate_sqlite(connection):
    for table in TABLES:
        columns = _sqlite_columns(connection, table)
        # Bảng chưa dựng thì không có gì để kiểm — đừng bắt lỗi lúc khởi tạo.
        if not columns:
            continue
        if not set(COLUMNS) <= columns:
            raise RuntimeError(f"shipping spec columns missing on {table}")


def validate_postgresql(connection):
    for table in TABLES:
        exists = list(connection.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :table
        """), {"table": table}))
        if not exists:
            continue
        # Hỏi đúng những cột cần kiểm để truy vấn tự nhận diện được, không lẫn
        # với truy vấn cột của migration khác trên cùng bảng.
        columns = {
            row[0] for row in connection.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table
                  AND column_name IN ('carrier_name', 'delivery_method', 'seal_weight',
                                      'temperature_requirement', 'cargo_insurance', 'warehouse_owner')
            """), {"table": table})
        }
        if not set(COLUMNS) <= columns:
            raise RuntimeError(f"shipping spec columns missing on {table}")
