from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Numeric, UniqueConstraint, Index
from sqlalchemy import Date, CheckConstraint, ForeignKeyConstraint, LargeBinary
from sqlalchemy.orm import relationship
from database import Base
import datetime

MONEY_TYPE = Numeric(24, 6)
QUANTITY_TYPE = Numeric(18, 4)
RATE_TYPE = Numeric(18, 8)
DISTANCE_TYPE = Numeric(18, 3)


class CurrencyDefinition(Base):
    __tablename__ = "currency_definitions"
    __table_args__ = (CheckConstraint("minor_units >= 0 AND minor_units <= 6", name="ck_currency_minor_units"),)
    code = Column(String(3), primary_key=True)
    minor_units = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class CurrencyRateHistory(Base):
    __tablename__ = "currency_rate_history"
    __table_args__ = (
        UniqueConstraint("currency_code", "functional_currency", "rate_date", "source", name="uq_currency_rate_history"),
        CheckConstraint("rate > 0", name="ck_currency_rate_positive"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    currency_code = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    functional_currency = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    rate_date = Column(Date, nullable=False)
    rate = Column(RATE_TYPE, nullable=False)
    source = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class TaxCode(Base):
    __tablename__ = "tax_codes"
    __table_args__ = (
        CheckConstraint("rate >= 0", name="ck_tax_code_rate_nonnegative"),
        CheckConstraint("mode IN ('exclusive', 'inclusive', 'exempt')", name="ck_tax_code_mode"),
        CheckConstraint("effective_to IS NULL OR effective_from <= effective_to", name="ck_tax_code_effective_range"),
        UniqueConstraint("code", "effective_from", name="uq_tax_code_effective_from"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, index=True)
    rate = Column(RATE_TYPE, nullable=False)
    mode = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class FinanceControlConfig(Base):
    __tablename__ = "finance_control_config"
    __table_args__ = (
        CheckConstraint("distance_variance_threshold >= 0", name="ck_finance_distance_variance_nonnegative"),
        CheckConstraint("id = 'GLOBAL'", name="ck_finance_config_singleton"),
    )
    id = Column(String(20), primary_key=True, default="GLOBAL")
    functional_currency = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False, default="VND")
    enforce_creator_approver_sod = Column(Boolean, nullable=False, default=True)
    require_distinct_poster = Column(Boolean, nullable=False, default=True)
    distance_variance_threshold = Column(RATE_TYPE, nullable=False, default=0)
    document_https_hosts = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

# 1. Vehicles
class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(String, primary_key=True) # Biển số xe (VD: 51C-123.45)
    brand = Column(String, default="Hyundai") # Hãng xe / Thương hiệu (VD: Hyundai, Isuzu, Hino, Volvo, Howo...)
    type = Column(String) # Loại xe (VD: Xe tải 10 tấn, Container 20FT)
    weight_capacity = Column(Float, default=0.0) # Tải trọng (kg)
    volume_capacity_m3 = Column(Float, default=30.0) # Thể tích thùng xe (m3)
    pallet_capacity = Column(Integer, default=0) # Số pallet tối đa
    fuel_norm = Column(Float, default=0.0) # Định mức nhiên liệu (lít/100km)
    min_speed_kmh = Column(Float, default=35.0) # Tốc độ tối thiểu dùng tính ETA/điều phối
    avg_speed_kmh = Column(Float, default=45.0) # Tốc độ kế hoạch riêng của xe
    max_speed_kmh = Column(Float, default=80.0) # Tốc độ tối đa dùng cảnh báo/GPS
    maintenance_date = Column(String) # Ngày bảo dưỡng
    status = Column(String, default="Sẵn sàng") # Trạng thái — NHÃN CHỮ, chỉ để hiện; xem operational_status
    # TRANG THAI VAN HANH LA MA CHUAN, KHONG PHAI NHAN CHU (moc 045).
    #
    # `status` o tren la mot chuoi tieng Viet do ma ghi cung; sua chu la moi xe
    # thanh khong dieu duoc, va ban tieng Lao khong khop chuoi nao. Bon cot nay
    # la su that: he thong cap nhat theo lich (dieu xe, xe ve, huy chuyen, lich
    # xuong) va nguoi dung dat tay duoc (dua xe ra khoi doi / dua lai). Chu hien
    # ra lay tu lang.json theo ma. `status` van duoc chieu tu ma cho cho cu.
    operational_status = Column(String(32), nullable=False, default="available", server_default="available")
    operational_ref = Column(String(128)) # Ma chuyen / phieu xuong dang giu xe
    operational_note = Column(Text) # Ly do khi nguoi dung dat tay
    operational_updated_at = Column(DateTime(timezone=True))
    engine_no = Column(String) # Số máy
    chassis_no = Column(String) # Số khung
    insurance_date = Column(String) # Bảo hiểm
    inspection_date = Column(String) # Ngày đăng kiểm
    inspection_place = Column(String) # Nơi đăng kiểm
    depot = Column(String) # Bãi / chi nhánh xe đậu (VD: Bãi Sóng Thần, Chi nhánh Hà Nội)
    depot_code = Column(String, index=True) # Mã bãi, dùng để lọc — ở đội 500 xe đây là bộ lọc chính
    inspection_exp = Column(String) # Hạn đăng kiểm (Hết hạn)
    # Đội xe thật lập lịch bảo dưỡng theo KM CHẠY, không theo ngày lịch: một
    # chiếc chạy 400 km/ngày thì một ngày lịch không nói được gì. Để rỗng
    # được, và màn hình phải nói "chưa khai số km" chứ không vẽ thanh 0% —
    # thanh đỏ đó đọc ra như xe đến hạn gấp.
    odometer_km = Column(Float) # Số km đồng hồ hiện tại
    next_service_odometer_km = Column(Float) # Mốc đồng hồ của kỳ bảo dưỡng kế tiếp
    engine_cap = Column(String) # Dung tích động cơ
    dimensions = Column(String) # Kích thước thùng (DxRxC)
    image_url = Column(Text) # Ảnh phương tiện dạng URL


class VehicleMaintenanceRequest(Base):
    __tablename__ = "vehicle_maintenance_requests"
    __table_args__ = (
        UniqueConstraint("request_no", name="uq_vehicle_maintenance_request_no"),
        CheckConstraint("planned_end > planned_start", name="ck_vehicle_maintenance_period"),
        CheckConstraint(
            "status IN ('requested','approved','in_progress','completed','cancelled')",
            name="ck_vehicle_maintenance_status",
        ),
        Index("ix_vehicle_maintenance_vehicle_period", "vehicle_id", "planned_start", "planned_end"),
    )
    id = Column(String(128), primary_key=True)
    request_no = Column(String(128), nullable=False)
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=False)
    category = Column(String(32), nullable=False, default="corrective")
    priority = Column(String(20), nullable=False, default="normal")
    planned_start = Column(DateTime(timezone=True), nullable=False)
    planned_end = Column(DateTime(timezone=True), nullable=False)
    actual_start = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    description = Column(Text, nullable=False)
    cause = Column(Text)
    odometer_km = Column(Float)
    workshop = Column(String(255))
    currency_code = Column(String(3), nullable=False, default="VND")
    estimated_total = Column(MONEY_TYPE, nullable=False, default=0)
    actual_total = Column(MONEY_TYPE, nullable=False, default=0)
    next_maintenance_date = Column(String(10))
    status = Column(String(20), nullable=False, default="requested")
    cancellation_reason = Column(Text)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False, default="system")
    updated_by = Column(String(128), nullable=False, default="system")
    approved_at = Column(DateTime)
    approved_by = Column(String(128))
    completed_at = Column(DateTime)
    completed_by = Column(String(128))
    cost_lines = relationship(
        "VehicleMaintenanceCostLine",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="VehicleMaintenanceCostLine.id",
    )


class VehicleMaintenanceCostLine(Base):
    __tablename__ = "vehicle_maintenance_cost_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_vehicle_maintenance_cost_quantity"),
        CheckConstraint("estimated_unit_cost >= 0", name="ck_vehicle_maintenance_estimated_cost"),
        CheckConstraint("actual_unit_cost >= 0", name="ck_vehicle_maintenance_actual_cost"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(128), ForeignKey("vehicle_maintenance_requests.id"), nullable=False)
    category = Column(String(32), nullable=False, default="other")
    description = Column(String(500), nullable=False)
    quantity = Column(QUANTITY_TYPE, nullable=False, default=1)
    unit = Column(String(32), nullable=False, default="item")
    estimated_unit_cost = Column(MONEY_TYPE, nullable=False, default=0)
    estimated_total = Column(MONEY_TYPE, nullable=False, default=0)
    actual_unit_cost = Column(MONEY_TYPE, nullable=False, default=0)
    actual_total = Column(MONEY_TYPE, nullable=False, default=0)
    request = relationship("VehicleMaintenanceRequest", back_populates="cost_lines")

# 1.5 Vehicle Types (Danh mục loại phương tiện)
class VehicleType(Base):
    __tablename__ = "vehicle_types"
    id = Column(String, primary_key=True) # VD: VT-001
    name = Column(String, nullable=False) # VD: Container 20FT
    icon = Column(String, default="🚛")
    max_weight = Column(Float, default=0.0) # Tải trọng tối đa (kg)
    volume_capacity_m3 = Column(Float, default=30.0) # Thể tích tối đa (m3)
    pallet_capacity = Column(Integer, default=0) # Số pallet tối đa
    fuel_norm = Column(Float, default=0.0) # Định mức nhiên liệu (lít/100km)
    avg_speed_kmh = Column(Float, default=45.0) # Tốc độ kế hoạch mặc định của loại xe
    base_rate = Column(MONEY_TYPE, default=0.0) # Đơn giá trên 1 km (đ/km) — mọi đơn giá chi phí trong dự án quy về "trên 1 km"
    maint_cost = Column(MONEY_TYPE, default=0.0) # Phí bảo dưỡng
    # Khấu hao và bảo dưỡng TRÊN 1 KM — cấu phần giá thành duy nhất trong spec
    # mà hệ thống chưa có. Thiếu nó thì biên lợi nhuận cao giả tạo.
    dep_cost_per_km = Column(MONEY_TYPE)
    dims = Column(String) # Kích thước
    fuel_type = Column(String, default="Diesel") # Loại nhiên liệu
    special = Column(String) # Điều kiện đặc biệt
    notes = Column(String) # Ghi chú

# 2. Drivers
class Driver(Base):
    __tablename__ = "drivers"
    id = Column(String, primary_key=True) # Mã tài xế
    name = Column(String, nullable=False)
    role = Column(String, default="Lái xe chính") # Lái xe chính / Phụ xe
    license_type = Column(String, default="Hạng FC")
    phone = Column(String)
    assigned_vehicle = Column(String, default="Chưa gán")
    shift = Column(String, default="Ca Sáng (06:00 - 14:00)")
    status = Column(String, default="🟢 Rảnh (Sẵn sàng)") # NHÃN CHỮ, chỉ để hiện; xem operational_status
    # Cung mot ly do voi Vehicle.operational_status (moc 045).
    operational_status = Column(String(32), nullable=False, default="available", server_default="available")
    operational_ref = Column(String(128))
    operational_note = Column(Text)
    operational_updated_at = Column(DateTime(timezone=True))
    photo_url = Column(Text) # Ảnh chân dung tài xế/phụ xe dạng URL
    # Ba cột dưới đây là đơn vị XẾP CA. Khớp với `vehicles.depot_code` để một
    # bãi xem được cả người và xe của mình trong cùng một màn — ở đội ~500 xe,
    # một danh sách phẳng hàng trăm tài xế không dùng để xếp ca được.
    depot_code = Column(String, index=True) # Mã bãi tài xế thuộc về
    team_code = Column(String, index=True) # Mã tổ (ca đội trực) — đơn vị xếp ca thật
    # Mẫu xoay ca, viết như `SSCCDD--` (S sáng, C chiều, D đêm, `-` nghỉ).
    # Chức năng sinh lịch theo mẫu đọc cột này; trước đây mẫu chỉ nằm trong đầu
    # người xếp lịch.
    rotation_pattern = Column(String)


class DriverShiftAssignment(Base):
    __tablename__ = "driver_shift_assignments"
    __table_args__ = (
        CheckConstraint("shift_end > shift_start", name="ck_driver_shift_period"),
        CheckConstraint(
            "shift_type IN ('morning','afternoon','night','office','custom')",
            name="ck_driver_shift_type",
        ),
        CheckConstraint(
            "status IN ('planned','confirmed','cancelled')",
            name="ck_driver_shift_status",
        ),
        CheckConstraint(
            "availability_kind IN ('work','leave','sick','off','unavailable')",
            name="ck_driver_shift_availability_kind",
        ),
        Index("ix_driver_shift_driver_period", "driver_id", "shift_start", "shift_end"),
        Index("ix_driver_shift_vehicle_period", "vehicle_id", "shift_start", "shift_end"),
    )
    id = Column(String(128), primary_key=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    trip_id = Column(String(128), ForeignKey("transport_trips.id"))
    shift_type = Column(String(20), nullable=False, default="custom")
    availability_kind = Column(String(20), nullable=False, default="work")
    shift_start = Column(DateTime(timezone=True), nullable=False)
    shift_end = Column(DateTime(timezone=True), nullable=False)
    work_location = Column(String(500))
    notes = Column(Text)
    status = Column(String(20), nullable=False, default="planned")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False, default="system")
    updated_by = Column(String(128), nullable=False, default="system")

# 3. Routes
class Route(Base):
    __tablename__ = "routes"
    id = Column(String, primary_key=True) # Route Code
    name = Column(String, nullable=False) # Route Name (Bình Dương - Cát Lái)
    distance_km = Column(Float, default=0.0) # Total Distance
    segments_json = Column(Text) # Chặng đường (A->B->C)
    # HÌNH ĐƯỜNG BỘ THẬT của tuyến, lưu lại để không phải lấy lại mỗi lần vẽ.
    # Một tuyến bốn điểm trả về hơn hai nghìn điểm hình; lấy lại mỗi lần mở màn
    # là một giây chờ và một lời gọi ra ngoài cho một thứ không bao giờ đổi.
    # Kèm dấu vân của danh sách điểm, để biết khi nào phải lấy lại.
    road_geometry_json = Column(Text)
    # Độ dài đường BỘ thật. KHÁC `distance_km` — con số người dùng khai, và là
    # thứ đang nuôi phép tính giá cước lẫn ETA. Giữ cả hai chứ không ghi đè:
    # thay số người khai bằng số máy lấy về là đổi tiền trên những đơn đã chốt.
    road_distance_km = Column(Float)
    # BOT thuộc ĐƯỜNG, không thuộc xe. Trước đây phí cầu đường chỉ có trong công
    # thức theo loại xe, nên tuyến 19,9 km và tuyến 129 km cùng một mức BOT.
    bot_fee = Column(MONEY_TYPE)

# 4. Locations (Branch, Port, Warehouse)
class Location(Base):
    __tablename__ = "locations"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, default="Warehouse") # Branch, Port, Warehouse
    address = Column(String)
    capacity = Column(Float, default=0.0)
    # Toạ độ là DỮ LIỆU GỐC của địa điểm, cùng loại với địa chỉ — không phải một
    # bảng cứng trong mã, và không phải một lời gọi ra Internet mỗi lần vẽ bản
    # đồ. Để rỗng được: màn hình phải nói "chưa biết toạ độ điểm này" chứ không
    # được đặt (0, 0), cặp đó đặt địa điểm ra ngoài khơi bờ biển châu Phi.
    latitude = Column(Float)
    longitude = Column(Float)

Warehouse = Location

# 5. Customers
class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, default="Account") # Lead, Account
    contact_person = Column(String)
    phone = Column(String)
    address = Column(String)
    vendor_type = Column(String, nullable=True) # Carrier, Supplier, etc.

class CoHoiKhach(Base):
    """CƠ HỘI KHÁCH HÀNG (CRM-01) — bước đứng TRƯỚC báo giá.

    Khách hỏi giá thì ghi ở đây: ai, tuyến nào, hàng gì, bao nhiêu tấn, mấy
    chuyến/tháng, ai theo, hẹn liên hệ lại lúc nào. Từ cơ hội bấm "Lập báo giá"
    sinh MỘT báo giá nháp (`quotation_id`), rồi báo giá đi tiếp luồng
    QT → DO → Trip. Khách chưa có trong `customers` thì giữ `prospect_name`,
    lúc lập báo giá mới tạo khách. Xem `migrations/v047_co_hoi_khach_hang.py`.
    """
    __tablename__ = "crm_opportunities"
    __table_args__ = (
        CheckConstraint("stage IN ('new','contacted','negotiating','quoted','won','lost')",
                        name="ck_crm_opportunity_stage"),
        CheckConstraint("version > 0", name="ck_crm_opportunity_version"),
        Index("ix_crm_opportunity_stage", "stage"),
        Index("ix_crm_opportunity_customer", "customer_id"),
        Index("ix_crm_opportunity_quotation", "quotation_id"),
    )
    id = Column(String(64), primary_key=True)                     # LEAD-2026-001
    customer_id = Column(String, ForeignKey("customers.id"))
    prospect_name = Column(String(255))                           # khách chưa có trong danh mục
    contact_name = Column(String(255))
    contact_phone = Column(String(64))
    contact_email = Column(String(255))
    source = Column(String(32), nullable=False, default="other")  # phone|email|web|referral|tender|existing|other
    route_id = Column(String, ForeignKey("routes.id"))
    origin_text = Column(String(255))
    destination_text = Column(String(255))
    cargo_type = Column(String(255))
    est_weight_kg = Column(Float, nullable=False, default=0.0)
    est_trips_per_month = Column(Integer, nullable=False, default=0)
    expected_start = Column(String(32))
    expected_price = Column(MONEY_TYPE)
    stage = Column(String(20), nullable=False, default="new")
    owner = Column(String(128))
    notes = Column(Text)
    lost_reason = Column(Text)
    quotation_id = Column(String, ForeignKey("quotations.id"))
    next_action_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False, default="system")
    updated_by = Column(String(128), nullable=False, default="system")
    version = Column(Integer, nullable=False, default=1)


# 6. (Đơn hàng SO đã bỏ khỏi luồng 10/09 — migration 049)
class VehicleCostOverride(Base):
    """Phần chênh lệch giá thành của MỘT chiếc xe so với loại xe của nó.

    Công thức thuộc về loại xe; bảng này chỉ chứa những con số mà chiếc xe cụ
    thể khác đi. Xe không ghi đè thì không có dòng nào ở đây và kế thừa nguyên
    vẹn — nhờ vậy đổi giá dầu vẫn sửa một chỗ cho cả đội 500 xe.
    """
    __tablename__ = "vehicle_cost_overrides"
    id = Column(String, primary_key=True)
    vehicle_id = Column(String, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    component = Column(String, nullable=False)  # fuel | driver | toll | wh | rate
    value = Column(MONEY_TYPE, nullable=False, default=0)
    note = Column(String)
    updated_at = Column(DateTime)
    updated_by = Column(String)
    __table_args__ = (UniqueConstraint("vehicle_id", "component", name="uq_vehicle_cost_overrides_vehicle_component"),)


# 7. DeliveryOrders
class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"
    __table_args__ = (
        CheckConstraint(
            # `arrived` = xe da toi diem giao, CHUA co POD ky nhan. Migration
            # v002 da cho phep no o Postgres tu lau, nhung rang buoc trong mo
            # hinh (dung cho SQLite cua bo kiem) thi chua — nen bo kiem chan
            # dung cai ma co so du lieu that cho phep.
            "canonical_status IN ('pending','in_transit','arrived','delivered','cancelled')",
            name="ck_delivery_orders_canonical_status",
        ),
    )
    id = Column(String, primary_key=True) # DO-2026-001
    canonical_status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")
    updated_by = Column(String, nullable=False, default="system")
    version = Column(Integer, nullable=False, default=1)
    # LUỒNG MỚI: DO sinh trực tiếp từ báo giá, không qua đơn hàng.
    #
    # Thiếu cột này thì đường chốt giá ở `delivery_completion_service` — vốn lần
    # theo DO → SO → báo giá — trả về BASE_PRICE_MISSING trong luồng mới, tức
    # hoàn tất giao hàng vỡ hoàn toàn: không giá, không hoá đơn, không lợi nhuận.
    quotation_id = Column(String, ForeignKey("quotations.id"), index=True)
    # Giá cước KHOÁ cho chuyến này, tính ra ₫/chuyến lúc tách DO. Một DO một con
    # số — không phụ thuộc cân thực tế sau này.
    unit_price = Column(MONEY_TYPE)
    price_basis = Column(String)  # cách báo giá, giữ lại để in và đối soát
    # Số lượng dùng để xuất hoá đơn. Với cước theo tấn/m³ thì đây là số CÂN
    # THỰC TẾ lấy từ POD, không phải số khai.
    billed_qty = Column(Float)
    driver_note = Column(Text)  # ghi chú vận hành kế thừa từ báo giá
    customer_id = Column(String, ForeignKey("customers.id"))
    route_id = Column(String, ForeignKey("routes.id"))
    origin = Column(String)
    destination = Column(String)
    pickup_window_start = Column(DateTime(timezone=True))
    pickup_window_end = Column(DateTime(timezone=True))
    delivery_window_start = Column(DateTime(timezone=True))
    delivery_window_end = Column(DateTime(timezone=True))
    weight_kg = Column(Float, default=0.0)
    pallet_count = Column(Integer, default=0)
    notes = Column(Text)  # O Ghi chu tren man lenh giao hang
    # Ly do huy — BAT BUOC khi chuyen sang `cancelled` (migration 048). Bao gia da
    # co `close_reason`; DO truoc day huy khong ghi gi nen khong tra loi duoc
    # "vi sao lenh nay bi huy" khi doi soat.
    cancel_reason = Column(Text)
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True)
    co_driver = Column(String, nullable=True) # Phụ xế (nếu có)
    status = Column(String, default="Chờ vận chuyển")
    pickup_date = Column(DateTime(timezone=True))
    delivery_date = Column(DateTime(timezone=True))
    planned_departure_at = Column(DateTime(timezone=True))
    planned_arrival_at = Column(DateTime(timezone=True))
    planned_return_at = Column(DateTime(timezone=True))
    avg_speed_kmh = Column(Float)
    max_speed_kmh = Column(Float)
    return_speed_kmh = Column(Float)
    load_minutes = Column(Integer, default=0)
    unload_minutes = Column(Integer, default=0)
    return_distance_km = Column(Float)
    packaging_spec = Column(String, default="Thùng Carton") # Quy cách đóng gói
    volume_m3 = Column(Float, default=5.0) # Thể tích chiếm chỗ (m3)
    # Số niêm phong. Hàng NGUYÊN KHỐI không đếm kiện — một container niêm phong
    # là một đơn vị, xe không mở ra để đếm — nên bằng chứng duy nhất cho biết
    # hàng không bị mở trên đường là số niêm phong này. `seal_weight` bên Đơn
    # bán là TRỌNG TẢI niêm phong, một con số, không dùng để đối chiếu được.
    #
    # Để RỖNG được: không phải đơn nào cũng là hàng nguyên khối. Chỗ bắt buộc
    # nằm ở tầng nghiệp vụ (`packing_control_policy`), nơi biết đơn thuộc loại
    # nào — bắt buộc ở đây thì mọi đơn lẻ cũng phải điền một ô vô nghĩa.
    seal_no = Column(String)

# 8. DeliveryOrderDetails (Chi tiết hàng hóa)
class DeliveryOrderDetail(Base):
    __tablename__ = "delivery_order_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String)
    description = Column(String)
    qty = Column(Integer, default=1)
    uom = Column(String, default="PCS")
    unit_price = Column(MONEY_TYPE, default=0.0)
    amount = Column(MONEY_TYPE, default=0.0)
    weight_kg = Column(Float, default=0.0)


class ParkingList(Base):
    __tablename__ = "parking_lists"
    __table_args__ = (
        UniqueConstraint("do_id", "version", name="uq_parking_list_do_version"),
        CheckConstraint(
            "status IN ('draft','ready','parked','gate_in','loaded','dispatched','delivered','cancelled')",
            name="ck_parking_list_status",
        ),
        Index("ix_parking_list_status_created", "status", "created_at"),
    )
    id = Column(String(128), primary_key=True)
    do_id = Column(String, ForeignKey("delivery_orders.id"), nullable=False, index=True)
    trip_id = Column(String(128), ForeignKey("transport_trips.id"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)
    store_id = Column(String(128))
    store_name = Column(String(255))
    route_code = Column(String(128))
    route_name = Column(String(500))
    wave = Column(String(64))
    gate = Column(String(64))
    box_count = Column(Integer, nullable=False, default=1)
    total_pieces = Column(Integer, nullable=False, default=0)
    total_weight_kg = Column(Float, nullable=False, default=0)
    total_cube_m3 = Column(Float, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="ready")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False, default="system")
    updated_by = Column(String(128), nullable=False, default="system")
    items = relationship("ParkingListItem", back_populates="parking_list", cascade="all, delete-orphan", order_by="ParkingListItem.id")
    labels = relationship("ParkingLabel", back_populates="parking_list", cascade="all, delete-orphan", order_by="ParkingLabel.package_no")
    events = relationship("ParkingEvent", back_populates="parking_list", cascade="all, delete-orphan", order_by="ParkingEvent.occurred_at")


class ParkingListItem(Base):
    __tablename__ = "parking_list_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parking_list_id = Column(String(128), ForeignKey("parking_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    source_detail_id = Column(Integer)
    barcode = Column(String(128))
    item_id_laos = Column(String(128))
    item_id_thai = Column(String(128))
    sku = Column(String(128))
    description = Column(String(500))
    case_qty = Column(Integer, nullable=False, default=0)
    piece_qty = Column(Integer, nullable=False, default=0)
    uom = Column(String(32))
    weight_kg = Column(Float, nullable=False, default=0)
    cube_m3 = Column(Float, nullable=False, default=0)
    note = Column(Text)
    parking_list = relationship("ParkingList", back_populates="items")


class ParkingLabel(Base):
    __tablename__ = "parking_labels"
    __table_args__ = (
        UniqueConstraint("parking_list_id", "package_no", name="uq_parking_label_package"),
        UniqueConstraint("qr_token", name="uq_parking_label_qr_token"),
    )
    id = Column(String(128), primary_key=True)
    parking_list_id = Column(String(128), ForeignKey("parking_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    package_no = Column(Integer, nullable=False)
    package_total = Column(Integer, nullable=False)
    qr_token = Column(String(128), nullable=False)
    status = Column(String(20), nullable=False, default="ready")
    printed_at = Column(DateTime(timezone=True))
    reprint_count = Column(Integer, nullable=False, default=0)
    parking_list = relationship("ParkingList", back_populates="labels")


class ParkingEvent(Base):
    __tablename__ = "parking_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parking_list_id = Column(String(128), ForeignKey("parking_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    actor = Column(String(128), nullable=False, default="system")
    note = Column(Text)
    parking_list = relationship("ParkingList", back_populates="events")

# 9. ShipmentCosts (Chi phí vận chuyển)
class ShipmentCost(Base):
    __tablename__ = "shipment_costs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    do_id = Column(String, ForeignKey("delivery_orders.id"))
    fuel_cost = Column(MONEY_TYPE, default=0.0)
    driver_cost = Column(MONEY_TYPE, default=0.0)
    toll_fee = Column(MONEY_TYPE, default=0.0)
    warehouse_fee = Column(MONEY_TYPE, default=0.0)
    total_cost = Column(MONEY_TYPE, default=0.0)
    selling_price = Column(MONEY_TYPE, default=0.0)
    margin_pct = Column(Float, default=15.0)

# 10. VehicleTracking (Dữ liệu GPS)
class VehicleTracking(Base):
    __tablename__ = "vehicle_tracking"
    do_id = Column(String, ForeignKey("delivery_orders.id"), primary_key=True)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    lat = Column(Float)
    lng = Column(Float)
    speed_kmh = Column(Float, default=0.0)
    remaining_distance_km = Column(Float, default=0.0)
    eta = Column(String)
    planned_return_at = Column(String)
    last_update = Column(DateTime, default=datetime.datetime.utcnow)

# 11. POD (Xác nhận giao hàng)
class POD(Base):
    __tablename__ = "pod"
    do_id = Column(String, ForeignKey("delivery_orders.id"), primary_key=True)
    delivery_time = Column(String)
    photo_url = Column(String)
    signature_url = Column(String)
    note = Column(Text)


class DeliveryPODRecord(Base):
    __tablename__ = "delivery_pod_records"
    __table_args__ = (
        CheckConstraint("stop_no > 0", name="ck_delivery_pod_stop_positive"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(128), nullable=True)
    do_id = Column(String, ForeignKey("delivery_orders.id"), nullable=False)
    trip_id = Column(String(128), ForeignKey("transport_trips.id"))
    leg_id = Column(String(128), ForeignKey("transport_trip_legs.id"))
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True)
    stop_no = Column(Integer, nullable=False, default=1)
    location_text = Column(String)
    receiver_name = Column(String)
    receiver_phone = Column(String)
    delivery_time = Column(DateTime(timezone=True))
    photo_url = Column(String)
    signature_url = Column(String)
    delivery_result = Column(String(32))
    # SỐ CÂN THỰC TẾ lúc ký POD. Cước theo tấn/m³ không xuất được hoá đơn đúng
    # nếu không có chỗ ghi số cân: khai 24 cân 22 thì mình xuất thừa, khai 24
    # cân 26 thì mình xuất thiếu. Trước đây cả hệ thống không có cột nào chứa nó.
    actual_qty = Column(Float)
    actual_qty_uom = Column(String)
    cargo_condition = Column(Text)
    note = Column(Text)
    status = Column(String, nullable=False, default="completed")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    created_by = Column(String, nullable=False, default="system")


Index(
    "uq_delivery_pod_idempotency",
    DeliveryPODRecord.idempotency_key,
    unique=True,
    sqlite_where=DeliveryPODRecord.idempotency_key.is_not(None),
    postgresql_where=DeliveryPODRecord.idempotency_key.is_not(None),
)
Index(
    "uq_legacy_delivery_pod_vehicle_stop",
    DeliveryPODRecord.do_id, DeliveryPODRecord.vehicle_id, DeliveryPODRecord.stop_no,
    unique=True,
    sqlite_where=DeliveryPODRecord.trip_id.is_(None),
    postgresql_where=DeliveryPODRecord.trip_id.is_(None),
)
Index(
    "uq_trip_delivery_pod_vehicle_stop",
    DeliveryPODRecord.trip_id, DeliveryPODRecord.leg_id, DeliveryPODRecord.do_id,
    DeliveryPODRecord.vehicle_id, DeliveryPODRecord.stop_no,
    unique=True,
    sqlite_where=DeliveryPODRecord.trip_id.is_not(None),
    postgresql_where=DeliveryPODRecord.trip_id.is_not(None),
)


class DeliveryOrderCloseout(Base):
    __tablename__ = "delivery_order_closeouts"
    __table_args__ = (
        CheckConstraint("base_selling_price_snapshot >= 0", name="ck_do_closeout_base_nonnegative"),
        CheckConstraint("surcharge_total >= 0", name="ck_do_closeout_surcharge_nonnegative"),
        CheckConstraint("final_selling_price >= 0", name="ck_do_closeout_final_nonnegative"),
        CheckConstraint(
            "final_selling_price = base_selling_price_snapshot + surcharge_total",
            name="ck_do_closeout_final_total",
        ),
    )
    id = Column(String(128), primary_key=True)
    do_id = Column(String, ForeignKey("delivery_orders.id"), nullable=False, unique=True)
    base_selling_price_snapshot = Column(MONEY_TYPE, nullable=False)
    base_price_source = Column(String(32), nullable=False)
    base_price_source_id = Column(String(128), nullable=False)
    surcharge_total = Column(MONEY_TYPE, nullable=False, default=0)
    final_selling_price = Column(MONEY_TYPE, nullable=False)
    currency_code = Column(String(3), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    completed_by = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


class DeliveryOrderChargeAdjustment(Base):
    __tablename__ = "delivery_order_charge_adjustments"
    __table_args__ = (
        UniqueConstraint("closeout_id", "line_no", name="uq_do_charge_adjustment_line"),
        CheckConstraint("line_no > 0", name="ck_do_charge_adjustment_line_positive"),
        CheckConstraint("original_amount >= 0", name="ck_do_charge_adjustment_original_nonnegative"),
        CheckConstraint("actual_amount >= original_amount", name="ck_do_charge_adjustment_actual_gte_original"),
        CheckConstraint(
            "increase_amount = actual_amount - original_amount",
            name="ck_do_charge_adjustment_increase_total",
        ),
    )
    id = Column(String(128), primary_key=True)
    closeout_id = Column(
        String(128), ForeignKey("delivery_order_closeouts.id", ondelete="CASCADE"), nullable=False
    )
    line_no = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    # Mã costindex — khoản khách trả thêm cũng là một dòng THU cần lập phiếu,
    # nên nó mang mã như dòng chi phí.
    cost_index = Column(String(32))
    original_amount = Column(MONEY_TYPE, nullable=False, default=0)
    actual_amount = Column(MONEY_TYPE, nullable=False)
    increase_amount = Column(MONEY_TYPE, nullable=False)
    note = Column(Text)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    created_by = Column(String(255), nullable=False)


class DeliveryPODDocument(Base):
    __tablename__ = "delivery_pod_documents"
    __table_args__ = (
        UniqueConstraint("pod_record_id", "checksum", name="uq_delivery_pod_document_checksum"),
        CheckConstraint("file_size >= 0 AND file_size <= 10485760", name="ck_delivery_pod_document_size"),
    )
    id = Column(String(128), primary_key=True)
    pod_record_id = Column(
        Integer, ForeignKey("delivery_pod_records.id", ondelete="CASCADE"), nullable=False
    )
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(Integer, nullable=False)
    checksum = Column(String(128), nullable=False)
    content = Column(LargeBinary, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    created_by = Column(String(255), nullable=False)

# 12. ARInvoices (Hóa đơn công nợ)
class ARInvoice(Base):
    __tablename__ = "ar_invoices"
    id = Column(String, primary_key=True) # INV-2026-001
    canonical_status = Column(String, nullable=False, default="posted")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")
    updated_by = Column(String, nullable=False, default="system")
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    reversal_of_invoice_id = Column(String, ForeignKey("ar_invoices.id"))
    currency_code = Column(String, nullable=False, default="VND")
    exchange_rate_snapshot = Column(Numeric, nullable=False, default=1)
    tax_rate_snapshot = Column(Numeric)
    do_id = Column(String, ForeignKey("delivery_orders.id"))
    customer_id = Column(String, ForeignKey("customers.id"))
    invoice_date = Column(String)
    amount = Column(MONEY_TYPE, nullable=False, default=0) # Giá vốn/Bán
    vat_pct = Column(RATE_TYPE, nullable=False, default=10)
    vat_amount = Column(MONEY_TYPE, nullable=False, default=0)
    total = Column(MONEY_TYPE, nullable=False, default=0)
    status = Column(String, default="Posted")

Index("uq_active_invoice_do", ARInvoice.do_id, unique=True, sqlite_where=ARInvoice.is_active.is_(True), postgresql_where=ARInvoice.is_active.is_(True))

# 13. GLTransactions (Bút toán kế toán)
class GLTransaction(Base):
    __tablename__ = "gl_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String, ForeignKey("ar_invoices.id"))
    date = Column(String)
    account_code = Column(String) # 131, 511, 3331...
    debit = Column(MONEY_TYPE, default=0.0)
    credit = Column(MONEY_TYPE, default=0.0)

# 14. Incidents (Báo cáo sự cố)
class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    do_id = Column(String)
    vehicle_id = Column(String)
    incident_type = Column(String)
    severity = Column(String, default="Medium")
    location = Column(String)
    description = Column(Text)
    reporter = Column(String, default="Tài xế / Điều phối")
    reported_at = Column(String)
    status = Column(String, default="Pending")

# 15. AuditLogs (Lịch sử thay đổi)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)
    action = Column(String) # CREATE, UPDATE, DELETE
    table_name = Column(String)
    record_id = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String)

# ==========================================
# NEW MASTER DATA & FORMS
# ==========================================

# 15. Item / Cargo
class Item(Base):
    __tablename__ = "items"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    cargo_type = Column(String) # Container 20FT, Box, Pallet
    notes = Column(Text)  # O Ghi chu tren man bao gia
    default_uom = Column(String)
    weight_kg = Column(Float, default=0.0)

# 16. UOM (Unit of Measure)
class UOM(Base):
    __tablename__ = "uoms"
    id = Column(String, primary_key=True) # PCS, KG, CBM, TEU
    description = Column(String)

# 17. Cost Formula
class CostFormula(Base):
    __tablename__ = "cost_formulas"
    id = Column(String, primary_key=True)
    name = Column(String)
    formula_expression = Column(Text) # JSON or eval string

# 18. Price List
class PriceList(Base):
    __tablename__ = "price_lists"
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.id"))
    item_id = Column(String, ForeignKey("items.id"))
    unit_price = Column(MONEY_TYPE, default=0.0)
    valid_to = Column(String)

# 19. Currency
class Currency(Base):
    __tablename__ = "currencies"
    id = Column(String, primary_key=True) # VND, USD
    exchange_rate = Column(MONEY_TYPE, default=1.0)

# 20. User & Role
class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True) # Admin, Sales, Dispatcher
    permissions = Column(Text)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    role_id = Column(String, ForeignKey("roles.id"))

# 21. Chart of Account
class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"
    account_code = Column(String, primary_key=True) # 131, 511
    account_name = Column(String)
    type = Column(String) # Asset, Liability, Equity, Revenue, Expense

# 22. Quotation
class Quotation(Base):
    __tablename__ = "quotations"
    # Ràng buộc trạng thái CÙNG tập với mốc 040 (`ck_quotations_canonical_status`).
    #
    # Trước đây ràng buộc này chỉ có trên PostgreSQL (do mốc nâng cấp tạo), còn
    # `models.py` không khai — nên mọi schema dựng từ model (bộ kiểm) nhận bất kỳ
    # chuỗi nào, và bài đối chiếu schema chỉ soi chiều "model có → DB có" nên
    # không thấy. Khai ở đây để hai bên nói cùng một tập; thêm trạng thái mới thì
    # sửa CẢ đây và viết mốc mới.
    __table_args__ = (
        CheckConstraint(
            "canonical_status IN ('draft','pending_approval','sent','approved','accepted',"
            "'rejected','split','expired','cancelled','unknown')",
            name="ck_quotations_canonical_status",
        ),
    )
    id = Column(String, primary_key=True) # QT-2026-001
    canonical_status = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")
    updated_by = Column(String, nullable=False, default="system")
    version = Column(Integer, nullable=False, default=1)
    customer_id = Column(String, ForeignKey("customers.id"))
    route_id = Column(String, ForeignKey("routes.id"))
    origin = Column(String)
    destination = Column(String)
    pickup_window_start = Column(String)
    pickup_window_end = Column(String)
    delivery_window_start = Column(String)
    delivery_window_end = Column(String)
    weight_kg = Column(Float, default=0.0)
    pallet_count = Column(Integer, default=0)
    cargo_type = Column(String)
    valid_to = Column(String)
    fuel_cost = Column(MONEY_TYPE, default=0.0)
    driver_cost = Column(MONEY_TYPE, default=0.0)
    toll_fee = Column(MONEY_TYPE, default=0.0)
    total_cost = Column(MONEY_TYPE, default=0.0)
    selling_price = Column(MONEY_TYPE, default=0.0)
    packaging_spec = Column(String, default="Thùng Carton") # Quy cách đóng gói
    # Quy cach va dieu kien van chuyen. Dat tren Quotation:
    # day la dieu kien chao cho khach o buoc bao gia, va phai di theo sang don
    # hang khi chot — khong bat khai lai. Tab nay tung co sau o nhap ma khong
    # co cot nao de chua, nen dien xong la mat.
    carrier_name = Column(String)             # Don vi van chuyen
    delivery_method = Column(String)          # Phuong thuc giao
    seal_weight = Column(String)              # Trong tai niem phong
    temperature_requirement = Column(String)  # Yeu cau nhiet do
    cargo_insurance = Column(String)          # Bao hiem hang hoa
    warehouse_owner = Column(String)          # Nguoi phu trach kho
    volume_m3 = Column(Float, default=5.0) # Thể tích m3
    notes = Column(Text)  # O Ghi chu tren man bao gia
    status = Column(String, default="Draft") # Draft, Sent, Approved

    # ===================== LUỒNG MỚI: QT → DO, bỏ bước SO =====================
    # Đơn vị tính cước. Chốt với chủ dự án sau khi bàn bài toán mỏ đá: báo giá
    # theo đơn vị của KHÁCH, nhưng DO luôn khoá một con số ₫/chuyến. Nếu cơ sở
    # dữ liệu lưu ₫/kg thì mọi con số phía sau phụ thuộc CÂN THỰC TẾ, mà cân
    # thực tế luôn khác cân khai — nghĩa là giá khách đã đồng ý sẽ tự đổi sau
    # khi xe chạy.
    price_basis = Column(String)  # per_trip | per_tonne | per_m3 | per_kg | per_km
    unit_price = Column(MONEY_TYPE)  # đơn giá theo `price_basis`
    # Mức tối thiểu tính tiền mỗi chuyến. Thứ chặn mỏ xúc thiếu tải làm một
    # chuyến lãi thành lỗ: giá thành không đổi một đồng khi xe chở ít hơn.
    min_qty_per_trip = Column(Float)

    # Mã hiện cho khách, cấp lúc GỬI. Khác khoá chính: spec đòi "nháp chưa có
    # mã", mà khoá chính thì không thể rỗng nên nháp sẽ không lưu được.
    quote_no = Column(String, index=True)
    vehicle_type_id = Column(String, ForeignKey("vehicle_types.id"))
    currency_code = Column(String, default="VND")
    # Tỷ giá LÚC GỬI, lưu kèm báo giá: tỷ giá đổi sau đó thì PDF khách đã nhận
    # và bản đối soát của mình phải vẫn khớp nhau.
    fx_rate = Column(Float, default=1.0)
    payment_terms = Column(String)
    sales_rep = Column(String)
    trips_per_month = Column(Integer)
    waiting_surcharge = Column(MONEY_TYPE)  # phụ phí chờ quá giờ
    cargo_value = Column(MONEY_TYPE)  # chỉ dùng khi công thức có phí bảo hiểm
    stacking = Column(String)
    sealing = Column(String)
    recipient_contact = Column(String)
    # BA ô ghi chú TÁCH RỜI. Trước đây dùng một cột `notes`, nên ghi chú nội bộ
    # ("khách đang so giá, tối đa giảm 3%") in ra cho chính khách đọc.
    notes_customer = Column(Text)  # in trên PDF
    notes_ops = Column(Text)       # hiện trên DO và lệnh tài xế
    notes_internal = Column(Text)  # không in
    bot_fee = Column(MONEY_TYPE)   # BOT chốt theo tuyến lúc báo giá
    # Ảnh chụp bảng cấu phần giá thành lúc gửi. Công thức ở Dữ liệu gốc đổi theo
    # tháng, nên không lưu lại thì không ai dựng lại được con số đã chào khách.
    cost_breakdown_json = Column(Text)
    target_margin = Column(Float)  # biên mục tiêu riêng cho khách này
    # Giá đối thủ mà khách nói ra, tính bằng VNĐ. Cột riêng chứ không nhét vào
    # ghi chú nội bộ: một con số nằm trong đoạn văn tự do là con số không lọc
    # được, không dùng được làm mốc gợi ý giá, và không đối soát lại được sau
    # một quý là mình mất khách vì giá hay vì thứ khác.
    competitor_price = Column(Numeric(18, 2))
    # Chiết khấu cho khách (0..1). `unit_price` vẫn là giá CUỐI; cột này chỉ để
    # suy ngược "giá gốc trước chiết khấu" trên phiếu gửi khách (v050).
    discount_percent = Column(Float)
    sent_at = Column(DateTime)
    accepted_at = Column(DateTime)
    closed_at = Column(DateTime)
    close_reason = Column(Text)


class QuotationItem(Base):
    """Một dòng hàng hoá của báo giá.

    KHÔNG có đơn giá và thành tiền, có chủ ý: mình là đơn vị vận chuyển, chỉ
    tính cước chứ không tính tiền hàng. Thêm hai cột đó vào là mở đường cho
    người dùng gõ giá trị lô hàng rồi tưởng hệ thống đang tính tiền hàng.
    """
    __tablename__ = "quotation_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_quotation_items_qty"),
    )
    id = Column(String, primary_key=True)
    quotation_id = Column(String, ForeignKey("quotations.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    line_no = Column(Integer, nullable=False, default=1)
    name = Column(String)
    quantity = Column(MONEY_TYPE, nullable=False, default=0)
    uom = Column(String, nullable=False, default="Chuyến")  # 40' · 20' · Tấn · Pallet · Kiện
    note = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class QuotationAttachment(Base):
    """Chứng từ đính kèm báo giá — đi theo DO xuống vận hành và kế toán."""
    __tablename__ = "quotation_attachments"
    id = Column(String, primary_key=True)
    quotation_id = Column(String, ForeignKey("quotations.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    doc_type = Column(String, nullable=False, default="Khác")
    file_name = Column(String, nullable=False)
    storage_url = Column(Text, nullable=False)
    mime_type = Column(String)
    size_bytes = Column(Integer)
    note = Column(String)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    uploaded_by = Column(String, nullable=False, default="system")


class QuotationVersion(Base):
    """Phiên bản giá của một báo giá.

    Mỗi lần sửa giá SAU KHI đã gửi thì tăng phiên bản. Không có bảng này thì
    không ai đối soát được với bản PDF khách đang giữ.
    """
    __tablename__ = "quotation_versions"
    __table_args__ = (
        UniqueConstraint("quotation_id", "version", name="uq_quotation_versions"),
    )
    id = Column(String, primary_key=True)
    quotation_id = Column(String, ForeignKey("quotations.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    version = Column(Integer, nullable=False)
    selling_price = Column(MONEY_TYPE)
    unit_price = Column(MONEY_TYPE)
    price_basis = Column(String)
    total_cost = Column(MONEY_TYPE)
    currency_code = Column(String)
    fx_rate = Column(Float)
    note = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")

class QuotationDetail(Base):
    __tablename__ = "quotation_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    quotation_id = Column(String, ForeignKey("quotations.id"))
    item_id = Column(String, ForeignKey("items.id"))
    qty = Column(Integer, default=1)
    uom = Column(String)
    unit_price = Column(MONEY_TYPE, default=0.0)
    amount = Column(MONEY_TYPE, default=0.0)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("actor", "method", "path", "idempotency_key", name="uq_idempotency_scope"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(128), nullable=False)
    method = Column(String(16), nullable=False)
    path = Column(String(500), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    operation = Column(String, nullable=False, default="")
    request_hash = Column(String, nullable=False)
    response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class AccountingPeriod(Base):
    __tablename__ = "accounting_periods"
    id = Column(String, primary_key=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    closed_at = Column(DateTime)
    closed_by = Column(String)


class AccountMapping(Base):
    __tablename__ = "account_mappings"
    mapping_key = Column(String, primary_key=True)
    account_code = Column(String, nullable=False)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)


class JournalBatch(Base):
    __tablename__ = "journal_batches"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_journal_source"),
        CheckConstraint("source_type IS NULL OR source_type IN ('ar_invoice','ap_invoice','ap_payment','ap_reversal','payment_reversal')", name="ck_journal_source_type"),
    )
    id = Column(String, primary_key=True)
    invoice_id = Column(String, ForeignKey("ar_invoices.id"), nullable=True, unique=True)
    source_type = Column(String(32), nullable=True)
    source_id = Column(String, nullable=True)
    status = Column(String, nullable=False)
    posted_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class JournalLine(Base):
    __tablename__ = "journal_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("journal_batches.id"), nullable=False)
    account_code = Column(String, nullable=False)
    debit = Column(Numeric, nullable=False, default=0)
    credit = Column(Numeric, nullable=False, default=0)
    currency_code = Column(String, nullable=False, default="VND")
    exchange_rate_snapshot = Column(Numeric, nullable=False, default=1)
    transaction_amount = Column(MONEY_TYPE, nullable=False, default=0)
    transaction_currency = Column(String(3), nullable=False, default="VND")
    exchange_rate = Column(RATE_TYPE, nullable=False, default=1)
    functional_debit = Column(MONEY_TYPE, nullable=False, default=0)
    functional_credit = Column(MONEY_TYPE, nullable=False, default=0)


class MigrationQuarantine(Base):
    __tablename__ = "migration_quarantine"
    id = Column(Integer, primary_key=True, autoincrement=True)
    migration_version = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    quarantined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


# 23. TMS Core Planning
class TransportDemand(Base):
    __tablename__ = "transport_demands"
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    pickup_location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    delivery_location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    pickup_window_start = Column(DateTime, nullable=False)
    pickup_window_end = Column(DateTime, nullable=False)
    delivery_window_start = Column(DateTime, nullable=False)
    delivery_window_end = Column(DateTime, nullable=False)
    weight_kg = Column(Float, nullable=False, default=0)
    volume_m3 = Column(Float, nullable=False, default=0)
    pallet_count = Column(Integer, nullable=False, default=0)
    service_requirements = Column(Text)
    status = Column(String, nullable=False, default="draft")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    created_by = Column(String, nullable=False, default="system")
    updated_by = Column(String, nullable=False, default="system")


class FreightUnit(Base):
    __tablename__ = "freight_units"
    id = Column(String, primary_key=True)
    demand_id = Column(String, ForeignKey("transport_demands.id"), nullable=False, unique=True)
    pickup_location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    delivery_location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    pickup_window_start = Column(DateTime, nullable=False)
    pickup_window_end = Column(DateTime, nullable=False)
    delivery_window_start = Column(DateTime, nullable=False)
    delivery_window_end = Column(DateTime, nullable=False)
    weight_kg = Column(Float, nullable=False, default=0)
    volume_m3 = Column(Float, nullable=False, default=0)
    pallet_count = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="open")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")


class FreightOrderUnit(Base):
    __tablename__ = "freight_order_units"
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), primary_key=True)
    freight_unit_id = Column(String, ForeignKey("freight_units.id"), primary_key=True, unique=True)


class FreightOrder(Base):
    __tablename__ = "freight_orders"
    id = Column(String, primary_key=True)
    pickup_location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    delivery_location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    pickup_window_start = Column(DateTime, nullable=False)
    pickup_window_end = Column(DateTime, nullable=False)
    delivery_window_start = Column(DateTime, nullable=False)
    delivery_window_end = Column(DateTime, nullable=False)
    total_weight_kg = Column(Float, nullable=False, default=0)
    total_volume_m3 = Column(Float, nullable=False, default=0)
    total_pallet_count = Column(Integer, nullable=False, default=0)
    max_weight_kg = Column(Float, nullable=False)
    max_volume_m3 = Column(Float, nullable=False)
    max_pallet_count = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="planned")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")
    updated_by = Column(String, nullable=False, default="system")
    units = relationship("FreightUnit", secondary="freight_order_units")
    resource_assignments = relationship("ResourceAssignment", back_populates="freight_order")


class TransportTrip(Base):
    """Một lần thực thi vận tải, tách biệt với nhu cầu Freight Order/DO."""
    __tablename__ = "transport_trips"
    __table_args__ = (
        CheckConstraint(
            "trip_type IN ('one_way','round_trip','backhaul','multi_stop')",
            name="ck_transport_trip_type",
        ),
        CheckConstraint(
            "status IN ('draft','planned','dispatched','in_transit','completed','settled','cancelled')",
            name="ck_transport_trip_status",
        ),
        CheckConstraint("version > 0", name="ck_transport_trip_version"),
    )
    id = Column(String(128), primary_key=True)
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), nullable=False, index=True)
    trip_type = Column(String(20), nullable=False, default="one_way")
    status = Column(String(20), nullable=False, default="draft")
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    driver_id = Column(String, ForeignKey("drivers.id"))
    co_driver_id = Column(String, ForeignKey("drivers.id"))
    planned_departure_at = Column(DateTime(timezone=True))
    planned_arrival_at = Column(DateTime(timezone=True))
    planned_return_at = Column(DateTime(timezone=True))
    actual_departure_at = Column(DateTime(timezone=True))
    actual_arrival_at = Column(DateTime(timezone=True))
    actual_return_at = Column(DateTime(timezone=True))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False, default="system")
    updated_by = Column(String(128), nullable=False, default="system")


class TripDeliveryOrder(Base):
    """Nhiều-nhiều: một DO có thể được thực hiện qua nhiều chuyến."""
    __tablename__ = "trip_delivery_orders"
    trip_id = Column(String(128), ForeignKey("transport_trips.id", ondelete="CASCADE"), primary_key=True)
    do_id = Column(String, ForeignKey("delivery_orders.id"), primary_key=True)
    allocation_sequence = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False, default="system")


class TransportTripLeg(Base):
    """Chặng có thứ tự, bao gồm lượt đi, giao hàng và lượt về/backhaul."""
    __tablename__ = "transport_trip_legs"
    __table_args__ = (
        UniqueConstraint("trip_id", "sequence_no", name="uq_transport_trip_leg_sequence"),
        ForeignKeyConstraint(
            ["trip_id", "do_id"],
            ["trip_delivery_orders.trip_id", "trip_delivery_orders.do_id"],
            name="fk_trip_leg_delivery_order_membership",
        ),
        CheckConstraint("sequence_no > 0", name="ck_transport_trip_leg_sequence_positive"),
        CheckConstraint(
            "leg_type IN ('outbound','pickup','delivery','empty_return','backhaul','warehouse_transfer')",
            name="ck_transport_trip_leg_type",
        ),
        CheckConstraint(
            "status IN ('planned','ready','in_transit','arrived','completed','cancelled')",
            name="ck_transport_trip_leg_status",
        ),
        CheckConstraint(
            "distance_km >= 0 AND avg_speed_kmh > 0 AND dwell_minutes >= 0",
            name="ck_transport_trip_leg_metrics",
        ),
    )
    id = Column(String(128), primary_key=True)
    trip_id = Column(String(128), ForeignKey("transport_trips.id", ondelete="CASCADE"), nullable=False)
    do_id = Column(String)
    sequence_no = Column(Integer, nullable=False)
    leg_type = Column(String(30), nullable=False)
    origin = Column(String(500), nullable=False)
    destination = Column(String(500), nullable=False)
    stop_name = Column(String(500))
    receiver_name = Column(String(255))
    receiver_phone = Column(String(64))
    delivery_note = Column(Text)
    distance_km = Column(DISTANCE_TYPE, nullable=False, default=0)
    avg_speed_kmh = Column(RATE_TYPE, nullable=False)
    dwell_minutes = Column(Integer, nullable=False, default=0)
    planned_departure_at = Column(DateTime(timezone=True))
    planned_arrival_at = Column(DateTime(timezone=True))
    actual_departure_at = Column(DateTime(timezone=True))
    actual_arrival_at = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="planned")
    allocated_cost = Column(MONEY_TYPE, nullable=False, default=0)
    allocated_revenue = Column(MONEY_TYPE, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.datetime.utcnow)


class Carrier(Base):
    __tablename__ = "carriers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tax_code = Column(String)
    contact_person = Column(String)
    phone = Column(String)
    email = Column(String)
    status = Column(String, nullable=False, default="active")
    is_internal = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")


class Tender(Base):
    __tablename__ = "tenders"
    id = Column(String, primary_key=True)
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), nullable=False, unique=True)
    response_deadline = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="published")
    awarded_offer_id = Column(String)
    awarded_carrier_id = Column(String, ForeignKey("carriers.id"))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")
    updated_by = Column(String, nullable=False, default="system")
    offers = relationship("TenderOffer", back_populates="tender")


class TenderOffer(Base):
    __tablename__ = "tender_offers"
    __table_args__ = (UniqueConstraint("tender_id", "carrier_id", name="uq_tender_carrier_offer"),)
    id = Column(String, primary_key=True)
    tender_id = Column(String, ForeignKey("tenders.id"), nullable=False)
    carrier_id = Column(String, ForeignKey("carriers.id"), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    currency_code = Column(String, nullable=False, default="VND")
    note = Column(Text)
    status = Column(String, nullable=False, default="offered")
    submitted_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    submitted_by = Column(String, nullable=False, default="system")
    tender = relationship("Tender", back_populates="offers")


class DriverQualification(Base):
    __tablename__ = "driver_qualifications"
    driver_id = Column(String, ForeignKey("drivers.id"), primary_key=True)
    license_type = Column(String, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="active")
    verified_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    verified_by = Column(String, nullable=False, default="system")


class WarehouseAppointment(Base):
    __tablename__ = "warehouse_appointments"
    __table_args__ = (UniqueConstraint("freight_order_id", "appointment_type", name="uq_fo_appointment_type"),)
    id = Column(String, primary_key=True)
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), nullable=False)
    appointment_type = Column(String, nullable=False)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="booked")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")


class ResourceAssignment(Base):
    __tablename__ = "resource_assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), nullable=False)
    trip_id = Column(String(128), ForeignKey("transport_trips.id"))
    leg_id = Column(String(128), ForeignKey("transport_trip_legs.id"))
    vehicle_id = Column(String, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    co_driver_id = Column(String, ForeignKey("drivers.id"))
    assignment_start = Column(DateTime(timezone=True), nullable=False)
    assignment_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False, default="system")
    freight_order = relationship("FreightOrder", back_populates="resource_assignments")


Index(
    "uq_legacy_assignment_freight_order",
    ResourceAssignment.freight_order_id,
    unique=True,
    sqlite_where=ResourceAssignment.trip_id.is_(None),
    postgresql_where=ResourceAssignment.trip_id.is_(None),
)
Index(
    "uq_active_assignment_trip",
    ResourceAssignment.trip_id,
    unique=True,
    sqlite_where=ResourceAssignment.trip_id.is_not(None) & (ResourceAssignment.status == "active"),
    postgresql_where=ResourceAssignment.trip_id.is_not(None) & (ResourceAssignment.status == "active"),
)


class TransportEvent(Base):
    __tablename__ = "transport_events"
    __table_args__ = (
        UniqueConstraint("freight_order_id", "idempotency_key", name="uq_transport_event_idempotency"),
        Index("ix_transport_events_order_time", "freight_order_id", "event_time", "recorded_at"),
    )
    id = Column(String, primary_key=True)
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), nullable=False)
    trip_id = Column(String(128), ForeignKey("transport_trips.id"))
    leg_id = Column(String(128), ForeignKey("transport_trip_legs.id"))
    event_type = Column(String, nullable=False)
    event_time = Column(DateTime, nullable=False)
    lat = Column(Float)
    lng = Column(Float)
    speed_kmh = Column(Float)
    distance_km = Column(Float)
    eta = Column(String)
    location_text = Column(String)
    source = Column(String, nullable=False)
    device_id = Column(String)
    reason = Column(Text)
    note = Column(Text)
    idempotency_key = Column(String, nullable=False)
    payload_hash = Column(String, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    recorded_by = Column(String, nullable=False)
    documents = relationship("TransportEventDocument", back_populates="event")


class TransportEventDocument(Base):
    __tablename__ = "transport_event_documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, ForeignKey("transport_events.id"), nullable=False)
    document_type = Column(String, nullable=False)
    storage_url = Column(Text, nullable=False)
    file_name = Column(String)
    mime_type = Column(String)
    checksum = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    uploaded_by = Column(String, nullable=False)
    event = relationship("TransportEvent", back_populates="documents")


class FreightActualCost(Base):
    __tablename__ = "freight_actual_costs"
    __table_args__ = (
        CheckConstraint("status IN ('draft','submitted','approved','reversed')", name="ck_freight_cost_status"),
        CheckConstraint("planned_distance_km >= 0 AND actual_distance_km >= 0", name="ck_freight_cost_distance"),
        CheckConstraint("version > 0", name="ck_freight_cost_version"),
        CheckConstraint("(status = 'reversed' AND is_active = false) OR (status <> 'reversed' AND is_active = true)", name="ck_freight_cost_active_status"),
        CheckConstraint("reversal_of_cost_id IS NULL OR reversal_of_cost_id <> id", name="ck_freight_cost_no_self_reversal"),
        CheckConstraint("reversal_of_cost_id IS NULL OR (status = 'reversed' AND is_active = false AND length(trim(reversal_reason)) > 0 AND subtotal_amount <= 0 AND tax_amount <= 0 AND total_amount <= 0)", name="ck_freight_cost_reversal_shape"),
        CheckConstraint("status <> 'reversed' OR reversal_of_cost_id IS NOT NULL OR reversed_by_cost_id IS NOT NULL", name="ck_freight_cost_reversed_link"),
    )
    id = Column(String, primary_key=True)
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), nullable=False)
    trip_id = Column(String(128), ForeignKey("transport_trips.id"))
    leg_id = Column(String(128), ForeignKey("transport_trip_legs.id"))
    carrier_id = Column(String, ForeignKey("carriers.id"), nullable=False)
    currency_code = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    functional_currency = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    exchange_rate_snapshot = Column(RATE_TYPE, nullable=False, default=1)
    exchange_rate_date = Column(Date, nullable=False)
    exchange_rate_source = Column(String(100), nullable=False)
    planned_distance_km = Column(DISTANCE_TYPE, nullable=False, default=0)
    actual_distance_km = Column(DISTANCE_TYPE, nullable=False, default=0)
    distance_status = Column(String(32), nullable=False, default="insufficient_gps_data")
    distance_variance_percent = Column(RATE_TYPE)
    distance_variance_warning = Column(Boolean, nullable=False, default=False)
    subtotal_amount = Column(MONEY_TYPE, nullable=False, default=0)
    tax_amount = Column(MONEY_TYPE, nullable=False, default=0)
    total_amount = Column(MONEY_TYPE, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="draft")
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    reversal_of_cost_id = Column(String, ForeignKey("freight_actual_costs.id"), unique=True)
    reversed_by_cost_id = Column(String, ForeignKey("freight_actual_costs.id", deferrable=True, initially="DEFERRED"), unique=True)
    reversal_reason = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    reversed_at = Column(DateTime)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    submitted_by = Column(String)
    approved_by = Column(String)
    reversed_by = Column(String)


Index(
    "uq_legacy_active_cost_freight_order",
    FreightActualCost.freight_order_id,
    unique=True,
    sqlite_where=FreightActualCost.trip_id.is_(None) & FreightActualCost.is_active.is_(True),
    postgresql_where=FreightActualCost.trip_id.is_(None) & FreightActualCost.is_active.is_(True),
)
Index(
    "uq_active_cost_trip",
    FreightActualCost.trip_id,
    unique=True,
    sqlite_where=FreightActualCost.trip_id.is_not(None) & FreightActualCost.is_active.is_(True),
    postgresql_where=FreightActualCost.trip_id.is_not(None) & FreightActualCost.is_active.is_(True),
)


class FreightChargeItem(Base):
    __tablename__ = "freight_charge_items"
    __table_args__ = (
        CheckConstraint("charge_type IN ('fuel','toll','driver','yard','waiting','loading','unloading','carrier_base','surcharge','discount','other')", name="ck_freight_charge_type"),
        CheckConstraint("quantity >= 0", name="ck_freight_charge_quantity"),
        CheckConstraint("charge_type = 'discount' OR unit_price >= 0", name="ck_freight_charge_nonnegative"),
    )
    id = Column(String, primary_key=True)
    cost_id = Column(String, ForeignKey("freight_actual_costs.id", ondelete="CASCADE"), nullable=False)
    charge_type = Column(String(32), nullable=False)
    # Mã costindex của EPL — mã phân loại chi phí do người làm tài chính đặt
    # trên công thức giá thành, đi theo dòng chi phí tới hồ sơ hoàn tất để hệ
    # công nợ lập phiếu chi. Khác `charge_type` (mã nội bộ cố định của hệ).
    cost_index = Column(String(32))
    description = Column(String(500))
    original_amount = Column(MONEY_TYPE, nullable=False, default=0)
    actual_amount = Column(MONEY_TYPE, nullable=False, default=0)
    increase_amount = Column(MONEY_TYPE, nullable=False, default=0)
    note = Column(Text)
    quantity = Column(QUANTITY_TYPE, nullable=False)
    unit_price = Column(MONEY_TYPE, nullable=False)
    tax_code = Column(String(50), nullable=False)
    tax_rate_snapshot = Column(RATE_TYPE, nullable=False)
    tax_mode = Column(String(20), nullable=False)
    net_amount = Column(MONEY_TYPE, nullable=False)
    tax_amount = Column(MONEY_TYPE, nullable=False)
    total_amount = Column(MONEY_TYPE, nullable=False)
    rounding_adjustment = Column(MONEY_TYPE, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)


class FreightCostDocument(Base):
    __tablename__ = "freight_cost_documents"
    __table_args__ = (UniqueConstraint("cost_id", "checksum", name="uq_freight_cost_document_checksum"),)
    id = Column(String, primary_key=True)
    cost_id = Column(String, ForeignKey("freight_actual_costs.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(64), nullable=False)
    storage_url = Column(Text, nullable=False)
    file_name = Column(String(255))
    mime_type = Column(String(128))
    checksum = Column(String(128), nullable=False)
    vendor_invoice_no = Column(String(128))
    document_date = Column(Date)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)


class EPLExpenseVoucher(Base):
    __tablename__ = "epl_expense_vouchers"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uq_epl_expense_voucher_trip"),
        UniqueConstraint("voucher_no", name="uq_epl_expense_voucher_no"),
        CheckConstraint(
            "payment_method IN ('cash','bank_transfer','credit','other')",
            name="ck_epl_expense_voucher_payment_method",
        ),
        CheckConstraint("version > 0", name="ck_epl_expense_voucher_version"),
    )
    id = Column(String(128), primary_key=True)
    trip_id = Column(String(128), ForeignKey("transport_trips.id"), nullable=False)
    cost_id = Column(String(128), ForeignKey("freight_actual_costs.id"), nullable=False)
    do_id = Column(String, ForeignKey("delivery_orders.id"))
    voucher_no = Column(String(128), nullable=False)
    voucher_date = Column(Date, nullable=False)
    vehicle_manager = Column(String(255))
    payment_method = Column(String(32), nullable=False, default="cash")
    contract_no = Column(String(128))
    machine_numbers = Column(String(500))
    checked_by = Column(String(255))
    note = Column(Text)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String(128), nullable=False)
    updated_by = Column(String(128), nullable=False)


class APInvoice(Base):
    __tablename__ = "ap_invoices"
    __table_args__ = (
        UniqueConstraint("carrier_id", "normalized_vendor_invoice_no", "document_kind", name="uq_ap_vendor_document"),
        CheckConstraint("document_kind IN ('invoice','credit_memo')", name="ck_ap_document_kind"),
        CheckConstraint("status IN ('draft','submitted','approved','posted','partially_paid','paid','reversed')", name="ck_ap_status"),
        CheckConstraint("version > 0", name="ck_ap_version"),
        CheckConstraint("reversal_of_ap_id IS NULL OR reversal_of_ap_id <> id", name="ck_ap_no_self_reversal"),
        CheckConstraint("document_kind <> 'credit_memo' OR (subtotal_amount <= 0 AND tax_amount <= 0 AND total_amount <= 0)", name="ck_ap_credit_negative"),
    )
    id = Column(String, primary_key=True)
    cost_id = Column(String, ForeignKey("freight_actual_costs.id"), nullable=False)
    carrier_id = Column(String, ForeignKey("carriers.id"), nullable=False)
    carrier_name_snapshot = Column(String, nullable=False)
    carrier_tax_code_snapshot = Column(String)
    vendor_invoice_no = Column(String(128), nullable=False)
    normalized_vendor_invoice_no = Column(String(128), nullable=False)
    document_kind = Column(String(20), nullable=False, default="invoice")
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    currency_code = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    functional_currency = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    exchange_rate_snapshot = Column(RATE_TYPE, nullable=False)
    exchange_rate_date = Column(Date, nullable=False)
    exchange_rate_source = Column(String(100), nullable=False)
    subtotal_amount = Column(MONEY_TYPE, nullable=False)
    tax_amount = Column(MONEY_TYPE, nullable=False)
    total_amount = Column(MONEY_TYPE, nullable=False)
    functional_subtotal_amount = Column(MONEY_TYPE, nullable=False)
    functional_tax_amount = Column(MONEY_TYPE, nullable=False)
    functional_total_amount = Column(MONEY_TYPE, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    reversal_of_ap_id = Column(String, ForeignKey("ap_invoices.id"), unique=True)
    reversed_by_ap_id = Column(String, ForeignKey("ap_invoices.id", deferrable=True, initially="DEFERRED"), unique=True)
    reversal_reason = Column(Text)
    posting_reference = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    posted_at = Column(DateTime)
    reversed_at = Column(DateTime)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)
    submitted_by = Column(String)
    approved_by = Column(String)
    posted_by = Column(String)
    reversed_by = Column(String)


Index("uq_active_ap_cost", APInvoice.cost_id, unique=True,
      sqlite_where=APInvoice.is_active.is_(True), postgresql_where=APInvoice.is_active.is_(True))


class APInvoiceLine(Base):
    __tablename__ = "ap_invoice_lines"
    __table_args__ = (CheckConstraint("tax_mode IN ('exclusive','inclusive','exempt')", name="ck_ap_line_tax_mode"),)
    id = Column(String, primary_key=True)
    ap_invoice_id = Column(String, ForeignKey("ap_invoices.id", ondelete="CASCADE"), nullable=False)
    charge_item_id = Column(String, ForeignKey("freight_charge_items.id"), nullable=False)
    charge_type = Column(String(32), nullable=False)
    description = Column(String(500))
    quantity = Column(QUANTITY_TYPE, nullable=False)
    unit_price = Column(MONEY_TYPE, nullable=False)
    currency_code = Column(String(3), nullable=False)
    tax_code = Column(String(50), nullable=False)
    tax_rate_snapshot = Column(RATE_TYPE, nullable=False)
    tax_mode = Column(String(20), nullable=False)
    account_mapping_key = Column(String(128), nullable=False)
    account_code_snapshot = Column(String)
    net_amount = Column(MONEY_TYPE, nullable=False)
    tax_amount = Column(MONEY_TYPE, nullable=False)
    total_amount = Column(MONEY_TYPE, nullable=False)
    rounding_adjustment = Column(MONEY_TYPE, nullable=False, default=0)


class FreightSettlement(Base):
    __tablename__ = "freight_settlements"
    __table_args__ = (
        CheckConstraint("status IN ('open','partially_paid','paid','reversed')", name="ck_freight_settlement_status"),
        CheckConstraint("version > 0", name="ck_freight_settlement_version"),
        CheckConstraint("approved_amount >= 0 AND paid_amount >= 0 AND remaining_amount >= 0", name="ck_freight_settlement_nonnegative"),
        CheckConstraint("paid_amount <= approved_amount", name="ck_freight_settlement_not_overpaid"),
    )
    id = Column(String, primary_key=True)
    ap_invoice_id = Column(String, ForeignKey("ap_invoices.id"), nullable=False, unique=True)
    settlement_period = Column(String(32), nullable=False)
    currency_code = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    functional_currency = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    approved_amount = Column(MONEY_TYPE, nullable=False)
    paid_amount = Column(MONEY_TYPE, nullable=False, default=0)
    remaining_amount = Column(MONEY_TYPE, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)


class SettlementPayment(Base):
    __tablename__ = "settlement_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_settlement_payment_positive"),
        CheckConstraint("status IN ('posted','reversed')", name="ck_settlement_payment_status"),
        CheckConstraint("reversal_of_payment_id IS NULL OR reversal_of_payment_id <> id", name="ck_settlement_payment_no_self_reversal"),
    )
    id = Column(String, primary_key=True)
    settlement_id = Column(String, ForeignKey("freight_settlements.id"), nullable=False)
    amount = Column(MONEY_TYPE, nullable=False)
    currency_code = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    functional_currency = Column(String(3), ForeignKey("currency_definitions.code"), nullable=False)
    exchange_rate_snapshot = Column(RATE_TYPE, nullable=False)
    exchange_rate_date = Column(Date, nullable=False)
    exchange_rate_source = Column(String(100), nullable=False)
    functional_amount = Column(MONEY_TYPE, nullable=False)
    posting_date = Column(Date, nullable=False)
    payment_method = Column(String(32), nullable=False)
    reference_no = Column(String(128))
    status = Column(String(20), nullable=False, default="posted")
    posting_reference = Column(String)
    reversal_of_payment_id = Column(String, ForeignKey("settlement_payments.id"), unique=True)
    reversed_by_payment_id = Column(String, ForeignKey("settlement_payments.id", deferrable=True, initially="DEFERRED"), unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=False)
    

FreightActualCost.items = relationship(FreightChargeItem, cascade="all, delete-orphan", back_populates="cost")
FreightActualCost.documents = relationship(FreightCostDocument, cascade="all, delete-orphan", back_populates="cost")
FreightChargeItem.cost = relationship(FreightActualCost, back_populates="items")
FreightCostDocument.cost = relationship(FreightActualCost, back_populates="documents")
APInvoice.lines = relationship(APInvoiceLine, cascade="all, delete-orphan", back_populates="invoice")
APInvoiceLine.invoice = relationship(APInvoice, back_populates="lines")
FreightSettlement.payments = relationship(SettlementPayment, cascade="all, delete-orphan", back_populates="settlement")
SettlementPayment.settlement = relationship(FreightSettlement, back_populates="payments")


class FreightOrderLegacyLink(Base):
    __tablename__ = "freight_order_legacy_links"
    freight_order_id = Column(String, ForeignKey("freight_orders.id"), primary_key=True)
    delivery_order_id = Column(String, ForeignKey("delivery_orders.id"), nullable=False, unique=True)
