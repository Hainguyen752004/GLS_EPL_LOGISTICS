# -*- coding: utf-8 -*-
"""Màn KHOẢN MỤC CHI PHÍ (Danh mục, 08/10 — anh Khampla: thêm khoản chi lưu sẵn để dùng lại thay cho "Khác — tự gõ"; chủ dự án chốt
cách trả mặc định theo khoản mục, cấu hình ở đây). Luật ở services/khoan_muc.py.

    GET  /api/khoan-muc/danh-sach   mọi khoản (kể cả đã ngưng) + số dòng đang dùng + quyền
    POST /api/khoan-muc             thêm khoản (mục IV · V · VI; tên ba thứ tiếng; cách trả mặc định ở mục IV, VI)
    PUT  /api/khoan-muc/{id}        sửa tên (khoản thêm mới), cách trả mặc định, thứ tự, đang dùng / ngưng

Đọc danh mục cho phiếu vẫn là GET /api/khoan-muc (routes/phieu.py). Sửa: KT Chi phí VC và Sếp (khoan_muc.VAI_SUA)."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import CostItem
from services import khoan_muc as KMC
from services.bao_mat import can_vai, nguoi_hien_tai
from services.tinh_toan import CACH_TRA

router = APIRouter()
SUA = can_vai(*KMC.VAI_SUA)


def _ten(d, k):
    v = d.get(k)
    return (str(v).strip()[:120] or None) if v is not None else None


def _cach_tra(section, v):
    if section not in KMC.MUC_CACH_TRA:
        return None
    v = (str(v or "").strip() or "tien_mat")
    if v not in CACH_TRA:
        raise HTTPException(422, {"ma": "CACH_TRA_SAI", "loi": "Cách trả phải là chi ngay khi xe đi, trả cùng lương hoặc nợ nhà cung cấp."})
    return v


def _chan_trung_ten(db, section, vi, bo_id=None):
    if not vi:
        return
    for r in db.query(CostItem).filter(CostItem.section == section).all():
        if r.id != bo_id and (r.name_vi or "").strip().lower() == vi.lower():
            raise HTTPException(409, {"ma": "TRUNG_TEN", "loi": "Mục này đã có khoản «%s»." % vi})


@router.get("/api/khoan-muc/danh-sach")
def danh_sach(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    KMC.nap(db)
    rows = db.query(CostItem).order_by(CostItem.section, CostItem.sort, CostItem.key).all()
    return {"items": [dict(KMC.xuat(r), so_dong=KMC.so_dong(db, r.key)) for r in rows],
            "quyen": {"sua": user.role in KMC.VAI_SUA or user.role == "admin"},
            "lookups": {"sections": list(KMC.MUC), "sections_them": list(KMC.MUC_THEM), "sections_cach_tra": list(KMC.MUC_CACH_TRA),
                        "pay_channels": list(CACH_TRA)}}


@router.post("/api/khoan-muc")
def them(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    section = str(d.get("section") or "").strip()
    if section not in KMC.MUC_THEM:
        raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Khoản mới thêm được ở mục IV (đi đường), V (sửa chữa), VI (khác) — mục III chỉ có dầu."})
    vi, lo, en = _ten(d, "name_vi"), _ten(d, "name_lo"), _ten(d, "name_en")
    if not (vi or lo):
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Nhập tên khoản (tiếng Việt hoặc tiếng Lào)."})
    _chan_trung_ten(db, section, vi)
    cuoi = max([r.sort or 0 for r in db.query(CostItem).filter(CostItem.section == section).all()] or [0])
    r = CostItem(key=KMC.moi_khoa(), section=section, name_vi=vi or lo, name_lo=lo or vi, name_en=en, built_in=False, active=True,
                 pay_default=_cach_tra(section, d.get("pay_default")), sort=cuoi + 10, updated_by=user.full_name, updated_at=KMC.gio())
    db.add(r)
    db.commit()
    KMC.nap(db)
    return dict(KMC.xuat(r), so_dong=0)


@router.put("/api/khoan-muc/{iid}")
def sua(iid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    r = db.get(CostItem, iid)
    if r is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khoản mục này."})
    if not r.built_in:
        vi = _ten(d, "name_vi") if "name_vi" in d else r.name_vi
        lo = _ten(d, "name_lo") if "name_lo" in d else r.name_lo
        if not (vi or lo):
            raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Nhập tên khoản (tiếng Việt hoặc tiếng Lào)."})
        _chan_trung_ten(db, r.section, vi, bo_id=r.id)
        r.name_vi, r.name_lo = vi or lo, lo or vi
        if "name_en" in d:
            r.name_en = _ten(d, "name_en")
    if "pay_default" in d and r.section in KMC.MUC_CACH_TRA:
        moi = _cach_tra(r.section, d.get("pay_default"))
        KMC.doi_cach_tra_mac_dinh(db, r, moi)        # dòng cũ đang theo mặc định ghi rõ cách trả cũ — phiếu cũ không đổi nghĩa
        r.pay_default = moi
    if "sort" in d:
        try:
            r.sort = int(d.get("sort") or 0)
        except (TypeError, ValueError):
            raise HTTPException(422, {"ma": "SO_SAI", "loi": "Thứ tự phải là số."})
    if "active" in d:
        if not d.get("active") and r.key in KMC.KHONG_TAT:
            raise HTTPException(409, {"ma": "KHONG_NGUNG_DUOC", "loi": "Khoản này máy dùng (dầu mục III / phí cao tốc theo tuyến) — không ngưng được."})
        r.active = bool(d.get("active"))
    r.updated_by, r.updated_at = user.full_name, KMC.gio()
    db.commit()
    KMC.nap(db)
    return dict(KMC.xuat(r), so_dong=KMC.so_dong(db, r.key))
