import datetime as dt
import math

from models import AuditLog, Carrier, FreightOrder, Tender, TenderOffer
from services.errors import DomainError, conflict, missing_master


def _now():
    return dt.datetime.utcnow()


def _audit(db, action, table, record_id, actor):
    db.add(AuditLog(user_id=actor, action=action, table_name=table, record_id=record_id,
                    timestamp=_now(), ip_address=db.info.get("audit_ip")))


def _deadline(value):
    try:
        return value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("INVALID_DEADLINE", "Hạn phản hồi tender không hợp lệ.", 422) from None


def _amount(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise DomainError("INVALID_OFFER_AMOUNT", "Giá chào không hợp lệ.", 422) from None
    if not math.isfinite(result) or result <= 0:
        raise DomainError("INVALID_OFFER_AMOUNT", "Giá chào phải lớn hơn 0.", 422)
    return result


def create_carrier(db, data, actor="system"):
    if not data.get("id") or not str(data.get("name") or "").strip():
        raise DomainError("INVALID_CARRIER", "Cần nhập mã và tên nhà vận chuyển.", 422)
    carrier = Carrier(
        id=data["id"], name=str(data["name"]).strip(), tax_code=data.get("tax_code"),
        contact_person=data.get("contact_person"), phone=data.get("phone"), email=data.get("email"),
        status=data.get("status") or "active",
        is_internal=bool(data.get("is_internal", False)),
        created_by=actor,
    )
    db.add(carrier)
    _audit(db, "CREATE_CARRIER", "carriers", carrier.id, actor)
    db.flush()
    return carrier


def publish_tender(db, data, actor="system", now=_now):
    order = db.query(FreightOrder).filter(FreightOrder.id == data.get("freight_order_id")).with_for_update().first()
    if not order:
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy Freight Order để phát hành tender.", 404)
    if order.status != "planned":
        raise conflict("FREIGHT_ORDER_NOT_PLANNED", "Chỉ Freight Order đã lập kế hoạch mới được phát hành tender.")
    deadline = _deadline(data.get("response_deadline"))
    if deadline <= now():
        raise DomainError("INVALID_DEADLINE", "Hạn phản hồi phải ở tương lai.", 422)
    tender = Tender(
        id=data.get("id"), freight_order_id=order.id, response_deadline=deadline,
        status="published", created_by=actor, updated_by=actor,
    )
    db.add(tender)
    _audit(db, "PUBLISH_TENDER", "tenders", tender.id, actor)
    db.flush()
    return tender


def submit_offer(db, tender_id, data, actor="system", now=_now):
    tender = db.query(Tender).filter(Tender.id == tender_id).with_for_update().first()
    if not tender:
        raise DomainError("TENDER_NOT_FOUND", f"Không tìm thấy tender {tender_id}.", 404)
    if tender.status != "published":
        raise conflict("TENDER_NOT_OPEN", "Tender không còn nhận báo giá.")
    if now() > tender.response_deadline:
        tender.status = "expired"
        tender.version += 1
        raise conflict("TENDER_EXPIRED", "Tender đã hết hạn nhận báo giá.")
    carrier = db.query(Carrier).filter(Carrier.id == data.get("carrier_id")).first()
    if not carrier or carrier.status != "active":
        raise missing_master("carrier", "nhà vận chuyển đang hoạt động")
    if db.query(TenderOffer.id).filter(TenderOffer.tender_id == tender.id, TenderOffer.carrier_id == carrier.id).first():
        raise conflict("DUPLICATE_CARRIER_OFFER", "Nhà vận chuyển đã gửi báo giá cho tender này.")
    offer = TenderOffer(
        id=data.get("id"), tender_id=tender.id, carrier_id=carrier.id,
        amount=_amount(data.get("amount")), currency_code=data.get("currency_code") or "VND",
        note=data.get("note") or "", submitted_at=now(), submitted_by=actor,
    )
    db.add(offer)
    _audit(db, "SUBMIT_TENDER_OFFER", "tender_offers", offer.id, actor)
    db.flush()
    return offer


def award_offer(db, tender_id, offer_id, expected_version, actor="system"):
    tender = db.query(Tender).filter(Tender.id == tender_id).with_for_update().first()
    if not tender:
        raise DomainError("TENDER_NOT_FOUND", f"Không tìm thấy tender {tender_id}.", 404)
    if tender.status == "awarded":
        raise conflict("TENDER_ALREADY_AWARDED", "Tender đã được chọn nhà vận chuyển.")
    if tender.version != expected_version:
        raise conflict("VERSION_CONFLICT", "Tender đã thay đổi. Vui lòng tải lại dữ liệu.")
    if tender.status != "published":
        raise conflict("TENDER_NOT_OPEN", "Tender không ở trạng thái có thể award.")
    offers = db.query(TenderOffer).filter(TenderOffer.tender_id == tender.id).with_for_update().all()
    selected = next((offer for offer in offers if offer.id == offer_id), None)
    if not selected:
        raise DomainError("TENDER_OFFER_NOT_FOUND", "Không tìm thấy báo giá được chọn.", 404)
    for offer in offers:
        offer.status = "accepted" if offer.id == selected.id else "rejected"
    tender.status = "awarded"
    tender.awarded_offer_id = selected.id
    tender.awarded_carrier_id = selected.carrier_id
    tender.version += 1
    tender.updated_at = _now()
    tender.updated_by = actor
    _audit(db, "AWARD_TENDER", "tenders", tender.id, actor)
    db.flush()
    return tender
