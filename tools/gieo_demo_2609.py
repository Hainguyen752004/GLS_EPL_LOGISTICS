# -*- coding: utf-8 -*-
"""Gieo BỘ DỮ LIỆU MẪU tháng 9/2026 — đi qua API như người thật, mỗi bước đúng vai trong bảng Nhiệm Vụ.

    python tools/gieo_demo_2609.py [http://127.0.0.1:8011]

Không xoá gì, không gieo lại DB (DB dùng chung). Mỗi chứng từ, tồn kho, giá bình quân sinh ra đúng luật của máy
chủ. Để người mới vào xem được TỪNG MODULE có số liệu thật:

  Kho      nhập dầu kho Viêng Chăn · mua dầu Việt Nam vào kho xe · chuyển kho · nhập phụ tùng (giá bình quân)
  Phiếu A  xe nhà, đi trọn luồng: 6 mục duyệt → xe về → khoá → hoá đơn → thu đủ
  Phiếu B  xe liên kết: EPL ứng dầu kho, một khoản chủ xe tự trả → khoá → hoá đơn → thu; chủ xe mua dầu ở quầy
           → đợt trả chủ xe TỰ TRỪ (deal − hàng mua = thực trả)
  Phiếu C  xe nhà lấy 600 lít ở kho xe (dầu mua VN), đang trên đường; 400 lít dư chuyển về kho hiện trường
  Phiếu D  DO GOM mỏ → bãi (xe 342) đã về, hàng vào kho bãi
  Phiếu E  DO GIAO bãi → cảng (xe 341) lấy 25 t từ lô của D — Bãi vừa lập, CHỜ KẾ TOÁN NHẬP GIÁ
  Bán hàng khách mua lọc dầu + dầu, đã thu · Lệnh sửa bảo dưỡng định kỳ xe 342 · đẩy chứng từ sang sổ
"""
import json
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
TK = {}


def goi(duong, body=None, vai="admin", method=None):
    r = urllib.request.Request(GOC + duong, data=json.dumps(body).encode("utf-8") if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"),
                               headers={"Content-Type": "application/json", "Authorization": "Bearer " + TK.get(vai, "")})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def ok(duong, body=None, vai="admin", method=None, buoc=""):
    s, g = goi(duong, body, vai, method)
    if s != 200:
        raise SystemExit("DỪNG ở «%s» (%s): %s %s" % (buoc or duong, vai, s, json.dumps(g, ensure_ascii=False)[:400]))
    return g


def bao(chu):
    print("  ✓ " + chu)


def dong_muc(pid, muc):
    """Gửi → kiểm → ghi sổ → chi một mục chi, mỗi bước đúng vai."""
    nguoi = {"fuel": ("thabok", "khonl", "khonl", "quyvc"), "travel": ("thabok", "ketoancp", "ketoancp", "quytb"),
             "other": ("thabok", "ketoancp", "ketoancp", "quytb"), "repair": ("totsua", "ketoancp", "ketoancp", "quytb")}[muc]
    for hd, v in zip(("send", "verify", "book", "pay"), nguoi):
        ok("/api/trips/%s/sections/%s/%s" % (pid, muc, hd), {}, v, buoc="%s %s" % (muc, hd))


def nhap_gia(pid, gia):
    """Người KIỂM mục nhập đơn giá cho dòng Bãi đã khai (Bãi không nhập giá — anh Khampla A2)."""
    p = ok("/api/trips/%s" % pid, vai="admin")
    for m, vai in (("fuel", "khonl"), ("travel", "ketoancp"), ("other", "ketoancp")):
        dong = [{"id": e["id"], "section": m, "unit_price": gia[e["item_key"]][0], "currency": gia[e["item_key"]][1]}
                for e in p["expenses"] if e["section"] == m and e.get("item_key") in gia and e.get("source") != "kho"]
        if dong:
            ok("/api/trips/%s" % pid, {"expenses": dong}, vai, "PUT", buoc="nhập giá %s" % m)


def da_gieo(ma):
    return any((p.get("note") or "") == ma for p in ok("/api/trips", vai="admin"))


def main():
    for u in ("admin", "thabok", "ketoan", "ketoancp", "khonl", "khopt", "totsua", "quyvc", "quytb", "doanhthu"):
        TK[u] = ok("/api/dang-nhap", {"username": u, "password": "1234"}, buoc="đăng nhập " + u)["token"]
    xe = {v["truck_no"]: v for v in ok("/api/vehicles", vai="admin")}
    tx = {d["name"]: d for d in ok("/api/drivers", vai="admin")}
    kh = {c["name"]: c for c in ok("/api/customers", vai="admin")}
    tuyen = ok("/api/routes", vai="admin")
    ncc = {s["name"]: s for s in ok("/api/suppliers", vai="admin")}
    kho = {k["code"]: k for k in ok("/api/fuel-places?tat_ca=1", vai="admin")}
    pt = {p["name"]: p for p in ok("/api/parts", vai="admin")}
    chu = next(o for o in ok("/api/owners", vai="admin") if o["active"])
    X342, X341, XLK = xe["342"], xe["341"], next(v for v in xe.values() if v["owner_type"] == "joint")
    TX = list(tx.values())
    VANNA, KHAMTUI, LAOCHIN = kh["ນາງ ວັນນາ"], kh["ຄຳຕຸ້ຍ"], kh["ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ"]
    R1, R2 = tuyen[0], tuyen[1]
    SIPHING_LA = next(s for n, s in ncc.items() if "ລາວ" in n)
    TRAM_VN = next(s for n, s in ncc.items() if "Việt Nam" in n)
    YANG = next(s for n, s in ncc.items() if "ຢາງ" in n)
    lop = next(p for n, p in pt.items() if "lốp" in n); loc = next(p for n, p in pt.items() if "lọc dầu" in n)

    print("KHO")
    da_co = any(r["doc_no"] == "PO-2609-01" for r in ok("/api/fuel-moves", vai="khonl")["rows"])
    if da_co:
        print("  · kho đã gieo ở lượt trước — bỏ qua")
    else:
        gieo_kho(kho, SIPHING_LA, TRAM_VN, lop, loc)


    # ------------------------------------------------------------ phiếu A: xe nhà, trọn luồng
    if da_gieo("MAU-A"):
        print("  · phiếu A đã gieo — bỏ qua")
    else:
        print("PHIẾU A — xe nhà, trọn luồng tới thu tiền")
        A = ok("/api/trips", {"company": "EPL", "vehicle_id": X342["id"], "driver_id": TX[2]["id"], "customer_id": VANNA["id"], "route_id": R1["id"],
                              "doc_date": "2026-09-18", "out_date": "2026-09-18", "odo_out": 152300, "note": "MAU-A", "weight_origin": 41.2,
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 180, "place_id": kho["KHO-TB"]["id"]},
                                           {"section": "fuel", "item_key": "diesel", "qty": 650, "place_id": kho["VN-01"]["id"], "ghi_no": True},
                                           {"section": "travel", "item_key": "x_food", "qty": 3},
                                           {"section": "travel", "item_key": "x_water", "qty": 2}]}, "thabok", buoc="Bãi lập phiếu A")
        nhap_gia(A["id"], {"diesel": (27500, "VND"), "x_food": (120000, "LAK"), "x_water": (60000, "LAK")})
        bao("%s · Bãi lập (số lượng) → KT kho / KT Chi phí nhập giá" % A["doc_no"])
        ok("/api/trips/%s" % A["id"], {"ore_bill_no": "HR-2609-118", "ore_bill_date": "2026-09-18"}, "ketoan", "PUT")   # kế toán nhập khi nhận giấy (C3.7)
        for m in ("info", "trans"):
            ok("/api/trips/%s/sections/%s/send" % (A["id"], m), {}, "thabok"); ok("/api/trips/%s/sections/%s/verify" % (A["id"], m), {}, "ketoan")
        dong_muc(A["id"], "fuel"); dong_muc(A["id"], "travel")
        ok("/api/trips/%s/transport-status" % A["id"], {"status": "transit"}, "thabok")
        ok("/api/trips/%s/transport-status" % A["id"], {"status": "arrived", "weight_dest": 40.9, "odo_back": 153290, "back_date": "2026-09-20"}, "thabok")
        ok("/api/trips/%s/khoa" % A["id"], {"xac_nhan": True}, "ketoan")
        ok("/api/trips/%s/invoice" % A["id"], {}, "doanhthu")
        k = ok("/api/trips/%s" % A["id"], vai="doanhthu")["tinh"]
        ok("/api/trips/%s/thu-tien" % A["id"], {"amount": k["doanh_thu"], "currency": k["ccy"], "method": "bank", "pay_date": "2026-09-22",
                                                "ref": "BCEL-2209-331"}, "doanhthu")
        bao("duyệt 4 mục → xe về 40,9 t → khoá → hoá đơn → thu đủ %s %s" % (k["doanh_thu"], k["ccy"]))

    # ------------------------------------------------------------ phiếu B: xe liên kết + chủ xe mua ở quầy
    if da_gieo("MAU-B"):
        print("  · phiếu B đã gieo — bỏ qua")
    else:
        print("PHIẾU B — xe liên kết, chủ xe mua dầu ở quầy bị trừ khi trả")
        B = ok("/api/trips", {"company": "joint", "vehicle_id": XLK["id"], "driver_id": TX[1]["id"], "customer_id": KHAMTUI["id"], "route_id": R1["id"],
                              "doc_date": "2026-09-19", "out_date": "2026-09-19", "odo_out": 88100, "note": "MAU-B", "weight_origin": 42.0,
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 150, "place_id": kho["KHO-TB"]["id"], "paid_by_epl": True},
                                           {"section": "travel", "item_key": "x_food", "qty": 2, "paid_by_epl": False}]}, "thabok", buoc="Bãi lập phiếu B")
        ok("/api/trips/%s" % B["id"], {"hire_price": 38.5, "hire_ccy": "USD"}, "ketoan", "PUT")
        nhap_gia(B["id"], {"x_food": (100000, "LAK")})
        ok("/api/trips/%s" % B["id"], {"ore_bill_no": "HR-2609-124", "ore_bill_date": "2026-09-19"}, "ketoan", "PUT")   # kế toán nhập khi nhận giấy (C3.7)
        for m in ("info", "trans"):
            ok("/api/trips/%s/sections/%s/send" % (B["id"], m), {}, "thabok"); ok("/api/trips/%s/sections/%s/verify" % (B["id"], m), {}, "ketoan")
        dong_muc(B["id"], "fuel"); dong_muc(B["id"], "travel")
        ok("/api/trips/%s/transport-status" % B["id"], {"status": "transit"}, "thabok")
        ok("/api/trips/%s/transport-status" % B["id"], {"status": "arrived", "weight_dest": 41.8, "odo_back": 89080, "back_date": "2026-09-21"}, "thabok")
        ok("/api/trips/%s/khoa" % B["id"], {"xac_nhan": True}, "ketoan")
        ok("/api/trips/%s/invoice" % B["id"], {}, "doanhthu")
        kb = ok("/api/trips/%s" % B["id"], vai="doanhthu")["tinh"]
        ok("/api/trips/%s/thu-tien" % B["id"], {"amount": kb["doanh_thu"], "currency": kb["ccy"], "method": "cash", "pay_date": "2026-09-22"}, "doanhthu")
        ban = ok("/api/ban-hang", {"sale_date": "2026-09-21", "owner_id": chu["id"], "currency": "LAK", "note": "Chủ xe đổ thêm dầu ở bãi",
                                   "lines": [{"item_type": "fuel", "place_id": kho["KHO-TB"]["id"], "qty": 20, "unit_price": 31000}]}, "ketoan")
        tra = ok("/api/owners/%s/tra" % chu["id"], {"trip_ids": [B["id"]], "pay_date": "2026-09-23", "method": "cash"}, "quytb")
        dot = tra["da_tra"][0]
        bao("%s · tiền thuê %s USD · chủ xe mua 20 L ở quầy (%s) → thực trả %s − %s = %s USD"
            % (B["doc_no"], kb["tien_thue"], ban["doc_no"], dot["gross"], dot["sales_deducted"], dot["amount"]))

    # ------------------------------------------------------------ phiếu C: dầu kho xe, đang trên đường
    if da_gieo("MAU-C"):
        print("  · phiếu C đã gieo — bỏ qua")
    else:
        print("PHIẾU C — lấy 600 L ở kho xe (dầu mua VN), đang chạy")
        C = ok("/api/trips", {"company": "EPL", "vehicle_id": X341["id"], "driver_id": TX[0]["id"], "customer_id": LAOCHIN["id"], "route_id": R2["id"],
                              "doc_date": "2026-09-22", "out_date": "2026-09-22", "odo_out": 201450, "note": "MAU-C", "weight_origin": 40.6,
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 600, "place_id": kho["KHO-XE-VN"]["id"]},
                                           {"section": "travel", "item_key": "x_food", "qty": 3}]}, "thabok", buoc="Bãi lập phiếu C")
        nhap_gia(C["id"], {"x_food": (120000, "LAK")})
        for m in ("info", "trans"):
            ok("/api/trips/%s/sections/%s/send" % (C["id"], m), {}, "thabok"); ok("/api/trips/%s/sections/%s/verify" % (C["id"], m), {}, "ketoan")
        dong_muc(C["id"], "fuel"); dong_muc(C["id"], "travel")
        ok("/api/trips/%s/transport-status" % C["id"], {"status": "transit"}, "thabok")
        ok("/api/fuel-transfers", {"from_place_id": kho["KHO-XE-VN"]["id"], "to_place_id": kho["KHO-TB-HL"]["id"], "move_date": "2026-09-22",
                                   "qty_l": 400, "note": "Dầu mua VN còn dư sau khi cấp phiếu %s" % C["doc_no"]}, "khonl")
        bao("%s · 600 L từ kho xe · đang trên đường · 400 L dư chuyển về bãi Huay Loek" % C["doc_no"])

    # ------------------------------------------------------------ phiếu D (gom) → E (giao) tách chặng
    if da_gieo("MAU-D"):
        print("  · phiếu D (gom) → E (giao) tách chặng đã gieo — bỏ qua")
    else:
        print("PHIẾU D/E — tách chặng: gom mỏ → bãi, giao bãi → cảng bằng xe khác")
        D = ok("/api/trips", {"kind": "gom", "company": "EPL", "vehicle_id": X342["id"], "driver_id": TX[2]["id"], "customer_id": KHAMTUI["id"],
                              "doc_date": "2026-09-21", "out_date": "2026-09-21", "odo_out": 153300, "note": "MAU-D", "weight_origin": 39.5,
                              "origin": "ກາສີ (ບ່ອນຂຸດແຮ່)", "destination": "ທ່າບົກ (ສະໜາມ EPL)",
                              "goods": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 39.5}],
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 90, "place_id": kho["KHO-TB"]["id"]},
                                           {"section": "travel", "item_key": "x_food", "qty": 1}]}, "thabok", buoc="Bãi lập DO gom D")
        nhap_gia(D["id"], {"x_food": (120000, "LAK")})
        for m in ("info", "trans"):
            ok("/api/trips/%s/sections/%s/send" % (D["id"], m), {}, "thabok"); ok("/api/trips/%s/sections/%s/verify" % (D["id"], m), {}, "ketoan")
        dong_muc(D["id"], "fuel"); dong_muc(D["id"], "travel")
        ok("/api/trips/%s/transport-status" % D["id"], {"status": "transit"}, "thabok")
        ok("/api/trips/%s/transport-status" % D["id"], {"status": "arrived", "weight_dest": 39.3, "odo_back": 153520, "back_date": "2026-09-21"}, "thabok")
        lo = next(x for x in ok("/api/kho-hang/lo", vai="thabok") if x["lo_trip_id"] == D["id"])
        E = ok("/api/trips", {"kind": "giao", "company": "EPL", "vehicle_id": X341["id"], "driver_id": TX[1]["id"], "customer_id": KHAMTUI["id"],
                              "route_id": R2["id"], "doc_date": "2026-09-23", "out_date": "2026-09-23", "odo_out": 202400, "note": "MAU-E",
                              "goods": [{"goods_name": lo["goods_name"], "qty_t": 25, "tu_phieu_id": D["id"]}],
                              "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 160, "place_id": kho["KHO-TB"]["id"]},
                                           {"section": "fuel", "item_key": "diesel", "qty": 500, "place_id": kho["VN-01"]["id"], "ghi_no": True},
                                           {"section": "travel", "item_key": "x_food", "qty": 3},
                                           {"section": "travel", "item_key": "x_water", "qty": 2}]}, "thabok", buoc="Bãi lập DO giao E")
        for m in ("info", "trans", "fuel", "travel"):
            ok("/api/trips/%s/sections/%s/send" % (E["id"], m), {}, "thabok")
        bao("%s gom 39,5 t → bãi nhận 39,3 t · %s giao 25 t từ lô đó — Bãi đã gửi kiểm, CHỜ KT nhập giá" % (D["doc_no"], E["doc_no"]))

    # ------------------------------------------------------------ bán hàng · sửa chữa · đẩy sổ
    print("BÁN HÀNG · SỬA CHỮA · SỔ")
    bh = ok("/api/ban-hang", {"sale_date": "2026-09-22", "customer_id": KHAMTUI["id"], "currency": "LAK", "note": "Khách mua ở quầy bãi Thà Bốc",
                              "lines": [{"item_type": "part", "part_id": loc["id"], "qty": 2, "unit_price": 230000},
                                        {"item_type": "fuel", "place_id": kho["KHO-TB"]["id"], "qty": 40, "unit_price": 31500}]}, "ketoan")
    ok("/api/ban-hang/%s/thu" % bh["id"], {"pay_date": "2026-09-22"}, "quytb")
    bao("%s · 2 lọc dầu + 40 L dầu · đã thu tiền mặt (PXK_BAN Nợ 607 · HD_BAN · PT_BAN)" % bh["doc_no"])
    lsc = ok("/api/lenh-sua-chua", {"vehicle_id": X342["id"], "kind": "bao_duong", "order_date": "2026-09-23", "odo_km": 153520,
                                    "note": "Bảo dưỡng 10.000 km: thay lọc dầu, kiểm phanh",
                                    "lines": [{"source": "kho", "part_id": loc["id"], "qty": 1, "item_name": loc["name"]},
                                              {"source": "mua", "item_name": "Công thợ bảo dưỡng", "qty": 1, "unit_price": 350000, "currency": "LAK",
                                               "supplier_id": YANG["id"]}]}, "totsua")
    ok("/api/lenh-sua-chua/%s/verify" % lsc["id"], {}, "ketoancp")
    bao("%s · xe 342 bảo dưỡng · lọc dầu lấy kho (PXK_PT) + công thợ · KT Chi phí đã kiểm, chờ ghi sổ" % lsc["doc_no"])
    d = ok("/api/chung-tu/day", {}, "ketoan")
    bao("đẩy chứng từ sang sổ kế toán: %d tờ, %d lỗi" % (d["xong"], d["loi"]))
    print("\nXONG — bộ mẫu tháng 9: 5 phiếu mới ở 5 trạng thái khác nhau, kho, bán hàng, chủ xe, sửa chữa, sổ.")


def gieo_kho(kho, SIPHING_LA, TRAM_VN, lop, loc):
    ok("/api/fuel-moves", {"kind": "in", "place_id": kho["KHO-VC"]["id"], "move_date": "2026-09-18", "qty_l": 3000, "unit_price": 29500,
                           "currency": "LAK", "supplier_id": SIPHING_LA["id"], "doc_no": "PO-2609-01", "note": "Nhập dầu kho Viêng Chăn"}, "khonl")
    bao("KT kho xăng dầu nhập 3.000 L vào kho Viêng Chăn · 29.500 LAK/L (PNK_NL)")
    ok("/api/fuel-moves", {"kind": "in", "place_id": kho["KHO-XE-VN"]["id"], "move_date": "2026-09-21", "qty_l": 1000, "unit_price": 26500,
                           "currency": "VND", "rate_to_lak": 1.2, "supplier_id": TRAM_VN["id"], "doc_no": "PO-VN-2609-01",
                           "note": "Mua dầu ở Việt Nam, nhận vào kho xe"}, "khonl")
    bao("Mua 1.000 L ở Việt Nam vào KHO XE · 26.500 VND × 1,2 (PNK_NL, Có 4021 trạm VN)")
    ok("/api/fuel-transfers", {"from_place_id": kho["KHO-TB"]["id"], "to_place_id": kho["KHO-TK"]["id"], "move_date": "2026-09-20",
                               "qty_l": 500, "note": "Cấp dầu cho bãi Thà Khẹc"}, "khonl")
    bao("Chuyển 500 L Thà Bốc → bãi Thà Khẹc (CK_NL)")
    ok("/api/parts/%s/moves" % lop["id"], {"kind": "in", "qty": 4, "unit_price": 3300000, "move_date": "2026-09-18", "note": "Nhập 4 lốp · ຮ້ານຢາງ"}, "khopt")
    ok("/api/parts/%s/moves" % loc["id"], {"kind": "in", "qty": 10, "unit_price": 175000, "move_date": "2026-09-18", "note": "Nhập 10 lọc dầu"}, "khopt")
    bao("Thủ kho phụ tùng nhập 4 lốp · 10 lọc dầu (giá bình quân tính lại, PNK_PT)")


if __name__ == "__main__":
    main()
