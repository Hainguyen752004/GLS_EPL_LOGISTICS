# -*- coding: utf-8 -*-
"""Gieo bộ dữ liệu mẫu — CHÉP TỪ EXCEL của họ, không bịa.

Nguồn: sheet "ໜ້າລາຍງານຂົນສົ່ງ" (dòng 1: phiếu T4-0428-08/EPL) và "ໃບບິນອອກລົດ" (chi tiết chi
phí của đúng phiếu đó), cộng bốn phiếu minh hoạ thêm trong bản giao diện mẫu để bảng theo
dõi có đủ trạng thái để nhìn: đang đi · đã tới · xe liên kết · đã thu tiền · vừa xuất bến.

    python backend/app/seed.py            # chỉ gieo khi DB trống
    python backend/app/seed.py --dung-lai # XOÁ hết bảng rồi dựng lại và gieo — chỉ máy dev
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, SessionLocal, engine, tao_bang  # noqa: E402
from models import (MUC, Customer, Driver, ExchangeRate, FuelMove, Part, Supplier, Trip, TripExpense,  # noqa: E402
                    TripLog, TripSection, User, Vehicle)
from services.bao_mat import bam_mat_khau  # noqa: E402

D = dt.date
MAT_KHAU_DEMO = "1234"     # bản demo — đổi ngay khi lên máy thật (qua màn Tài khoản)


def dong(section, item_key, qty, unit_price, currency="LAK", place=None, paid_by_epl=True, acct=None, name=None):
    tk = acct or {"fuel": "625/371", "travel": "625/402", "repair": "614/402", "other": "625/402"}[section]
    return dict(section=section, item_key=item_key, item_name=name, qty=qty, unit_price=unit_price,
                currency=currency, place=place, paid_by_epl=paid_by_epl, acct_code=tk)


# Bộ chi phí đi đường chuẩn — đúng 7 dòng trong sheet "ໃບບິນອອກລົດ" mục IV
def di_duong_chuan():
    return [dong("travel", "x_water", 1, 60000), dong("travel", "x_vn", 1, 430000),
            dong("travel", "x_chip_lao", 1, 620000), dong("travel", "x_chip_vn", 1, 1500000),
            dong("travel", "x_toll", 1, 1833500), dong("travel", "x_trip", 1, 1800000),
            dong("travel", "x_phone", 1, 150000)]


def gieo(db):
    # ---- tài khoản theo vai (sheet ໜ້າວຽກ)
    users = [
        ("thabok", "ສົມໄຊ (Somchai)", "yard", "TB"), ("ketoan", "ນາງ ພອນ (Phone)", "acct", "KT"),
        ("khonl", "ທ້າວ ວິໄລ (Vilay)", "fuel", "KN"), ("quyvc", "ນາງ ມະນີ (Manee)", "treasury", "QV"),
        ("quytb", "ນາງ ດາວ (Dao)", "cash", "CE"), ("doanhthu", "ທ້າວ ຄຳ (Kham)", "rev", "DT"),
        ("admin", "Admin", "admin", "AD"),
    ]
    for u, ten, vai, av in users:
        db.add(User(username=u, password_hash=bam_mat_khau(MAT_KHAU_DEMO), full_name=ten, role=vai, avatar=av))

    for ma, gt in (("USD", 22000), ("THB", 700), ("VND", 1.2), ("LAK", 1)):
        db.add(ExchangeRate(code=ma, rate_to_lak=gt))

    # ---- danh mục
    kh = {t: Customer(name=t) for t in ("ຄຳຕຸ້ຍ", "ນາງ ວັນນາ")}
    for c in kh.values(): db.add(c)
    tx = {t: Driver(name=t) for t in ("ທ້າວ ທັດສະດາພອນ", "ທ້າວ ບຸນມີ", "ທ້າວ ສົມພອນ")}
    for d in tx.values(): db.add(d)
    xe = {
        "341": Vehicle(truck_no="341", brand_model="HOWO-430", plate_head="ບອ 3262", plate_trailer="ບອ 3282"),
        "342": Vehicle(truck_no="342", brand_model="HOWO-430", plate_head="ບອ 3311", plate_trailer="ບອ 3312"),
        "ຮ່ວມ-07": Vehicle(truck_no="ຮ່ວມ-07", brand_model="SHACMAN", plate_head="ກຂ 8812", plate_trailer="ກຂ 8813",
                          owner_type="joint", owner_name="ທ້າວ ຄຳຫລ້າ"),
    }
    for v in xe.values(): db.add(v)
    for ten, khoa, tk, han in (("ຊີບປີງ ລາວ (ສາງພາສີ)", "x_chip_lao", "625/402", "t_monthly"),
                               ("ຊີບປີງ ຫວຽດ", "x_chip_vn", "625/402", "t_monthly"),
                               ("ຮ້ານຢາງ", "x_tire", "614/402", "t_monthly"),
                               ("ທາງດ່ວນ (ບັດ)", "x_toll", "625/402", "t_prepaid")):
        db.add(Supplier(name=ten, item_key=khoa, acct_code=tk, payment_term=han))
    db.flush()

    # ---- năm phiếu
    def phieu(**k):
        chi = k.pop("chi", [])
        tt_muc = k.pop("tt_muc", None)
        p = Trip(**k)
        # chép xe/tài xế/khách từ danh mục
        x = xe.get(p.truck_no)
        if x:
            p.vehicle_id, p.brand_model, p.plate_head, p.plate_trailer = x.id, x.brand_model, x.plate_head, x.plate_trailer
            if x.owner_type == "joint": p.company, p.owner_name = "joint", x.owner_name
        if p.driver_name in tx: p.driver_id = tx[p.driver_name].id
        if p.customer_name in kh: p.customer_id = kh[p.customer_name].id
        p.created_by = "ສົມໄຊ (Somchai)"
        db.add(p); db.flush()
        for i, d in enumerate(chi, 1):
            db.add(TripExpense(trip_id=p.id, line_no=i, **d))
        # trạng thái duyệt mặc định: xe vừa xuất bến = đã nhập; đã tới = nhiên liệu đã kiểm; đã thu = xong hết
        for m in MUC:
            if tt_muc and m in tt_muc: st = tt_muc[m]
            elif p.finance_status == "paid": st = "paid" if m in ("fuel", "travel", "repair", "other") else "verified"
            elif p.transport_status == "dispatched": st = "entered"
            else: st = "verified" if m == "fuel" else "entered"
            db.add(TripSection(trip_id=p.id, section=m, status=st))
        db.add(TripLog(trip_id=p.id, user_name="ສົມໄຊ (Somchai)", role="yard", action="a_create"))
        return p

    # Phiếu 1 — dòng thật trong Excel: 42,06 t đi · 41,30 t tới · 41 USD/t · đang đi · chưa thu
    phieu(doc_no="T4-0428-08/EPL", doc_date=D(2026, 8, 19), out_date=D(2026, 8, 19), back_date=D(2026, 8, 22),
          truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=7891, odo_back=6921,
          customer_name="ຄຳຕຸ້ຍ", origin="ກາສີ", destination="ກາລໍ", ore_bill_date=D(2026, 8, 19),
          weight_origin=42.06, weight_dest=41.30, price_usd=41,
          transport_status="transit", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 100, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 750, 28000, "VND", "fp_vn")]
              + di_duong_chuan())
    phieu(doc_no="T4-0429-08/EPL", doc_date=D(2026, 8, 19), out_date=D(2026, 8, 19), back_date=D(2026, 8, 22),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=5120, odo_back=6090,
          customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2231", origin="ກາສີ", destination="ທ່າເຮືອກະລໍ",
          weight_origin=42.30, weight_dest=42.06, price_usd=41, transport_status="arrived", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 120, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 700, 28000, "VND", "fp_vn")]
              + di_duong_chuan()
              + [dong("repair", "x_tire", 1, 150000, acct="614/402"), dong("repair", "x_air", 1, 500000, acct="614/371"),
                 dong("other", "x_misc", 1, 150000)])
    phieu(doc_no="T4-0430-08/EPL", doc_date=D(2026, 8, 20), out_date=D(2026, 8, 20), back_date=D(2026, 8, 23),
          truck_no="ຮ່ວມ-07", driver_name="ທ້າວ ສົມພອນ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2235", origin="ກາສີ", destination="ທ່າເຮືອກະລໍ",
          weight_origin=41.00, weight_dest=40.50, price_usd=41, hire_price_usd=40.5, fee_pct=2, over_limit_t=40, over_price_usd=1,
          transport_status="arrived", finance_status="partial",
          chi=[dong("fuel", "diesel", 150, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 600, 28000, "VND", "fp_vn", paid_by_epl=False),
               dong("travel", "x_toll", 1, 1833500), dong("travel", "x_chip_lao", 1, 620000),
               dong("travel", "x_vn", 1, 430000, paid_by_epl=False)])
    phieu(doc_no="T4-0431-08/EPL", doc_date=D(2026, 8, 21), out_date=D(2026, 8, 21), back_date=D(2026, 8, 24),
          truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=6921, odo_back=7900,
          customer_name="ນາງ ວັນນາ", ore_bill_no="HR-2240", origin="ກາສີ", destination="ກາລໍ",
          weight_origin=40.80, weight_dest=40.60, price_usd=42, transport_status="arrived", finance_status="paid", invoiced=True,
          chi=[dong("fuel", "diesel", 110, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 720, 28000, "VND", "fp_vn")]
              + di_duong_chuan())
    phieu(doc_no="T4-0432-08/EPL", doc_date=D(2026, 8, 23), out_date=D(2026, 8, 23),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=6090,
          customer_name="ຄຳຕຸ້ຍ", origin="ກາສີ", destination="ທ່າເຮືອກະລໍ",
          weight_origin=41.90, weight_dest=None, price_usd=41, transport_status="dispatched", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 150, 30000, "LAK", "fp_yard"),
               dong("travel", "x_water", 1, 60000), dong("travel", "x_vn", 1, 430000), dong("travel", "x_phone", 1, 150000)])

    # ---- kho nhiên liệu: một lần nhập, các lần xuất theo phiếu
    db.add(FuelMove(move_date=D(2026, 8, 15), doc_no="PN-0815", kind="in", qty_l=5000, unit_price=28500, by_user="ນາງ ພອນ (Phone)"))
    for ngay, so, xe_, lit in ((D(2026, 8, 19), "T4-0428", "341", 100), (D(2026, 8, 19), "T4-0429", "342", 120),
                               (D(2026, 8, 20), "T4-0430", "ຮ່ວມ-07", 150), (D(2026, 8, 21), "T4-0431", "341", 110),
                               (D(2026, 8, 23), "T4-0432", "342", 150)):
        db.add(FuelMove(move_date=ngay, doc_no=so, kind="out", truck_no=xe_, qty_l=lit, unit_price=30000, by_user="ນາງ ພອນ (Phone)"))

    # ---- kho phụ tùng
    for ten, dv, ton, toi_thieu, gia, ngay, xe_ in (("ເຕົ້າລົມ (bầu hơi)", "u_pc", 2, 2, 500000, D(2026, 8, 19), "341"),
                                                     ("ໄສ້ກອງນ້ຳມັນ (lọc dầu)", "u_pc", 8, 4, 180000, D(2026, 8, 21), "341"),
                                                     ("ຢາງລົດ (lốp)", "u_pc", 3, 4, 3200000, D(2026, 8, 10), "342"),
                                                     ("ຜ້າເບຣກ (bố thắng)", "u_set", 5, 2, 950000, D(2026, 8, 2), "341"),
                                                     ("ນ້ຳມັນເຄື່ອງ (nhớt)", "u_l", 60, 40, 85000, D(2026, 8, 21), "341")):
        db.add(Part(name=ten, unit=dv, qty=ton, min_qty=toi_thieu, unit_price=gia, last_date=ngay, last_truck=xe_))
    db.commit()


def main():
    dung_lai = "--dung-lai" in sys.argv
    if dung_lai:
        import models  # noqa: F401
        Base.metadata.drop_all(bind=engine)
        print("Đã xoá toàn bộ bảng.")
    tao_bang()
    db = SessionLocal()
    try:
        if db.query(User).count():
            print("DB đã có dữ liệu — không gieo lại. Dùng --dung-lai nếu muốn dựng lại từ đầu.")
            return
        gieo(db)
        print("Đã gieo: %d tài khoản · %d khách · %d xe · %d tài xế · %d phiếu · %d dòng chi" % (
            db.query(User).count(), db.query(Customer).count(), db.query(Vehicle).count(),
            db.query(Driver).count(), db.query(Trip).count(), db.query(TripExpense).count()))
        print("Mật khẩu mọi tài khoản demo: %s" % MAT_KHAU_DEMO)
    finally:
        db.close()


if __name__ == "__main__":
    main()
