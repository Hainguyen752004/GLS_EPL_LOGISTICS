# -*- coding: utf-8 -*-
"""Bán hàng — EPL bán phụ tùng và xăng dầu cho bên ngoài. KHÔNG làm trên trang điều xe.

28/09 (đợt 6) dời sang trang kế toán (Kho → Bán hàng). 01/10 chủ dự án bỏ phần TIỀN của trang đó (số thử) và giữ nó làm KHO
TẠM: phiếu bán, xuất kho bán (PXK_BAN) là việc của kho; hoá đơn bán, thu tiền bán (HD_BAN · PT_BAN) là việc của hệ kế toán
anh Tune. Bảng sales / sale_lines bên này đứng yên từ ngày dời.
"""
from fastapi import APIRouter, Depends, HTTPException

from services.bao_mat import nguoi_hien_tai

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Bán hàng không làm trên EPL: phiếu bán, xuất kho bán ở kho (Kho → Bán hàng); "
                                             "hoá đơn, thu tiền bán ở hệ kế toán."}


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
