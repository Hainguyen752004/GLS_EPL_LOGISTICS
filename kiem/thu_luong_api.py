# -*- coding: utf-8 -*-
"""Đi trọn luồng nghiệp vụ của bên Lào trên MÁY CHỦ THẬT — đúng thứ tự sheet ໜ້າວຽກ.

    python kiem/thu_luong_api.py [http://127.0.0.1:8010]

  Admin Thà Bốc lập phiếu xe liên kết, nhập 6 mục, gửi kiểm
  → Kế toán Viêng Chăn kiểm I, II, IV; kế toán kho kiểm III; ghi sổ
  → Quỹ Viêng Chăn chi III; tiền mặt lẻ chi IV
  → Bãi báo xe đã tới, nhập cân cuối
  → Kế toán doanh thu lập hoá đơn, ghi thu tiền
  Xen giữa là các bước PHẢI BỊ TỪ CHỐI: sai vai (403), sai bước (409), sửa mục đã khoá (409).

Cuối cùng xoá phiếu thử (admin) để không để rác trong DB.
"""
import json
import sys
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
TOKEN = {}


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau, method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=30) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def dang_nhap(u):
    s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
    assert s == 200, (u, g)
    TOKEN[u] = g["token"]
    return g["user"]["role"]


def phai(s, mong, buoc, g=None):
    assert s == mong, "%s: mong %s, nhận %s — %s" % (buoc, mong, s, json.dumps(g, ensure_ascii=False)[:200])
    print("  ✓ %-58s %s%s" % (buoc, s, (" " + g["detail"]["ma"]) if isinstance(g, dict) and "detail" in g else ""))


def main():
    for u in ("thabok", "ketoan", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        dang_nhap(u)
    print("✓ đăng nhập 7 vai")

    # ---- 0. Dọn phiếu thử còn sót từ lần chạy trước (nếu có)
    s, cu = goi("/api/trips?q=THU-LUONG-01", vai="admin")
    for p in cu:
        if p["doc_no"] == "THU-LUONG-01/EPL":
            goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
            print("  · đã dọn phiếu thử sót lại từ lần trước")

    # ---- 1. Bãi lập phiếu xe liên kết
    s, xe = goi("/api/vehicles", vai="thabok"); lk = next(x for x in xe if x["owner_type"] == "joint")
    s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    s, g = goi("/api/trips", {"doc_no": "THU-LUONG-01/EPL", "company": "joint", "vehicle_id": lk["id"], "driver_id": tx[0]["id"],
                              "customer_id": kh[0]["id"], "doc_date": "2026-09-14", "out_date": "2026-09-14", "origin": "ກາສີ", "destination": "ກາລໍ",
                              "weight_origin": 42, "price_usd": 41, "hire_price_usd": 40.5,
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                                           {"section": "travel", "item_key": "x_toll", "qty": 1, "unit_price": 1833500},
                                           {"section": "travel", "item_key": "x_vn", "qty": 1, "unit_price": 430000, "paid_by_epl": False}]}, vai="thabok")
    phai(s, 200, "Bãi lập phiếu xe liên kết", g); P = g["id"]
    assert g["plate_head"] == lk["plate_head"] and g["owner_name"] == lk["owner_name"], "phải chép biển số và chủ xe từ danh mục"
    assert g["tinh"]["lien_ket"] and g["tinh"]["tien_thue_usd"] == round(42 * 40.5, 2)
    s, g = goi("/api/trips", {"doc_no": "THU-LUONG-01/EPL"}, vai="ketoan"); phai(s, 403, "Kế toán lập phiếu → bị từ chối", g)
    s, g = goi("/api/trips", {"doc_no": "THU-LUONG-01/EPL"}, vai="thabok"); phai(s, 409, "Trùng số phiếu → bị từ chối", g)

    # ---- 2. Gửi kiểm & kiểm
    for m in ("info", "trans", "fuel", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/send" % (P, m), {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục %s" % m, g)
    s, g = goi("/api/trips/%s/sections/repair/send" % P, {}, vai="thabok"); phai(s, 409, "Gửi kiểm mục V rỗng → bị từ chối", g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="ketoan"); phai(s, 403, "Kế toán thu/chi kiểm nhiên liệu → bị từ chối", g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="thabok"); phai(s, 403, "Bãi tự kiểm → bị từ chối", g)
    for m in ("info", "trans", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/verify" % (P, m), {}, vai="ketoan"); phai(s, 200, "Kế toán Viêng Chăn kiểm mục %s" % m, g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="khonl"); phai(s, 200, "Kế toán kho kiểm mục III", g)
    s, g = goi("/api/trips/%s" % P, {"weight_origin": 43}, vai="thabok", method="PUT"); phai(s, 409, "Bãi sửa mục II đã kiểm → bị khoá", g)
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"section": "travel", "item_key": "x_food", "qty": 1, "unit_price": 1}]}, vai="thabok", method="PUT")
    phai(s, 409, "Bãi sửa dòng chi mục IV đã kiểm → bị khoá", g)
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"section": "other", "item_key": "x_misc", "qty": 1, "unit_price": 150000}]}, vai="thabok", method="PUT")
    phai(s, 200, "Bãi thêm dòng mục VI (chưa khoá) → được", g)

    # ---- 3. Ghi sổ & chi
    s, g = goi("/api/trips/%s/sections/travel/pay" % P, {}, vai="quytb"); phai(s, 409, "Chi khi chưa ghi sổ → sai bước", g)
    s, g = goi("/api/trips/%s/sections/travel/book" % P, {}, vai="ketoan"); phai(s, 200, "Kế toán ghi sổ mục IV", g)
    s, g = goi("/api/trips/%s/sections/fuel/book" % P, {}, vai="khonl"); phai(s, 200, "Kế toán kho ghi sổ mục III", g)
    s, g = goi("/api/trips/%s/sections/fuel/pay" % P, {}, vai="quytb"); phai(s, 403, "Tiền mặt lẻ chi nhiên liệu → bị từ chối", g)
    s, g = goi("/api/trips/%s/sections/fuel/pay" % P, {}, vai="quyvc"); phai(s, 200, "Quỹ Viêng Chăn chi mục III", g)
    s, g = goi("/api/trips/%s/sections/travel/pay" % P, {}, vai="quytb"); phai(s, 200, "Tiền mặt lẻ chi mục IV", g)
    assert g["sections"]["fuel"] == "paid" and g["sections"]["travel"] == "paid"

    # ---- 3b. Trên đường: tới điểm theo tuyến, sửa xe lấy phụ tùng từ kho / mua ngoài → rơi vào mục V
    s, tuyen = goi("/api/routes", vai="thabok"); r0 = tuyen[0]
    s, g = goi("/api/trips/%s" % P, {"route_id": r0["id"], "origin": "", "destination": ""}, vai="thabok", method="PUT")
    phai(s, 409, "Bãi gắn tuyến khi mục II đã kiểm → bị khoá", g)
    s, g = goi("/api/trips/%s/sections/trans/return" % P, {}, vai="ketoan"); phai(s, 200, "Kế toán trả lại mục II để Bãi gắn tuyến", g)
    s, g = goi("/api/trips/%s" % P, {"route_id": r0["id"]}, vai="thabok", method="PUT"); phai(s, 200, "Bãi gắn tuyến %s" % r0["name"], g)
    assert len(g["route_stops"]) == r0["so_diem"], "phiếu phải mang đủ điểm của tuyến"
    s, g = goi("/api/trips/%s/sections/trans/send" % P, {}, vai="thabok"); s, g = goi("/api/trips/%s/sections/trans/verify" % P, {}, vai="ketoan")
    phai(s, 200, "Kiểm lại mục II sau khi gắn tuyến", g)
    s, g = goi("/api/trips/%s/events" % P, {"kind": "arrive_stop", "stop_seq": 2, "note": "về bãi"}, vai="thabok"); phai(s, 200, "Bãi ghi xe tới điểm 2", g)
    assert g["stop_reached"] == 2 and g["transport_status"] == "transit", g["transport_status"]
    s, g = goi("/api/trips/%s/events" % P, {"kind": "arrive_stop", "stop_seq": 99}, vai="thabok"); phai(s, 422, "Tới điểm không có trên tuyến → bị từ chối", g)
    s, parts = goi("/api/parts", vai="thabok"); pt = next(x for x in parts if x["qty"] >= 1); ton = pt["qty"]
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "incident_type": "breakdown", "stop_seq": 3, "note": "thử: hỏng bầu hơi",
                                              "repair": {"source": "kho", "part_id": pt["id"], "qty": 1}}, vai="thabok")
    phai(s, 200, "Sửa xe lấy phụ tùng từ KHO → dòng mục V, trừ tồn", g)
    d_kho = [e for e in g["expenses"] if e["section"] == "repair" and e["source"] == "kho"][-1]
    assert d_kho["acct_code"] == "4022/371" and d_kho["stock_move_id"], d_kho          # xe liên kết → 4022, kho → /371
    assert g["sections"]["repair"] == "entered", "mục V phải về 'đã nhập' để kiểm lại"
    s, parts2 = goi("/api/parts", vai="thabok"); assert next(x for x in parts2 if x["id"] == pt["id"])["qty"] == ton - 1, "tồn phụ tùng phải giảm 1"
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "repair": {"source": "mua", "item_name": "thử: vá lốp garage", "qty": 1, "unit_price": 300000}}, vai="thabok")
    phai(s, 200, "Sửa xe MUA NGOÀI → dòng mục V, định khoản …/402", g)
    assert [e for e in g["expenses"] if e["section"] == "repair"][-1]["acct_code"] == "4022/402"
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "repair": {"source": "kho", "part_id": pt["id"], "qty": 10 ** 6}}, vai="thabok"); phai(s, 409, "Xuất quá tồn kho → bị từ chối", g)
    s, g = goi("/api/trips/%s/events" % P, {"kind": "note", "note": "x"}, vai="ketoan"); phai(s, 403, "Kế toán ghi diễn biến → bị từ chối", g)
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"section": "repair", "item_name": "xoá hết"}]}, vai="thabok", method="PUT")
    phai(s, 409, "Bãi xoá dòng đã xuất kho khỏi phiếu → bị từ chối", g)
    # Sửa xe khai từ màn theo dõi đã đặt mục V ở "đã nhập" — kế toán kiểm thẳng, không cần Bãi gửi nữa
    s, g = goi("/api/trips/%s/sections/repair/send" % P, {}, vai="thabok"); phai(s, 409, "Mục V đã 'đã nhập' sẵn → gửi lại là sai bước", g)
    for hd, v in (("verify", "ketoan"), ("book", "ketoan"), ("pay", "quytb")):
        s, g = goi("/api/trips/%s/sections/repair/%s" % (P, hd), {}, vai=v); phai(s, 200, "Mục V: %s (%s)" % (hd, v), g)
    s, kho = goi("/api/fuel-moves", vai="khonl")
    assert any(r["doc_no"] == "THU-LUONG-01/EPL" and r["kind"] == "out" for r in kho["rows"]), "ghi sổ mục III phải sinh dòng xuất kho nhiên liệu theo phiếu"
    print("  ✓ ghi sổ mục III đã sinh dòng xuất kho nhiên liệu THU-LUONG-01/EPL")

    # ---- 4. Xe về, cân cuối, hoá đơn, thu tiền
    s, g = goi("/api/trips/%s/invoice" % P, {}, vai="thabok"); phai(s, 403, "Bãi lập hoá đơn → bị từ chối", g)
    s, g = goi("/api/trips/%s/transport-status" % P, {"status": "arrived", "weight_dest": 40.5, "back_date": "2026-09-16"}, vai="thabok")
    phai(s, 200, "Bãi báo xe đã tới, cân cuối 40,5 t", g)
    # Tính lại đúng cách trên giấy: từng khoản làm tròn 2 số lẻ rồi mới trừ — như máy chủ và như Excel.
    thue = round(40.5 * 40.5, 2); phi = round(thue * 0.02, 2); vuot = 0.5
    # EPL đã ứng = dầu kho 100 L + cao tốc + mục VI 150.000 + hai khoản sửa xe vừa khai (phụ tùng kho + vá lốp) ÷ tỷ giá.
    # Dòng x_vn "chủ xe tự trả" không tính. Lấy tổng chi từ máy chủ rồi kiểm lại từng phần.
    chi = g["tinh"]["chi"]
    assert chi["fuel"] == 100 * 30000 and chi["travel"] == 1833500 and chi["other"] == 150000, chi
    assert chi["repair"] == round(pt["unit_price"] * 1 + 300000), (chi["repair"], pt["unit_price"])
    ung = round(g["tinh"]["tong_chi_lak"] / 22000, 2)
    assert g["tinh"]["tan_tinh"] == 40.5, g["tinh"]
    assert g["tinh"]["tra_chu_xe_usd"] == round(thue - phi - vuot - ung, 2), (g["tinh"]["tra_chu_xe_usd"], thue, phi, vuot, ung)
    s, g = goi("/api/trips/%s/finance-status" % P, {"status": "paid"}, vai="doanhthu"); phai(s, 409, "Ghi thu trước khi có hoá đơn → sai bước", g)
    # ---- 4b. Bước 14: kế toán rà lại rồi KHOÁ. Chưa khoá thì chưa có hoá đơn; khoá rồi Bãi hết sửa.
    s, g = goi("/api/trips/%s/invoice" % P, {}, vai="doanhthu"); phai(s, 409, "Lập hoá đơn khi phiếu chưa khoá → sai bước", g)
    s, g = goi("/api/trips/%s/khoa" % P, {}, vai="thabok"); phai(s, 403, "Bãi khoá phiếu → bị từ chối", g)
    s, g = goi("/api/trips/%s/kiem-lai" % P, vai="ketoan"); phai(s, 200, "Kế toán bấm Kiểm lại → bảng cảnh báo", g)
    ma_cb = [x["ma"] for x in g["canh_bao"]]
    assert "THIEU_PHIEU_QUANG" in ma_cb and "THIEU_KM_VE" in ma_cb, "phải cảnh báo thiếu phiếu quặng và thiếu km về: %s" % ma_cb
    s, g = goi("/api/trips/%s/khoa" % P, {}, vai="ketoan"); phai(s, 409, "Khoá khi còn cảnh báo mà chưa xác nhận → chặn", g)
    s, g = goi("/api/trips/%s/khoa" % P, {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "Kế toán xác nhận khoá phiếu", g)
    assert g["locked"] and g["locked_by"], g.get("locked")
    s, g = goi("/api/trips/%s" % P, {"odo_back": 9999}, vai="thabok", method="PUT"); phai(s, 409, "Bãi sửa phiếu đã khoá → bị chặn", g)
    s, g = goi("/api/trips/%s/tra-chu-xe" % P, {}, vai="thabok"); phai(s, 403, "Bãi trả chủ xe → bị từ chối", g)
    s, g = goi("/api/trips/%s/invoice" % P, {}, vai="doanhthu"); phai(s, 200, "Kế toán doanh thu lập hoá đơn", g)
    s, g = goi("/api/trips/%s/finance-status" % P, {"status": "paid"}, vai="doanhthu"); phai(s, 200, "Kế toán doanh thu ghi đã thu tiền", g)
    assert g["invoiced"] and g["finance_status"] == "paid"
    # ---- 4c. Xe liên kết: quỹ trả chủ xe một lần → chứng từ PC_CX
    s, g = goi("/api/trips/%s/tra-chu-xe" % P, {}, vai="quytb"); phai(s, 200, "Quỹ trả chủ xe liên kết", g)
    assert g["owner_paid"] and g["owner_paid_usd"] == g["tinh"]["tra_chu_xe_usd"], (g["owner_paid_usd"], g["tinh"]["tra_chu_xe_usd"])
    s, g2 = goi("/api/trips/%s/tra-chu-xe" % P, {}, vai="quytb"); phai(s, 409, "Trả chủ xe lần hai → từ chối", g2)
    s, so = goi("/api/chung-tu?trip_id=%s&loai=PC_CX" % P, vai="ketoan"); phai(s, 200, "Sổ chứng từ có tờ PC_CX", so)
    assert len(so["ds"]) == 1 and so["ds"][0]["tien_te"] == "USD" and so["ds"][0]["no"] == "4022", so["ds"]
    s, g3 = goi("/api/trips/%s/mo-khoa" % P, vai="ketoan", method="POST"); phai(s, 409, "Mở khoá sau khi đã xuất hoá đơn → chặn", g3)
    s, g = goi("/api/trips/%s" % P, vai="admin")     # lấy lại phiếu đầy đủ để soi nhật ký
    assert any(l["action"] == "a_invoice" for l in g["logs"]) and any(l["action"] == "sec_fuel:pay" for l in g["logs"]), "nhật ký phải ghi từng bước"
    print("  ✓ nhật ký có %d dòng, đủ các bước" % len(g["logs"]))

    # ---- 5. Báo cáo thấy phiếu này
    s, g = goi("/api/bao-cao/xe-lien-ket?thang=2026-09", vai="doanhthu"); assert any(p["id"] == P for p in g), "báo cáo xe liên kết phải có phiếu thử"
    s, g = goi("/api/bao-cao/theo-doi?thang=2026-09", vai="doanhthu"); assert any(p["id"] == P for p in g)
    print("  ✓ báo cáo xe liên kết và theo dõi đều thấy phiếu thử")

    # ---- 6. Dọn — trả lại kho đúng những gì phiếu thử đã lấy, rồi xoá phiếu
    s, g = goi("/api/trips/%s" % P, vai="thabok", method="DELETE"); phai(s, 409, "Bãi xoá phiếu đã duyệt → bị từ chối", g)
    s, g = goi("/api/parts/%s/moves" % pt["id"], {"kind": "in", "qty": 1, "note": "hoàn trả sau thử luồng"}, vai="thabok"); phai(s, 200, "Trả lại 1 phụ tùng vào kho", g)
    s, kho = goi("/api/fuel-moves", vai="khonl")
    for r in kho["rows"]:
        if r["doc_no"] == "THU-LUONG-01/EPL":
            goi("/api/fuel-moves/%s" % r["id"], vai="khonl", method="DELETE")
    print("  ✓ đã xoá dòng xuất kho nhiên liệu của phiếu thử")
    s, g = goi("/api/trips/%s" % P, vai="admin", method="DELETE"); phai(s, 200, "Admin xoá phiếu thử (dọn)", g)
    print("\nTHỬ LUỒNG API: ĐẠT — 7 vai · 6 mục · 5 bước duyệt · 10 chỗ từ chối đúng")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("\nTHỬ LUỒNG API: HỎNG —", e); sys.exit(1)
