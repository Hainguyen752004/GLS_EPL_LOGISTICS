# -*- coding: utf-8 -*-
"""Thử NỢ TRẠM DẦU VIỆT NAM và CẤN TRỪ CƯỚC THÁNG (anh Khampla C5.1) — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_no_tram_dau.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; trạm dầu VN thử + nhà cung cấp thử + khách / xe / tài xế /
DO thử dựng mới ở một tháng d7 chưa có DO; không gọi mạng. (Trước 06/10 bài gọi máy 8010 và GẮN khách cấn trừ vào trạm VN-01 thật.)

Ghi chú của họ ở C5.1: tài xế đổ dầu bên Việt Nam **ghi nợ tại trạm**, cuối tháng EPL cấn trừ với cước khách. Công nợ **hai chiều**:
EPL nợ trạm, khách nợ EPL, hai số bù nhau. Phân biệt phải giữ:
  · dòng dầu mua ngoài mà **tài xế trả tiền mặt** → EPL không nợ trạm đồng nào (và nó vào tạm ứng);
  · dòng dầu mua ngoài **ghi nợ trạm** → đúng bằng số EPL nợ trạm đó (không vào tạm ứng).
Từ 01/10 công nợ nhà cung cấp ở lại trang này (/api/suppliers/cong-no — trả tiền là phiếu chi bên hệ kế toán anh Tune), bảng cấn trừ
là bảng tính /api/bao-cao/can-tru; GHI cấn trừ là việc của hệ kế toán (/api/bao-cao/can-tru/ghi → 409 — từ kiem/thu_chot_22_09.py).
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ
import _quy_trinh as Q                                  # noqa: E402 — Bãi lập không tiền → KT nhập giá (quy trình 23/09)

dung, phai, ma = K.dung, K.phai, K.ma


def bang(a, b, ten, sai_so=1.0):
    return dung(abs((a or 0) - (b or 0)) <= sai_so, ten, "nhận %s, mong %s" % (a, b))


def main():
    with K.Khung() as m:
        goi = m.goi
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        xe = m.xe("THU-NT-01")
        tx = m.tai_xe("ທ້າວ ທົດລອງ ປໍ້າ")
        khach = m.khach("ລູກຄ້າ ທົດລອງ ປໍ້າ")
        m.commit()

        print("== 1. trạm dầu là nhà cung cấp, cấn trừ vào cước khách")
        s, tram = goi("/api/suppliers", {"name": "ປໍ້ານໍ້າມັນ ຫວຽດນາມ ທົດລອງ (Trạm dầu VN thử)", "item_key": "diesel",
                                         "acct_code": "625/4021", "payment_term": "t_monthly"}, vai="ketoancp")
        phai(s, 200, "KT Chi phí lập nhà cung cấp trạm dầu VN (thử)", tram)
        vn = m.diem_do("THU-VN-01", "ປໍ້ານໍ້າມັນ ຫວຽດນາມ ທົດລອງ", country="VN", owner_type="ngoai", supplier_id=tram["id"])
        m.commit()
        s, g = goi("/api/suppliers/%s" % tram["id"], {"customer_id": khach.id}, vai="thabok", method="PUT")
        phai(s, 403, "Bãi gắn khách cấn trừ cho trạm → bị chặn", g)
        s, tram = goi("/api/suppliers/%s" % tram["id"], {"customer_id": khach.id}, vai="ketoancp", method="PUT")
        phai(s, 200, "KT Chi phí gắn trạm dầu cấn trừ vào cước khách thử", tram)
        dung(tram["customer_name"] == khach.name and "ghi_no_lak" not in tram and "con_no_lak" not in tram,
             "Trạm mang tên khách cấn trừ; danh mục không có cột tiền", sorted(tram)[:8])
        s, g = goi("/api/suppliers/%s/payments" % tram["id"], vai="ketoancp")
        phai(s, 404, "Đường cũ 'các lần trả' của trang kế toán tạm → đã gỡ", g)
        s, g = goi("/api/suppliers/cong-no", vai="thabok")
        phai(s, 403, "Bãi xem công nợ nhà cung cấp → bị chặn (tiền chi)", g)
        s, ncc_kt = goi("/api/suppliers/cong-no", vai="ketoancp")
        phai(s, 200, "Công nợ nhà cung cấp (phát sinh từ phiếu − đã chi bên kế toán)", None)
        no_truoc = next(x for x in ncc_kt if x["id"] == tram["id"])["ghi_no_lak"]

        print("== 2. phiếu: một dòng trả tiền mặt, một dòng ghi nợ")
        s, P = Q.lap_phieu(goi, {
            "doc_no": "THU-NT-%s/EPL" % m.thang, "kind": "gom", "doc_date": m.ngay(10).isoformat(), "out_date": m.ngay(10).isoformat(),
            "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": khach.id,
            "goods_type": "iron_ore", "weight_origin": 20, "price": 40, "price_ccy": "USD",
            "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 20}],
            "expenses": [
                {"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 20000, "currency": "LAK", "place_id": vn.id},
                {"section": "fuel", "item_key": "diesel", "qty": 200, "unit_price": 20000, "currency": "LAK", "place_id": vn.id, "ghi_no": True},
            ],
        }, vai="thabok")
        phai(s, 200, "Bãi lập phiếu (KT kho nhập giá): một dòng dầu trả tiền mặt, một dòng ghi nợ trạm", P)
        pid = P["id"]
        dong = [d for d in P["expenses"] if d["section"] == "fuel"]
        dung(len(dong) == 2 and [d["ghi_no"] for d in dong] == [False, True], "Cờ ghi nợ giữ đúng từng dòng", [d["ghi_no"] for d in dong])
        dung(all(d["supplier_id"] == tram["id"] for d in dong), "Dòng đổ ở trạm ngoài tự mang nhà cung cấp của trạm",
             [d["supplier_id"] for d in dong])

        s, pc = goi("/api/trips/%s/phieu-chi" % pid, vai="admin")
        dau = [d for d in pc["dong"] if d["section"] == "fuel"]
        dung(len(dau) == 1 and dau[0]["qty"] == 100, "Phiếu tạm ứng chỉ gồm dầu trả tiền mặt (200 L ghi nợ không tính)", dau)

        print("== 3. công nợ trạm chỉ tính dòng ghi nợ")
        s, ncc2 = goi("/api/suppliers/cong-no", vai="ketoancp")
        t2 = next(x for x in ncc2 if x["id"] == tram["id"])
        bang(t2["ghi_no_lak"] - no_truoc, 200 * 20000, "Nợ trạm tăng đúng phần GHI NỢ (dòng tiền mặt không tính)")

        print("== 4. bảng cấn trừ cuối tháng — bảng tính ở đây, ghi ở hệ kế toán")
        s, g = goi("/api/bao-cao/can-tru?thang=%s" % m.thang, vai="thabok")
        phai(s, 403, "Bãi xem bảng cấn trừ → bị chặn (tiền bán)", g)
        s, g = goi("/api/bao-cao/can-tru/ghi", {"customer_id": khach.id, "thang": m.thang}, vai="doanhthu")
        phai(s, 409, "Ghi cấn trừ bên trang điều xe → việc của hệ kế toán", g)
        s, ct = goi("/api/bao-cao/can-tru?thang=%s" % m.thang, vai="doanhthu")
        phai(s, 200, "KT Doanh thu xem bảng cấn trừ tháng thử", None)
        o = next((x for x in ct["ds"] if x["customer_id"] == khach.id), None)
        dung(o is not None, "Bảng cấn trừ có khách thử", [x["customer_name"] for x in ct["ds"]])
        if o:
            bang(o["dau_vn_lak"], 200 * 20000, "Bảng cấn trừ: nợ trạm dầu VN của khách trong tháng")
            dung(o["can_tru_lak"] == o["the_lak"] + o["dau_vn_lak"] and o["con_thu_lak"] == o["cuoc_lak"] - o["can_tru_lak"],
                 "Cấn trừ = thẻ khách + trạm dầu VN; còn phải thu = cước − cấn trừ", {k: o[k] for k in ("cuoc_lak", "can_tru_lak", "con_thu_lak")})
            dung("da_ghi_lak" not in o, "Bảng không còn cột 'đã ghi' của sổ thu trang tạm", sorted(o))
            dung(any(t["name"] == tram["name"] for t in o["tram"]), "Bảng nói rõ trạm nào", o["tram"])

        print("== 5. dọn")
        s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử", g)
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("NỢ TRẠM DẦU VIỆT NAM")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("NỢ TRẠM DẦU VIỆT NAM")
