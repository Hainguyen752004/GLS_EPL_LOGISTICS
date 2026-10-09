# -*- coding: utf-8 -*-
"""Đăng nhập kiểu 2016: tên + mật khẩu, phiên là một chuỗi ký HMAC gửi kèm mỗi yêu cầu.

Không JWT, không OAuth, không cookie phức tạp — một token `username.hết_hạn.chữ_ký` trong
header `Authorization: Bearer …`. Đủ cho một hệ nội bộ chạy trong mạng công ty, và ai đọc
mã cũng hiểu ngay nó làm gì.

Mật khẩu băm PBKDF2-SHA256 với muối riêng từng người — KHÔNG lưu chữ thường, kể cả bản demo.
"""
import base64
import hashlib
import hmac
import os
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db

KHOA = (os.getenv("EPL_LAO_SECRET") or "doi-khoa-nay-khi-len-may-chu-that").encode("utf-8")
HAN_PHIEN_GIAY = 12 * 3600      # một ca làm việc


def bam_mat_khau(mat_khau):
    muoi = os.urandom(16)
    bam = hashlib.pbkdf2_hmac("sha256", mat_khau.encode("utf-8"), muoi, 120_000)
    return base64.b64encode(muoi).decode() + "$" + base64.b64encode(bam).decode()


def khop_mat_khau(mat_khau, chuoi_bam):
    try:
        muoi_b64, bam_b64 = chuoi_bam.split("$", 1)
        muoi = base64.b64decode(muoi_b64)
        bam = hashlib.pbkdf2_hmac("sha256", mat_khau.encode("utf-8"), muoi, 120_000)
        return hmac.compare_digest(bam, base64.b64decode(bam_b64))
    except Exception:  # noqa: BLE001 — chuỗi băm hỏng thì coi như sai mật khẩu
        return False


def _ky(noi_dung):
    return hmac.new(KHOA, noi_dung.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def ky_phien(username):
    het_han = int(time.time()) + HAN_PHIEN_GIAY
    noi_dung = "%s.%d" % (username, het_han)
    return noi_dung + "." + _ky(noi_dung)


def doc_phien(token):
    """Trả username nếu token hợp lệ và còn hạn; không thì None."""
    try:
        username, het_han, chu_ky = token.rsplit(".", 2)
    except ValueError:
        return None
    if not hmac.compare_digest(_ky("%s.%s" % (username, het_han)), chu_ky):
        return None
    if int(het_han) < time.time():
        return None
    return username


def nguoi_dung_gls(db, tt):
    """Tài khoản EPL gắn với tài khoản GLS `tt` (kết quả dang_nhap_gls.xac_thuc) — theo users.gls_username, không phân biệt hoa thường."""
    from sqlalchemy import func
    from models import User
    ten = (tt.get("username") or "").strip().lower()
    return db.query(User).filter(func.lower(User.gls_username) == ten).first() if ten else None


def nguoi_hien_tai(request: Request, db: Session = Depends(get_db)):
    dau = request.headers.get("Authorization", "")
    return nguoi_tu_token(db, dau[7:].strip() if dau.lower().startswith("bearer ") else "")


def nguoi_tu_token(db, token):
    """Token EPL cũ (`tên.hết_hạn.chữ_ký`) hoặc token GLS → tài khoản EPL đang dùng; không thì HTTPException 401 / 403.
    Dùng chung cho header Authorization và cho ?tk=… của thẻ <img> / <a> mở tệp."""
    from models import User
    username = doc_phien(token) if token else None
    if username:
        user = db.query(User).filter(User.username == username, User.active.is_(True)).first()
        if not user:
            raise HTTPException(401, {"ma": "TAI_KHOAN_KHOA", "loi": "Tài khoản không còn hiệu lực."})
        return user
    # 08/10 (chuyển sang module Vận tải C#): token GLS — từ màn đăng nhập EPL (EPL_DANG_NHAP_GLS=1) hoặc từ Web GLS (BFF
    # chuyển tiếp token phiên). Kiểm bằng auth/info của API GLS, rồi lấy tài khoản EPL gắn với tài khoản GLS đó.
    from services import dang_nhap_gls as GLS
    tt = GLS.xac_thuc(token) if token else None
    if not tt:
        raise HTTPException(401, {"ma": "CHUA_DANG_NHAP", "loi": "Vui lòng đăng nhập."})
    user = nguoi_dung_gls(db, tt)
    if not user:
        raise HTTPException(403, {"ma": "CHUA_GAN_TAI_KHOAN_GLS",
                                  "loi": "Tài khoản «%s» chưa được cấp quyền dùng module Vận tải — nhờ Admin gắn ở màn Tài khoản." % tt["username"]})
    if not user.active:
        raise HTTPException(401, {"ma": "TAI_KHOAN_KHOA", "loi": "Tài khoản không còn hiệu lực."})
    # 08/10 (việc 6): vai theo mã quyền GLS Logistics.Role.* nếu người dùng có; không có thì giữ vai ở màn Tài khoản.
    # Đổi vai chỉ cho lượt gọi này: tách bản ghi khỏi phiên DB trước khi đổi để không bao giờ ghi ngược vào bảng users.
    cac_vai = GLS.vai(token)
    vai_moi = GLS.chon_vai(user.role, cac_vai)
    user.nguon_vai = "gls" if cac_vai else "epl"          # thuộc tính tạm của lượt gọi (không phải cột) — /api/toi trả ra
    if vai_moi != user.role:
        if vai_moi == "driver" and not user.driver_id:
            raise HTTPException(403, {"ma": "THIEU_TAI_XE", "loi": "Vai tài xế cần gắn tài xế ở màn Tài khoản của module Vận tải."})
        if vai_moi == "depot" and not user.place_id:
            raise HTTPException(403, {"ma": "THIEU_KHO", "loi": "Vai thủ kho nhiên liệu cần gắn kho ở màn Tài khoản của module Vận tải."})
        db.expunge(user)
        user.role = vai_moi
    return user


def can_vai(*vai):
    """Dependency: chỉ cho các vai được kể tên (admin luôn qua)."""
    def kiem(user=Depends(nguoi_hien_tai)):
        if user.role != "admin" and user.role not in vai:
            raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                      "loi": "Vai %s không được làm việc này." % user.role})
        return user
    return kiem


# ---------------------------------------------------------------- kho tạm (máy EPL_KETOAN) gọi sang (28/09)
# Từ 01/10 máy EPL_KETOAN bỏ phần tiền, chỉ còn làm KHO TẠM (cấp dầu QR, phụ tùng, sổ quặng gửi bãi, giá vốn, sửa chữa
# xe) — nhưng màn Cấp phát, Điểm đổ, Lệnh sửa chữa… bên đó vẫn gọi về đây, nên khoá nhận và cửa máy gọi GIỮ NGUYÊN.
# Tên `ke_toan` giữ như cũ (khoá `token_nhan_ke_toan` trong bảng cau_hinh của máy thật 8020, routes/lien_thong.py gọi
# theo tên này); đọc là "kho tạm". Đổi tên ở đợt dọn dẹp nếu cần, đổi cùng lúc cả khoá bảng.
def token_nhan_ke_toan(db):
    """Khoá kho tạm (máy EPL_KETOAN, xưa gọi "trang kế toán") phải mang khi gọi sang đây. Sếp tạo ở màn cấu hình rồi
    chép sang Cài đặt bên đó; hoặc đặt EPL_LAO_TOKEN_NHAN_KE_TOAN trong .env."""
    from models import CauHinh
    r = db.get(CauHinh, "token_nhan_ke_toan")
    return (r.gia_tri.strip() if r and r.gia_tri else "") or (os.getenv("EPL_LAO_TOKEN_NHAN_KE_TOAN") or "").strip()


def token_nhan_qlsx(db):
    """Khoá hệ kế toán của anh Tune (QLSX DemoLao) phải mang khi đọc API bàn giao DO ở đây. Tách riêng khỏi khoá của
    trang kế toán tạm (EPL_KETOAN): hai hệ, hai khoá, thu hồi cái này không làm tắt cái kia. Sếp tạo bằng
    `POST /api/handover/tao-khoa`; hoặc đặt EPL_LAO_TOKEN_NHAN_QLSX trong .env."""
    from models import CauHinh
    r = db.get(CauHinh, "token_nhan_qlsx")
    return (r.gia_tri.strip() if r and r.gia_tri else "") or (os.getenv("EPL_LAO_TOKEN_NHAN_QLSX") or "").strip()


def may_qlsx_goi(request: Request, db: Session = Depends(get_db)):
    """Hệ anh Tune đọc DO đã khoá (chỉ ĐỌC, không ghi gì vào đây) bằng `Authorization: Bearer <khoá>`. Không có người
    bấm bên này nên không cần `X-Nguoi-Dung`; trả tên máy để ghi nhật ký."""
    mong = token_nhan_qlsx(db)
    dau = request.headers.get("Authorization", "")
    tk = dau[7:].strip() if dau.lower().startswith("bearer ") else ""
    if not mong:
        raise HTTPException(503, {"ma": "CHUA_DAT_TOKEN", "loi": "EPL chưa tạo khoá cho hệ kế toán gọi sang."})
    if not tk or not hmac.compare_digest(tk, mong):
        raise HTTPException(401, {"ma": "SAI_TOKEN", "loi": "Khoá đọc bàn giao DO không đúng."})
    return "qlsx"


def may_ke_toan_goi(request: Request, db: Session = Depends(get_db)):
    """Kho đã dời sang máy EPL_KETOAN (28/09; từ 01/10 máy đó chỉ còn là kho tạm, bỏ phần tiền); màn bên đó cần đọc /
    ghi vào phiếu thì gọi sang đây bằng khoá máy, kèm `X-Nguoi-Dung: <tên đăng nhập>` của người đang bấm. Hai bên
    dùng CÙNG tên đăng nhập, nên người đó phải có tài khoản còn hiệu lực ở đây — trả về chính tài khoản đó, và quyền là quyền của vai
    người đó bên này (không có vai nào "máy" làm được hơn người)."""
    from models import User
    mong = token_nhan_ke_toan(db)
    dau = request.headers.get("Authorization", "")
    tk = dau[7:].strip() if dau.lower().startswith("bearer ") else ""
    if not mong:
        raise HTTPException(503, {"ma": "CHUA_DAT_TOKEN", "loi": "EPL chưa tạo khoá cho kho tạm gọi sang."})
    if not tk or not hmac.compare_digest(tk, mong):
        raise HTTPException(401, {"ma": "SAI_TOKEN", "loi": "Khoá nối EPL không đúng — kiểm lại Cài đặt bên kho tạm."})
    ten = (request.headers.get("X-Nguoi-Dung") or "").strip()
    u = db.query(User).filter(User.username == ten, User.active.is_(True)).first() if ten else None
    if not u:
        raise HTTPException(403, {"ma": "KHONG_CO_TAI_KHOAN",
                                  "loi": "Tài khoản \"%s\" không có trên EPL." % (ten or "?")})
    return u
