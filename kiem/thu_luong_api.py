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
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _quy_trinh as Q
import _ke_toan as K       # kho phụ tùng ở trang kế toán (28/09)

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
    for u in ("totsua", "khopt", "thabok", "ketoan", "ketoancp", "khonl", "quyvc", "quytb", "doanhthu", "admin"):
        dang_nhap(u)
    print("✓ đăng nhập 7 vai")

    # ---- 0. Dọn phiếu thử còn sót từ lần chạy trước (nếu có)
    for so_thu in ("01", "02"):
        s, cu = goi("/api/trips?q=THU-LUONG-" + so_thu, vai="admin")
        for p in cu:
            if p["doc_no"] == "THU-LUONG-%s/EPL" % so_thu:
                goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
                print("  · đã dọn phiếu thử %s sót lại từ lần trước" % so_thu)

    # dòng giá thử K3 sót lại (lần chạy trước hỏng giữa đường)
    s, kh0 = goi("/api/customers", vai="ketoan")
    for k in kh0:
        s, ds = goi("/api/customers/%s/bang-gia" % k["id"], vai="ketoan")
        for r in ds:
            if r.get("note") == "thử K3":
                goi("/api/bang-gia/%s" % r["id"], vai="ketoan", method="DELETE"); print("  · đã dọn dòng giá thử sót lại")

    # ---- 1. Bãi lập phiếu xe liên kết
    s, xe = goi("/api/vehicles", vai="thabok"); lk = next(x for x in xe if x["owner_type"] == "joint")
    s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    # Bãi lập (số lượng) → KT VC nhập giá cước/giá thuê → người kiểm mục nhập đơn giá (kiem/_quy_trinh.py)
    s, g = Q.lap_phieu(goi, {"doc_no": "THU-LUONG-01/EPL", "company": "joint", "vehicle_id": lk["id"], "driver_id": tx[0]["id"],
                              "customer_id": kh[0]["id"], "doc_date": "2026-09-14", "out_date": "2026-09-14", "origin": "ກາສີ", "destination": "ກາລໍ",
                              "weight_origin": 42, "price": 41, "price_ccy": "USD", "hire_price": 40.5, "hire_ccy": "USD", "odo_out": 1000,   # chủ xe mẫu ký thuê bằng Kíp; phiếu thử này thoả thuận USD nên ghi rõ
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                                           {"section": "travel", "item_key": "x_toll", "qty": 1, "unit_price": 1833500},
                                           {"section": "travel", "item_key": "x_vn", "qty": 1, "unit_price": 430000, "paid_by_epl": False}]}, vai="thabok")
    phai(s, 200, "Bãi lập phiếu xe liên kết", g); P = g["id"]
    s, g = goi("/api/trips/%s" % P, vai="thabok")
    assert g["plate_head"] == lk["plate_head"] and g["owner_name"] == lk["owner_name"], "phải chép biển số và chủ xe từ danh mục"
    # Bãi KHÔNG nhận tiền bán: máy chủ bỏ hẳn khoá, không phải giao diện che (nợ kỹ thuật 3.1).
    assert "price" not in g and "hire_price" not in g, "Bãi không được nhận đơn giá cước / giá thuê"
    assert "tien_thue" not in g["tinh"] and "lai" not in g["tinh"], "Bãi không được nhận tiền thuê / lãi"
    print("  \u2713 %-58s" % "Bãi gọi /api/trips: gói trả về không có khoá tiền bán nào")
    s, gk = goi("/api/trips/%s" % P, vai="ketoan")
    assert gk["tinh"]["lien_ket"] and gk["tinh"]["tien_thue"] == round(42 * 40.5, 2)
    s, g = goi("/api/trips", {"doc_no": "THU-LUONG-01/EPL"}, vai="ketoan"); phai(s, 403, "Kế toán lập phiếu → bị từ chối", g)
    s, g = goi("/api/trips", {"doc_no": "THU-LUONG-01/EPL"}, vai="thabok"); phai(s, 409, "Trùng số phiếu → bị từ chối", g)
    # C3.7 (anh Khampla): số phiếu quặng do KẾ TOÁN nhập khi nhận giấy; Bãi chỉ đính kèm ảnh.
    s, g = goi("/api/trips/%s" % P, {"ore_bill_no": "HR-9999"}, vai="thabok", method="PUT"); phai(s, 403, "Bãi gõ số phiếu quặng → bị từ chối", g)
    s, g = goi("/api/trips/%s" % P, {"ore_bill_no": "HR-9999", "ore_bill_date": "2026-09-14"}, vai="ketoan", method="PUT"); phai(s, 200, "Kế toán nhập số phiếu quặng", g)
    assert g["ore_bill_no"] == "HR-9999", g["ore_bill_no"]
    s, g = goi("/api/trips/%s" % P, {"ore_bill_no": "HR-9999", "weight_origin": 42}, vai="thabok", method="PUT"); phai(s, 200, "Bãi lưu lại phiếu (số quặng không đổi) → vẫn lưu được", g)

    # ---- 1b. K3: bảng giá khách × tuyến — kế toán đặt giá, Bãi lập phiếu KHÔNG gửi giá, máy tự điền
    s, tuyen = goi("/api/routes", vai="ketoan"); T = tuyen[0]["id"]
    s, g = goi("/api/customers/%s/bang-gia" % kh[0]["id"], vai="thabok"); phai(s, 403, "Bãi xem bảng giá → bị từ chối (Bãi không thấy tiền)", g)
    s, g = goi("/api/customers/%s/bang-gia" % kh[0]["id"], {"route_id": T, "price": 39, "hire_price": 38.5, "valid_from": "2026-01-01"}, vai="thabok")
    phai(s, 403, "Bãi đặt giá → bị từ chối", g)
    s, g = goi("/api/customers/%s/bang-gia" % kh[0]["id"], {"route_id": T, "price": 0}, vai="ketoan"); phai(s, 422, "Giá 0 → bị từ chối", g)
    s, gia = goi("/api/customers/%s/bang-gia" % kh[0]["id"], {"route_id": T, "price": 39, "hire_price": 38.5, "valid_from": "2026-01-01", "note": "thử K3"}, vai="ketoan")
    phai(s, 200, "Kế toán đặt giá 39 USD/t cho khách × tuyến", gia)
    s, g = goi("/api/bang-gia/tra?customer_id=%s&route_id=%s&ngay=2026-09-14" % (kh[0]["id"], T), vai="ketoan"); phai(s, 200, "Hỏi giá", g)
    assert g.get("price") == 39, "hỏi giá phải trả dòng mới nhất còn hiệu lực (39): %s" % g
    s, g = goi("/api/bang-gia/tra?customer_id=%s&route_id=%s&ngay=2025-12-31" % (kh[0]["id"], T), vai="ketoan"); phai(s, 200, "Hỏi giá trước ngày hiệu lực", g)
    assert not g.get("price") or g.get("id") != gia["id"], "trước ngày hiệu lực không được lấy dòng giá này"
    s, p2 = goi("/api/trips", {"doc_no": "THU-LUONG-02/EPL", "company": "joint", "vehicle_id": lk["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
                               "route_id": T, "doc_date": "2026-09-14", "out_date": "2026-09-14", "weight_origin": 40}, vai="thabok")
    phai(s, 200, "Bãi lập phiếu có khách + tuyến, không gửi giá", p2)
    assert "price" not in p2, "gói trả cho Bãi không được có đơn giá, dù máy đã tự điền vào phiếu"
    s, p2k = goi("/api/trips/%s" % p2["id"], vai="ketoan")
    assert p2k["price"] == 39 and p2k["hire_price"] == 38.5, "máy phải tự điền giá 39 và giá thuê 38.5 từ bảng giá: %s / %s" % (p2k["price"], p2k["hire_price"])
    s, g = goi("/api/trips/%s" % p2["id"], {"price": 45}, vai="ketoan", method="PUT"); phai(s, 200, "Kế toán sửa giá khác hợp đồng", g)
    assert g["price"] == 45, "giá kế toán gõ phải được giữ, không bị bảng giá ghi đè"
    s, g = goi("/api/trips/%s" % p2["id"], vai="admin", method="DELETE"); phai(s, 200, "Dọn phiếu thử 02", g)
    s, g = goi("/api/bang-gia/%s" % gia["id"], vai="ketoan", method="DELETE"); phai(s, 200, "Dọn dòng giá thử", g)
    print("  ✓ K3 bảng giá: Bãi không thấy · kế toán đặt giá · phiếu tự điền 39/38.5 · kế toán sửa được · ngày hiệu lực đúng")

    # ---- 2. Gửi kiểm & kiểm
    for m in ("info", "trans", "fuel", "travel"):
        s, g = goi("/api/trips/%s/sections/%s/send" % (P, m), {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục %s" % m, g)
    s, g = goi("/api/trips/%s/sections/repair/send" % P, {}, vai="thabok"); phai(s, 403, "Bãi gửi kiểm mục V → bị từ chối (việc tổ sửa chữa, C1.2)", g)
    s, g = goi("/api/trips/%s/sections/repair/send" % P, {}, vai="totsua"); phai(s, 409, "Tổ sửa chữa gửi kiểm mục V rỗng → bị từ chối", g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="ketoan"); phai(s, 403, "Kế toán thu/chi kiểm nhiên liệu → bị từ chối", g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="thabok"); phai(s, 403, "Bãi tự kiểm → bị từ chối", g)
    # Bảng Nhiệm Vụ của khách: KT Thu/Chi VC xác nhận I–II; KT Chi phí VC xác nhận IV–VI. Không chéo.
    s, g = goi("/api/trips/%s/sections/travel/verify" % P, {}, vai="ketoan"); phai(s, 403, "KT Thu/Chi kiểm mục IV → bị từ chối (việc của KT Chi phí)", g)
    s, g = goi("/api/trips/%s/sections/info/verify" % P, {}, vai="ketoancp"); phai(s, 403, "KT Chi phí kiểm mục I → bị từ chối (việc của KT Thu/Chi)", g)
    for m in ("info", "trans"):
        s, g = goi("/api/trips/%s/sections/%s/verify" % (P, m), {}, vai="ketoan"); phai(s, 200, "KT Thu/Chi Viêng Chăn kiểm mục %s" % m, g)
    s, g = goi("/api/trips/%s/sections/travel/verify" % P, {}, vai="ketoancp"); phai(s, 200, "KT Chi phí VC kiểm mục IV", g)
    # xe thuê: dầu kho EPL ứng là XUẤT BÁN cho chủ xe — KT kho gõ giá bán trước khi kiểm (chủ dự án 29/09)
    s, pk = goi("/api/trips/%s" % P, vai="khonl")
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"id": e["id"], "section": "fuel", "sale_price": 31000}
                                                  for e in pk["expenses"] if e["section"] == "fuel" and e["source"] == "kho"]}, vai="khonl", method="PUT")
    phai(s, 200, "KT kho gõ giá bán dầu cho chủ xe", g)
    s, g = goi("/api/trips/%s/sections/fuel/verify" % P, {}, vai="khonl"); phai(s, 200, "Kế toán kho kiểm mục III", g)
    s, g = goi("/api/trips/%s" % P, {"weight_origin": 43}, vai="thabok", method="PUT"); phai(s, 409, "Bãi sửa mục II đã kiểm → bị khoá", g)
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"section": "travel", "item_key": "x_food", "qty": 1, "unit_price": 1}]}, vai="thabok", method="PUT")
    phai(s, 409, "Bãi sửa dòng chi mục IV đã kiểm → bị khoá", g)
    s, g = Q.sua_phieu(goi, P, {"expenses": [{"section": "other", "item_key": "x_misc", "qty": 1, "unit_price": 150000}]})
    phai(s, 200, "Bãi thêm dòng mục VI (chưa khoá) → được", g)

    # ---- 3. Ghi sổ & chi
    s, g = goi("/api/trips/%s/sections/travel/pay" % P, {}, vai="quytb"); phai(s, 409, "Chi khi chưa ghi sổ → sai bước", g)
    s, g = goi("/api/trips/%s/sections/travel/book" % P, {}, vai="ketoan"); phai(s, 403, "KT Thu/Chi ghi sổ mục IV → bị từ chối", g)
    s, g = goi("/api/trips/%s/sections/travel/book" % P, {}, vai="ketoancp"); phai(s, 200, "KT Chi phí VC ghi sổ mục IV", g)
    # dầu kho chỉ rời kho theo phiếu ĐỀ NGHỊ đã cấp (chủ dự án 30/09): Bãi in đề nghị → cấp dầu → mới ghi sổ mục III
    s, v = goi("/api/trips/%s/vouchers" % P, {"kind": "fuel"}, vai="thabok"); phai(s, 200, "Bãi in phiếu đề nghị xuất kho nhiên liệu", v)
    for x in v:
        s, g = goi("/api/vouchers/%s/cap" % x["id"], {"qty": x["qty_l"]}, vai="khonl"); phai(s, 200, "Cấp dầu theo " + x["doc_no"], g)
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
    # Bãi không thấy giá phụ tùng (anh Khampla A2) — máy chủ không gửi; giá đọc bằng vai được xem (KT Chi phí)
    assert "unit_price" not in pt, "Bãi không được nhận giá phụ tùng: %s" % pt
    s, parts_kt = goi("/api/parts", vai="ketoancp"); pt["unit_price"] = next(x for x in parts_kt if x["id"] == pt["id"])["unit_price"]
    print("  ✓ %-58s" % "Bãi đọc kho phụ tùng: có tồn, KHÔNG có giá")
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "incident_type": "breakdown", "stop_seq": 3, "note": "thử: hỏng bầu hơi",
                                              "repair": {"source": "kho", "part_id": pt["id"], "qty": 1}}, vai="thabok")
    phai(s, 403, "Bãi khai khoản sửa chữa → bị từ chối (C1.2)", g)
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "incident_type": "breakdown", "stop_seq": 3, "note": "thử: hỏng bầu hơi",
                                              "repair": {"source": "kho", "part_id": pt["id"], "qty": 1}}, vai="totsua")
    phai(s, 200, "Tổ sửa chữa khai lấy phụ tùng từ KHO → dòng mục V, trừ tồn", g)
    d_kho = [e for e in g["expenses"] if e["section"] == "repair" and e["source"] == "kho"][-1]
    assert d_kho["acct_code"] == "4022/1371" and d_kho["stock_move_id"], d_kho          # xe liên kết → 4022, kho → /1371
    assert g["sections"]["repair"] == "entered", "mục V phải về 'đã nhập' để kiểm lại"
    s, parts2 = goi("/api/parts", vai="thabok"); assert next(x for x in parts2 if x["id"] == pt["id"])["qty"] == ton - 1, "tồn phụ tùng phải giảm 1"
    to = [v for v in K.to_kho(g["doc_no"]) if v["trip_no"] == g["doc_no"]]
    assert len(to) == 1 and to[0]["debit"] == "4022" and to[0]["credit"] == "1371", "PXK_PT bên kế toán: %s" % to
    print("  ✓ %-58s %s" % ("Trang kế toán sinh PXK_PT Nợ 4022 / Có 1371 (xe liên kết)", to[0]["ref"]))
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "repair": {"source": "mua", "item_name": "thử: vá lốp garage", "qty": 1, "unit_price": 300000}}, vai="totsua")
    phai(s, 200, "Sửa xe MUA NGOÀI → dòng mục V, định khoản …/4021", g)
    assert [e for e in g["expenses"] if e["section"] == "repair"][-1]["acct_code"] == "4022/4021"
    s, g = goi("/api/trips/%s/events" % P, {"kind": "repair", "repair": {"source": "kho", "part_id": pt["id"], "qty": 10 ** 6}}, vai="totsua"); phai(s, 409, "Xuất quá tồn kho → bị từ chối", g)
    s, g = goi("/api/trips/%s/events" % P, {"kind": "note", "note": "x"}, vai="ketoan"); phai(s, 403, "Kế toán ghi diễn biến → bị từ chối", g)
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"section": "repair", "item_name": "xoá hết"}]}, vai="totsua", method="PUT")
    phai(s, 409, "Tổ sửa chữa xoá dòng đã xuất kho khỏi phiếu → bị từ chối", g)
    # Sửa xe khai từ màn theo dõi đã đặt mục V ở "đã nhập" — kế toán kiểm thẳng, không cần Bãi gửi nữa
    s, g = goi("/api/trips/%s/sections/repair/send" % P, {}, vai="totsua"); phai(s, 409, "Mục V đã 'đã nhập' sẵn → gửi lại là sai bước", g)
    for hd, v in (("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "quytb")):
        s, g = goi("/api/trips/%s/sections/repair/%s" % (P, hd), {}, vai=v); phai(s, 200, "Mục V: %s (%s)" % (hd, v), g)
    s, kho = K.kt("/api/nhien-lieu", vai="khonl")             # sổ dầu ở trang kế toán (28/09)
    # 30/09: dầu kho chỉ rời kho theo phiếu ĐỀ NGHỊ đã cấp — dòng xuất kho mang số phiếu đề nghị (PLNL-…), không còn do ghi sổ mục III
    assert any(str(r["doc_no"]).startswith("PLNL-THU-LUONG-01/EPL") and r["kind"] == "out" for r in kho["rows"]), "cấp dầu theo phiếu đề nghị phải sinh dòng xuất kho nhiên liệu"
    print("  ✓ cấp dầu theo phiếu đề nghị đã sinh dòng xuất kho nhiên liệu PLNL-THU-LUONG-01/EPL")

    # ---- 4. Xe về, cân cuối, hoá đơn, thu tiền
    # C2.1 (anh Khampla): tài xế báo ngày về và km về qua điện thoại; Bãi cân rồi mới xác nhận tới.
    s, g = goi("/api/trips/%s" % P, {"back_date": "2026-09-16", "odo_back": 1500}, vai="thabok", method="PUT")
    phai(s, 409, "Bãi gõ ngày xe về, km về bằng nút Lưu khi xe chưa về → bị chặn (điền khi xe về)", g)
    s, g = goi("/api/trips/%s" % P, {"weight_dest": 40.5}, vai="thabok", method="PUT")
    phai(s, 409, "Bãi gõ cân cuối bằng nút Lưu khi xe chưa tới → bị chặn (điền khi xe tới)", g)
    s, g = goi("/api/trips/%s/bao-ve" % P, {"back_date": "2026-09-16", "odo_back": 900}, vai="thabok"); phai(s, 422, "Km về nhỏ hơn km đi → bị từ chối", g)
    s, g = goi("/api/trips/%s/bao-ve" % P, {"back_date": "2026-09-16", "odo_back": 1500}, vai="ketoan"); phai(s, 403, "Kế toán báo xe về → bị từ chối", g)
    s, g = goi("/api/trips/%s/bao-ve" % P, {"back_date": "2026-09-16", "odo_back": 1500}, vai="thabok"); phai(s, 200, "Báo đã về: ngày 16/09, km 1500", g)
    assert g["transport_status"] != "arrived" and g["back_date"] == "2026-09-16" and g["odo_back"] == 1500, "báo về chỉ ghi số, không tự chuyển sang đã tới: %s" % g["transport_status"]
    s, g = K.kt("/api/hoa-don/phieu/%s/xuat" % P, {}, vai="thabok"); phai(s, 403, "Bãi lập hoá đơn (trang kế toán) → bị từ chối", g)
    s, g = goi("/api/trips/%s/transport-status" % P, {"status": "arrived", "weight_dest": 40.5, "back_date": "2026-09-16"}, vai="thabok")
    phai(s, 200, "Bãi báo xe đã tới, cân cuối 40,5 t", g)
    # Trạng thái phải nhất quán: đã giao hàng thì coi như qua hết chặng, và số ngày đi dừng ở ngày về.
    s, bang = goi("/api/theo-doi?tat_ca=1", vai="thabok")
    ct = next(x for x in bang["chuyen"] if x["id"] == P)
    assert ct["transport_status"] == "arrived", ct["transport_status"]
    if ct["so_diem"]:
        assert ct["stop_reached"] == ct["so_diem"], (
            "đã giao hàng mà vẫn %s/%s chặng" % (ct["stop_reached"], ct["so_diem"]))
    print("  ✓ đã giao hàng: %s/%s chặng · đi %s ngày (đếm tới ngày về)"
          % (ct["stop_reached"], ct["so_diem"], ct["so_ngay_di"]))
    # Tính lại đúng cách trên giấy: từng khoản làm tròn 2 số lẻ rồi mới trừ — như máy chủ và như Excel.
    thue = round(40.5 * 40.5, 2); phi = round(thue * 0.02, 2); vuot = 0.5
    # EPL đã ứng = dầu kho 100 L + cao tốc + mục VI 150.000 + hai khoản sửa xe vừa khai (phụ tùng kho + vá lốp) ÷ tỷ giá.
    # Dòng x_vn "chủ xe tự trả" không tính. Lấy tổng chi từ máy chủ rồi kiểm lại từng phần.
    # Từ đây kiểm TIỀN BÁN (tiền thuê, phần trừ, trả chủ xe) nên phải đọc bằng vai kế toán —
    # gói trả cho Bãi không còn các khoá đó nữa (nợ kỹ thuật 3.1).
    assert "tra_chu_xe" not in g["tinh"], "Bãi không được nhận số phải trả chủ xe"
    s, g = goi("/api/trips/%s" % P, vai="ketoan")
    chi = g["tinh"]["chi"]
    # Dầu lấy từ KHO mang giá BÌNH QUÂN của kho lúc xuất (anh Khampla C5.3), không phải giá Bãi gõ.
    dau = [e for e in g["expenses"] if e["section"] == "fuel"][0]
    s, mv = K.kt("/api/nhien-lieu", vai="khonl")
    xuat = next(r for r in mv["rows"] if str(r["doc_no"]).startswith("PLNL-THU-LUONG-01/EPL") and r["kind"] == "out")
    assert dau["currency"] == "LAK" and abs(dau["unit_price"] - xuat["unit_cost_lak"]) < 0.01, (dau, xuat)
    # xe thuê: dầu kho là xuất BÁN cho chủ xe — tiền dầu theo giá bán KT kho gõ (29/09), giá vốn vẫn ở unit_price
    assert chi["fuel"] == round(100 * dau["sale_price"]) and chi["travel"] == 1833500 and chi["other"] == 150000, chi
    print("  ✓ %-58s %s LAK/L" % ("dầu kho mang giá bình quân của kho lúc xuất", format(round(dau["unit_price"]), ",")))
    assert chi["repair"] == round(pt["unit_price"] * 1 + 300000), (chi["repair"], pt["unit_price"])
    ung = round(g["tinh"]["tong_chi_lak"] / 22000, 2)
    assert g["tinh"]["tan_tinh"] == 40.5, g["tinh"]
    assert g["tinh"]["tra_chu_xe"] == round(thue - phi - vuot - ung, 2), (g["tinh"]["tra_chu_xe"], thue, phi, vuot, ung)
    s, g = K.kt("/api/hoa-don/phieu/%s/thu" % P, {"amount": 100, "currency": "USD"}, vai="doanhthu"); phai(s, 409, "Ghi thu trước khi có hoá đơn → sai bước", g)
    # ---- 4b. Bước 14: kế toán rà lại rồi KHOÁ. Chưa khoá thì chưa có hoá đơn; khoá rồi Bãi hết sửa.
    s, g = K.kt("/api/hoa-don/phieu/%s/xuat" % P, {}, vai="doanhthu"); phai(s, 409, "Lập hoá đơn khi phiếu chưa khoá → sai bước", g)
    s, g = goi("/api/trips/%s/khoa" % P, {}, vai="thabok"); phai(s, 403, "Bãi khoá phiếu → bị từ chối", g)
    s, g = goi("/api/trips/%s/kiem-lai" % P, vai="ketoan"); phai(s, 200, "Kế toán bấm Kiểm lại → bảng cảnh báo", g)
    ma_cb = [x["ma"] for x in g["canh_bao"]]
    # Tài xế đã báo km về ở bước trên nên KHÔNG còn cảnh báo thiếu km — đúng là nhờ tài xế báo mà kế toán đỡ một việc.
    # Phiếu quặng của khách: kế toán đã NHẬP TAY số HR-9999 ở bước 1 — từ 23/09 nhập tay là đủ (anh chủ dự án:
    # "phiếu khách hàng thì mình nhập tay được"), không bắt đính kèm ảnh nên KHÔNG còn cảnh báo thiếu phiếu quặng.
    assert "THIEU_PHIEU_QUANG" not in ma_cb and "THIEU_KM_VE" not in ma_cb, "đã nhập tay số phiếu quặng và tài xế đã báo km — không được còn hai cảnh báo này: %s" % ma_cb
    assert ma_cb, "phiếu thử vẫn phải còn cảnh báo khác (hao hụt, dòng hàng) để thử bước xác nhận khoá: %s" % ma_cb
    s, g = goi("/api/trips/%s/khoa" % P, {}, vai="ketoan"); phai(s, 409, "Khoá khi còn cảnh báo mà chưa xác nhận → chặn", g)
    s, g = goi("/api/trips/%s/khoa" % P, {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "Kế toán xác nhận khoá phiếu", g)
    assert g["locked"] and g["locked_by"], g.get("locked")
    s, g = goi("/api/trips/%s" % P, {"odo_back": 9999}, vai="thabok", method="PUT"); phai(s, 409, "Bãi sửa phiếu đã khoá → bị chặn", g)
    s, g = K.kt("/api/xe-lien-ket/phieu/%s/tra" % P, {}, vai="thabok"); phai(s, 403, "Bãi trả chủ xe (trang kế toán) → bị từ chối", g)
    s, g = K.kt("/api/hoa-don/phieu/%s/xuat" % P, {}, vai="doanhthu"); phai(s, 200, "Kế toán doanh thu lập hoá đơn (trang kế toán)", g)
    s, g = K.kt("/api/hoa-don/phieu/%s/thu" % P, {"amount": g["hoa_don"]["con_lai"], "currency": g["hoa_don"]["ccy"]}, vai="doanhthu")
    phai(s, 200, "Kế toán doanh thu ghi đã thu tiền (trang kế toán)", g)
    assert g["hoa_don"]["finance_status"] == "paid", "thu đủ thì trạng thái phải tự sang đã thu: %s" % g["hoa_don"]["finance_status"]
    s, g = goi("/api/trips/%s" % P, vai="doanhthu")
    assert g["invoiced"] and g["finance_status"] == "paid", "bản chép trên phiếu phải là đã xuất hoá đơn · đã thu: %s %s" % (g["invoiced"], g["finance_status"])
    # ---- 4c. Xe liên kết: quỹ trả chủ xe một lần → chứng từ PC_CX
    # trả chủ xe ở TRANG KẾ TOÁN từ 28/09 (đợt 7b) — phiếu nhận bản chép "đã trả"
    s, dot = K.kt("/api/xe-lien-ket/phieu/%s/tra" % P, {}, vai="quytb"); phai(s, 200, "Quỹ trả chủ xe liên kết (trang kế toán)", dot)
    s, g = goi("/api/trips/%s" % P, vai="quytb")
    assert g["owner_paid"] and g["owner_payment_id"] == dot["id"] and g["owner_paid_usd"] == g["tinh"]["tra_chu_xe"], (g["owner_paid_usd"], g["tinh"]["tra_chu_xe"])
    s, g2 = K.kt("/api/xe-lien-ket/phieu/%s/tra" % P, {}, vai="quytb"); phai(s, 409, "Trả chủ xe lần hai → từ chối", g2)
    s, so = K.kt("/api/chung-tu?loai=PC_CX&limit=1000", vai="ketoan"); phai(s, 200, "Sổ có tờ PC_CX", so)
    so = [v for v in so if v["trip_no"] == "THU-LUONG-01/EPL"]
    assert len(so) == 1 and so[0]["currency"] == "USD" and so[0]["debit"] == "4022" and so[0]["entry_id"], so
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
    s, g = goi("/api/parts/%s/moves" % pt["id"], {"kind": "in", "qty": 1, "note": "hoàn trả sau thử luồng"}, vai="khopt")
    phai(s, 409, "Trang điều xe không còn nhập / xuất phụ tùng (đã dời sang kế toán)", g)
    s, g = K.kt("/api/phu-tung/%s/nhap-xuat" % pt["id"], {"kind": "in", "qty": 1, "note": "hoàn trả sau thử luồng"}, vai="thabok")
    phai(s, 403, "Bãi nhập kho phụ tùng ở trang kế toán → bị từ chối (C1.2)", g)
    s, g = goi("/api/trips/%s" % P, vai="admin", method="DELETE"); phai(s, 409, "Phiếu còn hoá đơn bên kế toán → chưa xoá được", g)
    s, g = K.kt("/api/xe-lien-ket/dot/%s" % dot["id"], vai="admin", method="DELETE"); phai(s, 200, "Sếp huỷ đợt trả chủ xe của phiếu thử (trang kế toán)", g)
    s, h = K.kt("/api/hoa-don/phieu/%s" % P, vai="admin")
    for x in h.get("thu_tien") or []:
        s, g = K.kt("/api/hoa-don/thu/%s" % x["id"], vai="admin", method="DELETE"); phai(s, 200, "Sếp xoá lần thu của phiếu thử (trang kế toán)", g)
    s, g = K.kt("/api/hoa-don/phieu/%s" % P, vai="admin", method="DELETE"); phai(s, 200, "Sếp huỷ hoá đơn phiếu thử (trang kế toán)", g)
    s, g = goi("/api/trips/%s" % P, vai="admin", method="DELETE"); phai(s, 200, "Admin xoá phiếu thử (dọn)", g)
    # xoá phiếu → phụ tùng mục V về kho bên trang kế toán, tờ PXK_PT của phiếu rút theo
    s, parts3 = goi("/api/parts", vai="thabok")
    assert next(x for x in parts3 if x["id"] == pt["id"])["qty"] == ton, "xoá phiếu phải trả phụ tùng về kho: %s" % ton
    assert not [v for v in K.to_kho("THU-LUONG-01/EPL") if v["trip_no"] == "THU-LUONG-01/EPL"], "tờ PXK_PT của phiếu đã xoá phải rút"
    print("  ✓ %-58s %s" % ("Xoá phiếu → phụ tùng về kho kế toán, PXK_PT rút theo", ton))
    s, kho = K.kt("/api/nhien-lieu", vai="khonl")
    assert not [r for r in kho["rows"] if r["doc_no"] == "THU-LUONG-01/EPL"], "xoá phiếu phải trả dầu mục III về kho"
    print("  ✓ %-58s" % "Xoá phiếu → dầu mục III về kho kế toán")
    print("\nTHỬ LUỒNG API: ĐẠT — 9 vai · 6 mục · 5 bước duyệt · bảng giá khách × tuyến · 13 chỗ từ chối đúng")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("\nTHỬ LUỒNG API: HỎNG —", e); sys.exit(1)
