from typing import Optional

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import APInvoice, FreightActualCost, FreightSettlement
from services import tms_ap_service, tms_cost_service, tms_journal_service, tms_settlement_service
from services.errors import DomainError, conflict, raise_http
from services.finance_authorization import resolve_finance_context
from schemas.cost import TripActualCostRequest


router = APIRouter(prefix="/api/tms/finance", tags=["TMS Finance"])


def _serialize_actual_cost(cost):
    total_amount = cost.total_amount
    if not total_amount:
        total_amount = sum(
            (item.total_amount or item.actual_amount or 0) + (item.rounding_adjustment or 0)
            for item in cost.items
        )
    return {
        "id": cost.id,
        "trip_id": cost.trip_id,
        "freight_order_id": cost.freight_order_id,
        "carrier_id": cost.carrier_id,
        "currency_code": cost.currency_code,
        "total_amount": total_amount,
        "status": cost.status,
        "version": cost.version,
        "lines": [
            {
                "id": item.id,
                "name": item.description,
                "original_amount": item.original_amount,
                "actual_amount": item.actual_amount,
                "increase_amount": item.increase_amount,
                "note": item.note,
            }
            for item in cost.items
        ],
    }


def _principal(request):
    return getattr(request.state, "principal", None)


def _context(request, db, required):
    db.info["request_ip"] = request.client.host if request.client else None
    try:
        return resolve_finance_context(db, _principal(request), set(required))
    except DomainError as error:
        raise_http(error)


def _key(value):
    if not isinstance(value, str) or not value.strip():
        raise_http(DomainError("IDEMPOTENCY_KEY_REQUIRED", "Thiếu Idempotency-Key cho thao tác tài chính.", 422))
    return value.strip()


def _execute(db, action):
    try:
        entity = action()
        db.commit()
        if hasattr(entity, "__table__"):
            db.refresh(entity)
        return {"message": "Đã xử lý nghiệp vụ tài chính thành công.", "data": jsonable_encoder(entity)}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("FINANCE_CONFLICT", "Dữ liệu tài chính đã thay đổi hoặc bị trùng. Vui lòng tải lại."))


@router.get("/costs")
def list_costs(request: Request, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    costs = db.query(FreightActualCost).order_by(FreightActualCost.created_at.desc()).limit(100).all()
    return {"message": "Đã tải chi phí vận tải.", "data": [_serialize_actual_cost(cost) for cost in costs]}


@router.get("/costs/{cost_id}")
def get_cost(request: Request, cost_id: str, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    entity = db.get(FreightActualCost, cost_id)
    if entity is None:
        raise_http(DomainError("COST_NOT_FOUND", "Không tìm thấy hồ sơ chi phí.", 404))
    return {"message": "Đã tải hồ sơ chi phí.", "data": _serialize_actual_cost(entity)}


@router.put("/trips/{trip_id}/actual-cost")
def save_trip_actual_cost(
    request: Request,
    trip_id: str,
    data: TripActualCostRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    actor, permissions = _context(request, db, {"finance_creator"})
    payload = data.model_dump()
    result = _execute(db, lambda: tms_cost_service.save_trip_cost_rows(
        db,
        trip_id,
        payload,
        request.method,
        request.url.path,
        _key(idempotency_key),
        actor,
        permissions,
    ))
    cost_id = result["data"]["id"]
    cost = db.get(FreightActualCost, cost_id)
    result["data"] = _serialize_actual_cost(cost)
    return result


@router.get("/trips/{trip_id}/actual-cost")
def get_trip_actual_cost(request: Request, trip_id: str, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    cost = (
        db.query(FreightActualCost)
        .filter(FreightActualCost.trip_id == trip_id, FreightActualCost.is_active.is_(True))
        .order_by(FreightActualCost.updated_at.desc())
        .first()
    )
    if cost is None:
        raise_http(DomainError("COST_NOT_FOUND", "Chưa có chi phí thực tế cho chuyến xe này.", 404))
    return {"message": "Đã tải chi phí thực tế của chuyến xe.", "data": _serialize_actual_cost(cost)}


@router.post("/freight-orders/{order_id}/costs")
def create_cost(request: Request, order_id: str, data: dict = Body(...),
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.create_cost(
        db, order_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.post("/costs/{cost_id}/submit")
def submit_cost(request: Request, cost_id: str, data: dict = Body(...),
                idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.submit_cost(
        db, cost_id, data.get("expected_version"), request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.post("/costs/{cost_id}/items")
def save_cost_item(request: Request, cost_id: str, data: dict = Body(...),
                   idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                   db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.save_charge_item(
        db, cost_id, data, data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.delete("/costs/{cost_id}/items/{item_id}")
def delete_cost_item(request: Request, cost_id: str, item_id: str, data: dict = Body(default={}),
                     idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                     db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.delete_draft_charge_item(
        db, cost_id, item_id, data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.post("/costs/{cost_id}/documents")
def save_cost_document(request: Request, cost_id: str, data: dict = Body(...),
                       idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                       db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.save_cost_document(
        db, cost_id, data, data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.put("/costs/{cost_id}/documents/{document_id}")
def update_cost_document(request: Request, cost_id: str, document_id: str, data: dict = Body(...),
                         idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                         db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.update_cost_document(
        db, cost_id, document_id, data, data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.delete("/costs/{cost_id}/documents/{document_id}")
def delete_cost_document(request: Request, cost_id: str, document_id: str, data: dict = Body(default={}),
                         idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                         db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_cost_service.delete_draft_cost_document(
        db, cost_id, document_id, data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.post("/costs/{cost_id}/approve")
def approve_cost(request: Request, cost_id: str, data: dict = Body(...),
                 idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                 db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_approver"})
    return _execute(db, lambda: tms_cost_service.approve_cost(
        db, cost_id, data.get("expected_version"), request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.post("/costs/{cost_id}/reverse")
def reverse_cost(request: Request, cost_id: str, data: dict = Body(...),
                 idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                 db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_poster"})
    return _execute(db, lambda: tms_cost_service.reverse_cost(
        db, cost_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.get("/ap-invoices")
def list_ap_invoices(request: Request, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    return {"message": "Đã tải hóa đơn phải trả.", "data": db.query(APInvoice).order_by(APInvoice.created_at.desc()).limit(100).all()}


@router.get("/ap-invoices/{ap_id}")
def get_ap_invoice(request: Request, ap_id: str, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    entity = db.get(APInvoice, ap_id)
    if entity is None:
        raise_http(DomainError("AP_NOT_FOUND", "Không tìm thấy hóa đơn phải trả.", 404))
    return {"message": "Đã tải hóa đơn phải trả.", "data": entity}


@router.post("/costs/{cost_id}/ap-invoices")
def create_ap(request: Request, cost_id: str, data: dict = Body(...),
              idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
              db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_ap_service.create_ap_from_cost(
        db, cost_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.post("/ap-invoices/{ap_id}/submit")
def submit_ap(request: Request, ap_id: str, data: dict = Body(...),
              idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
              db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_creator"})
    return _execute(db, lambda: tms_ap_service.transition_ap(
        db, ap_id, "submit", data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.post("/ap-invoices/{ap_id}/approve")
def approve_ap(request: Request, ap_id: str, data: dict = Body(...),
               idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
               db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_approver"})
    return _execute(db, lambda: tms_ap_service.transition_ap(
        db, ap_id, "approve", data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.post("/ap-invoices/{ap_id}/post")
def post_ap(request: Request, ap_id: str, data: dict = Body(...),
            idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
            db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_poster"})
    def callback(ap):
        return tms_journal_service._post_ap_journal(db, ap, actor).id
    db.info["ap_post_callback"] = callback
    return _execute(db, lambda: tms_ap_service.transition_ap(
        db, ap_id, "post", data.get("expected_version"), request.method, request.url.path,
        _key(idempotency_key), actor, permissions))


@router.post("/ap-invoices/{ap_id}/reverse")
def reverse_ap(request: Request, ap_id: str, data: dict = Body(...),
               idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
               db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_poster"})
    return _execute(db, lambda: tms_ap_service.reverse_ap(
        db, ap_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.post("/ap-invoices/{ap_id}/settlements")
def create_settlement(request: Request, ap_id: str, data: dict = Body(default={}),
                      idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                      db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_payment"})
    return _execute(db, lambda: tms_settlement_service.create_settlement(
        db, ap_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.get("/settlements")
def list_settlements(request: Request, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    return {"message": "Đã tải hồ sơ đối soát.", "data": db.query(FreightSettlement).order_by(FreightSettlement.created_at.desc()).limit(100).all()}


@router.get("/settlements/{settlement_id}")
def get_settlement(request: Request, settlement_id: str, db: Session = Depends(get_db)):
    _context(request, db, {"finance_read"})
    entity = db.get(FreightSettlement, settlement_id)
    if entity is None:
        raise_http(DomainError("SETTLEMENT_NOT_FOUND", "Không tìm thấy hồ sơ đối soát.", 404))
    return {"message": "Đã tải hồ sơ đối soát.", "data": entity}


@router.post("/settlements/{settlement_id}/payments")
def post_payment(request: Request, settlement_id: str, data: dict = Body(...),
                 idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                 db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_payment"})
    return _execute(db, lambda: tms_settlement_service.post_payment(
        db, settlement_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.post("/settlement-payments/{payment_id}/reverse")
def reverse_payment(request: Request, payment_id: str, data: dict = Body(...),
                    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
                    db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_payment"})
    return _execute(db, lambda: tms_settlement_service.reverse_payment(
        db, payment_id, data, request.method, request.url.path, _key(idempotency_key), actor, permissions))


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    actor, permissions = _context(request, db, {"finance_read"})
    return {"message": "Đã tải dashboard tài chính vận tải.", "data": tms_settlement_service.get_finance_dashboard(db, {}, actor, permissions)}

