# -*- coding: utf-8 -*-
"""Thử TẤT TOÁN TÀI XẾ và TRẢ NHÀ CUNG CẤP nối hệ kế toán anh Tune (chủ dự án chốt 01/10: bỏ phần tiền trang kế toán tạm).

    python kiem/thu_tat_toan_tune.py [http://127.0.0.1:8013] [http://127.0.0.1:5090] [YYYY-MM]

CHỈ chạy trên máy thử (bản sao DB) nối API GLS CHẠY Ở MÁY EM (5090). Mọi phiếu chi / thu bài lập bên kế toán đều CHƯA ghi sổ
và được rút (xoá) ở cuối — như kiem/thu_xe_thue_ke_toan.py.

1. Các đường máy tiền của trang kế toán tạm đã gỡ → 404; đường cũ /api/owners/{id}/cong-no, /api/suppliers/{id}/payments → 404;
   đường kho (cap-phat, nguoi-mua, ty-gia, ma-ke-toan, xe) còn.
2. Tất toán: Bãi / KT Thu-Chi không xem / không chốt; KT Chi phí chốt một tài xế chênh dương → phiếu chi "Chi khác" (DOTY 60,
   Nợ 1601 / Có 1011, đối tượng nhân viên EPLTX-…) + QT_TU Nợ 625 / Có 1601 thành bút toán chờ; chốt lần hai bị chặn; hỏi lại;
   bỏ chốt → phiếu bên kế toán bị rút, bút toán huỷ. Một tài xế chênh âm → phiếu thu "Thu khác" (DOTY 17, Nợ 1011 / Có 1601).
3. Trả nhà cung cấp: công nợ (phát sinh − đã chi − chờ chi); Bãi không xem; KT Thu-Chi không lập; trả vượt nợ phải xác nhận;
   lập đề nghị → phiếu chi "Chi khác" (Nợ 4021 / Có 1021, đối tượng nhà cung cấp EPLNCC-…); số chờ chi trừ vào còn nợ; huỷ →
   phiếu bên kế toán bị rút, công nợ về như cũ.
"""
import json
import os
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8013").rstrip("/")
KT = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:5090").rstrip("/")
KY = sys.argv[3] if len(sys.argv) > 3 else "2026-09"
if GOC.endswith((":8020", ":8010", ":8001")):
    sys.exit("Không chạy bài này trên máy thật.")
TK, LOI = {}, []
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
    return dk


def phieu_ben_kt(real_id, vt):
    """Master + Entries của một phiếu bên kế toán; (None, câu lỗi) khi không đọc được (đã xoá)."""
    s, g = ke_toan("/api/v1/accounting/cmpayment-receipt/%s?voucherType=%s" % (real_id, vt))
    if s == 200 and isinstance(g, dict) and g.get("Success") and (g.get("Result") or {}).get("Master"):
        return g["Result"], None
    return None, (g or {}).get("Message") if isinstance(g, dict) else s


def ma_doi_tuong(duong, so):
    s, g = ke_toan("/api/v1/master-data/%s/list" % duong, {"PageIndex": 1, "ObjKey": so})
    return next((x.get("ObjId") for x in (((g or {}).get("Result") or {}).get("Data") or []) if x.get("ObjectNo") == so), None)


def kiem_phieu(pk, loai, vt, doty, no, co, tien, duong_dt, so_dt):
    kq, loi = phieu_ben_kt(pk["real_id"], vt)
    if not dung(kq is not None, "đọc được phiếu %s bên kế toán" % pk.get("document_no"), loi or ""):
        return
    m, e = kq["Master"], (kq.get("Entries") or [{}])[0]
    dung(m.get("DOTY") == doty and m.get("STATUS") not in (12, 13), "%s: %s loại %s, CHƯA ghi sổ" % (loai, vt, doty),
         "DOTY %s · STATUS %s" % (m.get("DOTY"), m.get("STATUS")))
    dung(e.get("ET_DEBTORACCOUNT") == no and e.get("ET_CREDITACCOUNT") == co and abs((e.get("ET_TOTALAMOUNT") or 0) - tien) < 0.5,
         "định khoản Nợ %s / Có %s · %s" % (no, co, format(round(tien), ",")),
         "%s / %s · %s" % (e.get("ET_DEBTORACCOUNT"), e.get("ET_CREDITACCOUNT"), e.get("ET_TOTALAMOUNT")))
    oid = ma_doi_tuong(duong_dt, so_dt)
    dung(oid and m.get("SUPPLIER") == oid == pk.get("obj_id"), "đối tượng %s bên kế toán" % so_dt, e.get("OBJ_NAME") or "")


def main():
    for u in ("thabok", "ketoan", "ketoancp", "quytb", "admin"):
        TK[u] = goi("/api/dang-nhap", {"username": u, "password": "1234"})[1]["token"]

    print("1. Đường tiền của trang kế toán tạm đã gỡ")
    for d in ("doanh-thu/phieu", "doanh-thu/so-lieu", "doanh-thu/cho-gop", "chu-xe", "chu-xe/x/cho-tra", "chu-xe/phieu",
              "xe-lien-ket", "tien-tai-xe", "tat-toan", "tat-toan/x", "ncc", "ncc/x", "can-tru", "thang-moi-nhat"):
        s, g = goi("/api/lien-thong/" + d)
        dung(s == 404, "GET /api/lien-thong/%s → 404" % d, s)
    for d in ("doanh-thu/xuat", "doanh-thu/bo-xuat", "doanh-thu/da-thu", "chu-xe/tra", "chu-xe/bo-tra"):
        s, g = goi("/api/lien-thong/" + d, {})
        dung(s == 404, "POST /api/lien-thong/%s → 404" % d, s)
    s, g = goi("/api/owners/x/cong-no", vai="admin"); dung(s == 404, "đường cũ /api/owners/{id}/cong-no → 404", s)
    s, g = goi("/api/suppliers/x/payments", vai="admin"); dung(s == 404, "đường cũ /api/suppliers/{id}/payments → 404", s)
    for d in ("cap-phat", "nguoi-mua", "ty-gia", "ma-ke-toan", "xe"):          # đường KHO (kho tạm) giữ nguyên
        s, g = goi("/api/lien-thong/" + d); dung(s != 404, "đường kho /api/lien-thong/%s giữ nguyên (không 404)" % d, s)

    print("2. Tất toán tài xế kỳ %s" % KY)
    s, g = goi("/api/tat-toan?ky=" + KY, vai="thabok"); dung(s == 403, "Bãi xem tất toán → 403", s)
    s, g = goi("/api/tat-toan?ky=" + KY, vai="ketoan"); dung(s == 403, "KT Thu/Chi xem tất toán → 403 (việc KT Chi phí, quỹ)", s)
    s, b = goi("/api/tat-toan?ky=" + KY, vai="quytb"); dung(s == 200, "Quỹ tiền mặt xem bảng tất toán", s)
    s, b = goi("/api/tat-toan?ky=" + KY, vai="ketoancp")
    dung(s == 200, "KT Chi phí xem bảng tất toán", "%s dòng" % len(b.get("dong") or []))
    da_lam = set()
    for dau, loai, vt, doty, no, co in ((1, "TT_CHI", "CMP", 60, "1601", "1011"), (-1, "TT_THU", "CMR", 17, "1011", "1601")):
        ung = [d for d in b["dong"] if not d["da_tat_toan"] and d["chenh_lech_lak"] * dau >= 1 and d["driver_id"] not in da_lam]
        if not ung:
            print("  · kỳ %s không có tài xế chênh %s chưa chốt — bỏ qua %s" % (KY, "dương" if dau > 0 else "âm", loai))
            continue
        lam = None
        for d in ung:
            if loai == "TT_CHI":
                s, g = goi("/api/tat-toan", {"driver_id": d["driver_id"], "period": KY}, "ketoan")
                dung(s == 403, "KT Thu/Chi chốt → 403", s)
            s, r = goi("/api/tat-toan", {"driver_id": d["driver_id"], "period": KY, "note": "thử nối kế toán"}, "ketoancp")
            if s == 409 and ma(r) == "TAM_UNG_CHUA_CHI_XONG":
                dung(bool((r.get("detail") or {}).get("phieu")), "tài xế còn tạm ứng chờ chi ở kế toán → chặn chốt, kể rõ phiếu", cau(r)[:90])
                continue
            lam = d
            break
        if lam is None:
            continue
        da_lam.add(lam["driver_id"])
        tt = (r or {}).get("tat_toan") or {}
        pk = tt.get("phieu_ke_toan") or {}
        if not dung(s == 200 and tt.get("status") == "cho_chi", "chốt %s · %s (chênh %s)" % (loai, lam["driver_name"], lam["chenh_lech_lak"]),
                    "%s %s %s" % (s, ma(r), cau(r)[:100])):
            continue
        dung(pk.get("loai") == loai and pk.get("status") == "da_gui" and pk.get("document_no"),
             "%s → phiếu %s bên kế toán chờ thủ quỹ" % (loai, vt), "%s %s %s" % (pk.get("status"), pk.get("document_no"), pk.get("error_message") or ""))
        dung(abs((pk.get("amount") or 0) - abs(tt["chenh_lech_lak"])) < 0.5, "số phiếu = |chênh lệch| đã chốt", pk.get("amount"))
        qt = tt.get("quyet_toan") or {}
        dq = (qt.get("dong") or [{}])[0]
        dung(qt.get("status") == "cho_gui" and dq.get("no") == "625" and dq.get("co") == "1601"
             and abs((dq.get("tien") or 0) - tt["tong_chi_lak"]) < 0.5 and (dq.get("doi_tuong") or {}).get("ref_id") == lam["driver_id"],
             "QT_TU Nợ 625 / Có 1601 = đã chi thật → bút toán chờ gửi", "%s %s/%s %s" % (qt.get("status"), dq.get("no"), dq.get("co"), dq.get("tien")))
        if pk.get("real_id"):
            kiem_phieu(pk, loai, vt, doty, no, co, abs(tt["chenh_lech_lak"]), "staff", "EPLTX-" + lam["driver_id"])
        s, g = goi("/api/tat-toan", {"driver_id": lam["driver_id"], "period": KY}, "ketoancp")
        dung(s == 409 and ma(g) == "DA_TAT_TOAN", "chốt lần hai → 409", ma(g))
        s, g = goi("/api/tat-toan/%s/cap-nhat?ky=%s" % (lam["driver_id"], KY), {}, "quytb")
        dung(s == 200 and (g["tat_toan"]["phieu_ke_toan"] or {}).get("status") == "da_gui", "quỹ bấm cập nhật: hỏi lại, vẫn chờ chi", s)
        s, g = goi("/api/tat-toan/%s/gui-lai?ky=%s" % (lam["driver_id"], KY), {}, "ketoancp")
        dung(s == 409 and ma(g) == "KHONG_GUI_LAI", "gửi lại phiếu đang chờ → 409", ma(g))
        s, g = goi("/api/tat-toan?ky=" + KY, vai="ketoancp")
        x = next((d for d in g["dong"] if d["driver_id"] == lam["driver_id"]), {})
        dung(x.get("da_tat_toan") and (x.get("tat_toan") or {}).get("status") == "cho_chi" and not x["tat_toan"]["lech"],
             "bảng tháng: đã chốt, chờ chi, số khớp", (x.get("tat_toan") or {}).get("status"))
        if loai == "TT_THU" and pk.get("real_id"):
            # bên kế toán xoá tay phiếu chưa ghi sổ → hỏi lại thấy mất (PHIEU_CHI_MAT); bỏ chốt vẫn được, không gọi xoá phiếu không còn
            ke_toan("/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(pk["real_id"]), "VoucherType": vt})
            s, g = goi("/api/tat-toan/%s/cap-nhat?ky=%s" % (lam["driver_id"], KY), {}, "quytb")
            p2 = ((g or {}).get("tat_toan") or {}).get("phieu_ke_toan") or {}
            dung(s == 200 and p2.get("status") == "loi" and p2.get("error_code") == "PHIEU_CHI_MAT",
                 "phiếu bị xoá bên kế toán → hỏi lại thấy PHIEU_CHI_MAT, không treo chờ chi", "%s %s" % (p2.get("status"), p2.get("error_code")))
        s, g = goi("/api/tat-toan/%s?ky=%s" % (lam["driver_id"], KY), vai="quytb", method="DELETE")
        dung(s == 403, "quỹ bỏ chốt → 403", s)
        s, g = goi("/api/tat-toan/%s?ky=%s" % (lam["driver_id"], KY), vai="ketoancp", method="DELETE")
        dung(s == 200, "KT Chi phí bỏ chốt (dọn)", "%s %s %s" % (s, ma(g), cau(g)[:100]))
        if pk.get("real_id"):
            kq, loi = phieu_ben_kt(pk["real_id"], vt)
            dung(kq is None, "phiếu %s bên kế toán đã rút" % pk.get("document_no"), loi or "")
        s, g = goi("/api/tat-toan/%s?ky=%s" % (lam["driver_id"], KY), vai="ketoancp")
        dung(s == 200 and not g["da_tat_toan"] and g["tat_toan"] is None, "tài xế về chưa tất toán", s)

    print("3. Trả nhà cung cấp")
    s, g = goi("/api/suppliers/cong-no", vai="thabok"); dung(s == 403, "Bãi xem công nợ nhà cung cấp → 403", s)
    s, ds = goi("/api/suppliers/cong-no", vai="ketoancp")
    dung(s == 200 and all(abs(x["con_no_lak"] - (x["phat_sinh_lak"] - x["da_tra_lak"] - x["cho_chi_lak"])) <= 1 for x in ds),
         "công nợ = phát sinh − đã chi − chờ chi", "%s nhà cung cấp" % len(ds))
    ncc = next((x for x in ds if x["active"] and x["payment_term"] != "t_prepaid" and x["con_no_lak"] > 100000), None)
    if not dung(ncc is not None, "có nhà cung cấp còn nợ để thử", ncc["name"] if ncc else ""):
        return ket_thuc()
    sid = ncc["id"]
    s, g = goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": 1000}, "ketoan"); dung(s == 403, "KT Thu/Chi lập đề nghị trả → 403", s)
    s, g = goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": 0}, "ketoancp"); dung(s == 422 and ma(g) == "SO_SAI", "số tiền 0 → 422", ma(g))
    s, g = goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": ncc["con_no_lak"] + 10 ** 9}, "ketoancp")
    dung(s == 409 and ma(g) == "TRA_QUA_NO", "trả vượt số còn nợ mà không xác nhận → 409", ma(g))
    s, r = goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": 1000, "phuong_thuc": "bank", "ghi_chu": "thử nối kế toán"}, "ketoancp")
    if not dung(s == 200 and r.get("status") == "da_gui" and r.get("document_no"), "lập đề nghị trả 1.000 LAK → phiếu chi bên kế toán chờ chi",
                "%s %s %s %s" % (s, r.get("status"), r.get("document_no"), r.get("error_message") or cau(r))):
        if s == 200 and r.get("id"):
            goi("/api/chi-ncc/%s/huy" % r["id"], {}, "ketoancp")
        return ket_thuc()
    rid = r["id"]
    kiem_phieu(r, "PC_NCC", "CMP", 60, "4021", "1021", 1000, "suppliers", "EPLNCC-" + sid)
    s, t = goi("/api/suppliers/%s/tra-ke-toan" % sid, vai="quytb")
    dung(s == 200 and t["ncc"]["cho_chi_lak"] == ncc["cho_chi_lak"] + 1000 and t["ncc"]["con_no_lak"] == ncc["con_no_lak"] - 1000
         and t["de_nghi"][0]["id"] == rid, "quỹ xem: chờ chi +1.000, còn nợ −1.000, đề nghị mới nhất trên cùng", t["ncc"]["con_no_lak"] if s == 200 else s)
    s, g = goi("/api/chi-ncc/%s/cap-nhat" % rid, {}, "quytb"); dung(s == 200 and g["status"] == "da_gui", "quỹ bấm cập nhật: vẫn chờ chi", s)
    # bên kế toán xoá tay phiếu chưa ghi sổ: API đọc vẫn Success true, Master null — bên này phải nhận ra, không treo "chờ chi"
    ke_toan("/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(r["real_id"]), "VoucherType": "CMP"})
    s, g = goi("/api/chi-ncc/%s/cap-nhat" % rid, {}, "quytb")
    dung(s == 200 and g["status"] == "loi" and g["error_code"] == "PHIEU_CHI_MAT", "phiếu bị xoá bên kế toán → đề nghị thành lỗi PHIEU_CHI_MAT",
         "%s %s" % (g.get("status"), g.get("error_code")))
    s, g = goi("/api/chi-ncc/%s/gui-lai" % rid, {}, "ketoancp")
    dung(s == 200 and g["status"] == "da_gui" and g["real_id"] != r["real_id"], "gửi lại → phiếu chi mới bên kế toán", g.get("document_no"))
    r = g if s == 200 else r
    s, g = goi("/api/chi-ncc/%s/huy" % rid, {}, "quytb"); dung(s == 403, "quỹ huỷ đề nghị → 403", s)
    s, g = goi("/api/chi-ncc/%s/huy" % rid, {}, "ketoancp"); dung(s == 200 and g["status"] == "huy", "KT Chi phí huỷ đề nghị (dọn)", "%s %s" % (s, ma(g)))
    kq, loi = phieu_ben_kt(r["real_id"], "CMP")
    dung(kq is None, "phiếu %s bên kế toán đã rút" % r.get("document_no"), loi or "")
    s, g = goi("/api/chi-ncc/%s/gui-lai" % rid, {}, "ketoancp"); dung(s == 409 and ma(g) == "KHONG_GUI_LAI", "gửi lại đề nghị đã huỷ → 409", ma(g))
    s, t = goi("/api/suppliers/%s/tra-ke-toan" % sid, vai="ketoancp")
    dung(t["ncc"]["con_no_lak"] == ncc["con_no_lak"] and t["ncc"]["cho_chi_lak"] == ncc["cho_chi_lak"], "công nợ về như cũ", t["ncc"]["con_no_lak"])
    ket_thuc()


def ket_thuc():
    print("\nTẤT TOÁN · NHÀ CUNG CẤP NỐI KẾ TOÁN: %s" % ("ĐẠT" if not LOI else "SAI %d — %s" % (len(LOI), "; ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
