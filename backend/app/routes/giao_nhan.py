# -*- coding: utf-8 -*-
"""GIAO HÀNG HOÀN TẤT — ký nhận trên điện thoại tài xế (chủ dự án chốt 24/09).

Nơi giao hàng chỉ có tài xế, nên người nhận ký NGAY TRÊN ĐIỆN THOẠI tài xế: chữ ký, tên, điện thoại người nhận, tình
trạng hàng, ảnh biên bản / phiếu cân, giờ ký và vị trí GPS. Gửi xong thì khối POD của phiếu (mục II) tự đầy — Bãi và
kế toán thấy ngay, in được "Biên bản giao nhận hàng" (in ở giao diện, js/bien_ban.js).

    POST /api/trips/{id}/giao-nhan     multipart: nguoi_nhan, sdt, tinh_trang, ghi_chu, luc, lat, lng, ma_gui, pod_no
                                       + tệp `chu_ky` (PNG) và / hoặc `anh` (ảnh · PDF, nhiều tệp)

Luật (giống POD đã chốt): có CHỮ KÝ hoặc ẢNH biên bản là đủ — nơi khách vẫn dùng giấy thì chụp giấy. Mất mạng thì máy
tài xế giữ lại và gửi khi có mạng: `ma_gui` là mã lần gửi, gửi lại cùng mã không ghi hai lần; `luc` là giờ ký thật
trên máy, không phải giờ máy chủ nhận.
"""
import datetime as dt
import mimetypes
import os
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Trip, TripAttachment, ma_moi
from routes.phieu import _chan_khoa, _cua_tai_xe, _ghi_log, xuat_phieu
from services.bao_mat import nguoi_hien_tai
from services.tep import loi_co_tep, TEP_DIR, TEP_KIEU, TEP_TOI_DA

router = APIRouter()
TINH_TRANG = ("du", "thieu", "hong")
KY_TOI_DA = 2 * 1024 * 1024
ANH_TOI_DA_SO = 5


def _loi(ma, loi, code=422):
    raise HTTPException(code, {"ma": ma, "loi": loi})


async def _luu_tep(p, tep, kind, user, chi_png=False):
    kieu = (tep.content_type or mimetypes.guess_type(tep.filename or "")[0] or "").lower()
    if chi_png and kieu != "image/png":
        _loi("KIEU_TEP", "Chữ ký phải là ảnh PNG.")
    if kieu not in TEP_KIEU:
        _loi("KIEU_TEP", "Chỉ nhận ảnh (JPG, PNG, WEBP, HEIC) hoặc PDF.")
    du = await tep.read()
    if not du:
        _loi("TEP_RONG", "Tệp rỗng.")
    if len(du) > (KY_TOI_DA if chi_png else TEP_TOI_DA) or (not chi_png and loi_co_tep(kieu, len(du))):
        _loi("TEP_QUA_LON", (not chi_png and loi_co_tep(kieu, len(du))) or "Tệp %.1f MB, quá lớn." % (len(du) / 1048576))
    a = TripAttachment(trip_id=p.id, kind=kind, content_type=kieu, size=len(du), by_user=user.full_name,
                       filename=re.sub(r"[^\w.\-() ]+", "_", tep.filename or kind)[:120])
    a.id = ma_moi()
    a.stored = a.id + TEP_KIEU[kieu]
    os.makedirs(os.path.join(TEP_DIR, p.id), exist_ok=True)
    with open(os.path.join(TEP_DIR, p.id, a.stored), "wb") as f:
        f.write(du)
    return a


@router.post("/api/trips/{tid}/giao-nhan")
async def giao_nhan(tid: str, nguoi_nhan: str = Form(""), sdt: str = Form(""), tinh_trang: str = Form("du"),
                    ghi_chu: str = Form(""), luc: str = Form(""), lat: str = Form(""), lng: str = Form(""),
                    ma_gui: str = Form(""), pod_no: str = Form(""),
                    chu_ky: Optional[UploadFile] = File(None), anh: Optional[List[UploadFile]] = File(None),
                    db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid) or _loi("KHONG_THAY", "Không có phiếu này.", 404)
    if user.role not in ("driver", "yard", "admin"):
        _loi("KHONG_CO_QUYEN", "Chỉ tài xế của phiếu (hoặc Bãi) ghi giao hàng hoàn tất.", 403)
    _cua_tai_xe(db, p, user)
    ma_gui = (ma_gui or "").strip()[:64]
    if ma_gui and p.pod_ref == ma_gui:                  # máy tài xế gửi lại lần đã nhận (mất mạng rồi có mạng)
        return xuat_phieu(db, p, vai=user.role)
    _chan_khoa(p, user)
    if p.kind != "giao":
        _loi("KHONG_PHAI_PHIEU_GIAO", "Phiếu gom về bãi của mình — không có người nhận ký.", 409)
    if p.transport_status == "dispatched":
        _loi("CHUA_XUAT_PHAT", "Xe chưa xuất phát — chưa ghi giao hàng hoàn tất được.", 409)
    if db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind == "pod_sign").count() and chu_ky:
        _loi("DA_KY", "Phiếu này đã có chữ ký người nhận. Muốn ký lại thì nhờ Bãi hoặc kế toán xoá chữ ký cũ.", 409)
    ds_anh = [a for a in (anh or []) if a is not None and (a.filename or "")]
    if len(ds_anh) > ANH_TOI_DA_SO:
        _loi("QUA_NHIEU_ANH", "Tối đa %d ảnh mỗi lần." % ANH_TOI_DA_SO)
    if not chu_ky and not ds_anh:
        _loi("THIEU_BANG_CHUNG", "Cần chữ ký người nhận hoặc ít nhất một ảnh biên bản / phiếu cân.")
    nguoi_nhan = (nguoi_nhan or "").strip()
    if chu_ky and not nguoi_nhan:
        _loi("THIEU_NGUOI_NHAN", "Có chữ ký thì phải ghi tên người nhận.")
    tinh_trang = (tinh_trang or "du").strip()
    if tinh_trang not in TINH_TRANG:
        _loi("TINH_TRANG_SAI", "Tình trạng hàng phải là đủ, thiếu hoặc hư hỏng.")
    if tinh_trang != "du" and not (ghi_chu or "").strip():
        _loi("THIEU_GHI_CHU", "Hàng thiếu hoặc hư hỏng thì phải ghi rõ thiếu / hỏng gì.")
    try:
        luc_ky = dt.datetime.fromisoformat(luc.strip().replace("Z", "+00:00")) if (luc or "").strip() else dt.datetime.now()
        if luc_ky.tzinfo is not None:
            luc_ky = luc_ky.astimezone().replace(tzinfo=None)      # giờ máy chủ (Lào, cùng múi với máy tài xế)
    except ValueError:
        _loi("GIO_SAI", "Giờ ký không đúng dạng.")
    if luc_ky > dt.datetime.now() + dt.timedelta(minutes=10):
        _loi("GIO_SAI", "Giờ ký ở tương lai — kiểm lại giờ trên điện thoại.")
    try:
        vi_do = float(lat) if (lat or "").strip() else None
        kinh_do = float(lng) if (lng or "").strip() else None
    except ValueError:
        vi_do = kinh_do = None
    if vi_do is not None and not (-90 <= vi_do <= 90 and -180 <= kinh_do <= 180):
        vi_do = kinh_do = None

    moi = []
    tong = sum((a.size or 0) for a in ds_anh) + ((chu_ky.size or 0) if chu_ky else 0)
    if tong > TEP_TOI_DA:
        _loi("TEP_QUA_LON", "Một lần gửi %.1f MB, tối đa 10 MB — bớt ảnh." % (tong / 1048576))
    if chu_ky:
        moi.append(await _luu_tep(p, chu_ky, "pod_sign", user, chi_png=True))
    for a in ds_anh:
        moi.append(await _luu_tep(p, a, "pod", user))
    for a in moi:
        db.add(a)
    p.pod_receiver = nguoi_nhan or p.pod_receiver
    p.pod_phone = (sdt or "").strip() or p.pod_phone
    p.pod_condition, p.pod_note = tinh_trang, (ghi_chu or "").strip() or None
    p.pod_at, p.pod_date = luc_ky, luc_ky.date()
    p.pod_lat, p.pod_lng = vi_do, kinh_do
    p.pod_by, p.pod_ref = user.full_name, ma_gui or None
    p.pod_no = (pod_no or "").strip() or p.pod_no or ("POD-" + p.doc_no.split("/")[0])
    _ghi_log(db, p, user, "a_pod_sign")
    db.commit()
    return xuat_phieu(db, p, vai=user.role)
