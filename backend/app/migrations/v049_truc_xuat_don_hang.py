"""TRUC XUAT DON HANG (SO) khoi co so du lieu.

Buoc Don hang da roi khoi luong tu moc 7c445d1: bao gia khach chap nhan thi sinh
thang lenh giao hang. Do tren du lieu demo (10/09): 0 don hang, 0/16 lenh con
`so_id`. Chu du an: "SO van con ton tai trong he thong a? truc xuat no di".

Bo: bang `sales_order_documents`, `sales_order_lines`, `sales_orders`; cot
`so_id` tren `delivery_orders`, `delivery_order_details`, `parking_lists`.
`delivery_order_details` khong con khoa noi voi don nao — giu bang (du lieu cu),
khong dung tiep.

ROLLBACK chi dung lai KHUNG toi thieu de code cu import duoc, KHONG khoi phuc du
lieu — du lieu SO da la 0 dong tu truoc moc nay.
"""

VERSION = "049_truc_xuat_don_hang"

from sqlalchemy import text

BO_COT = (("delivery_orders", "so_id"), ("delivery_order_details", "so_id"), ("parking_lists", "so_id"))
BO_BANG = ("sales_order_documents", "sales_order_lines", "sales_orders")


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return [
            "CREATE TABLE IF NOT EXISTS sales_orders (id VARCHAR PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS sales_order_lines (id VARCHAR PRIMARY KEY, so_id VARCHAR REFERENCES sales_orders(id))",
            "CREATE TABLE IF NOT EXISTS sales_order_documents (id VARCHAR PRIMARY KEY, so_id VARCHAR REFERENCES sales_orders(id))",
        ] + ["ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s VARCHAR REFERENCES sales_orders(id)" % (b, c) for b, c in BO_COT]
    return (["ALTER TABLE %s DROP COLUMN IF EXISTS %s" % (b, c) for b, c in BO_COT]
            + ["DROP TABLE IF EXISTS %s" % b for b in BO_BANG])


def _co_bang_sqlite(connection, bang):
    return bool(list(connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % bang)))


def _co_cot_sqlite(connection, bang, cot):
    return any(r[1] == cot for r in connection.execute('PRAGMA table_info("%s")' % bang))


def upgrade_sqlite(connection):
    for b, c in BO_COT:
        if _co_bang_sqlite(connection, b) and _co_cot_sqlite(connection, b, c):
            try:
                connection.execute("ALTER TABLE %s DROP COLUMN %s" % (b, c))
            except Exception:  # noqa: BLE001 — SQLite cu khong DROP COLUMN duoc; du an da ngung SQLite
                pass
    for b in BO_BANG:
        connection.execute("DROP TABLE IF EXISTS %s" % b)


def rollback_sqlite(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS sales_orders (id TEXT PRIMARY KEY)")


def validate_sqlite(connection):
    return


def validate_postgresql(connection):
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"))):
        return
    if list(connection.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'sales_orders'"))):
        raise RuntimeError("bang sales_orders van con sau khi truc xuat")
