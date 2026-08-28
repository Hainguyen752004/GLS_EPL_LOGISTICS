import datetime as dt
import uuid
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from models import (APInvoice, AccountMapping, AccountingPeriod, AuditLog, FreightSettlement,
                    JournalBatch, JournalLine, SettlementPayment)
from services.errors import DomainError, conflict, missing_master
from services.tms_cost_service import _actor, _idempotent, _require_permission
from services.tms_money import quantize_currency, to_functional


def _now():
    return dt.datetime.utcnow()


def _date(value, field):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("PAYMENT_DATE_INVALID", f"{field} không hợp lệ.", 422) from None


def _positive_decimal(value, code, message):
    if isinstance(value, bool):
        raise DomainError(code, message, 422)
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError(code, message, 422) from None
    if not amount.is_finite() or amount <= 0:
        raise DomainError(code, message, 422)
    return amount


def _account(db, key):
    mapping = db.get(AccountMapping, key)
    if mapping is None:
        raise missing_master("chart_of_accounts", f"ánh xạ tài khoản: {key}")
    return mapping.account_code


def create_settlement(db, ap_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_payment")
    actor = _actor(actor)
    payload = {**data, "ap_id": ap_id}
    return _idempotent(db, actor, method, path, key, payload,
                       lambda: _create_settlement(db, ap_id, data, actor))


def _create_settlement(db, ap_id, data, actor):
    ap = db.scalar(select(APInvoice).where(APInvoice.id == ap_id).with_for_update())
    if ap is None:
        raise DomainError("AP_NOT_FOUND", "Không tìm thấy hóa đơn phải trả.", 404)
    if ap.status != "posted" or ap.document_kind != "invoice":
        raise conflict("AP_SETTLEMENT_STATUS_INVALID", "Chỉ được tạo đối soát cho AP gốc đã hạch toán.")
    existing = db.scalar(select(FreightSettlement.id).where(FreightSettlement.ap_invoice_id == ap.id))
    if existing:
        raise conflict("SETTLEMENT_DUPLICATE", "AP này đã có hồ sơ đối soát.")
    settlement = FreightSettlement(
        id=str(data.get("id") or uuid.uuid4()),
        ap_invoice_id=ap.id,
        settlement_period=str(data.get("settlement_period") or ap.invoice_date.strftime("%Y-%m")),
        currency_code=ap.currency_code,
        functional_currency=ap.functional_currency,
        approved_amount=ap.total_amount,
        paid_amount=Decimal("0"),
        remaining_amount=ap.total_amount,
        status="open",
        created_by=actor,
        updated_by=actor,
    )
    db.add(settlement)
    db.add(AuditLog(user_id=actor, action="CREATE_FREIGHT_SETTLEMENT", table_name="freight_settlements",
                    record_id=settlement.id, ip_address=db.info.get("request_ip")))
    try:
        db.flush()
    except IntegrityError:
        raise conflict("SETTLEMENT_DUPLICATE", "AP này đã có hồ sơ đối soát.") from None
    return settlement


def post_payment(db, settlement_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_payment")
    actor = _actor(actor)
    payload = {**data, "settlement_id": settlement_id}
    return _idempotent(db, actor, method, path, key, payload,
                       lambda: _post_payment(db, settlement_id, data, actor))


def _post_payment(db, settlement_id, data, actor):
    settlement = db.scalar(select(FreightSettlement).where(FreightSettlement.id == settlement_id).with_for_update())
    if settlement is None:
        raise DomainError("SETTLEMENT_NOT_FOUND", "Không tìm thấy hồ sơ đối soát.", 404)
    if settlement.status not in {"open", "partially_paid"}:
        raise conflict("SETTLEMENT_PAYMENT_STATUS_INVALID", "Trạng thái đối soát không cho phép ghi thanh toán.")
    amount = quantize_currency(
        db,
        _positive_decimal(data.get("amount"), "PAYMENT_AMOUNT_INVALID", "Số tiền thanh toán không hợp lệ."),
        settlement.currency_code,
    )
    currency = str(data.get("currency_code") or settlement.currency_code).upper()
    if currency != settlement.currency_code:
        raise DomainError("PAYMENT_CURRENCY_INVALID", "Tiền thanh toán phải cùng loại tiền với AP trong phạm vi Core 5.", 422)
    if amount > Decimal(settlement.remaining_amount):
        raise conflict("PAYMENT_OVER_AMOUNT", "Số tiền thanh toán vượt quá số còn phải trả.")

    payment_date = _date(data.get("posting_date") or dt.date.today(), "Ngày thanh toán")
    _require_open_period(db, payment_date)
    method_name = str(data.get("payment_method") or "cash").strip().lower()
    bank_account = _account(db, f"bank:{method_name}")
    payable_account = _account(db, "accounts_payable")
    ap = db.get(APInvoice, settlement.ap_invoice_id)
    payment_fx = to_functional(db, amount, settlement.currency_code, payment_date)
    functional_amount = payment_fx["functional_amount"]
    ap_functional_portion = quantize_currency(db, amount * Decimal(ap.exchange_rate_snapshot), settlement.functional_currency)
    payment = SettlementPayment(
        id=str(data.get("id") or uuid.uuid4()),
        settlement_id=settlement.id,
        amount=amount,
        currency_code=settlement.currency_code,
        functional_currency=settlement.functional_currency,
        exchange_rate_snapshot=payment_fx["exchange_rate_snapshot"],
        exchange_rate_date=payment_fx["rate_date"],
        exchange_rate_source=payment_fx["source"],
        functional_amount=functional_amount,
        posting_date=payment_date,
        payment_method=method_name,
        reference_no=data.get("reference_no"),
        created_by=actor,
    )
    batch = _payment_journal(db, payment, payable_account, bank_account, ap_functional_portion)
    payment.posting_reference = batch.id
    db.add(payment)

    new_paid = quantize_currency(db, Decimal(settlement.paid_amount) + amount, settlement.currency_code)
    remaining = quantize_currency(db, Decimal(settlement.approved_amount) - new_paid, settlement.currency_code)
    new_status = "paid" if remaining == 0 else "partially_paid"
    current_version = settlement.version
    next_version = current_version + 1
    changed = db.execute(update(FreightSettlement).where(
        FreightSettlement.id == settlement.id,
        FreightSettlement.version == current_version,
    ).values(paid_amount=new_paid, remaining_amount=remaining, status=new_status,
             version=next_version, updated_at=_now(), updated_by=actor))
    if changed.rowcount != 1:
        raise conflict("VERSION_CONFLICT", "Đối soát đã thay đổi. Vui lòng tải lại dữ liệu.")
    settlement.paid_amount, settlement.remaining_amount, settlement.status = new_paid, remaining, new_status
    settlement.version = next_version
    settlement.updated_at, settlement.updated_by = _now(), actor
    db.add(AuditLog(user_id=actor, action="POST_SETTLEMENT_PAYMENT", table_name="settlement_payments",
                    record_id=payment.id, ip_address=db.info.get("request_ip")))
    db.flush()
    return payment


def _require_open_period(db, posting_date):
    stamp = dt.datetime.combine(posting_date, dt.time.min)
    period = db.scalar(select(AccountingPeriod).where(AccountingPeriod.starts_at <= stamp,
        AccountingPeriod.ends_at >= stamp, AccountingPeriod.status == "open"))
    if period is None:
        raise DomainError("MISSING_OPEN_ACCOUNTING_PERIOD", "Thiếu kỳ kế toán đang mở. Vui lòng vào Master Data.", 422,
                          ["master-data/accounting-periods"])


def _payment_journal(db, payment, payable_account, bank_account, ap_functional_portion=None):
    ap_functional_portion = ap_functional_portion if ap_functional_portion is not None else payment.functional_amount
    batch = JournalBatch(id=f"JB-PAY-{payment.id}", source_type="ap_payment",
                         source_id=payment.id, status="posted", posted_at=_now())
    db.add(batch)
    db.add(JournalLine(batch_id=batch.id, account_code=payable_account, debit=ap_functional_portion,
        credit=Decimal("0"), currency_code=payment.functional_currency, exchange_rate_snapshot=payment.exchange_rate_snapshot,
        transaction_amount=payment.amount, transaction_currency=payment.currency_code,
        exchange_rate=payment.exchange_rate_snapshot, functional_debit=ap_functional_portion,
        functional_credit=Decimal("0")))
    db.add(JournalLine(batch_id=batch.id, account_code=bank_account, debit=Decimal("0"),
        credit=payment.functional_amount, currency_code=payment.functional_currency,
        exchange_rate_snapshot=payment.exchange_rate_snapshot, transaction_amount=-payment.amount,
        transaction_currency=payment.currency_code, exchange_rate=payment.exchange_rate_snapshot,
        functional_debit=Decimal("0"), functional_credit=payment.functional_amount))
    realized_fx = Decimal(ap_functional_portion) - Decimal(payment.functional_amount)
    if realized_fx > 0:
        db.add(JournalLine(batch_id=batch.id, account_code=_account(db, "fx_gain"), debit=Decimal("0"),
            credit=realized_fx, currency_code=payment.functional_currency,
            exchange_rate_snapshot=payment.exchange_rate_snapshot, transaction_amount=Decimal("0"),
            transaction_currency=payment.currency_code, exchange_rate=payment.exchange_rate_snapshot,
            functional_debit=Decimal("0"), functional_credit=realized_fx))
    elif realized_fx < 0:
        loss = -realized_fx
        db.add(JournalLine(batch_id=batch.id, account_code=_account(db, "fx_loss"), debit=loss,
            credit=Decimal("0"), currency_code=payment.functional_currency,
            exchange_rate_snapshot=payment.exchange_rate_snapshot, transaction_amount=Decimal("0"),
            transaction_currency=payment.currency_code, exchange_rate=payment.exchange_rate_snapshot,
            functional_debit=loss, functional_credit=Decimal("0")))
    return batch


def reverse_payment(db, payment_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_payment")
    actor = _actor(actor)
    payload = {**data, "payment_id": payment_id}
    return _idempotent(db, actor, method, path, key, payload,
                       lambda: _reverse_payment(db, payment_id, data, actor))


def _reverse_payment(db, payment_id, data, actor):
    payment = db.scalar(select(SettlementPayment).where(SettlementPayment.id == payment_id).with_for_update())
    if payment is None:
        raise DomainError("PAYMENT_NOT_FOUND", "Không tìm thấy thanh toán cần đảo.", 404)
    if payment.reversal_of_payment_id or payment.status == "reversed":
        raise conflict("PAYMENT_ALREADY_REVERSED", "Thanh toán này đã được đảo hoặc là bút toán đảo.")
    settlement = db.scalar(select(FreightSettlement).where(FreightSettlement.id == payment.settlement_id).with_for_update())
    if settlement is None:
        raise DomainError("SETTLEMENT_NOT_FOUND", "Không tìm thấy hồ sơ đối soát.", 404)
    reversal = SettlementPayment(
        id=str(data.get("id") or uuid.uuid4()),
        settlement_id=settlement.id,
        amount=payment.amount,
        currency_code=payment.currency_code,
        functional_currency=payment.functional_currency,
        exchange_rate_snapshot=payment.exchange_rate_snapshot,
        exchange_rate_date=payment.exchange_rate_date,
        exchange_rate_source=payment.exchange_rate_source,
        functional_amount=payment.functional_amount,
        posting_date=_date(data.get("posting_date") or dt.date.today(), "Ngày đảo thanh toán"),
        payment_method=payment.payment_method,
        reference_no=data.get("reference_no") or payment.reference_no,
        status="reversed",
        reversal_of_payment_id=payment.id,
        created_by=actor,
    )
    batch = JournalBatch(id=f"JB-PAY-REV-{reversal.id}", source_type="payment_reversal",
                         source_id=reversal.id, status="posted", posted_at=_now())
    db.add(batch)
    original_lines = db.query(JournalLine).filter_by(batch_id=payment.posting_reference).all()
    if not original_lines:
        raise conflict("PAYMENT_JOURNAL_NOT_FOUND", "Không tìm thấy bút toán gốc của thanh toán.")
    for line in original_lines:
        db.add(JournalLine(batch_id=batch.id, account_code=line.account_code,
            debit=line.credit, credit=line.debit, currency_code=line.currency_code,
            exchange_rate_snapshot=line.exchange_rate_snapshot,
            transaction_amount=-Decimal(line.transaction_amount or 0),
            transaction_currency=line.transaction_currency, exchange_rate=line.exchange_rate,
            functional_debit=line.functional_credit, functional_credit=line.functional_debit))
    reversal.posting_reference = batch.id
    payment.status = "reversed"
    payment.reversed_by_payment_id = reversal.id
    new_paid = quantize_currency(db, Decimal(settlement.paid_amount) - Decimal(payment.amount), settlement.currency_code)
    settlement.paid_amount = new_paid
    settlement.remaining_amount = quantize_currency(db, Decimal(settlement.approved_amount) - new_paid, settlement.currency_code)
    settlement.status = "open" if new_paid == 0 else "partially_paid"
    settlement.version += 1
    settlement.updated_at = _now()
    settlement.updated_by = actor
    db.add(reversal)
    db.add(AuditLog(user_id=actor, action="REVERSE_SETTLEMENT_PAYMENT", table_name="settlement_payments",
                    record_id=reversal.id, ip_address=db.info.get("request_ip")))
    db.flush()
    return reversal


def get_finance_dashboard(db, filters, actor, permissions):
    _require_permission(permissions, "finance_read")
    return {
        "actual_cost_total": db.query(func.coalesce(func.sum(APInvoice.total_amount), 0)).filter(APInvoice.is_active.is_(True)).scalar(),
        "ap_open_count": db.query(APInvoice).filter(APInvoice.status.in_(["draft", "submitted", "approved", "posted"])).count(),
        "settlement_open_count": db.query(FreightSettlement).filter(FreightSettlement.status.in_(["open", "partially_paid"])).count(),
        "payment_total": db.query(func.coalesce(func.sum(SettlementPayment.amount), 0)).filter(SettlementPayment.status == "posted").scalar(),
    }
