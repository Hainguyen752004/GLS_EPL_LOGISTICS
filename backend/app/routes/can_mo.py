# -*- coding: utf-8 -*-
"""CÂN TẠI MỎ — tài xế báo từ điện thoại (chủ dự án chốt 29/09).

Phiếu GOM: xe rời bãi đi lấy hàng; số tấn chỉ có khi đã bốc xong và cân ở mỏ — lúc đó chỉ tài xế đứng cạnh phiếu cân.
Tài xế ghi số tấn, chụp phiếu cân / phiếu quặng; gửi xong thì ô "Cân tại mỏ" của phiếu (mục II) tự đầy, máy ghi dòng hàng
theo Loại hàng, ảnh vào "Phiếu quặng đính kèm". Bãi vẫn là người chốt: xem lại số, sửa nếu cần, rồi Gửi kiểm tra mục II.

    POST /api/trips/{id}/bao-can-mo     multipart: tan, ghi_chu, luc, ma_gui + tệp `anh` (ảnh · PDF, nhiều tệp, không bắt buộc)

Mất mạng ở mỏ là chuyện thường: máy tài xế giữ lần báo lại và gửi khi có mạng. `ma_gui` là mã lần gửi — gửi lại cùng mã
không ghi hai lần; `luc` là giờ cân thật trên máy, không phải giờ máy chủ nhận. Ảnh không bắt buộc: phiếu của khách nhập
tay được (chốt 23/09).
"""
import datetime as dt

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Trip, TripEvent, TripGoods, bay_gio
from routes.giao_nhan import ANH_TOI_DA_SO, _loi, _luu_tep
from routes.phieu import _chan_khoa, _cua_tai_xe, _dong_hang_gom, _ghi_log, _gon, _muc_cua, _so, xuat_phieu
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import duoc_sua_muc
from services.tep import TEP_TOI_DA

router = APIRouter()


@router.post("/api/trips/{tid}/bao-can-mo")
async def bao_can_mo(tid: str, tan: str = Form(""), ghi_chu: str = Form(""), luc: str = Form(""), ma_gui: str = Form(""),
                     anh: Optional[List[UploadFile]] = File(None),
                     db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid) or _loi("KHONG_THAY", "Không có phiếu này.", 404)
    if user.role not in ("driver", "yard", "admin"):
        _loi("KHONG_CO_QUYEN", "Chỉ tài xế của phiếu (hoặc Bãi) báo cân tại mỏ.", 403)
    _cua_tai_xe(db, p, user)
    ma_gui = (ma_gui or "").strip()[:64]
    if ma_gui and p.mine_ref == ma_gui:                 # máy tài xế gửi lại lần đã nhận (mất mạng rồi có mạng)
        return xuat_phieu(db, p, vai=user.role)
    _chan_khoa(p, user)
    if p.kind != "gom":
        _loi("KHONG_PHAI_PHIEU_GOM", "Chỉ phiếu gom (đi lấy hàng ở mỏ) mới báo cân tại mỏ.", 409)
    if p.transport_status == "arrived":
        _loi("PHIEU_DA_TOI", "Xe đã về tới bãi — hàng đã vào kho theo cân tại mỏ %s t." % _gon(p.weight_origin), 409)
    so_tan = _so(tan, "tan")
    if not so_tan or so_tan <= 0:
        _loi("THIEU_TAN", "Ghi số tấn cân tại mỏ (theo phiếu cân).")
    # Tài xế ghi thay Bãi, nên theo quyền của Bãi: mục II đã gửi kiểm vẫn sửa được, đã kiểm rồi thì thôi.
    st = _muc_cua(db, p)["trans"].status
    if not duoc_sua_muc("yard" if user.role == "driver" else user.role, "trans", st):
        _loi("MUC_DA_KHOA", "Mục II đã kiểm với cân tại mỏ %s t — muốn đổi thì báo Bãi nhờ kế toán trả lại mục II."
             % _gon(p.weight_origin), 409)
    if db.query(TripGoods).filter(TripGoods.trip_id == p.id, TripGoods.loai == "hang").count() > 1:
        _loi("NHIEU_DONG_HANG", "Phiếu có nhiều dòng hàng — Bãi ghi số tấn từng dòng trên phiếu.", 409)
    ds_anh = [a for a in (anh or []) if a is not None and (a.filename or "")]
    if len(ds_anh) > ANH_TOI_DA_SO:
        _loi("QUA_NHIEU_ANH", "Tối đa %d ảnh mỗi lần." % ANH_TOI_DA_SO)
    if sum((a.size or 0) for a in ds_anh) > TEP_TOI_DA:
        _loi("TEP_QUA_LON", "Một lần gửi quá 10 MB — bớt ảnh.")
    # 06/10: lưu giờ UTC không múi như mọi cột giờ (models.bay_gio) — trước lưu giờ máy chủ (Lào), Diễn biến lệch 7 tiếng / đảo thứ tự
    try:
        luc_can = dt.datetime.fromisoformat(luc.strip().replace("Z", "+00:00")) if (luc or "").strip() else bay_gio()
        if luc_can.tzinfo is not None:
            luc_can = luc_can.astimezone(dt.timezone.utc).replace(tzinfo=None)
    except ValueError:
        _loi("GIO_SAI", "Giờ cân không đúng dạng.")
    if luc_can > bay_gio() + dt.timedelta(minutes=10):
        _loi("GIO_SAI", "Giờ cân ở tương lai — kiểm lại giờ trên điện thoại.")

    for a in ds_anh:
        db.add(await _luu_tep(p, a, "ore_bill", user))   # vào "Phiếu quặng đính kèm" của phiếu
    cu = p.weight_origin
    p.weight_origin = so_tan
    _dong_hang_gom(db, p, user)
    p.mine_ref = ma_gui or None
    ghi = (ghi_chu or "").strip()
    db.add(TripEvent(trip_id=p.id, kind="note", ts=luc_can, by_user=user.full_name,
                     note="Báo cân tại mỏ %s t%s%s%s" % (_gon(so_tan), " (trước %s t)" % _gon(cu) if cu and abs(cu - so_tan) > 0.0005 else "",
                                                        " · %d ảnh" % len(ds_anh) if ds_anh else "", " · " + ghi if ghi else "")))
    _ghi_log(db, p, user, "a_can_mo")
    db.commit()
    return xuat_phieu(db, p, vai=user.role)
