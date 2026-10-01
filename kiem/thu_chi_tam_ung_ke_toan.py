# -*- coding: utf-8 -*-
"""Thử CHI TẠM ỨNG Ở HỆ KẾ TOÁN anh Tune (chủ dự án chốt 01/10/2026: "chi thật là anh Tune xong update trạng thái về").

    python kiem/thu_chi_tam_ung_ke_toan.py [http://127.0.0.1:8011] [http://127.0.0.1:5090]

CHỈ chạy trên máy thử: trang điều xe 8011 (bản sao DB) nối API GLS chạy Ở MÁY EM (5090, QLSX_BASE_URL) — DB demo Lào anh Tune
đã sao lưu và cho thử. Bài này TẠO THẬT một phiếu chi bên đó (số tham chiếu PTU-THU-CK-…) và đóng vai thủ quỹ ghi sổ nó.

Kịch bản: lập phiếu có 580.000 LAK tiền mặt tài xế cầm đi → Bãi in tờ tạm ứng → gửi, kiểm, GHI SỔ mục IV → phiếu chi "Chi trước"
sang hệ kế toán (chưa ghi sổ) → Quỹ bấm chi mục IV / quét QR trên trang điều xe bị chặn → tài xế bấm Xuất phát bị chặn, câu báo
nói số phiếu chi bên đó → thủ quỹ GHI SỔ ở hệ kế toán → tài xế bấm Xuất phát được ngay (trang điều xe hỏi lại) → mục IV đã chi,
tờ tạm ứng đã cấp → gửi lại không tạo phiếu thứ hai.
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
    sys.exit("Không chạy bài này trên máy thật — nó tạo phiếu chi thật bên hệ kế toán.")
TK, LOI = {}, []
DONG = [("x_water", 60000), ("x_vn", 430000), ("x_chip_lao", 620000), ("x_chip_vn", 1500000), ("x_trip", 1800000), ("x_phone", 150000)]
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
    s, g = _http(KT + duong, body, {"Authorization": "Bearer " + TOKEN_KT})
    return s, g


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


def phai(s, mong, buoc, g=None):
    dung(s == mong, buoc, "%s %s" % (s, ma(g)))
    if s != mong:
        raise SystemExit("DỪNG: %s → %s %s" % (buoc, s, json.dumps(g, ensure_ascii=False)[:400]))


def main():
    for u in ("thabok", "ketoancp", "quytb", "tx01", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        TK[u] = g["token"]
    s, toi = goi("/api/toi", vai="tx01")
    s, tx = goi("/api/drivers", vai="thabok")
    s, xe = goi("/api/vehicles", vai="thabok")
    s, kh = goi("/api/customers", vai="thabok")
    tai_xe = next(d for d in tx if d["name"] == toi["full_name"])
    nha = next(x for x in xe if x["owner_type"] != "joint" and x.get("active") is not False)
    so = "THU-CK-%s/EPL" % time.strftime("%H%M%S")

    print("1. Lập phiếu có tiền mặt tài xế cầm đi")
    s, p = goi("/api/trips", {"doc_no": so, "kind": "giao", "company": "EPL", "vehicle_id": nha["id"], "driver_id": tai_xe["id"],
                              "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"),
                              "expenses": [{"section": "travel", "item_key": k, "qty": 1, "unit_price": g, "currency": "LAK"} for k, g in DONG]},
               "admin")
    phai(s, 200, "lập phiếu %s cho tài xế %s (6 khoản mục IV)" % (so, toi["full_name"]), p)
    pid = p["id"]
    s, v = goi("/api/trips/%s/vouchers" % pid, {"kind": "advance"}, "thabok")
    phai(s, 200, "Bãi in tờ đề nghị tạm ứng", v)
    vid = v[0]["id"]

    print("2. Ghi sổ mục IV → phiếu chi sang hệ kế toán")
    s, g = goi("/api/trips/%s/chi-ke-toan" % pid, vai="ketoancp")
    dung(s == 200 and g.get("o_ke_toan") is True and not g.get("status"), "chưa ghi sổ thì chưa có phiếu chi bên kế toán", g.get("status"))
    for hd, vai in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/travel/%s" % (pid, hd), {}, vai)
        phai(s, 200, "mục IV: %s (%s)" % (hd, vai), g)
    ct = g.get("chi_tam_ung") or {}
    dung(ct.get("status") == "da_gui" and str(ct.get("document_no") or "").startswith("1368-CTR") and round(ct.get("amount_lak") or 0) == 580000,
         "ghi sổ xong → có phiếu chi bên kế toán, chờ chi, 580.000 LAK", "%s %s %s" % (ct.get("status"), ct.get("document_no"), ct.get("amount_lak")))
    rid = ct.get("real_id")
    s, d = ke_toan("/api/v1/accounting/cmpayment-receipt/%s?voucherType=CMP" % rid)
    m = ((d or {}).get("Result") or {}).get("Master") or {}
    e = (((d or {}).get("Result") or {}).get("Entries") or [{}])[0]
    dung(m.get("STATUS") == 1 and m.get("DOTY") == 59 and m.get("REFDOCUMENTNO") == "PTU-" + so and round(m.get("AMOUNT") or 0) == 580000,
         "bên kế toán: phiếu \"Chi trước\", chưa ghi sổ, tham chiếu đúng tờ PTU, 580.000",
         "%s · DOTY %s · %s" % (m.get("STATUS"), m.get("DOTY"), m.get("REFDOCUMENTNO")))
    nk = [str(e.get(k) or "") for k in e if "ACCOUNT" in k.upper() or k.upper() in ("DEBITACCOUNT", "CREDITACCOUNT")]
    dung(any("1601" in x for x in nk) and any("1011" in x for x in nk), "định khoản Nợ 1601 / Có 1011 (xe nhà: tạm ứng nhân viên)", ", ".join(nk)[:120])
    s, g = goi("/api/trips/%s/chi-ke-toan" % pid, vai="thabok")
    dung(s == 200 and g.get("amount_lak") is None and g.get("status") == "da_gui", "Bãi xem được trạng thái, không thấy số tiền")

    print("3. Trang điều xe không chi tạm ứng nữa")
    s, g = goi("/api/trips/%s/sections/travel/pay" % pid, {}, "quytb")
    dung(s == 409 and ma(g) == "CHI_O_KE_TOAN" and ct.get("document_no", "~") in cau(g), "Quỹ bấm chi mục IV → 409, câu báo nói số phiếu chi bên kế toán", cau(g)[:90])
    s, g = goi("/api/vouchers/%s/cap" % vid, {}, "quytb")
    dung(s == 409 and ma(g) == "CHI_O_KE_TOAN", "Quỹ quét QR tờ tạm ứng → 409 CHI_O_KE_TOAN", ma(g))
    s, g = goi("/api/trips/%s/chi-ke-toan" % pid, {}, "thabok")
    dung(s == 403, "Bãi bấm gửi phiếu chi → 403 (KT Chi phí · Sếp)", s)
    s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "transit"}, "tx01")
    dung(s == 409 and ma(g) == "CHUA_NHAN_TAM_UNG" and ct.get("document_no", "~") in cau(g),
         "tài xế bấm Xuất phát khi thủ quỹ chưa chi → 409, nói số phiếu chi chờ ghi sổ", cau(g)[:90])

    print("4. Thủ quỹ chi và ghi sổ ở hệ kế toán → tài xế xuất phát được")
    s, g = ke_toan("/api/v1/accounting/cmpayment-receipt/post", {"DocumentId": rid, "VoucherType": "CMP", "PostMode": "PostedFinal"})
    dung(s == 200 and (g or {}).get("Success") is True, "(đóng vai thủ quỹ) ghi sổ phiếu chi bên kế toán", (g or {}).get("Message"))
    s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "transit"}, "tx01")
    phai(s, 200, "tài xế bấm Xuất phát → được ngay (trang điều xe hỏi lại hệ kế toán)", g)
    s, p = goi("/api/trips/%s" % pid, vai="admin")
    ct = p.get("chi_tam_ung") or {}
    dung(p["sections"]["travel"] == "paid" and ct.get("status") == "da_chi" and ct.get("post_by"),
         "mục IV đã chi · phiếu chi bên kế toán đã ghi sổ, có người ghi sổ", "%s · %s" % (ct.get("status"), ct.get("post_by")))
    dung(any(l["action"] == "sec_travel:pay" and "(hệ kế toán)" in (l["user"] or "") for l in p["logs"]), "nhật ký phiếu: 'chi mục IV' bởi thủ quỹ (hệ kế toán)")
    s, ds = goi("/api/trips/%s/vouchers" % pid, vai="ketoancp")
    tu = next(x for x in ds if x["kind"] == "advance")
    dung(tu["status"] == "da_cap" and "(hệ kế toán)" in (tu["granted_by"] or ""), "tờ tạm ứng đã cấp (Tất toán đếm là đã ứng)", tu["granted_by"])
    s, g = goi("/api/trips/%s/chi-ke-toan" % pid, {}, "ketoancp")
    s2, dsk = ke_toan("/api/v1/accounting/cmpayment-receipt/list", {"PageIndex": 1, "PageSize": 50, "VoucherType": "CMP", "OrgAutoId": 1368,
                                                                    "DateType": 0, "DateFrom": time.strftime("%Y-%m-%d"), "DateTo": time.strftime("%Y-%m-%d"),
                                                                    "ObjectId": (p.get("chi_tam_ung") or {}).get("obj_id") or None})
    cung = [r for r in ((dsk or {}).get("Result") or {}).get("Rows") or [] if r.get("DOC_REFDOCUMENTNO") == "PTU-" + so]
    dung(s == 200 and g.get("status") == "da_chi" and len(cung) == 1, "KT Chi phí bấm gửi lại → không tạo phiếu thứ hai bên kế toán", "%d phiếu" % len(cung))
    s, g = goi("/api/chi-ke-toan/cap-nhat", {}, "ketoancp")
    dung(s == 200 and "da_hoi" in g, "nút Cập nhật cả danh sách chạy được", json.dumps(g, ensure_ascii=False))
    s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
    dung(s == 409 and ma(g) == "DA_CHI_O_KE_TOAN", "Sếp xoá phiếu đã chi ở hệ kế toán → 409 (đối soát bên đó trước)", ma(g))
    print("  · phiếu %s và phiếu chi %s bên kế toán ở lại DB thử (đã ghi sổ — không xoá)" % (so, ct.get("document_no")))

    print("5. Xoá phiếu khi phiếu chi bên kế toán còn chờ → rút phiếu chi bên đó")
    so2 = "THU-CK2-%s/EPL" % time.strftime("%H%M%S")
    s, p2 = goi("/api/trips", {"doc_no": so2, "kind": "giao", "company": "EPL", "vehicle_id": nha["id"], "driver_id": tai_xe["id"],
                               "customer_id": kh[0]["id"], "doc_date": time.strftime("%Y-%m-%d"),
                               "expenses": [{"section": "travel", "item_key": "x_vn", "qty": 1, "unit_price": 120000, "currency": "LAK"}]}, "admin")
    phai(s, 200, "lập phiếu thứ hai %s (120.000 tiền mặt)" % so2, p2)
    goi("/api/trips/%s/vouchers" % p2["id"], {"kind": "advance"}, "thabok")
    for hd, vai in (("send", "thabok"), ("verify", "ketoancp"), ("book", "ketoancp")):
        s, g = goi("/api/trips/%s/sections/travel/%s" % (p2["id"], hd), {}, vai)
        phai(s, 200, "mục IV: %s (%s)" % (hd, vai), g)
    c2 = g.get("chi_tam_ung") or {}
    dung(c2.get("status") == "da_gui" and c2.get("real_id"), "có phiếu chi chờ bên kế toán", c2.get("document_no"))
    s, g = goi("/api/trips/%s" % p2["id"], vai="admin", method="DELETE")
    phai(s, 200, "Sếp xoá phiếu", g)
    s2, dsk = ke_toan("/api/v1/accounting/cmpayment-receipt/list", {"PageIndex": 1, "PageSize": 50, "VoucherType": "CMP", "OrgAutoId": 1368,
                                                                    "DateType": 0, "DateFrom": time.strftime("%Y-%m-%d"), "DateTo": time.strftime("%Y-%m-%d"),
                                                                    "ObjectId": c2.get("obj_id")})
    con = [r for r in ((dsk or {}).get("Result") or {}).get("Rows") or [] if r.get("DOC_REFDOCUMENTNO") == "PTU-" + so2]
    dung(not con, "phiếu chi %s bên kế toán đã được rút (không còn trong danh sách)" % c2.get("document_no"), "%d còn lại" % len(con))
    print("\nCHI TẠM ỨNG Ở HỆ KẾ TOÁN: %s" % ("ĐẠT" if not LOI else "SAI %d — %s" % (len(LOI), "; ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
