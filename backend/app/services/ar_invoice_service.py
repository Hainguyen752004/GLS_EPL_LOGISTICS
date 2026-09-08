import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select

from models import AccountingPeriod, ARInvoice, DeliveryOrder, DeliveryOrderCloseout, FinanceControlConfig, JournalBatch, JournalLine, SalesOrder
from services.errors import DomainError, conflict


MONEY_QUANTUM = Decimal("0.000001")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _utc_naive(value=None) -> dt.datetime:
    value = value or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainError(
            "TIMEZONE_REQUIRED",
            "Thời điểm lập hóa đơn phải kèm múi giờ.",
            422,
        )
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def _require_open_accounting_period(db, stamp):
    """Từ chối hạch toán ngoài một kỳ kế toán đang mở.

    Đường AP và settlement đã kiểm điều này (tms_ap_service._validate_post_readiness,
    tms_settlement_service), nhưng đường AR thì không — trong khi posted_at lại
    do client gửi lên. Nghĩa là người gọi có thể ghi doanh thu lùi vào một kỳ
    đã đóng, đúng thứ mà việc khóa kỳ tồn tại để ngăn.
    """
    period = db.scalar(
        select(AccountingPeriod).where(
            AccountingPeriod.starts_at <= stamp,
            AccountingPeriod.ends_at >= stamp,
            AccountingPeriod.status == "open",
        )
    )
    if period is None:
        raise DomainError(
            "MISSING_OPEN_ACCOUNTING_PERIOD",
            "Thiếu kỳ kế toán đang mở cho thời điểm ghi sổ. Vui lòng vào Master Data.",
            422,
            ["master-data/accounting-periods"],
        )
    return period


def post_ar_invoice(db, data, user="system"):
    do_id = data["do_id"]
    amount_override = data.get("amount_override")
    existing = db.scalar(select(ARInvoice).where(
        ARInvoice.do_id == do_id,
        ARInvoice.is_active.is_(True),
    ).with_for_update())
    if existing:
        if amount_override is not None and _money(existing.amount) != _money(amount_override):
            raise conflict(
                "AR_ALREADY_POSTED_DIFFERENT_AMOUNT",
                "Hóa đơn công nợ đã ghi sổ với số tiền khác.",
                ["ar-invoices", "delivery-closeout"],
            )
        return existing

    delivery = db.scalar(select(DeliveryOrder).where(
        DeliveryOrder.id == do_id,
    ).with_for_update())
    if not delivery:
        raise DomainError(
            "DELIVERY_ORDER_NOT_FOUND",
            f"Không tìm thấy lệnh giao hàng {do_id}.",
            404,
            ["delivery-orders"],
        )
    if delivery.canonical_status != "delivered":
        raise conflict(
            "DELIVERY_ORDER_NOT_DELIVERED",
            "Chỉ lệnh giao hàng đã hoàn thành POD mới được lập hóa đơn.",
            ["delivery-orders", "pod"],
        )

    sales_order = db.get(SalesOrder, delivery.so_id) if delivery.so_id else None
    if not sales_order or sales_order.canonical_status != "confirmed":
        raise conflict(
            "SALES_ORDER_NOT_CONFIRMED",
            "Đơn hàng nguồn phải được xác nhận trước khi lập hóa đơn.",
            ["sales-orders"],
        )
    if not delivery.customer_id or delivery.customer_id != sales_order.customer_id:
        raise DomainError(
            "INVOICE_LINEAGE_INVALID",
            "Khách hàng trên DO không khớp với đơn hàng nguồn.",
            422,
            ["sales-orders", "delivery-orders"],
        )

    closeout = db.scalar(select(DeliveryOrderCloseout).where(
        DeliveryOrderCloseout.do_id == do_id,
    ))
    amount = _money(
        amount_override
        if amount_override is not None
        else closeout.final_selling_price if closeout is not None else sales_order.total_amount
    )
    if amount <= 0:
        raise DomainError(
            "INVOICE_AMOUNT_INVALID",
            "Giá trị hợp đồng trên đơn hàng phải lớn hơn 0.",
            422,
            ["sales-orders"],
        )
    vat_pct = _money(sales_order.tax_rate_snapshot or 0)
    vat_amount = _money(amount * vat_pct / Decimal("100"))
    total = _money(amount + vat_amount)
    posted_at = _utc_naive(data.get("posted_at"))
    # posted_at do client gửi lên, nên phải chốt vào một kỳ kế toán đang mở
    # trước khi ghi bất cứ thứ gì.
    _require_open_accounting_period(db, posted_at)
    invoice_id = data.get("id") or f"INV-{posted_at:%Y%m%d}-{uuid4().hex[:12].upper()}"

    invoice = ARInvoice(
        id=invoice_id,
        canonical_status="posted",
        created_at=posted_at,
        updated_at=posted_at,
        created_by=user,
        updated_by=user,
        is_active=True,
        currency_code=sales_order.currency_code or "VND",
        exchange_rate_snapshot=sales_order.exchange_rate_snapshot or 1,
        tax_rate_snapshot=vat_pct,
        do_id=delivery.id,
        customer_id=delivery.customer_id,
        invoice_date=posted_at.date().isoformat(),
        amount=amount,
        vat_pct=vat_pct,
        vat_amount=vat_amount,
        total=total,
        status="Posted",
    )
    db.add(invoice)
    db.flush()

    batch = JournalBatch(
        id=f"JB-AR-{invoice.id}",
        invoice_id=invoice.id,
        source_type="ar_invoice",
        source_id=invoice.id,
        status="posted",
        posted_at=posted_at,
        created_at=posted_at,
    )
    db.add(batch)
    db.flush()
    exchange_rate = _money(invoice.exchange_rate_snapshot or 1)
    functional_total = _money(total * exchange_rate)
    functional_amount = _money(amount * exchange_rate)
    functional_vat = _money(vat_amount * exchange_rate)
    finance_config = db.get(FinanceControlConfig, "GLOBAL")
    functional_currency = finance_config.functional_currency if finance_config else "VND"
    common = {
        "batch_id": batch.id,
        "currency_code": functional_currency,
        "exchange_rate_snapshot": invoice.exchange_rate_snapshot,
        "transaction_currency": invoice.currency_code,
        "exchange_rate": invoice.exchange_rate_snapshot,
    }
    db.add_all([
        JournalLine(
            account_code="131",
            debit=functional_total,
            credit=0,
            transaction_amount=total,
            functional_debit=functional_total,
            functional_credit=0,
            **common,
        ),
        JournalLine(
            account_code="511",
            debit=0,
            credit=functional_amount,
            transaction_amount=amount,
            functional_debit=0,
            functional_credit=functional_amount,
            **common,
        ),
        JournalLine(
            account_code="3331",
            debit=0,
            credit=functional_vat,
            transaction_amount=vat_amount,
            functional_debit=0,
            functional_credit=functional_vat,
            **common,
        ),
    ])
    db.flush()
    return invoice


def serialize_ar_invoice(invoice):
    timestamp = invoice.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    else:
        timestamp = timestamp.astimezone(dt.timezone.utc)
    return {
        "id": invoice.id,
        "do_id": invoice.do_id,
        "customer_id": invoice.customer_id,
        "invoice_date": invoice.invoice_date,
        "posted_at": timestamp.isoformat().replace("+00:00", "Z"),
        "canonical_status": invoice.canonical_status,
        "currency_code": invoice.currency_code,
        "amount": float(invoice.amount or 0),
        "vat_pct": float(invoice.vat_pct or 0),
        "vat_amount": float(invoice.vat_amount or 0),
        "total": float(invoice.total or 0),
        "version": invoice.version,
    }
