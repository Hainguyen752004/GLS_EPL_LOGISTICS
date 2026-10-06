# -*- coding: utf-8 -*-
"""Thử CHỦ XE LIÊN KẾT — danh mục, phí riêng từng chủ, đề nghị trả gộp nhiều phiếu (anh Khampla C4.2 · C4.3) — TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_chu_xe.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; tài xế, khách thử dựng mới, chủ xe / xe liên kết / DO thử
lập qua API ở một tháng d7 chưa có DO; không gọi mạng — phiếu chi bên hệ kế toán anh Tune và bút toán thuê xe lúc khoá GIẢ LẬP.
(Trước 06/10 bài gọi máy 8010, cấp dầu ở kho tạm 8031 đã bỏ, và lập phiếu chi THẬT bên DB demo.)

Kịch bản: kế toán lập chủ xe mới với phí 3 %, ngưỡng 38 t, trả gộp tháng → Bãi thêm xe liên kết gắn chủ đó → Bãi lập hai phiếu gom
bằng xe đó (phí trên phiếu tự điền 3 % / 38 t / 1,5) → đi tới khoá (phí, quá tải tính theo điều khoản chủ xe; bút toán thuê xe gửi
sang bộ giả) → KT Thu/Chi lập ĐỀ NGHỊ TRẢ GỘP hai phiếu một lần → một phiếu chi bên hệ kế toán (bộ giả) → phiếu đang nằm đề nghị thì
không vào đề nghị khác, không mở khoá được → bỏ đề nghị → hai phiếu về lại chờ trả. Cấn trừ SO nhiên liệu / SO quầy, tiền về 0:
kiem/thu_tat_toan_doi_tac.py; phí quản lý 715 / quá tải 758: kiem/thu_phi_qua_tai_thue_xe.py.
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ

dung, phai, ma = K.dung, K.phai, K.ma


def main():
    with K.Khung() as m:
        goi = m.goi
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        tx = m.tai_xe("ທ້າວ ທົດລອງ ລົດຮ່ວມ")
        kh = m.khach("ລູກຄ້າ ທົດລອງ ລົດຮ່ວມ")
        m.commit()

        print("== 1. danh mục chủ xe")
        s, g = goi("/api/owners", {"name": "Chủ thử", "fee_pct": 3}, vai="thabok")
        phai(s, 403, "Bãi thêm chủ xe → bị từ chối (điều khoản hợp đồng là của kế toán)", g)
        s, chu = goi("/api/owners", {"name": "ທ້າວ ທົດສອບ (Chủ thử)", "phone": "020 1111 2222", "fee_pct": 3, "over_limit_t": 38,
                                     "over_price": 1.5, "hire_ccy": "USD", "pay_mode": "thang", "note": "thử bộ kiểm"}, vai="ketoan")
        phai(s, 200, "Kế toán lập chủ xe: phí 3 % · ngưỡng 38 t · trả gộp tháng", chu)
        s, g = goi("/api/owners", {"name": "x", "pay_mode": "tuy_y"}, vai="ketoan"); phai(s, 422, "Cách trả lạ → bị từ chối", g)
        s, g = goi("/api/owners", {"name": "x", "fee_pct": 150}, vai="ketoan"); phai(s, 422, "Phí 150 % → bị từ chối", g)
        s, ds = goi("/api/owners", vai="thabok")
        c0 = next(c for c in ds if c["id"] == chu["id"])
        dung("fee_pct" not in c0 and "cho_tra" not in c0, "Bãi xem danh mục chủ xe: có tên, không có phí và tiền", sorted(c0))

        print("== 2. xe liên kết gắn chủ xe")
        s, xe = goi("/api/vehicles", {"truck_no": "THU-CX-01", "plate_head": "ກຂ 0001", "owner_type": "joint", "owner_id": chu["id"]}, vai="thabok")
        phai(s, 200, "Bãi thêm xe liên kết, chọn chủ xe từ danh mục", xe)
        dung(xe["owner_name"] == chu["name"], "Tên chủ xe chép từ danh mục", xe["owner_name"])
        s, g = goi("/api/vehicles", {"truck_no": "THU-CX-02", "owner_type": "joint", "owner_id": "khong-co"}, vai="thabok")
        phai(s, 422, "Chủ xe không có trong danh mục → bị từ chối", g)

        print("== 3. hai phiếu gom bằng xe đó → phí tự điền theo chủ, khoá tính theo điều khoản chủ")
        phieu = []
        for i, (so, tan) in enumerate((("THU-CX-A/EPL", 41.0), ("THU-CX-B/EPL", 39.0))):
            ngay = m.ngay(15 + i).isoformat()
            s, P = goi("/api/trips", {"doc_no": so, "kind": "gom", "doc_date": ngay, "out_date": ngay, "vehicle_id": xe["id"],
                                      "driver_id": tx.id, "customer_id": kh.id, "odo_out": 100, "weight_origin": tan,
                                      "goods": [{"goods_name": "ແຮ່ເຫຼັກ", "qty_t": tan}]}, vai="thabok")
            phai(s, 200, "Bãi lập phiếu gom %s bằng xe của chủ thử" % so, P)
            dung(P["company"] == "joint" and P["owner_id"] == chu["id"] and "fee_pct" not in P,
                 "Phiếu nhận chủ xe từ xe; Bãi không thấy phí chủ xe (nợ kỹ thuật 3.1)", (P["company"], P.get("owner_id")))
            s, P = goi("/api/trips/%s" % P["id"], vai="ketoan")
            dung((P["fee_pct"], P["over_limit_t"], P["over_price"]) == (3, 38, 1.5), "Phí / ngưỡng / mức trừ tự điền theo CHỦ XE (3 · 38 · 1,5)",
                 (P["fee_pct"], P["over_limit_t"], P["over_price"]))
            phieu.append(P)
        n_bt = len(K.GIA.but_toan)
        for P in phieu:
            s, g = goi("/api/trips/%s" % P["id"], {"price": 41, "price_ccy": "USD", "hire_price": 40, "hire_ccy": "USD"}, vai="ketoan", method="PUT")
            phai(s, 200, "Kế toán đặt giá bán 41, giá thuê 40 USD/t cho %s" % P["doc_no"], g)
            for muc in ("info", "trans"):
                s, g = goi("/api/trips/%s/sections/%s/send" % (P["id"], muc), {}, vai="thabok"); phai(s, 200, "gửi kiểm %s" % muc, g)
                s, g = goi("/api/trips/%s/sections/%s/verify" % (P["id"], muc), {}, vai="ketoan"); phai(s, 200, "kiểm %s" % muc, g)
            s, g = goi("/api/trips/%s/transport-status" % P["id"], {"status": "arrived", "weight_dest": P["weight_origin"], "odo_back": 300,
                                                                    "back_date": m.ngay(18).isoformat()}, vai="thabok")
            phai(s, 200, "xe về, cân bãi", g)
            s, g = goi("/api/trips/%s/khoa" % P["id"], {"xac_nhan": True}, vai="ketoan"); phai(s, 200, "khoá %s" % P["doc_no"], g)
            k, thue = g["tinh"], round(P["weight_origin"] * 40, 2)
            dung(abs(k["phi"] - round(thue * 0.03, 2)) < 0.01 and abs(k["tru_vuot"] - round(max(0, P["weight_origin"] - 38) * 1.5, 2)) < 0.01,
                 "Phí 3 %% của %s USD tiền thuê, quá tải theo ngưỡng 38 t × 1,5" % thue, (k["phi"], k["tru_vuot"]))
        gui = [z for z in K.GIA.but_toan[n_bt:] if z[0] == "POST" and not z[1].endswith("/reverse")]
        dung(len(gui) == 2, "Khoá hai phiếu → hai bút toán thuê xe gửi sang hệ kế toán (bộ giả)", len(gui))

        print("== 4. đề nghị trả gộp — hệ kế toán anh Tune (bộ giả)")
        s, g = goi("/api/owners/%s/cong-no" % chu["id"], vai="quytb"); phai(s, 404, "Đường cũ công nợ chủ xe (trang kế toán tạm) → đã gỡ", g)
        s, g = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="thabok"); phai(s, 403, "Bãi xem tiền trả chủ xe → bị từ chối", g)
        s, cn = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="quytb"); phai(s, 200, "Quỹ xem phiếu chờ trả", cn)
        ids_p = {P["id"] for P in phieu}
        cho = [x for x in cn["cho"] if x["id"] in ids_p]
        dung(len(cho) == 2 and all(x["locked"] and not x["owner_paid"] for x in cho), "Hai phiếu đã khoá chờ trả", len(cho))
        tong_usd = round(sum(x["tra_chu_xe"] for x in cho), 2)
        ids = [x["id"] for x in cho]
        s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": ids}, vai="quytb")
        phai(s, 403, "Quỹ lập đề nghị trả → bị từ chối (KT Thu/Chi · Sếp)", g)
        s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": []}, vai="ketoan"); phai(s, 409, "Đề nghị không chọn phiếu → bị từ chối", g)
        n_kt = len(K.GIA.ke_toan)
        s, r = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": ids, "phuong_thuc": "bank"}, vai="ketoan")
        phai(s, 200, "KT Thu/Chi lập đề nghị trả gộp hai phiếu", r)
        s2, cn = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="ketoan")
        dn = [d for d in cn["de_nghi"] if sorted(d["trip_ids"]) == sorted(ids) and d["status"] in ("da_gui", "loi")]
        luu = [z for z in K.GIA.ke_toan[n_kt:] if z[1] == "/api/v1/accounting/cmpayment-receipt/save-and-commit"]
        dung(len(dn) == 1 and dn[0]["status"] == "da_gui" and dn[0]["document_no"] and abs(dn[0]["amount"] - tong_usd) < 0.01
             and dn[0]["currency"] == "USD" and len(luu) == 1,
             "MỘT đề nghị cho cả hai phiếu → MỘT phiếu chi bên kế toán (bộ giả) đúng tổng trả chủ xe", dn and (dn[0]["status"], dn[0]["amount"], tong_usd))
        dn = dn[0]
        dung(not [x for x in cn["cho"] if x["id"] in ids_p], "Phiếu đang nằm đề nghị không còn ở danh sách chờ")
        s, g = goi("/api/owners/%s/de-nghi-tra" % chu["id"], {"trip_ids": ids}, vai="ketoan"); phai(s, 409, "Đề nghị lần hai cùng phiếu → từ chối", g)
        s, g = goi("/api/trips/%s/mo-khoa" % phieu[0]["id"], {}, vai="admin")
        phai(s, 409, "Phiếu đang nằm đề nghị trả → không mở khoá được (kể cả Sếp)", g)
        s, g = goi("/api/trips/%s/tra-chu-xe" % phieu[0]["id"], {}, vai="quytb"); phai(s, 409, "Nút trả từng phiếu cũ → 409 (trả qua đề nghị)", g)

        print("== 5. bỏ đề nghị")
        s, g = goi("/api/chi-chu-xe/%s/huy" % dn["id"], {}, vai="quytb"); phai(s, 403, "Quỹ bỏ đề nghị → bị từ chối", g)
        s, g = goi("/api/chi-chu-xe/%s/huy" % dn["id"], {}, vai="ketoan"); phai(s, 200, "Bỏ đề nghị (rút phiếu chi chưa ghi sổ bên kế toán)", g)
        s, cn = goi("/api/owners/%s/tra-ke-toan" % chu["id"], vai="ketoan")
        dung(len([x for x in cn["cho"] if x["id"] in ids_p]) == 2, "Bỏ đề nghị: hai phiếu về lại chờ trả")
        for P in phieu:
            s, g = goi("/api/trips/%s/mo-khoa" % P["id"], {}, vai="admin")
            s, g = goi("/api/trips/%s" % P["id"], vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử %s" % P["doc_no"], g)
        s, g = goi("/api/vehicles/%s" % xe["id"], {"active": False}, vai="thabok", method="PUT"); phai(s, 200, "Ngưng dùng xe thử", g)
        s, g = goi("/api/owners/%s" % chu["id"], {"name": chu["name"], "active": False}, vai="ketoan", method="PUT"); phai(s, 200, "Ngưng chủ xe thử", g)
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("THỬ CHỦ XE")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("THỬ CHỦ XE")
