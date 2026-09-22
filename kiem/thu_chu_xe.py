# -*- coding: utf-8 -*-
"""Thử CHỦ XE LIÊN KẾT — danh mục, phí riêng từng chủ, trả gộp nhiều phiếu (anh Khampla C4.2 · C4.3).

    python kiem/thu_chu_xe.py [http://127.0.0.1:8010]

Kịch bản: kế toán lập chủ xe mới với phí 3 %, ngưỡng 38 t, trả gộp tháng → Bãi thêm xe liên kết gắn
chủ đó → Bãi lập hai phiếu gom bằng xe đó (phí trên phiếu tự điền 3 % / 38 t) → đi tới khoá → quỹ
trả GỘP hai phiếu một lần → một tờ PC_CX, hai phiếu đánh đã trả → trả lại thì bị chặn → dọn.
"""
import json
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau,
                               method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def phai(s, mong, buoc, g=None):
    dt_ = (g or {}).get("detail") if isinstance(g, dict) else None
    ma = dt_.get("ma", "") if isinstance(dt_, dict) else ""
    print("%s %-60s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 8 vai")

    # ---------------------------------------------------------------- 0. dọn dấu vết lần chạy trước bị đứt
    s, ds = goi("/api/trips", vai="admin")
    for p in [x for x in ds if x["doc_no"] in ("THU-CX-A/EPL", "THU-CX-B/EPL")]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin"); goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
    s, ds = goi("/api/vehicles", vai="admin")
    for x in [x for x in ds if x["truck_no"] in ("THU-CX-01", "THU-CX-02") and x["active"]]:
        goi("/api/vehicles/%s" % x["id"], {"active": False}, vai="admin", method="PUT")
    s, ds = goi("/api/owners", vai="admin")
    for x in [x for x in ds if "Chủ thử" in (x["name"] or "") and x["active"]]:
        goi("/api/owners/%s" % x["id"], {"name": x["name"], "active": False}, vai="admin", method="PUT")

    # ---------------------------------------------------------------- 1. danh mục chủ xe
    s, g = goi("/api/owners", {"name": "Chủ thử", "fee_pct": 3}, vai="thabok")
    phai(s, 403, "Bãi thêm chủ xe → bị từ chối (điều khoản hợp đồng là của kế toán)", g)
    s, chu = goi("/api/owners", {"name": "ທ້າວ ທົດສອບ (Chủ thử)", "phone": "020 1111 2222", "fee_pct": 3, "over_limit_t": 38,
                                 "over_price": 1.5, "hire_ccy": "USD", "pay_mode": "thang", "note": "thử bộ kiểm"}, vai="ketoan")
    phai(s, 200, "Kế toán lập chủ xe: phí 3 % · ngưỡng 38 t · trả gộp tháng", chu)
    s, g = goi("/api/owners", {"name": "x", "pay_mode": "tuy_y"}, vai="ketoan"); phai(s, 422, "Cách trả lạ → bị từ chối", g)
    s, g = goi("/api/owners", {"name": "x", "fee_pct": 150}, vai="ketoan"); phai(s, 422, "Phí 150 % → bị từ chối", g)
    s, ds = goi("/api/owners", vai="thabok")
    c0 = next(c for c in ds if c["id"] == chu["id"])
    assert "fee_pct" not in c0 and "cho_tra" not in c0, "Bãi không được thấy phí và số chờ trả của chủ xe: %s" % list(c0)
    print("  ✓ %-60s" % "Bãi xem danh mục chủ xe: có tên, không có phí và tiền")

    # ---------------------------------------------------------------- 2. xe liên kết gắn chủ xe
    s, xe = goi("/api/vehicles", {"truck_no": "THU-CX-01", "plate_head": "ກຂ 0001", "owner_type": "joint", "owner_id": chu["id"]}, vai="thabok")
    phai(s, 200, "Bãi thêm xe liên kết, chọn chủ xe từ danh mục", xe)
    assert xe["owner_name"] == chu["name"], "tên chủ xe phải chép từ danh mục: %s" % xe["owner_name"]
    s, g = goi("/api/vehicles", {"truck_no": "THU-CX-02", "owner_type": "joint", "owner_id": "khong-co"}, vai="thabok")
    phai(s, 422, "Chủ xe không có trong danh mục → bị từ chối", g)

    # ---------------------------------------------------------------- 3. hai phiếu gom bằng xe đó → phí tự điền theo chủ
    s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok"); s, tuyen = goi("/api/routes", vai="thabok")
    phieu = []
    for i, (so, tan) in enumerate((("THU-CX-A/EPL", 41.0), ("THU-CX-B/EPL", 39.0))):
        s, P = goi("/api/trips", {"doc_no": so, "kind": "gom", "doc_date": "2026-09-1%d" % (i + 5), "out_date": "2026-09-1%d" % (i + 5),
                                  "vehicle_id": xe["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"],
                                  "odo_out": 100, "goods": [{"goods_name": "ແຮ່ເຫຼັກ", "qty_t": tan}],
                                  "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 50, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"}]}, vai="thabok")
        phai(s, 200, "Bãi lập phiếu gom %s bằng xe của chủ thử" % so, P)
        assert P["company"] == "joint" and P["owner_id"] == chu["id"], "phiếu phải nhận chủ xe từ xe: %s" % P.get("owner_id")
        assert P["fee_pct"] == 3 and P["over_limit_t"] == 38 and P["over_price"] == 1.5, \
            "phí/ngưỡng/mức trừ phải tự điền theo CHỦ XE (3 · 38 · 1.5): %s %s %s" % (P["fee_pct"], P["over_limit_t"], P["over_price"])
        phieu.append(P)
    print("  ✓ %-60s" % "phiếu tự điền phí 3 % · ngưỡng 38 t · trừ 1,5 USD/t theo hồ sơ chủ xe")

    # kế toán đặt giá bán và giá thuê, đi tới khoá
    for P in phieu:
        s, g = goi("/api/trips/%s" % P["id"], {"price": 41, "price_ccy": "USD", "hire_price": 40, "hire_ccy": "USD"}, vai="ketoan", method="PUT")
        phai(s, 200, "Kế toán đặt giá bán 41, giá thuê 40 USD/t cho %s" % P["doc_no"], g)
        for muc in ("info", "trans", "fuel"):
            s, g = goi("/api/trips/%s/sections/%s/send" % (P["id"], muc), {}, vai="thabok"); phai(s, 200, "gửi kiểm %s" % muc, g)
        for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl")):
            s, g = goi("/api/trips/%s/sections/%s/verify" % (P["id"], muc), {}, vai=v); phai(s, 200, "kiểm %s" % muc, g)
        s, g = goi("/api/trips/%s/sections/fuel/book" % P["id"], {}, vai="khonl"); phai(s, 200, "ghi sổ III", g)
        s, g = goi("/api/trips/%s/sections/fuel/pay" % P["id"], {}, vai="quyvc"); phai(s, 200, "chi III", g)
        s, g = goi("/api/trips/%s/transport-status" % P["id"], {"status": "arrived", "weight_dest": P["weight_origin"], "odo_back": 300, "back_date": "2026-09-18"}, vai="thabok")
        phai(s, 200, "xe về, cân bãi", g)
        s, g = goi("/api/trips/%s/khoa" % P["id"], {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "khoá %s" % P["doc_no"], g)
        # phí 3 % trên tiền thuê, vượt 38 t trừ 1,5 USD/t — đúng điều khoản chủ xe
        k = g["tinh"]; thue = round(P["weight_origin"] * 40, 2)
        assert abs(k["phi"] - round(thue * 0.03, 2)) < 0.01, "phí phải là 3 %% của %s: %s" % (thue, k["phi"])
        assert abs(k["tru_vuot"] - round(max(0, P["weight_origin"] - 38) * 1.5, 2)) < 0.01, "quá tải phải theo ngưỡng 38 t × 1,5: %s" % k["tru_vuot"]
    print("  ✓ %-60s" % "hai phiếu đã khoá; phí và quá tải tính theo điều khoản chủ xe")

    # ---------------------------------------------------------------- 4. công nợ và trả gộp
    s, g = goi("/api/owners/%s/cong-no" % chu["id"], vai="thabok"); phai(s, 403, "Bãi xem công nợ chủ xe → bị từ chối", g)
    s, cn = goi("/api/owners/%s/cong-no" % chu["id"], vai="quytb"); phai(s, 200, "Quỹ xem công nợ chủ xe", cn)
    assert cn["tong"]["so_phieu"] == 2, "phải có 2 phiếu chờ trả: %s" % cn["tong"]
    tong_usd = round(sum(p["tra_chu_xe"] for p in cn["cho_tra"]), 2)
    print("  ✓ %-60s %s USD" % ("2 phiếu chờ trả, tổng", tong_usd))

    ids = [p["id"] for p in cn["cho_tra"]]
    s, g = goi("/api/owners/%s/tra" % chu["id"], {"trip_ids": ids}, vai="ketoan"); phai(s, 403, "Kế toán trả tiền → bị từ chối (quỹ chi)", g)
    s, g = goi("/api/owners/%s/tra" % chu["id"], {"trip_ids": []}, vai="quytb"); phai(s, 422, "Trả mà không chọn phiếu → bị từ chối", g)
    s, g = goi("/api/owners/%s/tra" % chu["id"], {"trip_ids": ids, "pay_date": "2026-09-30", "method": "bank", "ref": "UNC-CX-01"}, vai="quytb")
    phai(s, 200, "Quỹ trả GỘP hai phiếu một lần (chuyển khoản)", g)
    assert g["tong"]["so_phieu"] == 0 and len(g["da_tra"]) == 1, "sau trả gộp: 0 phiếu chờ, 1 đợt đã trả: %s" % g["tong"]
    dot = g["da_tra"][0]
    assert abs(dot["amount"] - tong_usd) < 0.01 and dot["currency"] == "USD" and sorted(dot["phieu"]) == sorted(p["doc_no"] for p in phieu), \
        "đợt trả phải đúng tổng và đủ hai phiếu: %s" % dot
    print("  ✓ %-60s %s %s · %d phiếu" % ("đợt trả ghi đúng", dot["amount"], dot["currency"], len(dot["phieu"])))

    s, ct = goi("/api/chung-tu?loai=PC_CX&limit=20", vai="ketoan")
    to = [c for c in ct["ds"] if c["nguon_bang"] == "owner_payments" and c["nguon_id"] == dot["id"]]
    assert len(to) == 1 and to[0]["co"] == "1022", "một đợt → MỘT tờ PC_CX, vế Có ngân hàng ngoại tệ 1022: %s" % to
    print("  ✓ %-60s %s · Nợ %s / Có %s" % ("một tờ PC_CX cho cả đợt", to[0]["so"], to[0]["no"], to[0]["co"]))

    for P in phieu:
        s, g = goi("/api/trips/%s" % P["id"], vai="quytb")
        assert g["owner_paid"] and g["owner_payment_id"] == dot["id"], "phiếu %s phải đánh đã trả và trỏ về đợt" % P["doc_no"]
    s, g = goi("/api/trips/%s/tra-chu-xe" % phieu[0]["id"], {}, vai="quytb"); phai(s, 409, "Trả lại từng phiếu đã nằm trong đợt → từ chối", g)
    s, g = goi("/api/owners/%s/tra" % chu["id"], {"trip_ids": ids}, vai="quytb"); phai(s, 409, "Trả gộp lần hai cùng phiếu → từ chối", g)

    # ---------------------------------------------------------------- 5. dọn
    for P in phieu:
        s, g = goi("/api/trips/%s/mo-khoa" % P["id"], {}, vai="admin")
        s, g = goi("/api/trips/%s" % P["id"], vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử %s" % P["doc_no"], g)
    s, g = goi("/api/vehicles/%s" % xe["id"], {"active": False}, vai="thabok", method="PUT"); phai(s, 200, "Ngưng dùng xe thử", g)
    s, g = goi("/api/owners/%s" % chu["id"], {"name": chu["name"], "active": False}, vai="ketoan", method="PUT"); phai(s, 200, "Ngưng chủ xe thử", g)

    print("\nTHỬ CHỦ XE: ĐẠT — danh mục · phí riêng từng chủ tự điền vào phiếu · trả gộp nhiều phiếu một tờ PC_CX · chặn trả trùng · phân quyền")


if __name__ == "__main__":
    main()
