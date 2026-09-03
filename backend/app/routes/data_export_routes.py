"""Ảnh chụp toàn bộ dữ liệu cho giao diện: GET /api/data/all.

Một endpoint duy nhất nhưng dài 360 dòng — nó tuần tự hóa gần như mọi bảng cho
frontend nạp một lần khi khởi động. Tách riêng vì nó không liên quan gì tới các
nhóm nghiệp vụ khác trong main.py.

Endpoint này cố tình BÔI TRẮNG các tập dữ liệu nhạy cảm (invoices, ap_invoices,
settlements, users, audit_logs). Lưu ý: biện pháp đó chỉ có nghĩa khi các đường
trực tiếp tới cùng dữ liệu cũng được bảo vệ ngang nhau — trước đây chúng không,
nên lớp che này từng vô nghĩa.
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


@router.get("/api/data/all")
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


# Bốn hàm phụ trợ cho master-data (_parse_iso_datetime, _parse_iso_date,
# _clean_master_string, _master_saved) đã chuyển sang
# routes/finance_master_routes.py cùng các endpoint dùng chúng — không chỗ
# nào khác trong main.py cần tới.


# Các endpoint /api/master-data/* đã chuyển sang routes/finance_master_routes.py.
# Đây là dữ liệu ĐIỀU KHIỂN của nghiệp vụ tài chính — kỳ kế toán, mã thuế,
# ánh xạ tài khoản GL — và cả 12 endpoint từng không kiểm quyền một dòng nào,
# trong khi chính nghiệp vụ dùng chúng lại được gác rất kỹ. Đặt chúng trên một
# router có dependency xác thực ở tầng router khiến việc gác quyền là thuộc
# tính CẤU TRÚC, không còn phụ thuộc vào việc từng hàm có tự gọi hay không.


# Dynamic Frontend Directory Resolution
