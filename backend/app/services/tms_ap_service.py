import datetime as dt
import re
import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from models import (APInvoice, APInvoiceLine, AccountMapping, AccountingPeriod, AuditLog,
                    Carrier, FreightActualCost, TaxCode)
from services.errors import DomainError, conflict, missing_master
from services.tms_cost_service import _actor, _expected_version, _idempotent, _require_permission
from services.tms_money import quantize_currency, require_finance_config


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
        raise DomainError("AP_DATE_INVALID", f"{field} không hợp lệ.", 422) from None


def normalize_vendor_invoice_no(value):
    normalized = re.sub(r"\s+", " ", str(value or "").strip()).upper()
    if not normalized or len(normalized) > 128:
        raise DomainError("VENDOR_INVOICE_NO_INVALID", "Số hóa đơn nhà cung cấp không hợp lệ.", 422)
    return normalized


def ap_for_update_statement(ap_id):
    return select(APInvoice).where(APInvoice.id == ap_id).with_for_update()


def _ap_for_update(db, ap_id):
    ap = db.scalar(ap_for_update_statement(ap_id))
    if ap is None:
        raise DomainError("AP_NOT_FOUND", "Không tìm thấy hóa đơn phải trả.", 404)
    return ap


def _audit(db, action, record_id, actor):
    db.add(AuditLog(user_id=actor, action=action, table_name="ap_invoices", record_id=record_id,
                    ip_address=db.info.get("request_ip")))


def create_ap_from_cost(db, cost_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    actor = _actor(actor)
    payload = {**data, "cost_id": cost_id}
    return _idempotent(db, actor, method, path, key, payload,
                       lambda: _create_ap_from_cost(db, cost_id, data, actor))


def _create_ap_from_cost(db, cost_id, data, actor):
    cost = db.scalar(select(FreightActualCost).where(FreightActualCost.id == cost_id).with_for_update())
    if cost is None:
        raise DomainError("FREIGHT_COST_NOT_FOUND", "Không tìm thấy chi ph? thực tế.", 404)
    if cost.status != "approved" or not cost.is_active:
        raise conflict("COST_NOT_APPROVED", "Chỉ được lập AP từ chi ph? đã duyệt đang hoạt động.")
    if cost.reversal_of_cost_id:
        raise conflict("COST_REVERSAL_AP_FORBIDDEN", "Không được lập AP từ chứng từ đảo chi ph?.")
    carrier = db.get(Carrier, cost.carrier_id)
    if carrier is None or carrier.status != "active":
        raise missing_master("carrier", "nhà vận chuyển đang hoạt động")
    vendor_no = str(data.get("vendor_invoice_no") or "").strip()
    normalized = normalize_vendor_invoice_no(vendor_no)
    invoice_date = _date(data.get("invoice_date"), "Ngày hóa đơn")
    due_date = _date(data["due_date"], "Hạn thanh toán") if data.get("due_date") else None
    if due_date and due_date < invoice_date:
        raise DomainError("AP_DUE_DATE_INVALID", "Hạn thanh toán không được trước ngày hóa đơn.", 422)
    duplicate = db.scalar(select(APInvoice.id).where(
        ((APInvoice.cost_id == cost.id) & (APInvoice.is_active.is_(True)))
        | ((APInvoice.carrier_id == carrier.id)
           & (APInvoice.normalized_vendor_invoice_no == normalized)
           & (APInvoice.document_kind == "invoice"))
    ))
    if duplicate:
        raise conflict("AP_DUPLICATE", "Hóa đơn nhà cung cấp hoặc AP đang hoạt động cho chi phí này đã tồn tại.")
    ap = APInvoice(id=str(data.get("id") or uuid.uuid4()), cost_id=cost.id, carrier_id=carrier.id,
        carrier_name_snapshot=carrier.name, carrier_tax_code_snapshot=carrier.tax_code,
        vendor_invoice_no=vendor_no, normalized_vendor_invoice_no=normalized, document_kind="invoice",
        invoice_date=invoice_date, due_date=due_date, currency_code=cost.currency_code,
        functional_currency=cost.functional_currency, exchange_rate_snapshot=cost.exchange_rate_snapshot,
        exchange_rate_date=cost.exchange_rate_date, exchange_rate_source=cost.exchange_rate_source,
        subtotal_amount=cost.subtotal_amount, tax_amount=cost.tax_amount, total_amount=cost.total_amount,
        functional_subtotal_amount=quantize_currency(db, Decimal(cost.subtotal_amount) * Decimal(cost.exchange_rate_snapshot), cost.functional_currency),
        functional_tax_amount=quantize_currency(db, Decimal(cost.tax_amount) * Decimal(cost.exchange_rate_snapshot), cost.functional_currency),
        functional_total_amount=quantize_currency(db, Decimal(cost.total_amount) * Decimal(cost.exchange_rate_snapshot), cost.functional_currency),
        created_by=actor, updated_by=actor)
    db.add(ap)
    for item in cost.items:
        ap.lines.append(APInvoiceLine(id=str(uuid.uuid4()), charge_item_id=item.id,
            charge_type=item.charge_type, description=item.description, quantity=item.quantity,
            unit_price=item.unit_price, currency_code=cost.currency_code, tax_code=item.tax_code,
            tax_rate_snapshot=item.tax_rate_snapshot, tax_mode=item.tax_mode,
            account_mapping_key=f"carrier_expense:{item.charge_type}", net_amount=item.net_amount,
            tax_amount=item.tax_amount, total_amount=item.total_amount,
            rounding_adjustment=item.rounding_adjustment))
    _audit(db, "CREATE_AP_INVOICE", ap.id, actor)
    try:
        db.flush()
    except IntegrityError:
        raise conflict("AP_DUPLICATE", "Hóa đơn nhà cung cấp hoặc AP đang hoạt động cho chi phí này đã tồn tại.") from None
    return ap


def transition_ap(db, ap_id, action, expected_version, method, path, key, actor, permissions):
    permission = {"submit": "finance_creator", "approve": "finance_approver", "post": "finance_poster"}.get(action)
    if permission is None:
        raise DomainError("AP_ACTION_INVALID", "Thao tác AP không hợp lệ.", 422)
    _require_permission(permissions, permission)
    actor = _actor(actor)
    payload = {"action": action, "expected_version": expected_version}
    return _idempotent(db, actor, method, path, key, payload,
                       lambda: _transition_ap(db, ap_id, action, expected_version, actor))


def _transition_ap(db, ap_id, action, expected_version, actor):
    expected_version = _expected_version(expected_version)
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
        raise DomainError("EXPECTED_VERSION_INVALID", "Phiên bản dự kiến phải là số nguyên dương.", 422)
    ap = _ap_for_update(db, ap_id)
    if ap.version != expected_version:
        raise conflict("VERSION_CONFLICT", "AP đã thay đổi. Vui lòng tải lại dữ liệu.")
    source, target = {"submit": ("draft", "submitted"), "approve": ("submitted", "approved"), "post": ("approved", "posted")}[action]
    if ap.status != source or ap.document_kind != "invoice":
        raise conflict("AP_TRANSITION_INVALID", "Trạng thái AP không cho phép thao tác này.")
    config = require_finance_config(db)
    if action == "approve" and config.enforce_creator_approver_sod and ap.created_by == actor:
        raise DomainError("SEPARATION_OF_DUTIES", "Người tạo không được đồng thời duyệt AP.", 403)
    if action == "post":
        if config.require_distinct_poster and actor in {ap.created_by, ap.approved_by}:
            raise DomainError("SEPARATION_OF_DUTIES", "Người tạo hoặc duyệt không được đồng thời hạch toán AP.", 403)
        _validate_post_readiness(db, ap)
        callback = db.info.get("ap_post_callback")
        if callback is None:
            raise DomainError("AP_POSTING_SERVICE_UNAVAILABLE", "Dịch vụ hạch toán AP chưa sẵn sàng.", 503)
    stamp = _now()
    action_fields = {
        "submit": ("submitted_at", "submitted_by"),
        "approve": ("approved_at", "approved_by"),
        "post": ("posted_at", "posted_by"),
    }
    at_field, by_field = action_fields[action]
    values = {"status": target, "version": expected_version + 1, "updated_at": stamp, "updated_by": actor,
              at_field: stamp, by_field: actor}
    changed = db.execute(update(APInvoice).where(APInvoice.id == ap.id, APInvoice.version == expected_version,
                                                APInvoice.status == source).values(**values))
    if changed.rowcount != 1:
        raise conflict("VERSION_CONFLICT", "AP đã thay đổi. Vui lòng tải lại dữ liệu.")
    for name, value in values.items():
        setattr(ap, name, value)
    if action == "post":
        callback = db.info.get("ap_post_callback")
        if callback is None:
            raise DomainError("AP_POSTING_SERVICE_UNAVAILABLE", "Dịch vụ hạch toán AP chưa sẵn sàng.", 503)
        ap.posting_reference = callback(ap)
    _audit(db, f"{action.upper()}_AP_INVOICE", ap.id, actor)
    db.flush()
    return ap


def _validate_post_readiness(db, ap):
    stamp = dt.datetime.combine(ap.invoice_date, dt.time.min)
    period = db.scalar(select(AccountingPeriod).where(AccountingPeriod.starts_at <= stamp,
        AccountingPeriod.ends_at >= stamp, AccountingPeriod.status == "open"))
    if period is None:
        raise DomainError("MISSING_OPEN_ACCOUNTING_PERIOD", "Thiếu kỳ kế toán đang mở. Vui lòng vào Master Data.", 422,
                          ["master-data/accounting-periods"])
    required = {"accounts_payable"}
    if Decimal(ap.tax_amount) != 0:
        required.add("input_tax")
    required.update(line.account_mapping_key for line in ap.lines)
    mappings = {row.mapping_key: row for row in db.scalars(select(AccountMapping).where(AccountMapping.mapping_key.in_(required)))}
    missing = sorted(required - mappings.keys())
    if missing:
        raise missing_master("chart_of_accounts", "ánh xạ tài khoản: " + ", ".join(missing))
    for line in ap.lines:
        tax = db.scalar(select(TaxCode).where(TaxCode.code == line.tax_code, TaxCode.is_active.is_(True),
                                              TaxCode.effective_from <= ap.invoice_date,
                                              (TaxCode.effective_to.is_(None) | (TaxCode.effective_to >= ap.invoice_date))))
        if tax is None or Decimal(tax.rate) != Decimal(line.tax_rate_snapshot) or tax.mode != line.tax_mode:
            raise DomainError("MISSING_TAX_CODE", "Thiếu cấu hình thuế hợp lệ. Vui lòng vào Master Data.", 422,
                              ["master-data/tax-codes"])
        line.account_code_snapshot = mappings[line.account_mapping_key].account_code


def reverse_ap(db, ap_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_poster")
    actor = _actor(actor)
    return _idempotent(db, actor, method, path, key, data,
                       lambda: _reverse_ap(db, ap_id, data, actor))


def _reverse_ap(db, ap_id, data, actor):
    ap = _ap_for_update(db, ap_id)
    expected = _expected_version(data.get("expected_version"))
    reason = str(data.get("reason") or "").strip()
    if ap.version != expected:
        raise conflict("VERSION_CONFLICT", "AP đã thay đổi. Vui lòng tải lại dữ liệu.")
    if ap.document_kind != "invoice" or ap.status != "posted" or ap.reversal_of_ap_id:
        raise conflict("AP_REVERSAL_INVALID", "Chỉ được đảo AP gốc đã hạch toán và chưa thanh toán.")
    if not reason:
        raise DomainError("REVERSAL_REASON_REQUIRED", "Lý do đảo AP là bắt buộc.", 422)
    if db.scalar(select(APInvoice.id).where(APInvoice.reversal_of_ap_id == ap.id)):
        raise conflict("AP_ALREADY_REVERSED", "AP đã có chứng từ đảo.")
    payment_guard = db.info.get("ap_has_active_payment")
    if payment_guard and payment_guard(ap.id):
        raise conflict("AP_HAS_ACTIVE_PAYMENT", "Phải đảo thanh toán trước khi đảo AP.")
    reversal_date = _date(data.get("reversal_date") or dt.date.today(), "Ngày đảo")
    credit_id = str(uuid.uuid4())
    changed = db.execute(update(APInvoice).where(APInvoice.id == ap.id, APInvoice.version == expected,
        APInvoice.status == "posted").values(status="reversed", is_active=False, version=expected + 1,
        reversed_by_ap_id=credit_id, reversed_at=_now(), reversed_by=actor, updated_at=_now(), updated_by=actor))
    if changed.rowcount != 1:
        raise conflict("VERSION_CONFLICT", "AP đã thay đổi. Vui lòng tải lại dữ liệu.")
    ap.status, ap.is_active, ap.version, ap.reversed_by_ap_id = "reversed", False, expected + 1, credit_id
    credit = APInvoice(id=credit_id, cost_id=ap.cost_id, carrier_id=ap.carrier_id,
        carrier_name_snapshot=ap.carrier_name_snapshot, carrier_tax_code_snapshot=ap.carrier_tax_code_snapshot,
        vendor_invoice_no=f"CM-{ap.vendor_invoice_no}", normalized_vendor_invoice_no=f"CM-{ap.normalized_vendor_invoice_no}",
        document_kind="credit_memo", invoice_date=reversal_date, due_date=reversal_date,
        currency_code=ap.currency_code, functional_currency=ap.functional_currency,
        exchange_rate_snapshot=ap.exchange_rate_snapshot, exchange_rate_date=ap.exchange_rate_date,
        exchange_rate_source=ap.exchange_rate_source, subtotal_amount=-ap.subtotal_amount,
        tax_amount=-ap.tax_amount, total_amount=-ap.total_amount,
        functional_subtotal_amount=-ap.functional_subtotal_amount, functional_tax_amount=-ap.functional_tax_amount,
        functional_total_amount=-ap.functional_total_amount, status="posted", is_active=False,
        reversal_of_ap_id=ap.id, reversal_reason=reason, posting_reference=f"REV-{ap.posting_reference or ap.id}",
        created_by=actor, updated_by=actor, posted_by=actor, posted_at=_now())
    for line in ap.lines:
        credit.lines.append(APInvoiceLine(id=str(uuid.uuid4()), charge_item_id=line.charge_item_id,
            charge_type=line.charge_type, description=line.description, quantity=line.quantity,
            unit_price=line.unit_price, currency_code=line.currency_code, tax_code=line.tax_code,
            tax_rate_snapshot=line.tax_rate_snapshot, tax_mode=line.tax_mode,
            account_mapping_key=line.account_mapping_key, account_code_snapshot=line.account_code_snapshot,
            net_amount=-line.net_amount, tax_amount=-line.tax_amount, total_amount=-line.total_amount,
            rounding_adjustment=-line.rounding_adjustment))
    db.add(credit)
    _audit(db, "REVERSE_AP_INVOICE", credit.id, actor)
    db.flush()
    return credit
