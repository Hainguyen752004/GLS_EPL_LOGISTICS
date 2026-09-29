# -*- coding: utf-8 -*-
"""Thử CÂN TẠI MỎ của phiếu GOM (chốt 29/09).

    python kiem/thu_can_mo.py [http://127.0.0.1:8011]

  · Phiếu gom một mặt hàng không còn bảng "Hàng trên phiếu": máy ghi dòng hàng từ Loại hàng + Cân tại mỏ — lúc lập, lúc
    sửa, cả khi màn cũ gửi bảng rỗng.
  · Tài xế báo cân ở mỏ trên điện thoại (số tấn + ảnh phiếu cân): ô Cân tại mỏ tự đầy, ảnh vào "Phiếu quặng đính kèm",
    gửi lại cùng mã không ghi hai lần, mục II đã kiểm thì không đổi được nữa.
  · "Xe đã tới" của phiếu gom: chưa có cân tại mỏ thì bị chặn; hộp gửi kèm cân tại mỏ thì hàng vào kho theo số đó.
Cần trang kế toán chạy (hàng vào kho ở bên đó). "Xe đã tới" gọi bằng vai admin để khỏi đi chuỗi tạm ứng mục IV
(tuyến thử có phí cầu đường) — luật cân tại mỏ áp cho cả admin. Bài tự lập phiếu thử và tự xoá.
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
JPG = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb004300") + b"\x08" * 64 + bytes.fromhex("ffd9")
QUANG, KHAC = "ແຮ່ເຫຼັກ (quặng sắt)", "ສິນຄ້າອື່ນ (hàng khác)"


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


def bao(tid, vai, truong, tep=()):
    """POST /api/trips/{id}/bao-can-mo — multipart như máy tài xế gửi."""
    b = uuid.uuid4().hex
    than = b"".join(b"--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b.encode(), k.encode(), str(v).encode())
                    for k, v in truong.items())
    for ten_o, ten_tep, kieu, du in tep:
        than += b"--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (
            b.encode(), ten_o.encode(), ten_tep.encode(), kieu.encode()) + du + b"\r\n"
    than += b"--%s--\r\n" % b.encode()
    r = urllib.request.Request(GOC + "/api/trips/%s/bao-can-mo" % tid, data=than, method="POST",
                               headers={"Content-Type": "multipart/form-data; boundary=" + b, "Authorization": "Bearer " + TK[vai]})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def phai(s, mong, buoc, g=None):
    ma = g.get("detail", {}).get("ma", "") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""
    print("  %s %-70s %s %s" % ("✓" if s == mong else "SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s — %s" % (buoc, g))


def hang(p):
    return [(x["goods_name"], round(x["qty_t"], 3)) for x in p["goods"] if x["loai"] == "hang"]


def lap(dau, tx, kind="gom", **them):
    s, xe = goi("/api/vehicles", vai="thabok"); s, kh = goi("/api/customers", vai="thabok"); s, tuyen = goi("/api/routes", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    s, p = goi("/api/trips", {"doc_no": "%s-%s/EPL" % (dau, time.strftime("%H%M%S")), "kind": kind, "company": "EPL", "vehicle_id": nha["id"],
                              "driver_id": tx["user"]["driver_id"], "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"],
                              "doc_date": time.strftime("%Y-%m-%d"), "note": "thử cân tại mỏ", **them}, "thabok")
    phai(s, 200, "Bãi lập phiếu %s %s" % (kind.upper(), " · ".join("%s=%s" % kv for kv in them.items()) or "(chưa cân)"), p)
    TAO.append(p["id"])
    return p


def chay():
    dn = {}
    for u in ("thabok", "ketoan", "admin", "tx01", "tx02"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TK[u] = g["token"]; dn[u] = g
    print("✓ đăng nhập 5 vai")

    # ---------------------------------------------------------------- 1. dòng hàng phiếu gom máy tự ghi
    a = lap("THU-CM-A", dn["tx01"], weight_origin=40)
    assert hang(a) == [(QUANG, 40.0)] and a["weight_origin"] == 40, hang(a)
    print("  ✓ %-70s %s" % ("Chỉ ghi Cân tại mỏ 40 → máy ghi MỘT dòng hàng theo Loại hàng", hang(a)))
    s, a = goi("/api/trips/%s" % a["id"], {"weight_origin": 41.5}, "thabok", "PUT"); phai(s, 200, "Bãi sửa Cân tại mỏ 41,5", a)
    assert hang(a) == [(QUANG, 41.5)], hang(a)
    s, a = goi("/api/trips/%s" % a["id"], {"goods_type": "other_goods"}, "thabok", "PUT"); phai(s, 200, "Bãi đổi Loại hàng → Hàng khác", a)
    assert hang(a) == [(KHAC, 41.5)], hang(a)
    s, a = goi("/api/trips/%s" % a["id"], {"goods_type": "iron_ore", "weight_origin": 40, "goods": []}, "thabok", "PUT")
    phai(s, 200, "Màn cũ gửi bảng hàng RỖNG + cân 40 → vẫn ra một dòng, không mất dòng", a)
    assert hang(a) == [(QUANG, 40.0)], hang(a)

    # ---------------------------------------------------------------- 2. tài xế báo cân ở mỏ
    b = lap("THU-CM-B", dn["tx01"])
    assert hang(b) == [] and not b["weight_origin"], hang(b)
    g0 = {"tan": "38.2", "ghi_chu": "ບິນຊັ່ງ 0457", "luc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 600)),
          "ma_gui": "thu-" + uuid.uuid4().hex[:10]}
    s, g = bao(b["id"], "tx02", g0); phai(s, 403, "Tài xế khác báo cân phiếu không phải của mình → bị chặn", g)
    s, g = bao(b["id"], "ketoan", g0); phai(s, 403, "Kế toán báo cân tại mỏ → bị chặn (việc của tài xế / Bãi)", g)
    s, g = bao(b["id"], "tx01", {**g0, "tan": "0"}); phai(s, 422, "Số tấn 0 → bị từ chối", g)
    s, g = bao(b["id"], "tx01", {**g0, "luc": "2030-01-01T00:00:00Z"}); phai(s, 422, "Giờ cân ở tương lai → bị từ chối", g)
    s, g = bao(b["id"], "tx01", g0, [("anh", "phieu-can.jpg", "image/jpeg", JPG)])
    phai(s, 200, "Tài xế báo 38,2 t + ảnh phiếu cân (xe chưa xuất phát vẫn báo được)", g)
    assert g["weight_origin"] == 38.2 and hang(g) == [(QUANG, 38.2)], (g["weight_origin"], hang(g))
    s, tep = goi("/api/trips/%s/tep" % b["id"], vai="thabok")
    assert [t["kind"] for t in tep] == ["ore_bill"], [t["kind"] for t in tep]
    s, sk = goi("/api/trips/%s/events" % b["id"], vai="thabok")
    assert any("38.2" in (e.get("note") or "") and "ບິນຊັ່ງ 0457" in (e.get("note") or "") for e in sk), [e.get("note") for e in sk]
    print("  ✓ %-70s" % "Ô Cân tại mỏ tự đầy · dòng hàng 38,2 t · ảnh vào Phiếu quặng · diễn biến ghi lại")
    s, g = bao(b["id"], "tx01", g0, [("anh", "phieu-can.jpg", "image/jpeg", JPG)])
    phai(s, 200, "Máy gửi LẠI cùng mã (mất mạng rồi có mạng) → nhận, không ghi thêm", g)
    s, tep = goi("/api/trips/%s/tep" % b["id"], vai="thabok")
    assert len(tep) == 1, len(tep)
    s, g = bao(b["id"], "tx01", {**g0, "tan": "38.4", "ma_gui": "thu-" + uuid.uuid4().hex[:10]})
    phai(s, 200, "Báo lại số khác (không ảnh — phiếu nhập tay được) → 38,4 t", g)
    assert g["weight_origin"] == 38.4 and hang(g) == [(QUANG, 38.4)], hang(g)
    s, g = goi("/api/trips/%s/sections/trans/send" % b["id"], {}, "thabok"); phai(s, 200, "Bãi xem lại rồi Gửi kiểm tra mục II", g)
    s, g = bao(b["id"], "tx01", {**g0, "tan": "38.5", "ma_gui": "thu-" + uuid.uuid4().hex[:10]})
    phai(s, 200, "Mục II mới gửi kiểm (chưa kiểm) → tài xế vẫn báo sửa được", g)
    s, g = goi("/api/trips/%s/sections/trans/verify" % b["id"], {}, "ketoan"); phai(s, 200, "Kế toán kiểm mục II", g)
    s, g = bao(b["id"], "tx01", {**g0, "tan": "39", "ma_gui": "thu-" + uuid.uuid4().hex[:10]})
    phai(s, 409, "Mục II đã kiểm → tài xế không đổi cân tại mỏ được nữa", g)
    giao = lap("THU-CM-G", dn["tx01"], kind="giao")
    s, g = bao(giao["id"], "tx01", g0); phai(s, 409, "Phiếu GIAO → không có báo cân ở mỏ", g)

    # ---------------------------------------------------------------- 3. Xe đã tới: phiếu gom phải có cân tại mỏ
    c = lap("THU-CM-C", dn["tx01"])
    s, g = goi("/api/trips/%s/transport-status" % c["id"], {"status": "arrived", "weight_dest": 29.8}, "admin")
    phai(s, 422, "Xe gom tới mà chưa có cân tại mỏ → bị chặn (hàng không có số vào kho)", g)
    s, g = goi("/api/trips/%s" % c["id"], vai="thabok")
    assert g["transport_status"] != "arrived" and not g["weight_dest"], "bị chặn thì phiếu chưa được ghi là đã tới"
    s, g = goi("/api/trips/%s/transport-status" % c["id"], {"status": "arrived", "weight_origin": 30, "weight_dest": 29.8}, "admin")
    phai(s, 200, "Hộp Xe đã tới ghi luôn cân tại mỏ 30 + cân bãi 29,8", g)
    assert g["weight_origin"] == 30 and hang(g) == [(QUANG, 30.0)], hang(g)
    hao = [x for x in g["goods"] if x["loai"] == "hao_hut"]
    assert hao and abs(hao[0]["qty_t"] - 0.2) < 0.001, g["goods"]
    s, lo = goi("/api/kho-hang/lo", vai="thabok")
    mot = [x for x in lo if x["lo_trip_id"] == c["id"]]
    assert mot and abs(mot[0]["con_t"] - 29.8) < 0.001, mot
    print("  ✓ %-70s" % "Hàng vào kho 29,8 t (cân bãi) · dòng hao hụt 0,2 t · có lô cho phiếu giao lấy")
    s, g = goi("/api/trips/%s/transport-status" % b["id"], {"status": "arrived", "weight_origin": 38.5, "weight_dest": 38.1}, "admin")
    phai(s, 200, "Phiếu tài xế đã báo cân: Xe đã tới với số điền sẵn (không đổi) → được", g)
    s, g = goi("/api/trips/%s/transport-status" % a["id"], {"status": "arrived", "weight_origin": 45, "weight_dest": 39.8}, "admin")
    assert s == 200 and g["weight_origin"] == 45 and hang(g) == [(QUANG, 45.0)], (s, g.get("weight_origin"), hang(g) if s == 200 else g)
    print("  ✓ %-70s %s" % ("Mục II chưa kiểm: hộp Xe đã tới sửa được cân tại mỏ (40 → 45)", s))
    s, g = bao(b["id"], "tx01", {**g0, "tan": "38.9", "ma_gui": "thu-" + uuid.uuid4().hex[:10]})
    phai(s, 409, "Xe đã về tới bãi → không báo cân ở mỏ được nữa", g)


def main():
    try:
        chay()
        print("\nTHỬ CÂN TẠI MỎ: ĐẠT — máy tự ghi dòng hàng phiếu gom · tài xế báo từ điện thoại · Xe đã tới hỏi cân mỏ")
    finally:
        for pid in reversed(TAO):
            goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        print("  · đã xoá %d phiếu thử" % len(TAO))


if __name__ == "__main__":
    main()
