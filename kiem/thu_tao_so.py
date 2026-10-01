# -*- coding: utf-8 -*-
"""Thử đường TẠO SO bên kế toán (anh Tune) từ phiếu đề nghị thu — hợp đồng kế toán, mục 3.2 (01/10).

    python kiem/thu_tao_so.py [http://127.0.0.1:8011]

KHÔNG gọi sang hệ anh Tune: chỉ đường XEM TRƯỚC (máy chủ dựng và kiểm gói, không gọi mạng) và các lần bị chặn quyền.
Bài này gán tạm mã khách của một khách trên máy thử rồi trả lại như cũ.

Kiểm: vai không thấy tiền bán (Bãi, tài xế) bị chặn · vai khác acct / admin không gửi được · DO chưa khoá bị chặn · khách
chưa có mã bên kế toán bị chặn, câu lỗi nói rõ · mã ghép khách_tuyến quá 50 ký tự bị chặn · gói đúng khuôn: ba khoá gốc,
customer_id = mã khách bên kế toán, một dòng thu, tổng khớp chính xác, tiền VND/LAK/USD, không mang khối lồng ngoài hợp đồng.
"""
import json
import sys
import urllib.error
import urllib.request
from decimal import Decimal

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
if GOC.endswith((":8020", ":8010")):
    sys.exit("Không chạy bài này trên máy thật — nó gán tạm mã khách.")
TK = {}
LOI = []


def goi(duong, body=None, u=None, method=None):
    r = urllib.request.Request(GOC + duong, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[u]} if u else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def ma_loi(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma") if isinstance(d, dict) else None


def main():
    for u in ("ketoan", "thabok", "tx01", "doanhthu", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        TK[u] = g["token"]
    khoa, mo = [], []
    for th in ("2026-08", "2026-09"):
        s, d = goi("/api/de-nghi-thu?thang=" + th, u="ketoan")
        khoa += [x for x in d["ds"] if x["locked"]]
        mo += [x for x in d["ds"] if not x["locked"]]
    s, ds_trip = goi("/api/trips?locked=false&co=5", u="admin")
    chua_khoa = mo[0]["trip_id"] if mo else (ds_trip[0]["id"] if ds_trip else None)
    if not khoa:
        sys.exit("DỪNG: máy thử không có DO nào đã khoá")
    x = khoa[0]
    tid = x["trip_id"]
    print("DO thử: %s (%s) · %d DO đã khoá" % (x["doc_no"], x["customer_name"], len(khoa)))

    print("1. Quyền")
    dung(goi("/api/trips/%s/tao-so" % tid, u="thabok")[0] == 403, "Bãi xem trước → 403 (không thấy tiền bán)")
    dung(goi("/api/trips/%s/tao-so" % tid, u="tx01")[0] == 403, "tài xế → 403")
    for u in ("thabok", "tx01", "doanhthu"):
        s, g = goi("/api/trips/%s/tao-so" % tid, {}, u=u)
        dung(s == 403 and ma_loi(g) == "KHONG_CO_QUYEN", "%s gửi → 403 KHONG_CO_QUYEN (chỉ KT Thu/Chi VC · Sếp)" % u, str(s))
    dung(goi("/api/trips/%s/tao-so" % tid)[0] == 401, "không đăng nhập → 401")

    print("2. Luật chặn (xem trước, không gọi mạng)")
    if chua_khoa:
        s, v = goi("/api/trips/%s/tao-so" % chua_khoa, u="ketoan")
        dung(s == 200 and (v.get("loi") or {}).get("ma") == "DO_CHUA_KHOA", "DO chưa khoá → DO_CHUA_KHOA", str((v.get("loi") or {}).get("ma")))
    s, p = goi("/api/trips/" + tid, u="ketoan")
    cid = p["customer_id"]
    s, khs = goi("/api/customers", u="ketoan")
    ma_cu = next(k for k in khs if k["id"] == cid).get("code")
    try:
        goi("/api/customers/" + cid, {"code": ""}, u="ketoan", method="PUT")
        s, v = goi("/api/trips/%s/tao-so" % tid, u="ketoan")
        l = v.get("loi") or {}
        dung(s == 200 and l.get("ma") == "THIEU_MA_KHACH_KE_TOAN" and "mã khách" in (l.get("loi") or ""),
             "khách chưa có mã bên kế toán → THIEU_MA_KHACH_KE_TOAN, câu lỗi nói rõ")
        dung("body" not in v, "bị chặn thì không có gói")
        # mã khách + '_' + mã tuyến (12 ký tự) phải ≤ 50 → danh mục khách chặn ngay lúc gán mã dài hơn 37
        s, g = goi("/api/customers/" + cid, {"code": "KIEM-" + "X" * 33}, u="ketoan", method="PUT")
        dung(s == 422 and ((g.get("detail") or {}).get("ma") == "MA_KHACH_SAI"),
             "mã khách 38 ký tự (ghép với mã tuyến quá 50) bị danh mục chặn ngay lúc gán → 422 MA_KHACH_SAI", s)
        goi("/api/customers/" + cid, {"code": "KIEM-" + "X" * 32}, u="ketoan", method="PUT")
        s, v = goi("/api/trips/%s/tao-so" % tid, u="ketoan")
        dung(s == 200 and "loi" not in v and len(v["tom_tat"]["item_code"]) == 50,
             "mã khách đúng 37 ký tự → gói dựng được, mã mặt hàng khách_tuyến đúng 50 ký tự",
             len((v.get("tom_tat") or {}).get("item_code") or ""))

        print("3. Khuôn gói")
        goi("/api/customers/" + cid, {"code": "KIEM-SO-01"}, u="ketoan", method="PUT")
        s, v = goi("/api/trips/%s/tao-so" % tid, u="ketoan")
        b = v.get("body") or {}
        h = b.get("header") or {}
        ds = b.get("details") or []
        dung(s == 200 and not v.get("loi") and sorted(b) == ["details", "header", "schemaVersion"] and b.get("schemaVersion") == 1,
             "đúng ba khoá gốc schemaVersion / header / details")
        dung(h.get("do_id") == "EPLLAO-" + tid and h.get("status") == "delivered", "do_id EPLLAO-<Trip.id>, status delivered")
        dung(h.get("customer_id") == "KIEM-SO-01", "header.customer_id = mã khách bên kế toán (không phải mã nội bộ)", h.get("customer_id"))
        dung(h.get("currency") in ("VND", "LAK", "USD") and h.get("currency_thu") == h.get("currency"), "tiền VND/LAK/USD, currency_thu = currency")
        dung(len(ds) == 1 and ds[0]["kind"] == "thu" and ds[0]["currency"] == h.get("currency"), "một dòng thu cùng tiền cước (hợp đồng 3.2)")
        tong = Decimal(str(h.get("selling_price"))) + Decimal(str(h.get("customer_surcharge_total")))
        dung(tong == Decimal(str(h.get("final_selling_price"))) == Decimal(str(ds[0]["actual_amount"])) > Decimal("0.01"),
             "selling_price + phụ thu = final_selling_price = dòng thu, > 0.01", str(h.get("final_selling_price")))
        dung(abs(float(h.get("final_selling_price")) - float(x["doanh_thu"])) < 0.001, "tổng bán = cước trên phiếu đề nghị thu", "%s %s" % (x["doanh_thu"], x["ccy"]))
        dung(isinstance(h.get("route"), dict) and h["route"].get("id") and len("KIEM-SO-01_" + h["route"]["id"]) <= 50, "có tuyến, mã ghép ≤ 50")
        dung(not any(k in h for k in ("hire", "fx_rates_on_trip", "cost_by_section_lak", "customer_code")),
             "không mang khối lồng / khoá ngoài hợp đồng")
        dung((v.get("tom_tat") or {}).get("item_code") == "KIEM-SO-01_" + h["route"]["id"], "tóm tắt có mã mặt hàng khách_tuyến")
        dung(v.get("may") and v.get("co_token") in (True, False), "cho biết máy nhận và có token hay chưa (không lộ token)", v.get("may"))
        env = dict(l.split("=", 1) for l in open(".env", encoding="utf-8").read().splitlines() if "=" in l and not l.startswith("#"))
        tk_kt = (env.get("EPL_ACC_CODE_TOKEN") or "").strip().strip('"')
        dung(not tk_kt or tk_kt not in json.dumps(v), "không trả token ra ngoài")
    finally:
        goi("/api/customers/" + cid, {"code": ma_cu or ""}, u="ketoan", method="PUT")
        print("  · đã trả mã khách về %r" % ma_cu)

    print()
    if LOI:
        print("TẠO SO: SAI %d bước — %s" % (len(LOI), "; ".join(LOI)))
        sys.exit(1)
    print("TẠO SO: ĐẠT")


if __name__ == "__main__":
    main()
