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
from models import (MUC, Customer, CustomerRate, Driver, DriverLicense, ExchangeRate, FuelMove, FuelPlace, GoodsMove, Invoice, InvoicePayment, Owner, Part, Route,  # noqa: E402
                    RepairLine, RepairOrder, RouteStop, TollCard, TollCardMove, Sale, SaleLine, Supplier, Trailer, TrailerAssignment, Trip, TripEvent, TripExpense, TripGoods, TripLog,
                    TripPayment, TripSection, User, Vehicle, Voucher)
from services import chung_tu as CT  # noqa: E402
from services.bao_mat import bam_mat_khau  # noqa: E402
from services.tinh_toan import tinh_phieu, ty_gia  # noqa: E402

D = dt.date
MAT_KHAU_DEMO = "1234"     # bản demo — đổi ngay khi lên máy thật (qua màn Tài khoản)


def ma_tk(company, section, source=None, place=None):
    if section == "fuel" and source is None:
        source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    duoi = "371" if source == "kho" else "402"
    return ("4022/" if company == "joint" else ("614/" if section == "repair" else "625/")) + duoi


def dong(section, item_key, qty, unit_price, currency="LAK", place=None, paid_by_epl=True, source=None, name=None,
         ghi_no=False):
    if section == "fuel": source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    if section == "repair" and source is None: source = "mua"
    # ghi_no: đổ ở trạm ngoài mà TRẠM GHI SỔ, cuối tháng EPL trả hoặc cấn trừ với khách (C5.1)
    return dict(section=section, item_key=item_key, item_name=name, qty=qty, unit_price=unit_price,
                currency=currency, place=place, paid_by_epl=paid_by_epl, source=source, ghi_no=ghi_no)


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
        # Năm kho dầu anh Khampla kể thêm (C5.2, 22/09) — đủ bảy kho của EPL
        "fp_km28_vc": FuelPlace(code="KHO-KM28-VC", name="ສາງນໍ້າມັນ ຫຼັກ 28 ວຽງຈັນ (Kho dầu Km 28 Viêng Chăn)", country="LA",
                                owner_type="epl", address="ຫຼັກ 28, ວຽງຈັນ"),
        "fp_huaylek": FuelPlace(code="KHO-TB-HL", name="ສາງນໍ້າມັນ ສະໜາມທ່າບົກ ຫ້ວຍເລິກ (Kho dầu sân Thà Bốc Huay Lek)", country="LA",
                                owner_type="epl", address="ຫ້ວຍເລິກ"),
        "fp_thavai": FuelPlace(code="KHO-THAVAI", name="ສາງນໍ້າມັນ ບ້ານທວາຍ (Kho dầu bản Thavai)", country="LA",
                               owner_type="epl", address="ບ້ານທວາຍ"),
        "fp_thakhek": FuelPlace(code="KHO-TK", name="ສາງນໍ້າມັນ ສະໜາມທ່າແຂກ (Kho dầu sân Thakhek)", country="LA",
                                owner_type="epl", address="ທ່າແຂກ"),
        "fp_km28_tk": FuelPlace(code="KHO-KM28-TK", name="ສາງນໍ້າມັນ ເສັ້ນທາງຫຼັກ 28 ທ່າແຂກ, ທາງເລກ 8 (Kho dầu Km 28 Thakhek, đường 8)", country="LA",
                                owner_type="epl", address="ທາງເລກ 8, ທ່າແຂກ"),
    }
    for x in diem_do.values():
        db.add(x)
    db.flush()

    # ---- tài khoản theo vai (sheet ໜ້າວຽກ)
    users = [
        ("thabok", "ສົມໄຊ (Somchai)", "yard", "TB", None), ("ketoan", "ນາງ ພອນ (Phone)", "acct", "KT", None),
        ("ketoancp", "ນາງ ວິໄລວັນ (Vilayvanh)", "expacct", "KC", None),
        ("khonl", "ທ້າວ ວິໄລ (Vilay)", "fuel", "KN", None), ("quyvc", "ນາງ ມະນີ (Manee)", "treasury", "QV", None),
        ("quytb", "ນາງ ດາວ (Dao)", "cash", "CE", None), ("doanhthu", "ທ້າວ ຄຳ (Kham)", "rev", "DT", None),
        # Thủ kho tại điểm đổ: mỗi người giữ MỘT kho, chỉ thấy phiếu lĩnh của kho mình.
        ("khotb", "ທ້າວ ບຸນມາ (Bounma)", "depot", "KT", "fp_yard"),
        ("khovc", "ນາງ ສີດາ (Sida)", "depot", "KV", "fp_vc"),
        # Hai người ở Thà Bốc anh Khampla nói là người RIÊNG, không phải Admin Bãi (C1.2):
        ("khopt", "ທ້າວ ແກ້ວ (Keo)", "parts", "PT", None),        # thủ kho phụ tùng
        ("totsua", "ທ້າວ ສຸກ (Souk)", "repair", "SC", None),      # tổ sửa chữa
        ("admin", "Admin", "admin", "AD", None),
    ]
    for u, ten, vai, av, kho in users:
        db.add(User(username=u, password_hash=bam_mat_khau(MAT_KHAU_DEMO), full_name=ten, role=vai, avatar=av,
                    place_id=diem_do[kho].id if kho else None))

    for ma, gt in (("USD", 22000), ("THB", 700), ("VND", 1.2), ("CNY", 3000), ("LAK", 1)):
        db.add(ExchangeRate(code=ma, rate_to_lak=gt))

    # ---- chủ xe liên kết (anh Khampla C4.2 · C4.3): phí và cách trả riêng từng chủ
    chu = Owner(name="ທ້າວ ຄຳຫລ້າ", phone="020 5555 7777", fee_pct=2, over_limit_t=40, over_price=1, hire_ccy="LAK",
                pay_mode="thang", note="Hợp đồng thuê xe SHACMAN ຮ່ວມ-07, trả gộp cuối tháng bằng Kíp")
    db.add(chu); db.flush()

    # ---- danh mục
    kh = {t: Customer(name=t) for t in ("ຄຳຕຸ້ຍ", "ນາງ ວັນນາ", "ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ")}
    kh["ຄຳຕຸ້ຍ"].phone = "020 5555 1234"
    # Khách HỢP ĐỒNG: chạy nhiều chuyến trong tháng, cuối tháng nhận MỘT tờ hoá đơn gộp (C8.2).
    kh["ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ"].phone = "021 264 900"
    kh["ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ"].address = "ນະຄອນຫຼວງວຽງຈັນ"
    kh["ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ"].invoice_mode = "thang"
    kh["ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ"].note = "Hợp đồng tháng — cuối tháng gộp một hoá đơn cho mọi phiếu"
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
                          owner_type="joint", owner_id=chu.id, owner_name=chu.name, status="available"),
    }
    for v in xe.values(): db.add(v)
    db.flush()
    for so, bien in (("341", "ບອ 3282"), ("342", "ບອ 3312"), ("ຮ່ວມ-07", "ກຂ 8813")):
        db.add(TrailerAssignment(trailer_id=rm[bien].id, vehicle_id=xe[so].id, attached_at=dt.datetime(2026, 1, 5), by_user="ສົມໄຊ (Somchai)"))
    # 341 từng chạy với 3399 trước khi 3399 nứt sàn
    db.add(TrailerAssignment(trailer_id=rm["ບອ 3399"].id, vehicle_id=xe["341"].id, attached_at=dt.datetime(2025, 6, 1),
                             detached_at=dt.datetime(2026, 1, 5), reason="Nứt sàn — đưa đi hàn", by_user="ສົມໄຊ (Somchai)"))

    tx = {
        "ທ້າວ ທັດສະດາພອນ": Driver(driver_code="DRV-01", name="ທ້າວ ທັດສະດາພອນ", name_latin="Thatsadaphone", phone="020 9876 1111", dob=D(1988, 4, 12), role="main", hire_date=D(2021, 3, 1),
                                license_class_hr="C", license_status="active",
                                license_no="LA-2201345", license_type="C", license_valid_from=D(2022, 5, 10), license_valid_to=D(2027, 5, 10),
                                default_vehicle_id=xe["341"].id, status="on_trip"),
        "ທ້າວ ບຸນມີ": Driver(driver_code="DRV-02", name="ທ້າວ ບຸນມີ", name_latin="Bounmi", phone="020 9876 2222", dob=D(1991, 9, 3), role="main", hire_date=D(2022, 8, 15),
                          license_class_hr="C", license_status="active",
                          license_no="LA-2318877", license_type="C", license_valid_from=D(2023, 2, 1), license_valid_to=D(2026, 10, 1),   # sắp hết hạn → cờ vàng
                          default_vehicle_id=xe["342"].id, status="on_trip"),
        "ທ້າວ ສົມພອນ": Driver(driver_code="DRV-LK-01", name="ທ້າວ ສົມພອນ", name_latin="Somphone", phone="020 5555 7777", role="main",
                           license_class_hr="C", license_status="active",
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
    # TRẠM DẦU BÊN VIỆT NAM (C5.1): tài xế đổ dầu ghi nợ tại trạm, cuối tháng EPL không trả tiền mặt
    # mà CẤN TRỪ vào cước của khách đứng ra với trạm.
    tram_vn = Supplier(name="ປໍ້ານໍ້າມັນ ຫວຽດນາມ (Trạm dầu Việt Nam)", item_key="diesel", acct_code="625/4021",
                       payment_term="t_monthly", customer_id=kh["ຄຳຕຸ້ຍ"].id, customer_name="ຄຳຕຸ້ຍ",
                       note="Tài xế đổ ghi nợ; cuối tháng cấn trừ vào cước ຄຳຕຸ້ຍ")
    db.add(tram_vn); db.flush()
    diem_do["fp_vn"].supplier_id = tram_vn.id

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

    # ---- bảng giá khách × tuyến (K3): 41 USD/t như hoá đơn trong Excel; tuyến cảng xa hơn 43 USD/t
    for k in kh.values():
        db.add(CustomerRate(customer_id=k.id, route_id=tuyen["ກາສີ → ກາລໍ"].id, price=41, price_ccy="USD", hire_price=40.5, hire_ccy="USD", valid_from=D(2026, 1, 1), created_by="seed"))
        db.add(CustomerRate(customer_id=k.id, route_id=tuyen["ກາສີ → ທ່າເຮືອກະລໍ"].id, price=43, price_ccy="USD", valid_from=D(2026, 1, 1), created_by="seed"))
    # Khách vãng lai không hợp đồng: giá KHOÁN TRỌN CHUYẾN (anh Khampla C3.6) — 1.800 USD một chuyến, không nhân tấn
    db.add(CustomerRate(customer_id=kh["ນາງ ວັນນາ"].id, route_id=tuyen["ກາສີ → ທ່າເຮືອກະລໍ"].id, price=1800, price_ccy="USD",
                        price_mode="chuyen", valid_from=D(2026, 1, 1), note="Khoán trọn chuyến, không theo tấn", created_by="seed"))
    db.flush()

    # ---- năm phiếu
    def phieu(**k):
        chi = k.pop("chi", [])
        hang = k.pop("hang", None)          # dòng hàng: [(tên, tấn)] — DO gom là hàng bốc ở mỏ
        lay_tu = k.pop("lay_tu", None)      # DO giao lấy hàng từ phiếu gom nào: [(doc_no gom, tấn)]
        tt_muc = k.pop("tt_muc", None)
        ten_tuyen = k.pop("tuyen", None)
        su_kien = k.pop("su_kien", [])
        p = Trip(**k)
        x = xe.get(p.truck_no)
        if x:
            p.vehicle_id, p.brand_model, p.plate_head, p.plate_trailer = x.id, x.brand_model, x.plate_head, x.plate_trailer
            if x.owner_type == "joint": p.company, p.owner_name, p.owner_id = "joint", x.owner_name, x.owner_id
        if p.driver_name in tx: p.driver_id = tx[p.driver_name].id
        if p.customer_name in kh: p.customer_id = kh[p.customer_name].id
        if ten_tuyen: p.route_id = tuyen[ten_tuyen].id
        p.created_by = "ສົມໄຊ (Somchai)"
        db.add(p); db.flush()
        for i, d in enumerate(chi, 1):
            d = dict(d); d["acct_code"] = ma_tk(p.company, d["section"], d.get("source"), d.get("place"))
            if d.get("place") in diem_do:                   # nơi đổ cũ (chuỗi) → điểm đổ thật (bản ghi)
                dd = diem_do[d["place"]]
                d["place_id"] = dd.id
                if dd.owner_type != "epl" and dd.supplier_id:
                    d["supplier_id"] = dd.supplier_id       # trạm ngoài → công nợ của trạm đó (C5.1)
            db.add(TripExpense(trip_id=p.id, line_no=i, **d))
        # trạng thái duyệt mặc định: xe vừa xuất bến = đã nhập; đã tới = nhiên liệu đã kiểm; đã thu = xong hết
        for m in MUC:
            if tt_muc and m in tt_muc: st = tt_muc[m]
            elif p.finance_status == "paid": st = "paid" if m in ("fuel", "travel", "repair", "other") else "verified"
            elif p.transport_status == "dispatched": st = "entered"
            else: st = "verified" if m == "fuel" else "entered"
            db.add(TripSection(trip_id=p.id, section=m, status=st))
        for ten, tan in (hang or []):
            db.add(TripGoods(trip_id=p.id, loai="hang", goods_name=ten, qty_t=tan))
        for so_gom, tan in (lay_tu or []):
            g = db.query(Trip).filter(Trip.doc_no == so_gom).first()
            db.add(TripGoods(trip_id=p.id, loai="hang", goods_name="ແຮ່ເຫຼັກ (quặng sắt)", qty_t=tan,
                             tu_phieu_id=g.id if g else None))
            db.add(GoodsMove(move_date=p.out_date or p.doc_date, kind="out", goods_name="ແຮ່ເຫຼັກ (quặng sắt)",
                             qty_t=tan, trip_id=p.id, trip_doc_no=p.doc_no,
                             lo_trip_id=g.id if g else None, depot="Thà Bốc", by_user="ສົມໄຊ (Somchai)"))
        db.add(TripLog(trip_id=p.id, user_name="ສົມໄຊ (Somchai)", role="yard", action="a_create"))
        for gio, kind, seq, ghi in su_kien:
            db.add(TripEvent(trip_id=p.id, ts=gio, kind=kind, stop_seq=seq, note=ghi, by_user="ສົມໄຊ (Somchai)",
                             incident_type="delay" if kind == "incident" else None))
        return p

    # Phiếu 1 — dòng thật trong Excel: 42,06 t đi · 41,30 t tới · 41 USD/t · đang đi · chưa thu
    phieu(doc_no="T4-0428-08/EPL", doc_date=D(2026, 8, 19), out_date=D(2026, 8, 19), back_date=D(2026, 8, 22),
          truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=7891, odo_back=6921, tuyen="ກາສີ → ກາລໍ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_date=D(2026, 8, 19),
          weight_origin=42.06, weight_dest=41.30, price=41, price_ccy="USD",
          transport_status="transit", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 100, 30000, "LAK", "fp_yard"),
               dong("fuel", "diesel", 750, 28000, "VND", "fp_vn", ghi_no=True)]
              + di_duong_chuan(),
          su_kien=[(dt.datetime(2026, 8, 19, 6, 30), "arrive_stop", 1, "Xe vào mỏ, bắt đầu lên hàng"),
                   (dt.datetime(2026, 8, 19, 13, 10), "arrive_stop", 2, "Về bãi Thà Bốk, cân 42,06 t"),
                   (dt.datetime(2026, 8, 20, 9, 0), "incident", 3, "Chờ làm thủ tục cửa khẩu 3 giờ")])
    phieu(doc_no="T4-0429-08/EPL", doc_date=D(2026, 8, 19), out_date=D(2026, 8, 19), back_date=D(2026, 8, 22),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=5120, odo_back=6090, tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2231",
          # Khách Trung Quốc ký hợp đồng bằng NHÂN DÂN TỆ — 300 CNY/tấn, không phải USD.
          weight_origin=42.30, weight_dest=42.06, price=300, price_ccy="CNY", transport_status="arrived", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 120, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 700, 28000, "VND", "fp_vn")]
              + di_duong_chuan()
              + [dong("repair", "x_tire", 1, 150000, source="mua"), dong("repair", None, 1, 500000, source="kho", name="ເຕົ້າລົມ (bầu hơi)"),
                 dong("other", "x_misc", 1, 150000)])
    phieu(doc_no="T4-0430-08/EPL", doc_date=D(2026, 8, 20), out_date=D(2026, 8, 20), back_date=D(2026, 8, 23),
          truck_no="ຮ່ວມ-07", driver_name="ທ້າວ ສົມພອນ", tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2235",
          # Xe liên kết: bán bằng USD nhưng thuê xe Lào trả bằng KÍP — hai tiền khác nhau trên một phiếu.
          weight_origin=41.00, weight_dest=40.50, price=41, price_ccy="USD",
          hire_price=890000, hire_ccy="LAK", fee_pct=2, over_limit_t=40, over_price=22000,
          transport_status="arrived", finance_status="partial", invoiced=True,
          locked=True, locked_by="ນາງ ຄຳ (Kham)", locked_at=dt.datetime(2026, 8, 26, 9, 0),
          chi=[dong("fuel", "diesel", 150, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 600, 28000, "VND", "fp_vn", paid_by_epl=False),
               dong("travel", "x_toll", 1, 1833500), dong("travel", "x_chip_lao", 1, 620000),
               dong("travel", "x_vn", 1, 430000, paid_by_epl=False)])
    phieu(doc_no="T4-0431-08/EPL", doc_date=D(2026, 8, 21), out_date=D(2026, 8, 21), back_date=D(2026, 8, 24),
          truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=6921, odo_back=7900, tuyen="ກາສີ → ກາລໍ",
          customer_name="ນາງ ວັນນາ", ore_bill_no="HR-2240",
          weight_origin=40.80, weight_dest=40.60, price=42, price_ccy="USD", transport_status="arrived", finance_status="paid", invoiced=True,
          locked=True, locked_by="ນາງ ຄຳ (Kham)", locked_at=dt.datetime(2026, 8, 25, 9, 0),
          chi=[dong("fuel", "diesel", 110, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 720, 28000, "VND", "fp_vn")]
              + di_duong_chuan())
    phieu(doc_no="T4-0432-08/EPL", doc_date=D(2026, 8, 23), out_date=D(2026, 8, 23),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=6090, tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ",
          # Khách trong nước trả thẳng bằng KÍP: 900.000 LAK/tấn.
          weight_origin=41.90, weight_dest=None, price=900000, price_ccy="LAK", transport_status="dispatched", finance_status="unpaid",
          chi=[dong("fuel", "diesel", 150, 30000, "LAK", "fp_yard"),
               dong("travel", "x_water", 1, 60000), dong("travel", "x_vn", 1, 430000), dong("travel", "x_phone", 1, 150000)])

    # ---- LUỒNG HAI DO (chốt 21/09): một phiếu đi GOM hàng ở mỏ về bãi, rồi một phiếu đi GIAO hàng
    # đó từ bãi ra cảng. Hai phiếu nối nhau qua lô hàng trong kho bãi, và xe hai chặng khác nhau.
    pg = phieu(doc_no="G4-0101-09/EPL", kind="gom", doc_date=D(2026, 9, 14), out_date=D(2026, 9, 14), back_date=D(2026, 9, 15),
               truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=7900, odo_back=8045, tuyen="ກາສີ → ກາລໍ",
               customer_name="ຄຳຕຸ້ຍ", ore_bill_no="HR-2301", ore_bill_date=D(2026, 9, 14),
               origin="ກາສີ (ບ່ອນຂຸດແຮ່)", destination="ທ່າບົກ (ສະໜາມ EPL)",
               weight_origin=42.50, weight_dest=42.30,     # cân mỏ 42,50 · cân bãi 42,30 → hao 0,20
               price=6, price_ccy="USD",                   # B4: khách trả cước riêng cho chặng gom (6 USD/t)
               transport_status="arrived", finance_status="unpaid",
               hang=[("ແຮ່ເຫຼັກ (quặng sắt)", 42.50)],
               chi=[dong("fuel", "diesel", 60, 30000, "LAK", "fp_yard"), dong("travel", "x_water", 1, 60000)])
    db.flush()
    db.add(GoodsMove(move_date=D(2026, 9, 15), kind="in", goods_name="ແຮ່ເຫຼັກ (quặng sắt)", qty_t=42.30,
                     trip_id=pg.id, trip_doc_no=pg.doc_no, lo_trip_id=pg.id, depot="Thà Bốc", by_user="ສົມໄຊ (Somchai)"))
    db.add(TripGoods(trip_id=pg.id, loai="hao_hut", goods_name="ແຮ່ເຫຼັກ (quặng sắt)", qty_t=0.20,
                     note="Cân mỏ 42.5 t − cân bãi 42.3 t"))
    db.flush()
    CT.ghi(db, "PNK_HH", nguon_bang="trips", nguon_id=pg.id, trip=pg, ngay=D(2026, 9, 15), doi_tuong_loai="kho",
           doi_tuong_ten="Thà Bốc", by_user="ສົມໄຊ (Somchai)", mo_ta="Nhập kho hàng từ %s · 42.3 tấn" % pg.doc_no,
           payload={"tan": 42.3, "boc_len": 42.5, "hao_hut": 0.2})
    pv = phieu(doc_no="T4-0433-09/EPL", kind="giao", doc_date=D(2026, 9, 16), out_date=D(2026, 9, 16),
          truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=6300, tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
          customer_name="ຄຳຕຸ້ຍ", origin="ທ່າບົກ (ສະໜາມ EPL)", destination="ທ່າເຮືອກະລໍ",
          price=43, price_ccy="USD", weight_origin=30.00, transport_status="transit", finance_status="unpaid",
          lay_tu=[("G4-0101-09/EPL", 30.00)],
          chi=[dong("fuel", "diesel", 90, 30000, "LAK", "fp_yard"), dong("travel", "x_toll", 1, 1833500)])
    db.flush()
    CT.ghi(db, "PXK_HH", nguon_bang="trips", nguon_id=pv.id, trip=pv, ngay=D(2026, 9, 16), doi_tuong_loai="kho",
           doi_tuong_ten="Thà Bốc", by_user="ສົມໄຊ (Somchai)", mo_ta="Xuất kho hàng đi giao %s · 30.0 tấn" % pv.doc_no,
           payload={"tan": 30.0, "dong": [{"hang": "ແຮ່ເຫຼັກ (quặng sắt)", "tan": 30.0, "lo": pg.id}]})

    # ---- hai phiếu của KHÁCH HỢP ĐỒNG trong tháng 9: đã khoá, chờ gộp một hoá đơn cuối tháng.
    # Đây là dữ liệu để thấy màn Hoá đơn gộp có việc: khách này không xuất hoá đơn từng phiếu.
    muc_xong = {"info": "verified", "trans": "verified", "fuel": "paid", "travel": "paid"}
    hd_phieu = [
        phieu(doc_no="T4-0440-09/EPL", doc_date=D(2026, 9, 3), out_date=D(2026, 9, 3), back_date=D(2026, 9, 6),
              truck_no="341", driver_name="ທ້າວ ທັດສະດາພອນ", odo_out=8045, odo_back=9010, tuyen="ກາສີ → ກາລໍ",
              customer_name="ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ", ore_bill_no="HR-2310", ore_bill_date=D(2026, 9, 3),
              weight_origin=41.50, weight_dest=41.20, price=44, price_ccy="USD",
              transport_status="arrived", finance_status="unpaid", tt_muc=muc_xong,
              locked=True, locked_by="ນາງ ຄຳ (Kham)", locked_at=dt.datetime(2026, 9, 8, 9, 0),
              chi=[dong("fuel", "diesel", 115, 30000, "LAK", "fp_yard"),
                   dong("fuel", "diesel", 700, 28000, "VND", "fp_vn", ghi_no=True)]
                  + di_duong_chuan()),
        phieu(doc_no="T4-0441-09/EPL", doc_date=D(2026, 9, 11), out_date=D(2026, 9, 11), back_date=D(2026, 9, 14),
              truck_no="342", driver_name="ທ້າວ ບຸນມີ", odo_out=6200, odo_back=7150, tuyen="ກາສີ → ທ່າເຮືອກະລໍ",
              customer_name="ບໍລິສັດ ລາວ-ຈີນ ມີເນີໂຣ", ore_bill_no="HR-2318", ore_bill_date=D(2026, 9, 11),
              weight_origin=40.90, weight_dest=40.70, price=44, price_ccy="USD",
              transport_status="arrived", finance_status="unpaid", tt_muc=muc_xong,
              locked=True, locked_by="ນາງ ຄຳ (Kham)", locked_at=dt.datetime(2026, 9, 16, 9, 0),
              chi=[dong("fuel", "diesel", 120, 30000, "LAK", "fp_yard"), dong("fuel", "diesel", 690, 28000, "VND", "fp_vn")]
                  + di_duong_chuan()),
    ]

    # ---- THẺ CAO TỐC (C6.1): một thẻ do khách cấp (cuối tháng cấn trừ vào cước) và một thẻ của EPL.
    the = [
        TollCard(card_no="ETC-8801", name="Thẻ khách ຄຳຕຸ້ຍ", kind="khach", customer_id=kh["ຄຳຕຸ້ຍ"].id,
                 customer_name="ຄຳຕຸ້ຍ", driver_id=tx["ທ້າວ ທັດສະດາພອນ"].id, driver_name="ທ້າວ ທັດສະດາພອນ",
                 currency="LAK", balance=0, note="Khách cấp thẻ và nạp tiền; cuối tháng trừ vào cước"),
        TollCard(card_no="ETC-9902", name="Thẻ EPL xe 342", kind="epl", vehicle_id=xe["342"].id, truck_no="342",
                 currency="LAK", balance=0, note="Quỹ Thà Bốc nạp"),
    ]
    for t in the:
        db.add(t)
    db.flush()
    for t, so_nap, ngay_nap in ((the[0], 5000000, D(2026, 9, 1)), (the[1], 3000000, D(2026, 9, 5))):
        t.balance = so_nap
        db.add(TollCardMove(card_id=t.id, move_date=ngay_nap, kind="nap", amount=so_nap, balance_after=so_nap,
                            ref="NAP-%s" % t.card_no, note="Nạp tiền vào thẻ", by_user="ນາງ ດາວ (Dao)"))
    db.flush()

    # ---- LỆNH SỬA CHỮA RIÊNG (C7.3): xe nằm bãi bảo dưỡng định kỳ, không gắn phiếu nào.
    # Một tờ đã đi hết chuỗi duyệt (để thấy tờ chi), một tờ tổ sửa chữa vừa nhập (để có việc chờ).
    xe_bd = xe["342"]
    lsc = RepairOrder(doc_no="LSC-2609-01", vehicle_id=xe_bd.id, truck_no=xe_bd.truck_no, plate_head=xe_bd.plate_head,
                      order_date=D(2026, 9, 12), kind="bao_duong", odo_km=6090, status="entered",
                      note="Bảo dưỡng 10.000 km: thay dầu máy, lọc gió, kiểm phanh", by_user="ທ້າວ ສຸກ (Souk)")
    db.add(lsc); db.flush()
    db.add(RepairLine(order_id=lsc.id, line_no=1, item_key="x_oil", qty=1, unit_price=850000, currency="LAK",
                      source="mua", acct_code="614/4021", note="Dầu máy + công thay tại gara Thà Bốc"))
    db.add(RepairLine(order_id=lsc.id, line_no=2, item_name="ໄສ້ຕອງລົມ (lọc gió)", qty=1, unit_price=180000,
                      currency="LAK", source="mua", acct_code="614/4021"))
    db.flush()

    # ---- phiếu lĩnh (tờ giấy tài xế cầm đi, có mã QR)
    # Phiếu vừa xuất bến còn ĐANG CHỜ CẤP để màn Cấp phát có việc; các phiếu cũ thì tiền đã trao
    # tay rồi, đánh dấu "đã cấp" để bảng Tất toán có cả cột đã ứng lẫn cột đã chi.
    import secrets as _sc
    db.flush()          # phiên này autoflush=False: dòng chi của phiếu cuối chưa xuống DB thì query không thấy
    for pp in db.query(Trip).order_by(Trip.doc_no).all():
        dong_p = db.query(TripExpense).filter(TripExpense.trip_id == pp.id).all()
        tg = {"USD": pp.rate_usd or 22000, "THB": pp.rate_thb or 700, "VND": pp.rate_vnd or 1.2,
              "CNY": pp.rate_cny or 3000, "LAK": 1.0}
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
    gieo_ban_hang(db)
    gieo_chung_tu(db)


def gieo_ban_hang(db):
    """Một phiếu bán mẫu: bán 2 lọc dầu cho khách ngoài, đã thu. Để màn Bán hàng và Sổ chứng từ có gì mà xem."""
    loc = db.query(Part).filter(Part.name.like("%lọc dầu%")).first()
    kh = db.query(Customer).first()
    if not loc or not kh:
        return
    s = Sale(doc_no="BH-2608-0001", sale_date=D(2026, 8, 26), customer_id=kh.id, customer_name=kh.name, currency="LAK",
             rate_to_lak=1, status="paid", total=2 * 220000, total_lak=2 * 220000, cost_lak=2 * (loc.unit_price or 0),
             note="Bán lẻ tại bãi", by_user="ນາງ ຄຳ (Kham)", paid_at=dt.datetime(2026, 8, 26, 10, 0), paid_by="ນາງ ຄຳ (Kham)")
    db.add(s); db.flush()
    from models import PartMove
    mv = PartMove(part_id=loc.id, move_date=D(2026, 8, 26), kind="out", qty=2, note="Bán · BH-2608-0001 · %s" % kh.name, by_user="ນາງ ຄຳ (Kham)")
    db.add(mv); db.flush()
    loc.qty = (loc.qty or 0) - 2
    db.add(SaleLine(sale_id=s.id, line_no=1, item_type="part", part_id=loc.id, name=loc.name, unit=loc.unit, qty=2, unit_price=220000,
                    amount=440000, cost_lak=2 * (loc.unit_price or 0), stock_move_id=mv.id))
    db.flush()
    dong = [{"line_no": 1, "item_type": "part", "name": loc.name, "qty": 2, "unit_price": 220000, "amount": 440000}]
    CT.ghi(db, "PXK_BAN", nguon_bang="sales", nguon_id=s.id, ngay=s.sale_date, doi_tuong_loai="khach", doi_tuong_ten=kh.name,
           tien=s.cost_lak, by_user=s.by_user, mo_ta="Xuất kho bán hàng %s (giá vốn)" % s.doc_no, payload={"doc_no": s.doc_no, "lines": dong})
    CT.ghi(db, "HD_BAN", nguon_bang="sales", nguon_id=s.id, ngay=s.sale_date, doi_tuong_loai="khach", doi_tuong_ten=kh.name,
           tien=s.total, by_user=s.by_user, mo_ta="Hoá đơn bán hàng %s · %s" % (s.doc_no, kh.name), payload={"doc_no": s.doc_no, "lines": dong})
    CT.ghi(db, "PT_BAN", nguon_bang="sales", nguon_id=s.id, ngay=s.sale_date, doi_tuong_loai="khach", doi_tuong_ten=kh.name,
           tien=s.total, by_user=s.paid_by, mo_ta="Thu tiền bán hàng %s · %s" % (s.doc_no, kh.name), payload={"doc_no": s.doc_no})
    db.commit()


def gieo_chung_tu(db):
    """Sổ chứng từ cho dữ liệu mẫu — đúng những tờ mà luồng thật đã sinh nếu các phiếu này đi qua máy.
    Dữ liệu gieo thẳng vào bảng nên không qua route; gieo lại ở đây để màn Sổ chứng từ có gì mà xem."""
    from models import PartMove, SupplierPayment, Voucher  # noqa: F401
    for p in db.query(Trip).order_by(Trip.doc_date).all():
        CT.ghi(db, "DO", nguon_bang="trips", nguon_id=p.id, trip=p, ngay=p.doc_date, doi_tuong_loai="khach",
               doi_tuong_ten=p.customer_name, by_user=p.created_by,
               mo_ta="Phiếu xuất xe %s · %s → %s" % (p.doc_no, p.origin or "", p.destination or ""),
               payload={"truck_no": p.truck_no, "driver_name": p.driver_name, "company": p.company})
        if p.invoiced:
            dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id).all()
            k = tinh_phieu(p, dong)
            ngay_hd = p.back_date or p.doc_date
            CT.ghi(db, "HD", nguon_bang="trips", nguon_id=p.id, trip=p, ngay=ngay_hd, doi_tuong_loai="khach",
                   doi_tuong_ten=p.customer_name, tien=k["doanh_thu"], tien_te=k["ccy"], tien_lak=k["doanh_thu_lak"],
                   by_user="ນາງ ຄຳ (Kham)", mo_ta="Hoá đơn vận chuyển %s" % p.doc_no,
                   payload={"tan_tinh": k["tan_tinh"], "don_gia": p.price, "currency": k["ccy"],
                            "rate_to_lak": ty_gia(p, k["ccy"])})
            # Khách trả tiền: mỗi lần là MỘT DÒNG có ngày, số tiền, tiền tệ và tỷ giá ngày thu.
            # Hoá đơn ghi USD nhưng khách chuyển Kíp — đúng như bên Lào vẫn làm.
            if p.finance_status in ("paid", "partial"):
                du = k["doanh_thu_lak"] if p.finance_status == "paid" else round(k["doanh_thu_lak"] * 0.55)
                x = TripPayment(trip_id=p.id, pay_date=ngay_hd, amount=du, currency="LAK", rate_to_lak=1,
                                amount_lak=du, method="bank", ref="UNC-%s" % p.doc_no.split("-")[1],
                                note="Khách chuyển khoản bằng Kíp cho hoá đơn %s %s" % (k["doanh_thu"], k["ccy"]),
                                by_user="ນາງ ຄຳ (Kham)")
                db.add(x); db.flush()
                CT.ghi(db, "PT", nguon_bang="trip_payments", nguon_id=x.id, trip=p, ngay=ngay_hd, doi_tuong_loai="khach",
                       doi_tuong_ten=p.customer_name, tien=du, tien_te="LAK", tien_lak=du,
                       by_user="ນາງ ຄຳ (Kham)", mo_ta="Thu tiền khách phiếu %s · %s LAK" % (p.doc_no, du),
                       payload={"rate_to_lak": 1, "method": "bank", "hoa_don_ccy": k["ccy"],
                                "hoa_don": k["doanh_thu"], "hoa_don_lak": k["doanh_thu_lak"]})
    # ---- TỜ HOÁ ĐƠN GỘP THÁNG 9 cho khách hợp đồng: một tờ, hai dòng phiếu (C8.2).
    # Tiền của tờ = cộng doanh thu từng phiếu; khách chuyển trước 60 % bằng Kíp, phần tiền đó
    # được PHÂN BỔ xuống từng phiếu theo thứ tự ngày để trạng thái từng phiếu vẫn đúng.
    hd_phieu = (db.query(Trip).filter(Trip.doc_no.in_(("T4-0440-09/EPL", "T4-0441-09/EPL")))
                .order_by(Trip.doc_date, Trip.doc_no).all())
    kh_gop = db.query(Customer).filter(Customer.invoice_mode == "thang").first()
    tong_hd, tong_lak_hd, dong_hd = 0.0, 0.0, []
    for p in hd_phieu:
        k = tinh_phieu(p, db.query(TripExpense).filter(TripExpense.trip_id == p.id).all())
        tong_hd += k["doanh_thu"]; tong_lak_hd += k["doanh_thu_lak"]
        dong_hd.append({"doc_no": p.doc_no, "doc_date": p.doc_date.isoformat(), "tan_tinh": k["tan_tinh"],
                        "don_gia": p.price, "cach_tinh": k["cach_tinh"], "thanh_tien": k["doanh_thu"],
                        "thanh_tien_lak": k["doanh_thu_lak"], "rate_to_lak": ty_gia(p, k["ccy"])})
    hd_gop = Invoice(inv_no="HDT-202609-01", customer_id=kh_gop.id,
                     customer_name=kh_gop.name, period="2026-09", inv_date=D(2026, 9, 30),
                     currency="USD", amount=round(tong_hd, 2), amount_lak=round(tong_lak_hd), so_phieu=len(hd_phieu),
                     note="Hoá đơn gộp tháng 9 theo hợp đồng", by_user="ນາງ ຄຳ (Kham)")
    db.add(hd_gop); db.flush()
    for p in hd_phieu:
        p.invoice_id, p.invoiced = hd_gop.id, True
    CT.ghi(db, "HD", nguon_bang="invoices", nguon_id=hd_gop.id, ngay=hd_gop.inv_date, doi_tuong_loai="khach",
           doi_tuong_ten=hd_gop.customer_name, tien=hd_gop.amount, tien_te="USD", tien_lak=hd_gop.amount_lak,
           by_user="ນາງ ຄຳ (Kham)", mo_ta="Hoá đơn gộp tháng 2026-09 · %s · %d phiếu" % (hd_gop.customer_name, len(hd_phieu)),
           payload={"inv_no": hd_gop.inv_no, "period": "2026-09", "currency": "USD", "so_phieu": len(hd_phieu), "phieu": dong_hd})
    tra_lak = round(hd_gop.amount_lak * 0.6)
    ip = InvoicePayment(invoice_id=hd_gop.id, pay_date=D(2026, 10, 2), amount=tra_lak, currency="LAK",
                        rate_to_lak=1, amount_lak=tra_lak, method="bank", ref="UNC-2609",
                        note="Khách chuyển 60 % hoá đơn gộp tháng 9 bằng Kíp", by_user="ນາງ ຄຳ (Kham)")
    db.add(ip); db.flush()
    con_lai_hd, chia_hd = tra_lak, []
    for i, p in enumerate(hd_phieu):
        if con_lai_hd <= 0:
            break
        k = tinh_phieu(p, db.query(TripExpense).filter(TripExpense.trip_id == p.id).all())
        phan = con_lai_hd if i == len(hd_phieu) - 1 else min(con_lai_hd, round(k["doanh_thu_lak"]))
        db.add(TripPayment(trip_id=p.id, pay_date=ip.pay_date, amount=phan, currency="LAK", rate_to_lak=1,
                           amount_lak=phan, method="bank", ref=ip.ref, invoice_payment_id=ip.id,
                           note="Phân bổ từ hoá đơn gộp %s" % hd_gop.inv_no, by_user="ນາງ ຄຳ (Kham)"))
        p.finance_status = "paid" if phan >= round(k["doanh_thu_lak"]) else "partial"
        chia_hd.append({"doc_no": p.doc_no, "phan_bo_lak": phan})
        con_lai_hd -= phan
    CT.ghi(db, "PT", nguon_bang="invoice_payments", nguon_id=ip.id, ngay=ip.pay_date, doi_tuong_loai="khach",
           doi_tuong_ten=hd_gop.customer_name, tien=tra_lak, tien_te="LAK", tien_lak=tra_lak,
           by_user="ນາງ ຄຳ (Kham)", phuong_thuc="bank",
           mo_ta="Thu tiền khách hoá đơn gộp %s · %s LAK" % (hd_gop.inv_no, tra_lak),
           payload={"inv_no": hd_gop.inv_no, "period": "2026-09", "rate_to_lak": 1, "method": "bank",
                    "ref": ip.ref, "hoa_don_ccy": "USD", "hoa_don": hd_gop.amount,
                    "hoa_don_lak": hd_gop.amount_lak, "phan_bo": chia_hd})
    db.flush()

    phieu_theo_so = {p.doc_no: p for p in db.query(Trip).all()}
    for m in db.query(FuelMove).order_by(FuelMove.move_date).all():
        p = phieu_theo_so.get(m.doc_no)
        if m.kind == "in":
            CT.ghi(db, "PNK_NL", nguon_bang="fuel_moves", nguon_id=m.id, ngay=m.move_date, doi_tuong_loai="ncc",
                   tien=(m.qty_l or 0) * (m.unit_price or 0), tien_te=m.currency or "LAK", by_user=m.by_user,
                   mo_ta="Nhập %s lít dầu · %s" % (m.qty_l, m.doc_no or ""), payload={"qty_l": m.qty_l, "unit_price": m.unit_price})
        else:
            CT.ghi(db, "PXK_NL", nguon_bang="fuel_moves", nguon_id=m.id, trip=p, ngay=m.move_date, doi_tuong_loai="kho",
                   tien=(m.qty_l or 0) * (m.unit_price or 0), tien_te=m.currency or "LAK", section="fuel", by_user=m.by_user,
                   mo_ta="Xuất %s lít dầu · %s" % (m.qty_l, m.doc_no or ""), payload={"qty_l": m.qty_l, "unit_price": m.unit_price, "truck_no": m.truck_no})
    for v in db.query(Voucher).filter(Voucher.kind == "advance", Voucher.status == "da_cap").all():
        p = db.get(Trip, v.trip_id)
        CT.ghi(db, "PTU", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=v.doc_date, doi_tuong_loai="tai_xe",
               doi_tuong_ten=v.driver_name, tien=v.amount_lak, by_user=v.issued_by,
               mo_ta="Tạm ứng đi đường phiếu %s" % p.doc_no, payload={"voucher_id": v.id, "doc_no": v.doc_no})
        CT.ghi(db, "PC_TU", nguon_bang="vouchers", nguon_id=v.id, trip=p, ngay=v.doc_date, doi_tuong_loai="tai_xe",
               doi_tuong_ten=v.driver_name, tien=v.amount_lak, section="travel", by_user=v.granted_by,
               mo_ta="Chi tạm ứng đi đường theo %s" % v.doc_no, payload={"voucher_doc_no": v.doc_no, "truck_no": p.truck_no})
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
