"""Theo dõi hành trình và chốt giá lệnh giao hàng.

Endpoint chốt giá dài hơn 200 dòng: nó tổng hợp công thức chi phí, phụ phí,
chứng từ POD và giá bán cuối. Tách riêng để main.py không phải ôm nó.
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


@router.get("/api/tracking/{do_id}")
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
        return {"id": "", "name": "", "currency": "VND", "components": {}, "terms": []}
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


@router.get("/api/delivery-orders/{do_id}/closeout")
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
