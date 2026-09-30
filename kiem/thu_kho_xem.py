# -*- coding: utf-8 -*-
"""Thử màn XEM KHO (sếp 30/09: kho dời về trang logistics, chỉ xem, quản lý theo mặt hàng).

    python kiem/thu_kho_xem.py [http://127.0.0.1:8011]

Phải thấy:
  · mỗi kho dầu EPL một dòng, mỗi phụ tùng một dòng, mỗi loại hàng khách gửi một dòng — số tồn hỏi bên kho;
  · phiếu đề nghị xuất kho nhiên liệu CHỜ CẤP của một phiếu thử hiện đúng ở kho của nó (số lít, số phiếu DO); huỷ đề nghị
    thì chuyển sang "đã khai, chưa có đề nghị"; còn lại = tồn − chờ cấp − đã khai;
  · Bãi xem được nhưng không nhận giá (giá bình quân, giá từng lần); tài xế bị chặn.
Bài tự lập một phiếu thử và tự xoá.
"""
import json
import sys
import time
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[vai]} if vai else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def dung(dk, buoc, chi_tiet=""):
    print("  %s %-80s %s" % ("✓" if dk else "SAI", buoc, chi_tiet))
    if not dk:
        raise SystemExit("DỪNG: " + buoc)


def kho(vai, ma):
    s, g = goi("/api/kho-xem", vai=vai)
    dung(s == 200, "GET /api/kho-xem (%s)" % vai, s)
    return g, next((k for k in g["nhien_lieu"] if k["place_id"] == ma), None)


def main():
    for u in ("thabok", "ketoan", "admin", "tx01"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
    s, g = goi("/api/kho-xem", vai="tx01"); dung(s == 403, "Tài xế không vào màn kho", s)

    s, diem = goi("/api/fuel-places", vai="ketoan")
    tb = next(d for d in diem if d.get("code") == "KHO-TB")
    g, k0 = kho("ketoan", tb["id"])
    dung(len(g["nhien_lieu"]) >= 1 and k0 is not None, "Mỗi kho dầu EPL một dòng — có kho Thà Bốc", "%d kho" % len(g["nhien_lieu"]))
    dung(k0["ton_lit"] is not None and "gia_bq" in k0 and isinstance(k0["gan_day"], list), "Kho Thà Bốc có tồn, giá bình quân, lần gần đây",
         "%s L" % k0["ton_lit"])
    dung(all("ton" in p and "min_qty" in p and "tren_phieu" in p for p in g["phu_tung"]), "Mỗi phụ tùng một dòng: tồn, tối thiểu, trên phiếu",
         "%d phụ tùng" % len(g["phu_tung"]))
    dung(all("ton_t" in h and "lo" in h for h in g["hang"]), "Mỗi loại hàng khách gửi một dòng, kèm lô", "%d loại" % len(g["hang"]))

    # ---- phiếu thử: 123 L dầu kho Thà Bốc, lập phiếu đề nghị
    s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] == "EPL")
    so_phieu = "THU-KX-%s/EPL" % time.strftime("%H%M%S")
    s, p = goi("/api/trips", {"doc_no": so_phieu, "kind": "gom", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
                              "doc_date": time.strftime("%Y-%m-%d"),
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 123, "place_id": tb["id"], "paid_by_epl": True}]}, "thabok")
    dung(s == 200, "Bãi lập phiếu thử 123 L dầu kho Thà Bốc", s)
    pid = p["id"]
    try:
        g, k1 = kho("ketoan", tb["id"])
        x = next((v for v in k1["chua_de_nghi"] if v["trip_id"] == pid), None)
        dung(x is not None and x["qty_l"] == 123, "Chưa lập đề nghị → nằm ở 'đã khai, chưa có đề nghị' 123 L")
        s, vs = goi("/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, "thabok")
        dung(s == 200, "Bãi lập phiếu đề nghị xuất kho nhiên liệu", s)
        g, k2 = kho("ketoan", tb["id"])
        v = next((v for v in k2["de_nghi"] if v["trip_id"] == pid), None)
        dung(v is not None and v["qty_l"] == 123 and v["doc_no"] == so_phieu and v["voucher_no"].startswith("PLNL-"),
             "Đề nghị chờ cấp hiện ở kho Thà Bốc: 123 L, đúng số phiếu DO", v and v["voucher_no"])
        dung(not any(x["trip_id"] == pid for x in k2["chua_de_nghi"]), "Có đề nghị rồi thì không còn ở 'chưa có đề nghị'")
        dung(abs(k2["cho_xuat"] - k1["cho_xuat"] - 123) < 0.01, "Tổng chờ cấp của kho tăng đúng 123 L", "%s → %s" % (k1["cho_xuat"], k2["cho_xuat"]))
        dung(abs(k2["con_dung"] - (k2["ton_lit"] - k2["cho_xuat"] - k2["chua_de_nghi_l"])) < 0.01, "Còn lại = tồn − chờ cấp − đã khai")

        g, kb = kho("thabok", tb["id"])
        dung(g["thay_gia"] is False and "gia_bq" not in kb and all("gia" not in m for m in kb["gan_day"])
             and all("gia_bq" not in p for p in g["phu_tung"]), "Bãi xem kho nhưng không nhận giá")
        dung(any(v["trip_id"] == pid for v in kb["de_nghi"]), "Bãi thấy đề nghị chờ cấp của phiếu mình")
    finally:
        s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại (%s)" % s))
    g, k3 = kho("ketoan", tb["id"])
    dung(not any(v["trip_id"] == pid for v in k3["de_nghi"] + k3["chua_de_nghi"]), "Xoá phiếu thử → không còn trong phần chờ")
    print("\nTHỬ XEM KHO: ĐẠT — theo mặt hàng · đề nghị chờ cấp đúng kho · còn lại = tồn − chờ · Bãi không thấy giá · tài xế bị chặn")


if __name__ == "__main__":
    main()
