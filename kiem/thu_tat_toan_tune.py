# -*- coding: utf-8 -*-
"""Thử TẤT TOÁN TÀI XẾ và TRẢ NHÀ CUNG CẤP nối hệ kế toán anh Tune (chủ dự án chốt 01/10: bỏ phần tiền trang kế toán tạm).

    python kiem/thu_tat_toan_tune.py

06/10 (anh Hải duyệt): chạy TRONG TIẾN TRÌNH (kiem/_tien_trinh_tune.py) — trước đây cần máy thử 8013 nối API 5090 thật, lập rồi
rút phiếu thật bên DB demo. Nay: TestClient trên bản sao _d7, mỗi phần một giao dịch ngoài cuối ROLLBACK; API phiếu thu / chi
bên kế toán GIẢ (GiaKeToan); mọi lời gọi mạng bị chặn. Dữ liệu thử TẠO MỚI trong giao dịch: hai tài xế, xe nhà, khách, các DO kỳ
2026-07 đã khoá (mục IV đã chi, dòng tiền mặt, tờ tạm ứng đã cấp), một nhà cung cấp có dòng ghi nợ.

1. Các đường máy tiền của trang kế toán tạm đã gỡ → 404; đường cũ /api/owners/{id}/cong-no, /api/suppliers/{id}/payments → 404.
   (Bỏ phần "đường kho tạm cap-phat / nguoi-mua … còn" của bản 01/10: kho tạm 8031 đã bỏ từ 05/10.)
2. Tất toán: Bãi / KT Thu-Chi không xem / không chốt; KT Chi phí chốt một tài xế chênh dương → phiếu chi "Chi khác" (DOTY 60,
   Nợ 1601 / Có 1011, đối tượng nhân viên EPLTX-…) + QT_TU Nợ 625 / Có 1601 thành bút toán chờ; chốt lần hai bị chặn; hỏi lại;
   gửi lại phiếu đang chờ bị chặn; bỏ chốt → phiếu bên kế toán bị rút. Một tài xế chênh âm → phiếu thu "Thu khác" (DOTY 17, Nợ
   1011 / Có 1601); phiếu bị xoá tay bên kế toán → hỏi lại thấy PHIEU_CHI_MAT, bỏ chốt vẫn được.
3. Trả nhà cung cấp: công nợ (phát sinh − đã chi − chờ chi); Bãi không xem; KT Thu-Chi không lập; trả vượt nợ phải xác nhận;
   lập đề nghị → phiếu chi "Chi khác" (Nợ 4021 / Có 1021, đối tượng nhà cung cấp EPLNCC-…); số chờ chi trừ vào còn nợ; phiếu xoá
   tay → PHIEU_CHI_MAT → gửi lại; huỷ → phiếu bên kế toán bị rút, công nợ về như cũ.
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tien_trinh_tune as TT                           # noqa: E402 — chặn mạng, khung giao dịch ROLLBACK, API kế toán giả

import models as M                                      # noqa: E402

dung, ma, cau = TT.dung, TT.ma, TT.cau
KY = "2026-07"
NGUOI = ("thabok", "ketoan", "ketoancp", "quytb", "admin")
GIA = TT.GiaKeToan()
TT.gan_ke_toan(GIA)


def kiem_phieu(pk, loai, doty, no, co, tien, duong_dt, so_dt):
    x = GIA.phieu.get(pk.get("real_id"))
    if not dung(x is not None and not x["xoa"], "đọc được phiếu %s bên kế toán" % pk.get("document_no")):
        return
    h, e = x["body"]["Header"], (x["body"].get("Entries") or [{}])[0]
    dung(h.get("DotyAutoId") == doty and x["st"] not in (12, 13), "%s: %s loại %s, CHƯA ghi sổ" % (loai, x["body"]["VoucherType"], doty),
         "DOTY %s · ST %s" % (h.get("DotyAutoId"), x["st"]))
    dung(e.get("DebitAccount") == no and e.get("CreditAccount") == co and abs((e.get("Amount") or 0) - tien) < 0.5,
         "định khoản Nợ %s / Có %s · %s" % (no, co, format(round(tien), ",")),
         "%s / %s · %s" % (e.get("DebitAccount"), e.get("CreditAccount"), e.get("Amount")))
    dung(GIA.so_doi_tuong(h.get("ObjectId")) == so_dt and GIA.duong.get(so_dt) == duong_dt and h.get("ObjectId") == pk.get("obj_id"),
         "đối tượng %s (danh mục %s) bên kế toán" % (so_dt, duong_dt), GIA.so_doi_tuong(h.get("ObjectId")))


def du_lieu_tat_toan(db, d):
    """Kỳ 2026-07: tx1 chi thật 140.000 · ứng 100.000 (chênh +40.000 → phiếu chi); tx2 chi thật 30.000 · ứng 100.000 (chênh
    −70.000 → phiếu thu). DO đã về, đã khoá, mục IV đã chi, không dòng giá 0, không khai báo chờ duyệt."""
    ngay = dt.date(2026, 7, 10)
    for i, (tx, dong) in enumerate(((d.tx1, (("x_food", 2, 50000), ("x_phone", 1, 40000))), (d.tx2, (("x_water", 1, 30000),))), 1):
        p = M.Trip(doc_no="%s-%d/EPL" % (d.tag, i), kind="giao", company="EPL", doc_date=ngay, out_date=ngay, back_date=ngay,
                   vehicle_id=d.nha.id, truck_no=d.nha.truck_no, driver_id=tx.id, driver_name=tx.name, customer_id=d.kh.id,
                   transport_status="arrived", locked=True)
        db.add(p)
        db.flush()
        for sec, st in (("info", "verified"), ("trans", "verified"), ("fuel", "booked"), ("travel", "paid"), ("repair", "booked"),
                        ("other", "booked")):
            db.add(M.TripSection(trip_id=p.id, section=sec, status=st))
        for j, (khoan, sl, gia) in enumerate(dong, 1):
            db.add(M.TripExpense(trip_id=p.id, section="travel", line_no=j, item_key=khoan, qty=sl, unit_price=gia, currency="LAK",
                                 paid_by_epl=True, pay_channel="tien_mat"))
        db.add(M.Voucher(trip_id=p.id, kind="advance", doc_no="PTU-" + p.doc_no, doc_date=ngay, driver_id=tx.id, amount_lak=100000,
                         status="da_cap", token="thu-ttt-" + p.id))
    db.commit()


def phan_1_2(ca, d):
    print("1. Đường tiền của trang kế toán tạm đã gỡ")
    for duong in ("doanh-thu/phieu", "doanh-thu/so-lieu", "doanh-thu/cho-gop", "chu-xe", "chu-xe/x/cho-tra", "chu-xe/phieu",
                  "xe-lien-ket", "tien-tai-xe", "tat-toan", "tat-toan/x", "ncc", "ncc/x", "can-tru", "thang-moi-nhat"):
        s, g = ca.goi("/api/lien-thong/" + duong)
        dung(s == 404, "GET /api/lien-thong/%s → 404" % duong, s)
    for duong in ("doanh-thu/xuat", "doanh-thu/bo-xuat", "doanh-thu/da-thu", "chu-xe/tra", "chu-xe/bo-tra"):
        s, g = ca.goi("/api/lien-thong/" + duong, {})
        dung(s == 404, "POST /api/lien-thong/%s → 404" % duong, s)
    s, g = ca.goi("/api/owners/x/cong-no", u="admin"); dung(s == 404, "đường cũ /api/owners/{id}/cong-no → 404", s)
    s, g = ca.goi("/api/suppliers/x/payments", u="admin"); dung(s == 404, "đường cũ /api/suppliers/{id}/payments → 404", s)

    print("2. Tất toán tài xế kỳ %s" % KY)
    du_lieu_tat_toan(ca.db, d)
    s, g = ca.goi("/api/tat-toan?ky=" + KY, u="thabok"); dung(s == 403, "Bãi xem tất toán → 403", s)
    s, g = ca.goi("/api/tat-toan?ky=" + KY, u="ketoan"); dung(s == 403, "KT Thu/Chi xem tất toán → 403 (việc KT Chi phí, quỹ)", s)
    s, b = ca.goi("/api/tat-toan?ky=" + KY, u="quytb"); dung(s == 200, "Quỹ tiền mặt xem bảng tất toán", s)
    s, b = ca.goi("/api/tat-toan?ky=" + KY, u="ketoancp")
    dong = {x["driver_id"]: x for x in (b.get("dong") or [])}
    d1, d2 = dong.get(d.tx1.id) or {}, dong.get(d.tx2.id) or {}
    dung(s == 200 and d1.get("tong_chi_lak") == 140000 and d1.get("tong_ung_lak") == 100000 and d1.get("chenh_lech_lak") == 40000
         and d2.get("chenh_lech_lak") == -70000 and not d1.get("da_tat_toan") and not d2.get("da_tat_toan"),
         "KT Chi phí xem bảng: tài xế thử 1 chênh +40.000, tài xế thử 2 chênh −70.000, chưa chốt",
         ({k: d1.get(k) for k in ("tong_chi_lak", "tong_ung_lak", "chenh_lech_lak")}, d2.get("chenh_lech_lak")))
    for tx, loai, vt, doty, no, co in ((d.tx1, "TT_CHI", "CMP", 60, "1601", "1011"), (d.tx2, "TT_THU", "CMR", 17, "1011", "1601")):
        if loai == "TT_CHI":
            s, g = ca.goi("/api/tat-toan", {"driver_id": tx.id, "period": KY}, "ketoan")
            dung(s == 403, "KT Thu/Chi chốt → 403", s)
        s, r = ca.goi("/api/tat-toan", {"driver_id": tx.id, "period": KY, "note": "thử nối kế toán"}, "ketoancp")
        tt = (r or {}).get("tat_toan") or {}
        pk = tt.get("phieu_ke_toan") or {}
        if not dung(s == 200 and tt.get("status") == "cho_chi", "chốt %s · %s (chênh %s)" % (loai, tx.name, tt.get("chenh_lech_lak")),
                    "%s %s %s" % (s, ma(r), cau(r)[:100])):
            continue
        dung(pk.get("loai") == loai and pk.get("status") == "da_gui" and pk.get("document_no"),
             "%s → phiếu %s bên kế toán chờ thủ quỹ" % (loai, vt), "%s %s %s" % (pk.get("status"), pk.get("document_no"), pk.get("error_message") or ""))
        dung(abs((pk.get("amount") or 0) - abs(tt["chenh_lech_lak"])) < 0.5, "số phiếu = |chênh lệch| đã chốt", pk.get("amount"))
        qt = tt.get("quyet_toan") or {}
        dq = (qt.get("dong") or [{}])[0]
        dung(qt.get("status") == "cho_gui" and dq.get("no") == "625" and dq.get("co") == "1601"
             and abs((dq.get("tien") or 0) - tt["tong_chi_lak"]) < 0.5 and (dq.get("doi_tuong") or {}).get("ref_id") == tx.id,
             "QT_TU Nợ 625 / Có 1601 = đã chi thật → bút toán chờ gửi", "%s %s/%s %s" % (qt.get("status"), dq.get("no"), dq.get("co"), dq.get("tien")))
        kiem_phieu(pk, loai, doty, no, co, abs(tt["chenh_lech_lak"]), "staff", "EPLTX-" + tx.id)
        s, g = ca.goi("/api/tat-toan", {"driver_id": tx.id, "period": KY}, "ketoancp")
        dung(s == 409 and ma(g) == "DA_TAT_TOAN", "chốt lần hai → 409", ma(g))
        s, g = ca.goi("/api/tat-toan/%s/cap-nhat?ky=%s" % (tx.id, KY), {}, "quytb")
        dung(s == 200 and (g["tat_toan"]["phieu_ke_toan"] or {}).get("status") == "da_gui", "quỹ bấm cập nhật: hỏi lại, vẫn chờ chi", s)
        s, g = ca.goi("/api/tat-toan/%s/gui-lai?ky=%s" % (tx.id, KY), {}, "ketoancp")
        dung(s == 409 and ma(g) == "KHONG_GUI_LAI", "gửi lại phiếu đang chờ → 409", ma(g))
        s, g = ca.goi("/api/tat-toan?ky=" + KY, u="ketoancp")
        x = next((z for z in g["dong"] if z["driver_id"] == tx.id), {})
        dung(x.get("da_tat_toan") and (x.get("tat_toan") or {}).get("status") == "cho_chi" and not x["tat_toan"]["lech"],
             "bảng tháng: đã chốt, chờ chi, số khớp", (x.get("tat_toan") or {}).get("status"))
        if loai == "TT_THU":
            # bên kế toán xoá tay phiếu chưa ghi sổ → hỏi lại thấy mất (PHIEU_CHI_MAT); bỏ chốt vẫn được, không gọi xoá phiếu không còn
            GIA.xoa_tay(pk["real_id"])
            s, g = ca.goi("/api/tat-toan/%s/cap-nhat?ky=%s" % (tx.id, KY), {}, "quytb")
            p2 = ((g or {}).get("tat_toan") or {}).get("phieu_ke_toan") or {}
            dung(s == 200 and p2.get("status") == "loi" and p2.get("error_code") == "PHIEU_CHI_MAT",
                 "phiếu bị xoá bên kế toán → hỏi lại thấy PHIEU_CHI_MAT, không treo chờ chi", "%s %s" % (p2.get("status"), p2.get("error_code")))
        s, g = ca.goi("/api/tat-toan/%s?ky=%s" % (tx.id, KY), u="quytb", method="DELETE")
        dung(s == 403, "quỹ bỏ chốt → 403", s)
        so_xoa = sum(1 for z in GIA.nhan if z[1].endswith("/cmpayment-receipt/delete"))
        s, g = ca.goi("/api/tat-toan/%s?ky=%s" % (tx.id, KY), u="ketoancp", method="DELETE")
        dung(s == 200, "KT Chi phí bỏ chốt (dọn)", "%s %s %s" % (s, ma(g), cau(g)[:100]))
        x = GIA.phieu.get(pk["real_id"]) or {}
        xoa_moi = sum(1 for z in GIA.nhan if z[1].endswith("/cmpayment-receipt/delete")) - so_xoa
        dung(x.get("xoa") and xoa_moi == (1 if loai == "TT_CHI" else 0),
             "phiếu %s bên kế toán đã rút%s" % (pk.get("document_no"), "" if loai == "TT_CHI" else " (đã mất từ trước — không gọi xoá lần nữa)"),
             "gọi xoá %d lần" % xoa_moi)
        s, g = ca.goi("/api/tat-toan/%s?ky=%s" % (tx.id, KY), u="ketoancp")
        dung(s == 200 and not g["da_tat_toan"] and g["tat_toan"] is None, "tài xế về chưa tất toán", s)


def phan_3(ca, d):
    print("3. Trả nhà cung cấp")
    db = ca.db
    ncc = M.Supplier(name="NCC thử %s" % d.tag, payment_term="t_monthly", active=True)
    db.add(ncc)
    db.flush()
    p = M.Trip(doc_no="%s-NCC/EPL" % d.tag, kind="giao", company="EPL", doc_date=dt.date(2026, 7, 12), out_date=dt.date(2026, 7, 12),
               vehicle_id=d.nha.id, truck_no=d.nha.truck_no, driver_id=d.tx1.id, driver_name=d.tx1.name, customer_id=d.kh.id)
    db.add(p)
    db.flush()
    db.add(M.TripExpense(trip_id=p.id, section="fuel", line_no=1, item_key="diesel", qty=20, unit_price=25000, currency="LAK",
                         paid_by_epl=True, source="mua", supplier_id=ncc.id, ghi_no=True))
    db.commit()
    sid = ncc.id
    s, g = ca.goi("/api/suppliers/cong-no", u="thabok"); dung(s == 403, "Bãi xem công nợ nhà cung cấp → 403", s)
    s, ds = ca.goi("/api/suppliers/cong-no", u="ketoancp")
    dung(s == 200 and all(abs(x["con_no_lak"] - (x["phat_sinh_lak"] - x["da_tra_lak"] - x["cho_chi_lak"])) <= 1 for x in ds),
         "công nợ = phát sinh − đã chi − chờ chi (mọi nhà cung cấp)", "%s nhà cung cấp" % len(ds) if s == 200 else s)
    goc = next((x for x in ds if x["id"] == sid), None) if s == 200 else None
    if not dung(goc is not None and goc["phat_sinh_lak"] == 500000 and goc["con_no_lak"] == 500000,
                "nhà cung cấp thử: phát sinh 500.000 (20 L × 25.000 ghi nợ trạm), còn nợ 500.000", goc):
        return
    s, g = ca.goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": 1000}, "ketoan"); dung(s == 403, "KT Thu/Chi lập đề nghị trả → 403", s)
    s, g = ca.goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": 0}, "ketoancp"); dung(s == 422 and ma(g) == "SO_SAI", "số tiền 0 → 422", ma(g))
    s, g = ca.goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": goc["con_no_lak"] + 10 ** 9}, "ketoancp")
    dung(s == 409 and ma(g) == "TRA_QUA_NO", "trả vượt số còn nợ mà không xác nhận → 409", ma(g))
    s, r = ca.goi("/api/suppliers/%s/de-nghi-tra" % sid, {"so_tien": 1000, "phuong_thuc": "bank", "ghi_chu": "thử nối kế toán"}, "ketoancp")
    if not dung(s == 200 and r.get("status") == "da_gui" and r.get("document_no"), "lập đề nghị trả 1.000 LAK → phiếu chi bên kế toán chờ chi",
                "%s %s %s %s" % (s, r.get("status"), r.get("document_no"), r.get("error_message") or cau(r))):
        return
    rid = r["id"]
    kiem_phieu(r, "PC_NCC", 60, "4021", "1021", 1000, "suppliers", "EPLNCC-" + sid)
    s, t = ca.goi("/api/suppliers/%s/tra-ke-toan" % sid, u="quytb")
    dung(s == 200 and t["ncc"]["cho_chi_lak"] == goc["cho_chi_lak"] + 1000 and t["ncc"]["con_no_lak"] == goc["con_no_lak"] - 1000
         and t["de_nghi"][0]["id"] == rid, "quỹ xem: chờ chi +1.000, còn nợ −1.000, đề nghị mới nhất trên cùng",
         t["ncc"]["con_no_lak"] if s == 200 else s)
    s, g = ca.goi("/api/chi-ncc/%s/cap-nhat" % rid, {}, "quytb"); dung(s == 200 and g["status"] == "da_gui", "quỹ bấm cập nhật: vẫn chờ chi", s)
    GIA.xoa_tay(r["real_id"])                    # bên kế toán xoá tay phiếu chưa ghi sổ: đọc vẫn Success true, Master null
    s, g = ca.goi("/api/chi-ncc/%s/cap-nhat" % rid, {}, "quytb")
    dung(s == 200 and g["status"] == "loi" and g["error_code"] == "PHIEU_CHI_MAT", "phiếu bị xoá bên kế toán → đề nghị thành lỗi PHIEU_CHI_MAT",
         "%s %s" % (g.get("status"), g.get("error_code")))
    s, g = ca.goi("/api/chi-ncc/%s/gui-lai" % rid, {}, "ketoancp")
    dung(s == 200 and g["status"] == "da_gui" and g["real_id"] != r["real_id"], "gửi lại → phiếu chi mới bên kế toán", g.get("document_no"))
    r = g if s == 200 else r
    s, g = ca.goi("/api/chi-ncc/%s/huy" % rid, {}, "quytb"); dung(s == 403, "quỹ huỷ đề nghị → 403", s)
    s, g = ca.goi("/api/chi-ncc/%s/huy" % rid, {}, "ketoancp"); dung(s == 200 and g["status"] == "huy", "KT Chi phí huỷ đề nghị", "%s %s" % (s, ma(g)))
    dung((GIA.phieu.get(r["real_id"]) or {}).get("xoa"), "phiếu %s bên kế toán đã rút" % r.get("document_no"))
    s, g = ca.goi("/api/chi-ncc/%s/gui-lai" % rid, {}, "ketoancp"); dung(s == 409 and ma(g) == "KHONG_GUI_LAI", "gửi lại đề nghị đã huỷ → 409", ma(g))
    s, t = ca.goi("/api/suppliers/%s/tra-ke-toan" % sid, u="ketoancp")
    dung(t["ncc"]["con_no_lak"] == goc["con_no_lak"] and t["ncc"]["cho_chi_lak"] == goc["cho_chi_lak"], "công nợ về như cũ", t["ncc"]["con_no_lak"])


def main():
    for ten, phan in (("phần 1–2 (đường cũ, tất toán)", phan_1_2), ("phần 3 (nhà cung cấp)", phan_3)):
        with TT.Ca(NGUOI) as ca:
            d = TT.du_lieu_thu(ca.db, "TTT")
            try:
                phan(ca, d)
            except (AssertionError, KeyError, TypeError) as e:
                dung(False, "%s dừng giữa chừng" % ten, repr(e))
    TT.ket_thuc("TẤT TOÁN · NHÀ CUNG CẤP NỐI KẾ TOÁN")


if __name__ == "__main__":
    main()
