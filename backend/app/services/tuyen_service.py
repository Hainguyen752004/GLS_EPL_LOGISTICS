"""Danh mục Tuyến đường.

Nguồn cho ô "Tuyến giao" trên phiếu đóng gói, và là nơi màn Theo dõi lấy điểm
đầu - điểm cuối để vẽ đường xe. Khai một lần, mọi phiếu chọn lại.
"""

import uuid

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from models import Customer, PackingList, Route, RouteSegment
from services.loi import LoiNghiepVu


def ra_dict(db, r):
    """Tuyến kèm đủ các chặng và toạ độ để bản đồ vẽ được lộ trình."""
    diem = {}
    can = [x for c in r.segments for x in (c.from_id, c.to_id) if x]
    if can:
        for kh in db.query(Customer).filter(Customer.id.in_(set(can))).all():
            diem[kh.id] = kh

    chang = []
    for c in r.segments:
        di = diem.get(c.from_id)
        den = diem.get(c.to_id)
        chang.append({
            "id": c.id,
            "seq": c.seq,
            "from_id": c.from_id,
            "to_id": c.to_id,
            "from_name": c.from_name,
            "to_name": c.to_name,
            "distance_km": c.distance_km,
            "from_lat": di.lat if di else None,
            "from_lng": di.lng if di else None,
            "to_lat": den.lat if den else None,
            "to_lng": den.lng if den else None,
        })

    return {
        "id": r.id,
        "code": r.code,
        "name": r.name,
        "distance_km": tong_km(r),
        "note": r.note,
        "active": bool(r.active),
        "created_at": r.created_at,
        "segments": chang,
        "segment_count": len(chang),
        # Điểm đầu và điểm cuối của CẢ tuyến, suy từ chặng đầu và chặng cuối.
        "from_id": r.segments[0].from_id if r.segments else None,
        "to_id": r.segments[-1].to_id if r.segments else None,
        "from_name": r.segments[0].from_name if r.segments else None,
        "to_name": r.segments[-1].to_name if r.segments else None,
        "from_lat": chang[0]["from_lat"] if chang else None,
        "from_lng": chang[0]["from_lng"] if chang else None,
        "to_lat": chang[-1]["to_lat"] if chang else None,
        "to_lng": chang[-1]["to_lng"] if chang else None,
    }


def tong_km(r):
    """Tổng km LÀ tổng các chặng — không ai gõ tay một con số rồi quên sửa."""
    if r.segments:
        return round(sum(c.distance_km for c in r.segments), 2)
    return r.distance_km or 0


def nap(db, id_):
    r = db.query(Route).options(selectinload(Route.segments)).filter(Route.id == id_).first()
    if not r:
        raise LoiNghiepVu("RT_NOT_FOUND", f"Không tìm thấy tuyến đường {id_}", 404)
    return r


def danh_sach(db, q=None, chi_dang_dung=False):
    cau = db.query(Route).options(selectinload(Route.segments))
    if chi_dang_dung:
        cau = cau.filter(Route.active == 1)
    if q:
        tim = f"%{q.strip()}%"
        cau = cau.filter(Route.code.ilike(tim) | Route.name.ilike(tim))
    return [ra_dict(db, r) for r in cau.order_by(Route.code).all()]


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
    return ma, ten


def _doc_chang(db, payload):
    """Đọc và kiểm danh sách chặng. Tuyến phải có ít nhất một chặng."""
    vao = payload.get("segments")
    if vao is None:
        return None
    if not vao:
        raise LoiNghiepVu("RT_NO_SEGMENT", "Tuyến đường phải có ít nhất một chặng")

    # Tra tên địa điểm về id để lấy toạ độ — người dùng gõ tên tự do vẫn nhận.
    ds_diem = db.query(Customer).all()
    theo_ten = {}
    for kh in ds_diem:
        theo_ten[(kh.name or "").strip().lower()] = kh
        theo_ten[(kh.code or "").strip().lower()] = kh

    ra = []
    for i, c in enumerate(vao, start=1):
        ten_di = (c.get("from_name") or "").strip()
        ten_den = (c.get("to_name") or "").strip()
        if not ten_di or not ten_den:
            raise LoiNghiepVu("RT_SEGMENT_NO_POINT", f"Chặng {i} thiếu điểm đi hoặc điểm đến")
        km = float(c.get("distance_km") or 0)
        if km < 0:
            raise LoiNghiepVu("RT_KM_NEGATIVE", "Số km không được âm")

        di_id = c.get("from_id") or None
        den_id = c.get("to_id") or None
        if not di_id:
            kh = theo_ten.get(ten_di.lower())
            di_id = kh.id if kh else None
        if not den_id:
            kh = theo_ten.get(ten_den.lower())
            den_id = kh.id if kh else None
        for khoa in (di_id, den_id):
            if khoa and not any(x.id == khoa for x in ds_diem):
                raise LoiNghiepVu("CUST_NOT_FOUND", "Không tìm thấy địa điểm đã chọn", 404)

        ra.append({
            "seq": i,
            "from_id": di_id, "to_id": den_id,
            "from_name": ten_di, "to_name": ten_den,
            "distance_km": km,
        })
    return ra


def _ghi_chang(db, r, chang):
    if chang is None:
        return
    for c in list(r.segments):
        db.delete(c)
    db.flush()
    r.segments = [RouteSegment(route_id=r.id, **c) for c in chang]
    db.flush()
    r.distance_km = round(sum(c["distance_km"] for c in chang), 2)


def tao(db, payload):
    ma, ten = _kiem(db, payload)
    chang = _doc_chang(db, payload)
    if chang is None:
        raise LoiNghiepVu("RT_NO_SEGMENT", "Tuyến đường phải có ít nhất một chặng")
    r = Route(
        id=uuid.uuid4().hex[:12].upper(),
        code=ma,
        name=ten,
        note=payload.get("note"),
        active=1 if payload.get("active", True) else 0,
        distance_km=0,
    )
    db.add(r)
    db.flush()
    _ghi_chang(db, r, chang)
    return r


def sua(db, id_, payload):
    r = nap(db, id_)
    ma, ten = _kiem(db, payload, bo_qua_id=id_)
    r.code, r.name = ma, ten
    if "note" in payload:
        r.note = payload.get("note")
    if "active" in payload:
        r.active = 1 if payload.get("active") else 0
    _ghi_chang(db, r, _doc_chang(db, payload))
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
