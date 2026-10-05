# -*- coding: utf-8 -*-
"""BÀN GIAO PHIẾU ĐỀ NGHỊ XUẤT KHO NHIÊN LIỆU (PLNL) cho kho QLSX anh Tune (05/10 — bỏ kho tạm 8031; thủ kho cấp ở màn
"Quản lý kho" bên Web anh Tune). Cùng khoá máy với bàn giao DO (`Authorization: Bearer <khoá>`, services/bao_mat.may_qlsx_goi).

    GET  /api/handover/fuel-vouchers                     danh sách tờ PLNL — mặc định đang chờ cấp (status=cho); q, warehouse_code
    GET  /api/handover/fuel-vouchers/{voucher_id}         một tờ (DO, xe, xe nhà / xe thuê, đối tác, tài xế, kho, lít, dòng, cấp được không)
    POST /api/handover/fuel-vouchers/{voucher_id}/issued  kho QLSX báo đã cấp (số phiếu kho, lít thật, giá vốn) — gọi lại an toàn

Gói và luật ở services/ban_giao_dau.py; route chỉ đọc tham số, gọi service, bọc {message, data}.
"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Voucher
from services import ban_giao_dau as BGD
from services.bao_mat import may_qlsx_goi

router = APIRouter()


@router.get("/api/handover/fuel-vouchers")
def danh_sach(status: Optional[str] = Query("cho", description="cho · da_cap · huy; để trống = tất cả"),
              q: Optional[str] = Query(None, description="Tìm theo số phiếu đề nghị, số DO, số xe, tài xế"),
              warehouse_code: Optional[str] = Query(None, description="Chỉ tờ lĩnh ở kho có mã này (fuel_places.code)"),
              page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    chu = (q or "").strip()
    if len(chu) > 200:
        raise HTTPException(422, {"ma": "TU_KHOA_DAI", "loi": "Từ khoá tìm tối đa 200 ký tự."})
    tong, ds = BGD.danh_sach(db, (status or "").strip(), chu, (warehouse_code or "").strip(), page, page_size)
    return {"message": "Danh sách %d phiếu đề nghị xuất kho nhiên liệu (trang %d)." % (tong, page),
            "data": {"items": ds, "total": tong, "page": page, "page_size": page_size, "q": chu or None}}


@router.get("/api/handover/fuel-vouchers/{voucher_id}")
def chi_tiet(voucher_id: str, db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    v = db.get(Voucher, voucher_id)
    return {"message": "Phiếu đề nghị xuất kho nhiên liệu %s." % (v.doc_no if v else voucher_id), "data": BGD.goi(db, v)}


@router.post("/api/handover/fuel-vouchers/{voucher_id}/issued")
def da_cap(voucher_id: str, d: dict = Body(...), db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    x = BGD.ghi_da_cap(db, voucher_id, d or {})
    return {"message": ("Đã ghi nhận trước đó — phiếu %s cấp theo phiếu kho %s." if x.get("replayed")
                        else "Đã ghi nhận cấp dầu phiếu %s theo phiếu kho %s.") % (x["voucher_no"], x.get("stock_doc_no")),
            "data": x}
