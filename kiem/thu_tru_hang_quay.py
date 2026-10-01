# -*- coding: utf-8 -*-
"""Thử TRỪ HÀNG CHỦ XE MUA Ở QUẦY vào đề nghị trả chủ xe (chủ dự án 23/09: "deal 1tr6, mua xăng 3 trăm → trả 1tr3"; 01/10:
tiền trả ở hệ kế toán anh Tune, phiếu bán ở kho tạm).

    python kiem/thu_tru_hang_quay.py [http://127.0.0.1:8013] [kho tạm http://127.0.0.1:8031] [http://127.0.0.1:5090]

CHỈ chạy trên máy thử (bản sao DB). Máy điều xe đang kiểm phải trỏ kho tạm vào đúng máy ở tham số 2. Một chủ xe có phiếu
xe thuê đã khoá chờ trả; lập ở kho tạm một phiếu bán 50.000 LAK cho chủ xe đó, rồi:
  1. xem trước (/api/owners/{id}/hang-quay): có phiếu bán; số trả thực = Σ phiếu − hàng mua; Bãi không xem.
  2. lập đề nghị trả một phiếu → phiếu chi bên kế toán ĐÚNG SỐ TRẢ THỰC, phiếu bán giữ chỗ "TUNE-CHO:<số đề nghị>"
     (cần chi_tune theo giao ước 01/10); phiếu bán đã giữ chỗ không vào đề nghị khác.
  3. bỏ đề nghị → phiếu chi bên kế toán rút, phiếu bán về chờ trừ. Dọn: bỏ phiếu bán thử.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8013").rstrip("/")
KHO = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8031").rstrip("/")
KT = (sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:5090").rstrip("/")
if GOC.endswith((":8020", ":8010", ":8001")) or KHO.endswith(":8030"):
    sys.exit("Không chạy bài này trên máy thật.")
TK, TK_KHO, LOI = {}, {}, []
TOKEN_KT = next(d.split("=", 1)[1].strip().strip('"').strip("'") for d in open(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".env"), encoding="utf-8") if d.strip().startswith("EPL_ACC_CODE_TOKEN="))


def _http(url, body=None, dau=None, method=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"), headers={"Content-Type": "application/json", **(dau or {})})
    try:
        with urllib.request.urlopen(r, timeout=300) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, {}


def goi(duong, body=None, vai=None, method=None):
    return _http(GOC + duong, body, {"Authorization": "Bearer " + TK[vai]} if vai else None, method)


def kho(duong, body=None, vai=None, method=None):
    return _http(KHO + duong, body, {"Authorization": "Bearer " + TK_KHO[vai]} if vai else None, method)


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return (d or {}).get("ma", "") if isinstance(d, dict) else ""


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)
    return dk


def main():
    for u in ("thabok", "ketoan", "admin"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]
    TK_KHO["ketoan"] = kho("/api/dang-nhap", {"username": "ketoan", "password": "1234"})[1]["token"]
    s, ds = goi("/api/owners", vai="ketoan")
    chu = tt = None
    for o in [o for o in ds if o["active"]]:
        s, t = goi("/api/owners/%s/tra-ke-toan" % o["id"], vai="ketoan")
        duong = [x for x in (t or {}).get("cho") or [] if (x["tra_chu_xe_lak"] or 0) > 100000]
        if s == 200 and duong:
            chu, tt, x = o, t, duong[0]
            break
    if not dung(chu is not None, "có chủ xe với phiếu đã khoá chờ trả > 100.000 LAK", chu["name"] if chu else ""):
        return ket_thuc()
    s, dm = kho("/api/ban-hang/danh-muc", vai="ketoan")
    mon = next(p for p in dm["phu_tung"] if (p["qty"] or 0) >= 1)
    s, ban = kho("/api/ban-hang", {"sale_date": time.strftime("%Y-%m-%d"), "owner_id": chu["id"], "currency": "LAK",
                                   "note": "thử trừ hàng quầy vào đề nghị trả", "lines": [{"item_type": "part", "part_id": mon["id"], "qty": 1,
                                                                                           "unit_price": 50000}]}, vai="ketoan")
    if not dung(s == 200 and ban.get("owner_id") == chu["id"], "kho tạm: chủ xe mua 1 món ở quầy 50.000 LAK", ban.get("doc_no")):
        return ket_thuc()
    rid = None
    try:
        print("1. Xem trước số trả thực")
        s, g = goi("/api/owners/%s/hang-quay?trip_ids=%s" % (chu["id"], x["id"]), vai="thabok")
        dung(s == 403, "Bãi xem → 403", s)
        s, h = goi("/api/owners/%s/hang-quay?trip_ids=%s" % (chu["id"], x["id"]), vai="ketoan")
        u = (h or {}).get("uoc_tinh") or {}
        dung(s == 200 and any(b["id"] == ban["id"] for b in h["hang"]), "hàng chờ trừ có phiếu bán thử", "%s phiếu" % len((h or {}).get("hang") or []))
        co = any(b["id"] == ban["id"] for b in u.get("hang") or [])
        dung(co and u["tra_thuc_lak"] == u["tong_lak"] - u["tru_lak"] and u["tru_lak"] >= 50000
             and abs(u["dong"][0]["tra_thuc"] - (x["tra_chu_xe"] - u["dong"][0]["tru"])) < 0.01,
             "số trả thực = Σ phiếu − hàng mua", "%s %s − %s = %s %s (Kíp: %s − %s)" % (
                 u.get("tong"), u.get("ccy"), u.get("tru"), u.get("tra_thuc"), u.get("ccy"), u.get("tong_lak"), u.get("tru_lak")))
        print("2. Đề nghị trả đúng số trả thực")
        s, r = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": [x["id"]], "phuong_thuc": "bank"}, "ketoan")
        s2, t2 = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="ketoan")
        dn = next((d for d in t2["de_nghi"] if d["trip_ids"] == [x["id"]] and d["status"] in ("da_gui", "loi")), None)
        rid = dn["id"] if dn else None
        dung(dn is not None and abs(dn["amount"] - u["tra_thuc"]) < 0.01, "đề nghị mang SỐ TRẢ THỰC (không phải tổng phiếu)",
             "%s (tổng phiếu %s) · %s %s" % (dn and dn["amount"], u.get("tong"), dn and dn["status"], dn and (dn["document_no"] or dn["error_message"] or "")))
        s3, b3 = kho("/api/ban-hang/%s" % ban["id"], vai="ketoan")
        dung(dn is not None and b3.get("owner_payment_id") == "TUNE-CHO:" + dn["ref_no"], "phiếu bán giữ chỗ cho đề nghị",
             b3.get("owner_payment_id") or "trống")
        if dn and dn["status"] == "da_gui" and dn.get("real_id"):
            s4, g4 = _http(KT + "/api/v1/accounting/cmpayment-receipt/%s?voucherType=CMP" % dn["real_id"], dau={"Authorization": "Bearer " + TOKEN_KT})
            e = ((g4 or {}).get("Result") or {}).get("Entries") or []
            tong_dong = round(sum(z.get("ET_TOTALAMOUNT") or 0 for z in e), 2)
            dung(abs(tong_dong - u["tra_thuc"]) < 0.01 and all(z.get("ET_DEBTORACCOUNT") == "4022" for z in e),
                 "phiếu chi bên kế toán: các dòng Nợ 4022 cộng đúng số trả thực", "%s dòng · %s" % (len(e), tong_dong))
        s5, h5 = goi("/api/owners/%s/hang-quay" % chu["id"], vai="ketoan")
        dung(s5 == 200 and not any(b["id"] == ban["id"] for b in h5["hang"]), "phiếu bán đã giữ chỗ không còn chờ trừ (không vào đề nghị khác)")
    finally:
        if rid:
            s, g = goi("/api/chi-chu-xe/%s/huy" % rid, {}, vai="ketoan")
            dung(s == 200 and g["status"] == "huy", "bỏ đề nghị thử (rút phiếu chi bên kế toán)", "%s %s" % (s, ma(g)))
            s, b = kho("/api/ban-hang/%s" % ban["id"], vai="ketoan")
            dung(b.get("status") == "issued" and not b.get("owner_payment_id"), "bỏ đề nghị → phiếu bán về chờ trừ",
                 "%s %s" % (b.get("status"), b.get("owner_payment_id")))
        s, g = kho("/api/ban-hang/%s" % ban["id"], vai="ketoan", method="DELETE")
        if s != 200 and isinstance(g, dict) and ma(g) == "DA_TRU":          # chi_tune chưa trả phiếu bán khi bỏ đề nghị: gỡ tay
            TK_KHO["admin"] = kho("/api/dang-nhap", {"username": "admin", "password": "1234"})[1]["token"]
            may = kho("/api/cau-hinh", vai="admin")[1]["token_nhan"]                # khoá máy (Sếp thấy) — không in ra
            _http(KHO + "/api/lien-thong/ban-hang/bo-tru", {"ma": (kho("/api/ban-hang/%s" % ban["id"], vai="ketoan")[1] or {}).get("owner_payment_id")},
                  {"Authorization": "Bearer " + may, "X-Nguoi-Dung": "ketoan"})
            s, g = kho("/api/ban-hang/%s" % ban["id"], vai="ketoan", method="DELETE")
        dung(s == 200, "dọn: bỏ phiếu bán thử (hàng về kho)", "%s %s" % (s, ma(g)))
    ket_thuc()


def ket_thuc():
    print("\nTRỪ HÀNG QUẦY VÀO TRẢ CHỦ XE: %s" % ("ĐẠT" if not LOI else "SAI %d — %s" % (len(LOI), "; ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
