# -*- coding: utf-8 -*-
"""Gieo vài CƠ HỘI KHÁCH HÀNG (CRM-01) cho buổi demo — bước đứng trước báo giá.

Chạy được nhiều lần: cơ hội gieo có mã cố định `LEAD-DEMO-xx`, có rồi thì bỏ qua.
Dùng khách và tuyến ĐANG CÓ trong cơ sở dữ liệu (không tự bịa dữ liệu gốc); thiếu
thì ghi cơ hội dạng khách tiềm năng chưa có mã / chưa chọn tuyến — đúng là hai
trạng thái màn phải hiển thị được.

    cd backend/app && python ../scripts/gieo_co_hoi_demo.py
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
os.environ.pop("DATABASE_URL", None)

import config  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from models import CoHoiKhach, Customer, Route  # noqa: E402
from services import co_hoi_service as crm  # noqa: E402


def main():
    engine = create_engine(config.DATABASE_URL)
    db = sessionmaker(bind=engine)()
    try:
        khach = db.query(Customer).order_by(Customer.id).all()
        tuyen = db.query(Route).order_by(Route.id).all()
        k = lambda i: khach[i % len(khach)].id if khach else None  # noqa: E731
        t = lambda i: tuyen[i % len(tuyen)].id if tuyen else None  # noqa: E731
        gio = dt.datetime.now(dt.timezone.utc)
        cac = [
            ("LEAD-DEMO-01", dict(customer_id=k(0), route_id=t(0), cargo_type="Hàng tiêu dùng đóng pallet",
                                  est_weight_kg=14000, est_trips_per_month=12, source="existing", owner="tran.anh",
                                  contact_name="Anh Hoàng", contact_phone="0903 111 222",
                                  next_action_at=(gio - dt.timedelta(hours=3)).isoformat(),
                                  notes="Khách cũ hỏi thêm tuyến mới, cần báo giá trong tuần")),
            ("LEAD-DEMO-02", dict(prospect_name="Công ty May Hưng Thịnh", route_id=t(1), cargo_type="Vải cuộn",
                                  est_weight_kg=9000, est_trips_per_month=6, source="phone", owner="tran.anh",
                                  contact_name="Chị Lan", contact_phone="0901 234 567",
                                  next_action_at=(gio + dt.timedelta(days=1)).isoformat(),
                                  notes="Gọi từ số hotline, đang so giá 2 nhà xe")),
            ("LEAD-DEMO-03", dict(prospect_name="Lao Brewery Logistics", origin_text="Vientiane",
                                  destination_text="Cảng Vũng Áng", cargo_type="Bia lon, xếp pallet",
                                  est_weight_kg=22000, est_trips_per_month=20, source="tender", owner="sales",
                                  contact_name="Mr. Somsak", contact_email="somsak@example.la",
                                  expected_price=38_000_000,
                                  notes="Hồ sơ đấu thầu, chưa có tuyến trong Dữ liệu gốc")),
            ("LEAD-DEMO-04", dict(customer_id=k(1), route_id=t(2), cargo_type="Linh kiện điện tử",
                                  est_weight_kg=5000, est_trips_per_month=8, source="email", owner="sales",
                                  contact_name="Ms. Thuỷ", notes="Yêu cầu xe kín, có niêm phong")),
            ("LEAD-DEMO-05", dict(prospect_name="Nông sản Tây Nguyên", route_id=t(0), cargo_type="Cà phê nhân, bao 60kg",
                                  est_weight_kg=18000, est_trips_per_month=4, source="referral", owner="tran.anh",
                                  notes="Khách giới thiệu từ Nidec")),
        ]
        giai_doan = {"LEAD-DEMO-01": "negotiating", "LEAD-DEMO-02": "contacted", "LEAD-DEMO-04": "contacted",
                     "LEAD-DEMO-05": "lost"}
        tao, bo_qua = 0, 0
        for ma, than in cac:
            if db.get(CoHoiKhach, ma) is not None:
                bo_qua += 1
                continue
            than = {kk: v for kk, v in than.items() if v is not None}
            o = crm.tao(db, dict(than, id=ma), "demo-seed")
            gd = giai_doan.get(ma)
            if gd == "lost":
                crm.doi_giai_doan(db, ma, "contacted", "demo-seed", o["version"])
                o = crm.chi_tiet(db, ma)
                crm.doi_giai_doan(db, ma, "lost", "demo-seed", o["version"], "Khách chọn nhà xe quen, giá thấp hơn 8%")
            elif gd:
                crm.doi_giai_doan(db, ma, gd, "demo-seed", o["version"])
            tao += 1
        db.commit()
        print("Gieo co hoi demo: tao %d, bo qua %d (da co)." % (tao, bo_qua))
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
