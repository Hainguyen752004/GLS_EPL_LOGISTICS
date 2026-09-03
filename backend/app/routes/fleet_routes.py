"""Đội xe: phương tiện, loại xe, phiếu sửa chữa, công thức chi phí, tài xế.

18 endpoint. Nhóm này ghi dữ liệu gốc mà phần điều phối và tính giá đều dựa vào
— sức chở của xe quyết định gác tải, còn công thức chi phí nuôi giá cước.
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


router = APIRouter(dependencies=[Depends(require_api_principal)])


@router.get("/api/vehicles")
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

@router.post("/api/vehicles")
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


@router.get("/api/vehicles/{vehicle_id}/maintenance-requests")
async def get_vehicle_maintenance_requests(vehicle_id: str, db: Session = Depends(get_db)):
    try:
        items = list_vehicle_maintenance_requests(db, vehicle_id)
        return {"data": [serialize_vehicle_maintenance_request(item) for item in items]}
    except DomainError as error:
        raise_http(error)


@router.post("/api/vehicles/{vehicle_id}/maintenance-requests", status_code=201)
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


@router.post("/api/vehicle-maintenance-requests/{request_id}/approve")
async def approve_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "approve", request, data, db)


@router.post("/api/vehicle-maintenance-requests/{request_id}/start")
async def start_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "start", request, data, db)


@router.post("/api/vehicle-maintenance-requests/{request_id}/complete")
async def complete_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "complete", request, data, db)


@router.post("/api/vehicle-maintenance-requests/{request_id}/cancel")
async def cancel_vehicle_maintenance_request(request_id: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return await _run_vehicle_maintenance_transition(request_id, "cancel", request, data, db)

@router.delete("/api/vehicles/{vid}")
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
@router.get("/api/vehicle-types")
async def list_vehicle_types(db: Session = Depends(get_db)):
    from models import VehicleType
    return db.query(VehicleType).all()

@router.get("/api/vehicle-types/recommendations")
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

@router.post("/api/vehicle-types")
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

@router.delete("/api/vehicle-types/{vid}")
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


@router.get("/api/cost-formulas")
async def list_cost_formulas(db: Session = Depends(get_db)):
    return [
        _serialize_cost_formula(row)
        for row in db.query(CostFormula).order_by(CostFormula.id).all()
    ]


@router.post("/api/cost-formulas")
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
@router.get("/api/drivers")
async def list_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()

@router.post("/api/drivers")
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

@router.delete("/api/drivers/{did}")
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

# Toàn bộ phần tỷ giá (state, lịch làm mới, và 5 endpoint) đã chuyển sang
# routes/currency_routes.py. Tỷ giá nuôi mọi phép quy đổi tiền tệ nên nó
# thuộc nhóm tài chính, và router đó tự mang dependency xác thực.
# Các endpoint khách hàng và tuyến đường đã chuyển sang
# routes/master_data_routes.py.

# 7. Tracking API
