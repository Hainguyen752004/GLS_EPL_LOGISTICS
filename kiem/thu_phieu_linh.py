# -*- coding: utf-8 -*-
"""Thử luồng phiếu lĩnh — máy chủ thật, không phải bộ kiểm đơn vị.

    python kiem/thu_phieu_linh.py [http://127.0.0.1:8010]

Đi đúng đường một tờ phiếu lĩnh đi qua: Bãi lập → in mã QR → thủ kho quét, đối chiếu, cấp dầu →
dòng chi mang số phiếu xuất kho. Kèm các chỗ PHẢI bị từ chối: thủ kho kho khác, cấp lệch số lít mà
không ghi lý do, cấp hai lần, tài xế tự chi tiền cho mình, chi khi mục IV chưa ghi sổ. Cuối cùng là
tài xế khai đổ dầu dọc đường và bảng tất toán theo tháng (ở trang kế toán từ 28/09, đợt 7c).

Cần dữ liệu mẫu còn nguyên: python backend/app/seed.py --dung-lai
"""
import json
import os
import sys
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — kho nhiên liệu ở trang kế toán (28/09)



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
    _, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
    return g["token"]


def bao(nhan, ma, mong=200, chi_tiet=""):
    dau = "OK " if ma == mong else "SAI"
    print("  %s %-52s %s%s" % (dau, nhan, ma, (" · " + chi_tiet) if chi_tiet else ""))
    if ma != mong:
        raise SystemExit("DUNG: %s tra %s, mong %s" % (nhan, ma, mong))


tk = {u: vao(u) for u in ("admin", "thabok", "ketoan", "ketoancp", "khonl", "khotb", "khovc", "quytb", "tx01")}
print("Đăng nhập %d vai OK" % len(tk))

_, ds = goi("/api/trips", tk=tk["admin"])
# Bộ kiểm LUÔN tự lập phiếu thử của mình — không bao giờ lấy phiếu mẫu (rà giao diện 23/09: bộ kiểm cũ chọn phiếu
# mẫu còn dầu kho chưa xuất rồi cấp dầu lên đó, dầu của phiếu mẫu bị tính xuất hai lần, dữ liệu demo bẩn dần mỗi lần chạy).
p = None
if p is None:
    # Không còn phiếu mẫu nào chưa xuất dầu: KHÔNG gieo lại (DB dùng chung với máy chủ của chủ dự án) —
    # Bãi lập một phiếu thử của tài xế tx01: 60 lít lĩnh ở kho Thà Bốc + tiền ăn đi đường.
    import time
    _, dang = goi("/api/dang-nhap", {"username": "tx01", "password": "1234"})
    _, xe = goi("/api/vehicles", tk=tk["thabok"]); _, kh = goi("/api/customers", tk=tk["thabok"])
    _, dd0 = goi("/api/fuel-places", tk=tk["thabok"])
    tb = next(x for x in dd0 if x.get("code") == "KHO-TB")
    nha = next(x for x in xe if x["owner_type"] != "joint" and x.get("status") != "on_trip") if any(x["owner_type"] != "joint" and x.get("status") != "on_trip" for x in xe) else next(x for x in xe if x["owner_type"] != "joint")
    ma, p = goi("/api/trips", {"doc_no": "THU-PL-%s/EPL" % time.strftime("%d%H%M%S"), "company": "EPL", "vehicle_id": nha["id"],
                               "driver_id": dang["user"]["driver_id"], "customer_id": kh[0]["id"], "weight_origin": 40, "odo_out": 1000,
                               "doc_date": time.strftime("%Y-%m-%d"), "out_date": time.strftime("%Y-%m-%d"),
                               "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 60, "place_id": tb["id"], "paid_by_epl": True},
                                            {"section": "travel", "item_key": "x_food", "qty": 2, "paid_by_epl": True}]}, tk["thabok"])
    bao("Bãi lập phiếu thử (không có phiếu mẫu chưa xuất dầu)", ma, 200, p.get("doc_no", ""))
    _, ctk = goi("/api/trips/" + p["id"], tk=tk["admin"])
    d_an = [{"id": d["id"], "section": "travel", "unit_price": 100000, "currency": "LAK"} for d in ctk["expenses"] if d["section"] == "travel"]
    ma, r = goi("/api/trips/" + p["id"], {"expenses": d_an}, tk["ketoancp"], "PUT")
    bao("KT Chi phí nhập đơn giá tiền ăn", ma, 200)
print("Phiếu thử: %s · %s · %s" % (p["doc_no"], p["truck_no"], p["driver_name"]))

# 1. lập phiếu lĩnh nhiên liệu
ma, v = goi("/api/trips/%s/vouchers" % p["id"], {"kind": "fuel"}, tk["thabok"])
bao("Bãi lập phiếu lĩnh nhiên liệu", ma, 200, "%d tờ" % (len(v) if isinstance(v, list) else 0))
pl = v[0]
print("      kho: %s · %s lít · mã QR: %s" % (pl["place_name"][:30], pl["qty_l"], pl["token"]))

# 2. ảnh QR (nhị phân — đọc thẳng, không qua json)
import urllib.request as _u
with _u.urlopen(GOC + pl["qr"], timeout=20) as o:
    anh = o.read()
assert anh[1:4] == bytes([80, 78, 71]), "anh QR khong phai PNG"
print("  OK  ảnh QR là PNG, %d byte" % len(anh))

# 3. tra cứu bằng token — đúng thứ người cấp cần đối chiếu
ma, t = goi("/api/vouchers/tra-cuu/" + pl["token"], tk=tk["khotb"])
bao("Thủ kho quét QR tra cứu", ma, 200, "xe %s · %d dòng dầu" % (t["phieu"]["truck_no"], len(t["dong"])))

# 3b. thủ kho chỉ thấy phiếu của kho mình
_, a = goi("/api/vouchers?trang_thai=cho", tk=tk["khotb"])
_, b = goi("/api/vouchers?trang_thai=cho", tk=tk["khovc"])
assert any(x["id"] == pl["id"] for x in a), "thủ kho Thà Bốc phải thấy phiếu của kho mình"
assert not any(x["id"] == pl["id"] for x in b), "thủ kho Viêng Chăn KHÔNG được thấy phiếu kho khác"
print("  OK  thủ kho TB thấy %d phiếu chờ · thủ kho VC thấy %d (lọc theo kho đúng)" % (len(a), len(b)))

# 4. thủ kho kho KHÁC không cấp được
ma, r = goi("/api/vouchers/%s/cap" % pl["id"], {"qty": pl["qty_l"]}, tk["khovc"])
bao("Thủ kho kho khác cấp → bị từ chối", ma, 403, (r or {}).get("detail", {}).get("ma", ""))

# 5. cấp lệch số lít mà không ghi lý do → từ chối
ma, r = goi("/api/vouchers/%s/cap" % pl["id"], {"qty": (pl["qty_l"] or 0) + 20}, tk["khotb"])
bao("Cấp lệch số lít, không ghi lý do → từ chối", ma, 422, (r or {}).get("detail", {}).get("ma", ""))

# 6. cấp đúng
ma, r = goi("/api/vouchers/%s/cap" % pl["id"], {"qty": pl["qty_l"]}, tk["khotb"])
bao("Thủ kho đúng kho cấp dầu", ma, 200, "trạng thái %s" % r["status"])

# 7. cấp lần hai → từ chối
ma, r = goi("/api/vouchers/%s/cap" % pl["id"], {"qty": 1}, tk["khotb"])
bao("Cấp lần hai → từ chối", ma, 409, (r or {}).get("detail", {}).get("ma", ""))

# 8. dòng chi đã mang số phiếu xuất kho, và GIÁ BÌNH QUÂN của kho lúc cấp (anh Khampla C5.3)
_, ct = goi("/api/trips/" + p["id"], tk=tk["admin"])
dong_kho = [d for d in ct["expenses"] if d["section"] == "fuel" and d["source"] == "kho"]
print("  OK  dòng dầu kho đã gắn phiếu xuất kho: %s" % all(d["stock_move_id"] for d in dong_kho))
_, so_kho = K.kt("/api/nhien-lieu", vai="khonl")                    # sổ dầu ở trang kế toán (28/09)
mv = next(r for r in so_kho["rows"] if r["id"] == dong_kho[0]["stock_move_id"])
assert mv["unit_cost_lak"] and all(abs(d["unit_price"] - mv["unit_cost_lak"]) < 0.01 and d["currency"] == "LAK" for d in dong_kho), (mv, dong_kho)
print("  OK  dòng dầu mang giá bình quân kho lúc cấp: %s LAK/L" % format(round(mv["unit_cost_lak"]), ","))

# 9. phiếu tạm ứng
ma, v2 = goi("/api/trips/%s/vouchers" % p["id"], {"kind": "advance"}, tk["thabok"])
assert v2[0]["amount_lak"] is None, "Bãi lập phiếu tạm ứng nhưng không nhận số tiền (anh Khampla A2)"
_, v2k = goi("/api/trips/%s/vouchers" % p["id"], tk=tk["ketoan"])
bao("Bãi lập phiếu tạm ứng đi đường (Bãi không thấy số tiền)", ma, 200, "%s · %s LAK (kế toán thấy)" % (v2[0]["doc_no"], round(next(v for v in v2k if v["kind"] == "advance")["amount_lak"])))
ptu = v2[0]

# 10-11. hai chỗ phải chặn quanh phiếu tạm ứng — chỉ thử khi phiếu còn ĐANG CHỜ cấp
if ptu["status"] != "cho":
    print("  --  phiếu tạm ứng đã cấp sẵn (%s), bỏ qua hai bước chặn" % ptu["status"])
else:
    ma, r = goi("/api/vouchers/%s/cap" % ptu["id"], {}, tk["tx01"])
    bao("Tài xế tự chi tạm ứng → từ chối", ma, 403, (r or {}).get("detail", {}).get("ma", ""))
    tt = ct["sections"].get("travel")
    ma, r = goi("/api/vouchers/%s/cap" % ptu["id"], {}, tk["quytb"])
    # từ 01/10 tạm ứng chi ở hệ kế toán: quỹ quét QR trên trang điều xe bị chặn ở mọi bước
    bao("Quỹ quét QR tạm ứng trên trang điều xe → chặn (CHI_O_KE_TOAN khi mục IV đã ghi sổ, SAI_BUOC khi chưa)", ma, 409, (r or {}).get("detail", {}).get("ma", ""))


# 13. tài xế khai đổ dầu dọc đường ở Việt Nam
_, dd = goi("/api/fuel-places", tk=tk["tx01"])
vn = [x for x in dd if x["country"] == "VN" and x["owner_type"] != "epl"][0]   # trạm bán dầu, không phải "kho xe" của EPL
px = p   # khai đổ dầu trên chính phiếu thử (tài xế tx01) — không đụng phiếu mẫu
if px:
    ma, r = goi("/api/trips/%s/bao-nhien-lieu" % px["id"],
                {"qty_l": 300, "place_id": vn["id"], "unit_price": 26000, "currency": "VND",
                 "note": "Đổ ở Hà Tĩnh để chạy về"}, tk["tx01"])
    bao("Tài xế khai đổ dầu bên Việt Nam", ma, 200)
    _, ct2 = goi("/api/trips/" + px["id"], tk=tk["admin"])
    ev = [e for e in ct2["events"] if e["kind"] == "refuel" and e["status"] == "reported"][-1]
    ma, r = goi("/api/trips/%s/events/%s/duyet" % (px["id"], ev["id"]), {}, tk["ketoan"])
    bao("KT Thu/Chi duyệt dầu dọc đường → từ chối (việc của KT kho xăng dầu)", ma, 403)
    ma, r = goi("/api/trips/%s/events/%s/duyet" % (px["id"], ev["id"]), {}, tk["khonl"])
    bao("KT kho xăng dầu duyệt → thành dòng mục III nguồn mua", ma, 200)
    d3 = [d for d in r["expenses"] if d["section"] == "fuel" and d["source"] == "mua" and d["place_id"] == vn["id"]]
    print("      dòng mới: %d lít · %s · %s" % (d3[-1]["qty"], d3[-1]["currency"], d3[-1]["acct_code"]))
    ma, r = goi("/api/trips/%s/bao-nhien-lieu" % px["id"],
                {"qty_l": 100, "place_id": [x for x in dd if x["owner_type"] == "epl"][0]["id"]}, tk["tx01"])
    bao("Khai đổ ở KHO của công ty → bảo dùng phiếu lĩnh", ma, 422, (r or {}).get("detail", {}).get("ma", ""))

# 14. tất toán theo tháng — ở TRANG KẾ TOÁN từ 28/09 (đợt 7c); số vẫn tính từ phiếu bên này
ky = (p.get("out_date") or p.get("doc_date"))[:7]
ma, r = goi("/api/tat-toan?ky=" + ky, tk=tk["ketoancp"])
bao("Bên trang điều xe: tất toán → đã dời sang trang kế toán", ma, 409, (r or {}).get("detail", {}).get("ma", ""))
ma, tt = K.kt("/api/tat-toan?ky=" + ky, vai="ketoancp")
bao("Bảng tất toán tháng %s (trang kế toán)" % ky, ma, 200, "%d tài xế" % len(tt["dong"]))
for d in tt["dong"]:
    print("      %-22s %d phiếu · ứng %10s · chi %10s · chênh %10s"
          % (d["driver_name"][:22], d["so_phieu"], round(d["tong_ung_lak"]), round(d["tong_chi_lak"]),
             round(d["chenh_lech_lak"])))
cho_chot = [d for d in tt["dong"] if d["so_phieu"] and not d["da_tat_toan"]]
if cho_chot:
    mot = cho_chot[0]
    ma, r = K.kt("/api/tat-toan", {"driver_id": mot["driver_id"], "period": ky}, vai="ketoan")
    bao("KT Thu/Chi chốt tất toán → từ chối (việc của KT Chi phí)", ma, 403)
    ma, r = K.kt("/api/tat-toan", {"driver_id": mot["driver_id"], "period": ky}, vai="ketoancp")
    bao("KT Chi phí VC chốt tất toán", ma, 200, "đã tất toán = %s" % r["da_tat_toan"])
    ma, r = K.kt("/api/tat-toan", {"driver_id": mot["driver_id"], "period": ky}, vai="ketoancp")
    bao("Chốt lần hai → từ chối", ma, 409, (r or {}).get("detail", {}).get("ma", ""))
    ma, r = K.kt("/api/tat-toan/%s?ky=%s" % (mot["driver_id"], ky), vai="ketoancp", method="DELETE")
    bao("Kế toán bỏ chốt để sửa lại", ma, 200)

# 15. sổ chứng từ — mỗi bước ở trên phải để lại đúng tờ của nó
ma, so = goi("/api/chung-tu?trip_id=" + p["id"], tk=tk["ketoan"])
bao("Kế toán xem sổ chứng từ của phiếu", ma, 200, "%d tờ" % len(so["ds"]))
loai_co = {c["loai"] for c in so["ds"]}
for c in so["ds"]:
    print("      %-18s %-10s %-24s %12s %s  %s / %s" % (c["so"], c["ngay"], (c["mo_ta"] or "")[:24], round(c["tien_lak"] or 0),
                                                    c["tien_te"], c["no"] or (c["no_ten"] or "-")[:10], c["co"] or (c["co_ten"] or "-")[:10]))
for can in ("DO", "PLNL", "PTU"):
    if can not in loai_co:
        raise SystemExit("DUNG: sổ chứng từ thiếu %s (có: %s)" % (can, sorted(loai_co)))
# tờ xuất kho dầu (PXK_NL) sinh ở sổ trang kế toán từ 28/09 — bên này không còn giữ
so_pxk = [v["ref"] for v in K.to_kho(p["doc_no"], "PXK_NL") if v["trip_no"] == p["doc_no"]]
assert so_pxk and all(x.startswith("PXK_NL/") for x in so_pxk), "sổ kế toán thiếu PXK_NL của phiếu: %s" % so_pxk
print("  OK  có đủ DO · PLNL · PTU bên này, PXK_NL %s ở sổ kế toán; số chứng từ dạng LOAI/YYMM/000n" % ", ".join(so_pxk))
ma, r = goi("/api/chung-tu?trip_id=" + p["id"], tk=tk["thabok"])
bao("Bãi xem sổ chứng từ → từ chối (số kế toán)", ma, 403, (r or {}).get("detail", {}).get("ma", ""))
mot = so["ds"][0]
ma, r = goi("/api/chung-tu/%s/da-day" % mot["id"], {}, tk["ketoan"])
bao("Kế toán đánh dấu đã đối chiếu", ma, 200, "da_day=%s" % r["da_day"])
_, so2 = goi("/api/chung-tu?trip_id=%s&chua_day=1" % p["id"], tk=tk["ketoan"])
assert all(c["id"] != mot["id"] for c in so2["ds"]), "tờ đã đối chiếu vẫn nằm trong danh sách chưa đối chiếu"
ma, r = goi("/api/chung-tu/%s/da-day" % mot["id"], {"da_day": False}, tk["ketoan"])
bao("Mở lại tờ đã đối chiếu", ma, 200, "da_day=%s" % r["da_day"])
ma, ds_loai = goi("/api/chung-tu/loai", tk=tk["ketoan"])
bao("Danh mục loại chứng từ", ma, 200, "%d loại" % len(ds_loai))

print("\nTHỬ PHIẾU LĨNH: ĐẠT — QR · thủ kho cấp dầu · chặn đúng chỗ · khai đổ dọc đường · tất toán · sổ chứng từ")
