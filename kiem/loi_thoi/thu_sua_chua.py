# -*- coding: utf-8 -*-
"""Thử LỆNH SỬA CHỮA RIÊNG — ໃບສັ່ງສ້ອມແປງ (anh Khampla C7.3). Lệnh ở TRANG KẾ TOÁN từ 28/09 (đợt 6).

    python kiem/thu_sua_chua.py [điều xe=http://127.0.0.1:8010]      (trang kế toán: biến EPL_KT, mặc định 8031)

Mục V trên phiếu chỉ ghi được cái sửa TRONG một chuyến. Xe nằm bãi đại tu, hay bảo dưỡng định kỳ theo số km, thì không
có chuyến nào để gắn vào. Tờ lệnh sửa chữa là chỗ khai đúng việc đó, và đi qua **đúng chuỗi duyệt của mục V**:

    Tổ sửa chữa NHẬP → KT Chi phí KIỂM → KT Chi phí GHI SỔ → Quỹ tiền mặt CHI

Kịch bản (lệnh lập ở trang kế toán; xe, trạng thái xe và màn Xe ở trang điều xe): chỉ tổ sửa chữa lập được → xe bên
điều xe thành "đang sửa" → dòng lấy kho (trừ tồn ngay + tờ PXK_PT) và dòng mua ngoài → sai bước, sai vai bị chặn →
kiểm → ghi sổ → trả lại → kiểm lại → chi (một tờ PC_SC chỉ gồm khoản mua ngoài, Nợ 614 / Có 1011) → xe về rảnh → màn Xe
bên điều xe gom cả lệnh lẫn phiếu → đường cũ bên điều xe 409 → trang điều xe tắt thì không lập được lệnh → dọn.
"""
import json
import os
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — lệnh sửa chữa và kho phụ tùng ở trang kế toán (28/09)
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


def trang_thai_xe(vid):
    s, g = goi("/api/vehicles/%s" % vid, vai="admin")
    return g.get("status")


def main():
    for u in ("thabok", "ketoan", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    kt = lambda duong, du_lieu=None, vai=None, method=None: K.kt(duong, du_lieu, vai=vai, method=method)
    print("✓ đăng nhập (điều xe: thabok · ketoan · admin; kế toán: totsua · ketoancp · ketoan · quytb · thabok · khopt · admin)")

    # dọn dấu vết lần chạy trước (lệnh thử chưa xuất kho)
    s, ds = kt("/api/lenh-sua-chua", vai="totsua")
    for o in [x for x in ds if (x.get("note") or "").startswith("thử:")]:
        kt("/api/lenh-sua-chua/%s" % o["id"], vai="admin", method="DELETE")

    s, xe = kt("/api/lenh-sua-chua/xe", vai="totsua")
    phai(s, 200, "Ô chọn xe của lệnh (danh mục bên trang điều xe)", {"detail": xe} if s != 200 else {})
    con = [v for v in xe if v.get("active") is not False]
    x0 = next((v for v in con if v["status"] == "available"), con[0])
    tt0 = x0["status"]
    tt_vao = "maintenance" if tt0 not in ("inactive", "on_trip") else tt0      # đang chạy chuyến / ngưng dùng thì giữ nguyên
    s, parts = kt("/api/phu-tung", vai="khopt")
    pt = next(p for p in parts if p["qty"] >= 2); ton = pt["qty"]

    # ---------------------------------------------------------------- 1. lập lệnh: chỉ tổ sửa chữa
    than = {"vehicle_id": x0["id"], "kind": "bao_duong", "order_date": "2026-09-22", "odo_km": 12345,
            "garage": "Gara Thà Bốc", "note": "thử: bảo dưỡng định kỳ"}
    s, g = kt("/api/lenh-sua-chua", than, vai="thabok")
    phai(s, 403, "Bãi lập lệnh sửa chữa → bị chặn (C1.2)", g)
    s, g = kt("/api/lenh-sua-chua", than, vai="ketoancp")
    phai(s, 403, "KT Chi phí lập lệnh → bị chặn (họ là người kiểm)", g)
    s, O = kt("/api/lenh-sua-chua", than, vai="totsua")
    phai(s, 200, "Tổ sửa chữa lập lệnh sửa chữa (trang kế toán)", {"detail": O} if s != 200 else {})
    oid = O["id"]
    assert O["doc_no"].startswith("LSC-2609-") and O["status"] == "entered", O
    assert O["truck_no"] == x0["truck_no"], "số xe chép từ danh mục bên trang điều xe"
    print("  ✓ %-60s %s · xe %s" % ("Số lệnh cấp theo tháng", O["doc_no"], O["truck_no"]))
    assert trang_thai_xe(x0["id"]) == tt_vao, "lập lệnh thì xe bên trang điều xe phải thành %s (đang: %s)" % (tt_vao, trang_thai_xe(x0["id"]))
    print("  ✓ %-60s %s → %s" % ("Xe bên trang điều xe vào xưởng", tt0, tt_vao))

    s, g = kt("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoancp")
    phai(s, 409, "Kiểm lệnh chưa có dòng chi nào → bị từ chối", g)

    # ---------------------------------------------------------------- 2. dòng chi: kho và mua ngoài
    lines = [{"source": "kho", "part_id": pt["id"], "qty": 2},
             {"source": "mua", "item_name": "thử: công thay dầu", "qty": 1, "unit_price": 350000, "currency": "LAK"}]
    s, g = kt("/api/lenh-sua-chua/%s" % oid, {"lines": lines}, vai="thabok", method="PUT")
    phai(s, 403, "Bãi thêm dòng chi vào lệnh → bị chặn", g)
    s, O = kt("/api/lenh-sua-chua/%s" % oid, {"lines": lines}, vai="totsua", method="PUT")
    phai(s, 200, "Tổ sửa chữa thêm hai dòng: lấy kho + mua ngoài", {"detail": O} if s != 200 else {})
    assert O["so_dong"] == 2, O["so_dong"]
    kho_dong = [d for d in O["lines"] if d["source"] == "kho"][0]
    assert kho_dong["acct_code"] == "614/1371" and [d for d in O["lines"] if d["source"] == "mua"][0]["acct_code"] == "614/4021"
    print("  ✓ %-60s %s · %s" % ("Định khoản đúng mã anh Khampla cấp", "614/1371", "614/4021"))
    assert kho_dong["stock_move_id"], "dòng lấy kho phải sinh tờ xuất kho ngay lúc khai"
    s, parts2 = kt("/api/phu-tung", vai="khopt")
    assert next(p for p in parts2 if p["id"] == pt["id"])["qty"] == ton - 2, "tồn kho phải giảm 2"
    print("  ✓ %-60s %s → %s" % ("Lấy kho trừ tồn NGAY lúc khai", ton, ton - 2))
    to = K.to_kho(O["doc_no"])
    assert len(to) == 1 and to[0]["debit"] == "614" and to[0]["credit"] == "1371", "PXK_PT bên kế toán: %s" % to
    print("  ✓ %-60s %s" % ("PXK_PT mang số lệnh, Nợ 614 / Có 1371", to[0]["ref"]))

    s, g = kt("/api/lenh-sua-chua/%s" % oid, {"lines": [lines[1]]}, vai="totsua", method="PUT")
    phai(s, 409, "Xoá dòng đã xuất kho khỏi lệnh → bị từ chối", g)
    s, g = kt("/api/lenh-sua-chua/%s" % oid, vai="totsua", method="DELETE")
    phai(s, 409, "Xoá cả lệnh đã xuất kho → bị từ chối", g)

    # ---------------------------------------------------------------- 3. chuỗi duyệt như mục V
    s, g = kt("/api/lenh-sua-chua/%s/book" % oid, {}, vai="ketoancp")
    phai(s, 409, "Ghi sổ khi chưa kiểm → sai bước", g)
    s, g = kt("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoan")
    phai(s, 403, "KT Thu/Chi kiểm lệnh sửa chữa → bị chặn (việc KT Chi phí)", g)
    s, g = kt("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoancp")
    phai(s, 200, "KT Chi phí kiểm lệnh", {})
    s, g = kt("/api/lenh-sua-chua/%s" % oid, {"note": "sửa sau khi kiểm"}, vai="totsua", method="PUT")
    phai(s, 409, "Tổ sửa chữa sửa lệnh đã kiểm → bị chặn", g)
    s, g = kt("/api/lenh-sua-chua/%s/book" % oid, {}, vai="ketoancp")
    phai(s, 200, "KT Chi phí ghi sổ", {})
    s, g = kt("/api/lenh-sua-chua/%s/return" % oid, {}, vai="ketoancp")
    phai(s, 200, "Trả lại cho tổ sửa chữa sửa tiếp", {})
    assert g["status"] == "entered", g["status"]
    s, g = kt("/api/lenh-sua-chua/%s/verify" % oid, {}, vai="ketoancp"); phai(s, 200, "Kiểm lại", {})
    s, g = kt("/api/lenh-sua-chua/%s/book" % oid, {}, vai="ketoancp"); phai(s, 200, "Ghi sổ lại", {})
    s, g = kt("/api/lenh-sua-chua/%s/pay" % oid, {}, vai="ketoancp")
    phai(s, 403, "KT Chi phí tự chi tiền → bị chặn (việc quỹ)", g)
    s, O = kt("/api/lenh-sua-chua/%s/pay" % oid, {}, vai="quytb")
    phai(s, 200, "Quỹ tiền mặt chi lệnh sửa chữa", {"detail": O} if s != 200 else {})
    assert O["status"] == "paid" and O["chung_tu"], "chi rồi phải có tờ PC_SC: %s" % O
    pc = [v for v in K.to_kho(O["doc_no"], "PC_SC") if v["ref"] == O["chung_tu"]]
    assert len(pc) == 1 and pc[0]["debit"] == "614" and pc[0]["credit"] == "1011" and pc[0]["entry_id"], "PC_SC: %s" % pc
    assert abs(pc[0]["amount_lak"] - O["tong_mua_lak"]) < 1, \
        "tờ chi chỉ gồm khoản MUA NGOÀI (%s), không cộng phần lấy kho: %s" % (O["tong_mua_lak"], pc[0]["amount_lak"])
    print("  ✓ %-60s %s = %s LAK" % ("Tờ chi chỉ gồm khoản mua ngoài, Nợ 614 / Có 1011, vào sổ", pc[0]["ref"], round(pc[0]["amount_lak"])))
    assert trang_thai_xe(x0["id"]) == tt0, "chi xong thì xe bên trang điều xe phải về %s (đang: %s)" % (tt0, trang_thai_xe(x0["id"]))
    print("  ✓ %-60s %s" % ("Chi xong, xe bên trang điều xe về lại", tt0))

    # ---------------------------------------------------------------- 4. màn Xe bên điều xe gom cả hai nguồn
    s, xct = goi("/api/vehicles/%s" % x0["id"], vai="ketoan")
    sua = xct.get("sua_chua") or []
    assert not xct.get("sua_chua_lenh_loi") and any(d.get("lenh") and d["doc_no"] == O["doc_no"] for d in sua), \
        "tab Sửa chữa của xe phải thấy lệnh sửa chữa riêng (hỏi trang kế toán): %s" % [d.get("doc_no") for d in sua]
    print("  ✓ %-60s %d dòng" % ("Lịch sử sửa chữa của xe gom cả lệnh lẫn phiếu", len(sua)))

    # ---------------------------------------------------------------- 5. đường cũ bên điều xe · trang điều xe tắt
    s, g = goi("/api/lenh-sua-chua", vai="ketoan")
    phai(s, 409, "Đường lệnh sửa chữa bên trang điều xe → đã dời sang trang kế toán", g)
    s, cu = kt("/api/cau-hinh", vai="admin")
    kt("/api/cau-hinh", {"dieu_xe_api": "http://127.0.0.1:8097"}, vai="admin", method="PUT")
    try:
        s, g = kt("/api/lenh-sua-chua", than, vai="totsua")
        phai(s, 503, "Trang điều xe tắt → lập lệnh bị chặn (không biết xe nào, không báo được 'đang sửa')", g)
        s, ds2 = kt("/api/lenh-sua-chua", vai="totsua")
        assert s == 200 and not [x for x in ds2 if (x.get("note") or "").startswith("thử:") and x["status"] == "entered"], \
            "bị chặn thì không được có lệnh nửa vời"
        print("  ✓ %-60s" % "Trang điều xe tắt: vẫn xem được danh sách lệnh, không có lệnh nửa vời")
    finally:
        kt("/api/cau-hinh", {"dieu_xe_api": cu["dieu_xe_api"]}, vai="admin", method="PUT")

    # ---------------------------------------------------------------- 6. dọn
    s, g = K.kt("/api/phu-tung/%s/nhap-xuat" % pt["id"], {"kind": "in", "qty": 2, "note": "hoàn trả sau bộ kiểm"}, vai="khopt")
    phai(s, 200, "Trả lại phụ tùng đã xuất ở trang kế toán (dọn)", {})
    print("\n✅ LỆNH SỬA CHỮA RIÊNG (trang kế toán): đúng chuỗi duyệt mục V, lấy kho trừ tồn ngay, chi chỉ khoản mua ngoài,")
    print("   xe bên trang điều xe vào / ra xưởng đúng, màn Xe thấy cả hai nguồn, trang điều xe tắt thì chặn rõ.")
    print("   (Tờ thử giữ lại vì đã sinh chứng từ — công cụ dọn gỡ lệnh ghi chú 'thử'.)")


if __name__ == "__main__":
    main()
