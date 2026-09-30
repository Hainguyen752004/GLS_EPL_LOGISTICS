# -*- coding: utf-8 -*-
"""BỘ CHI PHÍ GỢI Ý cho 5 tuyến mẫu (30/09 — sếp: "dựa vào Excel kê sẵn chi phí cho họ kiểu gợi ý").

    python tools/mau_chi_phi_tuyen.py [http://127.0.0.1:8020]            chạy thử: in ra sẽ điền gì, KHÔNG ghi
    python tools/mau_chi_phi_tuyen.py [http://127.0.0.1:8020] that       ghi thật (qua API, bằng tài khoản ketoan)

Chỉ điền tuyến CHƯA có bộ riêng — tuyến đã có (người dùng tự đặt) thì để nguyên. Tuyến không có ở đây (hai tuyến một chặng
cũ ra thẳng cảng) dùng bộ chung theo Excel của máy chủ. Nguồn số:
  · ທ່າບົກ → ທ່າເຮືອກະລໍ (ra cảng Việt Nam): ĐÚNG tờ Excel mẫu ໃບບິນອອກລົດ — 100 L kho Thà Bốc + 750 L dầu Việt Nam qua kho xe,
    mục IV từng dòng như tờ (phí cao tốc là ô BOT của tuyến, không nằm đây).
  · Tuyến gom / nội địa: chỉ khoản Excel có giá mà hợp chuyến (tiền nước, điện thoại; chipping Lào ở tuyến ra cửa khẩu);
    TIỀN CHUYẾN để trống giá — Excel chỉ có số của chuyến ra cảng, kế toán gõ khi kiểm. Số lít dầu là SỐ MẪU theo km
    (≈ 0,7 L/km cả chuyến, như chuyến mẫu 200 L / 290 km) — anh sửa ở màn Tuyến đường.
"""
import json
import sys
import urllib.error
import urllib.request

GOC = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:8020").rstrip("/")
THAT = "that" in sys.argv[1:]
TK = {}

NUOC, DIEN_THOAI = ("x_water", 60000), ("x_phone", 150000)
MAU = {
    "ກາສີ → ທ່າບົກ": ([("KHO-TB", 200)], [NUOC, ("x_trip", None), DIEN_THOAI]),
    "ຊຽງຂວາງ → ທ່າບົກ": ([("KHO-TB", 360)], [NUOC, ("x_trip", None), DIEN_THOAI]),
    "ທ່າບົກ → ທ່າເຮືອກະລໍ": ([("KHO-TB", 100), ("KHO-XE-VN", 750)],
                         [NUOC, ("x_vn", 430000), ("x_chip_lao", 620000), ("x_chip_vn", 1500000), ("x_trip", 1800000), DIEN_THOAI]),
    "ທ່າບົກ → ດ່ານ ນໍ້າພາວ": ([("KHO-TB", 300)], [NUOC, ("x_chip_lao", 620000), ("x_trip", None), DIEN_THOAI]),
    "ທ່າບົກ → ວຽງຈັນ": ([("KHO-TB", 140)], [NUOC, ("x_trip", None), DIEN_THOAI]),
}


def goi(duong, than=None, cach=None):
    du = json.dumps(than).encode("utf-8") if than is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=cach or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK["t"]} if "t" in TK else {})})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def main():
    s, g = goi("/api/dang-nhap", {"username": "ketoan", "password": "1234"})
    if s != 200:
        raise SystemExit("Không đăng nhập được ketoan: %s" % g)
    TK["t"] = g["token"]
    s, diem = goi("/api/fuel-places")
    ma_diem = {d.get("code"): d["id"] for d in diem}
    s, tuyen = goi("/api/routes")
    print("Máy %s · %s" % (GOC, "GHI THẬT" if THAT else "chạy thử (không ghi)"))
    for ten, (dau, di_duong) in MAU.items():
        r = next((x for x in tuyen if x["name"] == ten), None)
        if r is None:
            print("  · %-24s không có tuyến này — bỏ qua" % ten)
            continue
        if r.get("cost_template"):
            print("  · %-24s đã có bộ riêng (%d dòng) — để nguyên" % (ten, len(r["cost_template"])))
            continue
        ds = [{"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": ma_diem[ma]} for ma, lit in dau if ma in ma_diem]
        ds += [{"section": "travel", "item_key": k, "qty": 1, **({"unit_price": g, "currency": "LAK"} if g is not None else {})}
               for k, g in di_duong]
        mo_ta = "dầu " + " + ".join("%s L %s" % (lit, ma) for ma, lit in dau) + " · " + ", ".join(
            "%s %s" % (k, format(g, ",") if g is not None else "(kế toán gõ)") for k, g in di_duong)
        if THAT:
            s, g = goi("/api/routes/%s" % r["id"], {"cost_template": ds}, "PUT")
            if s != 200:
                raise SystemExit("Ghi hỏng %s: %s %s" % (ten, s, g))
        print("  %s %-24s %s" % ("✓" if THAT else "→", ten, mo_ta))
    if not THAT:
        print("(chạy thử — chưa ghi gì; thêm 'that' để ghi thật)")


if __name__ == "__main__":
    main()
