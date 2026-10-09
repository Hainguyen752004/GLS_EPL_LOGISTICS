# -*- coding: utf-8 -*-
"""TẤT TOÁN ĐỐI TÁC (chủ xe liên kết) — chủ dự án chốt 02/10/2026. Số liệu ở services/tat_toan_doi_tac.py, lập / bỏ đề nghị ở
services/chi_tune.py (cùng đường với màn Xe liên kết: POST /api/owners/{oid}/de-nghi-tra · /api/chi-chu-xe/{rid}/{viec}).

    GET  /api/tat-toan-doi-tac?ky=YYYY-MM[&owner_id=][&cap_nhat=0|1]   bảng kỳ; có owner_id thì kèm chi_tiet từng chuyến
    POST /api/tat-toan-doi-tac/de-nghi {owner_id, trip_ids[], cach_tra: cash|bank}
                                        → {so, can_tru[], phieu_chi: {so, trang_thai} | null, de_nghi}
    POST /api/tat-toan-doi-tac/de-nghi/{so}/{viec}                   viec: bo (bỏ đề nghị chưa xong, gỡ cấn trừ) · gui-lai · cap-nhat

Quyền theo màn Xe liên kết (routes/chu_xe.py): xem — mọi vai trừ Bãi / tài xế / kho / tổ sửa (tiền thuê là tiền bán); lập, bỏ,
gửi lại — KT Thu/Chi VC và Sếp. `cap_nhat` mặc định: có owner_id thì đọc lại còn nợ SO nhiên liệu từ hệ kế toán (một lời gọi), không
có thì dùng bản đọc lại gần nhất.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ChiChuXeTune
from routes.chu_xe import DE_NGHI_TRA, KHONG_XEM_TRA
from services import chi_tune as CHI
from services import tat_toan_doi_tac as TTDT
from services.bao_mat import nguoi_hien_tai

router = APIRouter()


def _ky(ky):
    ky = (ky or dt.date.today().strftime("%Y-%m"))[:7]
    try:
        dt.date.fromisoformat(ky + "-01")
    except ValueError:
        raise HTTPException(422, {"ma": "KY_SAI", "loi": "Kỳ phải dạng YYYY-MM, nhận '%s'." % ky})
    return ky


def _xem(user):
    if user.role in KHONG_XEM_TRA:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem tiền trả đối tác." % user.role})


def _lam(user):
    if user.role not in DE_NGHI_TRA:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Thu/Chi Viêng Chăn hoặc Sếp lập / bỏ đề nghị trả đối tác."})


def _ket(r):
    """Kết quả lập / gửi lại / bỏ một đề nghị (giao ước)."""
    x = CHI.xuat_chu_xe(r)
    return {"so": r.ref_no, "trang_thai": r.status, "can_tru": x["can_tru"],
            "phieu_chi": {"so": r.document_no, "trang_thai": r.status} if r.real_id or r.document_no else None, "de_nghi": x}


@router.get("/api/tat-toan-doi-tac")
def bang(ky: str = "", owner_id: str = "", cap_nhat: int = -1, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _xem(user)
    return TTDT.bang(db, _ky(ky), owner_id or None, cap_nhat=bool(owner_id) if cap_nhat < 0 else bool(cap_nhat))


@router.post("/api/tat-toan-doi-tac/de-nghi")
def lap_de_nghi(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _lam(user)
    if not CHI.chi_o_ke_toan():
        raise HTTPException(409, {"ma": "CHI_TAI_CHO", "loi": "Đang để chi tại chỗ (EPL_CHI_TAM_UNG=tai_cho)."})
    if not d.get("owner_id"):
        raise HTTPException(422, {"ma": "THIEU_DOI_TAC", "loi": "Chưa chọn đối tác."})
    r = CHI.de_nghi_tra_chu_xe(db, str(d["owner_id"]), d.get("trip_ids") or [], (d.get("cach_tra") or d.get("phuong_thuc") or "cash").strip(),
                               user)
    return _ket(r)


@router.post("/api/tat-toan-doi-tac/de-nghi/{so}/{viec}")
def viec_de_nghi(so: str, viec: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    r = db.query(ChiChuXeTune).filter(ChiChuXeTune.ref_no == so).first()
    if r is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có đề nghị trả %s." % so})
    if viec == "cap-nhat":
        _xem(user)
        r = CHI.dong_bo_chu_xe(db, r, user=user)
    elif viec in ("bo", "gui-lai"):
        _lam(user)
        r = CHI.huy_chu_xe(db, r, user=user) if viec == "bo" else CHI.gui_lai_chu_xe(db, r, user)
    else:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có việc %s." % viec})
    return _ket(r)
