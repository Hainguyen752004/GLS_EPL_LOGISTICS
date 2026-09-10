"""XOA HAN module ke toan (AR/AP, so cai, thanh toan), thue va ky ke toan + bang di san rong.

VI SAO. Chu du an (10/09) chot: "xoa thi phai xoa luon backend cua module do".
Bon module da AN tren giao dien tu truoc — Shipment 360, Ke toan, Thue, Ky ke
toan — nay go het duong mau chu. Hoa don va hach toan la viec cua he cong no
cua dong nghiep (anh Khang): he nay chi BAN GIAO ho so hoan tat (header +
detail co Acc code) qua GET /api/handover/delivery-orders/{do_id}.

Do truoc khi xoa tren DB demo: ar_invoices 5, journal_lines 15, journal_batches 5,
accounting_periods 2, tax_codes 1, chart_of_accounts 3; cac bang AP/settlement
va bang di san (delivery_order_details, quotation_details, pod, shipment_costs)
deu 0 dong. Khong bang nao con duong doc/ghi tu ma nguon sau moc nay.

GIU LAI: account_mappings (Acc code dung chung theo khoan muc), finance_control_config
(tien te chuc nang), freight_actual_costs / freight_charge_items / freight_cost_documents
(chi phi phat sinh cua chuyen — ho so hoan tat dung), epl_expense_vouchers (bao cao).

ROLLBACK chi dung lai KHUNG toi thieu de code cu import duoc, khong khoi phuc du lieu.
"""

VERSION = "051_xoa_ke_toan_thue_ky_ke_toan"

from sqlalchemy import text

# Thu tu: bang con truoc bang cha (FK). DROP ... CASCADE de khong vuong FK sot.
BO_BANG = (
    "journal_lines", "journal_batches", "gl_transactions", "ar_invoices",
    "settlement_payments", "freight_settlements", "ap_invoice_lines", "ap_invoices",
    "tax_codes", "accounting_periods", "chart_of_accounts",
    "delivery_order_details", "quotation_details", "pod", "shipment_costs",
)


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
        "AND table_name IN (%s)" % ", ".join("'%s'" % b for b in BO_BANG)))]
    if con:
        raise RuntimeError("bang ke toan van con sau khi xoa: %s" % ", ".join(sorted(con)))
