# -*- coding: utf-8 -*-
"""Hoá đơn gộp tháng — ໃບເກັບເງິນລວມເດືອນ. Ở TRANG KẾ TOÁN từ 28/09 (đợt 7a).

Gộp hoá đơn tháng, thu tiền theo tờ gộp (rải xuống từng phiếu theo ngày), huỷ tờ, xoá lần thu dời sang trang kế toán
(Tiền vận chuyển → Hoá đơn gộp tháng), cùng xuất hoá đơn từng phiếu và sổ thu tiền. Bảng invoices / invoice_payments /
trip_payments bên này đứng yên từ ngày dời. Trang kế toán ghi bản chép vào phiếu (trips.invoiced · invoice_id · inv_no ·
collected_lak · finance_status) qua routes/lien_thong.py → /api/lien-thong/doanh-thu/….
"""
from fastapi import APIRouter, Depends, HTTPException

from services.bao_mat import nguoi_hien_tai

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Hoá đơn gộp tháng nay làm ở trang kế toán (Tiền vận chuyển → Hoá đơn gộp tháng)."}


@router.get("/api/hoa-don-gop/cho-gop")
def cho_gop(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.get("/api/hoa-don-gop")
def ds_hoa_don(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.get("/api/hoa-don-gop/{hid}")
def xem_hoa_don(hid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/hoa-don-gop")
def gop_thang(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.delete("/api/hoa-don-gop/{hid}")
def huy_hoa_don(hid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/hoa-don-gop/{hid}/thu-tien")
def thu_tien(hid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.delete("/api/hoa-don-thu/{pid}")
def xoa_thu_tien(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)
