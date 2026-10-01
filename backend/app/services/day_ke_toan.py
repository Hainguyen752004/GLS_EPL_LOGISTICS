# -*- coding: utf-8 -*-
"""ĐẨY CHỨNG TỪ sang trang kế toán tạm — ĐÃ BỎ từ 01/10/2026 (chủ dự án chốt).

Trước đây tờ chứng từ (phiếu thu, phiếu chi, nhập / xuất kho, hoá đơn…) được đẩy `POST /api/v1/epl-lao/vouchers` sang
trang kế toán tạm (EPL_KETOAN) để bên đó vào sổ. Từ 01/10 trang đó bỏ phần TIỀN (số bên đó là số thử, bỏ hết, cắt sổ
01/10), chỉ còn làm KHO TẠM; mọi việc tiền đi qua hệ anh Tune (services/gui_tune.py, chi_tune.py) — hệ anh Tune không
có cửa nhận phong bì này. Nên bên này **thôi gửi**: không còn lệnh HTTP nào đi ra từ tệp này.

Tờ chứng từ (`ChungTu`, services/chung_tu.py) VẪN sinh như cũ — để in / xem và định khoản cho màn Quy trình. Cờ
`da_day` vẫn là "bên kế toán đã nhận / đã đối chiếu", chỉ còn đánh tay (`POST /api/chung-tu/{id}/da-day`).

Còn lại trong tệp:
  · `cau_hinh` / `dat_cau_hinh` — đọc / ghi bảng `cau_hinh` chung (nhiều nơi gọi `DK.cau_hinh`: khoá kho, khoá nhận,
    hai mã bên kế toán cấp sau…). Cấu hình KHO đọc qua services/goi_ke_toan.py (`kho_api`, `kho_token`, `kho_web`).
  · `day_mot` / `day_hang_loat` / `trang_thai` — giữ tên và kiểu trả về cũ nhưng KHÔNG làm gì, để chỗ nào còn gọi
    không gãy. Xoá hẳn ở đợt dọn dẹp, cùng các đường `/api/chung-tu/day`, `/api/chung-tu/{id}/day`.
"""
import datetime as dt
import os

from models import CauHinh, ChungTu

KHONG_DAY_NUA = "Từ 01/10 không đẩy chứng từ sang trang kế toán tạm nữa — việc tiền đi qua hệ kế toán anh Tune."


# ---------------------------------------------------------------- cấu hình
def cau_hinh(db, khoa, mac_dinh=""):
    r = db.get(CauHinh, khoa)
    if r and (r.gia_tri or "").strip():
        return r.gia_tri.strip()
    return (os.getenv("EPL_" + khoa.upper()) or mac_dinh).strip()


def dat_cau_hinh(db, khoa, gia_tri, user=None):
    r = db.get(CauHinh, khoa)
    if not r:
        r = CauHinh(khoa=khoa); db.add(r)
    r.gia_tri = (gia_tri or "").strip()
    r.cap_nhat = dt.datetime.utcnow()
    r.by_user = getattr(user, "full_name", None)
    return r


def trang_thai(db):
    """Màn Sổ chứng từ / Đề nghị thu hỏi "đã nối đẩy chưa" để hiện nút Đẩy: luôn `cau_hinh: False` → không hiện nút.
    Vẫn đếm tờ chưa đánh dấu đã nhận (chỉ mục một phần ix_chung_tu_chua_day — số có giới hạn, không đếm mọi tờ)."""
    from sqlalchemy import func
    chua = db.query(func.count(ChungTu.id)).filter(ChungTu.da_day.is_(False)).scalar()
    return {"cau_hinh": False, "khong_day_nua": True, "ghi_chu": KHONG_DAY_NUA, "api": "", "co_token": False,
            "chua_day": chua, "loi": 0, "day_gan_nhat": None}


# ---------------------------------------------------------------- đẩy (đã bỏ — giữ chỗ cho người còn gọi)
def day_mot(db, c, user=None):
    """KHÔNG đẩy nữa. Trả (False, lý do) như kiểu cũ; không đụng tờ (không tăng lần thử, không ghi lỗi)."""
    return False, KHONG_DAY_NUA


def day_hang_loat(db, user=None, loai=None, gioi_han=200):
    """KHÔNG đẩy nữa. Trả tóm tắt rỗng đúng kiểu cũ."""
    return {"thu": 0, "xong": 0, "loi": 0, "chi_tiet_loi": [], "khong_day_nua": True, "ghi_chu": KHONG_DAY_NUA}
