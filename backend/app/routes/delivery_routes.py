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


@router.get("/api/tracking/control-tower", summary="Bảng theo dõi chuyến, GPS, POD và sự cố")
def get_tracking_control_tower(db: Session = Depends(get_db)):
    """Đọc dữ liệu thật; thiếu GPS không loại chuyến khỏi bảng và không suy diễn ETA."""
    from services.tracking_control_service import control_tower
    return control_tower(db)


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


def _doc_so_tien(raw):
    """Đọc một con số tiền viết dưới dạng chuỗi, chấp nhận cả hai kiểu dấu.

    Dự án có cả `"6,250"` (dấu phẩy phân cách nghìn) và `"4.800"` (dấu chấm,
    kiểu Việt Nam). Bản trước chỉ bỏ dấu phẩy, nên `"4.800"` bị đọc thành 4,8
    — sai đúng 1000 lần, và con số ra vẫn trông như một con số thật.

    Quy tắc: dấu xuất hiện SAU CÙNG mà theo sau nó KHÔNG phải đúng ba chữ số
    thì đó là dấu thập phân; còn lại đều là dấu phân cách nghìn.
    """
    text = str(raw if raw is not None else "0").strip()
    if not text:
        return Decimal("0")
    text = text.replace(" ", "")
    cuoi_cham = text.rfind(".")
    cuoi_phay = text.rfind(",")
    vi = max(cuoi_cham, cuoi_phay)
    if vi >= 0 and len(text) - vi - 1 != 3:
        # Dấu cuối là dấu thập phân: bỏ mọi dấu khác, giữ dấu này thành ".".
        nguyen = text[:vi].replace(".", "").replace(",", "")
        le = text[vi + 1:]
        text = nguyen + "." + le if le else nguyen
    else:
        text = text.replace(".", "").replace(",", "")
    try:
        return Decimal(text or "0")
    except (ValueError, ArithmeticError):
        return Decimal("0")


# Cấu phần trong `terms` dùng khóa ngắn, còn `components` dùng khóa dài.
KHOA_TERM_SANG_COMPONENT = {"wh": "warehouse", "rate": "freight_rate"}


def _configured_delivery_cost_lines(formula, delivery_order, route):
    """Các dòng CHI PHÍ theo công thức giá thành của loại xe.

    Đọc tiền từ `terms[].rate` — đó là số học thực sự, kèm `factor` (đơn vị
    nhân) và `kind` (chi phí hay doanh thu). `components` chỉ là chuỗi ĐÃ
    ĐỊNH DẠNG để hiển thị: hai công thức trong cơ sở dữ liệu định dạng khác
    nhau (`"4.800"` và `"6,250"`), và nó còn lệch với số thật — công thức
    `DEMO-VT-20FT` ghi `components.fuel = "6,250"` trong khi `rate` là 4800.
    Nên `components` chỉ dùng làm phương án dự phòng cho công thức cũ chưa
    có `terms`.

    Cấu phần `kind == "revenue"` KHÔNG vào đây. `rate` (cước phí vận chuyển
    /kg) là tiền THU CỦA KHÁCH, không phải khoản chi; cộng chung thì con số
    ra không phải giá thành, cũng không phải giá bán.
    """
    if not isinstance(formula, dict):
        return []
    currency = str(formula.get("currency") or "VND")
    distance = Decimal(str(getattr(route, "distance_km", 0) or 0))
    weight = Decimal(str(getattr(delivery_order, "weight_kg", 0) or 0))

    def display(value):
        return f"{float(value):,.0f}".replace(",", ".")

    def display_quantity(value):
        number = float(value)
        if number.is_integer():
            return display(value)
        return f"{number:,.2f}".rstrip("0").rstrip(".").replace(",", ".")

    NHAN = {
        "per_km": (distance, lambda: f"{display_quantity(distance)} km"),
        "per_kg": (weight, lambda: f"{display_quantity(weight)} kg"),
        "per_trip": (Decimal("1"), lambda: "Theo chuyến"),
    }

    dong = []
    terms = formula.get("terms") if isinstance(formula.get("terms"), list) else []
    components = formula.get("components") if isinstance(
        formula.get("components"), dict) else {}

    for term in terms:
        if not isinstance(term, dict):
            continue
        if str(term.get("kind") or "cost").lower() == "revenue":
            continue          # tiền thu của khách, không phải khoản chi
        khoa = str(term.get("key") or "").strip()
        if not khoa:
            continue
        don_gia = _doc_so_tien(term.get("rate"))
        if don_gia <= 0:
            continue
        factor = str(term.get("factor") or "per_trip")
        so_luong, mo_ta = NHAN.get(factor, NHAN["per_trip"])
        thanh_tien = don_gia * so_luong
        dong.append({
            "code": KHOA_TERM_SANG_COMPONENT.get(khoa, khoa),
            "name": str(term.get("label") or khoa),
            "original_amount": float(thanh_tien.quantize(Decimal("0.000001"))),
            "calculation": (f"{mo_ta()} × {display(don_gia)} {currency}"
                            if factor != "per_trip"
                            else f"Theo chuyến × {display(don_gia)} {currency}"),
        })
    if dong:
        return dong

    # Dự phòng: công thức cũ chỉ có `components`, không có `terms`.
    CU = [
        ("fuel", "Chi phí xăng dầu", "per_km"),
        ("driver", "Phụ cấp chuyến tài xế", "per_trip"),
        ("toll", "Phí cầu đường / BOT", "per_trip"),
        ("warehouse", "Phí bãi và lưu kho", "per_trip"),
    ]
    for khoa, ten, factor in CU:
        don_gia = _doc_so_tien(components.get(khoa))
        if don_gia <= 0:
            continue
        so_luong, mo_ta = NHAN[factor]
        dong.append({
            "code": khoa,
            "name": ten,
            "original_amount": float((don_gia * so_luong).quantize(
                Decimal("0.000001"))),
            "calculation": (f"{mo_ta()} × {display(don_gia)} {currency}"
                            if factor != "per_trip"
                            else f"Theo chuyến × {display(don_gia)} {currency}"),
        })
    return dong

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
    # Chỉ đòi công thức khi còn phải TÍNH giá thành. DO đã giao xong thì hồ
    # sơ đã chốt, màn "Đã hoàn tất" chỉ xem lại — đòi công thức ở đó là chặn
    # một việc không cần đến nó, và hậu quả là không xem được hồ sơ của một
    # chuyến đã giao.
    con_phai_tinh = str(delivery_order.canonical_status or "").lower() not in (
        "delivered", "completed", "cancelled")
    if sales_order and delivery_order.vehicle_id and formula_row is None and con_phai_tinh:
        # Nói ĐÚNG cái đang thiếu. Xe chưa được gán loại xe thì có tạo bao
        # nhiêu công thức cũng không khớp được — mà lời báo cũ lại chỉ người
        # dùng đi tạo công thức, tức chỉ họ sửa đúng thứ không hỏng.
        vehicle = db.get(Vehicle, delivery_order.vehicle_id)
        if vehicle is None:
            raise HTTPException(status_code=409, detail={
                "code": "VEHICLE_NOT_FOUND",
                "message": f"Không tìm thấy phương tiện {delivery_order.vehicle_id} trong Dữ liệu gốc.",
                "vehicle_id": delivery_order.vehicle_id,
                "navigation_targets": ["master-data/vehicles"],
            })
        if not str(vehicle.type or "").strip():
            raise HTTPException(status_code=409, detail={
                "code": "VEHICLE_TYPE_REQUIRED",
                "message": (
                    f"Phương tiện {vehicle.id} chưa được gán loại xe, nên không tra được"
                    " công thức giá thành. Hãy mở Dữ liệu gốc → Phương tiện và chọn loại xe"
                    " cho xe này trước."
                ),
                "vehicle_id": vehicle.id,
                "navigation_targets": ["master-data/vehicles"],
            })
        raise HTTPException(status_code=409, detail={
            "code": "COST_FORMULA_REQUIRED",
            "message": (
                f"Chưa cấu hình giá thành {sales_order.currency_code} cho loại xe"
                f" \"{vehicle.type}\" (xe {vehicle.id}). Hãy mở Dữ liệu gốc → Công thức"
                " giá thành và thêm công thức cho loại xe này."
            ),
            "vehicle_id": vehicle.id,
            "vehicle_type": vehicle.type,
            "currency": sales_order.currency_code,
            "navigation_targets": ["master-data/vehicle-types", "master-data/vehicles"],
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
        # Hồ sơ là CHỨNG TỪ nên phải tự đủ. Màn "Hoàn tất giao hàng" lấy 18
        # ô thông tin DO từ bộ đệm của trình duyệt; hồ sơ thì không được
        # phụ thuộc vào đó — bộ đệm có thể trống (mở hồ sơ ngay sau khi tải
        # trang) hoặc đã cũ. Đọc lại từ cơ sở dữ liệu tại đây.
        "delivery_order": {
            "id": delivery_order.id,
            "canonical_status": delivery_order.canonical_status or "",
            "status": delivery_order.status or "",
            "so_id": delivery_order.so_id or "",
            "customer_id": delivery_order.customer_id or "",
            "route_id": delivery_order.route_id or "",
            "origin": delivery_order.origin or "",
            "destination": delivery_order.destination or "",
            "pickup_window_start": _iso_or_none(delivery_order.pickup_window_start),
            "pickup_window_end": _iso_or_none(delivery_order.pickup_window_end),
            "delivery_window_start": _iso_or_none(delivery_order.delivery_window_start),
            "delivery_window_end": _iso_or_none(delivery_order.delivery_window_end),
            "pickup_date": str(delivery_order.pickup_date or ""),
            "delivery_date": str(delivery_order.delivery_date or ""),
            "vehicle_id": delivery_order.vehicle_id or "",
            "driver_id": delivery_order.driver_id or "",
            "co_driver": delivery_order.co_driver or "",
            "weight_kg": _decimal_to_float(delivery_order.weight_kg),
            "pallet_count": delivery_order.pallet_count,
            "volume_m3": _decimal_to_float(delivery_order.volume_m3),
            "packaging_spec": delivery_order.packaging_spec or "",
        },
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
