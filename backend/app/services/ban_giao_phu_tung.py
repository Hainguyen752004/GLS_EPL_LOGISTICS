# -*- coding: utf-8 -*-
"""BÁO NGƯỢC PHIẾU XUẤT PHỤ TÙNG MỤC V cho kho QLSX anh Tune (05/10 — chủ dự án: "làm báo ngược cho cả phiếu này, giống phiếu cấp dầu").

Phụ tùng lấy kho của mục V (tổ sửa khai «Sửa xe» lấy kho, duyệt báo hỏng — routes/phieu.py) xuất ở kho QLSX bằng phiếu 48 với
SourceRef `EPLLAO:trip_expense:<mã dòng>` (services/kho_qlsx.sr), dòng chi mang `stock_move_id = "qlsx:<số phiếu kho>"`. Thủ kho xoá
phiếu đó trên màn Danh sách chứng từ của Web anh Tune thì API bên đó:
  1. TRƯỚC khi huỷ hỏi `goi(db, ref)` — DO đã khoá thì bên đó từ chối huỷ (bút toán khoá phiếu đã theo lần xuất);
  2. SAU khi huỷ báo `ghi_da_huy(db, ref, d)` — dòng về "lấy kho, chưa xuất" (gỡ stock_move_id + giá vốn), như dầu khi phiếu cấp bị
     huỷ (services/ban_giao_dau.ghi_da_huy). Dòng chưa xuất thì khoá phiếu bị chặn PT_KHO_CHUA_XUAT — tổ sửa xoá dòng / khai lại.

GIAO ƯỚC (routes/ban_giao_dau.py gọi — giữ cố định):
    goi(db, ref) -> dict              {source_ref, line_id, do_id, do_code, trip_locked, truck_no, item_name, qty, status, stock_doc_no}
                                      status: "da_xuat" (còn mang qlsx:…) · "chua_xuat"; ref không phải dòng phụ tùng mục V → 404
    ghi_da_huy(db, ref, d) -> dict    d = {stock_doc_no?, reason?, cancelled_by?}; DO đã khoá → 409 DA_KHOA; gọi lại khi dòng đã gỡ →
                                      replayed = True
"""
from fastapi import HTTPException

from models import Trip, TripExpense, TripLog

TIEN_TO_SR = "EPLLAO:trip_expense:"   # services/kho_qlsx.sr("trip_expense:<mã dòng>")
TIEN_TO_MV = "qlsx:"                  # TripExpense.stock_move_id của dòng đã xuất ở kho QLSX


def _loi(ma, loi, code=422):
    raise HTTPException(code, {"ma": ma, "loi": loi})


def _dong(db, ref, khoa=False):
    sr = str(ref or "").strip()
    if not sr.startswith(TIEN_TO_SR):
        _loi("KHONG_PHAI_PHU_TUNG", "SourceRef %s không phải phiếu xuất phụ tùng mục V của EPL." % sr[:100], 404)
    q = db.query(TripExpense).filter(TripExpense.id == sr[len(TIEN_TO_SR):])
    e = (q.with_for_update() if khoa else q).first()
    if e is None or e.section != "repair" or e.source != "kho":
        _loi("KHONG_THAY", "Không còn dòng phụ tùng lấy kho của SourceRef %s trên EPL." % sr, 404)
    p = db.get(Trip, e.trip_id)
    if p is None:
        _loi("KHONG_THAY", "Dòng phụ tùng của SourceRef %s không còn phiếu DO." % sr, 404)
    return sr, e, p


def _goi(sr, e, p):
    from services import ban_giao as BG
    da = (e.stock_move_id or "").startswith(TIEN_TO_MV)
    return {"source_ref": sr, "line_id": e.id, "do_id": BG.TIEN_TO + p.id, "do_code": p.doc_no, "trip_locked": bool(p.locked),
            "truck_no": p.truck_no, "item_name": e.item_name, "qty": e.qty or 0, "status": "da_xuat" if da else "chua_xuat",
            "stock_doc_no": e.stock_move_id[len(TIEN_TO_MV):] if da else None}


def goi(db, ref):
    return _goi(*_dong(db, ref))


def ghi_da_huy(db, ref, d):
    sr, e, p = _dong(db, ref, khoa=True)
    if not (e.stock_move_id or "").startswith(TIEN_TO_MV):
        if e.stock_move_id:
            _loi("KHONG_PHAI_KHO_QLSX", "Dòng %s xuất ở kho tạm cũ (%s), không phải kho bên kế toán." % (e.item_name or e.id, e.stock_move_id), 409)
        return dict(_goi(sr, e, p), replayed=True)          # đã gỡ từ lần báo trước
    so = str(d.get("stock_doc_no") or "").strip()
    cu = e.stock_move_id[len(TIEN_TO_MV):]
    if so and so != cu:
        _loi("KHAC_PHIEU_KHO", "Dòng %s xuất theo phiếu kho %s, không phải %s." % (e.item_name or e.id, cu, so), 409)
    if p.locked:
        _loi("DA_KHOA", "DO %s đã khoá trên EPL — mở khoá DO trước rồi mới huỷ phiếu xuất phụ tùng." % p.doc_no, 409)
    e.stock_move_id, e.unit_price = None, 0
    ly_do = str(d.get("reason") or "").strip()[:200]
    nguoi = str(d.get("cancelled_by") or "").strip()[:80] or "QLSX"
    db.add(TripLog(trip_id=p.id, user_name=nguoi, role="qlsx", action=(
        "Kho QLSX huỷ phiếu xuất phụ tùng %s (%s × %s) — dòng mục V về «lấy kho, chưa xuất»%s" % (
            cu, e.item_name or "", e.qty or 0, (" (lý do: %s)" % ly_do) if ly_do else ""))[:500]))
    db.commit()
    return dict(_goi(sr, e, p), replayed=False, cancelled_stock_doc_no=cu)
