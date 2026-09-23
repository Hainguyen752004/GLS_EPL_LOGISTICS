# -*- coding: utf-8 -*-
"""Theo dõi nhà cung cấp — ຕິດຕາມຜູ້ສະໜອງ. Phí chip Lào/Việt, lốp, cầu đường… trả theo tháng.

Nợ phải trả = tổng các dòng chi trên phiếu có khoản mục của nhà cung cấp đó (và EPL ứng)
− các lần đã thanh toán. Tính lại mỗi lần gọi từ phiếu, không giữ số dư riêng.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Supplier, SupplierPayment, Trip, TripExpense
from services import chung_tu as CT
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi
from services.tinh_toan import tien_dong

router = APIRouter()


def _dong_cua(db, s, dau=None, sau=None):
    """Các dòng chi thuộc về nhà cung cấp này.

    Hai đường vào, cố ý khác nhau:
      · dòng **ghi rõ nhà cung cấp** (`supplier_id`) — chỉ tính khi **GHI NỢ tại trạm** (C5.1): tài xế
        đổ dầu ở Việt Nam mà chưa trả tiền. Tài xế đã trả tiền mặt tại trạm thì EPL không nợ ai cả.
      · dòng chỉ có **khoản mục** trùng (`item_key`, ví dụ phí chip) — cách cũ, giữ nguyên.
    """
    q = (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
         .filter(TripExpense.paid_by_epl.is_(True)))
    ra = []
    for d, p in q.all():
        if dau is not None and (not p.doc_date or not (dau <= p.doc_date < sau)):
            continue
        if d.supplier_id == s.id:
            if d.ghi_no:
                ra.append((d, p))
        elif d.supplier_id is None and s.item_key and d.item_key == s.item_key:
            ra.append((d, p))
    return ra


def _xuat(db, s):
    dong = _dong_cua(db, s)
    phat_sinh = sum(tien_dong(p, d) for d, p in dong)
    ghi_no = sum(tien_dong(p, d) for d, p in dong if d.ghi_no)
    da_tra = sum(x.amount_lak or 0 for x in db.query(SupplierPayment).filter(SupplierPayment.supplier_id == s.id).all())
    return {"id": s.id, "name": s.name, "item_key": s.item_key, "acct_code": s.acct_code,
            "payment_term": s.payment_term, "note": s.note, "active": s.active,
            "customer_id": s.customer_id, "customer_name": s.customer_name,
            "so_dong": len(dong), "phat_sinh_lak": round(phat_sinh), "ghi_no_lak": round(ghi_no),
            "da_tra_lak": round(da_tra), "con_no_lak": round(phat_sinh - da_tra)}


def _ap_khach(db, s, data):
    """Trạm dầu Việt Nam cuối tháng cấn trừ vào cước của khách nào (C5.1)."""
    if "customer_id" not in data:
        return
    kh = db.get(Customer, str(data["customer_id"])) if data["customer_id"] else None
    if data["customer_id"] and not kh:
        raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    s.customer_id, s.customer_name = (kh.id, kh.name) if kh else (None, None)


@router.get("/api/suppliers")
def ds(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    ra = [_xuat(db, s) for s in db.query(Supplier).order_by(Supplier.active.desc(), Supplier.name).all()]
    if not thay_tien_chi(user.role):
        # Bãi không thấy tiền, không thấy mã tài khoản (anh Khampla A2); chủ dự án chốt 23/09: màn Theo dõi NCC
        # của Bãi giữ danh sách · số dòng · kỳ trả, bỏ cột tiền. Trả NCC là việc kế toán và quỹ.
        for r in ra:
            for k in ("phat_sinh_lak", "ghi_no_lak", "da_tra_lak", "con_no_lak", "acct_code"):
                r.pop(k, None)
    return ra


@router.post("/api/suppliers")
def them(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("expacct"))):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Nhà cung cấp phải có tên."})
    s = Supplier(name=data["name"].strip(), item_key=data.get("item_key"), acct_code=data.get("acct_code"),
                 payment_term=data.get("payment_term") or "t_monthly", note=data.get("note"))
    _ap_khach(db, s, data)
    db.add(s); db.commit(); db.refresh(s)
    return _xuat(db, s)


@router.put("/api/suppliers/{sid}")
def sua(sid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("expacct"))):
    s = db.get(Supplier, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có nhà cung cấp này."})
    for k in ("name", "item_key", "acct_code", "payment_term", "note", "active"):
        if k in data:
            setattr(s, k, data[k].strip() if isinstance(data[k], str) else data[k])
    _ap_khach(db, s, data)
    db.commit(); db.refresh(s)
    return _xuat(db, s)


@router.get("/api/suppliers/{sid}/payments")
def cac_lan_tra(sid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if not thay_tien_chi(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Bãi không xem các lần trả nhà cung cấp."})
    return [{"id": x.id, "pay_date": x.pay_date.isoformat(), "amount_lak": x.amount_lak, "note": x.note, "by_user": x.by_user}
            for x in db.query(SupplierPayment).filter(SupplierPayment.supplier_id == sid)
            .order_by(SupplierPayment.pay_date.desc()).all()]


@router.post("/api/suppliers/{sid}/payments")
def tra(sid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(can_vai("expacct", "cash", "treasury"))):
    s = db.get(Supplier, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có nhà cung cấp này."})
    try:
        tien = float(str(data.get("amount_lak")).replace(",", ""))
    except (TypeError, ValueError):
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số tiền phải là số."})
    if tien <= 0:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số tiền phải lớn hơn 0."})
    try:
        ngay = dt.date.fromisoformat(str(data.get("pay_date") or dt.date.today())[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD."})
    tra_ncc = SupplierPayment(supplier_id=s.id, pay_date=ngay, amount_lak=tien, note=data.get("note"), by_user=user.full_name)
    db.add(tra_ncc); db.flush()
    CT.ghi(db, "PC_NCC", nguon_bang="supplier_payments", nguon_id=tra_ncc.id, ngay=ngay, doi_tuong_loai="ncc", phuong_thuc="cash",
           doi_tuong_ten=s.name, tien=tien, tien_te="LAK", by_user=user.full_name,
           mo_ta="Trả nhà cung cấp %s%s" % (s.name, (" · " + data["note"]) if data.get("note") else ""),
           payload={"supplier_id": s.id, "item_key": s.item_key, "acct_code": s.acct_code})
    db.commit()
    return _xuat(db, s)
