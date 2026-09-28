# -*- coding: utf-8 -*-
"""Thử LUỒNG HAI DO: phiếu gom hàng (mỏ → bãi) và phiếu giao hàng (bãi → cảng) nối nhau qua kho bãi.

    python kiem/thu_hai_do.py [http://127.0.0.1:8010]

Đi đúng đường người dùng đi: Bãi lập DO gom kèm dòng hàng → xe về bãi thì hàng vào kho và sinh phiếu
nhập kho → Bãi lập DO giao lấy hàng từ lô đó → sinh phiếu xuất kho, tồn giảm → giao xong có dòng hao
hụt → và kiểm những chỗ PHẢI bị từ chối (lấy quá tồn, xuất hoá đơn cho phiếu gom, xoá lô đã xuất).

Từ 28/09 (đợt 5) SỔ KHO HÀNG ở trang kế toán (EPL_KT, mặc định 8031 — máy điều xe đang kiểm phải trỏ vào đó): tồn,
tờ PNK_HH / PXK_HH / DC_HH và điều chỉnh kho kiểm ở bên đó; dòng hàng vẫn trên phiếu bên này. Thêm bước mất nối: trang
kế toán tắt thì lưu phiếu giao lấy lô và báo xe gom tới bãi bị chặn 503, không ghi gì nửa vời.
"""
import json
import sys
import urllib.error
import urllib.request
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _quy_trinh as Q  # Bãi lập không tiền → KT nhập giá (quy trình 23/09)
import _ke_toan as K       # sổ kho hàng ở trang kế toán (28/09, đợt 5)

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


def chi_tam_ung(pid, phai):
    """Quy trình: tài xế cầm tiền đi đường (mục IV "đã chi") rồi mới xuất phát / báo xe tới — từ 23/09 máy chặn
    cả hai cửa. Bộ kiểm đi đủ 4 bước như người thật thay vì bấm thẳng "Xe đã tới"."""
    for hd, v in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp"), ("pay", "quytb")):
        s, g = goi("/api/trips/%s/sections/travel/%s" % (pid, hd), {}, vai=v)
        if s == 409 and isinstance(g, dict) and (g.get("detail") or {}).get("ma") in ("MUC_TRONG", "SAI_BUOC"):
            return          # mục IV trống, hoặc đã đi qua bước này rồi
        phai(s, 200, "mục IV: %s (%s)" % (hd, v), g)


def ton_kho(vai="ketoan"):
    s, g = K.kt("/api/kho-hang", vai=vai)
    assert s == 200, ("sổ kho hàng bên trang kế toán", s, g)
    return g["ton_t"]


CAU_HINH = {}


def tat_ke_toan(tat):
    """Trỏ trang điều xe sang một cổng không ai nghe (trang kế toán 'tắt'), hoặc trả về như cũ."""
    if tat:
        CAU_HINH["cu"] = goi("/api/ke-toan/cau-hinh", vai="admin")[1]["ke_toan_api"]
    goi("/api/ke-toan/cau-hinh", {"ke_toan_api": "http://127.0.0.1:8097" if tat else CAU_HINH["cu"]}, vai="admin", method="PUT")


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "quytb", "doanhthu", "admin"):
        dang_nhap(u)
    print("✓ đăng nhập 4 vai")

    # ---- dọn phiếu thử của lần chạy trước (giao trước, gom sau — không xoá được lô đã xuất)
    s, ds = goi("/api/trips", vai="admin")
    for so in ("THU-GIAO-02/EPL", SO_GIAO, "THU-GOM-02/EPL", SO_GOM):
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
    s, gom = Q.lap_phieu(goi, {
        "doc_no": SO_GOM, "kind": "gom", "vehicle_id": xe1["id"], "driver_id": tx[0]["id"],
        "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-20", "out_date": "2026-09-20",
        "origin": "ກາສີ", "destination": "ທ່າບົກ", "weight_origin": 40,
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 40}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập DO GOM kèm dòng hàng 40 t", gom)
    assert gom["kind"] == "gom" and len(gom["goods"]) == 1, "phiếu phải là loại gom và có một dòng hàng"
    assert ton_kho() == ton0, "chưa về tới bãi thì tồn kho KHÔNG được đổi"
    print("  ✓ chưa về bãi: tồn kho giữ nguyên %s t" % ton0)

    # xe về tới bãi, cân bãi 39,6 t (hao 0,4 so với cân mỏ) — tài xế đã cầm tạm ứng mục IV từ trước
    chi_tam_ung(gom["id"], phai)
    s, g = goi("/api/trips/%s/transport-status" % gom["id"],
               {"status": "arrived", "weight_dest": 39.6, "back_date": "2026-09-21", "odo_back": 200},
               vai="thabok")
    phai(s, 200, "Xe gom về tới bãi, cân bãi 39,6 t", g)
    assert round(ton_kho() - ton0, 2) == 39.6, "hàng phải vào kho đúng 39,6 t (cân tại bãi), đang: %s" % (ton_kho() - ton0)
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin")
    hao = [x for x in g["goods"] if x["loai"] == "hao_hut"]
    assert hao and abs(hao[0]["qty_t"] - 0.4) < 0.01, "phải tự ghi MỘT DÒNG hao hụt 0,4 t: %s" % g["goods"]
    print("  ✓ vào kho 39,6 t · dòng hao hụt %s t ghi sẵn trên phiếu" % hao[0]["qty_t"])
    pnk = [v for v in K.to_kho(SO_GOM, "PNK_HH") if v["trip_no"] == SO_GOM]
    assert len(pnk) == 1 and abs(pnk[0]["lines"]["tan"] - 39.6) < 0.01 and not pnk[0].get("entry_id"), \
        "phải sinh MỘT tờ PNK_HH 39,6 t ở sổ kế toán (ngoài bảng, không bút toán): %s" % pnk
    print("  ✓ sổ kế toán có phiếu nhập kho hàng %s (39,6 t, ngoài bảng)" % pnk[0]["ref"])
    s, g = goi("/api/kho-hang", vai="admin")
    phai(s, 409, "Màn Kho hàng bên trang điều xe → đã dời sang trang kế toán", g)

    # ================================================================ 2. DO GIAO lấy hàng của lô đó
    s, lo = goi("/api/kho-hang/lo", vai="thabok")
    lo_moi = next(x for x in lo if x["doc_no"] == SO_GOM)
    assert abs(lo_moi["con_t"] - 39.6) < 0.01, "lô mới phải còn 39,6 t"

    s, g = Q.lap_phieu(goi, {
        "doc_no": SO_GIAO, "kind": "giao", "vehicle_id": xe2["id"], "driver_id": tx[0]["id"],
        "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-22", "out_date": "2026-09-22",
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 100, "tu_phieu_id": gom["id"]}],
    }, vai="thabok")
    phai(s, 409, "Lấy 100 t từ lô chỉ còn 39,6 t → bị từ chối", g)

    s, giao = Q.lap_phieu(goi, {
        "doc_no": SO_GIAO, "kind": "giao", "vehicle_id": xe2["id"], "driver_id": tx[0]["id"],
        "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-22", "out_date": "2026-09-22",
        "price": 43, "price_ccy": "USD",
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 25, "tu_phieu_id": gom["id"]}],
    }, vai="thabok")
    phai(s, 200, "Bãi lập DO GIAO lấy 25 t từ lô", giao)
    assert giao["weight_origin"] == 25, "cân đầu của phiếu giao = tấn lấy khỏi kho, đang: %s" % giao["weight_origin"]
    assert round(ton_kho() - ton0, 2) == 14.6, "tồn phải còn 14,6 t sau khi xuất 25 t"
    print("  ✓ xuất kho 25 t · tồn lô còn %s t · xe chặng giao khác xe chặng gom: %s ≠ %s"
          % (round(ton_kho() - ton0, 2), giao["truck_no"], gom["truck_no"]))
    pxk = [v for v in K.to_kho(SO_GIAO, "PXK_HH") if v["trip_no"] == SO_GIAO]
    assert len(pxk) == 1 and abs(pxk[0]["lines"]["tan"] - 25) < 0.01, "phải sinh MỘT tờ PXK_HH 25 t ở sổ kế toán: %s" % pxk
    print("  ✓ sổ kế toán có phiếu xuất kho hàng %s (25 t)" % pxk[0]["ref"])

    # nối hai phiếu: dòng hàng của phiếu giao chỉ đúng số phiếu gom
    assert giao["goods"][0]["tu_phieu_doc_no"] == SO_GOM, "dòng hàng phải chỉ rõ lấy từ phiếu gom nào"
    print("  ✓ hai DO nối nhau: %s lấy hàng của %s" % (SO_GIAO, giao["goods"][0]["tu_phieu_doc_no"]))

    # ================================================================ 3. giao xong → hao hụt chặng giao
    chi_tam_ung(giao["id"], phai)
    s, g = goi("/api/trips/%s/transport-status" % giao["id"],
               {"status": "arrived", "weight_dest": 24.7, "back_date": "2026-09-24", "odo_back": 300},
               vai="thabok")
    phai(s, 200, "Giao xong, cân ở cảng 24,7 t", g)
    s, g = goi("/api/trips/%s" % giao["id"], vai="admin")
    hao = [x for x in g["goods"] if x["loai"] == "hao_hut"]
    assert hao and abs(hao[0]["qty_t"] - 0.3) < 0.01, "phải ghi dòng hao hụt 0,3 t trên phiếu giao: %s" % g["goods"]
    print("  ✓ dòng hao hụt chặng giao: %s t" % hao[0]["qty_t"])

    # ================================================================ 3b. sửa sau khi đã tới: hao hụt phải tính lại
    s, g = goi("/api/trips/%s" % giao["id"], {"weight_dest": 24.0}, vai="admin", method="PUT")
    phai(s, 200, "Sửa cân cuối phiếu giao (24,7 → 24,0)", g)
    hao = [x for x in g["goods"] if x["loai"] == "hao_hut"]
    assert hao and abs(hao[0]["qty_t"] - 1.0) < 0.01, "sửa cân cuối thì dòng hao hụt phải tính lại thành 1,0 t: %s" % g["goods"]
    print("  ✓ sửa cân cuối → dòng hao hụt tính lại: %s t" % hao[0]["qty_t"])

    # ================================================================ 3c. điều chỉnh kho: sửa số bằng một dòng có lý do
    # (màn Kho hàng ở trang kế toán — cùng tên đăng nhập, đăng nhập riêng)
    s, g = K.kt("/api/kho-hang/dieu-chinh", {"lo_trip_id": gom["id"], "qty_t": -0.6, "ly_do": "cân bãi ghi dư"}, vai="thabok")
    phai(s, 403, "Bãi tự điều chỉnh kho (trang kế toán) → bị từ chối (kế toán ghi)", g)
    s, g = K.kt("/api/kho-hang/dieu-chinh", {"lo_trip_id": gom["id"], "qty_t": -0.6, "ly_do": "x"}, vai="ketoan")
    phai(s, 422, "Điều chỉnh không ghi lý do → bị từ chối", g)
    s, g = K.kt("/api/kho-hang/dieu-chinh", {"lo_trip_id": gom["id"], "qty_t": -0.6, "ly_do": "cân bãi ghi dư 0,6 t"}, vai="ketoan")
    phai(s, 200, "Kế toán điều chỉnh lô −0,6 t có lý do (trang kế toán)", g)
    assert abs(g["con_t"] - 14.0) < 0.01, "lô còn 14,6 giảm 0,6 phải còn 14,0: %s" % g["con_t"]
    s, g = K.kt("/api/kho-hang/dieu-chinh", {"lo_trip_id": gom["id"], "qty_t": -20, "ly_do": "thử giảm quá tồn"}, vai="ketoan")
    phai(s, 409, "Giảm quá tồn (hàng đã xuất cho phiếu giao) → bị từ chối", g)
    dc = [v for v in K.to_kho(SO_GOM, "DC_HH") if v["trip_no"] == SO_GOM]
    assert len(dc) == 1 and dc[0]["lines"]["chieu"] == "giam", "phải sinh MỘT tờ DC_HH (giảm) ở sổ kế toán: %s" % dc
    s, g = goi("/api/kho-hang/dieu-chinh", {"lo_trip_id": gom["id"], "qty_t": -0.6, "ly_do": "cân bãi ghi dư"}, vai="ketoan")
    phai(s, 409, "Điều chỉnh ở trang điều xe → đã dời sang trang kế toán", g)
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin")
    assert abs((g.get("ton_lo") or 0) - 14.0) < 0.01, "mở phiếu gom phải thấy tồn lô 14,0 t (hỏi trang kế toán): %s" % g.get("ton_lo")
    print("  ✓ điều chỉnh kho: một dòng −0,6 t có lý do · tồn 14,0 t · tờ %s · phiếu gom thấy tồn lô 14,0 t" % dc[0]["ref"])

    # ================================================================ 4. những chỗ phải bị chặn
    s, g = goi("/api/trips/%s" % gom["id"], {"goods": [{"goods_name": "x", "qty_t": 50}]}, vai="admin", method="PUT")
    phai(s, 409, "Sửa dòng hàng phiếu gom ĐÃ nhập kho → bị từ chối", g)
    s, g = goi("/api/trips/%s" % gom["id"], {"weight_dest": 30}, vai="admin", method="PUT")
    phai(s, 409, "Sửa cân bãi phiếu gom ĐÃ nhập kho → bị từ chối", g)
    s, g = goi("/api/trips/%s" % giao["id"], {"kind": "gom"}, vai="admin", method="PUT")
    phai(s, 409, "Đổi loại phiếu khi đã có sổ kho → bị từ chối", g)
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin")
    assert any(x["loai"] == "hao_hut" for x in g["goods"]), "dòng hao hụt của phiếu gom phải còn nguyên sau các lần bị từ chối"
    # B4 (anh Khampla 22/09): phiếu gom CÓ cước riêng, nên không còn bị chặn vì LOẠI phiếu —
    # chỉ còn chặn theo bước như mọi phiếu (mục II chưa kiểm, phiếu chưa khoá).
    s, g = K.kt("/api/hoa-don/phieu/%s/xuat" % gom["id"], {}, vai="doanhthu")      # hoá đơn ở trang kế toán (đợt 7a)
    ma = (g.get("detail") or {}).get("ma") if isinstance(g, dict) else None
    assert s == 409 and ma in ("CHUA_KIEM", "CHUA_KHOA"), "phiếu gom chưa kiểm/khoá phải bị chặn theo BƯỚC, không phải theo loại: %s %s" % (s, ma)
    assert ma != "PHIEU_GOM", "không được chặn hoá đơn chỉ vì là phiếu gom nữa"
    print("  ✓ %-58s %s %s" % ("Hoá đơn phiếu GOM: chặn theo bước, không chặn theo loại", s, ma))
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin", method="DELETE")
    phai(s, 409, "Xoá phiếu gom đã có người lấy hàng → bị từ chối", g)

    # ================================================================ 4b. trang kế toán tắt → chặn và báo rõ
    SO_GIAO2, SO_GOM2 = "THU-GIAO-02/EPL", "THU-GOM-02/EPL"
    ton_truoc = ton_kho()
    s, gom2 = Q.lap_phieu(goi, {
        "doc_no": SO_GOM2, "kind": "gom", "vehicle_id": xe1["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
        "route_id": tuyen[0]["id"], "doc_date": "2026-09-25", "out_date": "2026-09-25", "weight_origin": 10,
        "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 10}]}, vai="thabok")
    phai(s, 200, "Lập DO GOM thứ hai (chưa đụng kho)", gom2)
    chi_tam_ung(gom2["id"], phai)
    tat_ke_toan(True)
    try:
        s, g = goi("/api/trips", {"doc_no": SO_GIAO2, "kind": "giao", "vehicle_id": xe2["id"], "driver_id": tx[0]["id"],
                                  "customer_id": kh[0]["id"], "route_id": tuyen[0]["id"], "doc_date": "2026-09-25",
                                  "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 5, "tu_phieu_id": gom["id"]}]}, vai="thabok")
        phai(s, 503, "Trang kế toán tắt → lập DO GIAO lấy lô bị chặn", g)
        assert g["detail"]["ma"] == "CHUA_NOI_KE_TOAN", g
        s, ds2 = goi("/api/trips", vai="admin")
        assert not [p for p in ds2 if p["doc_no"] == SO_GIAO2], "bị chặn thì KHÔNG được có phiếu giao nửa vời"
        s, g = goi("/api/trips/%s/transport-status" % gom2["id"], {"status": "arrived", "weight_dest": 10, "back_date": "2026-09-26"}, vai="thabok")
        phai(s, 503, "Trang kế toán tắt → báo xe gom tới bãi bị chặn", g)
        s, g = goi("/api/trips/%s" % gom2["id"], vai="admin")
        assert g["transport_status"] != "arrived" and not [x for x in g["goods"] if x["loai"] == "hao_hut"], "bị chặn thì phiếu gom chưa được ghi là đã tới"
        s, g = goi("/api/trips/%s" % gom2["id"], {"note": "sửa ghi chú khi kế toán tắt"}, vai="thabok", method="PUT")
        phai(s, 200, "Trang kế toán tắt → sửa việc không đụng kho vẫn được", g)
    finally:
        tat_ke_toan(False)
    assert abs(ton_kho() - ton_truoc) < 0.001, "bị chặn thì sổ kho hàng không đổi"
    s, g = goi("/api/trips/%s/transport-status" % gom2["id"], {"status": "arrived", "weight_dest": 10, "back_date": "2026-09-26"}, vai="thabok")
    phai(s, 200, "Nối lại → báo xe gom tới được, hàng vào kho", g)
    assert abs(ton_kho() - ton_truoc - 10) < 0.001, "nối lại thì 10 t phải vào kho"
    s, g = goi("/api/trips/%s" % gom2["id"], vai="admin", method="DELETE")
    phai(s, 200, "Xoá DO GOM thứ hai (chưa ai lấy) → lô rời kho", g)
    assert abs(ton_kho() - ton_truoc) < 0.001 and not K.to_kho(SO_GOM2, "PNK_HH"), "xoá phiếu gom thì lô và tờ PNK_HH của nó phải đi theo"
    print("  ✓ mất nối: chặn rõ, không ghi nửa vời · việc không đụng kho vẫn chạy · nối lại làm được · xoá phiếu thì rút tờ")

    # ================================================================ 5. dọn
    s, g = goi("/api/trips/%s" % giao["id"], vai="admin", method="DELETE")
    phai(s, 200, "Xoá phiếu giao thử", g)
    assert round(ton_kho() - ton0, 2) == 39.0, "xoá phiếu giao thì hàng phải trả lại kho (39,6 nhập − 0,6 điều chỉnh): %s" % round(ton_kho() - ton0, 2)
    print("  ✓ xoá phiếu giao: hàng trả lại kho, tồn về %s t (đã trừ điều chỉnh)" % round(ton_kho() - ton0, 2))
    s, g = goi("/api/trips/%s" % gom["id"], vai="admin", method="DELETE")
    phai(s, 200, "Xoá phiếu gom thử", g)
    assert round(ton_kho() - ton0, 2) == 0, "xoá phiếu gom thì lô cũng mất khỏi kho"
    print("  ✓ xoá phiếu gom: tồn kho về đúng lúc đầu")

    assert not K.to_kho(SO_GOM, "PNK_HH") and not K.to_kho(SO_GIAO, "PXK_HH") and not K.to_kho(SO_GOM, "DC_HH"), \
        "xoá phiếu thì tờ kho hàng ở sổ kế toán phải rút theo"
    print("  ✓ tờ PNK_HH / PXK_HH / DC_HH của hai phiếu thử đã rút khỏi sổ kế toán")

    print("\nTHỬ HAI DO: ĐẠT — gom → nhập kho → giao lấy lô → xuất kho → hao hụt · sửa sau khi tới tính lại · điều chỉnh kho (trang kế toán) · mất nối chặn rõ · 9 chỗ từ chối đúng")


if __name__ == "__main__":
    main()
