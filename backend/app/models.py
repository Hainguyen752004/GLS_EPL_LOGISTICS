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
VAI = ("yard", "acct", "fuel", "treasury", "cash", "rev", "admin", "driver")
#   driver    Tài xế — chỉ thấy phiếu của mình: bấm "Xuất phát" sau khi nhận tiền tạm ứng, "Báo hỏng" trên đường
#   yard      Bãi Thà Bốc — nhập liệu (ສະໜາມທ່າບົກ)
#   acct      Kế toán thu/chi Viêng Chăn — kiểm & ghi sổ chi phí
#   fuel      Kế toán kho nhiên liệu — kiểm & ghi sổ mục nhiên liệu
#   treasury  Quỹ Viêng Chăn — chi tiền nhiên liệu
#   cash      Quỹ tiền mặt lẻ Thà Bốc — chi tiền đi đường / sửa chữa / khác
#   rev       Kế toán doanh thu — xuất hoá đơn, thu tiền khách
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
    owner_name = Column(String)                   # chủ xe liên kết
    engine_no = Column(String)                    # số máy
    chassis_no = Column(String)                   # số khung
    insurance_exp = Column(Date)                  # hạn bảo hiểm
    inspection_exp = Column(Date)                 # hạn đăng kiểm
    road_permit_exp = Column(Date)                # hạn giấy phép lưu hành / phù hiệu
    odometer_km = Column(Float)                   # công-tơ-mét hiện tại — cập nhật từ phiếu xe về
    next_service_km = Column(Float)               # mốc bảo dưỡng kế tiếp
    status = Column(String, nullable=False, default="available")   # TRANG_THAI_XE
    depot = Column(String, default="ທ່າບົກ")       # bãi đậu
    note = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


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
    phone = Column(String)
    dob = Column(Date)
    id_card = Column(String)                      # số CMND / căn cước
    address = Column(String)
    role = Column(String, default="main")         # main (lái chính) · co (phụ xe)
    hire_date = Column(Date)
    # Bằng lái HIỆN HÀNH (bản mới nhất); lịch sử đầy đủ ở driver_licenses
    license_no = Column(String)
    license_type = Column(String)                 # hạng: B2 · C · D · E · FC …
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
    """Nhà cung cấp theo dõi công nợ: phí chip Lào/Việt, lốp, cầu đường…"""
    __tablename__ = "suppliers"
    id = Column(String, primary_key=True, default=ma_moi)
    name = Column(String, nullable=False)
    item_key = Column(String)                     # khoản mục chi tương ứng (x_chip_lao…)
    acct_code = Column(String)                    # 625/402, 614/402…
    payment_term = Column(String, default="t_monthly")  # t_monthly | t_prepaid | t_per_trip
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
    """Tỷ giá quy về LAK — ghi trên đầu phiếu xuất xe: USD 22.000 · THB 700 · VND 1,2."""
    __tablename__ = "exchange_rates"
    code = Column(String, primary_key=True)
    rate_to_lak = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=bay_gio, onupdate=bay_gio)


# ---------------------------------------------------------------- phiếu xuất xe
TRANG_THAI_VAN_CHUYEN = ("dispatched", "transit", "arrived")    # ອອກລົດ · ກຳລັງຈັດສົ່ງ · ຮອດແລ້ວ
TRANG_THAI_TAI_CHINH = ("unpaid", "partial", "paid")            # ຄ້າງຊໍາລະ · ຊໍາລະບາງສ່ວນ · ຊໍາລະແລ້ວ
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


class Trip(Base):
    """Phiếu xuất xe đi vận chuyển — ໃບເບີກລົດອອກໄປຂົນສົ່ງ. Đơn vị làm việc duy nhất của họ."""
    __tablename__ = "trips"
    id = Column(String, primary_key=True, default=ma_moi)
    doc_no = Column(String, unique=True, nullable=False)      # T4-0428-08/EPL
    doc_date = Column(Date)                                    # ວັນທີອອກບິນ
    out_date = Column(Date)                                    # ວັນທີອອກລົດ
    back_date = Column(Date)                                   # ວັນທີລົດກັບ
    company = Column(String, nullable=False, default="EPL")    # EPL | joint (ລົດຮ່ວມ)
    owner_name = Column(String)                                # chủ xe liên kết
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
    price_usd = Column(Float, default=0)                       # ລາຄາ USD/tấn — bên A trả
    # Xe liên kết
    hire_price_usd = Column(Float)                             # giá thuê lại USD/tấn — trả chủ xe
    fee_pct = Column(Float, default=2)                         # ຫັກຄ່າທຳນຽມ 2%/ບິນ
    over_limit_t = Column(Float, default=40)                   # ngưỡng tấn
    over_price_usd = Column(Float, default=1)                  # ຫັກແກ່ເກີນ 1$/ໂຕນ
    # Trạng thái
    transport_status = Column(String, nullable=False, default="dispatched")
    finance_status = Column(String, nullable=False, default="unpaid")
    invoiced = Column(Boolean, nullable=False, default=False)
    # Tỷ giá KHOÁ trên phiếu lúc lập
    rate_usd = Column(Float, default=22000)
    rate_thb = Column(Float, default=700)
    rate_vnd = Column(Float, default=1.2)
    note = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, default=bay_gio)
    updated_at = Column(DateTime, default=bay_gio, onupdate=bay_gio)


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
    place = Column(String)                                     # fp_yard | fp_vn | fp_other (nhiên liệu)
    paid_by_epl = Column(Boolean, nullable=False, default=True)  # xe liên kết: EPL ứng hay chủ xe tự trả
    acct_code = Column(String)                                 # 625/371, 625/402, 614/402…
    # NGUỒN của khoản chi — quy tắc của họ: có trong kho thì XUẤT KHO, không có thì CHI MUA NGOÀI.
    #   kho  → phiếu xuất kho (nhiên liệu kho Thà Bốc, phụ tùng), định khoản …/371
    #   mua  → phiếu chi / công nợ nhà cung cấp, định khoản …/402
    source = Column(String)                                    # kho | mua | None (khoản đi đường)
    part_id = Column(String, ForeignKey("parts.id"))           # phụ tùng lấy từ kho (source=kho, mục V)
    stock_move_id = Column(String)                             # đã sinh phiếu xuất kho nào (chống xuất hai lần)
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
    km_from_prev = Column(Float, default=0)                    # km từ điểm trước
    note = Column(String)


SU_KIEN = ("arrive_stop", "incident", "repair", "note")        # tới điểm · sự cố · sửa xe · ghi chú
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
    reported_cost = Column(Float)                              # số tiền tài xế báo
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
