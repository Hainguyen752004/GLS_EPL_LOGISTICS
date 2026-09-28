# -*- coding: utf-8 -*-
"""Thử NỢ TRẠM DẦU VIỆT NAM và CẤN TRỪ CƯỚC THÁNG (anh Khampla C5.1).

    python kiem/thu_no_tram_dau.py [http://127.0.0.1:8010]

Ghi chú của họ ở C5.1: tài xế đổ dầu bên Việt Nam **ghi nợ tại trạm**, cuối tháng EPL cấn trừ với
cước khách. Đây là công nợ **hai chiều**: EPL nợ trạm, khách nợ EPL, hai số bù nhau.

Phân biệt phải giữ cho đúng:
  · dòng dầu mua ngoài mà **tài xế trả tiền mặt** → EPL không nợ trạm đồng nào;
  · dòng dầu mua ngoài **ghi nợ trạm** → đúng bằng số EPL nợ trạm đó.

Kịch bản: gắn khách cấn trừ cho trạm dầu → lập phiếu có hai dòng dầu VN (một trả tiền mặt, một ghi
nợ) → công nợ trạm CHỈ tính dòng ghi nợ → báo cáo cấn trừ cuối tháng đặt số đó cạnh cước phải thu
của khách → Bãi không xem được bảng cấn trừ → dọn. Công nợ nhà cung cấp và bảng cấn trừ ở TRANG KẾ TOÁN từ 28/09 (đợt 7d);
danh mục nhà cung cấp (gắn trạm với khách) vẫn ở đây.
"""
import json
import sys
import urllib.error
import urllib.request
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _quy_trinh as Q  # Bãi lập không tiền → KT nhập giá (quy trình 23/09)
import _ke_toan as K       # noqa: E402 — công nợ nhà cung cấp, cấn trừ ở trang kế toán (28/09, đợt 7d)

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}
SO_PHIEU = "NO-TRAM-01/EPL"
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
    print("%s %-60s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def bang(a, b, ten, sai_so=1.0):
    if abs((a or 0) - (b or 0)) > sai_so:
        raise SystemExit("DỪNG: %s — nhận %s, mong %s" % (ten, a, b))
    print("  ✓ %-60s %s" % (ten, a))


def don():
    s, ds = goi("/api/trips", vai="admin")
    for p in [x for x in ds if x["doc_no"] == SO_PHIEU]:
        goi("/api/trips/%s/mo-khoa" % p["id"], {}, vai="admin")
        goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 6 vai")
    don()

    s, kh = goi("/api/customers", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="ketoan")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    s, diem = goi("/api/fuel-places", vai="thabok")
    vn = next((d for d in diem if d.get("country") == "VN" and d.get("owner_type") != "epl"), None)
    if not vn:
        raise SystemExit("DỪNG: không có điểm đổ nào bên Việt Nam — chạy lại seed.py --dung-lai")
    khach = kh[0]

    # ---------------------------------------------------------------- 1. trạm dầu là nhà cung cấp, cấn trừ vào cước khách
    s, ncc = goi("/api/suppliers", vai="ketoancp")
    tram = next((x for x in ncc if x["id"] == vn.get("supplier_id")), None)
    if tram is None:
        s, tram = goi("/api/suppliers", {"name": "Trạm dầu VN (thử)", "item_key": "diesel",
                                         "acct_code": "625/4021", "payment_term": "t_monthly"}, vai="ketoancp")
        phai(s, 200, "Lập nhà cung cấp trạm dầu VN", tram)
    s, g = goi("/api/suppliers/%s" % tram["id"], {"customer_id": khach["id"]}, vai="thabok", method="PUT")
    phai(s, 403, "Bãi gắn khách cấn trừ cho trạm → bị chặn", g)
    s, tram = goi("/api/suppliers/%s" % tram["id"], {"customer_id": khach["id"]}, vai="ketoancp", method="PUT")
    phai(s, 200, "KT Chi phí gắn trạm dầu cấn trừ vào cước %s" % khach["name"], tram)
    assert tram["customer_name"] == khach["name"], tram
    assert "ghi_no_lak" not in tram and "con_no_lak" not in tram, "danh mục bên này không còn cột tiền: %s" % sorted(tram)
    s, g = goi("/api/suppliers/%s/payments" % tram["id"], vai="ketoancp")
    phai(s, 409, "Các lần trả nhà cung cấp bên này → đã dời sang trang kế toán", g)
    s, ncc_kt = K.kt("/api/nha-cung-cap", vai="ketoancp")
    phai(s, 200, "Công nợ nhà cung cấp ở trang kế toán", ncc_kt)
    no_truoc = next(x for x in ncc_kt if x["id"] == tram["id"])["ghi_no_lak"]

    # ---------------------------------------------------------------- 2. phiếu: một dòng trả tiền mặt, một dòng ghi nợ
    s, P = Q.lap_phieu(goi, {
        "doc_no": SO_PHIEU, "kind": "gom", "doc_date": THANG + "-10", "out_date": THANG + "-10",
        "vehicle_id": xe[0]["id"], "driver_id": tx[0]["id"], "customer_id": khach["id"],
        "route_id": tuyen[0]["id"], "goods_type": "iron_ore", "weight_origin": 20, "price": 40, "price_ccy": "USD",
        "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 20}],
        "expenses": [
            {"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 20000, "currency": "LAK",
             "place_id": vn["id"]},                                        # tài xế trả tiền mặt tại trạm
            {"section": "fuel", "item_key": "diesel", "qty": 200, "unit_price": 20000, "currency": "LAK",
             "place_id": vn["id"], "ghi_no": True},                        # trạm ghi nợ
        ],
    }, vai="thabok")
    phai(s, 200, "Bãi lập phiếu: một dòng dầu trả tiền mặt, một dòng ghi nợ trạm", P)
    pid = P["id"]
    dong = [d for d in P["expenses"] if d["section"] == "fuel"]
    assert len(dong) == 2, dong
    assert [d["ghi_no"] for d in dong] == [False, True], "cờ ghi nợ phải giữ đúng từng dòng: %s" % [d["ghi_no"] for d in dong]
    assert all(d["supplier_id"] == tram["id"] for d in dong), \
        "dòng đổ ở trạm ngoài phải mang nhà cung cấp của trạm: %s" % [d["supplier_id"] for d in dong]
    print("  ✓ %-60s" % "Dòng đổ trạm ngoài tự mang nhà cung cấp của trạm")

    # ---------------------------------------------------------------- 2b. tạm ứng KHÔNG gồm dầu trạm ghi nợ (rà giao diện 23/09)
    s, pc = goi("/api/trips/%s/phieu-chi" % pid, vai="admin")
    dau = [d for d in pc["dong"] if d["section"] == "fuel"]
    assert len(dau) == 1 and dau[0]["qty"] == 100, "phiếu tạm ứng chỉ được có 100 lít trả tiền mặt, không có 200 lít ghi nợ: %s" % dau
    print("  ✓ %-60s" % "Phiếu tạm ứng chỉ gồm dầu trả tiền mặt (200 L ghi nợ không tính)")

    # ---------------------------------------------------------------- 3. công nợ trạm chỉ tính dòng ghi nợ
    s, ncc2 = K.kt("/api/nha-cung-cap", vai="ketoancp")
    t2 = next(x for x in ncc2 if x["id"] == tram["id"])
    bang(t2["ghi_no_lak"] - no_truoc, 200 * 20000, "Nợ trạm tăng đúng phần GHI NỢ (dòng tiền mặt không tính)")

    # ---------------------------------------------------------------- 4. bảng cấn trừ cuối tháng
    s, g = K.kt("/api/can-tru?thang=%s" % THANG, vai="thabok")
    phai(s, 403, "Bãi xem bảng cấn trừ (trang kế toán) → bị chặn (tiền bán)", g)
    s, ct = K.kt("/api/can-tru?thang=%s" % THANG, vai="doanhthu")
    o = next((x for x in ct["ds"] if x["customer_id"] == khach["id"]), None)
    assert o, "bảng cấn trừ phải có khách %s: %s" % (khach["name"], ct)
    bang(o["dau_vn_lak"], 200 * 20000, "Bảng cấn trừ: nợ trạm dầu VN của khách trong tháng")
    bang(o["con_thu_lak"], o["cuoc_lak"] - o["can_tru_lak"], "Còn phải thu = cước − cấn trừ")
    assert any(t["name"] == tram["name"] for t in o["tram"]), "phải kể rõ trạm nào: %s" % o["tram"]
    print("  ✓ %-60s %s" % ("Bảng nói rõ trạm nào", o["tram"][0]["name"]))

    # ---------------------------------------------------------------- 5. dọn
    s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử (dọn)", g)
    print("\n✅ NỢ TRẠM DẦU VIỆT NAM: cờ ghi nợ tách đúng khỏi dòng tài xế trả tiền mặt, công nợ trạm")
    print("   chỉ gồm phần ghi nợ, và bảng cấn trừ cuối tháng đặt nó cạnh cước phải thu của khách.")


if __name__ == "__main__":
    main()
