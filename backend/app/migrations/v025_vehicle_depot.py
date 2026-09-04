"""Bãi / chi nhánh của phương tiện.

Chủ dự án vận hành khoảng 500 xe nằm ở nhiều bãi và nhiều chi nhánh, nhưng bảng
`vehicles` không có trường nào cho việc đó — chỉ có `inspection_place`, vốn là
nơi đăng kiểm chứ không phải nơi xe đậu. Không có cột này thì giao diện không
thể lọc theo bãi, mà ở quy mô 500 xe thì bãi là bộ lọc chính chứ không phải một
cột phụ.

Để rỗng thay vì đặt một giá trị mặc định nào đó: bịa ra một bãi mặc định sẽ làm
mọi xe cũ trông như đã được khai báo, trong khi thật ra chưa ai gán.
"""

VERSION = "025_vehicle_depot"

from sqlalchemy import text

_COLUMNS = ("depot", "depot_code")


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            "ALTER TABLE vehicles DROP COLUMN IF EXISTS depot_code",
            "ALTER TABLE vehicles DROP COLUMN IF EXISTS depot",
        ]
    return [
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS depot VARCHAR",
        "ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS depot_code VARCHAR",
        # Lọc theo bãi là thao tác thường xuyên nhất trên đội 500 xe.
        "CREATE INDEX IF NOT EXISTS ix_vehicles_depot_code ON vehicles (depot_code)",
    ]


def upgrade_sqlite(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}
    if not columns:
        return
    for column in _COLUMNS:
        if column not in columns:
            connection.execute(f"ALTER TABLE vehicles ADD COLUMN {column} VARCHAR")
    connection.execute("CREATE INDEX IF NOT EXISTS ix_vehicles_depot_code ON vehicles (depot_code)")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}
    if not columns:
        return
    connection.execute("DROP INDEX IF EXISTS ix_vehicles_depot_code")
    for column in reversed(_COLUMNS):
        if column in columns:
            connection.execute(f"ALTER TABLE vehicles DROP COLUMN {column}")


def validate_sqlite(connection):
    columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}
    # Lược đồ chưa dựng thì không có gì để kiểm — đừng bắt lỗi nhầm lúc khởi tạo.
    if not columns:
        return
    if not set(_COLUMNS) <= columns:
        raise RuntimeError("vehicle depot columns missing")


def validate_postgresql(connection):
    # Bảng chưa dựng thì không có gì để kiểm — đừng bắt lỗi nhầm lúc khởi tạo.
    table_exists = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'vehicles'
    """)))
    if not table_exists:
        return
    # Hỏi đúng hai cột cần kiểm thay vì liệt kê toàn bộ cột của bảng: truy vấn
    # tự nhận diện được, nên không lẫn với truy vấn của migration khác cũng đọc
    # cột của `vehicles`.
    columns = {
        row[0] for row in connection.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'vehicles'
              AND column_name IN ('depot', 'depot_code')
        """))
    }
    if not set(_COLUMNS) <= columns:
        raise RuntimeError("vehicle depot columns missing")
