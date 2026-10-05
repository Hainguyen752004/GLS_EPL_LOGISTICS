# -*- coding: utf-8 -*-
"""BÀN GIAO PHIẾU ĐỀ NGHỊ XUẤT KHO NHIÊN LIỆU (PLNL) cho kho QLSX anh Tune (05/10 — bỏ kho tạm 8031; thủ kho cấp ở màn
"Quản lý kho" bên Web anh Tune). Cùng khoá máy với bàn giao DO (`Authorization: Bearer <khoá>`, services/bao_mat.may_qlsx_goi).

    GET  /api/handover/fuel-vouchers                     danh sách tờ PLNL — mặc định đang chờ cấp (status=cho); q, warehouse_code
    GET  /api/handover/fuel-vouchers/{voucher_id}         một tờ (DO, xe, xe nhà / xe thuê, đối tác, tài xế, kho, lít, dòng, cấp được không)
    POST /api/handover/fuel-vouchers/{voucher_id}/issued  kho QLSX báo đã cấp (số phiếu kho, lít thật, giá vốn) — gọi lại an toàn
    POST /api/handover/fuel-vouchers/{voucher_ref}/cancelled  kho QLSX báo đã huỷ phiếu xuất → tờ về chờ cấp (05/10) — gọi lại an toàn
GET chi tiết và /cancelled nhận mã tờ HOẶC SourceRef (bên kho chỉ giữ SourceRef).

Phiếu xuất PHỤ TÙNG mục V (SourceRef EPLLAO:trip_expense:<mã dòng>, services/ban_giao_phu_tung.py — 05/10 đợt 3):
    GET  /api/handover/stock-issues/{source_ref}            dòng phụ tùng của phiếu kho (DO, khoá chưa, đã xuất chưa)
    POST /api/handover/stock-issues/{source_ref}/cancelled  kho QLSX báo đã huỷ phiếu xuất → dòng về «lấy kho, chưa xuất» — gọi lại an toàn

Gói và luật ở services/ban_giao_dau.py; route chỉ đọc tham số, gọi service, bọc {message, data}.
"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services import ban_giao_dau as BGD
from services import ban_giao_phu_tung as BGP
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
    v = BGD.tim(db, voucher_id)
    return {"message": "Phiếu đề nghị xuất kho nhiên liệu %s." % (v.doc_no if v else voucher_id), "data": BGD.goi(db, v)}


@router.post("/api/handover/fuel-vouchers/{voucher_id}/issued")
def da_cap(voucher_id: str, d: dict = Body(...), db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    x = BGD.ghi_da_cap(db, voucher_id, d or {})
    return {"message": ("Đã ghi nhận trước đó — phiếu %s cấp theo phiếu kho %s." if x.get("replayed")
                        else "Đã ghi nhận cấp dầu phiếu %s theo phiếu kho %s.") % (x["voucher_no"], x.get("stock_doc_no")),
            "data": x}


@router.post("/api/handover/fuel-vouchers/{voucher_ref}/cancelled")
def da_huy(voucher_ref: str, d: dict = Body(default={}), db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    x = BGD.ghi_da_huy(db, voucher_ref, d or {})
    return {"message": ("Phiếu %s đã ở trạng thái chờ cấp — không đổi gì." if x.get("replayed")
                        else "Đã mở lại phiếu %s (kho QLSX huỷ phiếu xuất).") % x["voucher_no"], "data": x}


@router.get("/api/handover/stock-issues/{source_ref}")
def phu_tung(source_ref: str, db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    x = BGP.goi(db, source_ref)
    return {"message": "Dòng phụ tùng %s của DO %s." % (x["item_name"] or x["line_id"], x["do_code"]), "data": x}


@router.post("/api/handover/stock-issues/{source_ref}/cancelled")
def phu_tung_da_huy(source_ref: str, d: dict = Body(default={}), db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    x = BGP.ghi_da_huy(db, source_ref, d or {})
    return {"message": ("Dòng phụ tùng %s đã ở trạng thái chưa xuất — không đổi gì." if x.get("replayed")
                        else "Đã gỡ phiếu kho khỏi dòng phụ tùng %s (kho QLSX huỷ phiếu xuất).") % (x["item_name"] or x["line_id"]),
            "data": x}
