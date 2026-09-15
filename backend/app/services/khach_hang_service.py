"""Danh mục khách hàng / nhà cung cấp / kho.

Đây là nguồn cho các ô CHỌN trên phiếu đơn hàng. Chủ dự án đã chốt: không cho
gõ tay tên khách trên phiếu — phải chọn từ danh mục có trang quản lý riêng,
giống EPL_System. Toạ độ ở đây cũng là thứ màn Theo dõi dùng để vẽ đường xe.
"""

import uuid

from sqlalchemy import func

from models import Customer, SalesOrder
from services.loi import LoiNghiepVu

LOAI = ("customer", "vendor", "depot")


def ra_dict(c):
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "kind": c.kind or "customer",
        "tax_number": c.tax_number,
        "address": c.address,
        "phone": c.phone,
        "contact_name": c.contact_name,
        "lat": c.lat,
        "lng": c.lng,
        "note": c.note,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def nap(db, id_):
    c = db.query(Customer).filter(Customer.id == id_).first()
    if not c:
        raise LoiNghiepVu("CUST_NOT_FOUND", f"Không tìm thấy khách hàng {id_}", 404)
    return c


def danh_sach(db, q=None, kind=None):
    cau = db.query(Customer)
    if kind:
        cau = cau.filter(Customer.kind == kind)
    if q:
        tim = f"%{q.strip()}%"
        cau = cau.filter(
            Customer.code.ilike(tim) | Customer.name.ilike(tim) | Customer.address.ilike(tim)
        )
    return [ra_dict(c) for c in cau.order_by(Customer.kind, Customer.name).all()]


def _kiem(payload, bo_qua_id=None, db=None):
    ma = (payload.get("code") or "").strip()
    ten = (payload.get("name") or "").strip()
    if not ma:
        raise LoiNghiepVu("CUST_NO_CODE", "Khách hàng phải có mã")
    if not ten:
        raise LoiNghiepVu("CUST_NO_NAME", "Khách hàng phải có tên")
    kind = payload.get("kind") or "customer"
    if kind not in LOAI:
        raise LoiNghiepVu("CUST_KIND_UNKNOWN", f"Loại không hợp lệ: {kind}")
    trung = db.query(Customer).filter(Customer.code == ma)
    if bo_qua_id:
        trung = trung.filter(Customer.id != bo_qua_id)
    if trung.first():
        raise LoiNghiepVu("CUST_CODE_DUPLICATE", f"Mã {ma} đã tồn tại", 409)
    lat = payload.get("lat")
    lng = payload.get("lng")
    if (lat in (None, "")) != (lng in (None, "")):
        raise LoiNghiepVu("CUST_COORD_HALF", "Toạ độ phải có đủ cả vĩ độ và kinh độ")
    return ma, ten, kind, (float(lat) if lat not in (None, "") else None), (float(lng) if lng not in (None, "") else None)


def tao(db, payload):
    ma, ten, kind, lat, lng = _kiem(payload, db=db)
    c = Customer(
        id=uuid.uuid4().hex[:12].upper(),
        code=ma,
        name=ten,
        kind=kind,
        tax_number=payload.get("tax_number"),
        address=payload.get("address"),
        phone=payload.get("phone"),
        contact_name=payload.get("contact_name"),
        lat=lat,
        lng=lng,
        note=payload.get("note"),
    )
    db.add(c)
    db.flush()
    return c


def sua(db, id_, payload):
    c = nap(db, id_)
    ma, ten, kind, lat, lng = _kiem(payload, bo_qua_id=id_, db=db)
    c.code, c.name, c.kind, c.lat, c.lng = ma, ten, kind, lat, lng
    for k in ("tax_number", "address", "phone", "contact_name", "note"):
        if k in payload:
            setattr(c, k, payload.get(k))
    db.flush()
    return c


def xoa(db, id_):
    c = nap(db, id_)
    dung = db.query(func.count(SalesOrder.id)).filter(SalesOrder.customer_id == id_).scalar() or 0
    if dung:
        raise LoiNghiepVu(
            "CUST_IN_USE",
            "Khách hàng đang có đơn hàng nên không xoá được",
            409,
            {"orders": int(dung)},
        )
    db.delete(c)
    db.flush()
    return True
