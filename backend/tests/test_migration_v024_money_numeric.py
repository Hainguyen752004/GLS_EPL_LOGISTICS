"""v024: các cột TIỀN phải là Numeric, không phải Float.

services/tms_money.py chủ động bật lỗi INVALID_DECIMAL với mọi giá trị float —
cả tầng tài chính nghiêm ngặt Decimal. Nhưng 21 cột tiền vẫn khai báo Float,
nặng nhất là gl_transactions.debit/credit (sổ cái) và currencies.exchange_rate
(nuôi mọi phép quy đổi). Float nhị phân không biểu diễn chính xác số thập phân
nên cộng dồn một sổ cái bằng float sẽ lệch dần.
"""

import importlib

import pytest

from migrations import v024_money_numeric as v024


def test_every_money_column_is_numeric_in_the_models():
    """Model và migration phải đồng thuận, nếu không lược đồ lại lệch nhau."""
    from sqlalchemy import Numeric

    models = importlib.import_module("models")
    by_table = {table.name: table for table in models.Base.metadata.sorted_tables}

    wrong = []
    for table, column in v024.MONEY_COLUMNS:
        col = by_table[table].columns[column]
        if not isinstance(col.type, Numeric):
            wrong.append(f"{table}.{column}={col.type}")
    assert not wrong, "cột tiền còn kiểu không phải Numeric: " + ", ".join(wrong)


def test_physical_measures_are_left_as_float():
    """Khối lượng, thể tích, km, tốc độ là SỐ ĐO — không phải tiền.

    Đổi chúng sang Numeric là mở rộng phạm vi không cần thiết và tăng rủi ro
    của một bản migration chạy trên dữ liệu thật.
    """
    from sqlalchemy import Float

    models = importlib.import_module("models")
    money = {(table, column) for table, column in v024.MONEY_COLUMNS}

    physical = []
    for table in models.Base.metadata.sorted_tables:
        for col in table.columns:
            name = col.name.lower()
            if any(k in name for k in ("weight", "volume", "cube", "_km", "kmh", "distance")):
                if (table.name, col.name) in money:
                    physical.append(f"{table.name}.{col.name}")
    assert not physical, "số đo vật lý bị đưa vào danh sách cột tiền: " + ", ".join(physical)


def test_postgres_statements_convert_in_place_and_are_reversible():
    up = v024.statements("postgresql", "upgrade")
    down = v024.statements("postgresql", "rollback")

    assert len(up) == len(v024.MONEY_COLUMNS)
    assert len(down) == len(v024.MONEY_COLUMNS)
    for sql in up:
        assert "TYPE NUMERIC(24,6)" in sql
        # USING ...::numeric là phép chuyển an toàn cho float8.
        assert "::numeric" in sql
        assert "DROP" not in sql.upper(), "không được xóa cột hay bảng"
    for sql in down:
        assert "DOUBLE PRECISION" in sql
    # Sổ cái là cột quan trọng nhất, phải có mặt.
    joined = " ".join(up)
    assert '"gl_transactions" ALTER COLUMN "debit"' in joined
    assert '"gl_transactions" ALTER COLUMN "credit"' in joined
    assert '"currencies" ALTER COLUMN "exchange_rate"' in joined


def test_sqlite_is_a_deliberate_no_op():
    """SQLite dùng kiểu động: đổi affinity không làm dữ liệu chính xác hơn.

    Dựng lại 8 bảng để đổi một kiểu chỉ mang tính gợi ý là rủi ro thật mà không
    đem lại gì. Database SQLite mới tự có kiểu đúng vì được dựng từ model.
    """
    assert v024.statements("sqlite", "upgrade") == []
    assert v024.statements("sqlite", "rollback") == []
    v024.upgrade_sqlite(None)   # không được chạm connection
    v024.rollback_sqlite(None)


def test_postgres_validator_only_checks_columns_that_exist():
    """Bản migration này chỉ đổi kiểu, không tạo cột.

    Đòi cột phải tồn tại sẽ làm vỡ mọi lược đồ được dựng từng phần — đó là điều
    đã xảy ra và phải sửa.
    """
    class Connection:
        def __init__(self, rows):
            self.rows = rows

        def execute(self, _statement):
            return self.rows

    # Lược đồ trống: không kết luận gì.
    v024.validate_postgresql(Connection([]))

    # Bảng có nhưng thiếu cột: bỏ qua, không bật lỗi.
    v024.validate_postgresql(Connection([("gl_transactions", "id", "text")]))

    # Cột đúng kiểu: qua.
    v024.validate_postgresql(Connection([
        ("gl_transactions", "debit", "numeric"),
        ("gl_transactions", "credit", "numeric"),
    ]))

    # Cột còn double precision: phải bật lỗi và nói rõ cột nào.
    with pytest.raises(RuntimeError) as excinfo:
        v024.validate_postgresql(Connection([
            ("gl_transactions", "debit", "double precision"),
        ]))
    assert "gl_transactions.debit" in str(excinfo.value)


def test_v024_is_the_registered_head():
    from migrations.runner import required_migration_head

    assert required_migration_head() == v024.VERSION
