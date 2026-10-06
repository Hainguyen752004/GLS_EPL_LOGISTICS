# -*- coding: utf-8 -*-
"""Thử HAI VAI MỚI ở Thà Bốc (C1.2) và ĐỔI XE GIỮA ĐƯỜNG (C2.2) — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_vai_va_doi_xe.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; ba xe (hai xe nhà, một xe liên kết của chủ xe thử), hai tài
xế (một có tài khoản), khách, DO thử dựng mới ở một tháng d7 chưa có DO; không gọi mạng — kho QLSX (tồn, xuất phụ tùng) GIẢ LẬP.
(Trước 06/10 bài gọi máy 8010 và kho phụ tùng ở trang kế toán tạm 8031 — đã bỏ: nhập kho phụ tùng nay ở Web anh Tune.)

Anh Khampla trả lời 22/09:
  · C1.2 — kho phụ tùng và tổ sửa chữa ở Thà Bốc là **người riêng**, không phải Admin Bãi. Mục V (sửa chữa) rút khỏi Bãi; tổ sửa chữa là
    người duyệt báo hỏng của tài xế và quyết lấy phụ tùng từ kho hay mang ra gara.
  · C2.2 — xe hỏng nặng giữa đường thì **đổi xe khác chở tiếp**, dù mục I đã kiểm xong. Làm trên chính tờ phiếu đang chạy: hàng,
    khách, tuyến và tiền đã chi vẫn là của chuyến đó. Không đổi chéo xe nhà ↔ xe liên kết (chứng từ mang mã loại cũ — từ
    kiem/thu_chot_22_09.py).

Kịch bản: tài xế báo hỏng → Bãi duyệt bị chặn, tổ sửa chữa duyệt được, dòng chi vào mục V → Bãi / kế toán khai sửa xe bị chặn, tổ sửa
chữa lấy phụ tùng kho (kho QLSX trừ tồn) → đổi xe giữa đường: chặn vai khác, chặn thiếu lý do, chặn trùng xe, chặn đổi chéo loại xe;
đổi xong phiếu mang xe mới, có dòng diễn biến, mục I về "đã nhập" → xoá phiếu thì phiếu xuất phụ tùng ở kho được huỷ, tồn về.
"""
import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ
import _quy_trinh as Q                                  # noqa: E402 — Bãi lập không tiền → KT nhập giá (quy trình 23/09)

dung, phai, ma = K.dung, K.phai, K.ma


def main():
    with K.Khung() as m:
        goi, M = m.goi, m.M
        from services import kho_qlsx as KQ
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        chu = m.chu_xe("ເຈົ້າຂອງລົດ ທົດລອງ ປ່ຽນລົດ")
        xe1, xe2, xe_lk = m.xe("THU-VD-01"), m.xe("THU-VD-02"), m.xe("THU-VD-LK", loai="joint", chu=chu)
        tx = m.tai_xe("ທ້າວ ທົດລອງ ປ່ຽນລົດ", tai_khoan=True)
        tx2 = m.tai_xe("ທ້າວ ທົດລອງ ປ່ຽນລົດ 2")
        kh = m.khach("ລູກຄ້າ ທົດລອງ ປ່ຽນລົດ")
        pt = m.db.query(M.Part).filter(M.Part.active.is_(True)).order_by(M.Part.id).first()
        K.GIA.ton[(KQ.kho_pt(), KQ.ma_pt(pt.id))] = [5, 520000]          # tồn phụ tùng bên kho QLSX (giả lập)
        m.commit()

        print("== 1. lập phiếu, kiểm mục I")
        s, P = Q.lap_phieu(goi, {
            "doc_no": "THU-VD-%s/EPL" % m.thang, "kind": "gom", "doc_date": m.ngay(21).isoformat(), "out_date": m.ngay(21).isoformat(),
            "vehicle_id": xe1.id, "driver_id": tx.id, "customer_id": kh.id, "goods_type": "iron_ore", "weight_origin": 35,
            "hang": [{"goods_name": "ແຮ່ເຫຼັກ (quặng sắt)", "qty_t": 35}],
            "expenses": [{"section": "fuel", "item_key": "diesel", "qty": 80, "unit_price": 30000, "currency": "LAK", "place": "fp_yard"}],
        }, vai="thabok")
        phai(s, 200, "Bãi lập phiếu với xe THU-VD-01", P)
        pid = P["id"]
        s, g = goi("/api/trips/%s/sections/info/send" % pid, {}, vai="thabok"); phai(s, 200, "Bãi gửi kiểm mục I", g)
        s, g = goi("/api/trips/%s/sections/info/verify" % pid, {}, vai="ketoan"); phai(s, 200, "Kế toán kiểm mục I", g)

        print("== 2. C1.2 — mục V là của tổ sửa chữa")
        s, g = goi("/api/trips/%s/events" % pid, {"kind": "arrive_stop", "stop_seq": 1, "note": "vào mỏ"}, vai="thabok")
        phai(s, 200, "Bãi vẫn ghi diễn biến bình thường", g)
        s, parts = goi("/api/parts", vai="totsua")
        ton = next(x for x in parts if x["id"] == pt.id)["qty"]
        dung(ton == 5, "Tồn phụ tùng đọc từ kho QLSX (giả lập)", ton)
        than_sua = {"kind": "repair", "incident_type": "breakdown", "note": "thử: hỏng bơm", "repair": {"source": "kho", "part_id": pt.id, "qty": 1}}
        s, g = goi("/api/trips/%s/events" % pid, than_sua, vai="thabok"); phai(s, 403, "Bãi khai khoản sửa chữa → bị chặn (C1.2)", g)
        s, g = goi("/api/trips/%s/events" % pid, than_sua, vai="ketoancp"); phai(s, 403, "Kế toán chi phí khai khoản sửa chữa → bị chặn", g)
        s, g = goi("/api/trips/%s/events" % pid, than_sua, vai="totsua"); phai(s, 200, "Tổ sửa chữa khai sửa xe, lấy phụ tùng từ kho", g)
        dong = [e for e in g["expenses"] if e["section"] == "repair"]
        dung(dong and dong[-1]["source"] == "kho" and (dong[-1]["stock_move_id"] or "").startswith("qlsx:") and g["sections"]["repair"] == "entered",
             "Sinh dòng mục V nguồn kho, có phiếu xuất kho QLSX, mục V về 'đã nhập'", dong and (dong[-1]["stock_move_id"], g["sections"]["repair"]))
        s, parts2 = goi("/api/parts", vai="totsua")
        dung(next(x for x in parts2 if x["id"] == pt.id)["qty"] == ton - 1, "Tồn phụ tùng giảm đúng 1", ton - 1)
        s, g = goi("/api/parts/%s/moves" % pt.id, {"kind": "in", "qty": 1, "note": "thử trả kho"}, vai="khopt")
        phai(s, 409, "Trang điều xe không còn nhập kho phụ tùng (nhập ở kho Web anh Tune)", g)

        # tài xế báo hỏng → tổ sửa chữa duyệt
        s, g = goi("/api/trips/%s/bao-hong" % pid, {"note": "thử: kêu lạ ở cầu sau", "reported_cost": 250000}, vai=tx.username)
        phai(s, 200, "Tài xế báo hỏng", g)
        ev = [e for e in g["events"] if e["status"] == "reported"][-1]
        mua = {"source": "mua", "item_name": "thử: thay bạc đạn", "qty": 1, "unit_price": 250000}
        s, g = goi("/api/trips/%s/events/%s/duyet" % (pid, ev["id"]), mua, vai="thabok")
        phai(s, 403, "Bãi duyệt báo hỏng → bị chặn (việc tổ sửa chữa)", g)
        s, g = goi("/api/trips/%s/events/%s/duyet" % (pid, ev["id"]), mua, vai="totsua")
        phai(s, 200, "Tổ sửa chữa duyệt báo hỏng → thành dòng mục V", g)
        dung(len([e for e in g["expenses"] if e["section"] == "repair"]) == 2, "Có hai dòng mục V")
        s, g = goi("/api/trips/%s/sections/repair/send" % pid, {}, vai="thabok"); phai(s, 403, "Bãi gửi kiểm mục V → bị chặn", g)
        s, g = goi("/api/trips/%s/sections/repair/verify" % pid, {}, vai="ketoancp"); phai(s, 200, "KT Chi phí kiểm mục V", g)
        s, g = goi("/api/trips/%s/sections/repair/verify" % pid, {}, vai="totsua")
        phai(s, 403, "Tổ sửa chữa tự kiểm mục V → bị chặn (KT Chi phí kiểm)", g)

        # TIỀN BÁN: hai vai mới xếp cùng nhóm Bãi — không xem lãi chuyến, không xem công nợ chủ xe, khách
        s, ds_chu = goi("/api/owners", vai="totsua")
        dung(s == 200 and all("fee_pct" not in o for o in ds_chu), "Tổ sửa chữa không thấy phí chủ xe", s)
        s, g = goi("/api/bao-cao/xe-lien-ket", vai="khopt"); phai(s, 403, "Thủ kho phụ tùng xem báo cáo xe liên kết (lãi) → bị chặn", g)
        s, g = goi("/api/de-nghi-thu", vai="totsua"); phai(s, 403, "Tổ sửa chữa xem đề nghị thu (cước) → bị chặn (tiền bán)", g)
        s, g = goi("/api/customers-cong-no", vai="totsua"); phai(s, 403, "Tổ sửa chữa xem công nợ khách → bị chặn (tiền bán)", g)

        print("== 3. C2.2 — đổi xe giữa đường")
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe2.id, "ly_do": "thử"}, vai="ketoan")
        phai(s, 403, "Kế toán đổi xe → bị chặn (Bãi điều xe)", g)
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe2.id}, vai="thabok"); phai(s, 422, "Đổi xe không ghi lý do → bị từ chối", g)
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe1.id, "ly_do": "thử"}, vai="thabok")
        phai(s, 409, "Đổi sang chính xe đang chạy → bị từ chối", g)
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe_lk.id, "ly_do": "thử chéo"}, vai="thabok")
        dung(s == 409 and ma(g) == "KHAC_LOAI_XE", "Đổi chéo xe nhà → xe liên kết → 409 KHAC_LOAI_XE (chứng từ mang mã loại cũ)", (s, ma(g)))
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe2.id, "driver_id": tx2.id, "ly_do": "thử: gãy nhíp giữa đường",
                                                   "xe_cu_hong": True}, vai="thabok")
        phai(s, 200, "Bãi đổi sang xe THU-VD-02 giữa đường", g)
        dung(g["truck_no"] == xe2.truck_no and g["plate_head"] == xe2.plate_head and g["driver_name"] == tx2.name,
             "Phiếu mang xe mới và tài xế mới", (g["truck_no"], g["driver_name"]))
        dung(g["sections"]["info"] == "entered", "Mục I quay về 'đã nhập' để kiểm lại", g["sections"]["info"])
        dx = [e for e in g["events"] if e["kind"] == "change_truck"]
        dung(dx and xe1.truck_no in dx[-1]["note"] and xe2.truck_no in dx[-1]["note"], "Diễn biến ghi rõ đổi từ xe nào sang xe nào",
             dx and dx[-1]["note"][:60])
        dung(len(g["expenses"]) >= 3, "Tiền đã chi của chuyến còn nguyên trên phiếu", len(g["expenses"]))
        m.db.expire_all()
        dung((m.db.get(M.Vehicle, xe1.id).status, m.db.get(M.Vehicle, xe2.id).status) == ("maintenance", "on_trip"),
             "Trạng thái hai xe đổi theo: xe cũ vào xưởng, xe mới đang chạy",
             (m.db.get(M.Vehicle, xe1.id).status, m.db.get(M.Vehicle, xe2.id).status))
        s, g = goi("/api/trips/%s/sections/info/verify" % pid, {}, vai="ketoan"); phai(s, 200, "Kế toán kiểm lại mục I sau khi đổi xe", g)
        s, g = goi("/api/trips/%s/transport-status" % pid, {"status": "arrived", "weight_dest": 35, "odo_back": 100}, vai="thabok")
        phai(s, 200, "Xe (mới) báo tới nơi", g)
        s, g = goi("/api/trips/%s/doi-xe" % pid, {"vehicle_id": xe1.id, "ly_do": "thử"}, vai="thabok")
        phai(s, 409, "Đổi xe khi đã tới nơi → bị từ chối", g)

        print("== 4. xoá phiếu → phiếu xuất phụ tùng ở kho được huỷ")
        s, g = goi("/api/trips/%s" % pid, vai="admin", method="DELETE"); phai(s, 200, "Xoá phiếu thử", g)
        s, parts3 = goi("/api/parts", vai="totsua")
        dung(next(x for x in parts3 if x["id"] == pt.id)["qty"] == ton, "Xoá phiếu → phụ tùng mục V về kho (kho QLSX nhận lệnh huỷ)",
             next(x for x in parts3 if x["id"] == pt.id)["qty"])
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("HAI VAI MỚI & ĐỔI XE")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("HAI VAI MỚI & ĐỔI XE")
