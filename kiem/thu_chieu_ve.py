# -*- coding: utf-8 -*-
"""Thử KM CHIỀU VỀ của tuyến (chốt 29/09): xe quay lại điểm đi — gom chạy rỗng lên mỏ, giao chạy rỗng về bãi.

    python kiem/thu_chieu_ve.py [http://127.0.0.1:8011]

Km về ước tính trên phiếu = km lúc đi + chiều đi + chiều về; cảnh báo "Km về lệch" lúc khoá so với đúng số đó.
Bài dùng lại một tuyến thử (tạo lần đầu, các lần sau sửa lại) và cuối bài để nó NGƯNG DÙNG — tên chữ Latinh xếp trước tên
chữ Lào, tuyến thử còn dùng là thành tuyến đầu danh sách của các bài khác. Phiếu thử tự xoá.
"""
import json
import sys
import time
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
TEN = "THU chiều về (bãi ↔ mỏ)"


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
    print("  %s %-70s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, g))


def main():
    for u in ("thabok", "ketoan", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
    print("✓ đăng nhập 3 vai")
    diem = [{"name": "ກາສີ (ບ່ອນຂຸດແຮ່)"}, {"name": "ທ່າບົກ (ສະໜາມ EPL)", "km_from_prev": 145}]
    s, ds = goi("/api/routes", vai="thabok")
    cu = next((r for r in ds if r["name"] == TEN), None)
    s, g = (goi("/api/routes/%s" % cu["id"], {"stops": diem, "return_km": -5, "active": True}, "thabok", "PUT") if cu
            else goi("/api/routes", {"name": TEN, "stops": diem, "return_km": -5}, "thabok"))
    phai(s, 422, "Km chiều về âm → bị từ chối", g)
    s, r = (goi("/api/routes/%s" % cu["id"], {"stops": diem, "return_km": 145, "toll_lak": 0, "active": True}, "thabok", "PUT") if cu
            else goi("/api/routes", {"name": TEN, "stops": diem, "return_km": 145, "toll_lak": 0}, "thabok"))
    phai(s, 200, "Bãi lưu tuyến mỏ → bãi 145 km, chiều về 145 km", r)
    assert r["total_km"] == 145 and r["return_km"] == 145 and r["round_km"] == 290, r
    s, ds = goi("/api/routes", vai="thabok")
    assert next(x for x in ds if x["id"] == r["id"])["round_km"] == 290
    print("  ✓ %-70s" % "Danh sách tuyến trả km chiều đi 145 · chiều về 145 · cả chuyến 290")

    pid = None
    try:
        s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
        nha = next(x for x in xe if x["owner_type"] != "joint")
        s, p = goi("/api/trips", {"doc_no": "THU-CV-%s/EPL" % time.strftime("%H%M%S"), "kind": "gom", "company": "EPL", "vehicle_id": nha["id"],
                                  "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "route_id": r["id"], "odo_out": 10000,
                                  "doc_date": time.strftime("%Y-%m-%d"), "weight_origin": 40}, "thabok")
        phai(s, 200, "Bãi lập phiếu gom trên tuyến đó, lúc đi 10.000 km", p); pid = p["id"]
        s, p = goi("/api/trips/%s" % pid, vai="ketoan")
        assert p["odo_est"] == 10290, p["odo_est"]
        print("  ✓ %-70s %s" % ("Km về ước tính = lúc đi + chiều đi + chiều về", p["odo_est"]))
        s, g = goi("/api/trips/%s/bao-ve" % pid, {"back_date": time.strftime("%Y-%m-%d"), "odo_back": 10300}, "thabok")
        phai(s, 200, "Xe về, km về 10.300 (cả chuyến 300 km)", g)
        s, kl = goi("/api/trips/%s/kiem-lai" % pid, vai="ketoan")
        assert "KM_LECH" not in [c["ma"] for c in kl["canh_bao"]], kl["canh_bao"]
        print("  ✓ %-70s" % "Chạy 300 km trên tuyến 290 km khứ hồi → KHÔNG báo lệch km")
        s, g = goi("/api/routes/%s" % r["id"], {"return_km": 0}, "thabok", "PUT")
        phai(s, 200, "Bỏ km chiều về (tuyến chỉ còn chiều đi 145 km)", g)
        s, kl = goi("/api/trips/%s/kiem-lai" % pid, vai="ketoan")
        lech = [c for c in kl["canh_bao"] if c["ma"] == "KM_LECH"]
        assert lech, kl["canh_bao"]
        print("  ✓ %-70s" % "Không tính chiều về thì cùng số km đó bị báo lệch (như trước 29/09)")
    finally:
        if pid:
            goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        s, g = goi("/api/routes/%s" % r["id"], {"active": False}, "thabok", "PUT")
        print("  · đã xoá phiếu thử, tuyến thử để ngưng dùng (%s)" % s)
    print("\nTHỬ KM CHIỀU VỀ: ĐẠT — tuyến lưu chiều về · km về ước tính tính cả chiều về · cảnh báo lệch km đúng")


if __name__ == "__main__":
    main()
