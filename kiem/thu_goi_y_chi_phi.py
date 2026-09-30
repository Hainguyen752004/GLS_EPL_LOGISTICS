# -*- coding: utf-8 -*-
"""Thử GỢI Ý CHI PHÍ THEO TUYẾN (sếp 30/09: "dựa vào Excel kê sẵn chi phí cho họ kiểu gợi ý, họ thêm bớt chỉnh sửa").

    python kiem/thu_goi_y_chi_phi.py [http://127.0.0.1:8011]

Cần chạy tools/mau_chi_phi_tuyen.py ... that trên máy đó trước (5 tuyến mẫu có bộ riêng). Phải thấy:
  · tuyến có bộ riêng → gợi ý theo tuyến; tuyến không có → bộ chung theo Excel;
  · Bãi không nhận đơn giá gợi ý (tiền chi); kế toán thấy;
  · Bãi lập phiếu từ các dòng gợi ý (không gửi giá) → máy chủ điền giá gợi ý; dầu kho vẫn theo bình quân kho;
  · Bãi sửa bộ gợi ý (không gửi giá) → giá kế toán đã đặt còn nguyên; bộ sai → bị từ chối.
Bài tự lập một phiếu thử và tự xoá, trả bộ gợi ý của tuyến về như cũ.
"""
import json
import sys
import time
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[vai]} if vai else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def phai(s, mong, buoc, g=None):
    ma = g.get("detail", {}).get("ma", "") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""
    print("  %s %-78s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, json.dumps(g, ensure_ascii=False)[:300]))


def dung(dk, buoc, chi_tiet=""):
    print("  %s %-78s %s" % ("✓" if dk else "SAI", buoc, chi_tiet))
    if not dk:
        raise SystemExit("DỪNG: " + buoc)


def main():
    for u in ("thabok", "ketoan", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
    s, tk = goi("/api/routes", vai="ketoan")
    cang = next(r for r in tk if r["name"] == "ທ່າບົກ → ທ່າເຮືອກະລໍ")
    gom = next(r for r in tk if r["name"] == "ກາສີ → ທ່າບົກ")
    cu = next((r for r in tk if not r["cost_template"]), None)
    dung(cang["goi_y_nguon"] == "tuyen" and any(x["item_key"] == "x_chip_vn" and x.get("unit_price") == 1500000 for x in cang["goi_y"]),
         "Tuyến ra cảng có bộ riêng đúng Excel (chipping Việt 1.500.000)")
    dung(not any(x["item_key"] == "x_toll" for x in cang["goi_y"]), "Phí cao tốc không nằm trong bộ gợi ý (là ô BOT của tuyến)")
    if cu:
        dung(cu["goi_y_nguon"] == "chung" and len(cu["goi_y"]) >= 6, "Tuyến chưa có bộ riêng dùng bộ chung theo Excel", cu["name"])
    s, tb = goi("/api/routes", vai="thabok")
    dung(all("unit_price" not in x for r in tb for x in r["goi_y"] + r["cost_template"]), "Bãi không nhận đơn giá gợi ý")
    s, bc = goi("/api/tuyen-bo-chung", vai="thabok"); dung(s == 200 and all("unit_price" not in x for x in bc), "Bộ chung cho Bãi: không có giá")
    s, bc = goi("/api/tuyen-bo-chung", vai="ketoan"); dung(any(x.get("unit_price") == 430000 for x in bc), "Bộ chung cho kế toán: có giá Excel")

    # ---- Bãi lập phiếu từ gợi ý (không gửi giá)
    s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] == "EPL" and x["truck_no"] == "348")
    goi_y = next(r for r in tb if r["id"] == gom["id"])["goi_y"]
    dong = [dict(x, paid_by_epl=True) for x in goi_y]
    s, p = goi("/api/trips", {"doc_no": "THU-GY-%s/EPL" % time.strftime("%H%M%S"), "kind": "gom", "vehicle_id": nha["id"], "driver_id": tx[0]["id"],
                              "customer_id": kh[0]["id"], "route_id": gom["id"], "doc_date": time.strftime("%Y-%m-%d"), "expenses": dong}, "thabok")
    phai(s, 200, "Bãi lập phiếu gom ກາສີ → ທ່າບົກ từ đúng các dòng gợi ý (không gửi giá)", p)
    pid = p["id"]
    try:
        s, pk = goi("/api/trips/%s" % pid, vai="ketoan")
        gia = {e["item_key"]: e["unit_price"] for e in pk["expenses"] if e["section"] == "travel"}
        dung(gia.get("x_water") == 60000 and gia.get("x_phone") == 150000, "Máy chủ điền giá gợi ý cho dòng Bãi khai", gia)
        dung(gia.get("x_trip") == 0, "Tiền chuyến tuyến gom chưa có giá gợi ý → để 0 cho kế toán gõ")
        dau = next(e for e in pk["expenses"] if e["section"] == "fuel")
        dung(dau["qty"] == 200 and dau["source"] == "kho" and dau["unit_price"] > 0, "Dầu 200 L lấy kho, giá theo bình quân kho", dau["unit_price"])

        # ---- Bãi sửa bộ gợi ý (không gửi giá): giá cũ còn
        mau = [{k: v for k, v in x.items() if k not in ("unit_price", "currency")} for x in next(r for r in tb if r["id"] == gom["id"])["cost_template"]]
        mau2 = [dict(x, qty=2) if x["item_key"] == "x_water" else x for x in mau]
        s, g = goi("/api/routes/%s" % gom["id"], {"cost_template": mau2}, "thabok", "PUT"); phai(s, 200, "Bãi đổi SL tiền nước trong bộ gợi ý", g)
        s, g = goi("/api/routes/%s" % gom["id"], vai="ketoan")
        nuoc = next(x for x in g["cost_template"] if x["item_key"] == "x_water")
        dung(nuoc["qty"] == 2 and nuoc.get("unit_price") == 60000, "Giá kế toán đã đặt còn nguyên sau lần Bãi sửa", nuoc)
        s, g = goi("/api/routes/%s" % gom["id"], {"cost_template": [{"section": "repair", "item_key": "x_tire", "qty": 1}]}, "ketoan", "PUT")
        phai(s, 422, "Bộ gợi ý có mục sửa chữa → bị từ chối (chỉ III, IV, VI)", g)
        s, g = goi("/api/routes/%s" % gom["id"], {"cost_template": [{"section": "travel", "item_key": "x_khong_co", "qty": 1}]}, "ketoan", "PUT")
        phai(s, 422, "Khoản mục không có trong danh mục → bị từ chối", g)
    finally:
        s, _ = goi("/api/routes/%s" % gom["id"], {"cost_template": gom["cost_template"]}, "ketoan", "PUT")
        print("  · trả bộ gợi ý tuyến gom về như cũ: %s" % s)
        s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại"))
    print("\nTHỬ GỢI Ý CHI PHÍ: ĐẠT — bộ riêng theo tuyến · bộ chung Excel · Bãi không thấy giá · máy điền giá gợi ý · sửa không mất giá")


if __name__ == "__main__":
    main()
