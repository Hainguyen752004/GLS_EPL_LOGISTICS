import datetime
import math
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_

from models import (
    AuditLog,
    Customer,
    DeliveryPODRecord,
    DeliveryOrder,
    Driver,
    FreightOrder,
    Incident,
    Quotation,
    ResourceAssignment,
    Route,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
    Vehicle,
    VehicleTracking,
    VehicleType,
)
from services.don_vi_cuoc import gia_moi_chuyen
from services.errors import DomainError, conflict, missing_master
from services.crew_policy import mark_crew_busy, mark_crew_ready, require_crew
from services.vehicle_capacity_policy import require_vehicle_capacity
from services.vehicle_recommendation_service import require_quotation_vehicle_capacity


READY_VEHICLE = "Sẵn sàng"
READY_DRIVER = "🟢 Rảnh (Sẵn sàng)"
UTC = datetime.timezone.utc
BUSINESS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


STATUS = {
    "quotation": {"draft": "Bản nháp", "approved": "Đã duyệt"},
    "delivery_order": {
        "pending": "Chờ vận chuyển",
        "in_transit": "Đang vận chuyển",
        # Xe đã tới điểm giao nhưng CHƯA có POD ký nhận. Nói rõ "chờ POD"
        # ngay trong nhãn, vì đây là mốc mà người điều hành hay tưởng là
        # đã xong và đi chốt tiền — mà tiền chỉ chốt sau khi có chứng từ.
        "arrived": "Đã đến nơi — chờ POD",
        # "Đã giao" mơ hồ: xe tới điểm giao mà chưa ký POD thì theo cách
        # hiểu thông thường cũng là "đã giao", nhưng lúc đó chưa có gì xác
        # nhận. Mốc này là ĐÃ ký POD, ĐÃ chốt giá, ĐÃ hạch toán — nên gọi
        # đúng tên là hoàn tất. Mốc "tới bãi chưa ký" là `arrived`.
        "delivered": "Đã hoàn tất",
        "cancelled": "Đã hủy",
    },
}

# Cac ro, xep theo MUC CAP BACH giam dan. Thu tu nay quyet dinh tab nao mo san
# tren man hinh: ro cap bach nhat ma CO DONG.
#
# Ban truoc chi co nam ro, va gop hai truong hop khac han nhau:
#
#   - DON QUA HAN bi de trong "Cho van chuyen", chi danh dau bang co
#     `is_overdue` ma khong ai nhin. Mot DO qua han ba tuan va mot DO con hai
#     tuan nua moi den han khong the nam cung mot cho.
#
#   - DON THIEU HAN GIAO (khong co ngay lay lan ngay giao nao) cung roi vao
#     "Cho van chuyen", nen khong ai thay la no thieu — du no khong lap ke
#     hoach duoc va cung khong do tre duoc.
DO_ANALYSIS_STAGE = {
    "incident": "Gặp sự cố",
    "overdue": "Đã quá hạn",
    "undated": "Thiếu hạn giao",
    "near_late": "Gần trễ",
    "pending": "Chờ vận chuyển",
    "active": "Đang vận chuyển",
    "completed": "Hoàn thành",
    # DA HUY LA MOT RO RIENG, khong phai "cho van chuyen".
    #
    # LOI DO DUOC TREN DU LIEU THAT: mot DO khach da huy roi van hien o tab
    # "Gan tre" cua man Lenh giao hang, vi nhanh else cuoi cua ham phan loai
    # coi moi trang thai khong phai da giao / dang chay la "cho van chuyen"
    # roi do han giao cua no. Nguoi dieu phoi thay mot don sap tre ma khong
    # co gi de lam — hang can xu ly bi lam ban boi nhung don da chet.
    "cancelled": "Đã huỷ",
}

#: Thu tu cap bach, dung de chon tab mo san.
DO_STAGE_URGENCY = ("incident", "overdue", "undated", "near_late", "pending", "active",
                    "completed", "cancelled")


# --------------------------------------------------------------------------
# Dòng hàng hóa vận chuyển
# --------------------------------------------------------------------------

# Quy đổi đơn vị tính cước ra khối lượng / thể tích.
#
# Đây là chỗ dữ liệu người dùng gõ vào bảng "Hàng hóa vận chuyển" cuối cùng có
# tác dụng thật: `vehicle_capacity_policy` chặn điều xe quá tải dựa trên đúng
# hai con số này. Trước đây bảng dòng hàng không được lưu ở đâu cả, nên hai con
# số đó phải nhập tay ở chỗ khác — hoặc bị bỏ trống.
#
# "Chuyến" và "Km" là cách tính cước theo lần đi, không nói gì về khối lượng,
# nên cố ý không quy đổi.
_UOM_TO_KG = {"kg": 1, "tấn": 1000, "tan": 1000, "ton": 1000}
_UOM_TO_M3 = {"khối": 1, "khoi": 1, "m3": 1, "m³": 1, "cbm": 1}


def _line_quantity_split(uom, quantity):
    """Trả về (kg, m3) mà một dòng đóng góp vào tải trọng đơn hàng."""
    key = str(uom or "").strip().lower()
    for token, factor in _UOM_TO_KG.items():
        if key.startswith(token):
            return quantity * Decimal(factor), Decimal(0)
    for token in _UOM_TO_M3:
        if key.startswith(token):
            return Decimal(0), quantity
    return Decimal(0), Decimal(0)


# Quy cach va dieu kien van chuyen.
#
# Tab nay tung co sau o nhap ma khong co cot nao de chua, khong duoc gui len, va
# ban than cac o nhap con bi ban dich xoa mat. Ba tang cung hong mot cho.
# Ke thua sang don hang cung mot le voi quy cach van chuyen: cargo_type la loai
# phuong tien da chao cho khach, va cuoc mot chuyen tinh bang cong thuc cua LOAI
# XE — thieu no thi don van chuyen khong ap lai duoc cong thuc theo tai trong
# thuc te. Truoc day khong co cot nao, nen man don hang tinh tien bang
# `so km x 6250 + 800000`, hai con so khong co nguon nao.
SHIPPING_SPEC_FIELDS = (
    "cargo_type",
    "carrier_name",
    "delivery_method",
    "seal_weight",
    "temperature_requirement",
    "cargo_insurance",
    "warehouse_owner",
)


def _apply_shipping_spec(target, data):
    """Chi ghi nhung truong CO MAT trong payload.

    Giong ly do o POST /api/vehicles: gan mac dinh cho truong khong gui se xoa
    trang du lieu cu ma khong mot thong bao nao.
    """
    for field in SHIPPING_SPEC_FIELDS:
        if field in data:
            value = str(data.get(field) or "").strip()
            setattr(target, field, value[:255] or None)


def _inherit_shipping_spec(order, quotation):
    """Don hang ke thua quy cach tu bao gia da duyet.

    Day la dieu kien da chao cho khach o buoc bao gia — bat khai lai la vua mat
    cong vua de lech voi cai da chao.
    """
    if quotation is None:
        return
    for field in SHIPPING_SPEC_FIELDS:
        if not getattr(order, field, None):
            setattr(order, field, getattr(quotation, field, None))


def _line_decimal(value, field):
    """Doc mot so tien/so luong cua dong hang thanh Decimal.

    KHONG dung _money(): helper do tra ve float, ma cac cot nay la NUMERIC.
    Di qua float se tai lap dung sai so nhi phan ma v024_money_numeric da don.
    """
    if value in (None, ""):
        return Decimal(0)
    if isinstance(value, bool):
        raise DomainError("SO_LINE_INVALID", f"{field} khong hop le.", 422)
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("SO_LINE_INVALID", f"{field} khong hop le.", 422) from None
    if not result.is_finite():
        raise DomainError("SO_LINE_INVALID", f"{field} khong hop le.", 422)
    if result < 0:
        raise DomainError("SO_LINE_NEGATIVE", "So luong va don gia cuoc khong duoc am.", 422)
    if result.adjusted() + 1 > 18:
        raise DomainError("SO_LINE_TOO_LARGE", f"{field} vuot qua Numeric(24,6).", 422)
    return result


def _parse_business_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        parsed = value
        naive_timezone = UTC
    elif isinstance(value, datetime.date):
        parsed = datetime.datetime.combine(value, datetime.time.min)
        naive_timezone = BUSINESS_TIMEZONE
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        naive_timezone = BUSINESS_TIMEZONE
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=naive_timezone)
    return parsed.astimezone(UTC)


def _aware_utc(value=None):
    return _parse_business_datetime(value or datetime.datetime.now(UTC))


def _delivery_order_due_at(order):
    for value in (
        order.planned_departure_at,
        order.pickup_window_start,
        order.pickup_date,
        order.delivery_window_start,
        order.delivery_date,
        order.delivery_window_end,
        order.planned_arrival_at,
    ):
        parsed = _parse_business_datetime(value)
        if parsed:
            return parsed
    return None


def _delivery_order_analysis_record(order, pod_counts, incident_counts, now, near_late_hours=24):
    key = (order.canonical_status or order.status or "unknown").strip().lower()
    due_at = _delivery_order_due_at(order)
    has_open_incident = bool(incident_counts.get(order.id, 0))

    if has_open_incident:
        # Su co van xet TRUOC ca huy: mot DO da huy nhung con su co chua dong
        # thi su co do van phai co nguoi dong lai.
        stage = "incident"
    elif key in {"cancelled", "canceled", "void", "voided"}:
        stage = "cancelled"
    elif key in {"delivered", "completed", "settled", "posted"}:
        stage = "completed"
    elif key in {"dispatched", "in_transit", "arrived"}:
        stage = "active"
    else:
        stage = "pending"

    is_overdue = bool(stage == "pending" and due_at and due_at < now)
    is_near_late = bool(
        stage == "pending"
        and due_at
        and now <= due_at
        and due_at <= now + datetime.timedelta(hours=near_late_hours)
    )
    # Chi xet han giao khi don CHUA len duong. Xe da chay thi han giao khong
    # con quyet dinh ro nua.
    if stage == "pending":
        if due_at is None:
            # Khong co ngay nao ca. Day la mot ro RIENG: khong lap ke hoach
            # duoc va cung khong do tre duoc, nen de lan vao "cho van chuyen"
            # thi khong ai thay la no thieu.
            stage = "undated"
        elif is_overdue:
            stage = "overdue"
        elif is_near_late:
            stage = "near_late"
    operational_status = DO_ANALYSIS_STAGE[stage]

    reason = {
        "overdue": "DO chưa vận chuyển và đã quá hạn lấy/giao.",
        "undated": "DO chưa có ngày lấy lẫn ngày giao nào, nên chưa lập kế hoạch được.",
        "near_late": "DO chưa vận chuyển và thời điểm lấy/giao nằm trong 24 giờ tới.",
        "completed": "DO đã giao/hoàn tất hoặc đã hạch toán.",
        "active": "DO đã được điều phối xe và đang trong quá trình vận chuyển.",
        "pending": "DO đã lập kế hoạch hoặc đã đủ điều kiện điều phối, nhưng chưa có xe đang chạy.",
        "incident": "DO đang có sự cố vận hành chưa được xử lý.",
        "cancelled": "DO đã huỷ — không còn nằm trong hàng đợi điều phối.",
    }[stage]

    return {
        "id": order.id,
        "stage": stage,
        "operational_status": operational_status,
        "canonical_status": key,
        "source_status": order.status,
        "due_at": due_at.isoformat() if due_at else None,
        "due_at_local": due_at.astimezone(BUSINESS_TIMEZONE).isoformat() if due_at else None,
        "is_near_late": is_near_late,
        "is_overdue": is_overdue,
        "has_open_incident": has_open_incident,
        "open_incident_count": incident_counts.get(order.id, 0),
        "has_pod": bool(pod_counts.get(order.id, 0)),
        "pod_count": pod_counts.get(order.id, 0),
        "reason": reason,
    }


def delivery_order_analysis(db, near_late_hours=24, now=None):
    now = _aware_utc(now)
    rows = db.query(
        DeliveryPODRecord.do_id,
        func.count(DeliveryPODRecord.id),
    ).group_by(DeliveryPODRecord.do_id).all()
    pod_counts = {do_id: int(count or 0) for do_id, count in rows}
    incident_rows = db.query(
        Incident.do_id,
        func.count(Incident.id),
    ).filter(
        ~func.lower(func.coalesce(Incident.status, "")).in_({"resolved", "closed", "completed"})
    ).group_by(Incident.do_id).all()
    incident_counts = {do_id: int(count or 0) for do_id, count in incident_rows if do_id}
    orders = db.query(DeliveryOrder).order_by(DeliveryOrder.id.desc()).limit(500).all()
    records = [
        _delivery_order_analysis_record(order, pod_counts, incident_counts, now, near_late_hours)
        for order in orders
    ]
    # Sinh tu DO_ANALYSIS_STAGE thay vi viet cung: them mot ro moi thi khong
    # phai sua hai cho, va khong the co ro nao xuat hien o day ma thieu o kia.
    buckets = {
        stage: {"label": label, "count": 0, "record_ids": []}
        for stage, label in DO_ANALYSIS_STAGE.items()
    }
    buckets["active"]["arrived"] = 0
    buckets["completed"]["with_pod"] = 0
    buckets["incident"]["open_incidents"] = 0
    for record in records:
        bucket = buckets[record["stage"]]
        bucket["count"] += 1
        bucket["record_ids"].append(record["id"])
        if record["stage"] == "active" and record["canonical_status"] == "arrived":
            bucket["arrived"] += 1
        if record["stage"] == "completed" and record["has_pod"]:
            bucket["with_pod"] += 1
        if record["stage"] == "incident":
            bucket["open_incidents"] += record["open_incident_count"]
    return {
        "generated_at": now.isoformat(),
        "near_late_hours": near_late_hours,
        # Thu tu cap bach, de man hinh biet mo san tab nao: ro cap bach nhat ma
        # CO DONG. Ban truoc mo cung "Gan tre", ma ro do dang co 0 don, nen mo
        # man ra la mot bang trong trong khi don thuc nam o cac tab khac.
        "urgency": list(DO_STAGE_URGENCY),
        "logic": {
            "overdue": "pending và hạn lấy/giao đã trôi qua.",
            "undated": "pending và không có ngày lấy lẫn ngày giao nào.",
            "near_late": "pending và hạn lấy/giao nằm từ hiện tại đến hết 24 giờ tới.",
            "pending": "pending: đã có hạn, còn thời gian, chờ điều phối xe.",
            "active": "in_transit: đã điều phối và đang vận chuyển.",
            "completed": "delivered/completed/settled/posted: đã giao hoặc hoàn tất.",
            "incident": "Có incident theo do_id với status chưa resolved/closed/completed.",
        },
        "buckets": buckets,
        "records": records,
    }


def _now():
    return datetime.datetime.utcnow()


def _next_id(db, model, prefix):
    year = datetime.datetime.now().year
    like = f"{prefix}-{year}-%"
    last = db.query(model.id).filter(model.id.like(like)).order_by(model.id.desc()).first()
    seq = int(last[0].split("-")[-1]) + 1 if last else 1
    return f"{prefix}-{year}-{seq:03d}"


def _audit(db, action, table, record_id, user="system", ip_address=None):
    db.add(AuditLog(user_id=user, action=action, table_name=table, record_id=record_id, timestamp=_now(), ip_address=ip_address or db.info.get("audit_ip")))


def _money(data, name, default=0):
    try:
        value = float(data.get(name, default) or 0)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không hợp lệ.", 422) from None
    if not math.isfinite(value) or value < 0:
        raise DomainError("INVALID_VALUE", f"Giá trị {name} phải là số hữu hạn không âm.", 422)
    return value


def _parse_datetime(value, default=None):
    if not value:
        return default
    if isinstance(value, datetime.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        raise DomainError("INVALID_DATETIME", "Thời gian không hợp lệ.", 422) from None


def _positive_float(data, name, default):
    raw = data.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không hợp lệ.", 422) from None
    if not math.isfinite(value) or value <= 0:
        raise DomainError("INVALID_VALUE", f"Giá trị {name} phải là số hữu hạn dương.", 422)
    return value


def _nonnegative_int(data, name, default=0):
    raw = data.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không hợp lệ.", 422) from None
    if value < 0:
        raise DomainError("INVALID_VALUE", f"Giá trị {name} không được âm.", 422)
    return value


def estimate_delivery_timing(
    distance_km,
    departure_at=None,
    avg_speed_kmh=45,
    load_minutes=0,
    unload_minutes=0,
    return_speed_kmh=None,
    return_distance_km=None,
):
    distance = float(distance_km or 0)
    if distance < 0 or not math.isfinite(distance):
        raise DomainError("INVALID_DISTANCE", "Quãng đường không hợp lệ.", 422)
    avg_speed = float(avg_speed_kmh or 45)
    return_speed = float(return_speed_kmh or avg_speed)
    if avg_speed <= 0 or return_speed <= 0:
        raise DomainError("INVALID_SPEED", "Vận tốc trung bình phải lớn hơn 0.", 422)
    start = _parse_datetime(departure_at, _now())
    load = int(load_minutes or 0)
    unload = int(unload_minutes or 0)
    return_distance = distance if return_distance_km in (None, "") else float(return_distance_km)
    arrival = start + datetime.timedelta(minutes=load, hours=distance / avg_speed)
    planned_return = arrival + datetime.timedelta(minutes=unload, hours=return_distance / return_speed)
    return {
        "planned_departure_at": start,
        "planned_arrival_at": arrival.replace(second=0, microsecond=0),
        "planned_return_at": planned_return.replace(second=0, microsecond=0),
        "distance_km": distance,
        "avg_speed_kmh": avg_speed,
        "return_speed_kmh": return_speed,
        "return_distance_km": return_distance,
    }


def _iso(dt_value):
    if not dt_value:
        return ""
    value = dt_value.replace(second=0, microsecond=0)
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _require(db, model, pk, entity, label):
    if not pk:
        raise missing_master(entity, label)
    row = db.query(model).filter(model.id == pk).first()
    if not row:
        raise missing_master(entity, label)
    return row


def _route_label(route):
    return (getattr(route, "name", None) or getattr(route, "id", "") or "").strip()


def _route_context_from_quote(q, route, data=None):
    data = data or {}
    fallback = _route_label(route)
    return {
        "route_id": data.get("route_id") or q.route_id,
        "origin": data.get("origin") or q.origin or fallback,
        "destination": data.get("destination") or q.destination or fallback,
        "pickup_window_start": data.get("pickup_window_start") or q.pickup_window_start,
        "pickup_window_end": data.get("pickup_window_end") or q.pickup_window_end,
        "delivery_window_start": data.get("delivery_window_start") or q.delivery_window_start,
        "delivery_window_end": data.get("delivery_window_end") or q.delivery_window_end,
        "weight_kg": _money(data, "weight_kg", q.weight_kg or 0),
        "pallet_count": _nonnegative_int(data, "pallet_count", q.pallet_count or 0),
    }


DON_VI_CUOC_HOP_LE = ("per_trip", "per_tonne", "per_m3", "per_kg", "per_km")

#: Chuoi ky tu chi don vi -> cach lay so luong CUA MOT CHUYEN de nhan voi don gia.
_SO_LUONG_MOI_CHUYEN = {
    "per_trip": lambda q, km: 1,
    "per_tonne": lambda q, km: float(q.weight_kg or 0) / 1000.0,
    "per_kg": lambda q, km: float(q.weight_kg or 0),
    "per_m3": lambda q, km: float(q.volume_m3 or 0),
    "per_km": lambda q, km: km,
}


def _km_cua_tuyen(route):
    if route is None:
        return 0.0
    for ten in ("road_distance_km", "distance_km"):
        try:
            gia_tri = float(getattr(route, ten, None) or 0)
        except (TypeError, ValueError):
            gia_tri = 0.0
        if gia_tri > 0:
            return gia_tri
    return 0.0


def _ap_truong_bao_gia_moi(db, q, data, route=None):
    """Ap cac truong cua ban thiet ke bao gia moi, va SUY RA `selling_price`.

    VI SAO MAY CHU SUY RA CUOC chu khong nhan con so giao dien gui len.

    Khach mo da bao gia theo TAN, khach dong pallet bao gia theo CHUYEN. Cot
    `unit_price` + `price_basis` la thu khach doc va ky; con `selling_price` la
    tien mot chuyen — thu ma lenh giao hang, quyet toan va hoa don doc. Neu
    giao dien tu tinh con so thu hai roi gui len thi hai cot co the noi hai
    dieu khac nhau ve cung mot bao gia, va lech do di thang vao loi nhuan ma
    khong co buoc nao doi chieu lai.

    Nen o day: nhan don gia va don vi, tu nhan voi so luong mot chuyen. Giao
    dien chi hien ket qua.

    `min_qty_per_trip` la chot chan mo xuc thieu tai: gia thanh khong giam mot
    dong nao khi xe cho it hon, nen so luong tinh tien khong duoc thap hon muc
    toi thieu da thoa thuan.
    """
    if data.get("vehicle_type_id"):
        q.vehicle_type_id = _require(
            db, VehicleType, data.get("vehicle_type_id"), "vehicle_type", "loai xe").id

    if "price_basis" in data and data.get("price_basis"):
        don_vi = str(data.get("price_basis"))
        if don_vi not in DON_VI_CUOC_HOP_LE:
            raise DomainError(
                "PRICE_BASIS_INVALID",
                "Don vi tinh cuoc khong hop le: %s. Nhan: %s."
                % (don_vi, ", ".join(DON_VI_CUOC_HOP_LE)), 422)
        q.price_basis = don_vi
    if not q.price_basis:
        q.price_basis = "per_trip"

    for ten in ("unit_price", "min_qty_per_trip", "waiting_surcharge", "cargo_value",
                "target_margin", "competitor_price"):
        if ten in data:
            setattr(q, ten, _money(data, ten, getattr(q, ten, 0) or 0))
    if "fx_rate" in data:
        q.fx_rate = _money(data, "fx_rate", q.fx_rate or 1) or 1
    if "trips_per_month" in data:
        q.trips_per_month = _nonnegative_int(data, "trips_per_month", q.trips_per_month or 0)
    for ten in ("currency_code", "payment_terms", "sales_rep", "stacking", "sealing",
                "recipient_contact", "notes_customer", "notes_ops", "notes_internal"):
        if ten in data:
            setattr(q, ten, data.get(ten) or None)
    if not q.currency_code:
        q.currency_code = "VND"

    # SUY RA cuoc mot chuyen. Chi lam khi co don gia — bo du lieu dang chay co
    # nhung bao gia cu chi co `selling_price` va khong co `unit_price`, va suy
    # ra tu con so khong co se ghi 0 len mot cuoc dang dung.
    # CON SO NAO NGUOI GOI VUA KHAI THI CON SO DO THANG.
    #
    # Hai duong luu cung ton tai, va chung khai gia bang hai cot khac nhau:
    # man Bao gia moi gui `unit_price` + `price_basis`, con duong cu (va cac
    # bai kiem cua no) chi gui `selling_price`.
    #
    # Ban dau day chi kiem "co don gia thi suy ra cuoc", va no lam vo duong cu:
    # sua cuoc tu 3.100.000 len 3.500.000 thi con so moi bi ghi de bang cuoc
    # tinh lai tu DON GIA CU con luu trong bang — nguoi dung bam Luu, khong co
    # loi nao, va cuoc van la con so cu.
    gui_don_gia = "unit_price" in data
    gui_cuoc = "selling_price" in data
    if gui_don_gia or (not gui_cuoc and float(getattr(q, "unit_price", 0) or 0) > 0):
        # Don gia la con so khach ky, nen no la goc. Nhanh nay cung chay khi
        # nguoi dung chi sua TAI TRONG: bao gia theo tan thi doi tai trong phai
        # doi cuoc, khong thi cuoc dung lai o so luong cu.
        if float(getattr(q, "unit_price", 0) or 0) > 0:
            if route is None:
                route = db.query(Route).filter(Route.id == q.route_id).first()
            km = _km_cua_tuyen(route)
            lay = _SO_LUONG_MOI_CHUYEN.get(q.price_basis or "per_trip")
            q.selling_price = gia_moi_chuyen(
                q.price_basis, q.unit_price, lay(q, km), q.min_qty_per_trip, km)
    elif gui_cuoc and (q.price_basis or "per_trip") == "per_trip":
        # Duong cu chi gui `selling_price`. Ghi lai thanh don gia mot chuyen de
        # phieu bao gia va lenh giao hang cung doc mot cot.
        q.unit_price = q.selling_price


def create_quotation(db, data, user="system"):
    customer = _require(db, Customer, data.get("customer_id"), "customer", "khách hàng")
    route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
    require_quotation_vehicle_capacity(db, data)
    q = Quotation(
        id=data.get("id") or _next_id(db, Quotation, "QT"),
        customer_id=customer.id,
        route_id=route.id,
        origin=data.get("origin") or _route_label(route),
        destination=data.get("destination") or _route_label(route),
        pickup_window_start=data.get("pickup_window_start") or "",
        pickup_window_end=data.get("pickup_window_end") or "",
        delivery_window_start=data.get("delivery_window_start") or "",
        delivery_window_end=data.get("delivery_window_end") or "",
        weight_kg=_money(data, "weight_kg"),
        pallet_count=_nonnegative_int(data, "pallet_count", 0),
        cargo_type=data.get("cargo_type") or "",
        valid_to=data.get("valid_to") or "",
        fuel_cost=_money(data, "fuel_cost"),
        driver_cost=_money(data, "driver_cost"),
        toll_fee=_money(data, "toll_fee"),
        total_cost=_chot_gia_thanh(
            _money(data, "fuel_cost"), _money(data, "driver_cost"),
            _money(data, "toll_fee"), _money(data, "total_cost")),
        selling_price=_money(data, "selling_price"),
        packaging_spec=data.get("packaging_spec") or "",
        # O Ghi chu tren man hinh. Truoc day khong co cot nao de chua va khong
        # payload nao gui len, nen go xong bam Luu la mat khong mot loi nao.
        notes=data.get("notes") or None,
        volume_m3=_money(data, "volume_m3"),
        status=STATUS["quotation"]["draft"],
        canonical_status="draft",
        created_by=user,
        updated_by=user,
    )
    _ap_truong_bao_gia_moi(db, q, data, route)
    db.add(q)
    _audit(db, "CREATE_QUOTATION", "quotations", q.id, user)
    return q


def _chot_gia_thanh(dau, tai_xe, phi_duong, tong):
    """Tong gia thanh phai MACH LAC voi cac cau phan cua chinh no.

    Bang `quotations` co ba cot cau phan (dau, tai xe, phi duong) va mot cot
    TONG. Truoc day tong duoc luu y nguyen con so may khach gui, khong doi
    chieu gi — nen mot bao gia co the noi "tong 2 trieu" trong khi ba cau phan
    cua no cong lai la 3 trieu. Loi nhuan tinh tu tong do, va con so sai di het
    duong sang lenh giao hang roi hoa don.

    VI SAO CHI CHAN "TONG NHO HON TONG CAC PHAN", khong doi hoi bang nhau. Duong
    luu cu cong ca PHI KHO vao tong, ma bang khong co cot phi kho — nen tong
    LON HON ba cau phan la binh thuong va co that. Doi hoi bang nhau la chan
    dung mot duong dang chay. Con tong NHO HON cac phan cua no thi khong the
    dung theo bat cu cach doc nao.

    Khong khai tong thi SUY ra tu ba cau phan, thay vi de rong: mot bao gia co
    chi phi ma tong bang khong se lot qua chot "khong lo" o buoc duyet.
    """
    phan = dau + tai_xe + phi_duong
    if tong <= 0:
        return phan
    # Bien mot dong: tien luu bang so thap phan, va cong ba so le co the lech
    # o chu so cuoi.
    if tong + 1.0 < phan:
        raise DomainError(
            "COST_BREAKDOWN_INCONSISTENT",
            f"Tổng giá thành {tong:,.0f} nhỏ hơn tổng ba cấu phần "
            f"(dầu {dau:,.0f} + tài xế {tai_xe:,.0f} + phí đường {phi_duong:,.0f} "
            f"= {phan:,.0f}). Một trong hai con số sai — lợi nhuận tính từ tổng "
            "nên số này phải đúng.",
            422,
        )
    return tong


def _ngay_kinh_doanh(gia_tri):
    """Doc mot NGAY tu chuoi. Tra ve `None` khi khong doc duoc.

    `quotations.valid_to` la cot chuoi, nen no co the chua bat cu thu gi nguoi
    nhap go vao. Tra ve `None` chu khong nem loi: ben goi quyet dinh "khong doc
    duoc" nghia la gi — o duong DUYET thi do la mot ly do de chan, con o duong
    doc bao cao thi khong.
    """
    if not gia_tri:
        return None
    if isinstance(gia_tri, datetime.datetime):
        return gia_tri.date()
    if isinstance(gia_tri, datetime.date):
        return gia_tri
    text = str(gia_tri).strip()
    if not text:
        return None
    try:
        return datetime.date.fromisoformat(text[:10])
    except ValueError:
        return None


def _hom_nay_kinh_doanh():
    """Hom nay theo gio LAM VIEC, khong theo UTC.

    Luc 07:00 gio Viet Nam thi UTC con la ngay hom truoc. Dung UTC thi mot bao
    gia het han hom qua van duyet duoc suot buoi sang — va do la dung cai phep
    kiem nay ton tai de chan.
    """
    return datetime.datetime.now(BUSINESS_TIMEZONE).date()


def kiem_bao_gia_truoc_khi_duyet(q):
    """Ba chot phai qua truoc khi mot bao gia duoc duyet.

    Chu du an chot: *"lỗ và hết hạn thì không cho duyệt"*. Va do la chot dung —
    mot bao gia da duyet la thu ma cac buoc sau TIN: gia cua no chay vao lenh
    giao hang, roi vao tien quyet toan va hoa don. Cho duyet roi canh bao thi
    canh bao nam lai o mot dong log, con con so lo thi di het duong.

    BA CHOT:

      1. CON HAN. `valid_to` phai co va phai chua qua. Bao gia khong co han la
         mot bao gia dung mai mai — gia dau, gia tai xe va phi duong doi theo
         thang, nen mot con so cua nam ngoai duyet hom nay la duyet mot muc gia
         khong con ton tai.
      2. CO DU HAI CON SO. Ca gia thanh lan cuoc thu phai lon hon khong. Thieu
         mot trong hai thi loi nhuan khong tinh duoc, va "khong tinh duoc" thi
         khong ai duoc phep noi la da duyet.
      3. KHONG LO. Cuoc thu phai tu gia thanh tro len. Bang gia thanh thi cho
         qua — do la mot quyet dinh kinh doanh (giu khach, chay lap chuyen) chu
         khong phai lo; con duoi gia thanh thi chan.

    Nem `DomainError` voi thong bao NOI RO CON SO, khong noi chung. "Bao gia bi
    lo" thi nguoi dung phai mo lai form doi chieu; "cuoc thu 3.000.000 thap hon
    gia thanh 3.500.000, lo 500.000" thi ho sua duoc ngay.
    """
    han = _ngay_kinh_doanh(q.valid_to)
    if han is None:
        raise DomainError(
            "QUOTATION_VALIDITY_REQUIRED",
            "Báo giá phải có ngày hết hạn (Hiệu lực đến) trước khi duyệt. "
            "Báo giá không hạn là báo giá dùng mãi mãi, mà giá dầu và phí đường "
            "thì đổi theo tháng."
            + (f" Giá trị đang có: {q.valid_to!r} — không đọc được thành ngày." if q.valid_to else ""),
            422,
        )
    hom_nay = _hom_nay_kinh_doanh()
    if han < hom_nay:
        raise DomainError(
            "QUOTATION_EXPIRED",
            f"Báo giá đã hết hạn ngày {han.isoformat()} (hôm nay {hom_nay.isoformat()}), "
            "không được duyệt. Hãy cập nhật giá và ngày hiệu lực rồi duyệt lại.",
            422,
        )

    gia_thanh = _money({"total_cost": q.total_cost}, "total_cost")
    cuoc_thu = _money({"selling_price": q.selling_price}, "selling_price")
    if cuoc_thu <= 0 or gia_thanh <= 0:
        thieu = []
        if gia_thanh <= 0:
            thieu.append("giá thành (chi phí)")
        if cuoc_thu <= 0:
            thieu.append("cước phí thu của khách")
        raise DomainError(
            "QUOTATION_MARGIN_UNKNOWN",
            "Chưa khai " + " và ".join(thieu) + " nên không tính được lợi nhuận. "
            "Báo giá phải có cả hai con số trước khi duyệt.",
            422,
        )
    if cuoc_thu < gia_thanh:
        lo = gia_thanh - cuoc_thu
        raise DomainError(
            "QUOTATION_BELOW_COST",
            f"Báo giá đang lỗ: cước thu {_tien_viet(cuoc_thu)} thấp hơn giá thành "
            f"{_tien_viet(gia_thanh)}, lỗ {_tien_viet(lo)}. Không duyệt được báo giá lỗ — "
            "hãy nâng cước hoặc soát lại giá thành.",
            422,
        )


def _tien_viet(x):
    """Số tiền đọc được theo kiểu Việt Nam: 1.240.000 chứ không phải 1,240,000.

    Thông báo này hiện NGUYÊN VĂN trên màn hình cho người dùng Việt Nam và Lào,
    nên một con số ngăn bằng dấu phẩy đọc ra thành một số thập phân — người
    dùng thấy "lỗ 160,000" và hiểu là lỗ một trăm sáu mươi nghìn phẩy không.
    """
    return "{:,.0f}".format(float(x or 0)).replace(",", ".")


def approve_quotation(db, qid, user="system"):
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", f"Không tìm thấy báo giá {qid}", 404)
    if q.canonical_status not in ("draft", "sent", "unknown"):
        raise conflict("INVALID_TRANSITION", "Chỉ báo giá bản nháp/chờ gửi mới được duyệt.")
    # Chan TRUOC khi kiem tai trong: het han va lo la hai ly do nguoi dung sua
    # duoc ngay tren form, con tai trong thi phai doi loai xe.
    kiem_bao_gia_truoc_khi_duyet(q)
    require_quotation_vehicle_capacity(db, {
        # `vehicle_type_id` PHAI co trong goi nay. Man Bao gia moi dat loai xe o
        # cot do, con `cargo_type` chi giu loai HANG — thieu no thi cua chan
        # khong tra ra loai xe nao va lang le bo qua.
        "vehicle_type_id": q.vehicle_type_id,
        "cargo_type": q.cargo_type,
        "weight_kg": q.weight_kg,
        "volume_m3": q.volume_m3,
        "pallet_count": q.pallet_count,
    })
    # CÙNG CỬA BIÊN MỎNG với đường gửi khách (`bao_gia_service.gui_khach`).
    #
    # Rà soát trọn luồng đo được: đường duyệt cũ này qua được cửa lỗ / hết hạn /
    # tải trọng nhưng KHÔNG rẽ sang chờ duyệt nội bộ khi biên dưới ngưỡng — một
    # báo giá biên 5 % có thể được duyệt, khách chấp nhận và tách DO mà không ai
    # ở cấp trưởng phòng nhìn qua, trong khi cùng báo giá đó đi đường "Gửi khách"
    # thì bị giữ lại. Hai đường phải nói cùng một câu.
    from services.bao_gia_service import NGUONG_BIEN_PHAI_DUYET, _bien_rieng, bien_loi_nhuan
    bien = bien_loi_nhuan(q.selling_price, q.total_cost)
    nguong = _bien_rieng(q.target_margin) or NGUONG_BIEN_PHAI_DUYET
    if bien is not None and bien < nguong:
        q.canonical_status = "pending_approval"
        q.status = "Chờ duyệt nội bộ"
        _audit(db, "QUOTATION_HELD_FOR_INTERNAL_APPROVAL", "quotations", q.id, user)
    else:
        q.status = STATUS["quotation"]["approved"]
        q.canonical_status = "approved"
        _audit(db, "APPROVE_QUOTATION", "quotations", q.id, user)
    q.updated_by = user
    q.updated_at = _now()
    q.version = (q.version or 1) + 1
    return q


def update_quotation(db, qid, data, user="system"):
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", f"Không tìm thấy báo giá {qid}", 404)
    if q.canonical_status not in ("draft", "sent", "unknown"):
        raise conflict("LOCKED_RECORD", "Báo giá đã duyệt chỉ được xem, không được sửa.", ["quotations"])
    if data.get("customer_id"):
        customer = _require(db, Customer, data.get("customer_id"), "customer", "khách hàng")
        q.customer_id = customer.id
    if data.get("route_id"):
        route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
        q.route_id = route.id
    else:
        route = db.query(Route).filter(Route.id == q.route_id).first()
    fallback = _route_label(route) if route else ""
    q.origin = data.get("origin", q.origin) or fallback
    q.destination = data.get("destination", q.destination) or fallback
    q.pickup_window_start = data.get("pickup_window_start", q.pickup_window_start) or ""
    q.pickup_window_end = data.get("pickup_window_end", q.pickup_window_end) or ""
    q.delivery_window_start = data.get("delivery_window_start", q.delivery_window_start) or ""
    q.delivery_window_end = data.get("delivery_window_end", q.delivery_window_end) or ""
    q.weight_kg = _money(data, "weight_kg", q.weight_kg or 0)
    q.pallet_count = _nonnegative_int(data, "pallet_count", q.pallet_count or 0)
    if "cargo_type" in data:
        q.cargo_type = data.get("cargo_type") or ""
    if "valid_to" in data:
        q.valid_to = data.get("valid_to") or ""
    q.fuel_cost = _money(data, "fuel_cost", q.fuel_cost or 0)
    q.driver_cost = _money(data, "driver_cost", q.driver_cost or 0)
    q.toll_fee = _money(data, "toll_fee", q.toll_fee or 0)
    # Cung chot nhu luc tao: tong khong duoc nho hon tong cac cau phan. Sua chi
    # mot cau phan roi de nguyen tong cu la cach de nhat de hai con so troi
    # khoi nhau, va o day thi lech do di thang vao loi nhuan.
    q.total_cost = _chot_gia_thanh(
        q.fuel_cost, q.driver_cost, q.toll_fee,
        _money(data, "total_cost", q.total_cost or 0))
    q.selling_price = _money(data, "selling_price", q.selling_price or 0)
    if "packaging_spec" in data:
        q.packaging_spec = data.get("packaging_spec") or ""
    if "notes" in data:
        q.notes = data.get("notes") or None
    q.volume_m3 = _money(data, "volume_m3", q.volume_m3 or 0)
    _ap_truong_bao_gia_moi(db, q, data, route)
    require_quotation_vehicle_capacity(db, {
        # `vehicle_type_id` PHAI co trong goi nay. Man Bao gia moi dat loai xe o
        # cot do, con `cargo_type` chi giu loai HANG — thieu no thi cua chan
        # khong tra ra loai xe nao va lang le bo qua.
        "vehicle_type_id": q.vehicle_type_id,
        "cargo_type": q.cargo_type,
        "weight_kg": q.weight_kg,
        "volume_m3": q.volume_m3,
        "pallet_count": q.pallet_count,
    })
    # SỬA BÁO GIÁ ĐÃ GỬI KHÁCH → VỀ NHÁP, phải gửi lại.
    #
    # Khách đang cầm bản đã gửi. Sửa giá hay khối lượng mà vẫn để `sent` thì bản
    # trong hệ và bản khách cầm là hai bản khác nhau dưới cùng một mã — khách
    # chấp nhận bản cũ, hệ tách DO theo bản mới. Về `draft` buộc người bán gửi
    # lại (ghi thêm một phiên bản, đi lại cửa lỗ / biên mỏng), và `quote_no` giữ
    # nguyên vì đó vẫn là cùng một báo giá với khách.
    if q.canonical_status == "sent":
        q.canonical_status = "draft"
        q.status = "Bản nháp — đã sửa sau khi gửi, cần gửi lại"
        q.sent_at = None
        _audit(db, "QUOTATION_REOPENED_AFTER_SENT", "quotations", q.id, user)
    q.updated_by = user
    q.updated_at = _now()
    q.version = (q.version or 1) + 1
    _audit(db, "UPDATE_QUOTATION", "quotations", q.id, user)
    return q


def delete_quotation(db, qid, user="system"):
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", f"Không tìm thấy báo giá {qid}", 404)
    if q.canonical_status not in ("draft", "sent", "unknown"):
        raise conflict("LOCKED_RECORD", "Báo giá đã duyệt chỉ được xem, không được xóa.", ["quotations"])
    db.delete(q)
    _audit(db, "DELETE_QUOTATION", "quotations", qid, user)
    return q


def _chan_doi_tuyen_lech_bao_gia(db, do, tuyen_moi):
    """Lệnh giao hàng sinh từ báo giá thì KHÔNG được đổi tuyến.

    LỖ NÀY ĐÃ ĐO ĐƯỢC trên PostgreSQL thật, bằng đúng đường mà giao diện đi:

        DO-2026-0007-DO02 (từ QT-2026-007)
        tuyến: VSIP2A-CATLAI (44,7 km)  ->  CATLAI-AMATA (38,4 km)
        cước thu khách: 1.326.200  ->  1.326.200      (KHÔNG ĐỔI)

    Đổi được, và không một lời cảnh báo nào. Chủ dự án tự nêu ra rủi ro đó:
    *"nếu nó lệch thì phiếu chi và cước phí báo khách đều sai hết"* — và anh
    đúng. Chi phí thực tế tính trên km THẬT của tuyến mới, còn cước thu khách
    vẫn là con số tính cho tuyến CŨ. Ở ví dụ trên lệch 14%; đổi sang tuyến
    129 km thì lệch gấp ba.

    VÌ SAO CHẶN chứ không tự tính lại giá. Tính lại là **âm thầm đổi con số đã
    gửi cho khách** — người bán đã báo 1.326.200 cho tuyến này, hệ thống tự sửa
    thành số khác là một thay đổi thương mại mà không ai quyết. Bắt quay lại
    sửa báo giá rồi tách lại thì chậm hơn một bước, nhưng con số nào cũng có
    người chịu trách nhiệm.

    Chỉ chặn khi tuyến THỰC SỰ đổi. Gửi lại đúng tuyến đang có là chuyện bình
    thường — giao diện gửi cả biểu mẫu mỗi lần lưu, nên chặn cả trường hợp đó
    là chặn mọi lần sửa khối lượng hay khung giờ.

    DO tạo tay (không có `quotation_id`) thì đổi tuyến tự do: nó không mang một
    lời hứa giá nào với khách.
    """
    if not do.quotation_id:
        return
    if not tuyen_moi or str(tuyen_moi.id) == str(do.route_id or ""):
        return

    cu = db.query(Route).filter(Route.id == do.route_id).first()
    km_cu = _so_km(cu)
    km_moi = _so_km(tuyen_moi)
    gia = _money({"unit_price": do.unit_price}, "unit_price")

    doan = []
    if km_cu and km_moi:
        lech = abs(km_moi - km_cu) / km_cu * 100
        doan.append("Tuyến đang có %s dài %s km, tuyến mới %s dài %s km — lệch %.0f%%."
                    % (_route_label(cu) or do.route_id, _dep_km(km_cu),
                       _route_label(tuyen_moi) or tuyen_moi.id, _dep_km(km_moi), lech))
    else:
        doan.append("Tuyến đang có là %s, tuyến mới là %s."
                    % (_route_label(cu) or do.route_id, _route_label(tuyen_moi) or tuyen_moi.id))
    if gia > 0:
        doan.append("Cước thu khách %s đ đã khoá theo tuyến cũ và sẽ KHÔNG tự đổi, "
                    "nên phiếu chi tính trên km mới còn cước thu khách vẫn là giá "
                    "của tuyến cũ." % _tien_viet(gia))
    doan.append("Muốn đổi tuyến thì sửa lại báo giá %s rồi tách DO lại."
                % (do.quotation_id or ""))

    raise conflict("DO_ROUTE_LOCKED_BY_QUOTATION", " ".join(doan),
                   ["crm-sales", "ops-planning"])


def _so_km(route):
    if not route:
        return 0.0
    for ten in ("km_duong_bo", "distance_km"):
        gia_tri = _so(getattr(route, ten, None))
        if gia_tri > 0:
            return gia_tri
    return 0.0


def _so(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _dep_km(x):
    """31,2 km chứ không phải 31.2 km — thông báo này hiện nguyên văn cho người
    dùng Việt Nam và Lào."""
    return ("%.1f" % float(x or 0)).replace(".", ",")


def update_delivery_order(db, do_id, data, user="system"):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    if do.canonical_status != "pending":
        raise conflict("LOCKED_RECORD", "Lệnh giao hàng đang vận chuyển hoặc đã kết thúc chỉ được xem, không được sửa.", ["delivery-orders"])
    if data.get("route_id"):
        route = _require(db, Route, data.get("route_id"), "route", "tuyến đường")
        _chan_doi_tuyen_lech_bao_gia(db, do, route)
        do.route_id = route.id
    else:
        route = db.query(Route).filter(Route.id == do.route_id).first()
    fallback = _route_label(route) if route else ""
    do.origin = data.get("origin", do.origin) or fallback
    do.destination = data.get("destination", do.destination) or fallback
    if "pickup_window_start" in data:
        do.pickup_window_start = _parse_business_datetime(data.get("pickup_window_start"))
    if "pickup_window_end" in data:
        do.pickup_window_end = _parse_business_datetime(data.get("pickup_window_end"))
    if "delivery_window_start" in data:
        do.delivery_window_start = _parse_business_datetime(data.get("delivery_window_start"))
    if "delivery_window_end" in data:
        do.delivery_window_end = _parse_business_datetime(data.get("delivery_window_end"))
    do.weight_kg = _money(data, "weight_kg", do.weight_kg or 0)
    do.pallet_count = _nonnegative_int(data, "pallet_count", do.pallet_count or 0)
    if "pickup_date" in data:
        do.pickup_date = _parse_business_datetime(data.get("pickup_date"))
    if "delivery_date" in data:
        do.delivery_date = _parse_business_datetime(data.get("delivery_date"))
    if "packaging_spec" in data:
        do.packaging_spec = data.get("packaging_spec") or ""
    # So niem phong: chuoi rong hoac toan khoang trang la CHUA dien, ghi `None`
    # chu khong ghi "" — de phep kiem "co niem phong chua" khong phai doan.
    if "seal_no" in data:
        do.seal_no = (data.get("seal_no") or "").strip() or None
    do.volume_m3 = _money(data, "volume_m3", do.volume_m3 or 0)
    do.updated_by = user
    do.updated_at = _now()
    do.version = (do.version or 1) + 1
    _audit(db, "UPDATE_DELIVERY_ORDER", "delivery_orders", do.id, user)
    return do


def delete_delivery_order(db, do_id, user="system"):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    # Xoa duoc khi CHO (chua ai dong vao) hoac DA HUY (chu du an: "đã hủy thì cho
    # phép xóa"). Dang chay / da giao thi chi xem: tien va POD da gan vao.
    if do.canonical_status not in ("pending", "cancelled"):
        raise conflict("LOCKED_RECORD", "Lệnh giao hàng đang vận chuyển hoặc đã kết thúc chỉ được xem, không được xóa.", ["delivery-orders"])
    # DO da huy co the con dong lien ket voi chuyen DA HUY (huy chuyen tra DO ve
    # cho, roi huy DO). Go lien ket chet do; con dinh chuyen dang song thi khong xoa.
    lien_ket = db.query(TripDeliveryOrder, TransportTrip.status).join(
        TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id
    ).filter(TripDeliveryOrder.do_id == do.id).all()
    for link, tt_trip in lien_ket:
        if tt_trip not in ("cancelled", "completed"):
            raise conflict("ACTIVE_TRIP_EXISTS",
                           "Lệnh %s còn thuộc chuyến %s đang mở — huỷ chuyến trước." % (do.id, link.trip_id))
        db.delete(link)
    db.delete(do)
    _audit(db, "DELETE_DELIVERY_ORDER", "delivery_orders", do_id, user)
    return do


def update_delivery_status(db, do_id, status, user="system", reason=None):
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    ly_do_huy = str(reason or "").strip()
    if status == "cancelled" and not ly_do_huy:
        # Huy khong ly do la thu khong doi soat duoc voi khach. Bao gia da bat
        # `close_reason`; DO cung vay.
        raise DomainError("CANCEL_REASON_REQUIRED",
                          "Huỷ lệnh giao hàng phải ghi lý do (khách huỷ, đổi ngày, trùng lệnh…).", 422)
    allowed = {
        "pending": {"in_transit", "cancelled"},
        # `arrived` là mốc "xe đã tới điểm giao, chưa có POD". Trước đây nó
        # có trong danh sách trạng thái hợp lệ (migration v002) mà KHÔNG có
        # đường nào đặt được, nên màn hình không bao giờ phân biệt được xe
        # còn trên đường hay đã tới bãi chờ bốc dỡ.
        #
        # Cho đi thẳng `in_transit -> delivered` luôn: không phải chuyến nào
        # cũng gửi được mốc đến nơi (GPS mất tín hiệu, tài xế không báo), và
        # chặn đường cũ lại thì mọi chuyến như vậy bị kẹt.
        "in_transit": {"arrived", "delivered"},
        "arrived": {"delivered"},
    }
    if status not in allowed.get(do.canonical_status, set()):
        raise conflict("INVALID_TRANSITION", f"Không thể chuyển từ {do.status} sang {status}.")
    if status in ("in_transit", "arrived") and not (do.vehicle_id and do.driver_id):
        # Không có xe thì "đang vận chuyển" là một câu nói dối, và nó kéo
        # theo ba hệ quả: DO biến mất khỏi bản đồ điều độ, vì không có bản
        # ghi vehicle_tracking nên /api/tracking/{id} trả 404; DO kẹt mãi ở
        # in_transit, vì hoàn tất giao đòi một Trip có chặng giao mà DO đi
        # đường tắt này thì không có Trip nào; và xe lẫn tài xế không bị
        # đánh dấu đang chạy nên vẫn điều được cho DO khác — cùng một chiếc
        # xe nhận hai lệnh. Mọi đường điều phối đúng đều gán xe, tạo sẵn bản
        # ghi GPS và gắn DO vào một Trip,
        # nên chốt này không đóng đường nào đang dùng — nó đóng đường tắt
        # đã sinh ra dữ liệu tự mâu thuẫn.
        raise conflict(
            "NOT_DISPATCHED",
            "Lệnh giao hàng chưa được điều phối xe và tài xế nên không thể chuyển sang đang vận chuyển."
            " Hãy điều phối ở màn Điều phối để hệ thống gán xe, đánh dấu tài xế đang chạy"
            " và mở theo dõi GPS cho chuyến.",
            ["dispatch"],
        )
    if status == "cancelled":
        do.cancel_reason = ly_do_huy
        active_trip = db.query(TransportTrip.id).join(
            TripDeliveryOrder,
            TripDeliveryOrder.trip_id == TransportTrip.id,
        ).filter(
            TripDeliveryOrder.do_id == do.id,
            ~TransportTrip.status.in_(("completed", "cancelled")),
        ).first()
        if active_trip:
            # CAU BAO LOI PHAI CHI DUNG DUONG RA. Ban truoc chi noi "khong huy
            # duoc" roi chi sang man Chuyen — ma luc do man Chuyen KHONG co nut
            # huy nao, nen nguoi dung mac han o day va duong duy nhat con lai la
            # xoa cung DO. Gio da co `POST /api/tms/trips/{id}/cancel`, nen noi
            # ro ten chuyen va viec phai lam.
            raise conflict(
                "ACTIVE_TRIP_EXISTS",
                "Lệnh %s đang thuộc chuyến %s. Huỷ chuyến đó trước "
                "(POST /api/tms/trips/%s/cancel) — huỷ chuyến sẽ trả lệnh này về "
                "chờ điều phối, rồi mới huỷ được lệnh."
                % (do.id, active_trip[0], active_trip[0]),
                ["transport-trips"],
            )
    if status == "delivered":
        has_pod = db.query(DeliveryPODRecord.id).filter(
            DeliveryPODRecord.do_id == do.id,
            DeliveryPODRecord.vehicle_id == do.vehicle_id,
        ).first()
        if not has_pod:
            raise DomainError("POD_REQUIRED", "Cần cập nhật POD cho xe đang giao trước khi hoàn tất giao hàng.")
    do.canonical_status = status
    do.status = STATUS["delivery_order"][status]
    do.updated_by = user
    do.updated_at = _now()
    do.version = (do.version or 1) + 1
    if status == "delivered":
        release_resources(db, do)
    _audit(db, f"DELIVERY_{status.upper()}", "delivery_orders", do.id, user)
    return do


def dispatch(db, do_id, data, user="system"):
    """ĐƯỜNG ĐIỀU PHỐI LẺ ĐÃ ĐÓNG PHẦN GHI. Điều phối đi qua CHUYẾN.

    VÌ SAO ĐÓNG, chứ không vá thêm cửa. Bản trước đã được bổ sung đủ 5 cửa kiểm
    của điều phối chuyến (hạn pháp lý xe, bằng lái, ca làm việc, Packing List,
    niêm phong) — nhưng nó vẫn **không lập Chuyến và không tạo phân công**. Rà
    soát trọn luồng đo được hậu quả: một lệnh giao hàng đi qua đây rơi vào một
    trạng thái KHÔNG CÓ ĐƯỜNG RA.

      · nộp POD               -> 422 POD_LINEAGE_INVALID (đòi chuyến + thành viên)
      · đổi trạng thái sang đã giao -> 409 ATOMIC_COMPLETION_REQUIRED
      · huỷ                   -> bảng chuyển trạng thái không cho `in_transit` sang huỷ
      · lập chuyến để chữa    -> 409 DELIVERY_ORDER_NOT_PENDING
      · ghi mốc thực thi      -> đòi một phân công đang mở, mà đường này không tạo

    Và nặng nhất: `vehicle.status` thành "Đang vận chuyển đơn ..." trong khi mọi
    đường giải phóng đều đi từ bước hoàn tất hoặc bước xe-về-bãi — cả hai đều
    cần chuyến. Nên **xe và cả hai tài xế bị giữ vĩnh viễn**, và không có API
    nào đặt lại `status` của xe. Bấm nút này một lần trong buổi demo là mất một
    xe khỏi đội cho tới khi có người sửa tay trong cơ sở dữ liệu.

    Thêm cửa không chữa được điều đó: vấn đề không phải thiếu cửa mà là đường
    này tạo ra một bản ghi thiếu xương sống. Chuyến là nơi giữ phân công, chặng,
    lệnh vận chuyển — tức là nơi giữ đường ra.

    Nên đường này giờ CHỈ trả về một câu chỉ dẫn. Nó không còn ghi gì.
    """
    from models import TransportTrip, TripDeliveryOrder

    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)

    chuyen = (db.query(TransportTrip.id, TransportTrip.status)
              .join(TripDeliveryOrder, TripDeliveryOrder.trip_id == TransportTrip.id)
              .filter(TripDeliveryOrder.do_id == do.id,
                      TransportTrip.status.notin_(("cancelled", "completed", "settled")))
              .first())
    if chuyen:
        raise conflict(
            "DISPATCH_VIA_TRIP_REQUIRED",
            "Lệnh %s đã thuộc chuyến %s (%s). Điều phối qua chuyến: "
            "PUT /api/tms/trips/%s/dispatch." % (do.id, chuyen[0], chuyen[1], chuyen[0]),
            ["dispatch"],
        )
    raise conflict(
        "DISPATCH_VIA_TRIP_REQUIRED",
        "Không còn điều phối lẻ từng lệnh giao hàng. Lập chuyến cho %s trước "
        "(POST /api/tms/trips/from-delivery-orders), rồi điều phối chuyến đó "
        "(PUT /api/tms/trips/{id}/dispatch). Chuyến là nơi giữ phân công xe, "
        "tổ lái và chặng giao — thiếu nó thì lệnh không nộp được POD và xe "
        "không được giải phóng." % do.id,
        ["dispatch"],
    )


def _pod_record_payload(record):
    return {
        "id": record.id,
        "do_id": record.do_id,
        "trip_id": record.trip_id,
        "leg_id": record.leg_id,
        "vehicle_id": record.vehicle_id,
        "driver_id": record.driver_id,
        "stop_no": record.stop_no,
        "location_text": record.location_text,
        "receiver_name": record.receiver_name,
        "receiver_phone": record.receiver_phone,
        "delivery_time": record.delivery_time,
        "photo_url": record.photo_url,
        "signature_url": record.signature_url,
        "note": record.note,
        "status": record.status,
    }


def list_pod_records(db, do_id):
    return db.query(DeliveryPODRecord).filter(DeliveryPODRecord.do_id == do_id).order_by(
        DeliveryPODRecord.stop_no.asc(), DeliveryPODRecord.id.asc()
    ).all()


#: Tran so lenh giao hang cho MOT lan hoi POD hang loat.
#:
#: Co tran, va tran nay khong phai con so bat ky: cau `IN (...)` cang dai thi
#: PostgreSQL cang cham lap ke hoach, va mot ben goi vo tinh gui ca nghin ma se
#: bien mot duong doc thanh mot duong lam nghen may chu. Ben goi phai chia lo.
POD_HANG_LOAT_TOI_DA = 200


def list_pod_records_for_dos(db, do_ids):
    """POD cua NHIEU lenh giao hang trong MOT cau truy van.

    Vi sao can: bang chuyen o man Giao hang & van chuyen phai hien "da ky POD
    may/ tong bao nhieu don" cho TUNG dong. Duong theo tung don
    (`GET /api/pod/{do_id}`) thi ve mot bang N dong phai goi N lan — o quy mo
    hang nghin chuyen la man hinh khong mo duoc. Ma con so do khong phai trang
    tri: thieu POD tren mot don la ca chuyen khong doi soat duoc va hoa don treo.

    Tra ve `{ma lenh: [ban ghi POD]}`. Lenh khong co POD thi KHONG co khoa trong
    ket qua — de ben goi phan biet duoc "chua ky" voi "khong hoi den".
    """
    ma_sach = []
    da_thay = set()
    for ma in (do_ids or []):
        ma = str(ma or "").strip()
        if not ma or ma in da_thay:
            continue
        da_thay.add(ma)
        ma_sach.append(ma)
    if not ma_sach:
        return {}
    if len(ma_sach) > POD_HANG_LOAT_TOI_DA:
        raise DomainError(
            "TOO_MANY_DELIVERY_ORDERS",
            "Mot lan chi hoi POD cho toi da %d lenh giao hang." % POD_HANG_LOAT_TOI_DA,
            422,
        )
    dong = db.query(DeliveryPODRecord).filter(
        DeliveryPODRecord.do_id.in_(ma_sach)
    ).order_by(
        DeliveryPODRecord.do_id.asc(),
        DeliveryPODRecord.stop_no.asc(),
        DeliveryPODRecord.id.asc(),
    ).all()
    ket = {}
    for ban_ghi in dong:
        ket.setdefault(str(ban_ghi.do_id), []).append(ban_ghi)
    return ket


def save_pod(db, do_id, data, user="system"):
    idempotency_key = str(data.get("idempotency_key") or "").strip()
    if not idempotency_key:
        raise DomainError("IDEMPOTENCY_KEY_REQUIRED", "Thiếu Idempotency-Key khi lưu POD.", 422)
    existing = db.query(DeliveryPODRecord).filter(
        DeliveryPODRecord.idempotency_key == idempotency_key
    ).first()
    if existing:
        if (existing.do_id == do_id and existing.trip_id == data.get("trip_id")
                and existing.leg_id == data.get("leg_id") and existing.vehicle_id == data.get("vehicle_id")
                and existing.stop_no == data.get("stop_no")):
            return existing
        raise conflict("IDEMPOTENCY_CONFLICT", "Idempotency-Key đã được dùng cho POD khác.")
    do = db.query(DeliveryOrder).filter(DeliveryOrder.id == do_id).with_for_update().first()
    if not do:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy lệnh giao hàng {do_id}", 404)
    if do.canonical_status != "in_transit":
        raise conflict("INVALID_TRANSITION", "Chỉ cập nhật POD khi đơn đang vận chuyển hoặc đã đến nơi.")
    trip = db.query(TransportTrip).filter(
        TransportTrip.id == data.get("trip_id")
    ).with_for_update().first()
    if not trip or trip.status != "in_transit":
        raise conflict("TRIP_NOT_IN_TRANSIT", "POD chỉ được ghi cho chuyến đang vận chuyển.")
    membership = db.query(TripDeliveryOrder).filter_by(trip_id=trip.id, do_id=do.id).first()
    leg = db.query(TransportTripLeg).filter_by(id=data.get("leg_id"), trip_id=trip.id).first()
    if not membership or not leg or leg.do_id != do.id:
        raise conflict("POD_LINEAGE_INVALID", "Trip, chặng và DO của POD không khớp nhau.")
    assignment = db.query(ResourceAssignment).filter_by(trip_id=trip.id, status="active").first()
    if (not assignment or assignment.vehicle_id != data.get("vehicle_id")
            or trip.vehicle_id != data.get("vehicle_id") or do.vehicle_id != data.get("vehicle_id")):
        raise conflict("POD_RESOURCE_MISMATCH", "Xe của POD không khớp phân công chuyến.")
    record = DeliveryPODRecord(
        idempotency_key=idempotency_key,
        do_id=do_id,
        trip_id=trip.id,
        leg_id=leg.id,
        vehicle_id=assignment.vehicle_id,
        driver_id=assignment.driver_id,
        stop_no=data.get("stop_no"),
        location_text=data.get("location_text"),
        receiver_name=data.get("receiver_name"),
        receiver_phone=data.get("receiver_phone"),
        delivery_time=data.get("delivery_time"),
        photo_url=data.get("photo_url"),
        signature_url=data.get("signature_url"),
        note=data.get("note") or "",
        status=data.get("status") or "completed",
        created_by=user,
    )
    db.add(record)
    db.flush()
    if record.status == "completed":
        leg.status = "completed"
        leg.actual_arrival_at = record.delivery_time
        db.flush()
        active_trip_ids = {
            row[0] for row in db.query(TripDeliveryOrder.trip_id)
            .join(TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id)
            .filter(
                TripDeliveryOrder.do_id == do.id,
                TransportTrip.status != "cancelled",
            ).all()
        }
        required_legs = db.query(TransportTripLeg.id).filter(
            TransportTripLeg.trip_id.in_(active_trip_ids),
            TransportTripLeg.do_id == do.id,
            TransportTripLeg.status != "cancelled",
        ).all()
        completed_leg_ids = {
            row[0] for row in db.query(DeliveryPODRecord.leg_id).filter(
                DeliveryPODRecord.trip_id.in_(active_trip_ids),
                DeliveryPODRecord.do_id == do.id,
                DeliveryPODRecord.status == "completed",
            ).all()
        }
        if {row[0] for row in required_legs} <= completed_leg_ids:
            do.canonical_status = "delivered"
            do.status = "Hoàn thành"
            do.delivery_date = record.delivery_time
            do.version += 1
            do.updated_at = _now()
            do.updated_by = user
        open_legs = db.query(TransportTripLeg.id).filter(
            TransportTripLeg.trip_id == trip.id,
            TransportTripLeg.status.notin_(("completed", "cancelled")),
        ).first()
        if not open_legs:
            trip.status = "completed"
            trip.actual_arrival_at = record.delivery_time
            trip.version += 1
            trip.updated_at = datetime.datetime.now(UTC)
            trip.updated_by = user
            freight_order = db.get(FreightOrder, trip.freight_order_id)
            if freight_order:
                freight_order.status = "delivered"
                freight_order.version += 1
                freight_order.updated_at = _now()
                freight_order.updated_by = user
            assignment.status = "completed"
            release_resources(db, do)
    elif record.status == "rejected":
        db.add(Incident(
            do_id=do.id,
            vehicle_id=assignment.vehicle_id,
            incident_type="POD_REJECTED",
            severity="High",
            location=record.location_text,
            description=record.note or "POD bị từ chối, cần điều phối xử lý.",
            reporter=user,
            reported_at=record.delivery_time.isoformat() if record.delivery_time else None,
            status="Pending",
        ))
    _audit(db, "SAVE_POD", "delivery_pod_records", do.id, user)
    return record


def release_resources(db, do):
    if do.vehicle_id:
        active_vehicle = db.query(func.count(DeliveryOrder.id)).filter(
            DeliveryOrder.id != do.id,
            DeliveryOrder.canonical_status == "in_transit",
            DeliveryOrder.vehicle_id == do.vehicle_id,
        ).scalar()
        if not active_vehicle:
            vehicle = db.query(Vehicle).filter(Vehicle.id == do.vehicle_id).first()
            if vehicle:
                vehicle.status = READY_VEHICLE
    for crew_id in {do.driver_id, do.co_driver} - {None, ""}:
        active_crew = db.query(func.count(DeliveryOrder.id)).filter(
            DeliveryOrder.id != do.id,
            DeliveryOrder.canonical_status == "in_transit",
            or_(DeliveryOrder.driver_id == crew_id, DeliveryOrder.co_driver == crew_id),
        ).scalar()
        if not active_crew:
            crew_member = db.query(Driver).filter(Driver.id == crew_id).first()
            if crew_member:
                mark_crew_ready(crew_member)
    # MA TRANG THAI chieu lai tu lich sau khi phan cong da dong. Nhan o tren la
    # ban chieu cu; ma moi la thu man hinh doc (moc 045).
    from services import lich_xe
    db.flush()
    lich_xe.dong_bo_trang_thai_theo_lich(
        db, vehicle_id=do.vehicle_id,
        crew_ids=[x for x in (do.driver_id, do.co_driver) if x])
