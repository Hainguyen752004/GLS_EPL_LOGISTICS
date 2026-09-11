"""Sự cố và hồ sơ lệnh giao hàng.

Gộp hai nhóm cùng bản chất "tra cứu vận hành": danh sách/tạo sự cố, và hồ sơ
tổng hợp một lệnh giao hàng.
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
from models import (    Vehicle, Driver, Route, Warehouse, Customer, DeliveryOrder,
    VehicleTracking, DeliveryPODRecord, 
    AuditLog, Quotation, Incident, 
    AccountMapping, Carrier, Tender, TenderOffer, FreightOrder, TransportTrip,
    TransportEvent, ResourceAssignment, TripDeliveryOrder, TransportTripLeg,
    FreightActualCost, FreightChargeItem, 
    CurrencyDefinition, CurrencyRateHistory, Role, User, CostFormula, DeliveryOrderCloseout,
    DeliveryOrderChargeAdjustment, DeliveryPODDocument, VehicleMaintenanceRequest,
    FreightOrderLegacyLink,
)
from gateway.router import GatewayRouter
from agents.query_agent import QueryAgent
from agents.action_agent import ActionAgent
from runtime_state import runtime_state
from schemas.workflow import RouteCreateRequest
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


@router.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).order_by(Incident.id.desc()).all()

@router.post("/api/incidents")
def create_incident(data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    required = ["do_id", "vehicle_id", "incident_type", "location", "reporter"]
    missing = [key for key in required if not isinstance(data.get(key), str) or not data[key].strip()]
    if missing:
        raise HTTPException(status_code=422, detail={
            "code": "MISSING_INCIDENT_DATA",
            "message": "Thiếu dữ liệu báo cáo sự cố. Vui lòng nhập đủ DO, xe, loại sự cố, vị trí và người báo cáo.",
            "missing_fields": missing,
            "navigation_targets": ["incidents", "delivery-orders", "master-data/vehicles"],
        })
    data = {**data, **{key: data[key].strip() for key in required}}
    order = db.get(DeliveryOrder, data['do_id'])
    vehicle = db.get(Vehicle, data['vehicle_id'])
    if order is None or vehicle is None:
        raise HTTPException(status_code=404, detail={
            'code': 'INCIDENT_RESOURCE_NOT_FOUND',
            'message': 'Không tìm thấy DO hoặc xe của báo cáo sự cố.',
        })
    assigned = {order.vehicle_id} if order.vehicle_id else set()
    assigned.update(row.vehicle_id for row in db.query(TransportTrip).join(
        TripDeliveryOrder, TripDeliveryOrder.trip_id == TransportTrip.id
    ).filter(TripDeliveryOrder.do_id == order.id) if row.vehicle_id)
    if assigned and vehicle.id not in assigned:
        raise HTTPException(status_code=409, detail={
            'code': 'INCIDENT_VEHICLE_MISMATCH',
            'message': 'Xe không thuộc DO hoặc Trip của DO này. Vui lòng kiểm tra lại điều phối.',
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

# 10. Bang dieu khien — chi so tong quan. (Shipment 360 / dossier da xoa 10/09.)


@router.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Chi so Bang dieu khien, do truc tiep tu du lieu.

    DOANH THU = tong gia ban cuoi cua HO SO HOAN TAT (delivery_order_closeouts).
    Module hoa don AR da xoa (10/09): hoa don la viec cua he cong no cua dong
    nghiep, he nay ban giao ho so hoan tat. Khong con `booked_revenue_so` (SO da
    truc xuat) hay `recognized_revenue_ar`.
    """
    from services import lich_xe
    recognized_revenue = float(db.query(func.sum(DeliveryOrderCloseout.final_selling_price)).scalar() or 0)
    total_do = db.query(DeliveryOrder).count()
    # So LENH GIAO HANG dang lan banh, dem theo trang thai chuan.
    in_transit_orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.canonical_status.in_(("in_transit", "arrived"))
    ).count()
    # "So xe hoat dong" = xe dang trong doi (khong ngoai doi, khong nam xuong).
    active_vehicle_count = lich_xe.dem_xe_hoat_dong(db)
    incidents_count = db.query(Incident).count()
    return {
        "revenue_ytd": recognized_revenue,
        "recognized_revenue": recognized_revenue,
        "completed_deliveries": db.query(DeliveryOrderCloseout).count(),
        "total_deliveries": total_do,
        "in_transit_orders": in_transit_orders,
        "active_vehicles": active_vehicle_count,
        "incidents_count": incidents_count,
    }
