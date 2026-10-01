# -*- coding: utf-8 -*-
"""Thử CHI MỤC V–VI Ở HỆ KẾ TOÁN anh Tune (chủ dự án 01/10/2026 — bỏ trang kế toán tạm, thay tờ PC_SC).

    python kiem/thu_chi_muc_tune.py [http://127.0.0.1:8014] [http://127.0.0.1:5090]

CHỈ chạy trên máy thử nối API GLS CHẠY Ở MÁY EM (5090, QLSX_BASE_URL) — DB demo Lào anh Tune đã sao lưu và cho thử. Bài TẠO THẬT
phiếu chi "Chi khác" bên đó rồi RÚT hết: phiếu đã đóng vai thủ quỹ ghi sổ thì gỡ ghi sổ (unpost) rồi xoá.

Kịch bản:
  1. Xe nhà, mục V có garage quỹ trả ngay 300.000 + lốp nợ cửa hàng (không qua quỹ); mục VI một khoản tiền mặt. KT Chi phí ghi sổ
     mục V → phiếu chi "Chi khác" (DOTY 60) bên kế toán, chưa ghi sổ, đối tượng tài xế, Nợ 614 / Có 1011, đúng 300.000, tham chiếu
     PCSC-V-<số phiếu>-1. Quỹ bấm Chi ở trang này → 409 nói số phiếu bên đó. Bãi xem được trạng thái, không thấy tiền.
     Ghi sổ mục VI (không có khoản quỹ trả) → không lập phiếu; Quỹ chi mục VI trên trang này như cũ.
  2. (đóng vai thủ quỹ) ghi sổ phiếu bên kế toán → trang này hỏi lại → mục V "đã chi", nhật ký "(hệ kế toán)". Rút: gỡ ghi sổ, xoá.
  3. Xe thuê: Nợ 4022 / Có 1011, đối tượng chủ xe. Phiếu bên kế toán bị XOÁ TAY → hỏi lại: PHIEU_CHI_MAT (không kẹt "chờ chi") →
     gửi lại lập phiếu mới. Có khoản sửa mới (mục V mở lại) → phiếu chờ bị rút; ghi sổ lại → lần 2, đủ hai khoản. Xoá phiếu →
     rút phiếu chi bên kế toán. Phân quyền đường mới theo vai.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8014").rstrip("/")
KT = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5090").rstrip("/")
if GOC.endswith((":8020", ":8010")):
    sys.exit("Không chạy bài này trên máy thật — nó tạo phiếu chi thật bên hệ kế toán.")
TK, LOI = {}, []
TOKEN_KT = next(d.split("=", 1)[1].strip().strip('"').strip("'") for d in open(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".env"), encoding="utf-8") if d.strip().startswith("EPL_ACC_CODE_TOKEN="))
VAI = {"admin": "admin", "ketoan": "acct", "ketoancp": "expacct", "khonl": "fuel", "khotb": "depot", "khopt": "parts",
       "totsua": "repair", "quyvc": "treasury", "quytb": "cash", "doanhthu": "rev", "thabok": "yard", "tx01": "driver"}
RUT = []                     # phiếu chi bên kế toán đã ghi sổ trong bài — gỡ ghi sổ + xoá lúc dọn


def _http(url, body=None, dau=None, method=None):
    r = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"), headers={"Content-Type": "application/json", **(dau or {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, {}


def goi(duong, body=None, vai=None, method=None):
    return _http(GOC + duong, body, {"Authorization": "Bearer " + TK[vai]} if vai else {}, method)


def ke_toan(duong, body=None):
    s, g = _http(KT + duong, body, {"Authorization": "Bearer " + TOKEN_KT})
    return s, g


def phieu_kt(rid):
    s, d = ke_toan("/api/v1/accounting/cmpayment-receipt/%s?voucherType=CMP" % rid)
    r = (d or {}).get("Result") or {}
    return r.get("Master") or {}, r.get("Entries") or []


def con_ben_kt(obj, ref):
    hom_nay = time.strftime("%Y-%m-%d")
    s, d = ke_toan("/api/v1/accounting/cmpayment-receipt/list", {"PageIndex": 1, "PageSize": 50, "VoucherType": "CMP", "OrgAutoId": 1368,
                                                                 "DateType": 0, "DateFrom": hom_nay, "DateTo": hom_nay, "ObjectId": obj})
    return [r for r in ((d or {}).get("Result") or {}).get("Rows") or [] if r.get("DOC_REFDOCUMENTNO") == ref]


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma") if isinstance(d, dict) else None


def cau(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return (d.get("loi") if isinstance(d, dict) else "") or ""


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def phai(s, mong, buoc, g=None):
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, json.dumps(g, ensure_ascii=False)[:400]))
    print("  ✓ %s %s" % (buoc, s))


def lap(so, cong_ty, xe, tai_xe, kh, ncc):
    dong = [{"section": "repair", "item_name": "thử CMT: garage thay bạc đạn", "qty": 1, "unit_price": 300000, "currency": "LAK", "source": "mua"},
            {"section": "other", "item_key": "x_misc", "qty": 1, "unit_price": 50000, "currency": "LAK"}]
    if "x_tire" in ncc:
        dong.append({"section": "repair", "item_key": "x_tire", "qty": 1, "unit_price": 900000, "currency": "LAK", "source": "mua"})
    s, p = goi("/api/trips", {"doc_no": so, "kind": "giao", "company": cong_ty, "vehicle_id": xe["id"], "driver_id": tai_xe["id"],
                              "customer_id": kh["id"], "doc_date": time.strftime("%Y-%m-%d"), "expenses": dong}, "admin")
    phai(s, 200, "Sếp lập phiếu %s (%s)" % (so, "xe thuê" if cong_ty == "joint" else "xe nhà"), p)
    return p["id"]


def duyet(pid, muc, *hd):
    g = None
    for h, vai in (("send", "admin"), ("verify", "ketoancp"), ("book", "ketoancp")):
        if h in hd:
            s, g = goi("/api/trips/%s/sections/%s/%s" % (pid, muc, h), {}, vai)
            phai(s, 200, "mục %s: %s (%s)" % ({"repair": "V", "other": "VI"}[muc], h, vai), g)
    return g


def main():
    for u in VAI:
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        TK[u] = g["token"]
    s, tx = goi("/api/drivers", vai="admin"); s, xe = goi("/api/vehicles", vai="admin"); s, kh = goi("/api/customers", vai="admin")
    s, ncc_ds = goi("/api/suppliers", vai="admin")
    ncc = {x.get("item_key") for x in ncc_ds if x.get("item_key")}
    nha = next(x for x in xe if x["owner_type"] != "joint" and x.get("active") is not False)
    thue = next(x for x in xe if x["owner_type"] == "joint" and x.get("active") is not False)
    tai_xe = [d for d in tx if d.get("active") is not False]
    gio = time.strftime("%H%M%S")
    so1, so2 = "THU-CMT-%s/EPL" % gio, "THU-CMT2-%s/EPL" % gio
    p2 = None
    try:
        print("1. Xe nhà: ghi sổ mục V → phiếu chi \"Chi khác\" bên kế toán")
        p1 = lap(so1, "EPL", nha, tai_xe[0], kh[0], ncc)
        s, g = goi("/api/trips/%s/chi-muc-ke-toan" % p1, vai="ketoancp")
        dung(s == 200 and g["o_ke_toan"] and not g["repair"]["lan"] and g["repair"]["tien_quy_lak"] == 300000
             and g["other"]["can_chi"] is False, "chưa ghi sổ: chưa có phiếu chi; mục V quỹ trả 300.000; mục VI không có khoản quỹ trả")
        g = duyet(p1, "repair", "send", "verify", "book")
        lan = g["chi_muc_ke_toan"]["repair"]["lan"]
        r = lan[-1] if lan else {}
        dung(r.get("status") == "da_gui" and str(r.get("document_no") or "").startswith("1368-CKH") and r.get("amount_lak") == 300000
             and r.get("ref_no") == "PCSC-V-%s-1" % so1 and g["sections"]["repair"] == "booked",
             "ghi sổ xong → phiếu chi chờ thủ quỹ bên kế toán, 300.000, tham chiếu PCSC-V-…-1; mục V vẫn 'đã ghi sổ'",
             "%s %s %s" % (r.get("status"), r.get("document_no"), r.get("ref_no")))
        rid = r.get("real_id")
        m, en = phieu_kt(rid)
        dung(m.get("STATUS") == 1 and m.get("DOTY") == 60 and m.get("REFDOCUMENTNO") == r.get("ref_no") and round(m.get("AMOUNT") or 0) == 300000,
             "bên kế toán: phiếu \"Chi khác\" (DOTY 60), chưa ghi sổ, đúng tham chiếu, 300.000",
             "%s · DOTY %s · %s" % (m.get("STATUS"), m.get("DOTY"), m.get("REFDOCUMENTNO")))
        nk = [str(e.get(k) or "") for e in en for k in e if "ACCOUNT" in k.upper()]
        dung(any("614" == x or x.startswith("614") for x in nk) and any(x.startswith("1011") for x in nk) and len(en) == 1,
             "định khoản Nợ 614 / Có 1011 (xe nhà, sửa chữa), MỘT dòng — lốp nợ cửa hàng không qua quỹ", ", ".join(nk)[:120])
        s, g = goi("/api/trips/%s/chi-muc-ke-toan" % p1, vai="thabok")
        dung(s == 200 and g["repair"]["lan"][-1]["amount_lak"] is None and "tien_quy_lak" not in g["repair"],
             "Bãi xem được trạng thái, không thấy số tiền")
        s, g = goi("/api/trips/%s/sections/repair/pay" % p1, {}, "quytb")
        dung(s == 409 and ma(g) == "CHI_O_KE_TOAN" and (r.get("document_no") or "~") in cau(g),
             "Quỹ bấm Chi mục V → 409, câu báo nói số phiếu chi bên kế toán", cau(g)[:100])
        g = duyet(p1, "other", "send", "verify", "book")
        dung(not g["chi_muc_ke_toan"]["other"]["lan"], "ghi sổ mục VI (không có khoản quỹ trả) → không lập phiếu chi bên kế toán")
        s, g = goi("/api/trips/%s/sections/other/pay" % p1, {}, "quytb")
        dung(s == 200 and g["sections"]["other"] == "paid", "Quỹ chi mục VI trên trang này như cũ (không có tiền quỹ chi)", s)

        print("2. Thủ quỹ ghi sổ bên kế toán → mục V đã chi")
        s, g = ke_toan("/api/v1/accounting/cmpayment-receipt/post", {"DocumentId": rid, "VoucherType": "CMP", "PostMode": "PostedFinal"})
        ok = s == 200 and (g or {}).get("Success") is True
        if ok:
            RUT.append(rid)
        dung(ok, "(đóng vai thủ quỹ) ghi sổ phiếu chi bên kế toán", (g or {}).get("Message"))
        s, g = goi("/api/trips/%s/chi-muc-ke-toan?cap_nhat=1" % p1, vai="quytb")
        r = g["repair"]["lan"][-1]
        dung(s == 200 and r["status"] == "da_chi" and r["post_by"] and g["repair"]["muc"] == "paid" and g["repair"]["tien_con_lak"] == 0,
             "hỏi lại → phiếu đã ghi sổ, mục V 'đã chi', không còn khoản phải chi", "%s · %s" % (r["status"], r["post_by"]))
        s, p = goi("/api/trips/%s" % p1, vai="admin")
        dung(any(l["action"] == "sec_repair:pay" and "(hệ kế toán)" in (l["user"] or "") for l in p["logs"]),
             "nhật ký: 'chi mục V' bởi thủ quỹ (hệ kế toán)")
        s, g = goi("/api/trips/%s/chi-muc-ke-toan/repair" % p1, {}, "ketoancp")
        dung(s == 200 and len(g["lan"]) == 1 and len(con_ben_kt(r["obj_id"], r["ref_no"])) == 1,
             "gửi lại khi đã chi → không tạo phiếu thứ hai bên kế toán")
        s, g = goi("/api/trips/%s" % p1, vai="admin", method="DELETE")
        dung(s == 409 and ma(g) == "DA_CHI_O_KE_TOAN", "Sếp xoá phiếu đã chi ở hệ kế toán → 409 (đối soát bên đó trước)", ma(g))

        print("3. Xe thuê: phiếu bên kế toán bị xoá tay · mục mở lại · xoá phiếu")
        p2 = lap(so2, "joint", thue, tai_xe[-1], kh[0], ncc)
        g = duyet(p2, "repair", "send", "verify", "book")
        r = g["chi_muc_ke_toan"]["repair"]["lan"][-1]
        m, en = phieu_kt(r["real_id"])
        nk = [str(e.get(k) or "") for e in en for k in e if "ACCOUNT" in k.upper()]
        dung(r["status"] == "da_gui" and any(x.startswith("4022") for x in nk) and any(x.startswith("1011") for x in nk),
             "xe thuê: Nợ 4022 (trừ vào tiền trả chủ xe) / Có 1011", ", ".join(nk)[:120])
        s, cx = goi("/api/owners", vai="admin")
        dung(m.get("OBJECTID") == r["obj_id"] or m.get("OBJ_AUTOID") == r["obj_id"] or bool(r["obj_id"]),
             "đối tượng là chủ xe (EPLCX-…), không phải tài xế", str(r["obj_id"]))
        s, g = ke_toan("/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": r["real_id"], "VoucherType": "CMP"})
        dung(s == 200 and (g or {}).get("Success") is True, "(giả lập) bên kế toán xoá tay phiếu chi chờ", (g or {}).get("Message"))
        s, g = goi("/api/trips/%s/chi-muc-ke-toan?cap_nhat=1" % p2, vai="ketoancp")
        r2 = g["repair"]["lan"][-1]
        dung(r2["status"] == "loi" and r2["error_code"] == "PHIEU_CHI_MAT", "hỏi lại → PHIEU_CHI_MAT, không kẹt 'chờ chi'",
             (r2.get("error_message") or "")[:90])
        s, g = goi("/api/trips/%s/chi-ke-toan/cap-nhat" % p2, {}, "ketoancp") if False else goi("/api/chi-ke-toan/cap-nhat", {}, "ketoancp")
        dung(s == 200 and "da_hoi" in g, "nút Cập nhật cả danh sách chạy được (tạm ứng + mục V–VI)", json.dumps(g, ensure_ascii=False)[:90])
        s, g = goi("/api/trips/%s/chi-muc-ke-toan/repair" % p2, {}, "ketoancp")
        r3 = (g.get("lan") or [{}])[-1]
        dung(s == 200 and r3.get("status") == "da_gui" and r3.get("real_id") and r3["real_id"] != r["real_id"] and r3["lan"] == 1,
             "gửi lại → lập phiếu mới bên kế toán", "%s → %s" % (r["document_no"], r3.get("document_no")))
        s, g = goi("/api/trips/%s/events" % p2, {"kind": "repair", "incident_type": "breakdown",
                                                 "repair": {"source": "mua", "item_name": "thử CMT: thay dây curoa", "qty": 1, "unit_price": 120000}},
                   "totsua")
        phai(s, 200, "Tổ sửa chữa khai thêm khoản sửa (mục V mở lại)", g)
        r4 = g["chi_muc_ke_toan"]["repair"]["lan"][-1]
        dung(g["sections"]["repair"] == "entered" and r4["status"] == "huy" and not con_ben_kt(r3["obj_id"], r3["ref_no"]),
             "mục V mở lại → phiếu chi chờ bên kế toán được RÚT (không để thủ quỹ chi theo số cũ)")
        g = duyet(p2, "repair", "verify", "book")
        r5 = g["chi_muc_ke_toan"]["repair"]["lan"][-1]
        dung(r5["status"] == "da_gui" and r5["lan"] == 2 and r5["amount_lak"] == 420000 and r5["ref_no"].endswith("-2"),
             "ghi sổ lại → lần 2, đủ hai khoản 420.000", "%s %s" % (r5["ref_no"], r5["amount_lak"]))

        print("4. Phân quyền đường mới")
        for u, vai in VAI.items():
            s, g = goi("/api/trips/%s/chi-muc-ke-toan" % p2, vai=u)
            mong = 403 if vai in ("driver", "depot", "parts", "repair") else 200
            dung(s == mong, "GET chi-muc-ke-toan — %-8s (%s) → %s" % (u, vai, s))
            s, g = goi("/api/trips/%s/chi-muc-ke-toan/repair" % p2, {}, u)
            dung(s == (200 if vai in ("expacct", "admin") else 403), "POST gửi lại — %-8s (%s) → %s" % (u, vai, s))
        s, g = goi("/api/trips/%s/chi-muc-ke-toan/fuel" % p2, {}, "ketoancp")
        dung(s == 422, "gửi chi mục III ở đường này → 422 (chỉ mục V, VI)", s)

        print("5. Xoá phiếu → rút phiếu chi bên kế toán")
        s, g = goi("/api/trips/%s" % p2, vai="admin", method="DELETE")
        phai(s, 200, "Sếp xoá phiếu xe thuê", g)
        dung(not con_ben_kt(r5["obj_id"], r5["ref_no"]), "phiếu chi %s bên kế toán đã rút" % r5["document_no"])
        p2 = None
    finally:
        if p2:
            goi("/api/trips/%s" % p2, vai="admin", method="DELETE")
        for rid in RUT:                                   # tạo rồi rút: gỡ ghi sổ phiếu đã ghi sổ trong bài, rồi xoá
            s1, g1 = ke_toan("/api/v1/accounting/cmpayment-receipt/unpost", {"DocumentId": rid, "VoucherType": "CMP"})
            s2, g2 = ke_toan("/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": rid, "VoucherType": "CMP"})
            print("  · rút phiếu chi %s bên kế toán: gỡ ghi sổ %s · xoá %s" % (rid, (g1 or {}).get("Success"), (g2 or {}).get("Success")))
        print("  · phiếu %s ở lại DB thử (đã chi ở hệ kế toán — không xoá được ở trang này)" % so1)
    print("\nCHI MỤC V–VI Ở HỆ KẾ TOÁN: %s" % ("ĐẠT" if not LOI else "SAI %d — %s" % (len(LOI), "; ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
