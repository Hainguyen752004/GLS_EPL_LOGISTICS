from io import BytesIO

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from database import get_db
from models import ParkingLabel
from routes.workflow_routes import _context
from schemas.parking_list import (
    ParkingListAutoCreateRequest,
    ParkingListCreateRequest,
    ParkingListPrintRequest,
    ParkingQrScanRequest,
    ParkingListStatusRequest,
)
from services import parking_list_service as service
from services.errors import DomainError, raise_http


router = APIRouter()


def _response(data, message="Thao tác thành công"):
    return {"message": message, "data": jsonable_encoder(data)}


def _commit(db, callback):
    try:
        value = callback()
        db.commit()
        return value
    except DomainError as exc:
        db.rollback()
        raise_http(exc)
    except Exception:
        db.rollback()
        raise


@router.post("/api/parking-lists/from-do/{do_id}")
def create_from_do(do_id: str, payload: ParkingListCreateRequest, request: Request, db: Session = Depends(get_db)):
    actor = _context(request, db)
    item = _commit(db, lambda: service.generate_from_do(db, do_id, payload.model_dump(), actor))
    return _response(service.serialize(item), "Đã tạo Parking List từ DO")


@router.post("/api/parking-lists/auto-from-do/{do_id}")
def auto_create_from_do(
    do_id: str,
    payload: ParkingListAutoCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = _context(request, db)
    batch = _commit(
        db,
        lambda: service.generate_many_from_do(db, do_id, payload.list_count, actor),
    )
    return _response(batch, "Đã tự động tạo các Packing List từ DO")


@router.get("/api/parking-lists")
def list_parking_lists(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _context(request, db)
    return _response(service.list_parking_lists(db, q=q, status=status, page=page, page_size=page_size))


@router.get("/api/parking-lists/{parking_id}")
def get_parking_list(parking_id: str, request: Request, db: Session = Depends(get_db)):
    _context(request, db)
    try:
        return _response(service.serialize(service._load(db, parking_id)))
    except DomainError as exc:
        raise_http(exc)


@router.get("/api/parking-lists/{parking_id}/label")
def get_label_data(parking_id: str, request: Request, db: Session = Depends(get_db)):
    _context(request, db)
    try:
        return _response(service.serialize(service._load(db, parking_id)))
    except DomainError as exc:
        raise_http(exc)


@router.get("/api/parking-lists/{parking_id}/packing-list")
def get_packing_list_data(parking_id: str, request: Request, db: Session = Depends(get_db)):
    _context(request, db)
    try:
        return _response(service.serialize(service._load(db, parking_id)))
    except DomainError as exc:
        raise_http(exc)


@router.post("/api/parking-lists/{parking_id}/status")
def update_status(parking_id: str, payload: ParkingListStatusRequest, request: Request, db: Session = Depends(get_db)):
    actor = _context(request, db)
    item = _commit(db, lambda: service.transition(db, parking_id, payload.status, actor, payload.note))
    return _response(service.serialize(item), "Đã cập nhật trạng thái Parking List")


@router.post("/api/parking-lists/{parking_id}/print")
def record_print(parking_id: str, payload: ParkingListPrintRequest, request: Request, db: Session = Depends(get_db)):
    actor = _context(request, db)
    item = _commit(db, lambda: service.record_print(db, parking_id, payload.document_type, actor))
    return _response(service.serialize(item), "Đã ghi nhận lịch sử in")


@router.get("/api/parking-qr/{token}")
def scan_parking_qr(token: str, db: Session = Depends(get_db)):
    label = db.query(ParkingLabel).filter(ParkingLabel.qr_token == token).first()
    if not label:
        raise_http(DomainError("PARKING_QR_NOT_FOUND", "Mã QR không hợp lệ hoặc đã hết hiệu lực.", 404))
    item = label.parking_list
    return _response({
        "parking_list_id": item.id,
        "do_id": item.do_id,
        "package_no": label.package_no,
        "package_total": label.package_total,
        "status": item.status,
        "store_id": item.store_id,
        "store_name": item.store_name,
    })


@router.post("/api/parking-qr/{token}/scan")
def record_parking_qr_scan(
    token: str,
    payload: ParkingQrScanRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = _context(request, db)
    item = _commit(
        db,
        lambda: service.scan_label(db, token, payload.action, actor, payload.note),
    )
    return _response(service.serialize(item), "Da ghi nhan quet QR")


@router.get("/api/parking-labels/{label_id}/qr.svg")
def parking_qr_svg(label_id: str, request: Request, db: Session = Depends(get_db)):
    label = db.get(ParkingLabel, label_id)
    if not label:
        raise_http(DomainError("PARKING_LABEL_NOT_FOUND", "Không tìm thấy nhãn kiện hàng.", 404))
    scan_url = str(request.base_url).rstrip("/") + f"/api/parking-qr/{label.qr_token}"
    image = qrcode.make(scan_url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    output = BytesIO()
    image.save(output)
    return Response(content=output.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, no-store"})
