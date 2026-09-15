"""Danh mục Tuyến đường.

Nguồn cho ô "Tuyến giao" trên phiếu đóng gói, và là nơi màn Theo dõi lấy điểm
đầu - điểm cuối để vẽ đường xe. Khai một lần, mọi phiếu chọn lại.
"""

import uuid

from sqlalchemy import func

from models import Customer, PackingList, Route
from services.loi import LoiNghiepVu


def ra_dict(r, diem=None):
    data = {
        "id": r.id,
        "code": r.code,
        "name": r.name,
        "from_id": r.from_id,
        "to_id": r.to_id,
        "distance_km": r.distance_km,
        "note": r.note,
        "active": bool(r.active),
        "created_at": r.created_at,
    }
    if diem:
        dau, cuoi = diem
        data["from_name"] = dau.name if dau else None
        data["to_name"] = cuoi.name if cuoi else None
        data["from_lat"] = dau.lat if dau else None
        data["from_lng"] = dau.lng if dau else None
        data["to_lat"] = cuoi.lat if cuoi else None
        data["to_lng"] = cuoi.lng if cuoi else None
    return data


def _diem(db, r):
    dau = db.query(Customer).filter(Customer.id == r.from_id).first() if r.from_id else None
    cuoi = db.query(Customer).filter(Customer.id == r.to_id).first() if r.to_id else None
    return dau, cuoi


def nap(db, id_):
    r = db.query(Route).filter(Route.id == id_).first()
    if not r:
        raise LoiNghiepVu("RT_NOT_FOUND", f"Không tìm thấy tuyến đường {id_}", 404)
    return r


def danh_sach(db, q=None, chi_dang_dung=False):
    cau = db.query(Route)
    if chi_dang_dung:
        cau = cau.filter(Route.active == 1)
    if q:
        tim = f"%{q.strip()}%"
        cau = cau.filter(Route.code.ilike(tim) | Route.name.ilike(tim))
    return [ra_dict(r, _diem(db, r)) for r in cau.order_by(Route.code).all()]


def _kiem(db, payload, bo_qua_id=None):
    ma = (payload.get("code") or "").strip()
    ten = (payload.get("name") or "").strip()
    if not ma:
        raise LoiNghiepVu("RT_NO_CODE", "Tuyến đường phải có mã")
    if not ten:
        raise LoiNghiepVu("RT_NO_NAME", "Tuyến đường phải có tên")
    trung = db.query(Route).filter(Route.code == ma)
    if bo_qua_id:
        trung = trung.filter(Route.id != bo_qua_id)
    if trung.first():
        raise LoiNghiepVu("RT_CODE_DUPLICATE", f"Mã tuyến {ma} đã tồn tại", 409)
    km = float(payload.get("distance_km") or 0)
    if km < 0:
        raise LoiNghiepVu("RT_KM_NEGATIVE", "Số km không được âm")
    for khoa in ("from_id", "to_id"):
        if payload.get(khoa) and not db.query(Customer).filter(Customer.id == payload[khoa]).first():
            raise LoiNghiepVu("CUST_NOT_FOUND", "Không tìm thấy địa điểm đã chọn", 404)
    return ma, ten, km


def tao(db, payload):
    ma, ten, km = _kiem(db, payload)
    r = Route(
        id=uuid.uuid4().hex[:12].upper(),
        code=ma,
        name=ten,
        from_id=payload.get("from_id") or None,
        to_id=payload.get("to_id") or None,
        distance_km=km,
        note=payload.get("note"),
        active=1 if payload.get("active", True) else 0,
    )
    db.add(r)
    db.flush()
    return r


def sua(db, id_, payload):
    r = nap(db, id_)
    ma, ten, km = _kiem(db, payload, bo_qua_id=id_)
    r.code, r.name, r.distance_km = ma, ten, km
    r.from_id = payload.get("from_id") or None
    r.to_id = payload.get("to_id") or None
    if "note" in payload:
        r.note = payload.get("note")
    if "active" in payload:
        r.active = 1 if payload.get("active") else 0
    db.flush()
    return r


def xoa(db, id_):
    r = nap(db, id_)
    dung = db.query(func.count(PackingList.id)).filter(PackingList.route_id == id_).scalar() or 0
    if dung:
        raise LoiNghiepVu(
            "RT_IN_USE",
            "Tuyến đang được Packing List dùng nên không xoá được",
            409,
            {"packing_lists": int(dung)},
        )
    db.delete(r)
    db.flush()
    return True
