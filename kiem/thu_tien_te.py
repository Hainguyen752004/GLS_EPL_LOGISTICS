# -*- coding: utf-8 -*-
"""Thử NHIỀU TIỀN TỆ trên phiếu và trên ĐỀ NGHỊ THU sang hệ kế toán anh Tune.

    python kiem/thu_tien_te.py [http://127.0.0.1:8011]

Nghiệp vụ đang thử (chốt 21/09/2026 với anh chủ dự án): bên Lào nhận cước bằng USD, Kíp, Nhân dân tệ hay Bath tuỳ hợp đồng
từng khách; doanh thu quy Kíp theo tỷ giá KHOÁ trên phiếu.

Từ 01/10 chủ dự án bỏ trang kế toán tạm (hoá đơn, sổ thu tiền ở đó là số thử): trang điều xe không lập hoá đơn, không thu tiền.
Phiếu khoá xong sinh PHIẾU ĐỀ NGHỊ THU theo đúng tiền của phiếu; tờ đó gửi sang hệ anh Tune thành SO (công nợ khách). Bên đó mới
nhận cước VND · LAK · USD, nên cước Nhân dân tệ phải bị chặn ngay ở xem trước, không gửi một con số đổi tiền lặng lẽ.

Kịch bản: lập phiếu cước Nhân dân tệ → doanh thu quy Kíp đúng tỷ giá khoá → khoán trọn chuyến → đi tới khoá phiếu → đề nghị thu
mang CNY · xem trước SO chặn TIEN_TE_CHUA_NHAN → nút hoá đơn / thu tiền cũ trả 409 chỉ sang hệ kế toán → mở khoá, đổi sang USD,
khoá lại → đề nghị thu và gói SO theo USD, đúng số → phiếu không còn cờ hoá đơn trang tạm, "đã thu" = 0 (chưa có SO) → báo cáo chia
theo tiền → dọn. KHÔNG gọi sang hệ anh Tune (chỉ xem trước gói).
"""
import json
import sys
import urllib.error
import urllib.request
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _quy_trinh as Q  # Bãi lập không tiền → KT nhập giá (quy trình 23/09)
import _ke_toan as K  # noqa: E402 — kho tạm (EPL_KT): nhập trước rồi cấp (01/10)

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
if GOC.endswith((":8010", ":8020")):
    raise SystemExit("Không chạy bài này trên máy thật — nó lập rồi xoá phiếu thử.")
TOKEN = {}
SO = "THU-TIEN-01/EPL"


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau, method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma", "") if isinstance(d, dict) else ""


def phai(s, mong, buoc, g=None):
    print("%s %-62s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma(g)))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def bang(a, b, ten, sai_so=1.0):
    if abs((a or 0) - (b or 0)) > sai_so:
        raise SystemExit("DỪNG: %s — nhận %s, mong %s" % (ten, a, b))
    print("  ✓ %-62s %s" % (ten, a))


def don():
    s, cu = goi("/api/trips?q=THU-TIEN-01", vai="admin")
    for x in [x for x in (cu or []) if x["doc_no"] == SO]:
        goi("/api/trips/%s/mo-khoa" % x["id"], {}, vai="admin")
        s, g = goi("/api/trips/%s" % x["id"], vai="admin", method="DELETE")
        print("  · dọn phiếu thử %s sót lại → %s" % (SO, s))


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 8 vai")

    s, tg = goi("/api/rates", vai="admin")
    assert "CNY" in tg, "bảng tỷ giá phải có Nhân dân tệ: %s" % tg
    print("  ✓ tỷ giá: " + " · ".join("1 %s = %s LAK" % (k, v) for k, v in tg.items() if k != "LAK"))
    s, kh = goi("/api/customers", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    don()

    # ---------------------------------------------------------------- 1. tiền tệ trên phiếu
    # Phiếu GIAO phải lấy hàng từ một lô trong kho bãi (luồng hai DO), nên chọn lô còn hàng.
    s, lo = goi("/api/kho-hang/lo", vai="thabok")
    con = [x for x in lo if (x.get("con_t") or 0) >= 5]
    if not con:
        raise SystemExit("DỪNG: kho bãi không còn lô nào đủ 5 tấn để thử — chạy lại seed.py --dung-lai")
    lo0 = con[0]
    TAN = 10.0 if (lo0["con_t"] or 0) >= 10 else round(lo0["con_t"], 2)
    nha = [v for v in xe if v["owner_type"] == "EPL" and v["active"]]
    r0 = next((r for r in tuyen if not r.get("toll_lak")), tuyen[0])
    s, P = Q.lap_phieu(goi, {
        "doc_no": SO, "kind": "giao", "doc_date": "2026-09-20", "out_date": "2026-09-20",
        "vehicle_id": nha[0]["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
        "route_id": r0["id"], "goods_type": "iron_ore",
        "goods": [{"goods_name": lo0["goods_name"], "qty_t": TAN, "tu_phieu_id": lo0["lo_trip_id"]}],
        "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                     {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập phiếu giao lấy %s tấn từ kho bãi" % TAN, P)
    pid = P["id"]
    try:
        chay(pid, TAN, tg)
    finally:
        goi("/api/trips/%s/mo-khoa" % pid, {}, vai="admin")
        s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        print("  · dọn phiếu thử → %s" % s)
    s, g = goi("/api/trips/%s" % pid, vai="admin")
    phai(s, 404, "Phiếu thử đã xoá hẳn", g)
    print("\nTHỬ TIỀN TỆ: ĐẠT — cước CNY · quy Kíp đúng tỷ giá khoá · trọn chuyến · đề nghị thu mang đúng tiền · CNY chặn ở xem "
          "trước SO · USD gói đúng số · không còn cờ hoá đơn trang tạm · báo cáo chia theo tiền")


def chay(pid, TAN, tg):
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
    assert g["tinh"]["cach_tinh"] == "chuyen" and abs(g["tinh"]["doanh_thu"] - 5000) < 0.01, g["tinh"]["doanh_thu"]
    s, g = goi("/api/trips/%s" % pid, {"price_mode": "gi_do"}, vai="ketoan", method="PUT")
    phai(s, 422, "Cách tính lạ → bị từ chối", g)
    s, g = goi("/api/trips/%s" % pid, {"price_mode": "ton", "price": 300}, vai="ketoan", method="PUT")
    phai(s, 200, "Trả về theo tấn 300 CNY/t", g)
    bang(g["tinh"]["doanh_thu"], 300 * TAN, "theo tấn lại đúng tấn × giá", 0.01)

    # ---------------------------------------------------------------- 2. đi tới khoá phiếu
    for muc in ("info", "trans", "fuel", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/send" % (pid, muc), {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục %s" % muc, g)
    for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/verify" % (pid, muc), {}, vai=v); phai(s, 200, "Kiểm mục %s" % muc, g)
    # từ 30/09 dầu kho chỉ rời kho theo phiếu đề nghị đã cấp — in đề nghị, thủ kho cấp, rồi mới ghi sổ mục III
    # 01/10 kho tạm chặn cấp quá tồn: nhập trước đúng số lít sẽ cấp ở kho Thà Bốc (kho gốc, "fp_yard"); dòng nhập tự gỡ lúc bài xong (_ke_toan)
    K.nhap_truoc("KHO-TB", 100, "thử tiền tệ: nhập trước 100 L rồi cấp")
    s, vs = goi("/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, vai="thabok"); phai(s, 200, "Bãi in phiếu đề nghị xuất kho nhiên liệu", vs)
    for x in vs:
        s, g = goi("/api/vouchers/%s/cap" % x["id"], {"qty": x["qty_l"]}, vai="khonl"); phai(s, 200, "Cấp dầu theo " + x["doc_no"], g)
    for muc, v in (("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/book" % (pid, muc), {}, vai=v); phai(s, 200, "Ghi sổ mục %s" % muc, g)
    s, g = goi("/api/trips/%s/sections/fuel/pay" % pid, {}, vai="quyvc"); phai(s, 200, "Quỹ VC chi mục III", g)
    # mục IV chỉ có tiền nước trả cùng lương — không có tiền mặt tạm ứng, xe đi không vướng
    s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": TAN, "odo_back": 100, "back_date": "2026-09-22",
                                                        "pod_no": "THU-TIEN-POD"}, vai="thabok")
    phai(s, 200, "Bãi báo xe đã tới", g)
    s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "Kế toán khoá phiếu", g)

    # ---------------------------------------------------------------- 3. hoá đơn · thu tiền không còn ở đây
    for d, vai in (("/api/trips/%s/invoice" % pid, "doanhthu"), ("/api/trips/%s/thu-tien" % pid, "doanhthu")):
        s, g = goi(d, {}, vai=vai)
        phai(s, 409, "Nút cũ %s → 409, chỉ sang hệ kế toán" % d.rsplit("/", 1)[-1], g)
        assert ma(g) == "DA_DOI_SANG_KE_TOAN" and "hệ kế toán" in g["detail"]["loi"], g
    s, g = goi("/api/hoa-don-gop", vai="doanhthu"); phai(s, 409, "Hoá đơn gộp tháng → 409, làm ở hệ kế toán", g)

    # ---------------------------------------------------------------- 4. đề nghị thu theo tiền của phiếu · CNY chặn ở SO
    s, d = goi("/api/trips/%s/de-nghi-thu" % pid, vai="ketoan"); phai(s, 200, "Tờ đề nghị thu của phiếu đã khoá", d)
    assert d["ccy"] == "CNY" and abs(d["doanh_thu"] - 300 * TAN) < 0.01 and d["pdt"], d
    bang(d["doanh_thu_lak"], 300 * TAN * tg["CNY"], "đề nghị thu quy Kíp đúng tỷ giá khoá")
    assert d["trang_thai"] == "cho_gui" and not d["da_tao_so"] and d["da_thu_lak"] == 0, d
    print("  ✓ %-62s %s" % ("trạng thái: chờ gửi bên công nợ, chưa có SO, đã thu 0", d["trang_thai"]))
    s, v = goi("/api/trips/%s/tao-so" % pid, vai="ketoan"); phai(s, 200, "Xem trước gói SO (không gọi mạng)", v)
    assert (v.get("loi") or {}).get("ma") == "TIEN_TE_CHUA_NHAN", "cước CNY phải bị chặn: bên kế toán mới nhận VND · LAK · USD — %s" % v.get("loi")
    print("  ✓ %-62s %s" % ("cước CNY → xem trước chặn TIEN_TE_CHUA_NHAN (không đổi tiền lặng lẽ)", v["loi"]["ma"]))

    # ---------------------------------------------------------------- 5. mở khoá, đổi sang USD, khoá lại
    s, g = goi("/api/trips/%s/mo-khoa" % pid, {}, vai="ketoan"); phai(s, 200, "Chưa có SO → KT Thu/Chi mở khoá được", g)
    s, d = goi("/api/trips/%s/de-nghi-thu" % pid, vai="ketoan")
    assert not d["pdt"] and d["trang_thai"] == "cho_khoa", "mở khoá phải rút tờ đề nghị thu chưa có SO: %s" % d.get("pdt")
    s, g = goi("/api/trips/%s/sections/trans/return" % pid, {}, vai="ketoan"); phai(s, 200, "Kế toán trả lại mục II để sửa cước", g)
    s, g = goi("/api/trips/%s" % pid, {"price": 45, "price_ccy": "USD"}, vai="ketoan", method="PUT"); phai(s, 200, "Đổi cước 45 USD/t", g)
    s, g = goi("/api/trips/%s/sections/trans/send" % pid, {}, vai="thabok"); phai(s, 200, "Bãi gửi lại mục II", g)
    s, g = goi("/api/trips/%s/sections/trans/verify" % pid, {}, vai="ketoan"); phai(s, 200, "Kiểm lại mục II", g)
    s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "Khoá lại", g)
    s, d = goi("/api/trips/%s/de-nghi-thu" % pid, vai="ketoan")
    assert d["ccy"] == "USD" and abs(d["doanh_thu"] - 45 * TAN) < 0.01 and d["pdt"]["tien_te"] == "USD", d
    bang(d["pdt"]["tien_lak"], round(45 * TAN * tg["USD"]), "tờ đề nghị thu MỚI theo số mới (USD quy Kíp)")
    s, v = goi("/api/trips/%s/tao-so" % pid, vai="ketoan"); phai(s, 200, "Xem trước gói SO theo USD", v)
    assert not v.get("loi"), v.get("loi")
    h = v["body"]["header"]
    assert h["currency"] == "USD" and abs(float(h["final_selling_price"]) - 45 * TAN) < 0.001, h
    print("  ✓ %-62s %s %s" % ("gói SO mang đúng tiền và số cước", h["final_selling_price"], h["currency"]))

    # ---------------------------------------------------------------- 6. phiếu không còn cờ trang tạm; đã thu đọc từ hệ kế toán
    s, p = goi("/api/trips/%s" % pid, vai="doanhthu")
    lo = [k for k in ("invoiced", "inv_no", "invoice_id", "invoiced_date", "last_paid_date") if k in p]
    assert not lo, "gói phiếu không được còn cờ hoá đơn trang tạm: %s" % lo
    assert p["da_tao_so"] is False and p["so_ke_toan"] is None and p["tinh"]["da_thu_lak"] == 0 and p["finance_status"] == "unpaid", \
        (p["da_tao_so"], p["so_ke_toan"], p["tinh"]["da_thu_lak"], p["finance_status"])
    print("  ✓ %-62s" % "phiếu: chưa có SO · đã thu 0 · không còn cờ hoá đơn trang tạm")
    s, ds = goi("/api/trips?q=THU-TIEN-01&da_tao_so=false", vai="doanhthu")
    assert any(x["id"] == pid for x in ds), "lọc 'chưa tạo SO' phải ra phiếu thử"
    s, ds = goi("/api/trips?q=THU-TIEN-01&da_tao_so=true", vai="doanhthu")
    assert not any(x["id"] == pid for x in ds), "lọc 'đã tạo SO' không được ra phiếu thử"
    print("  ✓ %-62s" % "lọc danh sách theo 'đã tạo SO' đúng")

    # ---------------------------------------------------------------- 7. báo cáo chia theo từng loại tiền
    s, tq = goi("/api/bao-cao/tong-quan?thang=2026-09", vai="admin"); phai(s, 200, "Tổng quan tháng 9", tq)
    assert "doanh_thu_lak" in tq and "doanh_thu_usd" not in tq, "tổng quan phải cộng bằng Kíp, không còn khoá _usd: %s" % list(tq)
    assert tq["doanh_thu_tien"].get("USD"), "phải chia doanh thu theo từng loại tiền: %s" % tq["doanh_thu_tien"]
    print("  ✓ %-62s %s" % ("tổng quan chia theo tiền", " · ".join("%s %s" % (v, k) for k, v in tq["doanh_thu_tien"].items())))
    s, tq2 = goi("/api/bao-cao/tong-quan?thang=2026-09", vai="thabok")
    assert "doanh_thu_lak" not in tq2 and "doanh_thu_tien" not in tq2, "Bãi vẫn không được thấy tiền bán: %s" % list(tq2)
    print("  ✓ %-62s" % "Bãi vẫn không thấy tiền bán (kể cả ô chia theo tiền)")
    s, td = goi("/api/bao-cao/theo-doi?thang=2026-09&q=THU-TIEN-01", vai="admin")
    dong = next(x for x in td if x["doc_no"] == SO)
    assert dong["tinh"]["ccy"] == "USD", "bảng theo dõi phải nói rõ tiền của từng phiếu"


if __name__ == "__main__":
    main()
