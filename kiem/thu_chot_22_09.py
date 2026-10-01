# -*- coding: utf-8 -*-
"""Thử BỐN QUYẾT ĐỊNH anh chủ dự án chốt chiều 22/09.

    python kiem/thu_chot_22_09.py [http://127.0.0.1:8010]

  1. **Cấn trừ tháng** — bảng đặt cước cạnh khoản khách trả hộ (thẻ cao tốc · nợ trạm dầu VN). Từ 01/10
     (bỏ phần tiền trang kế toán tạm) GHI cấn trừ là việc của hệ kế toán anh Tune; trang này chỉ đưa bảng tính.
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
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — bán hàng ở trang kế toán (28/09, đợt 6)

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

    # ================================================================ 1. cấn trừ tháng — BẢNG TÍNH ở đây, GHI ở hệ kế toán anh Tune
    # Dữ liệu gieo: khách ຄຳຕຸ້ຍ tháng 8 có dòng dầu VN ghi nợ. 01/10 bỏ phần tiền trang kế toán tạm: phiếu thu "cấn trừ" bên đó
    # (số thử) không còn; bảng cấn trừ chỉ đặt cước cạnh khoản khách trả hộ, ghi cấn trừ là việc của hệ kế toán.
    s, g = goi("/api/bao-cao/can-tru/ghi", {"customer_id": "x", "thang": "2026-08"}, vai="doanhthu")
    phai(s, 409, "Ghi cấn trừ bên trang điều xe → việc của hệ kế toán", g)
    s, g = goi("/api/bao-cao/can-tru?thang=2026-08", vai="thabok")
    phai(s, 403, "Bãi xem bảng cấn trừ → bị chặn (tiền bán)", g)
    s, ct = goi("/api/bao-cao/can-tru?thang=2026-08", vai="doanhthu")
    phai(s, 200, "KT Doanh thu xem bảng cấn trừ tháng 8", ct)
    o = next((x for x in ct["ds"] if x["can_tru_lak"] > 0), None)
    assert o, "phải có khách có khoản trả hộ tháng 8: %s" % ct
    assert o["can_tru_lak"] == o["the_lak"] + o["dau_vn_lak"] and o["con_thu_lak"] == o["cuoc_lak"] - o["can_tru_lak"], o
    assert "da_ghi_lak" not in o, "bảng không còn cột 'đã ghi' của sổ thu trang tạm: %s" % sorted(o)
    print("  ✓ %-62s %s · trả hộ %s · còn thu %s" % ("Bảng cấn trừ: cước − (thẻ khách + trạm dầu VN)", o["customer_name"],
                                                   o["can_tru_lak"], o["con_thu_lak"]))

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

    # tờ mới sinh sau khi đặt mã: bán một món phụ tùng → PXK_BAN mang Nợ 632. Bán hàng ở trang kế toán từ đợt 6: bên
    # đó hỏi sang đây mã giá vốn đang đặt ở cấu hình này.
    s, parts = K.kt("/api/phu-tung", vai="ketoan")
    pt = next(x for x in parts if x["qty"] >= 1)
    s, kh = goi("/api/customers", vai="ketoan")
    s, b = K.kt("/api/ban-hang", {"customer_id": kh[0]["id"], "sale_date": "2026-09-22", "currency": "LAK",
                                  "lines": [{"item_type": "part", "part_id": pt["id"], "qty": 1, "unit_price": pt["unit_price"] or 1000}],
                                  "note": "thử mã giá vốn"}, vai="ketoan")
    phai(s, 200, "Bán một phụ tùng sau khi đặt mã (trang kế toán)", b)
    to = next((v for v in K.to_kho(b.get("doc_no") or "?", "PXK_BAN") if (v.get("lines") or {}).get("doc_no") == b.get("doc_no")), None)
    assert to and to["debit"] == "632" and to["credit"] == "1371", "tờ xuất kho bán phải mang Nợ 632 / Có 1371: %s" % to
    print("  ✓ %-62s %s / %s" % ("Tờ PXK_BAN sinh sau khi đặt mã mang đúng mã", to["debit"], to["credit"]))
    if b.get("id"):
        K.kt("/api/ban-hang/%s" % b["id"], vai="ketoan", method="DELETE")
    s, g = goi("/api/ke-toan/cau-hinh", cu, vai="admin", method="PUT"); phai(s, 200, "Trả cấu hình về như cũ (dọn)", g)

    # ================================================================ 5. công nợ khách — CHỈ ở hệ kế toán anh Tune (01/10)
    s, kh = goi("/api/customers", vai="ketoan")
    s, g = goi("/api/customers/%s/cong-no" % kh[0]["id"], vai="doanhthu")
    phai(s, 404, "Công nợ khách theo sổ trang kế toán tạm → đã gỡ", g)
    s, g = goi("/api/customers-cong-no", vai="thabok")
    phai(s, 403, "Bãi xem công nợ khách → bị chặn (tiền bán)", g)
    s, cn = goi("/api/customers-cong-no", vai="doanhthu")
    phai(s, 200, "KT Doanh thu xem công nợ mọi khách (theo SO bên hệ kế toán)", cn)
    assert all(v.get("nguon") == "he_ke_toan" for v in cn.values()), "công nợ khách chỉ còn nguồn hệ kế toán: %s" % list(cn.values())[:1]

    print("\n✅ BỐN QUYẾT ĐỊNH 22/09: bảng cấn trừ (ghi ở hệ kế toán) · không đổi chéo loại xe · ảnh tài xế ·")
    print("   hai mã kế toán là ô cấu hình, hàng khách gửi ngoài bảng.")


if __name__ == "__main__":
    main()
