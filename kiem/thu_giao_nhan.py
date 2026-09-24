# -*- coding: utf-8 -*-
"""Thử GIAO HÀNG HOÀN TẤT — người nhận ký trên điện thoại tài xế (chốt 24/09).

    python kiem/thu_giao_nhan.py [http://127.0.0.1:8011]

Tài xế gửi chữ ký (PNG) và / hoặc ảnh biên bản + tên, điện thoại người nhận, tình trạng hàng, giờ ký, GPS. Khối POD
của phiếu tự đầy; gửi lại cùng `ma_gui` (mất mạng rồi có mạng) không ghi hai lần; hàng thiếu / hỏng bắt ghi chú và
hiện ở bảng cảnh báo khoá. Bài tự lập phiếu thử và tự xoá.
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
TAO = []
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
JPG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb004300") + b"\x08" * 64 + bytes.fromhex("ffd9")


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


def gui(tid, vai, truong, tep=()):
    b = uuid.uuid4().hex
    than = b"".join(b"--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b.encode(), k.encode(), str(v).encode())
                    for k, v in truong.items())
    for ten_o, ten_tep, kieu, du in tep:
        than += b"--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (
            b.encode(), ten_o.encode(), ten_tep.encode(), kieu.encode()) + du + b"\r\n"
    than += b"--%s--\r\n" % b.encode()
    r = urllib.request.Request(GOC + "/api/trips/%s/giao-nhan" % tid, data=than, method="POST",
                               headers={"Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + TK[vai]})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def phai(s, mong, buoc, g=None):
    ma = g.get("detail", {}).get("ma", "") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""
    print("  %s %-68s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, g))


def lap(dau, tx, kind="giao"):
    s, xe = goi("/api/vehicles", vai="thabok"); s, kh = goi("/api/customers", vai="thabok"); s, tuyen = goi("/api/routes", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    s, p = goi("/api/trips", {"doc_no": "%s-%s/EPL" % (dau, time.strftime("%H%M%S")), "kind": kind, "company": "EPL", "vehicle_id": nha["id"],
                              "driver_id": tx["user"]["driver_id"], "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"],
                              "doc_date": time.strftime("%Y-%m-%d"), "weight_origin": 40, "note": "thử giao nhận"}, "thabok")
    assert s == 200, p
    TAO.append(p["id"])
    return p


def chay():
    dn = {}
    for u in ("thabok", "ketoan", "admin", "tx01", "tx02"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]; dn[u] = g
    print("✓ đăng nhập 5 vai")
    p = lap("THU-GN", dn["tx01"])
    g0 = {"nguoi_nhan": "ນາງ ທົດລອງ", "sdt": "020 5555 0000", "tinh_trang": "du", "luc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600)),
          "lat": "17.9757", "lng": "102.6331", "ma_gui": "thu-" + uuid.uuid4().hex[:10]}
    s, g = gui(p["id"], "tx01", g0, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 409, "Xe chưa xuất phát → chưa ký nhận được", g)
    goi("/api/trips/%s/transport-status" % p["id"], {"status": "transit"}, "admin")
    s, g = gui(p["id"], "tx02", g0, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 403, "Tài xế khác ký phiếu không phải của mình → bị chặn", g)
    s, g = gui(p["id"], "ketoan", g0, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 403, "Kế toán ghi giao hàng hoàn tất → bị chặn", g)
    s, g = gui(p["id"], "tx01", g0); phai(s, 422, "Không chữ ký, không ảnh → bị từ chối", g)
    s, g = gui(p["id"], "tx01", {**g0, "nguoi_nhan": ""}, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 422, "Có chữ ký mà không ghi tên người nhận → bị từ chối", g)
    s, g = gui(p["id"], "tx01", g0, [("chu_ky", "ky.jpg", "image/jpeg", JPG)]); phai(s, 422, "Chữ ký không phải PNG → bị từ chối", g)
    s, g = gui(p["id"], "tx01", {**g0, "tinh_trang": "thieu"}, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 422, "Hàng thiếu mà không ghi chú → bị từ chối", g)
    s, g = gui(p["id"], "tx01", {**g0, "luc": "2030-01-01T00:00:00Z"}, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 422, "Giờ ký ở tương lai → bị từ chối", g)

    g1 = {**g0, "tinh_trang": "thieu", "ghi_chu": "ຂາດ 0.5 ໂຕນ"}
    s, g = gui(p["id"], "tx01", g1, [("chu_ky", "ky.png", "image/png", PNG), ("anh", "bien-ban.jpg", "image/jpeg", JPG), ("anh", "phieu-can.jpg", "image/jpeg", JPG)])
    phai(s, 200, "Tài xế gửi: chữ ký + 2 ảnh + GPS + hàng thiếu có ghi chú", g)
    assert g["pod_signed"] and g["pod_files"] == 2, (g["pod_signed"], g["pod_files"])
    assert g["pod_receiver"] == "ນາງ ທົດລອງ" and g["pod_phone"] == "020 5555 0000" and g["pod_condition"] == "thieu", g
    assert abs(g["pod_lat"] - 17.9757) < 1e-6 and g["pod_no"] and g["pod_date"] and g["pod_at"], g
    print("  ✓ %-68s %s · %s · %s" % ("Khối POD tự đầy: số POD, người nhận, giờ ký, vị trí, tình trạng", g["pod_no"], g["pod_at"], g["pod_condition"]))
    s, g = gui(p["id"], "tx01", g1, [("chu_ky", "ky.png", "image/png", PNG), ("anh", "bien-ban.jpg", "image/jpeg", JPG)])
    phai(s, 200, "Máy tài xế gửi LẠI cùng mã (mất mạng rồi có mạng) → nhận, không ghi thêm", g)
    s, dt = goi("/api/trips/%s/tep" % p["id"], vai="thabok")
    assert len([t for t in dt if t["kind"] == "pod_sign"]) == 1 and len([t for t in dt if t["kind"] == "pod"]) == 2, [t["kind"] for t in dt]
    print("  ✓ %-68s" % "Gửi lại không đẻ thêm tệp: 1 chữ ký · 2 ảnh")
    s, g = gui(p["id"], "tx01", {**g0, "ma_gui": "khac-" + uuid.uuid4().hex[:6]}, [("chu_ky", "ky.png", "image/png", PNG)])
    phai(s, 409, "Ký lần hai (mã khác) khi đã có chữ ký → bị chặn", g)
    s, kl = goi("/api/trips/%s/kiem-lai" % p["id"], vai="ketoan")
    ma = [c["ma"] for c in kl["canh_bao"]]
    assert "HANG_THIEU_HONG" in ma and "THIEU_POD" not in ma, ma
    print("  ✓ %-68s" % "Khoá phiếu: cảnh báo hàng THIẾU người nhận ghi; không còn cảnh báo thiếu POD")

    pb = lap("THU-GN-ANH", dn["tx01"])
    goi("/api/trips/%s/transport-status" % pb["id"], {"status": "transit"}, "admin")
    s, g = gui(pb["id"], "tx01", {"tinh_trang": "du", "ma_gui": uuid.uuid4().hex[:8]}, [("anh", "giay.jpg", "image/jpeg", JPG)])
    phai(s, 200, "Chỉ ảnh biên bản giấy (không chữ ký) → vẫn được", g)
    assert not g["pod_signed"] and g["pod_files"] == 1, g
    pg = lap("THU-GN-GOM", dn["tx01"], "gom")
    goi("/api/trips/%s/transport-status" % pg["id"], {"status": "transit"}, "admin")
    s, g = gui(pg["id"], "tx01", g0, [("chu_ky", "ky.png", "image/png", PNG)]); phai(s, 409, "Phiếu GOM (về bãi mình) → không có ký nhận", g)
    goi("/api/trips/%s/transport-status" % pb["id"], {"status": "arrived", "weight_dest": 39.9}, "admin")
    goi("/api/trips/%s/khoa" % pb["id"], {"xac_nhan": True}, "ketoan")
    s, g = gui(pb["id"], "tx01", {"tinh_trang": "du", "ma_gui": uuid.uuid4().hex[:8]}, [("anh", "giay2.jpg", "image/jpeg", JPG)])
    phai(s, 409, "Phiếu đã khoá → tài xế không gửi thêm", g)
    print("\n✅ GIAO HÀNG HOÀN TẤT: ký trên điện thoại tài xế · chữ ký hoặc ảnh · GPS · giờ ký thật · gửi lại không trùng · "
          "chặn đúng vai / loại phiếu / bước · hàng thiếu có cảnh báo khoá")


if __name__ == "__main__":
    try:
        chay()
    finally:
        for tid in TAO:
            s, g = goi("/api/trips/%s" % tid, vai="admin", method="DELETE")
            print("  dọn phiếu thử:", s)
