# -*- coding: utf-8 -*-
"""Hoá đơn gộp tháng — ໃບເກັບເງິນລວມເດືອນ. KHÔNG làm trên trang điều xe.

28/09 (đợt 7a) dời sang trang kế toán tạm; 01/10 chủ dự án bỏ trang tạm — hoá đơn, thu tiền ở đó là số thử, bỏ hết (cờ
trips.invoiced · invoice_id · inv_no · collected_lak trên phiếu không còn ý nghĩa). Hoá đơn và công nợ khách nay ở HỆ KẾ TOÁN
anh Tune: mỗi DO đã khoá gửi một SO (phiếu đề nghị thu, services/gui_tune.py); gộp tháng, thu tiền làm ở bên đó. Bảng
invoices / invoice_payments / trip_payments bên này đứng yên.
"""
from fastapi import APIRouter, Depends, HTTPException

from services.bao_mat import nguoi_hien_tai

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Hoá đơn và thu tiền khách làm ở hệ kế toán: mỗi DO đã khoá gửi một đề nghị thu (SO) ở "
                                             "màn Phiếu đề nghị thu; gộp tháng, thu tiền ở công nợ khách bên đó."}


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
