# -*- coding: utf-8 -*-
"""Thử CÁCH TRẢ từng dòng mục IV (chốt 29/09: làm theo Excel anh Khampla).

    python kiem/thu_cach_tra.py [http://127.0.0.1:8011]

Dựng đúng mục IV của tờ ໃບເບີກລົດອອກໄປຂົນສົ່ງ mẫu: tiền nước 60.000 · sang VN 430.000 · chipping Lào 620.000 · chipping
Việt 1.500.000 · tiền chuyến 1.800.000 · điện thoại 150.000, cột ghi chú nói cách trả. Phải thấy:
  · cách trả mặc định theo khoản mục như Excel (cùng lương · tiền mặt khi xe đi · nợ nhà cung cấp);
  · phiếu tạm ứng CHỈ gồm dòng "chi ngay khi xe đi" = 430.000 + 150.000 = 580.000;
  · người lập đổi cách trả một dòng thì tạm ứng đổi theo; cách trả bậy bị từ chối;
  · màn Tiền chuyến & tiền nước chỉ cộng dòng "trả cùng lương".
Bài tự lập phiếu thử và tự xoá.
"""
import json
import sys
import time
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
DONG = [("x_water", 60000), ("x_vn", 430000), ("x_chip_lao", 620000), ("x_chip_vn", 1500000), ("x_trip", 1800000), ("x_phone", 150000)]
MONG = {"x_water": "luong", "x_vn": "tien_mat", "x_chip_lao": "ncc", "x_chip_vn": "ncc", "x_trip": "luong", "x_phone": "tien_mat"}


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


def phai(s, mong, buoc, g=None):
    ma = g.get("detail", {}).get("ma", "") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""
    print("  %s %-72s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, g))


def tam_ung(pid):
    s, v = goi("/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "ketoancp")
    phai(s, 200, "Lập / lấy lại phiếu tạm ứng", v)
    return round(v[0]["amount_lak"])


def main():
    for u in ("thabok", "ketoancp", "quytb", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
    print("✓ đăng nhập 4 vai")
    s, km = goi("/api/khoan-muc", vai="thabok")
    assert km["pay_channels"] == ["tien_mat", "luong", "ncc"] and km["pay_default"]["x_trip"] == "luong", km.get("pay_default")
    s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    s, p = goi("/api/trips", {"doc_no": "THU-CT-%s/EPL" % time.strftime("%H%M%S"), "kind": "giao", "company": "EPL", "vehicle_id": nha["id"],
                              "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"),
                              "expenses": [{"section": "travel", "item_key": k, "qty": 1, "unit_price": g, "currency": "LAK"} for k, g in DONG]},
               "admin")
    phai(s, 200, "Lập phiếu có đúng mục IV như tờ Excel mẫu (6 khoản, SL 1)", p)
    pid = p["id"]
    try:
        s, p = goi("/api/trips/%s" % pid, vai="ketoancp")
        ca = {e["item_key"]: e["cach_tra"] for e in p["expenses"] if e["section"] == "travel"}
        assert ca == MONG, ca
        print("  ✓ %-72s" % "Cách trả mặc định đúng cột ghi chú Excel: nước, chuyến cùng lương · VN, điện thoại tiền mặt · chipping nợ NCC")
        assert {e["item_key"] for e in p["expenses"] if e["tien_mat_tx"]} == {"x_vn", "x_phone"}
        u = tam_ung(pid)
        assert u == 580000, u
        print("  ✓ %-72s %s" % ("Phiếu tạm ứng chỉ gồm dòng chi ngay khi xe đi: 430.000 + 150.000", u))

        dong = [{"id": e["id"], "section": "travel", "item_key": e["item_key"], "qty": e["qty"],
                 "pay_channel": ("tien_mat" if e["item_key"] == "x_trip" else e["cach_tra"])} for e in p["expenses"] if e["section"] == "travel"]
        s, g = goi("/api/trips/%s" % pid, {"expenses": dong}, "thabok", "PUT")
        phai(s, 200, "Bãi đổi cách trả tiền chuyến thành chi ngay khi xe đi (giữ giá kế toán đã nhập)", g)
        u = tam_ung(pid)
        assert u == 580000 + 1800000, u
        print("  ✓ %-72s %s" % ("Tạm ứng đổi theo: 580.000 + 1.800.000", u))
        # lưu xong máy dựng lại dòng (mã mới) — lấy lại dòng như màn phiếu nạp lại sau mỗi lần lưu
        s, p = goi("/api/trips/%s" % pid, vai="ketoancp")
        dong = [{"id": e["id"], "section": "travel", "item_key": e["item_key"], "qty": e["qty"], "pay_channel": e["cach_tra"]}
                for e in p["expenses"] if e["section"] == "travel"]
        bay = [dict(d, pay_channel="tuy_y") if d["item_key"] == "x_vn" else d for d in dong]
        s, g = goi("/api/trips/%s" % pid, {"expenses": bay}, "thabok", "PUT")
        phai(s, 422, "Cách trả không có trong danh sách → bị từ chối", g)
        ve = [dict(d, pay_channel=MONG[d["item_key"]]) for d in dong]
        s, g = goi("/api/trips/%s" % pid, {"expenses": ve}, "thabok", "PUT")
        phai(s, 200, "Đổi lại đúng như Excel", g)
        assert tam_ung(pid) == 580000

        # Bãi bấm Phiếu chi tạm ứng: tờ QR có sẵn, Bãi không thấy số tiền
        s, v = goi("/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "thabok")
        phai(s, 200, "Bãi bấm Phiếu chi tạm ứng → có tờ tạm ứng mã QR (Bãi không thấy số tiền)", v)
        assert v[0]["token"] and v[0]["amount_lak"] is None, v[0]
        # quỹ chi THẲNG ở mục IV (trang điều xe) → tờ tạm ứng thành đã cấp: Tất toán đếm được, quét QR không chi lần hai
        for hd, vai in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "quytb")):
            s, g = goi("/api/trips/%s/sections/travel/%s" % (pid, hd), {}, vai)
            phai(s, 200, "Mục IV: %s (%s)" % (hd, vai), g)
        s, ds = goi("/api/trips/%s/vouchers" % pid, vai="ketoancp")
        tu = next(x for x in ds if x["kind"] == "advance")
        assert tu["status"] == "da_cap" and round(tu["amount_lak"]) == 580000, tu
        print("  ✓ %-72s" % "Quỹ chi thẳng ở mục IV → tờ tạm ứng thành Đã cấp 580.000 (Tất toán đếm được là đã ứng)")
        s, g = goi("/api/vouchers/%s/cap" % tu["id"], {}, "quytb")
        phai(s, 409, "Quét QR chi lần hai → bị chặn", g)

        s, tt = goi("/api/bao-cao/tien-tai-xe?thang=%s" % time.strftime("%Y-%m"), vai="ketoancp")
        phai(s, 200, "Màn Tiền chuyến & tiền nước", tt)
        r = next((x for x in tt["rows"] if x["driver"] == p["driver_name"]), None)
        assert r and r["khoan"].get("x_trip", 0) >= 1800000 and r["khoan"].get("x_water", 0) >= 60000, r
        assert not r["khoan"].get("x_vn") and not r["khoan"].get("x_phone"), r["khoan"]
        print("  ✓ %-72s" % "Chỉ cộng dòng trả cùng lương (tiền chuyến, tiền nước), không cộng khoản đã đưa tiền mặt")
    finally:
        s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại bản sao DB thử (mục đã kiểm thì không xoá được)"))
    print("\nTHỬ CÁCH TRẢ: ĐẠT — theo cột ghi chú Excel · tạm ứng chỉ khoản chi ngay khi xe đi · màn tiền chuyến chỉ khoản cùng lương")


if __name__ == "__main__":
    main()
