import datetime
import math
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_

from models import (
    AuditLog,
    Customer,
    DeliveryPODRecord,
    DeliveryOrder,
    Driver,
    FreightOrder,
    Incident,
    Quotation,
    ResourceAssignment,
    Route,
    SalesOrder,
    SalesOrderLine,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
    Vehicle,
    VehicleTracking,
)
from services.errors import DomainError, conflict, missing_master
from services.crew_policy import mark_crew_busy, mark_crew_ready, require_crew
from services.vehicle_capacity_policy import require_vehicle_capacity
from services.vehicle_recommendation_service import require_quotation_vehicle_capacity


READY_VEHICLE = "Sẵn sàng"
READY_DRIVER = "🟢 Rảnh (Sẵn sàng)"
UTC = datetime.timezone.utc
BUSINESS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


STATUS = {
    "quotation": {"draft": "Bản nháp", "approved": "Đã duyệt"},
    "sales_order": {"draft": "Bản nháp", "confirmed": "Đã xác nhận"},
    "delivery_order": {
        "pending": "Chờ vận chuyển",
        "in_transit": "Đang vận chuyển",
        "delivered": "Đã giao hàng",
        "cancelled": "Đã hủy",
    },
}

DO_ANALYSIS_STAGE = {
    "near_late": "Gần trễ",
    "pending": "Chờ vận chuyển",
    "active": "Đang vận chuyển",
    "completed": "Hoàn thành",
    "incident": "Gặp sự cố",
}


# --------------------------------------------------------------------------
# Dòng hàng hóa vận chuyển
# --------------------------------------------------------------------------

# Quy đổi đơn vị tính cước ra khối lượng / thể tích.
#
# Đây là chỗ dữ liệu người dùng gõ vào bảng "Hàng hóa vận chuyển" cuối cùng có
# tác dụng thật: `vehicle_capacity_policy` chặn điều xe quá tải dựa trên đúng
# hai con số này. Trước đây bảng dòng hàng không được lưu ở đâu cả, nên hai con
# số đó phải nhập tay ở chỗ khác — hoặc bị bỏ trống.
#
# "Chuyến" và "Km" là cách tính cước theo lần đi, không nói gì về khối lượng,
# nên cố ý không quy đổi.
_UOM_TO_KG = {"kg": 1, "tấn": 1000, "tan": 1000, "ton": 1000}
_UOM_TO_M3 = {"khối": 1, "khoi": 1, "m3": 1, "m³": 1, "cbm": 1}


def _line_quantity_split(uom, quantity):
    """Trả về (kg, m3) mà một dòng đóng góp vào tải trọng đơn hàng."""
    key = str(uom or "").strip().lower()
    for token, factor in _UOM_TO_KG.items():
        if key.startswith(token):
            return quantity * Decimal(factor), Decimal(0)
    for token in _UOM_TO_M3:
        if key.startswith(token):
            return Decimal(0), quantity
    return Decimal(0), Decimal(0)


# Quy cach va dieu kien van chuyen.
#
# Tab nay tung co sau o nhap ma khong co cot nao de chua, khong duoc gui len, va
# ban than cac o nhap con bi ban dich xoa mat. Ba tang cung hong mot cho.
# Ke thua sang don hang cung mot le voi quy cach van chuyen: cargo_type la loai
# phuong tien da chao cho khach, va cuoc mot chuyen tinh bang cong thuc cua LOAI
# XE — thieu no thi don van chuyen khong ap lai duoc cong thuc theo tai trong
# thuc te. Truoc day khong co cot nao, nen man don hang tinh tien bang
# `so km x 6250 + 800000`, hai con so khong co nguon nao.
SHIPPING_SPEC_FIELDS = (
    "cargo_type",
    "carrier_name",
    "delivery_method",
    "seal_weight",
    "temperature_requirement",
    "cargo_insurance",
    "warehouse_owner",
)


def _apply_shipping_spec(target, data):
    """Chi ghi nhung truong CO MAT trong payload.

    Giong ly do o POST /api/vehicles: gan mac dinh cho truong khong gui se xoa
    trang du lieu cu ma khong mot thong bao nao.
    """
    for field in SHIPPING_SPEC_FIELDS:
        if field in data:
            value = str(data.get(field) or "").strip()
            setattr(target, field, value[:255] or None)


def _inherit_shipping_spec(order, quotation):
    """Don hang ke thua quy cach tu bao gia da duyet.

    Day la dieu kien da chao cho khach o buoc bao gia — bat khai lai la vua mat
    cong vua de lech voi cai da chao.
    """
    if quotation is None:
        return
    for field in SHIPPING_SPEC_FIELDS:
        if not getattr(order, field, None):
            setattr(order, field, getattr(quotation, field, None))


def _line_decimal(value, field):
    """Doc mot so tien/so luong cua dong hang thanh Decimal.

    KHONG dung _money(): helper do tra ve float, ma cac cot nay la NUMERIC.
    Di qua float se tai lap dung sai so nhi phan ma v024_money_numeric da don.
    """
    if value in (None, ""):
        return Decimal(0)
    if isinstance(value, bool):
        raise DomainError("SO_LINE_INVALID", f"{field} khong hop le.", 422)
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("SO_LINE_INVALID", f"{field} khong hop le.", 422) from None
    if not result.is_finite():
        raise DomainError("SO_LINE_INVALID", f"{field} khong hop le.", 422)
    if result < 0:
        raise DomainError("SO_LINE_NEGATIVE", "So luong va don gia cuoc khong duoc am.", 422)
    if result.adjusted() + 1 > 18:
        raise DomainError("SO_LINE_TOO_LARGE", f"{field} vuot qua Numeric(24,6).", 422)
    return result


def _replace_sales_order_lines(db, so, rows):
    """Ghi lại toàn bộ dòng hàng của một đơn, rồi tính lại số tổng.

    Thay trọn bộ thay vì vá từng dòng: giao diện gửi lên cả bảng, và ghép từng
    dòng sẽ để lại dòng mồ côi khi người dùng xóa bớt.
    """
    if rows is None:
        return
    if not isinstance(rows, list):
        raise DomainError("SO_LINES_INVALID", "Danh sách hàng hóa vận chuyển phải là một mảng.", 422)
    if len(rows) > 200:
        raise DomainError("SO_LINES_TOO_MANY", "Một đơn hàng vận chuyển không được quá 200 dòng hàng.", 422)

    db.query(SalesOrderLine).filter(SalesOrderLine.so_id == so.id).delete(synchronize_session=False)

    total = Decimal(0)
    total_kg = Decimal(0)
    total_m3 = Decimal(0)
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise DomainError("SO_LINES_INVALID", "Mỗi dòng hàng phải là một đối tượng.", 422)
        quantity = _line_decimal(row.get("quantity"), "Số lượng")
        unit_price = _line_decimal(row.get("unit_price"), "Đơn giá cước")
        amount = quantity * unit_price
        uom = str(row.get("uom") or "Tấn").strip() or "Tấn"
        db.add(SalesOrderLine(
            id=f"{so.id}-L{index:03d}",
            so_id=so.id,
            line_no=index,
            description=str(row.get("description") or "").strip()[:500],
            quantity=quantity,
            uom=uom[:32],
            unit_price=unit_price,
            amount=amount,
        ))
        total += amount
        kg, m3 = _line_quantity_split(uom, quantity)
        total_kg += kg
        total_m3 += m3

    # Số tổng được TÍNH LẠI từ các dòng, không nhận từ giao diện: nếu nhận thì
    # tổng và các dòng có thể nói hai con số khác nhau.
    so.total_amount = total
    if total_kg:
        so.weight_kg = float(total_kg)
    if total_m3:
        so.volume_m3 = float(total_m3)


def serialize_sales_order_lines(db, so_id):
    rows = (
        db.query(SalesOrderLine)
        .filter(SalesOrderLine.so_id == so_id)
        .order_by(SalesOrderLine.line_no)
        .all()
    )
    return [
        {
            "line_no": row.line_no,
            "description": row.description or "",
            "quantity": float(row.quantity or 0),
            "uom": row.uom,
            "unit_price": float(row.unit_price or 0),
            "amount": float(row.amount or 0),
        }
        for row in rows
    ]

def _parse_business_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        parsed = value
        naive_timezone = UTC
    elif isinstance(value, datetime.date):
        parsed = datetime.datetime.combine(value, datetime.time.min)
        naive_timezone = BUSINESS_TIMEZONE
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        naive_timezone = BUSINESS_TIMEZONE
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=naive_timezone)
    return parsed.astimezone(UTC)


def _aware_utc(value=None):
    return _parse_business_datetime(value or datetime.datetime.now(UTC))


def _delivery_order_due_at(order):
    for value in (
        order.planned_departure_at,
        order.pickup_window_start,
        order.pickup_date,
        order.delivery_window_start,
        order.delivery_date,
        order.delivery_window_end,
        order.planned_arrival_at,
    ):
        parsed = _parse_business_datetime(value)
        if parsed:
            return parsed
    return None


def _delivery_order_analysis_record(order, pod_counts, incident_counts, now, near_late_hours=24):
    key = (order.canonical_status or order.status or "unknown").strip().lower()
    due_at = _delivery_order_due_at(order)
    has_open_incident = bool(incident_counts.get(order.id, 0))

    if has_open_incident:
        stage = "incident"
    elif key in {"delivered", "completed", "settled", "posted"}:
        stage = "completed"
    elif key in {"dispatched", "in_transit", "arrived"}:
        stage = "active"
    else:
        stage = "pending"

    is_overdue = bool(stage == "pending" and due_at and due_at < now)
    is_near_late = bool(
        stage == "pending"
        and due_at
        and now <= due_at
        and due_at <= now + datetime.timedelta(hours=near_late_hours)
    )
    if is_near_late:
        stage = "near_late"
    operational_status = DO_ANALYSIS_STAGE[stage]

    reason = {
        "near_late": "DO chưa vận chuyển và thời điểm lấy/giao nằm trong 24 giờ tới.",
        "completed": "DO đã giao/hoàn tất hoặc đã hạch toán.",
        "active": "DO đã được điều phối xe và đang trong quá trình vận chuyển.",
        "pending": "DO đã lập kế hoạch hoặc đã đủ điều kiện điều phối, nhưng chưa có xe đang chạy.",
        "incident": "DO đang có sự cố vận hành chưa được xử lý.",
    }[stage]

    return {
        "id": order.id,
        "stage": stage,
        "operational_status": operational_status,
        "canonical_status": key,
        "source_status": order.status,
        "due_at": due_at.isoformat() if due_at else None,
        "due_at_local": due_at.astimezone(BUSINESS_TIMEZONE).isoformat() if due_at else None,
        "is_near_late": is_near_late,
        "is_overdue": is_overdue,
        "has_open_incident": has_open_incident,
        "open_incident_count": incident_counts.get(order.id, 0),
        "has_pod": bool(pod_counts.get(order.id, 0)),
        "pod_count": pod_counts.get(order.id, 0),
        "reason": reason,
    }


def delivery_order_analysis(db, near_late_hours=24, now=None):
    now = _aware_utc(now)
    rows = db.query(
        DeliveryPODRecord.do_id,
        func.count(DeliveryPODRecord.id),
    ).group_by(DeliveryPODRecord.do_id).all()
    pod_counts = {do_id: int(count or 0) for do_id, count in rows}
    incident_rows = db.query(
        Incident.do_id,
        func.count(Incident.id),
    ).filter(
        ~func.lower(func.coalesce(Incident.status, "")).in_({"resolved", "closed", "completed"})
    ).group_by(Incident.do_id).all()
    incident_counts = {do_id: int(count or 0) for do_id, count in incident_rows if do_id}
    orders = db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc()).limit(500).all()
    records = [
        _delivery_order_analysis_record(order, pod_counts, incident_counts, now, near_late_hours)
        for order in orders
    ]
    buckets = {
        "near_late": {"label": "Gần trễ", "count": 0, "record_ids": []},
        "pending": {"label": "Chờ vận chuyển", "count": 0, "record_ids": []},
        "active": {"label": "Đang vận chuyển", "count": 0, "arrived": 0, "record_ids": []},
        "completed": {"label": "Hoàn thành", "count": 0, "with_pod": 0, "record_ids": []},
        "incident": {"label": "Gặp sự cố", "count": 0, "open_incidents": 0, "record_ids": []},
    }
    for record in records:
        bucket = buckets[record["stage"]]
        bucket["count"] += 1
        bucket["record_ids"].append(record["id"])
        if record["stage"] == "active" and record["canonical_status"] == "arrived":
            bucket["arrived"] += 1
        if record["stage"] == "completed" and record["has_pod"]:
            bucket["with_pod"] += 1
        if record["stage"] == "incident":
            bucket["open_incidents"] += record["open_incident_count"]
    return {
        "generated_at": now.isoformat(),
        "near_late_hours": near_late_hours,
        "logic": {
            "near_late": "pending và hạn lấy/giao nằm từ hiện tại đến hết 24 giờ tới.",
            "pending": "pending: chờ vận chuyển; đơn quá hạn có cờ is_overdue riêng.",
            "active": "in_transit: đã điều phối và đang vận chuyển.",
            "completed": "delivered/completed/settled/posted: đã giao hoặc hoàn tất.",
            "incident": "Có incident theo do_id với status chưa resolved/closed/completed.",
        },
        "buckets": buckets,
        "records": records,
    }


def _now():
    return datetime.datetime.utcnow()


def _next_id(db, model, prefix):
    year = datetime.datetime.now().year
    like = f"{prefix}-{year}-%"
    last = db.query(model.id).filter(model.id.like(like)).order_by(model.id.desc()).first()
    seq = int(last[0].split("-")[-1]) + 1 if last else 1
    return f"{prefix}-{year}-{seq:03d}"


def _audit(db, action, table, record_id, user="system", ip_address=None):
    db.add(AuditLog(user_id=user, action=action, table_name=table, record_id=record_id, timestamp=_now(), ip_address=ip_address or db.info.get("audit_ip")))


def _money(data, name, default=0):
    try:
        value = float(data.get(name, default) or 0)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không hợp lệ.", 422) from None
    if not math.isfinite(value) or value < 0:
        raise DomainError("INVALID_VALUE", f"Giá trị {name} phải là số hữu hạn không âm.", 422)
    return value


def _parse_datetime(value, default=None):
    if not value:
        return default
    if isinstance(value, datetime.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise DomainError("INVALID_DATETIME", "Thời gian không hợp lệ.", 422) from None


def _positive_float(data, name, default):
    raw = data.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không hợp lệ.", 422) from None
    if not math.isfinite(value) or value <= 0:
        raise DomainError("INVALID_VALUE", f"Giá trị {name} phải là số hữu hạn dương.", 422)
    return value


def _nonnegative_int(data, name, default=0):
    raw = data.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không hợp lệ.", 422) from None
    if value < 0:
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không được âm.", 422)
    return value


def estimate_delivery_timing(
    distance_km,
    departure_at=None,
    avg_speed_kmh=45,
    load_minutes=0,
    unload_minutes=0,
    return_speed_kmh=None,
    return_distance_km=None,
):
    distance = float(distance_km or 0)
    if distance < 0 or not math.isfinite(distance):
        raise DomainError("INVALID_DISTANCE", "Quãng đường không hợp lệ.", 422)
    avg_speed = float(avg_speed_kmh or 45)
    return_speed = float(return_speed_kmh or avg_speed)
    if avg_speed <= 0 or return_speed <= 0:
        raise DomainError("INVALID_SPEED", "Vận tốc trung bình phải lớn hơn 0.", 422)
    start = _parse_datetime(departure_at, _now())
    load = int(load_minutes or 0)
    unload = int(unload_minutes or 0)
    return_distance = distance if return_distance_km in (None, "") else float(return_distance_km)
    arrival = start + datetime.timedelta(minutes=load, hours=distance / avg_speed)
    planned_return = arrival + datetime.timedelta(minutes=unload, hours=return_distance / return_speed)
    return {
        "planned_departure_at": start,
        "planned_arrival_at": arrival.replace(second=0, microsecond=0),
        "planned_return_at": planned_return.replace(second=0, microsecond=0),
        "distance_km": distance,
        "avg_speed_kmh": avg_speed,
        "return_speed_kmh": return_speed,
        "return_distance_km": return_distance,
    }


def _iso(dt_value):
    if not dt_value:
        return ""
    value = dt_value.replace(second=0, microsecond=0)
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _require(db, model, pk, entity, label):
    if not pk:
        raise missing_master(entity, label)
    row = db.query(model).filter(model.id == pk).first()
    if not row:
        raise missing_master(entity, label)
    return row


def _route_label(route):
    return (getattr(route, "name", None) or getattr(route, "id", "") or "").strip()


def _route_context_from_quote(q, route, data=None):
    data = data or {}
    fallback = _route_label(route)
    return {
        "route_id": data.get("route_id") or q.route_id,
        "origin": data.get("origin") or q.origin or fallback,
        "destination": data.get("destination") or q.destination or fallback,
        "pickup_window_start": data.get("pickup_window_start") or q.pickup_window_start,
        "pickup_window_end": data.get("pickup_window_end") or q.pickup_window_end,
        "delivery_window_start": data.get("delivery_window_start") or q.delivery_window_start,
        "delivery_window_end": data.get("delivery_window_end") or q.delivery_window_end,
        "weight_kg": _money(data, "weight_kg", q.weight_kg or 0),
        "pallet_count": _nonnegative_int(data, "pallet_count", q.pallet_count or 0),
    }


def create_quotation(db, data, user="system"):
    customer = _require(db, Customer, data.get("customer_id"), "customer", "khách hàng")
    route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
    require_quotation_vehicle_capacity(db, data)
    q = Quotation(
        id=data.get("id") or _next_id(db, Quotation, "QT"),
        customer_id=customer.id,
        route_id=route.id,
        origin=data.get("origin") or _route_label(route),
        destination=data.get("destination") or _route_label(route),
        pickup_window_start=data.get("pickup_window_start") or "",
        pickup_window_end=data.get("pickup_window_end") or "",
        delivery_window_start=data.get("delivery_window_start") or "",
        delivery_window_end=data.get("delivery_window_end") or "",
        weight_kg=_money(data, "weight_kg"),
        pallet_count=_nonnegative_int(data, "pallet_count", 0),
        cargo_type=data.get("cargo_type") or "",
        valid_to=data.get("valid_to") or "",
        fuel_cost=_money(data, "fuel_cost"),
        driver_cost=_money(data, "driver_cost"),
        toll_fee=_money(data, "toll_fee"),
        total_cost=_money(data, "total_cost"),
        selling_price=_money(data, "selling_price"),
        packaging_spec=data.get("packaging_spec") or "",
        volume_m3=_money(data, "volume_m3"),
        status=STATUS["quotation"]["draft"],
        canonical_status="draft",
        created_by=user,
        updated_by=user,
    )
    db.add(q)
    _audit(db, "CREATE_QUOTATION", "quotations", q.id, user)
    return q


def approve_quotation(db, qid, user="system"):
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", f"Không tìm thấy báo giá {qid}", 404)
    if q.canonical_status not in ("draft", "sent", "unknown"):
        raise conflict("INVALID_TRANSITION", "Chỉ báo giá bản nháp/chờ gửi mới được duyệt.")
    require_quotation_vehicle_capacity(db, {
        "cargo_type": q.cargo_type,
        "weight_kg": q.weight_kg,
        "volume_m3": q.volume_m3,
        "pallet_count": q.pallet_count,
    })
    q.status = STATUS["quotation"]["approved"]
    q.canonical_status = "approved"
    q.updated_by = user
    q.updated_at = _now()
    q.version = (q.version or 1) + 1
    _audit(db, "APPROVE_QUOTATION", "quotations", q.id, user)
    return q


def update_quotation(db, qid, data, user="system"):
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", f"Không tìm thấy báo giá {qid}", 404)
    if q.canonical_status not in ("draft", "sent", "unknown"):
        raise conflict("LOCKED_RECORD", "Báo giá đã duyệt chỉ được xem, không được sửa.", ["quotations"])
    if data.get("customer_id"):
        customer = _require(db, Customer, data.get("customer_id"), "customer", "khách hàng")
        q.customer_id = customer.id
    if data.get("route_id"):
        route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
        q.route_id = route.id
    else:
        route = db.query(Route).filter(Route.id == q.route_id).first()
    fallback = _route_label(route) if route else ""
    q.origin = data.get("origin", q.origin) or fallback
    q.destination = data.get("destination", q.destination) or fallback
    q.pickup_window_start = data.get("pickup_window_start", q.pickup_window_start) or ""
    q.pickup_window_end = data.get("pickup_window_end", q.pickup_window_end) or ""
    q.delivery_window_start = data.get("delivery_window_start", q.delivery_window_start) or ""
    q.delivery_window_end = data.get("delivery_window_end", q.delivery_window_end) or ""
    q.weight_kg = _money(data, "weight_kg", q.weight_kg or 0)
    q.pallet_count = _nonnegative_int(data, "pallet_count", q.pallet_count or 0)
    if "cargo_type" in data:
        q.cargo_type = data.get("cargo_type") or ""
    if "valid_to" in data:
        q.valid_to = data.get("valid_to") or ""
    q.fuel_cost = _money(data, "fuel_cost", q.fuel_cost or 0)
    q.driver_cost = _money(data, "driver_cost", q.driver_cost or 0)
    q.toll_fee = _money(data, "toll_fee", q.toll_fee or 0)
    q.total_cost = _money(data, "total_cost", q.total_cost or 0)
    q.selling_price = _money(data, "selling_price", q.selling_price or 0)
    if "packaging_spec" in data:
        q.packaging_spec = data.get("packaging_spec") or ""
    q.volume_m3 = _money(data, "volume_m3", q.volume_m3 or 0)
    require_quotation_vehicle_capacity(db, {
        "cargo_type": q.cargo_type,
        "weight_kg": q.weight_kg,
        "volume_m3": q.volume_m3,
        "pallet_count": q.pallet_count,
    })
    q.updated_by = user
    q.updated_at = _now()
    q.version = (q.version or 1) + 1
    _audit(db, "UPDATE_QUOTATION", "quotations", q.id, user)
    return q


def create_sales_order(db, data, user="system"):
    qid = data.get("quotation_id")
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá nguồn để tạo đơn hàng.", 404)
    if q.canonical_status != "approved":
        raise DomainError("QUOTATION_NOT_APPROVED", "Báo giá phải được duyệt trước khi tạo đơn hàng.")
    route = _require(db, Route, q.route_id, "route", "tuyến đường")
    route_context = _route_context_from_quote(q, route, data)
    so = SalesOrder(
        id=data.get("id") or q.id.replace("QT-", "SO-", 1),
        quotation_id=q.id,
        customer_id=q.customer_id,
        route_id=route_context["route_id"],
        origin=route_context["origin"],
        destination=route_context["destination"],
        pickup_window_start=route_context["pickup_window_start"],
        pickup_window_end=route_context["pickup_window_end"],
        delivery_window_start=route_context["delivery_window_start"],
        delivery_window_end=route_context["delivery_window_end"],
        weight_kg=route_context["weight_kg"],
        pallet_count=route_context["pallet_count"],
        total_amount=_money(data, "total_amount", q.selling_price or 0),
        packaging_spec=q.packaging_spec,
        volume_m3=q.volume_m3,
        status=STATUS["sales_order"]["draft"],
        canonical_status="draft",
        order_date=data.get("order_date") or datetime.date.today().isoformat(),
        currency_code=data.get("currency_code") or "VND",
        created_by=user,
        updated_by=user,
    )
    # Don hang ke thua quy cach van chuyen tu bao gia da duyet — day la dieu
    # kien da chao cho khach, bat khai lai la vua mat cong vua de lech voi cai
    # da chao.
    _inherit_shipping_spec(so, q)
    _apply_shipping_spec(so, data)
    db.add(so)
    _audit(db, "CREATE_SALES_ORDER", "sales_orders", so.id, user)
    return so


def update_sales_order(db, so_id, data, user="system"):
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).with_for_update().first()
    if not so:
        raise DomainError("SALES_ORDER_NOT_FOUND", f"Không tìm thấy đơn hàng {so_id}", 404)
    if so.canonical_status != "draft":
        raise conflict("LOCKED_RECORD", "Đơn hàng đã xác nhận chỉ được xem, không được sửa.", ["sales-orders"])
    if data.get("route_id"):
        route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
        so.route_id = route.id
    else:
        route = db.query(Route).filter(Route.id == so.route_id).first()
    fallback = _route_label(route) if route else ""
    so.origin = data.get("origin", so.origin) or fallback
    so.destination = data.get("destination", so.destination) or fallback
    so.pickup_window_start = data.get("pickup_window_start", so.pickup_window_start) or ""
    so.pickup_window_end = data.get("pickup_window_end", so.pickup_window_end) or ""
    so.delivery_window_start = data.get("delivery_window_start", so.delivery_window_start) or ""
    so.delivery_window_end = data.get("delivery_window_end", so.delivery_window_end) or ""
    so.weight_kg = _money(data, "weight_kg", so.weight_kg or 0)
    # Dong hang duoc ghi SAU cac truong tong, vi no tinh lai tong tu cac dong.
    _apply_shipping_spec(so, data)
    _replace_sales_order_lines(db, so, data.get("lines"))
    so.pallet_count = _nonnegative_int(data, "pallet_count", so.pallet_count or 0)
    so.total_amount = _money(data, "total_amount", so.total_amount or 0)
    if "currency_code" in data:
        so.currency_code = data.get("currency_code") or "VND"
    if "packaging_spec" in data:
        so.packaging_spec = data.get("packaging_spec") or ""
    so.volume_m3 = _money(data, "volume_m3", so.volume_m3 or 0)
    so.updated_by = user
    so.updated_at = _now()
    so.version = (so.version or 1) + 1
    _audit(db, "UPDATE_SALES_ORDER", "sales_orders", so.id, user)
    return so


def confirm_sales_order(db, so_id, user="system"):
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).with_for_update().first()
    if not so:
        raise DomainError("SALES_ORDER_NOT_FOUND", f"Không tìm thấy đơn hàng {so_id}", 404)
    if so.canonical_status != "draft":
        raise conflict("INVALID_TRANSITION", "Chỉ đơn hàng bản nháp mới được xác nhận.")
    so.status = STATUS["sales_order"]["confirmed"]
    so.canonical_status = "confirmed"
    so.updated_by = user
    so.updated_at = _now()
    so.version = (so.version or 1) + 1
    _audit(db, "CONFIRM_SALES_ORDER", "sales_orders", so.id, user)
    return so


def delete_quotation(db, qid, user="system"):
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", f"Không tìm thấy báo giá {qid}", 404)
    if q.canonical_status not in ("draft", "sent", "unknown"):
        raise conflict("LOCKED_RECORD", "Báo giá đã duyệt chỉ được xem, không được xóa.", ["quotations"])
    db.delete(q)
    _audit(db, "DELETE_QUOTATION", "quotations", qid, user)
    return q


def delete_sales_order(db, so_id, user="system"):
    so = db.query(SalesOrder).filter(SalesOrder.id == so_id).with_for_update().first()
    if not so:
        raise DomainError("SALES_ORDER_NOT_FOUND", f"Không tìm thấy đơn hàng {so_id}", 404)
    if so.canonical_status != "draft":
        raise conflict("LOCKED_RECORD", "Đơn hàng đã xác nhận chỉ được xem, không được xóa.", ["sales-orders"])
    db.delete(so)
    _audit(db, "DELETE_SALES_ORDER", "sales_orders", so_id, user)
    return so


def create_delivery_order(db, data, user="system"):
    so = db.query(SalesOrder).filter(SalesOrder.id == data.get("so_id")).first()
    if not so:
        raise DomainError("SALES_ORDER_NOT_FOUND", "Không tìm thấy đơn hàng nguồn để tạo lệnh giao hàng.", 404)
    if so.canonical_status != "confirmed":
        raise DomainError("SALES_ORDER_NOT_CONFIRMED", "Đơn hàng phải được xác nhận trước khi tạo lệnh giao hàng.")
    route_id = data.get("route_id") or so.route_id
    route = _require(db, Route, route_id, "route", "tuyến đường")
    do = DeliveryOrder(
        id=data.get("id") or so.id.replace("SO-", "DO-", 1),
        so_id=so.id,
        customer_id=so.customer_id,
        route_id=route_id,
        origin=data.get("origin") or so.origin or _route_label(route),
        destination=data.get("destination") or so.destination or _route_label(route),
        pickup_window_start=_parse_business_datetime(data.get("pickup_window_start") or so.pickup_window_start),
        pickup_window_end=_parse_business_datetime(data.get("pickup_window_end") or so.pickup_window_end),
        delivery_window_start=_parse_business_datetime(data.get("delivery_window_start") or so.delivery_window_start),
        delivery_window_end=_parse_business_datetime(data.get("delivery_window_end") or so.delivery_window_end),
        weight_kg=_money(data, "weight_kg", so.weight_kg or 0),
        pallet_count=_nonnegative_int(data, "pallet_count", so.pallet_count or 0),
        pickup_date=_parse_business_datetime(data.get("pickup_date") or so.pickup_window_start),
        delivery_date=_parse_business_datetime(data.get("delivery_date") or so.delivery_window_end or so.delivery_date),
        packaging_spec=so.packaging_spec,
        volume_m3=so.volume_m3,
        status=STATUS["delivery_order"]["pending"],
        canonical_status="pending",
        created_by=user,
        updated_by=user,
    )
    db.add(do)
    _audit(db, "CREATE_DELIVERY_ORDER", "delivery_orders", do.id, user)
    return do


def update_delivery_order(db, do_id, data, user="system"):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    if do.canonical_status != "pending":
        raise conflict("LOCKED_RECORD", "Lệnh giao hàng đang vận chuyển hoặc đã kết thúc chỉ được xem, không được sửa.", ["delivery-orders"])
    if data.get("route_id"):
        route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
        do.route_id = route.id
    else:
        route = db.query(Route).filter(Route.id == do.route_id).first()
    fallback = _route_label(route) if route else ""
    do.origin = data.get("origin", do.origin) or fallback
    do.destination = data.get("destination", do.destination) or fallback
    if "pickup_window_start" in data:
        do.pickup_window_start = _parse_business_datetime(data.get("pickup_window_start"))
    if "pickup_window_end" in data:
        do.pickup_window_end = _parse_business_datetime(data.get("pickup_window_end"))
    if "delivery_window_start" in data:
        do.delivery_window_start = _parse_business_datetime(data.get("delivery_window_start"))
    if "delivery_window_end" in data:
        do.delivery_window_end = _parse_business_datetime(data.get("delivery_window_end"))
    do.weight_kg = _money(data, "weight_kg", do.weight_kg or 0)
    do.pallet_count = _nonnegative_int(data, "pallet_count", do.pallet_count or 0)
    if "pickup_date" in data:
        do.pickup_date = _parse_business_datetime(data.get("pickup_date"))
    if "delivery_date" in data:
        do.delivery_date = _parse_business_datetime(data.get("delivery_date"))
    if "packaging_spec" in data:
        do.packaging_spec = data.get("packaging_spec") or ""
    do.volume_m3 = _money(data, "volume_m3", do.volume_m3 or 0)
    do.updated_by = user
    do.updated_at = _now()
    do.version = (do.version or 1) + 1
    _audit(db, "UPDATE_DELIVERY_ORDER", "delivery_orders", do.id, user)
    return do


def delete_delivery_order(db, do_id, user="system"):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    if do.canonical_status != "pending":
        raise conflict("LOCKED_RECORD", "Lệnh giao hàng đang vận chuyển hoặc đã kết thúc chỉ được xem, không được xóa.", ["delivery-orders"])
    db.delete(do)
    _audit(db, "DELETE_DELIVERY_ORDER", "delivery_orders", do_id, user)
    return do


def update_delivery_status(db, do_id, status, user="system"):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    allowed = {
        "pending": {"in_transit", "cancelled"},
        "in_transit": {"delivered"},
    }
    if status not in allowed.get(do.canonical_status, set()):
        raise conflict("INVALID_TRANSITION", f"Không thể chuyển từ {do.status} sang {status}.")
    if status == "cancelled":
        active_trip = db.query(TransportTrip.id).join(
            TripDeliveryOrder,
            TripDeliveryOrder.trip_id == TransportTrip.id,
        ).filter(
            TripDeliveryOrder.do_id == do.id,
            ~TransportTrip.status.in_(("completed", "cancelled")),
        ).first()
        if active_trip:
            raise conflict(
                "ACTIVE_TRIP_EXISTS",
                "Không thể hủy lệnh giao hàng khi còn chuyến vận tải đang hoạt động.",
                ["transport-trips"],
            )
    if status == "delivered":
        has_pod = db.query(DeliveryPODRecord.id).filter(
            DeliveryPODRecord.do_id == do.id,
            DeliveryPODRecord.vehicle_id == do.vehicle_id,
        ).first()
        if not has_pod:
            raise DomainError("POD_REQUIRED", "Cần cập nhật POD cho xe đang giao trước khi hoàn tất giao hàng.")
    do.canonical_status = status
    do.status = STATUS["delivery_order"][status]
    do.updated_by = user
    do.updated_at = _now()
    do.version = (do.version or 1) + 1
    if status == "delivered":
        release_resources(db, do)
    _audit(db, f"DELIVERY_{status.upper()}", "delivery_orders", do.id, user)
    return do


def dispatch(db, do_id, data, user="system"):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    if do.canonical_status != "pending":
        raise conflict("INVALID_TRANSITION", "Chỉ lệnh giao hàng đang chờ vận chuyển mới được điều phối.")
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.get("vehicle_id")).with_for_update().first()
    driver = db.query(Driver).filter(Driver.id == data.get("driver_id")).with_for_update().first()
    co_driver_id = str(data.get("co_driver_id") or "").strip() or None
    co_driver = None
    if co_driver_id:
        co_driver = db.query(Driver).filter(Driver.id == co_driver_id).with_for_update().first()
    if not vehicle:
        raise missing_master("vehicle", "phương tiện")
    if not driver:
        raise missing_master("driver", "tài xế")
    if co_driver_id and not co_driver:
        raise missing_master("driver", "phụ xe")
    require_crew(driver, co_driver)
    crew_ids = [driver.id] + ([co_driver.id] if co_driver else [])
    active = db.query(DeliveryOrder.id).filter(
        DeliveryOrder.id != do.id,
        DeliveryOrder.canonical_status == "in_transit",
        or_(
            DeliveryOrder.vehicle_id == vehicle.id,
            DeliveryOrder.driver_id.in_(crew_ids),
            DeliveryOrder.co_driver.in_(crew_ids),
        ),
    ).first()
    if active:
        raise conflict("RESOURCE_BUSY", "Phương tiện hoặc tài xế đang được gán cho lệnh giao hàng khác.", ["delivery-orders"])
    if vehicle.status != READY_VEHICLE:
        raise DomainError("VEHICLE_BUSY", f"Xe {vehicle.id} đang bận, vui lòng chọn xe khác.", 409, ["master-data/vehicles"])
    require_vehicle_capacity(
        vehicle,
        weight_kg=do.weight_kg,
        volume_m3=do.volume_m3,
        pallet_count=do.pallet_count,
        subject=f"DO {do.id}",
    )
    route = db.query(Route).filter(Route.id == do.route_id).first()
    distance = float(getattr(route, "distance_km", 0) or 0)
    avg_speed = _positive_float(data, "avg_speed_kmh", 45)
    return_speed = _positive_float(data, "return_speed_kmh", avg_speed)
    load_minutes = _nonnegative_int(data, "load_minutes", 0)
    unload_minutes = _nonnegative_int(data, "unload_minutes", 0)
    timing = estimate_delivery_timing(
        distance_km=distance,
        departure_at=data.get("departure_at") or data.get("planned_departure_at") or _now(),
        avg_speed_kmh=avg_speed,
        load_minutes=load_minutes,
        unload_minutes=unload_minutes,
        return_speed_kmh=return_speed,
        return_distance_km=data.get("return_distance_km", distance),
    )
    do.vehicle_id = vehicle.id
    do.driver_id = driver.id
    do.co_driver = co_driver.id if co_driver else None
    if data.get("packaging_spec") is not None:
        do.packaging_spec = data.get("packaging_spec") or ""
    if data.get("volume_m3") is not None:
        do.volume_m3 = _money(data, "volume_m3", do.volume_m3 or 0)
    do.planned_departure_at = _aware_utc(timing["planned_departure_at"])
    do.planned_arrival_at = _aware_utc(timing["planned_arrival_at"])
    do.planned_return_at = _aware_utc(timing["planned_return_at"])
    do.avg_speed_kmh = avg_speed
    do.max_speed_kmh = _money(data, "max_speed_kmh", 0) or None
    do.return_speed_kmh = return_speed
    do.load_minutes = load_minutes
    do.unload_minutes = unload_minutes
    do.return_distance_km = timing["return_distance_km"]
    vehicle.status = f"Đang vận chuyển đơn {do.id}"
    mark_crew_busy(driver, vehicle.id, do.id)
    if co_driver:
        mark_crew_busy(co_driver, vehicle.id, do.id)
    do.canonical_status = "in_transit"
    do.status = STATUS["delivery_order"]["in_transit"]
    do.updated_by = user
    do.updated_at = _now()
    do.version = (do.version or 1) + 1
    tracking = db.get(VehicleTracking, do.id) or VehicleTracking(do_id=do.id)
    tracking.vehicle_id = vehicle.id
    tracking.lat = None
    tracking.lng = None
    tracking.speed_kmh = 0
    tracking.remaining_distance_km = distance
    tracking.eta = _iso(do.planned_arrival_at)
    tracking.planned_return_at = _iso(do.planned_return_at)
    tracking.last_update = _now()
    db.add(tracking)
    _audit(db, "DISPATCH_DELIVERY", "delivery_orders", do.id, user)
    return do


def _pod_record_payload(record):
    return {
        "id": record.id,
        "do_id": record.do_id,
        "trip_id": record.trip_id,
        "leg_id": record.leg_id,
        "vehicle_id": record.vehicle_id,
        "driver_id": record.driver_id,
        "stop_no": record.stop_no,
        "location_text": record.location_text,
        "receiver_name": record.receiver_name,
        "receiver_phone": record.receiver_phone,
        "delivery_time": record.delivery_time,
        "photo_url": record.photo_url,
        "signature_url": record.signature_url,
        "note": record.note,
        "status": record.status,
    }


def list_pod_records(db, do_id):
    return db.query(DeliveryPODRecord).filter(DeliveryPODRecord.do_id == do_id).order_by(
        DeliveryPODRecord.stop_no.asc(), DeliveryPODRecord.id.asc()
    ).all()


def save_pod(db, do_id, data, user="system"):
    idempotency_key = str(data.get("idempotency_key") or "").strip()
    if not idempotency_key:
        raise DomainError("IDEMPOTENCY_KEY_REQUIRED", "Thiếu Idempotency-Key khi lưu POD.", 422)
    existing = db.query(DeliveryPODRecord).filter(
        DeliveryPODRecord.idempotency_key == idempotency_key
    ).first()
    if existing:
        if (existing.do_id == do_id and existing.trip_id == data.get("trip_id")
                and existing.leg_id == data.get("leg_id") and existing.vehicle_id == data.get("vehicle_id")
                and existing.stop_no == data.get("stop_no")):
            return existing
        raise conflict("IDEMPOTENCY_CONFLICT", "Idempotency-Key đã được dùng cho POD khác.")
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    if do.canonical_status != "in_transit":
        raise conflict("INVALID_TRANSITION", "Chỉ cập nhật POD khi đơn đang vận chuyển hoặc đã đến nơi.")
    trip = db.query(TransportTrip).filter(
        TransportTrip.id == data.get("trip_id")
    ).with_for_update().first()
    if not trip or trip.status != "in_transit":
        raise conflict("TRIP_NOT_IN_TRANSIT", "POD chỉ được ghi cho chuyến đang vận chuyển.")
    membership = db.query(TripDeliveryOrder).filter_by(trip_id=trip.id, do_id=do.id).first()
    leg = db.query(TransportTripLeg).filter_by(id=data.get("leg_id"), trip_id=trip.id).first()
    if not membership or not leg or leg.do_id != do.id:
        raise conflict("POD_LINEAGE_INVALID", "Trip, chặng và DO của POD không khớp nhau.")
    assignment = db.query(ResourceAssignment).filter_by(trip_id=trip.id, status="active").first()
    if (not assignment or assignment.vehicle_id != data.get("vehicle_id")
            or trip.vehicle_id != data.get("vehicle_id") or do.vehicle_id != data.get("vehicle_id")):
        raise conflict("POD_RESOURCE_MISMATCH", "Xe của POD không khớp phân công chuyến.")
    record = DeliveryPODRecord(
        idempotency_key=idempotency_key,
        do_id=do_id,
        trip_id=trip.id,
        leg_id=leg.id,
        vehicle_id=assignment.vehicle_id,
        driver_id=assignment.driver_id,
        stop_no=data.get("stop_no"),
        location_text=data.get("location_text"),
        receiver_name=data.get("receiver_name"),
        receiver_phone=data.get("receiver_phone"),
        delivery_time=data.get("delivery_time"),
        photo_url=data.get("photo_url"),
        signature_url=data.get("signature_url"),
        note=data.get("note") or "",
        status=data.get("status") or "completed",
        created_by=user,
    )
    db.add(record)
    db.flush()
    if record.status == "completed":
        leg.status = "completed"
        leg.actual_arrival_at = record.delivery_time
        db.flush()
        active_trip_ids = {
            row[0] for row in db.query(TripDeliveryOrder.trip_id)
            .join(TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id)
            .filter(
                TripDeliveryOrder.do_id == do.id,
                TransportTrip.status != "cancelled",
            ).all()
        }
        required_legs = db.query(TransportTripLeg.id).filter(
            TransportTripLeg.trip_id.in_(active_trip_ids),
            TransportTripLeg.do_id == do.id,
            TransportTripLeg.status != "cancelled",
        ).all()
        completed_leg_ids = {
            row[0] for row in db.query(DeliveryPODRecord.leg_id).filter(
                DeliveryPODRecord.trip_id.in_(active_trip_ids),
                DeliveryPODRecord.do_id == do.id,
                DeliveryPODRecord.status == "completed",
            ).all()
        }
        if {row[0] for row in required_legs} <= completed_leg_ids:
            do.canonical_status = "delivered"
            do.status = "Hoàn thành"
            do.delivery_date = record.delivery_time
            do.version += 1
            do.updated_at = _now()
            do.updated_by = user
        open_legs = db.query(TransportTripLeg.id).filter(
            TransportTripLeg.trip_id == trip.id,
            TransportTripLeg.status.notin_(("completed", "cancelled")),
        ).first()
        if not open_legs:
            trip.status = "completed"
            trip.actual_arrival_at = record.delivery_time
            trip.version += 1
            trip.updated_at = datetime.datetime.now(UTC)
            trip.updated_by = user
            freight_order = db.get(FreightOrder, trip.freight_order_id)
            if freight_order:
                freight_order.status = "delivered"
                freight_order.version += 1
                freight_order.updated_at = _now()
                freight_order.updated_by = user
            assignment.status = "completed"
            release_resources(db, do)
    elif record.status == "rejected":
        db.add(Incident(
            do_id=do.id,
            vehicle_id=assignment.vehicle_id,
            incident_type="POD_REJECTED",
            severity="High",
            location=record.location_text,
            description=record.note or "POD bị từ chối, cần điều phối xử lý.",
            reporter=user,
            reported_at=record.delivery_time.isoformat() if record.delivery_time else None,
            status="Pending",
        ))
    _audit(db, "SAVE_POD", "delivery_pod_records", do.id, user)
    return record


def release_resources(db, do):
    if do.vehicle_id:
        active_vehicle = db.query(func.count(DeliveryOrder.id)).filter(
            DeliveryOrder.id != do.id,
            DeliveryOrder.canonical_status == "in_transit",
            DeliveryOrder.vehicle_id == do.vehicle_id,
        ).scalar()
        if not active_vehicle:
            vehicle = db.query(Vehicle).filter(Vehicle.id == do.vehicle_id).first()
            if vehicle:
                vehicle.status = READY_VEHICLE
    for crew_id in {do.driver_id, do.co_driver} - {None, ""}:
        active_crew = db.query(func.count(DeliveryOrder.id)).filter(
            DeliveryOrder.id != do.id,
            DeliveryOrder.canonical_status == "in_transit",
            or_(DeliveryOrder.driver_id == crew_id, DeliveryOrder.co_driver == crew_id),
        ).scalar()
        if not active_crew:
            crew_member = db.query(Driver).filter(Driver.id == crew_id).first()
            if crew_member:
                mark_crew_ready(crew_member)
