# -*- coding: utf-8 -*-
"""Đi trọn luồng nghiệp vụ của bên Lào trên MÁY CHỦ THẬT — đúng thứ tự sheet ໜ້າວຽກ.

    python kiem/thu_luong_api.py [http://127.0.0.1:8010]

  Bãi Thà Bốc lập phiếu xe liên kết, nhập 6 mục, gửi kiểm
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

    # ---- 4. Xe về, cân cuối, hoá đơn, thu tiền
    s, g = goi("/api/trips/%s/invoice" % P, {}, vai="thabok"); phai(s, 403, "Bãi lập hoá đơn → bị từ chối", g)
    s, g = goi("/api/trips/%s/transport-status" % P, {"status": "arrived", "weight_dest": 40.5, "back_date": "2026-09-16"}, vai="thabok")
    phai(s, 200, "Bãi báo xe đã tới, cân cuối 40,5 t", g)
    # Tính lại đúng cách trên giấy: từng khoản làm tròn 2 số lẻ rồi mới trừ — như máy chủ và như Excel.
    thue = round(40.5 * 40.5, 2); phi = round(thue * 0.02, 2); vuot = 0.5
    ung = round((100 * 30000 + 1833500 + 150000) / 22000, 2)          # dòng x_vn chủ xe tự trả → không tính
    assert g["tinh"]["tan_tinh"] == 40.5, g["tinh"]
    assert g["tinh"]["tra_chu_xe_usd"] == round(thue - phi - vuot - ung, 2), (g["tinh"]["tra_chu_xe_usd"], thue, phi, vuot, ung)
    s, g = goi("/api/trips/%s/finance-status" % P, {"status": "paid"}, vai="doanhthu"); phai(s, 409, "Ghi thu trước khi có hoá đơn → sai bước", g)
    s, g = goi("/api/trips/%s/invoice" % P, {}, vai="doanhthu"); phai(s, 200, "Kế toán doanh thu lập hoá đơn", g)
    s, g = goi("/api/trips/%s/finance-status" % P, {"status": "paid"}, vai="doanhthu"); phai(s, 200, "Kế toán doanh thu ghi đã thu tiền", g)
    assert g["invoiced"] and g["finance_status"] == "paid"
    assert any(l["action"] == "a_invoice" for l in g["logs"]) and any(l["action"] == "sec_fuel:pay" for l in g["logs"]), "nhật ký phải ghi từng bước"
    print("  ✓ nhật ký có %d dòng, đủ các bước" % len(g["logs"]))

    # ---- 5. Báo cáo thấy phiếu này
    s, g = goi("/api/bao-cao/xe-lien-ket?thang=2026-09", vai="doanhthu"); assert any(p["id"] == P for p in g), "báo cáo xe liên kết phải có phiếu thử"
    s, g = goi("/api/bao-cao/theo-doi?thang=2026-09", vai="doanhthu"); assert any(p["id"] == P for p in g)
    print("  ✓ báo cáo xe liên kết và theo dõi đều thấy phiếu thử")

    # ---- 6. Dọn
    s, g = goi("/api/trips/%s" % P, vai="thabok", method="DELETE"); phai(s, 409, "Bãi xoá phiếu đã duyệt → bị từ chối", g)
    s, g = goi("/api/trips/%s" % P, vai="admin", method="DELETE"); phai(s, 200, "Admin xoá phiếu thử (dọn)", g)
    print("\nTHỬ LUỒNG API: ĐẠT — 7 vai · 6 mục · 5 bước duyệt · 10 chỗ từ chối đúng")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("\nTHỬ LUỒNG API: HỎNG —", e); sys.exit(1)
