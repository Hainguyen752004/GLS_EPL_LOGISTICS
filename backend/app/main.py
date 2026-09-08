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
from routes.finance_master_routes import router as finance_master_router
from routes.currency_routes import router as currency_router
from routes.currency_routes import _start_currency_reference_scheduler
from routes.master_data_routes import router as master_data_router
from routes.fleet_routes import router as fleet_router
from routes.delivery_routes import router as delivery_router
from routes.accounting_routes import router as accounting_router
from routes.operations_routes import router as operations_router
from routes.data_export_routes import router as data_export_router
from routes.ai_upload_routes import router as ai_upload_router
# Năm hàm phụ trợ dưới đây đã chuyển sang routes/shared.py vì nhiều nhóm route
# cùng dùng. Giữ tên cũ có dấu gạch dưới để không phải sửa toàn bộ chỗ gọi
# trong file này.
from routes.shared import (
    decimal_to_float as _decimal_to_float,
    iso_or_none as _iso_or_none,
    require_api_principal as _require_api_principal,
    safe_permissions as _safe_permissions,
    serialize_cost_formula as _serialize_cost_formula,
)
from routes.workflow_routes import router as workflow_router
from routes.bao_gia_routes import router as bao_gia_router
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
# currency_reference_* đã chuyển sang routes/currency_routes.py cùng phần
# lịch làm mới và các endpoint dùng chúng.
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

def _strict_startup():
    """Từ chối phục vụ khi migration lúc khởi động thất bại. MẶC ĐỊNH BẬT.

    Một instance có lược đồ không hợp lệ thì không nên tồn tại: nó qua được mọi
    probe của load balancer rồi 500 trên từng request nghiệp vụ.

    Trước đây đây là cơ chế bật tự nguyện, vì auto_migrate_db() thất bại trên
    đường khởi tạo mới — các migration lịch sử là lệnh *sửa* bảng nên không chạy
    được trên một database trắng. Nay database mới được dựng từ model rồi đánh
    mốc lịch sử (xem database._needs_baseline), nên khởi tạo chạy được ở mọi
    môi trường và fail-fast trở thành mặc định đúng đắn.

    Đặt EPL_ALLOW_DEGRADED_START=1 để vẫn khởi động khi cần vào chẩn đoán một
    instance có lược đồ lỗi.
    """
    return os.getenv("EPL_ALLOW_DEGRADED_START", "").strip().lower() not in {"1", "true", "yes"}


def _docs_enabled():
    """Tài liệu API chỉ mở khi được bật tường minh.

    Mở mặc định thì `/openapi.json` trao trọn danh mục endpoint cho người
    chưa xác thực. Bật bằng EPL_ENABLE_DOCS=1 khi phát triển cục bộ.
    """
    return os.getenv("EPL_ENABLE_DOCS", "").strip().lower() in {"1", "true", "yes"}


def _allowed_origins():
    """Danh sách origin cho CORS, đọc từ EPL_CORS_ORIGINS (phân tách bằng dấu phẩy).

    Không bao giờ trả về ["*"]: kết hợp với allow_credentials=True thì Starlette
    phản chiếu đúng origin của người gọi kèm Access-Control-Allow-Credentials,
    nên mọi website đều điều khiển được API từ trình duyệt nạn nhân.
    """
    raw = os.getenv("EPL_CORS_ORIGINS", "").strip()
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip()]
        if origins and "*" not in origins:
            return origins
    # Mặc định an toàn: chỉ chính máy chủ đang phục vụ frontend.
    return [
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]


app = FastAPI(
    title="EPL Logistics Enterprise System (Production 100% Real DB)",
    description="Hệ thống Quản lý Logistics EPL với CSDL PostgreSQL thực tế & AI Agents không bịa dữ liệu",
    version="3.0.0",
    docs_url="/docs" if _docs_enabled() else None,
    redoc_url="/redoc" if _docs_enabled() else None,
    openapi_url="/openapi.json" if _docs_enabled() else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
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

MAX_REQUEST_BODY_BYTES = int(os.getenv("EPL_MAX_REQUEST_BODY_BYTES", str(16 * 1024 * 1024)))
# Các đường upload tự có hạn mức riêng, rộng hơn hạn mức JSON chung.
_UPLOAD_PATH_PREFIXES = ("/api/uploads/", "/api/ai/checkpoint/", "/api/pod/")
MAX_UPLOAD_BODY_BYTES = int(os.getenv("EPL_MAX_UPLOAD_BODY_BYTES", str(256 * 1024 * 1024)))


# Giới hạn tần suất cho các đường tốn tài nguyên nhất. Đây là lớp phòng thủ
# BỔ SUNG, không thay thế reverse proxy: bộ đếm nằm trong bộ nhớ tiến trình nên
# với N worker thì hạn mức thực tế là N lần con số dưới đây, và nó mất khi
# khởi động lại. Hạn mức thật vẫn nên đặt ở nginx/gateway.
_RATE_LIMITED_PREFIXES = (
    "/api/agent/",              # gọi LLM, chạy trong threadpool
    "/api/v1/ai/chat",
    "/api/ai/checkpoint/",      # suy luận thị giác máy tính, có khóa toàn cục
    "/api/uploads/",            # ghi đĩa
)
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("EPL_RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("EPL_RATE_LIMIT_MAX_REQUESTS", "30"))
_rate_limit_hits = defaultdict(deque)
_rate_limit_lock = Lock()


def _rate_limit_key(request: Request):
    principal = getattr(request.state, "principal", None)
    if principal:
        return f"principal:{principal}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


def _rate_limit_exceeded(key: str, now: float) -> bool:
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_limit_lock:
        hits = _rate_limit_hits[key]
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_MAX_REQUESTS:
            return True
        hits.append(now)
        # Dọn các khóa đã hết hạn để bộ đếm không phình theo số IP từng gặp.
        if len(_rate_limit_hits) > 4096:
            for stale in [k for k, v in _rate_limit_hits.items() if not v]:
                del _rate_limit_hits[stale]
        return False


async def limit_expensive_endpoints(request: Request, call_next):
    """Chặn dồn dập vào các endpoint tốn tài nguyên."""
    if request.url.path.startswith(_RATE_LIMITED_PREFIXES):
        if _rate_limit_exceeded(_rate_limit_key(request), time.monotonic()):
            return JSONResponse(
                status_code=429,
                content={
                    "error": _error_payload(
                        "RATE_LIMIT_EXCEEDED",
                        "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.",
                    ),
                    "detail": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.",
                    },
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
    return await call_next(request)


async def limit_request_body(request: Request, call_next):
    """Từ chối request có thân quá lớn trước khi nó được đệm vào bộ nhớ.

    Trước đây chỉ hai đường upload có hạn mức, còn mọi endpoint Body(...) khác
    nhận JSON không giới hạn — nên một POST 500 MB là đủ làm cạn RAM. Đây là
    chốt phòng thủ trong ứng dụng; reverse proxy vẫn nên đặt client_max_body_size
    của riêng nó, vì Content-Length có thể bị khai sai.
    """
    path = request.url.path
    limit = (
        MAX_UPLOAD_BODY_BYTES
        if path.startswith(_UPLOAD_PATH_PREFIXES)
        else MAX_REQUEST_BODY_BYTES
    )
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > limit:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": _error_payload(
                            "REQUEST_BODY_TOO_LARGE",
                            "Dữ liệu gửi lên vượt quá giới hạn cho phép.",
                        ),
                        "detail": {
                            "code": "REQUEST_BODY_TOO_LARGE",
                            "message": "Dữ liệu gửi lên vượt quá giới hạn cho phép.",
                        },
                    },
                )
        except ValueError:
            pass  # Content-Length không hợp lệ: để tầng ASGI xử lý.
    return await call_next(request)


# Middleware đăng ký sau sẽ chạy TRƯỚC. Thứ tự thực thi mong muốn:
#   limit_request_body → tms_bearer_auth → limit_expensive_endpoints
# nên đăng ký theo chiều ngược lại. Rate limit đặt SAU xác thực để đếm theo
# principal khi có, thay vì gộp mọi người dùng sau cùng một NAT vào một IP.
app.middleware("http")(limit_expensive_endpoints)
app.middleware("http")(tms_bearer_auth)
app.middleware("http")(limit_request_body)
app.include_router(health_router)
# Router này tự mang dependency xác thực ở tầng router — xem
# routes/finance_master_routes.py để biết vì sao nhóm endpoint này cần lớp thứ hai.
app.include_router(finance_master_router)
# Cũng mang dependency xác thực ở tầng router: tỷ giá ghi ở đây thắng mọi
# nguồn khác khi quy đổi tiền tệ. Xem routes/currency_routes.py.
app.include_router(currency_router)
app.include_router(master_data_router)
app.include_router(fleet_router)
app.include_router(delivery_router)
app.include_router(accounting_router)
app.include_router(operations_router)
app.include_router(data_export_router)
# ai_upload_router KHÔNG gắn dependency ở tầng router vì GET /uploads/ phải
# công khai cho thẻ <img src>. Xem routes/ai_upload_routes.py.
app.include_router(ai_upload_router)
app.include_router(bao_gia_router)
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
        startup_logger.error(
            "Database startup failed code=DATABASE_STARTUP_UNAVAILABLE correlation_id=%s",
            correlation_id,
        )
        # Mức log là ERROR chứ không phải WARNING: hạ xuống warning là lý do lỗi
        # này nằm im suốt. Với EPL_STRICT_STARTUP=1 thì tiến trình từ chối phục
        # vụ hẳn — xem _strict_startup() để biết vì sao đó chưa thể là mặc định.
        if _strict_startup():
            raise
    _start_currency_reference_scheduler()

# ==========================================
# UNIFIED AI GATEWAY (Single Endpoint)
# ==========================================

# Trợ lý AI, upload ảnh và quét checkpoint đã chuyển sang routes/ai_upload_routes.py.

# Xe, loại xe, phiếu sửa chữa, công thức chi phí và tài xế đã chuyển sang routes/fleet_routes.py.

# Tracking và chốt giá lệnh giao hàng đã chuyển sang routes/delivery_routes.py.

# Hóa đơn, sổ cái và chỉ số bảng điều khiển đã chuyển sang routes/accounting_routes.py.

# Sự cố và hồ sơ lệnh giao hàng đã chuyển sang routes/operations_routes.py.

# Endpoint /api/data/all đã chuyển sang routes/data_export_routes.py.

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
        # Không bao giờ phát EPL_TMS_API_TOKEN vào HTML: `GET /` là đường công
        # khai, nên làm vậy là trao bí mật của server cho khách vãng lai và vô
        # hiệu hóa toàn bộ lớp phân quyền phía sau. Frontend tự lấy token từ
        # localStorage (xem financeAuthHeaders trong frontend/js/app.js).
        return _frontend_html_response(content)
    return _frontend_html_response(f"<h1>Không tìm thấy index.html tại {index_path}</h1>", status_code=404)
