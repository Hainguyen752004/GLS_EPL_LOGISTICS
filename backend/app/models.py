# -*- coding: utf-8 -*-
"""Bảng dữ liệu của bản Lào — dựng THEO ĐÚNG tệp Excel `ຂົນສົ່ງ EPL.xlsx` của họ.

Nguyên tắc: Excel có ô nào thì đây có cột đó; Excel không có thì không thêm. Cụ thể:
  · Không có Báo giá, không có Lệnh giao hàng, không có Chuyến — họ chỉ có MỘT tờ
    "ໃບເບີກລົດອອກໄປຂົນສົ່ງ" (phiếu xuất xe) là đơn vị làm việc duy nhất.
  · Xe container mang HAI biển: đầu kéo (ທະບຽນຫົວ) và thùng (ທະບຽນຫາງ), cộng số hiệu nội
    bộ (ເບີລົດ). Đây là chỗ họ nói module xe của EPL_System thiếu.
  · Xe liên kết (ລົດຮ່ວມ): xe ngoài chạy hàng EPL, tính tiền thuê theo tấn, trừ 2%/phiếu
    và trừ 1 USD/tấn vượt ngưỡng. Mô hình môi giới: nhận 2, thuê lại 1, lời 1.
  · Tiền: cước tính USD, chi phí LAK/VND/THB, tỷ giá ghi ngay trên phiếu.
  · Mỗi khoản chi có mã tài khoản kép kiểu 625/371 — chép nguyên từ cột "ເດິນບັນຊີ".
"""
import datetime as dt
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from database import Base


def ma_moi():
    return uuid.uuid4().hex[:12]


def bay_gio():
    return dt.datetime.utcnow()


# ---------------------------------------------------------------- người dùng & vai
VAI = ("yard", "acct", "expacct", "fuel", "depot", "parts", "repair", "treasury", "cash", "rev", "admin", "driver")
#   driver    Tài xế — chỉ thấy phiếu của mình: bấm "Xuất phát" sau khi nhận tiền tạm ứng, "Báo hỏng" trên đường
#   yard      Admin Thà Bốc — nhập liệu (ແອັດມິນ ທ່າບົກ)
#   acct      KT Thu/Chi Viêng Chăn — xác nhận mục I (xe) và II (khách hàng, vận chuyển)
#   expacct   KT Chi phí VC — xác nhận và ghi sổ mục IV, V, VI (đi lại, sửa chữa, khác)
#   (Hai vai này là HAI NGƯỜI trong bảng Nhiệm Vụ của khách — không gộp.)
#   fuel      KT kho xăng dầu VC — xác nhận & ghi sổ mục III, duyệt dầu tài xế đổ dọc đường
#   depot     Thủ kho tại MỘT điểm đổ nhiên liệu — chỉ thấy phiếu lĩnh của kho mình, cấp dầu và lập phiếu xuất kho
#   treasury  Thủ quỹ VC — thanh toán mục III
#   cash      Quỹ tiền mặt cảng cạn — thanh toán mục IV, V, VI
#   rev       KT Doanh thu VC — lập và ghi sổ hoá đơn thu phí vận tải
#   admin     Quản trị


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=ma_moi)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="yard")
    avatar = Column(String, default="")          # hai chữ cái hiện ở góc trên
    driver_id = Column(String, ForeignKey("drivers.id"))   # tài khoản vai driver gắn với tài xế nào
    place_id = Column(String, ForeignKey("fuel_places.id"))  # tài khoản vai depot phụ trách điểm đổ nào
    active = Column(Boolean, nullable=False, default=True)


# ---------------------------------------------------------------- dữ liệu gốc
class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True, default=ma_moi)
    name = Column(String, nullable=False)
    phone = Column(String)
    address = Column(String)
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)
    # Cách xuất hoá đơn (anh Khampla C8.2, 22/09): `phieu` = mỗi phiếu một tờ (khách vãng lai) ·
    # `thang` = cuối tháng kế toán doanh thu GỘP mọi phiếu đã khoá của khách thành MỘT tờ.
    invoice_mode = Column(String, nullable=False, default="phieu")


CACH_XUAT_HOA_DON = ("phieu", "thang")           # mỗi phiếu một hoá đơn · gộp một tờ cuối tháng
CACH_TRA_CHU_XE = ("phieu", "thang", "dot")      # trả từng phiếu · gộp cuối tháng · theo đợt thoả thuận


class Owner(Base):
    """CHỦ XE LIÊN KẾT (ເຈົ້າຂອງລົດຮ່ວມ) — danh mục riêng (anh Khampla 22/09, C4.2 · C4.3).

    Phí 2 %/phiếu, ngưỡng tấn và mức trừ quá tải là ĐIỀU KHOẢN HỢP ĐỒNG với từng chủ xe, không phải
    hằng số chung; lập phiếu cho xe của chủ nào thì ba ô đó tự điền theo chủ đó, kế toán vẫn sửa được
    trên phiếu. `pay_mode` là cách hai bên đã thoả thuận trả tiền — chỉ để quỹ biết gom hay không gom.
    """
    __tablename__ = "owners"
    id = Column(String, primary_key=True, default=ma_moi)
    name = Column(String, nullable=False)
    phone = Column(String)
    address = Column(String)
    fee_pct = Column(Float, nullable=False, default=2)          # ຫັກຄ່າທຳນຽມ %/phiếu
    over_limit_t = Column(Float, nullable=False, default=40)    # ngưỡng tấn
    over_price = Column(Float, nullable=False, default=1)       # trừ mỗi tấn vượt, theo hire_ccy
    hire_ccy = Column(String, nullable=False, default="USD")    # tiền trả chủ xe
    pay_mode = Column(String, nullable=False, default="phieu")  # CACH_TRA_CHU_XE
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


TRANG_THAI_XE = ("available", "on_trip", "maintenance", "inactive")   # rảnh · đang chạy · đang sửa · ngưng dùng


class Vehicle(Base):
    """ĐẦU KÉO. Hồ sơ mang sang từ module Xe của EPL_System (số máy, số khung, bảo hiểm, đăng kiểm,
    công-tơ-mét, kỳ bảo dưỡng), bỏ những gì bên Lào không dùng (tốc độ, ETA, GPS, định mức nhiên liệu).

    Rơ-moóc là THỰC THỂ RIÊNG (bảng trailers): hư cái này thì tháo ra lắp cái khác. `trailer_id` là
    cái đang lắp; `plate_trailer` là biển của nó chép lại để phiếu cũ không đổi khi đổi rơ-moóc."""
    __tablename__ = "vehicles"
    id = Column(String, primary_key=True, default=ma_moi)
    truck_no = Column(String, nullable=False)     # ເບີລົດ — số hiệu nội bộ, ví dụ 341
    brand_model = Column(String)                  # ຍີຫໍ້ — HOWO-430
    year = Column(Integer)                        # năm sản xuất
    plate_head = Column(String)                   # ທະບຽນຫົວ — biển đầu kéo, ບອ 3262
    trailer_id = Column(String, ForeignKey("trailers.id"))   # rơ-moóc ĐANG lắp
    plate_trailer = Column(String)                # biển rơ-moóc đang lắp (chép lại)
    owner_type = Column(String, nullable=False, default="EPL")  # EPL | joint
    owner_id = Column(String, ForeignKey("owners.id"))          # chủ xe liên kết (danh mục)
    owner_name = Column(String)                   # tên chủ xe chép lại — phiếu cũ không đổi khi đổi tên
    engine_no = Column(String)                    # số máy
    chassis_no = Column(String)                   # số khung
    insurance_exp = Column(Date)                  # hạn bảo hiểm
    inspection_exp = Column(Date)                 # hạn đăng kiểm
    road_permit_exp = Column(Date)                # hạn giấy phép lưu hành / phù hiệu
    odometer_km = Column(Float)                   # công-tơ-mét hiện tại — cập nhật từ phiếu xe về
    next_service_km = Column(Float)
    service_date = Column(Date)                                # ngày bảo dưỡng gần nhất / kế tiếp
    fuel_norm = Column(Float)                                  # định mức dầu L/100km
    capacity_t = Column(Float)                                 # tải trọng (t)
    inspection_place = Column(String)                          # nơi đăng kiểm
    engine_cap = Column(String)                                # dung tích máy, ví dụ "9,7 L / 430 HP"
    box_size = Column(String)                                  # cỡ thùng, ví dụ "12,1 × 2,4 × 2,6 m"
    tyre = Column(String)                                      # cỡ lốp, ví dụ "11R22.5"               # mốc bảo dưỡng kế tiếp
    status = Column(String, nullable=False, default="available")   # TRANG_THAI_XE
    depot = Column(String, default="ທ່າບົກ")       # bãi đậu
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


# Các ô hồ sơ xe thêm theo bản thiết kế màn Xe (21/09): định mức dầu, nơi đăng kiểm, ngày bảo dưỡng,
# dung tích máy, cỡ thùng, cỡ lốp. Trước chỉ có trong Excel của họ chứ phần mềm không giữ chỗ để nhập.
class Trailer(Base):
    """RƠ-MOÓC (ຫາງ) — quản lý riêng, lắp/tháo được giữa các đầu kéo."""
    __tablename__ = "trailers"
    id = Column(String, primary_key=True, default=ma_moi)
    plate = Column(String, nullable=False)        # ທະບຽນຫາງ — ບອ 3282
    trailer_type = Column(String)                 # thùng ben · sàn · container 40'
    capacity_t = Column(Float)                    # tải trọng (tấn)
    year = Column(Integer)
    owner_type = Column(String, nullable=False, default="EPL")
    owner_name = Column(String)
    insurance_exp = Column(Date)
    inspection_exp = Column(Date)
    status = Column(String, nullable=False, default="available")   # available · attached · maintenance · inactive
    depot = Column(String)                                     # bãi đậu
    chassis_no = Column(String)
    inspection_place = Column(String)
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


class TrailerAssignment(Base):
    """Lịch sử lắp/tháo: rơ-moóc nào từng đi với đầu kéo nào, từ ngày đến ngày, vì sao đổi."""
    __tablename__ = "trailer_assignments"
    id = Column(String, primary_key=True, default=ma_moi)
    trailer_id = Column(String, ForeignKey("trailers.id"), nullable=False, index=True)
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=False, index=True)
    attached_at = Column(DateTime, default=bay_gio)
    detached_at = Column(DateTime)
    reason = Column(String)                       # lý do tháo: hư, đổi tuyến, bảo dưỡng…
    by_user = Column(String)


TRANG_THAI_TAI_XE = ("available", "on_trip", "leave", "inactive")     # rảnh · đang chạy · nghỉ · ngưng


class Driver(Base):
    """TÀI XẾ — hồ sơ và bằng lái mang sang từ EPL_System; bỏ ca, tổ, lịch trực (họ không xếp ca)."""
    __tablename__ = "drivers"
    id = Column(String, primary_key=True, default=ma_moi)
    driver_code = Column(String)                  # mã nội bộ
    name = Column(String, nullable=False)
    name_latin = Column(String)                   # tên viết Latin, để người không đọc chữ Lào gọi tên được
    phone = Column(String)
    dob = Column(Date)
    id_card = Column(String)                      # số CMND / căn cước
    address = Column(String)
    role = Column(String, default="main")         # main (lái chính) · co (phụ xe)
    hire_date = Column(Date)
    # Bằng lái HIỆN HÀNH (bản mới nhất); lịch sử đầy đủ ở driver_licenses
    license_no = Column(String)
    license_type = Column(String)                 # hạng: B2 · C · D · E · FC …
    # Hạng ghi trong HỒ SƠ NHÂN SỰ. Khác hạng trên bằng lái là dấu hiệu hồ sơ sai hoặc bằng chưa nâng —
    # màn Tài xế bắt chỗ lệch này và chặn điều xe cho tới khi người ta sửa.
    license_class_hr = Column(String)
    license_status = Column(String, default="active")   # active · suspended · revoked (bằng bị treo thì không được lái)
    license_valid_from = Column(Date)
    license_valid_to = Column(Date)
    default_vehicle_id = Column(String, ForeignKey("vehicles.id"))   # xe thường lái
    status = Column(String, nullable=False, default="available")     # TRANG_THAI_TAI_XE
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


class DriverLicense(Base):
    """Từng bằng lái / lần gia hạn của tài xế — để tra "hạn nào, cấp ở đâu, ai kiểm"."""
    __tablename__ = "driver_licenses"
    id = Column(String, primary_key=True, default=ma_moi)
    driver_id = Column(String, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    license_no = Column(String, nullable=False)
    license_type = Column(String)
    valid_from = Column(Date)
    valid_to = Column(Date)
    issued_by = Column(String)
    note = Column(String)
    verified_by = Column(String)
    verified_at = Column(DateTime, default=bay_gio)


class Supplier(Base):
    """Nhà cung cấp theo dõi công nợ: phí chip Lào/Việt, lốp, cầu đường, TRẠM DẦU bên Việt Nam…"""
    __tablename__ = "suppliers"
    id = Column(String, primary_key=True, default=ma_moi)
    name = Column(String, nullable=False)
    item_key = Column(String)                     # khoản mục chi tương ứng (x_chip_lao…)
    acct_code = Column(String)                    # 625/402, 614/402…
    payment_term = Column(String, default="t_monthly")  # t_monthly | t_prepaid | t_per_trip
    # Cấn trừ hai chiều (C5.1): có trạm dầu bên Việt Nam mà cuối tháng EPL không trả tiền mặt, mà
    # TRỪ VÀO CƯỚC của một khách — tiền EPL nợ trạm và tiền khách nợ EPL bù nhau. Ghi khách đó ở đây
    # thì báo cáo cuối tháng ra được số bù; hạch toán cấn trừ vẫn là việc của bên kế toán.
    customer_id = Column(String, ForeignKey("customers.id"))
    customer_name = Column(String)
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


class SupplierPayment(Base):
    __tablename__ = "supplier_payments"
    id = Column(String, primary_key=True, default=ma_moi)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False, index=True)
    pay_date = Column(Date, nullable=False)
    amount_lak = Column(Float, nullable=False, default=0)
    note = Column(Text)
    by_user = Column(String)


class ExchangeRate(Base):
    """Tỷ giá quy về LAK — ghi trên đầu phiếu xuất xe: USD 22.000 · THB 700 · VND 1,2 · CNY 3.000.

    Đây chỉ là tỷ giá MẶC ĐỊNH cho phiếu lập mới. Phiếu đã lập giữ tỷ giá riêng của nó
    (`trips.rate_usd`…), nên sửa ở đây KHÔNG làm đổi con số trên phiếu cũ.
    """
    __tablename__ = "exchange_rates"
    code = Column(String, primary_key=True)
    rate_to_lak = Column(Float, nullable=False)
    by_user = Column(String)                                   # ai đặt lần gần nhất
    updated_at = Column(DateTime, default=bay_gio, onupdate=bay_gio)


class ExchangeRateLog(Base):
    """Lịch sử tỷ giá đã áp dụng — mỗi lần đổi ghi một dòng, giữ luôn số cũ.

    Cần lịch sử vì tỷ giá là con số đi vào tiền: khi kế toán hỏi "tháng trước mình để 1 USD bao
    nhiêu Kíp", phải trả lời được bằng dữ liệu chứ không phải trí nhớ.
    """
    __tablename__ = "exchange_rate_logs"
    id = Column(String, primary_key=True, default=ma_moi)
    code = Column(String, nullable=False, index=True)
    rate_to_lak = Column(Float, nullable=False)                # số MỚI đặt
    rate_cu = Column(Float)                                    # số trước đó, None nếu lần đầu
    ap_dung_tu = Column(Date, nullable=False)                  # ngày bắt đầu áp dụng
    nguon = Column(String, nullable=False, default="tay")      # tay (người gõ) · api (sau này nối)
    by_user = Column(String)
    ghi_chu = Column(String)
    ts = Column(DateTime, nullable=False, default=bay_gio)


# ---------------------------------------------------------------- phiếu xuất xe
TRANG_THAI_VAN_CHUYEN = ("dispatched", "transit", "arrived")    # ອອກລົດ · ກຳລັງຈັດສົ່ງ · ຮອດແລ້ວ
TRANG_THAI_TAI_CHINH = ("unpaid", "partial", "paid")            # ຄ້າງຊໍາລະ · ຊໍາລະບາງສ່ວນ · ຊໍາລະແລ້ວ
# Các loại tiền EPL Lào thật sự nhận và chi. LAK là gốc: mọi tỷ giá là "bao nhiêu LAK cho 1 đơn vị".
TIEN_TE = ("LAK", "USD", "THB", "VND", "CNY")
CACH_TINH_CUOC = ("ton", "chuyen")   # theo tấn cân nơi giao · trọn chuyến
MUC = ("info", "trans", "fuel", "travel", "repair", "other")    # I..VI trên phiếu
MUC_CHI = ("fuel", "travel", "repair", "other")
# Chuỗi duyệt của từng mục: hai mục thông tin chỉ tới "đã kiểm", bốn mục chi đi tới "đã chi".
CHUOI = {
    "info":   ("wait", "entered", "verified"),
    "trans":  ("wait", "entered", "verified"),
    "fuel":   ("wait", "entered", "verified", "booked", "paid"),
    "travel": ("wait", "entered", "verified", "booked", "paid"),
    "repair": ("wait", "entered", "verified", "booked", "paid"),
    "other":  ("wait", "entered", "verified", "booked", "paid"),
}


LOAI_DO = ("gom", "giao")
#   gom   DO đi GOM HÀNG:  mỏ → bãi Thà Bốc. Không có cước, không hoá đơn. Xe về bãi thì hàng NHẬP KHO.
#   giao  DO đi GIAO HÀNG: bãi → cảng/khách. Lấy hàng từ kho (XUẤT KHO) rồi giao, có cước và hoá đơn.
# Hai DO "tuy hai mà một": bãi Thà Bốc đứng giữa như một bưu cục, dây nối chính là lô hàng trong kho —
# mỗi dòng hàng của DO giao ghi rõ nó lấy từ DO gom nào. Xe chặng gom và chặng giao có thể khác nhau.


class Trip(Base):
    """Phiếu xuất xe đi vận chuyển — ໃບເບີກລົດອອກໄປຂົນສົ່ງ. Đơn vị làm việc duy nhất của họ."""
    __tablename__ = "trips"
    id = Column(String, primary_key=True, default=ma_moi)
    doc_no = Column(String, unique=True, nullable=False)      # T4-0428-08/EPL
    kind = Column(String, nullable=False, default="giao")     # LOAI_DO: gom (đi lấy hàng) · giao (đi giao hàng)
    doc_date = Column(Date)                                    # ວັນທີອອກບິນ
    out_date = Column(Date)                                    # ວັນທີອອກລົດ
    back_date = Column(Date)                                   # ວັນທີລົດກັບ
    company = Column(String, nullable=False, default="EPL")    # EPL | joint (ລົດຮ່ວມ)
    owner_id = Column(String, ForeignKey("owners.id"))         # chủ xe liên kết (danh mục) — chép từ xe lúc lập
    owner_name = Column(String)                                # tên chủ xe chép lại
    owner_payment_id = Column(String, ForeignKey("owner_payments.id"))   # nằm trong đợt trả nào = đã trả chủ xe
    # Xe & tài xế: chép giá trị vào phiếu lúc lập, KHÔNG chỉ giữ khoá ngoại — đổi biển số
    # trong danh mục sau này không được làm phiếu cũ đổi theo.
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    truck_no = Column(String)
    brand_model = Column(String)
    plate_head = Column(String)
    plate_trailer = Column(String)
    driver_id = Column(String, ForeignKey("drivers.id"))
    driver_name = Column(String)
    odo_out = Column(Float)                                    # ເລກກົງເຕີ đi
    odo_back = Column(Float)                                   # ເລກກົງເຕີ về
    # Vận chuyển
    customer_id = Column(String, ForeignKey("customers.id"))
    customer_name = Column(String)
    route_id = Column(String, ForeignKey("routes.id"))         # tuyến chuẩn: chặng, km, BOT
    goods_type = Column(String, default="iron_ore")            # ແຮ່ເຫຼັກ
    ore_bill_no = Column(String)                               # ເລກທີບິນແຮ່
    ore_bill_date = Column(Date)
    origin = Column(String)
    destination = Column(String)
    weight_origin = Column(Float)                              # ນ້ຳໜັກຕົ້ນທາງ (tấn)
    weight_dest = Column(Float)                                # ນ້ຳໜັກປາຍທາງ (tấn) — cân nơi giao
    # ---- TIỀN BÁN. Đơn giá ghi theo TIỀN TỆ CỦA PHIẾU (`price_ccy`), không mặc định USD:
    # bên Lào nhận cước bằng USD, LAK, Nhân dân tệ, Bath Thái tuỳ hợp đồng từng khách.
    price = Column(Float, default=0)                           # ລາຄາ/tấn (hoặc trọn chuyến) theo price_ccy — bên A trả
    price_ccy = Column(String, nullable=False, default="USD")  # tiền tệ của cước: USD · LAK · CNY · THB · VND
    # Cách tính cước (anh Khampla C3.6, 22/09): `ton` = đơn giá × tấn cân nơi giao (hợp đồng) ·
    # `chuyen` = giá trọn chuyến, không nhân tấn (xe ngoài không hợp đồng). Giá thuê xe ngoài đi theo cùng cách.
    price_mode = Column(String, nullable=False, default="ton")
    # Xe liên kết. Giá thuê có thể khác tiền với giá bán (bán USD, thuê xe Lào trả LAK là chuyện thường),
    # nên nó mang tiền tệ riêng; trống thì hiểu là cùng tiền với cước.
    hire_price = Column(Float)                                 # giá thuê lại /tấn theo hire_ccy — trả chủ xe
    hire_ccy = Column(String)                                  # trống = theo price_ccy
    fee_pct = Column(Float, default=2)                         # ຫັກຄ່າທຳນຽມ 2%/ບິນ
    over_limit_t = Column(Float, default=40)                   # ngưỡng tấn
    over_price = Column(Float, default=1)                      # ຫັກແກ່ເກີນ 1$/ໂຕນ — theo hire_ccy
    # Trạng thái
    transport_status = Column(String, nullable=False, default="dispatched")
    finance_status = Column(String, nullable=False, default="unpaid")
    invoiced = Column(Boolean, nullable=False, default=False)
    invoice_id = Column(String, ForeignKey("invoices.id"))    # nằm trong tờ hoá đơn gộp tháng nào (trống = hoá đơn riêng)
    # Bước 14: xe về, kế toán rà cả phiếu rồi KHOÁ. Khoá rồi Bãi không sửa gì nữa; chỉ phiếu đã khoá mới xuất hoá đơn.
    locked = Column(Boolean, nullable=False, default=False)
    locked_by = Column(String)
    locked_at = Column(DateTime)
    # Xe liên kết: đã chi trả chủ xe chưa (một lần cho cả phiếu) → chứng từ PC_CX
    owner_paid = Column(Boolean, nullable=False, default=False)
    owner_paid_usd = Column(Float)
    owner_paid_lak = Column(Float)
    owner_paid_by = Column(String)
    owner_paid_at = Column(DateTime)
    # Tỷ giá KHOÁ trên phiếu lúc lập — bao nhiêu LAK cho một đơn vị tiền đó
    rate_usd = Column(Float, default=22000)
    rate_thb = Column(Float, default=700)
    rate_vnd = Column(Float, default=1.2)
    rate_cny = Column(Float, default=3000)
    note = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, default=bay_gio)
    updated_at = Column(DateTime, default=bay_gio, onupdate=bay_gio)


class TripGoods(Base):
    """Dòng HÀNG trên một DO — mặt hàng gì, bao nhiêu tấn.

    · Trên DO gom: hàng bốc ở mỏ (cân tại mỏ).
    · Trên DO giao: hàng lấy ra khỏi kho bãi, `tu_phieu_id` trỏ về DO gom đã mang lô hàng đó về —
      đây chính là dây nối hai DO.
    · Dòng `loai = "hao_hut"`: chênh lệch cân, ghi thành MỘT DÒNG cho rõ ràng thay vì để người đọc tự trừ.
    """
    __tablename__ = "trip_goods"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    loai = Column(String, nullable=False, default="hang")      # hang · hao_hut
    goods_name = Column(String, nullable=False)                # ແຮ່ເຫຼັກ · quặng sắt…
    qty_t = Column(Float, nullable=False, default=0)           # tấn
    tu_phieu_id = Column(String, ForeignKey("trips.id", ondelete="SET NULL"))   # DO giao: lấy từ DO gom nào
    note = Column(Text)


class GoodsMove(Base):
    """SỔ KHO HÀNG tại bãi — quặng nằm bãi giữa hai chặng. Tồn = nhập trừ xuất, tính cộng dồn,
    không có bảng tồn riêng để khỏi lệch. Mỗi dòng đều dẫn ngược về DO sinh ra nó."""
    __tablename__ = "goods_moves"
    id = Column(String, primary_key=True, default=ma_moi)
    move_date = Column(Date, nullable=False)
    kind = Column(String, nullable=False)                       # in (DO gom về bãi) · out (DO giao lấy đi) · adj (điều chỉnh, qty_t có dấu)
    goods_name = Column(String, nullable=False)
    qty_t = Column(Float, nullable=False)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    trip_doc_no = Column(String)
    lo_trip_id = Column(String, ForeignKey("trips.id", ondelete="SET NULL"), index=True)   # lô = DO gom
    depot = Column(String, default="Thà Bốc")
    note = Column(Text)
    by_user = Column(String)
    created_at = Column(DateTime, default=bay_gio)


class TripExpense(Base):
    """Một dòng chi trên phiếu: nhiên liệu (III), đi đường (IV), sửa chữa (V), khác (VI)."""
    __tablename__ = "trip_expenses"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    section = Column(String, nullable=False)                   # fuel | travel | repair | other
    line_no = Column(Integer, nullable=False, default=1)
    item_key = Column(String)                                  # x_toll, diesel… — khoá để dịch
    item_name = Column(String)                                 # tên tự gõ khi không có khoá
    qty = Column(Float, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0)
    currency = Column(String, nullable=False, default="LAK")   # nhiên liệu đổ ở VN tính VND
    place = Column(String)                                     # fp_yard | fp_vn | fp_other — khoá cũ, giữ để đọc dữ liệu cũ
    place_id = Column(String, ForeignKey("fuel_places.id"))    # ĐIỂM ĐỔ thật: quyết định kho nào cấp, và kho hay mua
    supplier_id = Column(String, ForeignKey("suppliers.id"))   # mua ngoài thì mua của ai (dầu đổ dọc đường, bên VN)
    paid_by_epl = Column(Boolean, nullable=False, default=True)  # xe liên kết: EPL ứng hay chủ xe tự trả
    acct_code = Column(String)                                 # 625/371, 625/402, 614/402…
    # NGUỒN của khoản chi — quy tắc của họ: có trong kho thì XUẤT KHO, không có thì CHI MUA NGOÀI.
    #   kho  → phiếu xuất kho (nhiên liệu kho Thà Bốc, phụ tùng), định khoản …/371
    #   mua  → phiếu chi / công nợ nhà cung cấp, định khoản …/402
    source = Column(String)                                    # kho | mua | None (khoản đi đường)
    part_id = Column(String, ForeignKey("parts.id"))           # phụ tùng lấy từ kho (source=kho, mục V)
    stock_move_id = Column(String)                             # đã sinh phiếu xuất kho nào (chống xuất hai lần)
    # Phí cầu đường trả bằng THẺ (C6.1): trừ vào thẻ nào, và đã trừ chưa (chống trừ hai lần).
    toll_card_id = Column(String, ForeignKey("toll_cards.id"))
    card_move_id = Column(String)
    # GHI NỢ TẠI TRẠM (C5.1, anh Khampla 22/09): tài xế đổ dầu ở Việt Nam mà KHÔNG trả tiền ngay —
    # trạm ghi sổ, cuối tháng EPL trả (hoặc cấn trừ với cước khách). Khác hẳn "tài xế trả tiền mặt
    # từ tiền tạm ứng": tiền chưa ra khỏi túi ai cả, nó là công nợ với trạm.
    ghi_no = Column(Boolean, nullable=False, default=False)
    note = Column(String)


class TripSection(Base):
    """Trạng thái duyệt của từng mục I–VI trên một phiếu."""
    __tablename__ = "trip_sections"
    __table_args__ = (UniqueConstraint("trip_id", "section", name="uq_trip_section"),)
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    section = Column(String, nullable=False)
    status = Column(String, nullable=False, default="wait")


class TripLog(Base):
    __tablename__ = "trip_logs"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime, default=bay_gio)
    user_name = Column(String)
    role = Column(String)
    action = Column(String)                                    # khoá i18n hoặc chữ thường


# ---------------------------------------------------------------- tuyến đường & theo dõi
class Route(Base):
    """Tuyến chuẩn: A → B → C. Mang sang từ EPL_System nhưng cắt hết hình đường bộ, GPS, ETA —
    chỉ giữ thứ họ dùng: tên điểm, km từng chặng, phí cầu đường (BOT thuộc ĐƯỜNG, không thuộc xe)."""
    __tablename__ = "routes"
    id = Column(String, primary_key=True, default=ma_moi)
    name = Column(String, nullable=False)                      # ກາສີ → ກາລໍ
    origin = Column(String)
    destination = Column(String)
    total_km = Column(Float, default=0)
    toll_lak = Column(Float, default=0)                        # BOT cả tuyến, tự thành dòng x_toll khi lập phiếu
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


class RouteStop(Base):
    """Một điểm trên tuyến. seq=1 là điểm đi, điểm cuối là điểm đến."""
    __tablename__ = "route_stops"
    __table_args__ = (UniqueConstraint("route_id", "seq", name="uq_route_stop"),)
    id = Column(String, primary_key=True, default=ma_moi)
    route_id = Column(String, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    km_from_prev = Column(Float, default=0)
    # Toạ độ để vẽ bản đồ. Không bắt buộc: tuyến chưa khai toạ độ thì màn Theo dõi chỉ vẽ
    # dải tiến độ, không vẽ bản đồ — thiếu toạ độ mà vẫn chấm đại lên bản đồ là nói dối.
    lat = Column(Float)
    lng = Column(Float)                    # km từ điểm trước
    note = Column(String)


SU_KIEN = ("arrive_stop", "incident", "repair", "refuel", "note", "change_truck")
# tới điểm · sự cố · sửa xe · đổ dầu · ghi chú · ĐỔI XE giữa đường (C2.2)
#   refuel  Tài xế đổ dầu DỌC ĐƯỜNG (thường là mua ở Việt Nam để chạy về). Khai xong ở trạng thái
#           "reported"; kế toán duyệt mới thành dòng chi mục III nguồn "mua".
LOAI_SU_CO = ("breakdown", "accident", "delay", "other")       # hỏng xe · tai nạn · chậm · khác


class TripEvent(Base):
    """Diễn biến của một phiếu trên đường — Bãi ghi khi tài xế gọi về. Không GPS: "xe đã tới điểm X"
    là do người bấm. Sửa xe khai ở đây sinh dòng chi vào mục V của phiếu."""
    __tablename__ = "trip_events"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime, default=bay_gio)
    kind = Column(String, nullable=False)                      # SU_KIEN
    stop_seq = Column(Integer)                                 # điểm trên tuyến (arrive_stop, hoặc nơi xảy ra sự cố)
    incident_type = Column(String)                             # LOAI_SU_CO
    note = Column(Text)
    expense_id = Column(String)                                # dòng chi mục V sinh ra từ sự kiện này
    by_user = Column(String)
    # Báo hỏng của TÀI XẾ: tài xế khai số tiền dự kiến → chờ admin/Bãi duyệt → duyệt mới sinh dòng
    # chi vào mục V. Bãi tự ghi thì status = approved ngay (Bãi là người duyệt).
    status = Column(String, default="approved")                # reported · approved · rejected
    reported_cost = Column(Float)
    qty_l = Column(Float)                                      # refuel: số lít đổ
    place_id = Column(String, ForeignKey("fuel_places.id"))    # refuel: đổ ở trạm nào
    supplier_id = Column(String, ForeignKey("suppliers.id"))   # refuel: mua của nhà cung cấp nào                              # số tiền tài xế báo
    currency = Column(String)                                  # tiền của số tiền báo
    approved_by = Column(String)
    approved_at = Column(DateTime)


# ---------------------------------------------------------------- kho
class FuelMove(Base):
    """Sổ kho nhiên liệu: nhập (in) / xuất cho xe (out). Tồn tính bằng cộng dồn."""
    __tablename__ = "fuel_moves"
    id = Column(String, primary_key=True, default=ma_moi)
    move_date = Column(Date, nullable=False)
    doc_no = Column(String)                                    # PN-0815 hoặc số phiếu xuất xe
    kind = Column(String, nullable=False)                      # in | out
    truck_no = Column(String)
    qty_l = Column(Float, nullable=False, default=0)
    unit_price = Column(Float, default=0)
    currency = Column(String, default="LAK")
    note = Column(String)
    by_user = Column(String)
    expense_id = Column(String)                                # dòng chi mục III sinh ra phiếu xuất này
    place_id = Column(String, ForeignKey("fuel_places.id"))    # xuất từ kho nào
    voucher_id = Column(String, ForeignKey("vouchers.id"))     # do phiếu lĩnh nào sinh ra


class Part(Base):
    __tablename__ = "parts"
    id = Column(String, primary_key=True, default=ma_moi)
    name = Column(String, nullable=False)
    unit = Column(String, default="u_pc")                      # u_pc | u_set | u_l
    qty = Column(Float, nullable=False, default=0)
    min_qty = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    last_date = Column(Date)
    last_truck = Column(String)
    active = Column(Boolean, nullable=False, default=True)


class PartMove(Base):
    __tablename__ = "part_moves"
    id = Column(String, primary_key=True, default=ma_moi)
    part_id = Column(String, ForeignKey("parts.id"), nullable=False, index=True)
    move_date = Column(Date, nullable=False)
    kind = Column(String, nullable=False)                      # in | out
    qty = Column(Float, nullable=False)
    truck_no = Column(String)
    trip_doc_no = Column(String)
    note = Column(String)
    by_user = Column(String)
    expense_id = Column(String)                                # dòng chi mục V sinh ra phiếu xuất này


# ---------------------------------------------------------------- thẻ cao tốc (C6.1)
LOAI_THE = ("khach", "epl")                 # khách cấp thẻ và nạp tiền · thẻ của EPL tự nạp
DONG_THE = ("nap", "chi", "dieu_chinh")     # nạp tiền · trừ khi qua trạm · điều chỉnh có lý do


class TollCard(Base):
    """THẺ CAO TỐC — ບັດທາງດ່ວນ (anh Khampla C6.1, 22/09).

    Họ muốn biết **thẻ còn bao nhiêu tiền**, và mỗi chuyến qua trạm thì trừ từ thẻ nào. Có hai kiểu,
    khác nhau ở chỗ ai bỏ tiền chứ không phải ở cách ghi:

      · `khach` — **khách cấp thẻ và nạp tiền**. Tiền thẻ là tiền của khách, nên cuối tháng phần EPL
        đã tiêu trên thẻ đó được **cấn trừ vào cước** phải thu của chính khách ấy.
      · `epl`   — khách không cấp thẻ; quỹ Thà Bốc nạp tiền (hoặc đưa tiền mặt cho tài xế). Đây là
        chi phí của EPL như mọi khoản đi đường khác.

    Số dư ở đây là số dư SỔ của bên mình, cộng dồn từ các dòng `toll_card_moves`; nó có thể lệch với
    số dư thật trên trạm nếu ai đó quẹt mà không khai — nên có dòng *điều chỉnh* kèm lý do.
    """
    __tablename__ = "toll_cards"
    id = Column(String, primary_key=True, default=ma_moi)
    card_no = Column(String, unique=True, nullable=False)      # số in trên thẻ
    name = Column(String)                                      # tên gọi trong nội bộ
    kind = Column(String, nullable=False, default="epl")       # LOAI_THE
    customer_id = Column(String, ForeignKey("customers.id"))   # thẻ của khách nào (kind = khach)
    customer_name = Column(String)
    driver_id = Column(String, ForeignKey("drivers.id"))       # ai đang cầm thẻ
    driver_name = Column(String)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))     # gắn theo xe (nếu để trên xe)
    truck_no = Column(String)
    currency = Column(String, nullable=False, default="LAK")   # thẻ Lào nạp Kíp, thẻ VN nạp VND
    balance = Column(Float, nullable=False, default=0)         # số dư sổ, cộng dồn từ các dòng
    active = Column(Boolean, nullable=False, default=True)
    note = Column(String)


class TollCardMove(Base):
    """Một lần nạp tiền vào thẻ, một lần trừ khi qua trạm, hay một lần điều chỉnh có lý do."""
    __tablename__ = "toll_card_moves"
    id = Column(String, primary_key=True, default=ma_moi)
    card_id = Column(String, ForeignKey("toll_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    move_date = Column(Date, nullable=False)
    kind = Column(String, nullable=False)                      # DONG_THE
    amount = Column(Float, nullable=False, default=0)          # theo currency của thẻ; chi là số dương
    balance_after = Column(Float, nullable=False, default=0)   # số dư sau dòng này — để tra lại khỏi cộng tay
    trip_id = Column(String, ForeignKey("trips.id", ondelete="SET NULL"))
    trip_doc_no = Column(String)
    expense_id = Column(String)                                # dòng chi mục IV đã trừ thẻ
    ref = Column(String)                                       # số biên lai nạp
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)


# ---------------------------------------------------------------- lệnh sửa chữa riêng (C7.3)
CHUOI_SUA_CHUA = ("entered", "verified", "booked", "paid")   # tổ sửa nhập → KT chi phí kiểm → ghi sổ → quỹ chi
LOAI_SUA_CHUA = ("bao_duong", "sua_chua")                    # bảo dưỡng định kỳ · sửa hỏng


class RepairOrder(Base):
    """LỆNH SỬA CHỮA của một chiếc xe, KHÔNG gắn phiếu xuất xe (anh Khampla C7.3, 22/09).

    Mục V trên phiếu chỉ ghi được cái sửa TRONG một chuyến. Còn xe nằm bãi cả tuần để đại tu, hay
    bảo dưỡng định kỳ theo số km, thì không có chuyến nào để gắn vào — trước đây họ không khai được
    ở đâu cả. Lệnh sửa chữa là tờ riêng cho đúng việc đó, đi qua cùng chuỗi duyệt như mục V:

        Tổ sửa chữa NHẬP → KT Chi phí KIỂM → KT Chi phí GHI SỔ → Quỹ tiền mặt CHI

    Phụ tùng lấy từ kho thì trừ tồn NGAY LÚC KHAI (như mục V) và sinh tờ `PXK_PT`; khoản mua ngoài
    thì tới bước chi mới sinh tờ `PC_SC`.
    """
    __tablename__ = "repair_orders"
    id = Column(String, primary_key=True, default=ma_moi)
    doc_no = Column(String, unique=True, nullable=False)       # LSC-2609-01
    vehicle_id = Column(String, ForeignKey("vehicles.id"), index=True)
    truck_no = Column(String)                                  # chép lại, phiếu cũ không đổi theo danh mục
    plate_head = Column(String)
    order_date = Column(Date, nullable=False)
    kind = Column(String, nullable=False, default="sua_chua")  # LOAI_SUA_CHUA
    odo_km = Column(Float)                                     # số công-tơ-mét lúc vào xưởng
    garage = Column(String)                                    # tên gara ngoài, để trống là làm tại Thà Bốc
    status = Column(String, nullable=False, default="entered")
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)
    verified_by = Column(String); verified_at = Column(DateTime)
    booked_by = Column(String);   booked_at = Column(DateTime)
    paid_by = Column(String);     paid_at = Column(DateTime)


class RepairLine(Base):
    """Một dòng chi của lệnh sửa chữa — cùng hình dạng với dòng mục V trên phiếu."""
    __tablename__ = "repair_lines"
    id = Column(String, primary_key=True, default=ma_moi)
    order_id = Column(String, ForeignKey("repair_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False, default=1)
    item_key = Column(String)
    item_name = Column(String)
    qty = Column(Float, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0)
    currency = Column(String, nullable=False, default="LAK")
    source = Column(String, nullable=False, default="mua")     # kho (xuất kho phụ tùng) · mua (gara, mua ngoài)
    part_id = Column(String, ForeignKey("parts.id"))
    stock_move_id = Column(String)                             # tờ xuất kho đã sinh (chống xuất hai lần)
    supplier_id = Column(String, ForeignKey("suppliers.id"))
    acct_code = Column(String)
    note = Column(String)


# ---------------------------------------------------------------- điểm đổ nhiên liệu
class FuelPlace(Base):
    """Nơi đổ dầu — ສະຖານທີ່ໃສ່ນໍ້າມັນ.

    Trước đây "nơi đổ" chỉ là ba chữ chết trong mã (bãi · Việt Nam · nơi khác). Nhưng phiếu lĩnh
    nhiên liệu phải chạy ĐẾN ĐÚNG người giữ kho đó, nên nơi đổ phải là một bản ghi có chủ.

      owner_type = 'epl'   kho của công ty  → lĩnh dầu, XUẤT KHO, định khoản …/371
      owner_type = 'ngoai' trạm bán dầu     → mua ngoài, phiếu chi / công nợ, định khoản …/402
    """
    __tablename__ = "fuel_places"
    id = Column(String, primary_key=True, default=ma_moi)
    code = Column(String)                                      # KHO-TB, VN-01…
    name = Column(String, nullable=False)                      # tên tiếng Lào/Việt hiện trên phiếu
    country = Column(String, nullable=False, default="LA")     # LA | VN
    owner_type = Column(String, nullable=False, default="epl")  # epl | ngoai
    supplier_id = Column(String, ForeignKey("suppliers.id"))   # trạm ngoài thì của nhà cung cấp nào
    address = Column(String)
    note = Column(String)
    active = Column(Boolean, nullable=False, default=True)


# ---------------------------------------------------------------- phiếu lĩnh (có mã QR)
LOAI_PHIEU_LINH = ("fuel", "advance")
#   fuel     Phiếu lĩnh nhiên liệu — tài xế cầm đến kho ghi ở ô Nơi đổ để lấy dầu
#   advance  Phiếu tạm ứng đi đường — tài xế cầm đến kế toán/quỹ để lấy tiền mặt
TRANG_THAI_PHIEU_LINH = ("cho", "da_cap", "huy")


class Voucher(Base):
    """Một tờ giấy tài xế cầm đi, in từ MỘT mục của phiếu xuất xe.

    Phiếu xuất xe là hồ sơ của cả chuyến; phiếu lĩnh là tờ đi lấy hàng/lấy tiền. Một chuyến có thể
    có nhiều phiếu lĩnh nhiên liệu (mỗi điểm đổ một tờ) nhưng chỉ một phiếu tạm ứng đi đường.

    `token` là chuỗi ngẫu nhiên nằm trong mã QR. Quét QR ra một đường dẫn tra cứu, KHÔNG nhồi số
    liệu vào QR: số liệu còn đổi sau lúc in, nhồi vào là tờ giấy nói một đằng hệ thống nói một nẻo.
    """
    __tablename__ = "vouchers"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String, nullable=False)                      # fuel | advance
    doc_no = Column(String, nullable=False)                    # PLNL-T4-0428-08/EPL · PTU-T4-0428-08/EPL
    doc_date = Column(Date, nullable=False)
    place_id = Column(String, ForeignKey("fuel_places.id"))    # phiếu nhiên liệu: lĩnh ở kho nào
    driver_id = Column(String, ForeignKey("drivers.id"))
    driver_name = Column(String)
    truck_no = Column(String)
    qty_l = Column(Float, default=0)                           # phiếu nhiên liệu: số lít được duyệt
    amount_lak = Column(Float, default=0)                      # phiếu tạm ứng: số tiền quy LAK
    status = Column(String, nullable=False, default="cho")     # cho | da_cap | huy
    token = Column(String, unique=True, nullable=False)        # nội dung mã QR
    issued_by = Column(String)                                 # ai in phiếu
    issued_at = Column(DateTime, default=bay_gio)
    granted_by = Column(String)                                # ai cấp dầu / chi tiền
    granted_at = Column(DateTime)
    granted_qty = Column(Float)                                # số lít cấp THẬT (có thể lệch số duyệt)
    granted_note = Column(String)                              # lệch thì bắt buộc ghi lý do
    note = Column(String)


# ---------------------------------------------------------------- tất toán tiền tài xế
class DriverSettlement(Base):
    """Tất toán tạm ứng của MỘT tài xế trong MỘT tháng — chủ dự án chốt chốt theo tháng.

    Ứng 10 triệu, chi thật 11 triệu thì công ty chi bù 1 triệu; chi thật 9 triệu thì tài xế nộp
    lại 1 triệu. Tất toán xong là khoá, không ai sửa ngược các phiếu trong kỳ nữa.
    """
    __tablename__ = "driver_settlements"
    id = Column(String, primary_key=True, default=ma_moi)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False, index=True)
    driver_name = Column(String)
    period = Column(String, nullable=False)                    # YYYY-MM
    so_phieu = Column(Integer, default=0)                      # bao nhiêu phiếu xuất xe trong kỳ
    tong_ung_lak = Column(Float, default=0)
    tong_chi_lak = Column(Float, default=0)
    chenh_lech_lak = Column(Float, default=0)                  # chi - ứng; dương = công ty trả thêm
    status = Column(String, nullable=False, default="done")    # done
    settled_by = Column(String)
    settled_at = Column(DateTime, default=bay_gio)
    note = Column(String)
    __table_args__ = (UniqueConstraint("driver_id", "period", name="uq_tat_toan_ky"),)


# ---------------------------------------------------------------- vị trí xe (GPS thật)
class VehiclePosition(Base):
    """Một điểm GPS do ĐIỆN THOẠI TÀI XẾ gửi về khi đang bật chia sẻ vị trí.

    Đây là vị trí THẬT, khác hẳn "mốc đã xác nhận tới" mà Bãi bấm tay. Màn Theo dõi ưu tiên vị trí
    thật; GPS cũ quá ngưỡng thì coi như không có và lùi về mốc, chứ không vẽ một chấm đứng im từ
    hôm qua như thể xe đang ở đó.

    Ghi theo CHUYẾN chứ không chỉ theo xe: cùng một xe chạy nhiều phiếu, và người điều hành hỏi
    "phiếu này đang ở đâu" chứ không hỏi "cái xe này đang ở đâu".
    """
    __tablename__ = "vehicle_positions"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    driver_id = Column(String, ForeignKey("drivers.id"))
    ts = Column(DateTime, nullable=False, default=bay_gio, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    accuracy_m = Column(Float)                                 # sai số máy báo, mét
    speed_kmh = Column(Float)
    heading = Column(Float)                                    # hướng, độ
    source = Column(String, nullable=False, default="driver_app")   # driver_app | manual
    by_user = Column(String)


# ---------------------------------------------------------------- sổ chứng từ (điểm nối kế toán)
class ChungTu(Base):
    """Một bản ghi chứng từ sinh ra ở một bước nghiệp vụ, để module kế toán (anh Khang) kéo về.

    Không phải sổ kế toán: bên mình không ghi bút toán, không cộng sổ. Hai vế `no`/`co` chỉ là
    GỢI Ý theo đúng bảng định khoản trong quy trình của họ; vế nào họ không ghi mã thì để trống
    mã, ghi tên. Xem services/chung_tu.py.
    """
    __tablename__ = "chung_tu"
    id = Column(String, primary_key=True, default=ma_moi)
    loai = Column(String, nullable=False, index=True)          # DO · PLNL · PTU · PXK_NL · PC_TU · HD · PT …
    so = Column(String, nullable=False, unique=True)           # PXK_NL/2609/0001
    ngay = Column(Date, nullable=False)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="SET NULL"), index=True)
    trip_doc_no = Column(String)
    doi_tuong_loai = Column(String)                            # khach · ncc · tai_xe · kho · chu_xe
    doi_tuong_ten = Column(String)
    tien = Column(Float)                                       # theo tiền tệ gốc
    tien_te = Column(String, default="LAK")
    tien_lak = Column(Float)                                   # quy về LAK theo tỷ giá trên phiếu
    no = Column(String); no_ten = Column(String)               # vế Nợ gợi ý
    co = Column(String); co_ten = Column(String)               # vế Có gợi ý
    mo_ta = Column(String)
    nguon_bang = Column(String, nullable=False)                # bảng gốc: vouchers · fuel_moves · trips …
    nguon_id = Column(String, nullable=False)
    by_user = Column(String)
    ts = Column(DateTime, nullable=False, default=bay_gio)
    da_day = Column(Boolean, nullable=False, default=False)    # bên kế toán đã nhận chưa
    day_luc = Column(DateTime)                                 # lần đẩy (hoặc thử đẩy) gần nhất
    ma_ben_ke_toan = Column(String)                            # mã phiếu bên kế toán trả về khi nhận
    loi_day = Column(String)                                   # lần đẩy gần nhất hỏng vì sao (None = không lỗi)
    lan_thu = Column(Integer, default=0)
    payload = Column(Text)                                     # JSON chi tiết dòng, để bên kia khỏi gọi lại
    __table_args__ = (UniqueConstraint("loai", "nguon_bang", "nguon_id", name="uq_chung_tu_nguon"),)


class CauHinh(Base):
    """Cấu hình đặt được trong màn hình (Sếp), không cần khởi động lại: địa chỉ và token API kế toán…
    Có giá trị ở đây thì dùng, không có thì rơi về biến môi trường cùng tên (EPL_<KHOA>)."""
    __tablename__ = "cau_hinh"
    khoa = Column(String, primary_key=True)                    # ke_toan_api · ke_toan_token
    gia_tri = Column(Text)
    by_user = Column(String)
    cap_nhat = Column(DateTime, default=bay_gio)


# ---------------------------------------------------------------- khách trả tiền hoá đơn vận chuyển
PHUONG_THUC_THU = ("cash", "bank", "offset", "other")     # tiền mặt · chuyển khoản · cấn trừ · khác


class TripPayment(Base):
    """MỘT LẦN khách trả tiền cho một phiếu xuất xe.

    Trước đây phần mềm chỉ có cái nút "đã thu" bật trạng thái phiếu sang `paid` — không biết khách
    trả bao nhiêu, bằng tiền gì, ngày nào. Thực tế bên Lào: hoá đơn ghi USD nhưng khách chuyển LAK
    hoặc Nhân dân tệ, và trả làm nhiều lần. Nên mỗi lần tiền về là một dòng ở đây.

    `amount` theo `currency` của LẦN THU đó; `rate_to_lak` là tỷ giá NGÀY THU (mặc định lấy tỷ giá
    khoá trên phiếu, người ghi sửa được); `amount_lak` là tích của hai số, đã tính sẵn để khỏi tính
    lại. Trạng thái tài chính của phiếu (chưa thu · một phần · đủ) do TỔNG các dòng này quyết định,
    không ai bấm tay nữa. Mỗi dòng sinh một chứng từ PT trong Sổ chứng từ.
    """
    __tablename__ = "trip_payments"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    # Dòng này do một lần thu THEO HOÁ ĐƠN GỘP phân bổ xuống (trống = khách trả thẳng cho phiếu).
    # Phân bổ để trạng thái từng phiếu vẫn tự suy ra được; tờ PT thì ghi ở lần thu gộp, không ghi ở đây.
    invoice_payment_id = Column(String, ForeignKey("invoice_payments.id", ondelete="CASCADE"), index=True)
    pay_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False, default=0)          # theo currency
    currency = Column(String, nullable=False, default="LAK")
    rate_to_lak = Column(Float, nullable=False, default=1)     # LAK cho 1 đơn vị currency, tỷ giá ngày thu
    amount_lak = Column(Float, nullable=False, default=0)      # = amount × rate_to_lak
    method = Column(String, nullable=False, default="bank")    # PHUONG_THUC_THU
    ref = Column(String)                                       # số uỷ nhiệm chi · biên lai bên khách
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)


# ---------------------------------------------------------------- hoá đơn gộp tháng (một tờ nhiều phiếu)
class Invoice(Base):
    """MỘT TỜ HOÁ ĐƠN gộp nhiều phiếu của cùng một khách trong một tháng (anh Khampla C8.2 · B3).

    Khách vãng lai vẫn mỗi phiếu một hoá đơn như cũ — không có dòng ở đây. Khách có cờ
    `invoice_mode = thang` thì cuối tháng kế toán doanh thu bấm "Gộp hoá đơn tháng": mọi phiếu đã
    khoá, đã kiểm mục II, cùng tiền cước của khách trong tháng đó gom về một tờ; từng phiếu trỏ về
    tờ qua trips.invoice_id. Tổng tiền = cộng doanh thu từng phiếu, không gõ tay. Sổ thu tiền của
    khách gắn vào TỜ này (invoice_payments), mỗi lần thu phân bổ xuống phiếu theo thứ tự ngày.
    """
    __tablename__ = "invoices"
    id = Column(String, primary_key=True, default=ma_moi)
    inv_no = Column(String, unique=True, nullable=False)       # HDT-202609-01
    customer_id = Column(String, ForeignKey("customers.id"), index=True)
    customer_name = Column(String)
    period = Column(String, nullable=False, index=True)        # YYYY-MM — tháng gộp
    inv_date = Column(Date, nullable=False)
    currency = Column(String, nullable=False, default="USD")   # tiền cước chung của các phiếu trong tờ
    amount = Column(Float, nullable=False, default=0)          # Σ doanh thu theo currency
    amount_lak = Column(Float, nullable=False, default=0)      # Σ doanh thu quy Kíp theo tỷ giá từng phiếu
    so_phieu = Column(Integer, nullable=False, default=0)
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)


class InvoicePayment(Base):
    """MỘT LẦN khách trả tiền cho một tờ hoá đơn gộp. Sinh một tờ PT; phần phân bổ xuống từng
    phiếu nằm ở trip_payments.invoice_payment_id."""
    __tablename__ = "invoice_payments"
    id = Column(String, primary_key=True, default=ma_moi)
    invoice_id = Column(String, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    pay_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False, default=0)          # theo currency của LẦN THU
    currency = Column(String, nullable=False, default="LAK")
    rate_to_lak = Column(Float, nullable=False, default=1)
    amount_lak = Column(Float, nullable=False, default=0)
    method = Column(String, nullable=False, default="bank")    # PHUONG_THUC_THU
    ref = Column(String)
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)


# ---------------------------------------------------------------- trả tiền chủ xe liên kết theo đợt
class OwnerPayment(Base):
    """MỘT ĐỢT trả chủ xe: một hay nhiều phiếu đã khoá của cùng chủ xe, cùng tiền thuê.

    Trước chỉ có nút trả từng phiếu. Anh Khampla (C4.3): trả từng phiếu, gộp cuối tháng, hay theo đợt
    đều có. Số tiền = tổng "trả chủ xe" của các phiếu trong đợt, không gõ tay — để khớp với chứng từ
    từng phiếu và với bảng tính trong Excel của họ. Phiếu trỏ về đợt qua trips.owner_payment_id."""
    __tablename__ = "owner_payments"
    id = Column(String, primary_key=True, default=ma_moi)
    owner_id = Column(String, ForeignKey("owners.id"), index=True)
    pay_date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False, default=0)          # theo currency (= tiền thuê)
    currency = Column(String, nullable=False, default="USD")
    rate_to_lak = Column(Float, nullable=False, default=1)
    amount_lak = Column(Float, nullable=False, default=0)
    method = Column(String, nullable=False, default="cash")    # PHUONG_THUC_THU
    ref = Column(String)
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)


# ---------------------------------------------------------------- tệp đính kèm phiếu (phiếu quặng của khách…)
class TripAttachment(Base):
    """Ảnh hoặc PDF kèm phiếu xuất xe. Tệp nằm trên đĩa (thư mục EPL_LAO_TEP, mặc định backend/tep), bảng chỉ giữ tên."""
    __tablename__ = "trip_attachments"
    id = Column(String, primary_key=True, default=ma_moi)
    trip_id = Column(String, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String, nullable=False, default="ore_bill")   # ore_bill · other
    filename = Column(String, nullable=False)                   # tên gốc người dùng đưa lên
    stored = Column(String, nullable=False)                     # tên trên đĩa: <id>.<ext>
    content_type = Column(String)
    size = Column(Integer, default=0)
    note = Column(String)
    by_user = Column(String)
    ts = Column(DateTime, nullable=False, default=bay_gio)


class VehiclePhoto(Base):
    """ẢNH XE — ຮູບລົດ. Bản thiết kế màn Xe có khung ảnh; trước 22/09 khung đó để trống vì máy chủ
    chưa có chỗ chứa tệp cho xe (nợ kỹ thuật 3.2).

    Dùng lại **đúng chỗ chứa tệp của phiếu** (thư mục `EPL_LAO_TEP`), chỉ khác thư mục con: ảnh xe
    nằm ở `xe/<vehicle_id>/`. Không dựng kho tệp thứ hai — một chỗ chứa thì một chỗ sao lưu.
    """
    __tablename__ = "vehicle_photos"
    id = Column(String, primary_key=True, default=ma_moi)
    vehicle_id = Column(String, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)                   # tên gốc người dùng đưa lên
    stored = Column(String, nullable=False)                     # tên trên đĩa: <id>.<ext>
    content_type = Column(String)
    size = Column(Integer, default=0)
    chinh = Column(Boolean, nullable=False, default=False)      # ảnh đại diện của xe
    note = Column(String)
    by_user = Column(String)
    ts = Column(DateTime, nullable=False, default=bay_gio)


class DriverPhoto(Base):
    """ẢNH TÀI XẾ — ຮູບໂຊເຟີ. Cùng bộ máy với ảnh xe (routes/anh.py), thư mục con `tai-xe/<driver_id>/`."""
    __tablename__ = "driver_photos"
    id = Column(String, primary_key=True, default=ma_moi)
    driver_id = Column(String, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    stored = Column(String, nullable=False)
    content_type = Column(String)
    size = Column(Integer, default=0)
    chinh = Column(Boolean, nullable=False, default=False)
    note = Column(String)
    by_user = Column(String)
    ts = Column(DateTime, nullable=False, default=bay_gio)


# ---------------------------------------------------------------- bán phụ tùng · xăng dầu cho bên ngoài
class CustomerRate(Base):
    """Bảng giá hợp đồng: khách × tuyến × loại hàng → đơn giá USD/tấn (và giá thuê xe ngoài nếu tuyến đó
    hay đi xe liên kết). Bước 7 quy trình chữ của họ: "theo đơn giá quy định trong hợp đồng" — nên giá
    nằm ở danh mục, mở phiếu là tự điền; kế toán chỉ sửa trên phiếu khi chuyến đó khác hợp đồng.
    Nhiều dòng cùng khách × tuyến với valid_from khác nhau = lịch sử giá; lấy dòng mới nhất còn hiệu lực."""
    __tablename__ = "customer_rates"
    id = Column(String, primary_key=True, default=ma_moi)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    route_id = Column(String, ForeignKey("routes.id"), nullable=False)
    goods_type = Column(String, nullable=False, default="iron_ore")
    price = Column(Float, nullable=False)                      # đơn giá/tấn (hoặc trọn chuyến) bên A trả, theo price_ccy
    price_ccy = Column(String, nullable=False, default="USD")  # tiền của hợp đồng này: USD · LAK · CNY · THB · VND
    price_mode = Column(String, nullable=False, default="ton") # ton · chuyen — cách tính, phiếu tự điền theo
    hire_price = Column(Float)                                 # /tấn trả chủ xe ngoài (nếu có thoả thuận sẵn)
    hire_ccy = Column(String)                                  # trống = cùng tiền với cước
    valid_from = Column(Date)                                  # trống = áp dụng từ đầu
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String)
    created_at = Column(DateTime, default=bay_gio)


class Sale(Base):
    __tablename__ = "sales"
    id = Column(String, primary_key=True, default=ma_moi)
    doc_no = Column(String, unique=True, nullable=False)        # BH-2609-0001
    sale_date = Column(Date, nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"))
    customer_name = Column(String, nullable=False)
    currency = Column(String, nullable=False, default="LAK")
    rate_to_lak = Column(Float, default=1)
    status = Column(String, nullable=False, default="issued")   # issued · paid
    total = Column(Float, default=0)                            # theo tiền tệ của phiếu
    total_lak = Column(Float, default=0)
    cost_lak = Column(Float, default=0)                         # giá vốn hàng xuất, LAK
    note = Column(String)
    by_user = Column(String)
    created_at = Column(DateTime, nullable=False, default=bay_gio)
    paid_at = Column(DateTime)
    paid_by = Column(String)


class SaleLine(Base):
    __tablename__ = "sale_lines"
    id = Column(String, primary_key=True, default=ma_moi)
    sale_id = Column(String, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False, default=1)
    item_type = Column(String, nullable=False)                  # part · fuel
    part_id = Column(String, ForeignKey("parts.id"))
    place_id = Column(String, ForeignKey("fuel_places.id"))     # kho dầu xuất (dòng fuel)
    name = Column(String)
    unit = Column(String)
    qty = Column(Float, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0)
    amount = Column(Float, nullable=False, default=0)
    cost_lak = Column(Float, default=0)
    stock_move_id = Column(String)                              # part_moves.id hoặc fuel_moves.id
