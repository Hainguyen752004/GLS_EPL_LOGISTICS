# -*- coding: utf-8 -*-
"""Thử luật TẠM ỨNG / XUẤT DẦU THEO LOẠI XE (chủ dự án chốt 29/09).

    python kiem/thu_loai_xe.py [http://127.0.0.1:8011]

Xe nhà → tạm ứng nội bộ · xuất nội bộ. Xe thuê, EPL ứng → tạm ứng ghi công nợ chủ xe · dầu kho là XUẤT BÁN theo giá bán
riêng KT kho xăng dầu gõ trên phiếu; tiền trừ chủ xe tính theo giá bán; Tất toán tài xế chỉ có phiếu xe nhà.
Thêm 30/09: dầu kho chỉ rời kho theo phiếu đề nghị đã cấp (ghi sổ mục III chưa cấp → chặn); xe thuê không có "trả cùng
lương" — tiền chuyến EPL ứng là tạm ứng ghi công nợ chủ xe; màn Tiền chuyến & tiền nước chỉ xe nhà.
Bài tự lập hai phiếu trên bản sao DB thử (phiếu đã kiểm thì ở lại).
Từ 01/10 (bỏ phần tiền trang kế toán tạm) tất toán tài xế CHỐT ở trang điều xe (GET /api/tat-toan/{tài xế}), tiền ở hệ
kế toán anh Tune — bài đọc tất toán ở trang điều xe, không còn sang trang kế toán tạm.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K  # noqa: E402 — kho tạm (EPL_KT): nhập trước rồi cấp (01/10)

DX = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TK = {}
GIA_BAN = 33000


def goi(goc, duong, body=None, vai=None, method=None):
    du = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(goc + duong, data=du, method=method or ("POST" if du is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[(goc, vai)]} if vai else {})})
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
        raise SystemExit("DỪNG: %s — %s" % (buoc, json.dumps(g, ensure_ascii=False)[:400]))


def dung(dk, buoc, chi_tiet=""):
    print("  %s %-78s %s" % ("✓" if dk else "SAI", buoc, chi_tiet))
    if not dk:
        raise SystemExit("DỪNG: " + buoc)


def main():
    for u in ("thabok", "ketoan", "ketoancp", "khonl", "admin"):
        s, g = goi(DX, "/api/dang-nhap", {"username": u, "password": "1234"}); TK[(DX, u)] = g["token"]
    s, xe = goi(DX, "/api/vehicles", vai="admin"); s, tx = goi(DX, "/api/drivers", vai="admin"); s, kh = goi(DX, "/api/customers", vai="admin")
    s, diem = goi(DX, "/api/fuel-places", vai="admin")
    thue = [x for x in xe if x["owner_type"] == "joint" and x["truck_no"].startswith("ຮ່ວມ")]
    xe_thue = next((x for x in thue if x["status"] == "available"), thue[0])      # bản Lào không chặn xe đang bận
    xe_nha = next(x for x in xe if x["owner_type"] == "EPL" and x["truck_no"] in ("347", "348", "349"))
    # kho Thà Bốc (trước đây: kho EPL đầu danh sách — có lúc rơi vào kho đang âm trên bản sao)
    kho = next((d for d in diem if d.get("code") == "KHO-TB"), None) or next(d for d in diem if d.get("owner_type") == "epl")
    tai_xe = next(t for t in tx if t["name"] == "ທ້າວ ບົວພັນ") if any(t["name"] == "ທ້າວ ບົວພັນ" for t in tx) else tx[-1]
    hom_nay = time.strftime("%Y-%m-%d")
    print("✓ đăng nhập · xe thuê %s (chủ xe %s) · xe nhà %s · tài xế %s" % (xe_thue["truck_no"], xe_thue.get("owner_name"), xe_nha["truck_no"], tai_xe["name"]))

    def tien_chuyen():
        s, tt = goi(DX, "/api/bao-cao/tien-tai-xe?thang=%s" % hom_nay[:7], vai="ketoancp")
        r = next((x for x in tt["rows"] if x["driver"] == tai_xe["name"]), None)
        return round((r or {}).get("khoan", {}).get("x_trip", 0))
    tc0 = tien_chuyen()

    def lap(xe_):
        s, p = goi(DX, "/api/trips", {"kind": "giao", "vehicle_id": xe_["id"], "driver_id": tai_xe["id"], "customer_id": kh[0]["id"],
                                      "doc_date": hom_nay, "out_date": hom_nay, "note": "THỬ loại xe",
                                      "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "place_id": kho["id"], "paid_by_epl": True},
                                                   {"section": "travel", "item_key": "x_vn", "qty": 1, "unit_price": 0, "currency": "LAK", "paid_by_epl": True},
                                                   {"section": "travel", "item_key": "x_trip", "qty": 1, "unit_price": 0, "currency": "LAK", "paid_by_epl": True}]},
                     "thabok")
        phai(s, 200, "Bãi lập phiếu xe %s: 100 L dầu kho + sang Việt Nam + tiền chuyến" % xe_["truck_no"], p)
        return p

    # ---------------------------------------------------------------- xe thuê
    print("\n— Xe THUÊ, EPL ứng —")
    p = lap(xe_thue); pid = p["id"]
    dung(p["company"] == "joint", "Phiếu tự thành phiếu xe thuê", p["company"])
    s, pk = goi(DX, "/api/trips/%s" % pid, vai="ketoan")
    dung(pk["hinh_thuc"] == {"tam_ung": "cong_no_chu_xe", "xuat": "xuat_ban"}, "Bản chất: tạm ứng ghi công nợ chủ xe · dầu xuất bán", pk["hinh_thuc"])
    dau = next(e for e in pk["expenses"] if e["section"] == "fuel")
    dung("sale_price" in dau and dau["sale_price"] is None, "Kế toán thấy ô giá bán (còn trống)")
    s, pb = goi(DX, "/api/trips/%s" % pid, vai="thabok")
    dung(all("sale_price" not in e for e in pb["expenses"]), "Bãi không nhận giá bán (tiền bán)")
    for m in ("info", "fuel", "travel"):
        s, g = goi(DX, "/api/trips/%s/sections/%s/send" % (pid, m), {}, "thabok"); phai(s, 200, "Bãi gửi kiểm mục %s" % m, g)
    s, g = goi(DX, "/api/trips/%s/sections/fuel/verify" % pid, {}, "khonl")
    phai(s, 409, "KT kho kiểm mục III khi chưa có giá bán → bị chặn", g)
    dung(g["detail"]["ma"] == "THIEU_GIA_BAN", "Mã chặn THIEU_GIA_BAN", g["detail"]["loi"][:90])
    s, g = goi(DX, "/api/trips/%s" % pid, {"expenses": [{"id": dau["id"], "section": "fuel", "sale_price": GIA_BAN}]}, "khonl", "PUT")
    phai(s, 200, "KT kho gõ giá bán %s LAK/L" % format(GIA_BAN, ","), g)
    dau = next(e for e in g["expenses"] if e["section"] == "fuel")
    dung(dau["sale_price"] == GIA_BAN and dau["unit_price"] != GIA_BAN, "Giá bán lưu riêng, giá vốn vẫn là bình quân kho",
         "bán %s · vốn %s" % (dau["sale_price"], dau["unit_price"]))
    dung(round(g["tinh"]["chi"]["fuel"]) == 100 * GIA_BAN, "Tiền dầu của phiếu xe thuê tính theo giá bán", g["tinh"]["chi"]["fuel"])
    # Bãi lưu lại cả phiếu (không gửi giá) — giá bán KT kho đã gõ phải còn
    s, pb = goi(DX, "/api/trips/%s" % pid, vai="thabok")
    s, g = goi(DX, "/api/trips/%s" % pid, {"expenses": [{k: e[k] for k in ("id", "section", "item_key", "qty", "place_id", "paid_by_epl", "source") if k in e}
                                                        for e in pb["expenses"] if e["section"] == "fuel"]}, "thabok", "PUT")
    phai(s, 200, "Bãi lưu lại mục III (không thấy, không gửi giá)", g)
    s, pk = goi(DX, "/api/trips/%s" % pid, vai="ketoan")
    dung(next(e for e in pk["expenses"] if e["section"] == "fuel")["sale_price"] == GIA_BAN, "Giá bán vẫn còn sau lần Bãi lưu")
    s, g = goi(DX, "/api/trips/%s/sections/fuel/verify" % pid, {}, "khonl"); phai(s, 200, "KT kho kiểm mục III (đã có giá bán)", g)
    s, v = goi(DX, "/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, "thabok")
    phai(s, 200, "Bãi in phiếu đề nghị xuất kho nhiên liệu", v)
    dung(v[0]["hinh_thuc"] == "xuat_ban" and v[0]["owner_name"] == pk["owner_name"], "Tờ đề nghị ghi: xuất bán cho chủ xe", "%s · %s" % (v[0]["hinh_thuc"], v[0]["owner_name"]))
    s, ct = goi(DX, "/api/chung-tu?trip_id=%s" % pid, vai="admin")
    pl = next(c for c in ct["ds"] if c["loai"] == "PLNL")
    dung(pl["payload"].get("hinh_thuc") == "xuat_ban", "Dữ liệu gửi sang kho mang bản chất xuất bán", pl["payload"].get("hinh_thuc"))
    # 30/09: ghi sổ mục III không tự xuất kho — dầu kho phải được cấp theo phiếu đề nghị trước
    s, g = goi(DX, "/api/trips/%s/sections/fuel/book" % pid, {}, "khonl")
    phai(s, 409, "Ghi sổ mục III khi dầu kho chưa cấp theo phiếu đề nghị → bị chặn", g)
    dung(g["detail"]["ma"] == "CHUA_CAP_THEO_DE_NGHI", "Mã chặn CHUA_CAP_THEO_DE_NGHI", g["detail"]["loi"][:80])
    # 01/10 kho tạm chặn cấp quá tồn: nhập trước đúng số lít sẽ cấp ở kho Thà Bốc (kho gốc, "fp_yard"); dòng nhập tự gỡ lúc bài xong (_ke_toan)
    K.nhap_truoc(kho["id"], v[0]["qty_l"], "thử loại xe: nhập trước rồi cấp")
    s, g = goi(DX, "/api/vouchers/%s/cap" % v[0]["id"], {"qty": v[0]["qty_l"]}, "khonl"); phai(s, 200, "Cấp dầu theo phiếu đề nghị", g)
    s, g = goi(DX, "/api/trips/%s/sections/fuel/book" % pid, {}, "khonl"); phai(s, 200, "Ghi sổ mục III (dầu đã cấp theo đề nghị)", g)
    GIA_IV = {"x_vn": 430000, "x_trip": 1800000}
    s, g = goi(DX, "/api/trips/%s" % pid, {"expenses": [{"id": e["id"], "section": "travel", "unit_price": GIA_IV[e["item_key"]], "currency": "LAK"}
                                                        for e in pk["expenses"] if e["section"] == "travel"]}, "ketoancp", "PUT")
    phai(s, 200, "KT chi phí nhập giá mục IV (sang VN 430.000 · tiền chuyến 1.800.000)", g)
    tc = next(e for e in g["expenses"] if e["item_key"] == "x_trip")
    dung(tc["cach_tra"] == "tien_mat" and tc["tien_mat_tx"], "Xe thuê: tiền chuyến EPL ứng là tiền mặt khi xe đi (không có trả cùng lương)", tc["cach_tra"])
    for hd in ("verify", "book"):
        s, g = goi(DX, "/api/trips/%s/sections/travel/%s" % (pid, hd), {}, "ketoancp"); phai(s, 200, "Mục IV %s" % hd, g)
    s, v = goi(DX, "/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "thabok")
    phai(s, 200, "Bãi in phiếu đề nghị tạm ứng", v)
    dung(v[0]["hinh_thuc"] == "cong_no_chu_xe", "Tờ đề nghị tạm ứng ghi: ghi công nợ chủ xe", v[0]["hinh_thuc"])
    s, vk = goi(DX, "/api/trips/%s/vouchers" % pid, vai="ketoancp")
    tu = next(x for x in vk if x["kind"] == "advance")
    dung(round(tu["amount_lak"]) == 430000 + 1800000, "Đề nghị tạm ứng xe thuê gồm cả tiền chuyến EPL ứng", tu["amount_lak"])
    s, pc = goi(DX, "/api/trips/%s/phieu-chi" % pid, vai="ketoancp")
    dung(pc["hinh_thuc"] == "cong_no_chu_xe", "Bản in đề nghị tạm ứng mang bản chất", pc["hinh_thuc"])
    s, g = goi(DX, "/api/trips/%s" % pid, vai="ketoan")
    t = g["tinh"]
    mong = round((100 * GIA_BAN + 430000 + 1800000) / (g["rate_usd"] if (t.get("hire_ccy") or "USD") == "USD" else 1), 2)
    dung(abs((t.get("ung_truoc") or 0) - mong) < 0.02, "Tiền EPL ứng trừ chủ xe = dầu theo giá bán + tạm ứng", "%s (mong %s)" % (t.get("ung_truoc"), mong))

    # ---------------------------------------------------------------- xe nhà
    print("\n— Xe NHÀ —")
    q = lap(xe_nha); qid = q["id"]
    s, qk = goi(DX, "/api/trips/%s" % qid, vai="ketoan")
    dung(qk["hinh_thuc"] == {"tam_ung": "noi_bo", "xuat": "noi_bo"}, "Bản chất: tạm ứng nội bộ · xuất nội bộ", qk["hinh_thuc"])
    dau2 = next(e for e in qk["expenses"] if e["section"] == "fuel")
    s, g = goi(DX, "/api/trips/%s" % qid, {"expenses": [{"id": dau2["id"], "section": "fuel", "item_key": "diesel", "qty": 100,
                                                         "place_id": kho["id"], "paid_by_epl": True, "sale_price": 99999}]}, "admin", "PUT")
    phai(s, 200, "Admin gửi giá bán cho phiếu xe nhà", g)
    dung(next(e for e in g["expenses"] if e["section"] == "fuel")["sale_price"] is None, "Xe nhà: giá bán bị bỏ — xuất nội bộ theo giá vốn")
    s, g = goi(DX, "/api/trips/%s" % qid, {"expenses": [{"id": e["id"], "section": "travel", "unit_price": {"x_vn": 430000, "x_trip": 1800000}[e["item_key"]],
                                                         "currency": "LAK"} for e in qk["expenses"] if e["section"] == "travel"]}, "ketoancp", "PUT")
    phai(s, 200, "KT chi phí nhập giá mục IV phiếu xe nhà", g)
    dung(next(e for e in g["expenses"] if e["item_key"] == "x_trip")["cach_tra"] == "luong", "Xe nhà: tiền chuyến vẫn trả cùng lương")
    tc1 = tien_chuyen()
    dung(tc1 - tc0 == 1800000, "Màn Tiền chuyến & tiền nước chỉ cộng tiền chuyến xe NHÀ (xe thuê không vào)", "%s → %s" % (tc0, tc1))

    # ---------------------------------------------------------------- tất toán
    print("\n— Tất toán tài xế (chốt ở trang điều xe, tiền ở hệ kế toán anh Tune) —")
    s, tt = goi(DX, "/api/tat-toan/%s?ky=%s" % (tai_xe["id"], hom_nay[:7]), vai="ketoancp")
    phai(s, 200, "Mở tất toán của tài xế %s" % tai_xe["name"], tt)
    so = json.dumps(tt, ensure_ascii=False)
    dung(q["doc_no"] in so, "Có phiếu xe nhà %s" % q["doc_no"])
    dung(p["doc_no"] not in so, "Không có phiếu xe thuê %s (tạm ứng xe thuê là công nợ chủ xe)" % p["doc_no"])
    s_xoa, _ = goi(DX, "/api/trips/%s" % qid, vai="admin", method="DELETE")
    # 01/10: ghi sổ mục IV phiếu xe thuê đã sinh phiếu chi tạm ứng "chờ chi" bên hệ anh Tune — phiếu xe thuê ở lại DB thử thì
    # Sếp chi tay mục IV để máy RÚT phiếu chi đó (không để phiếu thử chờ thủ quỹ bên kế toán)
    s, g = goi(DX, "/api/trips/%s/sections/travel/pay" % pid, {}, "admin"); phai(s, 200, "Sếp chi tay mục IV phiếu xe thuê (rút phiếu chi chờ bên kế toán)", g)
    s, ck = goi(DX, "/api/trips/%s/chi-ke-toan" % pid, vai="ketoancp")
    dung(s == 200 and (ck or {}).get("status") != "da_gui", "Không còn phiếu chi tạm ứng chờ bên kế toán cho phiếu xe thuê thử", (ck or {}).get("status"))
    # 01/10: xoá cả phiếu xe thuê thử — dầu đã cấp về kho, rồi dòng nhập thử tự gỡ (_ke_toan); không để phiếu thử rút kho mỗi lần chạy
    goi(DX, "/api/trips/%s/mo-khoa" % pid, {}, "admin")
    s_xoa2, _ = goi(DX, "/api/trips/%s" % pid, vai="admin", method="DELETE")
    print("  · phiếu xe nhà thử %s; phiếu xe thuê thử %s" % ("đã xoá" if s_xoa == 200 else "ở lại", "đã xoá (dầu về kho)" if s_xoa2 == 200 else "ở lại (%s)" % s_xoa2))
    print("\nTHỬ LOẠI XE: ĐẠT — xe nhà nội bộ · xe thuê ghi công nợ + xuất bán theo giá bán · tất toán, tiền chuyến chỉ xe nhà · dầu kho chỉ rời kho theo phiếu đề nghị đã cấp")


if __name__ == "__main__":
    main()
