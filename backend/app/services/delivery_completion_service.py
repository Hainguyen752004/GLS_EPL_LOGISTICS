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
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
)
from services.errors import DomainError, conflict
from services.workflow_service import release_resources
from services import parking_list_service


MONEY_QUANTUM = Decimal("0.000001")
MAX_POD_BYTES = 10 * 1024 * 1024
ALLOWED_POD_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
ALLOWED_SIGNATURE_MIME_TYPES = {"image/png"}


def _costindex_theo_ten(db, trip_id, ten):
    """Ma costindex cho mot khoan khach tra them, suy tu cong thuc cua xe chay chuyen.

    Khoan khach tra them duoc nhap bang TEN ("Phi cau duong"), khong co khoa.
    Tra "" khi khong suy duoc — ho so hoan tat se noi "chua gan ma" thay vi bia.
    """
    from models import TransportTrip
    from services.khoan_muc_chi_phi import bang_costindex_cua_xe, costindex_cho

    trip = db.get(TransportTrip, trip_id) if trip_id else None
    if trip is None or not trip.vehicle_id:
        return ""
    return costindex_cho(bang_costindex_cua_xe(db, trip.vehicle_id), ten=ten) or ""


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


def _serialize(closeout, adjustments, pod_records, documents):
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
    # `arrived` CŨNG được hoàn tất — đó chính là trạng thái "xe đã tới, chờ POD",
    # tức bước ngay TRƯỚC hoàn tất. Bản trước chỉ nhận `in_transit`, và sau khi
    # mốc `arrival` bắt đầu tự đưa DO sang `arrived` (đồng bộ qua
    # `trip_delivery_orders`) thì MỌI chuyến báo tới nơi đều bị 409 ở bước POD —
    # đo được khi gieo demo: 5/5 case xong vỡ với "Chỉ DO đang vận chuyển mới
    # được hoàn tất giao". Chuyến không báo mốc tới nơi vẫn đi thẳng
    # `in_transit -> delivered` như cũ.
    if delivery.canonical_status not in ("in_transit", "arrived"):
        raise conflict("DELIVERY_ORDER_NOT_IN_TRANSIT",
                       "Chỉ DO đang vận chuyển hoặc đã đến nơi mới được hoàn tất giao.")

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
    # Thứ tự dưới đây theo mức cụ thể, cao nhất trước:
    #
    #   1. `delivery_orders.unit_price` — giá đã khoá cho ĐÚNG chuyến này. Nó cụ
    #      thể hơn cả báo giá, vì một báo giá tách ra nhiều DO và giá khoá là
    #      con số vận hành không sửa được ở dưới.
    #   2. Báo giá mà DO trỏ tới (`quotation_id`). Không còn đường nào khác:
    #      bước Đơn hàng (SO) đã trục xuất ở migration 049.
    quotation = None
    if getattr(delivery, "quotation_id", None):
        quotation = db.get(Quotation, delivery.quotation_id)

    base_price = _money(getattr(delivery, "unit_price", 0))
    source = "delivery_order"
    source_id = delivery.id if base_price > 0 else None
    if base_price <= 0 and quotation is not None:
        base_price = _money(quotation.selling_price)
        source = "quotation"
        source_id = quotation.id
    if base_price <= 0 or not source_id:
        raise DomainError(
            "BASE_PRICE_MISSING",
            "Lệnh giao hàng %s chưa có giá: không có giá khoá trên lệnh và không nối "
            "được báo giá. Không có giá thì không "
            "quyết toán và không phát hành hoá đơn được." % delivery.id,
            422)

    # ĐỒNG TIỀN lấy theo nguồn giá đang dùng (DO hoặc báo giá), không mặc định
    # "VND": một báo giá bằng USD sẽ lặng lẽ bị quyết toán như tiền đồng.
    source_currency = "VND"
    ma_tien = getattr(quotation, "currency_code", None) if quotation is not None else None
    if ma_tien:
        source_currency = str(ma_tien).upper()
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
            # Ma costindex: man gui thi lay, khong thi suy tu cong thuc gia thanh
            # cua xe chay chuyen theo ten khoan muc — de dong THU nao cung co ma
            # cho he cong no, khong phu thuoc giao dien co nho gui hay khong.
            cost_index=(item.cost_index or "").strip() or _costindex_theo_ten(db, payload.trip_id, item.name),
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

    # KHONG lap hoa don AR o day nua (module ke toan da xoa 10/09): hoa don la viec
    # cua he cong no dong nghiep, doc tu GET /api/handover/delivery-orders/{do_id}.
    response = _serialize(closeout, adjustments, pod_rows, document_rows)
    db.add(IdempotencyRecord(
        actor=actor, method="POST", path=path, idempotency_key=idempotency_key,
        operation="complete_delivery", request_hash=payload_hash,
        response_json=json.dumps(response, ensure_ascii=False),
    ))
    db.flush()
    return response
