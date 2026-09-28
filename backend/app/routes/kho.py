# -*- coding: utf-8 -*-
"""Mô-đun kho: kho nhiên liệu (ສາງນໍ້າມັນ · TK 625/371) và kho phụ tùng (ສາງອາໄຫຼ່ · TK 614/371).

Cả hai là SỔ KHO kiểu 2016: nhập một dòng, xuất một dòng, tồn = cộng dồn. Không có lô, không
FIFO, không định mức tiêu hao — Excel của họ không có mấy thứ đó.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Part
from services import chung_tu as CT
from services import gia_von as GV
from services import kho_ke_toan as KK
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi

router = APIRouter()
# Nhập, xuất tay, chuyển kho dầu: KT kho xăng dầu (Thà Bốc / Viêng Chăn) và kế toán — anh Khampla A1/A3: "ບັນຊີສາງ"
# lập đơn mua và nhập kho. Bãi xem được số lít tồn nhưng không thấy giá dầu (A2) nên không ghi sổ kho.
SUA_KHO = can_vai("fuel", "acct")
# Kho phụ tùng là của THỦ KHO PHỤ TÙNG Thà Bốc (anh Khampla C1.2) — trước đây Bãi và kế toán làm
# thay. Tổ sửa chữa xem được tồn nhưng không tự nhập xuất; họ lấy phụ tùng qua dòng mục V trên phiếu.


def _ngay(v):
    if not v:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD."})


def _so(v, ten, bat_buoc=False):
    if v in (None, ""):
        if bat_buoc:
            raise HTTPException(422, {"ma": "THIEU", "loi": "Thiếu %s." % ten})
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "%s phải là số." % ten})


# ---------------------------------------------------------------- kho nhiên liệu — ở trang kế toán từ 28/09
# Sổ dầu từng kho, tồn, giá bình quân, nhập kho, chuyển kho dời sang trang kế toán (Kho → Kho nhiên liệu). Bảng
# fuel_moves bên này đứng yên từ ngày dời (khoá ngoại của phiếu cũ); phiếu hỏi giá / xuất dầu qua services/kho_ke_toan.py.
DA_DOI_NL = {"ma": "DA_DOI_SANG_KE_TOAN",
             "loi": "Kho nhiên liệu nay quản lý ở trang kế toán (Kho → Kho nhiên liệu)."}


@router.get("/api/fuel-moves")
def so_nhien_lieu(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_NL)


@router.post("/api/fuel-moves")
def ghi_nhien_lieu(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_NL)


@router.post("/api/fuel-transfers")
def chuyen_kho(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_NL)


@router.delete("/api/fuel-moves/{mid}")
def xoa_nhien_lieu(mid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_NL)


# ---------------------------------------------------------------- kho phụ tùng — ở trang kế toán từ 28/09
# Danh mục, tồn, giá bình quân và sổ nhập xuất phụ tùng dời sang trang kế toán. Bảng parts bên này chỉ còn là bản chép
# danh mục (khoá ngoại của dòng chi mục V, dòng lệnh sửa, dòng bán). Ô chọn phụ tùng trên phiếu hỏi tồn / giá thẳng
# bên đó; nhập / xuất / sửa danh mục làm ở trang kế toán (Kho → Kho phụ tùng).
DA_DOI_PT = {"ma": "DA_DOI_SANG_KE_TOAN",
             "loi": "Kho phụ tùng nay quản lý ở trang kế toán (Kho → Kho phụ tùng). Ở đây chỉ còn danh mục để chọn trên phiếu."}


@router.get("/api/parts")
def ds_phu_tung(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Phụ tùng đang dùng kèm tồn và giá bình quân HIỆN TẠI của trang kế toán. Trang kế toán tắt thì vẫn trả danh mục
    bản chép (không tồn, không giá, `khong_noi`) để phiếu mở được; xuất kho lúc đó sẽ bị chặn và báo rõ."""
    try:
        ds = [x for x in KK.ds_phu_tung(db) if x.get("active")]
    except HTTPException:
        ds = [{"id": p.id, "name": p.name, "unit": p.unit, "qty": None, "min_qty": p.min_qty, "unit_price": None,
               "active": p.active, "status": None, "khong_noi": True}
              for p in db.query(Part).filter(Part.active.is_(True)).order_by(Part.name).all()]
    if not thay_tien_chi(user.role):            # Bãi không thấy giá (anh Khampla A2)
        for r in ds: r.pop("unit_price", None)
    return ds


@router.post("/api/parts")
def them_phu_tung(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)


@router.put("/api/parts/{pid}")
def sua_phu_tung(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)


@router.get("/api/parts/{pid}/moves")
def so_phu_tung(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)


@router.post("/api/parts/{pid}/moves")
def nhap_xuat_phu_tung(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)
