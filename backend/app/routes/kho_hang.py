# -*- coding: utf-8 -*-
"""Kho HÀNG ở bãi Thà Bốc — quặng nằm giữa hai chặng. Ở TRANG KẾ TOÁN từ 28/09 (đợt 5).

Sổ nhập xuất, tồn từng lô, điều chỉnh kho (DC_HH) và màn Kho hàng dời sang trang kế toán (Kho → Kho hàng). Bên này
chỉ còn dòng hàng trên phiếu (services/kho_hang.py) và ô chọn lô của phiếu giao — ô đó hỏi thẳng bên kia.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from routes.kho_xem import go_gia
from services import kho_ke_toan as KK
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import thay_gia_kho

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Kho hàng nay quản lý ở trang kế toán (Kho → Kho hàng)."}


@router.get("/api/kho-hang")
def xem_kho(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/kho-hang/dieu-chinh")
def dieu_chinh(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.get("/api/kho-hang/lo")
def lo_con_hang(tru_phieu: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Các lô còn hàng (sổ ở trang kế toán), để màn phiếu giao hàng chọn lấy từ đâu. Trang kế toán tắt → 503: không
    biết lô còn bao nhiêu thì cũng không lưu được phiếu giao lấy hàng.

    `tru_phieu` = phiếu giao đang sửa: bỏ qua phần chính nó đang giữ, không thì sửa lại phiếu cũ sẽ
    thấy lô hết hàng dù chính nó là người đang giữ.

    Lô hôm nay chỉ có tấn; vai không thấy giá vốn kho (Bãi lập phiếu giao) vẫn gỡ mọi khoá tiền, phòng bên kho thêm.
    """
    ds = KK.lo_hang(db, tru_phieu)
    return ds if thay_gia_kho(user.role) else go_gia(ds)
