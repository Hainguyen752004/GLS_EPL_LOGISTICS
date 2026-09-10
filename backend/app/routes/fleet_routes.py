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
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.append(app_dir)

from database import get_db
from models import (Location, 
    Vehicle, Driver, Route, Warehouse, Customer, DeliveryOrder,
    DeliveryOrderDetail, ShipmentCost, VehicleTracking, POD, DeliveryPODRecord, ARInvoice,
    GLTransaction, AuditLog, Quotation, Incident, TaxCode, AccountingPeriod,
    AccountMapping, Carrier, Tender, TenderOffer, FreightOrder, TransportTrip,
    TransportEvent, ResourceAssignment, TripDeliveryOrder, TransportTripLeg,
    FreightActualCost, FreightChargeItem, APInvoice, FreightSettlement,
    CurrencyDefinition, CurrencyRateHistory, Role, User, CostFormula, DeliveryOrderCloseout,
    DeliveryOrderChargeAdjustment, DeliveryPODDocument, VehicleMaintenanceRequest,
    FreightOrderLegacyLink, DriverShiftAssignment, DriverQualification,
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
    list_requests_in_period as list_vehicle_maintenance_in_period,
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


from services import vehicle_cost_service

router = APIRouter(dependencies=[Depends(require_api_principal)])


#: Loai dia diem duoc coi la BAI / CHI NHANH — noi xe dau va nhan su thuoc ve.
#: `Waypoint` va `RoutePoint` la diem tren tuyen, khong phai bai.
LOAI_BAI = ("Depot", "Branch", "Warehouse", "Yard")


@router.get("/api/depots")
async def list_depots(db: Session = Depends(get_db)):
    """Danh muc BAI / CHI NHANH, doc tu bang `locations`.

    VI SAO CO. O "Bai / Chi nhanh" va "Ma bai" tren ho so xe truoc day la HAI O GO
    TU DO, khong co danh muc nao dung sau. Man Dieu phoi gom doi xe "theo bai"
    bang chinh chuoi nguoi ta go — go lech mot chu la thanh hai bai. Bang
    `locations` da co san (kho, chi nhanh, cang) nen bai la mot LOAI dia diem,
    khong phai mot chuoi rieng. Moi xe / tai xe chon bai tu day.
    """
    from models import Location
    from sqlalchemy import func as _f
    rows = db.query(Location).filter(Location.type.in_(LOAI_BAI)).order_by(Location.name).all()
    so_xe = dict(db.query(Vehicle.depot_code, _f.count(Vehicle.id))
                 .filter(Vehicle.depot_code.isnot(None)).group_by(Vehicle.depot_code).all())
    so_tx = dict(db.query(Driver.depot_code, _f.count(Driver.id))
                 .filter(Driver.depot_code.isnot(None)).group_by(Driver.depot_code).all())
    return [{
        "id": r.id, "name": r.name, "type": r.type, "address": r.address,
        "vehicle_count": int(so_xe.get(r.id, 0)), "driver_count": int(so_tx.get(r.id, 0)),
    } for r in rows]


@router.post("/api/depots")
async def create_depot(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Them / sua mot bai. `id` la ma bai (dung de loc), `name` la ten hien."""
    _require_api_principal(request)
    from models import Location
    ma = str(data.get("id") or "").strip()
    ten = str(data.get("name") or "").strip()
    if not ma or not ten:
        raise HTTPException(status_code=422, detail={
            "code": "DEPOT_ID_NAME_REQUIRED", "message": "Bãi cần cả mã (để lọc) và tên (để hiện)."})
    loai = str(data.get("type") or "Depot").strip()
    if loai not in LOAI_BAI:
        raise HTTPException(status_code=422, detail={
            "code": "DEPOT_TYPE_INVALID",
            "message": "Loại bãi phải là một trong: %s." % ", ".join(LOAI_BAI)})
    r = db.get(Location, ma)
    if r is None:
        r = Location(id=ma)
        db.add(r)
    r.name = ten
    r.type = loai
    if data.get("address") is not None:
        r.address = str(data.get("address") or "")
    db.commit()
    return {"message": "Đã lưu bãi %s." % ma, "data": {"id": r.id, "name": r.name, "type": r.type}}


def loai_xe_cua(gia_tri):
    """Tra ban ghi VehicleType theo MA hoac TEN (xe cu con luu ten). Cache theo phien goi."""
    from models import VehicleType
    from database import SessionLocal
    chu = str(gia_tri or "").strip()
    if not chu:
        return None
    with SessionLocal() as db:
        r = db.get(VehicleType, chu)
        if r is None:
            r = db.query(VehicleType).filter(func.lower(VehicleType.name) == chu.lower()).first()
        if r is not None:
            db.expunge(r)
        return r


@router.get("/api/vehicles")
async def list_vehicles(
    paginated: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    depot_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Vehicle).order_by(Vehicle.id.desc())
    # Loc bai ngay o may chu. O doi 500 xe, keo het ve roi loc bang JavaScript
    # la keo ve 500 ban ghi de dung 40 — bai la bo loc thuong dung nhat.
    if depot_code:
        query = query.filter(Vehicle.depot_code == depot_code.strip().upper())
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
        # MA CHUAN tu lich (moc 045): available | on_trip | maintenance |
        # out_of_service. Chu hien ra do lang.json quyet theo ma — khong gui nhan
        # tieng Viet cung nua. `operational_status_label` giu cho cho cu, chieu
        # tu cung mot ma.
        from services import lich_xe
        ma, ref = lich_xe.trang_thai_xe_theo_lich(db, vehicle, now)
        payload["operational_status"] = ma
        payload["operational_ref"] = ref
        payload["operational_note"] = vehicle.operational_note
        payload["operational_status_label"] = lich_xe._nhan(lich_xe.NHAN_XE, ma, ref)
        # LOAI XE: xe luu MA loai (sau khi POST chuan hoa), xe cu co the con TEN.
        # Tra ca hai de giao dien hien TEN va chon theo MA — khong doan tu chuoi.
        loai = loai_xe_cua(vehicle.type)
        payload["vehicle_type_id"] = loai.id if loai else None
        payload["vehicle_type_name"] = loai.name if loai else (vehicle.type or None)
        # BAI: ten hien thi lay tu danh muc dia diem theo ma bai, neu co.
        bai = db.get(Location, vehicle.depot_code) if vehicle.depot_code else None
        payload["depot_name"] = (bai.name if bai else None) or vehicle.depot or None
        result.append(payload)
    if paginated:
        return {"items": result, "page": page, "page_size": page_size, "total": total}
    return result

@router.post("/api/vehicles")
async def create_vehicle(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Tạo mới hoặc cập nhật một xe.

    Chỉ ghi những trường THẬT SỰ CÓ trong payload.

    Bản trước dựng một đối tượng Vehicle mới với mọi trường lấy từ
    `data.get(..., mặc_định)` rồi `db.merge()`. Nghĩa là sửa một xe mà không gửi
    kèm một trường nào đó thì trường đó **bị xóa trắng** — thử trên máy chủ:
    sửa `brand` và `weight_capacity` của một xe đã có bãi "Bãi Sóng Thần" thì
    bãi biến thành NULL, không một thông báo nào.

    Ở đội 500 xe, đó là mất dữ liệu thầm lặng: sửa tải trọng một xe là mất luôn
    thông tin bãi của xe đó.
    """
    _require_api_principal(request)
    vid = data.get("id")
    if not vid:
        raise HTTPException(status_code=400, detail="Thiếu Biển số xe")

    existing = db.get(Vehicle, vid)
    veh = existing or Vehicle(id=vid, status="Sẵn sàng")
    if existing is None:
        db.add(veh)

    def _first_key(*names):
        """Tên trường nào có mặt trong payload — hỗ trợ cả snake_case lẫn camelCase."""
        for name in names:
            if name in data:
                return name
        return None

    def _text(field, *names, default=""):
        name = _first_key(*names)
        if name is None:
            # Xe mới thì đặt mặc định; xe đã có thì GIỮ NGUYÊN giá trị cũ.
            if existing is None:
                setattr(veh, field, default)
            return
        setattr(veh, field, data.get(name) or "")

    def _number(field, *names, default=0.0, cast=float):
        name = _first_key(*names)
        if name is None:
            if existing is None:
                setattr(veh, field, cast(default))
            return
        try:
            setattr(veh, field, cast(data.get(name) or 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Giá trị {name} không hợp lệ") from None

    _text("brand", "brand", default="Hyundai")
    _text("type", "type", default="")

    # `type` PHẢI là MÃ loại xe có thật khi danh mục loại xe đã có.
    #
    # Lỗi đã gặp trên dữ liệu thật: hai xe ghi "Container 20FT" (TÊN hiển thị)
    # thay vì "DEMO-VT-20FT" (MÃ). Mọi phép tra theo mã, nên hai xe đó không khớp
    # loại nào — điều phối không so được năng lực, giá thành không tìm được công
    # thức — và không có thông báo nào, vì chuỗi nào cũng lưu được. Nhận cả TÊN
    # rồi tự đổi về MÃ (người nhập tay hay gõ tên), còn chuỗi không khớp gì thì
    # 422 kèm danh mục để chọn. Danh mục còn trống (đang dựng dữ liệu gốc) thì cho
    # qua — lúc đó chưa có gì để đối chiếu.
    if "type" in data and str(veh.type or "").strip():
        from models import VehicleType
        cac_loai = db.query(VehicleType).all()
        if cac_loai:
            chu = str(veh.type).strip()
            khop = next((t for t in cac_loai if t.id == chu), None) \
                or next((t for t in cac_loai if str(t.name or "").strip().lower() == chu.lower()), None)
            if khop is None:
                raise HTTPException(status_code=422, detail={
                    "code": "VEHICLE_TYPE_UNKNOWN",
                    "message": (f"Loại xe \"{chu}\" không có trong danh mục Loại phương tiện. "
                                "Chọn một mã loại xe có thật, hoặc thêm loại xe trước."),
                    "vehicle_types": [{"id": t.id, "name": t.name} for t in cac_loai],
                    "navigation_targets": ["master-data/vehicle-types"],
                })
            veh.type = khop.id
    _number("weight_capacity", "weight_capacity", "weightCapacity", "maxWeight")
    _number("volume_capacity_m3", "volume_capacity_m3", "volumeCapacityM3", default=30.0)
    _number("pallet_capacity", "pallet_capacity", "palletCapacity", default=0, cast=int)
    _number("fuel_norm", "fuel_norm", "fuelNorm")
    _number("avg_speed_kmh", "avg_speed_kmh", "avgSpeedKmh", default=45.0)
    _number("min_speed_kmh", "min_speed_kmh", "min_speed")
    _number("max_speed_kmh", "max_speed_kmh", "max_speed")
    for field in ("maintenance_date", "engine_no", "chassis_no", "insurance_date",
                  "inspection_date", "inspection_place", "inspection_exp",
                  "engine_cap", "dimensions", "image_url"):
        _text(field, field)
    _text("depot", "depot")

    # Mã bãi luôn chuẩn hóa về chữ in, vì nó là khóa lọc.
    if "depot_code" in data:
        veh.depot_code = (str(data.get("depot_code") or "").strip().upper() or None)
    elif existing is None:
        veh.depot_code = None
    # Chuỗi rỗng lưu thành NULL cho hai cột bãi, để bộ lọc "chưa gán bãi" đúng.
    if not (veh.depot or "").strip():
        veh.depot = None

    db.commit()
    return {"message": "Cập nhật dữ liệu xe thành công", "data": veh}


@router.get("/api/vehicle-maintenance-requests")
async def get_vehicle_maintenance_requests_in_period(
    start: str = Query(..., description="Dau khoang, dang ISO co mui gio"),
    end: str = Query(..., description="Cuoi khoang, dang ISO co mui gio"),
    db: Session = Depends(get_db),
):
    """Bao duong cua MOI xe co giao voi mot khoang thoi gian.

    Duong theo tung xe ben duoi khong dung duoc cho man xep lich: he thong
    chay o quy mo ~500 xe, tuc 500 lan goi cho mot tuan lich.
    """
    try:
        items = list_vehicle_maintenance_in_period(db, start, end)
        return {"data": [serialize_vehicle_maintenance_request(item) for item in items]}
    except DomainError as error:
        raise_http(error)


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
    # Truoc day khong tim thay thi ham roi xuong `return {"message": "Đã xóa
    # phương tiện"}` o cuoi — nguoi dung go nham mot bien so, bam Xoa, va nhan
    # mot loi khang dinh SAI trong khi khong co gi bi xoa.
    if not veh:
        raise HTTPException(status_code=404, detail={
            "code": "VEHICLE_NOT_FOUND",
            "message": f"Không tìm thấy phương tiện {vid}.",
        })
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

# 1.5 Vehicle Types API
@router.get("/api/vehicles/{vehicle_id}/cost")
async def get_vehicle_effective_cost(vehicle_id: str, db: Session = Depends(get_db)):
    """Gia thanh THUC TE cua mot chiec xe: cong thuc loai xe + phan ghi de.

    Tra ve ca `inherited` lan `is_overridden` cho tung cau phan, de giao dien
    noi ro con so nao la ke thua va con so nao bi doi — thay vi hien mot day so
    ma khong ai biet no tu dau ra.
    """
    try:
        return {"data": vehicle_cost_service.effective_cost(db, vehicle_id)}
    except DomainError as error:
        raise_http(error)


@router.put("/api/vehicles/{vehicle_id}/cost-overrides")
async def put_vehicle_cost_overrides(
    vehicle_id: str,
    request: Request,
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    """Ghi lai toan bo phan ghi de cua mot xe.

    Gui mang rong nghia la "xe nay quay ve ke thua hoan toan tu loai xe".
    """
    actor = _require_api_principal(request)
    try:
        result = vehicle_cost_service.replace_overrides(db, vehicle_id, data.get("overrides"), str(actor))
        db.commit()
        return {"message": "Da cap nhat ghi de gia thanh cho xe.", "data": result}
    except DomainError as error:
        db.rollback()
        raise_http(error)


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
    """Xoa mot loai xe khoi Master Data.

    Truoc day co hai cho sai:

      1. Khong tim thay thi tra ve `{"message": "Không tìm thấy loại phương
         tiện"}` voi MA TRANG THAI 200. Giao dien kiem `res.ok`, thay 200, va
         bao "da xoa" — than phan hoi noi mot dieu, ma trang thai noi dieu
         nguoc lai, va giao dien tin ma trang thai.

      2. Khong kiem dang-su-dung. `Vehicle.type` doi chieu voi loai xe, nen xoa
         mot loai xe ma doi xe con thuoc loai do la lam phep tra tai trong va
         gia thanh mat nguon — am tham, khong mot loi bao nao.

      3. LOI THU BA, do do bang bo kiem sau khi `POST /api/vehicles` bat dau
         CHUAN HOA `type` ve MA loai xe (`veh.type = khop.id`): cua chan nay
         chi so theo TEN, nen voi moi xe tao sau thay doi do no khong khop gi
         ca va loai xe bi xoa tu do — dung lo hong ma no duoc dung de bit.
         Phai so CA HAI: ma (xe moi) va ten (xe cu, tao truoc khi chuan hoa).
    """
    _require_api_principal(request)
    from models import VehicleType
    vt = db.query(VehicleType).filter(VehicleType.id == vid).first()
    if not vt:
        raise HTTPException(status_code=404, detail={
            "code": "VEHICLE_TYPE_NOT_FOUND",
            "message": f"Không tìm thấy loại phương tiện {vid}.",
        })

    dang_dung = db.query(Vehicle.id).filter(or_(
        func.lower(Vehicle.type) == str(vt.id or "").lower(),
        func.lower(Vehicle.type) == str(vt.name or "").lower(),
    )).first()
    if dang_dung:
        raise HTTPException(status_code=409, detail={
            "code": "LOCKED_RECORD",
            "message": (
                "Còn phương tiện đang thuộc loại \"%s\", không được xóa loại xe này."
                " Hãy đổi loại cho các xe đó trước." % vt.name
            ),
            "navigation_targets": ["master-data/vehicles"],
        })

    db.delete(vt)
    db.commit()
    return {"message": f"Đã xóa loại phương tiện {vid}"}

# 1.6 Cost Formula API


#: API danh mục ACC CODE của bên công nợ (anh Khang) — Golden SME.
#:
#:   EPL_ACC_CODE_API     : gốc API (vd https://demo-lao-api.goldensme.com) HOẶC đường
#:                          đầy đủ tới /api/v1/common/country-accounts.
#:   EPL_ACC_CODE_TOKEN   : JWT Bearer bên đó cấp. KHÔNG ghi vào mã nguồn.
#:   EPL_ACC_CODE_COUNTRY : `tryAutoId` — mã quốc gia trong PUBCOUNTRY (Lào = 11).
#:
#: Không đặt EPL_ACC_CODE_API thì ô chọn trên màn Công thức giá thành ở trạng
#: thái CHỜ — không có tuỳ chọn nào, không tự sinh mã. Chủ dự án chốt: mã do bên
#: kia cấp. Danh mục ~500 dòng, đổi hiếm, nên giữ trong bộ nhớ 10 phút.
BIEN_API_ACC_CODE = "EPL_ACC_CODE_API"
BIEN_TOKEN_ACC_CODE = "EPL_ACC_CODE_TOKEN"
BIEN_QUOC_GIA_ACC_CODE = "EPL_ACC_CODE_COUNTRY"
DUONG_COUNTRY_ACCOUNTS = "/api/v1/common/country-accounts"
_BO_NHO_ACC_CODE = {"khoa": None, "luc": 0.0, "goi": None}
ACC_CODE_CACHE_GIAY = 600


def _url_acc_code():
    goc = (os.getenv(BIEN_API_ACC_CODE) or "").strip()
    if not goc:
        return ""
    if "country-accounts" in goc:
        url = goc
    else:
        url = goc.rstrip("/") + DUONG_COUNTRY_ACCOUNTS
    quoc_gia = (os.getenv(BIEN_QUOC_GIA_ACC_CODE) or "11").strip()
    if "tryAutoId=" not in url:
        url += ("&" if "?" in url else "?") + "tryAutoId=%s" % quoc_gia
    if "onlyActive=" not in url:
        url += "&onlyActive=true"
    return url


def _chuan_hoa_acc_code(goi):
    """Đưa gói của bên công nợ về danh sách {code, name, description, parent, postable}.

    Hai hình gói được nhận:
      · Golden SME: {"Success", "Result": [{"AccCode", "AccName", "AccDescription",
        "AccParentId", "AccAccountWrite", "AccIsActive"}, ...]}
      · dạng chung {"data": [{"code","name"} | "6421" ...]} — giữ cho bộ kiểm cũ.
    `name` là tên tài khoản (tiếng Lào theo bên đó), `description` là diễn giải
    tiếng Việt; màn hiện cả hai vì người dùng đọc tiếng Việt nhưng mã phải khớp
    tên của hệ kế toán bên kia.
    """
    if isinstance(goi, dict) and isinstance(goi.get("Result"), list):
        ket = []
        for x in goi["Result"]:
            if not isinstance(x, dict):
                continue
            ma = str(x.get("AccCode") or "").strip()
            if not ma:
                continue
            ket.append({
                "code": ma,
                "name": str(x.get("AccName") or "").strip() or ma,
                "description": str(x.get("AccDescription") or "").strip(),
                "parent": (str(x.get("AccParentId")).strip() if x.get("AccParentId") not in (None, "") else None),
                "postable": bool(x.get("AccAccountWrite")),
                "active": bool(x.get("AccIsActive", True)),
            })
        return ket
    ds = goi.get("data") if isinstance(goi, dict) else goi
    ket = []
    for x in (ds if isinstance(ds, list) else []):
        if isinstance(x, str):
            ket.append({"code": x.strip(), "name": x.strip()})
        elif isinstance(x, dict):
            ma = str(x.get("code") or x.get("acc_code") or x.get("id") or "").strip()
            if ma:
                ket.append({"code": ma, "name": str(x.get("name") or x.get("label") or ma)})
    return ket


@router.get("/api/acc-codes")
async def danh_muc_acc_code(request: Request, refresh: bool = False):
    """Danh mục Acc code (mã tài khoản kế toán) cho ô chọn của từng khoản mục.

    Trả `{"data": [...], "source", "message", "count"}`. `source` là `remote`
    khi lấy được từ API bên công nợ, `cached` khi lấy từ bộ nhớ, `unconfigured`
    khi chưa nối, `error` khi nối mà không đọc được — các trạng thái này phải
    phân biệt được trên màn hình, vì "danh mục rỗng" và "chưa nối API" là hai
    câu khác nhau với người dùng.
    """
    _require_api_principal(request)
    url = _url_acc_code()
    if not url:
        return {"data": [], "source": "unconfigured", "count": 0,
                "message": "Chưa nối API mã tài khoản của bên công nợ (đặt %s)." % BIEN_API_ACC_CODE}
    import time as _time
    bo = _BO_NHO_ACC_CODE
    if (not refresh and bo["goi"] is not None and bo["khoa"] == url
            and _time.time() - bo["luc"] < ACC_CODE_CACHE_GIAY):
        return {"data": bo["goi"], "source": "cached", "count": len(bo["goi"]),
                "message": "Danh mục %d mã (bộ nhớ, tối đa 10 phút)." % len(bo["goi"])}
    try:
        import json as _json
        import urllib.request as _ur
        dau = {"Accept": "application/json"}
        token = (os.getenv(BIEN_TOKEN_ACC_CODE) or "").strip()
        if token:
            dau["Authorization"] = "Bearer " + token
        with _ur.urlopen(_ur.Request(url, headers=dau), timeout=15) as tra:
            goi = _json.loads(tra.read().decode("utf-8", "replace"))
    except Exception as loi:  # noqa: BLE001 — mọi lỗi mạng/định dạng đều là "không đọc được"
        # Không lộ token trong thông điệp lỗi.
        return {"data": [], "source": "error", "count": 0,
                "message": "Không đọc được danh mục Acc code từ API bên công nợ: %s"
                           % str(loi).replace(token or "\x00", "***")[:160]}
    if isinstance(goi, dict) and goi.get("Success") is False:
        return {"data": [], "source": "error", "count": 0,
                "message": "API bên công nợ từ chối: %s" % str(goi.get("Message") or goi.get("Code"))[:160]}
    ket = _chuan_hoa_acc_code(goi)
    bo["khoa"], bo["luc"], bo["goi"] = url, _time.time(), ket
    return {"data": ket, "source": "remote", "count": len(ket), "message": "Đã tải %d mã." % len(ket)}


@router.get("/api/cost-formulas")
async def list_cost_formulas(db: Session = Depends(get_db)):
    return [
        _serialize_cost_formula(row)
        for row in db.query(CostFormula).order_by(CostFormula.id).all()
    ]


@router.get("/api/cost-formulas/fleet-overview")
async def cost_formula_fleet_overview(request: Request, db: Session = Depends(get_db)):
    """Dữ liệu giá hiệu lực và lịch sử ghi đè để so sánh loại xe/xe."""
    _require_api_principal(request)
    return {'data': vehicle_cost_service.fleet_overview(db)}


def _sanitize_formula_terms(rows):
    """Lam sach danh sach hang tu cua cong thuc dong truoc khi ghi vao JSON.

    Chi giu dung nhung khoa minh biet, va chan he so / dau la — de mot payload
    bat ky khong ghi duoc thuoc tinh tuy y vao co so du lieu.
    """
    if not isinstance(rows, list):
        return []
    factors = {"per_km", "per_kg", "per_tonne", "per_trip", "per_stop"}
    operators = {"add", "sub"}
    # Loai cua cau phan: tien CHI ra hay tien THU cua khach. Bon cau phan dau
    # (xang dau, phu cap, BOT, phi bai) la chi phi, cuoc phi theo kg la gia
    # ban. Cong ca nam vao mot con so thi ket qua khong phai gia thanh cung
    # khong phai gia ban.
    kinds = {"cost", "revenue"}
    # Nam cau phan dung san co loai von co cua chung. Cong thuc luu TRUOC khi
    # co truong nay thi khong khai loai, nen phai suy ra theo khoa — neu khong
    # thi `rate` bi xep thanh chi phi va gia thanh cao gap gan bon lan.
    builtin_kinds = {
        "fuel": "cost", "driver": "cost", "toll": "cost", "wh": "cost",
        "rate": "revenue",
    }
    clean = []
    for index, row in enumerate(rows[:30]):
        if not isinstance(row, dict):
            continue
        try:
            rate = float(str(row.get("rate") or 0).replace(",", "").strip() or 0)
        except (TypeError, ValueError):
            rate = 0.0
        key = str(row.get("key") or f"term_{index + 1}")[:64]
        kind = row.get("kind")
        if kind not in kinds:
            # Mac dinh an toan la chi phi: nham mot khoan chi thanh doanh thu
            # se lam loi nhuan trong ra cao hon thuc te.
            kind = builtin_kinds.get(key, "cost")
        clean.append({
            "key": key,
            "label": str(row.get("label") or "")[:120],
            "operator": row.get("operator") if row.get("operator") in operators else "add",
            "factor": row.get("factor") if row.get("factor") in factors else "per_trip",
            "kind": kind,
            "rate": max(0.0, rate),
            "builtin": bool(row.get("builtin")),
            # MA COSTINDEX — ma phan loai chi phi cua EPL, do nguoi lam tai chinh
            # tu dat cho tung khoan muc (vi du "CP-XD-01"). Ma nay di theo khoan
            # muc suot luong: cong thuc -> bao gia -> chi phi thuc te cua chuyen
            # -> ho so hoan tat, va he cong no cua dong nghiep doc no de lap
            # phieu thu / phieu chi. Khong co no thi ben kia phai doan theo ten.
            "cost_index": str(row.get("cost_index") or "").strip()[:32],
        })
    return clean


@router.post("/api/cost-formulas/evaluate")
async def evaluate_cost_formula(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    _require_api_principal(request)
    from services.cost_expression import evaluate_expressions
    formula_id = str(data.get("formula_id") or "")
    if formula_id:
        row = db.get(CostFormula, formula_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy công thức.")
        formula = _serialize_cost_formula(row)
    else:
        formula = data
    try:
        result = evaluate_expressions(formula.get("expressions") or {},
                                      _sanitize_formula_terms(formula.get("terms")), data.get("trip") or {})
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": result}


@router.post("/api/cost-formulas")
async def save_cost_formula(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    actor = _require_api_principal(request)
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
        # Cong thuc DONG: danh sach hang tu (dau, don gia, he so nhan). Cho phep
        # them cau phan tuy chinh va phep tru, nen khong the goi gon vao
        # "components" voi nam khoa co dinh.
        "terms": _sanitize_formula_terms(data.get("terms")),
    }
    # ACC CODE DUNG CHUNG THEO KHOAN MUC: dong chua co ma thi ke thua tu Mapping tai khoan;
    # dong co ma thi ghi vao bang chung va lan sang cong thuc cua loai xe khac (chi dong
    # trong hoac dang theo ma chung cu). Xem services/acc_code_chung.py.
    from services import acc_code_chung
    _bang_chung = acc_code_chung.bang_chung(db)
    acc_code_chung.ke_thua(payload["terms"], _bang_chung)
    if data.get("expressions") is not None:
        from services.cost_expression import evaluate_expressions
        expressions = data["expressions"]
        if not isinstance(expressions, dict) or set(expressions) != {"COST", "REV", "PROFIT"}:
            raise HTTPException(status_code=422, detail="Cần đủ công thức Giá thành, Cước và Lợi nhuận.")
        try:
            evaluate_expressions(expressions, payload["terms"])
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        payload["expressions"] = expressions
    from datetime import datetime, timezone
    previous = db.get(CostFormula, formula_id)
    previous_raw = previous.formula_expression if previous else None
    try:
        previous_payload = json.loads(previous_raw or '{}')
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Công thức cũ không đọc được. Chưa thay đổi dữ liệu.")
    if not isinstance(previous_payload, dict):
        raise HTTPException(status_code=422, detail="Công thức cũ không đúng cấu trúc.")
    if ('expected_updated_at' in data
            and data['expected_updated_at'] != previous_payload.get('updated_at')):
        raise HTTPException(status_code=409, detail="Bộ giá đã được người khác thay đổi. Hãy tải lại trước khi lưu.")
    history = previous_payload.get('history', [])
    payload['updated_at'] = datetime.now(timezone.utc).isoformat()
    payload['history'] = ([{'at': payload['updated_at'], 'terms': payload['terms'],
                           'expressions': payload.get('expressions'), 'currency': currency,
                           'actor': str(actor)}] + (history if isinstance(history, list) else []))[:100]
    values = {'name': str(data.get("name") or formula_id).strip(),
              'formula_expression': json.dumps(payload, ensure_ascii=False)}
    from sqlalchemy.exc import IntegrityError
    try:
        acc_code_chung.ghi_nhan_va_lan(db, payload["terms"], formula_id, _bang_chung)
        if previous:
            # Compare the original document inside the UPDATE, not only in Python.
            changed = db.query(CostFormula).filter(
                CostFormula.id == formula_id, CostFormula.formula_expression == previous_raw
            ).update(values, synchronize_session=False)
            if changed != 1:
                db.rollback()
                raise HTTPException(status_code=409, detail="Bộ giá vừa thay đổi. Chưa ghi đè dữ liệu mới.")
        else:
            db.add(CostFormula(id=formula_id, **values))
        db.commit()
        db.expire_all()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bộ giá vừa được tạo ở phiên khác. Hãy tải lại.") from exc
    saved = db.get(CostFormula, formula_id)
    return {"message": "Đã lưu công thức giá thành vào CSDL.", "data": _serialize_cost_formula(saved)}

# 2. Drivers API
@router.get("/api/drivers")
async def list_drivers(db: Session = Depends(get_db)):
    from services import lich_xe
    now = datetime.now(timezone.utc)
    ra = []
    for nguoi in db.query(Driver).all():
        payload = jsonable_encoder(nguoi)
        ma, ref = lich_xe.trang_thai_tai_xe_theo_lich(db, nguoi, now)
        payload["operational_status"] = ma
        payload["operational_ref"] = ref
        payload["operational_status_label"] = lich_xe._nhan(lich_xe.NHAN_TAI_XE, ma, ref)
        ra.append(payload)
    return ra


@router.put("/api/vehicles/{vehicle_id}/operational-status")
async def dat_trang_thai_xe(vehicle_id: str, request: Request,
                            data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Nguoi dung dat tay trang thai van hanh cua xe.

    Chi nhan `available` (dua lai hoat dong) va `out_of_service` (dua ra khoi
    doi, kem ly do). `on_trip` / `maintenance` do lich quyet — khong dat tay.
    """
    _require_api_principal(request)
    from services import lich_xe
    from services.errors import DomainError, raise_http
    try:
        xe = lich_xe.dat_trang_thai_xe(db, vehicle_id, str(data.get("status") or "").strip(),
                                       data.get("note") or "")
        db.commit()
        db.refresh(xe)
    except DomainError as loi:
        db.rollback()
        raise_http(loi)
    return {"message": "Đã cập nhật trạng thái vận hành của xe %s: %s." % (xe.id, xe.operational_status),
            "data": {"id": xe.id, "operational_status": xe.operational_status,
                     "operational_ref": xe.operational_ref, "operational_note": xe.operational_note,
                     "operational_updated_at": xe.operational_updated_at}}


@router.put("/api/drivers/{driver_id}/operational-status")
async def dat_trang_thai_tai_xe(driver_id: str, request: Request,
                                data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """Nguoi dung dat tay trang thai nhan su: `available` / `off_duty` / `inactive`."""
    _require_api_principal(request)
    from services import lich_xe
    from services.errors import DomainError, raise_http
    try:
        nguoi = lich_xe.dat_trang_thai_tai_xe(db, driver_id, str(data.get("status") or "").strip(),
                                              data.get("note") or "")
        db.commit()
        db.refresh(nguoi)
    except DomainError as loi:
        db.rollback()
        raise_http(loi)
    return {"message": "Đã cập nhật trạng thái của nhân sự %s: %s." % (nguoi.id, nguoi.operational_status),
            "data": {"id": nguoi.id, "operational_status": nguoi.operational_status,
                     "operational_ref": nguoi.operational_ref, "operational_note": nguoi.operational_note,
                     "operational_updated_at": nguoi.operational_updated_at}}

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
    """Xoa mot tai xe khoi Master Data.

    Truoc day ham nay co ba cho sai, va ca ba deu im lang:

      1. KHONG tim thay thi van tra ve "Đã xóa nhân sự". Nguoi dung doc thay
         "da xoa" trong khi khong co gi bi xoa ca — go nham mot ma tai xe la
         nhan duoc mot loi khang dinh sai.
      2. Khong tim ra theo ma thi TIM THEO TEN. `DELETE /api/drivers/Nguyễn
         Văn A` xoa theo ho ten, va `.first()` chon tuy y mot nguoi khi hai
         tai xe trung ten. Mot thao tac xoa khong duoc phep doan.
      3. Khong kiem dang-su-dung, khac han `delete_vehicle` ngay ben tren von
         kiem rat can than tham chieu DO/Trip/Tracking. Xoa mot tai xe dang
         chay chuyen la de lai tham chieu mo coi trong DO, Trip, ca lam viec
         va POD — hoac vo o tang khoa ngoai.
    """
    _require_api_principal(request)
    drv = db.query(Driver).filter(Driver.id == did).first()
    if not drv:
        raise HTTPException(status_code=404, detail={
            "code": "DRIVER_NOT_FOUND",
            "message": f"Không tìm thấy nhân sự {did}.",
        })

    in_use = any([
        db.query(DeliveryOrder.id).filter(DeliveryOrder.driver_id == did).first(),
        db.query(DeliveryPODRecord.id).filter(DeliveryPODRecord.driver_id == did).first(),
        db.query(TransportTrip.id).filter(
            (TransportTrip.driver_id == did) | (TransportTrip.co_driver_id == did)
        ).first(),
        db.query(ResourceAssignment.id).filter(
            (ResourceAssignment.driver_id == did) | (ResourceAssignment.co_driver_id == did)
        ).first(),
        db.query(DriverShiftAssignment.id).filter(
            DriverShiftAssignment.driver_id == did
        ).first(),
        db.query(DriverQualification.driver_id).filter(
            DriverQualification.driver_id == did
        ).first(),
    ])
    if in_use:
        raise HTTPException(status_code=409, detail={
            "code": "LOCKED_RECORD",
            "message": "Nhân sự đang gắn với DO/Trip/ca làm việc, không được xóa khỏi Master Data.",
            "navigation_targets": ["dispatch", "tracking", "master-data/drivers"],
        })

    db.delete(drv)
    db.commit()
    return {"message": f"Đã xóa nhân sự {did}"}

# Toàn bộ phần tỷ giá (state, lịch làm mới, và 5 endpoint) đã chuyển sang
# routes/currency_routes.py. Tỷ giá nuôi mọi phép quy đổi tiền tệ nên nó
# thuộc nhóm tài chính, và router đó tự mang dependency xác thực.
# Các endpoint khách hàng và tuyến đường đã chuyển sang
# routes/master_data_routes.py.

# 7. Tracking API
