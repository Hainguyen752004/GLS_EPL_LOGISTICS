# -*- coding: utf-8 -*-
"""Thử LUỒNG HAI DO: phiếu gom hàng (mỏ → bãi) và phiếu giao hàng (bãi → cảng) nối nhau qua kho bãi.

    python kiem/thu_hai_do.py [http://127.0.0.1:8010]

Đi đúng đường người dùng đi: Bãi lập DO gom kèm dòng hàng → xe về bãi thì hàng vào kho và sinh phiếu
nhập kho → Bãi lập DO giao lấy hàng từ lô đó → sinh phiếu xuất kho, tồn giảm → giao xong có dòng hao
hụt → và kiểm những chỗ PHẢI bị từ chối (lấy quá tồn, xuất hoá đơn cho phiếu gom, xoá lô đã xuất).
"""
import json
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
TOKEN = {}
SO_GOM, SO_GIAO = "THU-GOM-01/EPL", "THU-GIAO-01/EPL"


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau,
                               method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=30) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def dang_nhap(u):
    s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
    assert s == 200, "đăng nhập %s hỏng: %s" % (u, g)
    TOKEN[u if u != "thabok" else "thabok"] = g["token"]
    return g


def phai(s, mong, buoc, g=None):
    dau = "  ✓" if s == mong else "  SAI"
    dt_ = (g or {}).get("detail") if isinstance(g, dict) else None
    ma = dt_.get("ma", "") if isinstance(dt_, dict) else (dt_ or "")
    print("%s %-58s %s %s" % (dau, buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def ton_kho(vai="admin"):
    s, g = goi("/api/kho-hang", vai=vai)
    return g["ton_t"]


def main():
    for u in ("thabok", "ketoan", "doanhthu", "admin"):
        dang_nhap(u)
    print("✓ đăng nhập 4 vai")

    # ---- dọn phiếu thử của lần chạy trước (giao trước, gom sau — không xoá được lô đã xuất)
    s, ds = goi("/api/trips", vai="admin")
    for so in (SO_GIAO, SO_GOM):
        for p in ds:
            if p["doc_no"] == so:
                goi("/api/trips/%s" % p["id"], vai="admin", method="DELETE")
                print("  · đã dọn %s của lần trước" % so)

    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    s, kh = goi("/api/customers", vai="thabok")
    s, tuyen = goi("/api/routes", vai="thabok")
    xe1, xe2 = xe[0], (xe[1] if len(xe) > 1 else xe[0])

    # ================================================================ 1. DO GOM
    ton0 = ton_kho()
    s, gom = goi("/api/trips", {
        "doc_no": SO_GOM, "kind": "gom", "vehicle_id": xe1["id"], "driver_id": tx[0]["id"],
        "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-20", "out_date": "2026-09-20",
        "origin": "ກາສີ", "destination": "ທ່າບົກ", "weight_origin": 40,
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 40}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập DO GOM kèm dòng hàng 40 t", gom)
    assert gom["kind"] == "gom" and len(gom["goods"]) == 1, "phiếu phải là loại gom và có một dòng hàng"
    assert ton_kho() == ton0, "chưa về tới bãi thì tồn kho KHÔNG được đổi"
    print("  ✓ chưa về bãi: tồn kho giữ nguyên %s t" % ton0)

    # xe về tới bãi, cân bãi 39,6 t (hao 0,4 so với cân mỏ)
    s, g = goi("/api/trips/%s/transport-status" % gom["id"],
               {"status": "arrived", "weight_dest": 39.6, "back_date": "2026-09-21", "odo_back": 200},
               vai="thabok")
    phai(s, 200, "Xe gom về tới bãi, cân bãi 39,6 t", g)
    assert round(ton_kho() - ton0, 2) == 39.6, "hàng phải vào kho đúng 39,6 t (cân tại bãi), đang: %s" % (ton_kho() - ton0)
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin")
    hao = [x for x in g["goods"] if x["loai"] == "hao_hut"]
    assert hao and abs(hao[0]["qty_t"] - 0.4) < 0.01, "phải tự ghi MỘT DÒNG hao hụt 0,4 t: %s" % g["goods"]
    print("  ✓ vào kho 39,6 t · dòng hao hụt %s t ghi sẵn trên phiếu" % hao[0]["qty_t"])
    s, ct = goi("/api/chung-tu?loai=PNK_HH", vai="ketoan")
    assert any(c["trip_doc_no"] == SO_GOM for c in ct["ds"]), "phải sinh phiếu nhập kho hàng PNK_HH"
    print("  ✓ sổ chứng từ có phiếu nhập kho hàng")

    # ================================================================ 2. DO GIAO lấy hàng của lô đó
    s, lo = goi("/api/kho-hang/lo", vai="thabok")
    lo_moi = next(x for x in lo if x["doc_no"] == SO_GOM)
    assert abs(lo_moi["con_t"] - 39.6) < 0.01, "lô mới phải còn 39,6 t"

    s, g = goi("/api/trips", {
        "doc_no": SO_GIAO, "kind": "giao", "vehicle_id": xe2["id"], "driver_id": tx[0]["id"],
        "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-22", "out_date": "2026-09-22",
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 100, "tu_phieu_id": gom["id"]}],
    }, vai="thabok")
    phai(s, 409, "Lấy 100 t từ lô chỉ còn 39,6 t → bị từ chối", g)

    s, giao = goi("/api/trips", {
        "doc_no": SO_GIAO, "kind": "giao", "vehicle_id": xe2["id"], "driver_id": tx[0]["id"],
        "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-22", "out_date": "2026-09-22",
        "price_usd": 43,
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 25, "tu_phieu_id": gom["id"]}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập DO GIAO lấy 25 t từ lô", giao)
    assert giao["weight_origin"] == 25, "cân đầu của phiếu giao = tấn lấy khỏi kho, đang: %s" % giao["weight_origin"]
    assert round(ton_kho() - ton0, 2) == 14.6, "tồn phải còn 14,6 t sau khi xuất 25 t"
    print("  ✓ xuất kho 25 t · tồn lô còn %s t · xe chặng giao khác xe chặng gom: %s ≠ %s"
          % (round(ton_kho() - ton0, 2), giao["truck_no"], gom["truck_no"]))
    s, ct = goi("/api/chung-tu?loai=PXK_HH", vai="ketoan")
    assert any(c["trip_doc_no"] == SO_GIAO for c in ct["ds"]), "phải sinh phiếu xuất kho hàng PXK_HH"
    print("  ✓ sổ chứng từ có phiếu xuất kho hàng")

    # nối hai phiếu: dòng hàng của phiếu giao chỉ đúng số phiếu gom
    assert giao["goods"][0]["tu_phieu_doc_no"] == SO_GOM, "dòng hàng phải chỉ rõ lấy từ phiếu gom nào"
    print("  ✓ hai DO nối nhau: %s lấy hàng của %s" % (SO_GIAO, giao["goods"][0]["tu_phieu_doc_no"]))

    # ================================================================ 3. giao xong → hao hụt chặng giao
    s, g = goi("/api/trips/%s/transport-status" % giao["id"],
               {"status": "arrived", "weight_dest": 24.7, "back_date": "2026-09-24", "odo_back": 300},
               vai="thabok")
    phai(s, 200, "Giao xong, cân ở cảng 24,7 t", g)
    s, g = goi("/api/trips/%s" % giao["id"], vai="admin")
    hao = [x for x in g["goods"] if x["loai"] == "hao_hut"]
    assert hao and abs(hao[0]["qty_t"] - 0.3) < 0.01, "phải ghi dòng hao hụt 0,3 t trên phiếu giao: %s" % g["goods"]
    print("  ✓ dòng hao hụt chặng giao: %s t" % hao[0]["qty_t"])

    # ================================================================ 4. những chỗ phải bị chặn
    s, g = goi("/api/trips/%s/invoice" % gom["id"], {}, vai="doanhthu")
    phai(s, 409, "Xuất hoá đơn cho phiếu GOM → bị từ chối", g)
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin", method="DELETE")
    phai(s, 409, "Xoá phiếu gom đã có người lấy hàng → bị từ chối", g)

    # ================================================================ 5. dọn
    s, g = goi("/api/trips/%s" % giao["id"], vai="admin", method="DELETE")
    phai(s, 200, "Xoá phiếu giao thử", g)
    assert round(ton_kho() - ton0, 2) == 39.6, "xoá phiếu giao thì hàng phải trả lại kho"
    print("  ✓ xoá phiếu giao: hàng trả lại kho, tồn về %s t" % round(ton_kho() - ton0, 2))
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin", method="DELETE")
    phai(s, 200, "Xoá phiếu gom thử", g)
    assert round(ton_kho() - ton0, 2) == 0, "xoá phiếu gom thì lô cũng mất khỏi kho"
    print("  ✓ xoá phiếu gom: tồn kho về đúng lúc đầu")

    print("\nTHỬ HAI DO: ĐẠT — gom → nhập kho → giao lấy lô → xuất kho → hao hụt · 3 chỗ từ chối đúng")


if __name__ == "__main__":
    main()
