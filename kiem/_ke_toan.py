# -*- coding: utf-8 -*-
"""Bộ kiểm của trang điều xe gọi sang KHO TẠM (máy EPL_KETOAN) — kho dời sang đó 28/09; từ 01/10 máy đó bỏ phần tiền,
chỉ còn làm kho tạm.

Địa chỉ kho tạm: biến môi trường EPL_KT (mặc định http://127.0.0.1:8031 — máy thử). Máy chủ trang điều xe đang kiểm
phải trỏ cùng kho tạm đó (cấu hình kho `kho_api`; chưa lưu khoá mới thì khoá cũ `ke_toan_api` — services/goi_ke_toan.py),
nếu không thì tồn đọc ở hai nơi là hai kho khác nhau. Hai bên dùng CÙNG tên đăng nhập và cùng mật khẩu demo 1234.
"""
import json
import os
import urllib.error
import urllib.request

KT = os.getenv("EPL_KT", "http://127.0.0.1:8031").rstrip("/")
TOKEN = {}


def kt(duong, du_lieu=None, vai=None, method=None):
    if vai and vai not in TOKEN:
        vao(vai)
    dau = {"Content-Type": "application/json", **({"Authorization": "Bearer " + TOKEN[vai]} if vai else {})}
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(KT + duong, data=than, headers=dau, method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, {}


def vao(u):
    r = urllib.request.Request(KT + "/api/dang-nhap", data=json.dumps({"username": u, "password": "1234"}).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(r, timeout=30) as t:
        TOKEN[u] = json.loads(t.read())["token"]


def to_kho(q, loai="PXK_PT"):
    """Tờ kho sinh ở trang kế toán (source EPL_KETOAN) có `q` trong số phiếu / diễn giải."""
    s, ds = kt("/api/chung-tu?loai=%s&limit=1000&q=%s" % (loai, urllib.request.quote(q)), vai="ketoan")
    assert s == 200, (s, ds)
    return [v for v in ds if v["source"] == "EPL_KETOAN"]
