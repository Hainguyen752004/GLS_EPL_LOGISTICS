# -*- coding: utf-8 -*-
"""Thử NHIỀU TIỀN TỆ và SỔ THU TIỀN.

    python kiem/thu_tien_te.py [http://127.0.0.1:8010]

Nghiệp vụ đang thử (chốt 21/09/2026 với anh chủ dự án): bên Lào nhận cước bằng USD, Kíp, Nhân dân
tệ hay Bath tuỳ hợp đồng từng khách, và **khách trả bằng tiền khác với tiền ghi trên hoá đơn** —
hoá đơn USD mà chuyển Kíp là chuyện thường. Trước đây phần mềm chỉ có một cái nút "đã thu" nên
không ghi được điều đó; giờ mỗi lần tiền về là một dòng có ngày, số tiền, tiền tệ và tỷ giá.

Kịch bản: lập phiếu cước bằng Nhân dân tệ → kiểm doanh thu quy Kíp đúng tỷ giá khoá trên phiếu →
đi trọn luồng tới hoá đơn → thu lần một bằng Kíp (một phần) → thu lần hai bằng chính Nhân dân tệ
(đủ) → thử thu dư → xoá một lần thu → kiểm báo cáo chia tiền đúng → dọn sạch.
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
    print("%s %-58s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def bang(a, b, ten, sai_so=1.0):
    if abs((a or 0) - (b or 0)) > sai_so:
        raise SystemExit("DỪNG: %s — nhận %s, mong %s" % (ten, a, b))
    print("  ✓ %-58s %s" % (ten, a))


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 7 vai")

    s, tg = goi("/api/rates", vai="admin")
    assert "CNY" in tg, "bảng tỷ giá phải có Nhân dân tệ: %s" % tg
    print("  ✓ tỷ giá: " + " · ".join("1 %s = %s LAK" % (k, v) for k, v in tg.items() if k != "LAK"))

    s, kh = goi("/api/customers", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")

    # ---------------------------------------------------------------- 1. tiền tệ trên phiếu
    # Phiếu GIAO phải lấy hàng từ một lô trong kho bãi (luồng hai DO), nên chọn lô còn hàng.
    # lần chạy trước hỏng giữa đường thì phiếu thử còn giữ hàng của lô — dọn trước
    s, cu = goi("/api/trips?q=THU-TIEN-01", vai="admin")
    for x in [x for x in (cu or []) if x["doc_no"] == "THU-TIEN-01/EPL"]:
        goi("/api/trips/%s/mo-khoa" % x["id"], {}, vai="admin"); goi("/api/trips/%s" % x["id"], vai="admin", method="DELETE")
        print("  · đã dọn phiếu thử THU-TIEN-01/EPL sót lại")
    s, lo = goi("/api/kho-hang/lo", vai="thabok")
    con = [x for x in lo if (x.get("con_t") or 0) >= 5]
    if not con:
        raise SystemExit("DỪNG: kho bãi không còn lô nào đủ 5 tấn để thử — chạy lại seed.py --dung-lai")
    lo0 = con[0]
    TAN = 10.0 if (lo0["con_t"] or 0) >= 10 else round(lo0["con_t"], 2)
    s, P = Q.lap_phieu(goi, {
        "doc_no": "THU-TIEN-01/EPL", "kind": "giao", "doc_date": "2026-09-20", "out_date": "2026-09-20",
        "vehicle_id": xe[0]["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
        "route_id": tuyen[0]["id"], "goods_type": "iron_ore",
        "goods": [{"goods_name": lo0["goods_name"], "qty_t": TAN, "tu_phieu_id": lo0["lo_trip_id"]}],
        "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                     {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập phiếu giao lấy %s tấn từ kho bãi" % TAN, P)
    pid = P["id"]

    s, g = goi("/api/trips/%s" % pid, {"price": 300, "price_ccy": "CNY"}, vai="ketoan", method="PUT")
    phai(s, 200, "Kế toán đặt cước 300 Nhân dân tệ/tấn", g)
    assert g["price_ccy"] == "CNY", "phiếu phải giữ đúng tiền tệ CNY: %s" % g["price_ccy"]
    bang(g["tinh"]["doanh_thu"], 300 * TAN, "doanh thu %s CNY" % (300 * TAN), 0.01)
    bang(g["tinh"]["doanh_thu_lak"], 300 * TAN * tg["CNY"], "quy về Kíp theo tỷ giá khoá trên phiếu")
    assert g["tinh"]["ccy"] == "CNY", "khối tính phải nói rõ tiền tệ"

    s, g = goi("/api/trips/%s" % pid, {"price_ccy": "XYZ"}, vai="ketoan", method="PUT")
    phai(s, 422, "Tiền tệ lạ → bị từ chối, không lặng lẽ đổi thành Kíp", g)

    # 2.1 (anh Khampla C3.6): cước KHOÁN TRỌN CHUYẾN — thành tiền = đơn giá, không nhân tấn
    s, g = goi("/api/trips/%s" % pid, {"price_mode": "chuyen", "price": 5000}, vai="ketoan", method="PUT")
    phai(s, 200, "Kế toán đổi sang khoán trọn chuyến 5.000 CNY", g)
    assert g["tinh"]["cach_tinh"] == "chuyen" and abs(g["tinh"]["doanh_thu"] - 5000) < 0.01, "trọn chuyến thì doanh thu = đơn giá: %s" % g["tinh"]["doanh_thu"]
    s, g = goi("/api/trips/%s" % pid, {"price_mode": "gi_do"}, vai="ketoan", method="PUT")
    phai(s, 422, "Cách tính lạ → bị từ chối", g)
    s, g = goi("/api/trips/%s" % pid, {"price_mode": "ton", "price": 300}, vai="ketoan", method="PUT")
    phai(s, 200, "Trả về theo tấn 300 CNY/t", g)
    bang(g["tinh"]["doanh_thu"], 300 * TAN, "theo tấn lại đúng tấn × giá", 0.01)

    # ---------------------------------------------------------------- 2. đi tới hoá đơn
    s, g = goi("/api/dang-nhap", {"username": "khonl", "password": "1234"}); TOKEN["khonl"] = g["token"]
    for muc in ("info", "trans", "fuel", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/send" % (pid, muc), {}, vai="thabok")
        phai(s, 200, "Bãi gửi kiểm mục %s" % muc, g)
    for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/verify" % (pid, muc), {}, vai=v)
        phai(s, 200, "Kiểm mục %s" % muc, g)
    for muc, v in (("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/book" % (pid, muc), {}, vai=v)
        phai(s, 200, "Ghi sổ mục %s" % muc, g)
    s, g = goi("/api/trips/%s/sections/fuel/pay" % pid, {}, vai="quyvc"); phai(s, 200, "Quỹ VC chi mục III", g)
    s, g = goi("/api/trips/%s/sections/travel/pay" % pid, {}, vai="quytb"); phai(s, 200, "Quỹ Thabok chi mục IV", g)
    s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": TAN, "odo_back": 100, "back_date": "2026-09-22"}, vai="thabok")
    phai(s, 200, "Bãi báo xe đã tới", g)
    s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "Kế toán khoá phiếu", g)
    s, HD = goi("/api/trips/%s/invoice" % pid, {}, vai="doanhthu"); phai(s, 200, "Lập hoá đơn", HD)

    s, ct = goi("/api/chung-tu?loai=HD&limit=5", vai="ketoan")
    to_hd = next((c for c in ct["ds"] if c["trip_doc_no"] == "THU-TIEN-01/EPL"), None)
    assert to_hd and to_hd["tien_te"] == "CNY" and abs(to_hd["tien"] - 300 * TAN) < 0.01, \
        "chứng từ hoá đơn phải mang tiền tệ CNY và số %s: %s" % (300 * TAN, to_hd)
    print("  ✓ %-58s %s %s" % ("chứng từ hoá đơn mang đúng tiền tệ", to_hd["tien"], to_hd["tien_te"]))

    # ---------------------------------------------------------------- 3. thu tiền nhiều lần, nhiều tiền tệ
    tong_lak = round(300 * TAN * tg["CNY"])
    s, g = goi("/api/trips/%s/thu-tien" % pid, {"amount": 1000, "currency": "LAK"}, vai="thabok")
    phai(s, 403, "Bãi ghi thu tiền → bị từ chối", g)

    thu1 = round(tong_lak * 0.4)
    s, g = goi("/api/trips/%s/thu-tien" % pid,
               {"pay_date": "2026-09-23", "amount": thu1, "currency": "LAK", "method": "bank", "ref": "UNC-001"}, vai="doanhthu")
    phai(s, 200, "Thu lần 1: khách chuyển Kíp cho hoá đơn CNY", g)
    assert g["finance_status"] == "partial", "thu một phần thì trạng thái phải là 'partial': %s" % g["finance_status"]
    bang(g["tinh"]["da_thu_lak"], thu1, "đã thu (Kíp)")
    bang(g["tinh"]["con_lai_lak"], tong_lak - thu1, "còn lại (Kíp)")
    bang(g["tinh"]["con_lai"], (tong_lak - thu1) / tg["CNY"], "còn lại quy về tiền hoá đơn (CNY)", 0.05)

    s, g = goi("/api/trips/%s/thu-tien" % pid, {"amount": 99999, "currency": "CNY"}, vai="doanhthu")
    phai(s, 409, "Thu nhiều hơn số còn lại → chặn, bắt xác nhận", g)

    con = g["detail"]["con_lai_lak"] if isinstance(g.get("detail"), dict) else None
    assert con is not None, "lỗi thu dư phải nói rõ còn lại bao nhiêu để màn hình hiện được"

    s, g = goi("/api/trips/%s/thu-tien" % pid, {"amount": round((tong_lak - thu1) / tg["CNY"], 2), "currency": "CNY", "method": "cash"}, vai="doanhthu")
    phai(s, 200, "Thu lần 2: khách trả nốt bằng chính Nhân dân tệ", g)
    assert g["finance_status"] == "paid", "thu đủ thì trạng thái phải tự sang 'paid': %s" % g["finance_status"]
    assert len(g["thu_tien"]) == 2, "sổ thu phải có hai dòng: %s" % g["thu_tien"]
    print("  ✓ %-58s %s" % ("trạng thái tài chính tự suy từ tổng đã thu", g["finance_status"]))

    s, ct = goi("/api/chung-tu?loai=PT&limit=20", vai="ketoan")
    pt = [c for c in ct["ds"] if c["trip_doc_no"] == "THU-TIEN-01/EPL"]
    assert len(pt) == 2, "mỗi lần thu phải để lại MỘT phiếu thu trong sổ chứng từ: %s" % len(pt)
    assert {c["tien_te"] for c in pt} == {"LAK", "CNY"}, "phiếu thu phải mang đúng tiền khách trả: %s" % pt
    print("  ✓ %-58s %s" % ("sổ chứng từ có hai phiếu thu đúng tiền tệ", " · ".join("%s %s" % (c["tien"], c["tien_te"]) for c in pt)))

    # ---------------------------------------------------------------- 4. xoá một lần thu
    s, dsthu = goi("/api/trips/%s/thu-tien" % pid, vai="doanhthu")
    phai(s, 200, "Xem sổ thu tiền", dsthu)
    id_thu2 = dsthu["ds"][-1]["id"]
    s, g = goi("/api/thu-tien/%s" % id_thu2, vai="thabok", method="DELETE")
    phai(s, 403, "Bãi xoá lần thu → bị từ chối", g)
    s, g = goi("/api/thu-tien/%s" % id_thu2, vai="doanhthu", method="DELETE")
    phai(s, 200, "Kế toán doanh thu xoá lần thu ghi nhầm", g)
    assert g["finance_status"] == "partial", "xoá bớt lần thu thì trạng thái phải lùi về 'partial': %s" % g["finance_status"]

    # đánh dấu tờ phiếu thu còn lại là đã đẩy kế toán → không xoá được nữa
    s, ct = goi("/api/chung-tu?loai=PT&limit=20", vai="ketoan")
    to_pt = next(c for c in ct["ds"] if c["trip_doc_no"] == "THU-TIEN-01/EPL")
    s, g = goi("/api/chung-tu/%s/da-day" % to_pt["id"], {"da_day": True}, vai="ketoan")
    phai(s, 200, "Đánh dấu phiếu thu đã đẩy sang kế toán", g)
    s, g = goi("/api/thu-tien/%s" % dsthu["ds"][0]["id"], vai="doanhthu", method="DELETE")
    phai(s, 409, "Xoá lần thu đã đẩy kế toán → bị từ chối", g)
    s, g = goi("/api/chung-tu/%s/da-day" % to_pt["id"], {"da_day": False}, vai="ketoan")

    # ---------------------------------------------------------------- 5. báo cáo chia theo từng loại tiền
    s, tq = goi("/api/bao-cao/tong-quan?thang=2026-09", vai="admin")
    phai(s, 200, "Tổng quan tháng 9", tq)
    assert "doanh_thu_lak" in tq and "doanh_thu_usd" not in tq, "tổng quan phải cộng bằng Kíp, không còn khoá _usd: %s" % list(tq)
    assert tq["doanh_thu_tien"].get("CNY"), "phải chia doanh thu theo từng loại tiền: %s" % tq["doanh_thu_tien"]
    print("  ✓ %-58s %s" % ("tổng quan chia theo tiền", " · ".join("%s %s" % (v, k) for k, v in tq["doanh_thu_tien"].items())))

    s, tq2 = goi("/api/bao-cao/tong-quan?thang=2026-09", vai="thabok")
    assert "doanh_thu_lak" not in tq2 and "doanh_thu_tien" not in tq2, "Bãi vẫn không được thấy tiền bán: %s" % list(tq2)
    print("  ✓ %-58s" % "Bãi vẫn không thấy tiền bán (kể cả ô chia theo tiền)")

    s, td = goi("/api/bao-cao/theo-doi?thang=2026-09", vai="admin")
    dong = next(p for p in td if p["doc_no"] == "THU-TIEN-01/EPL")
    assert dong["tinh"]["ccy"] == "CNY", "bảng theo dõi phải nói rõ tiền của từng phiếu"

    # ---------------------------------------------------------------- 6. dọn
    s, g = goi("/api/trips/%s/mo-khoa" % pid, {}, vai="admin")
    s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
    phai(s, 200, "Admin xoá phiếu thử (dọn)", g)
    s, g = goi("/api/trips/%s" % pid, vai="admin")
    phai(s, 404, "Phiếu thử đã xoá hẳn", g)

    print("\nTHỬ TIỀN TỆ: ĐẠT — cước CNY · quy Kíp đúng tỷ giá khoá · thu nhiều lần nhiều tiền · "
          "trạng thái tự suy · chặn thu dư · chặn xoá tờ đã đẩy · báo cáo chia theo tiền")


if __name__ == "__main__":
    main()
