# -*- coding: utf-8 -*-
"""Đăng nhập bằng tài khoản GLS (Web / API anh Khang) — việc 4 của đợt chuyển sang module Vận tải C# (08/10).

Hai việc:
  * `dang_nhap(ten, mat_khau)` — gọi POST {GLS}/api/v2/auth/login (như màn đăng nhập Web GLS), trả token GLS hoặc None.
  * `xac_thuc(token)` — token GLS có thật không: gọi GET {GLS}/api/v1/auth/info bằng chính token (đúng cách Web GLS tự
    kiểm phiên, AuthenticationMiddleware), nhớ kết quả vài phút. Token sai / hết hạn → None.
Tài khoản GLS gắn với tài khoản EPL qua cột users.gls_username (Admin đặt ở màn Tài khoản); vai, tài xế, kho vẫn của EPL.

Không lưu, không ghi log token. Từ auth/info chỉ giữ tên, mã người dùng, chi nhánh — bỏ mọi trường khoá / refresh token.
Địa chỉ GLS: QLSX_BASE_URL, không có thì lấy giao thức + tên máy của EPL_ACC_CODE_API (cùng chỗ gửi bút toán / SO).
"""
import base64
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from fastapi import HTTPException

from services import mang as MANG

CHO_GIAY = 15
_NHO = {}                      # sha256(token) → (thông tin, hết hạn theo time.time())
_KHOA = threading.Lock()


def bat():
    """Màn đăng nhập trang điều xe gọi API đăng nhập GLS — EPL_DANG_NHAP_GLS=1. Mặc định tắt (chỉ tài khoản EPL)."""
    return (os.getenv("EPL_DANG_NHAP_GLS") or "").strip().lower() in ("1", "true", "bat", "on", "yes")


def _nho_giay():
    try:
        return max(30, int(os.getenv("EPL_GLS_XAC_THUC_GIAY") or 300))
    except ValueError:
        return 300


def goc():
    g = (os.getenv("QLSX_BASE_URL") or "").strip()
    if not g:
        acc = (os.getenv("EPL_ACC_CODE_API") or "").strip()
        u = urlsplit(acc) if acc else None
        g = "%s://%s" % (u.scheme, u.netloc) if u and u.scheme and u.netloc else ""
    return g.rstrip("/")


def la_jwt(token):
    """Token GLS là JWT (3 đoạn, đoạn đầu giải ra JSON có "alg"). Token EPL cũ là `tên.hết_hạn.chữ_ký` — không giải ra JSON."""
    phan = (token or "").split(".")
    if len(phan) != 3:
        return False
    try:
        dau = json.loads(base64.urlsafe_b64decode(phan[0] + "=" * (-len(phan[0]) % 4)))
        return isinstance(dau, dict) and "alg" in dau
    except Exception:  # noqa: BLE001
        return False


def _het_han_jwt(token):
    """`exp` trong JWT (không kiểm chữ ký — chữ ký do API GLS kiểm khi gọi auth/info). Không đọc được → None."""
    try:
        p = token.split(".")[1]
        return int(json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4))).get("exp") or 0) or None
    except Exception:  # noqa: BLE001
        return None


def _goi(method, duong, token=None, than=None):
    """→ (http, thân dict | None). Mất mạng / quá giờ → HTTPException 503."""
    g = goc()
    if not g:
        raise HTTPException(503, {"ma": "CHUA_CAU_HINH_GLS",
                                  "loi": "Chưa cấu hình địa chỉ máy chủ đăng nhập (QLSX_BASE_URL hoặc EPL_ACC_CODE_API)."})
    dau = {"Accept": "application/json"}
    if token:
        dau["Authorization"] = "Bearer " + token
    du_lieu = None
    if than is not None:
        du_lieu = json.dumps(than).encode("utf-8")
        dau["Content-Type"] = "application/json"
    yc = urllib.request.Request(g + duong, data=du_lieu, headers=dau, method=method)
    try:
        with MANG.mo(yc, timeout=CHO_GIAY) as tra:
            return tra.status, json.loads(tra.read().decode("utf-8", "replace") or "null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace") or "null")
        except Exception:  # noqa: BLE001
            return e.code, None
    except Exception:  # noqa: BLE001 — mất mạng, quá giờ, chứng chỉ…
        raise HTTPException(503, {"ma": "KHONG_GOI_DUOC_GLS", "loi": "Không kết nối được máy chủ đăng nhập. Thử lại sau."})


def _ket_qua(than):
    """Phong bì GLS {Success, Result} — Success false (kể cả khi HTTP 200) là thất bại."""
    if not isinstance(than, dict) or than.get("Success") is False:
        return None
    return than.get("Result")


def xac_thuc(token):
    """Token GLS hợp lệ → {user_id, username, full_name, branch_id, object_id}; không hợp lệ → None."""
    if not la_jwt(token):
        return None
    exp = _het_han_jwt(token)
    bay_gio = time.time()
    if exp and exp <= bay_gio:
        return None
    khoa = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with _KHOA:
        nho = _NHO.get(khoa)
        if nho and nho[1] > bay_gio:
            return nho[0]
    http, than = _goi("GET", "/api/v1/auth/info", token=token)
    r = _ket_qua(than) if http == 200 else None
    if not isinstance(r, dict) or int(r.get("UserID") or 0) <= 0 or not r.get("UserName"):
        return None
    tt = {"user_id": int(r["UserID"]), "username": str(r["UserName"]).strip(), "full_name": r.get("FullName") or "",
          "branch_id": r.get("BranchId"), "object_id": r.get("ObjectId")}
    het = bay_gio + _nho_giay()
    if exp:
        het = min(het, exp)
    with _KHOA:
        if len(_NHO) > 2000:          # không để bộ nhớ phình: xoá mục đã hết hạn
            for k in [k for k, v in _NHO.items() if v[1] <= bay_gio]:
                _NHO.pop(k, None)
        _NHO[khoa] = (tt, het)
    return tt


# 08/10 (việc 6): vai điều xe lấy theo mã quyền GLS Logistics.Role.<Vai> (script 20261008_logistics_role_permissions.sql,
# TargetCode = mã vai EPL). Có nhiều vai thì lấy vai đứng trước trong THU_TU_VAI (đúng thứ tự trong script).
THU_TU_VAI = ("admin", "acct", "expacct", "rev", "treasury", "cash", "fuel", "yard", "repair", "parts", "depot", "driver")
TIEN_TO_QUYEN = "logistics.role."
_NHO_VAI = {}


def vai(token):
    """Tập vai EPL theo mã quyền hiệu lực của người dùng GLS (GET api/v1/ui-shell/get → Permissions). Lỗi / không có → tập rỗng
    (trang điều xe giữ vai đang đặt ở màn Tài khoản)."""
    khoa = hashlib.sha256(token.encode("utf-8")).hexdigest()
    bay_gio = time.time()
    with _KHOA:
        nho = _NHO_VAI.get(khoa)
        if nho and nho[1] > bay_gio:
            return nho[0]
    try:
        http, than = _goi("GET", "/api/v1/ui-shell/get", token=token)
    except HTTPException:
        return frozenset()
    r = _ket_qua(than) if http == 200 else None
    ra = set()
    for q in (r or {}).get("Permissions") or []:
        ma = str((q or {}).get("PermissionCode") or "")
        if ma.lower().startswith(TIEN_TO_QUYEN):
            v = str(q.get("TargetCode") or ma[len(TIEN_TO_QUYEN):]).strip().lower()
            if v in THU_TU_VAI:
                ra.add(v)
    ra = frozenset(ra)
    het = bay_gio + _nho_giay()
    exp = _het_han_jwt(token)
    with _KHOA:
        _NHO_VAI[khoa] = (ra, min(het, exp) if exp else het)
    return ra


def chon_vai(vai_dang_dat, cac_vai_gls):
    """Vai dùng cho lượt này: không có mã GLS → vai đang đặt; vai đang đặt có trong mã GLS → giữ; không thì vai đầu tiên theo thứ tự."""
    if not cac_vai_gls:
        return vai_dang_dat
    if vai_dang_dat in cac_vai_gls:
        return vai_dang_dat
    return next(v for v in THU_TU_VAI if v in cac_vai_gls)


def dang_nhap(ten, mat_khau):
    """Tên + mật khẩu GLS → token GLS (chuỗi) hoặc None nếu GLS từ chối."""
    http, than = _goi("POST", "/api/v2/auth/login", than={"Username": ten, "Password": mat_khau, "RememberPassword": False})
    tok = _ket_qua(than) if http == 200 else None
    return tok.strip() if isinstance(tok, str) and tok.strip() else None
