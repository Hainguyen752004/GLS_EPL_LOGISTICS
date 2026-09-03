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


@router.get("/api/incidents")
async def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).order_by(Incident.id.desc()).all()

@router.post("/api/incidents")
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


def _dossier_row(row):
    if row is None:
        return None
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }


@router.get("/api/delivery-orders/{delivery_order_id}/dossier")
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
