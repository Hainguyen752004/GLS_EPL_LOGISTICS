# -*- coding: utf-8 -*-
"""Thử BA MÓN NỢ KỸ THUẬT đã dọn 22/09 (mục 3 tệp CONG_VIEC_CHO_ANH_KHAMPLA_CHOT).

    python kiem/thu_no_ky_thuat.py [http://127.0.0.1:8010]

  · **3.1 — máy chủ không trả giá bán cho vai không được thấy.** Trước đây `/api/trips` và
    `/api/bao-cao/theo-doi` vẫn trả đơn giá, doanh thu, lãi cho mọi vai; giao diện che nhưng mở công
    cụ trình duyệt là đọc được hết. Nay các khoá đó bị **bỏ hẳn** khỏi gói trả về.
  · **3.2 — ảnh xe lưu được**, dùng lại đúng chỗ chứa tệp của phiếu.
  · **3.4 — ô "Việc của tôi" của KT Doanh thu** đếm phiếu đã khoá chưa xuất hoá đơn + hoá đơn chưa
    thu đủ, thay vì luôn là 0 (họ không phụ trách mục nào trên phiếu).
"""
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}
# Ảnh PNG 1×1 thật (đủ để máy chủ nhận là image/png), không cần thư viện ngoài.
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
    """Gửi multipart/form-data bằng tay — bộ kiểm không kéo thêm thư viện ngoài."""
    ranh = "----eplkiem1234567890"
    than = io.BytesIO()
    than.write(("--%s\r\n" % ranh).encode())
    than.write(('Content-Disposition: form-data; name="tep"; filename="%s"\r\n' % ten).encode())
    than.write(b"Content-Type: image/png\r\n\r\n")
    than.write(du)
    than.write(("\r\n--%s--\r\n" % ranh).encode())
    r = urllib.request.Request(GOC + duong, data=than.getvalue(), method="POST", headers={
        "Content-Type": "multipart/form-data; boundary=%s" % ranh,
        "Authorization": "Bearer " + TOKEN[vai]})
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


KHOA_BAN = ("price", "price_ccy", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price")
TINH_BAN = ("doanh_thu", "doanh_thu_lak", "lai", "lai_lak", "tien_thue", "tra_chu_xe", "da_thu_lak", "con_lai_lak")
TINH_CHI = ("tong_chi_lak", "chi", "tan_tinh")


def main():
    for u in ("thabok", "ketoan", "doanhthu", "khotb", "tx01", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            raise SystemExit("Không đăng nhập được %s: %s" % (u, g))
        TOKEN[u] = g["token"]
    print("✓ đăng nhập 6 vai")

    # ================================================================ 3.1 giá bán không ra khỏi máy chủ
    for vai, ten in (("thabok", "Bãi"), ("tx01", "Tài xế"), ("khotb", "Thủ kho")):
        s, ds = goi("/api/trips", vai=vai)
        phai(s, 200, "%s gọi /api/trips" % ten, ds)
        if not ds:
            continue
        lo = sorted({k for p in ds for k in KHOA_BAN if k in p})
        lo_t = sorted({k for p in ds for k in TINH_BAN if k in (p.get("tinh") or {})})
        assert not lo and not lo_t, "%s vẫn nhận khoá tiền bán: %s %s" % (ten, lo, lo_t)
        con = sorted({k for k in TINH_CHI if k in (ds[0].get("tinh") or {})})
        if vai == "thabok":
            # anh Khampla A2 (23/09): Bãi không thấy cả tiền CHI (tổng chi, đơn giá, tỷ giá); tài xế vẫn thấy tạm ứng của mình
            lo_chi = sorted({k for k in ("tong_chi_lak", "chi") if k in (ds[0].get("tinh") or {})})
            lo_dg = [d for p in ds for d in (p.get("expenses") or []) if "unit_price" in d]
            assert not lo_chi and not lo_dg and not any("rate_usd" in p for p in ds), "%s vẫn nhận tiền chi: %s" % (ten, lo_chi)
        else:
            assert len(con) == len(TINH_CHI), "phần CHI PHÍ phải giữ nguyên cho %s: %s" % (ten, con)
    print("  ✓ %-60s" % "Ba vai không thấy tiền bán; Bãi không thấy cả tiền chi")

    s, ds = goi("/api/bao-cao/theo-doi", vai="thabok")
    lo = sorted({k for p in ds for k in KHOA_BAN if k in p})
    assert not lo, "báo cáo Theo dõi vẫn trả tiền bán cho Bãi: %s" % lo
    print("  ✓ %-60s" % "Báo cáo Theo dõi cũng không trả tiền bán cho Bãi")

    s, ds = goi("/api/trips", vai="ketoan")
    p0 = next((p for p in ds if p.get("price")), None)
    assert p0 and p0.get("price_ccy") and p0["tinh"].get("doanh_thu") is not None, \
        "kế toán PHẢI thấy đủ tiền bán — nếu không thì phép lọc đã cắt nhầm cả vai được xem"
    print("  ✓ %-60s %s %s" % ("Kế toán vẫn thấy đủ (phép lọc không cắt nhầm)", p0["price"], p0["price_ccy"]))

    s, g = goi("/api/trips/%s" % p0["id"], vai="thabok")
    assert "price" not in g and "doanh_thu" not in g["tinh"], "xem một phiếu cũng phải lọc: %s" % list(g)[:30]
    print("  ✓ %-60s" % "Xem chi tiết một phiếu cũng lọc đúng như danh sách")

    # ================================================================ 3.2 ảnh xe
    s, xe = goi("/api/vehicles", vai="thabok")
    x0 = xe[0]
    s, g = gui_anh("/api/vehicles/%s/anh" % x0["id"], "thu-anh-xe.png", PNG_1x1, "tx01")
    phai(s, 403, "Tài xế đưa ảnh xe lên → bị chặn", g)
    s, ds_anh = gui_anh("/api/vehicles/%s/anh" % x0["id"], "thu-anh-xe.png", PNG_1x1, "thabok")
    phai(s, 200, "Bãi đưa ảnh xe %s lên" % x0["truck_no"], ds_anh)
    a = ds_anh[0]
    assert a["chinh"], "ảnh đầu tiên phải tự thành ảnh đại diện"
    print("  ✓ %-60s %s" % ("Ảnh đầu tiên tự thành ảnh đại diện", a["filename"]))

    r = urllib.request.Request(GOC + a["url"] + "?tk=" + urllib.parse.quote(TOKEN["thabok"]))
    with urllib.request.urlopen(r, timeout=30) as t:
        du = t.read()
    assert du == PNG_1x1, "ảnh tải về phải đúng tệp đã gửi lên (%d byte)" % len(du)
    print("  ✓ %-60s %d byte" % ("Tải ảnh về đúng bằng tệp đã gửi lên", len(du)))

    try:
        urllib.request.urlopen(urllib.request.Request(GOC + a["url"]), timeout=30)
        raise SystemExit("DỪNG: mở ảnh không có phiên mà vẫn được")
    except urllib.error.HTTPError as e:
        phai(e.code, 401, "Mở ảnh khi chưa đăng nhập → bị chặn")

    s, xe2 = goi("/api/vehicles", vai="thabok")
    assert next(v for v in xe2 if v["id"] == x0["id"]).get("anh_chinh"), "danh sách xe phải mang ảnh đại diện"
    s, ct = goi("/api/vehicles/%s" % x0["id"], vai="thabok")
    assert len(ct.get("anh") or []) == 1, "hồ sơ xe phải kể ảnh: %s" % ct.get("anh")
    print("  ✓ %-60s" % "Danh sách và hồ sơ xe đều mang ảnh")

    s, ds_anh = goi("/api/anh-xe/%s" % a["id"], vai="thabok", method="DELETE")
    phai(s, 200, "Xoá ảnh thử (dọn)", ds_anh)
    assert not ds_anh, "xoá xong không còn ảnh nào"

    # ================================================================ 3.4 việc của tôi của KT Doanh thu
    s, tq = goi("/api/bao-cao/xu-huong", vai="doanhthu")
    xn = tq["xem_nhanh"]
    s, ds = goi("/api/trips", vai="doanhthu")
    mong = len([p for p in ds if p.get("locked") and not p.get("invoiced")]) \
        + len([p for p in ds if p.get("invoiced") and p.get("finance_status") != "paid"])
    # `/api/trips` không lọc tháng còn Tổng quan thì có, nên chỉ kiểm CÓ VIỆC chứ không so bằng nhau.
    assert xn["viec_toi"] > 0 or mong == 0, \
        "KT Doanh thu phải có số việc thật (phiếu chờ hoá đơn + hoá đơn chưa thu), không phải luôn 0"
    print("  ✓ %-60s %s" % ("KT Doanh thu: ô Việc của tôi đã có số thật", xn["viec_toi"]))
    if xn["viec_toi"]:
        assert xn.get("viec_phieu"), "bấm vào ô phải mở thẳng một phiếu cụ thể"
        print("  ✓ %-60s" % "Bấm vào ô mở thẳng phiếu đang chờ")

    s, tq2 = goi("/api/bao-cao/tong-quan", vai="thabok")
    assert "doanh_thu_lak" not in tq2, "Tổng quan của Bãi vẫn không có doanh thu (giữ như cũ)"
    print("\n✅ NỢ KỸ THUẬT: giá bán không ra khỏi máy chủ với vai không được xem · ảnh xe lưu được ·")
    print("   ô Việc của tôi của KT Doanh thu đã đếm đúng việc của họ.")


if __name__ == "__main__":
    main()
