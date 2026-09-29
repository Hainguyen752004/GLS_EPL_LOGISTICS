# -*- coding: utf-8 -*-
"""PHIẾU MẪU ĐI TRỌN A → Z (29/09) — để chủ dự án mở cho sếp xem bằng nhiều vai và xem bút toán ở sổ.

Một phiếu GOM mỏ → bãi và một phiếu GIAO lấy hàng từ lô đó ra cảng, đi đúng thứ tự mục 10.0b của tài liệu A → Z, qua API
của hai trang, MỖI BƯỚC BẰNG ĐÚNG VAI người bấm (Bãi, kế toán, KT chi phí, thủ kho, KT kho xăng dầu, quỹ, tài xế, KT doanh
thu). Máy chủ kiểm và chặn như khi bấm tay — không ghi thẳng DB. Xong thì hai phiếu đã khoá, đã lập hoá đơn, đã thu đủ,
chứng từ của hai phiếu đã đẩy sang sổ.

    python tools/phieu_mau_a_z.py                                        chạy thử: kiểm điều kiện, kể ra sẽ làm gì — KHÔNG ghi
    python tools/phieu_mau_a_z.py http://127.0.0.1:8020 http://127.0.0.1:8030 that     làm thật

Cố ý KHÔNG dùng xe 343 / 344, tài xế tx01 / tx02 của bài bấm tay 10.0b (chủ dự án đang bấm theo số km 61.200 / 58.800 của
hai xe đó): phiếu mẫu dùng xe 345 (gom), 346 (giao), tài xế tx03, số tấn riêng. Chỉ đẩy chứng từ của HAI phiếu mẫu — không
bấm "Đẩy hết" (sẽ cuốn cả tờ của phiếu đang test tay). Hôm nay đã có phiếu mẫu (ghi chú bắt đầu bằng GHI_CHU) thì dừng.
"""
import datetime as dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

DX = next((a for a in sys.argv[1:] if a.startswith("http") and a.rstrip("/").endswith(("8020", "8011"))), "http://127.0.0.1:8020").rstrip("/")
KT = next((a for a in sys.argv[1:] if a.startswith("http") and a.rstrip("/").endswith(("8030", "8031"))), "http://127.0.0.1:8030").rstrip("/")
THAT = "that" in sys.argv[1:]
CHO_TRUNG = "cho_trung" in sys.argv[1:]          # chỉ dùng trên máy thử: lập thêm một cặp dù hôm nay đã có
HOM_NAY = dt.date.today().isoformat()
GHI_CHU = "Phiếu mẫu A→Z"
XE_GOM, XE_GIAO, TAI_XE = "345", "346", "tx03"
KHACH, TUYEN_GOM, TUYEN_GIAO = "ຄຳຕຸ້ຍ", "ກາສີ → ທ່າບົກ", "ທ່າບົກ → ທ່າເຮືອກະລໍ"
CAN_MO, CAN_BAI, TAN_GIAO, CAN_CANG = 42, 41.5, 30, 29.7
LIT_GOM, LIT_GIAO = 200, 300
GIA_IV = {"x_water": 60000, "x_vn": 430000, "x_chip_lao": 620000, "x_trip": 1800000, "x_phone": 150000}
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
TK = {}
BUOC = [0]


def goi(goc, duong, than=None, vai=None, cach=None):
    du = json.dumps(than).encode("utf-8") if than is not None else None
    r = urllib.request.Request(goc + duong, data=du, method=cach or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[(goc, vai)]} if vai else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def gui_tep(duong, vai, truong, tep=()):
    b = uuid.uuid4().hex
    than = b"".join(b"--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b.encode(), k.encode(), str(v).encode("utf-8"))
                    for k, v in truong.items())
    for ten_o, ten_tep, kieu, du in tep:
        than += b"--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (
            b.encode(), ten_o.encode(), ten_tep.encode(), kieu.encode()) + du + b"\r\n"
    than += b"--%s--\r\n" % b.encode()
    r = urllib.request.Request(DX + duong, data=than, method="POST",
                               headers={"Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + TK[(DX, vai)]})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def phai(s, g, viec, vai):
    BUOC[0] += 1
    if s != 200:
        raise SystemExit("DỪNG ở bước %d — %s (%s): %s %s" % (BUOC[0], viec, vai, s, json.dumps(g, ensure_ascii=False)[:500]))
    print("  %2d. %-9s %s" % (BUOC[0], vai, viec), flush=True)
    return g


def dang_nhap(goc, u):
    s, g = goi(goc, "/api/dang-nhap", {"username": u, "password": "1234"})
    if s != 200:
        raise SystemExit("Không đăng nhập được %s ở %s: %s" % (u, goc, g))
    TK[(goc, u)] = g["token"]
    return g["user"]


TEN_MUC = {"info": "I", "trans": "II", "fuel": "III", "travel": "IV"}
TEN_HD = {"send": "Gửi kiểm tra", "verify": "Xác nhận kiểm tra", "book": "Ghi sổ kế toán"}


def muc(pid, m, hd, vai):
    return phai(*goi(DX, "/api/trips/%s/sections/%s/%s" % (pid, m, hd), {}, vai), "mục %s · %s" % (TEN_MUC[m], TEN_HD[hd]), vai)


def so(x):
    return format(round(x or 0), ",").replace(",", ".")


def nhap_gia_iv(pid):
    """KT Chi phí gõ đơn giá như tờ Excel (chỉ các dòng Bãi đã khai; phí cao tốc máy đã điền theo tuyến)."""
    s, p = goi(DX, "/api/trips/%s" % pid, vai="ketoancp")
    dong = [{"id": e["id"], "section": "travel", "unit_price": GIA_IV[e["item_key"]], "currency": "LAK"}
            for e in p["expenses"] if e["section"] == "travel" and e["item_key"] in GIA_IV]
    p = phai(*goi(DX, "/api/trips/%s" % pid, {"expenses": dong}, "ketoancp", "PUT"), "mục IV · gõ đơn giá như Excel → Lưu", "ketoancp")
    return sum((e["qty"] or 0) * (e["unit_price"] or 0) for e in p["expenses"] if e["section"] == "travel")


def cap_va_chi(pid):
    """Bãi in tờ tạm ứng (lúc này mục IV đã có giá — tờ PTU ra đúng số ngay), thủ kho cấp dầu theo phiếu lĩnh, KT kho
    xăng dầu kiểm + ghi sổ mục III, quỹ chi tạm ứng theo tờ QR."""
    phai(*goi(DX, "/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "thabok"), "Phiếu chi tạm ứng (tờ QR) → In", "thabok")
    s, ds = goi(DX, "/api/trips/%s/vouchers" % pid, vai="ketoancp")
    linh = next(v for v in ds if v["kind"] == "fuel")
    phai(*goi(DX, "/api/vouchers/%s/cap" % linh["id"], {"qty": linh["qty_l"]}, "khotb"),
         "Kho → Cấp phát · Cấp dầu %s lít (%s)" % (so(linh["qty_l"]), linh["doc_no"]), "khotb")
    muc(pid, "fuel", "verify", "khonl")
    muc(pid, "fuel", "book", "khonl")
    s, ds = goi(DX, "/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "ketoancp")
    tu = ds[0]
    phai(*goi(DX, "/api/vouchers/%s/cap" % tu["id"], {}, "quytb"),
         "Kho → Cấp phát · Chi tiền tạm ứng %s LAK (%s)" % (so(tu["amount_lak"]), tu["doc_no"]), "quytb")
    return tu["amount_lak"]


def dong_iv(bo=()):
    return [{"section": "travel", "item_key": k, "qty": 1, "unit_price": 0, "currency": "LAK", "paid_by_epl": True}
            for k in ("x_water", "x_vn", "x_chip_lao", "x_trip", "x_phone") if k not in bo]


def main():
    print("Trang điều xe %s · trang kế toán %s · %s" % (DX, KT, "LÀM THẬT" if THAT else "chạy thử (không ghi)"))
    nguoi = {u: dang_nhap(DX, u) for u in ("thabok", "ketoan", "ketoancp", "khonl", "khotb", "quytb", TAI_XE, "admin")}
    dang_nhap(KT, "doanhthu")
    dang_nhap(KT, "ketoan")
    s, xe = goi(DX, "/api/vehicles", vai="admin")
    s, tuyen = goi(DX, "/api/routes", vai="admin")
    s, kh = goi(DX, "/api/customers", vai="admin")
    s, diem = goi(DX, "/api/fuel-places", vai="admin")
    xg, xd = (next(v for v in xe if v["truck_no"] == n) for n in (XE_GOM, XE_GIAO))
    tg, td = (next(r for r in tuyen if r["name"] == n) for n in (TUYEN_GOM, TUYEN_GIAO))
    khach = next(k for k in kh if k["name"] == KHACH)
    kho = next(d for d in diem if d["id"] == nguoi["khotb"]["place_id"])
    s, hom_nay = goi(DX, "/api/trips?tu=%s&den=%s&co=500" % (HOM_NAY, HOM_NAY), vai="admin")
    da_co = [p["doc_no"] for p in hom_nay if (p.get("note") or "").startswith(GHI_CHU)]
    print("Xe gom %s (%s, km %s) · xe giao %s (%s, km %s) · tài xế %s" % (
        XE_GOM, xg["status"], so(xg.get("odometer_km")), XE_GIAO, xd["status"], so(xd.get("odometer_km")), nguoi[TAI_XE]["full_name"]))
    print("Tuyến gom %s (%s + %s km) · tuyến giao %s (%s + %s km, BOT %s) · kho lĩnh dầu %s" % (
        TUYEN_GOM, so(tg["total_km"]), so(tg.get("return_km")), TUYEN_GIAO, so(td["total_km"]), so(td.get("return_km")),
        so(td.get("toll_lak")), kho["name"]))
    if da_co and not CHO_TRUNG:
        raise SystemExit("Hôm nay đã có phiếu mẫu (%s) — không lập trùng." % ", ".join(da_co))
    if not THAT:
        print("\nSẼ LÀM: phiếu GOM (xe %s, %s) mỏ %s t → bãi %s t, và phiếu GIAO (xe %s) %s t từ lô đó → cảng %s t; đủ các bước"
              " kiểm, cấp dầu, chi tạm ứng, xe đi, xe về, khoá, hoá đơn, thu đủ, đẩy chứng từ hai phiếu.\n"
              "(chạy thử — chưa ghi gì; thêm 'that' để làm thật)" % (XE_GOM, TUYEN_GOM, CAN_MO, CAN_BAI, XE_GIAO, TAN_GIAO, CAN_CANG))
        return
    tx = nguoi[TAI_XE]

    # ================================================================ PHIẾU GOM
    print("\n— A. Phiếu GOM %s —" % TUYEN_GOM)
    g = phai(*goi(DX, "/api/trips", {
        "kind": "gom", "company": "EPL", "vehicle_id": xg["id"], "driver_id": tx["driver_id"], "route_id": tg["id"],
        "customer_id": khach["id"], "goods_type": "iron_ore", "doc_date": HOM_NAY, "out_date": HOM_NAY,
        "odo_out": xg.get("odometer_km"), "note": GHI_CHU + " · phiếu gom",
        "expenses": [{"section": "fuel", "item_key": "diesel", "qty": LIT_GOM, "place_id": kho["id"], "paid_by_epl": True}] + dong_iv()},
        "thabok"), "Phiếu mới · Gom · xe %s · dầu %s L · mục IV 5 dòng · Lưu" % (XE_GOM, LIT_GOM), "thabok")
    gid, gso = g["id"], g["doc_no"]
    print("      → %s · km lúc đi %s · km về ước tính %s" % (gso, so(g.get("odo_out")), so(g.get("odo_est"))))
    for m in ("info", "fuel", "travel"):
        muc(gid, m, "send", "thabok")
    phai(*goi(DX, "/api/trips/%s/vouchers" % gid, {"kind": "fuel"}, "thabok"), "Phiếu lĩnh nhiên liệu (tờ QR)", "thabok")
    muc(gid, "info", "verify", "ketoan")
    print("      → tổng mục IV %s LAK" % so(nhap_gia_iv(gid)))
    muc(gid, "travel", "verify", "ketoancp")
    muc(gid, "travel", "book", "ketoancp")
    tu_gom = cap_va_chi(gid)
    phai(*goi(DX, "/api/trips/%s/transport-status" % gid, {"status": "transit"}, TAI_XE), "Phiếu của tôi · Xuất phát", TAI_XE)
    phai(*gui_tep("/api/trips/%s/bao-can-mo" % gid, TAI_XE, {"tan": str(CAN_MO), "ghi_chu": "phiếu cân mỏ ກາສີ",
                                                             "ma_gui": uuid.uuid4().hex[:12]},
                  [("anh", "phieu-can-mo.png", "image/png", PNG)]),
         "Báo cân ở mỏ · %s t · 1 ảnh phiếu cân" % CAN_MO, TAI_XE)
    muc(gid, "trans", "send", "thabok")
    phai(*goi(DX, "/api/trips/%s" % gid, {"ore_bill_no": "MAU-2909-01", "ore_bill_date": HOM_NAY}, "ketoan", "PUT"),
         "mục II · Số phiếu quặng MAU-2909-01 → Lưu", "ketoan")
    muc(gid, "trans", "verify", "ketoan")
    km_ve = round((xg.get("odometer_km") or 0) + (tg["total_km"] or 0) + (tg.get("return_km") or 0))
    phai(*goi(DX, "/api/trips/%s/bao-ve" % gid, {"back_date": HOM_NAY, "odo_back": km_ve}, TAI_XE), "Báo đã về · km %s" % so(km_ve), TAI_XE)
    phai(*goi(DX, "/api/trips/%s/transport-status" % gid, {"status": "arrived", "weight_origin": CAN_MO, "weight_dest": CAN_BAI,
                                                           "back_date": HOM_NAY, "odo_back": km_ve}, "thabok"),
         "Xe đã tới · cân tại bãi %s t → hàng vào kho" % CAN_BAI, "thabok")
    g = phai(*goi(DX, "/api/trips/%s/khoa" % gid, {"xac_nhan": True}, "ketoan"), "🔒 Khoá phiếu", "ketoan")
    if g.get("canh_bao"):
        print("      → cảnh báo lúc khoá: %s" % "; ".join(c["loi"] for c in g["canh_bao"]))

    # ================================================================ PHIẾU GIAO
    print("\n— B. Phiếu GIAO %s, lấy hàng từ lô %s —" % (TUYEN_GIAO, gso))
    s, gg = goi(DX, "/api/trips/%s" % gid, vai="thabok")
    ten_hang = next(x["goods_name"] for x in gg["goods"] if x["loai"] == "hang")
    t = phai(*goi(DX, "/api/trips", {
        "kind": "giao", "company": "EPL", "vehicle_id": xd["id"], "driver_id": tx["driver_id"], "route_id": td["id"],
        "customer_id": khach["id"], "goods_type": "iron_ore", "doc_date": HOM_NAY, "out_date": HOM_NAY,
        "odo_out": xd.get("odometer_km"), "note": GHI_CHU + " · phiếu giao",
        "goods": [{"loai": "hang", "goods_name": ten_hang, "qty_t": TAN_GIAO, "tu_phieu_id": gid}],
        "expenses": [{"section": "fuel", "item_key": "diesel", "qty": LIT_GIAO, "place_id": kho["id"], "paid_by_epl": True}]
        + dong_iv(bo=("x_chip_lao",))}, "thabok"),
        "Phiếu mới · Giao · xe %s · %s t từ lô %s · dầu %s L · Lưu" % (XE_GIAO, TAN_GIAO, gso, LIT_GIAO), "thabok")
    tid, tso = t["id"], t["doc_no"]
    print("      → %s · cân đầu %s t · km về ước tính %s" % (tso, t.get("weight_origin"), so(t.get("odo_est"))))
    for m in ("info", "trans", "fuel", "travel"):
        muc(tid, m, "send", "thabok")
    phai(*goi(DX, "/api/trips/%s/vouchers" % tid, {"kind": "fuel"}, "thabok"), "Phiếu lĩnh nhiên liệu (tờ QR)", "thabok")
    phai(*goi(DX, "/api/trips/%s" % tid, {"ore_bill_no": "MAU-2909-02", "ore_bill_date": HOM_NAY}, "ketoan", "PUT"),
         "mục II · Số phiếu quặng MAU-2909-02 → Lưu", "ketoan")
    muc(tid, "info", "verify", "ketoan")
    muc(tid, "trans", "verify", "ketoan")
    print("      → tổng mục IV %s LAK (gồm phí cao tốc máy điền theo tuyến)" % so(nhap_gia_iv(tid)))
    muc(tid, "travel", "verify", "ketoancp")
    muc(tid, "travel", "book", "ketoancp")
    tu_giao = cap_va_chi(tid)
    phai(*goi(DX, "/api/trips/%s/transport-status" % tid, {"status": "transit"}, TAI_XE), "Phiếu của tôi · Xuất phát", TAI_XE)
    phai(*gui_tep("/api/trips/%s/giao-nhan" % tid, TAI_XE, {"nguoi_nhan": "ນາງ ມະນີ", "sdt": "020 5555 0101", "tinh_trang": "du",
                                                             "ma_gui": uuid.uuid4().hex[:12]},
                  [("chu_ky", "chu-ky.png", "image/png", PNG), ("anh", "bien-ban.png", "image/png", PNG)]),
         "Giao hàng hoàn tất · ký nhận ນາງ ມະນີ · 1 ảnh biên bản", TAI_XE)
    km_ve2 = round((xd.get("odometer_km") or 0) + (td["total_km"] or 0) + (td.get("return_km") or 0))
    phai(*goi(DX, "/api/trips/%s/bao-ve" % tid, {"back_date": HOM_NAY, "odo_back": km_ve2}, TAI_XE), "Báo đã về · km %s" % so(km_ve2), TAI_XE)
    phai(*goi(DX, "/api/trips/%s/transport-status" % tid, {"status": "arrived", "weight_dest": CAN_CANG, "back_date": HOM_NAY,
                                                           "odo_back": km_ve2, "pod_receiver": "ນາງ ມະນີ"}, "thabok"),
         "Xe đã tới · cân cuối tại cảng %s t" % CAN_CANG, "thabok")
    t = phai(*goi(DX, "/api/trips/%s/khoa" % tid, {"xac_nhan": True}, "ketoan"), "🔒 Khoá phiếu", "ketoan")
    if t.get("canh_bao"):
        print("      → cảnh báo lúc khoá: %s" % "; ".join(c["loi"] for c in t["canh_bao"]))

    # ================================================================ HOÁ ĐƠN, THU TIỀN (trang kế toán)
    print("\n— C. Hoá đơn, thu tiền (trang kế toán, doanhthu) —")
    for pid, so_p, hai_lan in ((gid, gso, False), (tid, tso, True)):
        h = phai(*goi(KT, "/api/hoa-don/phieu/%s/xuat" % pid, {}, "doanhthu"), "Lập hóa đơn thu · %s" % so_p, "doanhthu")["hoa_don"]
        print("      → %s t × %s %s = %s %s (%s LAK)" % (h["tan_tinh"], h["price"], h["ccy"], h["doanh_thu"], h["ccy"], so(h["doanh_thu_lak"])))
        lan = [400, None] if hai_lan else [None]
        for i, a in enumerate(lan, 1):
            a = a if a is not None else h["con_lai"]
            h = phai(*goi(KT, "/api/hoa-don/phieu/%s/thu" % pid, {"amount": a, "currency": h["ccy"], "pay_date": HOM_NAY, "method": "bank",
                                                                  "ref": "UNC-MAU-%s-%d" % (so_p.split("/")[0], i)}, "doanhthu"),
                     "Ghi một lần thu · %s %s (lần %d/%d)" % (a, h["ccy"], i, len(lan)), "doanhthu")["hoa_don"]
        print("      → %s · còn lại %s %s" % (h["finance_status"], h["con_lai"], h["ccy"]))

    # ================================================================ ĐẨY CHỨNG TỪ HAI PHIẾU (không bấm "Đẩy hết")
    print("\n— D. Đẩy chứng từ của hai phiếu mẫu sang sổ (ketoan, trang điều xe) —")
    for pid in (gid, tid):
        s, r = goi(DX, "/api/chung-tu?trip_id=%s" % pid, vai="ketoan")
        for c in sorted(r["ds"], key=lambda c: (c["ngay"] or "", c["loai"])):
            if not c["da_day"]:
                s, loi = goi(DX, "/api/chung-tu/%s/day" % c["id"], {}, "ketoan")
                if s != 200:
                    raise SystemExit("Đẩy hỏng %s %s: %s %s" % (c["loai"], c["so"], s, loi))
            print("      %-6s %-28s %14s LAK  Nợ %-10s Có %-10s %s" % (c["loai"], c["so"], so(c["tien_lak"]),
                                                                    c["no"] or "", c["co"] or "", "đã đẩy trước" if c["da_day"] else "vừa đẩy"))

    # ================================================================ SỔ KẾ TOÁN
    for so_p in (gso, tso):
        s, nk = goi(KT, "/api/so/nhat-ky?q=%s&moi_trang=200" % urllib.parse.quote(so_p), vai="ketoan")
        print("\n— Sổ kế toán · Nhật ký chung · %s · %d bút toán —" % (so_p, nk.get("n", 0)))
        for e in sorted(nk.get("ds", []), key=lambda e: (e.get("date") or "", e.get("code") or "")):
            dong = " · ".join("%s %s %s" % ("Nợ" if (x.get("debit") or 0) else "Có", x["acc"], so(x.get("debit") or x.get("credit")))
                              for x in e.get("lines", []))
            print("    %-12s %-8s %-46s %s" % (e.get("code"), e.get("doc_type"), (e.get("desc") or "")[:46], dong))

    # ================================================================ MỖI VAI THẤY GÌ
    print("\n— E. Mỗi vai mở phiếu %s thấy gì —" % tso)
    for vai in ("thabok", TAI_XE, "ketoan", "ketoancp", "admin"):
        s, p = goi(DX, "/api/trips/%s" % tid, vai=vai)
        tinh = p.get("tinh") or {}
        tien_iv = [e.get("unit_price") for e in p.get("expenses", []) if e["section"] == "travel"]
        print("    %-9s giá cước %-6s doanh thu %-10s đơn giá mục IV %s" % (vai, p.get("price"), tinh.get("doanh_thu"), tien_iv))
    print("\nXONG — phiếu gom %s (tạm ứng %s LAK) · phiếu giao %s (tạm ứng %s LAK)" % (gso, so(tu_gom), tso, so(tu_giao)))


if __name__ == "__main__":
    main()
