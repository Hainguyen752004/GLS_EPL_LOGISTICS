# -*- coding: utf-8 -*-
"""Thử TRẠM THU PHÍ dọc tuyến (16/10, anh Hải: «anh đi đường container — tính trạm thu phí để phiếu xuất xe có sẵn phí»).

    python kiem/thu_tram_thu_phi.py [http://127.0.0.1:8011]

Anh chọn 16/10: một giá một lượt cho xe EPL mỗi trạm · tuyến có km chiều về thì cộng lượt về (trừ trạm thu một chiều) · phiếu có MỖI TRẠM
MỘT DÒNG phí cao tốc. Phải thấy:
  · Bãi thêm / sửa trạm được nhưng KHÔNG thấy và KHÔNG đặt được giá (giá Bãi gửi bị bỏ); kế toán đặt giá;
  · dò trạm cần đường xe đi; đường đi qua trạm → trạm nằm trong «tren», trạm cách 300 m → chỉ là gợi ý «gan»;
  · tuyến gắn trạm: GET tuyến có tram · lượt · phi_tram (kế toán), Bãi không có giá; gợi ý phiếu có mỗi trạm một dòng;
  · Bãi lập phiếu KHÔNG gửi dòng phí cao tốc → máy tự thêm mỗi trạm một dòng, đúng giá trạm, lượt = 2 khi tuyến có chiều về,
    trạm thu một chiều lượt = 1;
  · tuyến chưa gắn trạm vẫn dùng ô BOT cả tuyến như cũ.
Bài tự lập trạm thử / phiếu thử, cuối bài xoá phiếu, trả tuyến về như cũ, xoá hai trạm thử.
"""
import json
import sys
import time
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
SAI = []


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


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them if not dk else ""))
    if not dk:
        SAI.append(buoc)


def main():
    import os
    mk = os.environ.get("PW_8011") or "1234"                # máy thử: mật khẩu chung của bản demo
    for v in ("ketoan", "thabok", "admin"):
        s, d = goi("/api/dang-nhap", {"username": v, "password": mk})
        assert s == 200, (v, s, d)
        TK[v] = d["token"]
    s, ds = goi("/api/routes", vai="ketoan")
    di = next(r for r in ds if r["active"] and (r["return_km"] or 0) > 0 and not r["tram"])       # tuyến có chiều về, chưa gắn trạm
    cu = {"tolls": [t["id"] for t in di["tram"]], "toll_lak": di["toll_lak"]}
    print("Tuyến thử: %s (về %s km, BOT %s)" % (di["name"], di["return_km"], di["toll_lak"]))
    a = b = pid = None
    try:
        # ---- trạm thử: Bãi tạo (giá bị bỏ), kế toán đặt giá
        s, a = goi("/api/toll-stations", {"name": "THU-TP A %s" % time.strftime("%H%M%S"), "country": "VN", "lat": 18.5, "lng": 105.6,
                                          "fee": 999, "currency": "VND"}, "thabok")
        dung(s == 200 and "fee" not in a and not a["co_gia"], "Bãi thêm trạm được, giá Bãi gửi bị bỏ, không thấy giá", a)
        s, a = goi("/api/toll-stations/%s" % a["id"], {"fee": 180000, "currency": "VND"}, "ketoan", "PUT")
        dung(s == 200 and a["fee"] == 180000 and a["currency"] == "VND", "Kế toán đặt giá 180.000 VND", a)
        s, x = goi("/api/toll-stations/%s" % a["id"], {"fee": 1}, "thabok", "PUT")
        s, a2 = goi("/api/toll-stations", vai="ketoan")
        dung(next(t for t in a2 if t["id"] == a["id"])["fee"] == 180000, "Bãi sửa giá → bị bỏ, giá kế toán còn nguyên")
        s, b = goi("/api/toll-stations", {"name": "THU-TP B %s" % time.strftime("%H%M%S"), "country": "LA", "lat": 18.4, "lng": 103.2,
                                          "fee": 20000, "currency": "LAK", "one_way": True}, "ketoan")
        dung(s == 200 and b["one_way"] and b["fee"] == 20000, "Trạm thu một chiều 20.000 LAK", b)
        s, x = goi("/api/toll-stations", {"name": "", "country": "LA"}, "ketoan")
        dung(s == 422, "Trạm không tên → bị từ chối")
        s, x = goi("/api/toll-stations", {"name": "X", "country": "XX"}, "ketoan")
        dung(s == 422, "Nước sai → bị từ chối")

        # ---- dò trạm: đường đi qua trạm A; trạm B cách ~300 m chỉ là gợi ý
        duong = [[18.5, 105.55], [18.5, 105.65]]                    # đường ngang qua đúng chỗ trạm A
        s, d = goi("/api/toll-stations/doc-tuyen", {"duong": duong}, "ketoan")
        dung(s == 200 and any(t["id"] == a["id"] for t in d["tren"]), "Dò trạm: đường đi qua → trạm nằm trong danh sách trên tuyến", d)
        s, d = goi("/api/toll-stations/doc-tuyen", {"duong": [[18.4027, 103.15], [18.4027, 103.25]]}, "ketoan")   # cách B ~300 m
        dung(s == 200 and not any(t["id"] == b["id"] for t in d["tren"]) and any(g.get("id") == b["id"] for g in d["gan"]),
             "Trạm cách đường ~300 m → chỉ là gợi ý gần đường", d)
        s, d = goi("/api/toll-stations/doc-tuyen", {"duong": [[18.5, 105.6]]}, "ketoan")
        dung(s == 422, "Dò trạm thiếu đường xe đi → bị từ chối")

        # ---- gắn hai trạm vào tuyến
        s, g = goi("/api/routes/%s" % di["id"], {"tolls": [a["id"], b["id"]]}, "ketoan", "PUT")
        dung(s == 200 and [t["id"] for t in g["tram"]] == [a["id"], b["id"]], "Gắn trạm A, B vào tuyến theo thứ tự", g.get("tram"))
        la = {t["id"]: t["luot"] for t in g["tram"]}
        dung(la == {a["id"]: 2, b["id"]: 1}, "Lượt: A hai chiều = 2 (tuyến có chiều về), B thu một chiều = 1", la)
        dung(g.get("phi_tram") == {"VND": 360000, "LAK": 20000}, "Phí trạm tuyến: 360.000 VND + 20.000 LAK", g.get("phi_tram"))
        s, gb = goi("/api/routes/%s" % di["id"], vai="thabok")
        dung("phi_tram" not in gb and all("fee" not in t for t in gb["tram"]) and all("unit_price" not in x for x in gb["goi_y"]),
             "Bãi xem tuyến: thấy trạm, không thấy giá")
        s, gy = goi("/api/trips-goi-y?route_id=%s" % di["id"], vai="ketoan")
        tp = [x for x in gy["dong"] if x["item_key"] == "x_toll"]
        dung(len(tp) == 2 and all(x["toll_station_id"] for x in tp), "Gợi ý phiếu: mỗi trạm một dòng phí cao tốc", tp)
        s, x = goi("/api/routes/%s" % di["id"], {"tolls": ["khong-co"]}, "ketoan", "PUT")
        dung(s == 422, "Gắn trạm không có trong danh mục → bị từ chối")
        s, x = goi("/api/toll-stations/%s" % a["id"], vai="ketoan", method="DELETE")
        dung(s == 409, "Xoá trạm đang gắn với tuyến → bị chặn (chỉ ngưng dùng)", x)

        # ---- Bãi lập phiếu KHÔNG gửi dòng phí cao tốc → máy thêm theo trạm
        s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
        # 20/10: lập phiếu chặn xe / tài xế hết hạn giấy tờ — chọn xe, tài xế còn hạn
        hop_le = lambda **k: not goi("/api/kiem-giay-to?" + "&".join("%s=%s" % (a, b) for a, b in k.items()), vai="ketoan")[1]["chan"]
        nha = next(x for x in xe if x["owner_type"] == "EPL" and x.get("active", True) and hop_le(vehicle_id=x["id"]))
        tx = [t for t in tx if hop_le(driver_id=t["id"])]
        s, p = goi("/api/trips", {"doc_no": "THU-TP-%s/EPL" % time.strftime("%H%M%S"), "kind": "gom", "vehicle_id": nha["id"], "driver_id": tx[0]["id"],
                                  "customer_id": kh[0]["id"], "route_id": di["id"], "doc_date": time.strftime("%Y-%m-%d"), "expenses": []}, "thabok")
        dung(s == 200, "Bãi lập phiếu theo tuyến có trạm", p)
        pid = p.get("id")
        s, pk = goi("/api/trips/%s" % pid, vai="ketoan")
        dong = sorted([(e["item_name"], e["qty"], e["unit_price"], e["currency"]) for e in pk["expenses"] if e["item_key"] == "x_toll"])
        dung(dong == sorted([(a["name"], 2, 180000, "VND"), (b["name"], 1, 20000, "LAK")]),
             "Phiếu có mỗi trạm một dòng: A 2 lượt × 180.000 VND, B 1 lượt × 20.000 LAK (không còn dòng BOT cả tuyến)", dong)
    finally:
        if pid:
            s, _ = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); print("  · phiếu thử %s" % ("đã xoá" if s == 200 else "ở lại (%s)" % s))
        s, _ = goi("/api/routes/%s" % di["id"], {"tolls": cu["tolls"]}, "ketoan", "PUT"); print("  · trả trạm của tuyến về như cũ: %s" % s)
        for t in (a, b):
            if t and t.get("id"):
                s, _ = goi("/api/toll-stations/%s" % t["id"], vai="ketoan", method="DELETE")
                print("  · xoá trạm thử %s: %s" % (t["name"], s))
    # ---- tuyến chưa gắn trạm: BOT cả tuyến như cũ
    s, ds = goi("/api/routes", vai="ketoan")
    bot = next((r for r in ds if not r["tram"] and (r["toll_lak"] or 0) > 0), None)
    if bot:
        s, gy = goi("/api/trips-goi-y?route_id=%s" % bot["id"], vai="ketoan")
        dung(not any(x["item_key"] == "x_toll" for x in gy["dong"]), "Tuyến chưa gắn trạm: gợi ý không có dòng theo trạm (BOT thêm lúc lưu như cũ)")
    print("\nTHỬ TRẠM THU PHÍ: %s" % ("ĐẠT" if not SAI else "SAI %d bước: %s" % (len(SAI), "; ".join(SAI))))
    sys.exit(1 if SAI else 0)


if __name__ == "__main__":
    main()
