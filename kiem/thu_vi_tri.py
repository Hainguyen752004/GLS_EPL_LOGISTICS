# -*- coding: utf-8 -*-
"""Thử luồng GPS thật — điện thoại tài xế gửi vị trí, màn Theo dõi dùng nó thay cho mốc.

    python kiem/thu_vi_tri.py [http://127.0.0.1:8010]

Kiểm đúng những chỗ dễ sai: ai được gửi, phiếu nào được nhận, điểm gửi quá dày thì bỏ, GPS còn mới
thì bản đồ lấy GPS, GPS cũ thì lùi về mốc đã xác nhận tới và gắn cờ "GPS thiếu hoặc cũ".
"""
import datetime as dt
import json
import sys
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"


def goi(duong, than=None, tk=None, cach=None):
    r = urllib.request.Request(GOC + duong, method=cach or ("POST" if than is not None else "GET"))
    r.add_header("Accept", "application/json")
    if tk:
        r.add_header("Authorization", "Bearer " + tk)
    du = None
    if than is not None:
        du = json.dumps(than).encode()
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, du, timeout=30) as o:
            return o.status, json.loads(o.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "null")


def vao(u):
    return goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]


def bao(nhan, ma, mong=200, chi_tiet=""):
    print("  %s %-54s %s%s" % ("OK " if ma == mong else "SAI", nhan, ma, (" · " + chi_tiet) if chi_tiet else ""))
    if ma != mong:
        raise SystemExit("DUNG: %s tra %s, mong %s" % (nhan, ma, mong))


tk = {u: vao(u) for u in ("admin", "thabok", "ketoan", "tx01", "tx02", "tx03")}
print("Đăng nhập %d vai OK" % len(tk))

# ---- tìm một phiếu ĐANG CHẠY và tài khoản tài xế của đúng phiếu đó
_, ds = goi("/api/trips", tk=tk["admin"])
p = next((x for x in ds if x["transport_status"] == "transit"), None)
if p is None:
    raise SystemExit("Không có phiếu nào đang chạy — gieo lại: python backend/app/seed.py --dung-lai")
tx = None
for u in ("tx01", "tx02", "tx03"):
    _, cua_toi = goi("/api/trips", tk=tk[u])
    if any(x["id"] == p["id"] for x in cua_toi):
        tx = u
        break
assert tx, "không tìm được tài khoản tài xế của phiếu %s" % p["doc_no"]
print("Phiếu thử: %s · %s · tài xế %s (%s)" % (p["doc_no"], p["truck_no"], p["driver_name"], tx))

# ---- 1. tài xế KHÁC không gửi được
khac = next(u for u in ("tx01", "tx02", "tx03") if u != tx)
ma, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.5, "lng": 103.5}, tk[khac])
bao("Tài xế khác gửi vị trí → từ chối", ma, 403, (r or {}).get("detail", {}).get("ma", ""))

# ---- 2. kế toán không gửi được
ma, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.5, "lng": 103.5}, tk["ketoan"])
bao("Kế toán gửi vị trí → từ chối", ma, 403, (r or {}).get("detail", {}).get("ma", ""))

# ---- 3. toạ độ sai khoảng
ma, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 999, "lng": 103.5}, tk[tx])
bao("Vĩ độ 999 → từ chối", ma, 422, (r or {}).get("detail", {}).get("ma", ""))

# ---- 4. tài xế của phiếu gửi được
ma, r = goi("/api/trips/%s/vi-tri" % p["id"],
            {"lat": 18.44, "lng": 103.15, "speed_kmh": 52.5, "accuracy_m": 8}, tk[tx])
bao("Tài xế gửi vị trí", ma, 200, "ghi=%s" % r["ghi"])
assert r["ghi"] is True, "điểm đầu tiên phải được ghi"

# ---- 5. gửi dồn dập thì bỏ bớt
ma, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.45, "lng": 103.16}, tk[tx])
bao("Gửi lại ngay sau đó → bỏ bớt, không ghi", ma, 200, "ghi=%s · %s" % (r["ghi"], r.get("ly_do", "")))
assert r["ghi"] is False, "điểm gửi quá dày phải bị bỏ"

# ---- 6. màn Theo dõi dùng GPS thật
ma, tt = goi("/api/theo-doi?tat_ca=1", tk=tk["admin"])
bao("Bảng theo dõi", ma, 200)
c = next(x for x in tt["chuyen"] if x["id"] == p["id"])
assert c["gps"], "phiếu phải có GPS"
assert c["gps"]["cu"] is False, "GPS vừa gửi thì không được coi là cũ"
assert c["vi_tri"]["nguon"] == "gps", "còn GPS mới thì bản đồ phải lấy GPS, đang lấy %s" % c["vi_tri"]["nguon"]
print("  OK  Bản đồ lấy vị trí GPS thật: %.4f, %.4f · %s phút trước · %s km/h"
      % (c["vi_tri"]["lat"], c["vi_tri"]["lng"], c["vi_tri"]["tuoi_phut"], c["vi_tri"].get("speed_kmh")))

# ---- 7. vệt đường
ma, v = goi("/api/trips/%s/vet" % p["id"], tk=tk["admin"])
bao("Vệt đường của phiếu", ma, 200, "%d điểm" % v["so_diem"])
assert v["so_diem"] >= 1

# ---- 8. GPS CŨ thì lùi về mốc đã xác nhận tới
#      Đẩy lùi thời gian điểm vừa gửi để giả cảnh mất sóng cả tiếng.
import os                                                       # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app"))
from database import SessionLocal                               # noqa: E402
from models import VehiclePosition                              # noqa: E402

db = SessionLocal()
diem = (db.query(VehiclePosition).filter(VehiclePosition.trip_id == p["id"])
        .order_by(VehiclePosition.ts.desc()).first())
diem.ts = dt.datetime.utcnow() - dt.timedelta(hours=2)
db.commit()
db.close()

ma, tt = goi("/api/theo-doi?tat_ca=1", tk=tk["admin"])
c = next(x for x in tt["chuyen"] if x["id"] == p["id"])
assert c["gps"]["cu"] is True, "GPS 2 tiếng trước phải bị coi là cũ"
assert c["vi_tri"] is None or c["vi_tri"]["nguon"] == "moc", "GPS cũ thì phải lùi về mốc đã xác nhận tới"
assert tt["kpi"]["gps_thieu"] >= 1, "ô số GPS thiếu/cũ phải đếm được phiếu này"
print("  OK  GPS cũ 2 tiếng → lùi về mốc, ô số 'GPS thiếu hoặc cũ' = %d" % tt["kpi"]["gps_thieu"])

# ---- 9. phiếu đã tới nơi thì không nhận vị trí nữa
xong = next((x for x in ds if x["transport_status"] == "arrived"), None)
if xong:
    ma, r = goi("/api/trips/%s/vi-tri" % xong["id"], {"lat": 18.4, "lng": 103.1}, tk["admin"])
    bao("Phiếu đã tới nơi → không nhận vị trí", ma, 409, (r or {}).get("detail", {}).get("ma", ""))

print("\nTHỬ VỊ TRÍ: ĐẠT — phân quyền · lọc điểm dày · GPS mới thì dùng · GPS cũ thì lùi về mốc")
