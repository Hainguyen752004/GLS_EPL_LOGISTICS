# -*- coding: utf-8 -*-
"""Lệnh sửa chữa riêng — ໃບສັ່ງສ້ອມແປງ (anh Khampla C7.3). Ở TRANG KẾ TOÁN từ 28/09 (đợt 6).

Lệnh, dòng chi, chuỗi duyệt (tổ sửa nhập → KT Chi phí kiểm → ghi sổ → quỹ chi), xuất kho phụ tùng và tờ PC_SC dời sang
trang kế toán (Kho → Lệnh sửa chữa). Bảng repair_orders / repair_lines bên này đứng yên từ ngày dời. Bên đó báo sang
đây khi xe vào / ra xưởng (routes/lien_thong.py → /api/lien-thong/xe/{id}/sua-chua), và màn Xe bên này hỏi bên đó lịch
sử lệnh của xe (routes/danh_muc.py). Mục V trên phiếu xuất xe vẫn ở đây như cũ.
"""
from fastapi import APIRouter, Depends, HTTPException

from services.bao_mat import nguoi_hien_tai

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Lệnh sửa chữa nay làm ở trang kế toán (Kho → Lệnh sửa chữa)."}


@router.get("/api/lenh-sua-chua")
def ds_lenh(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.get("/api/lenh-sua-chua/{oid}")
def xem_lenh(oid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/lenh-sua-chua")
def lap_lenh(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.put("/api/lenh-sua-chua/{oid}")
def sua_lenh(oid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.delete("/api/lenh-sua-chua/{oid}")
def xoa_lenh(oid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/lenh-sua-chua/{oid}/{hanh_dong}")
def duyet(oid: str, hanh_dong: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)
