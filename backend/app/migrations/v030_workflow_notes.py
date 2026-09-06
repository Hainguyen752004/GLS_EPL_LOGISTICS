"""Cot ghi chu cho bao gia, don van chuyen va lenh giao hang.

Ba man hinh deu co mot o Ghi chu lon (textarea 4-5 dong) kem placeholder rat
cu the — `qt-notes` goi y "Bao gia chua bao gom thue VAT 10%, co hieu luc trong
30 ngay, thanh toan truoc 50%". Nhung khong mot bang nao co cot de chua, va
khong mot payload nao gui chung len.

He qua: nguoi dung go dieu kien bao gia vao do, bam Luu, va noi dung bien mat
khong mot loi nao. Day dung la loai o nhap "chi de cho vui" — no trong nhu that
va nhan duoc chu, chi la khong luu.

Dat tren CA BA bang: dieu kien chao o buoc bao gia, ghi chu dieu phoi o buoc
don hang, va luu y giao nhan o buoc lenh giao hang la ba thu khac nhau, khong
ke thua cho nhau duoc.

Dung TEXT chu khong phai VARCHAR: day la o nhap nhieu dong, khong co gioi han
do dai tu nhien nao.
"""

VERSION = "030_workflow_notes"

from sqlalchemy import text

COLUMNS = ("notes",)

TABLES = ("quotations", "sales_orders", "delivery_orders")


def statements(dialect, direction="upgrade"):
    if direction == "rollback":
        return [
            f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}"
            for table in TABLES
            for column in reversed(COLUMNS)
        ]
    return [
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} TEXT"
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
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
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
        # Bang chua dung thi khong co gi de kiem — dung bat loi luc khoi tao.
        if not columns:
            continue
        if not set(COLUMNS) <= columns:
            raise RuntimeError(f"notes column missing on {table}")


def validate_postgresql(connection):
    for table in TABLES:
        exists = list(connection.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :table
        """), {"table": table}))
        if not exists:
            continue
        # Hoi dung cot can kiem de truy van tu nhan dien duoc, khong lan voi
        # truy van cot cua migration khac tren cung bang.
        columns = {
            row[0] for row in connection.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table
                  AND column_name IN ('notes')
            """), {"table": table})
        }
        if not set(COLUMNS) <= columns:
            raise RuntimeError(f"notes column missing on {table}")
