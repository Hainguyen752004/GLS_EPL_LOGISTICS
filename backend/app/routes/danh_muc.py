# -*- coding: utf-8 -*-
"""Dữ liệu gốc còn giữ lại: khách hàng, xe (hai biển số), tài xế, tỷ giá.

Đây là phần "master data" duy nhất bên Lào dùng — không loại xe, không công thức, không
lịch ca. Mỗi danh mục: xem · thêm · sửa · ngưng dùng (không xoá cứng, phiếu cũ còn trỏ tới).
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Driver, ExchangeRate, Vehicle
from services.bao_mat import can_vai, nguoi_hien_tai

router = APIRouter()
SUA_DANH_MUC = can_vai("yard", "acct")       # Bãi và Kế toán được sửa danh mục


def _dict(o):
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


def _ap(o, data, cot):
    for k in cot:
        if k in data:
            v = data[k]
            setattr(o, k, v.strip() if isinstance(v, str) else v)


# ---------------------------------------------------------------- khách hàng
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


# ---------------------------------------------------------------- xe
@router.get("/api/vehicles")
def ds_xe(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_dict(v) for v in db.query(Vehicle).order_by(Vehicle.active.desc(), Vehicle.owner_type, Vehicle.truck_no).all()]


@router.post("/api/vehicles")
def them_xe(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    if not str(data.get("truck_no") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_SO_XE", "loi": "Xe phải có số hiệu (ເບີລົດ)."})
    if data.get("owner_type", "EPL") not in ("EPL", "joint"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "owner_type phải là EPL hoặc joint."})
    if data.get("owner_type") == "joint" and not str(data.get("owner_name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_CHU_XE", "loi": "Xe liên kết phải ghi tên chủ xe."})
    v = Vehicle(); _ap(v, data, ("truck_no", "brand_model", "plate_head", "plate_trailer",
                                  "owner_type", "owner_name", "note"))
    db.add(v); db.commit(); db.refresh(v)
    return _dict(v)


@router.put("/api/vehicles/{vid}")
def sua_xe(vid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    _ap(v, data, ("truck_no", "brand_model", "plate_head", "plate_trailer",
                  "owner_type", "owner_name", "note", "active"))
    db.commit(); db.refresh(v)
    return _dict(v)


# ---------------------------------------------------------------- tài xế
@router.get("/api/drivers")
def ds_tai_xe(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_dict(d) for d in db.query(Driver).order_by(Driver.active.desc(), Driver.name).all()]


@router.post("/api/drivers")
def them_tai_xe(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Tài xế phải có tên."})
    d = Driver(); _ap(d, data, ("name", "phone", "license_no", "note"))
    db.add(d); db.commit(); db.refresh(d)
    return _dict(d)


@router.put("/api/drivers/{did}")
def sua_tai_xe(did: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    _ap(d, data, ("name", "phone", "license_no", "note", "active"))
    db.commit(); db.refresh(d)
    return _dict(d)


# ---------------------------------------------------------------- tỷ giá
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
            try:
                gt = float(data[ma])
            except (TypeError, ValueError):
                raise HTTPException(422, {"ma": "SO_SAI", "loi": "Tỷ giá %s phải là số." % ma})
            if gt <= 0:
                raise HTTPException(422, {"ma": "SO_SAI", "loi": "Tỷ giá %s phải lớn hơn 0." % ma})
            r = db.get(ExchangeRate, ma) or ExchangeRate(code=ma, rate_to_lak=gt)
            r.rate_to_lak = gt; r.updated_at = dt.datetime.utcnow()
            db.add(r)
    db.commit()
    return ds_ty_gia(db)
