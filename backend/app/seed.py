# -*- coding: utf-8 -*-
"""Gieo bộ dữ liệu mẫu — CHÉP TỪ EXCEL của họ, không bịa.

Nguồn: sheet "ໜ້າລາຍງານຂົນສົ່ງ" (dòng 1: phiếu T4-0428-08/EPL) và "ໃບບິນອອກລົດ" (chi tiết chi
phí của đúng phiếu đó), cộng bốn phiếu minh hoạ thêm trong bản giao diện mẫu để bảng theo
dõi có đủ trạng thái để nhìn: đang đi · đã tới · xe liên kết · đã thu tiền · vừa xuất bến.
Thêm: hai tuyến chuẩn (ກາສີ → ກາລໍ, ກາສີ → ທ່າເຮືອກະລໍ), ba rơ-moóc lắp vào ba đầu kéo, bằng lái tài xế,
và diễn biến trên đường của phiếu đang chạy.

    python backend/app/seed.py            # chỉ gieo khi DB trống
    python backend/app/seed.py --dung-lai # XOÁ hết bảng rồi dựng lại và gieo — chỉ máy dev
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, SessionLocal, engine, tao_bang  # noqa: E402
from models import (MUC, Customer, Driver, DriverLicense, ExchangeRate, FuelMove, FuelPlace, Part, Route,  # noqa: E402
                    RouteStop, Supplier, Trailer, TrailerAssignment, Trip, TripEvent, TripExpense, TripLog,
                    TripSection, User, Vehicle, Voucher)
from services.bao_mat import bam_mat_khau  # noqa: E402

D = dt.date
MAT_KHAU_DEMO = "1234"     # bản demo — đổi ngay khi lên máy thật (qua màn Tài khoản)


def ma_tk(company, section, source=None, place=None):
    if section == "fuel" and source is None:
        source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    duoi = "371" if source == "kho" else "402"
    return ("4022/" if company == "joint" else ("614/" if section == "repair" else "625/")) + duoi


def dong(section, item_key, qty, unit_price, currency="LAK", place=None, paid_by_epl=True, source=None, name=None):
    if section == "fuel": source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    if section == "repair" and source is None: source = "mua"
    return dict(section=section, item_key=item_key, item_name=name, qty=qty, unit_price=unit_price,
                currency=currency, place=place, paid_by_epl=paid_by_epl, source=source)


# Bộ chi phí đi đường chuẩn — đúng 7 dòng trong sheet "ໃບບິນອອກລົດ" mục IV
def di_duong_chuan():
    return [dong("travel", "x_water", 1, 60000), dong("travel", "x_vn", 1, 430000),
            dong("travel", "x_chip_lao", 1, 620000), dong("travel", "x_chip_vn", 1, 1500000),
            dong("travel", "x_toll", 1, 1833500), dong("travel", "x_trip", 1, 1800000),
            dong("travel", "x_phone", 1, 150000)]


def gieo(db):
    # ---- điểm đổ nhiên liệu (ສະຖານທີ່ໃສ່ນໍ້າມັນ). Kho của EPL thì LĨNH; trạm bán dầu thì MUA.
    diem_do = {
        "fp_yard": FuelPlace(code="KHO-TB", name="ສາງນໍ້າມັນ ທ່າບົກ (Kho dầu Thà Bốc)", country="LA",
                             owner_type="epl", address="ສະໜາມທ່າບົກ"),
        "fp_vc": FuelPlace(code="KHO-VC", name="ສາງນໍ້າມັນ ວຽງຈັນ (Kho dầu Viêng Chăn)", country="LA",
                           owner_type="epl", address="ວຽງຈັນ"),
        "fp_vn": FuelPlace(code="VN-01", name="ປໍ້ານໍ້າມັນ ຫວຽດນາມ (Trạm dầu Việt Nam)", country="VN",
                           owner_type="ngoai", note="Đổ chiều về để chạy ngược sang Lào"),
        "fp_other": FuelPlace(code="LA-02", name="ປໍ້ານໍ້າມັນ ຂ້າງທາງ (Trạm dầu dọc đường)", country="LA",
                              owner_type="ngoai"),
    }
    for x in diem_do.values():
        db.add(x)
    db.flush()

    # ---- tài khoản theo vai (sheet ໜ້າວຽກ)
    users = [
        ("thabok", "ສົມໄຊ (Somchai)", "yard", "TB", None), ("ketoan", "ນາງ ພອນ (Phone)", "acct", "KT", None),
        ("khonl", "ທ້າວ ວິໄລ (Vilay)", "fuel", "KN", None), ("quyvc", "ນາງ ມະນີ (Manee)", "treasury", "QV", None),
        ("quytb", "ນາງ ດາວ (Dao)", "cash", "CE", None), ("doanhthu", "ທ້າວ ຄຳ (Kham)", "rev", "DT", None),
        # Thủ kho tại điểm đổ: mỗi người giữ MỘT kho, chỉ thấy phiếu lĩnh của kho mình.
        ("khotb", "ທ້າວ ບຸນມາ (Bounma)", "depot", "KT", "fp_yard"),
        ("khovc", "ນາງ ສີດາ (Sida)", "depot", "KV", "fp_vc"),
        ("admin", "Admin", "admin", "AD", None),
    ]
    for u, ten, vai, av, kho in users:
        db.add(User(username=u, password_hash=bam_mat_khau(MAT_KHAU_DEMO), full_name=ten, role=vai, avatar=av,
                    place_id=diem_do[kho].id if kho else None))

    for ma, gt in (("USD", 22000), ("THB", 700), ("VND", 1.2), ("LAK", 1)):
        db.add(ExchangeRate(code=ma, rate_to_lak=gt))

    # ---- danh mục
    kh = {t: Customer(name=t) for t in ("ຄຳຕຸ້ຍ", "ນາງ ວັນນາ")}
    kh["ຄຳຕຸ້ຍ"].phone = "020 5555 1234"
    for c in kh.values(): db.add(c)

    # Rơ-moóc là thực thể riêng; lắp vào đầu kéo qua trailer_id
    rm = {
        "ບອ 3282": Trailer(plate="ບອ 3282", trailer_type="ຕ້ວນຖັງ (thùng ben)", capacity_t=42, year=2019, insurance_exp=D(2027, 3, 1), inspection_exp=D(2026, 12, 15), status="attached"),
        "ບອ 3312": Trailer(plate="ບອ 3312", trailer_type="ຕ້ວນຖັງ (thùng ben)", capacity_t=42, year=2019, insurance_exp=D(2027, 3, 1), inspection_exp=D(2026, 10, 2), status="attached"),
        "ບອ 3399": Trailer(plate="ບອ 3399", trailer_type="ຕ້ວນຖັງ (thùng ben)", capacity_t=40, year=2017, insurance_exp=D(2026, 9, 20), inspection_exp=D(2026, 9, 25), status="maintenance",
                          note="Nứt sàn, đang hàn tại Thà Bốk — dự phòng cho 341/342"),
        "ກຂ 8813": Trailer(plate="ກຂ 8813", trailer_type="ຕ້ວນຖັງ", capacity_t=40, owner_type="joint", owner_name="ທ້າວ ຄຳຫລ້າ", status="attached"),
    }
    for t in rm.values(): db.add(t)
    db.flush()
    xe = {
        "341": Vehicle(truck_no="341", brand_model="HOWO-430", year=2019, plate_head="ບອ 3262", trailer_id=rm["ບອ 3282"].id, plate_trailer="ບອ 3282",
                       engine_no="WD615.47-1903421", chassis_no="LZZ5EXSB3KN123456", insurance_exp=D(2027, 3, 1), inspection_exp=D(2026, 12, 15),
                       road_permit_exp=D(2026, 9, 30), odometer_km=7891, next_service_km=10000, status="on_trip"),
        "342": Vehicle(truck_no="342", brand_model="HOWO-430", year=2019, plate_head="ບອ 3311", trailer_id=rm["ບອ 3312"].id, plate_trailer="ບອ 3312",
                       engine_no="WD615.47-1903587", chassis_no="LZZ5EXSB3KN123789", insurance_exp=D(2027, 3, 1), inspection_exp=D(2026, 10, 2),
                       road_permit_exp=D(2027, 1, 31), odometer_km=6090, next_service_km=6000, status="on_trip"),
        "ຮ່ວມ-07": Vehicle(truck_no="ຮ່ວມ-07", brand_model="SHACMAN", year=2018, plate_head="ກຂ 8812", trailer_id=rm["ກຂ 8813"].id, plate_trailer="ກຂ 8813",
                          owner_type="joint", owner_name="ທ້າວ ຄຳຫລ້າ", status="available"),
    }
    for v in xe.values(): db.add(v)
    db.flush()
    for so, bien in (("341", "ບອ 3282"), ("342", "ບອ 3312"), ("ຮ່ວມ-07", "ກຂ 8813")):
        db.add(TrailerAssignment(trailer_id=rm[bien].id, vehicle_id=xe[so].id, attached_at=dt.datetime(2026, 1, 5), by_user="ສົມໄຊ (Somchai)"))
    # 341 từng chạy với 3399 trước khi 3399 nứt sàn
    db.add(TrailerAssignment(trailer_id=rm["ບອ 3399"].id, vehicle_id=xe["341"].id, attached_at=dt.datetime(2025, 6, 1),
                             detached_at=dt.datetime(2026, 1, 5), reason="Nứt sàn — đưa đi hàn", by_user="ສົມໄຊ (Somchai)"))

    tx = {
        "ທ້າວ ທັດສະດາພອນ": Driver(driver_code="DRV-01", name="ທ້າວ ທັດສະດາພອນ", phone="020 9876 1111", dob=D(1988, 4, 12), role="main", hire_date=D(2021, 3, 1),
                                license_no="LA-2201345", license_type="C", license_valid_from=D(2022, 5, 10), license_valid_to=D(2027, 5, 10),
                                default_vehicle_id=xe["341"].id, status="on_trip"),
        "ທ້າວ ບຸນມີ": Driver(driver_code="DRV-02", name="ທ້າວ ບຸນມີ", phone="020 9876 2222", dob=D(1991, 9, 3), role="main", hire_date=D(2022, 8, 15),
                          license_no="LA-2318877", license_type="C", license_valid_from=D(2023, 2, 1), license_valid_to=D(2026, 10, 1),   # sắp hết hạn → cờ vàng
                          default_vehicle_id=xe["342"].id, status="on_trip"),
        "ທ້າວ ສົມພອນ": Driver(driver_code="DRV-LK-01", name="ທ້າວ ສົມພອນ", phone="020 5555 7777", role="main",
                           license_no="LA-1907720", license_type="C", license_valid_from=D(2019, 7, 1), license_valid_to=D(2026, 7, 1),   # đã hết hạn → cờ đỏ
                           status="available", note="Tài xế của chủ xe liên kết ທ້າວ ຄຳຫລ້າ"),
    }
    for d in tx.values(): db.add(d)
    db.flush()
    for d in tx.values():
        db.add(DriverLicense(driver_id=d.id, license_no=d.license_no, license_type=d.license_type, valid_from=d.license_valid_from,
                             valid_to=d.license_valid_to, issued_by="ກົມຂົນສົ່ງ ວຽງຈັນ", verified_by="ນາງ ພອນ (Phone)"))
    # Tài khoản vai TÀI XẾ — mỗi tài xế một tài khoản, chỉ thấy phiếu của mình: bấm Xuất phát, Báo hỏng
    for u, d in (("tx01", tx["ທ້າວ ທັດສະດາພອນ"]), ("tx02", tx["ທ້າວ ບຸນມີ"]), ("tx03", tx["ທ້າວ ສົມພອນ"])):
        db.add(User(username=u, password_hash=bam_mat_khau(MAT_KHAU_DEMO), full_name=d.name, role="driver", avatar="TX", driver_id=d.id))

    for ten, khoa, tk, han in (("ຊີບປີງ ລາວ (ສາງພາສີ)", "x_chip_lao", "625/402", "t_monthly"),
                               ("ຊີບປີງ ຫວຽດ", "x_chip_vn", "625/402", "t_monthly"),
                               ("ຮ້ານຢາງ", "x_tire", "614/402", "t_monthly"),
                               ("ທາງດ່ວນ (ບັດ)", "x_toll", "625/402", "t_prepaid")):
        db.add(Supplier(name=ten, item_key=khoa, acct_code=tk, payment_term=han))

    # ---- tuyến đường (chặng, km, BOT)
    # Toạ độ ĐẠI KHÁI của các điểm trên hai tuyến, đủ để bản đồ vẽ đúng hình. Người dùng sửa lại
    # cho chuẩn ngay trên màn Tuyến đường; không có toạ độ thì màn Theo dõi chỉ bỏ phần bản đồ.
    TOA_DO = {
        "ກາສີ (ບ່ອນຂຸດແຮ່)": (19.1500, 102.2500),      # mỏ quặng Kasi
        "ທ່າບົກ (ສະໜາມ EPL)": (18.4400, 103.1500),     # bãi Thà Bốc
        "ດ່ານ ນໍ້າພາວ": (18.3800, 105.1100),            # cửa khẩu Nậm Phao
        "ກາລໍ": (18.1000, 105.9000),
        "ທ່າເຮືອກະລໍ": (18.0700, 106.4200),            # cảng
    }
    tuyen = {}
    for ten, bot, diem in (
        ("ກາສີ → ກາລໍ", 1833500, [("ກາສີ (ບ່ອນຂຸດແຮ່)", 0), ("ທ່າບົກ (ສະໜາມ EPL)", 145), ("ດ່ານ ນໍ້າພາວ", 210), ("ກາລໍ", 130)]),
        ("ກາສີ → ທ່າເຮືອກະລໍ", 1833500, [("ກາສີ (ບ່ອນຂຸດແຮ່)", 0), ("ທ່າບົກ (ສະໜາມ EPL)", 145), ("ດ່ານ ນໍ້າພາວ", 210), ("ທ່າເຮືອກະລໍ", 150)]),
    ):
        r = Route(name=ten, origin=diem[0][0], destination=diem[-1][0], total_km=sum(k for _, k in diem), toll_lak=bot)
        db.add(r); db.flush()
        for i, (n, km) in enumerate(diem, 1):
            vt = TOA_DO.get(n, (None, None))
            db.add(RouteStop(route_id=r.id, seq=i, name=n, km_from_prev=km, lat=vt[0], lng=vt[1]))
        tuyen[ten] = r
    db.flush()

    # ---- năm phiếu
    def phieu(**k):
        chi = k.pop("chi", [])
        tt_muc = k.pop("tt_muc", None)
        ten_tuyen = k.pop("tuyen", None)
        su_kien = k.pop("su_kien", [])
        p = Trip(**k)
        x = xe.get(p.truck_no)
        if x:
            p.vehicle_id, p.brand_model, p.plate_head, p.plate_trailer = x.id, x.brand_model, x.plate_head, x.plate_trailer
            if x.owner_type == "joint": p.company, p.owner_name = "joint", x.owner_name
        if p.driver_name in tx: p.driver_id = tx[p.driver_name].id
        if p.customer_name in kh: p.customer_id = kh[p.customer_name].id
        if ten_tuyen: p.route_id = tuyen[ten_tuyen].id
        p.created_by = "ສົມໄຊ (Somchai)"
        db.add(p); db.flush()
        for i, d in enumerate(chi, 1):
            d = dict(d); d["acct_code"] = ma_tk(p.company, d["section"], d.get("source"), d.get("place"))
            if d.get("place") in diem_do:                   # nơi đổ cũ (chuỗi) → điểm đổ thật (bản ghi)
                d["place_id"] = diem_do[d["place"]].id
            db.add(TripExpense(trip_id=p.id, line_no=i, **d))
        # trạng thái duyệt mặc định: xe vừa xuất bến = đã nhập; đã tới = nhiên liệu đã kiểm; đã thu = xong hết
        for m in MUC:
            if tt_muc and m in tt_muc: st = tt_muc[m]
            elif p.finance_status == "paid": st = "paid" if m in ("fuel", "travel", "repair", "other") else "verified"
            elif p.transport_status == "dispatched": st = "entered"
            else: st = "verified" if m == "fuel" else "entered"
            db.add(TripSection(trip_id=p.id, section=m, status=st))
        db.add(TripLog(trip_id=p.id, user_name="ສົມໄຊ (Somchai)", role="yard", action="a_create"))
        for gio, kind, seq, ghi in su_kien:
            db.add(TripEvent(trip_id=p.id, ts=gio, kind=kind, stop_seq=seq, note=ghi, by_user="ສົມໄຊ (Somchai)",
                             incident_type="delay" if kind == "incident" else None))
        return p

    # Phiếu 1 — dòng thật trong Excel: 42,06 t đi · 41,30 t tới · 41 USD/t · đang đi · chưa thu
    phieu(doc_no="T4-0428-08/EPL", doc_date=D(2026, 8, 19), out_date=D(2026, 8, 19), back_date=D(2026, 8, 22),
          truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=7891, odo_back=6921, tuyen="ກາສີ → ກາລໍ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_date=D(2026, 8, 19),
          weight_origin=42.06, weight_dest=41.30, price_usd=41,
          transport_status="transit", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 100, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 750, 28000, "VND", "fp_vn")]
              + di_duong_chuan(),
          su_kien=[(dt.datetime(2026, 8, 19, 6, 30), "arrive_stop", 1, "Xe vào mỏ, bắt đầu lên hàng"),
                   (dt.datetime(2026, 8, 19, 13, 10), "arrive_stop", 2, "Về bãi Thà Bốk, cân 42,06 t"),
                   (dt.datetime(2026, 8, 20, 9, 0), "incident", 3, "Chờ làm thủ tục cửa khẩu 3 giờ")])
    phieu(doc_no="T4-0429-08/EPL", doc_date=D(2026, 8, 19), out_date=D(2026, 8, 19), back_date=D(2026, 8, 22),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=5120, odo_back=6090, tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2231",
          weight_origin=42.30, weight_dest=42.06, price_usd=41, transport_status="arrived", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 120, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 700, 28000, "VND", "fp_vn")]
              + di_duong_chuan()
              + [dong("repair", "x_tire", 1, 150000, source="mua"), dong("repair", None, 1, 500000, source="kho", name="ເຕົ້າລົມ (bầu hơi)"),
                 dong("other", "x_misc", 1, 150000)])
    phieu(doc_no="T4-0430-08/EPL", doc_date=D(2026, 8, 20), out_date=D(2026, 8, 20), back_date=D(2026, 8, 23),
          truck_no="ຮ່ວມ-07", driver_name="ທ້າວ ສົມພອນ", tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2235",
          weight_origin=41.00, weight_dest=40.50, price_usd=41, hire_price_usd=40.5, fee_pct=2, over_limit_t=40, over_price_usd=1,
          transport_status="arrived", finance_status="partial",
          chi=[dong("fuel", "diesel", 150, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 600, 28000, "VND", "fp_vn", paid_by_epl=False),
               dong("travel", "x_toll", 1, 1833500), dong("travel", "x_chip_lao", 1, 620000),
               dong("travel", "x_vn", 1, 430000, paid_by_epl=False)])
    phieu(doc_no="T4-0431-08/EPL", doc_date=D(2026, 8, 21), out_date=D(2026, 8, 21), back_date=D(2026, 8, 24),
          truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=6921, odo_back=7900, tuyen="ກາສີ → ກາລໍ",
          customer_name="ນາງ ວັນນາ", ore_bill_no="HR-2240",
          weight_origin=40.80, weight_dest=40.60, price_usd=42, transport_status="arrived", finance_status="paid", invoiced=True,
          chi=[dong("fuel", "diesel", 110, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 720, 28000, "VND", "fp_vn")]
              + di_duong_chuan())
    phieu(doc_no="T4-0432-08/EPL", doc_date=D(2026, 8, 23), out_date=D(2026, 8, 23),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=6090, tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ",
          weight_origin=41.90, weight_dest=None, price_usd=41, transport_status="dispatched", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 150, 30000, "LAK", "fp_yard"),
               dong("travel", "x_water", 1, 60000), dong("travel", "x_vn", 1, 430000), dong("travel", "x_phone", 1, 150000)])

    # ---- phiếu lĩnh (tờ giấy tài xế cầm đi, có mã QR)
    # Phiếu vừa xuất bến còn ĐANG CHỜ CẤP để màn Cấp phát có việc; các phiếu cũ thì tiền đã trao
    # tay rồi, đánh dấu "đã cấp" để bảng Tất toán có cả cột đã ứng lẫn cột đã chi.
    import secrets as _sc
    db.flush()          # phiên này autoflush=False: dòng chi của phiếu cuối chưa xuống DB thì query không thấy
    for pp in db.query(Trip).order_by(Trip.doc_no).all():
        dong_p = db.query(TripExpense).filter(TripExpense.trip_id == pp.id).all()
        tg = {"USD": pp.rate_usd or 22000, "THB": pp.rate_thb or 700, "VND": pp.rate_vnd or 1.2, "LAK": 1.0}
        ung = sum((e.qty or 0) * (e.unit_price or 0) * tg.get(e.currency or "LAK", 1)
                  for e in dong_p if e.paid_by_epl and e.source != "kho" and e.section in ("fuel", "travel", "other"))
        moi_chay = pp.transport_status == "dispatched"
        chung = dict(trip_id=pp.id, doc_date=pp.out_date or pp.doc_date, driver_id=pp.driver_id,
                     driver_name=pp.driver_name, truck_no=pp.truck_no, issued_by="ສົມໄຊ (Somchai)")
        if ung > 0:
            db.add(Voucher(kind="advance", doc_no="PTU-" + pp.doc_no, token=_sc.token_urlsafe(9),
                           amount_lak=round(ung, 2), status="cho" if moi_chay else "da_cap",
                           granted_by=None if moi_chay else "ນາງ ດາວ (Dao)",
                           granted_at=None if moi_chay else dt.datetime.utcnow(), **chung))
        if moi_chay:
            lit = sum(e.qty or 0 for e in dong_p if e.section == "fuel" and e.source == "kho" and e.paid_by_epl)
            if lit > 0:
                db.add(Voucher(kind="fuel", doc_no="PLNL-%s-1" % pp.doc_no, token=_sc.token_urlsafe(9),
                               place_id=diem_do["fp_yard"].id, qty_l=lit, status="cho", **chung))

    # ---- kho nhiên liệu: một lần nhập, các lần xuất theo phiếu
    db.add(FuelMove(move_date=D(2026, 8, 15), doc_no="PN-0815", kind="in", qty_l=5000, unit_price=28500, by_user="ນາງ ພອນ (Phone)"))
    for ngay, so, xe_, lit in ((D(2026, 8, 19), "T4-0428-08/EPL", "341", 100), (D(2026, 8, 19), "T4-0429-08/EPL", "342", 120),
                               (D(2026, 8, 20), "T4-0430-08/EPL", "ຮ່ວມ-07", 150), (D(2026, 8, 21), "T4-0431-08/EPL", "341", 110),
                               (D(2026, 8, 23), "T4-0432-08/EPL", "342", 150)):
        db.add(FuelMove(move_date=ngay, doc_no=so, kind="out", truck_no=xe_, qty_l=lit, unit_price=30000, by_user="ນາງ ພອນ (Phone)"))

    # ---- kho phụ tùng
    for ten, dv, ton, toi_thieu, gia, ngay, xe_ in (("ເຕົ້າລົມ (bầu hơi)", "u_pc", 2, 2, 500000, D(2026, 8, 19), "342"),
                                                     ("ໄສ້ກອງນ້ຳມັນ (lọc dầu)", "u_pc", 8, 4, 180000, D(2026, 8, 21), "341"),
                                                     ("ຢາງລົດ 12R22.5 (lốp)", "u_pc", 3, 4, 3200000, D(2026, 8, 10), "342"),
                                                     ("ຜ້າເບຣກ (bố thắng)", "u_set", 5, 2, 950000, D(2026, 8, 2), "341"),
                                                     ("ນ້ຳມັນເຄື່ອງ 15W-40 (nhớt)", "u_l", 60, 40, 85000, D(2026, 8, 21), "341")):
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
        print("Đã gieo: %d tài khoản · %d khách · %d xe · %d rơ-moóc · %d tài xế · %d tuyến · %d phiếu · %d dòng chi · %d sự kiện" % (
            db.query(User).count(), db.query(Customer).count(), db.query(Vehicle).count(), db.query(Trailer).count(),
            db.query(Driver).count(), db.query(Route).count(), db.query(Trip).count(), db.query(TripExpense).count(),
            db.query(TripEvent).count()))
        print("Mật khẩu mọi tài khoản demo: %s" % MAT_KHAU_DEMO)
    finally:
        db.close()


if __name__ == "__main__":
    main()
