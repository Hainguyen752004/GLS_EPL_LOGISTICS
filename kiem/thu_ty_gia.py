# -*- coding: utf-8 -*-
"""Thử màn TỶ GIÁ — ອັດຕາແລກປ່ຽນ — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_ty_gia.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; xe, tài xế, khách, DO thử dựng mới ở một tháng d7 chưa có DO;
không gọi mạng. Trước 06/10 bài gọi máy 8010 rồi tự TRẢ tỷ giá về số cũ — hỏng giữa chừng hai lần (23/09) để sót USD sai trong DB dùng
chung; nay ROLLBACK lo việc đó.

LƯU Ý — bài SỬA năm dòng tỷ giá ĐANG CÓ trên d7 (trong giao dịch, rollback cuối bài): suốt lúc bài chạy (vài giây), ai lưu tỷ giá trên
máy 8011 sẽ phải chờ. Đừng chạy lúc người khác đang sửa màn Tỷ giá.

Tỷ giá là con số đi thẳng vào tiền, nên chỗ này phải chắc: ai được sửa, sửa rồi có ghi lịch sử không, gõ lại đúng số cũ có đẻ ra dòng
rác không, và — quan trọng nhất — **sửa tỷ giá có làm đổi con số trên phiếu đã lập hay không** (không được đổi: phiếu khoá tỷ giá riêng).
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ

dung, phai, ma = K.dung, K.phai, K.ma


def main():
    with K.Khung() as m:
        goi = m.goi
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        xe, xe2 = m.xe("THU-TG-01"), m.xe("THU-TG-02")
        tx, tx2 = m.tai_xe("ທ້າວ ທົດລອງ ອັດຕາ"), m.tai_xe("ທ້າວ ທົດລອງ ອັດຕາ 2")
        kh = m.khach("ລູກຄ້າ ທົດລອງ ອັດຕາ")
        m.commit()

        print("== 1. ai xem, ai sửa")
        s, g = goi("/api/rates"); phai(s, 401, "Chưa đăng nhập mà hỏi tỷ giá → bị chặn", g)
        s, goc = goi("/api/rates", vai="thabok"); phai(s, 200, "Bãi XEM được tỷ giá (chi phí của họ có VND, THB)", None)
        dung(goc.get("LAK") == 1.0 and all(x in goc for x in ("USD", "THB", "VND", "CNY")), "Đủ bốn tỷ giá + Kíp gốc = 1",
             " · ".join("%s=%s" % (k, v) for k, v in goc.items()))
        s, g = goi("/api/rates", {"USD": 25000}, vai="thabok", method="PUT"); phai(s, 403, "Bãi SỬA tỷ giá → bị từ chối", g)
        s, g = goi("/api/rates", {"USD": 25000}, vai="tx01", method="PUT"); phai(s, 403, "Tài xế sửa tỷ giá → bị từ chối", g)
        s, ct = goi("/api/rates/chi-tiet", vai="ketoan"); phai(s, 200, "Màn Tỷ giá đọc được bảng chi tiết", None)
        s, g = goi("/api/rates/chi-tiet", vai="thabok"); phai(s, 403, "Bãi không có màn Tỷ giá → bảng chi tiết bị chặn", g)
        dung(ct["goc"] == "LAK" and len(ct["ds"]) == 4, "Bảng chi tiết có 4 loại tiền, gốc là Kíp", len(ct["ds"]))

        print("== 2. phiếu lập TRƯỚC khi đổi tỷ giá")
        s, p0 = goi("/api/trips", {"doc_no": "THU-TG-0/EPL", "kind": "gom", "doc_date": m.ngay(20).isoformat(), "vehicle_id": xe.id,
                                   "driver_id": tx.id, "customer_id": kh.id, "price": 12, "price_ccy": "USD", "weight_origin": 30}, vai="admin")
        phai(s, 200, "Sếp lập phiếu USD trước khi đổi tỷ giá", p0)
        s, p0 = goi("/api/trips/" + p0["id"], vai="ketoan")
        dt_truoc, rate_truoc = p0["tinh"]["doanh_thu_lak"], p0["rate_usd"]

        print("== 3. sửa và ghi lịch sử")
        moi = round(goc["USD"] * 1.1)
        s, g = goi("/api/rates", {"USD": moi, "ap_dung_tu": m.ngay(21).isoformat(), "ghi_chu": "thử bộ kiểm"}, vai="ketoan", method="PUT")
        phai(s, 200, "Kế toán đặt tỷ giá USD mới (%s → %s)" % (goc["USD"], moi), g)
        dung(g["USD"] == moi and g["_da_doi"] == ["USD"], "Nói rõ vừa đổi những mã nào", g.get("_da_doi"))
        s, ct = goi("/api/rates/chi-tiet", vai="ketoan")
        u = next(x for x in ct["ds"] if x["code"] == "USD")
        dung(u["rate_to_lak"] == moi and u["truoc"] == goc["USD"] and u["by_user"], "Thẻ USD nhớ số lần trước và người đặt",
             (u["truoc"], u["rate_to_lak"], u["by_user"]))
        ls = [x for x in ct["lich_su"] if x["code"] == "USD"]
        dung(ls and ls[0]["rate_cu"] == goc["USD"] and ls[0]["ghi_chu"] == "thử bộ kiểm" and ls[0]["nguon"] == "tay",
             "Lịch sử ghi lại lần đổi kèm số cũ, ghi chú, nguồn", ls[:1])

        print("== 4. gõ lại đúng số cũ → không đẻ dòng rác; số sai bị chặn")
        truoc_n = len(ct["lich_su"])
        s, g = goi("/api/rates", {"USD": moi}, vai="ketoan", method="PUT")
        phai(s, 200, "Gõ lại ĐÚNG số đang dùng", g)
        s, ct2 = goi("/api/rates/chi-tiet", vai="ketoan")
        dung(g["_da_doi"] == [] and len(ct2["lich_su"]) == truoc_n, "Không đổi gì: danh sách đã đổi rỗng, lịch sử không tăng",
             (g["_da_doi"], truoc_n, len(ct2["lich_su"])))
        for xau, ten in ((0, "0"), (-5, "số âm"), ("abc", "chữ")):
            s, g = goi("/api/rates", {"THB": xau}, vai="ketoan", method="PUT"); phai(s, 422, "Tỷ giá %s → bị từ chối" % ten, g)
        # 01/10: USD từng bị đặt 1 Kíp (−99,995 %) không ai chặn — đổi quá ngưỡng mà chưa xác nhận thì máy chủ không ghi
        s, g = goi("/api/rates", {"USD": 1}, vai="ketoan", method="PUT"); phai(s, 409, "USD đổi −99,99 % chưa xác nhận → bị chặn", g)
        s, ct3 = goi("/api/rates/chi-tiet", vai="ketoan")
        dung(next(x for x in ct3["ds"] if x["code"] == "USD")["rate_to_lak"] == moi and len(ct3["lich_su"]) == truoc_n,
             "Bị chặn thì không ghi tỷ giá, không đẻ dòng lịch sử")

        print("== 5. phiếu cũ giữ tỷ giá của nó; phiếu mới lấy số mới")
        s, p1 = goi("/api/trips/%s" % p0["id"], vai="ketoan")
        dung(p1["rate_usd"] == rate_truoc and p1["tinh"]["doanh_thu_lak"] == dt_truoc, "Phiếu đã lập GIỮ tỷ giá và doanh thu quy Kíp",
             (p1["rate_usd"], rate_truoc, p1["tinh"]["doanh_thu_lak"], dt_truoc))
        s, pm = goi("/api/trips", {"doc_no": "THU-TG-1/EPL", "kind": "gom", "doc_date": m.ngay(21).isoformat(), "vehicle_id": xe2.id,
                                   "driver_id": tx2.id, "customer_id": kh.id}, vai="thabok")
        phai(s, 200, "Lập phiếu MỚI sau khi đổi tỷ giá", pm)
        dung("rate_usd" not in pm, "Gói trả cho Bãi không có tỷ giá (anh Khampla A2)")
        s, pm = goi("/api/trips/%s" % pm["id"], vai="ketoan")
        dung(pm["rate_usd"] == moi, "Phiếu mới khoá tỷ giá mới", (pm["rate_usd"], moi))
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("THỬ TỶ GIÁ")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("THỬ TỶ GIÁ")
