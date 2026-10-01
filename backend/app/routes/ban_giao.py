# -*- coding: utf-8 -*-
"""BÀN GIAO DO cho hệ kế toán của anh Tune — đúng khuôn API bàn giao của EPL_System, chỉ ĐỌC.

    GET  /api/handover/delivery-orders            (khoá máy) danh sách DO đã về, đã khoá — mới khoá trước; `q` tìm theo chữ
    GET  /api/handover/delivery-orders/{do_id}    (khoá máy) {header, details} của một DO
    GET  /api/handover/trang-thai                 (Sếp) đã có khoá chưa, bao nhiêu DO đang bàn giao được
    POST /api/handover/tao-khoa                   (Sếp) tạo (lại) khoá — chép sang cấu hình Logistics bên anh Tune
    GET  /api/handover/xem-truoc/{tid}            (Sếp, kế toán) xem đúng gói bên kia sẽ nhận của một phiếu

Khoá máy: `Authorization: Bearer <khoá>` (`services/bao_mat.py:may_qlsx_goi`), riêng với khoá của trang kế toán tạm.
Đóng gói ở `services/ban_giao.py`. Hợp đồng: `DOCS/md/HOP_DONG_API_KE_TOAN_ANH_TUNE.md`, mục 12.5 và 12.7.4.
"""
import datetime as dt
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Trip
from services import ban_giao as BG
from services import day_ke_toan as DK
from services.bao_mat import can_vai, may_qlsx_goi, token_nhan_qlsx

router = APIRouter()


def _ngay(chuoi, ten):
    if not chuoi:
        return None
    try:
        return dt.date.fromisoformat(str(chuoi).strip()[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Tham số %s phải là ngày ISO (YYYY-MM-DD)." % ten})


def _da_khoa(db):
    return db.query(Trip).filter(Trip.locked.is_(True), Trip.transport_status == "arrived")


def _tim_chu(db, qs, chu):
    """Lọc theo chữ trên ĐÚNG các ô một dòng danh sách trả ra: mã DO, số phiếu, mã khách bên kế toán, tên khách, số xe,
    biển đầu kéo — không phân biệt hoa thường. `%` và `_` người dùng gõ là chữ thường, không phải ký tự đại diện."""
    k = "%" + chu.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    ma_kt = db.query(Customer.id).filter(Customer.code.ilike(k, escape="!"))
    return qs.filter(or_(func.concat(BG.TIEN_TO, Trip.id).ilike(k, escape="!"), Trip.doc_no.ilike(k, escape="!"),
                         Trip.customer_id.in_(ma_kt), Trip.customer_name.ilike(k, escape="!"),
                         Trip.truck_no.ilike(k, escape="!"), Trip.plate_head.ilike(k, escape="!")))


@router.get("/api/handover/delivery-orders")
def danh_sach(customer_id: Optional[str] = Query(None, description="Chỉ lấy DO của một khách"),
              completed_from: Optional[str] = Query(None, description="Khoá từ ngày (ISO, gồm cả ngày đó)"),
              completed_to: Optional[str] = Query(None, description="Khoá đến ngày (ISO, gồm cả ngày đó)"),
              q: Optional[str] = Query(None, description="Tìm theo số phiếu, mã DO, tên / mã khách, số xe, biển đầu kéo"),
              page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
              db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    """DANH SÁCH DO đã về và đã khoá — bước quét của hệ kế toán, trước khi gọi chi tiết theo `do_id`.
    `q`: màn "Vụ việc" bên anh Tune tìm trên TOÀN BỘ DO ở đây, `total` là tổng sau khi lọc; trả lại `q` đã dùng để bên
    kia biết đã lọc ở đây (bản cũ không trả thì bên kia tự lọc trong trang đã tải)."""
    tu, den = _ngay(completed_from, "completed_from"), _ngay(completed_to, "completed_to")
    chu = (q or "").strip()
    if len(chu) > 200:
        raise HTTPException(422, {"ma": "TU_KHOA_DAI", "loi": "Từ khoá tìm tối đa 200 ký tự."})
    qs = _da_khoa(db)
    if customer_id:
        # nhận cả mã khách bên kế toán (OBJ_OBJECTNO) lẫn mã khách bên em
        theo_ma = [r[0] for r in db.query(Customer.id).filter(Customer.code == customer_id).all()]
        qs = qs.filter(Trip.customer_id.in_(theo_ma + [customer_id]))
    if tu:
        qs = qs.filter(Trip.locked_at >= dt.datetime.combine(tu, dt.time.min))
    if den:
        qs = qs.filter(Trip.locked_at < dt.datetime.combine(den + dt.timedelta(days=1), dt.time.min))
    if chu:
        qs = _tim_chu(db, qs, chu)
    tong = qs.count()
    dong = (qs.order_by(Trip.locked_at.desc(), Trip.id.desc()).offset((page - 1) * page_size).limit(page_size).all())
    ma = dict(db.query(Customer.id, Customer.code).filter(Customer.id.in_({p.customer_id for p in dong if p.customer_id})).all())
    return {"message": "Danh sách %d lệnh giao hàng đã hoàn tất%s (trang %d)." % (tong, ' khớp "%s"' % chu if chu else "", page),
            "data": {"items": [BG.dong_danh_sach(p, ma.get(p.customer_id)) for p in dong], "total": tong, "page": page,
                     "page_size": page_size, "q": chu or None}}


def _goi(db, p, do_id):
    if p is None:
        raise HTTPException(404, {"ma": "DO_KHONG_THAY", "loi": "Không có lệnh giao hàng %s." % do_id})
    if not BG.ban_giao_duoc(p):
        raise HTTPException(409, {"ma": "DO_CHUA_KHOA",
                                  "loi": "Phiếu %s chưa về hoặc chưa được kế toán Viêng Chăn khoá — chỉ bàn giao DO đã "
                                         "khoá." % p.doc_no})
    return BG.dong_goi(db, p)


@router.get("/api/handover/delivery-orders/{do_id}")
def chi_tiet(do_id: str, db: Session = Depends(get_db), may=Depends(may_qlsx_goi)):
    return {"message": "Hồ sơ bàn giao của %s." % do_id, "data": _goi(db, BG.tim(db, do_id), do_id)}


@router.get("/api/handover/trang-thai")
def trang_thai(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    return {"co_khoa": bool(token_nhan_qlsx(db)), "so_do_ban_giao_duoc": _da_khoa(db).count(),
            "duong_danh_sach": "/api/handover/delivery-orders", "duong_chi_tiet": "/api/handover/delivery-orders/{do_id}"}


@router.post("/api/handover/tao-khoa")
def tao_khoa(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Khoá mới thay khoá cũ ngay — bên anh Tune phải dán khoá mới vào cấu hình Logistics thì mới đọc tiếp được.
    Trả khoá đúng một lần trong câu trả lời này để Sếp chép; sau đó chỉ báo "đã có khoá"."""
    k = secrets.token_urlsafe(32)
    DK.dat_cau_hinh(db, "token_nhan_qlsx", k, user)
    db.commit()
    return {"token_nhan_qlsx": k}


@router.get("/api/handover/xem-truoc/{tid}")
def xem_truoc(tid: str, db: Session = Depends(get_db), user=Depends(can_vai("acct"))):
    """Sếp / kế toán Viêng Chăn xem đúng gói hệ kế toán sẽ nhận của một phiếu — không cần khoá máy."""
    p = db.get(Trip, tid)
    return {"message": "Gói bàn giao sẽ gửi của phiếu %s." % (p.doc_no if p else tid),
            "data": _goi(db, p, BG.TIEN_TO + tid)}
