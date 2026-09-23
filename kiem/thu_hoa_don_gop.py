# -*- coding: utf-8 -*-
"""Thử HOÁ ĐƠN GỘP THÁNG — ໃບເກັບເງິນລວມເດືອນ.

    python kiem/thu_hoa_don_gop.py [http://127.0.0.1:8010]

Nghiệp vụ (anh Khampla trả lời 22/09, C8.2 · B3): khách có hợp đồng thì **cuối tháng gộp mọi phiếu
thành MỘT tờ hoá đơn**; khách vãng lai vẫn mỗi phiếu một tờ như cũ. Chỗ dễ sai nhất không phải là
gộp, mà là **thu tiền**: khách chuyển một cục cho cả tháng, nếu chỉ ghi ở tờ gộp thì mọi phiếu
trong tháng vẫn treo "chưa thu" và báo cáo theo phiếu sai hết. Nên tiền thu ở tờ gộp phải được
phân bổ xuống từng phiếu theo thứ tự ngày phiếu.

Kịch bản: đặt khách sang "gộp tháng" → lập hai phiếu, đi trọn luồng tới khoá → thử xuất hoá đơn
lẻ (phải bị chặn) → gộp một tờ → kiểm tiền tờ = cộng hai phiếu → thu một phần, kiểm phân bổ:
phiếu cũ đủ, phiếu sau còn thiếu → thử thu ở phiếu lẻ (phải bị chặn) → thử xoá dòng phân bổ ở
phiếu (phải bị chặn) → thử huỷ tờ khi đã thu (phải bị chặn) → thu nốt, cả hai phiếu thành "đã thu
đủ" → xoá lần thu, hai phiếu quay lại "chưa thu" → huỷ tờ, hai phiếu quay lại "chưa xuất hoá
đơn" → dọn sạch.
"""
import json
import sys
import urllib.error
import urllib.request
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _quy_trinh as Q  # Bãi lập không tiền → KT nhập giá (quy trình 23/09)

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}
SO_PHIEU = ("HDGOP-01/EPL", "HDGOP-02/EPL")
THANG = "2026-07"


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
    print("%s %-62s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def bang(a, b, ten, sai_so=1.0):
    if abs((a or 0) - (b or 0)) > sai_so:
        raise SystemExit("DỪNG: %s — nhận %s, mong %s" % (ten, a, b))
    print("  ✓ %-62s %s" % (ten, a))


def don():
    """Xoá dấu vết lần chạy trước bị đứt giữa chừng."""
    s, ds = goi("/api/trips", vai="admin")
    for p in [x for x in ds if x["doc_no"] in SO_PHIEU]:
        if p.get("invoice_id"):
            s, hd = goi("/api/hoa-don-gop/%s" % p["invoice_id"], vai="doanhthu")
            for x in (hd.get("thu_tien") or []):
                goi("/api/hoa-don-thu/%s" % x["id"], vai="doanhthu", method="DELETE")
            goi("/api/hoa-don-gop/%s" % p["invoice_id"], vai="doanhthu", method="DELETE")
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin")
        goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")


def den_khoa(pid, tan):
    """Đưa một phiếu đi trọn luồng tới trạng thái ĐÃ KHOÁ."""
    for muc in ("info", "trans", "fuel", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/send" % (pid, muc), {}, vai="thabok"); phai(s, 200, "gửi kiểm %s" % muc, g)
    for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/verify" % (pid, muc), {}, vai=v); phai(s, 200, "kiểm %s" % muc, g)
    for muc, v in (("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/book" % (pid, muc), {}, vai=v); phai(s, 200, "ghi sổ %s" % muc, g)
    s, g = goi("/api/trips/%s/sections/fuel/pay" % pid, {}, vai="quyvc"); phai(s, 200, "quỹ VC chi mục III", g)
    s, g = goi("/api/trips/%s/sections/travel/pay" % pid, {}, vai="quytb"); phai(s, 200, "quỹ Thabok chi mục IV", g)
    s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": tan, "odo_back": 200},
               vai="thabok"); phai(s, 200, "báo xe tới, cân %s t" % tan, g)
    s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "kế toán khoá phiếu", g)
    return g


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 8 vai")
    don()

    s, kh = goi("/api/customers", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    khach = kh[0]

    # ---------------------------------------------------------------- 1. cờ gộp tháng của khách
    s, g = goi("/api/customers/%s" % khach["id"], {"invoice_mode": "nam"}, vai="ketoan", method="PUT")
    phai(s, 422, "Cách xuất hoá đơn lạ → bị từ chối", g)
    s, g = goi("/api/customers/%s" % khach["id"], {"invoice_mode": "thang"}, vai="ketoan", method="PUT")
    phai(s, 200, "Đặt khách %s sang GỘP HOÁ ĐƠN THÁNG" % khach["name"], g)
    assert g["invoice_mode"] == "thang", "cờ phải lưu lại: %s" % g

    # ---------------------------------------------------------------- 2. hai phiếu trong cùng một tháng
    P = []
    for i, (so_p, ngay, tan, gia) in enumerate(((SO_PHIEU[0], "2026-07-05", 40.0, 50),
                                                (SO_PHIEU[1], "2026-07-19", 30.0, 50))):
        s, p = Q.lap_phieu(goi, {
            "doc_no": so_p, "kind": "gom", "doc_date": ngay, "out_date": ngay,
            "vehicle_id": xe[0]["id"], "driver_id": tx[0]["id"], "customer_id": khach["id"],
            "route_id": tuyen[0]["id"], "goods_type": "iron_ore", "weight_origin": tan,
            "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": tan}],
            "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 80, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                         {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"}],
        }, vai="thabok")
        phai(s, 200, "Bãi lập phiếu %s" % so_p, p)
        s, g = goi("/api/trips/%s" % p["id"], {"price": gia, "price_ccy": "USD"}, vai="ketoan", method="PUT")
        phai(s, 200, "Kế toán đặt cước %s USD/t cho %s" % (gia, so_p), g)
        P.append(p)

    # ---------------------------------------------------------------- 3. chưa khoá thì chưa gộp được
    s, g = goi("/api/hoa-don-gop", {"customer_id": khach["id"], "period": THANG}, vai="doanhthu")
    phai(s, 409, "Chưa phiếu nào khoá → không có gì để gộp", g)

    g1 = den_khoa(P[0]["id"], 40.0)
    g2 = den_khoa(P[1]["id"], 30.0)
    hd1, hd2 = g1["tinh"]["doanh_thu_lak"], g2["tinh"]["doanh_thu_lak"]

    # ---------------------------------------------------------------- 4. khách gộp tháng: không xuất hoá đơn lẻ
    s, g = goi("/api/trips/%s/invoice" % P[0]["id"], {}, vai="doanhthu")
    phai(s, 409, "Khách gộp tháng → chặn xuất hoá đơn lẻ từng phiếu", g)

    s, g = goi("/api/hoa-don-gop/cho-gop?period=%s" % THANG, vai="doanhthu")
    nhom = next((o for o in g["ds"] if o["customer_id"] == khach["id"] and o["ccy"] == "USD"), None)
    assert nhom and nhom["so_phieu"] == 2, "bảng chờ gộp phải thấy 2 phiếu: %s" % g
    print("  ✓ %-62s %s phiếu · %s USD" % ("Bảng chờ gộp thấy đúng khách và tiền", nhom["so_phieu"], nhom["tong"]))

    s, g = goi("/api/hoa-don-gop/cho-gop?period=%s" % THANG, vai="thabok")
    phai(s, 403, "Bãi xem hoá đơn (tiền bán) → bị từ chối", g)

    # ---------------------------------------------------------------- 5. gộp một tờ
    s, g = goi("/api/hoa-don-gop", {"customer_id": khach["id"], "period": THANG, "inv_date": "2026-07-31"}, vai="ketoan")
    phai(s, 403, "Kế toán VC gộp hoá đơn → bị từ chối (việc của KT doanh thu)", g)
    s, HD = goi("/api/hoa-don-gop", {"customer_id": khach["id"], "period": THANG, "inv_date": "2026-07-31",
                                     "note": "Hoá đơn gộp thử"}, vai="doanhthu")
    phai(s, 200, "KT doanh thu gộp hoá đơn tháng %s" % THANG, HD)
    assert HD["so_phieu"] == 2, "tờ phải có 2 phiếu: %s" % HD
    bang(HD["amount_lak"], hd1 + hd2, "Tiền tờ gộp = cộng doanh thu hai phiếu (LAK)")
    assert HD["currency"] == "USD", "tờ phải mang tiền cước USD: %s" % HD["currency"]
    print("  ✓ %-62s %s" % ("Số hoá đơn gộp", HD["inv_no"]))

    s, g = goi("/api/chung-tu?loai=HD&limit=10", vai="ketoan")
    to = next((c for c in g["ds"] if (c.get("mo_ta") or "").find(HD["inv_no"]) >= 0 or c["so"] == HD.get("chung_tu")), None)
    assert to and abs(to["tien_lak"] - HD["amount_lak"]) < 1, "phải có MỘT chứng từ HD cho cả tờ: %s" % to
    print("  ✓ %-62s %s · %s %s" % ("Một chứng từ HD cho cả tờ gộp", to["so"], to["tien"], to["tien_te"]))

    s, g = goi("/api/trips/%s" % P[0]["id"], vai="doanhthu")
    assert g["invoiced"] and g["invoice_id"] == HD["id"] and g["inv_no"] == HD["inv_no"], "phiếu phải trỏ về tờ gộp: %s" % g
    print("  ✓ %-62s %s" % ("Phiếu trỏ về tờ gộp", g["inv_no"]))

    # ---------------------------------------------------------------- 6. thu tiền ở tờ, phân bổ về phiếu
    s, g = goi("/api/trips/%s/thu-tien" % P[0]["id"], {"amount": 100, "currency": "USD"}, vai="doanhthu")
    phai(s, 409, "Ghi thu ở phiếu lẻ của tờ gộp → bị chặn, phải thu ở tờ", g)

    thu1 = hd1 + round(hd2 * 0.5)            # đủ phiếu 1, một nửa phiếu 2
    s, HD = goi("/api/hoa-don-gop/%s/thu-tien" % HD["id"],
                {"pay_date": "2026-08-05", "amount": thu1, "currency": "LAK", "method": "bank", "ref": "UNC-HDG-1"}, vai="doanhthu")
    phai(s, 200, "Thu lần một bằng Kíp (đủ phiếu cũ + nửa phiếu sau)", HD)
    bang(HD["da_thu_lak"], thu1, "Tờ gộp ghi nhận đã thu")
    bang(HD["con_lai_lak"], hd1 + hd2 - thu1, "Tờ gộp còn lại")
    assert HD["finance_status"] == "partial", "tờ phải là 'thu một phần': %s" % HD["finance_status"]

    s, a = goi("/api/trips/%s" % P[0]["id"], vai="doanhthu")
    s, b = goi("/api/trips/%s" % P[1]["id"], vai="doanhthu")
    assert a["finance_status"] == "paid", "phiếu CŨ phải đã thu đủ (phân bổ theo ngày): %s" % a["finance_status"]
    assert b["finance_status"] == "partial", "phiếu SAU phải là thu một phần: %s" % b["finance_status"]
    print("  ✓ %-62s %s · %s" % ("Phân bổ theo ngày: phiếu cũ đủ, phiếu sau một phần", a["doc_no"], b["doc_no"]))
    bang(a["tinh"]["da_thu_lak"], hd1, "Phiếu cũ đã thu = đúng doanh thu của nó")
    bang(b["tinh"]["da_thu_lak"], round(hd2 * 0.5), "Phiếu sau đã thu = nửa doanh thu")

    dong_pb = [x for x in (a.get("thu_tien") or []) if x.get("invoice_payment_id")]
    assert dong_pb, "dòng thu ở phiếu phải ghi rõ do tờ gộp phân bổ xuống"
    s, g = goi("/api/thu-tien/%s" % dong_pb[0]["id"], vai="doanhthu", method="DELETE")
    phai(s, 409, "Xoá lẻ dòng phân bổ ở phiếu → bị chặn", g)

    s, g = goi("/api/hoa-don-gop/%s" % HD["id"], vai="doanhthu", method="DELETE")
    phai(s, 409, "Huỷ tờ khi đã thu tiền → bị chặn", g)

    # ---------------------------------------------------------------- 7. thu nốt · thu dư
    con = HD["con_lai_lak"]
    s, g = goi("/api/hoa-don-gop/%s/thu-tien" % HD["id"], {"amount": con + 500000, "currency": "LAK"}, vai="doanhthu")
    phai(s, 409, "Thu quá số còn lại → phải xác nhận mới ghi", g)
    s, HD = goi("/api/hoa-don-gop/%s/thu-tien" % HD["id"],
                {"pay_date": "2026-08-20", "amount": con, "currency": "LAK", "method": "cash"}, vai="doanhthu")
    phai(s, 200, "Thu nốt phần còn lại", HD)
    assert HD["finance_status"] == "paid", "tờ phải thành 'đã thu đủ': %s" % HD["finance_status"]
    s, a = goi("/api/trips/%s" % P[0]["id"], vai="doanhthu")
    s, b = goi("/api/trips/%s" % P[1]["id"], vai="doanhthu")
    assert a["finance_status"] == "paid" and b["finance_status"] == "paid", \
        "cả hai phiếu phải 'đã thu đủ': %s · %s" % (a["finance_status"], b["finance_status"])
    print("  ✓ %-62s" % "Thu đủ tờ gộp → cả hai phiếu đều 'đã thu đủ'")

    s, g = goi("/api/chung-tu?loai=PT&limit=10", vai="ketoan")
    to_pt = [c for c in g["ds"] if (c.get("mo_ta") or "").find(HD["inv_no"]) >= 0]
    assert len(to_pt) == 2, "mỗi lần thu ở tờ gộp sinh đúng MỘT phiếu thu: %s" % len(to_pt)
    print("  ✓ %-62s %s" % ("Hai lần thu → hai tờ PT (không phải mỗi phiếu một tờ)", ", ".join(c["so"] for c in to_pt)))

    # ---------------------------------------------------------------- 8. xoá lần thu → trạng thái lùi lại
    for x in (HD.get("thu_tien") or []):
        s, HD = goi("/api/hoa-don-thu/%s" % x["id"], vai="doanhthu", method="DELETE")
        phai(s, 200, "Xoá lần thu %s" % x["pay_date"], HD)
    bang(HD["da_thu_lak"], 0, "Tờ gộp về lại chưa thu đồng nào")
    s, a = goi("/api/trips/%s" % P[0]["id"], vai="doanhthu")
    s, b = goi("/api/trips/%s" % P[1]["id"], vai="doanhthu")
    assert a["finance_status"] == "unpaid" and b["finance_status"] == "unpaid", \
        "hai phiếu phải quay về 'chưa thu': %s · %s" % (a["finance_status"], b["finance_status"])
    print("  ✓ %-62s" % "Xoá hết lần thu → hai phiếu quay về 'chưa thu'")

    # ---------------------------------------------------------------- 9. huỷ tờ → phiếu về chưa xuất hoá đơn
    s, g = goi("/api/hoa-don-gop/%s" % HD["id"], vai="doanhthu", method="DELETE")
    phai(s, 200, "Huỷ tờ hoá đơn gộp", g)
    s, a = goi("/api/trips/%s" % P[0]["id"], vai="doanhthu")
    assert not a["invoiced"] and not a["invoice_id"], "phiếu phải quay về 'chưa xuất hoá đơn': %s" % a
    print("  ✓ %-62s" % "Huỷ tờ → hai phiếu quay về 'chưa xuất hoá đơn'")

    # ---------------------------------------------------------------- 10. dọn
    s, g = goi("/api/customers/%s" % khach["id"], {"invoice_mode": "phieu"}, vai="ketoan", method="PUT")
    phai(s, 200, "Trả khách về mỗi phiếu một hoá đơn", g)
    for p in P:
        s, g = goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin"); phai(s, 200, "Mở khoá %s" % p["doc_no"], g)
        s, g = goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử %s" % p["doc_no"], g)
    print("\n✅ HOÁ ĐƠN GỘP THÁNG: gộp đúng tiền, thu ở tờ phân bổ đúng về từng phiếu, xoá và huỷ lùi lại sạch.")


if __name__ == "__main__":
    main()
