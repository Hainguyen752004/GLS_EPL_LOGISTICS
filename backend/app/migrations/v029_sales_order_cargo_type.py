"""Loại phương tiện trên đơn vận chuyển, kế thừa từ báo giá cước.

Cước một chuyến được tính bằng công thức của **loại xe**: mỗi loại xe có đơn giá
xăng dầu, phụ cấp, cước theo kg riêng. Báo giá có `cargo_type` để chọn loại xe,
nhưng `sales_orders` thì không có cột nào — nên đơn vận chuyển không biết mình
thuộc loại xe nào và không thể áp lại công thức theo tải trọng thực tế của đơn.

Hệ quả trước đây: màn đơn vận chuyển tính tiền bằng `số km × 6250 + 800000`, hai
con số không có nguồn nào và không dính gì đến công thức đã cấu hình.

Cột này lấy giá trị từ báo giá khi chốt đơn — điều kiện đã chào cho khách phải đi
theo sang đơn hàng, không bắt khai lại — nhưng sửa được, vì loại xe thực tế điều
đi có thể khác loại xe lúc chào giá.
"""

VERSION = "029_sales_order_cargo_type"

from sqlalchemy import text

COLUMNS = ("cargo_type",)

TABLES = ("sales_orders",)


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
            raise RuntimeError(f"cargo_type column missing on {table}")


def validate_postgresql(connection):
    for table in TABLES:
        exists = list(connection.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :table
        """), {"table": table}))
        if not exists:
            continue
        # Hỏi đúng cột cần kiểm để truy vấn tự nhận diện được, không lẫn với
        # truy vấn cột của migration khác trên cùng bảng.
        columns = {
            row[0] for row in connection.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table
                  AND column_name IN ('cargo_type')
            """), {"table": table})
        }
        if not set(COLUMNS) <= columns:
            raise RuntimeError(f"cargo_type column missing on {table}")
