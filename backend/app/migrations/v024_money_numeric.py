"""Đổi các cột TIỀN còn kiểu Float sang Numeric(24,6).

Tầng tài chính của dự án nghiêm ngặt Decimal: services/tms_money.py chủ động
bật lỗi INVALID_DECIMAL với mọi giá trị float. Nhưng 21 cột tiền trong models.py
vẫn khai báo Float, trong khi 49 cột khác đã dùng MONEY_TYPE = Numeric(24,6).
Nặng nhất là gl_transactions.debit/credit — sổ cái — và currencies.exchange_rate,
vốn nuôi mọi phép quy đổi tiền tệ.

Float nhị phân không biểu diễn chính xác được số thập phân, nên cộng dồn một sổ
cái bằng float sẽ lệch dần và không bao giờ khớp tuyệt đối.

CHỈ đổi cột tiền. Các đại lượng vật lý (khối lượng, thể tích, km, tốc độ) giữ
nguyên Float: chúng là số đo, không phải số tiền, và không cần chính xác thập
phân tuyệt đối.
"""

VERSION = "024_money_numeric"

from sqlalchemy import text


# (bảng, cột) — 21 cột tiền còn sót lại kiểu Float.
MONEY_COLUMNS = (
    ("currencies", "exchange_rate"),
    ("vehicle_types", "base_rate"),
    ("vehicle_types", "maint_cost"),
    ("price_lists", "unit_price"),
    ("quotations", "fuel_cost"),
    ("quotations", "driver_cost"),
    ("quotations", "toll_fee"),
    ("quotations", "total_cost"),
    ("quotations", "selling_price"),
    ("quotation_details", "unit_price"),
    ("quotation_details", "amount"),
    ("delivery_order_details", "unit_price"),
    ("delivery_order_details", "amount"),
    ("shipment_costs", "fuel_cost"),
    ("shipment_costs", "driver_cost"),
    ("shipment_costs", "toll_fee"),
    ("shipment_costs", "warehouse_fee"),
    ("shipment_costs", "total_cost"),
    ("shipment_costs", "selling_price"),
    ("gl_transactions", "debit"),
    ("gl_transactions", "credit"),
)

MONEY_SQL_TYPE = "NUMERIC(24,6)"


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        # SQLite có kiểu động: kiểu khai báo chỉ mang tính gợi ý về affinity.
        # Xem upgrade_sqlite để biết vì sao ở đó là lệnh rỗng có chủ ý.
        return []
    if direction == "rollback":
        return [
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE DOUBLE PRECISION '
            f'USING "{column}"::double precision'
            for table, column in MONEY_COLUMNS
        ]
    # USING ...::numeric là phép chuyển an toàn cho float8: PostgreSQL làm tròn
    # về biểu diễn thập phân ngắn nhất, nên 4670000.0 vẫn ra 4670000.000000.
    return [
        f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE {MONEY_SQL_TYPE} '
        f'USING "{column}"::numeric'
        for table, column in MONEY_COLUMNS
    ]


def upgrade_sqlite(connection):
    """Lệnh rỗng có chủ ý trên SQLite.

    SQLite dùng kiểu động: kiểu cột chỉ là "affinity", không phải ràng buộc, nên
    đổi nó không làm dữ liệu chính xác hơn. Cách duy nhất để đổi kiểu khai báo
    là dựng lại bảng — với 8 bảng thì đó là rủi ro thật mà không đem lại gì.

    Và nó tự khỏi: sau bản migration này models.py khai báo Numeric, nên mọi
    database SQLite mới (dựng qua create_all rồi đánh mốc — xem
    database._needs_baseline) đã có kiểu đúng ngay từ đầu. Chỉ các file SQLite
    cũ giữ affinity REAL, mà đó đều là file dùng một lần cho dev và test.

    Đích cần đúng đắn là PostgreSQL, và ở đó phép đổi kiểu là thật.
    """
    validate_sqlite(connection)


def rollback_sqlite(connection):
    """Lệnh rỗng: không có gì để hoàn nguyên trên SQLite."""
    return


def validate_sqlite(connection):
    """Không có gì để kiểm trên SQLite.

    Bản migration này chỉ ĐỔI KIỂU, không tạo cột — nên cột chưa tồn tại không
    phải việc của nó, mà là việc của bản migration sinh ra cột đó. Và kiểu cột
    trên SQLite chỉ là affinity nên cũng không kiểm được điều gì có ý nghĩa.
    """
    return


def validate_postgresql(connection):
    """Mọi cột tiền phải thực sự là numeric, không còn double precision."""
    # Lặp trực tiếp trên kết quả, không gọi .fetchall(): đó là khuôn các
    # migration khác dùng, và các test double trả về list thuần.
    rows = list(connection.execute(text("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
    """)))
    if not rows:
        return
    actual = {(row[0], row[1]): row[2] for row in rows}
    tables_present = {row[0] for row in rows}

    # Chỉ kiểm KIỂU của những cột đang tồn tại. Bản migration này không tạo
    # cột, nên bảng hay cột chưa có là việc của bản migration sinh ra chúng —
    # đòi chúng phải có ở đây sẽ làm vỡ mọi lược đồ dựng từng phần.
    wrong = []
    for table, column in MONEY_COLUMNS:
        if table not in tables_present:
            continue
        data_type = actual.get((table, column))
        if data_type is None:
            continue
        if data_type != "numeric":
            wrong.append(f"{table}.{column}={data_type}")
    if wrong:
        raise RuntimeError("money columns must be numeric: " + ", ".join(sorted(wrong)))
