# -*- coding: utf-8 -*-
"""Thử PHIẾU ĐỀ NGHỊ theo DO (sếp 30/09): đề nghị chi theo bước, đề nghị thu khi DO xong.

    python kiem/thu_de_nghi.py [http://127.0.0.1:8011]

Phải thấy:
  · màn Đề nghị theo DO: DO mới có mục III, IV đang chờ; lập phiếu đề nghị xuất nhiên liệu → hiện ngay ở DO đó;
  · màn Phiếu đề nghị chi tìm được tờ theo số DO;
  · khoá phiếu (xe về, có POD) → máy lập PHIẾU ĐỀ NGHỊ THU (PDT) đúng cước, đúng tiền tệ của phiếu (USD), vào hồ sơ gửi kế toán;
  · mở khoá → rút tờ chưa gửi; khoá lại → tờ mới; tờ đã gửi bên công nợ thì kế toán không mở khoá được (Sếp mở được);
  · Bãi xem DO nhưng không nhận tiền cước / không vào đề nghị thu; tài xế bị chặn.
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


def ma(g):
    return g.get("detail", {}).get("ma", "") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""


def phai(s, mong, buoc, g=None):
    print("  %s %-80s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma(g)))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, json.dumps(g, ensure_ascii=False)[:300]))


def dung(dk, buoc, chi_tiet=""):
    print("  %s %-80s %s" % ("✓" if dk else "SAI", buoc, chi_tiet))
    if not dk:
        raise SystemExit("DỪNG: " + buoc)


def dong_do(vai, so):
    s, g = goi("/api/de-nghi-theo-do?q=" + urllib.request.quote(so), vai=vai)
    phai(s, 200, "GET /api/de-nghi-theo-do (%s)" % vai, g)
    return g, next((x for x in g["ds"] if x["doc_no"] == so), None)


def dong_thu(so):
    s, g = goi("/api/de-nghi-thu?q=" + urllib.request.quote(so), vai="ketoan")
    phai(s, 200, "GET /api/de-nghi-thu", g)
    return next((x for x in g["ds"] if x["doc_no"] == so), None)


def main():
    for u in ("thabok", "ketoan", "admin", "tx01"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
    s, g = goi("/api/de-nghi-theo-do", vai="tx01"); phai(s, 403, "Tài xế không vào màn Đề nghị theo DO", g)
    s, g = goi("/api/de-nghi-thu", vai="thabok"); phai(s, 403, "Bãi không vào Phiếu đề nghị thu (tiền cước)", g)

    s, diem = goi("/api/fuel-places", vai="ketoan"); tb = next(d for d in diem if d.get("code") == "KHO-TB")
    s, xe = goi("/api/vehicles", vai="admin"); s, tx = goi("/api/drivers", vai="admin"); s, kh = goi("/api/customers", vai="admin")
    nha = next(x for x in xe if x["owner_type"] == "EPL")
    so = "THU-DN-%s/EPL" % time.strftime("%H%M%S")
    s, p = goi("/api/trips", {"doc_no": so, "kind": "giao", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
                              "doc_date": time.strftime("%Y-%m-%d"), "price": 12, "price_ccy": "USD", "weight_origin": 40,
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "place_id": tb["id"], "paid_by_epl": True},
                                           {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "paid_by_epl": True}]}, "admin")
    phai(s, 200, "Lập phiếu thử: giao, 40 t × 12 USD, 100 L dầu kho, tiền nước", p)
    pid = p["id"]
    try:
        g, x = dong_do("ketoan", so)
        dung(x is not None and x["thu"]["trang_thai"] == "cho_khoa", "DO mới: đề nghị thu 'chờ khoá phiếu'")
        dung(set(x["muc"]) == {"fuel", "travel"} and x["muc"]["travel"]["tien_lak"] == 60000, "Mục III, IV có dòng — kế toán thấy tiền mục IV",
             x["muc"])
        dung(not x["nhien_lieu"] and x["ho_so"]["tong"] >= 1, "Chưa có đề nghị nhiên liệu; hồ sơ có tờ DO", x["ho_so"])

        s, vs = goi("/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, "thabok"); phai(s, 200, "Bãi lập phiếu đề nghị xuất nhiên liệu", vs)
        g, x = dong_do("ketoan", so)
        dung(len(x["nhien_lieu"]) == 1 and x["nhien_lieu"][0]["status"] == "cho" and x["nhien_lieu"][0]["qty_l"] == 100,
             "Đề nghị nhiên liệu hiện ngay ở DO: 100 L, chờ cấp")
        s, ds = goi("/api/vouchers?trang_thai=&q=" + urllib.request.quote(so), vai="thabok")
        dung(s == 200 and any(v["trip_doc_no"] == so and v["kind"] == "fuel" for v in ds), "Phiếu đề nghị chi: tìm được tờ theo số DO")
        g, xb = dong_do("thabok", so)
        dung("doanh_thu" not in xb["thu"] and all("tien_lak" not in m for m in xb["muc"].values()), "Bãi xem DO nhưng không nhận tiền")

        # ---- DO xong: xe về, có POD, kế toán khoá → đề nghị thu
        s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": 39.5, "back_date": time.strftime("%Y-%m-%d"),
                                                            "pod_no": "POD-" + so, "pod_receiver": "ນາງ ທົດລອງ"}, "admin")
        phai(s, 200, "Xe về: cân cuối 39,5 t, có số POD", g)
        x = dong_thu(so)
        dung(x is not None and x["trang_thai"] == "cho_khoa" and x["pdt"] is None, "Xe về mà chưa khoá: chưa có đề nghị thu")
        s, g = goi("/api/trips/%s/de-nghi-thu" % pid, {}, "ketoan"); phai(s, 409, "Chưa khoá thì không lập đề nghị thu", g)
        s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, "ketoan"); phai(s, 200, "Kế toán khoá phiếu", g)
        x = dong_thu(so)
        dung(x["trang_thai"] == "cho_gui" and x["pdt"] and x["pdt"]["so"].startswith("PDT/"), "Khoá → máy lập phiếu đề nghị thu, chờ gửi",
             x["pdt"] and x["pdt"]["so"])
        dung(x["ccy"] == "USD" and abs(x["doanh_thu"] - 474) < 0.01 and x["pdt"]["tien_te"] == "USD" and abs(x["pdt"]["tien"] - 474) < 0.01,
             "Đề nghị thu đúng cước 39,5 t × 12 = 474 USD, đúng tiền tệ phiếu", "%s %s" % (x["doanh_thu"], x["ccy"]))
        s, t = goi("/api/trips/%s/de-nghi-thu" % pid, vai="ketoan")
        dung(s == 200 and t["pod_no"] == "POD-" + so and t["customer_name"] == p["customer_name"] and t["tan_tinh"] == 39.5,
             "Tờ in: khách, số POD, tấn tính cước")
        s, r = goi("/api/chung-tu?trip_id=" + pid, vai="ketoan")
        dung(any(c["loai"] == "PDT" and c["loai_ten"] == "Phiếu đề nghị thu" for c in r["ds"]), "Tờ PDT nằm trong hồ sơ gửi kế toán")
        id1 = x["pdt"]["id"]

        # ---- mở khoá → rút tờ chưa gửi; khoá lại → tờ mới
        s, g = goi("/api/trips/%s/mo-khoa" % pid, {}, "ketoan"); phai(s, 200, "Kế toán mở khoá (tờ chưa gửi)", g)
        x = dong_thu(so); dung(x["pdt"] is None and x["trang_thai"] == "cho_khoa", "Mở khoá → tờ đề nghị thu chưa gửi được rút")
        s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, "ketoan"); phai(s, 200, "Khoá lại", g)
        x = dong_thu(so)
        # tờ cũ chưa gửi đã rút nên số có thể dùng lại (số = lớn nhất còn lại + 1) — tờ mới là bản ghi mới
        dung(x["pdt"] and x["pdt"]["id"] != id1, "Khoá lại → tờ đề nghị thu mới (bản ghi mới)", x["pdt"]["so"])
        s, g = goi("/api/chung-tu/%s/da-day" % x["pdt"]["id"], {"da_day": True}, "ketoan"); phai(s, 200, "Đánh dấu tờ đã gửi bên công nợ", g)
        x = dong_thu(so); dung(x["trang_thai"] == "da_gui", "Trạng thái: đã gửi")
        s, g = goi("/api/trips/%s/mo-khoa" % pid, {}, "ketoan"); phai(s, 409, "Tờ đã gửi bên công nợ → kế toán không mở khoá được", g)
        dung(ma(g) == "DA_GUI_DE_NGHI_THU", "Mã lỗi DA_GUI_DE_NGHI_THU", ma(g))
        s, g = goi("/api/chung-tu/%s/da-day" % x["pdt"]["id"], {"da_day": False}, "ketoan"); phai(s, 200, "Trả tờ về chưa gửi (dọn bài thử)", g)
    finally:
        goi("/api/trips/%s/mo-khoa" % pid, {}, "admin")
        s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại (%s)" % s))
    s, r = goi("/api/chung-tu?trip_id=" + pid, vai="ketoan")
    dung(not r["ds"], "Xoá phiếu thử → không còn tờ nào của nó")
    print("\nTHỬ ĐỀ NGHỊ: ĐẠT — theo DO · đề nghị chi theo bước · khoá sinh đề nghị thu đúng tiền tệ · mở khoá rút tờ · tờ đã gửi chặn mở khoá")


if __name__ == "__main__":
    main()
