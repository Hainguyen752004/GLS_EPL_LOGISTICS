import datetime as dt
from decimal import Decimal

from sqlalchemy import or_

from models import (
    AuditLog,
    Driver,
    DriverShiftAssignment,
    ResourceAssignment,
    TransportEvent,
    TransportTrip,
    TransportTripLeg,
    Vehicle,
    VehicleMaintenanceRequest,
    VehicleType,
)
from services.errors import DomainError, conflict


RETURN_LEG_TYPES = {"empty_return", "backhaul"}
SHIFT_TYPES = {"morning", "afternoon", "night", "office", "custom"}
SHIFT_STATUSES = {"planned", "confirmed", "cancelled"}
AVAILABILITY_KINDS = {"work", "leave", "sick", "off", "unavailable"}


def _utc(value, field="thời gian"):
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as error:
            raise DomainError("INVALID_DATETIME", f"{field.capitalize()} không hợp lệ.", 422) from error
    else:
        raise DomainError("INVALID_DATETIME", f"Thiếu {field}.", 422)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _iso(value):
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _number(value):
    try:
        return float(Decimal(str(value or 0)))
    except Exception:
        return 0.0


def _speed(candidates):
    for source, value in candidates:
        speed = _number(value)
        if speed > 0:
            return speed, source
    raise DomainError("PLANNING_SPEED_REQUIRED", "Thiếu vận tốc hợp lệ để tính ETA chuyến.", 422)


def forecast_trip_turnaround(
    legs,
    latest_speed_kmh=None,
    vehicle_avg_speed_kmh=None,
    vehicle_type_avg_speed_kmh=None,
):
    ordered = sorted((dict(row) for row in (legs or [])), key=lambda row: int(row.get("sequence_no") or 0))
    if not ordered:
        raise DomainError("TRIP_LEGS_REQUIRED", "Trip chưa có chặng từ Route Master.", 422)
    departure = _utc(ordered[0].get("planned_departure_at"), "giờ khởi hành Trip")
    previous_arrival = None
    previous_dwell = 0
    outbound_speed = outbound_source = return_speed = return_source = None
    destination_available = None
    return_arrival = None
    return_mode = "missing"

    for index, leg in enumerate(ordered):
        is_return = str(leg.get("leg_type") or "").lower() in RETURN_LEG_TYPES
        if previous_arrival is not None:
            departure = previous_arrival + dt.timedelta(minutes=previous_dwell)
        candidates = (
            [("vehicle", vehicle_avg_speed_kmh), ("vehicle_type", vehicle_type_avg_speed_kmh), ("trip_leg", leg.get("avg_speed_kmh"))]
            if is_return
            else [("gps_tracking", latest_speed_kmh), ("vehicle", vehicle_avg_speed_kmh), ("vehicle_type", vehicle_type_avg_speed_kmh), ("trip_leg", leg.get("avg_speed_kmh"))]
        )
        speed, source = _speed(candidates)
        arrival = departure + dt.timedelta(hours=_number(leg.get("distance_km")) / speed)
        if is_return:
            return_speed, return_source = speed, source
            return_arrival = arrival
            return_mode = str(leg.get("leg_type")).lower()
        else:
            if outbound_speed is None:
                outbound_speed, outbound_source = speed, source
            destination_available = arrival + dt.timedelta(minutes=int(leg.get("dwell_minutes") or 0))
        previous_arrival = arrival
        previous_dwell = int(leg.get("dwell_minutes") or 0)

    result = {
        "outbound_speed_kmh": outbound_speed,
        "outbound_speed_source": outbound_source,
        "return_speed_kmh": return_speed,
        "return_speed_source": return_source,
        "available_at_destination": destination_available,
        "available_at_origin": return_arrival,
        "return_mode": return_mode,
        "warning_code": None,
    }
    if return_mode == "missing":
        result["warning_code"] = "RETURN_ROUTE_REQUIRED"
    return result


def serialize_shift(row):
    return {
        "id": row.id,
        "driver_id": row.driver_id,
        "vehicle_id": row.vehicle_id,
        "trip_id": row.trip_id,
        "shift_type": row.shift_type,
        "availability_kind": row.availability_kind or "work",
        "shift_start": _iso(row.shift_start),
        "shift_end": _iso(row.shift_end),
        "work_location": row.work_location,
        "notes": row.notes,
        "status": row.status,
        "version": row.version,
    }


def list_driver_shifts(db, start, end):
    start_at = _utc(start, "ngày bắt đầu")
    end_at = _utc(end, "ngày kết thúc")
    if start_at >= end_at:
        raise DomainError("INVALID_PERIOD", "Khoảng thời gian xem lịch không hợp lệ.", 422)
    rows = db.query(DriverShiftAssignment).filter(
        DriverShiftAssignment.status != "cancelled",
        DriverShiftAssignment.shift_start < end_at,
        DriverShiftAssignment.shift_end > start_at,
    ).order_by(DriverShiftAssignment.shift_start, DriverShiftAssignment.driver_id).all()
    return [serialize_shift(row) for row in rows]


def _audit(db, action, record_id, actor):
    db.add(AuditLog(
        user_id=actor,
        action=action,
        table_name="driver_shift_assignments",
        record_id=record_id,
        ip_address=db.info.get("audit_ip"),
    ))


def save_driver_shift(db, data, actor="system", shift_id=None):
    allowed = {"id", "driver_id", "vehicle_id", "trip_id", "shift_type", "availability_kind", "shift_start", "shift_end", "work_location", "notes", "status", "expected_version"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise DomainError("SHIFT_PAYLOAD_INVALID", "Dữ liệu ca làm việc có trường không được hỗ trợ.", 422)
    record_id = str(shift_id or data.get("id") or "").strip()
    driver_id = str(data.get("driver_id") or "").strip()
    vehicle_id = str(data.get("vehicle_id") or "").strip() or None
    trip_id = str(data.get("trip_id") or "").strip() or None
    if not record_id or not driver_id:
        raise DomainError("SHIFT_IDENTITY_REQUIRED", "Cần mã ca và tài xế.", 422)
    start_at = _utc(data.get("shift_start"), "giờ bắt đầu ca")
    end_at = _utc(data.get("shift_end"), "giờ kết thúc ca")
    if start_at >= end_at:
        raise DomainError("INVALID_SHIFT_PERIOD", "Giờ kết thúc ca phải sau giờ bắt đầu.", 422)
    shift_type = str(data.get("shift_type") or "custom").lower()
    status = str(data.get("status") or "planned").lower()
    availability_kind = str(data.get("availability_kind") or "work").lower()
    if shift_type not in SHIFT_TYPES or status not in SHIFT_STATUSES:
        raise DomainError("SHIFT_VALUE_INVALID", "Loại ca hoặc trạng thái ca không hợp lệ.", 422)
    if availability_kind not in AVAILABILITY_KINDS:
        raise DomainError("AVAILABILITY_KIND_INVALID", "Loai lich nhan su khong hop le.", 422)
    if availability_kind != "work":
        vehicle_id = None
        trip_id = None
    if not db.get(Driver, driver_id):
        raise DomainError("DRIVER_NOT_FOUND", "Không tìm thấy tài xế cần xếp ca.", 404)
    if vehicle_id and not db.get(Vehicle, vehicle_id):
        raise DomainError("VEHICLE_NOT_FOUND", "Không tìm thấy xe cần gán vào ca.", 404)

    overlap = db.query(DriverShiftAssignment.id).filter(
        DriverShiftAssignment.id != record_id,
        DriverShiftAssignment.status != "cancelled",
        DriverShiftAssignment.driver_id == driver_id,
        DriverShiftAssignment.shift_start < end_at,
        DriverShiftAssignment.shift_end > start_at,
    ).first()
    if overlap:
        raise conflict("DRIVER_SHIFT_OVERLAP", "Tài xế đã có ca làm việc trùng thời gian.")
    active_crew_assignment = db.query(ResourceAssignment.id).filter(
        ResourceAssignment.status == "active",
        ResourceAssignment.assignment_start < end_at,
        ResourceAssignment.assignment_end > start_at,
        or_(
            ResourceAssignment.driver_id == driver_id,
            ResourceAssignment.co_driver_id == driver_id,
        ),
    ).first()
    if active_crew_assignment:
        raise conflict(
            "DRIVER_ACTIVE_TRIP_OVERLAP",
            "Tai xe hoac phu xe dang duoc phan cong cho chuyen khac trong thoi gian nay.",
        )
    if vehicle_id:
        vehicle_overlap = db.query(DriverShiftAssignment.id).filter(
            DriverShiftAssignment.id != record_id,
            DriverShiftAssignment.status != "cancelled",
            DriverShiftAssignment.vehicle_id == vehicle_id,
            DriverShiftAssignment.shift_start < end_at,
            DriverShiftAssignment.shift_end > start_at,
        ).first()
        if vehicle_overlap:
            raise conflict("VEHICLE_SHIFT_OVERLAP", "Xe đã được gán vào ca khác trong cùng thời gian.")
        active_vehicle_assignment = db.query(ResourceAssignment.id).filter(
            ResourceAssignment.status == "active",
            ResourceAssignment.vehicle_id == vehicle_id,
            ResourceAssignment.assignment_start < end_at,
            ResourceAssignment.assignment_end > start_at,
        ).first()
        if active_vehicle_assignment:
            raise conflict(
                "VEHICLE_ACTIVE_TRIP_OVERLAP",
                "Xe dang thuc hien chuyen khac va chua toi thoi diem ranh.",
            )
        trip_overlap = db.query(TransportTrip.id).filter(
            TransportTrip.status.in_(("planned", "dispatched", "in_transit")),
            TransportTrip.vehicle_id == vehicle_id,
            TransportTrip.planned_departure_at < end_at,
            TransportTrip.planned_return_at.is_not(None),
            TransportTrip.planned_return_at > start_at,
        ).first()
        if trip_overlap:
            raise conflict("VEHICLE_NOT_RETURNED", "Xe chưa hoàn tất hành trình quay đầu của Trip trước.")

    row = db.query(DriverShiftAssignment).filter(DriverShiftAssignment.id == record_id).with_for_update().first()
    if row:
        expected = data.get("expected_version")
        if expected is not None and row.version != int(expected):
            raise conflict("VERSION_CONFLICT", "Ca làm việc đã được người khác cập nhật.")
        row.version += 1
        action = "UPDATE_DRIVER_SHIFT"
    else:
        row = DriverShiftAssignment(id=record_id, created_by=actor)
        db.add(row)
        action = "CREATE_DRIVER_SHIFT"
    row.driver_id = driver_id
    row.vehicle_id = vehicle_id
    row.trip_id = trip_id
    row.shift_type = shift_type
    row.availability_kind = availability_kind
    row.shift_start = start_at
    row.shift_end = end_at
    row.work_location = str(data.get("work_location") or "").strip() or None
    row.notes = str(data.get("notes") or "").strip() or None
    row.status = status
    row.updated_at = dt.datetime.now(dt.timezone.utc)
    row.updated_by = actor
    _audit(db, action, row.id, actor)
    db.flush()
    return serialize_shift(row)


def save_weekly_driver_schedule(db, data, actor="system"):
    """Expand a recurring weekly pattern into editable, persisted work shifts."""
    driver_id = str(data.get("driver_id") or "").strip()
    if not driver_id or not db.get(Driver, driver_id):
        raise DomainError("DRIVER_NOT_FOUND", "Khong tim thay tai xe can lap lich mac dinh.", 404)
    try:
        weekdays = sorted({int(value) for value in data.get("weekdays", [])})
        start_date = dt.date.fromisoformat(str(data.get("effective_start") or ""))
        end_date = dt.date.fromisoformat(str(data.get("effective_end") or ""))
        start_time = dt.time.fromisoformat(str(data.get("start_time") or ""))
        end_time = dt.time.fromisoformat(str(data.get("end_time") or ""))
        explicit_day_offset = data.get("end_day_offset")
        end_day_offset = int(explicit_day_offset) if explicit_day_offset is not None else (1 if end_time <= start_time else 0)
        timezone_offset = int(data.get("timezone_offset_minutes") or 0)
    except (TypeError, ValueError) as error:
        raise DomainError("WEEKLY_SCHEDULE_INVALID", "Ngay, gio hoac thu trong tuan khong hop le.", 422) from error
    if not weekdays or any(value < 0 or value > 6 for value in weekdays):
        raise DomainError("WEEKDAYS_REQUIRED", "Chon it nhat mot ngay lam viec trong tuan.", 422)
    if start_date > end_date or (end_date - start_date).days > 366:
        raise DomainError("SCHEDULE_PERIOD_INVALID", "Khoang ap dung lich phai tu 1 den 366 ngay.", 422)
    if end_day_offset < 0 or end_day_offset > 7 or (end_day_offset == 0 and end_time <= start_time):
        raise DomainError("SHIFT_DURATION_INVALID", "Thoi gian ca phai lon hon 0 va khong qua 7 ngay.", 422)
    if timezone_offset < -840 or timezone_offset > 840:
        raise DomainError("TIMEZONE_OFFSET_INVALID", "Mui gio lich lam viec khong hop le.", 422)

    shift_type = str(data.get("shift_type") or "custom").lower()
    if shift_type not in SHIFT_TYPES:
        raise DomainError("SHIFT_VALUE_INVALID", "Loai ca khong hop le.", 422)
    vehicle_id = str(data.get("vehicle_id") or "").strip() or None
    work_location = str(data.get("work_location") or "").strip() or None
    notes = str(data.get("notes") or "Lich lam viec mac dinh lap theo tuan").strip() or None
    rows = []
    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays:
            start_at = dt.datetime.combine(current, start_time, tzinfo=dt.timezone.utc) + dt.timedelta(minutes=timezone_offset)
            end_day = current + dt.timedelta(days=end_day_offset)
            end_at = dt.datetime.combine(end_day, end_time, tzinfo=dt.timezone.utc) + dt.timedelta(minutes=timezone_offset)
            record_id = f"WEEKLY-{driver_id}-{current:%Y%m%d}-{start_time:%H%M}-{end_time:%H%M}-D{end_day_offset}"
            rows.append(save_driver_shift(db, {
                "id": record_id,
                "driver_id": driver_id,
                "vehicle_id": vehicle_id,
                "shift_type": shift_type,
                "availability_kind": "work",
                "shift_start": start_at,
                "shift_end": end_at,
                "work_location": work_location,
                "notes": notes,
                "status": "planned",
            }, actor=actor, shift_id=record_id))
        current += dt.timedelta(days=1)
    return {"created_count": len(rows), "shifts": rows}


def delete_driver_shift(db, shift_id, actor="system"):
    row = db.query(DriverShiftAssignment).filter(DriverShiftAssignment.id == shift_id).with_for_update().first()
    if not row:
        raise DomainError("SHIFT_NOT_FOUND", "Không tìm thấy ca làm việc.", 404)
    row.status = "cancelled"
    row.version += 1
    row.updated_at = dt.datetime.now(dt.timezone.utc)
    row.updated_by = actor
    _audit(db, "CANCEL_DRIVER_SHIFT", row.id, actor)
    db.flush()
    return serialize_shift(row)


def list_vehicle_availability(db, start, end):
    start_at = _utc(start, "ngày bắt đầu")
    end_at = _utc(end, "ngày kết thúc")
    trips = db.query(TransportTrip).filter(
        # Chuyen DA HOAN TAT khong con giu xe. Ban truoc de no trong lich, nen man
        # Dieu phoi dem 9/9 xe "dang chay" trong khi chi 6 xe co chuyen mo — moi
        # xe tung chay xong mot chuyen deu bi coi la ban mai.
        TransportTrip.status.notin_(("cancelled", "settled", "completed")),
        TransportTrip.planned_departure_at < end_at,
        TransportTrip.planned_departure_at >= start_at - dt.timedelta(days=14),
    ).order_by(TransportTrip.planned_departure_at).all()
    rows = []
    for trip in trips:
        legs = db.query(TransportTripLeg).filter(TransportTripLeg.trip_id == trip.id).order_by(TransportTripLeg.sequence_no).all()
        if not legs:
            continue
        vehicle = db.get(Vehicle, trip.vehicle_id) if trip.vehicle_id else None
        vehicle_type = None
        if vehicle and vehicle.type:
            vehicle_type = db.query(VehicleType).filter(
                (VehicleType.id == vehicle.type) | (VehicleType.name == vehicle.type)
            ).first()
        event = db.query(TransportEvent).filter(
            TransportEvent.trip_id == trip.id,
            TransportEvent.speed_kmh.is_not(None),
            TransportEvent.speed_kmh > 0,
        ).order_by(TransportEvent.event_time.desc(), TransportEvent.recorded_at.desc()).first()
        forecast = forecast_trip_turnaround(
            [{
                "sequence_no": leg.sequence_no,
                "leg_type": leg.leg_type,
                "origin": leg.origin,
                "destination": leg.destination,
                "distance_km": leg.distance_km,
                "avg_speed_kmh": leg.avg_speed_kmh,
                "dwell_minutes": leg.dwell_minutes,
                "planned_departure_at": leg.planned_departure_at,
            } for leg in legs],
            latest_speed_kmh=event.speed_kmh if event else None,
            vehicle_avg_speed_kmh=vehicle.avg_speed_kmh if vehicle else None,
            vehicle_type_avg_speed_kmh=vehicle_type.avg_speed_kmh if vehicle_type else None,
        )
        rows.append({
            "kind": "trip",
            "trip_id": trip.id,
            "vehicle_id": trip.vehicle_id,
            "driver_id": trip.driver_id,
            "co_driver_id": trip.co_driver_id,
            "origin": legs[0].origin,
            "destination": next((leg.destination for leg in reversed(legs) if leg.leg_type not in RETURN_LEG_TYPES), legs[-1].destination),
            "planned_departure_at": _iso(trip.planned_departure_at),
            "planned_arrival_at": _iso(trip.planned_arrival_at),
            "available_at_destination": _iso(forecast["available_at_destination"]),
            "available_at_origin": _iso(forecast["available_at_origin"]),
            "return_mode": forecast["return_mode"],
            "warning_code": forecast["warning_code"],
            "outbound_speed_kmh": forecast["outbound_speed_kmh"],
            "outbound_speed_source": forecast["outbound_speed_source"],
            "return_speed_kmh": forecast["return_speed_kmh"],
            "return_speed_source": forecast["return_speed_source"],
        })
    maintenance_rows = db.query(VehicleMaintenanceRequest).filter(
        VehicleMaintenanceRequest.status.in_(("approved", "in_progress")),
        VehicleMaintenanceRequest.planned_start < end_at,
        VehicleMaintenanceRequest.planned_end > start_at,
    ).order_by(VehicleMaintenanceRequest.planned_start).all()
    rows.extend({
        "kind": "maintenance",
        "maintenance_request_id": item.id,
        "vehicle_id": item.vehicle_id,
        "driver_id": None,
        "co_driver_id": None,
        "origin": None,
        "destination": None,
        "planned_departure_at": _iso(item.planned_start),
        "planned_arrival_at": _iso(item.planned_end),
        "available_at_destination": _iso(item.planned_end),
        "available_at_origin": _iso(item.planned_end),
        "return_mode": "maintenance",
        "warning_code": None,
        "maintenance_label": item.description or item.request_no,
    } for item in maintenance_rows)
    return rows
