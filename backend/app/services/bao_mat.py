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


def nguoi_hien_tai(request: Request, db: Session = Depends(get_db)):
    from models import User
    dau = request.headers.get("Authorization", "")
    token = dau[7:].strip() if dau.lower().startswith("bearer ") else ""
    username = doc_phien(token) if token else None
    if not username:
        raise HTTPException(401, {"ma": "CHUA_DANG_NHAP", "loi": "Vui lòng đăng nhập."})
    user = db.query(User).filter(User.username == username, User.active.is_(True)).first()
    if not user:
        raise HTTPException(401, {"ma": "TAI_KHOAN_KHOA", "loi": "Tài khoản không còn hiệu lực."})
    return user


def can_vai(*vai):
    """Dependency: chỉ cho các vai được kể tên (admin luôn qua)."""
    def kiem(user=Depends(nguoi_hien_tai)):
        if user.role != "admin" and user.role not in vai:
            raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                      "loi": "Vai %s không được làm việc này." % user.role})
        return user
    return kiem
