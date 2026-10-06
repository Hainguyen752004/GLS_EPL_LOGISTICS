# -*- coding: utf-8 -*-
"""Thử BA MÓN NỢ KỸ THUẬT đã dọn 22/09 (mục 3 tệp CONG_VIEC_CHO_ANH_KHAMPLA_CHOT) — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_no_ky_thuat.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; xe, tài xế (kèm tài khoản), khách, DO thử dựng mới ở một
tháng d7 chưa có DO; không gọi mạng. (Trước 06/10 bài gọi máy 8010 và đọc / sửa dữ liệu thật: ảnh xe đầu danh sách…)

  · **3.1 — máy chủ không trả giá bán cho vai không được thấy.** `/api/trips`, `/api/bao-cao/theo-doi`, chi tiết một phiếu, phiếu
    in (tạm ứng · phiếu thu · phiếu lĩnh): Bãi, tài xế, thủ kho không nhận khoá tiền bán; Bãi không nhận cả tiền chi; kế toán đủ.
  · **3.2 — ảnh xe lưu được**, dùng lại đúng chỗ chứa tệp của phiếu; **ảnh tài xế** cùng bộ máy (chuyển từ kiem/thu_chot_22_09.py,
    nay ở kiem/loi_thoi/).
  · **3.4 — ô "Việc của tôi" của KT Doanh thu** đếm phiếu đã khoá chưa tạo SO + SO chưa thu đủ (không còn cờ invoiced).
  · Mã kế toán cấu hình (mã hàng khách gửi, mã giá vốn) chỉ Sếp đặt — kế toán đặt → 403 (từ kiem/thu_chot_22_09.py; bài không ghi
    thử cấu hình: đó là dòng đang có trên d7).
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ

dung, phai, ma = K.dung, K.phai, K.ma
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000100ffff03000006000557bfabd4000000"
    "0049454e44ae426082")
KHOA_BAN = ("price", "price_ccy", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price")
TINH_BAN = ("doanh_thu", "doanh_thu_lak", "lai", "lai_lak", "tien_thue", "tra_chu_xe", "da_thu_lak", "con_lai_lak")
TINH_CHI = ("tong_chi_lak", "chi", "tan_tinh")


def main():
    with K.Khung() as m:
        goi = m.goi
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        xe, xe2 = m.xe("THU-NK-01"), m.xe("THU-NK-02")
        tx = m.tai_xe("ທ້າວ ທົດລອງ ໜີ້", tai_khoan=True)
        tx2 = m.tai_xe("ທ້າວ ທົດລອງ ໜີ້ 2")
        kh = m.khach("ລູກຄ້າ ທົດລອງ ໜີ້")
        m.commit()
        s, p1 = goi("/api/trips", {"doc_no": "THU-NK-1/EPL", "kind": "giao", "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": kh.id,
                                   "doc_date": m.ngay(3).isoformat(), "price": 12, "price_ccy": "USD", "weight_origin": 30,
                                   "expenses": [{"section": "travel", "item_key": "x_phone", "qty": 1, "unit_price": 150000, "paid_by_epl": True},
                                                {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "paid_by_epl": True}]},
                   "admin")
        phai(s, 200, "Sếp lập DO thử 1 (12 USD/t, điện thoại tiền mặt, tiền nước)", p1)
        s, p2 = goi("/api/trips", {"doc_no": "THU-NK-2/EPL", "kind": "giao", "vehicle_id": xe2.id, "driver_id": tx2.id, "customer_id": kh.id,
                                   "doc_date": m.ngay(4).isoformat(), "price": 10, "price_ccy": "USD", "weight_origin": 20}, "admin")
        phai(s, 200, "Sếp lập DO thử 2 (không dòng chi)", p2)

        print("== 3.1 giá bán không ra khỏi máy chủ")
        for vai, ten in (("thabok", "Bãi"), (tx.username, "Tài xế"), ("khotb", "Thủ kho")):
            s, ds = goi("/api/trips", vai=vai)
            phai(s, 200, "%s gọi /api/trips" % ten, ds)
            lo = sorted({k for p in ds for k in KHOA_BAN if k in p})
            lo_t = sorted({k for p in ds for k in TINH_BAN if k in (p.get("tinh") or {})})
            dung(not lo and not lo_t, "%s không nhận khoá tiền bán (%d phiếu)" % (ten, len(ds)), (lo, lo_t))
            if not ds:
                continue
            con = sorted({k for k in TINH_CHI if k in (ds[0].get("tinh") or {})})
            if vai == "thabok":
                # anh Khampla A2 (23/09): Bãi không thấy cả tiền CHI (tổng chi, đơn giá, tỷ giá); tài xế vẫn thấy tạm ứng của mình
                lo_chi = sorted({k for p in ds for k in ("tong_chi_lak", "chi") if k in (p.get("tinh") or {})})
                lo_dg = [d for p in ds for d in (p.get("expenses") or []) if "unit_price" in d]
                dung(not lo_chi and not lo_dg and not any("rate_usd" in p for p in ds), "Bãi không nhận tiền chi (tổng chi, đơn giá, tỷ giá)",
                     lo_chi)
            elif vai == "khotb":
                # thủ kho không thấy giá vốn kho (chủ dự án 30/09) — tổng chi có giá kho bên trong nên cũng bỏ
                dung(not ({"tong_chi_lak", "chi"} & set(ds[0].get("tinh") or {})), "Thủ kho không nhận tổng chi (lộ giá kho)", con)
            else:
                dung([p["doc_no"] for p in ds] == ["THU-NK-1/EPL"] and len(con) == len(TINH_CHI),
                     "Tài xế chỉ thấy phiếu của mình, phần CHI PHÍ giữ nguyên", (len(ds), con))

        s, ds = goi("/api/bao-cao/theo-doi", vai="thabok")
        phai(s, 200, "Bãi mở báo cáo Theo dõi", None)
        dung(not sorted({k for p in ds for k in KHOA_BAN if k in p}), "Báo cáo Theo dõi không trả tiền bán cho Bãi")

        # rà giao diện 23/09: phiếu in (tạm ứng, phiếu thu, phiếu lĩnh) từng là đường lộ tiền cho Bãi
        s, pc = goi("/api/trips/%s/phieu-chi" % p1["id"], vai="thabok"); phai(s, 200, "Bãi mở phiếu chi tạm ứng để in", pc)
        dung(pc["tong_lak"] is None and all("unit_price" not in d and "tien_lak" not in d for d in pc["dong"]),
             "Phiếu tạm ứng gửi cho Bãi không có đơn giá / thành tiền / tổng", pc.get("tong_lak"))
        s, g = goi("/api/trips/%s/phieu-thu" % p1["id"], vai="thabok")
        dung(s == 409 and "hệ kế toán" in ((g or {}).get("detail") or {}).get("loi", ""),
             "Bãi mở phiếu thu tiền khách → 409, câu báo chỉ sang hệ kế toán", (s, ma(g)))
        s, vs = goi("/api/trips/%s/vouchers" % p1["id"], vai="thabok")
        dung(s == 200 and all(v.get("amount_lak") is None for v in (vs or [])), "Phiếu lĩnh / tạm ứng gửi cho Bãi không có số tiền", len(vs or []))
        s, pc2 = goi("/api/trips/%s/phieu-chi" % p1["id"], vai="ketoan")
        dung(s == 200 and pc2["tong_lak"] == 150000, "Kế toán vẫn thấy tổng tạm ứng (150.000 điện thoại tiền mặt)", pc2.get("tong_lak"))

        s, ds = goi("/api/trips", vai="ketoan")
        k1 = next((p for p in ds if p["id"] == p1["id"]), None)
        dung(k1 and k1.get("price") == 12 and k1.get("price_ccy") == "USD" and k1["tinh"].get("doanh_thu") is not None,
             "Kế toán vẫn thấy đủ tiền bán (phép lọc không cắt nhầm)", k1 and (k1.get("price"), k1.get("price_ccy")))
        s, g = goi("/api/trips/%s" % p1["id"], vai="thabok")
        dung("price" not in g and "doanh_thu" not in g["tinh"] and "so_ke_toan" not in g and "but_toan_cho" not in g,
             "Xem chi tiết một phiếu cũng lọc đúng như danh sách (cả SO, bút toán chờ)", [k for k in g if "so_" in k])
        for vai in ("thabok", "ketoan", "admin"):
            s, g = goi("/api/trips/%s" % p1["id"], vai=vai)
            lo = [k for k in ("invoiced", "inv_no", "invoice_id", "invoiced_date", "last_paid_date") if k in g]
            dung(not lo and "da_tao_so" in g, "%s: gói phiếu không còn cờ hoá đơn trang tạm, có 'đã tạo SO'" % vai, lo)

        print("== 3.2 ảnh xe (xe thử)")
        s, g = m.gui_tep("/api/vehicles/%s/anh" % xe.id, "thu-anh-xe.png", PNG_1x1, "image/png", tx.username)
        phai(s, 403, "Tài xế đưa ảnh xe lên → bị chặn", g)
        s, ds_anh = m.gui_tep("/api/vehicles/%s/anh" % xe.id, "thu-anh-xe.png", PNG_1x1, "image/png", "thabok")
        phai(s, 200, "Bãi đưa ảnh xe THU-NK-01 lên", ds_anh)
        try:
            a = ds_anh[0]
            dung(a["chinh"], "Ảnh đầu tiên tự thành ảnh đại diện", a["filename"])
            s, du = m.tai(a["url"], "thabok")
            dung(s == 200 and du == PNG_1x1, "Tải ảnh về đúng bằng tệp đã gửi lên", "%s · %d byte" % (s, len(du or b"")))
            s, _ = m.tai(a["url"])
            dung(s == 401, "Mở ảnh khi chưa đăng nhập → bị chặn", s)
            s, xs = goi("/api/vehicles", vai="thabok")
            s2, ct = goi("/api/vehicles/%s" % xe.id, vai="thabok")
            dung(next(v for v in xs if v["id"] == xe.id).get("anh_chinh") and len(ct.get("anh") or []) == 1,
                 "Danh sách và hồ sơ xe đều mang ảnh")
        finally:
            s, con = goi("/api/anh-xe/%s" % ds_anh[0]["id"], vai="thabok", method="DELETE")      # xoá tệp trên đĩa (rollback không xoá)
        dung(s == 200 and not con, "Xoá ảnh thử → không còn ảnh nào", s)

        print("== 3.2b ảnh tài xế (tài xế thử — từ kiem/thu_chot_22_09.py)")
        s, g = m.gui_tep("/api/drivers/%s/anh" % tx.id, "anh-tx.png", PNG_1x1, "image/png", tx.username)
        phai(s, 403, "Tài xế tự đưa ảnh lên → bị chặn", g)
        s, ds_anh = m.gui_tep("/api/drivers/%s/anh" % tx.id, "anh-tx.png", PNG_1x1, "image/png", "thabok")
        phai(s, 200, "Bãi đưa ảnh tài xế lên", ds_anh)
        try:
            a = ds_anh[0]
            s, du = m.tai(a["url"], "thabok")
            dung(a["chinh"] and s == 200 and du == PNG_1x1, "Ảnh tài xế tải về đúng tệp, ảnh đầu là ảnh đại diện")
            s, tl = goi("/api/drivers", vai="thabok")
            s2, ct = goi("/api/drivers/%s" % tx.id, vai="thabok")
            dung(next(x for x in tl if x["id"] == tx.id).get("anh_chinh") and len(ct.get("anh") or []) == 1,
                 "Danh sách và hồ sơ tài xế đều mang ảnh")
        finally:
            s, _ = goi("/api/anh-tai-xe/%s" % ds_anh[0]["id"], vai="thabok", method="DELETE")
        dung(s == 200, "Xoá ảnh tài xế thử", s)

        print("== 3.4 việc của tôi của KT Doanh thu")
        s, g = goi("/api/trips/%s/transport-status" % p2["id"], {"status": "arrived", "weight_dest": 20, "back_date": m.ngay(5).isoformat()},
                   "admin")
        phai(s, 200, "DO thử 2 về tới", g)
        s, g = goi("/api/trips/%s/khoa" % p2["id"], {"xac_nhan": True}, "ketoan"); phai(s, 200, "Kế toán khoá DO thử 2 (chưa tạo SO)", g)
        s, tq = goi("/api/bao-cao/xu-huong?thang=" + m.thang, vai="doanhthu")
        phai(s, 200, "KT Doanh thu mở Tổng quan tháng thử", None)
        xn = tq["xem_nhanh"]
        dung(xn["viec_toi"] >= 1 and xn.get("viec_phieu"), "Ô Việc của tôi đếm phiếu đã khoá chưa tạo SO, bấm mở thẳng phiếu",
             (xn["viec_toi"], xn.get("viec_phieu")))
        s, tq2 = goi("/api/bao-cao/tong-quan", vai="thabok")
        dung(s == 200 and "doanh_thu_lak" not in tq2, "Tổng quan của Bãi không có doanh thu", s)

        print("== mã kế toán cấu hình (từ kiem/thu_chot_22_09.py)")
        s, g = goi("/api/ke-toan/cau-hinh", {"ma_gia_von": "632"}, vai="ketoan", method="PUT")
        dung(s == 403, "Kế toán đặt mã giá vốn / mã hàng khách gửi → 403 (chỉ Sếp)", (s, ma(g)))
        s, ch = goi("/api/ke-toan/cau-hinh", vai="admin")
        dung(s == 200 and "ma_hang_khach_gui" in ch and "ma_gia_von" in ch, "Sếp xem được hai ô mã cấu hình", s)
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
        import os
        from services import tep as TEP
        for d in (os.path.join(TEP.TEP_DIR, "xe", xe.id), os.path.join(TEP.TEP_DIR, "tai-xe", tx.id)):
            try:
                os.rmdir(d)                             # thư mục ảnh rỗng của xe / tài xế thử (tệp đã xoá qua API; rollback không xoá đĩa)
            except OSError:
                pass
    K.ket_thuc("NỢ KỸ THUẬT")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("NỢ KỸ THUẬT")
