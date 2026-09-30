# -*- coding: utf-8 -*-
"""Thử THẺ CAO TỐC — ບັດທາງດ່ວນ (anh Khampla C6.1).

    python kiem/thu_the_cao_toc.py [http://127.0.0.1:8010]

Họ muốn biết **thẻ còn bao nhiêu tiền**, mỗi chuyến qua trạm trừ từ thẻ nào, và cuối tháng — với thẻ
do **khách cấp và nạp tiền** — phần EPL đã tiêu trên thẻ được **cấn trừ vào cước** của chính khách đó.

Kịch bản: lập thẻ (chặn thẻ khách không ghi khách, chặn trùng số) → nạp tiền → lập phiếu có dòng phí
cầu đường chọn thẻ → **thẻ CHƯA bị trừ khi mới nhập** (dòng còn sửa được) → kế toán ghi sổ mục IV →
thẻ bị trừ đúng một lần, dòng chi ghi rõ đã trừ → ghi sổ lại không trừ thêm → xoá dòng đã trừ bị chặn →
điều chỉnh số dư phải có lý do → bảng cấn trừ cuối tháng ra đúng số của khách → dọn.
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
SO_PHIEU = "THE-CT-01/EPL"
SO_THE = "THU-THE-01"


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


def bang(a, b, ten, sai_so=1.0):
    if abs((a or 0) - (b or 0)) > sai_so:
        raise SystemExit("DỪNG: %s — nhận %s, mong %s" % (ten, a, b))
    print("  ✓ %-60s %s" % (ten, a))


def don():
    """Dọn dấu vết lần chạy trước bị đứt: xoá phiếu thử, và đổi số thẻ thử cũ đi cho khỏi trùng."""
    s, ds = goi("/api/trips", vai="admin")
    for p in [x for x in ds if x["doc_no"] == SO_PHIEU]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin")
        goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
    s, the = goi("/api/the-cao-toc", vai="ketoan")
    for t in [x for x in the if x["card_no"] == SO_THE]:
        # Đổi số cũ sang một số DUY NHẤT (kèm mã thẻ) rồi ngưng — số thẻ là khoá duy nhất, đặt
        # "-CU1" cho mọi lần chạy thì lần thứ hai đụng chính cái đã đổi lần trước.
        goi("/api/the-cao-toc/%s" % t["id"], {"card_no": "%s-CU-%s" % (SO_THE, t["id"][:6]), "active": False},
            vai="ketoan", method="PUT")


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

    # ---------------------------------------------------------------- 1. danh mục thẻ
    s, g = goi("/api/the-cao-toc", {"card_no": SO_THE, "kind": "khach", "currency": "LAK"}, vai="thabok")
    phai(s, 403, "Bãi lập thẻ → bị chặn (thoả thuận với khách, kế toán giữ)", g)
    s, g = goi("/api/the-cao-toc", {"card_no": SO_THE, "kind": "khach", "currency": "LAK"}, vai="ketoan")
    phai(s, 422, "Thẻ khách cấp mà không ghi khách nào → bị từ chối", g)
    s, THE = goi("/api/the-cao-toc", {"card_no": SO_THE, "name": "Thẻ thử", "kind": "khach",
                                      "customer_id": khach["id"], "driver_id": tx[0]["id"],
                                      "currency": "LAK", "balance": 0}, vai="ketoan")
    phai(s, 200, "Kế toán lập thẻ do khách %s cấp" % khach["name"], THE)
    tid = THE["id"]
    s, g = goi("/api/the-cao-toc", {"card_no": SO_THE, "kind": "epl", "currency": "LAK"}, vai="ketoan")
    phai(s, 409, "Trùng số thẻ → bị từ chối", g)

    # ---------------------------------------------------------------- 2. nạp tiền
    s, g = goi("/api/the-cao-toc/%s/nap" % tid, {"amount": 4000000, "ref": "NAP-THU"}, vai="thabok")
    phai(s, 403, "Bãi nạp tiền vào thẻ → bị chặn", g)
    s, THE = goi("/api/the-cao-toc/%s/nap" % tid, {"amount": 4000000, "ref": "NAP-THU", "move_date": "2026-09-02"}, vai="quytb")
    phai(s, 200, "Quỹ Thà Bốc nạp 4.000.000 Kíp", THE)
    bang(THE["balance"], 4000000, "Số dư thẻ sau khi nạp")
    assert THE["moves"][0]["balance_after"] == 4000000, "dòng nạp phải ghi số dư sau"

    # ---------------------------------------------------------------- 3. phiếu có dòng phí cầu đường trả bằng thẻ
    s, P = Q.lap_phieu(goi, {
        "doc_no": SO_PHIEU, "kind": "gom", "doc_date": "2026-09-20", "out_date": "2026-09-20",
        "vehicle_id": xe[0]["id"], "driver_id": tx[0]["id"], "customer_id": khach["id"],
        "route_id": tuyen[0]["id"], "goods_type": "iron_ore", "weight_origin": 30,
        "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 30}],
        "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 70, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                     {"section": "travel", "item_key": "x_toll", "qty": 1, "unit_price": 1200000, "currency": "LAK",
                      "toll_card_id": tid},
                     {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập phiếu, dòng phí cầu đường chọn trả bằng thẻ", P)
    pid = P["id"]
    dong_the = [d for d in P["expenses"] if d.get("toll_card_id")]
    assert len(dong_the) == 1 and not dong_the[0]["card_move_id"], "mới nhập thì CHƯA trừ thẻ: %s" % dong_the
    s, g = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
    bang(g["balance"], 4000000, "Nhập dòng chi xong thẻ vẫn chưa bị trừ")

    # ---------------------------------------------------------------- 4. ghi sổ mục IV → trừ thẻ
    for muc in ("info", "trans", "fuel", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/send" % (pid, muc), {}, vai="thabok"); phai(s, 200, "gửi kiểm %s" % muc, g)
    for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl"), ("travel", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/%s/verify" % (pid, muc), {}, vai=v); phai(s, 200, "kiểm %s" % muc, g)
    s, g = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
    bang(g["balance"], 4000000, "Kiểm xong mục IV thẻ vẫn chưa bị trừ")
    s, g = goi("/api/trips/%s/sections/travel/book" % pid, {}, vai="ketoancp")
    phai(s, 200, "KT Chi phí GHI SỔ mục IV → lúc này mới trừ thẻ", g)
    d = [x for x in g["expenses"] if x.get("toll_card_id")][0]
    assert d["card_move_id"], "dòng chi phải ghi đã trừ thẻ"
    s, THE = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
    bang(THE["balance"], 4000000 - 1200000, "Số dư thẻ sau khi qua trạm")
    m = THE["moves"][0]
    assert m["kind"] == "chi" and m["trip_doc_no"] == SO_PHIEU, "dòng trừ phải nhắc số phiếu: %s" % m
    print("  ✓ %-60s %s" % ("Dòng trừ thẻ nhắc đúng số phiếu", m["trip_doc_no"]))

    # dầu kho chỉ rời kho theo phiếu ĐỀ NGHỊ đã cấp (chủ dự án 30/09): Bãi in đề nghị → cấp dầu → mới ghi sổ mục III
    s, v = goi("/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, vai="thabok"); phai(s, 200, "Bãi in phiếu đề nghị xuất nhiên liệu", v)
    for x in v:
        s, g = goi("/api/vouchers/%s/cap" % x["id"], {"qty": x["qty_l"]}, vai="khonl"); phai(s, 200, "Cấp dầu theo " + x["doc_no"], g)
    s, g = goi("/api/trips/%s/sections/fuel/book" % pid, {}, vai="khonl"); phai(s, 200, "ghi sổ mục III", g)
    s, THE2 = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
    bang(THE2["balance"], 2800000, "Ghi sổ mục khác không trừ thẻ thêm lần nữa")

    # dòng đã trừ thẻ thì không xoá lặng lẽ khỏi phiếu
    s, g = goi("/api/trips/%s/sections/travel/unlock" % pid, {}, vai="admin"); phai(s, 200, "Sếp mở lại mục IV đã ghi sổ", g)
    s, g = goi("/api/trips/%s" % pid, {"expenses": [{"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"}]},
               vai="thabok", method="PUT")
    phai(s, 409, "Xoá dòng đã trừ thẻ khỏi phiếu → bị từ chối", g)

    # ---------------------------------------------------------------- 5. điều chỉnh số dư phải có lý do
    s, g = goi("/api/the-cao-toc/%s/dieu-chinh" % tid, {"amount": -50000}, vai="ketoan")
    phai(s, 422, "Điều chỉnh số dư không ghi lý do → bị từ chối", g)
    s, THE = goi("/api/the-cao-toc/%s/dieu-chinh" % tid, {"amount": -50000, "note": "thử: trạm quẹt chưa khai"}, vai="ketoan")
    phai(s, 200, "Điều chỉnh giảm 50.000 kèm lý do", THE)
    bang(THE["balance"], 2750000, "Số dư sau điều chỉnh")

    # ---------------------------------------------------------------- 6. cấn trừ cuối tháng
    s, g = goi("/api/the-cao-toc/cong-no?thang=2026-09", vai="thabok")
    phai(s, 403, "Bãi xem bảng cấn trừ cước → bị chặn (tiền bán)", g)
    s, ct = goi("/api/the-cao-toc/cong-no?thang=2026-09", vai="doanhthu" if "doanhthu" in TOKEN else "ketoan")
    o = next((x for x in ct["ds"] if x["customer_id"] == khach["id"]), None)
    assert o, "bảng cấn trừ phải có khách %s: %s" % (khach["name"], ct)
    assert o["can_tru"] >= 1200000, "số cấn trừ phải gồm 1.200.000 đã tiêu trên thẻ khách: %s" % o
    print("  ✓ %-60s %s LAK" % ("Cấn trừ vào cước của khách trong tháng", round(o["can_tru"])))

    # ---------------------------------------------------------------- 7. dọn
    s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử (dọn)", g)
    s, g = goi("/api/the-cao-toc/%s" % tid, {"active": False}, vai="ketoan", method="PUT")
    phai(s, 200, "Ngưng thẻ thử (dọn)", g)
    print("\n✅ THẺ CAO TỐC: số dư đúng, trừ ĐÚNG MỘT LẦN lúc ghi sổ mục IV, điều chỉnh phải có lý do,")
    print("   cấn trừ cuối tháng ra đúng số của khách cấp thẻ.")


if __name__ == "__main__":
    main()
