# -*- coding: utf-8 -*-
"""Thử PHÂN QUYỀN các màn mới 30/09: Xem kho · Phiếu đề nghị chi · Phiếu đề nghị thu · Đề nghị theo DO · trang tài xế.

    python kiem/thu_quyen_de_nghi_kho.py [http://127.0.0.1:8011]

Máy chủ phải chặn đúng như menu — vai không có màn thì API cũng không trả; vai không thấy tiền thì không nhận số tiền.
Chỉ đọc (và gọi hai đường ghi bằng mã giả / phiếu chưa khoá để thấy bị chặn), không đổi dữ liệu.
"""
import json
import sys
import time
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
    ma("/api/chung-tu?trip_id=%s" % khoa["id"], {**ALL, "thabok": 403, "tx01": 403, "totsua": 403, "khopt": 403, "khotb": 403})
    ma("/api/chung-tu/khong-co-to-nay/day", {**{u: 403 for u in VAI}, "ketoan": 404, "admin": 404}, body={})

    print("Giá vốn kho (30/09: thủ kho, thủ kho phụ tùng, tổ sửa chữa không thấy)")
    for u in ("khotb", "khopt", "totsua", "thabok"):
        s, g = goi("/api/kho-xem", u=u); dung(not co_tien(g, "gia_bq", "gia"), "%s: Xem kho không có giá vốn" % u)
        s, g = goi("/api/parts", u=u); dung(s != 200 or all("unit_price" not in x for x in g), "%s: danh mục phụ tùng không có giá" % u)
    s, g = goi("/api/kho-xem", u="quytb"); dung(co_tien(g, "gia_bq"), "Quỹ: Xem kho có giá vốn")
    # quét QR tờ đề nghị xuất kho nhiên liệu: thủ kho không nhận giá vốn dòng dầu kho (kiểm kê API kho 30/09)
    s, ds = goi("/api/vouchers?trang_thai=&loai=fuel&co=20", u="ketoan")
    to = next((v for v in (ds if s == 200 else []) if v.get("token")), None)
    if to:
        s, g = goi("/api/vouchers/tra-cuu/%s" % to["token"], u="khotb")
        s2, g2 = goi("/api/vouchers/tra-cuu/%s" % to["token"], u="ketoan")
        dung(s != 200 or all("unit_price" not in d and "tien_lak" not in d for d in g.get("dong", [])),
             "Thủ kho quét QR: dòng dầu kho không có giá vốn")
        dung(s2 == 200 and (not g2.get("dong") or any("unit_price" in d for d in g2["dong"])), "Kế toán quét QR: thấy giá dòng")
    s, pt = goi("/api/parts", u="ketoan")
    x = next((x for x in pt if (x.get("qty") or 0) > 1 and (x.get("unit_price") or 0) > 0), None)
    if x is None:
        dung(False, "máy thử cần một phụ tùng còn hàng và có giá bình quân")
    else:
        s, xe = goi("/api/vehicles", u="admin"); s, tx = goi("/api/drivers", u="admin"); s, kh = goi("/api/customers", u="admin")
        s, p = goi("/api/trips", {"doc_no": "THU-GK-%s/EPL" % time.strftime("%H%M%S"), "kind": "gom",
                                  "vehicle_id": next(v for v in xe if v["owner_type"] == "EPL")["id"], "driver_id": tx[0]["id"],
                                  "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"),
                                  "expenses": [{"section": "repair", "source": "kho", "part_id": x["id"], "item_name": x["name"], "qty": 1,
                                                "unit_price": 1, "paid_by_epl": True},
                                               {"section": "repair", "source": "mua", "item_name": "Garage thử", "qty": 1,
                                                "unit_price": 250000, "currency": "LAK", "paid_by_epl": True}]}, "admin")
        dung(s == 200, "Lập phiếu thử: một dòng phụ tùng lấy kho (gửi giá 1) và một dòng garage")
        try:
            s, pk = goi("/api/trips/%s" % p["id"], u="ketoan")
            kho = next(e for e in pk["expenses"] if e["section"] == "repair" and e["source"] == "kho")
            dung(abs(kho["unit_price"] - x["unit_price"]) < 0.01, "Dòng lấy kho lấy giá bình quân %s, không theo số gửi lên" % x["unit_price"])
            s, ps = goi("/api/trips/%s" % p["id"], u="totsua")
            kho = next(e for e in ps["expenses"] if e["section"] == "repair" and e["source"] == "kho")
            gara = next(e for e in ps["expenses"] if e["section"] == "repair" and e["source"] == "mua")
            dung("unit_price" not in kho and gara.get("unit_price") == 250000, "Tổ sửa chữa: dòng kho không có giá, dòng garage có")
            dung("chi" not in ps["tinh"] and "tong_chi_lak" not in ps["tinh"], "Tổ sửa chữa: không có tổng chi (có giá kho bên trong)")
            s, g = goi("/api/vehicles/%s" % pk["vehicle_id"], u="totsua")
            dung(all(y.get("tien_lak") is None for y in g["sua_chua"] if y.get("source") == "kho"), "Màn Xe · tổ sửa chữa: dòng kho không có tiền")
            s, g = goi("/api/vehicles/%s" % pk["vehicle_id"], u="thabok")
            dung(all(y.get("tien_lak") is None for y in g["sua_chua"]), "Màn Xe · Bãi: không có tiền sửa chữa")
            s, g = goi("/api/vehicles/%s" % pk["vehicle_id"], u="ketoan")
            dung(any(y.get("tien_lak") for y in g["sua_chua"]), "Màn Xe · kế toán: có tiền sửa chữa")
        finally:
            s, _ = goi("/api/trips/%s" % p["id"], u="admin", method="DELETE")
            print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại (%s)" % s))

    if LOI:
        print("\nSAI:"); [print("  -", x) for x in LOI]
        raise SystemExit(1)
    print("\nTHỬ QUYỀN 30/09: ĐẠT — Xem kho · Đề nghị theo DO · Phiếu đề nghị thu · Phiếu đề nghị chi · tài xế chỉ tờ của mình · giá vốn kho ẩn với thủ kho, tổ sửa chữa")


if __name__ == "__main__":
    main()
