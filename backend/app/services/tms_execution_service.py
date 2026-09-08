import datetime as dt
import hashlib
import json
import math
import os
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import (
    AuditLog,
    DeliveryOrder,
    FreightOrder,
    FreightOrderLegacyLink,
    ResourceAssignment,
    TransportEvent,
    TransportEventDocument,
    TransportTrip,
    VehicleTracking,
)
from services.errors import DomainError, conflict


MAIN_SEQUENCE = ("check_in", "pickup", "departure", "arrival", "unloading", "delivered")
EXCEPTION_TYPES = {"incident", "delay", "route_deviation"}
STATUS_AFTER = {
    "check_in": "checked_in",
    "pickup": "picked_up",
    "departure": "departed",
    "arrival": "arrived",
    "unloading": "unloading",
    "delivered": "delivered",
}
EXECUTING_STATUSES = {"dispatched", *STATUS_AFTER.values()} - {"delivered"}
EVENT_FIELDS = {"event_type", "event_time", "expected_version", "vehicle_id", "driver_id", "lat", "lng",
                "speed_kmh", "distance_km", "location_text", "source", "device_id", "eta", "reason", "note", "documents"}
STRING_LIMITS = {"event_type": 64, "source": 32, "vehicle_id": 128, "driver_id": 128,
                 "device_id": 128, "location_text": 500, "eta": 64, "reason": 2000, "note": 4000}


def freight_order_for_update(freight_order_id: str):
    return select(FreightOrder).where(FreightOrder.id == freight_order_id).with_for_update()


def _error(code, message, status_code=422):
    return DomainError(code, message, status_code)


def _event_time(value):
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        try:
            parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise _error("EVENT_TIME_INVALID", "Thời điểm sự kiện không hợp lệ.") from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def _naive_utc(value):
    """Doi mot moc thoi gian ve UTC KHONG mui gio, de so sanh duoc voi nhau.

    LOI DA XAY RA THAT. `_event_time` tra ve mot moc NAIVE (no cat `tzinfo` di),
    nhung cac cot lay tu co so du lieu — `resource_assignments.assignment_start`,
    `transport_events.event_time` — tra ve moc CO mui gio tren PostgreSQL. So
    hai loai voi nhau thi Python nem:

        TypeError: can't compare offset-naive and offset-aware datetimes

    Va vi phep so nam trong duong ghi su kien, hau qua la MOI lan ghi mot su
    kien van tai deu tra ve HTTP 500. Do duoc bang cach bam that: nut "ghi nhan
    xe da den noi" tra ve "Internal Server Error", khong mot loi nghiep vu nao.

    Quy uoc cua tep nay la NAIVE UTC (`_event_time` da chon vay), nen ham nay
    keo moi thu ve dung quy uoc do thay vi doi nguoc lai — doi nguoc thi phai
    sua ca cot va ca cac ban ghi da co.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def _chuyen_cua_lenh(db, freight_order_id):
    """Chuyen dang thuc hien lenh van chuyen nay, hoac `None`.

    VI SAO CAN. Cot `transport_events.trip_id` co san va cac man hinh doc su kien
    THEO CHUYEN — thap kiem soat gom su kien bang `TransportEvent.trip_id.in_(...)`.
    Truoc day duong ghi su kien khong dien cot nay, nen moi moc ghi qua API deu co
    `trip_id` rong: don doi trang thai dung, nhung truc tien do cua man theo doi
    khong thay moc vua ghi va cu bao no "chua ghi". Do la mot moc bi mo côi — no
    thuoc mot chuyen that ma khong noi ra la chuyen nao.

    Chon chuyen nao: mot lenh co the co nhieu chuyen (chay lai, doi xe), nen bo
    chuyen `cancelled` va lay chuyen MOI NHAT trong so con lai. Khong tim thay thi
    tra `None` — su kien van ghi duoc, vi rang buoc cua cot la co the rong.
    """
    return db.scalar(select(TransportTrip).where(
        TransportTrip.freight_order_id == freight_order_id,
        TransportTrip.status != "cancelled",
    ).order_by(TransportTrip.created_at.desc(), TransportTrip.id.desc()))


def _validate_payload_shape(data):
    if not isinstance(data, dict) or set(data) - EVENT_FIELDS:
        raise _error("EVENT_PAYLOAD_INVALID", "Dữ liệu sự kiện không hợp lệ.")
    for field, limit in STRING_LIMITS.items():
        value = data.get(field)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            raise _error("EVENT_PAYLOAD_INVALID", "Dữ liệu sự kiện không hợp lệ.")
    eta = data.get("eta")
    if eta:
        try:
            dt.datetime.fromisoformat(eta.replace("Z", "+00:00"))
        except ValueError:
            raise _error("EVENT_PAYLOAD_INVALID", "Dữ liệu sự kiện không hợp lệ.") from None


def _validate_values(data):
    for name, low, high in (("lat", -90, 90), ("lng", -180, 180)):
        value = data.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < low or value > high):
            raise _error("COORDINATE_INVALID", "Tọa độ không hợp lệ.")
    for name in ("speed_kmh", "distance_km"):
        value = data.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise _error("GPS_VALUE_INVALID", "Tốc độ hoặc quãng đường không hợp lệ.")
    source = data.get("source")
    if source not in {"device", "manual"}:
        raise _error("EVENT_SOURCE_INVALID", "Nguồn sự kiện không hợp lệ.")
    if source == "device" and not str(data.get("device_id") or "").strip():
        raise _error("DEVICE_ID_REQUIRED", "Sự kiện từ thiết bị phải có mã thiết bị.")


def _validate_documents(event_type, documents):
    if not isinstance(documents, list) or len(documents) > 10:
        raise _error("EVENT_DOCUMENT_INVALID", "Thông tin chứng từ sự kiện không hợp lệ.")
    for item in documents:
        if isinstance(item, dict) and (
            set(item) - {"document_type", "storage_url", "file_name", "mime_type", "checksum"}
            or any(not isinstance(item.get(field), str) or len(item.get(field)) > limit
                   for field, limit in {"document_type": 64, "storage_url": 2048, "file_name": 255,
                                        "mime_type": 128, "checksum": 128}.items()
                   if item.get(field) is not None)
        ):
            raise _error("EVENT_DOCUMENT_INVALID", "Thông tin chứng từ sự kiện không hợp lệ.")
        if not isinstance(item, dict) or not all(
            str(item.get(field) or "").strip()
            for field in ("document_type", "storage_url", "checksum")
        ):
            if event_type == "delivered" and isinstance(item, dict) and item.get("document_type") == "pod":
                raise _error("POD_DOCUMENT_REQUIRED", "Sự kiện giao hàng phải có chứng từ POD hợp lệ.")
            raise _error("EVENT_DOCUMENT_INVALID", "Thông tin chứng từ sự kiện không hợp lệ.")
    if event_type != "delivered":
        return
    pod = next((item for item in documents if item.get("document_type") == "pod"), None)
    if not pod or not str(pod.get("storage_url") or "").strip() or not str(pod.get("checksum") or "").strip():
        raise _error("POD_DOCUMENT_REQUIRED", "Sự kiện giao hàng phải có chứng từ POD hợp lệ.")


def _dong_bo_moc_do(db, order, event_type, actor):
    """Đưa mốc hành trình của chuyến hàng sang trạng thái của DO.

    Hệ thống có hai lớp trạng thái chạy song song: chuyến hàng đi qua sáu
    mốc (`check_in` … `delivered`), còn DO chỉ có ba. Sự kiện `arrival` chỉ
    đổi lớp chuyến hàng, nên DO vẫn là `in_transit` và màn hình không phân
    biệt được xe còn trên đường hay đã tới bãi chờ bốc dỡ.

    Đây là đường "GPS tự báo": thiết bị gửi `arrival`, DO tự sang
    `arrived`. Người điều hành vẫn bấm tay được qua
    `PUT /api/delivery-orders/{id}/status` khi GPS mất tín hiệu.

    Chỉ đồng bộ mốc `arrival`. `delivered` KHÔNG đồng bộ ở đây: hoàn tất
    giao còn đòi POD, ảnh ký nhận và chốt giá trong cùng một giao dịch —
    đó là việc của `complete_delivery`, không phải của một sự kiện GPS.
    """
    if event_type != "arrival":
        return
    # DO nối với chuyến hàng qua bảng riêng `freight_order_legacy_links`,
    # không phải một cột trên `freight_orders`.
    ma_do = db.scalar(select(FreightOrderLegacyLink.delivery_order_id).where(
        FreightOrderLegacyLink.freight_order_id == order.id))
    if not ma_do:
        return
    delivery = db.get(DeliveryOrder, ma_do)
    if delivery is None or delivery.canonical_status != "in_transit":
        return
    delivery.canonical_status = "arrived"
    delivery.status = "Đã đến nơi — chờ POD"
    delivery.updated_by = actor
    delivery.version = (delivery.version or 1) + 1

def record_event(db, freight_order_id: str, data: dict, idempotency_key: str, actor: str) -> TransportEvent:
    if not str(idempotency_key or "").strip():
        raise _error("IDEMPOTENCY_KEY_REQUIRED", "Khóa idempotency là bắt buộc.")
    if not isinstance(idempotency_key, str) or len(idempotency_key) > 128:
        raise _error("IDEMPOTENCY_KEY_INVALID", "Khóa idempotency không hợp lệ.")
    _validate_payload_shape(data)
    event_type = data.get("event_type")
    if event_type not in set(MAIN_SEQUENCE) | EXCEPTION_TYPES:
        raise _error("EVENT_TYPE_INVALID", "Loại sự kiện vận tải không hợp lệ.")
    if not actor or not str(actor).strip():
        raise _error("ACTOR_REQUIRED", "Không xác định được người thực hiện.")
    expected_version = data.get("expected_version")
    if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version <= 0:
        raise _error("EXPECTED_VERSION_INVALID", "Phiên bản dự kiến phải là số nguyên dương.")
    canonical = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False, separators=(",", ":"))
    payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    existing = db.scalar(select(TransportEvent).where(
        TransportEvent.freight_order_id == freight_order_id,
        TransportEvent.idempotency_key == idempotency_key,
    ))
    if existing is not None:
        if existing.payload_hash == payload_hash:
            return existing
        raise conflict("IDEMPOTENCY_KEY_REUSED", "Khóa idempotency đã được sử dụng với nội dung khác.")
    _validate_values(data)
    documents = data.get("documents")
    if documents is None:
        documents = []
    _validate_documents(event_type, documents)
    event_time = _event_time(data.get("event_time"))
    try:
        tolerance = int(os.getenv("TMS_EVENT_FUTURE_TOLERANCE_SECONDS", "300"))
        if tolerance < 0:
            tolerance = 300
    except (TypeError, ValueError):
        tolerance = 300
    if event_time > dt.datetime.utcnow() + dt.timedelta(seconds=tolerance):
        raise _error("EVENT_TIME_FUTURE", "Thời điểm sự kiện vượt quá ngưỡng tương lai cho phép.")

    if db.get_bind().dialect.name == "sqlite":
        connection = db.connection()
        driver_connection = connection.connection.driver_connection
        if not driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")

    order = db.execute(freight_order_for_update(freight_order_id)).scalar_one_or_none()
    if order is None:
        raise _error("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy lệnh vận chuyển.", 404)
    existing = db.scalar(select(TransportEvent).where(
        TransportEvent.freight_order_id == freight_order_id,
        TransportEvent.idempotency_key == idempotency_key,
    ))
    if existing is not None:
        if existing.payload_hash == payload_hash:
            return existing
        raise conflict("IDEMPOTENCY_KEY_REUSED", "Khóa idempotency đã được sử dụng với nội dung khác.")
    if order.version != expected_version:
        raise conflict("VERSION_CONFLICT", "Phiên bản lệnh vận chuyển đã thay đổi.")

    assignment = db.scalar(select(ResourceAssignment).where(
        ResourceAssignment.freight_order_id == freight_order_id,
        ResourceAssignment.status == "active",
    ))
    if assignment is None:
        raise _error("ACTIVE_ASSIGNMENT_REQUIRED", "Lệnh vận chuyển chưa có phân công đang hoạt động.")
    # `_naive_utc` o ca hai ben: mot ben naive, mot ben co mui gio thi Python nem
    # TypeError va ca duong ghi su kien tra ve 500.
    if (event_time < _naive_utc(assignment.assignment_start)
            or event_time > _naive_utc(assignment.assignment_end)):
        raise _error("ASSIGNMENT_TIME_INVALID", "Thời điểm sự kiện nằm ngoài thời gian phân công.")
    if data.get("vehicle_id") not in (None, assignment.vehicle_id) or data.get("driver_id") not in (None, assignment.driver_id):
        raise _error("ASSIGNMENT_MISMATCH", "Phương tiện hoặc tài xế không khớp phân công đang hoạt động.")

    main_events = db.scalars(select(TransportEvent).where(
        TransportEvent.freight_order_id == freight_order_id,
        TransportEvent.event_type.in_(MAIN_SEQUENCE),
    ).order_by(TransportEvent.event_time, TransportEvent.recorded_at, TransportEvent.id)).all()
    if main_events and event_time < _naive_utc(main_events[-1].event_time):
        raise _error("EVENT_TIME_REGRESSION", "Thời điểm sự kiện không được lùi trước sự kiện chính gần nhất.")
    if event_type in MAIN_SEQUENCE:
        if any(item.event_type == event_type for item in main_events):
            raise conflict("EVENT_ALREADY_RECORDED", "Sự kiện chính đã được ghi nhận.")
        expected_index = len(main_events)
        expected_status = "dispatched" if not main_events else STATUS_AFTER[main_events[-1].event_type]
        if expected_index >= len(MAIN_SEQUENCE) or MAIN_SEQUENCE[expected_index] != event_type or order.status != expected_status:
            raise conflict("EVENT_SEQUENCE_INVALID", "Thứ tự sự kiện vận tải không hợp lệ.")
    else:
        if order.status not in EXECUTING_STATUSES:
            raise _error("FREIGHT_ORDER_NOT_EXECUTING", "Lệnh vận chuyển không ở trạng thái đang thực thi.")
        if not str(data.get("reason") or "").strip():
            raise _error("EVENT_REASON_REQUIRED", "Sự kiện ngoại lệ phải có lý do.")

    chuyen = _chuyen_cua_lenh(db, freight_order_id)
    event = TransportEvent(
        id=str(uuid.uuid4()), freight_order_id=freight_order_id, event_type=event_type,
        trip_id=chuyen.id if chuyen is not None else None,
        event_time=event_time, lat=data.get("lat"), lng=data.get("lng"),
        speed_kmh=data.get("speed_kmh"), distance_km=data.get("distance_km"), eta=data.get("eta"),
        location_text=data.get("location_text"), source=data.get("source"),
        device_id=data.get("device_id"), reason=data.get("reason"), note=data.get("note"),
        idempotency_key=idempotency_key, payload_hash=payload_hash,
        recorded_by=actor,
    )
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(TransportEvent).where(
            TransportEvent.freight_order_id == freight_order_id,
            TransportEvent.idempotency_key == idempotency_key,
        ))
        if existing is not None and existing.payload_hash == payload_hash:
            return existing
        if existing is not None:
            raise conflict("IDEMPOTENCY_KEY_REUSED", "Khóa idempotency đã được sử dụng với nội dung khác.") from None
        raise conflict("IDEMPOTENCY_CONFLICT", "Không thể ghi nhận sự kiện do xung đột dữ liệu.") from None
    for item in documents:
        db.add(TransportEventDocument(
            event_id=event.id, document_type=item.get("document_type"),
            storage_url=item.get("storage_url"), file_name=item.get("file_name"),
            mime_type=item.get("mime_type"), checksum=item.get("checksum"), uploaded_by=actor,
        ))
    if event_type in MAIN_SEQUENCE:
        order.status = STATUS_AFTER[event_type]
        _dong_bo_moc_do(db, order, event_type, actor)
        order.version += 1
        order.updated_at = dt.datetime.utcnow()
        order.updated_by = actor
    db.add(AuditLog(
        user_id=actor, action="RECORD_TRANSPORT_EVENT", table_name="transport_events",
        record_id=event.id, ip_address=db.info.get("audit_ip"),
    ))
    db.flush()
    _project_legacy(db, event, assignment, documents)
    db.flush()
    return event


def _project_legacy(db, event, assignment, documents):
    link = db.get(FreightOrderLegacyLink, event.freight_order_id)
    if link is None:
        return
    if event.lat is not None and event.lng is not None:
        latest = db.scalar(select(TransportEvent).where(
            TransportEvent.freight_order_id == event.freight_order_id,
            TransportEvent.lat.is_not(None), TransportEvent.lng.is_not(None),
        ).order_by(TransportEvent.event_time.desc(), TransportEvent.recorded_at.desc(), TransportEvent.id.desc()))
        if latest is not None and latest.id == event.id:
            tracking = db.get(VehicleTracking, link.delivery_order_id)
            if tracking is None:
                tracking = VehicleTracking(do_id=link.delivery_order_id)
                db.add(tracking)
            tracking.vehicle_id = assignment.vehicle_id
            tracking.lat, tracking.lng = event.lat, event.lng
            tracking.speed_kmh = event.speed_kmh
            tracking.remaining_distance_km = event.distance_km
            tracking.eta = event.eta
            tracking.last_update = event.event_time


def list_events(db, freight_order_id: str) -> list[TransportEvent]:
    return list(db.scalars(select(TransportEvent).where(
        TransportEvent.freight_order_id == freight_order_id
    ).order_by(TransportEvent.event_time, TransportEvent.recorded_at, TransportEvent.id)).all())


def latest_position(db, freight_order_id: str) -> TransportEvent:
    event = db.scalar(select(TransportEvent).where(
        TransportEvent.freight_order_id == freight_order_id,
        TransportEvent.lat.is_not(None), TransportEvent.lng.is_not(None),
    ).order_by(TransportEvent.event_time.desc(), TransportEvent.recorded_at.desc(), TransportEvent.id.desc()))
    if event is None:
        raise _error("POSITION_NOT_FOUND", "Chưa có vị trí cho lệnh vận chuyển.", 404)
    return event


def link_legacy_delivery_order(db, freight_order_id: str, delivery_order_id: str, actor: str) -> FreightOrderLegacyLink:
    if not actor or not str(actor).strip():
        raise _error("ACTOR_REQUIRED", "Không xác định được người thực hiện.")
    link = FreightOrderLegacyLink(freight_order_id=freight_order_id, delivery_order_id=delivery_order_id)
    db.add(link)
    db.flush()
    db.add(AuditLog(
        user_id=actor, action="LINK_LEGACY_DELIVERY_ORDER", table_name="freight_order_legacy_links",
        record_id=freight_order_id, ip_address=db.info.get("audit_ip"),
    ))
    db.flush()
    return link
