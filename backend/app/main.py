import os
import sys
import json
import threading
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from uuid import uuid4
from decimal import Decimal, InvalidOperation

# Workaround for Protobuf >= 4.x compatibility with PaddleOCR / PaddlePaddle
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Depends, HTTPException, Body, UploadFile, File, Form, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
import base64
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.append(app_dir)

from database import get_db, auto_migrate_db
from models import (
    Vehicle, Driver, Route, Warehouse, Customer, SalesOrder, DeliveryOrder,
    DeliveryOrderDetail, ShipmentCost, VehicleTracking, POD, DeliveryPODRecord, ARInvoice,
    GLTransaction, AuditLog, Quotation, Incident, TaxCode, AccountingPeriod,
    AccountMapping, Carrier, Tender, TenderOffer, FreightOrder, TransportTrip,
    TransportEvent, ResourceAssignment, TripDeliveryOrder, TransportTripLeg,
    FreightActualCost, FreightChargeItem, APInvoice, FreightSettlement,
    CurrencyDefinition, CurrencyRateHistory, Role, User, CostFormula, DeliveryOrderCloseout,
    DeliveryOrderChargeAdjustment, DeliveryPODDocument, VehicleMaintenanceRequest,
    FreightOrderLegacyLink,
)
from gateway.router import GatewayRouter
from agents.query_agent import QueryAgent
from agents.action_agent import ActionAgent
from routes.health_routes import router as health_router
from routes.workflow_routes import router as workflow_router
from routes.tms_planning_routes import router as tms_planning_router
from routes.tms_finance_routes import router as tms_finance_router
from routes.tms_reporting_routes import router as tms_reporting_router
from routes.parking_list_routes import router as parking_list_router
from runtime_state import runtime_state
from auth_middleware import tms_bearer_auth
from schemas.invoice import ARInvoicePostRequest
from schemas.workflow import RouteCreateRequest
from services.ar_invoice_service import post_ar_invoice, serialize_ar_invoice
from services.errors import DomainError, raise_http
from services.vehicle_maintenance_service import (
    create_request as create_vehicle_maintenance_request,
    list_requests as list_vehicle_maintenance_requests,
    serialize_request as serialize_vehicle_maintenance_request,
    transition_request as transition_vehicle_maintenance_request,
)

ai_checkpoint_engine = None
ai_checkpoint_lock = threading.Lock()
currency_reference_lock = threading.Lock()
currency_reference_fetch_lock = threading.Lock()
currency_reference_scheduler_started = False
currency_reference_refresh_hours = max(
    1, int(os.getenv("EXCHANGE_RATE_REFRESH_HOURS", "12") or "12")
)
currency_reference_state = {
    "status": "not_configured",
    "provider": "openexchangerates.org",
    "base": "VND",
    "rates": {},
    "fetched_at": None,
    "provider_timestamp": None,
    "next_refresh_at": None,
    "refresh_interval_hours": currency_reference_refresh_hours,
    "applied": False,
    "error": None,
}
MAX_CHECKPOINT_UPLOAD_BYTES = 10 * 1024 * 1024
CHECKPOINT_READ_CHUNK_BYTES = 1024 * 1024
MAX_MASTER_IMAGE_UPLOAD_BYTES = 2 * 1024 * 1024
MASTER_IMAGE_READ_CHUNK_BYTES = 256 * 1024
MASTER_IMAGE_TARGETS = {"vehicles", "drivers"}
MASTER_IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class AIDependencyUnavailableError(RuntimeError):
    pass


class InvalidCheckpointImageError(ValueError):
    pass

app = FastAPI(
    title="EPL Logistics Enterprise System (Production 100% Real DB)",
    description="Hệ thống Quản lý Logistics EPL với CSDL PostgreSQL thực tế & AI Agents không bịa dữ liệu",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(code, message, fields=None, links=None):
    payload = {
        "code": code,
        "message": message,
        "fields": fields or [],
        "links": links or [],
    }
    return payload


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    fields = [".".join(str(part) for part in error.get("loc", ())) for error in raw_errors]
    legacy_detail = []
    for item in raw_errors:
        cleaned = {key: value for key, value in item.items() if key != "ctx"}
        legacy_detail.append(jsonable_encoder(cleaned))
    error = _error_payload(
        "VALIDATION_ERROR",
        "Dữ liệu gửi lên không hợp lệ.",
        fields=fields,
    )
    return JSONResponse(
        status_code=422,
        content={"error": error, "detail": legacy_detail},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        error = _error_payload(
            detail.get("code") or "HTTP_ERROR",
            detail.get("message") or "Yêu cầu không thể xử lý.",
            fields=detail.get("fields"),
            links=detail.get("links") or detail.get("navigation_targets"),
        )
    else:
        error = _error_payload("HTTP_ERROR", str(detail or "Yêu cầu không thể xử lý."))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error, "detail": detail},
        headers=exc.headers,
    )

app.middleware("http")(tms_bearer_auth)
app.include_router(health_router)
app.include_router(workflow_router)
app.include_router(tms_planning_router)
app.include_router(tms_finance_router)
app.include_router(tms_reporting_router)
app.include_router(parking_list_router)

# Startup performs schema maintenance only.
@app.on_event("startup")
def on_startup():
    correlation_id = __import__("uuid").uuid4().hex
    startup_logger = __import__("logging").getLogger(__name__)
    try:
        auto_migrate_db()
        startup_logger.info("Database auto-migration completed correlation_id=%s", correlation_id)
    except Exception:
        runtime_state.record_migration_failure(correlation_id)
        startup_logger.warning(
            "Database startup failed code=DATABASE_STARTUP_UNAVAILABLE correlation_id=%s",
            correlation_id,
        )
    _start_currency_reference_scheduler()

# ==========================================
# UNIFIED AI GATEWAY (Single Endpoint)
# ==========================================

@app.post("/api/v1/ai/chat")
async def gateway_chat(payload: Dict[str, Any], db: Session = Depends(get_db)):
    prompt = payload.get("prompt", "")
    is_confirmed = payload.get("is_confirmed", False)
    draft_data = payload.get("draft_data", None)
    
    if not prompt and not is_confirmed:
        raise HTTPException(status_code=400, detail="Vui lòng nhập nội dung câu hỏi.")
        
    return GatewayRouter.process_request(prompt, db, is_confirmed, draft_data)

# Direct Agent Endpoints
@app.post("/api/agent/query")
async def query_agent_api(payload: Dict[str, Any], db: Session = Depends(get_db)):
    return QueryAgent.process(payload.get("prompt", ""), db)

@app.post("/api/agent/action")
async def action_agent_api(payload: Dict[str, Any], db: Session = Depends(get_db)):
    return ActionAgent.process(payload.get("prompt", ""), db)

def _process_checkpoint(contents: bytes):
    global ai_checkpoint_engine
    if not contents:
        raise InvalidCheckpointImageError from None

    try:
        import cv2
        import numpy as np
    except Exception:
        raise AIDependencyUnavailableError from None

    # The engine and its native CV dependencies are shared and not assumed thread-safe.
    with ai_checkpoint_lock:
        if ai_checkpoint_engine is None:
            try:
                from cv_engine import AICheckpointEngine
                ai_checkpoint_engine = AICheckpointEngine()
            except Exception:
                raise AIDependencyUnavailableError from None

        nparr = np.frombuffer(contents, np.uint8)
        try:
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except cv2.error:
            raise InvalidCheckpointImageError from None
        if frame is None:
            raise InvalidCheckpointImageError from None

        results = ai_checkpoint_engine.process_frame(frame)
        if results.get("cropped_plate_img") is not None:
            _, buffer = cv2.imencode('.jpg', results["cropped_plate_img"])
            results["cropped_plate_img"] = (
                f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
            )
        return results


async def _read_checkpoint_upload(file: UploadFile) -> bytes:
    contents = bytearray()
    while True:
        chunk = await file.read(CHECKPOINT_READ_CHUNK_BYTES)
        if not chunk:
            return bytes(contents)
        contents.extend(chunk)
        if len(contents) > MAX_CHECKPOINT_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "UPLOAD_TOO_LARGE",
                    "message": "Tệp ảnh vượt quá dung lượng cho phép.",
                },
            )


def _upload_root() -> Path:
    configured = os.environ.get("EPL_UPLOAD_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(app_dir).resolve().parent / "uploads").resolve()


async def _read_master_image_upload(file: UploadFile) -> bytes:
    contents = bytearray()
    while True:
        chunk = await file.read(MASTER_IMAGE_READ_CHUNK_BYTES)
        if not chunk:
            return bytes(contents)
        contents.extend(chunk)
        if len(contents) > MAX_MASTER_IMAGE_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "UPLOAD_TOO_LARGE",
                    "message": "Ảnh tải lên tối đa 2MB. Vui lòng chọn ảnh nhẹ hơn.",
                },
            )


def _detect_image_extension(contents: bytes) -> str:
    if contents.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(contents) >= 12 and contents.startswith(b"RIFF") and contents[8:12] == b"WEBP":
        return ".webp"
    raise HTTPException(
        status_code=400,
        detail={
            "code": "INVALID_IMAGE_UPLOAD",
            "message": "Tệp tải lên không phải ảnh JPG, PNG hoặc WEBP hợp lệ.",
        },
    )


def _validate_upload_target(entity_type: str) -> str:
    target = (entity_type or "").strip().lower()
    if target not in MASTER_IMAGE_TARGETS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_UPLOAD_TARGET",
                "message": "Loại hồ sơ tải ảnh không hợp lệ. Chỉ hỗ trợ xe hoặc tài xế.",
                "navigation_target": "master-data",
            },
        )
    return target


def _stored_upload_file(target: str, filename: str) -> Path:
    if not filename or "/" in filename or "\\" in filename or "\x00" in filename:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tải lên.")
    root = _upload_root()
    target_dir = (root / target).resolve()
    full_path = (target_dir / filename).resolve()
    try:
        full_path.relative_to(target_dir)
    except ValueError:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tải lên.") from None
    return full_path


@app.post("/api/uploads/images", status_code=201)
async def upload_master_data_image(entity_type: str = Form(...), file: UploadFile = File(...)):
    target = _validate_upload_target(entity_type)
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_IMAGE_UPLOAD",
                "message": "Vui lòng chọn đúng tệp ảnh.",
            },
        )
    contents = await _read_master_image_upload(file)
    extension = _detect_image_extension(contents)
    target_dir = (_upload_root() / target).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    final_path = _stored_upload_file(target, filename)
    temp_path = target_dir / f".{filename}.tmp"
    try:
        with open(temp_path, "wb") as handle:
            handle.write(contents)
        os.replace(temp_path, final_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    url = f"/uploads/{target}/{filename}"
    return {
        "message": "Tải ảnh lên thành công.",
        "data": {
            "url": url,
            "filename": filename,
            "entity_type": target,
            "content_type": MASTER_IMAGE_MEDIA_TYPES[extension],
            "size": len(contents),
        },
    }


@app.get("/uploads/{asset_path:path}")
async def get_uploaded_asset(asset_path: str):
    parts = PurePosixPath(asset_path).parts
    if len(parts) != 2:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tải lên.")
    target = _validate_upload_target(parts[0])
    file_path = _stored_upload_file(target, parts[1])
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tải lên.")
    media_type = MASTER_IMAGE_MEDIA_TYPES.get(file_path.suffix.lower())
    if not media_type:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp tải lên.")
    return FileResponse(file_path, media_type=media_type)


@app.post("/api/ai/checkpoint/scan")
async def scan_checkpoint(file: UploadFile = File(...)):
    contents = await _read_checkpoint_upload(file)
    try:
        return await run_in_threadpool(_process_checkpoint, contents)
    except AIDependencyUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_DEPENDENCY_UNAVAILABLE",
                "message": "Dịch vụ AI tạm thời không khả dụng. Vui lòng thử lại sau.",
            },
        ) from None
    except InvalidCheckpointImageError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_IMAGE",
                "message": "Tệp tải lên không phải là ảnh hợp lệ.",
            },
        ) from None

# ==========================================
# REST API ENDPOINTS FOR 100% REAL DB CRUD
# Phase 1: Master Data
# ==========================================

# 1. Vehicles API
@app.get("/api/vehicles")
async def list_vehicles(
    paginated: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Vehicle).order_by(Vehicle.id.desc())
    total = query.count()
    vehicles = (
        query.offset((page - 1) * page_size).limit(page_size).all()
        if paginated
        else query.limit(100).all()
    )
    now = datetime.now(timezone.utc)
    result = []
    for vehicle in vehicles:
        payload = jsonable_encoder(vehicle)
        active_assignment = db.query(ResourceAssignment.id).filter(
            ResourceAssignment.vehicle_id == vehicle.id,
            ResourceAssignment.status == "active",
            ResourceAssignment.assignment_start <= now,
            ResourceAssignment.assignment_end > now,
        ).first()
        active_maintenance = db.query(VehicleMaintenanceRequest.id).filter(
            VehicleMaintenanceRequest.vehicle_id == vehicle.id,
            VehicleMaintenanceRequest.status.in_(("approved", "in_progress")),
            VehicleMaintenanceRequest.planned_start <= now,
            VehicleMaintenanceRequest.planned_end > now,
        ).first()
        if active_maintenance:
            payload["operational_status"] = "maintenance"
            payload["operational_status_label"] = "Đang sửa chữa / bảo dưỡng"
        elif active_assignment:
            payload["operational_status"] = "busy"
            payload["operational_status_label"] = "Đang thực hiện chuyến"
        else:
            payload["operational_status"] = "ready"
            payload["operational_status_label"] = "Sẵn sàng"
        result.append(payload)
    if paginated:
        return {"items": result, "page": page, "page_size": page_size, "total": total}
    return result

@app.post("/api/vehicles")
async def create_vehicle(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    _require_api_principal(request)
    vid = data.get("id")
    if not vid:
        raise HTTPException(status_code=400, detail="Thiếu Biển số xe")
    existing = db.get(Vehicle, vid)
    veh = Vehicle(
        id=vid,
        brand=data.get("brand", "Hyundai"),
        type=data.get("type", "Truck"),
        weight_capacity=float(data.get("weight_capacity") or 0),
        volume_capacity_m3=float(data.get("volume_capacity_m3") or data.get("volumeCapacityM3") or 30.0),
        pallet_capacity=int(data.get("pallet_capacity") or data.get("palletCapacity") or 0),
        fuel_norm=float(data.get("fuel_norm") or 0),
        avg_speed_kmh=float(data.get("avg_speed_kmh") or data.get("avgSpeedKmh") or 45.0),
        min_speed_kmh=float(data.get("min_speed_kmh") or data.get("min_speed") or 0),
        max_speed_kmh=float(data.get("max_speed_kmh") or data.get("max_speed") or 0),
        maintenance_date=data.get("maintenance_date", ""),
        status=existing.status if existing else "Sẵn sàng",
        engine_no=data.get("engine_no", ""),
        chassis_no=data.get("chassis_no", ""),
        insurance_date=data.get("insurance_date", ""),
        inspection_date=data.get("inspection_date", ""),
        inspection_place=data.get("inspection_place", ""),
        inspection_exp=data.get("inspection_exp", ""),
        engine_cap=data.get("engine_cap", ""),
        dimensions=data.get("dimensions", ""),
        image_url=data.get("image_url", "")
    )
    db.merge(veh)
    db.commit()
    return {"message": "Cập nhật dữ liệu xe thành công", "data": veh}


@app.get("/api/vehicles/{vehicle_id}/maintenance-requests")
async def get_vehicle_maintenance_requests(vehicle_id: str, db: Session = Depends(get_db)):
    try:
        items = list_vehicle_maintenance_requests(db, vehicle_id)
        return {"data": [serialize_vehicle_maintenance_request(item) for item in items]}
    except DomainError as error:
        raise_http(error)


@app.post("/api/vehicles/{vehicle_id}/maintenance-requests", status_code=201)
async def post_vehicle_maintenance_request(
    vehicle_id: str,
    request: Request,
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    _require_api_principal(request)
    try:
        actor = _require_api_principal(request)
        item = create_vehicle_maintenance_request(db, vehicle_id, data, str(actor))
        return {"data": serialize_vehicle_maintenance_request(item)}
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "code": "MAINTENANCE_REQUEST_DUPLICATE",
            "message": "Số phiếu sửa chữa đã tồn tại.",
        })


async def _run_vehicle_maintenance_transition(request_id, action, request, data, db):
    actor = _require_api_principal(request)
    if not request.headers.get("Idempotency-Key"):
        raise HTTPException(status_code=422, detail={
            "code": "IDEMPOTENCY_KEY_REQUIRED",
            "message": "Cần Idempotency-Key cho thao tác chuyển trạng thái.",
        })
    try:
        item = transition_vehicle_maintenance_request(db, request_id, action, data, str(actor))
        return {"data": serialize_vehicle_maintenance_request(item)}
    except DomainError as error:
        db.rollback()
        raise_http(error)


@app.post("/api/vehicle-maintenance-requests/{request_id}/approve")
async def approve_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "approve", request, data, db)


@app.post("/api/vehicle-maintenance-requests/{request_id}/start")
async def start_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "start", request, data, db)


@app.post("/api/vehicle-maintenance-requests/{request_id}/complete")
async def complete_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "complete", request, data, db)


@app.post("/api/vehicle-maintenance-requests/{request_id}/cancel")
async def cancel_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "cancel", request, data, db)

@app.delete("/api/vehicles/{vid}")
async def delete_vehicle(vid: str, request: Request, db: Session = Depends(get_db)):
    _require_api_principal(request)
    veh = db.query(Vehicle).filter(Vehicle.id == vid).first()
    if veh:
        in_use = any([
            db.query(DeliveryOrder.id).filter(DeliveryOrder.vehicle_id == vid).first(),
            db.query(VehicleTracking.do_id).filter(VehicleTracking.vehicle_id == vid).first(),
            db.query(DeliveryPODRecord.id).filter(DeliveryPODRecord.vehicle_id == vid).first(),
            db.query(TransportTrip.id).filter(TransportTrip.vehicle_id == vid).first(),
            db.query(ResourceAssignment.id).filter(ResourceAssignment.vehicle_id == vid).first(),
        ])
        if in_use:
            raise HTTPException(status_code=409, detail={
                "code": "LOCKED_RECORD",
                "message": "Xe đang được dùng bởi DO/Trip/Tracking, không được xóa khỏi Master Data.",
                "navigation_targets": ["dispatch", "tracking", "master-data/vehicles"],
            })
        db.delete(veh)
        db.commit()
        return {"message": f"Đã xóa phương tiện {vid}"}
    return {"message": "Đã xóa phương tiện"}

# 1.5 Vehicle Types API
@app.get("/api/vehicle-types")
async def list_vehicle_types(db: Session = Depends(get_db)):
    from models import VehicleType
    return db.query(VehicleType).all()

@app.get("/api/vehicle-types/recommendations")
async def get_vehicle_type_recommendations(
    weight_kg: float = 0,
    volume_m3: float = 0,
    pallet_count: int = 0,
    db: Session = Depends(get_db),
):
    from services.vehicle_recommendation_service import recommend_vehicle_types
    return {"data": recommend_vehicle_types(db, {
        "weight_kg": weight_kg,
        "volume_m3": volume_m3,
        "pallet_count": pallet_count,
    })}

@app.post("/api/vehicle-types")
async def save_vehicle_type(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    _require_api_principal(request)
    from models import VehicleType
    vid = data.get("id")
    if not vid:
        raise HTTPException(status_code=400, detail="Thiếu Mã Loại Phương Tiện")
    
    vt = VehicleType(
        id=vid,
        name=data.get("name", "Loại Xe Mới"),
        icon=data.get("icon", "🚛"),
        max_weight=float(data.get("maxWeight") or data.get("max_weight") or 0.0),
        volume_capacity_m3=float(data.get("volumeCapacityM3") or data.get("volume_capacity_m3") or 0.0),
        pallet_capacity=int(data.get("palletCapacity") or data.get("pallet_capacity") or 0),
        fuel_norm=float(data.get("fuelNorm") or data.get("fuel_norm") or 0.0),
        base_rate=float(data.get("baseRate") or data.get("base_rate") or 0.0),
        maint_cost=float(data.get("maintCost") or data.get("maint_cost") or 0.0),
        dims=data.get("dims", ""),
        fuel_type=data.get("fuelType") or data.get("fuel_type") or "Diesel",
        special=data.get("special", ""),
        notes=data.get("notes", "")
    )
    db.merge(vt)
    db.commit()
    return {"message": "Lưu loại phương tiện thành công", "data": vt}

@app.delete("/api/vehicle-types/{vid}")
async def delete_vehicle_type(vid: str, request: Request, db: Session = Depends(get_db)):
    _require_api_principal(request)
    from models import VehicleType
    vt = db.query(VehicleType).filter(VehicleType.id == vid).first()
    if vt:
        db.delete(vt)
        db.commit()
        return {"message": f"Đã xóa {vid}"}
    return {"message": "Không tìm thấy loại phương tiện"}

# 1.6 Cost Formula API
def _serialize_cost_formula(row: CostFormula):
    try:
        payload = json.loads(row.formula_expression or "{}")
    except json.JSONDecodeError:
        payload = {}
    components = payload.get("components") if isinstance(payload.get("components"), dict) else {}
    return {
        "id": row.id,
        "name": row.name,
        "configured": True,
        "vehicle_type_id": payload.get("vehicle_type_id") or None,
        "currency": payload.get("currency") or "VND",
        "components": components,
        "tokens": payload.get("tokens") if isinstance(payload.get("tokens"), list) else [],
        "formula_expression": row.formula_expression,
    }


@app.get("/api/cost-formulas")
async def list_cost_formulas(db: Session = Depends(get_db)):
    return [
        _serialize_cost_formula(row)
        for row in db.query(CostFormula).order_by(CostFormula.id).all()
    ]


@app.post("/api/cost-formulas")
async def save_cost_formula(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    _require_api_principal(request)
    requested_formula_id = str(data.get("id") or "").strip()
    vehicle_type_id = str(data.get("vehicle_type_id") or "").strip()
    if not requested_formula_id and not vehicle_type_id:
        raise HTTPException(status_code=422, detail="Thiếu mã công thức giá.")
    currency = str(data.get("currency") or "VND").strip().upper()
    if currency not in {"VND", "USD", "THB", "LAK"}:
        raise HTTPException(status_code=422, detail="Tiền tệ công thức giá không hợp lệ.")
    formula_id = f"vehicle-type::{vehicle_type_id}::{currency}" if vehicle_type_id else requested_formula_id
    payload = {
        "vehicle_type_id": vehicle_type_id or None,
        "currency": currency,
        "components": {
            "fuel": data.get("fuel") or "0",
            "driver": data.get("driver") or "0",
            "toll": data.get("toll") or "0",
            "warehouse": data.get("warehouse") or data.get("wh") or "0",
            "freight_rate": data.get("freight_rate") or data.get("rate") or "0",
        },
        "tokens": data.get("tokens") if isinstance(data.get("tokens"), list) else [],
    }
    row = CostFormula(
        id=formula_id,
        name=str(data.get("name") or formula_id).strip(),
        formula_expression=json.dumps(payload, ensure_ascii=False),
    )
    db.merge(row)
    db.commit()
    saved = db.get(CostFormula, formula_id)
    return {"message": "Đã lưu công thức giá thành vào CSDL.", "data": _serialize_cost_formula(saved)}

# 2. Drivers API
@app.get("/api/drivers")
async def list_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()

@app.post("/api/drivers")
async def create_driver(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    _require_api_principal(request)
    did = data.get("id") or data.get("name")
    if not did:
        raise HTTPException(status_code=400, detail="Thiếu Mã hoặc Họ Tên tài xế")
    drv = db.get(Driver, did)
    if drv is None:
        drv = Driver(id=did, status="🟢 Rảnh (Sẵn sàng)")
        db.add(drv)

    raw_status = str(drv.status or "").lower()
    is_operationally_busy = any(
        marker in raw_status
        for marker in ("bận", "theo xe", "đang thực hiện", "đang vận chuyển")
    )
    drv.name = data.get("name", did)
    drv.role = data.get("role", "Lái xe chính")
    drv.license_type = data.get("license_type", "Hạng FC")
    drv.phone = data.get("phone", "")
    if not is_operationally_busy:
        drv.assigned_vehicle = data.get("assigned_vehicle", "Chưa gán")
    drv.shift = data.get("shift", "Ca Sáng (06:00 - 14:00)")
    drv.photo_url = data.get("photo_url") or data.get("image_url") or ""
    db.commit()
    db.refresh(drv)
    return {"message": f"Đã lưu nhân sự {did}", "data": drv}

@app.delete("/api/drivers/{did}")
async def delete_driver(did: str, request: Request, db: Session = Depends(get_db)):
    _require_api_principal(request)
    drv = db.query(Driver).filter(Driver.id == did).first()
    if not drv:
        # Try matching by name
        drv = db.query(Driver).filter(Driver.name == did).first()
    if drv:
        db.delete(drv)
        db.commit()
        return {"message": f"Đã xóa nhân sự {did}"}
    return {"message": "Đã xóa nhân sự"}

# 2.5 Currencies API
def _currency_reference_snapshot():
    with currency_reference_lock:
        snapshot = dict(currency_reference_state)
        snapshot["rates"] = dict(currency_reference_state.get("rates") or {})
    if not os.getenv("OPEN_EXCHANGE_RATES_APP_ID", "").strip() and not snapshot["rates"]:
        snapshot["status"] = "not_configured"
    return snapshot


def _request_open_exchange_rates(app_id: str):
    query = urllib.parse.urlencode({
        "app_id": app_id,
        "symbols": "USD,VND,THB,LAK",
    })
    request = urllib.request.Request(
        f"https://openexchangerates.org/api/latest.json?{query}",
        headers={"Accept": "application/json", "User-Agent": "EPL-Logistics/1.0"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_currency_reference_rates():
    app_id = os.getenv("OPEN_EXCHANGE_RATES_APP_ID", "").strip()
    if not app_id:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "EXCHANGE_RATE_PROVIDER_NOT_CONFIGURED",
                "message": "Chưa cấu hình OPEN_EXCHANGE_RATES_APP_ID; tỷ giá đang giữ theo cấu hình thủ công.",
            },
        )

    try:
        payload = _request_open_exchange_rates(app_id)
        source_rates = payload.get("rates") or {}
        usd_to_vnd = float(source_rates["VND"])
        usd_to_thb = float(source_rates["THB"])
        usd_to_lak = float(source_rates["LAK"])
        if min(usd_to_vnd, usd_to_thb, usd_to_lak) <= 0:
            raise ValueError("Provider returned a non-positive exchange rate")
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        with currency_reference_lock:
            currency_reference_state["status"] = "error"
            currency_reference_state["error"] = "Provider response is missing USD/VND/THB/LAK rates."
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EXCHANGE_RATE_PROVIDER_INVALID_RESPONSE",
                "message": "Nhà cung cấp trả dữ liệu tỷ giá không đầy đủ hoặc không hợp lệ.",
            },
        ) from exc
    except Exception as exc:
        with currency_reference_lock:
            currency_reference_state["status"] = "error"
            currency_reference_state["error"] = str(exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": "EXCHANGE_RATE_PROVIDER_UNAVAILABLE",
                "message": "Không thể cập nhật tỷ giá tham chiếu; tỷ giá vận hành hiện tại không thay đổi.",
            },
        ) from exc

    now = datetime.now(timezone.utc)
    provider_timestamp = payload.get("timestamp")
    provider_time = None
    if provider_timestamp:
        try:
            provider_time = datetime.fromtimestamp(float(provider_timestamp), timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            provider_time = None
    rates = {
        "USD": usd_to_vnd,
        "THB": usd_to_vnd / usd_to_thb,
        "LAK": usd_to_vnd / usd_to_lak,
    }
    with currency_reference_lock:
        currency_reference_state.update({
            "status": "ready",
            "rates": rates,
            "fetched_at": now.isoformat(),
            "provider_timestamp": provider_time,
            "next_refresh_at": (now + timedelta(hours=currency_reference_refresh_hours)).isoformat(),
            "refresh_interval_hours": currency_reference_refresh_hours,
            "applied": False,
            "error": None,
        })
    return _currency_reference_snapshot()


def _refresh_currency_reference_rates():
    with currency_reference_fetch_lock:
        cached = _currency_reference_snapshot()
        next_refresh_at = cached.get("next_refresh_at")
        if cached.get("status") == "ready" and next_refresh_at:
            try:
                if datetime.fromisoformat(next_refresh_at) > datetime.now(timezone.utc):
                    return cached
            except (TypeError, ValueError):
                pass
        return _fetch_currency_reference_rates()


def _start_currency_reference_scheduler():
    global currency_reference_scheduler_started
    if currency_reference_scheduler_started or not os.getenv("OPEN_EXCHANGE_RATES_APP_ID", "").strip():
        return
    currency_reference_scheduler_started = True

    def refresh_loop():
        wait_seconds = currency_reference_refresh_hours * 60 * 60
        while True:
            try:
                _refresh_currency_reference_rates()
                delay = wait_seconds
            except Exception:
                delay = min(wait_seconds, 60 * 60)
            threading.Event().wait(delay)

    threading.Thread(
        target=refresh_loop,
        name="currency-reference-refresh",
        daemon=True,
    ).start()


@app.get("/api/currencies/reference-rates")
async def get_currency_reference_rates():
    return _currency_reference_snapshot()


@app.post("/api/currencies/reference-rates/refresh")
async def refresh_currency_reference_rates():
    return await run_in_threadpool(_refresh_currency_reference_rates)


@app.get("/api/currencies")
async def list_currencies(db: Session = Depends(get_db)):
    from models import Currency
    return db.query(Currency).all()


def _serialize_currency_history(db: Session):
    from models import Currency

    output = []
    for code in ("USD", "THB", "LAK"):
        current = db.get(Currency, code)
        rows = db.query(CurrencyRateHistory).filter(
            CurrencyRateHistory.currency_code == code,
            CurrencyRateHistory.functional_currency == "VND",
            CurrencyRateHistory.is_active.is_(True),
        ).order_by(
            CurrencyRateHistory.rate_date.desc(),
            CurrencyRateHistory.id.desc(),
        ).limit(30).all()
        current_rate = float(current.exchange_rate) if current else None
        approved = next((row for row in rows if row.source == "APPROVED_UI" and float(row.rate) == current_rate), None)
        previous = next((row for row in rows if current_rate is not None and float(row.rate) != current_rate), None)
        history = []
        if current_rate is not None:
            history.append({
                "rate": current_rate,
                "rate_date": (approved.rate_date if approved else datetime.now().date()).isoformat(),
                "source": approved.source if approved else "LEGACY_CURRENT",
                "created_at": approved.created_at.isoformat() if approved and approved.created_at else None,
            })
        for row in rows:
            if approved and row.id == approved.id:
                continue
            history.append({
                "rate": float(row.rate),
                "rate_date": row.rate_date.isoformat(),
                "source": row.source,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })
        previous_rate = float(previous.rate) if previous else None
        change = current_rate - previous_rate if current_rate is not None and previous_rate is not None else None
        change_percent = change / previous_rate * 100 if change is not None and previous_rate else None
        output.append({
            "code": code,
            "current_rate": current_rate,
            "previous_rate": previous_rate,
            "change": change,
            "change_percent": change_percent,
            "source": approved.source if approved else ("LEGACY_CURRENT" if current else None),
            "applied_at": approved.created_at.isoformat() if approved and approved.created_at else None,
            "history": history,
        })
    return {"functional_currency": "VND", "currencies": output}


@app.get("/api/currencies/history")
async def list_currency_history(db: Session = Depends(get_db)):
    return _serialize_currency_history(db)


@app.post("/api/currencies")
async def save_currency_rates(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    from models import Currency
    required_codes = ("USD", "THB", "LAK")
    parsed_rates = {}
    invalid_codes = []
    for code in required_codes:
        try:
            rate = Decimal(str(data.get(code)))
            if not rate.is_finite() or rate <= 0:
                raise ValueError
            parsed_rates[code] = rate
        except (InvalidOperation, TypeError, ValueError):
            invalid_codes.append(code)
    if invalid_codes or set(data) - set(required_codes):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_EXCHANGE_RATE",
                "message": "Tỷ giá USD, THB và LAK phải là số hợp lệ lớn hơn 0.",
                "fields": invalid_codes or sorted(set(data) - set(required_codes)),
            },
        )

    today = datetime.now().date()
    minor_units = {"VND": 0, "USD": 2, "THB": 2, "LAK": 2}
    for code, units in minor_units.items():
        definition = db.get(CurrencyDefinition, code)
        if not definition:
            db.add(CurrencyDefinition(code=code, minor_units=units, is_active=True))
    db.flush()

    for code, rate in parsed_rates.items():
        current = db.get(Currency, code)
        old_rate = Decimal(str(current.exchange_rate)) if current else None
        approved = db.query(CurrencyRateHistory).filter(
            CurrencyRateHistory.currency_code == code,
            CurrencyRateHistory.functional_currency == "VND",
            CurrencyRateHistory.rate_date == today,
            CurrencyRateHistory.source == "APPROVED_UI",
        ).first()
        previous = db.query(CurrencyRateHistory).filter(
            CurrencyRateHistory.currency_code == code,
            CurrencyRateHistory.functional_currency == "VND",
            CurrencyRateHistory.rate_date == today,
            CurrencyRateHistory.source == "PREVIOUS_UI",
        ).first()
        if old_rate is not None and old_rate != rate:
            if previous:
                previous.rate = old_rate
            else:
                db.add(CurrencyRateHistory(
                    currency_code=code,
                    functional_currency="VND",
                    rate_date=today,
                    rate=old_rate,
                    source="PREVIOUS_UI",
                    is_active=True,
                ))
        if approved:
            approved.rate = rate
            approved.is_active = True
        else:
            db.add(CurrencyRateHistory(
                currency_code=code,
                functional_currency="VND",
                rate_date=today,
                rate=rate,
                source="APPROVED_UI",
                is_active=True,
            ))
        db.merge(Currency(id=code, exchange_rate=float(rate)))
    db.commit()
    return {"message": "Đã cập nhật tỷ giá tiền tệ vào CSDL", "data": _serialize_currency_history(db)}

# 3. Customers API
@app.get("/api/customers")
async def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()

@app.post("/api/customers")
async def create_customer(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    cid = data.get("id")
    if not cid:
        raise HTTPException(status_code=400, detail="Thiếu Mã khách hàng")
    cus = Customer(
        id=cid,
        name=data.get("name", "Khách hàng Mới"),
        type=data.get("type", "Account"),
        contact_person=data.get("contact_person", ""),
        phone=data.get("phone", ""),
        address=data.get("address", "")
    )
    db.add(cus)
    db.commit()
    db.refresh(cus)
    return {"message": "Tạo khách hàng thành công", "data": cus}

@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    cus = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cus:
        raise HTTPException(status_code=404, detail="Không tìm thấy Khách hàng")
    if "name" in data: cus.name = data["name"]
    if "type" in data: cus.type = data["type"]
    if "contact_person" in data: cus.contact_person = data["contact_person"]
    if "phone" in data: cus.phone = data["phone"]
    if "address" in data: cus.address = data["address"]
    db.commit()
    db.refresh(cus)
    return {"message": "Cập nhật khách hàng thành công", "data": cus}

@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: str, db: Session = Depends(get_db)):
    cus = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cus:
        raise HTTPException(status_code=404, detail="Không tìm thấy Khách hàng")
    db.delete(cus)
    db.commit()
    return {"message": f"Đã xóa khách hàng {customer_id}"}

# 5. Routes API
@app.get("/api/routes")
async def list_routes(
    paginated: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Route).order_by(Route.id.asc())
    if not paginated:
        return query.limit(100).all()
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@app.post("/api/routes")
async def create_route(payload: RouteCreateRequest, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    route_id = data.get("id")
    if not route_id:
        count = db.query(Route).count() + 1
        route_id = f"RT-{count:03d}"
    existing = db.query(Route).filter(Route.id == route_id).first()
    if existing:
        existing.name = data.get("name", existing.name or "Tuyến mới")
        existing.distance_km = float(data.get("distance_km") or 0)
        existing.segments_json = data.get("segments_json", existing.segments_json or "[]")
        route = existing
    else:
        route = Route(
            id=route_id,
            name=data.get("name", "Tuyến mới"),
            distance_km=float(data.get("distance_km") or 0),
            segments_json=data.get("segments_json", "[]")
        )
        db.add(route)
    db.commit()
    db.refresh(route)
    return {"message": f"Đã lưu tuyến đường {route_id} thành công", "data": route}

@app.delete("/api/routes/{route_id}")
async def delete_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tuyến đường {route_id}")
    db.delete(route)
    db.commit()
    return {"message": f"Đã xóa tuyến đường {route_id} thành công"}

# 7. Tracking API
@app.get("/api/tracking/{do_id}")
async def get_tracking(do_id: str, db: Session = Depends(get_db)):
    track = db.query(VehicleTracking).filter(VehicleTracking.do_id == do_id).first()
    if not track:
        raise HTTPException(status_code=404, detail={
            "code": "TRACKING_NOT_FOUND",
            "message": f"Chưa có dữ liệu GPS cho lệnh giao hàng {do_id}. Vui lòng điều phối xe hoặc cập nhật thiết bị GPS trước.",
            "navigation_targets": ["dispatch", "master-data/vehicles"],
        })
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).first()
    route = db.query(Route).filter(Route.id == do.route_id).first() if do and do.route_id else None
    customer = db.query(Customer).filter(Customer.id == do.customer_id).first() if do and do.customer_id else None
    driver = db.query(Driver).filter(Driver.id == do.driver_id).first() if do and do.driver_id else None

    route_segments = []
    if route and route.segments_json:
        try:
            route_segments = json.loads(route.segments_json)
        except Exception:
            route_segments = []

    return {
        "do_id": track.do_id,
        "vehicle_id": track.vehicle_id,
        "lat": track.lat,
        "lng": track.lng,
        "speed_kmh": track.speed_kmh,
        "remaining_distance_km": track.remaining_distance_km,
        "eta": track.eta,
        "planned_return_at": track.planned_return_at,
        "last_update": track.last_update,
        "status": do.status if do else "",
        "route_id": route.id if route else "",
        "route_name": route.name if route else "",
        "route_distance_km": route.distance_km if route else 0,
        "route_segments": route_segments,
        "customer_id": customer.id if customer else "",
        "customer_name": customer.name if customer else "",
        "driver_id": driver.id if driver else "",
        "driver_name": driver.name if driver else "",
    }


def _decimal_to_float(value):
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _iso_or_none(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _require_api_principal(request: Request):
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        value = principal.get("id") or principal.get("sub") or principal.get("username")
        if value:
            return str(value)
    raise_http(DomainError("AUTHENTICATION_REQUIRED", "Vui lòng đăng nhập.", 401))


def _select_closeout_formula(db: Session, delivery_order: DeliveryOrder, currency_code: Optional[str] = None):
    required_currency = str(currency_code or "").strip().upper()
    if delivery_order and delivery_order.vehicle_id:
        vehicle = db.get(Vehicle, delivery_order.vehicle_id)
        if vehicle and vehicle.type:
            from models import VehicleType

            candidates = db.query(CostFormula).order_by(CostFormula.id).all()
            vehicle_type = db.get(VehicleType, vehicle.type)
            if vehicle_type is None:
                vehicle_type = (
                    db.query(VehicleType)
                    .filter(func.lower(VehicleType.name) == str(vehicle.type).lower())
                    .first()
                )
            if vehicle_type is not None:
                for candidate in candidates:
                    formula = _serialize_cost_formula(candidate)
                    currency_matches = not required_currency or formula.get("currency") == required_currency
                    if formula.get("vehicle_type_id") == vehicle_type.id and currency_matches:
                        return candidate

            normalized_type = str(vehicle.type).lower().replace(" ", "")
            for candidate in candidates:
                formula = _serialize_cost_formula(candidate)
                if required_currency and formula.get("currency") != required_currency:
                    continue
                text = f"{candidate.id} {candidate.name}".lower().replace(" ", "")
                if normalized_type in text or "20ft" in normalized_type and "20ft" in text:
                    return candidate
    if required_currency:
        return None
    return (
        db.get(CostFormula, "DEMO-COST-FORMULA-20FT")
        or db.get(CostFormula, "preset-1")
        or db.query(CostFormula).order_by(CostFormula.id).first()
    )


def _serialize_closeout_formula(row: Optional[CostFormula]):
    if row is None:
        return {"id": "", "name": "", "currency": "VND", "components": {}, "tokens": []}
    return _serialize_cost_formula(row)


def _configured_delivery_cost_lines(formula, delivery_order, route):
    components = formula.get("components") if isinstance(formula, dict) else {}
    if not isinstance(components, dict):
        return []

    def amount(code):
        raw = str(components.get(code) or "0").replace(",", "").strip()
        try:
            return Decimal(raw)
        except (ValueError, ArithmeticError):
            return Decimal("0")

    def display(value):
        return f"{float(value):,.0f}".replace(",", ".")

    def display_quantity(value):
        number = float(value)
        if number.is_integer():
            return display(value)
        return f"{number:,.2f}".rstrip("0").rstrip(".").replace(",", ".")

    distance = Decimal(str(getattr(route, "distance_km", 0) or 0))
    weight = Decimal(str(getattr(delivery_order, "weight_kg", 0) or 0))
    currency = str(formula.get("currency") or "VND")
    definitions = [
        ("fuel", "Chi phí xăng dầu", amount("fuel") * distance,
         f"{display_quantity(distance)} km × {display(amount('fuel'))} {currency}"),
        ("driver", "Phụ cấp chuyến tài xế", amount("driver"), "Theo chuyến"),
        ("toll", "Phí cầu đường / BOT", amount("toll"), "Theo chuyến"),
        ("warehouse", "Phí bãi và lưu kho", amount("warehouse"), "Theo chuyến"),
        ("freight_rate", "Cước vận chuyển theo tải trọng", amount("freight_rate") * weight,
         f"{display(weight)} kg × {display(amount('freight_rate'))} {currency}"),
    ]
    return [
        {
            "code": code,
            "name": name,
            "original_amount": float(original.quantize(Decimal("0.000001"))),
            "calculation": calculation,
        }
        for code, name, original, calculation in definitions
        if amount(code) > 0
    ]


@app.get("/api/delivery-orders/{do_id}/closeout")
async def get_delivery_order_closeout(do_id: str, request: Request, db: Session = Depends(get_db)):
    _require_api_principal(request)
    delivery_order = db.get(DeliveryOrder, do_id)
    if delivery_order is None:
        raise HTTPException(status_code=404, detail={
            "code": "DELIVERY_ORDER_NOT_FOUND",
            "message": f"Khong tim thay lenh giao hang {do_id}.",
            "navigation_targets": ["delivery-orders", "tracking"],
        })

    sales_order = db.get(SalesOrder, delivery_order.so_id) if delivery_order.so_id else None
    quotation = db.get(Quotation, sales_order.quotation_id) if sales_order and sales_order.quotation_id else None
    route = db.get(Route, delivery_order.route_id) if delivery_order.route_id else None
    formula_row = _select_closeout_formula(
        db, delivery_order, sales_order.currency_code if sales_order else None
    )
    if sales_order and delivery_order.vehicle_id and formula_row is None:
        raise HTTPException(status_code=409, detail={
            "code": "COST_FORMULA_REQUIRED",
            "message": f"Chưa cấu hình giá thành {sales_order.currency_code} cho loại xe của {delivery_order.vehicle_id}.",
            "vehicle_id": delivery_order.vehicle_id,
            "currency": sales_order.currency_code,
        })
    formula = _serialize_closeout_formula(formula_row)
    configured_cost_lines = _configured_delivery_cost_lines(formula, delivery_order, route)

    trip_link = (
        db.query(TripDeliveryOrder)
        .filter(TripDeliveryOrder.do_id == do_id)
        .order_by(TripDeliveryOrder.allocation_sequence.asc(), TripDeliveryOrder.created_at.desc())
        .first()
    )
    trip = db.get(TransportTrip, trip_link.trip_id) if trip_link else None
    assignment = None
    assigned_vehicle = None
    assigned_driver = None
    if trip:
        assignment = (
            db.query(ResourceAssignment)
            .filter(ResourceAssignment.trip_id == trip.id)
            .order_by(ResourceAssignment.id.desc())
            .first()
        )
        assigned_vehicle = db.get(Vehicle, trip.vehicle_id) if trip.vehicle_id else None
        assigned_driver = db.get(Driver, trip.driver_id) if trip.driver_id else None
    legs = []
    if trip:
        legs = (
            db.query(TransportTripLeg)
            .filter(TransportTripLeg.trip_id == trip.id, TransportTripLeg.do_id == do_id)
            .order_by(TransportTripLeg.sequence_no.asc())
            .all()
        )
    actual_cost = None
    if trip:
        actual_cost = (
            db.query(FreightActualCost)
            .filter(FreightActualCost.trip_id == trip.id, FreightActualCost.is_active.is_(True))
            .order_by(FreightActualCost.updated_at.desc())
            .first()
        )
    if actual_cost is None and delivery_order.id:
        freight_order_id = trip.freight_order_id if trip else None
        if freight_order_id:
            actual_cost = (
                db.query(FreightActualCost)
                .filter(FreightActualCost.freight_order_id == freight_order_id, FreightActualCost.is_active.is_(True))
                .order_by(FreightActualCost.updated_at.desc())
                .first()
            )
    actual_cost_lines = []
    if actual_cost:
        actual_cost_lines = [
            {
                "id": item.id,
                "charge_type": item.charge_type,
                "description": item.description or "",
                "quantity": _decimal_to_float(item.quantity),
                "unit_price": _decimal_to_float(item.unit_price),
                "total_amount": _decimal_to_float(item.total_amount),
            }
            for item in sorted(actual_cost.items, key=lambda row: row.id)
        ]

    pod_records = [
        {
            "id": pod.id,
            "stop_no": pod.stop_no,
            "trip_id": pod.trip_id,
            "leg_id": pod.leg_id,
            "vehicle_id": pod.vehicle_id,
            "driver_id": pod.driver_id,
            "location_text": pod.location_text or "",
            "receiver_name": pod.receiver_name or "",
            "receiver_phone": pod.receiver_phone or "",
            "delivery_time": _iso_or_none(pod.delivery_time),
            "photo_url": pod.photo_url or "",
            "signature_url": pod.signature_url or "",
            "delivery_result": pod.delivery_result or "",
            "cargo_condition": pod.cargo_condition or "",
            "note": pod.note or "",
            "status": pod.status,
        }
        for pod in db.query(DeliveryPODRecord)
        .filter(DeliveryPODRecord.do_id == do_id)
        .order_by(DeliveryPODRecord.stop_no.asc(), DeliveryPODRecord.id.asc())
        .all()
    ]
    closeout = db.query(DeliveryOrderCloseout).filter_by(do_id=do_id).one_or_none()
    customer_adjustments = []
    if closeout:
        customer_adjustments = [
            {
                "id": row.id,
                "line_no": row.line_no,
                "name": row.name,
                "original_amount": _decimal_to_float(row.original_amount),
                "actual_amount": _decimal_to_float(row.actual_amount),
                "increase_amount": _decimal_to_float(row.increase_amount),
                "note": row.note or "",
            }
            for row in db.query(DeliveryOrderChargeAdjustment)
            .filter_by(closeout_id=closeout.id)
            .order_by(DeliveryOrderChargeAdjustment.line_no.asc())
            .all()
        ]
    pod_ids = [row["id"] for row in pod_records]
    documents = []
    if pod_ids:
        documents = [
            {
                "id": row.id,
                "pod_record_id": row.pod_record_id,
                "file_name": row.file_name,
                "mime_type": row.mime_type,
                "file_size": row.file_size,
                "checksum": row.checksum,
                "download_url": f"/api/pod-documents/{row.id}",
            }
            for row in db.query(DeliveryPODDocument)
            .filter(DeliveryPODDocument.pod_record_id.in_(pod_ids))
            .order_by(DeliveryPODDocument.created_at.asc())
            .all()
        ]
    invoice = (
        db.query(ARInvoice)
        .filter(ARInvoice.do_id == do_id, ARInvoice.is_active.is_(True))
        .order_by(ARInvoice.created_at.desc())
        .first()
    )
    selling_price = _decimal_to_float(sales_order.total_amount if sales_order else None)
    if selling_price <= 0 and quotation is not None:
        selling_price = _decimal_to_float(quotation.selling_price)
    actual_total = _decimal_to_float(actual_cost.total_amount if actual_cost else None)
    quoted_cost = _decimal_to_float(quotation.total_cost if quotation else None)
    cost_basis = actual_total or quoted_cost
    currency = (
        (closeout.currency_code if closeout else None)
        or
        (actual_cost.currency_code if actual_cost else None)
        or formula.get("currency")
        or "VND"
    )

    return {
        "do_id": delivery_order.id,
        "status": delivery_order.canonical_status or delivery_order.status or "",
        "sales_order_id": sales_order.id if sales_order else "",
        "quotation_id": quotation.id if quotation else "",
        "customer_id": delivery_order.customer_id or "",
        "route": {
            "id": route.id if route else delivery_order.route_id or "",
            "name": route.name if route else "",
            "distance_km": _decimal_to_float(route.distance_km if route else None),
        },
        "vehicle_id": delivery_order.vehicle_id or "",
        "driver_id": delivery_order.driver_id or "",
        "currency": currency,
        "cost_formula": formula,
        "configured_cost_lines": configured_cost_lines,
        "commercials": {
            "quoted_cost": quoted_cost,
            "actual_cost_total": actual_total,
            "selling_price": _decimal_to_float(closeout.final_selling_price) if closeout else selling_price,
            "base_selling_price": _decimal_to_float(closeout.base_selling_price_snapshot) if closeout else selling_price,
            "base_price_source": closeout.base_price_source if closeout else ("sales_order" if sales_order else "quotation"),
            "base_price_source_id": closeout.base_price_source_id if closeout else (sales_order.id if sales_order else quotation.id if quotation else ""),
            "customer_surcharge_total": _decimal_to_float(closeout.surcharge_total) if closeout else 0.0,
            "final_selling_price": _decimal_to_float(closeout.final_selling_price) if closeout else selling_price,
            "margin_amount": (_decimal_to_float(closeout.final_selling_price) if closeout else selling_price) - cost_basis,
            "margin_percent": round((((_decimal_to_float(closeout.final_selling_price) if closeout else selling_price) - cost_basis) / (_decimal_to_float(closeout.final_selling_price) if closeout else selling_price)) * 100, 2) if (_decimal_to_float(closeout.final_selling_price) if closeout else selling_price) else 0.0,
            "margin_is_provisional": actual_cost is None,
        },
        "customer_charge_adjustments": customer_adjustments,
        "pod_documents": documents,
        "invoice": serialize_ar_invoice(invoice) if invoice else None,
        "resource_release": {
            "assignment_status": assignment.status if assignment else "",
            "vehicle_status": assigned_vehicle.status if assigned_vehicle else "",
            "driver_status": assigned_driver.status if assigned_driver else "",
        },
        "actual_cost": {
            "id": actual_cost.id if actual_cost else "",
            "status": actual_cost.status if actual_cost else "",
            "currency": actual_cost.currency_code if actual_cost else currency,
            "total_amount": actual_total,
        },
        "actual_cost_lines": actual_cost_lines,
        "pod_records": pod_records,
        "trip": {
            "id": trip.id if trip else "",
            "status": trip.status if trip else "",
            "freight_order_id": trip.freight_order_id if trip else "",
            "legs": [
                {
                    "id": leg.id,
                    "sequence_no": leg.sequence_no,
                    "leg_type": leg.leg_type,
                    "origin": leg.origin,
                    "destination": leg.destination,
                    "stop_name": leg.stop_name or leg.destination,
                    "receiver_name": leg.receiver_name or "",
                    "receiver_phone": leg.receiver_phone or "",
                    "delivery_note": leg.delivery_note or "",
                    "distance_km": _decimal_to_float(leg.distance_km),
                    "status": leg.status,
                }
                for leg in legs
            ],
        },
    }

# 8. Accounting & Finance API
@app.get("/api/invoices")
async def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(ARInvoice).filter(ARInvoice.is_active.is_(True)).order_by(
        ARInvoice.created_at.desc(), ARInvoice.id.desc()
    ).limit(100).all()
    return [serialize_ar_invoice(invoice) for invoice in invoices]

@app.get("/api/gl-transactions")
async def list_gl_transactions(db: Session = Depends(get_db)):
    return db.query(GLTransaction).limit(100).all()

@app.post("/api/invoices/post")
async def post_invoice_and_gl(data: ARInvoicePostRequest, request: Request, db: Session = Depends(get_db)):
    actor = _require_api_principal(request)
    try:
        invoice = post_ar_invoice(db, data.model_dump(), user=actor)
        db.commit()
        db.refresh(invoice)
        return {
            "message": "Đã lập hóa đơn phải thu và hạch toán sổ cái.",
            "data": serialize_ar_invoice(invoice),
        }
    except DomainError as error:
        db.rollback()
        raise_http(error)
    except Exception:
        db.rollback()
        raise

# 9. Dashboard API (100% REAL DYNAMIC CALCULATIONS FROM DB)
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    so_sum = db.query(func.sum(SalesOrder.total_amount)).scalar() or 0.0
    inv_sum = db.query(func.sum(ARInvoice.total)).scalar() or 0.0
    total_rev = max(so_sum, inv_sum)

    total_do = db.query(DeliveryOrder).count()

    in_transit_count = db.query(DeliveryOrder).filter(
        DeliveryOrder.status.in_(["In Transit", "Đang vận chuyển", "Ready for Dispatch", "Sẵn sàng điều phối"])
    ).count()

    incidents_count = db.query(Incident).count()

    # Calculate REAL monthly P&L breakdown from database invoices & costs
    invoices = db.query(ARInvoice).all()
    costs = db.query(ShipmentCost).all()

    total_invoice_amount = sum(i.total for i in invoices) if invoices else total_rev
    total_shipment_cost = sum(c.total_cost for c in costs) if costs else 0.0

    # Group real invoices & costs by Month from CSDL
    monthly_map = {}
    for m in range(1, 13):
        m_str = f"Tháng {m}"
        monthly_map[m_str] = {"revenue": 0.0, "cost": 0.0}

    for inv in invoices:
        if hasattr(inv, 'created_at') and inv.created_at:
            m_str = f"Tháng {inv.created_at.month}"
            monthly_map[m_str]["revenue"] += float(inv.total or 0)
        else:
            monthly_map["Tháng 7"]["revenue"] += float(inv.total or 0)

    for cost in costs:
        if hasattr(cost, 'created_at') and cost.created_at:
            m_str = f"Tháng {cost.created_at.month}"
            monthly_map[m_str]["cost"] += float(cost.total_cost or 0)
        else:
            monthly_map["Tháng 7"]["cost"] += float(cost.total_cost or 0)

    cur_m = datetime.now().month
    display_months = [f"Tháng {m}" for m in range(max(1, cur_m - 5), cur_m + 1)]
    monthly_pl = []
    for m_str in display_months:
        rev = round(monthly_map[m_str]["revenue"])
        cst = round(monthly_map[m_str]["cost"])
        monthly_pl.append({
            "month": m_str,
            "revenue": rev,
            "cost": cst,
            "profit": rev - cst
        })

    return {
        "revenue_ytd": total_rev,
        "total_deliveries": total_do,
        "active_vehicles": in_transit_count,
        "incidents_count": incidents_count,
        "monthly_pl": monthly_pl
    }

# 10. Incident Management API
@app.get("/api/incidents")
async def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).order_by(Incident.id.desc()).all()

@app.post("/api/incidents")
async def create_incident(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    required = ["do_id", "vehicle_id", "incident_type", "location", "reporter"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise HTTPException(status_code=422, detail={
            "code": "MISSING_INCIDENT_DATA",
            "message": "Thiếu dữ liệu báo cáo sự cố. Vui lòng nhập đủ DO, xe, loại sự cố, vị trí và người báo cáo.",
            "missing_fields": missing,
            "navigation_targets": ["incidents", "delivery-orders", "master-data/vehicles"],
        })
    inc = Incident(
        do_id=data.get("do_id"),
        vehicle_id=data.get("vehicle_id"),
        incident_type=data.get("incident_type"),
        severity=data.get("severity") or "Medium",
        location=data.get("location"),
        description=data.get("description", ""),
        reporter=data.get("reporter"),
        reported_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        status="Open"
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return {"message": "Đã ghi nhận báo cáo sự cố vận chuyển thành công!", "data": inc}

# 10. Full Data Query Endpoint
def _safe_permissions(value):
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        permissions = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return permissions if isinstance(permissions, list) else []


def _dossier_row(row):
    if row is None:
        return None
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }


@app.get("/api/delivery-orders/{delivery_order_id}/dossier")
async def get_delivery_order_dossier(
    delivery_order_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return only records that belong to one delivery order."""
    _require_api_principal(request)
    order = db.get(DeliveryOrder, delivery_order_id)
    if order is None:
        raise_http(DomainError("DELIVERY_ORDER_NOT_FOUND", "Khong tim thay Delivery Order.", 404))

    legacy_link = (
        db.query(FreightOrderLegacyLink)
        .filter(FreightOrderLegacyLink.delivery_order_id == delivery_order_id)
        .first()
    )
    freight_order_id = legacy_link.freight_order_id if legacy_link else None
    trip_links = (
        db.query(TripDeliveryOrder)
        .filter(TripDeliveryOrder.do_id == delivery_order_id)
        .all()
    )
    trip_ids = {link.trip_id for link in trip_links}
    trips = db.query(TransportTrip).filter(TransportTrip.id.in_(trip_ids)).all() if trip_ids else []
    if freight_order_id:
        known_trip_ids = {trip.id for trip in trips}
        for trip in db.query(TransportTrip).filter(TransportTrip.freight_order_id == freight_order_id).all():
            if trip.id not in known_trip_ids:
                trips.append(trip)
                trip_ids.add(trip.id)

    events = (
        db.query(TransportEvent)
        .filter(TransportEvent.freight_order_id == freight_order_id)
        .order_by(TransportEvent.event_time.asc())
        .all()
        if freight_order_id else []
    )
    pods = (
        db.query(DeliveryPODRecord)
        .filter(DeliveryPODRecord.do_id == delivery_order_id)
        .order_by(DeliveryPODRecord.stop_no.asc(), DeliveryPODRecord.id.asc())
        .all()
    )
    costs = (
        db.query(FreightActualCost)
        .filter(FreightActualCost.freight_order_id == freight_order_id)
        .order_by(FreightActualCost.created_at.asc())
        .all()
        if freight_order_id else []
    )
    cost_ids = [cost.id for cost in costs]
    ap_invoices = db.query(APInvoice).filter(APInvoice.cost_id.in_(cost_ids)).all() if cost_ids else []
    ap_ids = [invoice.id for invoice in ap_invoices]
    settlements = (
        db.query(FreightSettlement).filter(FreightSettlement.ap_invoice_id.in_(ap_ids)).all()
        if ap_ids else []
    )
    carrier_ids = {cost.carrier_id for cost in costs if cost.carrier_id}
    carriers = db.query(Carrier).filter(Carrier.id.in_(carrier_ids)).all() if carrier_ids else []

    sales_order = db.get(SalesOrder, order.so_id) if order.so_id else None
    quotation = db.get(Quotation, sales_order.quotation_id) if sales_order and sales_order.quotation_id else None
    route = db.get(Route, order.route_id) if order.route_id else None
    vehicle = db.get(Vehicle, order.vehicle_id) if order.vehicle_id else None
    driver_ids = {value for value in (order.driver_id, order.co_driver) if value}
    drivers = db.query(Driver).filter(Driver.id.in_(driver_ids)).all() if driver_ids else []
    freight_order = db.get(FreightOrder, freight_order_id) if freight_order_id else None
    ar_invoices = db.query(ARInvoice).filter(ARInvoice.do_id == delivery_order_id).all()
    closeouts = db.query(DeliveryOrderCloseout).filter(DeliveryOrderCloseout.do_id == delivery_order_id).all()

    order_payload = _dossier_row(order)
    order_payload["freight_order_id"] = freight_order_id
    if route and not order_payload.get("distance_km"):
        order_payload["distance_km"] = route.distance_km

    return {
        "delivery_orders": [order_payload],
        "sales_orders": [_dossier_row(sales_order)] if sales_order else [],
        "quotations": [_dossier_row(quotation)] if quotation else [],
        "routes": [_dossier_row(route)] if route else [],
        "vehicles": [_dossier_row(vehicle)] if vehicle else [],
        "drivers": [_dossier_row(row) for row in drivers],
        "freight_orders": [_dossier_row(freight_order)] if freight_order else [],
        "freight_order_legacy_links": [_dossier_row(legacy_link)] if legacy_link else [],
        "trip_delivery_orders": [_dossier_row(row) for row in trip_links],
        "transport_trips": [_dossier_row(row) for row in trips],
        "transport_events": [_dossier_row(row) for row in events],
        "pods": [_dossier_row(row) for row in pods],
        "freight_actual_costs": [_dossier_row(row) for row in costs],
        "ap_invoices": [_dossier_row(row) for row in ap_invoices],
        "settlements": [_dossier_row(row) for row in settlements],
        "carriers": [_dossier_row(row) for row in carriers],
        "invoices": [_dossier_row(row) for row in ar_invoices],
        "closeouts": [_dossier_row(row) for row in closeouts],
        "meta": {"loaded_at": datetime.now(timezone.utc).isoformat()},
    }


@app.get("/api/data/all")
async def get_all_data(request: Request, db: Session = Depends(get_db)):
    _require_api_principal(request)
    payload = {
        "vehicles": [
            {
                "id": v.id,
                "type": v.type,
                "weight_capacity": v.weight_capacity,
                "status": v.status,
                "fuel_norm": v.fuel_norm,
                "min_speed_kmh": v.min_speed_kmh,
                "max_speed_kmh": v.max_speed_kmh,
                "brand": v.brand,
                "image_url": v.image_url,
            }
            for v in db.query(Vehicle).order_by(Vehicle.id.desc()).limit(100).all()
        ],
        "drivers": [
            {"id": d.id, "name": d.name, "phone": d.phone, "status": d.status, "assigned_vehicle": d.assigned_vehicle}
            for d in db.query(Driver).limit(100).all()
        ],
        "customers": [
            {"id": c.id, "name": c.name, "type": c.type, "phone": c.phone}
            for c in db.query(Customer).limit(100).all()
        ],
        "quotations": [
            {
                "id": q.id, 
                "customer": q.customer_id, 
                "customer_id": q.customer_id, 
                "route": q.route_id, 
                "route_id": q.route_id, 
                "cargo_type": q.cargo_type, 
                "valid_to": q.valid_to,
                "origin": q.origin,
                "destination": q.destination,
                "pickup_window_start": q.pickup_window_start,
                "pickup_window_end": q.pickup_window_end,
                "delivery_window_start": q.delivery_window_start,
                "delivery_window_end": q.delivery_window_end,
                "weight_kg": q.weight_kg,
                "pallet_count": q.pallet_count,
                "total_cost": getattr(q, 'total_cost', 0) or ((getattr(q, 'fuel_cost', 0) or 0) + (getattr(q, 'driver_cost', 0) or 0) + (getattr(q, 'toll_fee', 0) or 0)),
                "margin_pct": None,
                "selling_price": q.selling_price,
                "status": q.status
            }
            for q in db.query(Quotation).order_by(Quotation.id.desc()).limit(100).all()
        ],
        "sales_orders": [
            {
                "id": s.id, 
                "quotation_id": s.quotation_id, 
                "customer": s.customer_id, 
                "customer_id": s.customer_id, 
                "origin": s.origin, 
                "destination": s.destination, 
                "route_id": s.route_id,
                "pickup_window_start": s.pickup_window_start,
                "pickup_window_end": s.pickup_window_end,
                "delivery_window_start": s.delivery_window_start,
                "delivery_window_end": s.delivery_window_end,
                "weight_kg": s.weight_kg,
                "pallet_count": s.pallet_count,
                "order_date": s.order_date, 
                "payment_terms": s.payment_terms, 
                "sales_rep": s.sales_rep, 
                "description": f"Vận chuyển {s.origin} -> {s.destination}", 
                "status": s.status, 
                "total_amount": s.total_amount
            }
            for s in db.query(SalesOrder).order_by(SalesOrder.id.desc()).limit(100).all()
        ],
        "delivery_orders": [
            {
                "id": d.id, 
                "so_id": d.so_id, 
                "customer": d.customer_id, 
                "customer_id": d.customer_id, 
                "route": d.route_id, 
                "route_id": d.route_id, 
                "origin": d.origin,
                "destination": d.destination,
                "pickup_window_start": d.pickup_window_start,
                "pickup_window_end": d.pickup_window_end,
                "delivery_window_start": d.delivery_window_start,
                "delivery_window_end": d.delivery_window_end,
                "pickup_date": d.pickup_date, 
                "delivery_date": d.delivery_date, 
                "planned_departure_at": d.planned_departure_at,
                "planned_arrival_at": d.planned_arrival_at,
                "planned_return_at": d.planned_return_at,
                "avg_speed_kmh": d.avg_speed_kmh,
                "return_speed_kmh": d.return_speed_kmh,
                "load_minutes": d.load_minutes,
                "unload_minutes": d.unload_minutes,
                "return_distance_km": d.return_distance_km,
                "vehicle": d.vehicle_id, 
                "vehicle_id": d.vehicle_id,
                "driver": d.driver_id, 
                "driver_id": d.driver_id,
                "weight_kg": d.weight_kg,
                "pallet_count": d.pallet_count,
                "status": d.status
            }
            for d in db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc()).limit(100).all()
        ],
        "routes": [
            {"id": r.id, "name": r.name, "distance_km": r.distance_km, "est_time": None}
            for r in db.query(Route).limit(100).all()
        ],
        "dispatches": [
            {
                "dispatch_date": d.pickup_date,
                "department": "Điều phối",
                "planner": d.updated_by,
                "do_id": d.id,
                "route": d.route_id,
                "vehicle": d.vehicle_id,
                "driver": d.driver_id,
                "schedule": None,
                "status": d.status
            }
            for d in db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc()).limit(100).all()
        ],
        "invoices": [
            {
                "id": inv.id,
                "customer": inv.customer_id,
                "customer_id": inv.customer_id,
                "do_id": inv.do_id,
                "invoice_date": inv.invoice_date,
                "due_date": None,
                "subtotal": round((inv.amount or 0), 2),
                "vat_amount": round((inv.vat_amount or 0), 2),
                "total": inv.total,
                "status": inv.status
            }
            for inv in db.query(ARInvoice).order_by(ARInvoice.id.desc()).limit(100).all()
        ],
        "incidents": [
            {
                "id": f"INC-{inc.id}",
                "do_id": inc.do_id,
                "date_time": inc.reported_at,
                "driver": inc.reporter,
                "incident_type": inc.incident_type,
                "location": inc.location,
                "description": inc.description,
                "status": inc.status
            }
            for inc in db.query(Incident).order_by(Incident.id.desc()).limit(100).all()
        ],
        "currencies": [
            {"code": c.code, "minor_units": c.minor_units, "status": "active" if c.is_active else "inactive"}
            for c in db.query(CurrencyDefinition).order_by(CurrencyDefinition.code.asc()).limit(100).all()
        ],
        "tax_codes": [
            {
                "id": t.id,
                "code": t.code,
                "rate": float(t.rate or 0),
                "mode": t.mode,
                "effective_from": t.effective_from,
                "effective_to": t.effective_to,
                "is_active": t.is_active,
                "status": "active" if t.is_active else "inactive",
            }
            for t in db.query(TaxCode).order_by(TaxCode.code.asc()).limit(100).all()
        ],
        "accounting_periods": [
            {"id": p.id, "starts_at": p.starts_at, "ends_at": p.ends_at, "status": p.status}
            for p in db.query(AccountingPeriod).order_by(AccountingPeriod.starts_at.desc()).limit(100).all()
        ],
        "carriers": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "tax_code": c.tax_code,
                "contact_person": c.contact_person,
                "phone": c.phone,
                "email": c.email,
                "is_internal": c.is_internal,
            }
            for c in db.query(Carrier).order_by(Carrier.id.asc()).limit(100).all()
        ],
        "freight_orders": [
            {
                "id": fo.id,
                "status": fo.status,
                "pickup_location_id": fo.pickup_location_id,
                "delivery_location_id": fo.delivery_location_id,
                "total_weight_kg": float(fo.total_weight_kg or 0),
                "total_volume_m3": float(fo.total_volume_m3 or 0),
                "total_pallet_count": fo.total_pallet_count,
                "version": fo.version,
            }
            for fo in db.query(FreightOrder).order_by(FreightOrder.created_at.desc()).limit(100).all()
        ],
        "tenders": [
            {
                "id": t.id,
                "freight_order_id": t.freight_order_id,
                "status": t.status,
                "response_deadline": t.response_deadline,
                "awarded_offer_id": t.awarded_offer_id,
                "awarded_carrier_id": t.awarded_carrier_id,
                "version": t.version,
            }
            for t in db.query(Tender).order_by(Tender.created_at.desc()).limit(100).all()
        ],
        "tender_offers": [
            {
                "id": o.id,
                "tender_id": o.tender_id,
                "carrier_id": o.carrier_id,
                "amount": float(o.amount or 0),
                "currency_code": o.currency_code,
                "transit_time_hours": o.transit_time_hours,
                "status": o.status,
            }
            for o in db.query(TenderOffer).order_by(TenderOffer.amount.asc()).limit(100).all()
        ],
        "transport_events": [
            {
                "id": e.id,
                "freight_order_id": e.freight_order_id,
                "event_type": e.event_type,
                "event_time": e.event_time,
                "lat": e.lat,
                "lng": e.lng,
                "speed_kmh": e.speed_kmh,
                "distance_km": e.distance_km,
                "eta": e.eta,
                "location_text": e.location_text,
                "source": e.source,
                "device_id": e.device_id,
                "reason": e.reason,
                "note": e.note,
                "recorded_at": e.recorded_at,
                "recorded_by": e.recorded_by,
            }
            for e in db.query(TransportEvent).order_by(TransportEvent.event_time.desc(), TransportEvent.recorded_at.desc()).limit(200).all()
        ],
        "account_mappings": [
            {
                "mapping_key": m.mapping_key,
                "account_code": m.account_code,
                "effective_from": m.effective_from,
                "effective_to": m.effective_to,
                "status": "inactive" if m.effective_to and m.effective_to <= datetime.utcnow() else "active",
            }
            for m in db.query(AccountMapping).order_by(AccountMapping.mapping_key.asc()).limit(100).all()
        ],
        "freight_actual_costs": [
            {
                "id": c.id,
                "freight_order_id": c.freight_order_id,
                "carrier_id": c.carrier_id,
                "total_amount": float(c.total_amount or 0),
                "currency_code": c.currency_code,
                "status": c.status,
                "version": c.version,
            }
            for c in db.query(FreightActualCost).order_by(FreightActualCost.created_at.desc()).limit(100).all()
        ],
        "ap_invoices": [
            {
                "id": ap.id,
                "cost_id": ap.cost_id,
                "carrier_id": ap.carrier_id,
                "vendor_invoice_no": ap.vendor_invoice_no,
                "total_amount": float(ap.total_amount or 0),
                "currency_code": ap.currency_code,
                "status": ap.status,
                "version": ap.version,
            }
            for ap in db.query(APInvoice).order_by(APInvoice.created_at.desc()).limit(100).all()
        ],
        "settlements": [
            {
                "id": s.id,
                "ap_invoice_id": s.ap_invoice_id,
                "approved_amount": float(s.approved_amount or 0),
                "paid_amount": float(s.paid_amount or 0),
                "remaining_amount": float(s.remaining_amount or 0),
                "currency_code": s.currency_code,
                "status": s.status,
                "version": s.version,
            }
            for s in db.query(FreightSettlement).order_by(FreightSettlement.created_at.desc()).limit(100).all()
        ],
        "roles": [
            {
                "id": r.id,
                "permissions": _safe_permissions(r.permissions),
            }
            for r in db.query(Role).order_by(Role.id.asc()).limit(100).all()
        ],
        "users": [
            {"id": u.id, "username": u.username, "role_id": u.role_id}
            for u in db.query(User).order_by(User.id.asc()).limit(100).all()
        ],
        "audit_logs": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "action": a.action,
                "table_name": a.table_name,
                "record_id": a.record_id,
                "created_at": a.timestamp,
                "ip_address": a.ip_address,
            }
            for a in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
        ],
        "pods": [
            {
                "id": f"POD-{p.id}",
                "pod_record_id": p.id,
                "do_id": p.do_id,
                "vehicle_id": p.vehicle_id,
                "driver_id": p.driver_id,
                "stop_no": p.stop_no,
                "location_text": p.location_text,
                "delivery_time": p.delivery_time,
                "receiver": p.receiver_name,
                "receiver_name": p.receiver_name,
                "receiver_phone": p.receiver_phone,
                "photo_url": p.photo_url,
                "signature_url": p.signature_url,
                "note": p.note,
            }
            for p in db.query(DeliveryPODRecord).order_by(DeliveryPODRecord.do_id.desc(), DeliveryPODRecord.stop_no.asc()).limit(200).all()
        ]
    }
    # Keep the broad bootstrap limited to operational/master-data records.
    # Finance identity, permissions, and audit history are served by their
    # authorized module endpoints or by the shipment-scoped dossier.
    for sensitive_key in ("invoices", "freight_actual_costs", "ap_invoices", "settlements", "roles", "users", "audit_logs"):
        payload[sensitive_key] = []
    return payload


def _parse_iso_datetime(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "MASTER_DATA_INVALID", "message": f"Vui lòng nhập {field} hợp lệ."},
        )
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "MASTER_DATA_INVALID", "message": f"Vui lòng nhập {field} đúng định dạng ngày giờ."},
        )


def _parse_iso_date(value: str, field: str):
    if isinstance(value, str) and len(value.strip()) == 10:
        value = f"{value.strip()}T00:00:00"
    return _parse_iso_datetime(value, field).date()


def _clean_master_string(data: dict, key: str, label: str, max_len: int = 100) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_len:
        raise HTTPException(
            status_code=422,
            detail={"code": "MASTER_DATA_INVALID", "message": f"Vui lòng nhập {label} hợp lệ."},
        )
    return value.strip()


def _master_saved(entity):
    return {"message": "Đã lưu cấu hình Master Data vào CSDL.", "data": entity}


@app.post("/api/master-data/tax-codes")
def save_tax_code(data: dict = Body(...), db: Session = Depends(get_db)):
    code = _clean_master_string(data, "code", "mã thuế", 50).upper()
    try:
        rate = Decimal(str(data.get("rate")))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Vui lòng nhập thuế suất hợp lệ."})
    if rate < 0:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Thuế suất không được âm."})
    mode = str(data.get("mode") or "exclusive").strip().lower()
    if mode not in {"exclusive", "inclusive", "exempt"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Kiểu tính thuế không hợp lệ."})
    effective_from = _parse_iso_date(data.get("effective_from"), "ngày hiệu lực")
    tax = db.query(TaxCode).filter(TaxCode.code == code, TaxCode.effective_from == effective_from).first()
    if not tax:
        tax = TaxCode(code=code, effective_from=effective_from)
        db.add(tax)
    tax.rate = rate
    tax.mode = mode
    tax.effective_to = _parse_iso_date(data["effective_to"], "ngày hết hiệu lực") if data.get("effective_to") else None
    tax.is_active = bool(data.get("is_active", True))
    tax.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(tax)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "MASTER_DATA_DUPLICATE", "message": "Mã thuế đã tồn tại hoặc dữ liệu không hợp lệ."})
    return _master_saved(tax)


@app.put("/api/master-data/tax-codes/{code}")
def update_tax_code(code: str, data: dict = Body(...), db: Session = Depends(get_db)):
    payload = dict(data or {})
    payload["code"] = code
    return save_tax_code(payload, db)


@app.post("/api/master-data/tax-codes/{code}/status")
def set_tax_code_status(code: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    is_active = bool((data or {}).get("is_active", True))
    rows = db.query(TaxCode).filter(func.upper(TaxCode.code) == str(code).upper()).all()
    if not rows:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mã thuế cần cập nhật."})
    for row in rows:
        row.is_active = is_active
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Đã cập nhật trạng thái mã thuế.", "data": {"code": code, "is_active": is_active}}


@app.delete("/api/master-data/tax-codes/{code}")
def delete_tax_code(code: str, db: Session = Depends(get_db)):
    rows = db.query(TaxCode).filter(func.upper(TaxCode.code) == str(code).upper()).all()
    if not rows:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mã thuế cần xóa."})
    for row in rows:
        db.delete(row)
    db.commit()
    return {"message": "Đã xóa mã thuế khỏi Master Data.", "data": {"code": code}}


@app.post("/api/master-data/accounting-periods")
def save_accounting_period(data: dict = Body(...), db: Session = Depends(get_db)):
    period_id = _clean_master_string(data, "id", "mã kỳ kế toán", 50)
    starts_at = _parse_iso_datetime(data.get("starts_at"), "ngày bắt đầu kỳ")
    ends_at = _parse_iso_datetime(data.get("ends_at"), "ngày kết thúc kỳ")
    if starts_at > ends_at:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Ngày bắt đầu kỳ không được sau ngày kết thúc kỳ."})
    status = str(data.get("status") or "open").strip().lower()
    if status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Trạng thái kỳ kế toán chỉ được là mở hoặc đã khóa."})
    period = db.get(AccountingPeriod, period_id) or AccountingPeriod(id=period_id)
    db.add(period)
    period.starts_at = starts_at
    period.ends_at = ends_at
    period.status = status
    try:
        db.commit()
        db.refresh(period)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "MASTER_DATA_DUPLICATE", "message": "Kỳ kế toán đã tồn tại hoặc dữ liệu không hợp lệ."})
    return _master_saved(period)


@app.put("/api/master-data/accounting-periods/{period_id}")
def update_accounting_period(period_id: str, data: dict = Body(...), db: Session = Depends(get_db)):
    payload = dict(data or {})
    payload["id"] = period_id
    return save_accounting_period(payload, db)


@app.post("/api/master-data/accounting-periods/{period_id}/status")
def set_accounting_period_status(period_id: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    period = db.get(AccountingPeriod, period_id)
    if not period:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy kỳ kế toán cần cập nhật."})
    status = str((data or {}).get("status") or "open").strip().lower()
    if status not in {"open", "closed"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Trạng thái kỳ kế toán chỉ được là mở hoặc đã khóa."})
    period.status = status
    period.closed_at = datetime.utcnow() if status == "closed" else None
    period.closed_by = "ui" if status == "closed" else None
    db.commit()
    return {"message": "Đã cập nhật trạng thái kỳ kế toán.", "data": {"id": period_id, "status": status}}


@app.delete("/api/master-data/accounting-periods/{period_id}")
def delete_accounting_period(period_id: str, db: Session = Depends(get_db)):
    period = db.get(AccountingPeriod, period_id)
    if not period:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy kỳ kế toán cần xóa."})
    db.delete(period)
    db.commit()
    return {"message": "Đã xóa kỳ kế toán khỏi Master Data.", "data": {"id": period_id}}


@app.post("/api/master-data/account-mappings")
def save_account_mapping(data: dict = Body(...), db: Session = Depends(get_db)):
    mapping_key = _clean_master_string(data, "mapping_key", "khóa mapping", 120)
    account_code = _clean_master_string(data, "account_code", "tài khoản GL", 50)
    mapping = db.get(AccountMapping, mapping_key) or AccountMapping(mapping_key=mapping_key)
    db.add(mapping)
    mapping.account_code = account_code
    mapping.effective_from = _parse_iso_datetime(data["effective_from"], "ngày hiệu lực") if data.get("effective_from") else None
    mapping.effective_to = _parse_iso_datetime(data["effective_to"], "ngày hết hiệu lực") if data.get("effective_to") else None
    if mapping.effective_from and mapping.effective_to and mapping.effective_from > mapping.effective_to:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Ngày hiệu lực mapping không hợp lệ."})
    try:
        db.commit()
        db.refresh(mapping)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "MASTER_DATA_DUPLICATE", "message": "Mapping tài khoản đã tồn tại hoặc dữ liệu không hợp lệ."})
    return _master_saved(mapping)


@app.put("/api/master-data/account-mappings/{mapping_key}")
def update_account_mapping(mapping_key: str, data: dict = Body(...), db: Session = Depends(get_db)):
    payload = dict(data or {})
    payload["mapping_key"] = mapping_key
    return save_account_mapping(payload, db)


@app.post("/api/master-data/account-mappings/{mapping_key}/status")
def set_account_mapping_status(mapping_key: str, data: dict = Body(default={}), db: Session = Depends(get_db)):
    mapping = db.get(AccountMapping, mapping_key)
    if not mapping:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mapping tài khoản cần cập nhật."})
    status = str((data or {}).get("status") or "active").strip().lower()
    if status not in {"active", "inactive"}:
        raise HTTPException(status_code=422, detail={"code": "MASTER_DATA_INVALID", "message": "Trạng thái mapping chỉ được là hoạt động hoặc ngưng hoạt động."})
    if status == "inactive" and not mapping.effective_to:
        mapping.effective_to = datetime.utcnow()
    if status == "active":
        mapping.effective_to = None
    db.commit()
    return {"message": "Đã cập nhật trạng thái mapping tài khoản.", "data": {"mapping_key": mapping_key, "status": status}}


@app.delete("/api/master-data/account-mappings/{mapping_key}")
def delete_account_mapping(mapping_key: str, db: Session = Depends(get_db)):
    mapping = db.get(AccountMapping, mapping_key)
    if not mapping:
        raise HTTPException(status_code=404, detail={"code": "MASTER_DATA_NOT_FOUND", "message": "Không tìm thấy mapping tài khoản cần xóa."})
    db.delete(mapping)
    db.commit()
    return {"message": "Đã xóa mapping tài khoản khỏi Master Data.", "data": {"mapping_key": mapping_key}}


# Dynamic Frontend Directory Resolution
possible_frontend_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "EPL_System", "frontend")),
]

frontend_dir = None
for path_cand in possible_frontend_paths:
    if os.path.exists(path_cand) and os.path.isdir(path_cand):
        frontend_dir = path_cand
        break

if not frontend_dir:
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    os.makedirs(frontend_dir, exist_ok=True)

print(f"[Static Assets]: Mounting frontend directory at: {frontend_dir}")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/favicon.ico")
async def serve_favicon():
    return Response(status_code=204)

@app.get("/tongquan.jpg")
async def serve_overview_image():
    possible_img_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tongquan.jpg")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tongquan.jpg")),
        os.path.abspath(os.path.join(os.getcwd(), "tongquan.jpg")),
    ]
    for img_p in possible_img_paths:
        if os.path.exists(img_p):
            return FileResponse(img_p)
    raise HTTPException(status_code=404, detail="Overview image not found")

FRONTEND_HTML_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}

TEST_RUNNER_HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kịch bản kiểm thử EPL</title>
</head>
<body>
  <main>
    <h1>Kịch bản kiểm thử EPL</h1>
    <p>Chạy tối đa 5,000 lượt kiểm tra hợp đồng API cho môi trường demo.</p>
    <p><strong>Kiểm thử API, không thay thế kiểm thử giao diện</strong></p>
  </main>
</body>
</html>"""


def _frontend_html_response(content: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        content=content,
        status_code=status_code,
        media_type="text/html; charset=utf-8",
        headers=FRONTEND_HTML_HEADERS,
    )


def _serve_frontend_html(filename: str, missing_label: str) -> HTMLResponse:
    html_path = os.path.join(frontend_dir, filename)
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return _frontend_html_response(f.read())
    return _frontend_html_response(
        content=f"<h1>Không tìm thấy {missing_label} tại {html_path}</h1>",
        status_code=404,
    )

@app.get("/test-runner", response_class=HTMLResponse)
async def serve_test_runner():
    runner_path = os.path.join(frontend_dir, "test_15_button_flow_runner.html")
    if os.path.exists(runner_path):
        return _serve_frontend_html(
            "test_15_button_flow_runner.html",
            "trang chạy kịch bản kiểm thử",
        )
    return _frontend_html_response(TEST_RUNNER_HTML)

@app.get("/kich-ban-test", response_class=HTMLResponse)
async def serve_test_runner_vietnamese_alias():
    return await serve_test_runner()

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        client_token = os.getenv("EPL_TMS_API_TOKEN", "").strip()
        if client_token:
            runtime_config = (
                "<script>window.EPL_TMS_API_TOKEN="
                + json.dumps(client_token)
                + ";</script>"
            )
            content = content.replace("</head>", runtime_config + "</head>", 1)
        return _frontend_html_response(content)
    return _frontend_html_response(f"<h1>Không tìm thấy index.html tại {index_path}</h1>", status_code=404)
