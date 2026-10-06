# -*- coding: utf-8 -*-
"""Thử PHIẾU ĐỀ NGHỊ theo DO (sếp 30/09): đề nghị chi theo bước, đề nghị thu khi DO xong — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_de_nghi.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; xe / tài xế / khách / DO thử dựng mới ở một tháng d7
chưa có DO; không gọi mạng — kho QLSX báo cấp dầu và bút toán gửi sang hệ kế toán đều GIẢ LẬP (06/10: trước đây bài gọi máy 8011
thật, mỗi lần khoá là một lần ghi thật sang DB demo; luật khoá đã đổi: dầu kho chưa cấp thì không khoá được).

Phải thấy:
  · màn Đề nghị theo DO: DO mới có mục III, IV đang chờ; lập phiếu đề nghị xuất kho nhiên liệu → hiện ngay ở DO đó;
  · màn Phiếu đề nghị chi tìm được tờ theo số DO; Bãi xem DO nhưng không nhận tiền; tài xế bị chặn;
  · dầu kho CHƯA CẤP thì Khoá phiếu bị 409 DAU_KHO_CHUA_CAP, không lập đề nghị thu (luật hiện hành);
  · kho QLSX báo đã cấp (cổng bàn giao, giả lập) → dòng dầu mang phiếu kho + giá vốn → khoá được: máy lập PHIẾU ĐỀ NGHỊ THU (PDT)
    đúng cước, đúng tiền tệ (USD), và bút toán xuất nội bộ 625/1371 GỬI ĐI (bộ giả nhận, không ra mạng); (06/10 tối) tiền nước trả
    cùng lương → bút toán cung_luong 625/4201 cũng gửi lúc khoá;
  · mở khoá → rút tờ chưa gửi, bút toán đã gửi được ĐẢO (bộ giả); khoá lại → tờ mới; cờ da_day đánh tay không chặn mở khoá,
    không đổi trạng thái — chỉ SO đã tạo bên hệ anh Tune chặn (DA_TAO_SO);
  · xoá DO có dầu đã cấp ở kho QLSX → 409 DA_CAP_KHO_QLSX; kho huỷ phiếu xuất → xoá được, không còn tờ nào của DO.
"""
import urllib.parse

import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ

dung, phai, ma = K.dung, K.phai, K.ma
SO_KHO = "1368-XKK-THU-DN-0001"


def main():
    with K.Khung() as m:
        goi = m.goi

        def dong_do(vai, so):
            s, g = goi("/api/de-nghi-theo-do?thang=%s&q=%s" % (m.thang, urllib.parse.quote(so)), vai=vai)
            phai(s, 200, "GET /api/de-nghi-theo-do (%s)" % vai, g)
            return g, next((x for x in g["ds"] if x["doc_no"] == so), None)

        def dong_thu(so):
            s, g = goi("/api/de-nghi-thu?thang=%s&q=%s" % (m.thang, urllib.parse.quote(so)), vai="ketoan")
            phai(s, 200, "GET /api/de-nghi-thu", g)
            return next((x for x in g["ds"] if x["doc_no"] == so), None)

        def but_toan(pid):
            s, g = goi("/api/but-toan-cho?trip_id=" + pid, vai="ketoan")
            phai(s, 200, "đọc bút toán chờ", g)
            return [b for b in g["ds"] if b["nguon"] == "xuat_noi_bo"]

        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        xe = m.xe("THU-DN-01")
        tx = m.tai_xe("ທ້າວ ທົດລອງ ເດີນ")
        kh = m.khach("ລູກຄ້າ ທົດລອງ ເດີນ")
        tb = m.diem_kho("KHO-TB")
        m.commit()

        s, g = goi("/api/de-nghi-theo-do", vai="tx01"); phai(s, 403, "Tài xế không vào màn Đề nghị theo DO", g)
        s, g = goi("/api/de-nghi-thu", vai="thabok"); phai(s, 403, "Bãi không vào Phiếu đề nghị thu (tiền cước)", g)

        so = "THU-DN-%s/EPL" % m.thang
        s, p = goi("/api/trips", {"doc_no": so, "kind": "giao", "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": kh.id,
                                  "doc_date": m.ngay(6).isoformat(), "price": 12, "price_ccy": "USD", "weight_origin": 40,
                                  "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 100, "place_id": tb.id, "paid_by_epl": True},
                                               {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "paid_by_epl": True}]},
                   "admin")
        phai(s, 200, "Lập phiếu thử: giao, 40 t × 12 USD, 100 L dầu kho, tiền nước", p)
        pid = p["id"]

        print("== 1. đề nghị theo DO, đề nghị xuất kho nhiên liệu")
        g, x = dong_do("ketoan", so)
        dung(x is not None and x["thu"]["trang_thai"] == "cho_khoa", "DO mới: đề nghị thu 'chờ khoá phiếu'")
        dung(set(x["muc"]) == {"fuel", "travel"} and x["muc"]["travel"]["tien_lak"] == 60000, "Mục III, IV có dòng — kế toán thấy tiền mục IV",
             x["muc"])
        dung(not x["nhien_lieu"] and x["ho_so"]["tong"] >= 1, "Chưa có đề nghị nhiên liệu; hồ sơ có tờ DO", x["ho_so"])
        s, vs = goi("/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, "thabok"); phai(s, 200, "Bãi lập phiếu đề nghị xuất kho nhiên liệu", vs)
        g, x = dong_do("ketoan", so)
        dung(len(x["nhien_lieu"]) == 1 and x["nhien_lieu"][0]["status"] == "cho" and x["nhien_lieu"][0]["qty_l"] == 100,
             "Đề nghị nhiên liệu hiện ngay ở DO: 100 L, chờ cấp")
        s, ds = goi("/api/vouchers?trang_thai=&q=" + urllib.parse.quote(so), vai="thabok")
        dung(s == 200 and any(v["trip_doc_no"] == so and v["kind"] == "fuel" for v in ds), "Phiếu đề nghị chi: tìm được tờ theo số DO")
        g, xb = dong_do("thabok", so)
        dung("doanh_thu" not in xb["thu"] and all("tien_lak" not in mm for mm in xb["muc"].values()), "Bãi xem DO nhưng không nhận tiền")

        print("== 2. DO xong: xe về, có POD — dầu kho chưa cấp thì chưa khoá được")
        s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": 39.5, "back_date": m.ngay(7).isoformat(),
                                                            "pod_no": "POD-" + so, "pod_receiver": "ນາງ ທົດລອງ"}, "admin")
        phai(s, 200, "Xe về: cân cuối 39,5 t, có số POD", g)
        x = dong_thu(so)
        dung(x is not None and x["trang_thai"] == "cho_khoa" and x["pdt"] is None, "Xe về mà chưa khoá: chưa có đề nghị thu")
        s, g = goi("/api/trips/%s/de-nghi-thu" % pid, {}, "ketoan"); phai(s, 409, "Chưa khoá thì không lập đề nghị thu", g)
        s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, "ketoan")
        dung(s == 409 and ma(g) == "DAU_KHO_CHUA_CAP", "Dầu kho chưa cấp → Khoá phiếu bị 409 DAU_KHO_CHUA_CAP (luật hiện hành)", (s, ma(g)))
        x = dong_thu(so)
        s, pp = goi("/api/trips/" + pid, vai="ketoan")
        dung(not pp["locked"] and x["pdt"] is None and not but_toan(pid), "Bị chặn: phiếu chưa khoá, không có đề nghị thu, không bút toán")

        print("== 3. kho QLSX báo đã cấp (cổng bàn giao, giả lập) → khoá được")
        v = vs[0]
        s, ct = goi("/api/handover/fuel-vouchers/" + v["id"])
        phai(s, 200, "Kho QLSX đọc tờ đề nghị (cổng bàn giao)", ct)
        ct = ct["data"]
        s, g = goi("/api/handover/fuel-vouchers/%s/issued" % v["id"],
                   {"source_ref": ct["source_ref"], "stock_doc_no": SO_KHO, "stock_doc_id": 99101, "qty_l": 100, "issued_by": "thu",
                    "lines": [{"item_code": "EPLNL-diesel", "qty": 100, "unit_cost": 26500}]})
        phai(s, 200, "Kho QLSX báo đã cấp 100 L, giá vốn 26.500", g)
        s, pp = goi("/api/trips/" + pid, vai="ketoan")
        dau = [e for e in pp["expenses"] if e["section"] == "fuel"]
        dung(dau and all(e["stock_move_id"] == "qlsx:" + SO_KHO and abs((e["unit_price"] or 0) - 26500) < 1e-9 for e in dau),
             "Dòng dầu mang phiếu kho qlsx:<số> và giá vốn kho", [(e["stock_move_id"], e["unit_price"]) for e in dau])
        n_bt = len(K.GIA.but_toan)
        s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, "ketoan"); phai(s, 200, "Kế toán khoá phiếu", g)
        x = dong_thu(so)
        dung(x["trang_thai"] == "cho_gui" and x["pdt"] and x["pdt"]["so"].startswith("PDT/"), "Khoá → máy lập phiếu đề nghị thu, chờ gửi",
             x["pdt"] and x["pdt"]["so"])
        dung(x["ccy"] == "USD" and abs(x["doanh_thu"] - 474) < 0.01 and x["pdt"]["tien_te"] == "USD" and abs(x["pdt"]["tien"] - 474) < 0.01,
             "Đề nghị thu đúng cước 39,5 t × 12 = 474 USD, đúng tiền tệ phiếu", "%s %s" % (x["doanh_thu"], x["ccy"]))
        s, t = goi("/api/trips/%s/de-nghi-thu" % pid, vai="ketoan")
        dung(s == 200 and t["pod_no"] == "POD-" + so and t["customer_name"] == p["customer_name"] and t["tan_tinh"] == 39.5,
             "Tờ in: khách, số POD, tấn tính cước")
        s, r = goi("/api/chung-tu?trip_id=" + pid, vai="ketoan")
        dung(any(c["loai"] == "PDT" and c["loai_ten"] == "Phiếu đề nghị thu" for c in r["ds"]), "Tờ PDT nằm trong hồ sơ gửi kế toán")
        bt = but_toan(pid)
        dong = [d for b in bt for d in b["dong"]]
        # 06/10 tối: DO xe nhà có tiền nước trả cùng lương → thêm bút toán cung_luong (Nợ 625 / Có 4201) cùng lúc khoá — đếm theo SourceRef
        gui = [z for z in K.GIA.but_toan[n_bt:] if z[0] == "POST" and not z[1].endswith("/reverse")]
        gui_xk = [z for z in gui if str((z[2] or {}).get("SourceRef", "")).startswith("EPLLAO-xuat_noi_bo-")]
        gui_cl = [z for z in gui if (z[2] or {}).get("SourceRef") == "EPLLAO-cung_luong-" + pid]
        dung(len(bt) == 1 and bt[0]["status"] == "da_gui" and [(d["no"], d["co"], d["tien"]) for d in dong] == [("625", "1371", 2650000)]
             and len(gui_xk) == 1, "Bút toán xuất nội bộ 625/1371 = 100 × 26.500 đã GỬI (bộ giả nhận một gói, không ra mạng)",
             [(b["status"], b.get("so_ben_ke_toan")) for b in bt])
        en = (gui_cl[0][2] or {}).get("Entries") or [] if gui_cl else []
        dung(len(gui_cl) == 1 and len(gui) == 2 and [(e.get("DebitAccount"), e.get("CreditAccount"), e.get("Amount")) for e in en] == [("625", "4201", 60000)],
             "Bút toán trả cùng lương Nợ 625 / Có 4201 = 60.000 (tiền nước) cũng GỬI lúc khoá — đúng hai gói", [z[2].get("SourceRef") for z in gui])
        id1 = x["pdt"]["id"]

        print("== 4. mở khoá → rút tờ chưa gửi, đảo bút toán; khoá lại → tờ mới")
        n_bt = len(K.GIA.but_toan)
        s, g = goi("/api/trips/%s/mo-khoa" % pid, {}, "ketoan"); phai(s, 200, "Kế toán mở khoá (tờ chưa gửi)", g)
        x = dong_thu(so); dung(x["pdt"] is None and x["trang_thai"] == "cho_khoa", "Mở khoá → tờ đề nghị thu chưa gửi được rút")
        dao = [z for z in K.GIA.but_toan[n_bt:] if z[1].endswith("/reverse")
               and str((z[2] or {}).get("SourceRef", "")).startswith("EPLLAO-xuat_noi_bo-")]
        dung(len(dao) == 1 and not [b for b in but_toan(pid) if b["status"] == "da_gui"],
             "Mở khoá → bút toán đã gửi được gửi ĐẢO (bộ giả), không còn bản 'đã gửi'", [b["status"] for b in but_toan(pid)])
        s, g = goi("/api/trips/%s/khoa" % pid, {"xac_nhan": True}, "ketoan"); phai(s, 200, "Khoá lại", g)
        x = dong_thu(so)
        # tờ cũ chưa gửi đã rút nên số có thể dùng lại (số = lớn nhất còn lại + 1) — tờ mới là bản ghi mới
        dung(x["pdt"] and x["pdt"]["id"] != id1, "Khoá lại → tờ đề nghị thu mới (bản ghi mới)", x["pdt"]["so"])
        # 01/10: "đã gửi" là đã tạo SO bên hệ anh Tune (da_tao_so) — cờ da_day của đường đẩy sang trang tạm không còn ý nghĩa
        s, g = goi("/api/chung-tu/%s/da-day" % x["pdt"]["id"], {"da_day": True}, "ketoan"); phai(s, 200, "Đánh dấu tay tờ đã đối chiếu (da_day)", g)
        x = dong_thu(so); dung(x["trang_thai"] == "cho_gui", "Trạng thái vẫn 'chờ gửi' — chỉ lần gửi SO sang hệ anh Tune mới đổi", x["trang_thai"])
        s, g = goi("/api/trips/%s/mo-khoa" % pid, {}, "ketoan"); phai(s, 200, "Chưa có SO bên hệ kế toán → kế toán mở khoá được (da_day không chặn)", g)
        x = dong_thu(so); dung(x["pdt"] is None and x["trang_thai"] == "cho_khoa", "Mở khoá → tờ đề nghị thu được rút (kể cả đã đánh da_day)")

        print("== 5. xoá DO có dầu đã cấp ở kho QLSX")
        s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE")
        dung(s == 409 and ma(g) == "DA_CAP_KHO_QLSX", "Xoá DO có dầu đã cấp ở kho QLSX → 409 DA_CAP_KHO_QLSX", (s, ma(g)))
        s, g = goi("/api/handover/fuel-vouchers/%s/cancelled" % v["id"], {"stock_doc_no": SO_KHO, "reason": "thử: huỷ phiếu xuất",
                                                                         "cancelled_by": "thu"})
        phai(s, 200, "Kho QLSX huỷ phiếu xuất (giả lập) → tờ đề nghị về chờ cấp", g)
        s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử", g)
        s, r = goi("/api/chung-tu?trip_id=" + pid, vai="ketoan")
        dung(s == 200 and not r["ds"], "Xoá phiếu thử → không còn tờ nào của nó", len(r.get("ds") or []))
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("THỬ ĐỀ NGHỊ")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:                           # bước bắt buộc hỏng (đã in SAI) — giao dịch đã ROLLBACK
        print(e)
        K.ket_thuc("THỬ ĐỀ NGHỊ")
