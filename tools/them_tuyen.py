# -*- coding: utf-8 -*-
"""THÊM TUYẾN MẪU CÓ CHIỀU VỀ cho bản demo (29/09) — đi qua API của trang điều xe, đúng như người dùng bấm ở màn
Tuyến đường và bảng giá khách × tuyến: máy chủ kiểm từng ô như lúc nhập tay, không ghi thẳng DB.

    python tools/them_tuyen.py [địa chỉ=http://127.0.0.1:8020]          chạy thử: kể ra sẽ thêm gì, KHÔNG ghi
    python tools/them_tuyen.py [địa chỉ] that                           thêm thật

Hai tuyến GOM (mỏ → bãi Thà Bốc, xe chạy rỗng từ bãi lên mỏ rồi chở hàng về) và ba tuyến GIAO (bãi → khách / cảng /
cửa khẩu, xe chạy rỗng về bãi). Các điểm trên tuyến là đường HÀNG đi; "Km chiều về" là đoạn xe chạy không hàng, nên
km về ước tính trên phiếu = km lúc đi + chiều đi + chiều về. Tên điểm, toạ độ dùng lại đúng các điểm của tuyến đã có
(ກາສີ, ທ່າບົກ, ດ່ານ ນໍ້າພາວ, ທ່າເຮືອກະລໍ). Km, BOT, giá là SỐ MẪU — anh sửa ở màn Tuyến đường, Danh mục → Khách hàng.

Kèm giá cước cho 3 khách đang có trên 5 tuyến mới (để phiếu lập trên tuyến mới tự ra giá như tuyến cũ): giá theo tấn
tỷ lệ với km, lấy mốc tuyến cũ ກາສີ → ກາລໍ 485 km · 41 USD/t · thuê xe liên kết 40,5 USD/t.
Cái nào đã có (cùng tên tuyến; cùng khách × tuyến × loại hàng) thì bỏ qua — chạy lại bao nhiêu lần cũng không trùng.
Cần máy chủ đã khởi động lại bản có "Km chiều về" (29/09); chưa thì công cụ dừng và nói rõ.
"""
import json
import sys
import urllib.error
import urllib.request

GOC = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:8020").rstrip("/")
THAT = "that" in sys.argv[1:]

KASI, THABOK = ("ກາສີ (ບ່ອນຂຸດແຮ່)", 19.15, 102.25), ("ທ່າບົກ (ສະໜາມ EPL)", 18.44, 103.15)
NAMPHAO, CANG = ("ດ່ານ ນໍ້າພາວ", 18.38, 105.11), ("ທ່າເຮືອກະລໍ", 18.07, 106.42)
XIENG, VIENG = ("ຊຽງຂວາງ (ບ່ອນຂຸດແຮ່)", 19.45, 103.19), ("ນະຄອນຫຼວງວຽງຈັນ", 17.97, 102.63)
GOM, GIAO = "ເກັບ (ບໍ່ແຮ່ → ສາງ)", "ສົ່ງ (ສາງ → ລູກຄ້າ)"      # đúng chữ ô Loại phiếu trên màn
# tên tuyến, các điểm (điểm, km từ điểm trước), km chiều về, BOT (LAK, cả đi và về), ghi chú
TUYEN = [
    ("ກາສີ → ທ່າບົກ", [(KASI, 0), (THABOK, 145)], 145, 0, GOM),
    ("ຊຽງຂວາງ → ທ່າບົກ", [(XIENG, 0), (THABOK, 260)], 260, 0, GOM),
    ("ທ່າບົກ → ທ່າເຮືອກະລໍ", [(THABOK, 0), (NAMPHAO, 210), (CANG, 150)], 360, 3667000, GIAO),
    ("ທ່າບົກ → ດ່ານ ນໍ້າພາວ", [(THABOK, 0), (NAMPHAO, 210)], 210, 0, GIAO),
    ("ທ່າບົກ → ວຽງຈັນ", [(THABOK, 0), (VIENG, 95)], 95, 0, GIAO),
]
MOC_KM, MOC_GIA, MOC_THUE = 485, 41.0, 40.5


def gia(km):
    """Giá theo tấn tỷ lệ với km chiều đi so với mốc tuyến cũ, làm tròn 0,5 USD; giá thuê xe liên kết kém 0,5."""
    g = max(round(MOC_GIA * km / MOC_KM * 2) / 2, 5.0)
    return g, g - (MOC_GIA - MOC_THUE)


def goi(duong, than=None, tk=None, cach=None):
    du = json.dumps(than).encode("utf-8") if than is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=cach or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tk} if tk else {})})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def phai(s, g, viec):
    if s != 200:
        raise SystemExit("DỪNG — %s: %s %s" % (viec, s, json.dumps(g, ensure_ascii=False)[:300]))
    return g


def main():
    tk_bai = phai(*goi("/api/dang-nhap", {"username": "thabok", "password": "1234"}), "đăng nhập thabok")["token"]
    tk_kt = phai(*goi("/api/dang-nhap", {"username": "ketoan", "password": "1234"}), "đăng nhập ketoan")["token"]
    ds = phai(*goi("/api/routes", tk=tk_bai), "đọc tuyến")
    if ds and "return_km" not in ds[0]:
        raise SystemExit("DỪNG — máy %s chưa chạy bản có Km chiều về: khởi động lại máy rồi chạy lại." % GOC)
    co_ten = {r["name"]: r for r in ds}
    moi = [t for t in TUYEN if t[0] not in co_ten]
    print("Máy %s · %d tuyến đang có" % (GOC, len(ds)))
    for ten, diem, ve, bot, ghi in TUYEN:
        di = sum(k for _, k in diem)
        print("  %s %-26s đi %3d km · về %3d km · cả chuyến %3d km · BOT %s LAK · giá %s / thuê %s USD/t · %s"
              % ("+" if ten not in co_ten else "=", ten, di, ve, di + ve, format(bot, ","), *gia(di), ghi))
    kh = phai(*goi("/api/customers", tk=tk_kt), "đọc khách")
    print("%s: %d tuyến mới (= là đã có, bỏ qua) · giá cước %d khách × 5 tuyến (dòng đã có thì bỏ qua)"
          % ("THÊM" if THAT else "SẼ THÊM", len(moi), len(kh)))
    if not THAT:
        print("\n(chạy thử — chưa ghi gì; thêm tham số 'that' để thêm thật)")
        return

    for ten, diem, ve, bot, ghi in moi:
        than = {"name": ten, "toll_lak": bot, "return_km": ve, "note": ghi,
                "stops": [{"name": d[0], "km_from_prev": k, "lat": d[1], "lng": d[2]} for d, k in diem]}
        r = phai(*goi("/api/routes", than, tk_bai), "thêm tuyến " + ten)
        co_ten[ten] = r
        print("  ✓ tuyến %-26s %s km đi · %s km về" % (ten, r["total_km"], r["return_km"]))
    so_gia = 0
    for k in kh:
        cu = phai(*goi("/api/customers/%s/bang-gia" % k["id"], tk=tk_kt), "đọc giá " + k["name"])
        da = {(g["route_id"], g.get("goods_type") or "iron_ore") for g in cu}
        for ten, diem, *_ in TUYEN:
            rid = co_ten[ten]["id"]
            if (rid, "iron_ore") in da:
                continue
            g, thue = gia(sum(km for _, km in diem))
            phai(*goi("/api/customers/%s/bang-gia" % k["id"], {"route_id": rid, "goods_type": "iron_ore", "price": g, "price_ccy": "USD",
                                                               "price_mode": "ton", "hire_price": thue, "hire_ccy": "USD",
                                                               "valid_from": "2026-01-01", "note": "giá mẫu 29/09"}, tk_kt),
                 "thêm giá %s · %s" % (k["name"], ten))
            so_gia += 1
    print("  ✓ %d dòng giá cước mới" % so_gia)
    print("\nĐÃ THÊM — xem ở Danh mục → Tuyến đường và Danh mục → Khách hàng → Bảng giá.")


if __name__ == "__main__":
    main()
