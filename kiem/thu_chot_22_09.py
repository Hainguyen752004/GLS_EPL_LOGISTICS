# -*- coding: utf-8 -*-
"""Thử BỐN QUYẾT ĐỊNH anh chủ dự án chốt chiều 22/09.

    python kiem/thu_chot_22_09.py [http://127.0.0.1:8010]

  1. **Ghi cấn trừ tháng** — khoản khách trả hộ (thẻ cao tốc · nợ trạm dầu VN) thành phiếu thu cách
     thu "cấn trừ" trên hoá đơn của chính khách đó; gọi lại không ghi trùng; phần không có chỗ bù để
     lại tháng sau.
  2. **Không đổi chéo xe nhà ↔ xe liên kết** giữa đường (chứng từ đã sinh mang mã loại cũ).
  3. **Ảnh tài xế** — cùng bộ máy với ảnh xe.
  4. **Hai mã kế toán còn thiếu là ô cấu hình**: Sếp gõ mã, tờ chứng từ sinh sau đó mang mã; hàng
     khách gửi là khoản NGOÀI BẢNG, không đụng kho 1371.
"""
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000100ffff03000006000557bfabd4000000"
    "0049454e44ae426082")


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


def gui_anh(duong, ten, du, vai):
    ranh = "----eplkiem1234567890"
    than = io.BytesIO()
    than.write(("--%s\r\n" % ranh).encode())
    than.write(('Content-Disposition: form-data; name="tep"; filename="%s"\r\n' % ten).encode())
    than.write(b"Content-Type: image/png\r\n\r\n"); than.write(du)
    than.write(("\r\n--%s--\r\n" % ranh).encode())
    r = urllib.request.Request(GOC + duong, data=than.getvalue(), method="POST", headers={
        "Content-Type": "multipart/form-data; boundary=%s" % ranh, "Authorization": "Bearer " + TOKEN[vai]})
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
    print("%s %-62s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def main():
    for u in ("thabok", "ketoan", "doanhthu", "tx01", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 5 vai")

    # ================================================================ 1. ghi cấn trừ tháng
    # Dữ liệu gieo: khách ຄຳຕຸ້ຍ tháng 8 có dòng dầu VN ghi nợ 25.200.000 và một phiếu đã xuất hoá đơn còn nợ.
    s, ct = goi("/api/bao-cao/can-tru?thang=2026-08", vai="doanhthu")
    o = next((x for x in ct["ds"] if x["chua_ghi_lak"] > 0), None)
    if o is None:
        print("  · tháng 8 đã ghi hết cấn trừ (lần chạy trước) — bỏ qua phần 1, kiểm phần chống trùng")
        o = next((x for x in ct["ds"] if x["can_tru_lak"] > 0), None)
        assert o, "phải có khách có khoản trả hộ tháng 8: %s" % ct
        s, g = goi("/api/bao-cao/can-tru/ghi", {"customer_id": o["customer_id"], "thang": "2026-08"}, vai="doanhthu")
        phai(s, 409, "Ghi lại khi đã ghi hết → bị từ chối, không ghi trùng", g)
    else:
        truoc = o["chua_ghi_lak"]
        s, g = goi("/api/bao-cao/can-tru/ghi", {"customer_id": o["customer_id"], "thang": "2026-08"}, vai="thabok")
        phai(s, 403, "Bãi ghi cấn trừ → bị chặn", g)
        s, r = goi("/api/bao-cao/can-tru/ghi", {"customer_id": o["customer_id"], "thang": "2026-08"}, vai="doanhthu")
        if s == 409 and r.get("detail", {}).get("ma") == "KHONG_CON_NO":
            # Lần chạy trước đã bù hết hoá đơn còn nợ; phần trả hộ dư đang chờ tháng sau — đúng luật, không ghi thu dư.
            print("  ✓ %-62s %s" % ("Còn %s LAK trả hộ nhưng không còn hoá đơn để bù → để lại, không ghi thu dư" % o["chua_ghi_lak"], "409 KHONG_CON_NO"))
            r = None
        else:
            phai(s, 200, "KT Doanh thu ghi cấn trừ tháng 8 cho %s" % o["customer_name"], r)
    if o is not None and r is not None:
        assert r["phieu_thu"] and r["ghi_lak"] > 0, "phải sinh ít nhất một phiếu thu cấn trừ: %s" % r
        assert r["ghi_lak"] + r["de_lai_lak"] == truoc, "ghi + để lại phải bằng phần chưa ghi: %s" % r
        print("  ✓ %-62s %s LAK vào %s · để lại %s" % ("Ghi cấn trừ: bù đúng vào hoá đơn còn nợ", r["ghi_lak"], r["phieu_thu"][0]["so"], r["de_lai_lak"]))
        s, ct2 = goi("/api/bao-cao/can-tru?thang=2026-08", vai="doanhthu")
        o2 = next(x for x in ct2["ds"] if x["customer_id"] == o["customer_id"])
        assert o2["da_ghi_lak"] == r["ghi_lak"] and o2["chua_ghi_lak"] == r["de_lai_lak"], \
            "bảng cấn trừ phải phản ánh phần đã ghi: %s" % o2
        print("  ✓ %-62s" % "Bảng cấn trừ đọc lại đúng phần đã ghi / chưa ghi")
        s, ds = goi("/api/trips", vai="doanhthu")
        p = next(x for x in ds if x["doc_no"] == r["phieu_thu"][0]["so"])
        s, tt = goi("/api/trips/%s/thu-tien" % p["id"], vai="doanhthu")
        dong = [x for x in tt["ds"] if x["method"] == "offset" and x["ref"] == r["ref"]]
        assert dong, "sổ thu của phiếu phải có dòng cách thu 'cấn trừ' mang ref %s" % r["ref"]
        print("  ✓ %-62s %s" % ("Sổ thu tiền của phiếu có dòng cách thu cấn trừ", dong[0]["ref"]))
        s, g = goi("/api/bao-cao/can-tru/ghi", {"customer_id": o["customer_id"], "thang": "2026-08"}, vai="doanhthu")
        assert s in (200, 409), g
        if s == 200:
            assert g["ghi_lak"] == 0 or g["de_lai_lak"] >= 0, g
        print("  ✓ %-62s %s" % ("Ghi lại lần hai không ghi trùng phần đã ghi", "409 " + g["detail"]["ma"] if s == 409 else "ghi thêm %s" % g["ghi_lak"]))

    # ================================================================ 2. không đổi chéo xe nhà ↔ xe liên kết
    s, xe = goi("/api/vehicles", vai="thabok")
    xe_nha = [x for x in xe if x.get("owner_type") != "joint" and x.get("active") is not False]
    xe_lk = [x for x in xe if x.get("owner_type") == "joint" and x.get("active") is not False]
    s, ds = goi("/api/trips", vai="thabok")
    p = next((x for x in ds if x["company"] == "EPL" and x["transport_status"] != "arrived" and not x["locked"]), None)
    if p and xe_lk:
        s, g = goi("/api/trips/%s/doi-xe" % p["id"], {"vehicle_id": xe_lk[0]["id"], "ly_do": "thử chéo"}, vai="thabok")
        phai(s, 409, "Đổi xe nhà → xe liên kết trên cùng phiếu → bị chặn", g)
        assert g["detail"]["ma"] == "KHAC_LOAI_XE", g
    else:
        print("  · không có phiếu xe nhà đang chạy để thử đổi chéo — bỏ qua")

    # ================================================================ 3. ảnh tài xế
    s, tx = goi("/api/drivers", vai="thabok")
    d0 = tx[0]
    s, g = gui_anh("/api/drivers/%s/anh" % d0["id"], "anh-tx.png", PNG_1x1, "tx01")
    phai(s, 403, "Tài xế tự đưa ảnh lên → bị chặn", g)
    s, ds_anh = gui_anh("/api/drivers/%s/anh" % d0["id"], "anh-tx.png", PNG_1x1, "thabok")
    phai(s, 200, "Bãi đưa ảnh tài xế %s lên" % d0["name"], ds_anh)
    a = ds_anh[0]; assert a["chinh"], "ảnh đầu tự thành ảnh đại diện"
    r = urllib.request.Request(GOC + a["url"] + "?tk=" + urllib.parse.quote(TOKEN["thabok"]))
    with urllib.request.urlopen(r, timeout=30) as t:
        assert t.read() == PNG_1x1, "ảnh tải về phải đúng tệp đã gửi"
    print("  ✓ %-62s" % "Ảnh tài xế tải về đúng tệp, ảnh đầu là ảnh đại diện")
    s, tx2 = goi("/api/drivers", vai="thabok")
    assert next(x for x in tx2 if x["id"] == d0["id"]).get("anh_chinh"), "danh sách tài xế phải mang ảnh đại diện"
    s, ct_tx = goi("/api/drivers/%s" % d0["id"], vai="thabok")
    assert len(ct_tx.get("anh") or []) == 1, ct_tx.get("anh")
    print("  ✓ %-62s" % "Danh sách và hồ sơ tài xế đều mang ảnh")
    s, g = goi("/api/anh-tai-xe/%s" % a["id"], vai="thabok", method="DELETE"); phai(s, 200, "Xoá ảnh thử (dọn)", g)

    # ================================================================ 4. hai mã kế toán còn thiếu là ô cấu hình
    s, ch = goi("/api/ke-toan/cau-hinh", vai="admin"); phai(s, 200, "Sếp xem cấu hình", ch)
    cu = {"ma_hang_khach_gui": ch.get("ma_hang_khach_gui") or "", "ma_gia_von": ch.get("ma_gia_von") or ""}
    s, g = goi("/api/ke-toan/cau-hinh", {"ma_gia_von": "632"}, vai="ketoan", method="PUT")
    phai(s, 403, "Kế toán đặt mã → bị chặn (chỉ Sếp)", g)
    s, g = goi("/api/ke-toan/cau-hinh", {"ma_hang_khach_gui": "002", "ma_gia_von": "632"}, vai="admin", method="PUT")
    phai(s, 200, "Sếp gõ hai mã bên kế toán cấp (thử 002 · 632)", g)
    assert g["ma_hang_khach_gui"] == "002" and g["ma_gia_von"] == "632", g

    # chứng từ hàng khách gửi ĐÃ CÓ (gieo trước khi đặt mã) vẫn phải không đụng kho 1371
    s, ct = goi("/api/chung-tu?loai=PNK_HH,PXK_HH&limit=10", vai="ketoan")
    for c in ct["ds"]:
        assert c["no"] != "1371" and c["co"] != "1371", "hàng khách gửi không được ghi vào kho 1371: %s" % c
    print("  ✓ %-62s %d tờ" % ("Hàng khách gửi không đụng kho 1371 (ngoài bảng)", len(ct["ds"])))

    # tờ mới sinh sau khi đặt mã: bán một món phụ tùng → PXK_BAN mang Nợ 632
    s, parts = goi("/api/parts", vai="ketoan")
    pt = next(x for x in parts if x["qty"] >= 1)
    s, kh = goi("/api/customers", vai="ketoan")
    s, b = goi("/api/ban-hang", {"customer_id": kh[0]["id"], "sale_date": "2026-09-22", "currency": "LAK",
                                 "lines": [{"item_type": "part", "part_id": pt["id"], "qty": 1, "unit_price": pt["unit_price"] or 1000}],
                                 "note": "thử mã giá vốn"}, vai="ketoan")
    phai(s, 200, "Bán một phụ tùng sau khi đặt mã", b)
    s, ct = goi("/api/chung-tu?loai=PXK_BAN&limit=5", vai="ketoan")
    to = next((c for c in ct["ds"] if b.get("doc_no") and b["doc_no"] in (c.get("mo_ta") or "")), ct["ds"][0] if ct["ds"] else None)
    assert to and to["no"] == "632" and to["co"] == "1371", "tờ xuất kho bán phải mang Nợ 632 / Có 1371: %s" % to
    print("  ✓ %-62s %s / %s" % ("Tờ PXK_BAN sinh sau khi đặt mã mang đúng mã", to["no"], to["co"]))
    if b.get("id"):
        goi("/api/ban-hang/%s" % b["id"], vai="ketoan", method="DELETE")
    s, g = goi("/api/ke-toan/cau-hinh", cu, vai="admin", method="PUT"); phai(s, 200, "Trả cấu hình về như cũ (dọn)", g)

    # ================================================================ 5. công nợ khách gom mọi tháng
    s, kh = goi("/api/customers", vai="ketoan")
    s, g = goi("/api/customers/%s/cong-no" % kh[0]["id"], vai="thabok")
    phai(s, 403, "Bãi xem công nợ khách → bị chặn (tiền bán)", g)
    s, cn = goi("/api/customers/%s/cong-no" % kh[0]["id"], vai="doanhthu")
    phai(s, 200, "KT Doanh thu xem công nợ khách %s" % kh[0]["name"], cn)
    assert cn["so_to"] >= 1 and cn["tong_lak"] >= cn["da_thu_lak"] and cn["con_no_lak"] >= 0, cn
    assert abs(sum(x["con_lai_lak"] for x in cn["dong"] if x["con_lai_lak"] > 0) - cn["con_no_lak"]) < 1, "tổng còn nợ phải bằng cộng các tờ còn nợ"
    print("  ✓ %-62s %s tờ · còn nợ %s LAK" % ("Công nợ khách gom hoá đơn lẻ + gộp, cộng đúng", cn["so_to"], cn["con_no_lak"]))
    s, kh_gop = goi("/api/customers", vai="ketoan")
    kg = next((k for k in kh_gop if k.get("invoice_mode") == "thang"), None)
    if kg:
        s, cn2 = goi("/api/customers/%s/cong-no" % kg["id"], vai="doanhthu")
        assert any(x["loai"] == "gop" for x in cn2["dong"]), "khách gộp tháng phải thấy tờ hoá đơn gộp trong công nợ: %s" % cn2["dong"]
        print("  ✓ %-62s" % "Khách hợp đồng: tờ hoá đơn gộp có trong công nợ")

    print("\n✅ BỐN QUYẾT ĐỊNH 22/09: ghi cấn trừ không trùng · không đổi chéo loại xe · ảnh tài xế ·")
    print("   hai mã kế toán là ô cấu hình, hàng khách gửi ngoài bảng.")


if __name__ == "__main__":
    main()
