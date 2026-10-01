# -*- coding: utf-8 -*-
"""Câu trả lời của anh Khampla 23/09 — kho dầu theo từng kho, giá BÌNH QUÂN, dầu mua Việt Nam đi qua KHO XE, chuyển kho.

    python kiem/thu_kho_xe_23_09.py [http://127.0.0.1:8011]

Đúng ví dụ A3 của anh ấy: mua 1.000 lít ở Việt Nam, nhập vào kho xe → phiếu xuất xe lấy 600 lít → 400 lít còn
lại chuyển về kho Thà Bốc. Kèm: Bãi không ghi sổ kho, không thấy giá dầu; Bãi không gửi được giá cước / giá thuê.
Phiếu thử và các dòng sổ kho thử được xoá khi xong; tờ chứng từ đã đẩy thì giữ.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
TK = {}
SO = "KHOXE-%s/EPL" % time.strftime("%d%H%M%S")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — kho nhiên liệu ở trang kế toán (28/09)



def goi(duong, body=None, vai="admin", method=None):
    du = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + TK.get(vai, "")})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def phai(s, mong, buoc, g=None):
    assert s == mong, "%s: mong %s, nhận %s — %s" % (buoc, mong, s, json.dumps(g, ensure_ascii=False)[:300])
    ma = g["detail"]["ma"] if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""
    print("  ✓ %-64s %s %s" % (buoc, s, ma))


def kho(vai="khonl"):
    s, g = K.kt("/api/nhien-lieu", vai=vai)          # sổ dầu ở trang kế toán (28/09)
    assert s == 200, (s, g)
    return {k["code"]: k for k in g["kho"]}, g


def main():
    for u in ("admin", "thabok", "ketoan", "khonl", "quyvc"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); assert s == 200, (u, g)
        TK[u] = g["token"]
    k0, _ = kho()
    XE, TB = k0["KHO-XE-VN"], k0["KHO-TB"]
    # 01/10 kho tạm chặn cấp / xoá quá tồn: bài NHẬP TRƯỚC 1.000 L vào kho xe rồi mới cấp 600; cuối bài xoá phiếu chuyển 400 L về
    # Thà Bốc — làm được chỉ khi hai kho không âm từ trước (xoá phần nhận chuyển mà kho đã âm thì kho tạm chặn, đúng luật)
    for k in (XE, TB):
        if k["ton_lit"] < -0.001:
            raise SystemExit("DỪNG: kho %s đang âm %s L trên máy thử — xử lý số âm trước (xoá phiếu thử cũ / phiếu nhập thật)."
                             % (k["code"], k["ton_lit"]))
    print("  · kho xe: %s L · %s LAK/L   |   Thà Bốc: %s L · %s LAK/L" % (XE["ton_lit"], XE["gia_bq"], TB["ton_lit"], TB["gia_bq"]))
    s, ncc = goi("/api/suppliers", vai="khonl")
    tram_vn = next((x for x in ncc if "VN" in (x.get("name") or "") or "ຫວຽດນາມ" in (x.get("name") or "")), ncc[0] if ncc else None)

    # ---- 1. Bãi không ghi sổ kho dầu, không thấy giá dầu (A2)
    s, g = goi("/api/fuel-moves", {"kind": "in", "place_id": XE["id"], "qty_l": 10, "unit_price": 1}, vai="khonl")
    phai(s, 409, "Trang điều xe không còn ghi sổ kho dầu (đã dời sang kế toán)", g)
    s, g = K.kt("/api/nhien-lieu", {"kind": "in", "place_id": XE["id"], "qty_l": 10, "unit_price": 1}, vai="thabok")
    phai(s, 403, "Bãi nhập kho dầu ở trang kế toán → bị từ chối (việc KT kho xăng dầu)", g)
    s, g = K.kt("/api/nhien-lieu", vai="thabok")
    assert "gia_bq" not in g and all("gia_bq" not in k for k in g["kho"]) and all("unit_price" not in r for r in g["rows"]), \
        "Bãi xem sổ kho: có số lít, không có giá"
    print("  ✓ %-64s" % "Bãi xem sổ kho dầu: thấy số lít, không thấy giá")

    # ---- 2. mua 1.000 lít ở Việt Nam, nhập vào KHO XE (VND, tỷ giá lúc nhập)
    s, g = K.kt("/api/nhien-lieu", {"kind": "in", "place_id": XE["id"], "qty_l": 1000, "unit_price": 26000, "currency": "VND",
                                    "rate_to_lak": 1.2, "doc_no": "PO-" + SO, "supplier_id": tram_vn["id"] if tram_vn else None,
                                    "note": "thử A3: mua dầu Việt Nam"}, vai="khonl")
    phai(s, 200, "KT kho xăng dầu nhập 1.000 L mua ở Việt Nam vào kho xe (26.000 VND)", g)
    k1, so1 = kho()
    gia_nhap = 26000 * 1.2
    mong = (XE["ton_lit"] * XE["gia_bq"] + 1000 * gia_nhap) / (XE["ton_lit"] + 1000) if XE["ton_lit"] > 0 else gia_nhap
    assert abs(k1["KHO-XE-VN"]["ton_lit"] - (XE["ton_lit"] + 1000)) < 0.01 and abs(k1["KHO-XE-VN"]["gia_bq"] - mong) < 0.02, (k1["KHO-XE-VN"], mong)
    nhap = next(r for r in so1["rows"] if r["doc_no"] == "PO-" + SO)
    pnk = next(c for c in K.to_kho("PO-" + SO, "PNK_NL"))                 # tờ nhập kho sinh ngay ở trang kế toán
    assert pnk["currency"] == "VND" and round(pnk["amount_lak"]) == round(1000 * gia_nhap) and pnk["debit"] == "1371" and pnk["credit"] == "4021", pnk
    print("  ✓ %-64s %s LAK · Nợ %s / Có %s" % ("phiếu nhập kho quy LAK theo tỷ giá lúc nhập", format(round(pnk["amount_lak"]), ","), pnk["debit"], pnk["credit"]))
    gia_xe = k1["KHO-XE-VN"]["gia_bq"]

    # ---- 3. phiếu xuất xe lấy 600 lít từ kho xe — giá tự là bình quân của kho xe
    s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    s, g = goi("/api/trips", {"doc_no": SO, "company": "EPL", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "price": 40}, vai="thabok")
    phai(s, 403, "Bãi gửi giá cước khi lập phiếu → bị từ chối (KT Viêng Chăn nhập, A2 · C4.1)", g)
    s, p = goi("/api/trips", {"doc_no": SO, "company": "EPL", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
                              "doc_date": time.strftime("%Y-%m-%d"), "out_date": time.strftime("%Y-%m-%d"), "weight_origin": 40,
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 600, "place_id": XE["id"], "unit_price": 1}]}, vai="thabok")
    phai(s, 200, "Bãi lập phiếu: 600 L lấy ở kho xe (gửi kèm giá 1 — phải bị bỏ qua)", p)
    P = p["id"]
    s, pk = goi("/api/trips/%s" % P, vai="khonl")
    d = next(e for e in pk["expenses"] if e["section"] == "fuel")
    assert d["source"] == "kho" and d["currency"] == "LAK" and abs(d["unit_price"] - gia_xe) < 0.02, (d, gia_xe)
    print("  ✓ %-64s %s LAK/L" % ("dòng dầu kho xe tự mang giá bình quân kho xe", format(round(d["unit_price"]), ",")))
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"id": d["id"], "section": "fuel", "unit_price": 5}]}, vai="khonl", method="PUT")
    s, pk = goi("/api/trips/%s" % P, vai="khonl")
    assert abs(next(e for e in pk["expenses"] if e["section"] == "fuel")["unit_price"] - gia_xe) < 0.02, "dòng kho không ai gõ giá được"
    print("  ✓ %-64s" % "kế toán gõ giá dòng lấy từ kho → bị bỏ qua (giá kho là bình quân)")
    s, g = goi("/api/trips/%s/sections/fuel/send" % P, {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục III", g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="khonl"); phai(s, 200, "KT kho xăng dầu kiểm mục III", g)
    # dầu kho chỉ rời kho theo phiếu ĐỀ NGHỊ đã cấp (chủ dự án 30/09): Bãi in đề nghị → cấp dầu → mới ghi sổ mục III
    s, v = goi("/api/trips/%s/vouchers" % P, {"kind": "fuel"}, vai="thabok"); phai(s, 200, "Bãi in phiếu đề nghị xuất kho nhiên liệu", v)
    for x in v:
        s, g = goi("/api/vouchers/%s/cap" % x["id"], {"qty": x["qty_l"]}, vai="khonl"); phai(s, 200, "Cấp dầu theo " + x["doc_no"], g)
    s, g = goi("/api/trips/%s/sections/fuel/book" % P, {}, vai="khonl"); phai(s, 200, "KT kho xăng dầu ghi sổ mục III (dầu đã xuất lúc cấp)", g)
    k2, so2 = kho()
    ra = next(r for r in so2["rows"] if str(r["doc_no"]).startswith("PLNL-" + SO) and r["kind"] == "out")   # xuất theo phiếu đề nghị
    assert ra["place_id"] == XE["id"] and ra["qty_out"] == 600 and abs(ra["unit_cost_lak"] - gia_xe) < 0.02, ra
    assert abs(k2["KHO-XE-VN"]["ton_lit"] - (XE["ton_lit"] + 400)) < 0.01, k2["KHO-XE-VN"]
    pxk = next(c for c in K.to_kho(SO, "PXK_NL") if c["trip_no"] == SO)
    assert round(pxk["amount_lak"]) == round(600 * gia_xe) and pxk["debit"] == "625" and pxk["credit"] == "1371", pxk
    print("  ✓ %-64s %s LAK · Nợ %s / Có %s" % ("xuất 600 L đúng kho xe, đúng giá bình quân", format(round(pxk["amount_lak"]), ","), pxk["debit"], pxk["credit"]))

    # ---- 4. chuyển 400 lít còn lại về kho Thà Bốc
    s, g = K.kt("/api/nhien-lieu/chuyen-kho", {"from_place_id": XE["id"], "to_place_id": XE["id"], "qty_l": 1}, vai="khonl")
    phai(s, 422, "Chuyển kho vào chính nó → bị từ chối", g)
    s, g = K.kt("/api/nhien-lieu/chuyen-kho", {"from_place_id": XE["id"], "to_place_id": TB["id"], "qty_l": 10 ** 6}, vai="khonl")
    phai(s, 409, "Chuyển quá tồn → bị từ chối", g)
    s, g = K.kt("/api/nhien-lieu/chuyen-kho", {"from_place_id": XE["id"], "to_place_id": TB["id"], "qty_l": 400}, vai="thabok")
    phai(s, 403, "Bãi chuyển kho → bị từ chối", g)
    tb_truoc = kho()[0]["KHO-TB"]
    s, ck = K.kt("/api/nhien-lieu/chuyen-kho", {"from_place_id": XE["id"], "to_place_id": TB["id"], "qty_l": 400, "note": "thử A3"}, vai="khonl")
    phai(s, 200, "KT kho xăng dầu chuyển 400 L kho xe → Thà Bốc (%s)" % ck.get("transfer_no"), ck)
    k3, so3 = kho()
    assert abs(k3["KHO-XE-VN"]["ton_lit"] - XE["ton_lit"]) < 0.01, "kho xe về đúng số trước khi mua: %s" % k3["KHO-XE-VN"]
    assert abs(k3["KHO-TB"]["ton_lit"] - (tb_truoc["ton_lit"] + 400)) < 0.01, k3["KHO-TB"]
    mong_tb = (tb_truoc["ton_lit"] * tb_truoc["gia_bq"] + 400 * gia_xe) / (tb_truoc["ton_lit"] + 400) if tb_truoc["ton_lit"] > 0 else gia_xe
    assert abs(k3["KHO-TB"]["gia_bq"] - mong_tb) < 0.05, (k3["KHO-TB"]["gia_bq"], mong_tb)
    print("  ✓ %-64s TB %s L · bình quân %s → %s" % ("tồn và giá bình quân hai kho đúng sau chuyển", k3["KHO-TB"]["ton_lit"],
                                                        format(round(tb_truoc["gia_bq"]), ","), format(round(k3["KHO-TB"]["gia_bq"]), ",")))
    to = [c for c in K.to_kho("", "CK_NL") if (c.get("lines") or {}).get("transfer_no") == ck["transfer_no"]]
    assert len(to) == 1 and not to[0]["debit"] and not to[0]["credit"] and not to[0]["entry_id"], "chuyển kho: MỘT tờ CK_NL, không định khoản (vẫn là 1371): %s" % to
    print("  ✓ %-64s %s" % ("một tờ chuyển kho, không sinh bút toán", to[0]["ref"]))

    # ---- 5. dọn: xoá phiếu chuyển (cả hai dòng), dòng xuất theo phiếu, phiếu thử, dòng nhập
    dong_ck = [r for r in so3["rows"] if r.get("transfer_no") == ck["transfer_no"]]
    assert len(dong_ck) == 2, dong_ck
    s, g = K.kt("/api/nhien-lieu/%s" % dong_ck[0]["id"], vai="khonl", method="DELETE"); phai(s, 200, "Xoá phiếu chuyển kho → xoá cả hai dòng", g)
    assert not [r for r in g["rows"] if r.get("transfer_no") == ck["transfer_no"]], "còn dòng của phiếu chuyển"
    s, g = K.kt("/api/nhien-lieu/%s" % ra["id"], vai="khonl", method="DELETE")
    phai(s, 409, "Xoá tay dòng xuất của phiếu ở kho → chặn (thuộc phiếu bên điều xe)", g)
    s, g = goi("/api/trips/%s" % P, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử → dầu mục III tự về kho", g)
    assert not [r for r in kho()[1]["rows"] if r["id"] == ra["id"]], "xoá phiếu phải trả dầu về kho (dòng xuất rút đi)"
    assert not [c for c in K.to_kho(SO, "PXK_NL") if c["trip_no"] == SO], "xoá phiếu phải rút tờ PXK_NL"
    s, g = K.kt("/api/nhien-lieu/%s" % nhap["id"], vai="khonl", method="DELETE"); phai(s, 200, "Xoá dòng nhập thử", g)
    k9, _ = kho()
    assert abs(k9["KHO-XE-VN"]["ton_lit"] - XE["ton_lit"]) < 0.01 and abs(k9["KHO-TB"]["ton_lit"] - TB["ton_lit"]) < 0.01, (k9["KHO-XE-VN"], k9["KHO-TB"])
    print("\n✅ KHO XE & CHUYỂN KHO (A3 · C5.2 · C5.3): nhập VND quy LAK lúc nhập · xuất cho xe theo bình quân kho ·"
          " chuyển phần dư về Thà Bốc · Bãi không ghi sổ kho, không thấy giá · dọn sạch.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("\nHỎNG —", e); sys.exit(1)
