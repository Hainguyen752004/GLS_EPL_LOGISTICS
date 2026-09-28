# -*- coding: utf-8 -*-
"""LIÊN THÔNG hai trang — trang điều xe (đây) ↔ trang kế toán (EPL_KETOAN).

    GET  /api/lien-thong/kiem          trang kế toán gọi sang thử khoá: đúng khoá + đúng người thì trả người đó
    GET  /api/lien-thong/thu           Sếp bấm "Kiểm kết nối": gọi sang trang kế toán và báo thật kết quả
    POST /api/lien-thong/tao-khoa      Sếp tạo (lại) khoá cho trang kế toán gọi sang — chép khoá này vào Cài đặt bên đó
"""
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services import day_ke_toan as DK
from services import goi_ke_toan as KT
from services.bao_mat import can_vai, may_ke_toan_goi, token_nhan_ke_toan

router = APIRouter()


@router.get("/api/lien-thong/kiem")
def kiem(u=Depends(may_ke_toan_goi)):
    return {"ok": True, "ben": "EPL_LAO_REAL", "nguoi": u.username, "vai": u.role}


@router.get("/api/lien-thong/thu")
def thu(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    goc, token = KT.cau_hinh(db)
    t0 = time.time()
    ra = {"api": goc, "co_token_nhan": bool(token_nhan_ke_toan(db))}
    try:
        ra.update(ok=True, ms=int((time.time() - t0) * 1000), ben_kia=KT.goi(db, "GET", "/api/lien-thong/kiem", nguoi=user))
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {"loi": str(e.detail)}
        ra.update(ok=False, co_token=bool(token), ma=d.get("ma"), loi=d.get("loi"))
    return ra


@router.post("/api/lien-thong/tao-khoa")
def tao_khoa(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Khoá mới thay khoá cũ ngay — trang kế toán phải dán khoá mới vào Cài đặt thì mới gọi sang được tiếp.
    Trả khoá đúng một lần trong câu trả lời này để Sếp chép; sau đó màn chỉ báo "đã có khoá"."""
    k = secrets.token_urlsafe(32)
    DK.dat_cau_hinh(db, "token_nhan_ke_toan", k, user)
    db.commit()
    return {"token_nhan_ke_toan": k}
