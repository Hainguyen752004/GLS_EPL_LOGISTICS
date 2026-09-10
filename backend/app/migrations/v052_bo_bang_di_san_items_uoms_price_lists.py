"""Bo ba bang DI SAN khong con duong doc/ghi: items, uoms, price_lists.

VI SAO. Ra soat DB demo (10/09) sau khi xoa SO va ke toan: ba bang nay con 1/3/1
dong gieo tu bo demo cu, nhung KHONG mot route hay service nao doc chung — hang hoa
cua bao gia nam o `quotation_items`, don vi cuoc nam trong `quotations.price_basis`,
gia theo khach di theo bao gia. Giu lai la giu rac: nguoi doc lua do nghi he co
"bang gia theo khach" trong khi khong man nao dung.

GIU `currencies` (bang cu) vi currency_routes va bao_gia_service con doc ty gia o do.
"""

VERSION = "052_bo_bang_di_san_items_uoms_price_lists"

from sqlalchemy import text

BO_BANG = ("price_lists", "items", "uoms")


def statements(dialect, direction="upgrade"):
    if dialect != "postgresql":
        return []
    if direction == "rollback":
        return ["CREATE TABLE IF NOT EXISTS %s (id VARCHAR PRIMARY KEY)" % b for b in reversed(BO_BANG)]
    return ["DROP TABLE IF EXISTS %s CASCADE" % b for b in BO_BANG]


def upgrade_sqlite(connection):
    for b in BO_BANG:
        connection.execute("DROP TABLE IF EXISTS %s" % b)


def rollback_sqlite(connection):
    for b in reversed(BO_BANG):
        connection.execute("CREATE TABLE IF NOT EXISTS %s (id TEXT PRIMARY KEY)" % b)


def validate_sqlite(connection):
    return


def validate_postgresql(connection):
    if not list(connection.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"))):
        return
    con = [r[0] for r in connection.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
        "AND table_name IN ('price_lists','items','uoms')"))]
    if con:
        raise RuntimeError("bang di san van con: %s" % ", ".join(sorted(con)))
