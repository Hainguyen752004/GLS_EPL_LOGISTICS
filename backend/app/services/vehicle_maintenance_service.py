import datetime as dt
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from models import (
    AuditLog,
    Vehicle,
    VehicleMaintenanceCostLine,
    VehicleMaintenanceRequest,
)
from services.errors import DomainError, conflict, missing_master


BLOCKING_STATUSES = ("approved", "in_progress")


def _now():
    return dt.datetime.utcnow()


def _utc(value, label):
    try:
        parsed = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("INVALID_DATETIME", f"Thời gian {label} không hợp lệ.", 422) from None
    if parsed.tzinfo is None:
        raise DomainError("TIMEZONE_REQUIRED", f"Thời gian {label} phải có múi giờ.", 422)
    return parsed.astimezone(dt.timezone.utc)


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _money(value, label):
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, ValueError):
        raise DomainError("INVALID_MONEY", f"{label} không hợp lệ.", 422) from None
    if amount < 0:
        raise DomainError("INVALID_MONEY", f"{label} không được âm.", 422)
    return amount


def _audit(db, action, record_id, actor):
    db.add(AuditLog(
        user_id=actor,
        action=action,
        table_name="vehicle_maintenance_requests",
        record_id=record_id,
        timestamp=_now(),
        ip_address=db.info.get("audit_ip"),
    ))


def _line_payload(line):
    return {
        "id": line.id,
        "category": line.category,
        "description": line.description,
        "quantity": str(line.quantity),
        "unit": line.unit,
        "estimated_unit_cost": str(line.estimated_unit_cost),
        "estimated_total": str(line.estimated_total),
        "actual_unit_cost": str(line.actual_unit_cost),
        "actual_total": str(line.actual_total),
    }


def serialize_request(item):
    return {
        "id": item.id,
        "request_no": item.request_no,
        "vehicle_id": item.vehicle_id,
        "category": item.category,
        "priority": item.priority,
        "planned_start": item.planned_start.isoformat() if item.planned_start else None,
        "planned_end": item.planned_end.isoformat() if item.planned_end else None,
        "actual_start": item.actual_start.isoformat() if item.actual_start else None,
        "actual_end": item.actual_end.isoformat() if item.actual_end else None,
        "description": item.description,
        "cause": item.cause,
        "odometer_km": item.odometer_km,
        "workshop": item.workshop,
        "currency_code": item.currency_code,
        "estimated_total": str(item.estimated_total),
        "actual_total": str(item.actual_total),
        "next_maintenance_date": item.next_maintenance_date,
        "status": item.status,
        "cancellation_reason": item.cancellation_reason,
        "version": item.version,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "created_by": item.created_by,
        "updated_by": item.updated_by,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "approved_by": item.approved_by,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "completed_by": item.completed_by,
        "cost_lines": [_line_payload(line) for line in item.cost_lines],
    }


def list_requests(db, vehicle_id):
    if not db.get(Vehicle, vehicle_id):
        raise missing_master("vehicle", "phương tiện")
    return (
        db.query(VehicleMaintenanceRequest)
        .filter(VehicleMaintenanceRequest.vehicle_id == vehicle_id)
        .order_by(VehicleMaintenanceRequest.planned_start.desc())
        .all()
    )


def list_requests_in_period(db, start, end):
    """Moi yeu cau bao duong CO GIAO voi khoang [start, end).

    Loc theo giao khoang chu khong theo "nam gon trong khoang": mot ky bao
    duong bat dau tu tuan truoc va keo qua tuan nay van chan xe trong tuan
    nay, nen phai tra ve.

    Chi tinh cac ky co `planned_start` va `planned_end`: mot yeu cau chua co
    lich thi khong chan o nao tren luoi, va de no vao chi lam nguoi doc tuong
    xe dang nam bai.
    """
    start_at = _utc(start, "ngay bat dau")
    end_at = _utc(end, "ngay ket thuc")
    if start_at >= end_at:
        raise DomainError("INVALID_PERIOD", "Khoang thoi gian xem bao duong khong hop le.", 422)
    return (
        db.query(VehicleMaintenanceRequest)
        .filter(
            VehicleMaintenanceRequest.planned_start.isnot(None),
            VehicleMaintenanceRequest.planned_end.isnot(None),
            VehicleMaintenanceRequest.planned_start < end_at,
            VehicleMaintenanceRequest.planned_end > start_at,
        )
        .order_by(VehicleMaintenanceRequest.vehicle_id, VehicleMaintenanceRequest.planned_start)
        .all()
    )


def create_request(db, vehicle_id, data, actor="system"):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).with_for_update().first()
    if not vehicle:
        raise missing_master("vehicle", "phương tiện")
    start = _utc(data.get("planned_start"), "bắt đầu sửa chữa")
    end = _utc(data.get("planned_end"), "kết thúc sửa chữa")
    if start >= end:
        raise DomainError("INVALID_MAINTENANCE_PERIOD", "Giờ kết thúc phải sau giờ bắt đầu.", 422)
    description = str(data.get("description") or "").strip()
    if not description:
        raise DomainError("MAINTENANCE_DESCRIPTION_REQUIRED", "Cần nhập nội dung sửa chữa.", 422)
    request_no = str(data.get("request_no") or "").strip()
    if not request_no:
        request_no = f"MR-{dt.datetime.utcnow():%Y%m%d}-{uuid4().hex[:6].upper()}"
    item = VehicleMaintenanceRequest(
        id=str(data.get("id") or f"VMR-{uuid4().hex.upper()}"),
        request_no=request_no,
        vehicle_id=vehicle_id,
        category=str(data.get("category") or "corrective"),
        priority=str(data.get("priority") or "normal"),
        planned_start=start,
        planned_end=end,
        description=description,
        cause=str(data.get("cause") or "").strip() or None,
        odometer_km=float(data["odometer_km"]) if data.get("odometer_km") not in (None, "") else None,
        workshop=str(data.get("workshop") or "").strip() or None,
        currency_code=str(data.get("currency_code") or "VND").upper(),
        status="requested",
        created_by=actor,
        updated_by=actor,
    )
    estimated_total = Decimal("0")
    for raw in data.get("cost_lines") or []:
        quantity = _money(raw.get("quantity") or 1, "Số lượng")
        if quantity <= 0:
            raise DomainError("INVALID_QUANTITY", "Số lượng phải lớn hơn 0.", 422)
        unit_cost = _money(raw.get("estimated_unit_cost"), "Đơn giá dự kiến")
        line_total = quantity * unit_cost
        item.cost_lines.append(VehicleMaintenanceCostLine(
            category=str(raw.get("category") or "other"),
            description=str(raw.get("description") or "Chi phí sửa chữa").strip(),
            quantity=quantity,
            unit=str(raw.get("unit") or "item"),
            estimated_unit_cost=unit_cost,
            estimated_total=line_total,
            actual_unit_cost=Decimal("0"),
            actual_total=Decimal("0"),
        ))
        estimated_total += line_total
    item.estimated_total = estimated_total
    db.add(item)
    _audit(db, "CREATE_VEHICLE_MAINTENANCE_REQUEST", item.id, actor)
    db.commit()
    db.refresh(item)
    return item


def transition_request(db, request_id, action, data, actor="system"):
    item = (
        db.query(VehicleMaintenanceRequest)
        .filter(VehicleMaintenanceRequest.id == request_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise DomainError("MAINTENANCE_REQUEST_NOT_FOUND", "Không tìm thấy phiếu sửa chữa.", 404)
    expected_version = data.get("expected_version")
    if expected_version is not None and int(expected_version) != item.version:
        raise conflict("VERSION_CONFLICT", "Phiếu sửa chữa đã thay đổi. Vui lòng tải lại dữ liệu.")
    transitions = {
        "approve": ("requested", "approved"),
        "start": ("approved", "in_progress"),
        "complete": ("in_progress", "completed"),
        "cancel": (("requested", "approved", "in_progress"), "cancelled"),
    }
    allowed, target = transitions[action]
    allowed_states = (allowed,) if isinstance(allowed, str) else allowed
    if item.status not in allowed_states:
        raise conflict("INVALID_MAINTENANCE_TRANSITION", f"Không thể {action} phiếu đang ở trạng thái {item.status}.")
    now = _now()
    if action == "approve":
        item.approved_at = now
        item.approved_by = actor
    elif action == "start":
        item.actual_start = _utc(data.get("actual_start"), "bắt đầu thực tế") if data.get("actual_start") else dt.datetime.now(dt.timezone.utc)
    elif action == "complete":
        item.actual_end = _utc(data.get("actual_end"), "kết thúc thực tế") if data.get("actual_end") else dt.datetime.now(dt.timezone.utc)
        if item.actual_start and _as_utc(item.actual_end) <= _as_utc(item.actual_start):
            raise DomainError("INVALID_MAINTENANCE_PERIOD", "Giờ hoàn tất phải sau giờ bắt đầu thực tế.", 422)
        updates = {int(raw["line_id"]): raw for raw in data.get("actual_cost_lines") or [] if raw.get("line_id") is not None}
        actual_total = Decimal("0")
        for line in item.cost_lines:
            raw = updates.get(line.id, {})
            actual_unit_cost = _money(raw.get("actual_unit_cost", line.estimated_unit_cost), "Đơn giá thực tế")
            line.actual_unit_cost = actual_unit_cost
            line.actual_total = Decimal(str(line.quantity)) * actual_unit_cost
            actual_total += line.actual_total
        item.actual_total = actual_total
        next_date = str(data.get("next_maintenance_date") or "").strip()
        if next_date:
            try:
                dt.date.fromisoformat(next_date)
            except ValueError:
                raise DomainError("INVALID_NEXT_MAINTENANCE_DATE", "Ngày bảo dưỡng tiếp theo không hợp lệ.", 422) from None
            item.next_maintenance_date = next_date
            vehicle = db.query(Vehicle).filter(Vehicle.id == item.vehicle_id).with_for_update().one()
            vehicle.maintenance_date = next_date
        item.completed_at = now
        item.completed_by = actor
    elif action == "cancel":
        reason = str(data.get("reason") or "").strip()
        if not reason:
            raise DomainError("CANCELLATION_REASON_REQUIRED", "Cần nhập lý do hủy phiếu sửa chữa.", 422)
        item.cancellation_reason = reason
    item.status = target
    item.version += 1
    item.updated_at = now
    item.updated_by = actor
    _audit(db, f"{action.upper()}_VEHICLE_MAINTENANCE", item.id, actor)
    db.commit()
    db.refresh(item)
    return item


def require_no_maintenance_overlap(db, vehicle_id, start, end):
    overlap = db.query(VehicleMaintenanceRequest.id).filter(
        VehicleMaintenanceRequest.vehicle_id == vehicle_id,
        VehicleMaintenanceRequest.status.in_(BLOCKING_STATUSES),
        VehicleMaintenanceRequest.planned_start < end,
        VehicleMaintenanceRequest.planned_end > start,
    ).first()
    if overlap:
        raise conflict(
            "VEHICLE_MAINTENANCE_OVERLAP",
            "Xe có lịch sửa chữa hoặc bảo dưỡng trùng thời gian điều phối.",
            ["master-data/vehicles"],
        )
