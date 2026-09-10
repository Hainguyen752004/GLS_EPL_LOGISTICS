import datetime as dt
import json
from decimal import Decimal, InvalidOperation

from models import (
    AuditLog,
    DeliveryOrder,
    FreightOrder,
    Location,
    ResourceAssignment,
    Route,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
)
from services.errors import DomainError, conflict


TRIP_TYPES = {"one_way", "round_trip", "backhaul", "multi_stop"}
LEG_TYPES = {"outbound", "pickup", "delivery", "empty_return", "backhaul", "warehouse_transfer"}
RETURN_LEG_TYPES = {"empty_return", "backhaul"}
RETURN_PURPOSES = {"none", "empty_return", "backhaul", "returned_goods"}


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _audit(db, action, table, record_id, actor):
    db.add(AuditLog(
        user_id=actor,
        action=action,
        table_name=table,
        record_id=record_id,
        timestamp=_now(),
        ip_address=db.info.get("audit_ip"),
    ))


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc).isoformat()


def _decimal_str(value):
    return str(value) if value is not None else None


def han_giao_cua_chuyen(db, delivery_order_ids):
    """Hạn giao của chuyến = mốc muộn nhất mà KHÁCH cho phép trên các DO nó chở.

    Vì sao không dùng `trip.planned_arrival_at`. Mốc đó là KẾ HOẠCH nội bộ do
    hệ thống tính lúc lập chuyến (giờ xuất bến + km / vận tốc + giờ dừng). Nó
    trả lời "mình định tới lúc nào", không trả lời "khách cần trước lúc nào".
    Hạn với khách nằm trên DO: `delivery_window_end`. Một chuyến tới nơi sau kế
    hoạch 2 giờ nhưng vẫn trong khung giao của khách KHÔNG trễ hạn — nó chỉ
    lệch kế hoạch. Trước đây bảng Trip so giờ tới thực tế với kế hoạch nội bộ
    nên chuyến đã hoàn tất đúng hẹn vẫn bị gán "trễ hạn".
    """
    if not delivery_order_ids:
        return None
    moc = []
    for order in db.query(DeliveryOrder).filter(DeliveryOrder.id.in_(delivery_order_ids)).all():
        han = order.delivery_window_end or order.planned_arrival_at or order.delivery_date
        if han is not None:
            if han.tzinfo is None:
                han = han.replace(tzinfo=dt.timezone.utc)
            moc.append(han)
    return max(moc) if moc else None


def _phut_giua(sau, truoc):
    if sau is None or truoc is None:
        return None
    if sau.tzinfo is None:
        sau = sau.replace(tzinfo=dt.timezone.utc)
    if truoc.tzinfo is None:
        truoc = truoc.replace(tzinfo=dt.timezone.utc)
    return int(round((sau - truoc).total_seconds() / 60.0))


def serialize_trip(db, trip):
    delivery_order_ids = [
        row[0] for row in (
            db.query(TripDeliveryOrder.do_id)
            .filter(TripDeliveryOrder.trip_id == trip.id)
            .order_by(TripDeliveryOrder.allocation_sequence, TripDeliveryOrder.do_id)
            .all()
        )
    ]
    leg_rows = (
        db.query(TransportTripLeg)
        .filter(TransportTripLeg.trip_id == trip.id)
        .order_by(TransportTripLeg.sequence_no, TransportTripLeg.id)
        .all()
    )
    total_distance_km = sum((Decimal(leg.distance_km or 0) for leg in leg_rows), Decimal("0"))
    return_distance_km = sum((
        Decimal(leg.distance_km or 0)
        for leg in leg_rows
        if leg.leg_type in RETURN_LEG_TYPES
    ), Decimal("0"))
    do_trip_counts = {}
    do_vehicle_counts = {}
    if delivery_order_ids:
        link_rows = (
            db.query(TripDeliveryOrder.do_id, TransportTrip.id, TransportTrip.vehicle_id)
            .join(TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id)
            .filter(TripDeliveryOrder.do_id.in_(delivery_order_ids))
            .all()
        )
        for do_id, linked_trip_id, vehicle_id in link_rows:
            do_trip_counts.setdefault(do_id, set()).add(linked_trip_id)
            if vehicle_id:
                do_vehicle_counts.setdefault(do_id, set()).add(vehicle_id)
    relationship_summary = {
        "do_count": len(delivery_order_ids),
        "has_many_dos_on_trip": len(delivery_order_ids) > 1,
        "has_split_do_across_trips": any(len(trip_ids) > 1 for trip_ids in do_trip_counts.values()),
        "trip_count_for_dos": {do_id: len(trip_ids) for do_id, trip_ids in do_trip_counts.items()},
        "vehicle_count_for_dos": {
            do_id: (len(vehicle_ids) if vehicle_ids else len(do_trip_counts.get(do_id, [])))
            for do_id, vehicle_ids in do_vehicle_counts.items()
        },
    }
    for do_id, trip_ids in do_trip_counts.items():
        relationship_summary["vehicle_count_for_dos"].setdefault(do_id, len(trip_ids))
    legs = [
        {
            "id": leg.id,
            "trip_id": leg.trip_id,
            "do_id": leg.do_id,
            "sequence_no": leg.sequence_no,
            "leg_type": leg.leg_type,
            "origin": leg.origin,
            "destination": leg.destination,
            "stop_name": leg.stop_name,
            "receiver_name": leg.receiver_name,
            "receiver_phone": leg.receiver_phone,
            "delivery_note": leg.delivery_note,
            "distance_km": _decimal_str(leg.distance_km),
            "avg_speed_kmh": _decimal_str(leg.avg_speed_kmh),
            "dwell_minutes": leg.dwell_minutes,
            "planned_departure_at": _iso(leg.planned_departure_at),
            "planned_arrival_at": _iso(leg.planned_arrival_at),
            "actual_departure_at": _iso(leg.actual_departure_at),
            "actual_arrival_at": _iso(leg.actual_arrival_at),
            "status": leg.status,
            "allocated_cost": _decimal_str(leg.allocated_cost),
            "allocated_revenue": _decimal_str(leg.allocated_revenue),
        }
        for leg in leg_rows
    ]
    han_giao = han_giao_cua_chuyen(db, delivery_order_ids)
    return {
        "id": trip.id,
        "freight_order_id": trip.freight_order_id,
        "trip_type": trip.trip_type,
        "status": trip.status,
        "vehicle_id": trip.vehicle_id,
        "driver_id": trip.driver_id,
        "co_driver_id": trip.co_driver_id,
        "delivery_order_ids": delivery_order_ids,
        "planned_departure_at": _iso(trip.planned_departure_at),
        "planned_arrival_at": _iso(trip.planned_arrival_at),
        "planned_return_at": _iso(trip.planned_return_at),
        "actual_departure_at": _iso(trip.actual_departure_at),
        "actual_arrival_at": _iso(trip.actual_arrival_at),
        "actual_return_at": _iso(trip.actual_return_at),
        # HAN VOI KHACH va hai con so tre — tinh MOT CHO o day de moi man doc
        # chung (bang Trip, ho so chuyen, theo doi) cung mot dinh nghia.
        #   delivery_due_at     : muon nhat khach cho phep (delivery_window_end lon nhat)
        #   is_late             : DA toi noi va toi SAU han khach -> "trễ hạn"
        #   behind_plan_minutes : toi noi lech ke hoach noi bo bao nhieu phut
        #                         (duong = tre hon ke hoach). Chi la lech, khong
        #                         phai tre hạn.
        "delivery_due_at": _iso(han_giao),
        "is_late": bool(trip.actual_arrival_at and han_giao
                        and _phut_giua(trip.actual_arrival_at, han_giao) > 0),
        "late_minutes": (max(0, _phut_giua(trip.actual_arrival_at, han_giao))
                         if trip.actual_arrival_at and han_giao else None),
        "behind_plan_minutes": _phut_giua(trip.actual_arrival_at, trip.planned_arrival_at)
        if trip.actual_arrival_at and trip.planned_arrival_at else None,
        "total_distance_km": _decimal_str(total_distance_km),
        "return_distance_km": _decimal_str(return_distance_km),
        "relationship_summary": relationship_summary,
        "version": trip.version,
        "legs": legs,
    }


def list_trips(db, status=None, freight_order_id=None, limit=100):
    query = db.query(TransportTrip)
    if status:
        query = query.filter(TransportTrip.status == status)
    if freight_order_id:
        query = query.filter(TransportTrip.freight_order_id == freight_order_id)
    query = query.order_by(TransportTrip.created_at.desc(), TransportTrip.id.desc())
    if limit is not None:
        query = query.limit(limit)
    return [
        serialize_trip(db, trip)
        for trip in query.all()
    ]


def get_trip_detail(db, trip_id):
    trip = db.get(TransportTrip, trip_id)
    if not trip:
        raise DomainError("TRIP_NOT_FOUND", "Không tìm thấy chuyến vận tải.", 404)
    return serialize_trip(db, trip)


def _bounded_text(value, field, maximum=500, required=True):
    if not isinstance(value, str):
        if required:
            raise DomainError("TRIP_PAYLOAD_INVALID", f"{field} phải là chuỗi hợp lệ.", 422)
        return None
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise DomainError("TRIP_PAYLOAD_INVALID", f"{field} không hợp lệ hoặc vượt quá {maximum} ký tự.", 422)
    return value or None


def _positive_version(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DomainError("EXPECTED_VERSION_INVALID", "Phiên bản dữ liệu phải là số nguyên dương.", 422)
    return value


def _decimal(value, field, positive=False):
    if isinstance(value, bool) or isinstance(value, float):
        raise DomainError("TRIP_METRIC_INVALID", f"{field} phải là số thập phân hữu hạn.", 422)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("TRIP_METRIC_INVALID", f"{field} không hợp lệ.", 422) from None
    if not number.is_finite() or number < 0 or (positive and number <= 0):
        raise DomainError("TRIP_METRIC_INVALID", f"{field} không hợp lệ.", 422)
    return number


def _datetime(value, field, required=False):
    if value is None and not required:
        return None
    try:
        parsed = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("TRIP_TIME_INVALID", f"Thời gian {field} không hợp lệ.", 422) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DomainError("TRIP_TIME_INVALID", f"Thời gian {field} phải có múi giờ.", 422)
    return parsed.astimezone(dt.timezone.utc)


def create_trip(db, data, actor):
    allowed = {"id", "freight_order_id", "trip_type", "do_ids", "vehicle_id", "driver_id"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise DomainError("TRIP_PAYLOAD_INVALID", "Dữ liệu chuyến vận tải có trường không được hỗ trợ.", 422)
    trip_id = _bounded_text(data.get("id"), "Mã chuyến", 128)
    freight_order_id = _bounded_text(data.get("freight_order_id"), "Mã Freight Order", 128)
    trip_type = data.get("trip_type")
    if trip_type not in TRIP_TYPES:
        raise DomainError("TRIP_TYPE_INVALID", "Loại chuyến không hợp lệ.", 422)
    if not db.get(FreightOrder, freight_order_id):
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy Freight Order để lập chuyến.", 404)
    do_ids = list(dict.fromkeys(data.get("do_ids") or []))
    if not do_ids:
        raise DomainError("TRIP_DO_REQUIRED", "Cần chọn ít nhất một đơn giao hàng cho chuyến.", 422)
    if any(not isinstance(do_id, str) or not do_id.strip() for do_id in do_ids):
        raise DomainError("TRIP_DO_INVALID", "Danh sách đơn giao hàng không hợp lệ.", 422)
    existing = {row[0] for row in db.query(DeliveryOrder.id).filter(DeliveryOrder.id.in_(do_ids)).all()}
    if existing != set(do_ids):
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", "Có đơn giao hàng không tồn tại.", 404)
    trip = TransportTrip(
        id=trip_id,
        freight_order_id=freight_order_id,
        trip_type=trip_type,
        vehicle_id=data.get("vehicle_id"),
        driver_id=data.get("driver_id"),
        created_by=actor,
        updated_by=actor,
    )
    db.add(trip)
    db.flush()
    for sequence, do_id in enumerate(do_ids, start=1):
        db.add(TripDeliveryOrder(
            trip_id=trip.id,
            do_id=do_id,
            allocation_sequence=sequence,
            created_by=actor,
        ))
    _audit(db, "CREATE_TRANSPORT_TRIP", "transport_trips", trip.id, actor)
    db.flush()
    return trip


def create_trip_payload(db, data, actor):
    trip = create_trip(db, data, actor)
    db.flush()
    return serialize_trip(db, trip)


def _route_segments(route):
    try:
        rows = json.loads(route.segments_json or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        rows = None
    if not isinstance(rows, list) or not rows:
        raise DomainError(
            "ROUTE_SEGMENTS_INVALID",
            "Tuyến chưa có danh sách chặng hợp lệ trong Master Data.",
            422,
            ["master-data/routes"],
        )
    segments = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise DomainError("ROUTE_SEGMENTS_INVALID", f"Chặng {index} không hợp lệ.", 422)
        origin = row.get("origin") or row.get("from") or row.get("start")
        destination = row.get("destination") or row.get("to") or row.get("end")
        distance = row.get("distance_km", row.get("dist_km", row.get("distance", row.get("km"))))
        try:
            distance = Decimal(str(distance))
        except (InvalidOperation, TypeError, ValueError):
            distance = Decimal("-1")
        if not str(origin or "").strip() or not str(destination or "").strip() or distance <= 0:
            raise DomainError("ROUTE_SEGMENTS_INVALID", f"Chặng {index} thiếu điểm đi, điểm đến hoặc số km.", 422)
        segments.append({
            "origin": str(origin).strip(),
            "destination": str(destination).strip(),
            "distance_km": distance,
        })
    route_total = Decimal(str(route.distance_km or 0))
    segment_total = sum((segment["distance_km"] for segment in segments), Decimal("0"))
    if route_total <= 0 or abs(route_total - segment_total) > Decimal("0.2"):
        raise DomainError(
            "ROUTE_SEGMENTS_INVALID",
            f"Tổng quãng đường các chặng ({segment_total} km) không khớp tuyến ({route_total} km).",
            422,
            ["master-data/routes"],
        )
    return segments


def _location(db, location_id, name):
    location = db.get(Location, location_id)
    if location is None:
        location = Location(id=location_id, name=name, type="RoutePoint")
        db.add(location)
        db.flush()
    return location


def create_trip_from_delivery_orders(db, data, actor):
    trip_id = _bounded_text(data.get("id"), "Mã chuyến", 128)
    do_ids = list(data.get("do_ids") or [])
    existing_trip = db.get(TransportTrip, trip_id)
    if existing_trip is not None:
        existing_do_ids = {
            row[0] for row in db.query(TripDeliveryOrder.do_id).filter_by(trip_id=trip_id).all()
        }
        if existing_do_ids != set(do_ids):
            raise conflict("TRIP_IDEMPOTENCY_CONFLICT", "Mã Trip đã tồn tại với danh sách DO khác.")
        return serialize_trip(db, existing_trip)

    orders = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.id.in_(do_ids))
        .with_for_update()
        .all()
    )
    if len(orders) != len(do_ids):
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", "Có DO không tồn tại.", 404)
    order_by_id = {order.id: order for order in orders}
    orders = [order_by_id[do_id] for do_id in do_ids]
    if any(order.canonical_status != "pending" for order in orders):
        raise conflict("DELIVERY_ORDER_NOT_PENDING", "Chỉ DO đang chờ vận chuyển mới được lập Trip.")
    route_ids = {order.route_id for order in orders}
    if len(route_ids) != 1 or None in route_ids:
        raise conflict("DELIVERY_ORDERS_INCOMPATIBLE", "Các DO phải dùng cùng một tuyến Master Data.")
    route = db.get(Route, next(iter(route_ids)))
    if route is None:
        raise DomainError("ROUTE_NOT_FOUND", "Không tìm thấy tuyến của DO trong Master Data.", 404)
    segments = _route_segments(route)
    return_purpose = data.get("return_purpose") or "none"
    if return_purpose not in RETURN_PURPOSES:
        raise DomainError("RETURN_PURPOSE_INVALID", "Mục đích chặng về không hợp lệ.", 422)
    trip_type = data.get("trip_type") or "one_way"
    if trip_type not in TRIP_TYPES:
        raise DomainError("TRIP_TYPE_INVALID", "Loại chuyến không hợp lệ.", 422)
    if trip_type in {"one_way", "multi_stop"} and return_purpose != "none":
        raise conflict("TRIP_RETURN_NOT_ALLOWED", "Loại Trip này không có chặng về.")
    if trip_type == "round_trip" and return_purpose == "none":
        raise conflict("TRIP_RETURN_PURPOSE_REQUIRED", "Trip khứ hồi phải chọn mục đích chặng về.")
    if trip_type == "backhaul" and return_purpose != "backhaul":
        raise conflict("TRIP_RETURN_PURPOSE_INVALID", "Trip backhaul phải chọn DO chiều về.")

    return_route = None
    return_segments = []
    return_do = None
    if return_purpose != "none":
        if not str(data.get("return_route_id") or "").strip():
            raise DomainError(
                "RETURN_ROUTE_REQUIRED",
                "Cần chọn tuyến chiều về từ Route Master để tính ETA và thời điểm xe sẵn sàng.",
                422,
                ["master-data/routes"],
            )
        return_route_id = _bounded_text(data.get("return_route_id"), "Mã tuyến chiều về", 128)
        return_route = db.get(Route, return_route_id)
        if return_route is None:
            raise DomainError("RETURN_ROUTE_NOT_FOUND", "Không tìm thấy tuyến chiều về trong Master Data.", 404)
        return_segments = _route_segments(return_route)
        if segments[-1]["destination"].strip().casefold() != return_segments[0]["origin"].strip().casefold():
            raise conflict("RETURN_ROUTE_DISCONNECTED", "Tuyến chiều về phải bắt đầu tại điểm kết thúc chiều đi.")
        if return_purpose in {"backhaul", "returned_goods"}:
            return_do_id = _bounded_text(data.get("return_do_id"), "Mã DO chiều về", 128)
            return_do = db.get(DeliveryOrder, return_do_id)
            if return_do is None:
                raise DomainError("RETURN_DO_NOT_FOUND", "Không tìm thấy DO chiều về.", 404)
            if return_do.id in do_ids:
                raise conflict("RETURN_DO_DUPLICATE", "DO chiều về không được trùng DO chiều đi.")
            if return_do.canonical_status != "pending":
                raise conflict("RETURN_DO_NOT_PENDING", "DO chiều về phải đang chờ vận chuyển.")
            if return_do.route_id != return_route.id:
                raise conflict("RETURN_ROUTE_MISMATCH", "DO chiều về phải dùng đúng tuyến chiều về đã chọn.")

    pickup_starts = [order.pickup_window_start for order in orders if order.pickup_window_start]
    pickup_ends = [order.pickup_window_end for order in orders if order.pickup_window_end]
    delivery_starts = [order.delivery_window_start for order in orders if order.delivery_window_start]
    delivery_ends = [order.delivery_window_end for order in orders if order.delivery_window_end]
    if min(map(len, (pickup_starts, pickup_ends, delivery_starts, delivery_ends))) != len(orders):
        raise DomainError("DELIVERY_TIME_WINDOW_REQUIRED", "DO phải có đủ khung giờ lấy và giao hàng.", 422)
    pickup_start, pickup_end = max(pickup_starts), min(pickup_ends)
    delivery_start, delivery_end = max(delivery_starts), min(delivery_ends)
    if pickup_start >= pickup_end or delivery_start >= delivery_end:
        raise conflict("DELIVERY_ORDERS_INCOMPATIBLE", "Khung giờ của các DO không giao nhau.")

    # BỎ MÚI GIỜ, GIỮ UTC — bốn mốc này đi vào `freight_orders`, và cột ở đó
    # KHÔNG mang múi giờ.
    #
    # LỖI ĐÃ ĐO ĐƯỢC, và chỉ xảy ra trên PostgreSQL. `models.py` khai không nhất
    # quán: `DeliveryOrder` và `TransportTrip` dùng `DateTime(timezone=True)`,
    # còn `FreightOrder` dùng `DateTime` trần. Trên PostgreSQL điều đó thành hai
    # kiểu cột thật khác nhau (`timestamptz` và `timestamp`), nên bốn giá trị
    # đọc ra từ `delivery_orders` là CÓ múi giờ (+07), và khi ghi vào cột trần
    # thì PostgreSQL **bỏ phần múi giờ đi và giữ giờ đồng hồ địa phương**:
    #
    #     delivery_orders : 2026-09-08 23:11:00+07:00   (đúng)
    #     freight_orders  : 2026-09-09 06:11:00         (mất 7 giờ)
    #
    # Rồi cửa chặn điều phối đọc lại bằng `_utc()`, mà hàm đó coi mốc trần LÀ
    # UTC. Nên khung giờ của chuyến lệch đúng 7 giờ, và mọi lệnh điều phối bị
    # chặn bằng `ASSIGNMENT_OUTSIDE_WINDOW` — "Thời gian điều phối phải nằm
    # trong khung lấy và giao hàng của chuyến". Trên SQLite không lộ ra, vì
    # SQLite không có kiểu thời gian thật và giữ nguyên thứ được đưa vào.
    #
    # Quy ước của dự án là LƯU UTC (hiển thị +7 ở tầng trình bày), nên chỗ đúng
    # để sửa là ở đây — đổi về UTC rồi bỏ nhãn múi giờ — chứ không phải nới cửa
    # chặn. Mốc đã trần thì giữ nguyên, nên SQLite không đổi hành vi.
    def _utc_tran(x):
        if x is None or x.tzinfo is None:
            return x
        return x.astimezone(dt.timezone.utc).replace(tzinfo=None)

    pickup_start, pickup_end = _utc_tran(pickup_start), _utc_tran(pickup_end)
    delivery_start, delivery_end = _utc_tran(delivery_start), _utc_tran(delivery_end)

    linked_freight_orders = {
        row[0] for row in (
            db.query(TransportTrip.freight_order_id)
            .join(TripDeliveryOrder, TripDeliveryOrder.trip_id == TransportTrip.id)
            .filter(TripDeliveryOrder.do_id.in_(do_ids))
            .distinct()
            .all()
        )
    }
    if len(linked_freight_orders) > 1:
        raise conflict("MIXED_FREIGHT_ORDERS", "Các DO đang thuộc nhiều Freight Order khác nhau.")
    freight_order_id = next(iter(linked_freight_orders), f"FO-{trip_id}")
    freight_order = db.get(FreightOrder, freight_order_id)
    total_weight = sum(float(order.weight_kg or 0) for order in orders)
    total_volume = sum(float(order.volume_m3 or 0) for order in orders)
    total_pallets = sum(int(order.pallet_count or 0) for order in orders)
    if freight_order is None:
        origin = segments[0]["origin"]
        destination = segments[-1]["destination"]
        pickup_location = _location(db, f"LOC-{route.id}-ORIGIN", origin)
        delivery_location = _location(db, f"LOC-{route.id}-DEST", destination)
        freight_order = FreightOrder(
            id=freight_order_id,
            pickup_location_id=pickup_location.id,
            delivery_location_id=delivery_location.id,
            pickup_window_start=pickup_start,
            pickup_window_end=pickup_end,
            delivery_window_start=delivery_start,
            delivery_window_end=delivery_end,
            total_weight_kg=total_weight,
            total_volume_m3=total_volume,
            total_pallet_count=total_pallets,
            max_weight_kg=max(total_weight, 1),
            max_volume_m3=max(total_volume, 1),
            max_pallet_count=max(total_pallets, 1),
            created_by=actor,
            updated_by=actor,
        )
        db.add(freight_order)
        db.flush()

    trip = create_trip(db, {
        "id": trip_id,
        "freight_order_id": freight_order.id,
        "trip_type": data.get("trip_type"),
        "do_ids": do_ids,
    }, actor)
    stop_plan = {
        int(item.get("sequence_no")): item
        for item in (data.get("stop_plan") or [])
        if isinstance(item, dict) and item.get("sequence_no") is not None
    }
    for sequence, segment in enumerate(segments, start=1):
        stop = stop_plan.get(sequence) or {}
        add_leg(db, trip.id, {
            "id": f"{trip.id}-LEG-{sequence:03d}",
            "do_id": do_ids[-1] if sequence == len(segments) else do_ids[0],
            "sequence_no": sequence,
            "leg_type": "delivery",
            "origin": segment["origin"],
            "destination": segment["destination"],
            "stop_name": stop.get("stop_name") or segment["destination"],
            "receiver_name": stop.get("receiver_name"),
            "receiver_phone": stop.get("receiver_phone"),
            "delivery_note": stop.get("delivery_note"),
            "distance_km": str(segment["distance_km"]),
            "avg_speed_kmh": str(data.get("avg_speed_kmh")),
            "dwell_minutes": stop.get("dwell_minutes") if stop.get("dwell_minutes") is not None else data.get("dwell_minutes", 0),
            "planned_departure_at": (
                data.get("planned_departure_at").isoformat()
                if sequence == 1 and isinstance(data.get("planned_departure_at"), dt.datetime)
                else data.get("planned_departure_at") if sequence == 1 else None
            ),
        }, expected_version=trip.version, actor=actor)
    return_leg_type = "empty_return" if return_purpose == "empty_return" else "backhaul"
    for offset, segment in enumerate(return_segments, start=len(segments) + 1):
        add_leg(db, trip.id, {
            "id": f"{trip.id}-LEG-{offset:03d}",
            "do_id": return_do.id if return_do is not None else None,
            "sequence_no": offset,
            "leg_type": return_leg_type,
            "origin": segment["origin"],
            "destination": segment["destination"],
            "stop_name": segment["destination"],
            "delivery_note": "Nhận hàng hoàn từ DO cũ" if return_purpose == "returned_goods" else None,
            "distance_km": str(segment["distance_km"]),
            "avg_speed_kmh": str(data.get("avg_speed_kmh")),
            "dwell_minutes": data.get("dwell_minutes", 0),
            "planned_departure_at": None,
        }, expected_version=trip.version, actor=actor)
    trip.status = "planned"
    trip.updated_at = _now()
    trip.updated_by = actor
    db.flush()
    return serialize_trip(db, trip)


def _recalculate_eta(db, trip):
    legs = (
        db.query(TransportTripLeg)
        .filter(TransportTripLeg.trip_id == trip.id)
        .order_by(TransportTripLeg.sequence_no, TransportTripLeg.id)
        .all()
    )
    previous_arrival = None
    for index, leg in enumerate(legs):
        requested_departure = leg.planned_departure_at
        if index == 0 and requested_departure is None:
            raise DomainError("TRIP_DEPARTURE_REQUIRED", "Chặng đầu tiên phải có thời gian khởi hành dự kiến.", 422)
        earliest = previous_arrival + dt.timedelta(minutes=leg.dwell_minutes or 0) if previous_arrival else None
        if earliest is None:
            departure = requested_departure
        elif requested_departure is None:
            departure = earliest
        else:
            departure = max(requested_departure, earliest)
        travel_hours = Decimal(leg.distance_km) / Decimal(leg.avg_speed_kmh)
        arrival = departure + dt.timedelta(seconds=float(travel_hours * Decimal(3600)))
        leg.planned_departure_at = departure
        leg.planned_arrival_at = arrival
        previous_arrival = arrival
    if legs:
        trip.planned_departure_at = legs[0].planned_departure_at
        trip.planned_arrival_at = legs[-1].planned_arrival_at
        return_legs = [leg for leg in legs if leg.leg_type in RETURN_LEG_TYPES]
        trip.planned_return_at = return_legs[-1].planned_arrival_at if return_legs else None


def add_leg(db, trip_id, data, expected_version, actor):
    _positive_version(expected_version)
    allowed = {
        "id", "do_id", "sequence_no", "leg_type", "origin", "destination",
        "distance_km", "avg_speed_kmh", "dwell_minutes", "planned_departure_at",
        "stop_name", "receiver_name", "receiver_phone", "delivery_note",
    }
    if not isinstance(data, dict) or set(data) - allowed:
        raise DomainError("TRIP_LEG_PAYLOAD_INVALID", "Dữ liệu chặng có trường không được hỗ trợ.", 422)
    trip = db.query(TransportTrip).filter(TransportTrip.id == trip_id).with_for_update().first()
    if not trip:
        raise DomainError("TRIP_NOT_FOUND", "Không tìm thấy chuyến vận tải.", 404)
    if trip.version != expected_version:
        raise conflict("VERSION_CONFLICT", "Chuyến đã được người khác cập nhật. Vui lòng tải lại dữ liệu.")
    if trip.status not in {"draft", "planned"}:
        raise conflict("TRIP_LOCKED", "Chỉ được sửa chặng khi chuyến đang ở trạng thái nháp hoặc đã lập kế hoạch.")
    leg_type = data.get("leg_type")
    if leg_type not in LEG_TYPES:
        raise DomainError("TRIP_LEG_TYPE_INVALID", "Loại chặng không hợp lệ.", 422)
    do_id = data.get("do_id")
    if leg_type == "backhaul" and not do_id:
        raise DomainError("BACKHAUL_DO_REQUIRED", "Chặng backhaul phải gắn với một đơn giao hàng chiều về.", 422)
    membership = db.get(TripDeliveryOrder, (trip.id, do_id)) if do_id else None
    if do_id and not membership:
        if leg_type != "backhaul":
            raise DomainError("TRIP_DO_MEMBERSHIP_REQUIRED", "Đơn giao hàng chưa được phân vào chuyến này.", 422)
        if not db.get(DeliveryOrder, do_id):
            raise DomainError("DELIVERY_ORDER_NOT_FOUND", "Không tìm thấy đơn giao hàng chiều về.", 404)
        current_links = (
            db.query(TripDeliveryOrder)
            .filter(TripDeliveryOrder.trip_id == trip.id)
            .order_by(TripDeliveryOrder.allocation_sequence.desc())
            .all()
        )
        db.add(TripDeliveryOrder(
            trip_id=trip.id,
            do_id=do_id,
            allocation_sequence=(current_links[0].allocation_sequence if current_links else 0) + 1,
            created_by=actor,
        ))
        db.flush()
    try:
        sequence_no = int(data.get("sequence_no"))
        dwell_minutes = int(data.get("dwell_minutes", 0))
    except (TypeError, ValueError):
        raise DomainError("TRIP_METRIC_INVALID", "Thứ tự hoặc thời gian dừng không hợp lệ.", 422) from None
    if isinstance(data.get("sequence_no"), bool) or isinstance(data.get("dwell_minutes", 0), bool) or sequence_no <= 0 or dwell_minutes < 0:
        raise DomainError("TRIP_METRIC_INVALID", "Thứ tự phải dương và thời gian dừng không được âm.", 422)
    leg = TransportTripLeg(
        id=_bounded_text(data.get("id"), "Mã chặng", 128),
        trip_id=trip.id,
        do_id=do_id,
        sequence_no=sequence_no,
        leg_type=leg_type,
        origin=_bounded_text(data.get("origin"), "Điểm đi"),
        destination=_bounded_text(data.get("destination"), "Điểm đến"),
        stop_name=_bounded_text(data.get("stop_name"), "Tên điểm dừng", required=False),
        receiver_name=_bounded_text(data.get("receiver_name"), "Người nhận", maximum=255, required=False),
        receiver_phone=_bounded_text(data.get("receiver_phone"), "Số điện thoại người nhận", maximum=64, required=False),
        delivery_note=_bounded_text(data.get("delivery_note"), "Ghi chú giao hàng", maximum=1000, required=False),
        distance_km=_decimal(data.get("distance_km"), "Khoảng cách"),
        avg_speed_kmh=_decimal(data.get("avg_speed_kmh"), "Vận tốc trung bình", positive=True),
        dwell_minutes=dwell_minutes,
        planned_departure_at=_datetime(data.get("planned_departure_at"), "khởi hành"),
    )
    db.add(leg)
    db.flush()
    _recalculate_eta(db, trip)
    trip.version += 1
    trip.updated_at = _now()
    trip.updated_by = actor
    _audit(db, "ADD_TRANSPORT_TRIP_LEG", "transport_trip_legs", leg.id, actor)
    db.flush()
    return leg


def add_leg_payload(db, trip_id, data, expected_version, actor):
    leg = add_leg(db, trip_id, data, expected_version, actor)
    db.flush()
    return {
        "id": leg.id,
        "trip_id": leg.trip_id,
        "do_id": leg.do_id,
        "sequence_no": leg.sequence_no,
        "leg_type": leg.leg_type,
        "stop_name": leg.stop_name,
        "receiver_name": leg.receiver_name,
        "receiver_phone": leg.receiver_phone,
        "delivery_note": leg.delivery_note,
        "planned_departure_at": _iso(leg.planned_departure_at),
        "planned_arrival_at": _iso(leg.planned_arrival_at),
        "status": leg.status,
    }


# ===========================================================================
# HUY CHUYEN
# ===========================================================================

#: Chuyen da DONG SO — huy la sua so sach, khong phai sua ke hoach.
CHUYEN_DA_DONG = {"completed", "settled"}


def cancel_trip(db, trip_id, data, actor):
    """Huy mot chuyen, tra xe / to lai / DO ve dung cho cua chung.

    VI SAO PHAI CO DUONG NAY. Ra soat tron luong do duoc: **khong mot cho nao
    trong ma nguon ghi trang thai huy cho mot chuyen**, va khong diem cuoi nao
    cho phep. Nhung cua chan huy DO lai tu choi khi con mot chuyen chua
    `completed`/`cancelled` — nen nhanh `cancelled` cua cua do KHONG BAO GIO toi
    duoc. Khach huy hang sau khi da lap chuyen thi:

      · huy DO  -> 409 ACTIVE_TRIP_EXISTS, va duoc chi sang man Chuyen,
      · man Chuyen -> khong co nut huy nao,
      · duong duy nhat con lai la XOA CUNG DO (duoc phep khi con `pending`)
        trong khi `trip_delivery_orders` van tro vao no — vi pham khoa ngoai
        tren PostgreSQL, hoac de lai mot chuyen mo coi.

    HUY LA MOT PHEP TRA VE, KHONG PHAI MOT PHEP XOA. Ba thu phai ve dung cho:

      1. **DO ve `pending`** — hang cua khach van con do, chi la chuyen nay
         khong chay nua. Xoa DO la mat mot yeu cau that cua khach.
      2. **Xe va to lai duoc giai phong** — dung `release_resources`, cung ham
         ma buoc hoan tat va buoc xe-ve-bai dung, nen mot chuyen bi huy khong
         giu xe lai qua buoi demo.
      3. **Phan cong va chang chuyen sang `cancelled`** — `list_vehicle_availability`
         loc bo chuyen da huy, nen lich xe sach ngay, khong con mot khoang bi
         chiem boi mot chuyen khong chay.

    HAI CUA KHONG DUOC MO. Chuyen da hoan tat / da quyet toan thi khong huy —
    do la sua so sach. Va chuyen co DO **da nop POD hoac da giao** thi cung
    khong: POD la bang chung giao hang co that, hoa don co the da phat sinh; huy
    luc do la xoa dau vet cua mot lan giao that.
    """
    from models import DeliveryPODRecord
    from services.workflow_service import STATUS, release_resources

    trip = db.query(TransportTrip).filter(TransportTrip.id == trip_id).with_for_update().first()
    if not trip:
        raise DomainError("TRIP_NOT_FOUND", f"Không tìm thấy chuyến {trip_id}.", 404)
    if trip.version != data.get("expected_version"):
        raise conflict("VERSION_CONFLICT", "Chuyến đã thay đổi. Vui lòng tải lại dữ liệu.")
    ly_do = str(data.get("reason") or "").strip()
    if not ly_do:
        raise DomainError(
            "TRIP_CANCEL_REASON_REQUIRED",
            "Phải ghi lý do huỷ chuyến — người đọc sổ sau này cần biết vì sao xe không chạy.",
            422,
        )
    if len(ly_do) > 500:
        raise DomainError("TRIP_CANCEL_REASON_TOO_LONG", "Lý do huỷ chuyến không được vượt quá 500 ký tự.", 422)
    if trip.status in CHUYEN_DA_DONG:
        raise conflict(
            "TRIP_ALREADY_CLOSED",
            f"Chuyến {trip.id} đã hoàn tất — không huỷ được. Sai số thì điều chỉnh ở bước quyết toán.",
            ["transport-trips"],
        )
    # HUY MOT CHUYEN DA HUY LA MOT VIEC KHONG CAN LAM, khong phai mot loi: nut
    # bam hai lan, hoac hai nguoi cung huy, thi ca hai nen thay cung ket qua.
    if trip.status == "cancelled":
        return serialize_trip(db, trip)

    ma_do = [row[0] for row in db.query(TripDeliveryOrder.do_id).filter_by(trip_id=trip.id).all()]
    deliveries = (
        db.query(DeliveryOrder).filter(DeliveryOrder.id.in_(ma_do)).with_for_update().all()
        if ma_do else []
    )
    da_giao = sorted(d.id for d in deliveries if d.canonical_status == "delivered")
    if da_giao:
        raise conflict(
            "TRIP_HAS_DELIVERED_DO",
            "Chuyến %s có lệnh đã giao xong (%s) — không huỷ được. Hàng đã tới tay khách."
            % (trip.id, ", ".join(da_giao)),
            ["delivery-completion"],
        )
    if ma_do:
        co_pod = db.query(DeliveryPODRecord.id).filter(DeliveryPODRecord.do_id.in_(ma_do)).first()
        if co_pod:
            raise conflict(
                "TRIP_HAS_POD",
                "Chuyến %s đã có bằng chứng giao hàng (POD) — không huỷ được. "
                "Hoàn tất giao hàng rồi xử lý ở bước quyết toán." % trip.id,
                ["delivery-completion"],
            )

    for leg in db.query(TransportTripLeg).filter(TransportTripLeg.trip_id == trip.id).with_for_update().all():
        if leg.status not in {"completed", "cancelled"}:
            leg.status = "cancelled"

    for assignment in db.query(ResourceAssignment).filter(
        ResourceAssignment.trip_id == trip.id,
        ResourceAssignment.status == "active",
    ).with_for_update().all():
        assignment.status = "cancelled"

    for delivery in deliveries:
        if delivery.canonical_status == "cancelled":
            continue
        # GIAI PHONG TRUOC KHI XOA GAN: `release_resources` doc
        # `do.vehicle_id` / `do.driver_id` de biet tra ai ve. Xoa gan truoc thi
        # no khong con gi de tra, va xe o lai trang thai "dang thuc hien".
        release_resources(db, delivery)
        delivery.canonical_status = "pending"
        delivery.status = STATUS["delivery_order"]["pending"]
        delivery.vehicle_id = None
        delivery.driver_id = None
        delivery.co_driver = None
        delivery.planned_departure_at = None
        delivery.planned_arrival_at = None
        delivery.planned_return_at = None
        delivery.version = (delivery.version or 1) + 1
        delivery.updated_at = _now()
        delivery.updated_by = actor

    freight_order = db.get(FreightOrder, trip.freight_order_id)
    if freight_order is not None and freight_order.status not in {"delivered", "cancelled"}:
        # Lenh van chuyen ve `planned`: no van la mot lenh can chay, chi la
        # chuyen thuc hien no da huy. Lap chuyen moi se dung lai chinh no.
        freight_order.status = "planned"
        freight_order.version = (freight_order.version or 1) + 1
        freight_order.updated_at = _now()
        freight_order.updated_by = actor

    trip.status = "cancelled"
    trip.version += 1
    trip.updated_at = _now()
    trip.updated_by = actor
    _audit(db, "CANCEL_TRANSPORT_TRIP", "transport_trips", trip.id, actor)
    db.flush()
    return serialize_trip(db, trip)


def complete_return(db, trip_id, data, actor):
    trip = db.query(TransportTrip).filter(TransportTrip.id == trip_id).with_for_update().first()
    if not trip:
        raise DomainError("TRIP_NOT_FOUND", "Khong tim thay chuyen van tai.", 404)
    expected_version = data.get("expected_version")
    if trip.version != expected_version:
        raise conflict("VERSION_CONFLICT", "Chuyen da thay doi. Vui long tai lai du lieu.")
    if trip.status not in {"dispatched", "in_transit"}:
        raise conflict("INVALID_TRANSITION", "Chi chuyen dang thuc thi moi duoc xac nhan quay ve.")

    return_legs = db.query(TransportTripLeg).filter(
        TransportTripLeg.trip_id == trip.id,
        TransportTripLeg.leg_type.in_(RETURN_LEG_TYPES),
    ).with_for_update().all()
    if not return_legs:
        raise conflict("RETURN_LEG_REQUIRED", "Chuyen chua co chang quay ve hoac backhaul.")
    open_delivery_leg = db.query(TransportTripLeg.id).filter(
        TransportTripLeg.trip_id == trip.id,
        TransportTripLeg.leg_type == "delivery",
        TransportTripLeg.status.notin_(("completed", "cancelled")),
    ).first()
    if open_delivery_leg:
        raise conflict("OPEN_DELIVERY_LEG", "Phai hoan tat POD cho tat ca chang giao truoc khi xac nhan xe quay ve.")
    linked_do_ids = [row[0] for row in db.query(TripDeliveryOrder.do_id).filter_by(trip_id=trip.id).all()]
    deliveries = db.query(DeliveryOrder).filter(DeliveryOrder.id.in_(linked_do_ids)).with_for_update().all()
    if any(item.canonical_status not in {"delivered", "cancelled"} for item in deliveries):
        raise conflict("OPEN_DELIVERY_ORDER", "Moi DO tren chuyen phai da giao hoac da huy.")

    actual_return_at = _datetime(data.get("actual_return_at"), "thoi diem xe quay ve")
    for leg in return_legs:
        if leg.status not in {"completed", "cancelled"}:
            leg.status = "completed"
            leg.actual_arrival_at = actual_return_at
    trip.status = "completed"
    trip.actual_return_at = actual_return_at
    trip.actual_arrival_at = actual_return_at
    trip.version += 1
    trip.updated_at = _now()
    trip.updated_by = actor
    freight_order = db.get(FreightOrder, trip.freight_order_id)
    if freight_order:
        freight_order.status = "delivered"
        freight_order.version += 1
        freight_order.updated_at = _now()
        freight_order.updated_by = actor
    assignments = db.query(ResourceAssignment).filter(
        ResourceAssignment.trip_id == trip.id,
        ResourceAssignment.status == "active",
    ).with_for_update().all()
    for assignment in assignments:
        assignment.status = "completed"
    from services.workflow_service import release_resources
    for delivery in deliveries:
        release_resources(db, delivery)
    _audit(db, "COMPLETE_TRANSPORT_TRIP_RETURN", "transport_trips", trip.id, actor)
    db.flush()
    return serialize_trip(db, trip)
