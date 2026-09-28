# -*- coding: utf-8 -*-
"""Lệnh sửa chữa riêng — ໃບສັ່ງສ້ອມແປງ (anh Khampla C7.3, 22/09).

Mục V trên phiếu xuất xe chỉ ghi được cái sửa TRONG một chuyến. Nhưng xe nằm bãi cả tuần để đại tu,
hay bảo dưỡng định kỳ theo số km, thì không có chuyến nào để gắn vào — trước đây họ không khai được
ở đâu cả, tiền sửa đó rơi ra ngoài sổ.

Tờ lệnh sửa chữa đi qua **đúng chuỗi duyệt của mục V**, không đẻ luật mới:

    Tổ sửa chữa NHẬP → KT Chi phí KIỂM → KT Chi phí GHI SỔ → Quỹ tiền mặt CHI

Quy tắc kho của họ giữ nguyên: **có trong kho thì xuất kho** (trừ tồn ngay lúc khai, tờ `PXK_PT`,
định khoản …/1371) · **không có thì mua ngoài** (tới bước chi mới sinh tờ `PC_SC`, định khoản …/4021).
Xe sửa là xe nhà nên vế Nợ là `614` (chi phí sửa chữa), không phải `625`.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (CHUOI_SUA_CHUA, LOAI_SUA_CHUA, TIEN_TE, ExchangeRate, Part, RepairLine,
                    RepairOrder, Supplier, Trip, Vehicle)
from services import chung_tu as CT
from services import kho_ke_toan as KK
from services.bao_mat import nguoi_hien_tai

router = APIRouter()

# Ai làm bước nào — soi đúng bảng QUYEN của mục V trong services/phan_quyen.py
LAM_BUOC = {"verify": ("expacct",), "book": ("expacct",), "pay": ("cash",)}
KE_TIEP = {"entered": "verify", "verified": "book", "booked": "pay"}


def _so(v, ten, mac_dinh=None):
    if v in (None, ""):
        return mac_dinh
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số, nhận '%s'." % (ten, v)})


def _ngay(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


def _so_moi(db, ngay):
    dau = "LSC-%s-" % ngay.strftime("%y%m")
    n = db.query(func.count(RepairOrder.id)).filter(RepairOrder.doc_no.like(dau + "%")).scalar() or 0
    for _lan in range(300):
        n += 1
        so = "%s%02d" % (dau, n)
        if db.query(RepairOrder).filter(RepairOrder.doc_no == so).first() is None:
            return so
    raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Không cấp được số lệnh sửa chữa, thử lại giúp em."})


def _dong(db, o):
    return db.query(RepairLine).filter(RepairLine.order_id == o.id).order_by(RepairLine.line_no).all()


_TY_GIA_DU_PHONG = {"USD": 22000, "THB": 700, "VND": 1.2, "CNY": 3000, "LAK": 1}


def _ty_gia(db, ma):
    """Lệnh sửa chữa KHÔNG gắn phiếu nên không có tỷ giá khoá của phiếu — lấy tỷ giá đang áp dụng,
    đúng như mọi chứng từ ngoài phiếu (bán hàng, nhập kho)."""
    ma = (ma or "LAK").upper()
    if ma == "LAK":
        return 1.0
    r = db.get(ExchangeRate, ma)
    return float(r.rate_to_lak) if r and r.rate_to_lak else _TY_GIA_DU_PHONG.get(ma, 1)


def _tien_dong(db, d):
    return (d.qty or 0) * (d.unit_price or 0) * _ty_gia(db, d.currency)


def xuat_dong(db, d):
    return {"id": d.id, "line_no": d.line_no, "item_key": d.item_key, "item_name": d.item_name,
            "qty": d.qty, "unit_price": d.unit_price, "currency": d.currency, "source": d.source,
            "part_id": d.part_id, "stock_move_id": d.stock_move_id, "supplier_id": d.supplier_id,
            "acct_code": d.acct_code, "note": d.note, "tien_lak": round(_tien_dong(db, d))}


def xuat(db, o, day_du=True):
    ds = _dong(db, o)
    r = {"id": o.id, "doc_no": o.doc_no, "vehicle_id": o.vehicle_id, "truck_no": o.truck_no,
         "plate_head": o.plate_head, "order_date": o.order_date.isoformat() if o.order_date else None,
         "kind": o.kind, "odo_km": o.odo_km, "garage": o.garage, "status": o.status, "note": o.note,
         "by_user": o.by_user, "created_at": o.created_at.isoformat() if o.created_at else None,
         "verified_by": o.verified_by, "booked_by": o.booked_by, "paid_by": o.paid_by,
         "so_dong": len(ds), "tong_lak": round(sum(_tien_dong(db, d) for d in ds)),
         "tong_kho_lak": round(sum(_tien_dong(db, d) for d in ds if d.source == "kho")),
         "tong_mua_lak": round(sum(_tien_dong(db, d) for d in ds if d.source != "kho"))}
    if day_du:
        r["lines"] = [xuat_dong(db, d) for d in ds]
        c = CT.tim(db, "PC_SC", "repair_orders", o.id)
        r["chung_tu"] = c.so if c is not None else None
    return r


def _sua_duoc(user, o):
    """Tổ sửa chữa sửa tờ của mình khi còn ở 'đã nhập'; kiểm rồi thì phải trả lại mới sửa."""
    if user.role == "admin":
        return
    if user.role != "repair":
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tổ sửa chữa Thà Bốc nhập lệnh sửa chữa."})
    if o is not None and o.status != "entered":
        raise HTTPException(409, {"ma": "DA_KIEM", "loi": "Lệnh %s đã kiểm (%s); phải trả lại mới sửa được." % (o.doc_no, o.status)})


# ---------------------------------------------------------------- dòng chi
def _ap_dong(db, o, cac_dong, user, gd):
    """Ghi lại toàn bộ dòng chi của lệnh. Dòng đã XUẤT KHO thì không cho xoá — tồn kho đã giảm thật.
    Kho phụ tùng ở trang kế toán (28/09): dòng lấy kho xuất qua `gd` (KK.GiaoDichKho) — bên kia kiểm tồn, trừ tồn và
    sinh PXK_PT; lần lưu bên này hỏng thì lần xuất bên kia được huỷ."""
    cu = {d.id: d for d in _dong(db, o)}
    giu = set()
    for i, x in enumerate([d for d in (cac_dong or []) if d], 1):
        d = cu.get(str(x.get("id") or ""))
        moi = d is None
        if moi:
            d = RepairLine(order_id=o.id)
            db.add(d)
        elif d.stock_move_id:
            giu.add(d.id)                 # dòng đã xuất kho: giữ nguyên, không sửa số lượng
            continue
        d.line_no = i
        d.item_key = (x.get("item_key") or "").strip() or None
        d.item_name = (x.get("item_name") or "").strip() or None
        d.qty = _so(x.get("qty"), "qty", 1) or 1
        d.unit_price = _so(x.get("unit_price"), "unit_price", 0) or 0
        d.currency = str(x.get("currency") or "LAK").upper()
        if d.currency not in TIEN_TE:
            raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền tệ phải là một trong %s." % ", ".join(TIEN_TE)})
        d.source = "kho" if x.get("source") == "kho" else "mua"
        d.note = (x.get("note") or "").strip() or None
        if x.get("supplier_id"):
            if not db.get(Supplier, str(x["supplier_id"])):
                raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có nhà cung cấp này."})
            d.supplier_id = str(x["supplier_id"])
        if d.source == "kho":
            pt = db.get(Part, str(x.get("part_id") or ""))           # bản chép danh mục — tồn, giá ở trang kế toán
            if not pt:
                raise HTTPException(422, {"ma": "THIEU_PHU_TUNG", "loi": "Lấy từ kho thì phải chọn phụ tùng."})
            d.part_id = pt.id
            if not d.item_name:
                d.item_name = pt.name
            if not d.unit_price:
                d.unit_price = KK.gia_phu_tung(db, pt.id)
        else:
            d.part_id = None
            if not (d.item_key or d.item_name):
                raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Dòng mua ngoài phải ghi tên khoản sửa."})
        # Xe nhà: sửa chữa ghi Nợ 614; kho …/1371, mua ngoài …/4021 (mã anh Khampla cấp 22/09).
        d.acct_code = "614/1371" if d.source == "kho" else "614/4021"
        db.flush()
        giu.add(d.id)
    for d in cu.values():
        if d.id in giu:
            continue
        if d.stock_move_id:
            raise HTTPException(409, {"ma": "DA_XUAT_KHO",
                                      "loi": "Dòng '%s' đã xuất kho, không xoá khỏi lệnh được. Nhờ thủ kho nhập lại rồi mới sửa." % (d.item_name or d.item_key or "")})
        db.delete(d)
    db.flush()
    # Xuất kho NGAY LÚC KHAI, như dòng sửa chữa trên phiếu: tồn kho phải nói đúng cái đang có thật.
    for d in _dong(db, o):
        if d.source != "kho" or d.stock_move_id:
            continue
        pt = db.get(Part, d.part_id)
        # trang kế toán kiểm tồn (không đủ → 409 nguyên câu), trừ tồn, ghi sổ kho, sinh PXK_PT (Nợ 614 / Có 1371)
        r = gd.xuat_phu_tung(khoa="repair_line:" + d.id, part_id=pt.id, qty=d.qty, ngay=o.order_date or dt.date.today(),
                             gia=d.unit_price, tien_te=d.currency, ty_gia=_ty_gia(db, d.currency), truck_no=o.truck_no,
                             trip_doc_no=o.doc_no, company="EPL", section="repair", repair_order=o.doc_no,
                             mo_ta="Xuất %s %s cho lệnh sửa chữa %s (xe %s)" % (d.qty, pt.name, o.doc_no, o.truck_no or ""),
                             note="Lệnh sửa chữa %s" % o.doc_no)
        d.stock_move_id = r["move_id"]


# ---------------------------------------------------------------- danh sách & xem
@router.get("/api/lenh-sua-chua")
def ds_lenh(vehicle_id: str = "", thang: str = "", status: str = "",
            db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    q = db.query(RepairOrder)
    if vehicle_id:
        q = q.filter(RepairOrder.vehicle_id == vehicle_id)
    if status:
        q = q.filter(RepairOrder.status == status)
    ds = q.order_by(RepairOrder.order_date.desc(), RepairOrder.doc_no.desc()).all()
    if thang:
        ds = [o for o in ds if o.order_date and o.order_date.strftime("%Y-%m") == thang[:7]]
    return [xuat(db, o, day_du=False) for o in ds]


@router.get("/api/lenh-sua-chua/{oid}")
def xem_lenh(oid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    o = db.get(RepairOrder, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lệnh sửa chữa này."})
    return xuat(db, o)


@router.post("/api/lenh-sua-chua")
def lap_lenh(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _sua_duoc(user, None)
    x = db.get(Vehicle, str(data.get("vehicle_id") or ""))
    if not x:
        raise HTTPException(422, {"ma": "THIEU_XE", "loi": "Lệnh sửa chữa phải gắn một chiếc xe."})
    loai = (data.get("kind") or "sua_chua").strip()
    if loai not in LOAI_SUA_CHUA:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Loại phải là %s." % " · ".join(LOAI_SUA_CHUA)})
    ngay = _ngay(data.get("order_date")) or dt.date.today()
    o = RepairOrder(doc_no=_so_moi(db, ngay), vehicle_id=x.id, truck_no=x.truck_no, plate_head=x.plate_head,
                    order_date=ngay, kind=loai, odo_km=_so(data.get("odo_km"), "odo_km", x.odometer_km),
                    garage=(data.get("garage") or "").strip() or None,
                    note=(data.get("note") or "").strip() or None, by_user=user.full_name)
    with KK.GiaoDichKho(db, user) as gd:
        db.add(o); db.flush()
        _ap_dong(db, o, data.get("lines"), user, gd)
        # Xe vào xưởng thì danh mục xe phải nói đúng như vậy — điều xe nhìn vào đó mà xếp chuyến.
        if x.status not in ("inactive", "on_trip"):
            x.status = "maintenance"
    return xuat(db, o)


@router.put("/api/lenh-sua-chua/{oid}")
def sua_lenh(oid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    o = db.get(RepairOrder, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lệnh sửa chữa này."})
    _sua_duoc(user, o)
    if "order_date" in data:
        o.order_date = _ngay(data.get("order_date")) or o.order_date
    if "kind" in data:
        if data["kind"] not in LOAI_SUA_CHUA:
            raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Loại phải là %s." % " · ".join(LOAI_SUA_CHUA)})
        o.kind = data["kind"]
    for c in ("garage", "note"):
        if c in data:
            setattr(o, c, (data[c] or "").strip() or None)
    if "odo_km" in data:
        o.odo_km = _so(data.get("odo_km"), "odo_km")
    with KK.GiaoDichKho(db, user) as gd:
        if "lines" in data:
            _ap_dong(db, o, data.get("lines"), user, gd)
    return xuat(db, o)


@router.delete("/api/lenh-sua-chua/{oid}")
def xoa_lenh(oid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    o = db.get(RepairOrder, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lệnh sửa chữa này."})
    _sua_duoc(user, o)
    if any(d.stock_move_id for d in _dong(db, o)):
        raise HTTPException(409, {"ma": "DA_XUAT_KHO", "loi": "Lệnh %s đã xuất kho phụ tùng, không xoá được." % o.doc_no})
    db.delete(o); db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- chuỗi duyệt (như mục V)
@router.post("/api/lenh-sua-chua/{oid}/{hanh_dong}")
def duyet(oid: str, hanh_dong: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """`verify` · `book` · `pay` — và `return` để trả lại cho tổ sửa chữa sửa tiếp."""
    o = db.get(RepairOrder, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lệnh sửa chữa này."})
    if hanh_dong == "return":
        if user.role not in ("expacct", "admin"):
            raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Chi phí VC trả lại lệnh sửa chữa."})
        if o.status not in ("verified", "booked"):
            raise HTTPException(409, {"ma": "SAI_BUOC", "loi": "Lệnh đang ở '%s', không trả lại được." % o.status})
        if o.status == "booked":
            CT.rut(db, nguon_bang="repair_orders", nguon_id=o.id)
        o.status, o.verified_by, o.verified_at = "entered", None, None
        o.booked_by, o.booked_at = None, None
        db.commit()
        return xuat(db, o)
    if hanh_dong not in LAM_BUOC:
        raise HTTPException(422, {"ma": "HANH_DONG_SAI", "loi": "Không có hành động %s." % hanh_dong})
    if user.role != "admin" and user.role not in LAM_BUOC[hanh_dong]:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không được %s lệnh sửa chữa." % (user.role, hanh_dong)})
    if KE_TIEP.get(o.status) != hanh_dong:
        raise HTTPException(409, {"ma": "SAI_BUOC", "loi": "Lệnh đang ở '%s', không thể %s." % (o.status, hanh_dong)})
    ds = _dong(db, o)
    if not ds:
        raise HTTPException(409, {"ma": "LENH_TRONG", "loi": "Lệnh %s chưa có dòng chi nào." % o.doc_no})
    bay_gio = dt.datetime.utcnow()
    o.status = CHUOI_SUA_CHUA[CHUOI_SUA_CHUA.index(o.status) + 1]
    if hanh_dong == "verify":
        o.verified_by, o.verified_at = user.full_name, bay_gio
    elif hanh_dong == "book":
        o.booked_by, o.booked_at = user.full_name, bay_gio
    else:
        o.paid_by, o.paid_at = user.full_name, bay_gio
        # Chỉ khoản MUA NGOÀI mới phải chi tiền; dòng lấy kho đã có tờ PXK_PT riêng lúc khai.
        mua = [d for d in ds if d.source != "kho"]
        tong = round(sum(_tien_dong(db, d) for d in mua))
        if tong > 0:
            CT.ghi(db, "PC_SC", nguon_bang="repair_orders", nguon_id=o.id, ngay=dt.date.today(),
                   doi_tuong_loai="ncc", doi_tuong_ten=o.garage or "Gara ngoài", tien=tong, tien_te="LAK",
                   tien_lak=tong, section="repair", phuong_thuc="cash", by_user=user.full_name,
                   mo_ta="Chi lệnh sửa chữa %s · xe %s" % (o.doc_no, o.truck_no or ""),
                   payload={"doc_no": o.doc_no, "truck_no": o.truck_no, "kind": o.kind, "garage": o.garage,
                            "lines": [{"item": d.item_key or d.item_name, "qty": d.qty, "unit_price": d.unit_price,
                                       "currency": d.currency, "acct_code": d.acct_code} for d in mua]})
        # Sửa xong, xe về rảnh — trừ khi đang chạy chuyến khác hoặc đã ngưng dùng.
        x = db.get(Vehicle, o.vehicle_id) if o.vehicle_id else None
        if x is not None and x.status == "maintenance":
            dang_chay = db.query(Trip.id).filter(Trip.vehicle_id == x.id, Trip.transport_status != "arrived").first()
            x.status = "on_trip" if dang_chay else "available"
    db.commit()
    return xuat(db, o)
