# -*- coding: utf-8 -*-
"""Thử LỆNH SỬA CHỮA RIÊNG — ໃບສັ່ງສ້ອມແປງ (anh Khampla C7.3).

    python kiem/thu_sua_chua.py [http://127.0.0.1:8010]

Mục V trên phiếu chỉ ghi được cái sửa TRONG một chuyến. Xe nằm bãi đại tu, hay bảo dưỡng định kỳ
theo số km, thì không có chuyến nào để gắn vào — trước đây tiền sửa đó rơi ra ngoài sổ. Tờ lệnh sửa
chữa là chỗ khai đúng việc đó, và đi qua **đúng chuỗi duyệt của mục V**, không đẻ luật mới:

    Tổ sửa chữa NHẬP → KT Chi phí KIỂM → KT Chi phí GHI SỔ → Quỹ tiền mặt CHI

Kịch bản: chỉ tổ sửa chữa lập được → thêm dòng lấy kho (trừ tồn ngay + tờ PXK_PT) và dòng mua ngoài →
sai bước bị chặn, sai vai bị chặn → kiểm → ghi sổ → trả lại → kiểm lại → chi (một tờ PC_SC chỉ gồm
khoản mua ngoài) → xe về rảnh → lịch sử sửa chữa của xe gom cả lệnh lẫn phiếu → dọn.
"""
import json
import os
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — kho phụ tùng ở trang kế toán (28/09)
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
    for u in ("thabok", "ketoan", "ketoancp", "quytb", "totsua", "khopt", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 7 vai")

    # dọn dấu vết lần chạy trước
    s, ds = goi("/api/lenh-sua-chua", vai="totsua")
    for o in [x for x in ds if (x.get("note") or "").startswith("thử:")]:
        goi("/api/lenh-sua-chua/%s" % o["id"], vai="admin", method="DELETE")

    s, xe = goi("/api/vehicles", vai="thabok")
    x0 = [v for v in xe if v.get("active") is not False][0]
    s, parts = goi("/api/parts", vai="khopt")
    pt = next(p for p in parts if p["qty"] >= 2); ton = pt["qty"]

    # ---------------------------------------------------------------- 1. lập lệnh: chỉ tổ sửa chữa
    than = {"vehicle_id": x0["id"], "kind": "bao_duong", "order_date": "2026-09-22", "odo_km": 12345,
            "garage": "Gara Thà Bốc", "note": "thử: bảo dưỡng định kỳ"}
    s, g = goi("/api/lenh-sua-chua", than, vai="thabok")
    phai(s, 403, "Bãi lập lệnh sửa chữa → bị chặn (C1.2)", g)
    s, g = goi("/api/lenh-sua-chua", than, vai="ketoancp")
    phai(s, 403, "KT Chi phí lập lệnh → bị chặn (họ là người kiểm)", g)
    s, O = goi("/api/lenh-sua-chua", than, vai="totsua")
    phai(s, 200, "Tổ sửa chữa lập lệnh sửa chữa", O)
    oid = O["id"]
    assert O["doc_no"].startswith("LSC-2609-"), "số lệnh phải theo tháng: %s" % O["doc_no"]
    assert O["status"] == "entered", O["status"]
    print("  ✓ %-60s %s" % ("Số lệnh cấp theo tháng", O["doc_no"]))

    s, g = goi("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoancp")
    phai(s, 409, "Kiểm lệnh chưa có dòng chi nào → bị từ chối", g)

    # ---------------------------------------------------------------- 2. dòng chi: kho và mua ngoài
    lines = [{"source": "kho", "part_id": pt["id"], "qty": 2},
             {"source": "mua", "item_name": "thử: công thay dầu", "qty": 1, "unit_price": 350000, "currency": "LAK"}]
    s, g = goi("/api/lenh-sua-chua/%s" % oid, {"lines": lines}, vai="thabok", method="PUT")
    phai(s, 403, "Bãi thêm dòng chi vào lệnh → bị chặn", g)
    s, O = goi("/api/lenh-sua-chua/%s" % oid, {"lines": lines}, vai="totsua", method="PUT")
    phai(s, 200, "Tổ sửa chữa thêm hai dòng: lấy kho + mua ngoài", O)
    assert O["so_dong"] == 2, O["so_dong"]
    kho_dong = [d for d in O["lines"] if d["source"] == "kho"][0]
    assert kho_dong["acct_code"] == "614/1371", "dòng lấy kho phải định khoản 614/1371: %s" % kho_dong["acct_code"]
    assert [d for d in O["lines"] if d["source"] == "mua"][0]["acct_code"] == "614/4021"
    print("  ✓ %-60s %s · %s" % ("Định khoản đúng mã anh Khampla cấp", "614/1371", "614/4021"))
    assert kho_dong["stock_move_id"], "dòng lấy kho phải sinh tờ xuất kho ngay lúc khai"
    s, parts2 = goi("/api/parts", vai="khopt")
    assert next(p for p in parts2 if p["id"] == pt["id"])["qty"] == ton - 2, "tồn kho phải giảm 2"
    print("  ✓ %-60s %s → %s" % ("Lấy kho trừ tồn NGAY lúc khai", ton, ton - 2))
    to = K.to_kho(O["doc_no"])
    assert len(to) == 1 and to[0]["debit"] == "614" and to[0]["credit"] == "1371", "PXK_PT bên kế toán: %s" % to
    print("  ✓ %-60s %s" % ("Trang kế toán sinh PXK_PT mang số lệnh, Nợ 614 / Có 1371", to[0]["ref"]))

    s, g = goi("/api/lenh-sua-chua/%s" % oid, {"lines": [lines[1]]}, vai="totsua", method="PUT")
    phai(s, 409, "Xoá dòng đã xuất kho khỏi lệnh → bị từ chối", g)
    s, g = goi("/api/lenh-sua-chua/%s" % oid, vai="totsua", method="DELETE")
    phai(s, 409, "Xoá cả lệnh đã xuất kho → bị từ chối", g)

    # ---------------------------------------------------------------- 3. chuỗi duyệt như mục V
    s, g = goi("/api/lenh-sua-chua/%s/book" % oid, {}, vai="ketoancp")
    phai(s, 409, "Ghi sổ khi chưa kiểm → sai bước", g)
    s, g = goi("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoan")
    phai(s, 403, "KT Thu/Chi kiểm lệnh sửa chữa → bị chặn (việc KT Chi phí)", g)
    s, g = goi("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoancp")
    phai(s, 200, "KT Chi phí kiểm lệnh", g)
    s, g = goi("/api/lenh-sua-chua/%s" % oid, {"note": "sửa sau khi kiểm"}, vai="totsua", method="PUT")
    phai(s, 409, "Tổ sửa chữa sửa lệnh đã kiểm → bị chặn", g)
    s, g = goi("/api/lenh-sua-chua/%s/book" % oid, {}, vai="ketoancp")
    phai(s, 200, "KT Chi phí ghi sổ", g)
    s, g = goi("/api/lenh-sua-chua/%s/return" % oid, {}, vai="ketoancp")
    phai(s, 200, "Trả lại cho tổ sửa chữa sửa tiếp", g)
    assert g["status"] == "entered", g["status"]
    s, g = goi("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoancp"); phai(s, 200, "Kiểm lại", g)
    s, g = goi("/api/lenh-sua-chua/%s/book" % oid, {}, vai="ketoancp"); phai(s, 200, "Ghi sổ lại", g)
    s, g = goi("/api/lenh-sua-chua/%s/pay" % oid, {}, vai="ketoancp")
    phai(s, 403, "KT Chi phí tự chi tiền → bị chặn (việc quỹ)", g)
    s, O = goi("/api/lenh-sua-chua/%s/pay" % oid, {}, vai="quytb")
    phai(s, 200, "Quỹ tiền mặt chi lệnh sửa chữa", O)
    assert O["status"] == "paid" and O["chung_tu"], "chi rồi phải có tờ PC_SC: %s" % O

    s, ct = goi("/api/chung-tu?loai=PC_SC&limit=5", vai="ketoan")
    to = next(c for c in ct["ds"] if c["so"] == O["chung_tu"])
    assert abs(to["tien_lak"] - O["tong_mua_lak"]) < 1, \
        "tờ chi chỉ gồm khoản MUA NGOÀI (%s), không cộng phần lấy kho: %s" % (O["tong_mua_lak"], to["tien_lak"])
    print("  ✓ %-60s %s = %s LAK" % ("Tờ chi chỉ gồm khoản mua ngoài", to["so"], round(to["tien_lak"])))

    # ---------------------------------------------------------------- 4. màn Xe gom cả hai nguồn
    s, xct = goi("/api/vehicles/%s" % x0["id"], vai="ketoan")
    sua = xct.get("sua_chua") or []
    assert any(d.get("lenh") and d["doc_no"] == O["doc_no"] for d in sua), \
        "tab Sửa chữa của xe phải thấy lệnh sửa chữa riêng: %s" % [d.get("doc_no") for d in sua]
    print("  ✓ %-60s %d dòng" % ("Lịch sử sửa chữa của xe gom cả lệnh lẫn phiếu", len(sua)))

    # ---------------------------------------------------------------- 5. dọn
    s, g = K.kt("/api/phu-tung/%s/nhap-xuat" % pt["id"], {"kind": "in", "qty": 2, "note": "hoàn trả sau bộ kiểm"}, vai="khopt")
    phai(s, 200, "Trả lại phụ tùng đã xuất ở trang kế toán (dọn)", g)
    print("\n✅ LỆNH SỬA CHỮA RIÊNG: đúng chuỗi duyệt mục V, lấy kho trừ tồn ngay, chi chỉ khoản mua ngoài,")
    print("   màn Xe thấy cả hai nguồn. (Tờ thử giữ lại vì đã sinh chứng từ — xoá tay nếu cần.)")


if __name__ == "__main__":
    main()
