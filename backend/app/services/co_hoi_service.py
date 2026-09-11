# -*- coding: utf-8 -*-
"""CƠ HỘI KHÁCH HÀNG (CRM-01) và HỒ SƠ KHÁCH (CRM-02) — bước đứng TRƯỚC báo giá.

Tài liệu phạm vi mở chuỗi vận hành bằng "Lead / Customer → Quotation → …". Hệ
đã có từ Báo giá trở đi; tệp này thêm đúng bước đầu:

  · Cơ hội  : khách hỏi → ghi lại ai, tuyến nào, hàng gì, bao nhiêu tấn, mấy
              chuyến/tháng, ai theo, hẹn liên hệ lại lúc nào. Đi qua các giai
              đoạn `new → contacted → negotiating → quoted → won | lost`.
  · Lập báo giá từ cơ hội : sinh MỘT BÁO GIÁ NHÁP kế thừa khách, tuyến, hàng,
              sản lượng — rồi báo giá đi tiếp đúng luồng QT → DO → Trip. Cơ hội
              chuyển `quoted` và trỏ vào báo giá. Khách chấp nhận báo giá thì hệ
              tự đặt cơ hội `won` (móc ở `bao_gia_service.khach_chap_nhan`).
  · Hồ sơ khách : gom từ các bảng ĐANG CÓ (cơ hội, báo giá, DO) — không lưu
              thêm số tổng nào để không có gì trôi.

Không có đường "đâm ngang": cơ hội KHÔNG sinh DO, chỉ sinh báo giá nháp.
"""
import datetime as dt
from decimal import Decimal

from sqlalchemy import func, or_, case

from models import (AuditLog, CoHoiKhach, Customer, DeliveryOrder, Quotation, Route,
                    TransportTrip, TripDeliveryOrder)
from services.errors import DomainError, conflict

GIAI_DOAN = ("new", "contacted", "negotiating", "quoted", "won", "lost")
GIAI_DOAN_MO = ("new", "contacted", "negotiating", "quoted")
NGUON = ("phone", "email", "web", "referral", "tender", "existing", "other")

# Chuyển giai đoạn nào được phép bằng tay. `quoted` chỉ do "Lập báo giá" đặt;
# `won` chỉ do khách chấp nhận báo giá đặt — hai mốc đó phải có bằng chứng.
CHUYEN_TAY = {
    "new": ("contacted", "negotiating", "lost"),
    "contacted": ("new", "negotiating", "lost"),
    "negotiating": ("contacted", "lost"),
    "quoted": ("lost",),
    "lost": ("new",),
    "won": (),
}


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _iso(v):
    if v is None:
        return None
    if isinstance(v, (dt.datetime,)):
        if v.tzinfo is None:
            v = v.replace(tzinfo=dt.timezone.utc)
        return v.astimezone(dt.timezone.utc).isoformat()
    return str(v)


def _so(v, ten, mac_dinh=0.0):
    if v in (None, ""):
        return mac_dinh
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise DomainError("CRM_VALUE_INVALID", "%s không phải là số." % ten, 422)
    if x < 0:
        raise DomainError("CRM_VALUE_INVALID", "%s không được âm." % ten, 422)
    return x


def _moc(v, ten):
    if v in (None, ""):
        return None
    try:
        x = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        raise DomainError("CRM_VALUE_INVALID", "%s không đúng định dạng thời gian." % ten, 422)
    if x.tzinfo is None:
        x = x.replace(tzinfo=dt.timezone.utc)
    return x


def _audit(db, action, record_id, actor):
    db.add(AuditLog(user_id=actor, action=action, table_name="crm_opportunities",
                    record_id=record_id, timestamp=dt.datetime.utcnow()))


def _ma_moi(db):
    nam = dt.datetime.now().year
    cuoi = (db.query(CoHoiKhach.id).filter(CoHoiKhach.id.like("LEAD-%d-%%" % nam))
            .order_by(CoHoiKhach.id.desc()).first())
    so = int(cuoi[0].split("-")[-1]) + 1 if cuoi else 1
    return "LEAD-%d-%03d" % (nam, so)


def _bao_gia_het_han(bg):
    """`bg` = (canonical_status, valid_to). Hết hạn KHÔNG lưu thành trạng thái ở
    bảng báo giá (xem _bung_bao_gia bên bao_gia_service) nên ở đây cũng tính lúc
    đọc, cùng một luật: còn chờ khách mà quá ngày hiệu lực."""
    if not bg:
        return False
    trang_thai, valid_to = bg
    if trang_thai == "expired":
        return True
    if trang_thai not in ("sent", "approved", "pending_approval") or not valid_to:
        return False
    try:
        han = dt.date.fromisoformat(str(valid_to)[:10])
    except ValueError:
        return False
    return han < dt.datetime.now().date()


def serialize(o, ten_khach=None, ten_tuyen=None, bao_gia=None):
    return {
        "id": o.id,
        "customer_id": o.customer_id,
        "customer_name": ten_khach or o.prospect_name or o.customer_id,
        "prospect_name": o.prospect_name,
        "contact_name": o.contact_name, "contact_phone": o.contact_phone,
        "contact_email": o.contact_email,
        "source": o.source,
        "route_id": o.route_id, "route_name": ten_tuyen,
        "origin_text": o.origin_text, "destination_text": o.destination_text,
        "cargo_type": o.cargo_type,
        "est_weight_kg": float(o.est_weight_kg or 0),
        "est_trips_per_month": int(o.est_trips_per_month or 0),
        "expected_start": o.expected_start,
        "expected_price": float(o.expected_price) if o.expected_price is not None else None,
        "stage": o.stage, "owner": o.owner, "notes": o.notes, "lost_reason": o.lost_reason,
        "quotation_id": o.quotation_id,
        "quotation_status": bao_gia[0] if bao_gia else None,
        "quotation_expired": _bao_gia_het_han(bao_gia),
        "next_action_at": _iso(o.next_action_at),
        "created_at": _iso(o.created_at), "updated_at": _iso(o.updated_at),
        "created_by": o.created_by, "version": o.version,
    }


def _bang_ten(db, ds):
    ma_khach = {o.customer_id for o in ds if o.customer_id}
    ma_tuyen = {o.route_id for o in ds if o.route_id}
    khach = dict(db.query(Customer.id, Customer.name).filter(Customer.id.in_(ma_khach)).all()) if ma_khach else {}
    tuyen = dict(db.query(Route.id, Route.name).filter(Route.id.in_(ma_tuyen)).all()) if ma_tuyen else {}
    ma_bg = {o.quotation_id for o in ds if o.quotation_id}
    bao_gia = {r[0]: (r[1], r[2]) for r in db.query(Quotation.id, Quotation.canonical_status, Quotation.valid_to)
               .filter(Quotation.id.in_(ma_bg)).all()} if ma_bg else {}
    return khach, tuyen, bao_gia


def _loc_chung(tv, owner=None, customer_id=None, q=None, source=None, since_days=None, due=None):
    """Bộ lọc dùng chung cho danh sách và bảng theo cột — một chỗ, không lệch nhau."""
    if owner:
        tv = tv.filter(CoHoiKhach.owner == owner)
    if customer_id:
        tv = tv.filter(CoHoiKhach.customer_id == customer_id)
    if source:
        tv = tv.filter(CoHoiKhach.source == str(source).strip().lower())
    if since_days:
        tv = tv.filter(CoHoiKhach.updated_at >= _now() - dt.timedelta(days=int(since_days)))
    if due == "today":
        cuoi = _now().replace(hour=23, minute=59, second=59)
        tv = tv.filter(CoHoiKhach.next_action_at.isnot(None), CoHoiKhach.next_action_at <= cuoi)
    elif due == "week":
        tv = tv.filter(CoHoiKhach.next_action_at.isnot(None), CoHoiKhach.next_action_at <= _now() + dt.timedelta(days=7))
    if q:
        chu = "%%%s%%" % str(q).strip().lower()
        tv = tv.filter(or_(func.lower(CoHoiKhach.id).like(chu),
                           func.lower(CoHoiKhach.prospect_name).like(chu),
                           func.lower(CoHoiKhach.contact_name).like(chu),
                           func.lower(CoHoiKhach.cargo_type).like(chu),
                           func.lower(CoHoiKhach.notes).like(chu),
                           func.lower(CoHoiKhach.owner).like(chu)))
    return tv


def _sap_xep(tv, sort):
    """`urgency`: trễ hẹn trước, rồi hẹn gần nhất, rồi mới sửa gần nhất. Cơ hội đã
    đóng thì theo lúc đóng (updated_at) mới nhất trước."""
    bay_gio = _now()
    huong = sort or "urgency"
    if huong == "urgency":
        tre = case((((CoHoiKhach.next_action_at.isnot(None)) & (CoHoiKhach.next_action_at <= bay_gio)), 0), else_=1)
        return tv.order_by(tre, CoHoiKhach.next_action_at.asc().nullslast(), CoHoiKhach.updated_at.desc())
    if huong == "updated":
        return tv.order_by(CoHoiKhach.updated_at.desc())
    if huong == "next_action":
        return tv.order_by(CoHoiKhach.next_action_at.asc().nullslast())
    if huong == "customer":
        return tv.order_by(func.coalesce(CoHoiKhach.prospect_name, CoHoiKhach.customer_id).asc())
    if huong == "stage":
        return tv.order_by(CoHoiKhach.stage.asc(), CoHoiKhach.updated_at.desc())
    if huong == "owner":
        return tv.order_by(CoHoiKhach.owner.asc().nullslast(), CoHoiKhach.updated_at.desc())
    if huong == "volume":
        return tv.order_by((CoHoiKhach.est_weight_kg * CoHoiKhach.est_trips_per_month).desc())
    return tv.order_by(CoHoiKhach.updated_at.desc())


def danh_sach(db, stage=None, owner=None, customer_id=None, q=None, limit=500,
              page=None, page_size=50, since_days=None, source=None, due=None, sort=None):
    """Danh sách cơ hội. Không truyền `page` thì trả MẢNG như trước (tương thích
    với mọi chỗ đang gọi); truyền `page` thì trả {items, total, page, page_size}."""
    tv = db.query(CoHoiKhach)
    if stage:
        ds_stage = [s for s in str(stage).split(",") if s]
        if ds_stage == ["open"]:
            tv = tv.filter(CoHoiKhach.stage.in_(GIAI_DOAN_MO))
        else:
            tv = tv.filter(CoHoiKhach.stage.in_(ds_stage))
    tv = _loc_chung(tv, owner=owner, customer_id=customer_id, q=q, source=source, since_days=since_days, due=due)
    tv = _sap_xep(tv, sort)
    if page is None:
        ds = tv.limit(limit).all()
        khach, tuyen, bao_gia = _bang_ten(db, ds)
        return [serialize(o, khach.get(o.customer_id), tuyen.get(o.route_id), bao_gia.get(o.quotation_id)) for o in ds]
    page = max(1, int(page)); page_size = max(1, min(200, int(page_size or 50)))
    total = tv.order_by(None).count()
    ds = tv.offset((page - 1) * page_size).limit(page_size).all()
    khach, tuyen, bao_gia = _bang_ten(db, ds)
    return {"items": [serialize(o, khach.get(o.customer_id), tuyen.get(o.route_id), bao_gia.get(o.quotation_id)) for o in ds],
            "total": total, "page": page, "page_size": page_size}


def bang_co_hoi(db, per_col=10, since_days=7, owner=None, q=None, source=None, due=None):
    """Bảng Kanban theo cột: mỗi giai đoạn trả SỐ ĐẾM + sản lượng + N thẻ đầu.

    Trang không tải cả trăm thẻ nữa; phần còn lại lấy thêm bằng `danh_sach`
    theo trang. Ba cột kho (`quoted`, `won`, `lost`) mặc định chỉ 7 ngày gần
    đây — `since_days=0` là tất cả. Số đếm ở đầu cột luôn là số THẬT của cột
    sau bộ lọc, dù chỉ tải N thẻ.
    """
    per_col = max(1, min(50, int(per_col or 10)))
    since = int(since_days or 0)
    cot = {}
    for stage in GIAI_DOAN:
        tv = db.query(CoHoiKhach).filter(CoHoiKhach.stage == stage)
        tv = _loc_chung(tv, owner=owner, q=q, source=source, due=due,
                        since_days=(since if (since and stage in ("quoted", "won", "lost")) else None))
        tong = tv.order_by(None).count()
        san_luong = tv.order_by(None).with_entities(
            func.coalesce(func.sum(CoHoiKhach.est_weight_kg * CoHoiKhach.est_trips_per_month), 0)).scalar() or 0
        ds = _sap_xep(tv, "updated" if stage in ("won", "lost") else "urgency").limit(per_col).all()
        khach, tuyen, bao_gia = _bang_ten(db, ds)
        cot[stage] = {"count": int(tong), "kg_per_month": float(san_luong),
                      "items": [serialize(o, khach.get(o.customer_id), tuyen.get(o.route_id), bao_gia.get(o.quotation_id)) for o in ds]}
    nguoi_theo = [r[0] for r in db.query(CoHoiKhach.owner).filter(CoHoiKhach.owner.isnot(None)).distinct().order_by(CoHoiKhach.owner).all()]
    return {"columns": cot, "per_col": per_col, "since_days": since, "owners": nguoi_theo}


def chi_tiet(db, ma):
    o = db.get(CoHoiKhach, ma)
    if o is None:
        raise DomainError("OPPORTUNITY_NOT_FOUND", "Không tìm thấy cơ hội %s." % ma, 404)
    khach, tuyen, bao_gia = _bang_ten(db, [o])
    return serialize(o, khach.get(o.customer_id), tuyen.get(o.route_id), bao_gia.get(o.quotation_id))


TRUONG_SUA = {"customer_id", "prospect_name", "contact_name", "contact_phone", "contact_email",
              "source", "route_id", "origin_text", "destination_text", "cargo_type",
              "est_weight_kg", "est_trips_per_month", "expected_start", "expected_price",
              "owner", "notes", "next_action_at"}


def _ap(db, o, data):
    la = set(data) - TRUONG_SUA - {"id", "stage", "expected_version"}
    if la:
        raise DomainError("CRM_PAYLOAD_INVALID",
                          "Trường không được hỗ trợ: %s." % ", ".join(sorted(la)), 422)
    if "customer_id" in data:
        ma = str(data.get("customer_id") or "").strip() or None
        if ma and db.get(Customer, ma) is None:
            raise DomainError("CUSTOMER_NOT_FOUND", "Không tìm thấy khách hàng %s." % ma, 404)
        o.customer_id = ma
    if "route_id" in data:
        ma = str(data.get("route_id") or "").strip() or None
        if ma and db.get(Route, ma) is None:
            raise DomainError("ROUTE_NOT_FOUND", "Không tìm thấy tuyến %s." % ma, 404)
        o.route_id = ma
    for k in ("prospect_name", "contact_name", "contact_phone", "contact_email",
              "origin_text", "destination_text", "cargo_type", "expected_start", "owner", "notes"):
        if k in data:
            setattr(o, k, (str(data.get(k) or "").strip() or None))
    if "source" in data:
        nguon = str(data.get("source") or "other").strip().lower()
        if nguon not in NGUON:
            raise DomainError("CRM_VALUE_INVALID", "Nguồn không hợp lệ: %s." % nguon, 422)
        o.source = nguon
    if "est_weight_kg" in data:
        o.est_weight_kg = _so(data.get("est_weight_kg"), "Khối lượng dự kiến")
    if "est_trips_per_month" in data:
        o.est_trips_per_month = int(_so(data.get("est_trips_per_month"), "Số chuyến/tháng"))
    if "expected_price" in data:
        v = data.get("expected_price")
        o.expected_price = Decimal(str(_so(v, "Giá khách mong muốn"))) if v not in (None, "") else None
    if "next_action_at" in data:
        o.next_action_at = _moc(data.get("next_action_at"), "Hẹn liên hệ")
    if not o.customer_id and not o.prospect_name:
        raise DomainError("CRM_CUSTOMER_REQUIRED",
                          "Cơ hội cần khách hàng có sẵn hoặc tên khách tiềm năng.", 422)


def tao(db, data, actor="system"):
    o = CoHoiKhach(id=str(data.get("id") or "").strip() or _ma_moi(db),
                   stage="new", source="other", est_weight_kg=0, est_trips_per_month=0,
                   created_by=actor, updated_by=actor, created_at=_now(), updated_at=_now(),
                   version=1)
    if db.get(CoHoiKhach, o.id):
        raise conflict("OPPORTUNITY_EXISTS", "Mã cơ hội %s đã tồn tại." % o.id)
    _ap(db, o, data)
    if not o.owner:
        o.owner = actor
    db.add(o)
    _audit(db, "CREATE_OPPORTUNITY", o.id, actor)
    db.flush()
    return chi_tiet(db, o.id)


def _lay_khoa(db, ma, expected_version):
    o = db.query(CoHoiKhach).filter(CoHoiKhach.id == ma).with_for_update().first()
    if o is None:
        raise DomainError("OPPORTUNITY_NOT_FOUND", "Không tìm thấy cơ hội %s." % ma, 404)
    if expected_version is not None and int(expected_version) != int(o.version or 1):
        raise conflict("VERSION_CONFLICT", "Cơ hội vừa được người khác sửa. Tải lại rồi thử lại.")
    return o


def sua(db, ma, data, actor="system"):
    o = _lay_khoa(db, ma, data.get("expected_version"))
    if o.stage in ("won",):
        raise conflict("OPPORTUNITY_CLOSED", "Cơ hội đã chốt — không sửa nữa.")
    _ap(db, o, {k: v for k, v in data.items() if k != "expected_version"})
    o.updated_by, o.updated_at, o.version = actor, _now(), (o.version or 1) + 1
    _audit(db, "UPDATE_OPPORTUNITY", o.id, actor)
    db.flush()
    return chi_tiet(db, o.id)


def doi_giai_doan(db, ma, stage, actor="system", expected_version=None, lost_reason=None):
    o = _lay_khoa(db, ma, expected_version)
    stage = str(stage or "").strip().lower()
    if stage not in GIAI_DOAN:
        raise DomainError("CRM_STAGE_INVALID", "Giai đoạn không hợp lệ: %s." % stage, 422)
    if stage == o.stage:
        return chi_tiet(db, o.id)
    if stage not in CHUYEN_TAY.get(o.stage, ()):
        goi_y = {"quoted": "Dùng nút “Lập báo giá” — giai đoạn Đã báo giá chỉ đặt khi có báo giá thật.",
                 "won": "Chốt do khách chấp nhận báo giá ở màn Báo giá — không đặt tay."}.get(stage, "")
        raise conflict("CRM_STAGE_TRANSITION_INVALID",
                       "Không chuyển được từ %s sang %s. %s" % (o.stage, stage, goi_y))
    if stage == "lost":
        ly_do = str(lost_reason or "").strip()
        if not ly_do:
            raise DomainError("CRM_LOST_REASON_REQUIRED", "Đánh mất cơ hội phải ghi lý do.", 422)
        o.lost_reason = ly_do
    if stage == "new" and o.stage == "lost":
        o.lost_reason = None
    o.stage = stage
    o.updated_by, o.updated_at, o.version = actor, _now(), (o.version or 1) + 1
    _audit(db, "MOVE_OPPORTUNITY_%s" % stage.upper(), o.id, actor)
    db.flush()
    return chi_tiet(db, o.id)


def lap_bao_gia(db, ma, actor="system", expected_version=None, valid_days=30):
    """Sinh báo giá NHÁP từ cơ hội. Khách chưa có trong danh mục thì tạo luôn."""
    from services import workflow_service
    o = _lay_khoa(db, ma, expected_version)
    if o.stage in ("won", "lost"):
        raise conflict("OPPORTUNITY_CLOSED", "Cơ hội đã đóng (%s) — không lập báo giá." % o.stage)
    if o.quotation_id and db.get(Quotation, o.quotation_id) is not None:
        raise conflict("OPPORTUNITY_ALREADY_QUOTED",
                       "Cơ hội đã có báo giá %s. Mở báo giá đó để sửa." % o.quotation_id)
    if not o.route_id:
        raise DomainError("CRM_ROUTE_REQUIRED",
                          "Chọn tuyến (Dữ liệu gốc) cho cơ hội trước khi lập báo giá — báo giá "
                          "tính km và chặng từ tuyến.", 422)
    if not o.customer_id:
        ma_khach = "CUS-" + "".join(ch for ch in (o.prospect_name or o.id).upper()
                                    if ch.isalnum())[:24]
        if db.get(Customer, ma_khach) is not None:
            ma_khach = "%s-%s" % (ma_khach, o.id.split("-")[-1])
        db.add(Customer(id=ma_khach, name=o.prospect_name or ma_khach, type="Account",
                        contact_person=o.contact_name or "", phone=o.contact_phone or "",
                        address=""))
        db.flush()
        o.customer_id = ma_khach
    hom_nay = dt.datetime.now().date()
    q = workflow_service.create_quotation(db, {
        "customer_id": o.customer_id,
        "route_id": o.route_id,
        "weight_kg": float(o.est_weight_kg or 0),
        "cargo_type": o.cargo_type or "",
        "valid_to": (hom_nay + dt.timedelta(days=int(valid_days))).isoformat(),
        # Ghi chú NỘI BỘ của phiếu (không in cho khách): nguồn gốc cơ hội.
        "notes_internal": ("Từ cơ hội %s" % o.id) + ((" — " + o.notes) if o.notes else ""),
        "trips_per_month": int(o.est_trips_per_month or 0),
        "sales_rep": o.owner or actor,
    }, actor)
    # Ghi bao gia xuong TRUOC roi moi tro khoa ngoai vao no: khong co
    # relationship() giua hai bang nen SQLAlchemy khong tu xep INSERT quotations
    # truoc UPDATE crm_opportunities — thieu flush la vo FK.
    db.flush()
    o.quotation_id = q.id
    o.stage = "quoted"
    o.updated_by, o.updated_at, o.version = actor, _now(), (o.version or 1) + 1
    _audit(db, "OPPORTUNITY_TO_QUOTATION", o.id, actor)
    db.flush()
    ra = chi_tiet(db, o.id)
    ra["quotation"] = {"id": q.id, "canonical_status": q.canonical_status}
    return ra


def danh_dau_thang_theo_bao_gia(db, quotation_id, actor="system"):
    """Móc từ bước khách chấp nhận báo giá: cơ hội đã lập báo giá này → `won`."""
    for o in db.query(CoHoiKhach).filter(CoHoiKhach.quotation_id == quotation_id,
                                          CoHoiKhach.stage != "won").all():
        o.stage = "won"
        o.updated_by, o.updated_at, o.version = actor, _now(), (o.version or 1) + 1
        _audit(db, "MOVE_OPPORTUNITY_WON", o.id, actor)


def danh_dau_mat_theo_bao_gia(db, quotation_id, ly_do="", actor="system"):
    """Móc từ bước khách TỪ CHỐI báo giá — đối xứng với `danh_dau_thang_theo_bao_gia`.

    Thiếu móc này thì thẻ cơ hội nằm ở "Đã báo giá" mãi sau khi khách đã nói
    không, cho tới khi ai đó nhớ kéo tay nó vào Kết quả. Lý do mất lấy từ phiếu
    từ chối, để bảng cơ hội đọc được vì sao mà không phải mở màn Báo giá.
    Cơ hội đã `won` không đụng: một báo giá đã chấp nhận thì không từ chối được
    nữa ở tầng báo giá, nhưng phòng hờ vẫn không lùi kết quả đã chốt.
    """
    ly_do = str(ly_do or "").strip()
    for o in db.query(CoHoiKhach).filter(CoHoiKhach.quotation_id == quotation_id,
                                          CoHoiKhach.stage.notin_(("won", "lost"))).all():
        o.stage = "lost"
        o.lost_reason = ("Khách từ chối báo giá %s" % quotation_id) + ((" — " + ly_do) if ly_do else "")
        o.updated_by, o.updated_at, o.version = actor, _now(), (o.version or 1) + 1
        _audit(db, "MOVE_OPPORTUNITY_LOST", o.id, actor)


def dai_so_lieu(db):
    bay_gio = _now()
    dem = dict(db.query(CoHoiKhach.stage, func.count(CoHoiKhach.id)).group_by(CoHoiKhach.stage).all())
    mo = sum(dem.get(s, 0) for s in GIAI_DOAN_MO)
    can_theo = db.query(func.count(CoHoiKhach.id)).filter(
        CoHoiKhach.stage.in_(GIAI_DOAN_MO), CoHoiKhach.next_action_at.isnot(None),
        CoHoiKhach.next_action_at <= bay_gio).scalar() or 0
    moc_30 = bay_gio - dt.timedelta(days=30)
    dong_30 = db.query(CoHoiKhach.stage, func.count(CoHoiKhach.id)).filter(
        CoHoiKhach.stage.in_(("won", "lost")), CoHoiKhach.updated_at >= moc_30
    ).group_by(CoHoiKhach.stage).all()
    d30 = dict(dong_30)
    tong_dong = d30.get("won", 0) + d30.get("lost", 0)
    san_luong = db.query(func.coalesce(func.sum(CoHoiKhach.est_weight_kg * CoHoiKhach.est_trips_per_month), 0)
                         ).filter(CoHoiKhach.stage.in_(GIAI_DOAN_MO)).scalar() or 0
    return {
        "open": mo, "by_stage": {s: dem.get(s, 0) for s in GIAI_DOAN},
        "due_follow_up": can_theo,
        "quoted_waiting": dem.get("quoted", 0),
        "won_30d": d30.get("won", 0), "lost_30d": d30.get("lost", 0),
        "win_rate_30d": (d30.get("won", 0) / tong_dong) if tong_dong else None,
        "pipeline_kg_per_month": float(san_luong),
    }


# ============================================================ HỒ SƠ KHÁCH (CRM-02)

def danh_sach_khach(db, q=None):
    khach = db.query(Customer).order_by(Customer.name).all()
    if q:
        chu = str(q).strip().lower()
        khach = [k for k in khach if chu in (k.name or "").lower() or chu in (k.id or "").lower()
                 or chu in (k.contact_person or "").lower()]
    ma = [k.id for k in khach]
    if not ma:
        return []
    co_hoi_mo = dict(db.query(CoHoiKhach.customer_id, func.count(CoHoiKhach.id)).filter(
        CoHoiKhach.customer_id.in_(ma), CoHoiKhach.stage.in_(GIAI_DOAN_MO)).group_by(CoHoiKhach.customer_id).all())
    bg = {}
    for cid, st, n, tien in db.query(Quotation.customer_id, Quotation.canonical_status,
                                     func.count(Quotation.id), func.coalesce(func.sum(Quotation.selling_price), 0)
                                     ).filter(Quotation.customer_id.in_(ma)).group_by(
                                         Quotation.customer_id, Quotation.canonical_status).all():
        bg.setdefault(cid, {})[st] = (n, float(tien or 0))
    do = {}
    for cid, st, n in db.query(DeliveryOrder.customer_id, DeliveryOrder.canonical_status,
                               func.count(DeliveryOrder.id)).filter(DeliveryOrder.customer_id.in_(ma)
                               ).group_by(DeliveryOrder.customer_id, DeliveryOrder.canonical_status).all():
        do.setdefault(cid, {})[st] = n
    lan_cuoi = dict(db.query(Quotation.customer_id, func.max(Quotation.updated_at)).filter(
        Quotation.customer_id.in_(ma)).group_by(Quotation.customer_id).all())
    ra = []
    for k in khach:
        b = bg.get(k.id, {})
        d = do.get(k.id, {})
        # Khach chap nhan xong thi bao gia sang `split` (da tach DO) — van la
        # bao gia DA CHOT voi khach, phai dem vao "chap nhan" va doanh thu.
        chap_nhan = (b.get("accepted", (0, 0.0))[0] + b.get("split", (0, 0.0))[0],
                     b.get("accepted", (0, 0.0))[1] + b.get("split", (0, 0.0))[1])
        ra.append({
            "id": k.id, "name": k.name, "type": k.type, "contact_person": k.contact_person,
            "phone": k.phone, "address": k.address,
            "open_opportunities": co_hoi_mo.get(k.id, 0),
            "quotations_total": sum(v[0] for v in b.values()),
            "quotations_sent": b.get("sent", (0, 0))[0] + b.get("approved", (0, 0))[0],
            "quotations_accepted": chap_nhan[0],
            "accepted_revenue": chap_nhan[1],
            "do_total": sum(d.values()),
            "do_active": d.get("in_transit", 0) + d.get("arrived", 0) + d.get("dispatched", 0),
            "do_delivered": d.get("delivered", 0),
            "do_pending": d.get("pending", 0),
            "last_activity_at": _iso(lan_cuoi.get(k.id)),
        })
    return ra


def ho_so_khach(db, customer_id):
    k = db.get(Customer, customer_id)
    if k is None:
        raise DomainError("CUSTOMER_NOT_FOUND", "Không tìm thấy khách hàng %s." % customer_id, 404)
    tom_tat = next((x for x in danh_sach_khach(db) if x["id"] == customer_id), None) or {}
    co_hoi = danh_sach(db, customer_id=customer_id, limit=50)
    bao_gia = [{
        "id": q.id, "quote_no": q.quote_no, "canonical_status": q.canonical_status,
        "route_id": q.route_id, "vehicle_type_id": q.vehicle_type_id,
        "selling_price": float(q.selling_price or 0), "total_cost": float(q.total_cost or 0),
        "valid_to": q.valid_to, "updated_at": _iso(q.updated_at),
    } for q in db.query(Quotation).filter(Quotation.customer_id == customer_id)
        .order_by(Quotation.updated_at.desc()).limit(30).all()]
    ds_do = db.query(DeliveryOrder).filter(DeliveryOrder.customer_id == customer_id)\
        .order_by(DeliveryOrder.updated_at.desc()).limit(30).all()
    ma_do = [d.id for d in ds_do]
    trip_cua = {}
    if ma_do:
        for do_id, trip_id, st in db.query(TripDeliveryOrder.do_id, TransportTrip.id, TransportTrip.status)\
                .join(TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id)\
                .filter(TripDeliveryOrder.do_id.in_(ma_do)).all():
            trip_cua.setdefault(do_id, []).append({"id": trip_id, "status": st})
    lenh = [{
        "id": d.id, "canonical_status": d.canonical_status, "quotation_id": d.quotation_id,
        "route_id": d.route_id, "weight_kg": float(d.weight_kg or 0),
        "unit_price": float(d.unit_price) if d.unit_price is not None else None,
        "delivery_window_end": _iso(d.delivery_window_end), "updated_at": _iso(d.updated_at),
        "trips": trip_cua.get(d.id, []),
    } for d in ds_do]
    return {
        "customer": {"id": k.id, "name": k.name, "type": k.type, "contact_person": k.contact_person,
                     "phone": k.phone, "address": k.address},
        "summary": tom_tat, "opportunities": co_hoi, "quotations": bao_gia, "delivery_orders": lenh,
    }
