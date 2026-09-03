"""Hóa đơn công nợ, sổ cái, và chỉ số Bảng điều khiển.

Nhóm này đọc và ghi số liệu tài chính, nên router mang dependency xác thực ở
tầng router.

Lưu ý về /api/dashboard/stats: nó trả về HAI chỉ tiêu doanh thu riêng biệt —
booked_revenue_so (đơn hàng đã ký) và recognized_revenue_ar (hóa đơn đã ghi
sổ). Trước đây nó trả max() của hai con số khác bản chất rồi gắn nhãn "doanh thu
hóa đơn thực tế", nên Bảng điều khiển và màn Phân tích hiện hai số lệch nhau.
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


@router.get("/api/invoices")
async def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(ARInvoice).filter(ARInvoice.is_active.is_(True)).order_by(
        ARInvoice.created_at.desc(), ARInvoice.id.desc()
    ).limit(100).all()
    return [serialize_ar_invoice(invoice) for invoice in invoices]

@router.get("/api/gl-transactions")
async def list_gl_transactions(db: Session = Depends(get_db)):
    return db.query(GLTransaction).limit(100).all()

@router.post("/api/invoices/post")
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
@router.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    # Hai chỉ tiêu khác bản chất, phải trả về riêng:
    #   booked_revenue_so   = tổng giá trị đơn hàng đã ký (doanh thu ký kết)
    #   recognized_revenue_ar = tổng hóa đơn đã ghi sổ (doanh thu ghi nhận)
    # Trước đây chỗ này lấy max(so_sum, inv_sum) — một phép tính không có ý
    # nghĩa kế toán nào — rồi gắn nhãn "Doanh thu hóa đơn thực tế (AR)". Kết
    # quả là hai con số doanh thu lệch nhau hiển thị cách nhau vài trăm pixel
    # trên cùng một trang, vì màn Tóm tắt lấy số ghi sổ từ endpoint khác.
    booked_revenue_so = db.query(func.sum(SalesOrder.total_amount)).scalar() or 0.0
    recognized_revenue_ar = db.query(func.sum(ARInvoice.total)).scalar() or 0.0
    total_rev = recognized_revenue_ar

    total_do = db.query(DeliveryOrder).count()

    # Số LỆNH GIAO HÀNG đang lăn bánh — không phải số xe. Tên cũ
    # "active_vehicles" khiến giao diện gắn giá trị này vào nhãn "Số Xe Hoạt
    # Động", và nó trông hợp lý chỉ vì đội xe demo tình cờ cũng có 3 chiếc.
    in_transit_orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.status.in_(["In Transit", "Đang vận chuyển", "Ready for Dispatch", "Sẵn sàng điều phối"])
    ).count()

    active_vehicle_count = db.query(Vehicle).filter(
        Vehicle.status.in_(["In Transit", "Đang vận chuyển", "Bận", "Sẵn sàng", "Ready"])
    ).count()

    incidents_count = db.query(Incident).count()

    # Đã dỡ phần tính monthly_pl cùng total_invoice_amount và
    # total_shipment_cost: cả ba được tính rồi không ai đọc. monthly_pl từng
    # nuôi một khối biểu đồ luôn ở trạng thái hidden với canvas không có id,
    # nên chưa bao giờ vẽ được. Cùng ba chuỗi doanh thu / chi phí / lợi nhuận
    # đó đã có biểu đồ đang CHẠY THẬT ở workspace Phân tích, lấy từ
    # /api/tms/reporting/transport-revenue — nên nối thêm ở đây chỉ tạo ra một
    # nguồn số thứ hai để lệch nhau, đúng vấn đề vừa phải đi sửa.

    return {
        # revenue_ytd giờ là doanh thu ĐÃ GHI SỔ, khớp với
        # /api/tms/reporting/transport-revenue thay vì mâu thuẫn với nó.
        "revenue_ytd": total_rev,
        "booked_revenue_so": booked_revenue_so,
        "recognized_revenue_ar": recognized_revenue_ar,
        "total_deliveries": total_do,
        "in_transit_orders": in_transit_orders,
        "active_vehicles": active_vehicle_count,
        "incidents_count": incidents_count,
    }

# 10. Incident Management API
