"""Mô hình dữ liệu của bản demo Packing List.

Luồng của bản demo, đọc từ trên xuống:

    Đơn hàng khách (SO)  ->  nhiều Packing List  ->  một chuyến giao hàng

Điều quan trọng nhất của bản demo này: **mỗi mặt hàng nằm trong một Packing List
phải truy ngược được về đúng dòng hàng của đúng SO**. Người giao hàng cầm một
kiện lên là phải trả lời được "kiện này thuộc SO nào, Packing List nào, dòng hàng
nào". Vì vậy `PackingListItem.so_line_id` là khoá bắt buộc, không cho rỗng.
"""

import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def _bay_gio():
    return datetime.datetime.utcnow()


def _ma_moi():
    return uuid.uuid4().hex.upper()


# --------------------------------------------------------------------------
# Danh mục nền
# --------------------------------------------------------------------------
class Customer(Base):
    """Khách hàng — bên đặt hàng, cũng là bên nhận hàng trong bản demo."""

    __tablename__ = "customers"
    id = Column(String(64), primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    tax_number = Column(String(64))
    address = Column(String(500))
    phone = Column(String(64))
    contact_name = Column(String(255))
    # customer = khách nhận hàng · vendor = nhà cung cấp · depot = kho xuất hàng của mình
    kind = Column(String(16), nullable=False, default="customer")
    # Toạ độ điểm giao, để màn Theo dõi vẽ được đường xe đi và biết còn bao xa.
    lat = Column(Float)
    lng = Column(Float)
    note = Column(Text)
    created_at = Column(DateTime, nullable=False, default=_bay_gio)
    updated_at = Column(DateTime, nullable=False, default=_bay_gio, onupdate=_bay_gio)


class Vehicle(Base):
    """Xe. Xe container ở Lào có hai biển: biển đầu kéo và biển thùng."""

    __tablename__ = "vehicles"
    id = Column(String(64), primary_key=True)
    plate_head = Column(String(64), nullable=False)
    plate_trailer = Column(String(64))
    internal_no = Column(String(32))
    vehicle_type = Column(String(64))
    payload_kg = Column(Float, nullable=False, default=0)
    cube_m3 = Column(Float, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="available")
    created_at = Column(DateTime, nullable=False, default=_bay_gio)


class Route(Base):
    """Tuyến giao hàng: đi từ kho nào, tới điểm giao nào, dài bao nhiêu km.

    Trước đây "tuyến" chỉ là một ô gõ tay trên phiếu đóng gói — ai không gõ thì
    phiếu in ra để trống, và màn Theo dõi không biết vẽ đường từ đâu tới đâu.
    Thành một danh mục thì khai một lần rồi mọi phiếu chọn lại, và bản đồ có
    điểm đầu điểm cuối thật.
    """

    __tablename__ = "routes"
    id = Column(String(64), primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    from_id = Column(String(64), ForeignKey("customers.id"), nullable=True)
    to_id = Column(String(64), ForeignKey("customers.id"), nullable=True)
    distance_km = Column(Float, nullable=False, default=0)
    note = Column(Text)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=_bay_gio)
    updated_at = Column(DateTime, nullable=False, default=_bay_gio, onupdate=_bay_gio)

    segments = relationship(
        "RouteSegment",
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteSegment.seq",
    )


class RouteSegment(Base):
    """Một CHẶNG của tuyến: đi từ đâu tới đâu, bao nhiêu km.

    Tuyến thật hiếm khi là một đường thẳng kho → cửa hàng; nó đi qua mấy chặng
    A → B → C. Tách chặng ra thì tổng km là tổng các chặng (không ai gõ tay một
    con số rồi quên cập nhật), và bản đồ vẽ được đúng lộ trình chứ không phải
    một đoạn thẳng nối hai đầu.

    `from_id` / `to_id` trỏ vào danh mục địa điểm để có toạ độ; ai gõ một địa
    điểm chưa có trong danh mục thì vẫn lưu được bằng `from_name` / `to_name`,
    chỉ là chặng đó không hiện trên bản đồ.
    """

    __tablename__ = "route_segments"
    __table_args__ = (
        UniqueConstraint("route_id", "seq", name="uq_route_segment_seq"),
        CheckConstraint("distance_km >= 0", name="ck_route_segment_km"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(64), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, nullable=False, default=1)
    from_id = Column(String(64), ForeignKey("customers.id"), nullable=True)
    to_id = Column(String(64), ForeignKey("customers.id"), nullable=True)
    from_name = Column(String(255), nullable=False)
    to_name = Column(String(255), nullable=False)
    distance_km = Column(Float, nullable=False, default=0)

    route = relationship("Route", back_populates="segments")


class Driver(Base):
    __tablename__ = "drivers"
    id = Column(String(64), primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(64))
    licence_class = Column(String(32))
    status = Column(String(32), nullable=False, default="available")
    created_at = Column(DateTime, nullable=False, default=_bay_gio)


# --------------------------------------------------------------------------
# Đơn hàng của khách (Sale Order)
# --------------------------------------------------------------------------
class SalesOrder(Base):
    __tablename__ = "sales_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','packing','packed','delivering','delivered','cancelled')",
            name="ck_so_status",
        ),
        Index("ix_so_status_created", "status", "created_at"),
    )
    id = Column(String(64), primary_key=True)
    po_number = Column(String(64), nullable=False, unique=True)
    order_date = Column(String(32))
    shipping_date = Column(String(32))

    customer_id = Column(String(64), ForeignKey("customers.id"), nullable=True)
    ship_to_code = Column(String(64))
    ship_to_name = Column(String(255))
    ship_to_address = Column(String(500))

    vendor_code = Column(String(64))
    vendor_name = Column(String(255))
    vendor_address = Column(String(500))
    tax_number = Column(String(64))

    currency = Column(String(8), nullable=False, default="LAK")
    zone = Column(String(32))
    note = Column(Text)
    status = Column(String(20), nullable=False, default="new")

    created_at = Column(DateTime, nullable=False, default=_bay_gio)
    updated_at = Column(DateTime, nullable=False, default=_bay_gio, onupdate=_bay_gio)
    created_by = Column(String(128), nullable=False, default="system")

    lines = relationship(
        "SalesOrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="SalesOrderLine.line_no",
    )
    packing_lists = relationship("PackingList", back_populates="order")


class SalesOrderLine(Base):
    """Một dòng hàng trên đơn — đúng một dòng của phiếu Purchase Order."""

    __tablename__ = "sales_order_lines"
    __table_args__ = (
        UniqueConstraint("so_id", "line_no", name="uq_so_line_no"),
        CheckConstraint("case_qty >= 0 AND piece_qty >= 0", name="ck_so_line_qty"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    so_id = Column(String(64), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False)

    barcode = Column(String(64))
    product_code = Column(String(64))
    description = Column(String(500), nullable=False)
    description_en = Column(String(500))

    vat_kind = Column(String(8))       # INC / EXC / NON
    vat_percent = Column(Float, nullable=False, default=0)
    pack_size = Column(Integer, nullable=False, default=1)
    unit_quantity = Column(String(32))  # ví dụ "2CT"

    case_qty = Column(Integer, nullable=False, default=0)   # số thùng đặt
    piece_qty = Column(Integer, nullable=False, default=0)  # số cái đặt
    uom = Column(String(32), nullable=False, default="CT")

    unit_price = Column(Float, nullable=False, default=0)
    discount = Column(Float, nullable=False, default=0)
    amount = Column(Float, nullable=False, default=0)

    weight_kg = Column(Float, nullable=False, default=0)   # trọng lượng MỘT thùng
    cube_m3 = Column(Float, nullable=False, default=0)     # thể tích MỘT thùng

    order = relationship("SalesOrder", back_populates="lines")
    packed_items = relationship("PackingListItem", back_populates="so_line")


# --------------------------------------------------------------------------
# Packing List
# --------------------------------------------------------------------------
TRANG_THAI_PL = (
    "ready",       # sẵn sàng in tem
    "parked",      # đã vào bãi chờ
    "gate_in",     # đã qua cổng
    "loaded",      # đã bốc lên xe
    "dispatched",  # đã xuất bãi
    "delivered",   # đã giao
    "cancelled",
)


class PackingList(Base):
    __tablename__ = "packing_lists"
    __table_args__ = (
        UniqueConstraint("so_id", "seq", name="uq_pl_so_seq"),
        CheckConstraint(
            "status IN ('ready','parked','gate_in','loaded','dispatched','delivered','cancelled')",
            name="ck_pl_status",
        ),
        Index("ix_pl_status_created", "status", "created_at"),
    )
    id = Column(String(64), primary_key=True)
    so_id = Column(String(64), ForeignKey("sales_orders.id"), nullable=False, index=True)
    seq = Column(Integer, nullable=False, default=1)
    delivery_id = Column(String(64), ForeignKey("deliveries.id"), nullable=True, index=True)

    store_code = Column(String(64))
    store_name = Column(String(255))
    route_id = Column(String(64), ForeignKey("routes.id"), nullable=True)
    route_name = Column(String(500))
    wave = Column(String(32))
    gate = Column(String(32))

    box_count = Column(Integer, nullable=False, default=1)
    total_cases = Column(Integer, nullable=False, default=0)
    total_pieces = Column(Integer, nullable=False, default=0)
    total_weight_kg = Column(Float, nullable=False, default=0)
    total_cube_m3 = Column(Float, nullable=False, default=0)

    status = Column(String(20), nullable=False, default="ready")
    note = Column(Text)

    created_at = Column(DateTime, nullable=False, default=_bay_gio)
    updated_at = Column(DateTime, nullable=False, default=_bay_gio, onupdate=_bay_gio)
    created_by = Column(String(128), nullable=False, default="system")

    order = relationship("SalesOrder", back_populates="packing_lists")
    delivery = relationship("Delivery", back_populates="packing_lists")
    items = relationship(
        "PackingListItem",
        back_populates="packing_list",
        cascade="all, delete-orphan",
        order_by="PackingListItem.id",
    )
    labels = relationship(
        "PackingLabel",
        back_populates="packing_list",
        cascade="all, delete-orphan",
        order_by="PackingLabel.package_no",
    )
    events = relationship(
        "PackingEvent",
        back_populates="packing_list",
        cascade="all, delete-orphan",
        order_by="PackingEvent.id",
    )
    pod = relationship(
        "PackingListPOD",
        back_populates="packing_list",
        cascade="all, delete-orphan",
        uselist=False,
    )


class PackingListItem(Base):
    """Một dòng hàng ĐÃ ĐÓNG vào Packing List.

    `so_line_id` KHÔNG ĐƯỢC RỖNG. Đây là sợi dây giúp người giao hàng truy ngược
    từ một kiện về đúng dòng hàng của đúng đơn — yêu cầu gốc của bản demo.
    """

    __tablename__ = "packing_list_items"
    __table_args__ = (
        CheckConstraint("case_qty >= 0 AND piece_qty >= 0", name="ck_pl_item_qty"),
        CheckConstraint("case_qty + piece_qty > 0", name="ck_pl_item_not_empty"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(
        String(64), ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    so_line_id = Column(
        Integer, ForeignKey("sales_order_lines.id"), nullable=False, index=True
    )

    barcode = Column(String(64))
    product_code = Column(String(64))
    description = Column(String(500))
    description_en = Column(String(500))

    case_qty = Column(Integer, nullable=False, default=0)
    piece_qty = Column(Integer, nullable=False, default=0)
    uom = Column(String(32))
    weight_kg = Column(Float, nullable=False, default=0)
    cube_m3 = Column(Float, nullable=False, default=0)
    note = Column(Text)

    packing_list = relationship("PackingList", back_populates="items")
    so_line = relationship("SalesOrderLine", back_populates="packed_items")


class PackingLabel(Base):
    """Tem QR dán lên từng kiện của một Packing List."""

    __tablename__ = "packing_labels"
    __table_args__ = (
        UniqueConstraint("packing_list_id", "package_no", name="uq_pl_label_package"),
        UniqueConstraint("qr_token", name="uq_pl_label_token"),
    )
    id = Column(String(64), primary_key=True, default=_ma_moi)
    packing_list_id = Column(
        String(64), ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_no = Column(Integer, nullable=False)
    package_total = Column(Integer, nullable=False)
    qr_token = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="ready")
    printed_at = Column(DateTime)
    reprint_count = Column(Integer, nullable=False, default=0)
    scanned_at = Column(DateTime)

    packing_list = relationship("PackingList", back_populates="labels")


class PackingEvent(Base):
    __tablename__ = "packing_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(
        String(64), ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = Column(String(32), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=_bay_gio)
    actor = Column(String(128), nullable=False, default="system")
    note = Column(Text)

    packing_list = relationship("PackingList", back_populates="events")


# --------------------------------------------------------------------------
# Giao hàng
# --------------------------------------------------------------------------
class Delivery(Base):
    """Một chuyến giao hàng chở nhiều Packing List.

    Cắt gọn từ core của EPL_System: giữ xe, tài xế, mốc thời gian và trạng thái;
    bỏ điều phối, tính giá thành, công thức và sắp ca — bản demo không cần.
    """

    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned','loading','in_transit','arrived','delivered','cancelled')",
            name="ck_delivery_status",
        ),
    )
    id = Column(String(64), primary_key=True)
    code = Column(String(64), nullable=False, unique=True)
    vehicle_id = Column(String(64), ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(String(64), ForeignKey("drivers.id"), nullable=True)

    plate_head = Column(String(64))
    plate_trailer = Column(String(64))
    driver_name = Column(String(255))
    driver_phone = Column(String(64))

    route_name = Column(String(500))
    planned_depart_at = Column(DateTime)
    departed_at = Column(DateTime)
    arrived_at = Column(DateTime)
    completed_at = Column(DateTime)

    status = Column(String(20), nullable=False, default="planned")
    note = Column(Text)

    created_at = Column(DateTime, nullable=False, default=_bay_gio)
    updated_at = Column(DateTime, nullable=False, default=_bay_gio, onupdate=_bay_gio)

    packing_lists = relationship("PackingList", back_populates="delivery")
    events = relationship(
        "DeliveryEvent",
        back_populates="delivery",
        cascade="all, delete-orphan",
        order_by="DeliveryEvent.id",
    )


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(
        String(64), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = Column(String(32), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=_bay_gio)
    actor = Column(String(128), nullable=False, default="system")
    note = Column(Text)

    delivery = relationship("Delivery", back_populates="events")


class PackingListPOD(Base):
    """Bằng chứng giao hàng của MỘT Packing List.

    Ghi theo từng Packing List chứ không theo cả chuyến: một chuyến chở hàng của
    nhiều đơn, người nhận mỗi nơi một khác, nên gộp vào chuyến là mất dấu ai đã
    ký nhận cái gì.
    """

    __tablename__ = "packing_list_pod"
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_list_id = Column(
        String(64), ForeignKey("packing_lists.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    delivery_id = Column(String(64), ForeignKey("deliveries.id"), nullable=True)
    received_by = Column(String(255))
    received_at = Column(DateTime, nullable=False, default=_bay_gio)
    result = Column(String(32), nullable=False, default="full")  # full / short / failed / returned
    goods_condition = Column(String(255))
    note = Column(Text)
    signature_data = Column(Text)

    packing_list = relationship("PackingList", back_populates="pod")


# --------------------------------------------------------------------------
# Theo dõi xe
# --------------------------------------------------------------------------
class VehiclePosition(Base):
    """Một mốc GPS của MỘT chuyến giao hàng.

    Ghi theo chuyến chứ không theo xe: câu người dùng hỏi là "hàng của đơn này
    đang ở đâu", và đơn gắn với chuyến. Mốc mới nhất của mỗi chuyến là vị trí
    hiện tại; toàn bộ mốc là vệt đường xe đã đi.
    """

    __tablename__ = "vehicle_positions"
    __table_args__ = (Index("ix_vpos_delivery_time", "delivery_id", "recorded_at"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(
        String(64), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    speed_kmh = Column(Float, nullable=False, default=0)
    heading = Column(Float)
    progress = Column(Float, nullable=False, default=0)   # 0..1 dọc tuyến, để mô phỏng chạy tiếp
    source = Column(String(32), nullable=False, default="manual")  # manual / gps / simulated
    note = Column(String(255))
    recorded_at = Column(DateTime, nullable=False, default=_bay_gio)


# --------------------------------------------------------------------------
# Nhận đơn tự động từ email
# --------------------------------------------------------------------------
class InboundOrder(Base):
    """Một phiếu đặt hàng KHÁCH GỬI TỚI, chưa phải đơn hàng thật.

    Đây cố ý là bảng riêng chứ không ghi thẳng vào `sales_orders`. Máy đọc phiếu
    bằng AI thì có lúc đọc sai, mà một đơn sai chui được vào luồng đóng gói là
    hàng ra khỏi kho sai. Nên mọi thứ máy đọc ra nằm ở đây dưới dạng BẢN NHÁP,
    có người mở tệp gốc ra đối chiếu, sửa lại rồi mới bấm duyệt; lúc duyệt mới
    sinh SalesOrder thật.

    Tệp gốc lưu luôn trong `file_data` để người duyệt còn mở ra soi. Bản demo
    chạy một máy nên để trong DB là đủ và không sợ lạc tệp.
    """

    __tablename__ = "inbound_orders"
    id = Column(String(64), primary_key=True, default=lambda: "IB" + uuid.uuid4().hex[:10].upper())

    source = Column(String(16), nullable=False, default="upload")   # gmail / upload
    message_id = Column(String(255), unique=True)                   # chống nhận trùng một email
    from_email = Column(String(255))
    subject = Column(String(500))
    body_text = Column(Text)
    received_at = Column(DateTime, nullable=False, default=_bay_gio)

    file_name = Column(String(255))
    file_mime = Column(String(128))
    file_size = Column(Integer, nullable=False, default=0)
    file_data = Column(Text)                                        # base64 của tệp gốc

    # new: vừa nhận, chưa đọc · parsed: AI đọc xong, chờ duyệt
    # failed: đọc không ra · approved: đã thành đơn thật · rejected: người duyệt bỏ
    status = Column(String(16), nullable=False, default="new", index=True)
    ai_confidence = Column(Integer, nullable=False, default=0)
    ai_warnings = Column(Text)                                      # JSON mảng chuỗi
    ai_error = Column(String(500))
    draft = Column(Text)                                            # JSON bản nháp đơn hàng

    so_id = Column(String(64), ForeignKey("sales_orders.id"), nullable=True)
    reviewed_by = Column(String(128))
    reviewed_at = Column(DateTime)
    note = Column(Text)
    created_at = Column(DateTime, nullable=False, default=_bay_gio)
    updated_at = Column(DateTime, nullable=False, default=_bay_gio, onupdate=_bay_gio)

    sales_order = relationship("SalesOrder")
