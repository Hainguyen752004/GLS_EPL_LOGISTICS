# -*- coding: utf-8 -*-
"""Kho HÀNG khách gửi ở bãi Thà Bốc — quặng nằm giữa hai chặng. Lại ở TRANG ĐIỀU XE từ 05/10 (bỏ kho tạm 8031).

Sổ goods_moves, tờ PNK_HH / PXK_HH / DC_HH tự sinh theo DO và đơn điều chỉnh: services/kho_hang_dia.py. Ở đây chỉ đọc / lập /
duyệt (giao ước với giao diện 05/10, khoá JSON tiếng Việt không dấu; lỗi {"detail": {"ma", "loi"}}):

    GET  /api/kho-hang/ton?q=&khach=&chi_con=1        tồn theo lô + tổng + cờ quyền (tài xế 403)
    GET  /api/kho-hang/lo                              ô chọn lô của phiếu giao (khuôn cũ, giữ nguyên)
    GET  /api/kho-hang/lo/{lo_id}                      chi tiết lô: nhập · các lần xuất · điều chỉnh
    GET  /api/trips/{tid}/to-kho-hang                  tờ PNK_HH (DO gom) / PXK_HH (DO giao) để in — chưa có → 404 CHUA_CO_TO
    POST /api/kho-hang/dieu-chinh                      Bãi (yard) / Sếp lập đơn {lo_id, tan có dấu ≠ 0, ly_do} → chờ duyệt
    GET  /api/kho-hang/dieu-chinh?trang_thai=          cho · da_duyet · tu_choi
    POST /api/kho-hang/dieu-chinh/{id}/duyet           KT Thu/Chi VC (acct) / Sếp {dong_y, ghi_chu} → adj + DC_HH
    GET  /api/kho-hang/doi-soat?ngay=YYYY-MM-DD        DO gom đã tới ↔ PNK_HH, DO giao ↔ PXK_HH

Phân quyền ở API (vai theo bảng Nhiệm Vụ — services/phan_quyen.py): lập = yard · admin; duyệt = acct · admin; xem = mọi vai
trừ tài xế. `quyen` trả kèm để giao diện ẩn nút. KHO_NGUON=kho_tam (quay lui): sổ ở kho tạm → các đường mới trả 409.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Trip
from routes.kho_xem import go_gia
from services import kho_hang_dia as KHD
from services import kho_ke_toan as KK
from services import kho_qlsx as KQ
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import thay_gia_kho

router = APIRouter()


def _quyen(vai):
    return {"lap_dieu_chinh": vai in KHD.VAI_LAP_DC, "duyet_dieu_chinh": vai in KHD.VAI_DUYET_DC}


def _xem(user):
    """Mọi vai trừ tài xế xem kho hàng; kho tạm đang bật (quay lui) thì sổ không ở đây."""
    if user.role == "driver":
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế không xem kho hàng."})
    if not KQ.bat():
        raise HTTPException(409, {"ma": "SO_O_KHO_TAM", "loi": "Đang chạy KHO_NGUON=kho_tam — sổ kho hàng ở kho tạm, không ở trang điều xe."})
    return user


def _ngay(s, ten="ngay"):
    if not s:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "%s phải dạng YYYY-MM-DD." % ten})


@router.get("/api/kho-hang")
@router.get("/api/kho-hang/ton")
def ton_kho(q: str = "", khach: str = "", chi_con: int = 1, limit: int = 2000, db: Session = Depends(get_db),
            user=Depends(nguoi_hien_tai)):
    """Tồn kho hàng theo lô. `chi_con=1` (mặc định): chỉ lô còn hàng, cũ trước; `chi_con=0`: cả lô đã hết, mới trước."""
    _xem(user)
    ra = KHD.ton_kho(db, q=q, khach=khach, chi_con=bool(chi_con), gioi_han=limit)
    ra["quyen"] = _quyen(user.role)
    return ra


@router.get("/api/kho-hang/lo")
def lo_con_hang(tru_phieu: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Các lô còn hàng, để màn phiếu giao hàng chọn lấy từ đâu (khuôn cũ: lo_trip_id, doc_no, goods_name, ngay, nhap_t,
    dieu_chinh_t, con_t, customer_name, origin, truck_no).

    `tru_phieu` = phiếu giao đang sửa: bỏ qua phần chính nó đang giữ, không thì sửa lại phiếu cũ sẽ
    thấy lô hết hàng dù chính nó là người đang giữ.

    Lô hôm nay chỉ có tấn; vai không thấy giá vốn kho (Bãi lập phiếu giao) vẫn gỡ mọi khoá tiền, phòng bên kho thêm.
    """
    ds = KK.lo_hang(db, tru_phieu)
    return ds if thay_gia_kho(user.role) else go_gia(ds)


@router.get("/api/kho-hang/lo/{lo_id}")
def mot_lo(lo_id: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _xem(user)
    ra = KHD.mot_lo(db, lo_id)
    ra["quyen"] = _quyen(user.role)
    return ra


@router.get("/api/trips/{tid}/to-kho-hang")
def to_kho_hang(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Tờ kho hàng để in của một DO (PNK_HH cho DO gom, PXK_HH cho DO giao)."""
    _xem(user)
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    return KHD.to_kho_hang(db, p)


@router.get("/api/kho-hang/dieu-chinh")
def ds_dieu_chinh(trang_thai: str = "", lo_id: str = "", limit: int = 500, db: Session = Depends(get_db),
                  user=Depends(nguoi_hien_tai)):
    _xem(user)
    return {"items": KHD.ds_dieu_chinh(db, trang_thai=(trang_thai or "").strip() or None, lo_id=(lo_id or "").strip() or None,
                                       gioi_han=limit),
            "quyen": _quyen(user.role)}


@router.post("/api/kho-hang/dieu-chinh")
def lap_dieu_chinh(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bãi lập đơn điều chỉnh một lô (cân sai, hao ở bãi, kiểm kê, đóng lô dư lẻ) — chờ KT Thu/Chi VC duyệt, chưa đổi tồn."""
    _xem(user)
    if user.role not in KHD.VAI_LAP_DC:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc (Bãi) hoặc Sếp lập phiếu điều chỉnh kho hàng."})
    don = KHD.lap_dieu_chinh(db, d.get("lo_id"), d.get("tan"), d.get("ly_do"), user)
    db.commit()
    return KHD.mot_don(db, don)


@router.post("/api/kho-hang/dieu-chinh/{did}/duyet")
def duyet_dieu_chinh(did: str, d: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """KT Thu/Chi Viêng Chăn (người xác nhận mục II — cân, hàng) hoặc Sếp duyệt / từ chối. Duyệt → dòng adj + tờ DC_HH."""
    _xem(user)
    if user.role not in KHD.VAI_DUYET_DC:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Thu/Chi Viêng Chăn hoặc Sếp duyệt phiếu điều chỉnh kho hàng."})
    if not isinstance(d.get("dong_y"), bool):
        raise HTTPException(422, {"ma": "THIEU_DONG_Y", "loi": "Gửi dong_y = true (duyệt) hoặc false (từ chối)."})
    don = KHD.duyet_dieu_chinh(db, did, d["dong_y"], d.get("ghi_chu"), user)
    db.commit()
    return KHD.mot_don(db, don)


@router.get("/api/kho-hang/doi-soat")
def doi_soat(ngay: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _xem(user)
    return KHD.doi_soat(db, _ngay(ngay))
