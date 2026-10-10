# -*- coding: utf-8 -*-
"""Thử TÀI KHOẢN NỢ / CÓ RIÊNG của nhà cung cấp · chủ xe · khách và XOÁ CHỦ XE (09/10, anh Khampla) — TRONG TIẾN TRÌNH.

    python kiem/thu_tk_rieng.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK, không gọi mạng. Sổ tài khoản GIẢ (routes.acc_code.lay_danh_muc
thay bằng bộ mã nhỏ: mã chi tiết, một mã tổng, một mã đã ngưng) — bài không phụ thuộc API sổ tài khoản bên kế toán.

Kịch bản:
  1. Nhà cung cấp: TK sai nhóm / mã tổng / đã ngưng / không có trong sổ, thư điện tử sai, đơn vị tiền lạ → 422 kèm ô lỗi; lưu đủ hồ sơ
     (mã số thuế, thư điện tử, trang web, đơn vị tiền, dịch vụ gõ tay, TK 6251 / 4031); Bãi không thấy TK; trống lại = mặc định.
  2. Chủ xe: TK sai nhóm → 422; lưu 6211 / 4025; Bãi không thấy TK.
  3. Khách: Bãi đổi TK → 403; kế toán gán TK sai nhóm → 422; gán 1213 / 7081; Bãi lưu lại form (TK không đổi) → được.
  4. Định khoản: dòng sửa chữa (mục V) chỉ mang khoản mục của nhà cung cấp (xe nhà) → nợ NCC 6251 / 4031 lúc khoá; mã lưu vẫn 614/4021;
     phiếu trả bảng tk_rieng cho màn; dòng ghi rõ nhà cung cấp → 6251 / 4031; mã tự chọn giữ nguyên. Xe thuê của chủ xe có TK riêng:
     tiền thuê 6211 / 4025, phí · quá tải Nợ 4025, nợ NCC Nợ 4025 / Có 4031; gói bàn giao DO: hire 6211/4025, cước 1213/7081.
  5. Xoá chủ xe: còn xe → 409 CON_XE; có phiếu → 409 CO_PHIEU; có hợp đồng → 409 CON_HOP_DONG; chủ xe trống → xoá được; Bãi → 403.
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ

dung, phai, ma = K.dung, K.phai, K.ma

# sổ tài khoản giả: (mã, tên Việt, ghi sổ được, đang dùng)
SO = [("1011", "Tiền mặt LAK", True, True), ("1012", "Tiền mặt ngoại tệ", True, True), ("1021", "Tiền gửi LAK", True, True),
      ("1211", "Phải thu khách — hàng hoá", True, True), ("1213", "Phải thu khách — dịch vụ", True, True),
      ("1371", "Kho hàng", True, True), ("1601", "Tạm ứng", True, True),
      ("4021", "Phải trả NCC", True, True), ("4022", "Phải trả chủ xe", True, True), ("4025", "Phải trả chủ xe — riêng", True, True),
      ("4029", "Phải trả cũ", True, False), ("4031", "Phải trả NCC — hoá đơn", True, True), ("4201", "Phải trả nhân viên", True, True),
      ("607", "Giá vốn", True, True), ("614", "Bảo trì sửa chữa", True, True), ("62", "Chi phí dịch vụ (tổng)", False, True),
      ("621", "Thuê xe ngoài", True, True), ("6211", "Thuê xe ngoài — riêng", True, True), ("625", "Đi lại", True, True),
      ("6251", "Đi lại — chip", True, True), ("707", "Doanh thu hàng", True, True), ("708", "Doanh thu vận chuyển", True, True),
      ("7081", "Doanh thu vận chuyển — riêng", True, True), ("715", "Hoa hồng", True, True), ("758", "Thu nhập khác", True, True)]


def main():
    import routes.acc_code as AC
    AC.lay_danh_muc = lambda refresh=False: ([{"code": c, "name": t, "description": t, "postable": p, "active": a} for c, t, p, a in SO],
                                             "remote", "sổ giả")
    from types import SimpleNamespace
    with K.Khung() as m:
        goi, M = m.goi, m.M
        from services import tai_khoan as TK
        from services import but_toan_cho as BTC
        from services import ban_giao as BG
        from services import khoan_muc as KMC
        KMC.nap(m.db)
        # khoản mục SỬA CHỮA (mục V) CHƯA có nhà cung cấp nào theo dõi — dòng không ghi nhà cung cấp mang khoản này là nợ nhà cung cấp
        # thử trả theo đợt (tai_khoan._ncc_theo_dot chỉ xét mục V; mục IV đi đường đi tạm ứng / cùng lương)
        co = {k for (k,) in m.db.query(M.Supplier.item_key).filter(M.Supplier.item_key.isnot(None))}
        khoan = next((k for k in KMC.KHOAN_MUC["repair"] if k not in co), None)
        phai(200 if khoan else 0, 200, "có khoản mục sửa chữa chưa nhà cung cấp nào theo dõi để thử (%s)" % khoan)
        print("== 0. dữ liệu thử (tháng %s, khoản mục %s)" % (m.thang, khoan))

        print("== 1. nhà cung cấp")
        than = {"name": "THU-NCC ທົດລອງ TK", "item_key": khoan, "payment_term": "t_monthly"}
        for tk, o, cau in ((("4021", ""), "acct_no", "TK Nợ nhóm 4 (sai vế)"), (("62", ""), "acct_no", "TK Nợ là mã tổng"),
                           (("6999", ""), "acct_no", "TK Nợ không có trong sổ"), (("", "4029"), "acct_co", "TK Có đã ngưng"),
                           (("", "6251"), "acct_co", "TK Có nhóm 6 (sai vế)")):
            s, g = goi("/api/suppliers", {**than, "acct_no": tk[0], "acct_co": tk[1]}, vai="ketoancp")
            dung(s == 422 and ma(g) == "TK_SAI" and g["detail"].get("o") == o and g["detail"].get("loi_lo"),
                 "%s → 422 TK_SAI, chỉ ô %s, có câu Lào" % (cau, o), (s, g.get("detail") if isinstance(g, dict) else g))
        s, g = goi("/api/suppliers", {**than, "email": "khong-co-a-cong"}, vai="ketoancp")
        dung(s == 422 and ma(g) == "EMAIL_SAI" and g["detail"].get("o") == "email", "Thư điện tử sai dạng → 422 EMAIL_SAI", ma(g))
        s, g = goi("/api/suppliers", {**than, "currency": "XYZ"}, vai="ketoancp")
        dung(s == 422 and ma(g) == "TIEN_TE_SAI" and g["detail"].get("o") == "currency", "Đơn vị tiền lạ → 422 TIEN_TE_SAI", ma(g))
        s, g = goi("/api/suppliers", {**than, "acct_no": "6251"}, vai="thabok")
        phai(s, 403, "Bãi thêm nhà cung cấp → bị từ chối", g)
        s, ncc = goi("/api/suppliers", {**than, "code": "THU-NCC-TK", "tax_no": "0101-777", "email": "chip@thu.la", "website": "thu.la",
                                        "currency": "thb", "dich_vu": "ຄ່າຊິບ (gõ tay)", "acct_no": "6251", "acct_co": "4031",
                                        "phone": "020 7777 1111"}, vai="ketoancp")
        phai(s, 200, "KT Chi phí lưu nhà cung cấp đủ hồ sơ + TK 6251 / 4031", ncc)
        dung((ncc["acct_no"], ncc["acct_co"], ncc["tax_no"], ncc["email"], ncc["website"], ncc["currency"], ncc["dich_vu"], ncc["code"])
             == ("6251", "4031", "0101-777", "chip@thu.la", "thu.la", "THB", "ຄ່າຊິບ (gõ tay)", "THU-NCC-TK"),
             "Hồ sơ trả về đúng (đơn vị tiền viết hoa)", ncc)
        s, ds = goi("/api/suppliers", vai="thabok")
        x = next(r for r in ds if r["id"] == ncc["id"])
        dung(not ({"acct_no", "acct_co", "acct_code"} & set(x)) and x["dich_vu"] == "ຄ່າຊິບ (gõ tay)", "Bãi xem danh mục: không có TK, có dịch vụ",
             sorted(x))
        s, ds = goi("/api/suppliers", vai="ketoancp")
        x = next(r for r in ds if r["id"] == ncc["id"])
        dung(x["acct_no"] == "6251" and x["acct_co"] == "4031", "KT Chi phí xem danh mục: thấy TK riêng", (x["acct_no"], x["acct_co"]))
        s, g = goi("/api/suppliers/" + ncc["id"], {"acct_no": "", "acct_co": ""}, vai="ketoancp", method="PUT")
        dung(s == 200 and g["acct_no"] is None and g["acct_co"] is None, "Để trống lại → về mặc định (không lưu mã)", (s, g.get("acct_no")))
        s, ncc = goi("/api/suppliers/" + ncc["id"], {"acct_no": "6251", "acct_co": "4031"}, vai="ketoancp", method="PUT")
        phai(s, 200, "Gán lại TK 6251 / 4031", ncc)
        s, ncc2 = goi("/api/suppliers", {"name": "THU-NCC2 trạm ghi nợ", "acct_no": "6251", "acct_co": "4031"}, vai="ketoancp")
        phai(s, 200, "Nhà cung cấp thứ hai (không khoản mục — dòng ghi rõ nhà cung cấp)", ncc2)

        print("== 2. chủ xe")
        s, g = goi("/api/owners", {"name": "THU-CX TK", "acct_no": "4022"}, vai="ketoan")
        dung(s == 422 and ma(g) == "TK_SAI" and g["detail"].get("o") == "acct_no", "Chủ xe TK Nợ nhóm 4 → 422 TK_SAI", ma(g))
        s, g = goi("/api/owners", {"name": "THU-CX TK", "acct_co": "621"}, vai="ketoan")
        dung(s == 422 and ma(g) == "TK_SAI" and g["detail"].get("o") == "acct_co", "Chủ xe TK Có nhóm 6 → 422 TK_SAI", ma(g))
        s, chu = goi("/api/owners", {"name": "THU-CX ທົດລອງ TK", "fee_pct": 2, "over_limit_t": 40, "over_price": 1, "hire_ccy": "USD",
                                     "acct_no": "6211", "acct_co": "4025"}, vai="ketoan")
        phai(s, 200, "Kế toán lập chủ xe TK 6211 / 4025", chu)
        dung(chu.get("acct_no") == "6211" and chu.get("acct_co") == "4025", "Chủ xe trả về TK riêng", (chu.get("acct_no"), chu.get("acct_co")))
        s, ds = goi("/api/owners", vai="thabok")
        x = next(r for r in ds if r["id"] == chu["id"])
        dung("acct_no" not in x and "acct_co" not in x, "Bãi xem danh mục chủ xe: không có TK", sorted(x))

        print("== 3. khách")
        kh = m.khach("ລູກຄ້າ ທົດລອງ TK")
        m.commit()
        s, g = goi("/api/customers/" + kh.id, {"acct_no": "1213"}, vai="thabok", method="PUT")
        dung(s == 403 and ma(g) == "TK_KHACH_KE_TOAN", "Bãi đổi TK khách → 403 TK_KHACH_KE_TOAN", (s, ma(g)))
        s, g = goi("/api/customers/" + kh.id, {"acct_no": "708"}, vai="ketoan", method="PUT")
        dung(s == 422 and ma(g) == "TK_SAI" and g["detail"].get("o") == "acct_no", "TK Nợ khách nhóm 7 → 422", ma(g))
        s, g = goi("/api/customers/" + kh.id, {"acct_co": "1211"}, vai="ketoan", method="PUT")
        dung(s == 422 and ma(g) == "TK_SAI" and g["detail"].get("o") == "acct_co", "TK Có khách nhóm 1 → 422", ma(g))
        s, g = goi("/api/customers/" + kh.id, {"name": kh.name, "acct_no": "1213", "acct_co": "7081"}, vai="ketoan", method="PUT")
        phai(s, 200, "Kế toán gán TK khách 1213 / 7081", g)
        dung(g.get("acct_no") == "1213" and g.get("acct_co") == "7081", "Khách trả về TK riêng", (g.get("acct_no"), g.get("acct_co")))
        s, g = goi("/api/customers/" + kh.id, {"name": kh.name, "phone": "020 1", "acct_no": "1213", "acct_co": "7081"}, vai="thabok", method="PUT")
        dung(s == 200, "Bãi lưu lại form khách (TK gửi đúng mã đang có) → được", (s, ma(g)))

        print("== 4. định khoản dùng TK riêng")
        tx = m.tai_xe("ທ້າວ ທົດລອງ TK")
        xe_nha = m.xe("THU-TK-01")
        o = m.db.get(M.Owner, chu["id"])
        xe_thue = m.xe("THU-TK-02", loai="joint", chu=o)
        m.commit()
        ngay = m.ngay(12).isoformat()
        s, p1 = goi("/api/trips", {"doc_no": "THU-TK-A/EPL", "kind": "giao", "vehicle_id": xe_nha.id, "driver_id": tx.id, "customer_id": kh.id,
                                   "doc_date": ngay, "out_date": ngay, "weight_origin": 40, "odo_out": 100, "price": 40, "price_ccy": "USD",
                                   "expenses": [{"section": "repair", "item_key": khoan, "qty": 1, "unit_price": 100000, "currency": "LAK"}]},
                    vai="admin")
        phai(s, 200, "Sếp lập phiếu xe nhà, dòng %s 100.000 Kíp" % khoan, p1)
        s, p1 = goi("/api/trips/" + p1["id"], vai="ketoan")
        d1 = next(d for d in p1["expenses"] if d["item_key"] == khoan)
        dung(d1["acct_code"] == "614/4021", "Mã lưu / theo luật trên dòng vẫn 614/4021 (không ghim mã riêng)", d1["acct_code"])
        dung((p1.get("tk_rieng") or {}).get("ncc_khoan", {}).get(khoan) == {"no": "6251", "co": "4031"},
             "Phiếu gửi bảng tk_rieng cho màn: khoản %s → 6251 / 4031" % khoan, p1.get("tk_rieng"))
        T1 = m.db.get(M.Trip, p1["id"])
        dong = m.db.query(M.TripExpense).filter(M.TripExpense.trip_id == T1.id).all()
        dung(TK.tk_dong_rieng(T1.company, dong[0], m.db) == "6251/4031", "tk_dong_rieng: dòng chỉ mang khoản mục → 6251/4031",
             TK.tk_dong_rieng(T1.company, dong[0], m.db))
        ra = BTC.dong_khoa_phieu(m.db, T1)
        nn = [(x["no"], x["co"], x["tien"]) for x in (ra.get(BTC.NO_NCC) or ([], ""))[0]]
        dung(nn == [("6251", "4031", 100000)], "Khoá phiếu xe nhà: nợ NCC Nợ 6251 / Có 4031 = 100.000", nn)
        # dòng ghi rõ nhà cung cấp (trạm ghi nợ) — nhà cung cấp thứ hai
        d2 = M.TripExpense(trip_id=T1.id, section="travel", item_key="x_food", qty=1, unit_price=5000, currency="LAK", paid_by_epl=True,
                           supplier_id=ncc2["id"], ghi_no=True, line_no=99)
        dung(TK.tk_dong(T1.company, d2, m.db).endswith("/4021") and TK.tk_dong_rieng(T1.company, d2, m.db) == "6251/4031",
             "Dòng ghi rõ nhà cung cấp, ghi nợ: …/4021 theo luật → 6251/4031", (TK.tk_dong(T1.company, d2, m.db), TK.tk_dong_rieng(T1.company, d2, m.db)))
        d3 = SimpleNamespace(**{c: getattr(d2, c) for c in ("section", "item_key", "source", "place", "paid_by_epl", "ghi_no", "supplier_id")},
                             toll_card_id=None, acct_code="6211/1012")
        dung(TK.tk_dong_rieng(T1.company, d3, m.db) == "6211/1012", "Mã người dùng tự chọn trên dòng: giữ nguyên", TK.tk_dong_rieng(T1.company, d3, m.db))

        s, p2 = goi("/api/trips", {"doc_no": "THU-TK-B/EPL", "kind": "giao", "company": "joint", "vehicle_id": xe_thue.id, "driver_id": tx.id,
                                   "customer_id": kh.id, "doc_date": ngay, "out_date": ngay, "weight_origin": 45, "odo_out": 100,
                                   "price": 40, "price_ccy": "USD", "hire_price": 30, "hire_ccy": "USD", "fee_pct": 2, "over_limit_t": 40,
                                   "over_price": 1,
                                   "expenses": [{"section": "repair", "item_key": khoan, "qty": 1, "unit_price": 150000, "currency": "LAK"}]},
                    vai="admin")
        phai(s, 200, "Sếp lập phiếu xe thuê của chủ xe có TK riêng", p2)
        s, g = goi("/api/trips/%s/transport-status" % p2["id"], {"status": "arrived", "weight_dest": 45, "odo_back": 500, "back_date": ngay},
                   vai="admin")
        phai(s, 200, "Sếp báo xe tới, cân cuối 45 t", g)
        s, p2 = goi("/api/trips/" + p2["id"], vai="ketoan")
        dung((p2.get("tk_rieng") or {}).get("chu_xe") == {"no": "6211", "co": "4025"}, "Phiếu xe thuê gửi TK riêng chủ xe cho màn",
             (p2.get("tk_rieng") or {}).get("chu_xe"))
        T2 = m.db.get(M.Trip, p2["id"])
        ra = BTC.dong_khoa_phieu(m.db, T2)
        tx_ = [(x["no"], x["co"], x.get("ve")) for x in (ra.get(BTC.THUE_XE) or ([], ""))[0]]
        dung(tx_ == [("6211", "4025", "thue"), ("4025", "715", "phi_quan_ly"), ("4025", "758", "cat_qua_tai")],
             "Khoá xe thuê: tiền thuê Nợ 6211 / Có 4025; phí, quá tải Nợ 4025", tx_)
        nn = [(x["no"], x["co"]) for x in (ra.get(BTC.NO_NCC) or ([], ""))[0]]
        dung(nn == [("4025", "4031")], "Xe thuê, dòng nợ NCC: Nợ (chủ xe) 4025 / Có (NCC) 4031", nn)
        gb = BG.dong_goi(m.db, T2)
        hire = ((gb or {}).get("header") or {}).get("hire") or {}
        cuoc = next((x for x in (gb or {}).get("details") or [] if x.get("charge_type") == "freight"), {})
        dung(hire.get("acc_code") == "6211/4025" and "4025" in (hire.get("acc_code_note") or ""), "Gói bàn giao DO: hire 6211/4025",
             hire.get("acc_code"))
        dung(cuoc.get("acc_code") == "1213/7081", "Gói bàn giao DO: dòng cước theo TK khách 1213/7081", cuoc.get("acc_code"))
        chi = next((x for x in (gb or {}).get("details") or [] if x.get("item_key") == khoan), {})
        dung(chi.get("acc_code") == "4025/4031", "Gói bàn giao DO: dòng chi nợ NCC xe thuê 4025/4031", chi.get("acc_code"))

        print("== 4b. các lỗi bản soát 10/10 tìm ra")
        # (1) bấm Đồng ý ở hộp Định khoản mà không đổi gì: màn gửi lại mã đang HIỆN (đã thay TK riêng) → KHÔNG ghim thành mã tự chọn
        s, P1 = goi("/api/trips/" + p1["id"], vai="admin")
        dl = next(d for d in P1["expenses"] if d["item_key"] == khoan)
        s, g = goi("/api/trips/" + p1["id"], {"expenses": [{**dl, "acct_code": "6251/4031"}]}, vai="admin", method="PUT")
        phai(s, 200, "Sếp lưu phiếu, dòng mang mã đang hiện 6251/4031", g)
        m.db.expire_all()
        d_luu = m.db.query(M.TripExpense).filter(M.TripExpense.trip_id == p1["id"], M.TripExpense.item_key == khoan).one()
        dung(not TK.tu_chon(d_luu) and TK.tk_dong(T1.company, d_luu, m.db) == "614/4021",
             "mã gửi lại trùng mã hiện → lưu theo luật 614/4021 (không ghim)", d_luu.acct_code)
        nn = [(x["no"], x["co"]) for x in (BTC.dong_khoa_phieu(m.db, m.db.get(M.Trip, p1["id"])).get(BTC.NO_NCC) or ([], ""))[0]]
        dung(nn == [("6251", "4031")], "dòng đó vẫn vào bút toán nợ NCC lúc khoá, theo TK riêng", nn)
        s, g = goi("/api/trips/" + p1["id"], {"expenses": [{**dl, "acct_code": "6211/4031"}]}, vai="admin", method="PUT")
        m.db.expire_all()
        d_luu = m.db.query(M.TripExpense).filter(M.TripExpense.trip_id == p1["id"], M.TripExpense.item_key == khoan).one()
        dung(s == 200 and TK.tu_chon(d_luu) and d_luu.acct_code == "6211/4031", "mã KHÁC mã hiện → vẫn là mã tự chọn như cũ", d_luu.acct_code)
        goi("/api/trips/" + p1["id"], {"expenses": [{**dl, "acct_code": "614/4021"}]}, vai="admin", method="PUT")
        # (3b) dòng trả tiền mặt / tạm ứng của nhà cung cấp ghi rõ: KHÔNG đổi sang TK riêng (chứng từ thật vẫn 625 · 614)
        d4 = M.TripExpense(trip_id=T1.id, section="travel", item_key="x_food", qty=1, unit_price=5000, currency="LAK", paid_by_epl=True,
                           supplier_id=ncc2["id"], ghi_no=False, line_no=98)
        dung(TK.tk_dong_rieng(T1.company, d4, m.db) == TK.tk_dong(T1.company, d4, m.db) and not TK.tk_dong(T1.company, d4, m.db).endswith("/4021"),
             "dòng nhà cung cấp trả tiền mặt (không ghi nợ): giữ mã theo luật", TK.tk_dong_rieng(T1.company, d4, m.db))
        # (3a) phiếu chi quỹ mục V xe thuê: Nợ công nợ chủ xe theo TK riêng (4025); xe nhà không đổi
        from types import SimpleNamespace as NS
        from services import chi_muc_tune as CMT
        try:
            g2 = CMT.dung_goi(m.db, T2, "repair", NS(id="thu", ref_no="THU-PCSC"), [x for x in m.db.query(M.TripExpense).filter(
                M.TripExpense.trip_id == T2.id).all() if x.section == "repair"], 1)
            dung({e["DebitAccount"] for e in g2["Entries"]} == {"4025"}, "phiếu chi quỹ mục V xe thuê: Nợ 4025 (TK riêng chủ xe)",
                 {e["DebitAccount"] for e in g2["Entries"]})
        except Exception as e:                       # noqa: BLE001
            dung(False, "dựng gói phiếu chi quỹ mục V xe thuê", str(e)[:200])
        # (2) Bãi không thấy TK riêng: khách, phiếu
        s, ds = goi("/api/customers", vai="thabok")
        x = next(r for r in ds if r["id"] == kh.id)
        dung("acct_no" not in x and "acct_co" not in x, "Bãi xem danh sách khách: không có TK", sorted(x)[:6])
        s, ds = goi("/api/customers", vai="ketoan")
        x = next(r for r in ds if r["id"] == kh.id)
        dung(x.get("acct_no") == "1213" and x.get("acct_co") == "7081", "KT Thu/Chi xem danh sách khách: có TK riêng", (x.get("acct_no"), x.get("acct_co")))
        s, g = goi("/api/customers/" + kh.id, {"name": kh.name, "phone": "020 2"}, vai="thabok", method="PUT")
        dung(s == 200 and "acct_no" not in g, "Bãi sửa khách: kết quả trả về không có TK", (s, sorted(g)[:5] if isinstance(g, dict) else g))
        s, P2b = goi("/api/trips/" + p2["id"], vai="thabok")
        dung(s == 200 and "tk_rieng" not in P2b, "Bãi mở phiếu xe thuê: không có tk_rieng", s)
        # (6) sổ tài khoản lỗi (bản chụp không có mã riêng): sửa SĐT / phí không bị chặn vì TK cũ không đổi
        tk_cu = AC.lay_danh_muc
        AC.lay_danh_muc = lambda refresh=False: ([{"code": c, "name": t, "description": t, "postable": p_, "active": a}
                                                  for c, t, p_, a in SO if c not in ("6251", "4031", "6211", "4025")], "error", "giả lỗi")
        try:
            s, g = goi("/api/suppliers/" + ncc["id"], {"phone": "020 9", "acct_no": "6251", "acct_co": "4031"}, vai="ketoancp", method="PUT")
            dung(s == 200, "nhà cung cấp: sửa SĐT, gửi lại TK cũ khi sổ tài khoản lỗi → được", (s, ma(g)))
            s, g = goi("/api/owners/" + chu["id"], {"phone": "020 9", "fee_pct": 3, "acct_no": "6211", "acct_co": "4025"}, vai="ketoan", method="PUT")
            dung(s == 200, "chủ xe: sửa SĐT / phí, gửi lại TK cũ khi sổ tài khoản lỗi → được", (s, ma(g)))
            s, g = goi("/api/owners/" + chu["id"], {"acct_co": "4029"}, vai="ketoan", method="PUT")
            dung(s == 422 and ma(g) == "TK_SAI", "chủ xe: ĐỔI sang mã không dùng được → vẫn bị chặn", ma(g))
        finally:
            AC.lay_danh_muc = tk_cu

        print("== 5. xoá chủ xe")
        s, g = goi("/api/owners/" + chu["id"], vai="thabok", method="DELETE")
        dung(s == 403, "Bãi xoá chủ xe → 403", s)
        s, g = goi("/api/owners/" + chu["id"], vai="ketoan", method="DELETE")
        dung(s == 409 and ma(g) == "CON_XE" and g["detail"].get("loi_lo"), "Chủ xe còn xe → 409 CON_XE (có câu Lào)", ma(g))
        xe_thue.owner_id = None
        m.commit()
        s, g = goi("/api/owners/" + chu["id"], vai="ketoan", method="DELETE")
        dung(s == 409 and ma(g) == "CO_PHIEU", "Chủ xe đã có phiếu → 409 CO_PHIEU", ma(g))
        s, c2 = goi("/api/owners", {"name": "THU-CX hợp đồng"}, vai="ketoan")
        m.db.add(M.Contract(contract_no="THU-HD-TK-01", kind="thue_xe", owner_id=c2["id"]))
        m.commit()
        s, g = goi("/api/owners/" + c2["id"], vai="ketoan", method="DELETE")
        dung(s == 409 and ma(g) == "CON_HOP_DONG", "Chủ xe còn hợp đồng → 409 CON_HOP_DONG", ma(g))
        s, c3 = goi("/api/owners", {"name": "THU-CX nhập nhầm"}, vai="ketoan")
        s, g = goi("/api/owners/" + c3["id"], vai="ketoan", method="DELETE")
        dung(s == 200 and g.get("ok"), "Chủ xe nhập nhầm (chưa dùng) → xoá được", (s, g))
        s, ds = goi("/api/owners", vai="ketoan")
        dung(all(r["id"] != c3["id"] for r in ds), "Danh sách chủ xe không còn chủ xe vừa xoá")
        s, g = goi("/api/owners/" + c3["id"], vai="ketoan", method="DELETE")
        dung(s == 404, "Xoá lần nữa → 404", s)
        import datetime as _dt
        s, c4 = goi("/api/owners", {"name": "THU-CX đợt trả cũ"}, vai="ketoan")
        m.db.add(M.OwnerPayment(owner_id=c4["id"], pay_date=_dt.date.today()))
        m.commit()
        s, g = goi("/api/owners/" + c4["id"], vai="ketoan", method="DELETE")
        dung(s == 409 and ma(g) == "CO_GIAO_DICH" and g["detail"].get("loi_lo"), "Chủ xe có đợt trả cũ → 409 CO_GIAO_DICH (không lỗi 500)", (s, ma(g)))

        print("== 6. cờ danh mục chung bật: dữ liệu sai bị chặn TRƯỚC khi tạo bên danh mục chung (không để lại đối tượng mồ côi)")
        import os
        from services import doi_tuong_gls as DT
        from services import khach_gls as KG
        tao, tao_kh = [], []
        DT.tao, KG.tao = (lambda *a, **k: tao.append(a) or 999999999), (lambda *a, **k: tao_kh.append(a) or 999999999)
        cu = {k: os.environ.get(k) for k in ("EPL_NCC_GLS", "EPL_KHACH_GLS")}
        os.environ["EPL_NCC_GLS"] = os.environ["EPL_KHACH_GLS"] = "1"
        try:
            s, g = goi("/api/suppliers", {"name": "THU-NCC sai", "email": "sai"}, vai="ketoancp")
            dung(s == 422 and ma(g) == "EMAIL_SAI" and not tao, "Nhà cung cấp thư điện tử sai → 422, không tạo bên danh mục chung", (s, len(tao)))
            s, g = goi("/api/suppliers", {"name": "THU-NCC sai", "acct_co": "6251"}, vai="ketoancp")
            dung(s == 422 and ma(g) == "TK_SAI" and not tao, "Nhà cung cấp TK sai → 422, không tạo", (s, len(tao)))
            s, g = goi("/api/owners", {"name": "THU-CX sai", "acct_no": "4022"}, vai="ketoan")
            dung(s == 422 and ma(g) == "TK_SAI" and not tao, "Chủ xe TK sai → 422, không tạo", (s, len(tao)))
            s, g = goi("/api/owners", {"name": "THU-CX sai", "fee_pct": 150}, vai="ketoan")
            dung(s == 422 and ma(g) == "PHI_SAI" and not tao, "Chủ xe phí 150 % → 422, không tạo", (s, len(tao)))
            s, g = goi("/api/customers", {"name": "THU-KH sai", "acct_no": "708"}, vai="ketoan")
            dung(s == 422 and ma(g) == "TK_SAI" and not tao_kh, "Khách TK sai → 422, không tạo", (s, len(tao_kh)))
            s, g = goi("/api/customers", {"name": "THU-KH sai", "acct_no": "1213"}, vai="thabok")
            dung(s == 403 and ma(g) == "TK_KHACH_KE_TOAN" and not tao_kh, "Bãi thêm khách kèm TK → 403, không tạo", (s, len(tao_kh)))
        finally:
            for k, v in cu.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    K.ket_thuc("THỬ TK RIÊNG + XOÁ CHỦ XE")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("THỬ TK RIÊNG + XOÁ CHỦ XE")
