# -*- coding: utf-8 -*-
"""Sổ chứng từ — điểm nối cho module kế toán (anh Khang) kéo phiếu thu / chi / nhập kho / xuất kho.

Bên mình không có sổ kế toán. Bảng này chỉ là "hộp thư đi": mỗi bước nghiệp vụ bỏ vào một tờ,
bên kế toán kéo về (`chua_day=1`), tạo phiếu bên họ, rồi báo lại `da-day`. Xem services/chung_tu.py.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ChungTu
from services import chung_tu as CT
from services.bao_mat import can_vai, nguoi_hien_tai

router = APIRouter()
XEM = ("acct", "expacct", "rev", "treasury", "cash", "fuel", "depot", "admin")


def _ngay(s, ten):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "%s phải dạng YYYY-MM-DD." % ten})


@router.get("/api/chung-tu/loai")
def ds_loai(user=Depends(nguoi_hien_tai)):
    """Danh mục loại chứng từ kèm hai vế định khoản gợi ý (xe nhà · mục vận chuyển)."""
    ra = []
    for ma, (ten, ten_lo, co_dk) in CT.LOAI.items():
        no, no_ten, co, co_ten = CT.dinh_khoan(ma) if co_dk else (None, None, None, None)
        ra.append({"ma": ma, "ten": ten, "ten_lo": ten_lo, "dinh_khoan": co_dk,
                   "no": no, "no_ten": no_ten, "co": co, "co_ten": co_ten})
    return ra


@router.get("/api/chung-tu")
def ds_chung_tu(loai: str = "", tu: str = "", den: str = "", trip_id: str = "", chua_day: int = 0,
                doi_tuong: str = "", limit: int = 500, db: Session = Depends(get_db), user=Depends(can_vai(*XEM))):
    q = db.query(ChungTu)
    if loai:
        q = q.filter(ChungTu.loai.in_([x.strip().upper() for x in loai.split(",") if x.strip()]))
    if tu:
        q = q.filter(ChungTu.ngay >= _ngay(tu, "Từ ngày"))
    if den:
        q = q.filter(ChungTu.ngay <= _ngay(den, "Đến ngày"))
    if trip_id:
        q = q.filter(ChungTu.trip_id == trip_id)
    if doi_tuong:
        q = q.filter(ChungTu.doi_tuong_loai == doi_tuong)
    if chua_day:
        q = q.filter(ChungTu.da_day.is_(False))
    q = q.order_by(ChungTu.ngay.desc(), ChungTu.ts.desc()).limit(max(1, min(limit, 2000)))
    ds = [CT.xuat(c) for c in q.all()]
    tong = {}
    for c in ds:
        t = tong.setdefault(c["loai"], {"so_to": 0, "tien_lak": 0.0, "chua_day": 0})
        t["so_to"] += 1
        t["tien_lak"] += c["tien_lak"] or 0
        t["chua_day"] += 0 if c["da_day"] else 1
    return {"ds": ds, "tong": tong}


@router.get("/api/chung-tu/{cid}")
def mot_chung_tu(cid: str, db: Session = Depends(get_db), user=Depends(can_vai(*XEM))):
    c = db.get(ChungTu, cid)
    if not c:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chứng từ này."})
    return CT.xuat(c)


@router.post("/api/chung-tu/{cid}/da-day")
def danh_dau_da_day(cid: str, d: dict = Body(default={}), db: Session = Depends(get_db),
                    user=Depends(can_vai("acct", "expacct", "rev", "treasury", "cash", "admin"))):
    """Bên kế toán (hoặc người đối chiếu) báo đã nhận tờ này. Gửi {"da_day": false} để mở lại."""
    c = db.get(ChungTu, cid)
    if not c:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chứng từ này."})
    c.da_day = bool(d.get("da_day", True))
    c.day_luc = dt.datetime.utcnow() if c.da_day else None
    db.commit()
    return CT.xuat(c)
