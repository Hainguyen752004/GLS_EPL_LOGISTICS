# -*- coding: utf-8 -*-
"""Theo dõi nhà cung cấp — ຕິດຕາມຜູ້ສະໜອງ. Phí chip Lào/Việt, lốp, cầu đường… trả theo tháng.

Nợ phải trả = tổng các dòng chi trên phiếu có khoản mục của nhà cung cấp đó (và EPL ứng)
− các lần đã thanh toán. Tính lại mỗi lần gọi từ phiếu, không giữ số dư riêng.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Supplier, SupplierPayment, Trip, TripExpense
from services import chung_tu as CT
from services.bao_mat import can_vai, nguoi_hien_tai
from services.tinh_toan import tien_dong

router = APIRouter()


def _xuat(db, s):
    phat_sinh = 0.0; so_dong = 0
    if s.item_key:
        for d, p in (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
                     .filter(TripExpense.item_key == s.item_key, TripExpense.paid_by_epl.is_(True)).all()):
            phat_sinh += tien_dong(p, d); so_dong += 1
    da_tra = sum(x.amount_lak or 0 for x in db.query(SupplierPayment).filter(SupplierPayment.supplier_id == s.id).all())
    return {"id": s.id, "name": s.name, "item_key": s.item_key, "acct_code": s.acct_code,
            "payment_term": s.payment_term, "note": s.note, "active": s.active,
            "so_dong": so_dong, "phat_sinh_lak": round(phat_sinh), "da_tra_lak": round(da_tra),
            "con_no_lak": round(phat_sinh - da_tra)}


@router.get("/api/suppliers")
def ds(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_xuat(db, s) for s in db.query(Supplier).order_by(Supplier.active.desc(), Supplier.name).all()]


@router.post("/api/suppliers")
def them(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("expacct"))):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Nhà cung cấp phải có tên."})
    s = Supplier(name=data["name"].strip(), item_key=data.get("item_key"), acct_code=data.get("acct_code"),
                 payment_term=data.get("payment_term") or "t_monthly", note=data.get("note"))
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
    db.commit(); db.refresh(s)
    return _xuat(db, s)


@router.get("/api/suppliers/{sid}/payments")
def cac_lan_tra(sid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
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
