# -*- coding: utf-8 -*-
"""Dữ liệu gốc: khách hàng · xe (đầu kéo) · rơ-moóc · tài xế & bằng lái · tỷ giá.

Xe và tài xế mang sang từ module của EPL_System theo yêu cầu bên Lào, cắt những gì họ không
dùng (tốc độ, ETA, GPS, ca kíp, tổ đội). Thêm RƠ-MOÓC là thực thể riêng: hư rơ-moóc này thì
tháo ra lắp cái khác vào đầu kéo, có lịch sử lắp/tháo.

Mỗi danh mục: xem · thêm · sửa · ngưng dùng (không xoá cứng — phiếu cũ còn trỏ tới).
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (TRANG_THAI_TAI_XE, TRANG_THAI_XE, Customer, CustomerRate, Driver, DriverLicense, ExchangeRate,
                    Route, Trailer, TrailerAssignment, Trip, TripExpense, Vehicle)
from services.bao_mat import can_vai, nguoi_hien_tai
from services.tinh_toan import tien_dong

router = APIRouter()
SUA_DANH_MUC = can_vai("yard", "acct")       # Bãi và Kế toán được sửa danh mục
SUA_BANG_GIA = can_vai("acct", "admin")      # giá là tiền: chỉ KT Thu/Chi VC (người kiểm mục II) và Sếp
XEM_BANG_GIA = can_vai("acct", "expacct", "rev", "treasury", "cash", "admin")   # Bãi không thấy tiền
NGAY_CANH_BAO = 30                            # giấy tờ hết hạn trong 30 ngày → cờ vàng


def _dict(o):
    ra = {}
    for c in o.__table__.columns:
        v = getattr(o, c.name)
        ra[c.name] = v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v
    return ra


def _ngay(v, ten):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ô %s phải là ngày YYYY-MM-DD." % ten})


def _so(v, ten):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số." % ten})


def _ap(o, data, cot, ngay=(), so=()):
    for k in cot:
        if k not in data:
            continue
        v = data[k]
        if k in ngay: v = _ngay(v, k)
        elif k in so: v = _so(v, k)
        elif isinstance(v, str): v = v.strip() or None
        setattr(o, k, v)


def _han(ngay):
    """Trạng thái giấy tờ: expired · soon · ok · none."""
    if not ngay:
        return "none"
    con = (ngay - dt.date.today()).days
    return "expired" if con < 0 else ("soon" if con <= NGAY_CANH_BAO else "ok")


# ================================================================ khách hàng
@router.get("/api/customers")
def ds_khach(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_dict(c) for c in db.query(Customer).order_by(Customer.active.desc(), Customer.name).all()]


@router.post("/api/customers")
def them_khach(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Khách hàng phải có tên."})
    c = Customer(); _ap(c, data, ("name", "phone", "address", "note"))
    db.add(c); db.commit(); db.refresh(c)
    return _dict(c)


@router.put("/api/customers/{cid}")
def sua_khach(cid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    c = db.get(Customer, cid)
    if not c:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    _ap(c, data, ("name", "phone", "address", "note", "active"))
    db.commit(); db.refresh(c)
    return _dict(c)


# ================================================================ bảng giá khách × tuyến (K3)
def tim_gia(db, customer_id, route_id, goods_type=None, ngay=None):
    """Dòng giá mới nhất còn hiệu lực cho khách × tuyến (× loại hàng) tại ngày `ngay`. Không có thì None."""
    if not customer_id or not route_id:
        return None
    ngay = ngay or dt.date.today()
    q = (db.query(CustomerRate).filter(CustomerRate.customer_id == customer_id, CustomerRate.route_id == route_id,
                                        CustomerRate.active.is_(True)))
    ds = [r for r in q.all() if r.valid_from is None or r.valid_from <= ngay]
    if goods_type:
        cung = [r for r in ds if r.goods_type == goods_type]
        ds = cung or [r for r in ds if r.goods_type == "iron_ore"]   # không có giá riêng loại hàng → dùng giá quặng
    if not ds:
        return None
    ds.sort(key=lambda r: (r.valid_from or dt.date.min, r.created_at or dt.datetime.min), reverse=True)
    return ds[0]


def _xuat_gia(db, r):
    d = _dict(r)
    t = db.get(Route, r.route_id); k = db.get(Customer, r.customer_id)
    d["route_name"] = t.name if t else None
    d["customer_name"] = k.name if k else None
    return d


def _ap_gia(db, r, data):
    if "route_id" in data:
        if not db.get(Route, data["route_id"] or ""):
            raise HTTPException(422, {"ma": "TUYEN_SAI", "loi": "Không có tuyến này."})
        r.route_id = data["route_id"]
    if "goods_type" in data: r.goods_type = (data["goods_type"] or "iron_ore").strip()
    if "price_usd" in data:
        gia = _so(data["price_usd"], "price_usd")
        if gia is None or gia <= 0:
            raise HTTPException(422, {"ma": "GIA_SAI", "loi": "Đơn giá USD/tấn phải lớn hơn 0."})
        r.price_usd = gia
    if "hire_price_usd" in data: r.hire_price_usd = _so(data["hire_price_usd"], "hire_price_usd")
    if "valid_from" in data: r.valid_from = _ngay(data["valid_from"], "valid_from")
    if "note" in data: r.note = (data["note"] or "").strip() or None
    if "active" in data: r.active = bool(data["active"])


@router.get("/api/customers/{cid}/bang-gia")
def ds_gia(cid: str, db: Session = Depends(get_db), _=Depends(XEM_BANG_GIA)):
    if not db.get(Customer, cid):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    ds = db.query(CustomerRate).filter(CustomerRate.customer_id == cid).all()
    ds.sort(key=lambda r: (not r.active, r.route_id, -(r.valid_from or dt.date.min).toordinal()))
    return [_xuat_gia(db, r) for r in ds]


@router.post("/api/customers/{cid}/bang-gia")
def them_gia(cid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_BANG_GIA)):
    if not db.get(Customer, cid):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    if not data.get("route_id"):
        raise HTTPException(422, {"ma": "THIEU_TUYEN", "loi": "Phải chọn tuyến."})
    if "price_usd" not in data:
        raise HTTPException(422, {"ma": "GIA_SAI", "loi": "Phải có đơn giá USD/tấn."})
    r = CustomerRate(customer_id=cid, created_by=user.full_name); _ap_gia(db, r, data)
    db.add(r); db.commit(); db.refresh(r)
    return _xuat_gia(db, r)


@router.put("/api/bang-gia/{gid}")
def sua_gia(gid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_BANG_GIA)):
    r = db.get(CustomerRate, gid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có dòng giá này."})
    _ap_gia(db, r, data); db.commit(); db.refresh(r)
    return _xuat_gia(db, r)


@router.delete("/api/bang-gia/{gid}")
def xoa_gia(gid: str, db: Session = Depends(get_db), _=Depends(SUA_BANG_GIA)):
    r = db.get(CustomerRate, gid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có dòng giá này."})
    db.delete(r); db.commit()
    return {"ok": True}


@router.get("/api/bang-gia/tra")
def tra_gia(customer_id: str, route_id: str, goods_type: str = None, ngay: str = None,
            db: Session = Depends(get_db), _=Depends(XEM_BANG_GIA)):
    """Màn phiếu hỏi: khách này đi tuyến này giá bao nhiêu? Trả {} nếu chưa có trong bảng."""
    r = tim_gia(db, customer_id, route_id, goods_type, _ngay(ngay, "ngay") if ngay else None)
    return _xuat_gia(db, r) if r else {}


# ================================================================ xe (đầu kéo)
COT_XE = ("truck_no", "brand_model", "year", "plate_head", "owner_type", "owner_name", "engine_no", "chassis_no",
          "insurance_exp", "inspection_exp", "road_permit_exp", "odometer_km", "next_service_km", "status", "depot", "note")
NGAY_XE = ("insurance_exp", "inspection_exp", "road_permit_exp")
SO_XE = ("year", "odometer_km", "next_service_km")


def xuat_xe(db, v, chi_tiet=False):
    r = _dict(v)
    r["giay_to"] = {"insurance": _han(v.insurance_exp), "inspection": _han(v.inspection_exp), "road_permit": _han(v.road_permit_exp)}
    r["can_bao_duong"] = bool(v.odometer_km and v.next_service_km and v.odometer_km >= v.next_service_km)
    if v.trailer_id:
        t = db.get(Trailer, v.trailer_id)
        r["trailer"] = _dict(t) if t else None
    if chi_tiet:
        # Chi phí sửa chữa của xe này — gom từ mục V các phiếu (không có bảng bảo dưỡng riêng)
        sua = []
        for e, p in (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
                     .filter(Trip.vehicle_id == v.id, TripExpense.section == "repair").order_by(Trip.doc_date.desc()).limit(50).all()):
            sua.append({"doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None, "item_key": e.item_key,
                        "item_name": e.item_name, "qty": e.qty, "unit_price": e.unit_price, "currency": e.currency,
                        "source": e.source, "acct_code": e.acct_code, "tien_lak": round(tien_dong(p, e))})
        r["sua_chua"] = sua
        r["so_phieu"] = db.query(Trip).filter(Trip.vehicle_id == v.id).count()
        r["lich_su_ro_mooc"] = [{"trailer_id": a.trailer_id, "plate": (db.get(Trailer, a.trailer_id) or Trailer()).plate,
                                 "attached_at": a.attached_at.isoformat() if a.attached_at else None,
                                 "detached_at": a.detached_at.isoformat() if a.detached_at else None, "reason": a.reason, "by_user": a.by_user}
                                for a in db.query(TrailerAssignment).filter(TrailerAssignment.vehicle_id == v.id)
                                .order_by(TrailerAssignment.attached_at.desc()).limit(20).all()]
    return r


@router.get("/api/vehicles")
def ds_xe(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [xuat_xe(db, v) for v in db.query(Vehicle).order_by(Vehicle.active.desc(), Vehicle.owner_type, Vehicle.truck_no).all()]


@router.get("/api/vehicles/{vid}")
def xem_xe(vid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    return xuat_xe(db, v, chi_tiet=True)


def _kiem_xe(data, v):
    if not str(getattr(v, "truck_no", "") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_SO_XE", "loi": "Xe phải có số hiệu (ເບີລົດ)."})
    if v.owner_type not in ("EPL", "joint"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "owner_type phải là EPL hoặc joint."})
    if v.owner_type == "joint" and not (v.owner_name or "").strip():
        raise HTTPException(422, {"ma": "THIEU_CHU_XE", "loi": "Xe liên kết phải ghi tên chủ xe."})
    if v.status not in TRANG_THAI_XE:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái xe phải là %s." % ", ".join(TRANG_THAI_XE)})


@router.post("/api/vehicles")
def them_xe(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    v = Vehicle(); _ap(v, data, COT_XE, NGAY_XE, SO_XE); v.status = v.status or "available"; v.owner_type = v.owner_type or "EPL"
    _kiem_xe(data, v)
    db.add(v); db.commit(); db.refresh(v)
    return xuat_xe(db, v)


@router.put("/api/vehicles/{vid}")
def sua_xe(vid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    _ap(v, data, COT_XE + ("active",), NGAY_XE, SO_XE)
    _kiem_xe(data, v)
    db.commit(); db.refresh(v)
    return xuat_xe(db, v)


# ================================================================ rơ-moóc
COT_RM = ("plate", "trailer_type", "capacity_t", "year", "owner_type", "owner_name", "insurance_exp", "inspection_exp", "status", "note")


def xuat_rm(db, t):
    r = _dict(t)
    r["giay_to"] = {"insurance": _han(t.insurance_exp), "inspection": _han(t.inspection_exp)}
    x = db.query(Vehicle).filter(Vehicle.trailer_id == t.id).first()
    r["dang_lap_xe"] = {"id": x.id, "truck_no": x.truck_no, "plate_head": x.plate_head} if x else None
    return r


@router.get("/api/trailers")
def ds_rm(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [xuat_rm(db, t) for t in db.query(Trailer).order_by(Trailer.active.desc(), Trailer.plate).all()]


@router.post("/api/trailers")
def them_rm(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    t = Trailer(); _ap(t, data, COT_RM, ("insurance_exp", "inspection_exp"), ("capacity_t", "year"))
    if not (t.plate or "").strip():
        raise HTTPException(422, {"ma": "THIEU_BIEN", "loi": "Rơ-moóc phải có biển số."})
    t.status = t.status or "available"; t.owner_type = t.owner_type or "EPL"
    db.add(t); db.commit(); db.refresh(t)
    return xuat_rm(db, t)


@router.put("/api/trailers/{tid}")
def sua_rm(tid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    t = db.get(Trailer, tid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có rơ-moóc này."})
    _ap(t, data, COT_RM + ("active",), ("insurance_exp", "inspection_exp"), ("capacity_t", "year"))
    # biển đổi thì cập nhật bản chép trên đầu kéo đang lắp
    x = db.query(Vehicle).filter(Vehicle.trailer_id == t.id).first()
    if x: x.plate_trailer = t.plate
    db.commit(); db.refresh(t)
    return xuat_rm(db, t)


@router.post("/api/vehicles/{vid}/trailer")
def lap_ro_mooc(vid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    """Lắp rơ-moóc vào đầu kéo. Rơ-moóc đang ở xe khác thì TỰ THÁO khỏi xe đó (ghi lịch sử) rồi lắp sang.
    Gửi trailer_id rỗng = tháo rơ-moóc hiện tại."""
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    ly_do = (data.get("reason") or "").strip() or None
    bay_gio = dt.datetime.utcnow()

    def thao(xe):
        if not xe.trailer_id: return
        a = (db.query(TrailerAssignment).filter(TrailerAssignment.vehicle_id == xe.id, TrailerAssignment.trailer_id == xe.trailer_id,
                                                TrailerAssignment.detached_at.is_(None)).first())
        if a: a.detached_at = bay_gio; a.reason = a.reason or ly_do
        rm = db.get(Trailer, xe.trailer_id)
        if rm and rm.status == "attached": rm.status = "available"
        xe.trailer_id = None; xe.plate_trailer = None

    tid = (data.get("trailer_id") or "").strip()
    if not tid:
        thao(v); db.commit(); return xuat_xe(db, v, chi_tiet=True)
    t = db.get(Trailer, tid)
    if not t or not t.active:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có rơ-moóc này."})
    if t.status == "maintenance":
        raise HTTPException(409, {"ma": "RO_MOOC_DANG_SUA", "loi": "Rơ-moóc %s đang sửa, không lắp được." % t.plate})
    khac = db.query(Vehicle).filter(Vehicle.trailer_id == t.id, Vehicle.id != v.id).first()
    if khac: thao(khac)
    thao(v)
    v.trailer_id = t.id; v.plate_trailer = t.plate; t.status = "attached"
    db.add(TrailerAssignment(trailer_id=t.id, vehicle_id=v.id, attached_at=bay_gio, reason=ly_do, by_user=user.full_name))
    db.commit()
    return xuat_xe(db, v, chi_tiet=True)


# ================================================================ tài xế & bằng lái
COT_TX = ("driver_code", "name", "phone", "dob", "id_card", "address", "role", "hire_date", "license_no", "license_type",
          "license_valid_from", "license_valid_to", "default_vehicle_id", "status", "note")
NGAY_TX = ("dob", "hire_date", "license_valid_from", "license_valid_to")


def xuat_tai_xe(db, d, chi_tiet=False):
    r = _dict(d)
    r["bang_lai"] = _han(d.license_valid_to)
    if d.default_vehicle_id:
        x = db.get(Vehicle, d.default_vehicle_id); r["default_vehicle"] = x.truck_no if x else None
    if chi_tiet:
        r["licenses"] = [_dict(l) for l in db.query(DriverLicense).filter(DriverLicense.driver_id == d.id)
                         .order_by(DriverLicense.valid_to.desc().nullslast()).all()]
        r["so_phieu"] = db.query(Trip).filter(Trip.driver_id == d.id).count()
        r["phieu_gan_day"] = [{"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
                               "truck_no": p.truck_no, "origin": p.origin, "destination": p.destination, "transport_status": p.transport_status}
                              for p in db.query(Trip).filter(Trip.driver_id == d.id).order_by(Trip.doc_date.desc()).limit(10).all()]
    return r


@router.get("/api/drivers")
def ds_tai_xe(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [xuat_tai_xe(db, d) for d in db.query(Driver).order_by(Driver.active.desc(), Driver.name).all()]


@router.get("/api/drivers/{did}")
def xem_tai_xe(did: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    return xuat_tai_xe(db, d, chi_tiet=True)


def _kiem_tx(d):
    if not (d.name or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Tài xế phải có tên."})
    if d.role not in ("main", "co"):
        raise HTTPException(422, {"ma": "VAI_SAI", "loi": "role phải là main (lái chính) hoặc co (phụ xe)."})
    if d.status not in TRANG_THAI_TAI_XE:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái phải là %s." % ", ".join(TRANG_THAI_TAI_XE)})
    if d.license_valid_from and d.license_valid_to and d.license_valid_to < d.license_valid_from:
        raise HTTPException(422, {"ma": "HAN_SAI", "loi": "Hạn bằng lái phải sau ngày cấp."})


@router.post("/api/drivers")
def them_tai_xe(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    d = Driver(); _ap(d, data, COT_TX, NGAY_TX); d.role = d.role or "main"; d.status = d.status or "available"
    _kiem_tx(d)
    db.add(d); db.flush()
    if d.license_no:
        db.add(DriverLicense(driver_id=d.id, license_no=d.license_no, license_type=d.license_type, valid_from=d.license_valid_from,
                             valid_to=d.license_valid_to, verified_by=user.full_name))
    db.commit(); db.refresh(d)
    return xuat_tai_xe(db, d, chi_tiet=True)


@router.put("/api/drivers/{did}")
def sua_tai_xe(did: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    _ap(d, data, COT_TX + ("active",), NGAY_TX)
    _kiem_tx(d)
    db.commit(); db.refresh(d)
    return xuat_tai_xe(db, d, chi_tiet=True)


@router.post("/api/drivers/{did}/licenses")
def them_bang_lai(did: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    """Ghi một bằng lái mới / lần gia hạn — đồng thời cập nhật bằng HIỆN HÀNH trên hồ sơ tài xế."""
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    so = str(data.get("license_no") or "").strip()
    if not so:
        raise HTTPException(422, {"ma": "THIEU_SO", "loi": "Bằng lái phải có số."})
    l = DriverLicense(driver_id=d.id, license_no=so, license_type=(data.get("license_type") or "").strip() or None,
                      valid_from=_ngay(data.get("valid_from"), "valid_from"), valid_to=_ngay(data.get("valid_to"), "valid_to"),
                      issued_by=data.get("issued_by"), note=data.get("note"), verified_by=user.full_name)
    if l.valid_from and l.valid_to and l.valid_to < l.valid_from:
        raise HTTPException(422, {"ma": "HAN_SAI", "loi": "Hạn bằng lái phải sau ngày cấp."})
    db.add(l)
    d.license_no, d.license_type, d.license_valid_from, d.license_valid_to = l.license_no, l.license_type, l.valid_from, l.valid_to
    db.commit(); db.refresh(d)
    return xuat_tai_xe(db, d, chi_tiet=True)


# ================================================================ tỷ giá
@router.get("/api/rates")
def ds_ty_gia(db: Session = Depends(get_db)):
    ra = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
    ra.setdefault("LAK", 1.0)
    return ra


@router.put("/api/rates")
def sua_ty_gia(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("acct", "rev"))):
    """Tỷ giá dùng làm MẶC ĐỊNH cho phiếu mới. Phiếu đã lập giữ tỷ giá riêng của nó."""
    for ma in ("USD", "THB", "VND"):
        if ma in data:
            gt = _so(data[ma], ma)
            if not gt or gt <= 0:
                raise HTTPException(422, {"ma": "SO_SAI", "loi": "Tỷ giá %s phải lớn hơn 0." % ma})
            r = db.get(ExchangeRate, ma) or ExchangeRate(code=ma, rate_to_lak=gt)
            r.rate_to_lak = gt; r.updated_at = dt.datetime.utcnow()
            db.add(r)
    db.commit()
    return ds_ty_gia(db)
