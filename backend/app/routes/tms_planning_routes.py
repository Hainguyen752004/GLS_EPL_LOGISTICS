from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import (Carrier, DriverQualification, FreightOrder, FreightUnit,
                    ResourceAssignment, Tender, TenderOffer, TransportDemand,
                    WarehouseAppointment)
from services import tms_dispatch_service as dispatch_service
from services import tms_planning_service as service
from services import tms_tender_service as tender_service
from services import tms_execution_service as execution_service
from services import tms_trip_service as trip_service
from services import tms_scheduling_service as scheduling_service
from services import sap_lich_service
from services.errors import DomainError, conflict, raise_http
from schemas.trip import TripCreateRequest, TripFromDeliveryOrdersRequest
from schemas.dispatch import TripDispatchRequest
from schemas.common import paginated_items


router = APIRouter(prefix="/api/tms", tags=["TMS Core Planning"])


def _actor(request):
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        actor = str(principal.get("id") or principal.get("sub") or principal.get("username") or "").strip()
        if actor:
            return actor
    raise DomainError("AUTHENTICATION_REQUIRED", "Vui lòng đăng nhập để thực hiện thao tác này.", 401)


def _execution_actor(request):
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        actor = str(principal.get("id") or principal.get("sub") or "").strip()
        if actor:
            return actor
    raise DomainError("AUTHENTICATION_REQUIRED", "Vui lòng đăng nhập để thực hiện thao tác này.", 401)


def _command(request, db, action):
    db.info["audit_ip"] = request.client.host if request.client else None
    try:
        entity = action(_actor(request))
        db.commit()
        db.refresh(entity)
        return {"message": "Đã lưu dữ liệu TMS thành công.", "data": entity}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("DUPLICATE_RECORD", "Mã hoặc liên kết nghiệp vụ đã tồn tại."))


def _execution_command(request, db, action, message):
    db.info["audit_ip"] = request.client.host if request.client else None
    try:
        entity = action(_execution_actor(request))
        db.commit()
        db.refresh(entity)
        return {"message": message, "data": entity}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("EXECUTION_CONFLICT", "Dữ liệu thực thi đã thay đổi, vui lòng thử lại."))


def _legacy_delivery_order_id(data):
    if not isinstance(data, dict) or set(data) != {"delivery_order_id"}:
        raise DomainError("LEGACY_LINK_PAYLOAD_INVALID", "Dữ liệu liên kết không hợp lệ.", 422)
    value = data.get("delivery_order_id")
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise DomainError("LEGACY_LINK_PAYLOAD_INVALID", "Dữ liệu liên kết không hợp lệ.", 422)
    return value.strip()


def _idempotency_key(value, label="thao tác chuyến vận tải"):
    if not isinstance(value, str) or not value.strip():
        raise DomainError("IDEMPOTENCY_KEY_REQUIRED", f"Thiếu Idempotency-Key cho {label}.", 422)
    if len(value.strip()) > 128:
        raise DomainError("IDEMPOTENCY_KEY_INVALID", "Idempotency-Key không được vượt quá 128 ký tự.", 422)
    return value.strip()


def _trip_command(request, db, action, message):
    db.info["audit_ip"] = request.client.host if request.client else None
    try:
        data = action(_execution_actor(request))
        db.commit()
        return {"message": message, "data": data}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("TRIP_CONFLICT", "Dữ liệu chuyến vận tải đã thay đổi hoặc bị trùng. Vui lòng tải lại."))


def _scheduling_command(request, db, action, message):
    db.info["audit_ip"] = request.client.host if request.client else None
    try:
        data = action(_actor(request))
        db.commit()
        return {"message": message, "data": data}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("SCHEDULING_CONFLICT", "Lịch tài xế hoặc xe đã thay đổi. Vui lòng tải lại."))


@router.get("/scheduling/driver-shifts")
def list_driver_shifts(start: str = Query(...), end: str = Query(...), db: Session = Depends(get_db)):
    try:
        return {"message": "Đã tải lịch tài xế.", "data": scheduling_service.list_driver_shifts(db, start, end)}
    except DomainError as error:
        raise_http(error)


@router.post("/scheduling/driver-shifts")
def create_driver_shift(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _scheduling_command(
        request, db,
        lambda actor: scheduling_service.save_driver_shift(db, data, actor),
        "Đã lưu ca làm việc vào hệ thống.",
    )


@router.post("/scheduling/driver-shifts/weekly-schedule")
def create_weekly_driver_schedule(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _scheduling_command(
        request, db,
        lambda actor: scheduling_service.save_weekly_driver_schedule(db, data, actor),
        "Da tao lich lam viec mac dinh theo tuan.",
    )


@router.put("/scheduling/driver-shifts/{shift_id}")
def update_driver_shift(request: Request, shift_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    return _scheduling_command(
        request, db,
        lambda actor: scheduling_service.save_driver_shift(db, data, actor, shift_id=shift_id),
        "Đã cập nhật ca làm việc.",
    )


@router.delete("/scheduling/driver-shifts/{shift_id}")
def delete_driver_shift(request: Request, shift_id: str, db: Session = Depends(get_db)):
    return _scheduling_command(
        request, db,
        lambda actor: scheduling_service.delete_driver_shift(db, shift_id, actor),
        "Đã hủy ca làm việc.",
    )


@router.get("/scheduling/board")
def scheduling_board(
    start: str = Query(...),
    days: int = Query(7, ge=1, le=31),
    depot: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Toan bo du lieu cua man "Sap lich xe va tai xe" trong MOT loi goi.

    Mot loi goi chu khong nam, vi ba khoi tren man — luoi nguoi, luoi xe, cot
    viec can lam — phai la ba mat cua MOT su that. Goi rieng thi ba khoi doc o
    ba thoi diem khac nhau va man hinh tu mau thuan.
    """
    try:
        return {
            "message": "Đã tải bảng sắp lịch xe và tài xế.",
            "data": sap_lich_service.bang_sap_lich(db, start, days, depot, team),
        }
    except DomainError as error:
        raise_http(error)


@router.get("/scheduling/fill-candidates")
def scheduling_fill_candidates(
    date: str = Query(...),
    shift: str = Query(...),
    depot: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Nhung nguoi CO THE nhan mot ca dang thieu, xep de truoc kho sau.

    Nguoi nghi phep khong xuat hien. Nguoi dang co ca do hoac dang co chuyen
    trong dung khung gio do cung khong.
    """
    try:
        return {
            "message": "Đã tính danh sách người có thể nhận ca này.",
            "data": sap_lich_service.ung_vien_lap_ca(db, date, shift, depot, team),
        }
    except DomainError as error:
        raise_http(error)


@router.post("/scheduling/generate-from-pattern")
def generate_shifts_from_pattern(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """Sinh ca cho ca mot to tu mau xoay cua tung nguoi.

    Khong ghi de o nao da co lich — ke ca ca da khoa vi co Trip va ca nghi
    phep. Ghi de o day la xoa mot quyet dinh nguoi khac da ra.
    """
    return _scheduling_command(
        request, db,
        lambda actor: sap_lich_service.sinh_lich_theo_mau(db, data, actor),
        "Đã sinh lịch theo mẫu xoay.",
    )


@router.put("/scheduling/drivers/{driver_id}/assignment")
def assign_driver_team(request: Request, driver_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    """Gan bai, to va mau xoay cho mot tai xe."""
    return _scheduling_command(
        request, db,
        lambda actor: sap_lich_service.gan_phan_to(db, driver_id, data, actor),
        "Đã cập nhật bãi, tổ và mẫu xoay của tài xế.",
    )


@router.get("/scheduling/vehicle-availability")
def vehicle_availability(start: str = Query(...), end: str = Query(...), db: Session = Depends(get_db)):
    try:
        return {"message": "Đã tính lịch rảnh và quay đầu của xe.", "data": scheduling_service.list_vehicle_availability(db, start, end)}
    except DomainError as error:
        raise_http(error)


@router.get("/trips")
def list_trips(
    request: Request,
    status: Optional[str] = Query(None),
    freight_order_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        _execution_actor(request)
        items = trip_service.list_trips(
            db,
            status=status,
            freight_order_id=freight_order_id,
            limit=None,
        )
        return paginated_items(items, page, page_size)
    except DomainError as error:
        raise_http(error)


@router.post("/trips")
def create_trip(request: Request, payload: TripCreateRequest,
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                db: Session = Depends(get_db)):
    _idempotency_key(idempotency_key, "tạo chuyến vận tải")
    data = payload.model_dump(exclude_unset=True)
    return _trip_command(
        request, db,
        lambda actor: trip_service.create_trip_payload(db, data, actor),
        "Đã tạo chuyến vận tải.",
    )


@router.post("/trips/from-delivery-orders")
def create_trip_from_delivery_orders(
    request: Request,
    data: TripFromDeliveryOrdersRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    _idempotency_key(idempotency_key, "tạo chuyến từ DO")
    payload = data.model_dump()
    return _trip_command(
        request,
        db,
        lambda actor: trip_service.create_trip_from_delivery_orders(db, payload, actor),
        "Đã tạo chuyến và các chặng từ tuyến Master Data.",
    )


@router.put("/trips/{trip_id}/dispatch")
def dispatch_trip(
    request: Request,
    trip_id: str,
    data: TripDispatchRequest,
    db: Session = Depends(get_db),
):
    payload = data.model_dump()
    return _trip_command(
        request,
        db,
        lambda actor: trip_service.serialize_trip(
            db, dispatch_service.dispatch_trip(db, trip_id, payload, actor)
        ),
        "Đã điều phối xe, tài xế và chuyển DO sang đang vận chuyển.",
    )


@router.get("/trips/{trip_id}")
def get_trip(request: Request, trip_id: str, db: Session = Depends(get_db)):
    try:
        _execution_actor(request)
        return {"message": "Đã tải hồ sơ chuyến vận tải.", "data": trip_service.get_trip_detail(db, trip_id)}
    except DomainError as error:
        raise_http(error)


@router.post("/trips/{trip_id}/legs")
def add_trip_leg(request: Request, trip_id: str, data: dict = Body(...),
                 idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                 db: Session = Depends(get_db)):
    _idempotency_key(idempotency_key, "thêm chặng vận tải")
    payload = dict(data or {})
    expected_version = payload.pop("expected_version", None)
    return _trip_command(
        request, db,
        lambda actor: trip_service.add_leg_payload(db, trip_id, payload, expected_version, actor),
        "Đã thêm chặng vận tải và tính lại ETA.",
    )


@router.post("/trips/{trip_id}/complete-return")
def complete_trip_return(request: Request, trip_id: str, data: dict = Body(...),
                         idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                         db: Session = Depends(get_db)):
    _idempotency_key(idempotency_key, "xac nhan xe quay ve")
    if not isinstance(data, dict) or set(data) != {"expected_version", "actual_return_at"}:
        raise_http(DomainError("RETURN_COMPLETION_PAYLOAD_INVALID", "Du lieu xac nhan xe quay ve khong hop le.", 422))
    return _trip_command(
        request, db,
        lambda actor: trip_service.complete_return(db, trip_id, data, actor),
        "Da xac nhan xe quay ve va giai phong nguon luc.",
    )


@router.get("/freight-orders/{order_id}/events")
def list_transport_events(request: Request, order_id: str, db: Session = Depends(get_db)):
    try:
        _execution_actor(request)
        return {"message": "Đã tải lịch sử sự kiện vận tải.", "data": execution_service.list_events(db, order_id)}
    except DomainError as error:
        raise_http(error)


@router.post("/freight-orders/{order_id}/events")
def record_transport_event(request: Request, order_id: str, data: dict = Body(...),
                           idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                           db: Session = Depends(get_db)):
    return _execution_command(
        request, db, lambda actor: execution_service.record_event(db, order_id, data, idempotency_key, actor),
        "Đã ghi nhận sự kiện vận tải.",
    )


@router.get("/freight-orders/{order_id}/latest-position")
def get_latest_transport_position(request: Request, order_id: str, db: Session = Depends(get_db)):
    try:
        _execution_actor(request)
        return {"message": "Đã tải vị trí mới nhất.", "data": execution_service.latest_position(db, order_id)}
    except DomainError as error:
        raise_http(error)


@router.post("/freight-orders/{order_id}/legacy-link")
def link_legacy_delivery_order(request: Request, order_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    return _execution_command(
        request, db,
        lambda actor: execution_service.link_legacy_delivery_order(db, order_id, _legacy_delivery_order_id(data), actor),
        "Đã cấu hình liên kết lệnh giao hàng cũ.",
    )


@router.get("/demands")
def list_demands(db: Session = Depends(get_db)):
    return db.query(TransportDemand).order_by(TransportDemand.created_at.desc()).limit(100).all()


@router.post("/demands")
def create_demand(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: service.create_demand(db, data, actor))


@router.put("/demands/{demand_id}/submit")
def submit_demand(request: Request, demand_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: service.submit_demand(db, demand_id, data.get("expected_version"), actor))


@router.get("/freight-units")
def list_freight_units(db: Session = Depends(get_db)):
    return db.query(FreightUnit).order_by(FreightUnit.created_at.desc()).limit(100).all()


@router.post("/freight-units/from-demand/{demand_id}")
def create_freight_unit(request: Request, demand_id: str, db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: service.create_freight_unit_from_demand(db, demand_id, actor))


@router.get("/freight-orders")
def list_freight_orders(db: Session = Depends(get_db)):
    return db.query(FreightOrder).order_by(FreightOrder.created_at.desc()).limit(100).all()


@router.post("/freight-orders")
def create_freight_order(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: service.create_freight_order(db, data, actor))


@router.get("/carriers")
def list_carriers(db: Session = Depends(get_db)):
    return db.query(Carrier).order_by(Carrier.created_at.desc()).limit(100).all()


@router.post("/carriers")
def create_carrier(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: tender_service.create_carrier(db, data, actor))


@router.put("/carriers/{carrier_id}")
def update_carrier(request: Request, carrier_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    def action(actor):
        carrier = db.get(Carrier, carrier_id)
        if not carrier:
            raise DomainError("CARRIER_NOT_FOUND", "Không tìm thấy carrier/vendor cần sửa.", 404)
        name = str((data or {}).get("name") or "").strip()
        if not name:
            raise DomainError("INVALID_CARRIER", "Cần nhập tên carrier/vendor.", 422)
        carrier.name = name
        carrier.tax_code = (data or {}).get("tax_code")
        carrier.contact_person = (data or {}).get("contact_person")
        carrier.phone = (data or {}).get("phone")
        carrier.email = (data or {}).get("email")
        carrier.is_internal = bool((data or {}).get("is_internal", False))
        carrier.status = (data or {}).get("status") or carrier.status or "active"
        tender_service._audit(db, "UPDATE_CARRIER", "carriers", carrier.id, actor)
        return carrier
    return _command(request, db, action)


@router.post("/carriers/{carrier_id}/status")
def set_carrier_status(request: Request, carrier_id: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    def action(actor):
        carrier = db.get(Carrier, carrier_id)
        if not carrier:
            raise DomainError("CARRIER_NOT_FOUND", "Không tìm thấy carrier/vendor cần cập nhật.", 404)
        status = str((data or {}).get("status") or "active").strip().lower()
        if status not in {"active", "inactive"}:
            raise DomainError("INVALID_CARRIER_STATUS", "Trạng thái carrier/vendor chỉ được là hoạt động hoặc ngưng hoạt động.", 422)
        carrier.status = status
        tender_service._audit(db, "SET_CARRIER_STATUS", "carriers", carrier.id, actor)
        return carrier
    return _command(request, db, action)


@router.delete("/carriers/{carrier_id}")
def delete_carrier(request: Request, carrier_id: str, db: Session = Depends(get_db)):
    db.info["audit_ip"] = request.client.host if request.client else None
    try:
      carrier = db.get(Carrier, carrier_id)
      if not carrier:
          raise DomainError("CARRIER_NOT_FOUND", "Không tìm thấy carrier/vendor cần xóa.", 404)
      db.delete(carrier)
      db.commit()
      return {"message": "Đã xóa carrier/vendor khỏi Master Data.", "data": {"id": carrier_id}}
    except DomainError as error:
      db.rollback()
      raise_http(error)
    except IntegrityError:
      db.rollback()
      raise_http(conflict("CARRIER_IN_USE", "Carrier/vendor đang được dùng trong tender hoặc chi phí, vui lòng khóa thay vì xóa."))


@router.get("/tenders")
def list_tenders(db: Session = Depends(get_db)):
    return db.query(Tender).order_by(Tender.created_at.desc()).limit(100).all()


@router.post("/tenders")
def publish_tender(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: tender_service.publish_tender(db, data, actor))


@router.get("/tenders/{tender_id}/offers")
def list_tender_offers(tender_id: str, db: Session = Depends(get_db)):
    return db.query(TenderOffer).filter(TenderOffer.tender_id == tender_id).order_by(TenderOffer.amount).all()


@router.post("/tenders/{tender_id}/offers")
def submit_tender_offer(request: Request, tender_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: tender_service.submit_offer(db, tender_id, data, actor))


@router.put("/tenders/{tender_id}/award")
def award_tender(request: Request, tender_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: tender_service.award_offer(
        db, tender_id, data.get("offer_id"), data.get("expected_version"), actor
    ))


@router.get("/driver-qualifications")
def list_driver_qualifications(
    paginated: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Danh sách bằng lái đã khai.

    PHẢI phân trang được, không phải để cho gọn màn hình mà để màn hình KHÔNG
    NÓI DỐI. Bản trước cắt cứng ở 100 dòng, và màn "Tài xế & bằng lái" đối chiếu
    danh sách này với danh sách tài xế để kết luận ai thiếu bằng. Ở quy mô thật
    (hàng trăm tài xế), tài xế thứ 101 trở đi sẽ không có dòng bằng lái nào
    trong gói trả về, nên màn hình kết luận "thiếu bằng lái — chặn điều phối"
    cho những người ĐANG CÓ bằng hợp lệ. Một con số sai mà không có cảnh báo
    còn tệ hơn một ô trống, vì người vận hành tin vào nó.

    Giữ nguyên nếp của `GET /api/vehicles`: không truyền gì thì trả về mảng như
    cũ (100 dòng đầu) để những chỗ gọi cũ không vỡ; truyền `paginated=true` thì
    trả về `{items, page, page_size, total}` để phía giao diện kéo hết.
    """
    query = db.query(DriverQualification).order_by(DriverQualification.driver_id)
    if not paginated:
        return query.limit(100).all()
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.post("/driver-qualifications")
def save_driver_qualification(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: dispatch_service.save_driver_qualification(db, data, actor))


@router.get("/warehouse-appointments")
def list_warehouse_appointments(db: Session = Depends(get_db)):
    return db.query(WarehouseAppointment).order_by(WarehouseAppointment.scheduled_start.desc()).limit(100).all()


@router.post("/warehouse-appointments")
def book_warehouse_appointment(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: dispatch_service.book_appointment(db, data, actor))


@router.get("/resource-assignments")
def list_resource_assignments(db: Session = Depends(get_db)):
    return db.query(ResourceAssignment).order_by(ResourceAssignment.created_at.desc()).limit(100).all()


@router.put("/freight-orders/{order_id}/dispatch")
def dispatch_freight_order(request: Request, order_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    return _command(request, db, lambda actor: dispatch_service.dispatch_freight_order(db, order_id, data, actor))

