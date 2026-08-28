import datetime
import hashlib
import json
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import DeliveryOrder, DeliveryPODDocument, IdempotencyRecord, Quotation, SalesOrder
from schemas.delivery_completion import DeliveryCompletionRequest
from schemas.pod import DeliveryPODRequest
from schemas.workflow import (
    DeliveryOrderCreateRequest,
    DeliveryOrderDispatchRequest,
    DeliveryOrderStatusRequest,
    DeliveryOrderUpdateRequest,
    QuotationCreateRequest,
    QuotationUpdateRequest,
    SalesOrderCreateRequest,
    SalesOrderUpdateRequest,
    WorkflowStatusRequest,
)
from schemas.common import paginated_query
from services import workflow_service as svc
from services.delivery_completion_service import complete_delivery
from services.errors import DomainError, conflict, raise_http


router = APIRouter()


@router.post("/api/delivery-orders/{do_id}/complete-delivery")
async def complete_delivery_order(do_id: str, request: Request, db: Session = Depends(get_db)):
    actor = _context(request, db)
    key = request.headers.get("Idempotency-Key")
    try:
        form = await request.form()
        raw_payload = form.get("payload")
        if not isinstance(raw_payload, str):
            raise DomainError("PAYLOAD_REQUIRED", "Thiáº¿u payload JSON hoÃ n táº¥t giao hÃ ng.", 422)
        try:
            payload = DeliveryCompletionRequest.model_validate_json(raw_payload)
        except ValidationError as exc:
            raise DomainError("PAYLOAD_INVALID", str(exc), 422) from exc

        files = {}
        for entry in payload.pod_entries:
            uploaded = form.get(entry.file_field)
            if uploaded is None or not callable(getattr(uploaded, "read", None)):
                raise DomainError(
                    "POD_FILE_REQUIRED", f"Thiáº¿u file POD cho cháº·ng {entry.leg_id}.", 422
                )
            content = await uploaded.read(10 * 1024 * 1024 + 1)
            files[entry.file_field] = {
                "file_name": uploaded.filename,
                "mime_type": uploaded.content_type,
                "content": content,
            }
            signature = form.get(entry.signature_file_field)
            if signature is None or not callable(getattr(signature, "read", None)):
                raise DomainError(
                    "POD_SIGNATURE_REQUIRED",
                    f"Thiếu chữ ký người nhận cho chặng {entry.leg_id}.",
                    422,
                )
            signature_content = await signature.read(10 * 1024 * 1024 + 1)
            files[entry.signature_file_field] = {
                "file_name": signature.filename,
                "mime_type": signature.content_type,
                "content": signature_content,
            }
        data = complete_delivery(
            db, do_id, payload, files, key, actor, request.url.path,
        )
        db.commit()
        return {"message": "HoÃ n táº¥t giao hÃ ng vÃ  chá»‘t giÃ¡ thÃ nh cÃ´ng", "data": data}
    except DomainError as exc:
        db.rollback()
        raise_http(exc)
    except IntegrityError:
        db.rollback()
        try:
            data = complete_delivery(
                db, do_id, payload, files, key, actor, request.url.path,
            )
            db.commit()
            return {"message": "HoÃ n táº¥t giao hÃ ng vÃ  chá»‘t giÃ¡ thÃ nh cÃ´ng", "data": data}
        except DomainError as exc:
            db.rollback()
            raise_http(exc)
    except Exception:
        db.rollback()
        raise


@router.get("/api/pod-documents/{document_id}")
async def download_pod_document(document_id: str, request: Request, db: Session = Depends(get_db)):
    _context(request, db)
    document = db.get(DeliveryPODDocument, document_id)
    if not document:
        raise_http(DomainError("POD_DOCUMENT_NOT_FOUND", "KhÃ´ng tÃ¬m tháº¥y chá»©ng tá»« POD.", 404))
    safe_name = (document.file_name or "pod-document").replace('"', "")
    return Response(
        content=document.content,
        media_type=document.mime_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


def _serialize_datetime(value: datetime.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _actor(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise_http(DomainError(
            "AUTHENTICATION_REQUIRED",
            "Vui lòng đăng nhập để thực hiện nghiệp vụ này.",
            401,
        ))
    if isinstance(principal, str):
        if principal.strip():
            return principal.strip()
        raise_http(DomainError(
            "AUTHENTICATION_REQUIRED",
            "Không xác định được người dùng đã xác thực.",
            401,
        ))
    for name in ("id", "sub", "username"):
        value = getattr(principal, name, None)
        if value:
            return str(value)
    if isinstance(principal, dict):
        value = principal.get("id") or principal.get("sub") or principal.get("username")
        if value:
            return str(value)
    raise_http(DomainError(
        "AUTHENTICATION_REQUIRED",
        "Không xác định được người dùng đã xác thực.",
        401,
    ))


def _context(request: Request, db: Session):
    actor = _actor(request)
    db.info["audit_ip"] = request.client.host if request.client else None
    return actor


def _idempotency(request, actor, data):
    key = request.headers.get("Idempotency-Key")
    if not key:
        return None, None, None
    operation = f"{request.method}:{request.url.path}:{actor}"
    request_hash = hashlib.sha256(json.dumps(
        data or {},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode()).hexdigest()
    return key, operation, request_hash


def _idempotency_record(db, request, actor, key):
    if not hasattr(db, "query"):
        return db.get(IdempotencyRecord, key)
    return db.query(IdempotencyRecord).filter_by(
        actor=actor,
        method=request.method,
        path=request.url.path,
        idempotency_key=key,
    ).one_or_none()


def _replay_response(record):
    try:
        response = json.loads(record.response_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        response = None
    if not isinstance(response, dict) or not isinstance(response.get("message"), str) or "data" not in response:
        raise_http(conflict(
            "IDEMPOTENCY_RECORD_CORRUPT",
            "Bản ghi idempotency không hợp lệ. Vui lòng liên hệ quản trị viên.",
        ))
    return response


def _execute(request, db, data, callback):
    actor = _context(request, db)
    scoped_key, operation, request_hash = _idempotency(request, actor, data)
    if scoped_key:
        existing = _idempotency_record(db, request, actor, scoped_key)
        if existing:
            if existing.operation != operation or existing.request_hash != request_hash:
                raise_http(conflict(
                    "IDEMPOTENCY_CONFLICT",
                    "Idempotency-Key đã được dùng với nội dung khác.",
                ))
            return _replay_response(existing)
    try:
        value = callback(actor)
        db.flush()
        if hasattr(value, "__table__"):
            db.refresh(value)
        response = {
            "message": "Thao tác thành công",
            "data": jsonable_encoder(
                value,
                custom_encoder={datetime.datetime: _serialize_datetime},
            ),
        }
        if scoped_key:
            db.add(IdempotencyRecord(
                actor=actor,
                method=request.method,
                path=request.url.path,
                idempotency_key=scoped_key,
                operation=operation,
                request_hash=request_hash,
                response_json=json.dumps(response, ensure_ascii=False),
            ))
            db.flush()
        db.commit()
        return response
    except DomainError as exc:
        db.rollback()
        if scoped_key:
            existing = _idempotency_record(db, request, actor, scoped_key)
            if existing:
                if existing.operation == operation and existing.request_hash == request_hash:
                    return _replay_response(existing)
                raise_http(conflict(
                    "IDEMPOTENCY_CONFLICT",
                    "Idempotency-Key đã được dùng với nội dung khác.",
                ))
        raise_http(exc)
    except IntegrityError:
        db.rollback()
        if scoped_key:
            existing = _idempotency_record(db, request, actor, scoped_key)
            if existing and existing.request_hash == request_hash:
                return _replay_response(existing)
        raise_http(conflict("DUPLICATE_RECORD", "Mã dữ liệu đã tồn tại."))


@router.get("/api/quotations")
async def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Quotation).order_by(Quotation.id.desc())
    return paginated_query(query, page, page_size)


@router.post("/api/quotations")
async def create_quotation(request: Request, payload: QuotationCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.create_quotation(db, data, actor))


@router.put("/api/quotations/{qid}")
async def update_quotation(qid: str, request: Request, payload: QuotationUpdateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.update_quotation(db, qid, data, actor))


@router.put("/api/quotations/{qid}/approve")
async def approve_quotation(qid: str, request: Request, db: Session = Depends(get_db)):
    return _execute(request, db, {}, lambda actor: svc.approve_quotation(db, qid, actor))


@router.put("/api/quotations/{qid}/status")
async def quotation_status_compat(qid: str, request: Request, payload: WorkflowStatusRequest, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data.get("status") not in ("Approved", "Đã duyệt", "approved"):
        raise_http(conflict(
            "INVALID_TRANSITION",
            "Báo giá chỉ được chuyển trạng thái qua bước duyệt chuẩn.",
        ))
    return _execute(request, db, data, lambda actor: svc.approve_quotation(db, qid, actor))


def _delete(request, db, identity, action):
    return _execute(request, db, {}, lambda actor: (action(actor), {"id": identity})[1])


@router.delete("/api/quotations/{qid}")
async def delete_quotation(qid: str, request: Request, db: Session = Depends(get_db)):
    return _delete(request, db, qid, lambda actor: svc.delete_quotation(db, qid, actor))


@router.get("/api/sales-orders")
async def list_sales_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(SalesOrder).order_by(SalesOrder.id.desc())
    return paginated_query(query, page, page_size)


@router.post("/api/sales-orders")
async def create_sales_order(request: Request, payload: SalesOrderCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.create_sales_order(db, data, actor))


@router.put("/api/sales-orders/{so_id}")
async def update_sales_order(so_id: str, request: Request, payload: SalesOrderUpdateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.update_sales_order(db, so_id, data, actor))


@router.put("/api/sales-orders/{so_id}/confirm")
async def confirm_sales_order(so_id: str, request: Request, db: Session = Depends(get_db)):
    return _execute(request, db, {}, lambda actor: svc.confirm_sales_order(db, so_id, actor))


@router.put("/api/sales-orders/{so_id}/status")
async def sales_order_status_compat(so_id: str, request: Request, payload: WorkflowStatusRequest, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data.get("status") not in ("Confirmed", "Đã xác nhận", "confirmed"):
        raise_http(conflict(
            "INVALID_TRANSITION",
            "Đơn hàng chỉ được chuyển trạng thái qua bước xác nhận chuẩn.",
        ))
    return _execute(request, db, data, lambda actor: svc.confirm_sales_order(db, so_id, actor))


@router.delete("/api/sales-orders/{so_id}")
async def delete_sales_order(so_id: str, request: Request, db: Session = Depends(get_db)):
    return _delete(request, db, so_id, lambda actor: svc.delete_sales_order(db, so_id, actor))


@router.get("/api/delivery-orders")
async def list_delivery_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc())
    return paginated_query(query, page, page_size)


@router.get("/api/delivery-orders/analysis")
async def analyze_delivery_orders(db: Session = Depends(get_db)):
    return svc.delivery_order_analysis(db)


@router.post("/api/delivery-orders")
async def create_delivery_order(request: Request, payload: DeliveryOrderCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.create_delivery_order(db, data, actor))


@router.put("/api/delivery-orders/{do_id}")
async def update_delivery_order(do_id: str, request: Request, payload: DeliveryOrderUpdateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.update_delivery_order(db, do_id, data, actor))


@router.put("/api/delivery-orders/{do_id}/status")
async def update_delivery_order_status(do_id: str, request: Request, payload: DeliveryOrderStatusRequest, db: Session = Depends(get_db)):
    data = payload.model_dump()
    status = {
        "In Transit": "in_transit",
        "Đang vận chuyển": "in_transit",
        "in_transit": "in_transit",
        "Delivered": "delivered",
        "Đã giao hàng": "delivered",
        "delivered": "delivered",
        "Cancelled": "cancelled",
        "Canceled": "cancelled",
        "Đã hủy": "cancelled",
        "cancelled": "cancelled",
    }.get(data.get("status"))
    if not status:
        raise_http(conflict("INVALID_STATUS", "Trạng thái lệnh giao hàng không hợp lệ."))
    if status == "delivered":
        raise_http(conflict(
            "ATOMIC_COMPLETION_REQUIRED",
            "Phải hoàn tất DO bằng hồ sơ POD, chữ ký và chốt giá trong cùng một giao dịch.",
            ["delivery-completion"],
        ))
    return _execute(request, db, data, lambda actor: svc.update_delivery_status(db, do_id, status, actor))


@router.put("/api/delivery-orders/{do_id}/dispatch")
async def dispatch_delivery_order(do_id: str, request: Request, payload: DeliveryOrderDispatchRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.dispatch(db, do_id, data, actor))


@router.delete("/api/delivery-orders/{do_id}")
async def delete_delivery_order(do_id: str, request: Request, db: Session = Depends(get_db)):
    return _delete(request, db, do_id, lambda actor: svc.delete_delivery_order(db, do_id, actor))


@router.post("/api/pod/{do_id}")
async def save_pod(do_id: str, request: Request, payload: DeliveryPODRequest, db: Session = Depends(get_db)):
    raise_http(conflict(
        "ATOMIC_COMPLETION_REQUIRED",
        "API POD cũ chỉ còn để đọc. Hãy dùng hoàn tất giao hàng để lưu POD, chữ ký, giá cuối và hóa đơn cùng lúc.",
        ["delivery-completion"],
    ))


@router.get("/api/pod/{do_id}")
async def get_pod(do_id: str, db: Session = Depends(get_db)):
    records = svc.list_pod_records(db, do_id)
    if not records:
        raise_http(DomainError(
            "POD_NOT_FOUND",
            f"Chưa có POD cho lệnh giao hàng {do_id}.",
            404,
            ["pod", "tracking"],
        ))
    latest = records[-1]
    record_payloads = [svc._pod_record_payload(record) for record in records]
    return {
        "do_id": do_id,
        "delivery_time": getattr(latest, "delivery_time", None),
        "photo_url": getattr(latest, "photo_url", None),
        "signature_url": getattr(latest, "signature_url", None),
        "note": getattr(latest, "note", None),
        "records": record_payloads,
        "completion": {
            "pod_count": len(record_payloads),
            "has_pod": bool(record_payloads),
        },
    }
