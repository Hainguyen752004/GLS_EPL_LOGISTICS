# -*- coding: utf-8 -*-
"""Kho HÀNG ở bãi Thà Bốc — quặng nằm giữa hai chặng.

Bãi đứng giữa như một bưu cục: DO gom chở hàng từ mỏ về thì NHẬP KHO, DO giao lấy hàng trong kho đi
cảng thì XUẤT KHO. Màn này cho thấy còn lô nào, mỗi lô còn mấy tấn, và sổ nhập xuất.

Không có bảng tồn riêng: tồn luôn cộng dồn từ sổ, để không bao giờ lệch. Xem services/kho_hang.py.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.bao_mat import can_vai, nguoi_hien_tai
from services import kho_hang as KH

router = APIRouter()


def _ngay(v, ten):
    if not v:
        return None
    try:
        return dt.date.fromisoformat(v)
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ô %s phải ghi dạng YYYY-MM-DD." % ten})


@router.get("/api/kho-hang")
def xem_kho(tu: str = None, den: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Tồn theo lô + sổ nhập xuất. Lô = một phiếu gom hàng."""
    lo = KH.danh_sach_lo(db, con_hang=False)
    so, ton = KH.so_kho(db, _ngay(tu, "tu"), _ngay(den, "den"))
    return {"ton_t": ton, "lo": lo, "so": so,
            "con_lo": len([x for x in lo if x["con_t"] > 0.0005])}


@router.get("/api/kho-hang/lo")
def lo_con_hang(tru_phieu: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Các lô còn hàng, để màn phiếu giao hàng chọn lấy từ đâu.

    `tru_phieu` = phiếu giao đang sửa: bỏ qua phần chính nó đang giữ, không thì sửa lại phiếu cũ sẽ
    thấy lô hết hàng dù chính nó là người đang giữ.
    """
    return KH.danh_sach_lo(db, con_hang=True, tru_phieu_id=tru_phieu)


@router.post("/api/kho-hang/dieu-chinh")
def dieu_chinh(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(can_vai("acct", "admin"))):
    """Kế toán (KT Thu/Chi VC, người kiểm mục II) hoặc Sếp điều chỉnh tồn một lô: {lo_trip_id, qty_t, ly_do}.
    Bãi không tự điều chỉnh — họ báo, kế toán ghi; đó cũng là cách Excel của họ đang chạy."""
    m = KH.dieu_chinh(db, data.get("lo_trip_id"), data.get("qty_t"), data.get("ly_do"), user)
    db.commit()
    return {"ok": True, "id": m.id, "qty_t": m.qty_t, "con_t": KH.ton_lo(db, m.lo_trip_id)}
