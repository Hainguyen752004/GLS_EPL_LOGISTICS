import datetime as dt
import math

from models import (
    AuditLog,
    Customer,
    FreightOrder,
    FreightUnit,
    Location,
    TransportDemand,
)
from services.errors import DomainError, conflict, missing_master


def _now():
    return dt.datetime.utcnow()


def _datetime(data, field):
    value = data.get(field)
    try:
        return value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("INVALID_DATETIME", f"Thời gian {field} không hợp lệ.", 422) from None


def _quantity(data, field, integer=False):
    try:
        value = int(data.get(field, 0)) if integer else float(data.get(field, 0))
    except (TypeError, ValueError):
        raise DomainError("INVALID_CAPACITY", f"Giá trị {field} không hợp lệ.", 422) from None
    if not math.isfinite(value) or value < 0:
        raise DomainError("INVALID_CAPACITY", f"Giá trị {field} phải là số không âm.", 422)
    return value


def _audit(db, action, table, record_id, actor):
    db.add(AuditLog(
        user_id=actor,
        action=action,
        table_name=table,
        record_id=record_id,
        timestamp=_now(),
        ip_address=db.info.get("audit_ip"),
    ))


def create_demand(db, data, actor="system"):
    customer_id = data.get("customer_id")
    if not db.query(Customer.id).filter(Customer.id == customer_id).first():
        raise missing_master("customer", "khách hàng")
    pickup_id = data.get("pickup_location_id")
    delivery_id = data.get("delivery_location_id")
    for location_id, label in ((pickup_id, "điểm lấy hàng"), (delivery_id, "điểm giao hàng")):
        if not db.query(Location.id).filter(Location.id == location_id).first():
            raise missing_master("location", label)
    pickup_start = _datetime(data, "pickup_window_start")
    pickup_end = _datetime(data, "pickup_window_end")
    delivery_start = _datetime(data, "delivery_window_start")
    delivery_end = _datetime(data, "delivery_window_end")
    if pickup_start >= pickup_end or delivery_start >= delivery_end or pickup_end > delivery_end:
        raise DomainError("INVALID_TIME_WINDOW", "Khung thời gian lấy/giao hàng không hợp lệ.", 422)
    demand = TransportDemand(
        id=data.get("id"), customer_id=customer_id,
        pickup_location_id=pickup_id, delivery_location_id=delivery_id,
        pickup_window_start=pickup_start, pickup_window_end=pickup_end,
        delivery_window_start=delivery_start, delivery_window_end=delivery_end,
        weight_kg=_quantity(data, "weight_kg"),
        volume_m3=_quantity(data, "volume_m3"),
        pallet_count=_quantity(data, "pallet_count", integer=True),
        service_requirements=data.get("service_requirements") or "",
        created_by=actor, updated_by=actor,
    )
    db.add(demand)
    _audit(db, "CREATE_TRANSPORT_DEMAND", "transport_demands", demand.id, actor)
    db.flush()
    return demand


def submit_demand(db, demand_id, expected_version, actor="system"):
    demand = db.query(TransportDemand).filter(TransportDemand.id == demand_id).with_for_update().first()
    if not demand:
        raise DomainError("DEMAND_NOT_FOUND", f"Không tìm thấy nhu cầu vận chuyển {demand_id}.", 404)
    if demand.version != expected_version:
        raise conflict("VERSION_CONFLICT", "Nhu cầu đã được người khác cập nhật. Vui lòng tải lại dữ liệu.")
    if demand.status != "draft":
        raise conflict("INVALID_TRANSITION", "Chỉ nhu cầu bản nháp mới được gửi lập kế hoạch.")
    demand.status = "submitted"
    demand.version += 1
    demand.updated_at = _now()
    demand.updated_by = actor
    _audit(db, "SUBMIT_TRANSPORT_DEMAND", "transport_demands", demand.id, actor)
    db.flush()
    return demand


def create_freight_unit_from_demand(db, demand_id, actor="system"):
    demand = db.query(TransportDemand).filter(TransportDemand.id == demand_id).with_for_update().first()
    if not demand:
        raise DomainError("DEMAND_NOT_FOUND", f"Không tìm thấy nhu cầu vận chuyển {demand_id}.", 404)
    if demand.status != "submitted":
        raise conflict("DEMAND_NOT_SUBMITTED", "Nhu cầu phải được gửi trước khi tạo Freight Unit.")
    if db.query(FreightUnit.id).filter(FreightUnit.demand_id == demand.id).first():
        raise conflict("FREIGHT_UNIT_EXISTS", "Nhu cầu này đã có Freight Unit.")
    unit = FreightUnit(
        id=demand.id.replace("TD-", "FU-", 1), demand_id=demand.id,
        pickup_location_id=demand.pickup_location_id, delivery_location_id=demand.delivery_location_id,
        pickup_window_start=demand.pickup_window_start, pickup_window_end=demand.pickup_window_end,
        delivery_window_start=demand.delivery_window_start, delivery_window_end=demand.delivery_window_end,
        weight_kg=demand.weight_kg, volume_m3=demand.volume_m3, pallet_count=demand.pallet_count,
        created_by=actor,
    )
    demand.status = "planned"
    demand.version += 1
    demand.updated_at = _now()
    demand.updated_by = actor
    db.add(unit)
    _audit(db, "CREATE_FREIGHT_UNIT", "freight_units", unit.id, actor)
    db.flush()
    return unit


def create_freight_order(db, data, actor="system"):
    unit_ids = list(dict.fromkeys(data.get("freight_unit_ids") or []))
    if not unit_ids:
        raise DomainError("FREIGHT_UNITS_REQUIRED", "Cần chọn ít nhất một Freight Unit.", 422)
    units = db.query(FreightUnit).filter(FreightUnit.id.in_(unit_ids)).with_for_update().all()
    if len(units) != len(unit_ids):
        raise DomainError("FREIGHT_UNIT_NOT_FOUND", "Có Freight Unit không tồn tại.", 404)
    if any(unit.status != "open" for unit in units):
        raise conflict("FREIGHT_UNIT_NOT_OPEN", "Chỉ Freight Unit đang mở mới được ghép chuyến.")
    route = {(unit.pickup_location_id, unit.delivery_location_id) for unit in units}
    if len(route) != 1:
        raise conflict("ROUTE_MISMATCH", "Các Freight Unit phải cùng điểm lấy và điểm giao trong kế hoạch này.")
    pickup_start = max(unit.pickup_window_start for unit in units)
    pickup_end = min(unit.pickup_window_end for unit in units)
    delivery_start = max(unit.delivery_window_start for unit in units)
    delivery_end = min(unit.delivery_window_end for unit in units)
    if pickup_start >= pickup_end or delivery_start >= delivery_end:
        raise conflict("TIME_WINDOW_MISMATCH", "Các Freight Unit không có khung thời gian giao nhau.")
    totals = {
        "weight": sum(unit.weight_kg for unit in units),
        "volume": sum(unit.volume_m3 for unit in units),
        "pallet": sum(unit.pallet_count for unit in units),
    }
    limits = {
        "weight": _quantity(data, "max_weight_kg"),
        "volume": _quantity(data, "max_volume_m3"),
        "pallet": _quantity(data, "max_pallet_count", integer=True),
    }
    if any(totals[key] > limits[key] for key in totals):
        raise conflict("CAPACITY_EXCEEDED", "Tổng tải trọng, thể tích hoặc số pallet vượt năng lực chuyến.")
    pickup_id, delivery_id = route.pop()
    order = FreightOrder(
        id=data.get("id"), pickup_location_id=pickup_id, delivery_location_id=delivery_id,
        pickup_window_start=pickup_start, pickup_window_end=pickup_end,
        delivery_window_start=delivery_start, delivery_window_end=delivery_end,
        total_weight_kg=totals["weight"], total_volume_m3=totals["volume"],
        total_pallet_count=totals["pallet"], max_weight_kg=limits["weight"],
        max_volume_m3=limits["volume"], max_pallet_count=limits["pallet"],
        created_by=actor, updated_by=actor, units=units,
    )
    for unit in units:
        unit.status = "planned"
        unit.version += 1
    db.add(order)
    _audit(db, "CREATE_FREIGHT_ORDER", "freight_orders", order.id, actor)
    db.flush()
    return order
