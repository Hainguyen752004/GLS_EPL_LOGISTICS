# -*- coding: utf-8 -*-
"""Điểm cuối CRM: cơ hội khách hàng (CRM-01) và hồ sơ khách (CRM-02).

Router mang dependency xác thực ở TẦNG ROUTER — cùng lý do `bao_gia_routes.py`.
Mọi đường GHI đi qua `_lenh` để commit / rollback / đổi lỗi ở một chỗ.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from routes.finance_master_routes import require_authenticated_principal
from services import co_hoi_service as crm
from services.errors import DomainError, conflict, raise_http

router = APIRouter(dependencies=[Depends(require_authenticated_principal)])


def _actor(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    if isinstance(principal, str) and principal.strip():
        return principal.strip()
    if isinstance(principal, dict):
        for ten in ("id", "sub", "username"):
            if str(principal.get(ten) or "").strip():
                return str(principal[ten]).strip()
    raise_http(DomainError("AUTHENTICATION_REQUIRED",
                           "Không xác định được người dùng đã xác thực.", 401))


def _lenh(db: Session, viec, thong_bao: str):
    try:
        du_lieu = viec()
        db.commit()
        return {"message": thong_bao, "data": du_lieu}
    except DomainError as loi:
        db.rollback()
        raise_http(loi)
    except IntegrityError:
        db.rollback()
        raise_http(conflict("CRM_CONFLICT", "Dữ liệu vừa được người khác sửa. Tải lại rồi thử lại."))


def _doc(viec, thong_bao):
    try:
        return {"message": thong_bao, "data": viec()}
    except DomainError as loi:
        raise_http(loi)


# ------------------------------------------------------------------ CƠ HỘI --

@router.get("/api/crm/opportunities/summary")
def dai_so_lieu(db: Session = Depends(get_db)):
    return _doc(lambda: crm.dai_so_lieu(db), "Đã tải số liệu cơ hội.")


@router.get("/api/crm/opportunities/board")
def bang_co_hoi(per_col: int = Query(10, ge=1, le=50), since_days: int = Query(7, ge=0, le=3650),
                owner: Optional[str] = Query(None), q: Optional[str] = Query(None),
                source: Optional[str] = Query(None), due: Optional[str] = Query(None),
                db: Session = Depends(get_db)):
    """Bảng theo cột: số đếm thật + N thẻ đầu mỗi cột. Khai TRƯỚC `/{ma}`."""
    return _doc(lambda: crm.bang_co_hoi(db, per_col=per_col, since_days=since_days, owner=owner, q=q, source=source, due=due),
                "Đã tải bảng cơ hội.")


@router.get("/api/crm/opportunities")
def danh_sach(stage: Optional[str] = Query(None), owner: Optional[str] = Query(None),
              customer_id: Optional[str] = Query(None), q: Optional[str] = Query(None),
              page: Optional[int] = Query(None, ge=1), page_size: int = Query(50, ge=1, le=200),
              since_days: Optional[int] = Query(None, ge=0), source: Optional[str] = Query(None),
              due: Optional[str] = Query(None), sort: Optional[str] = Query(None),
              db: Session = Depends(get_db)):
    return _doc(lambda: crm.danh_sach(db, stage=stage, owner=owner, customer_id=customer_id, q=q,
                                      page=page, page_size=page_size, since_days=since_days,
                                      source=source, due=due, sort=sort),
                "Đã tải danh sách cơ hội.")


@router.post("/api/crm/opportunities")
def tao(request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    actor = _actor(request)
    return _lenh(db, lambda: crm.tao(db, data, actor), "Đã ghi nhận cơ hội.")


@router.get("/api/crm/opportunities/{ma}")
def chi_tiet(ma: str, db: Session = Depends(get_db)):
    return _doc(lambda: crm.chi_tiet(db, ma), "Đã tải cơ hội.")


@router.put("/api/crm/opportunities/{ma}")
def sua(ma: str, request: Request, data: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    actor = _actor(request)
    return _lenh(db, lambda: crm.sua(db, ma, data, actor), "Đã lưu cơ hội.")


@router.put("/api/crm/opportunities/{ma}/stage")
def doi_giai_doan(ma: str, request: Request, data: Dict[str, Any] = Body(...),
                        db: Session = Depends(get_db)):
    actor = _actor(request)
    return _lenh(db, lambda: crm.doi_giai_doan(
        db, ma, data.get("stage"), actor, data.get("expected_version"), data.get("lost_reason")),
        "Đã chuyển giai đoạn.")


@router.post("/api/crm/opportunities/{ma}/quotation")
def lap_bao_gia(ma: str, request: Request, data: Dict[str, Any] = Body(default={}),
                      db: Session = Depends(get_db)):
    actor = _actor(request)
    return _lenh(db, lambda: crm.lap_bao_gia(db, ma, actor, (data or {}).get("expected_version"),
                                              int((data or {}).get("valid_days") or 30)),
                 "Đã lập báo giá nháp từ cơ hội.")


# ------------------------------------------------------------- HỒ SƠ KHÁCH --

@router.get("/api/crm/customers")
def danh_sach_khach(q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return _doc(lambda: crm.danh_sach_khach(db, q), "Đã tải danh sách khách hàng.")


@router.get("/api/crm/customers/{customer_id}/profile")
def ho_so_khach(customer_id: str, db: Session = Depends(get_db)):
    return _doc(lambda: crm.ho_so_khach(db, customer_id), "Đã tải hồ sơ khách hàng.")
