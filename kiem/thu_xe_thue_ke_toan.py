# -*- coding: utf-8 -*-
"""Thử LUỒNG XE THUÊ NGOÀI (xe liên kết) nối hệ kế toán anh Tune (01/10).

    python kiem/thu_xe_thue_ke_toan.py [http://127.0.0.1:8011] [http://127.0.0.1:5090]

CHỈ chạy trên máy thử 8011 (bản sao DB) nối API GLS CHẠY Ở MÁY EM (5090, DB demo Lào anh Tune đã sao lưu).

1. Tạm ứng xe thuê: ghi sổ mục IV → phiếu chi bên kế toán đứng tên CHỦ XE (nhà cung cấp EPLCX-…), Nợ 4022 / Có 1011.
   Danh mục tài khoản bên anh Tune CHƯA có 4022 → bên đó từ chối; bài kiểm câu lỗi hiện rõ trên phiếu và chủ xe đã có đối
   tượng nhà cung cấp bên đó. Khi mở mã 4022 thì bước này phải ra phiếu chi chờ (bài in rõ đang ở trường hợp nào).
2. Trả chủ xe: màn Xe liên kết thấy phiếu xe thuê đã khoá chờ trả; Bãi không xem được; đề nghị trả với phiếu sai bị chặn;
   lập đề nghị → phiếu chi "Chi khác" bên kế toán (hoặc câu lỗi rõ khi bên đó thiếu tiền tệ / mã 4022); phiếu đang nằm đề
   nghị thì không mở khoá được và không vào đề nghị khác; bỏ đề nghị → phiếu về lại chờ trả.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
KT = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5090").rstrip("/")
if GOC.endswith((":8020", ":8010")):
    sys.exit("Không chạy bài này trên máy thật.")
TK, LOI = {}, []
TOKEN_KT = next(d.split("=", 1)[1].strip().strip('"').strip("'") for d in open(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".env"), encoding="utf-8") if d.strip().startswith("EPL_ACC_CODE_TOKEN="))


def _http(url, body=None, dau=None, method=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"), headers={"Content-Type": "application/json", **(dau or {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def goi(duong, body=None, vai=None, method=None):
    return _http(GOC + duong, body, {"Authorization": "Bearer " + TK[vai]} if vai else None, method)


def ke_toan(duong, body=None):
    return _http(KT + duong, body, {"Authorization": "Bearer " + TOKEN_KT})


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return (d or {}).get("ma", "") if isinstance(d, dict) else ""


def cau(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return (d or {}).get("loi", "") if isinstance(d, dict) else ""


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def co_ma_4022():
    s, g = ke_toan("/api/v1/accounting/cmpayment-receipt/country-accounts?countryId=11")
    return any(str(a.get("AccCode") or a.get("ACC_CODE")) == "4022" for a in ((g or {}).get("Result") or []))


def main():
    for u in ("thabok", "ketoan", "ketoancp", "quytb", "admin"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]
    co4022 = co_ma_4022()
    print("· danh mục bên anh Tune %s mã 4022" % ("ĐÃ CÓ" if co4022 else "CHƯA CÓ"))
    s, xe = goi("/api/vehicles", vai="thabok")
    s, tx = goi("/api/drivers", vai="thabok")
    s, kh = goi("/api/customers", vai="thabok")
    thue = next(x for x in xe if x.get("owner_type") == "joint" and x.get("active") is not False and x.get("owner_id"))

    print("1. Tạm ứng xe thuê → phiếu chi đứng tên chủ xe")
    so = "THU-XT-%s/EPL" % time.strftime("%H%M%S")
    s, p = goi("/api/trips", {"doc_no": so, "kind": "giao", "company": "joint", "vehicle_id": thue["id"], "owner_id": thue["owner_id"],
                              "driver_id": tx[0]["id"], "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"),
                              "expenses": [{"section": "travel", "item_key": "x_vn", "qty": 1, "unit_price": 300000, "currency": "LAK"}]}, "admin")
    dung(s == 200, "lập phiếu xe thuê %s (chủ xe %s)" % (so, (p or {}).get("owner_name")), "%s %s" % (s, ma(p)))
    pid = p["id"]
    goi("/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "thabok")
    for hd, vai in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/travel/%s" % (pid, hd), {}, vai)
        dung(s == 200, "mục IV: %s (%s)" % (hd, vai), "%s %s" % (s, ma(g)))
    ct = g.get("chi_tam_ung") or {}
    s, ncc = ke_toan("/api/v1/master-data/suppliers/list", {"PageIndex": 1, "ObjKey": "EPLCX-" + thue["owner_id"]})
    dong_ncc = [x for x in (((ncc or {}).get("Result") or {}).get("Data") or []) if x.get("ObjectNo") == "EPLCX-" + thue["owner_id"]]
    dung(len(dong_ncc) == 1 and ct.get("obj_id") == dong_ncc[0].get("ObjId"), "đối tượng phiếu chi là CHỦ XE (nhà cung cấp EPLCX-…) bên kế toán",
         "%s" % (dong_ncc[0].get("Name") if dong_ncc else "không thấy"))
    if co4022:
        dung(ct.get("status") == "da_gui", "có 4022 → phiếu chi chờ thủ quỹ", "%s %s" % (ct.get("status"), ct.get("document_no")))
    else:
        dung(ct.get("status") == "loi" and ct.get("error_message"), "chưa có 4022 → bên kế toán từ chối, câu lỗi nằm trên phiếu",
             (ct.get("error_message") or "")[:110])
    s, g = goi("/api/trips/%s/chi-ke-toan" % pid, vai="ketoancp")
    body = json.loads(json.dumps(g))
    s, d = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
    dung(s == 200, "xoá phiếu thử (rút phiếu chi chờ nếu có)", "%s %s" % (s, ma(d)))

    print("2. Trả chủ xe qua hệ kế toán")
    s, ds = goi("/api/owners", vai="ketoan")
    chu = None
    for o in ds:
        s, t = goi("/api/owners/%s/tra-ke-toan" % o["id"], vai="ketoan")
        if s == 200 and t.get("cho"):
            chu, tt = o, t
            break
    dung(chu is not None, "có chủ xe với phiếu đã khoá chờ trả", chu["name"] if chu else "")
    if not chu:
        return ket_thuc()
    s, g = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="thabok")
    dung(s == 403, "Bãi xem tiền trả chủ xe → 403", s)
    s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": [tt["cho"][0]["id"]]}, "quytb")
    dung(s == 403, "Quỹ lập đề nghị trả → 403 (KT Thu/Chi VC · Sếp)", s)
    s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": ["khong-co"]}, "ketoan")
    dung(s == 409 and ma(g) == "PHIEU_KHONG_HOP_LE", "phiếu không còn chờ trả → 409", ma(g))
    duong = [x for x in tt["cho"] if (x["tra_chu_xe"] or 0) > 0]
    am = [x for x in tt["cho"] if (x["tra_chu_xe"] or 0) <= 0]
    if am:
        s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": [am[0]["id"]]}, "ketoan")
        dung(s == 409 and ma(g) == "KHONG_CON_PHAI_TRA", "phiếu EPL đã ứng / trừ nhiều hơn tiền thuê (còn trả ≤ 0) → không lập phiếu chi",
             "%s %s" % (am[0]["doc_no"], am[0]["tra_chu_xe"]))
    if not duong:
        print("  · không có phiếu còn phải trả > 0 trên dữ liệu thử — bỏ qua bước lập đề nghị")
        return ket_thuc()
    x = duong[0]
    s, r = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": [x["id"]], "phuong_thuc": "bank"}, "ketoan")
    if s == 200:
        dung(r.get("status") == "da_gui" and r.get("document_no"), "lập đề nghị → phiếu chi bên kế toán chờ chi", "%s %s %s" % (r.get("document_no"), r.get("amount"), r.get("currency")))
        rid = r["id"]
    else:
        dung(s in (422, 502) and cau(g := r), "bên kế toán chưa nhận được (thiếu tiền tệ / mã 4022) → câu lỗi rõ", cau(r)[:120])
        s2, t2 = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="ketoan")
        loi = [d for d in t2["de_nghi"] if d["status"] == "loi"]
        dung(bool(loi) and x["id"] in loi[0]["trip_ids"] and any(c["id"] == x["id"] for c in t2["cho"]),
             "đề nghị hỏng được ghi lại (gửi lại được), phiếu vẫn ở danh sách chờ trả", loi[0]["ref_no"] if loi else "")
        rid = loi[0]["id"] if loi else None
    if rid and s == 200:
        # Sếp: bỏ qua chặn hoá đơn / đề nghị thu / SO — nhưng đề nghị trả chủ xe vẫn chặn (số trả tính từ phiếu đã khoá)
        s, g = goi("/api/trips/%s/mo-khoa" % x["id"], {}, "admin")
        dung(s == 409 and ma(g) == "TRONG_DE_NGHI_TRA_CHU_XE", "phiếu đang nằm đề nghị trả → không mở khoá được (kể cả Sếp)", ma(g))
        s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": [x["id"]]}, "ketoan")
        dung(s == 409 and ma(g) == "PHIEU_KHONG_HOP_LE", "phiếu đã nằm đề nghị → không vào đề nghị thứ hai", ma(g))
    if rid:
        s, g = goi("/api/chi-chu-xe/%s/huy" % rid, {}, "ketoan")
        dung(s == 200 and g.get("status") == "huy", "bỏ đề nghị (rút phiếu chi chưa ghi sổ bên kế toán)", "%s %s" % (s, ma(g)))
        s, t3 = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="ketoan")
        dung(any(c["id"] == x["id"] for c in t3["cho"]), "phiếu về lại danh sách chờ trả")
    ket_thuc()


def ket_thuc():
    print("\nXE THUÊ NỐI KẾ TOÁN: %s" % ("ĐẠT" if not LOI else "SAI %d — %s" % (len(LOI), "; ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
