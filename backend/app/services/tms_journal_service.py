import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import APInvoice, AccountMapping, AuditLog, JournalBatch, JournalLine
from services.errors import DomainError, conflict, missing_master
from services.tms_cost_service import _actor, _idempotent, _require_permission
from services.tms_money import quantize_currency


def _now():
    return dt.datetime.utcnow()


def journal_source_statement(source_type, source_id):
    return select(JournalBatch).where(
        JournalBatch.source_type == source_type,
        JournalBatch.source_id == source_id,
    ).with_for_update()


def post_ap_journal(db, ap_id, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_poster")
    actor = _actor(actor)
    payload = {"ap_id": ap_id}
    return _idempotent(
        db, actor, method, path, key, payload,
        lambda: _post_ap_journal(db, ap_id, actor),
    )


def _post_ap_journal(db, ap_id, actor):
    existing = db.scalar(journal_source_statement("ap_invoice", ap_id))
    if existing:
        return existing

    ap = db.scalar(select(APInvoice).where(APInvoice.id == ap_id).with_for_update())
    if ap is None:
        raise DomainError("AP_NOT_FOUND", "Không tìm thấy hóa đơn phải trả.", 404)
    if ap.status != "posted" or ap.document_kind != "invoice":
        raise conflict("AP_JOURNAL_STATUS_INVALID", "Chỉ được hạch toán AP gốc đã post.")
    if not ap.lines:
        raise DomainError("AP_JOURNAL_LINES_REQUIRED", "AP chưa có dòng chi phí để hạch toán.", 422)

    batch = JournalBatch(
        id=f"JB-AP-{ap.id}",
        invoice_id=None,
        source_type="ap_invoice",
        source_id=ap.id,
        status="posted",
        posted_at=_now(),
    )
    db.add(batch)

    journal_lines = []
    input_tax_account = _account_mapping(db, "input_tax") if Decimal(ap.tax_amount) != 0 else None
    payable_account = _account_mapping(db, "accounts_payable")
    for line in ap.lines:
        if not line.account_code_snapshot:
            raise DomainError("MISSING_ACCOUNT_MAPPING", "Thiếu ánh xạ tài khoản. Vui lòng vào Master Data.", 422,
                              ["master-data/chart-of-accounts"])
        journal_lines.append(_add_line(db, batch.id, line.account_code_snapshot, Decimal(line.net_amount), ap))
        if Decimal(line.tax_amount) != 0:
            journal_lines.append(_add_line(db, batch.id, input_tax_account, Decimal(line.tax_amount), ap))
    journal_lines.append(_add_line(db, batch.id, payable_account, -Decimal(ap.total_amount), ap))

    _assert_balanced(journal_lines)
    db.add(AuditLog(user_id=actor, action="POST_AP_JOURNAL", table_name="journal_batches",
                    record_id=batch.id, ip_address=db.info.get("request_ip")))
    try:
        db.flush()
    except IntegrityError:
        existing = db.scalar(select(JournalBatch).where(
            JournalBatch.source_type == "ap_invoice", JournalBatch.source_id == ap.id))
        if existing:
            return existing
        raise conflict("JOURNAL_POST_CONFLICT", "Xung đột khi hạch toán journal.") from None
    return batch


def _account_mapping(db, key):
    mapping = db.get(AccountMapping, key)
    if mapping is None:
        raise missing_master("chart_of_accounts", f"ánh xạ tài khoản: {key}")
    return mapping.account_code


def _add_line(db, batch_id, account_code, amount, ap):
    functional = quantize_currency(db, amount * Decimal(ap.exchange_rate_snapshot), ap.functional_currency)
    debit = functional if functional > 0 else Decimal("0")
    credit = -functional if functional < 0 else Decimal("0")
    line = JournalLine(
        batch_id=batch_id,
        account_code=account_code,
        debit=debit,
        credit=credit,
        currency_code=ap.functional_currency,
        exchange_rate_snapshot=ap.exchange_rate_snapshot,
        transaction_amount=amount,
        transaction_currency=ap.currency_code,
        exchange_rate=ap.exchange_rate_snapshot,
        functional_debit=debit,
        functional_credit=credit,
    )
    db.add(line)
    return line


def _assert_balanced(lines):
    debit = sum((Decimal(line.functional_debit) for line in lines), Decimal("0"))
    credit = sum((Decimal(line.functional_credit) for line in lines), Decimal("0"))
    if debit != credit:
        raise DomainError("JOURNAL_NOT_BALANCED", "Bút toán journal không cân bằng.", 422)
