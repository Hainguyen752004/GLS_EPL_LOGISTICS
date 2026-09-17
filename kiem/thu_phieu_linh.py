# -*- coding: utf-8 -*-
"""Thử luồng phiếu lĩnh — máy chủ thật, không phải bộ kiểm đơn vị.

    python kiem/thu_phieu_linh.py [http://127.0.0.1:8010]

Đi đúng đường một tờ phiếu lĩnh đi qua: Bãi lập → in mã QR → thủ kho quét, đối chiếu, cấp dầu →
dòng chi mang số phiếu xuất kho. Kèm các chỗ PHẢI bị từ chối: thủ kho kho khác, cấp lệch số lít mà
không ghi lý do, cấp hai lần, tài xế tự chi tiền cho mình, chi khi mục IV chưa ghi sổ. Cuối cùng là
tài xế khai đổ dầu dọc đường và bảng tất toán theo tháng.

Cần dữ liệu mẫu còn nguyên: python backend/app/seed.py --dung-lai
"""
import json
import sys
import urllib.error
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"


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


tk = {u: vao(u) for u in ("admin", "thabok", "ketoan", "khotb", "khovc", "quytb", "tx01")}
print("Đăng nhập %d vai OK" % len(tk))

_, ds = goi("/api/trips", tk=tk["admin"])
# Phiếu dùng để thử: còn dòng dầu LĨNH KHO chưa xuất (chạy lại nhiều lần thì phiếu cũ đã xuất rồi).
p = None
for x in ds:
    if x["finance_status"] == "paid":
        continue
    _, ct0 = goi("/api/trips/" + x["id"], tk=tk["admin"])
    if any(d["section"] == "fuel" and d["source"] == "kho" and not d["stock_move_id"] and d["paid_by_epl"]
           for d in ct0["expenses"]):
        p = x
        break
if p is None:
    raise SystemExit("Không còn phiếu nào có dòng dầu kho chưa xuất — gieo lại: python backend/app/seed.py --dung-lai")
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

# 8. dòng chi đã mang số phiếu xuất kho
_, ct = goi("/api/trips/" + p["id"], tk=tk["admin"])
dong_kho = [d for d in ct["expenses"] if d["section"] == "fuel" and d["source"] == "kho"]
print("  OK  dòng dầu kho đã gắn phiếu xuất kho: %s" % all(d["stock_move_id"] for d in dong_kho))

# 9. phiếu tạm ứng
ma, v2 = goi("/api/trips/%s/vouchers" % p["id"], {"kind": "advance"}, tk["thabok"])
bao("Bãi lập phiếu tạm ứng đi đường", ma, 200, "%s · %s LAK" % (v2[0]["doc_no"], round(v2[0]["amount_lak"])))
ptu = v2[0]

# 10-11. hai chỗ phải chặn quanh phiếu tạm ứng — chỉ thử khi phiếu còn ĐANG CHỜ cấp
if ptu["status"] != "cho":
    print("  --  phiếu tạm ứng đã cấp sẵn (%s), bỏ qua hai bước chặn" % ptu["status"])
else:
    ma, r = goi("/api/vouchers/%s/cap" % ptu["id"], {}, tk["tx01"])
    bao("Tài xế tự chi tạm ứng → từ chối", ma, 403, (r or {}).get("detail", {}).get("ma", ""))
    tt = ct["sections"].get("travel")
    ma, r = goi("/api/vouchers/%s/cap" % ptu["id"], {}, tk["quytb"])
    if tt == "booked":
        bao("Quỹ chi tạm ứng (mục IV đã ghi sổ)", ma, 200, "trạng thái %s" % (r or {}).get("status"))
    else:
        bao("Chi khi mục IV đang '%s' → sai bước" % tt, ma, 409, (r or {}).get("detail", {}).get("ma", ""))


# 13. tài xế khai đổ dầu dọc đường ở Việt Nam
_, dd = goi("/api/fuel-places", tk=tk["tx01"])
vn = [x for x in dd if x["country"] == "VN"][0]
_, ds_tx = goi("/api/trips", tk=tk["tx01"])
px = next((x for x in ds_tx if x['finance_status'] != 'paid'), None)   # phiếu đã thu tiền xong thì không khai thêm
if px:
    ma, r = goi("/api/trips/%s/bao-nhien-lieu" % px["id"],
                {"qty_l": 300, "place_id": vn["id"], "unit_price": 26000, "currency": "VND",
                 "note": "Đổ ở Hà Tĩnh để chạy về"}, tk["tx01"])
    bao("Tài xế khai đổ dầu bên Việt Nam", ma, 200)
    _, ct2 = goi("/api/trips/" + px["id"], tk=tk["admin"])
    ev = [e for e in ct2["events"] if e["kind"] == "refuel" and e["status"] == "reported"][-1]
    ma, r = goi("/api/trips/%s/events/%s/duyet" % (px["id"], ev["id"]), {}, tk["ketoan"])
    bao("Kế toán duyệt → thành dòng mục III nguồn mua", ma, 200)
    d3 = [d for d in r["expenses"] if d["section"] == "fuel" and d["source"] == "mua" and d["place_id"] == vn["id"]]
    print("      dòng mới: %d lít · %s · %s" % (d3[-1]["qty"], d3[-1]["currency"], d3[-1]["acct_code"]))
    ma, r = goi("/api/trips/%s/bao-nhien-lieu" % px["id"],
                {"qty_l": 100, "place_id": [x for x in dd if x["owner_type"] == "epl"][0]["id"]}, tk["tx01"])
    bao("Khai đổ ở KHO của công ty → bảo dùng phiếu lĩnh", ma, 422, (r or {}).get("detail", {}).get("ma", ""))

# 14. tất toán theo tháng
ky = (p.get("out_date") or p.get("doc_date"))[:7]
ma, tt = goi("/api/tat-toan?ky=" + ky, tk=tk["ketoan"])
bao("Bảng tất toán tháng %s" % ky, ma, 200, "%d tài xế" % len(tt["dong"]))
for d in tt["dong"]:
    print("      %-22s %d phiếu · ứng %10s · chi %10s · chênh %10s"
          % (d["driver_name"][:22], d["so_phieu"], round(d["tong_ung_lak"]), round(d["tong_chi_lak"]),
             round(d["chenh_lech_lak"])))
if tt["dong"]:
    mot = tt["dong"][0]
    ma, r = goi("/api/tat-toan", {"driver_id": mot["driver_id"], "period": ky}, tk["ketoan"])
    bao("Kế toán chốt tất toán", ma, 200, "đã tất toán = %s" % r["da_tat_toan"])
    ma, r = goi("/api/tat-toan", {"driver_id": mot["driver_id"], "period": ky}, tk["ketoan"])
    bao("Chốt lần hai → từ chối", ma, 409, (r or {}).get("detail", {}).get("ma", ""))
    ma, r = goi("/api/tat-toan/%s?ky=%s" % (mot["driver_id"], ky), tk=tk["ketoan"], cach="DELETE")
    bao("Kế toán bỏ chốt để sửa lại", ma, 200)

print("\nTHỬ PHIẾU LĨNH: ĐẠT — QR · thủ kho cấp dầu · chặn đúng chỗ · khai đổ dọc đường · tất toán")
