import datetime as dt

from sqlalchemy import or_

from models import (AuditLog, DeliveryOrder, Driver, DriverQualification,
                    DriverShiftAssignment, FreightOrder, ResourceAssignment, Tender, TransportTrip,
                    TransportTripLeg, TripDeliveryOrder, Vehicle,
                    VehicleTracking, WarehouseAppointment)
from services.errors import DomainError, conflict, missing_master
from services.crew_policy import mark_crew_busy, require_crew
from services.vehicle_capacity_policy import require_vehicle_capacity
from services.vehicle_maintenance_service import require_no_maintenance_overlap
from services import parking_list_service


READY_VEHICLE = "Sẵn sàng"


def _require_work_schedule(db, crew_ids, start_at, end_at):
    """Require each crew member to have continuous work coverage for the trip."""
    for crew_id in crew_ids:
        shifts = db.query(DriverShiftAssignment).filter(
            DriverShiftAssignment.status.in_(("planned", "confirmed")),
            DriverShiftAssignment.driver_id == crew_id,
            DriverShiftAssignment.shift_start < end_at,
            DriverShiftAssignment.shift_end > start_at,
        ).order_by(DriverShiftAssignment.shift_start, DriverShiftAssignment.shift_end).all()
        if any((shift.availability_kind or "work") != "work" for shift in shifts):
            raise conflict(
                "DRIVER_UNAVAILABLE",
                f"Nhân sự {crew_id} đang nghỉ hoặc không sẵn sàng trong thời gian chuyến.",
                ["master-data/drivers"],
            )

        cursor = start_at
        for shift in (row for row in shifts if (row.availability_kind or "work") == "work"):
            shift_start = _utc(shift.shift_start)
            shift_end = _utc(shift.shift_end)
            if shift_start > cursor:
                break
            if shift_end > cursor:
                cursor = shift_end
            if cursor >= end_at:
                break
        if cursor < end_at:
            raise conflict(
            "DRIVER_WORK_SCHEDULE_REQUIRED",
            f"Nhân sự {crew_id} chưa có lịch làm việc bao phủ toàn bộ thời gian chuyến.",
                ["master-data/drivers"],
            )
READY_DRIVER = "🟢 Rảnh (Sẵn sàng)"


def _now():
    return dt.datetime.utcnow()


def _parse_datetime(value, label):
    try:
        return value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("INVALID_DATETIME", f"Thời gian {label} không hợp lệ.", 422) from None


def _parse_date(value):
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _audit(db, action, table, record_id, actor):
    db.add(AuditLog(user_id=actor, action=action, table_name=table, record_id=record_id,
                    timestamp=_now(), ip_address=db.info.get("audit_ip")))


def book_appointment(db, data, actor="system"):
    order = db.query(FreightOrder).filter(FreightOrder.id == data.get("freight_order_id")).with_for_update().first()
    if not order:
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy Freight Order để xếp lịch kho.", 404)
    appointment_type = data.get("appointment_type")
    if appointment_type not in {"pickup", "delivery"}:
        raise DomainError("INVALID_APPOINTMENT_TYPE", "Loại lịch hẹn phải là lấy hàng hoặc giao hàng.", 422)
    expected_location = order.pickup_location_id if appointment_type == "pickup" else order.delivery_location_id
    if data.get("location_id") != expected_location:
        raise conflict("APPOINTMENT_LOCATION_MISMATCH", "Địa điểm lịch hẹn không khớp Freight Order.")
    start = _parse_datetime(data.get("scheduled_start"), "bắt đầu lịch hẹn")
    end = _parse_datetime(data.get("scheduled_end"), "kết thúc lịch hẹn")
    window_start = order.pickup_window_start if appointment_type == "pickup" else order.delivery_window_start
    window_end = order.pickup_window_end if appointment_type == "pickup" else order.delivery_window_end
    if start >= end or start < window_start or end > window_end:
        raise conflict("APPOINTMENT_OUTSIDE_WINDOW", "Lịch hẹn phải nằm trong khung thời gian của Freight Order.")
    appointment = WarehouseAppointment(
        id=data.get("id"), freight_order_id=order.id, appointment_type=appointment_type,
        location_id=expected_location, scheduled_start=start, scheduled_end=end, created_by=actor,
    )
    db.add(appointment)
    _audit(db, "BOOK_WAREHOUSE_APPOINTMENT", "warehouse_appointments", appointment.id, actor)
    db.flush()
    return appointment


def save_driver_qualification(db, data, actor="system"):
    driver = db.query(Driver).filter(Driver.id == data.get("driver_id")).with_for_update().first()
    if not driver:
        raise missing_master("driver", "tài xế")
    valid_from = _parse_datetime(data.get("valid_from"), "bắt đầu hiệu lực bằng lái")
    valid_to = _parse_datetime(data.get("valid_to"), "hết hạn bằng lái")
    if valid_from >= valid_to:
        raise DomainError("INVALID_LICENSE_PERIOD", "Thời hạn bằng lái không hợp lệ.", 422)
    qualification = db.query(DriverQualification).filter(DriverQualification.driver_id == driver.id).first()
    if not qualification:
        qualification = DriverQualification(driver_id=driver.id)
        db.add(qualification)
    qualification.license_type = data.get("license_type") or driver.license_type
    qualification.valid_from = valid_from
    qualification.valid_to = valid_to
    qualification.status = data.get("status") or "active"
    qualification.verified_at = _now()
    qualification.verified_by = actor
    _audit(db, "SAVE_DRIVER_QUALIFICATION", "driver_qualifications", driver.id, actor)
    db.flush()
    return qualification


def _require_legal_vehicle(vehicle, trip_date):
    fields = {
        "đăng kiểm": _parse_date(vehicle.inspection_exp),
        "bảo hiểm": _parse_date(vehicle.insurance_date),
        "bảo dưỡng": _parse_date(vehicle.maintenance_date),
    }
    expired = [label for label, valid_to in fields.items() if valid_to is None or valid_to < trip_date]
    if expired:
        raise conflict("VEHICLE_LEGAL_EXPIRED", f"Xe thiếu hoặc hết hạn: {', '.join(expired)}.", ["master-data/vehicles"])


def dispatch_freight_order(db, order_id, data, actor="system"):
    order = db.query(FreightOrder).filter(FreightOrder.id == order_id).with_for_update().first()
    if not order:
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", f"Không tìm thấy Freight Order {order_id}.", 404)
    if order.version != data.get("expected_version"):
        raise conflict("VERSION_CONFLICT", "Freight Order đã thay đổi. Vui lòng tải lại dữ liệu.")
    if order.status != "planned":
        raise conflict("INVALID_TRANSITION", "Chỉ Freight Order đã lập kế hoạch mới được điều phối.")
    tender = db.query(Tender).filter(Tender.freight_order_id == order.id).first()
    if tender and tender.status != "awarded":
        raise conflict("TENDER_AWARD_REQUIRED", "Tender phải được trao thầu trước khi điều phối.")
    appointments = db.query(WarehouseAppointment).filter(
        WarehouseAppointment.freight_order_id == order.id,
        WarehouseAppointment.status == "booked",
    ).all()
    if {item.appointment_type for item in appointments} != {"pickup", "delivery"}:
        raise conflict("WAREHOUSE_APPOINTMENT_REQUIRED", "Cần xếp đủ lịch hẹn lấy và giao hàng trước khi điều phối.", ["warehouse-appointments"])
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
    if vehicle.status != READY_VEHICLE:
        raise conflict("RESOURCE_BUSY", "Xe hoặc tài xế không ở trạng thái sẵn sàng.")
    require_crew(driver, co_driver)
    require_vehicle_capacity(
        vehicle,
        weight_kg=order.total_weight_kg,
        volume_m3=order.total_volume_m3,
        pallet_count=order.total_pallet_count,
        subject=f"Freight Order {order.id}",
    )
    trip_date = order.pickup_window_start.date()
    _require_legal_vehicle(vehicle, trip_date)
    require_no_maintenance_overlap(
        db,
        vehicle.id,
        _utc(order.pickup_window_start),
        _utc(order.delivery_window_end),
    )
    qualification = db.query(DriverQualification).filter(DriverQualification.driver_id == driver.id).with_for_update().first()
    if (not qualification or qualification.status != "active" or qualification.valid_from.date() > trip_date
            or qualification.valid_to.date() < trip_date or qualification.license_type != driver.license_type):
        raise conflict("DRIVER_LICENSE_INVALID", "Bằng lái của tài xế không phù hợp hoặc đã hết hạn.", ["master-data/drivers"])
    crew_ids = [driver.id] + ([co_driver.id] if co_driver else [])
    _require_work_schedule(
        db,
        crew_ids,
        _utc(order.pickup_window_start),
        _utc(order.delivery_window_end),
    )
    overlap = db.query(ResourceAssignment.id).filter(
        ResourceAssignment.status == "active",
        ResourceAssignment.assignment_start < order.delivery_window_end,
        ResourceAssignment.assignment_end > order.pickup_window_start,
        or_(
            ResourceAssignment.vehicle_id == vehicle.id,
            ResourceAssignment.driver_id.in_(crew_ids),
            ResourceAssignment.co_driver_id.in_(crew_ids),
        ),
    ).first()
    if overlap:
        raise conflict("RESOURCE_TIME_OVERLAP", "Xe hoặc tài xế đã được phân cho chuyến khác trong cùng thời gian.")
    assignment = ResourceAssignment(
        freight_order_id=order.id, vehicle_id=vehicle.id, driver_id=driver.id,
        co_driver_id=co_driver.id if co_driver else None,
        assignment_start=order.pickup_window_start, assignment_end=order.delivery_window_end,
        created_by=actor,
    )
    db.add(assignment)
    vehicle.status = f"Đang thực hiện {order.id}"
    mark_crew_busy(driver, vehicle.id, order.id)
    if co_driver:
        mark_crew_busy(co_driver, vehicle.id, order.id)
    order.status = "dispatched"
    order.version += 1
    order.updated_at = _now()
    order.updated_by = actor
    _audit(db, "DISPATCH_FREIGHT_ORDER", "freight_orders", order.id, actor)
    db.flush()
    return order


def dispatch_trip(db, trip_id, data, actor="system"):
    # SQLite bỏ qua SELECT ... FOR UPDATE trong im lặng, nên trên SQLite các
    # lệnh khóa hàng ở dưới (xe, tài xế, phụ xe) không có tác dụng gì: hai lệnh
    # điều xe song song cho HAI chuyến khác nhau cùng vượt qua bước kiểm chồng
    # lịch rồi cùng commit, và một chiếc xe nằm trên hai chuyến đang chạy.
    # Lấy khóa ghi của SQLite trước mọi thao tác đọc để các phiên cạnh tranh
    # bị tuần tự hóa — đúng cách tms_cost_service._idempotent đang làm.
    #
    # Trên PostgreSQL không cần đoạn này: FOR UPDATE ở dưới khóa thật các hàng
    # xe/tài xế, tức đúng những tài nguyên xuất hiện trong điều kiện kiểm chồng
    # lịch, nên phiên thứ hai phải chờ và sau đó đọc được bản ghi đã commit.
    if db.get_bind().dialect.name == "sqlite" and not db.in_transaction():
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    trip = (
        db.query(TransportTrip)
        .filter(TransportTrip.id == trip_id)
        .with_for_update()
        .first()
    )
    if not trip:
        raise DomainError("TRIP_NOT_FOUND", f"Không tìm thấy chuyến {trip_id}.", 404)
    if trip.version != data.get("expected_version"):
        raise conflict("VERSION_CONFLICT", "Chuyến đã thay đổi. Vui lòng tải lại dữ liệu.")
    if trip.status != "planned":
        raise conflict("INVALID_TRANSITION", "Chỉ chuyến đã lập kế hoạch mới được điều phối.")

    order = (
        db.query(FreightOrder)
        .filter(FreightOrder.id == trip.freight_order_id)
        .with_for_update()
        .first()
    )
    if not order:
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy Freight Order của chuyến.", 404)

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
    if vehicle.status != READY_VEHICLE:
        raise conflict("RESOURCE_BUSY", "Xe hoặc tài xế không ở trạng thái sẵn sàng.")
    require_crew(driver, co_driver)
    require_vehicle_capacity(
        vehicle,
        weight_kg=order.total_weight_kg,
        volume_m3=order.total_volume_m3,
        pallet_count=order.total_pallet_count,
        subject=f"Trip {trip.id}",
    )

    assignment_start = _utc(data.get("assignment_start"))
    requested_assignment_end = _utc(data.get("assignment_end"))
    if assignment_start >= requested_assignment_end:
        raise DomainError("INVALID_ASSIGNMENT_PERIOD", "Thời gian điều phối không hợp lệ.", 422)
    if (assignment_start < _utc(order.pickup_window_start)
            or requested_assignment_end > _utc(order.delivery_window_end)):
        raise conflict(
            "ASSIGNMENT_OUTSIDE_WINDOW",
            "Thời gian điều phối phải nằm trong khung lấy và giao hàng của chuyến.",
        )

    availability_candidates = [requested_assignment_end]
    if trip.planned_arrival_at:
        availability_candidates.append(_utc(trip.planned_arrival_at))
    if trip.planned_return_at:
        availability_candidates.append(_utc(trip.planned_return_at))
    assignment_end = max(availability_candidates)

    require_no_maintenance_overlap(db, vehicle.id, assignment_start, assignment_end)

    crew_ids = [driver.id] + ([co_driver.id] if co_driver else [])
    driver_shifts = db.query(DriverShiftAssignment).filter(
        DriverShiftAssignment.status.in_(("planned", "confirmed")),
        DriverShiftAssignment.driver_id.in_(crew_ids),
        DriverShiftAssignment.shift_start < assignment_end,
        DriverShiftAssignment.shift_end > assignment_start,
    ).all()
    unavailable_shift = next(
        (
            shift for shift in driver_shifts
            if (shift.availability_kind or "work") != "work"
        ),
        None,
    )
    if unavailable_shift:
        raise conflict(
            "DRIVER_UNAVAILABLE",
            f"Nhan su {unavailable_shift.driver_id} dang nghi hoac khong san sang trong khung gio dieu phoi.",
            ["master-data/drivers"],
        )
    _require_work_schedule(db, crew_ids, assignment_start, assignment_end)
    mismatched_shift = next(
        (shift for shift in driver_shifts if shift.vehicle_id and shift.vehicle_id != vehicle.id),
        None,
    )
    if mismatched_shift:
        raise conflict(
            "SHIFT_VEHICLE_MISMATCH",
            f"Ca {mismatched_shift.id} đã gắn nhân sự {mismatched_shift.driver_id} với xe {mismatched_shift.vehicle_id}.",
            ["master-data/drivers"],
        )
    vehicle_shift = db.query(DriverShiftAssignment.id).filter(
        DriverShiftAssignment.status.in_(("planned", "confirmed")),
        DriverShiftAssignment.vehicle_id == vehicle.id,
        ~DriverShiftAssignment.driver_id.in_(crew_ids),
        DriverShiftAssignment.shift_start < assignment_end,
        DriverShiftAssignment.shift_end > assignment_start,
    ).first()
    if vehicle_shift:
        raise conflict(
            "VEHICLE_SHIFT_OVERLAP",
            "Xe đã được xếp cho tài xế khác trong cùng thời gian.",
            ["master-data/drivers"],
        )

    trip_date = assignment_start.date()
    _require_legal_vehicle(vehicle, trip_date)
    qualification = (
        db.query(DriverQualification)
        .filter(DriverQualification.driver_id == driver.id)
        .with_for_update()
        .first()
    )
    if (not qualification or qualification.status != "active"
            or _utc(qualification.valid_from).date() > trip_date
            or _utc(qualification.valid_to).date() < trip_date
            or qualification.license_type != driver.license_type):
        raise conflict(
            "DRIVER_LICENSE_INVALID",
            "Bằng lái của tài xế không phù hợp hoặc đã hết hạn.",
            ["master-data/drivers"],
        )

    overlap = db.query(ResourceAssignment.id).filter(
        ResourceAssignment.status == "active",
        ResourceAssignment.assignment_start < assignment_end,
        ResourceAssignment.assignment_end > assignment_start,
        or_(
            ResourceAssignment.vehicle_id == vehicle.id,
            ResourceAssignment.driver_id.in_(crew_ids),
            ResourceAssignment.co_driver_id.in_(crew_ids),
        ),
    ).first()
    if overlap:
        raise conflict("RESOURCE_TIME_OVERLAP", "Xe hoặc tài xế đã được phân cho chuyến khác trong cùng thời gian.")

    do_ids = [
        row[0]
        for row in db.query(TripDeliveryOrder.do_id).filter(TripDeliveryOrder.trip_id == trip.id).all()
    ]
    deliveries = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.id.in_(do_ids))
        .with_for_update()
        .all()
    )
    if len(deliveries) != len(do_ids) or any(item.canonical_status != "pending" for item in deliveries):
        raise conflict("DELIVERY_ORDER_NOT_PENDING", "Mọi DO trong chuyến phải đang chờ vận chuyển.")
    parking_list_service.require_loaded_for_dispatch(db, do_ids)

    assignment = ResourceAssignment(
        freight_order_id=order.id,
        trip_id=trip.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        co_driver_id=co_driver.id if co_driver else None,
        assignment_start=assignment_start,
        assignment_end=assignment_end,
        created_by=actor,
    )
    db.add(assignment)
    trip.vehicle_id = vehicle.id
    trip.driver_id = driver.id
    trip.co_driver_id = co_driver.id if co_driver else None
    trip.status = "in_transit"
    trip.version += 1
    trip.updated_at = dt.datetime.now(dt.timezone.utc)
    trip.updated_by = actor
    order.status = "dispatched"
    order.version += 1
    order.updated_at = _now()
    order.updated_by = actor
    for delivery in deliveries:
        delivery.canonical_status = "in_transit"
        delivery.status = "Đang vận chuyển"
        delivery.vehicle_id = vehicle.id
        delivery.driver_id = driver.id
        delivery.co_driver = co_driver.id if co_driver else None
        delivery.version += 1
        delivery.updated_at = _now()
        delivery.updated_by = actor
        parking_list_service.sync_do_status(
            db,
            delivery.id,
            "dispatched",
            actor,
            note=f"Dong bo tu dieu phoi Trip {trip.id}",
        )
    vehicle.status = f"Đang thực hiện {trip.id}"
    mark_crew_busy(driver, vehicle.id, trip.id)
    if co_driver:
        mark_crew_busy(co_driver, vehicle.id, trip.id)
    for delivery in deliveries:
        leg_distances = db.query(TransportTripLeg.distance_km).filter(
            TransportTripLeg.trip_id == trip.id,
            TransportTripLeg.do_id == delivery.id,
            TransportTripLeg.leg_type != "empty_return",
        ).all()
        remaining_distance = sum(float(row[0] or 0) for row in leg_distances)
        tracking = db.get(VehicleTracking, delivery.id) or VehicleTracking(do_id=delivery.id)
        tracking.vehicle_id = vehicle.id
        tracking.lat = None
        tracking.lng = None
        tracking.speed_kmh = 0
        tracking.remaining_distance_km = remaining_distance
        tracking.eta = trip.planned_arrival_at.isoformat() if trip.planned_arrival_at else None
        tracking.planned_return_at = trip.planned_return_at.isoformat() if trip.planned_return_at else None
        tracking.last_update = _now()
        db.add(tracking)
    _audit(db, "DISPATCH_TRIP", "transport_trips", trip.id, actor)
    db.flush()
    return trip
