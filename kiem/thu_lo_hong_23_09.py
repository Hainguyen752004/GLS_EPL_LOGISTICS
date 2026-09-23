# -*- coding: utf-8 -*-
"""Hai lỗ hổng quy trình bấm tay tìm ra 23/09 + danh mục Acc code thật.

    python kiem/thu_lo_hong_23_09.py [http://127.0.0.1:8011]

  1. Mục có dòng EPL trả mà ĐƠN GIÁ 0: Bãi GỬI được (Bãi không nhập giá — anh Khampla A2, 23/09), nhưng
     KT Chi phí KIỂM thì bị chặn (THIEU_DON_GIA) tới khi chính KT Chi phí nhập đơn giá.
  2. Bãi bấm "Xe đã tới" khi mục IV chưa chi tạm ứng → bị chặn (CHUA_NHAN_TAM_UNG), giống cửa Xuất phát.
  3. Quỹ chi THẲNG mục IV → sinh đúng MỘT tờ PC_TU bằng tiền mặt đi đường (không tính dòng trả bằng thẻ).
  4. Danh mục Acc code đọc được từ API bên công nợ (không còn "bản tạm từ Excel").
Phiếu thử được xoá khi xong nếu còn xoá được; tờ chứng từ đã sinh thì giữ (sổ không xoá tờ đã ghi).
"""
import json
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
TK = {}
import time
SO = "LOHONG-%s/EPL" % time.strftime("%d%H%M%S")   # mỗi lần chạy một số: phiếu lần trước đã sinh chứng từ nên không xoá được


def goi(duong, body=None, vai="admin", method=None):
    du = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(GOC + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + TK.get(vai, "")})
    try:
        with urllib.request.urlopen(r, timeout=60) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def phai(s, mong, buoc, g=None):
    assert s == mong, "%s: mong %s, nhận %s — %s" % (buoc, mong, s, json.dumps(g, ensure_ascii=False)[:300])
    print("  ✓ %-62s %s%s" % (buoc, s, (" " + g["detail"]["ma"]) if isinstance(g, dict) and isinstance(g.get("detail"), dict) else ""))


def main():
    for u in ("admin", "thabok", "ketoan", "ketoancp", "quytb"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); assert s == 200, (u, g)
        TK[u] = g["token"]
    # dọn phiếu thử lần trước
    s, cu = goi("/api/trips?q=LOHONG")
    for p in cu or []:
        if p["doc_no"].startswith("LOHONG-") and p["transport_status"] != "arrived":
            goi("/api/trips/%s" % p["id"], method="DELETE")
    s, xe = goi("/api/vehicles", vai="thabok"); s, tx = goi("/api/drivers", vai="thabok"); s, kh = goi("/api/customers", vai="thabok")
    s, tuyen = goi("/api/routes", vai="thabok")
    nha = next(x for x in xe if x["owner_type"] != "joint")
    s, p = goi("/api/trips", {"doc_no": SO, "company": "EPL", "vehicle_id": nha["id"], "driver_id": tx[0]["id"], "customer_id": kh[0]["id"],
                              "route_id": tuyen[0]["id"], "weight_origin": 40, "odo_out": 1000,
                              "expenses": [{"section": "travel", "item_key": "x_food", "qty": 2, "unit_price": 0, "currency": "LAK", "paid_by_epl": True}]},
               vai="thabok")
    phai(s, 200, "Bãi lập phiếu thử có dòng đi đường giá 0", p)
    P = p["id"]

    # ---- 1. dòng giá 0: Bãi gửi được, KT Chi phí kiểm thì bị chặn tới khi nhập giá
    s, g = goi("/api/trips/%s" % P, vai="thabok")
    assert all("unit_price" not in d for d in g["expenses"]) and "rate_usd" not in g and "chi" not in g["tinh"],         "gói trả cho Bãi không được có đơn giá, tỷ giá, tổng chi"
    print("  ✓ %-62s" % "Bãi mở phiếu: không có đơn giá, tỷ giá, tổng chi")
    s, g = goi("/api/trips/%s/sections/travel/send" % P, {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục IV (chưa có giá) → được", g)
    s, g = goi("/api/trips/%s/sections/travel/verify" % P, {}, vai="ketoancp"); phai(s, 409, "KT Chi phí kiểm mục IV có dòng giá 0 → bị chặn", g)
    assert g["detail"]["ma"] == "THIEU_DON_GIA" and "dòng" in g["detail"]["loi"], g
    print("     câu lỗi KT Chi phí thấy: «%s»" % g["detail"]["loi"])
    s, full = goi("/api/trips/%s" % P, vai="ketoancp")
    dong = [{"id": d["id"], "section": "travel", "unit_price": 150000, "currency": "LAK"} for d in full["expenses"] if d["section"] == "travel" and not d.get("unit_price")]
    s, g = goi("/api/trips/%s" % P, {"expenses": [{"section": "travel", "item_key": "x_food", "qty": 1}]}, vai="ketoancp", method="PUT")
    phai(s, 409, "KT Chi phí thêm dòng mới → bị từ chối (chỉ nhập giá)", g)
    s, g = goi("/api/trips/%s" % P, {"expenses": dong}, vai="ketoancp", method="PUT"); phai(s, 200, "KT Chi phí nhập đơn giá 150.000", g)
    # Bãi lưu lại phiếu như màn hình thật: gửi đủ dòng của mình (không có giá) — kèm thử một giá 999 gõ lén
    s, cua_bai = goi("/api/trips/%s" % P, vai="thabok")
    gui = [dict(d, unit_price=999) for d in cua_bai["expenses"] if d["section"] == "travel"]
    s, g = goi("/api/trips/%s" % P, {"expenses": gui}, vai="thabok", method="PUT"); phai(s, 200, "Bãi lưu lại mục IV (đã nhập)", g)
    s, g2 = goi("/api/trips/%s" % P, vai="ketoancp")
    an = [d for d in g2["expenses"] if d["section"] == "travel" and d["item_key"] == "x_food"]
    assert an and all(d["unit_price"] == 150000 and d["qty"] == 2 for d in an),         "Bãi gửi giá 999 → máy chủ phải bỏ qua, giữ giá kế toán và số lượng: %s" % an
    print("  ✓ %-62s" % "Bãi gửi giá 999 khi mục đã nhập → bị bỏ qua, giữ 150.000")

    # ---- 2. "Xe đã tới" khi chưa chi tạm ứng → chặn
    s, g = goi("/api/trips/%s/transport-status" % P, {"status": "arrived", "weight_dest": 39.8}, vai="thabok")
    phai(s, 409, "Bãi báo Xe đã tới khi mục IV chưa chi → bị chặn", g)
    assert g["detail"]["ma"] == "CHUA_NHAN_TAM_UNG", g
    s, g = goi("/api/trips/%s/transport-status" % P, {"status": "transit"}, vai="thabok")
    phai(s, 409, "Xuất phát khi chưa chi → vẫn bị chặn như trước", g)

    # ---- 3. chi thẳng mục IV → sinh đúng một PC_TU
    s, g = goi("/api/trips/%s/sections/travel/verify" % P, {}, vai="ketoancp"); phai(s, 200, "KT Chi phí kiểm mục IV (đã có giá)", g)
    s, g = goi("/api/trips/%s/sections/travel/book" % P, {}, vai="ketoancp"); phai(s, 200, "KT Chi phí ghi sổ mục IV", g)
    s, truoc = goi("/api/chung-tu?trip_id=%s&loai=PC_TU" % P, vai="ketoan"); n0 = len(truoc["ds"])
    s, g = goi("/api/trips/%s/sections/travel/pay" % P, {}, vai="quytb"); phai(s, 200, "Tiền mặt lẻ chi thẳng mục IV", g)
    s, sau = goi("/api/chung-tu?trip_id=%s&loai=PC_TU" % P, vai="ketoan")
    moi = [c for c in sau["ds"] if c["id"] not in {x["id"] for x in truoc["ds"]}]
    assert n0 == 0 and len(moi) == 1, "phải sinh đúng một PC_TU, có %d cũ, %d mới" % (n0, len(moi))
    tien_mat = sum((d["qty"] or 0) * (d["unit_price"] or 0) for d in g["expenses"] if d["section"] == "travel" and d.get("paid_by_epl") and not d.get("toll_card_id") and d.get("source") != "kho")
    assert round(moi[0]["tien_lak"]) == round(tien_mat), (moi[0]["tien_lak"], tien_mat)
    assert moi[0]["no"] and moi[0]["co"], moi[0]
    print("  ✓ %-62s %s · %s LAK · Nợ %s / Có %s" % ("Sinh đúng một tờ chi đi đường", moi[0]["so"], format(round(moi[0]["tien_lak"]), ","), moi[0]["no"], moi[0]["co"]))
    s, g = goi("/api/trips/%s/sections/travel/pay" % P, {}, vai="quytb"); phai(s, 409, "Chi lại mục IV lần hai → sai bước, không ra tờ thứ hai", g)
    s, g = goi("/api/trips/%s/transport-status" % P, {"status": "arrived", "weight_dest": 39.8}, vai="thabok"); phai(s, 200, "Chi rồi → Bãi báo Xe đã tới được", g)

    # ---- 3b. phiếu khách NHẬP TAY được: có số phiếu quặng là đủ, không bắt đính kèm ảnh
    s, kl = goi("/api/trips/%s/kiem-lai" % P, vai="ketoan"); phai(s, 200, "Kiểm lại trước khoá (chưa có phiếu khách)", kl)
    ma = [c["ma"] for c in (kl.get("canh_bao") if isinstance(kl, dict) else kl) or []]
    assert "THIEU_PHIEU_QUANG" in ma, "chưa ảnh, chưa số phiếu mà không nhắc phiếu khách: %s" % ma
    s, g = goi("/api/trips/%s" % P, {"ore_bill_no": "PQ-2309-01", "ore_bill_date": "2026-09-23"}, vai="ketoan", method="PUT")
    phai(s, 200, "Kế toán nhập tay số phiếu quặng của khách", g)
    s, kl = goi("/api/trips/%s/kiem-lai" % P, vai="ketoan")
    ma = [c["ma"] for c in (kl.get("canh_bao") if isinstance(kl, dict) else kl) or []]
    assert "THIEU_PHIEU_QUANG" not in ma, "đã nhập tay số phiếu mà vẫn nhắc thiếu phiếu khách: %s" % ma
    print("  ✓ %-62s còn lại: %s" % ("Nhập tay số phiếu → hết nhắc thiếu phiếu khách", ma))

    # ---- 4. danh mục Acc code thật
    s, g = goi("/api/acc-codes?refresh=true", vai="ketoan"); phai(s, 200, "Danh mục Acc code", g)
    assert g["source"] == "remote" and g["count"] > 100, "vẫn đang dùng bản tạm: %s · %s" % (g["source"], g["message"])
    ma = {x["code"] for x in g["data"]}
    thieu = [m for m in ("1371", "4021", "4022") if m not in ma]
    print("  ✓ %-62s %s mã · nguồn %s" % ("Danh mục đọc từ API bên công nợ", g["count"], g["source"]))
    print("     mã đang in trên phiếu mà danh mục thật không có: %s" % (thieu or "không"))
    print("\n✅ LỖ HỔNG 23/09: dòng giá 0 bị chặn lúc kế toán kiểm (Bãi không nhập giá) · Xe đã tới qua cửa tạm ứng · chi thẳng mục IV có phiếu chi ·"
          " danh mục mã kế toán thật (%d mã)." % g["count"])


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("\nHỎNG —", e); sys.exit(1)
