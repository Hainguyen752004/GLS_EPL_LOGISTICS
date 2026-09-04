"""Ghi đè giá thành theo từng chiếc xe.

Công thức giá thành thuộc về **loại xe**. Nhưng hai chiếc cùng loại vẫn có chi
phí thật khác nhau: xe cũ tốn dầu hơn, xe trả góp gánh thêm khấu hao, xe ở bãi
xa chịu phí điều động khác.

Cố ý KHÔNG cho mỗi chiếc một công thức riêng: đội xe khoảng 500 chiếc, nên đó là
500 công thức phải bảo trì — đổi giá dầu phải sửa 500 chỗ, và rất dễ có xe bị bỏ
sót rồi tính sai giá mà không ai biết.

Bảng này chỉ chứa **phần chênh lệch**. Xe không ghi đè thì không có dòng nào ở
đây, và nó kế thừa nguyên vẹn công thức của loại xe. Nhờ vậy đổi giá dầu vẫn sửa
một chỗ cho cả đội.
"""

VERSION = "027_vehicle_cost_overrides"

from sqlalchemy import text

TABLE = "vehicle_cost_overrides"


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [f"DROP TABLE IF EXISTS {TABLE}"]
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id VARCHAR PRIMARY KEY,
            vehicle_id VARCHAR NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
            component VARCHAR NOT NULL,
            value NUMERIC(24,6) NOT NULL DEFAULT 0,
            note VARCHAR,
            updated_at TIMESTAMP,
            updated_by VARCHAR
        )
        """,
        # Mot xe chi duoc ghi de MOT lan cho moi cau phan chi phi.
        f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{TABLE}_vehicle_component ON {TABLE} (vehicle_id, component)",
        f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_vehicle ON {TABLE} (vehicle_id)",
    ]


def upgrade_sqlite(connection):
    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id VARCHAR PRIMARY KEY,
            vehicle_id VARCHAR NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
            component VARCHAR NOT NULL,
            value NUMERIC NOT NULL DEFAULT 0,
            note VARCHAR,
            updated_at TIMESTAMP,
            updated_by VARCHAR
        )
    """)
    connection.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{TABLE}_vehicle_component ON {TABLE} (vehicle_id, component)")
    connection.execute(f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_vehicle ON {TABLE} (vehicle_id)")
    validate_sqlite(connection)


def rollback_sqlite(connection):
    connection.execute(f"DROP TABLE IF EXISTS {TABLE}")


def _required():
    return {"id", "vehicle_id", "component", "value", "note"}


def validate_sqlite(connection):
    rows = list(connection.execute(f'PRAGMA table_info("{TABLE}")'))
    if not rows:
        return
    if not _required() <= {row[1] for row in rows}:
        raise RuntimeError("vehicle cost override columns missing")


def validate_postgresql(connection):
    exists = list(connection.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'vehicle_cost_overrides'
    """)))
    if not exists:
        return
    columns = {
        row[0] for row in connection.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'vehicle_cost_overrides'
        """))
    }
    if not _required() <= columns:
        raise RuntimeError("vehicle cost override columns missing")
