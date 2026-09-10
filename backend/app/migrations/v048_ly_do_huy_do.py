"""Them cot `delivery_orders.cancel_reason` — LY DO HUY lenh giao hang.

VI SAO. Chu du an hoi (10/09): "khi huy bao gia hay DO gi do thi co ghi nhan lai
ly do khong". Bao gia da co `quotations.close_reason`; DO thi KHONG — duong huy
la `PUT /status {status: cancelled}` khong nhan gi them, nen mot DO da huy khong
tra loi duoc cau "vi sao" khi doi soat voi khach. Tu moc nay: huy DO phai kem ly
do (422 CANCEL_REASON_REQUIRED neu thieu), ly do luu o cot nay va hien duoi o
trang thai tren bang DO.
"""

VERSION = "048_ly_do_huy_do"

from sqlalchemy import text


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return ["ALTER TABLE delivery_orders DROP COLUMN IF EXISTS cancel_reason"]
    return ["ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS cancel_reason TEXT"]


def _co_cot_sqlite(connection, bang, cot):
    return any(r[1] == cot for r in connection.execute('PRAGMA table_info("%s")' % bang))


def upgrade_sqlite(connection):
    if list(connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='delivery_orders'")) \
            and not _co_cot_sqlite(connection, "delivery_orders", "cancel_reason"):
        connection.execute("ALTER TABLE delivery_orders ADD COLUMN cancel_reason TEXT")


def rollback_sqlite(connection):
    return


def validate_sqlite(connection):
    return


def validate_postgresql(connection):
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"))):
        return
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = 'delivery_orders' "
            "AND column_name = 'cancel_reason'"))):
        raise RuntimeError("delivery_orders thieu cot cancel_reason")
