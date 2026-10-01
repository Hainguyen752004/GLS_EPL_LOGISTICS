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


# ---------------------------------------------------------------- 01/10: kho tạm CHẶN cấp quá tồn (409 VUOT_TON)
# Tồn đi theo chứng từ: bộ kiểm nào cấp dầu ở một kho thì NHẬP TRƯỚC đúng số lít sẽ cấp (phiếu nhập PNK_NL, giá = bình quân
# hiện tại của kho để giá vốn kho không đổi), rồi dọn: xoá phiếu thử (dầu đã cấp về kho) → gỡ dòng nhập thử. Kho đang ÂM thì
# dừng và nói rõ — không nhập bù để che số âm (dòng nhập bù đó cũng không gỡ được: kho tạm chặn xoá dòng nhập làm tồn âm).
# Dòng nhập thử nào chưa gỡ lúc bài kết thúc (kể cả khi bài hỏng giữa chừng) thì tự gỡ — sau phần dọn phiếu thử của bài.
_NHAP = []


def _go_het():
    for mid in list(_NHAP):
        go_nhap(mid)


import atexit as _atexit  # noqa: E402
_atexit.register(_go_het)


def kho_dau(ma_hay_id, vai="khonl"):
    """Một kho dầu ở kho tạm theo mã (KHO-TB…) hoặc id; không truyền gì / 'fp_yard' = kho gốc Thà Bốc."""
    s, g = kt("/api/nhien-lieu", vai=vai)
    assert s == 200, (s, g)
    ma = ma_hay_id or "KHO-TB"
    if ma == "fp_yard":
        ma = "KHO-TB"
    k = next((x for x in g["kho"] if x["id"] == ma or x.get("code") == ma), None)
    assert k, "không có kho dầu %s ở kho tạm %s" % (ma, KT)
    return k


def nhap_truoc(ma_hay_id, lit, ghi_chu="bộ kiểm: nhập trước rồi cấp", vai="khonl"):
    """Nhập `lit` lít vào kho trước khi cấp. Trả id dòng nhập (để `go_nhap` lúc dọn)."""
    import time as _t
    k = kho_dau(ma_hay_id, vai)
    if k["ton_lit"] < -0.001:
        raise SystemExit("DỪNG: kho %s đang âm %s L trên máy thử — kho tạm chặn cấp quá tồn; xử lý số âm (xoá phiếu thử cũ / "
                         "phiếu nhập thật) rồi chạy lại. Bộ kiểm không nhập bù để che số âm." % (k.get("code"), k["ton_lit"]))
    so = "NHAP-THU-%s" % _t.strftime("%d%H%M%S")
    s, g = kt("/api/nhien-lieu", {"kind": "in", "place_id": k["id"], "qty_l": lit, "unit_price": k.get("gia_bq") or 25000,
                                  "currency": "LAK", "doc_no": so, "note": ghi_chu}, vai=vai)
    assert s == 200, ("nhập trước", s, g)
    dong = next(r for r in g["rows"] if r["doc_no"] == so and r["kind"] == "in")
    _NHAP.append(dong["id"])
    print("  ✓ %-64s %s L → tồn %s L" % ("nhập trước vào %s (phiếu nhập, luật 01/10)" % k.get("code"), lit, kho_dau(k["id"], vai)["ton_lit"]))
    return dong["id"]


def go_nhap(move_id, vai="khonl"):
    """Dọn: gỡ dòng nhập thử (sau khi đã xoá phiếu thử — dầu đã cấp về kho). Trả mã HTTP."""
    if not move_id:
        return None
    s, g = kt("/api/nhien-lieu/%s" % move_id, vai=vai, method="DELETE")
    if s in (200, 404) and move_id in _NHAP:
        _NHAP.remove(move_id)
    if s != 200:
        print("  ! chưa gỡ được dòng nhập thử %s: %s %s" % (move_id, s, (g or {}).get("detail") or g))
    return s
