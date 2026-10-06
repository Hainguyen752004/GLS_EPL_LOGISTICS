# -*- coding: utf-8 -*-
"""Thử luồng GPS thật — điện thoại tài xế gửi vị trí, màn Theo dõi dùng nó thay cho mốc — chạy TRONG TIẾN TRÌNH (06/10).

    python kiem/thu_vi_tri.py

Khung kiem/_khung_tien_trinh.py: bản sao _d7, một giao dịch, cuối ROLLBACK; xe, hai tài xế (kèm tài khoản), DO thử dựng mới ở một
tháng d7 chưa có DO; không gọi mạng. (Trước 06/10 bài gọi máy 8010, gửi điểm vào một phiếu ĐANG CHẠY thật rồi sửa thẳng giờ các điểm.)

Kiểm đúng những chỗ dễ sai: ai được gửi, phiếu nào được nhận, điểm gửi quá dày thì bỏ, GPS còn mới thì bản đồ lấy GPS, GPS cũ thì lùi
về mốc đã xác nhận tới và gắn cờ "GPS thiếu hoặc cũ". Gửi bù theo lô / giờ máy / hàng đợi mất mạng: kiem/thu_tai_xe_tat_toan.py (G7).
"""
import datetime as dt

import _khung_tien_trinh as K                           # đặt DATABASE_URL = _d7, chặn mạng, cài bộ giả — trước mọi mã máy chủ

dung, phai, ma = K.dung, K.phai, K.ma


def main():
    with K.Khung() as m:
        goi, M = m.goi, m.M
        print("== 0. dữ liệu thử (tháng %s, dựng trong giao dịch)" % m.thang)
        xe, xe2 = m.xe("THU-VT-01"), m.xe("THU-VT-02")
        tx = m.tai_xe("ທ້າວ ທົດລອງ ຈີພີເອສ", tai_khoan=True)
        khac = m.tai_xe("ທ້າວ ທົດລອງ ຈີພີເອສ 2", tai_khoan=True)
        kh = m.khach("ລູກຄ້າ ທົດລອງ ຈີພີເອສ")
        m.commit()
        s, p = goi("/api/trips", {"doc_no": "THU-VT-1/EPL", "kind": "gom", "vehicle_id": xe.id, "driver_id": tx.id, "customer_id": kh.id,
                                  "doc_date": m.ngay(8).isoformat(), "out_date": m.ngay(8).isoformat(), "weight_origin": 30}, "admin")
        phai(s, 200, "Sếp lập DO thử đang chạy", p)
        s, xong = goi("/api/trips", {"doc_no": "THU-VT-2/EPL", "kind": "gom", "vehicle_id": xe2.id, "driver_id": khac.id, "customer_id": kh.id,
                                     "doc_date": m.ngay(8).isoformat(), "out_date": m.ngay(8).isoformat(), "weight_origin": 30}, "admin")
        phai(s, 200, "Sếp lập DO thử thứ hai (sẽ về tới)", xong)
        for t in (p, xong):
            m.db.get(M.Trip, t["id"]).transport_status = "transit"
        m.db.get(M.Trip, xong["id"]).transport_status = "arrived"
        m.commit()

        print("== 1. ai được gửi")
        s, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.5, "lng": 103.5}, vai=khac.username)
        dung(s == 403, "Tài xế khác gửi vị trí → từ chối", (s, ma(r)))
        s, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.5, "lng": 103.5}, vai="ketoan")
        dung(s == 403, "Kế toán gửi vị trí → từ chối", (s, ma(r)))
        s, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 999, "lng": 103.5}, vai=tx.username)
        dung(s == 422, "Vĩ độ 999 → từ chối", (s, ma(r)))

        print("== 2. tài xế của phiếu gửi; điểm quá dày bỏ")
        s, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.44, "lng": 103.15, "speed_kmh": 52.5, "accuracy_m": 8}, vai=tx.username)
        dung(s == 200 and r.get("ghi") is True, "Tài xế gửi vị trí → điểm đầu tiên được ghi", (s, r))
        s, r = goi("/api/trips/%s/vi-tri" % p["id"], {"lat": 18.45, "lng": 103.16}, vai=tx.username)
        dung(s == 200 and r.get("ghi") is False, "Gửi lại ngay sau đó → bỏ bớt, không ghi", (s, r))

        print("== 3. màn Theo dõi dùng GPS thật")
        s, tt = goi("/api/theo-doi?tat_ca=1", vai="admin")
        phai(s, 200, "Bảng theo dõi", None)
        c = next((x for x in tt["chuyen"] if x["id"] == p["id"]), None)
        dung(c and c["gps"] and c["gps"]["cu"] is False and c["vi_tri"]["nguon"] == "gps",
             "GPS vừa gửi: không cũ, bản đồ lấy vị trí GPS thật", c and (c["gps"], c["vi_tri"]))
        s, v = goi("/api/trips/%s/vet" % p["id"], vai="admin")
        dung(s == 200 and v["so_diem"] >= 1, "Vệt đường của phiếu có điểm", v.get("so_diem") if isinstance(v, dict) else s)

        print("== 4. GPS cũ thì lùi về mốc đã xác nhận tới")
        n = (m.db.query(M.VehiclePosition).filter(M.VehiclePosition.trip_id == p["id"])
             .update({M.VehiclePosition.ts: dt.datetime.utcnow() - dt.timedelta(hours=2)}, synchronize_session=False))
        m.commit()
        s, tt = goi("/api/theo-doi?tat_ca=1", vai="admin")
        c = next((x for x in tt["chuyen"] if x["id"] == p["id"]), None)
        dung(n >= 1 and c["gps"]["cu"] is True and (c["vi_tri"] is None or c["vi_tri"]["nguon"] == "moc") and tt["kpi"]["gps_thieu"] >= 1,
             "GPS cũ 2 tiếng → cờ cũ, lùi về mốc, ô 'GPS thiếu hoặc cũ' đếm được phiếu", (c["gps"], c["vi_tri"], tt["kpi"]["gps_thieu"]))

        print("== 5. phiếu đã tới nơi thì không nhận vị trí")
        s, r = goi("/api/trips/%s/vi-tri" % xong["id"], {"lat": 18.4, "lng": 103.1}, vai="admin")
        dung(s == 409, "Phiếu đã tới nơi → không nhận vị trí", (s, ma(r)))
        dung(not K.MANG, "không có lời gọi mạng nào ra ngoài", K.MANG[:2])
    K.ket_thuc("THỬ VỊ TRÍ")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(e)
        K.ket_thuc("THỬ VỊ TRÍ")
