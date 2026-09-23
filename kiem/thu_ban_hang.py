# -*- coding: utf-8 -*-
"""Thử ba việc mới trên máy chủ thật: đính kèm phiếu quặng · bán phụ tùng, dầu · sổ chứng từ bán hàng.

    python kiem/thu_ban_hang.py [http://127.0.0.1:8010]

Khoá phiếu và trả chủ xe liên kết đã nằm trong kiem/thu_luong_api.py (đi cùng luồng một phiếu).
"""
import json
import sys
import urllib.error
import urllib.request
import uuid

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"


def goi(duong, than=None, tk=None, cach=None, tho=None, kieu=None):
    r = urllib.request.Request(GOC + duong, method=cach or ("POST" if (than is not None or tho is not None) else "GET"))
    r.add_header("Accept", "application/json")
    if tk:
        r.add_header("Authorization", "Bearer " + tk)
    du = None
    if tho is not None:
        du = tho; r.add_header("Content-Type", kieu)
    elif than is not None:
        du = json.dumps(than).encode(); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, du, timeout=30) as o:
            ct = o.headers.get("Content-Type", "")
            return o.status, (json.loads(o.read().decode() or "null") if "json" in ct else o.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "null")
        except ValueError:
            return e.code, None


def vao(u):
    _, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
    return g["token"]


def bao(nhan, ma, mong=200, chi_tiet=""):
    dau = "OK " if ma == mong else "SAI"
    print("  %s %-54s %s%s" % (dau, nhan, ma, (" · " + chi_tiet) if chi_tiet else ""))
    if ma != mong:
        raise SystemExit("DUNG: %s tra %s, mong %s" % (nhan, ma, mong))


def multipart(truong, tep_ten, tep_du, tep_kieu):
    """Gói multipart/form-data bằng tay — urllib không có sẵn."""
    ranh = "----epl" + uuid.uuid4().hex
    b = []
    for k, v in truong.items():
        b += [("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (ranh, k, v)).encode()]
    b += [("--%s\r\nContent-Disposition: form-data; name=\"tep\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (ranh, tep_ten, tep_kieu)).encode(),
          tep_du, b"\r\n", ("--%s--\r\n" % ranh).encode()]
    return b"".join(b), "multipart/form-data; boundary=" + ranh


tk = {u: vao(u) for u in ("admin", "thabok", "ketoan", "doanhthu", "khonl", "quytb", "tx01")}
print("Đăng nhập %d vai OK" % len(tk))

# ---------------------------------------------------------------- 1. đính kèm phiếu quặng
_, ds = goi("/api/trips", tk=tk["admin"])
p = next(x for x in ds if not x.get("locked"))
print("Phiếu thử đính kèm: %s" % p["doc_no"])
# PNG 1×1 hợp lệ
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8ffff3f0300050001019dd6b5c50000000049454e44ae426082")
du, kieu = multipart({"kind": "ore_bill", "note": "thử"}, "phieu_quang.png", PNG, "image/png")
ma, a = goi("/api/trips/%s/tep" % p["id"], tk=tk["thabok"], tho=du, kieu=kieu)
bao("Bãi đính kèm ảnh phiếu quặng", ma, 200, "%s · %s byte" % (a["filename"], a["size"]))
du2, kieu2 = multipart({}, "virus.exe", b"MZ....", "application/octet-stream")
ma, r = goi("/api/trips/%s/tep" % p["id"], tk=tk["thabok"], tho=du2, kieu=kieu2)
bao("Đưa tệp .exe → từ chối", ma, 422, (r or {}).get("detail", {}).get("ma", ""))
ma, r = goi("/api/trips/%s/tep" % p["id"], tk=tk["tx01"], tho=du, kieu=kieu)
bao("Tài xế đính kèm → từ chối", ma, 403)
ma, ds_tep = goi("/api/trips/%s/tep" % p["id"], tk=tk["ketoan"])
bao("Kế toán xem danh sách tệp", ma, 200, "%d tệp" % len(ds_tep))
ma, noi_dung = goi(a["url"] + "?tk=" + tk["ketoan"])
bao("Mở tệp bằng phiên trong ?tk=", ma, 200, "%d byte, đúng PNG=%s" % (len(noi_dung), noi_dung[:4] == PNG[:4]))
ma, r = goi(a["url"])
bao("Mở tệp không có phiên → từ chối", ma, 401)
_, ct = goi("/api/trips/" + p["id"], tk=tk["admin"])
assert ct["attachments"] >= 1, ct["attachments"]
ma, r = goi("/api/tep/" + a["id"], tk=tk["thabok"], cach="DELETE")
bao("Bãi xoá tệp mình đưa lên", ma, 200)

# ---------------------------------------------------------------- 2. bán phụ tùng · dầu
_, pt = goi("/api/parts", tk=tk["ketoan"])
mon = next(x for x in pt if (x["qty"] or 0) >= 2)
_, kh = goi("/api/customers", tk=tk["ketoan"])
_, diem = goi("/api/fuel-places", tk=tk["ketoan"])
# bán từ kho CÓ DẦU (Thà Bốc): từ 23/09 bán quá tồn của đúng kho đó là bị chặn, không để kho âm
kho = next(x for x in diem if x["owner_type"] == "epl" and x.get("code") == "KHO-TB")
_, so_kho = goi("/api/fuel-moves?place_id=%s" % kho["id"], tk=tk["khonl"])
gia_bq = so_kho["gia_bq"]
ton_truoc = mon["qty"]
than = {"sale_date": "2026-09-17", "customer_id": kh[0]["id"], "currency": "LAK", "note": "thử bán",
        "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 2, "unit_price": (mon["unit_price"] or 0) * 1.2 or 100000},
                  {"item_type": "fuel", "place_id": kho["id"], "qty": 50, "unit_price": 31000}]}
ma, r = goi("/api/ban-hang", than, tk["thabok"])
bao("Bãi lập phiếu bán → từ chối", ma, 403)
ma, bh = goi("/api/ban-hang", than, tk["ketoan"])
bao("Kế toán lập phiếu bán (2 %s + 50 lít dầu)" % mon["name"][:14], ma, 200, "%s · %s LAK" % (bh["doc_no"], round(bh["total_lak"])))
assert bh["status"] == "issued" and len(bh["lines"]) == 2 and all(d["stock_move_id"] for d in bh["lines"]), bh
_, pt2 = goi("/api/parts", tk=tk["ketoan"])
assert next(x for x in pt2 if x["id"] == mon["id"])["qty"] == ton_truoc - 2, "tồn phụ tùng phải trừ 2"
print("  OK  tồn %s: %s → %s" % (mon["name"][:20], ton_truoc, ton_truoc - 2))
_, kho_nl = goi("/api/fuel-moves", tk=tk["khonl"])
assert any(x["doc_no"] == bh["doc_no"] and x["kind"] == "out" and x["qty_out"] == 50 for x in kho_nl["rows"]), "sổ kho dầu phải có dòng xuất bán"
print("  OK  sổ kho nhiên liệu có dòng xuất %s · 50 lít" % bh["doc_no"])
dau = next(d for d in bh["lines"] if d["item_type"] == "fuel")
assert dau["cost_lak"] == round(50 * gia_bq), "giá vốn dầu bán = 50 lít × giá BÌNH QUÂN kho (C5.3): %s ≠ %s" % (dau["cost_lak"], round(50 * gia_bq))
print("  OK  giá vốn 50 lít dầu = bình quân kho %s LAK/L" % format(round(gia_bq), ","))
ma, r = goi("/api/ban-hang", {**than, "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 10 ** 6, "unit_price": 1}]}, tk["ketoan"])
bao("Bán quá tồn → từ chối", ma, 409, (r or {}).get("detail", {}).get("ma", ""))
ma, so = goi("/api/chung-tu?loai=PXK_BAN,HD_BAN,PT_BAN", tk=tk["ketoan"])
loai = {c["loai"] for c in so["ds"] if (c["payload"] or {}).get("doc_no") == bh["doc_no"]}
bao("Sổ chứng từ có PXK_BAN + HD_BAN của phiếu bán", 200 if loai == {"PXK_BAN", "HD_BAN"} else 500, 200, ", ".join(sorted(loai)))
pxk = next(c for c in so["ds"] if c["loai"] == "PXK_BAN" and (c["payload"] or {}).get("doc_no") == bh["doc_no"])
assert pxk["no"] and pxk["co"] == "1371", "xuất kho bán phải đủ hai vế giá vốn / 1371: %s / %s" % (pxk["no"], pxk["co"])
print("  OK  PXK_BAN đủ hai vế: Nợ %s / Có %s" % (pxk["no"], pxk["co"]))
ma, r = goi("/api/ban-hang/%s/thu" % bh["id"], {}, tk["thabok"])
bao("Bãi ghi thu → từ chối", ma, 403)
ma, r = goi("/api/ban-hang/%s/thu" % bh["id"], {}, tk["doanhthu"])
bao("Kế toán doanh thu ghi đã thu", ma, 200, r["status"])
ma, r = goi("/api/ban-hang/%s/thu" % bh["id"], {}, tk["quytb"])
bao("Ghi thu lần hai → từ chối", ma, 409)
ma, so = goi("/api/chung-tu?loai=PT_BAN", tk=tk["ketoan"])
assert any((c["payload"] or {}).get("doc_no") == bh["doc_no"] for c in so["ds"]), "phải có PT_BAN"
print("  OK  có PT_BAN sau khi thu")
ma, r = goi("/api/ban-hang/%s" % bh["id"], tk=tk["ketoan"], cach="DELETE")
bao("Bỏ phiếu đã thu → từ chối", ma, 409)
# phiếu thứ hai: lập rồi bỏ → hàng về kho, chứng từ rút
ma, bh2 = goi("/api/ban-hang", {**than, "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 1, "unit_price": 50000}]}, tk["ketoan"])
bao("Lập phiếu bán thứ hai (1 món)", ma, 200, bh2["doc_no"])
ma, r = goi("/api/ban-hang/%s" % bh2["id"], tk=tk["ketoan"], cach="DELETE")
bao("Bỏ phiếu chưa thu", ma, 200)
_, pt3 = goi("/api/parts", tk=tk["ketoan"])
assert next(x for x in pt3 if x["id"] == mon["id"])["qty"] == ton_truoc - 2, "bỏ phiếu thì hàng phải về kho"
ma, so = goi("/api/chung-tu?loai=PXK_BAN,HD_BAN", tk=tk["ketoan"])
assert not any((c["payload"] or {}).get("doc_no") == bh2["doc_no"] for c in so["ds"]), "chứng từ của phiếu đã bỏ phải rút"
print("  OK  hàng về kho, chứng từ của %s đã rút" % bh2["doc_no"])
ma, ds_bh = goi("/api/ban-hang?thang=2026-09", tk=tk["doanhthu"])
bao("Danh sách phiếu bán tháng 9", ma, 200, "%d phiếu · %s LAK" % (len(ds_bh["ds"]), round(ds_bh["tong_lak"])))

# 3. đánh số chứng từ: rút một tờ rồi ghi tờ mới thì KHÔNG được đụng số cũ
#    (trước đây đánh số bằng cách đếm dòng nên sau khi rút, số tụt lại và trùng)
def so_cua(bh_doc_no, loai):
    _, so = goi("/api/chung-tu?loai=" + loai, tk=tk["ketoan"])
    return [c["so"] for c in so["ds"] if (c["payload"] or {}).get("doc_no") == bh_doc_no]


mot = {"sale_date": "2026-09-17", "customer_id": kh[0]["id"], "currency": "LAK",
       "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 1, "unit_price": 50000}]}
ma, a = goi("/api/ban-hang", mot, tk["ketoan"]); bao("Lập phiếu bán A", ma, 200, a["doc_no"])
ma, b = goi("/api/ban-hang", mot, tk["ketoan"]); bao("Lập phiếu bán B", ma, 200, b["doc_no"])
so_b = so_cua(b["doc_no"], "PXK_BAN")
ma, _r = goi("/api/ban-hang/%s" % a["id"], tk=tk["ketoan"], cach="DELETE"); bao("Bỏ phiếu A (rút tờ chứng từ)", ma, 200)
ma, c = goi("/api/ban-hang", mot, tk["ketoan"]); bao("Lập phiếu bán C sau khi đã rút", ma, 200, c["doc_no"])
so_c = so_cua(c["doc_no"], "PXK_BAN")
print("      số tờ PXK_BAN: B %s · C %s" % (so_b, so_c))
if not so_c or so_c == so_b:
    raise SystemExit("DUNG: số chứng từ của C trùng số của B (%s) — phải lấy số lớn nhất + 1" % so_b)
print("  OK  số chứng từ không tụt lại sau khi rút tờ, không đụng số cũ")
for x in (b, c):
    goi("/api/ban-hang/%s" % x["id"], tk=tk["ketoan"], cach="DELETE")

print("\nTHỬ BÁN HÀNG: ĐẠT — đính kèm phiếu quặng · bán phụ tùng, dầu · xuất kho · hoá đơn · thu · bỏ phiếu")
