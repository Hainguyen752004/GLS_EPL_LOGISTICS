# -*- coding: utf-8 -*-
"""Thử PHÂN QUYỀN các màn mới 30/09: Xem kho · Phiếu đề nghị chi · Phiếu đề nghị thu · Đề nghị theo DO · trang tài xế.

    python kiem/thu_quyen_de_nghi_kho.py [http://127.0.0.1:8011]

Máy chủ phải chặn đúng như menu — vai không có màn thì API cũng không trả; vai không thấy tiền thì không nhận số tiền.
Chỉ đọc (và gọi hai đường ghi bằng mã giả / phiếu chưa khoá để thấy bị chặn), không đổi dữ liệu.
"""
import json
import sys
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK, U = {}, {}
VAI = ["thabok", "ketoan", "ketoancp", "khonl", "khotb", "quytb", "quyvc", "doanhthu", "totsua", "khopt", "tx01", "admin"]
LOI = []


def goi(duong, body=None, u=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[u]} if u else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def dung(dk, buoc):
    print("  %s %s" % ("✓" if dk else "SAI", buoc))
    if not dk:
        LOI.append(buoc)


def ma(duong, mong, **kw):
    """mong: {vai: mã HTTP}; vai không kể tên thì không kiểm."""
    for u, m in mong.items():
        s, _ = goi(duong, u=u, **kw)
        if s != m:
            LOI.append("%s %s: %s (mong %s)" % (u, duong, s, m))
    sai = [x for x in LOI if duong in x]
    print("  %s %-44s %s" % ("✓" if not sai else "SAI", duong, " · ".join("%s %s" % (u, m) for u, m in mong.items())))


def co_tien(g, *khoa):
    t = json.dumps(g, ensure_ascii=False)
    return any('"%s":' % k in t and '"%s": null' % k not in t for k in khoa)


def main():
    for u in VAI:
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]; U[u] = g.get("user") or {}
    s, ds = goi("/api/trips?co=80", u="admin")
    khoa = next(p for p in ds if p.get("locked"))
    mo = next(p for p in ds if not p.get("locked"))
    s, cua_tx = goi("/api/trips?co=20", u="tx01")
    cua_minh = cua_tx[0]
    khac = next(p for p in ds if p["id"] not in {x["id"] for x in cua_tx})
    ALL = {u: 200 for u in VAI}

    print("Xem kho")
    ma("/api/kho-xem", {**ALL, "tx01": 403})
    s, g = goi("/api/kho-xem", u="thabok"); dung(not co_tien(g, "gia_bq", "gia"), "Bãi: Xem kho không có giá")
    s, g = goi("/api/kho-xem", u="ketoan"); dung(co_tien(g, "gia_bq"), "Kế toán: Xem kho có giá bình quân")
    s, g = goi("/api/kho-xem", u="khotb")
    s, diem = goi("/api/fuel-places", u="admin")
    tb = next(d for d in diem if d.get("code") == "KHO-TB")
    dung(len(g["nhien_lieu"]) == 1 and g["nhien_lieu"][0]["place_id"] == tb["id"], "Thủ kho Thà Bốc: tab Nhiên liệu chỉ kho của mình")

    print("Đề nghị theo DO")
    ma("/api/de-nghi-theo-do", {**ALL, "tx01": 403, "khotb": 403, "khopt": 403, "totsua": 403})
    s, g = goi("/api/de-nghi-theo-do", u="thabok")
    dung(not co_tien(g, "doanh_thu", "tien_lak", "amount_lak", "doanh_thu_lak"), "Bãi: Đề nghị theo DO không có số tiền nào")
    s, g = goi("/api/de-nghi-theo-do", u="ketoan"); dung(co_tien(g, "tien_lak"), "Kế toán: có tiền chi các mục")

    print("Phiếu đề nghị thu (tiền cước)")
    BAN = {**ALL, "thabok": 403, "khotb": 403, "khopt": 403, "totsua": 403, "tx01": 403}
    ma("/api/de-nghi-thu", BAN)
    ma("/api/trips/%s/de-nghi-thu" % khoa["id"], BAN)
    ma("/api/trips/%s/de-nghi-thu" % mo["id"], {**{u: 403 for u in VAI}, "ketoan": 409, "admin": 409}, body={})

    print("Phiếu đề nghị chi")
    ma("/api/vouchers?trang_thai=&co=5", {**ALL, "totsua": 403, "khopt": 403})
    s, g = goi("/api/vouchers?trang_thai=&co=200", u="tx01")
    # mỗi tờ tài xế nhận được phải thuộc phiếu tài xế đó mở được (phiếu của mình)
    dung(all(goi("/api/trips/%s" % v["trip_id"], u="tx01")[0] == 200 for v in g[:10]), "Tài xế: danh sách tờ đề nghị chỉ của mình (%d tờ)" % len(g))
    s, g = goi("/api/vouchers?trang_thai=&co=200", u="khotb")
    dung(all(v["kind"] == "fuel" and v["place_id"] == tb["id"] for v in g), "Thủ kho: chỉ tờ nhiên liệu của kho mình")
    s, g = goi("/api/vouchers?trang_thai=&co=50", u="thabok")
    dung(all(v.get("amount_lak") is None for v in g), "Bãi: tờ tạm ứng không có số tiền")
    ma("/api/trips/%s/vouchers" % khac["id"], {"tx01": 403, "thabok": 200, "ketoan": 200})
    ma("/api/trips/%s/vouchers" % cua_minh["id"], {"tx01": 200})

    print("Hồ sơ gửi kế toán")
    ma("/api/chung-tu?trip_id=%s" % khoa["id"], {**ALL, "thabok": 403, "tx01": 403, "totsua": 403, "khopt": 403})
    ma("/api/chung-tu/khong-co-to-nay/day", {**{u: 403 for u in VAI}, "ketoan": 404, "admin": 404}, body={})

    if LOI:
        print("\nSAI:"); [print("  -", x) for x in LOI]
        raise SystemExit(1)
    print("\nTHỬ QUYỀN 30/09: ĐẠT — Xem kho · Đề nghị theo DO · Phiếu đề nghị thu · Phiếu đề nghị chi · tài xế chỉ tờ của mình")


if __name__ == "__main__":
    main()
