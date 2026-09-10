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
    Vehicle, Driver, Route, Warehouse, Customer, DeliveryOrder,
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


def _khoan_muc_tu(khoa, ten):
    """Mã KHOẢN MỤC chuẩn cho một cấu phần công thức.

    Nạp trong hàm chứ không ở đầu tệp, để không tạo vòng nạp giữa `routes` và
    nạp nó ở tầng module sẽ tạo một vòng nạp với `routes`.
    """
    from services.khoan_muc_chi_phi import khoan_muc_tu
    return khoan_muc_tu(khoa, ten)


def _configured_delivery_cost_lines(formula, delivery_order, route, ghi_de_theo_xe=None):
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
    if formula.get("expressions"):
        from services.cost_expression import evaluate_expressions
        try:
            segments = json.loads(getattr(route, 'segments_json', None) or '[]')
            if any(__import__('re').search(r'\bvalue\b', e) for e in formula['expressions'].values()):
                raise ValueError('Thiếu giá trị hàng để tính công thức.')
            if not segments and any(__import__('re').search(r'\blegs\b', e) for e in formula['expressions'].values()):
                raise ValueError('Tuyến chưa có dữ liệu số chặng.')
            result = evaluate_expressions(formula["expressions"], formula.get("terms") or [],
                                          {"km": float(distance), "tonnes": float(weight)/1000, "legs": len(segments) or 1})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Công thức giá thành không hợp lệ: {exc}") from exc
        return [{"code": "formula_cost", "name": "Giá thành theo công thức",
                 "original_amount": result["cost"], "calculation": formula["expressions"]["COST"]}]

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
        # PHÍ CỦA XE: xe chạy chuyến có ghi đè đơn giá cho khoản mục này thì
        # dùng đơn giá của xe (xe cũ tốn dầu hơn, xe trả góp gánh khấu hao).
        # Khoản mục và mã costindex vẫn kế thừa từ loại xe — ghi đè chỉ đổi SỐ.
        # Ghi rõ nguồn để người đọc hồ sơ biết con số này là của xe hay của loại.
        ghi_de = (ghi_de_theo_xe or {}).get(khoa)
        nguon_don_gia = "vehicle_type"
        if ghi_de is not None:
            don_gia = _doc_so_tien(ghi_de)
            nguon_don_gia = "vehicle"
        if don_gia <= 0:
            continue
        factor = str(term.get("factor") or "per_trip")
        so_luong, mo_ta = NHAN.get(factor, NHAN["per_trip"])
        thanh_tien = don_gia * so_luong
        dong.append({
            "code": KHOA_TERM_SANG_COMPONENT.get(khoa, khoa),
            "key": khoa,
            # MÃ COSTINDEX của EPL — do người làm tài chính đặt trên công thức,
            # hệ công nợ đọc mã này để lập phiếu. Rỗng = công thức chưa gán mã.
            "cost_index": str(term.get("cost_index") or "").strip(),
            "rate_source": nguon_don_gia,
            "unit_rate": float(don_gia),
            # MÃ KHOẢN MỤC dùng chung với `actual_cost_lines[].charge_type`.
            #
            # `code` ở trên là mã CẤU PHẦN của công thức giá thành, và nó KHÁC
            # bộ mã của bảng chi phí thực tế: cùng "Phí bãi & lưu kho" mà một
            # bên ghi `warehouse`, bên kia ghi `yard`. Ai đọc gói này để hạch
            # toán sẽ ánh xạ theo một danh sách rồi lệch danh sách kia — và
            # lệch im lặng, vì cả hai mã đều "trông đúng".
            #
            # `khoan_muc_tu` là MỘT nguồn duy nhất cho phép ánh xạ đó, dùng
            # chung với bảng chi phí thực tế. Giữ cả `code` để không làm vỡ
            # chỗ nào đang đọc nó.
            "charge_type": _khoan_muc_tu(khoa, str(term.get("label") or khoa)),
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
            "key": khoa,
            "charge_type": _khoan_muc_tu(khoa, ten),
            # Công thức cũ dạng `components` không có chỗ ghi mã costindex.
            "cost_index": "",
            "rate_source": "vehicle_type",
            "unit_rate": float(don_gia),
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

    # BÁO GIÁ: đọc từ CHÍNH lệnh giao hàng (`quotation_id`). Bước Đơn hàng (SO)
    # đã trục xuất khỏi hệ thống ở migration 049 — không còn đường tra nào khác.
    # Đã đo trên dữ liệu thật: `commercials.quoted_cost = 0` cho một lệnh đã
    # giao mà báo giá của nó ghi giá thành 2.409.255 đ. Giá thành bằng 0 thì lãi
    # gộp hiện ra 98,56% — con số đầu tiên người xem nhìn vào, và nó sai.
    #
    # `delivery_order.quotation_id` được gán ngay lúc tách, nên đó là đường
    # đúng; đường qua Đơn hàng giữ lại cho dữ liệu cũ.
    quotation = None
    if getattr(delivery_order, "quotation_id", None):
        quotation = db.get(Quotation, delivery_order.quotation_id)
    route = db.get(Route, delivery_order.route_id) if delivery_order.route_id else None
    # Tien te cua ho so: theo Don hang (du lieu cu) hoac theo BAO GIA (luong moi).
    # Truyen None la de `_select_closeout_formula` chon cong thuc dau tien theo ten
    # — voi loai xe co ca hai cong thuc USD/VND thi no chon USD, va mot DO bao gia
    # VND hien "1.118.000 USD". Da do duoc tren du lieu demo (DO-2026-0010).
    tien_te_nguon = quotation.currency_code if quotation else None
    formula_row = _select_closeout_formula(db, delivery_order, tien_te_nguon)
    # Chỉ đòi công thức khi còn phải TÍNH giá thành. DO đã giao xong thì hồ
    # sơ đã chốt, màn "Đã hoàn tất" chỉ xem lại — đòi công thức ở đó là chặn
    # một việc không cần đến nó, và hậu quả là không xem được hồ sơ của một
    # chuyến đã giao.
    con_phai_tinh = str(delivery_order.canonical_status or "").lower() not in (
        "delivered", "completed", "cancelled")
    if quotation and delivery_order.vehicle_id and formula_row is None and con_phai_tinh:
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
                f"Chưa cấu hình giá thành {tien_te_nguon or 'VND'} cho loại xe"
                f" \"{vehicle.type}\" (xe {vehicle.id}). Hãy mở Dữ liệu gốc → Công thức"
                " giá thành và thêm công thức cho loại xe này."
            ),
            "vehicle_id": vehicle.id,
            "vehicle_type": vehicle.type,
            "currency": tien_te_nguon or "VND",
            "navigation_targets": ["master-data/vehicle-types", "master-data/vehicles"],
        })
    formula = _serialize_closeout_formula(formula_row)
    # Ghi đè đơn giá theo XE chạy chuyến (bảng `vehicle_cost_overrides`), để
    # dòng chi phí trong hồ sơ là phí của CHIẾC XE này, không chỉ chuẩn của loại.
    ghi_de_theo_xe = {}
    if delivery_order.vehicle_id:
        from services.vehicle_cost_service import list_overrides
        ghi_de_theo_xe = {r["component"]: r["value"]
                          for r in list_overrides(db, delivery_order.vehicle_id)}
    configured_cost_lines = _configured_delivery_cost_lines(
        formula, delivery_order, route, ghi_de_theo_xe)

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
                # Mã costindex ghi trên dòng lúc chốt chi phí; dòng cũ chưa có
                # thì tra lại từ công thức theo `charge_type` ở bước lập sổ.
                "cost_index": item.cost_index or "",
                "description": item.description or "",
                "quantity": _decimal_to_float(item.quantity),
                "unit_price": _decimal_to_float(item.unit_price),
                "total_amount": _decimal_to_float(item.total_amount),
                # BA CON SỐ TIỀN THẬT, thiếu chúng thì gói này vô dụng với ai
                # đọc để hạch toán.
                #
                # `total_amount`, `unit_price` và `net_amount` của bảng chi phí
                # thực tế đều mang PHẦN VƯỢT (`increase_amount`), không mang
                # chi phí — đó là chủ ý của bảng đó: nó nói về CHÊNH LỆCH so
                # với kế hoạch. Nhưng gói closeout trước đây chỉ trả ba con số
                # ấy, nên bên đọc thấy 0 đồng cho một chuyến có chi phí thật
                # 2.271.600 đ, và không có gì trong gói cho biết vì sao.
                #
                # Đã đo: một lệnh giao hàng đã giao trả về `total_amount = 0`
                # cho cả bốn khoản mục, trong khi `original_amount` mới là tiền.
                "original_amount": _decimal_to_float(item.original_amount),
                "actual_amount": _decimal_to_float(item.actual_amount),
                "increase_amount": _decimal_to_float(item.increase_amount),
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
                "cost_index": row.cost_index or "",
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
    selling_price = _decimal_to_float(quotation.selling_price if quotation is not None else None)
    actual_total = _decimal_to_float(actual_cost.total_amount if actual_cost else None)
    quoted_cost = _decimal_to_float(quotation.total_cost if quotation else None)

    # GIÁ THÀNH lấy từ `actual_amount` CỦA TỪNG DÒNG, không lấy tổng của bảng.
    #
    # LỖI ĐÃ ĐO ĐƯỢC: lãi gộp hiện 98,56%. Bản trước viết
    # `cost_basis = actual_total or quoted_cost`, tức lấy `actual_cost.total_amount`
    # làm giá thành. Nhưng cột đó KHÔNG CÓ MỘT NGHĨA DUY NHẤT — nó là tổng của
    # `item.total_amount`, và `item.total_amount` mang hai nghĩa khác nhau tuỳ
    # đường nào tạo ra dòng đó:
    #
    #   · đường CHỐT GIÁ (`tms_cost_service`, dòng ~145) ghi `total_amount = increase`
    #     — tức PHẦN VƯỢT so với kế hoạch;
    #   · đường THÊM KHOẢN PHÍ (`add_charge_item`) ghi `total_amount` là tiền
    #     ĐẦY ĐỦ của dòng (số lượng × đơn giá, có thuế).
    #
    # Nên cùng một cột, một bộ dữ liệu cho ra 51.963 (phần vượt) và một bộ khác
    # cho ra 2.380.000 (chi phí thật). Lấy nó làm giá thành thì đúng ở một bộ và
    # sai ở bộ kia — và ở bộ demo thật nó cho ra lãi gộp 98,56%.
    #
    # `item.actual_amount` thì CHỈ CÓ MỘT NGHĨA: chi phí thực tế của dòng. Đường
    # chốt giá đặt nó đúng; đường thêm khoản phí không đặt (để 0), nên khi cả
    # bảng đều 0 thì lùi về tổng của bảng — đúng cho cả hai hình dạng dữ liệu.
    #
    # Đây là CÙNG MỘT LỖI đã sửa ở `tms_reporting_service` — báo cáo doanh thu
    # cũng từng hiện lãi gộp 99% vì lấy chênh lệch làm tổng. Sửa một chỗ mà
    # không soi chỗ còn lại thì lỗi vẫn sống ở màn khác, và đó là chuyện đã xảy ra.
    tong_thuc_te = 0.0
    if actual_cost:
        tong_thuc_te = sum(_decimal_to_float(it.actual_amount) for it in actual_cost.items)
    if tong_thuc_te > 0:
        cost_basis = tong_thuc_te
    elif actual_total > 0:
        cost_basis = actual_total
    else:
        # Chưa có bảng chi phí thực tế: dùng KẾ HOẠCH. Báo giá trước, rồi tới
        # tổng các dòng chi phí theo công thức — chính con số màn hình đang
        # hiện, nên hai bên không lệch nhau.
        cost_basis = quoted_cost or sum(
            float(x.get("original_amount") or 0) for x in (configured_cost_lines or []))

    # HAI CON SỐ TỔNG PHẢI NÓI ĐÚNG TÊN CỦA CHÚNG.
    #
    # LỖI ĐÃ ĐO ĐƯỢC trên dữ liệu thật (DO-2026-0001-DO01): gói này trả
    # `actual_cost_total = 17.227 đ` cho một chuyến có chi phí thực tế
    # 1.731.767 đ. Sai 100 lần, và sai IM LẶNG — vì `freight_actual_costs.
    # total_amount` là tổng của `item.total_amount`, mà cột đó ở đường CHỐT GIÁ
    # mang PHẦN VƯỢT chứ không mang chi phí (xem chú thích ngay trên).
    #
    # Nặng hơn: sau khi `cost_basis` được sửa để lấy từ `item.actual_amount`,
    # hai con số trong CÙNG MỘT GÓI tự chống nhau — `margin_amount` là
    # 934.233 = 2.666.000 − 1.731.767, trong khi `actual_cost_total` ghi
    # 17.227. Ai đọc gói này để hạch toán sẽ lập phiếu chi 17.227 đ cho một
    # chuyến tốn 1.731.767 đ, và không có gì trong gói cho biết vì sao.
    #
    # Nên: `actual_cost_total` = chi phí thực tế (chính `cost_basis` khi đã có
    # bảng chi phí), còn phần vượt được trả RIÊNG dưới tên đúng của nó.
    tong_chi_phi_thuc_te = tong_thuc_te if tong_thuc_te > 0 else actual_total
    phan_vuot_so_ke_hoach = actual_total if tong_thuc_te > 0 else 0.0

    # ======================= SỔ THU – CHI TỪNG DÒNG (`ledger_lines`) =======================
    #
    # ĐÂY LÀ THỨ ĐỒNG NGHIỆP CỦA CHỦ DỰ ÁN (anh Khang) ĐỌC ĐỂ LẬP PHIẾU. Yêu cầu
    # nguyên văn: *"chi tiết từng dòng luôn — chi tiết từng cái chi cái thu … đem
    # mấy cái phí của xe các thứ ra luôn"*. Vài con số tổng (giá SO, giá cuối,
    # chi phí, margin) không lập được phiếu; phải là TỪNG DÒNG, mỗi dòng mang MÃ
    # COSTINDEX của hệ kế toán bên đó.
    #
    # Mỗi dòng: `kind` (thu | chi), `cost_index`, `charge_type`, `name`,
    # `planned_amount` (chốt ban đầu), `actual_amount` (thực tế),
    # `customer_extra` (khách trả thêm), `variance` (thực tế − ban đầu), `source`.
    #
    # Ba nguồn gộp về một sổ:
    #   · CHI theo công thức (`configured_cost_lines`) — đơn giá đã áp ghi đè của
    #     xe chạy chuyến, nên đây là "phí của xe";
    #   · CHI thực tế (`actual_cost_lines`) — ghép vào dòng công thức cùng
    #     `charge_type`; dòng thực tế không có dòng công thức tương ứng thì đứng
    #     riêng (khoản phát sinh);
    #   · THU: cước cơ sở theo báo giá, và từng khoản khách trả thêm.
    #
    # Mã costindex thiếu trên dòng (dữ liệu cũ) thì tra lại từ công thức theo
    # `charge_type` / tên. Vẫn thiếu thì để RỖNG và `missing_cost_index = True` —
    # nói ra là "chưa gán mã", không bịa.
    from services.khoan_muc_chi_phi import (
        TEN_KHOAN_MUC, bang_costindex, costindex_cho, khoan_muc_tu)
    bang_ma = bang_costindex((formula or {}).get("terms"))

    def _ma(dong, khoa=None, charge_type=None, ten=None):
        return (str(dong.get("cost_index") or "").strip()
                or costindex_cho(bang_ma, khoa=khoa, charge_type=charge_type, ten=ten)
                or "")

    # Điền mã cho các dòng chi phí thực tế ghi TRƯỚC khi có cột `cost_index`
    # (dữ liệu cũ, NULL) — ngay trong `actual_cost_lines`, không chỉ trong sổ,
    # vì bên đọc có thể đọc thẳng mảng này. Ghi rõ mã đến từ đâu: `stored` là
    # mã đã ghi trên dòng lúc chốt, `formula` là mã tra lại từ công thức.
    for a in actual_cost_lines:
        if str(a.get("cost_index") or "").strip():
            a["cost_index_source"] = "stored"
        else:
            a["cost_index"] = costindex_cho(bang_ma, charge_type=a["charge_type"],
                                            ten=a.get("description")) or ""
            a["cost_index_source"] = "formula" if a["cost_index"] else "missing"

    so_dong = []
    da_ghep = set()
    # Đã có bảng chi phí thực tế hay chưa quyết định cách đọc một dòng công
    # thức KHÔNG có dòng thực tế tương ứng:
    #   · chưa có bảng  -> chưa ai chốt gì, thực tế TẠM = kế hoạch (tạm tính);
    #   · đã có bảng    -> người chốt đã ghi mọi khoản thực chi; khoản không có
    #                     trong bảng là KHÔNG phát sinh -> thực tế = 0, và dòng
    #                     vẫn hiện với "chốt ban đầu" để thấy nó đã rơi đi đâu.
    # Lấy kế hoạch làm thực tế ở trường hợp hai là cộng thêm một khoản không ai
    # chi vào tổng chi — sổ lệch khỏi giá thành đúng bằng khoản đó, và
    # `khop_gia_thanh` đỏ. Đã đo trên bộ demo: phí bãi 200.000 không có trong
    # bảng chi phí thực tế làm tổng chi 2.580.000 trong khi giá thành 2.380.000.
    co_bang_thuc_te = bool(actual_cost_lines)
    for c in configured_cost_lines or []:
        ct = c.get("charge_type") or khoan_muc_tu(c.get("key"), c.get("name"))
        thuc = next((a for a in actual_cost_lines
                     if a["charge_type"] == ct and a["id"] not in da_ghep), None)
        if thuc:
            da_ghep.add(thuc["id"])
        ke_hoach = float(c.get("original_amount") or 0)
        thuc_te = (float(thuc["actual_amount"]) if thuc
                   else (0.0 if co_bang_thuc_te else ke_hoach))
        ma = _ma(c, khoa=c.get("key"), charge_type=ct, ten=c.get("name")) \
            or (_ma(thuc, charge_type=ct, ten=thuc.get("description")) if thuc else "")
        so_dong.append({
            "kind": "chi", "cost_index": ma, "missing_cost_index": not ma,
            "charge_type": ct, "name": c.get("name") or TEN_KHOAN_MUC.get(ct, ct),
            "planned_amount": ke_hoach, "actual_amount": thuc_te,
            "variance": thuc_te - ke_hoach, "customer_extra": 0.0,
            "source": "vehicle" if c.get("rate_source") == "vehicle" else "cost_formula",
            "calculation": c.get("calculation") or "",
            "actual_cost_line_id": thuc["id"] if thuc else "",
        })
    for a in actual_cost_lines or []:
        if a["id"] in da_ghep:
            continue
        ma = _ma(a, charge_type=a["charge_type"], ten=a.get("description"))
        so_dong.append({
            "kind": "chi", "cost_index": ma, "missing_cost_index": not ma,
            "charge_type": a["charge_type"],
            "name": a.get("description") or TEN_KHOAN_MUC.get(a["charge_type"], a["charge_type"]),
            "planned_amount": float(a["original_amount"] or 0),
            "actual_amount": float(a["actual_amount"] or 0),
            "variance": float(a["actual_amount"] or 0) - float(a["original_amount"] or 0),
            "customer_extra": 0.0, "source": "actual_cost", "calculation": "",
            "actual_cost_line_id": a["id"],
        })

    gia_ban_goc = _decimal_to_float(closeout.base_selling_price_snapshot) if closeout else selling_price
    gia_ban_cuoi = _decimal_to_float(closeout.final_selling_price) if closeout else selling_price
    # Cước cơ sở: mã costindex của khoản mục DOANH THU trong công thức (`rate`).
    ma_cuoc = ""
    for t in (formula or {}).get("terms") or []:
        if isinstance(t, dict) and str(t.get("kind") or "").lower() == "revenue":
            ma_cuoc = str(t.get("cost_index") or "").strip()
            if ma_cuoc:
                break
    so_dong.append({
        "kind": "thu", "cost_index": ma_cuoc, "missing_cost_index": not ma_cuoc,
        "charge_type": "freight_revenue", "name": "Cước vận chuyển theo báo giá",
        "planned_amount": gia_ban_goc, "actual_amount": gia_ban_goc,
        "variance": 0.0, "customer_extra": 0.0,
        "source": "quotation" if quotation else "delivery_order",
        "calculation": (quotation.id if quotation else ""), "actual_cost_line_id": "",
    })
    for kt in customer_adjustments or []:
        ct = khoan_muc_tu(None, kt.get("name"))
        ma = _ma(kt, charge_type=ct, ten=kt.get("name"))
        so_dong.append({
            "kind": "thu", "cost_index": ma, "missing_cost_index": not ma,
            "charge_type": ct, "name": kt.get("name") or "",
            "planned_amount": float(kt.get("original_amount") or 0),
            "actual_amount": float(kt.get("actual_amount") or 0),
            "variance": float(kt.get("increase_amount") or 0),
            "customer_extra": float(kt.get("increase_amount") or 0),
            "source": "customer_surcharge", "calculation": kt.get("note") or "",
            "actual_cost_line_id": "",
        })

    # Tên bên công nợ dùng là ACC CODE; `cost_index` là tên cột trong hệ này.
    # Trả cả hai khoá, cùng một giá trị, để bên đọc dùng tên quen của họ.
    for d in so_dong:
        d["acc_code"] = d["cost_index"]
    for danh_sach in (configured_cost_lines, actual_cost_lines, customer_adjustments):
        for d in danh_sach or []:
            d["acc_code"] = d.get("cost_index") or ""

    tong_thu = sum(d["actual_amount"] if d["source"] != "customer_surcharge" else d["customer_extra"]
                   for d in so_dong if d["kind"] == "thu")
    tong_chi = sum(d["actual_amount"] for d in so_dong if d["kind"] == "chi")
    tong_so = {
        "tong_thu": tong_thu,
        "tong_chi": tong_chi,
        "lai_gop": tong_thu - tong_chi,
        # Hai phép đối chiếu, để bên đọc KIỂM được sổ chứ không phải tin nó:
        # tổng THU của sổ phải bằng giá cuối DO, tổng CHI phải bằng giá thành
        # dùng tính lãi. Lệch là có dòng bị sót hoặc đếm hai lần.
        "khop_gia_cuoi": abs(tong_thu - gia_ban_cuoi) < 1.0,
        "khop_gia_thanh": abs(tong_chi - cost_basis) < 1.0 if cost_basis else True,
        "so_dong_thieu_ma": sum(1 for d in so_dong if d["missing_cost_index"]),
        "currency": (closeout.currency_code if closeout else None)
                    or (actual_cost.currency_code if actual_cost else None)
                    or tien_te_nguon or (formula or {}).get("currency") or "VND",
    }
    currency = (
        (closeout.currency_code if closeout else None)
        or
        (actual_cost.currency_code if actual_cost else None)
        or tien_te_nguon
        or formula.get("currency")
        or "VND"
    )

    return {
        "do_id": delivery_order.id,
        "status": delivery_order.canonical_status or delivery_order.status or "",
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
            "actual_cost_total": tong_chi_phi_thuc_te,
            # Mẫu số của `margin_percent`, trả ra để bên đọc kiểm được con số
            # lãi chứ không phải tin nó. Thiếu nó thì một chênh lệch giữa
            # `actual_cost_total` và giá thành dùng để tính lãi là vô hình.
            "cost_basis": cost_basis,
            "cost_basis_source": ("actual_cost_items" if tong_thuc_te > 0
                                  else "actual_cost_total" if actual_total > 0
                                  else "quotation" if quoted_cost else "cost_formula"),
            "actual_cost_variance": phan_vuot_so_ke_hoach,
            "selling_price": _decimal_to_float(closeout.final_selling_price) if closeout else selling_price,
            "base_selling_price": _decimal_to_float(closeout.base_selling_price_snapshot) if closeout else selling_price,
            "base_price_source": closeout.base_price_source if closeout else "quotation",
            "base_price_source_id": closeout.base_price_source_id if closeout else (quotation.id if quotation else ""),
            "customer_surcharge_total": _decimal_to_float(closeout.surcharge_total) if closeout else 0.0,
            "final_selling_price": _decimal_to_float(closeout.final_selling_price) if closeout else selling_price,
            "margin_amount": (_decimal_to_float(closeout.final_selling_price) if closeout else selling_price) - cost_basis,
            "margin_percent": round((((_decimal_to_float(closeout.final_selling_price) if closeout else selling_price) - cost_basis) / (_decimal_to_float(closeout.final_selling_price) if closeout else selling_price)) * 100, 2) if (_decimal_to_float(closeout.final_selling_price) if closeout else selling_price) else 0.0,
            "margin_is_provisional": actual_cost is None,
        },
        "customer_charge_adjustments": customer_adjustments,
        # Sổ thu–chi từng dòng, mỗi dòng mang mã costindex — gói cho hệ công nợ.
        "ledger_lines": so_dong,
        "ledger_totals": tong_so,
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
            # Chi phí THỰC TẾ, không phải phần vượt — xem chú thích ở chỗ tính
            # `tong_chi_phi_thuc_te`.
            "total_amount": tong_chi_phi_thuc_te,
            "variance_amount": phan_vuot_so_ke_hoach,
            # Tổng thô của bảng, giữ lại để đối chiếu khi nghi số lệch. Đây
            # CHÍNH LÀ con số từng bị trả ra dưới tên `total_amount`.
            "table_total_amount": actual_total,
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
