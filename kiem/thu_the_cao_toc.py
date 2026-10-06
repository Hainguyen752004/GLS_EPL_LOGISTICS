# -*- coding: utf-8 -*-
"""Thử THẺ CAO TỐC — ບັດທາງດ່ວນ (anh Khampla C6.1) — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_the_cao_toc.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; thẻ, khách, xe, tài xế, DO thử dựng mới ở một tháng d7
chưa có DO; không gọi mạng — kho QLSX báo cấp dầu GIẢ LẬP (06/10: trước đây bài gọi máy 8010 và cấp dầu ở kho tạm 8031 đã bỏ).

Họ muốn biết **thẻ còn bao nhiêu tiền**, mỗi chuyến qua trạm trừ từ thẻ nào, và cuối tháng — với thẻ do **khách cấp và nạp tiền** —
phần EPL đã tiêu trên thẻ được **cấn trừ vào cước** của chính khách đó.

Kịch bản: lập thẻ (chặn thẻ khách không ghi khách, chặn trùng số) → nạp tiền → lập phiếu có dòng phí cầu đường chọn thẻ → **thẻ CHƯA bị
trừ khi mới nhập** → kế toán ghi sổ mục IV → thẻ bị trừ đúng một lần, dòng chi ghi rõ đã trừ → ghi sổ mục khác (mục III, sau khi kho
QLSX cấp dầu) không trừ thêm → xoá dòng đã trừ bị chặn → điều chỉnh số dư phải có lý do → bảng cấn trừ cuối tháng ra đúng số của khách.
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ
import _quy_trinh as Q                                  # noqa: E402 — Bãi lập không tiền → KT nhập giá (quy trình 23/09)

dung, phai, ma = K.dung, K.phai, K.ma
SO_KHO = "1368-XKK-THU-CT-0001"


def bang(a, b, ten, sai_so=1.0):
    return dung(abs((a or 0) - (b or 0)) <= sai_so, ten, "nhận %s, mong %s" % (a, b))


def main():
    with K.Khung() as m:
        goi = m.goi
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        xe = m.xe("THU-CT-01")
        tx = m.tai_xe("ທ້າວ ທົດລອງ ບັດ")
        khach = m.khach("ລູກຄ້າ ທົດລອງ ບັດ")
        m.commit()
        K.GIA.ton[("KHO-TB", "EPLNL-diesel")] = [5000, 26500]      # tồn + giá bình quân kho dầu Thà Bốc bên kho QLSX (giả lập)
        so_the = "THU-THE-%s-%s" % (m.thang, xe.id[:6])

        print("== 1. danh mục thẻ")
        s, g = goi("/api/the-cao-toc", {"card_no": so_the, "kind": "khach", "currency": "LAK"}, vai="thabok")
        phai(s, 403, "Bãi lập thẻ → bị chặn (thoả thuận với khách, kế toán giữ)", g)
        s, g = goi("/api/the-cao-toc", {"card_no": so_the, "kind": "khach", "currency": "LAK"}, vai="ketoan")
        phai(s, 422, "Thẻ khách cấp mà không ghi khách nào → bị từ chối", g)
        s, THE = goi("/api/the-cao-toc", {"card_no": so_the, "name": "Thẻ thử", "kind": "khach", "customer_id": khach.id,
                                          "driver_id": tx.id, "currency": "LAK", "balance": 0}, vai="ketoan")
        phai(s, 200, "Kế toán lập thẻ do khách thử cấp", THE)
        tid = THE["id"]
        s, g = goi("/api/the-cao-toc", {"card_no": so_the, "kind": "epl", "currency": "LAK"}, vai="ketoan")
        phai(s, 409, "Trùng số thẻ → bị từ chối", g)

        print("== 2. nạp tiền")
        s, g = goi("/api/the-cao-toc/%s/nap" % tid, {"amount": 4000000, "ref": "NAP-THU"}, vai="thabok")
        phai(s, 403, "Bãi nạp tiền vào thẻ → bị chặn", g)
        s, THE = goi("/api/the-cao-toc/%s/nap" % tid, {"amount": 4000000, "ref": "NAP-THU", "move_date": m.ngay(2).isoformat()}, vai="quytb")
        phai(s, 200, "Quỹ Thà Bốc nạp 4.000.000 Kíp", THE)
        bang(THE["balance"], 4000000, "Số dư thẻ sau khi nạp")
        dung(THE["moves"][0]["balance_after"] == 4000000, "Dòng nạp ghi số dư sau", THE["moves"][0].get("balance_after"))

        print("== 3. phiếu có dòng phí cầu đường trả bằng thẻ")
        so = "THU-CT-%s/EPL" % m.thang
        s, P = Q.lap_phieu(goi, {
            "doc_no": so, "kind": "gom", "doc_date": m.ngay(20).isoformat(), "out_date": m.ngay(20).isoformat(),
            "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": khach.id,
            "goods_type": "iron_ore", "weight_origin": 30, "price": 40, "price_ccy": "USD",
            "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 30}],
            "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 70, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"},
                         {"section": "travel", "item_key": "x_toll", "qty": 1, "unit_price": 1200000, "currency": "LAK", "toll_card_id": tid},
                         {"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"}],
        }, vai="thabok")
        phai(s, 200, "Bãi lập phiếu, dòng phí cầu đường chọn trả bằng thẻ (kế toán nhập giá)", P)
        pid = P["id"]
        dong_the = [d for d in P["expenses"] if d.get("toll_card_id")]
        dung(len(dong_the) == 1 and not dong_the[0]["card_move_id"], "Mới nhập thì CHƯA trừ thẻ", dong_the)
        s, g = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
        bang(g["balance"], 4000000, "Nhập dòng chi xong thẻ vẫn chưa bị trừ")

        print("== 4. ghi sổ mục IV → trừ thẻ đúng một lần")
        for muc in ("info", "trans", "fuel", "travel"):
            s, g = goi("/api/trips/%s/sections/%s/send" % (pid, muc), {}, vai="thabok"); phai(s, 200, "gửi kiểm %s" % muc, g)
        for muc, v in (("info", "ketoan"), ("trans", "ketoan"), ("fuel", "khonl"), ("travel", "ketoancp")):
            s, g = goi("/api/trips/%s/sections/%s/verify" % (pid, muc), {}, vai=v); phai(s, 200, "kiểm %s" % muc, g)
        s, g = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
        bang(g["balance"], 4000000, "Kiểm xong mục IV thẻ vẫn chưa bị trừ")
        s, g = goi("/api/trips/%s/sections/travel/book" % pid, {}, vai="ketoancp")
        phai(s, 200, "KT Chi phí GHI SỔ mục IV → lúc này mới trừ thẻ", g)
        d = [x for x in g["expenses"] if x.get("toll_card_id")][0]
        dung(bool(d["card_move_id"]), "Dòng chi ghi đã trừ thẻ", d.get("card_move_id"))
        s, THE = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
        bang(THE["balance"], 4000000 - 1200000, "Số dư thẻ sau khi qua trạm")
        mv = THE["moves"][0]
        dung(mv["kind"] == "chi" and mv["trip_doc_no"] == so, "Dòng trừ thẻ nhắc đúng số phiếu", (mv["kind"], mv["trip_doc_no"]))

        # dầu kho chỉ rời kho theo phiếu ĐỀ NGHỊ đã cấp: Bãi in đề nghị → kho QLSX cấp (giả lập) → mới ghi sổ mục III
        s, v = goi("/api/trips/%s/vouchers" % pid, {"kind": "fuel"}, vai="thabok"); phai(s, 200, "Bãi in phiếu đề nghị xuất kho nhiên liệu", v)
        s, ct = goi("/api/handover/fuel-vouchers/" + v[0]["id"])
        s, g = goi("/api/handover/fuel-vouchers/%s/issued" % v[0]["id"],
                   {"source_ref": ct["data"]["source_ref"], "stock_doc_no": SO_KHO, "qty_l": 70, "issued_by": "thu",
                    "lines": [{"item_code": "EPLNL-diesel", "qty": 70, "unit_cost": 26500}]})
        phai(s, 200, "Kho QLSX báo đã cấp 70 L (giả lập)", g)
        s, g = goi("/api/trips/%s/sections/fuel/book" % pid, {}, vai="khonl"); phai(s, 200, "ghi sổ mục III", g)
        s, THE2 = goi("/api/the-cao-toc/%s" % tid, vai="ketoan")
        bang(THE2["balance"], 2800000, "Ghi sổ mục khác không trừ thẻ thêm lần nữa")

        # dòng đã trừ thẻ thì không xoá lặng lẽ khỏi phiếu
        s, g = goi("/api/trips/%s/sections/travel/unlock" % pid, {}, vai="admin"); phai(s, 200, "Sếp mở lại mục IV đã ghi sổ", g)
        s, g = goi("/api/trips/%s" % pid, {"expenses": [{"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000,
                                                         "currency": "LAK"}]}, vai="thabok", method="PUT")
        phai(s, 409, "Xoá dòng đã trừ thẻ khỏi phiếu → bị từ chối", g)

        print("== 5. điều chỉnh số dư phải có lý do")
        s, g = goi("/api/the-cao-toc/%s/dieu-chinh" % tid, {"amount": -50000}, vai="ketoan")
        phai(s, 422, "Điều chỉnh số dư không ghi lý do → bị từ chối", g)
        s, THE = goi("/api/the-cao-toc/%s/dieu-chinh" % tid, {"amount": -50000, "note": "thử: trạm quẹt chưa khai"}, vai="ketoan")
        phai(s, 200, "Điều chỉnh giảm 50.000 kèm lý do", THE)
        bang(THE["balance"], 2750000, "Số dư sau điều chỉnh")

        print("== 6. cấn trừ cuối tháng")
        s, g = goi("/api/the-cao-toc/cong-no?thang=%s" % m.thang, vai="thabok")
        phai(s, 403, "Bãi xem bảng cấn trừ cước → bị chặn (tiền bán)", g)
        s, ct = goi("/api/the-cao-toc/cong-no?thang=%s" % m.thang, vai="doanhthu")
        phai(s, 200, "KT Doanh thu xem bảng cấn trừ cước theo thẻ", None)
        o = next((x for x in ct["ds"] if x["customer_id"] == khach.id), None)
        dung(o is not None and o["can_tru"] >= 1200000, "Cấn trừ vào cước của khách: gồm 1.200.000 đã tiêu trên thẻ khách",
             o and round(o["can_tru"]))

        print("== 7. dọn (kho huỷ phiếu xuất thì DO mới xoá được)")
        s, g = goi("/api/handover/fuel-vouchers/%s/cancelled" % v[0]["id"], {"stock_doc_no": SO_KHO, "reason": "thử", "cancelled_by": "thu"})
        phai(s, 200, "Kho QLSX huỷ phiếu xuất (giả lập)", g)
        s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử", g)
        s, g = goi("/api/the-cao-toc/%s" % tid, {"active": False}, vai="ketoan", method="PUT"); phai(s, 200, "Ngưng thẻ thử", g)
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("THẺ CAO TỐC")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("THẺ CAO TỐC")
