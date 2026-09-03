"""Trợ lý AI, upload ảnh, và quét biển số tại chốt.

Ba nhóm này ở cùng một chỗ vì chúng chia nhau phần đọc tệp upload theo từng
khối và ngưỡng kích thước.

KHÔNG gắn dependency xác thực ở tầng router, vì GET /uploads/{asset_path} phải
công khai: giao diện hiển thị ảnh bằng <img src="/uploads/...">, mà thẻ <img>
không gửi được header Authorization. Đường đọc đó tự phòng thủ thay vì dựa vào
xác thực — chặn path traversal, chỉ nhận đúng hai thành phần đường dẫn, và chỉ
phục vụ thư mục trong danh sách cho phép. Các endpoint còn lại của file này vẫn
được chặn bởi auth_middleware ở tầng ứng dụng.
"""

import os
import sys
import json
import threading
import time
from collections import defaultdict, deque
from threading import Lock
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from uuid import uuid4
from decimal import Decimal, InvalidOperation

# Workaround for Protobuf >= 4.x compatibility with PaddleOCR / PaddlePaddle
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form, Request, Query
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

from database import get_db
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
from runtime_state import runtime_state
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
from routes.shared import (
    decimal_to_float as _decimal_to_float,
    iso_or_none as _iso_or_none,
    require_api_principal,
    require_api_principal as _require_api_principal,
    safe_permissions as _safe_permissions,
    serialize_cost_formula as _serialize_cost_formula,
)


# Các biến và ngoại lệ dành riêng cho AI / upload, chuyển từ main.py cùng nhóm
# endpoint dùng chúng.
ai_checkpoint_engine = None
ai_checkpoint_lock = threading.Lock()

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


router = APIRouter()


@router.post("/api/v1/ai/chat")
async def gateway_chat(payload: Dict[str, Any], db: Session = Depends(get_db)):
    prompt = payload.get("prompt", "")
    is_confirmed = payload.get("is_confirmed", False)
    draft_data = payload.get("draft_data", None)
    
    if not prompt and not is_confirmed:
        raise HTTPException(status_code=400, detail="Vui lòng nhập nội dung câu hỏi.")

    # Các agent gọi LLM bằng urllib đồng bộ (timeout 12s, retry qua 4 model),
    # nên gọi trực tiếp trong hàm async sẽ khóa event loop tới ~48 giây và làm
    # đứng mọi request khác của tiến trình.
    return await run_in_threadpool(
        GatewayRouter.process_request, prompt, db, is_confirmed, draft_data
    )

# Direct Agent Endpoints
@router.post("/api/agent/query")
async def query_agent_api(payload: Dict[str, Any], db: Session = Depends(get_db)):
    return await run_in_threadpool(QueryAgent.process, payload.get("prompt", ""), db)

@router.post("/api/agent/action")
async def action_agent_api(payload: Dict[str, Any], db: Session = Depends(get_db)):
    return await run_in_threadpool(ActionAgent.process, payload.get("prompt", ""), db)

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


@router.post("/api/uploads/images", status_code=201)
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


@router.get("/uploads/{asset_path:path}")
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


@router.post("/api/ai/checkpoint/scan")
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
