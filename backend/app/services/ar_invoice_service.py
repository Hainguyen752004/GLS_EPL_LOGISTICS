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

    # CHỨNG TỪ NGUỒN CỦA MỘT HOÁ ĐƠN: đơn hàng (đường cũ) HOẶC báo giá (luồng mới).
    #
    # Luồng mới bỏ bước Đơn hàng: báo giá được khách chấp nhận thì tách thẳng
    # thành DO. Đoạn này trước đây chỉ biết đường `DO → so_id → SO`, và đòi SO
    # ở trạng thái `confirmed`. Một DO của luồng mới không có `so_id` nào, nên
    # nó dừng ở "Đơn hàng nguồn phải được xác nhận" — tức MỌI chuyến của luồng
    # mới không phát hành được hoá đơn, và lỗi chỉ hiện ra sau khi tài xế đã
    # giao hàng và POD đã ký xong.
    #
    # Với báo giá, trạng thái tương đương `confirmed` của đơn hàng là
    # `accepted` (khách đã chấp nhận) hoặc `split` (đã tách thành DO). Không
    # nhận `sent` hay `draft`: một con số khách chưa đồng ý thì chưa xuất được
    # hoá đơn.
    sales_order = db.get(SalesOrder, delivery.so_id) if delivery.so_id else None
    quotation = None
    if getattr(delivery, "quotation_id", None):
        from models import Quotation
        quotation = db.get(Quotation, delivery.quotation_id)

    TRANG_THAI_BAO_GIA_XUAT_HOA_DON = ("accepted", "split")
    if sales_order is not None and sales_order.canonical_status == "confirmed":
        nguon, ten_nguon, man_nguon = sales_order, "đơn hàng", "sales-orders"
    elif quotation is not None and quotation.canonical_status in TRANG_THAI_BAO_GIA_XUAT_HOA_DON:
        nguon, ten_nguon, man_nguon = quotation, "báo giá", "crm-sales"
    elif quotation is not None:
        raise conflict(
            "QUOTATION_NOT_ACCEPTED",
            "Báo giá nguồn %s đang ở trạng thái %s — phải được khách chấp nhận "
            "trước khi lập hóa đơn." % (quotation.quote_no or quotation.id,
                                        quotation.canonical_status),
            ["crm-sales"],
        )
    else:
        raise conflict(
            "SALES_ORDER_NOT_CONFIRMED",
            "Lệnh giao hàng %s không nối được chứng từ nguồn nào đã chốt: không có "
            "đơn hàng đã xác nhận, cũng không có báo giá đã được khách chấp nhận."
            % delivery.id,
            ["sales-orders", "crm-sales"],
        )

    if not delivery.customer_id or delivery.customer_id != nguon.customer_id:
        raise DomainError(
            "INVOICE_LINEAGE_INVALID",
            "Khách hàng trên DO không khớp với %s nguồn." % ten_nguon,
            422,
            [man_nguon, "delivery-orders"],
        )

    closeout = db.scalar(select(DeliveryOrderCloseout).where(
        DeliveryOrderCloseout.do_id == do_id,
    ))
    # Số tiền, xét theo mức cụ thể: số quyết toán > giá khoá của lệnh > số trên
    # chứng từ nguồn. Giá khoá nằm giữa vì nó là con số cho ĐÚNG chuyến này,
    # còn `selling_price` của báo giá là giá một chuyến chung của báo giá đó.
    if amount_override is not None:
        amount = _money(amount_override)
    elif closeout is not None:
        amount = _money(closeout.final_selling_price)
    else:
        amount = _money(getattr(delivery, "unit_price", 0))
        if amount <= 0:
            amount = _money(getattr(nguon, "total_amount", None)
                            if sales_order is nguon else nguon.selling_price)
    if amount <= 0:
        raise DomainError(
            "INVOICE_AMOUNT_INVALID",
            "Giá trị trên %s nguồn phải lớn hơn 0." % ten_nguon,
            422,
            [man_nguon],
        )
    # Báo giá không có cột thuế: các báo giá của luồng mới ghi rõ "giá chưa gồm
    # VAT" ở ghi chú gửi khách, và mức thuế do kế toán chốt lúc phát hành. Nên
    # ở đây là 0 chứ không phải một mức đoán.
    vat_pct = _money(getattr(nguon, "tax_rate_snapshot", None) or 0)
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
        currency_code=getattr(nguon, "currency_code", None) or "VND",
        # Ty gia: don hang giu o `exchange_rate_snapshot`, bao gia giu o
        # `fx_rate` (ty gia CHOT LUC GUI khach). Doc dung cho, neu khong thi
        # mot bao gia USD duoc ghi so voi ty gia 1.
        exchange_rate_snapshot=(getattr(nguon, "exchange_rate_snapshot", None)
                                or getattr(nguon, "fx_rate", None) or 1),
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
