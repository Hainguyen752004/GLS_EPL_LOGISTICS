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
from models import (DeliveryOrder, DeliveryPODDocument, IdempotencyRecord, Quotation,
                    )
from schemas.delivery_completion import DeliveryCompletionRequest
from schemas.pod import DeliveryPODRequest
from schemas.workflow import (
    DeliveryOrderDispatchRequest,
    DeliveryOrderStatusRequest,
    DeliveryOrderUpdateRequest,
    QuotationCreateRequest,
    QuotationUpdateRequest,
    WorkflowStatusRequest,
)
from schemas.common import paginated_query
from services import workflow_service as svc
from services.delivery_completion_service import (
    ALLOWED_POD_MIME_TYPES,
    MAX_POD_BYTES,
    complete_delivery,
)
from services.errors import DomainError, conflict, raise_http


# Chữ ký nhận dạng qua magic byte, cho đúng bộ MIME được phép của POD.
_MAGIC_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF-", "application/pdf"),
)


def _reject_oversized(content: bytes, code: str, message: str) -> None:
    if len(content) > MAX_POD_BYTES:
        raise DomainError(code, message, 413)


def _verified_mime_type(content: bytes, declared: str | None) -> str:
    """Suy ra kiểu tệp từ nội dung thật, không tin theo khai báo của client.

    Kiểu do client khai được lưu lại rồi dùng làm media_type khi phục vụ tệp,
    nên tin theo nó cho phép người gửi tự chọn cách trình duyệt diễn giải nội
    dung mình tải lên. Đường upload ảnh master (main.py::_detect_image_extension)
    đã xác thực magic byte đúng cách; đường POD chỉ là chưa được làm như vậy.
    """
    head = content[:8]
    for signature, mime_type in _MAGIC_SIGNATURES:
        if head.startswith(signature):
            return mime_type
    declared_clean = (declared or "").split(";")[0].strip().lower()
    if declared_clean in ALLOWED_POD_MIME_TYPES:
        # Nội dung không khớp chữ ký nào nhưng client khai kiểu hợp lệ: từ chối
        # thay vì tin lời khai.
        raise DomainError(
            "POD_FILE_TYPE_INVALID",
            "Nội dung tệp không khớp với định dạng đã khai báo. Chỉ nhận JPEG, PNG hoặc PDF.",
            422,
        )
    raise DomainError(
        "POD_FILE_TYPE_INVALID",
        "Chỉ nhận tệp JPEG, PNG hoặc PDF.",
        422,
    )


router = APIRouter()


@router.post("/api/delivery-orders/{do_id}/complete-delivery")
async def complete_delivery_order(do_id: str, request: Request, db: Session = Depends(get_db)):
    actor = _context(request, db)
    key = request.headers.get("Idempotency-Key")
    try:
        form = await request.form()
        raw_payload = form.get("payload")
        if not isinstance(raw_payload, str):
            raise DomainError("PAYLOAD_REQUIRED", "Thiếu payload JSON hoàn tất giao hàng.", 422)
        try:
            payload = DeliveryCompletionRequest.model_validate_json(raw_payload)
        except ValidationError as exc:
            raise DomainError("PAYLOAD_INVALID", str(exc), 422) from exc

        files = {}
        for entry in payload.pod_entries:
            uploaded = form.get(entry.file_field)
            if uploaded is None or not callable(getattr(uploaded, "read", None)):
                raise DomainError(
                    "POD_FILE_REQUIRED", f"Thiếu file POD cho chặng {entry.leg_id}.", 422
                )
            content = await uploaded.read(MAX_POD_BYTES + 1)
            # Kiểm NGAY tại đây, không đợi tới complete_delivery. Schema cho
            # phép 100 mục, mỗi mục một POD kèm một chữ ký, mỗi file tới 10 MB
            # — nếu đọc hết rồi mới kiểm thì ~2 GB đã nằm trong RAM trước khi
            # có bất kỳ lời từ chối nào.
            _reject_oversized(content, "POD_FILE_TOO_LARGE", "Tệp POD tối đa 10 MB.")
            files[entry.file_field] = {
                "file_name": uploaded.filename,
                "mime_type": _verified_mime_type(content, uploaded.content_type),
                "content": content,
            }
            signature = form.get(entry.signature_file_field)
            if signature is None or not callable(getattr(signature, "read", None)):
                raise DomainError(
                    "POD_SIGNATURE_REQUIRED",
                    f"Thiếu chữ ký người nhận cho chặng {entry.leg_id}.",
                    422,
                )
            signature_content = await signature.read(MAX_POD_BYTES + 1)
            _reject_oversized(
                signature_content, "POD_SIGNATURE_TOO_LARGE", "Ảnh chữ ký tối đa 10 MB."
            )
            files[entry.signature_file_field] = {
                "file_name": signature.filename,
                "mime_type": _verified_mime_type(signature_content, signature.content_type),
                "content": signature_content,
            }
        data = complete_delivery(
            db, do_id, payload, files, key, actor, request.url.path,
        )
        db.commit()
        return {"message": "Hoàn tất giao hàng và chốt giá thành công", "data": data}
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
            return {"message": "Hoàn tất giao hàng và chốt giá thành công", "data": data}
        except DomainError as exc:
            db.rollback()
            raise_http(exc)
    except Exception:
        db.rollback()
        raise


@router.get("/api/pod-documents/{document_id}")
def download_pod_document(document_id: str, request: Request, db: Session = Depends(get_db)):
    _context(request, db)
    document = db.get(DeliveryPODDocument, document_id)
    if not document:
        raise_http(DomainError("POD_DOCUMENT_NOT_FOUND", "Không tìm thấy chứng từ POD.", 404))
    safe_name = (document.file_name or "pod-document").replace('"', "")
    # attachment thay vì inline, kèm nosniff: một PDF dựng khéo được phục vụ
    # inline từ chính origin của ứng dụng sẽ chạy được JavaScript trong ngữ
    # cảnh đó. Chỉ trả về kiểu nằm trong danh sách cho phép, để một bản ghi cũ
    # có mime_type lạ không tự chọn được cách trình duyệt diễn giải nó.
    media_type = document.mime_type if document.mime_type in ALLOWED_POD_MIME_TYPES \
        else "application/octet-stream"
    return Response(
        content=document.content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Content-Type-Options": "nosniff",
        },
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
def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Quotation).order_by(Quotation.id.desc())
    return paginated_query(query, page, page_size)


@router.post("/api/quotations")
def create_quotation(request: Request, payload: QuotationCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.create_quotation(db, data, actor))


@router.put("/api/quotations/{qid}")
def update_quotation(qid: str, request: Request, payload: QuotationUpdateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.update_quotation(db, qid, data, actor))


@router.put("/api/quotations/{qid}/approve")
def approve_quotation(qid: str, request: Request, db: Session = Depends(get_db)):
    return _execute(request, db, {}, lambda actor: svc.approve_quotation(db, qid, actor))


@router.put("/api/quotations/{qid}/status")
def quotation_status_compat(qid: str, request: Request, payload: WorkflowStatusRequest, db: Session = Depends(get_db)):
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
def delete_quotation(qid: str, request: Request, db: Session = Depends(get_db)):
    return _delete(request, db, qid, lambda actor: svc.delete_quotation(db, qid, actor))


@router.get("/api/delivery-orders")
def list_delivery_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc())
    return paginated_query(query, page, page_size)


@router.get("/api/delivery-orders/analysis")
def analyze_delivery_orders(db: Session = Depends(get_db)):
    return svc.delivery_order_analysis(db)


@router.put("/api/delivery-orders/{do_id}")
def update_delivery_order(do_id: str, request: Request, payload: DeliveryOrderUpdateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.update_delivery_order(db, do_id, data, actor))


@router.put("/api/delivery-orders/{do_id}/status")
def update_delivery_order_status(do_id: str, request: Request, payload: DeliveryOrderStatusRequest, db: Session = Depends(get_db)):
    data = payload.model_dump()
    status = {
        "In Transit": "in_transit",
        "Đang vận chuyển": "in_transit",
        "in_transit": "in_transit",
        # Mốc "xe đã tới điểm giao, chưa có POD". Nhận cả nhãn tiếng Việt vì
        # thiết bị GPS và script demo gửi cả hai dạng.
        "Arrived": "arrived",
        "arrived": "arrived",
        "Đã đến nơi": "arrived",
        "Đã đến nơi — chờ POD": "arrived",
        "Delivered": "delivered",
        # Giữ cả hai chuỗi cũ: thiết bị và script demo cũ còn gửi chúng.
        "Đã giao hàng": "delivered",
        "Đã giao": "delivered",
        "Đã hoàn tất": "delivered",
        "Completed": "delivered",
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
    return _execute(request, db, data, lambda actor: svc.update_delivery_status(
        db, do_id, status, actor, reason=data.get("reason")))


@router.put("/api/delivery-orders/{do_id}/dispatch")
def dispatch_delivery_order(do_id: str, request: Request, payload: DeliveryOrderDispatchRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return _execute(request, db, data, lambda actor: svc.dispatch(db, do_id, data, actor))


@router.delete("/api/delivery-orders/{do_id}")
def delete_delivery_order(do_id: str, request: Request, db: Session = Depends(get_db)):
    return _delete(request, db, do_id, lambda actor: svc.delete_delivery_order(db, do_id, actor))


@router.post("/api/pod/{do_id}")
def save_pod(do_id: str, request: Request, payload: DeliveryPODRequest, db: Session = Depends(get_db)):
    raise_http(conflict(
        "ATOMIC_COMPLETION_REQUIRED",
        "API POD cũ chỉ còn để đọc. Hãy dùng hoàn tất giao hàng để lưu POD, chữ ký, giá cuối và hóa đơn cùng lúc.",
        ["delivery-completion"],
    ))


@router.get("/api/pod-records")
def list_pod_records_bulk(do_ids: str = "", db: Session = Depends(get_db)):
    """POD cua NHIEU lenh giao hang trong MOT loi goi.

    Duong nay sinh ra vi bang chuyen o man Giao hang & van chuyen phai hien "da
    ky POD may tren tong bao nhieu don" cho TUNG dong. Truoc do chi co duong
    theo tung don, nen ve mot bang N dong phai goi N lan — o quy mo hang nghin
    chuyen thi man hinh khong mo duoc.

    Con so do khong phai trang tri: thieu POD tren mot don la ca chuyen khong
    doi soat duoc va hoa don treo, nen no phai doc duoc ngay tren bang chu khong
    phai mo tung ho so ra dem.

    KHONG bao 404 khi khong co POD nao. Day la duong DOC HANG LOAT: "khong don
    nao trong lo nay co POD" la mot cau tra loi hop le, va bao loi thi ben goi
    phai bat ngoai le cho mot tinh huong binh thuong. Khac voi duong theo mot
    don, o do 404 dung nghia "don nay chua ky".
    """
    ma_sach = [x for x in (do_ids or "").split(",") if x.strip()]
    theo_don = svc.list_pod_records_for_dos(db, ma_sach)
    ket = []
    for ma, dong in theo_don.items():
        for ban_ghi in dong:
            goi = svc._pod_record_payload(ban_ghi)
            # Bao dam co `do_id` trong tung dong: ben goi nhom theo don, va mot
            # dong khong biet no thuoc don nao thi khong nhom duoc.
            goi.setdefault("do_id", ma)
            ket.append(goi)
    return {"records": ket, "do_count": len(theo_don)}


@router.get("/api/pod/{do_id}")
def get_pod(do_id: str, db: Session = Depends(get_db)):
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


# ==========================================================================
# Tep dinh kem cua don van chuyen (hop dong, bao gia da ky)
# --------------------------------------------------------------------------
# Truoc day tab "Tai lieu dinh kem" co mot o chon tep va bao "Da chon hop
# dong/bao gia dinh kem: <ten tep>", nhung khong co upload, khong co
# FormData, va backend cung khong co cho nao de chua. Tep bi bo ngay tai do.
#
# Cac endpoint duoi lam theo dung mau POD, ke ca cac tinh chat an toan cua no.
# ==========================================================================


