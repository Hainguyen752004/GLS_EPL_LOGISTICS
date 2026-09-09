# -*- coding: utf-8 -*-
"""Diem cuoi cho phieu THU / phieu CHI gan vao lenh giao hang.

Day cung la duong ma he CONG NO KHACH HANG cua ben doi tac doc: moi dong phieu
mang mot ma KHOAN MUC (`charge_type`) dung bang danh sach cua bang chi phi thuc
te, nen hai ben doi chieu duoc ma khong phai anh xa hai bo ma.
"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from services import phieu_thu_chi_service as svc
from services.errors import DomainError, conflict, raise_http

router = APIRouter(prefix="/api/do-vouchers", tags=["Phieu thu chi"])


def _actor(request: Request) -> str:
    """Nguoi dang thao tac, lay tu phien da xac thuc — KHONG lay tu payload.

    Mot ma nguoi dung do may khach tu khai thi ai cung ghi duoc phieu duoi ten
    nguoi khac, va voi mot chung tu tien te thi do la lo hong nghiem trong nhat.
    """
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        gia_tri = principal.get("id") or principal.get("sub") or principal.get("username")
        if gia_tri:
            return str(gia_tri)
    return "system"


def _bung(phieu):
    """Tra ve phieu kem cac dong, du de he cong no doc mot lan la xong."""
    goi = jsonable_encoder(phieu, exclude={"lines"})
    goi["lines"] = [{
        "id": d.id,
        "charge_type": d.charge_type,
        "ten_khoan_muc": svc.TEN_KHOAN_MUC.get(d.charge_type, d.charge_type),
        "description": d.description,
        "amount": float(d.amount or 0),
        "note": d.note,
    } for d in sorted(phieu.lines, key=lambda x: svc.KHOAN_MUC.index(x.charge_type)
                      if x.charge_type in svc.KHOAN_MUC else 99)]
    goi["total_amount"] = float(phieu.total_amount or 0)
    return goi


def _lam(db, viec):
    try:
        ket_qua = viec()
        db.commit()
        return ket_qua
    except DomainError as loi:
        db.rollback()
        raise_http(loi)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("DUPLICATE_VOUCHER",
                            "Số phiếu đã tồn tại. Để trống số phiếu thì hệ thống "
                            "tự cấp số theo tháng."))


@router.get("/khoan-muc")
def danh_muc_khoan_muc():
    """Danh muc KHOAN MUC de dung lam o chon tren man hinh.

    Tra ve tu MOT nguon: `phieu_thu_chi_service.KHOAN_MUC`, cung danh sach ma
    `freight_charge_items.charge_type` dung. Man hinh khong duoc tu liet ke lai —
    liet ke lai la tao mot ban thu hai roi hai ban troi khoi nhau.
    """
    return {"data": [{"ma": m, "ten": svc.TEN_KHOAN_MUC.get(m, m),
                      "la_chi_phi_chung_chuyen": m in svc.KHOAN_MUC_CHUNG_CHUYEN}
                     for m in svc.KHOAN_MUC]}


@router.get("")
def danh_sach(do_id: Optional[str] = Query(None), kind: Optional[str] = Query(None),
              trip_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    ds = svc.danh_sach_phieu(db, do_id=do_id, kind=kind, trip_id=trip_id)
    return {"data": {"items": [_bung(p) for p in ds], "total": len(ds)}}


@router.get("/goi-y/{do_id}")
def goi_y(do_id: str, db: Session = Depends(get_db)):
    """"Chi cho DO nay thi can nhung phieu gi" — doc tu chi phi THUC TE.

    Chi GOI Y, khong tao phieu. Nguoi dung xem, sua, roi bam tao — vi con so
    phan bo la thu ho phai chiu trach nhiem, nen ho phai thay truoc khi ghi.
    """
    try:
        return {"data": svc.goi_y_phieu_chi(db, do_id)}
    except DomainError as loi:
        raise_http(loi)


@router.get("/{ma}")
def mot(ma: str, db: Session = Depends(get_db)):
    try:
        return {"data": _bung(svc.mot_phieu(db, ma))}
    except DomainError as loi:
        raise_http(loi)


@router.post("")
def tao(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    actor = _actor(request)
    phieu = _lam(db, lambda: svc.tao_phieu(db, data, actor))
    return {"message": "Đã lập %s %s." % (
        "phiếu chi" if phieu.kind == "chi" else "phiếu thu", phieu.voucher_no),
        "data": _bung(phieu)}


@router.put("/{ma}/ghi-so")
def ghi_so(ma: str, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request)
    phieu = _lam(db, lambda: svc.ghi_so(db, ma, actor))
    return {"message": "Đã ghi sổ phiếu %s." % phieu.voucher_no, "data": _bung(phieu)}


@router.put("/{ma}/huy")
def huy(ma: str, request: Request, data: dict = Body(default={}),
        db: Session = Depends(get_db)):
    actor = _actor(request)
    phieu = _lam(db, lambda: svc.huy_phieu(db, ma, (data or {}).get("ly_do"), actor))
    return {"message": "Đã huỷ phiếu %s." % phieu.voucher_no, "data": _bung(phieu)}
