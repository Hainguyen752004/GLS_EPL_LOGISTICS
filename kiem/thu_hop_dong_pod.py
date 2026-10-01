# -*- coding: utf-8 -*-
"""Thử HỢP ĐỒNG và POD (chủ dự án chốt 24/09).

    python kiem/thu_hop_dong_pod.py [http://127.0.0.1:8011]

Hợp đồng — ສັນຍາ: giấy khung ký một lần (số · ngày ký · hiệu lực · bản scan) cho khách (vận chuyển) và chủ xe liên kết
(thuê xe); phiếu tự mang số hợp đồng còn hiệu lực, kế toán đổi được, Bãi thì không; bản scan có giá nên Bãi không mở.
POD — Biên bản giao nhận hàng · ໃບເຊັນຮັບສິນຄ້າ: nhập tay số POD hoặc đính kèm ảnh; thiếu thì khoá phiếu CẢNH BÁO, không chặn.
Bài tự dọn: xoá phiếu thử và hợp đồng thử.
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
TAO = {"trip": [], "hd": []}
DAU = "THU-HD-%s" % time.strftime("%d%H%M%S")


def goi(duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[vai]} if vai else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            raw = t.read()
            return t.status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def tep(duong, ten, du, kieu, vai, them=None):
    b = uuid.uuid4().hex
    than = b"".join([(b"--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b.encode(), k.encode(), v.encode()))
                     for k, v in (them or {}).items()])
    than += b"--%s\r\nContent-Disposition: form-data; name=\"tep\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (b.encode(), ten.encode(), kieu.encode())
    than += du + b"\r\n--%s--\r\n" % b.encode()
    r = urllib.request.Request(GOC + duong, data=than, method="POST",
                               headers={"Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + TK[vai]})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def phai(s, mong, buoc, g=None):
    ma = (g or {}).get("detail", {}).get("ma", "") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""
    print("  %s %-66s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, g))


PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def chay():
    for u in ("thabok", "ketoan", "doanhthu", "admin", "tx01"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]
    print("✓ đăng nhập 5 vai")
    s, kh = goi("/api/customers", vai="thabok"); s, xe = goi("/api/vehicles", vai="thabok"); s, chu = goi("/api/owners", vai="ketoan")
    s, tuyen = goi("/api/routes", vai="thabok")
    ktui = next(c for c in kh if "ຄຳຕຸ້ຍ" in c["name"]); vanna = next(c for c in kh if "ວັນນາ" in c["name"])
    lk = next(x for x in xe if x["owner_type"] == "joint"); nha = next(x for x in xe if x["owner_type"] != "joint")
    tx = goi("/api/drivers", vai="thabok")[1]                 # 01/10: phiếu phải có xe và tài xế
    ck = next(o for o in chu if o["id"] == lk["owner_id"])

    # ---------------------------------------------------------------- 1. danh mục hợp đồng + phân quyền
    s, g = goi("/api/hop-dong", {"contract_no": DAU + "-K", "kind": "khach", "customer_id": ktui["id"]}, "thabok"); phai(s, 403, "Bãi thêm hợp đồng → bị chặn", g)
    s, g = goi("/api/hop-dong", {"contract_no": DAU + "-T", "kind": "thue_xe", "owner_id": ck["id"]}, "doanhthu"); phai(s, 403, "KT Doanh thu thêm hợp đồng THUÊ XE → bị chặn", g)
    s, hk = goi("/api/hop-dong", {"contract_no": DAU + "-K", "kind": "khach", "customer_id": ktui["id"], "sign_date": "2026-01-02",
                                  "valid_from": "2026-01-02", "valid_to": "2026-12-31", "note": "thử"}, "ketoan"); phai(s, 200, "KT Thu/Chi thêm hợp đồng vận chuyển cho ຄຳຕຸ້ຍ", hk); TAO["hd"].append(hk["id"])
    s, g = goi("/api/hop-dong", {"contract_no": DAU + "-K", "kind": "khach", "customer_id": ktui["id"]}, "ketoan"); phai(s, 409, "Trùng số hợp đồng → bị chặn", g)
    s, g = goi("/api/hop-dong", {"contract_no": DAU + "-X", "kind": "khach", "customer_id": ktui["id"], "valid_from": "2026-05-01", "valid_to": "2026-02-01"}, "ketoan")
    phai(s, 422, "Ngày hết hạn trước ngày áp dụng → bị chặn", g)
    s, ht = goi("/api/hop-dong", {"contract_no": DAU + "-T", "kind": "thue_xe", "owner_id": ck["id"], "sign_date": "2026-03-01", "valid_to": "2026-10-10"}, "ketoan")
    phai(s, 200, "KT Thu/Chi thêm hợp đồng thuê xe cho chủ xe %s" % ck["name"], ht); TAO["hd"].append(ht["id"])
    s, hv = goi("/api/hop-dong", {"contract_no": DAU + "-V", "kind": "khach", "customer_id": vanna["id"], "valid_from": "2025-01-01", "valid_to": "2026-01-31"}, "doanhthu")
    phai(s, 200, "KT Doanh thu thêm hợp đồng ĐÃ HẾT HẠN cho ນາງ ວັນນາ", hv); TAO["hd"].append(hv["id"])
    assert hv["trang_thai"] == "het_han", hv
    assert ht["trang_thai"] in ("con_han", "sap_het"), ht
    print("  ✓ trạng thái hạn tự tính: %s · %s · %s" % (hk["trang_thai"], ht["trang_thai"], hv["trang_thai"]))

    s, g = tep("/api/hop-dong/%s/tep" % hk["id"], "hop_dong.png", PNG, "image/png", "ketoan"); phai(s, 200, "Đưa bản scan hợp đồng lên", g)
    s, g = tep("/api/hop-dong/%s/tep" % hk["id"], "x.exe", b"MZ", "application/octet-stream", "ketoan"); phai(s, 422, "Tệp .exe → bị từ chối", g)
    s, ds_b = goi("/api/hop-dong?kind=khach&customer_id=%s" % ktui["id"], vai="thabok")
    phai(s, 200, "Bãi xem danh sách hợp đồng (số, hạn)", ds_b)
    assert all("files" not in h for h in ds_b), "Bãi không được nhận danh sách bản scan (giấy có giá)"
    s, ds_k = goi("/api/hop-dong?kind=khach&customer_id=%s" % ktui["id"], vai="ketoan")
    f = next(h for h in ds_k if h["id"] == hk["id"])["files"][0]
    r = urllib.request.Request(GOC + f["url"] + "?tk=" + TK["thabok"])
    try:
        urllib.request.urlopen(r); sb = 200
    except urllib.error.HTTPError as e:
        sb = e.code
    phai(sb, 403, "Bãi mở bản scan hợp đồng → bị chặn")
    with urllib.request.urlopen(urllib.request.Request(GOC + f["url"] + "?tk=" + TK["ketoan"])) as t:
        phai(t.status, 200, "Kế toán mở bản scan hợp đồng")
    s, g = goi("/api/hop-dong", vai="tx01"); phai(s, 403, "Tài xế xem hợp đồng → bị chặn", g)

    # ---------------------------------------------------------------- 2. phiếu tự mang số hợp đồng
    s, p = goi("/api/trips", {"doc_no": DAU + "-1/EPL", "company": "EPL", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "customer_id": ktui["id"],
                              "route_id": tuyen[0]["id"], "doc_date": "2026-09-24", "weight_origin": 40,
                              "note": "thử hợp đồng"}, "thabok"); phai(s, 200, "Bãi lập phiếu cho ຄຳຕຸ້ຍ", p); TAO["trip"].append(p["id"])
    phai(p["contract_no"], DAU + "-K", "Phiếu tự điền số hợp đồng vận chuyển")
    assert p["contract_state"] in ("con_han", "sap_het"), p["contract_state"]
    s, g = goi("/api/trips/%s" % p["id"], {"contract_id": hv["id"]}, "thabok", "PUT"); phai(s, 403, "Bãi đổi hợp đồng trên phiếu → bị chặn", g)
    s, g = goi("/api/trips/%s" % p["id"], {"contract_id": hv["id"]}, "ketoan", "PUT"); phai(s, 422, "Kế toán chọn hợp đồng của KHÁCH KHÁC → bị chặn", g)
    s, g = goi("/api/trips/%s" % p["id"], {"contract_id": None}, "ketoan", "PUT"); phai(s, 200, "Kế toán chọn 'không có hợp đồng'", g)
    assert g["contract_no"] is None, g["contract_no"]
    s, g = goi("/api/trips/%s" % p["id"], {"note": "Bãi lưu lại"}, "thabok", "PUT"); phai(s, 200, "Bãi lưu lại phiếu", g)
    phai(g["contract_no"], None, "Lưu lại KHÔNG tự điền đè lựa chọn của kế toán")
    s, g = goi("/api/trips/%s" % p["id"], {"contract_id": hk["id"]}, "ketoan", "PUT"); phai(g["contract_no"], DAU + "-K", "Kế toán chọn lại hợp đồng")
    s, g = goi("/api/hop-dong/%s" % hk["id"], vai="ketoan", method="DELETE"); phai(s, 409, "Xoá hợp đồng đã có phiếu → bị chặn (ngưng dùng thay vì xoá)", g)

    s, pl = goi("/api/trips", {"doc_no": DAU + "-2/EPL", "company": "joint", "vehicle_id": lk["id"], "driver_id": tx[0]["id"], "customer_id": ktui["id"],
                               "route_id": tuyen[0]["id"], "doc_date": "2026-09-24", "weight_origin": 41}, "thabok")
    phai(s, 200, "Bãi lập phiếu xe liên kết %s" % lk["truck_no"], pl); TAO["trip"].append(pl["id"])
    phai(pl["hire_contract_no"], DAU + "-T", "Phiếu xe liên kết tự điền số hợp đồng thuê xe")

    # ---------------------------------------------------------------- 3. POD + cảnh báo khoá
    s, pv = goi("/api/trips", {"doc_no": DAU + "-3/EPL", "company": "EPL", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "customer_id": vanna["id"],
                               "route_id": tuyen[0]["id"], "doc_date": "2026-09-24", "weight_origin": 40}, "thabok")
    phai(s, 200, "Bãi lập phiếu cho ນາງ ວັນນາ (hợp đồng đã hết hạn)", pv); TAO["trip"].append(pv["id"])
    phai(pv["contract_no"], None, "Hợp đồng hết hạn thì KHÔNG tự điền")
    s, g = goi("/api/trips/%s/transport-status" % pv["id"], {"status": "arrived", "weight_dest": 39.8, "back_date": "2026-09-24"}, "admin")
    phai(s, 200, "Xe tới (không có POD)", g)
    s, kl = goi("/api/trips/%s/kiem-lai" % pv["id"], vai="ketoan")
    ma = [c["ma"] for c in kl["canh_bao"]]
    assert "THIEU_POD" in ma and "HOP_DONG_HET_HAN" in ma, ma
    print("  ✓ %-66s %s" % ("Bảng cảnh báo khoá có 'thiếu POD' và 'hợp đồng hết hạn'", "THIEU_POD · HOP_DONG_HET_HAN"))

    s, g = goi("/api/trips/%s/transport-status" % p["id"], {"status": "arrived", "weight_dest": 39.9, "back_date": "2026-09-24",
                                                             "pod_no": "POD-" + DAU, "pod_receiver": "ນາງ ທົດລອງ"}, "admin")
    phai(s, 200, "Xe tới, gõ luôn số POD và người ký nhận", g)
    assert g["pod_no"] == "POD-" + DAU and g["pod_receiver"] == "ນາງ ທົດລອງ" and g["pod_date"] == "2026-09-24", (g["pod_no"], g["pod_date"])
    s, g = goi("/api/trips/%s" % p["id"], {"pod_receiver": "ນາງ ທົດລອງ 2"}, "thabok", "PUT"); phai(s, 200, "Bãi sửa người ký nhận POD (mục II đã kiểm vẫn được)", g)
    s, g = tep("/api/trips/%s/tep" % p["id"], "pod.png", PNG, "image/png", "thabok", {"kind": "pod"}); phai(s, 200, "Bãi đính kèm ảnh POD", g)
    assert g["kind"] == "pod", g
    s, g = goi("/api/trips/%s" % p["id"], vai="thabok"); assert g["pod_files"] == 1, g["pod_files"]
    s, kl = goi("/api/trips/%s/kiem-lai" % p["id"], vai="ketoan")
    assert "THIEU_POD" not in [c["ma"] for c in kl["canh_bao"]], kl
    print("  ✓ %-66s" % "Có POD thì không còn cảnh báo thiếu POD")
    s, g = goi("/api/trips/%s/khoa" % pv["id"], {"xac_nhan": True}, "ketoan"); phai(s, 200, "Thiếu POD vẫn KHOÁ được sau khi xác nhận (chỉ cảnh báo)", g)
    s, g = goi("/api/trips/%s" % pv["id"], {"pod_no": "POD-SAU"}, "thabok", "PUT"); phai(s, 409, "Phiếu đã khoá: Bãi không ghi POD nữa", g)
    s, g = goi("/api/trips/%s" % pv["id"], {"pod_no": "POD-SAU"}, "ketoan", "PUT"); phai(s, 200, "Phiếu đã khoá: kế toán vẫn bổ sung được số POD", g)
    print("\n✅ HỢP ĐỒNG & POD: danh mục + bản scan + phân quyền · phiếu tự mang số hợp đồng (khách, thuê xe) · kế toán đổi được, Bãi không"
          " · POD nhập tay / ảnh · khoá chỉ cảnh báo thiếu POD và hợp đồng hết hạn")


def don():
    for tid in TAO["trip"]:
        goi("/api/trips/%s/mo-khoa" % tid, {}, "admin")
        s, g = goi("/api/trips/%s" % tid, vai="admin", method="DELETE")
        print("  dọn phiếu thử:", s)
    for hid in TAO["hd"]:
        s, g = goi("/api/hop-dong/%s" % hid, vai="admin", method="DELETE")
        print("  dọn hợp đồng thử:", s, (g or {}).get("detail", ""))


if __name__ == "__main__":
    try:
        chay()
    finally:
        don()
