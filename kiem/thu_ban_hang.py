# -*- coding: utf-8 -*-
"""Thử ba việc mới trên máy chủ thật: đính kèm phiếu quặng · bán phụ tùng, dầu · sổ chứng từ bán hàng.

    python kiem/thu_ban_hang.py [http://127.0.0.1:8010]

Khoá phiếu và trả chủ xe liên kết đã nằm trong kiem/thu_luong_api.py (đi cùng luồng một phiếu).
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — kho nhiên liệu ở trang kế toán (28/09)


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

# ---------------------------------------------------------------- 2. bán phụ tùng · dầu — ở TRANG KẾ TOÁN từ 28/09 (đợt 6)
kt = lambda duong, than=None, vai=None, cach=None: K.kt(duong, than, vai=vai, method=cach)
ma_ct = lambda r: ((r or {}).get("detail") or {}).get("ma", "") if isinstance(r, dict) else ""
ma, r = goi("/api/ban-hang", tk=tk["ketoan"])
bao("Đường bán hàng bên trang điều xe → đã dời sang trang kế toán", ma, 409, ma_ct(r))
_, pt = kt("/api/phu-tung", vai="ketoan")
mon = next(x for x in pt if (x["qty"] or 0) >= 2)
_, kh = goi("/api/customers", tk=tk["ketoan"])
_, diem = goi("/api/fuel-places", tk=tk["ketoan"])
# bán từ kho CÓ DẦU (Thà Bốc): từ 23/09 bán quá tồn của đúng kho đó là bị chặn, không để kho âm
kho = next(x for x in diem if x["owner_type"] == "epl" and x.get("code") == "KHO-TB")
_, so_kho = kt("/api/nhien-lieu?place_id=%s" % kho["id"], vai="khonl")
gia_bq = so_kho["gia_bq"]
ton_truoc = mon["qty"]
than = {"sale_date": "2026-09-17", "customer_id": kh[0]["id"], "currency": "LAK", "note": "thử bán",
        "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 2, "unit_price": (mon["unit_price"] or 0) * 1.2 or 100000},
                  {"item_type": "fuel", "place_id": kho["id"], "qty": 50, "unit_price": 31000}]}
ma, r = kt("/api/ban-hang", than, "thabok")
bao("Bãi lập phiếu bán (trang kế toán) → từ chối", ma, 403)
ma, bh = kt("/api/ban-hang", than, "ketoan")
bao("Kế toán lập phiếu bán (2 %s + 50 lít dầu)" % mon["name"][:14], ma, 200, "%s · %s LAK" % (bh.get("doc_no"), round(bh.get("total_lak") or 0)))
assert bh["status"] == "issued" and len(bh["lines"]) == 2 and all(d["stock_move_id"] for d in bh["lines"]), bh
assert bh["customer_name"] == kh[0]["name"], "tên khách lấy từ danh mục bên trang điều xe"
_, pt2 = kt("/api/phu-tung", vai="ketoan")
assert next(x for x in pt2 if x["id"] == mon["id"])["qty"] == ton_truoc - 2, "tồn phụ tùng phải trừ 2"
print("  OK  tồn %s: %s → %s" % (mon["name"][:20], ton_truoc, ton_truoc - 2))
_, kho_nl = kt("/api/nhien-lieu", vai="khonl")
assert any(x["doc_no"] == bh["doc_no"] and x["kind"] == "out" and x["qty_out"] == 50 for x in kho_nl["rows"]), "sổ kho dầu phải có dòng xuất bán"
print("  OK  sổ kho nhiên liệu có dòng xuất %s · 50 lít" % bh["doc_no"])
dau = next(d for d in bh["lines"] if d["item_type"] == "fuel")
assert dau["cost_lak"] == round(50 * gia_bq), "giá vốn dầu bán = 50 lít × giá BÌNH QUÂN kho (C5.3): %s ≠ %s" % (dau["cost_lak"], round(50 * gia_bq))
print("  OK  giá vốn 50 lít dầu = bình quân kho %s LAK/L" % format(round(gia_bq), ","))
ma, r = kt("/api/ban-hang", {**than, "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 10 ** 6, "unit_price": 1}]}, "ketoan")
bao("Bán quá tồn → từ chối", ma, 409, ma_ct(r))
_, pt_x = kt("/api/phu-tung", vai="ketoan")
assert next(x for x in pt_x if x["id"] == mon["id"])["qty"] == ton_truoc - 2, "bị từ chối thì tồn không được đổi"
to = lambda loai, so: [v for v in K.to_kho(so, loai) if (v.get("lines") or {}).get("doc_no") == so]
pxk, hd = to("PXK_BAN", bh["doc_no"]), to("HD_BAN", bh["doc_no"])
bao("Sổ kế toán có PXK_BAN + HD_BAN của phiếu bán", 200 if len(pxk) == 1 and len(hd) == 1 else 500, 200, "%s · %s" % ([v["ref"] for v in pxk], [v["ref"] for v in hd]))
assert pxk[0]["debit"] == "607" and pxk[0]["credit"] == "1371" and pxk[0]["entry_id"] and abs(pxk[0]["amount_lak"] - bh["cost_lak"]) < 1, pxk
assert hd[0]["debit"] == "1211" and hd[0]["credit"] == "70" and hd[0]["entry_id"] and abs(hd[0]["amount_lak"] - bh["total_lak"]) < 1, hd
print("  OK  PXK_BAN Nợ %s / Có %s (giá vốn) · HD_BAN Nợ %s / Có %s — vào sổ" % (pxk[0]["debit"], pxk[0]["credit"], hd[0]["debit"], hd[0]["credit"]))
ma, r = kt("/api/ban-hang/%s/thu" % bh["id"], {}, "thabok")
bao("Bãi ghi thu → từ chối", ma, 403)
ma, r = kt("/api/ban-hang/%s/thu" % bh["id"], {}, "doanhthu")
bao("Kế toán doanh thu ghi đã thu", ma, 200, (r or {}).get("status"))
ma, r = kt("/api/ban-hang/%s/thu" % bh["id"], {}, "quytb")
bao("Ghi thu lần hai → từ chối", ma, 409)
pt_ = to("PT_BAN", bh["doc_no"])
assert len(pt_) == 1 and pt_[0]["debit"] == "1011" and pt_[0]["credit"] == "1211", "phải có PT_BAN Nợ 1011 / Có 1211: %s" % pt_
print("  OK  có PT_BAN sau khi thu (Nợ 1011 / Có 1211)")
ma, r = kt("/api/ban-hang/%s" % bh["id"], cach="DELETE", vai="ketoan")
bao("Bỏ phiếu đã thu → từ chối", ma, 409)
# phiếu thứ hai: lập rồi bỏ → hàng về kho, chứng từ rút
ma, bh2 = kt("/api/ban-hang", {**than, "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 1, "unit_price": 50000}]}, "ketoan")
bao("Lập phiếu bán thứ hai (1 món)", ma, 200, bh2.get("doc_no"))
ma, r = kt("/api/ban-hang/%s" % bh2["id"], cach="DELETE", vai="ketoan")
bao("Bỏ phiếu chưa thu", ma, 200)
_, pt3 = kt("/api/phu-tung", vai="ketoan")
assert next(x for x in pt3 if x["id"] == mon["id"])["qty"] == ton_truoc - 2, "bỏ phiếu thì hàng phải về kho"
assert not to("PXK_BAN", bh2["doc_no"]) and not to("HD_BAN", bh2["doc_no"]), "chứng từ của phiếu đã bỏ phải rút"
print("  OK  hàng về kho, chứng từ của %s đã rút" % bh2["doc_no"])
ma, ds_bh = kt("/api/ban-hang?thang=2026-09", vai="doanhthu")
bao("Danh sách phiếu bán tháng 9", ma, 200, "%d phiếu · %s LAK" % (len(ds_bh["ds"]), round(ds_bh["tong_lak"])))

# 3. đánh số chứng từ: rút một tờ rồi ghi tờ mới thì KHÔNG được đụng số cũ
#    (trước đây đánh số bằng cách đếm dòng nên sau khi rút, số tụt lại và trùng)
mot = {"sale_date": "2026-09-17", "customer_id": kh[0]["id"], "currency": "LAK", "note": "thử bán",
       "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 1, "unit_price": 50000}]}
ma, a = kt("/api/ban-hang", mot, "ketoan"); bao("Lập phiếu bán A", ma, 200, a.get("doc_no"))
ma, b = kt("/api/ban-hang", mot, "ketoan"); bao("Lập phiếu bán B", ma, 200, b.get("doc_no"))
so_b = [v["ref"] for v in to("PXK_BAN", b["doc_no"])]
ma, _r = kt("/api/ban-hang/%s" % a["id"], cach="DELETE", vai="ketoan"); bao("Bỏ phiếu A (rút tờ chứng từ)", ma, 200)
ma, c = kt("/api/ban-hang", mot, "ketoan"); bao("Lập phiếu bán C sau khi đã rút", ma, 200, c.get("doc_no"))
so_c = [v["ref"] for v in to("PXK_BAN", c["doc_no"])]
print("      số tờ PXK_BAN: B %s · C %s" % (so_b, so_c))
if not so_c or so_c == so_b or c["doc_no"] in (a["doc_no"], b["doc_no"]):
    raise SystemExit("DUNG: số của C trùng số cũ (%s) — phải lấy số lớn nhất + 1" % so_b)
print("  OK  số phiếu và số chứng từ không tụt lại sau khi rút tờ, không đụng số cũ")
for x in (b, c):
    kt("/api/ban-hang/%s" % x["id"], cach="DELETE", vai="ketoan")

print("\nTHỬ BÁN HÀNG: ĐẠT — đính kèm phiếu quặng · bán phụ tùng, dầu (trang kế toán) · xuất kho · hoá đơn · thu · bỏ phiếu")
