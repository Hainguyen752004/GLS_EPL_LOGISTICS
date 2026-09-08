import datetime as dt
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select

from models import (
    DeliveryOrder,
    DeliveryOrderChargeAdjustment,
    DeliveryOrderCloseout,
    DeliveryPODDocument,
    DeliveryPODRecord,
    FreightOrder,
    IdempotencyRecord,
    Quotation,
    ResourceAssignment,
    SalesOrder,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
)
from services.ar_invoice_service import post_ar_invoice, serialize_ar_invoice
from services.errors import DomainError, conflict
from services.workflow_service import release_resources
from services import parking_list_service


MONEY_QUANTUM = Decimal("0.000001")
MAX_POD_BYTES = 10 * 1024 * 1024
ALLOWED_POD_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
ALLOWED_SIGNATURE_MIME_TYPES = {"image/png"}


def _money(value):
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _utc_naive(value):
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def request_hash(payload, files):
    normalized = payload.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8"))
    for field_name in sorted(files):
        item = files[field_name]
        digest.update(field_name.encode("utf-8"))
        digest.update(hashlib.sha256(item["content"]).digest())
    return digest.hexdigest()


def _serialize(closeout, adjustments, pod_records, documents, invoice):
    docs_by_pod = {}
    for document in documents:
        docs_by_pod.setdefault(document.pod_record_id, []).append({
            "id": document.id,
            "file_name": document.file_name,
            "mime_type": document.mime_type,
            "file_size": document.file_size,
            "checksum": document.checksum,
            "download_url": f"/api/pod-documents/{document.id}",
        })
    return {
        "do_id": closeout.do_id,
        "status": "delivered",
        "commercials": {
            "base_selling_price": float(closeout.base_selling_price_snapshot),
            "base_price_source": closeout.base_price_source,
            "base_price_source_id": closeout.base_price_source_id,
            "customer_surcharge_total": float(closeout.surcharge_total),
            "final_selling_price": float(closeout.final_selling_price),
            "currency_code": closeout.currency_code,
        },
        "customer_charge_adjustments": [{
            "id": row.id,
            "line_no": row.line_no,
            "name": row.name,
            "original_amount": float(row.original_amount),
            "actual_amount": float(row.actual_amount),
            "increase_amount": float(row.increase_amount),
            "note": row.note,
        } for row in adjustments],
        "pod_records": [{
            "id": row.id,
            "leg_id": row.leg_id,
            "stop_no": row.stop_no,
            "receiver_name": row.receiver_name,
            "receiver_phone": row.receiver_phone,
            "delivery_time": row.delivery_time.isoformat() if row.delivery_time else None,
            "delivery_result": row.delivery_result,
            "cargo_condition": row.cargo_condition,
            "documents": docs_by_pod.get(row.id, []),
        } for row in pod_records],
        "invoice": serialize_ar_invoice(invoice),
    }


def complete_delivery(db, do_id, payload, files, idempotency_key, actor, path):
    if not idempotency_key:
        raise DomainError("IDEMPOTENCY_KEY_REQUIRED", "Thiếu Idempotency-Key.", 422)
    if len(idempotency_key) > 96:
        raise DomainError("IDEMPOTENCY_KEY_INVALID", "Idempotency-Key quá dài.", 422)
    payload_hash = request_hash(payload, files)
    existing_key = db.scalar(select(IdempotencyRecord).where(
        IdempotencyRecord.actor == actor,
        IdempotencyRecord.method == "POST",
        IdempotencyRecord.path == path,
        IdempotencyRecord.idempotency_key == idempotency_key,
    ).with_for_update())
    if existing_key:
        if existing_key.request_hash != payload_hash:
            raise conflict("IDEMPOTENCY_CONFLICT", "Idempotency-Key đã dùng với nội dung khác.")
        return json.loads(existing_key.response_json)

    delivery = db.scalar(select(DeliveryOrder).where(DeliveryOrder.id == do_id).with_for_update())
    if not delivery:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy DO {do_id}.", 404)
    if delivery.canonical_status != "in_transit":
        raise conflict("DELIVERY_ORDER_NOT_IN_TRANSIT", "Chỉ DO đang vận chuyển mới được hoàn tất giao.")

    trip = db.scalar(select(TransportTrip).where(TransportTrip.id == payload.trip_id).with_for_update())
    membership = db.get(TripDeliveryOrder, (payload.trip_id, do_id))
    if not trip or not membership:
        raise DomainError("POD_LINEAGE_INVALID", "Trip không thuộc DO đã chọn.", 422)
    if trip.status not in ("dispatched", "in_transit"):
        raise conflict("TRIP_NOT_IN_TRANSIT", "Trip chưa ở trạng thái giao hàng.")

    # GIÁ GỐC CỦA MỘT DO — ba nguồn, xét theo thứ tự thẩm quyền.
    #
    # LUỒNG MỚI KHÔNG CÓ ĐƠN HÀNG (SO). Báo giá được khách chấp nhận thì tách
    # thẳng thành DO, và giá được KHOÁ ngay trên từng DO (`unit_price`) — đó
    # chính là lý do bước SO bị bỏ.
    #
    # Trước đây đoạn này chỉ đi một đường: DO → `so_id` → SO → báo giá. Một DO
    # sinh từ báo giá không có `so_id`, nên nó dừng ở "DO chưa có giá SO/Báo giá
    # hợp lệ" — nghĩa là MỌI chuyến của luồng mới không hoàn tất giao được, và
    # lỗi hiện ra ở bước cuối cùng, sau khi tài xế đã giao hàng xong.
    #
    # Thứ tự dưới đây theo mức cụ thể, cao nhất trước:
    #
    #   1. `delivery_orders.unit_price` — giá đã khoá cho ĐÚNG chuyến này. Nó cụ
    #      thể hơn cả báo giá, vì một báo giá tách ra nhiều DO và giá khoá là
    #      con số vận hành không sửa được ở dưới.
    #   2. Báo giá mà DO trỏ tới (`quotation_id`).
    #   3. Đường cũ: SO, rồi báo giá của SO. Giữ nguyên cho những DO tạo trước
    #      khi bỏ bước SO — chúng vẫn phải quyết toán được.
    sales_order = db.get(SalesOrder, delivery.so_id) if delivery.so_id else None
    quotation = None
    if getattr(delivery, "quotation_id", None):
        quotation = db.get(Quotation, delivery.quotation_id)
    if quotation is None and sales_order is not None and sales_order.quotation_id:
        quotation = db.get(Quotation, sales_order.quotation_id)

    base_price = _money(getattr(delivery, "unit_price", 0))
    source = "delivery_order"
    source_id = delivery.id if base_price > 0 else None
    if base_price <= 0 and quotation is not None:
        base_price = _money(quotation.selling_price)
        source = "quotation"
        source_id = quotation.id
    if base_price <= 0 and sales_order is not None:
        base_price = _money(sales_order.total_amount)
        source = "sales_order"
        source_id = sales_order.id
    if base_price <= 0 or not source_id:
        raise DomainError(
            "BASE_PRICE_MISSING",
            "Lệnh giao hàng %s chưa có giá: không có giá khoá trên lệnh, không nối "
            "được báo giá, và cũng không có đơn hàng. Không có giá thì không "
            "quyết toán và không phát hành hoá đơn được." % delivery.id,
            422)

    # ĐỒNG TIỀN lấy theo nguồn giá đang dùng, không lấy cứng từ SO: một DO của
    # luồng mới không có SO, nên đọc từ SO sẽ luôn ra "VND" — và một báo giá
    # bằng USD sẽ lặng lẽ được quyết toán như tiền đồng.
    source_currency = "VND"
    for nguoi_giu in (quotation if source in ("delivery_order", "quotation") else None,
                      sales_order):
        ma_tien = getattr(nguoi_giu, "currency_code", None) if nguoi_giu is not None else None
        if ma_tien:
            source_currency = str(ma_tien).upper()
            break
    if payload.currency_code != source_currency:
        raise DomainError(
            "CURRENCY_MISMATCH",
            "Đơn vị tiền phải khớp với nguồn giá (%s là %s)."
            % (source_id, source_currency), 422)

    delivery_legs = db.scalars(select(TransportTripLeg).where(
        TransportTripLeg.trip_id == trip.id,
        TransportTripLeg.do_id == do_id,
        TransportTripLeg.leg_type == "delivery",
    ).with_for_update()).all()
    leg_map = {leg.id: leg for leg in delivery_legs}
    if set(leg_map) != {entry.leg_id for entry in payload.pod_entries}:
        raise DomainError("POD_LINEAGE_INVALID", "Phải nộp POD cho đúng tất cả chặng giao của DO.", 422)

    pod_rows = []
    document_rows = []
    for entry in payload.pod_entries:
        leg = leg_map[entry.leg_id]
        if trip.vehicle_id and entry.vehicle_id != trip.vehicle_id:
            raise DomainError("POD_LINEAGE_INVALID", "Xe trên POD không khớp xe đã điều.", 422)
        uploaded = files.get(entry.file_field)
        signature = files.get(entry.signature_file_field)
        if not uploaded or not uploaded.get("content"):
            raise DomainError("POD_FILE_REQUIRED", f"Thiếu file POD cho chặng {entry.leg_id}.", 422)
        content = uploaded["content"]
        if len(content) > MAX_POD_BYTES:
            raise DomainError("POD_FILE_TOO_LARGE", "File POD tối đa 10 MB.", 422)
        mime_type = uploaded.get("mime_type") or "application/octet-stream"
        if mime_type not in ALLOWED_POD_MIME_TYPES:
            raise DomainError("POD_FILE_TYPE_INVALID", "POD chỉ hỗ trợ JPG, PNG hoặc PDF.", 422)
        if not signature or not signature.get("content"):
            raise DomainError(
                "POD_SIGNATURE_REQUIRED",
                f"Thiếu chữ ký người nhận cho chặng {entry.leg_id}.",
                422,
            )
        signature_content = signature["content"]
        if len(signature_content) > MAX_POD_BYTES:
            raise DomainError("POD_SIGNATURE_TOO_LARGE", "Ảnh chữ ký tối đa 10 MB.", 422)
        signature_mime_type = signature.get("mime_type") or "application/octet-stream"
        if signature_mime_type not in ALLOWED_SIGNATURE_MIME_TYPES:
            raise DomainError(
                "POD_SIGNATURE_TYPE_INVALID",
                "Chữ ký phải được gửi dưới dạng ảnh PNG.",
                422,
            )
        pod = DeliveryPODRecord(
            idempotency_key=f"{idempotency_key}:{entry.leg_id}", do_id=do_id,
            trip_id=trip.id, leg_id=leg.id, vehicle_id=entry.vehicle_id,
            driver_id=trip.driver_id, stop_no=entry.stop_no,
            location_text=entry.location_text, receiver_name=entry.receiver_name,
            receiver_phone=entry.receiver_phone, delivery_time=_utc_naive(entry.delivery_time),
            delivery_result=entry.delivery_result, cargo_condition=entry.cargo_condition,
            note=entry.note, status="completed", created_by=actor,
        )
        db.add(pod)
        db.flush()
        # ẢNH POD VÀ ẢNH CHỮ KÝ KHÔNG ĐƯỢC LÀ CÙNG MỘT TỆP.
        #
        # Bảng `delivery_pod_documents` có ràng buộc duy nhất trên
        # `(pod_record_id, checksum)`, nên hai tệp giống nhau từng byte làm cơ
        # sở dữ liệu nổ ra `IntegrityError` — và người dùng nhận về "Internal
        # Server Error 500" cho một việc họ tự sửa được trong ba giây: chọn lại
        # đúng ảnh chữ ký.
        #
        # Kiểm ở đây chứ không dựa vào ràng buộc: một lỗi 500 không nói được
        # điều gì, và nó xảy ra SAU KHI tài xế đã giao hàng xong — thời điểm tệ
        # nhất để người dùng gặp một thông báo không hiểu được.
        if hashlib.sha256(content).hexdigest() == hashlib.sha256(signature_content).hexdigest():
            raise DomainError(
                "POD_SIGNATURE_SAME_AS_FILE",
                "Ảnh POD và ảnh chữ ký của chặng %s đang là cùng một tệp. Hãy chọn "
                "ảnh chữ ký người nhận riêng." % entry.leg_id,
                422)
        documents = [
            DeliveryPODDocument(
                id=f"PODDOC-{uuid4().hex}", pod_record_id=pod.id,
                file_name=uploaded.get("file_name") or entry.file_field,
                mime_type=mime_type, file_size=len(content),
                checksum=hashlib.sha256(content).hexdigest(), content=content, created_by=actor,
            ),
            DeliveryPODDocument(
                id=f"PODDOC-{uuid4().hex}", pod_record_id=pod.id,
                file_name=signature.get("file_name") or f"signature-{entry.leg_id}.png",
                mime_type=signature_mime_type, file_size=len(signature_content),
                checksum=hashlib.sha256(signature_content).hexdigest(),
                content=signature_content, created_by=actor,
            ),
        ]
        db.add_all(documents)
        pod_rows.append(pod)
        document_rows.extend(documents)
        leg.status = "completed"
        leg.actual_arrival_at = _utc_naive(entry.delivery_time)

    surcharge_total = sum((row.increase_amount for row in payload.charge_adjustments), Decimal("0"))
    surcharge_total = _money(surcharge_total)
    final_price = _money(base_price + surcharge_total)
    completed_at = max(entry.delivery_time for entry in payload.pod_entries)
    closeout = DeliveryOrderCloseout(
        id=f"CLOSEOUT-{uuid4().hex}", do_id=do_id,
        base_selling_price_snapshot=base_price, base_price_source=source,
        base_price_source_id=source_id, surcharge_total=surcharge_total,
        final_selling_price=final_price, currency_code=payload.currency_code,
        completed_at=completed_at, completed_by=actor,
    )
    db.add(closeout)
    db.flush()
    adjustments = []
    for line_no, item in enumerate(payload.charge_adjustments, 1):
        row = DeliveryOrderChargeAdjustment(
            id=f"DOCHG-{uuid4().hex}", closeout_id=closeout.id, line_no=line_no,
            name=item.name, original_amount=_money(item.original_amount),
            actual_amount=_money(item.actual_amount), increase_amount=_money(item.increase_amount),
            note=item.note, created_by=actor,
        )
        db.add(row)
        adjustments.append(row)

    delivery.canonical_status = "delivered"
    delivery.status = "Đã hoàn tất"
    delivery.delivery_date = completed_at
    delivery.updated_at = completed_at
    delivery.updated_by = actor
    delivery.version += 1
    db.flush()
    parking_list_service.sync_do_status(
        db,
        do_id,
        "delivered",
        actor,
        note=f"Dong bo tu POD Trip {trip.id}",
    )
    open_delivery_leg = db.scalar(select(TransportTripLeg.id).where(
        TransportTripLeg.do_id == do_id,
        TransportTripLeg.leg_type == "delivery",
        TransportTripLeg.status.notin_(("completed", "cancelled")),
    ).limit(1))
    if open_delivery_leg:
        raise conflict(
            "TRIP_HAS_OPEN_DELIVERIES",
            "DO còn chặng giao hàng trên Trip khác, chưa thể chốt giá.",
        )
    open_legs = db.scalar(select(TransportTripLeg.id).where(
        TransportTripLeg.trip_id == trip.id,
        TransportTripLeg.status.notin_(("completed", "cancelled")),
    ).limit(1))
    linked_open_do = db.scalar(select(DeliveryOrder.id).join(
        TripDeliveryOrder, TripDeliveryOrder.do_id == DeliveryOrder.id,
    ).where(
        TripDeliveryOrder.trip_id == trip.id,
        DeliveryOrder.canonical_status.notin_(("delivered", "cancelled")),
    ).limit(1))
    if not open_legs and not linked_open_do:
        trip.status = "completed"
        trip.actual_arrival_at = completed_at
        trip.version += 1
        trip.updated_at = completed_at
        trip.updated_by = actor
        freight_order = db.get(FreightOrder, trip.freight_order_id)
        if freight_order:
            freight_order.status = "delivered"
            freight_order.version += 1
            freight_order.updated_at = completed_at
            freight_order.updated_by = actor
        assignments = db.scalars(select(ResourceAssignment).where(
            ResourceAssignment.trip_id == trip.id,
            ResourceAssignment.status == "active",
        ).with_for_update()).all()
        for assignment in assignments:
            assignment.status = "completed"
        release_resources(db, delivery)

    invoice = post_ar_invoice(db, {
        "do_id": do_id, "posted_at": completed_at, "amount_override": final_price,
    }, actor)
    db.flush()
    response = _serialize(closeout, adjustments, pod_rows, document_rows, invoice)
    db.add(IdempotencyRecord(
        actor=actor, method="POST", path=path, idempotency_key=idempotency_key,
        operation="complete_delivery", request_hash=payload_hash,
        response_json=json.dumps(response, ensure_ascii=False),
    ))
    db.flush()
    return response
