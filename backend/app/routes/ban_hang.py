# -*- coding: utf-8 -*-
"""Bán hàng — EPL bán phụ tùng và xăng dầu cho bên ngoài. Ở TRANG KẾ TOÁN từ 28/09 (đợt 6).

Phiếu bán, xuất kho bán, hoá đơn bán, thu tiền bán (PXK_BAN · HD_BAN · PT_BAN) dời sang trang kế toán (Kho → Bán hàng).
Bảng sales / sale_lines bên này đứng yên từ ngày dời. Đợt trả chủ xe bên này (routes/chu_xe.py) hỏi bên đó các phiếu
chủ xe mua ở quầy chờ trừ, và báo sang khi đã trừ.
"""
from fastapi import APIRouter, Depends, HTTPException

from services.bao_mat import nguoi_hien_tai

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Bán hàng nay làm ở trang kế toán (Kho → Bán hàng)."}


@router.get("/api/ban-hang")
def ds_ban_hang(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.get("/api/ban-hang/{sid}")
def mot_phieu_ban(sid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/ban-hang")
def lap_phieu_ban(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/ban-hang/{sid}/thu")
def thu_tien_ban(sid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.delete("/api/ban-hang/{sid}")
def bo_phieu_ban(sid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)
