import datetime
import json
import os
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

os.environ.setdefault("EPL_ENV_FILE", r"D:\Demo_Lao\.env")
os.environ["DATABASE_MODE"] = "postgres"

from database import SessionLocal, auto_migrate_db  # noqa: E402
from models import (  # noqa: E402
    ARInvoice,
    ChartOfAccount,
    Currency,
    Customer,
    DeliveryOrder,
    DeliveryOrderDetail,
    Driver,
    GLTransaction,
    Item,
    Location,
    PriceList,
    Quotation,
    Route,
    SalesOrder,
    ShipmentCost,
    UOM,
    Vehicle,
    VehicleTracking,
    VehicleType,
)


def merge_all(db, rows):
    for row in rows:
        db.merge(row)


def main():
    auto_migrate_db()
    db = SessionLocal()
    try:
        today = datetime.date.today()
        eta = (datetime.datetime.now() + datetime.timedelta(hours=1, minutes=35)).strftime("%H:%M")

        db.query(DeliveryOrderDetail).filter(DeliveryOrderDetail.so_id == "DEMO-SO-2026-001").delete()
        db.query(ShipmentCost).filter(ShipmentCost.do_id == "DEMO-DO-2026-001").delete()

        route_segments = [
            {
                "from": "Kho VSIP II-A, Tân Uyên, Bình Dương",
                "to": "Nút giao Mỹ Phước - Tân Vạn",
                "distance": 14.2,
                "from_lat": 11.0497,
                "from_lng": 106.7428,
                "to_lat": 10.9694,
                "to_lng": 106.7436,
            },
            {
                "from": "Nút giao Mỹ Phước - Tân Vạn",
                "to": "Xa lộ Hà Nội / TP. Thủ Đức",
                "distance": 18.6,
                "from_lat": 10.9694,
                "from_lng": 106.7436,
                "to_lat": 10.8478,
                "to_lng": 106.7717,
            },
            {
                "from": "Xa lộ Hà Nội / TP. Thủ Đức",
                "to": "Cảng Cát Lái, TP. Thủ Đức",
                "distance": 11.9,
                "from_lat": 10.8478,
                "from_lng": 106.7717,
                "to_lat": 10.7756,
                "to_lng": 106.7899,
            },
        ]

        merge_all(
            db,
            [
                VehicleType(
                    id="DEMO-VT-20FT",
                    name="Container 20FT",
                    icon="🚛",
                    max_weight=28000,
                    volume_capacity_m3=33.2,
                    pallet_capacity=22,
                    fuel_norm=26,
                    base_rate=32000,
                    maint_cost=750000,
                    dims="6.06m x 2.44m x 2.59m",
                    fuel_type="Diesel",
                    special="Phù hợp hàng pallet, hàng xuất nhập khẩu cảng",
                    notes="Thông số tham khảo theo container 20 feet tiêu chuẩn ISO",
                ),
                VehicleType(
                    id="DEMO-VT-TRUCK10",
                    name="Xe tải thùng 10 tấn",
                    icon="🚚",
                    max_weight=10000,
                    volume_capacity_m3=45,
                    pallet_capacity=16,
                    fuel_norm=18,
                    base_rate=22000,
                    maint_cost=450000,
                    dims="9.5m x 2.35m x 2.4m",
                    fuel_type="Diesel",
                    special="Phù hợp giao hàng nội tỉnh/liên tỉnh gần",
                    notes="Cấu hình demo cho vận tải đường bộ",
                ),
                Vehicle(
                    id="DEMO-51C-268.89",
                    brand="Hyundai",
                    type="Container 20FT",
                    weight_capacity=28000,
                    volume_capacity_m3=33.2,
                    fuel_norm=26,
                    maintenance_date=str(today + datetime.timedelta(days=45)),
                    status="Đang vận chuyển (Giao đơn DEMO-DO-2026-001 - VSIP II-A → Cảng Cát Lái)",
                    engine_no="D6CA-DEMO-26889",
                    chassis_no="KMFXKS7BPDU26889",
                    insurance_date=str(today + datetime.timedelta(days=210)),
                    inspection_date=str(today - datetime.timedelta(days=35)),
                    inspection_place="Trung tâm Đăng kiểm 61-05D Bình Dương",
                    inspection_exp=str(today + datetime.timedelta(days=150)),
                    engine_cap="12.3 L / 410 HP",
                    dimensions="Đầu kéo + mooc 20FT",
                    image_url="",
                ),
                Vehicle(
                    id="DEMO-61H-112.34",
                    brand="Isuzu",
                    type="Xe tải thùng 10 tấn",
                    weight_capacity=10000,
                    volume_capacity_m3=45,
                    fuel_norm=18,
                    maintenance_date=str(today + datetime.timedelta(days=30)),
                    status="Sẵn sàng",
                    engine_no="6HK1-DEMO-11234",
                    chassis_no="JAANPR75HD7101234",
                    insurance_date=str(today + datetime.timedelta(days=180)),
                    inspection_date=str(today - datetime.timedelta(days=20)),
                    inspection_place="Trung tâm Đăng kiểm 50-03S TP.HCM",
                    inspection_exp=str(today + datetime.timedelta(days=165)),
                    engine_cap="7.8 L / 280 HP",
                    dimensions="9.5m x 2.35m x 2.4m",
                    image_url="",
                ),
                Driver(
                    id="DEMO-DRV-001",
                    name="Nguyễn Văn Minh",
                    role="Lái xe chính",
                    license_type="Hạng FC",
                    phone="0908.268.899",
                    assigned_vehicle="DEMO-51C-268.89",
                    shift="Ca ngày (06:00 - 18:00)",
                    status="🔴 Bận (Lái đơn DEMO-DO-2026-001 - VSIP II-A → Cảng Cát Lái)",
                ),
                Driver(
                    id="DEMO-DRV-002",
                    name="Trần Quốc Huy",
                    role="Phụ xe",
                    license_type="Hạng C",
                    phone="0912.112.340",
                    assigned_vehicle="DEMO-51C-268.89",
                    shift="Ca ngày (06:00 - 18:00)",
                    status="🔴 Bận (Phụ đơn DEMO-DO-2026-001 - VSIP II-A → Cảng Cát Lái)",
                ),
                Driver(
                    id="DEMO-DRV-003",
                    name="Lê Hoàng Nam",
                    role="Lái xe chính",
                    license_type="Hạng C",
                    phone="0938.667.771",
                    assigned_vehicle="Chưa gán",
                    shift="Ca sáng (06:00 - 14:00)",
                    status="🟢 Rảnh (Sẵn sàng)",
                ),
                Location(
                    id="DEMO-LOC-VSIP2A",
                    name="Kho VSIP II-A Bình Dương",
                    type="Warehouse",
                    address="KCN VSIP II-A, Tân Uyên, Bình Dương",
                    capacity=12000,
                ),
                Location(
                    id="DEMO-LOC-CATLAI",
                    name="Cảng Cát Lái",
                    type="Port",
                    address="Phường Cát Lái, TP. Thủ Đức, TP.HCM",
                    capacity=50000,
                ),
                Customer(
                    id="DEMO-CUS-SGNFOOD",
                    name="Công ty CP Thực Phẩm Sài Gòn Demo",
                    type="Account",
                    contact_person="Ms. Lan Anh",
                    phone="028.3821.2026",
                    address="KCN VSIP II-A, Bình Dương",
                ),
                Customer(
                    id="DEMO-VEN-CATLAI",
                    name="Cảng Cát Lái - Tổng Công Ty Tân Cảng Sài Gòn",
                    type="Vendor",
                    contact_person="Bộ phận giao nhận cổng cảng",
                    phone="028.3742.2345",
                    address="Cát Lái, TP. Thủ Đức, TP.HCM",
                ),
                Route(
                    id="DEMO-RT-VSIP2A-CATLAI",
                    name="VSIP II-A Bình Dương → Cảng Cát Lái",
                    distance_km=44.7,
                    segments_json=json.dumps(route_segments, ensure_ascii=False),
                ),
                Item(
                    id="DEMO-ITEM-PALLET",
                    name="Hàng tiêu dùng đóng pallet",
                    cargo_type="Pallet / FMCG",
                    default_uom="PALLET",
                    weight_kg=8500,
                ),
                UOM(id="PALLET", description="Pallet"),
                UOM(id="CBM", description="Mét khối"),
                UOM(id="TRIP", description="Chuyến"),
                Currency(id="VND", exchange_rate=1),
                Currency(id="USD", exchange_rate=25000),
                PriceList(
                    id="DEMO-PL-SGNFOOD-PALLET",
                    customer_id="DEMO-CUS-SGNFOOD",
                    item_id="DEMO-ITEM-PALLET",
                    unit_price=4200000,
                    valid_to=str(today + datetime.timedelta(days=90)),
                ),
                ChartOfAccount(account_code="131", account_name="Phải thu khách hàng", type="Asset"),
                ChartOfAccount(account_code="511", account_name="Doanh thu vận tải", type="Revenue"),
                ChartOfAccount(account_code="3331", account_name="Thuế GTGT phải nộp", type="Liability"),
            ],
        )
        db.commit()

        merge_all(
            db,
            [
                Quotation(
                    id="DEMO-QT-2026-001",
                    canonical_status="approved",
                    customer_id="DEMO-CUS-SGNFOOD",
                    route_id="DEMO-RT-VSIP2A-CATLAI",
                    cargo_type="Hàng tiêu dùng đóng pallet / Container 20FT",
                    valid_to=str(today + datetime.timedelta(days=14)),
                    fuel_cost=1162200,
                    driver_cost=650000,
                    toll_fee=320000,
                    total_cost=2132200,
                    selling_price=4200000,
                    packaging_spec="Pallet quấn màng PE",
                    volume_m3=24,
                    status="Đã duyệt",
                ),
                SalesOrder(
                    id="DEMO-SO-2026-001",
                    canonical_status="confirmed",
                    quotation_id="DEMO-QT-2026-001",
                    customer_id="DEMO-CUS-SGNFOOD",
                    origin="Kho VSIP II-A Bình Dương",
                    destination="Cảng Cát Lái, TP. Thủ Đức",
                    status="Đã xác nhận",
                    total_amount=4200000,
                    order_date=str(today),
                    delivery_date=str(today + datetime.timedelta(days=1)),
                    payment_terms="30 Days",
                    sales_rep="Demo Sales",
                    packaging_spec="Pallet quấn màng PE",
                    volume_m3=24,
                ),
            ],
        )
        db.commit()

        merge_all(
            db,
            [
                DeliveryOrder(
                    id="DEMO-DO-2026-001",
                    canonical_status="in_transit",
                    so_id="DEMO-SO-2026-001",
                    customer_id="DEMO-CUS-SGNFOOD",
                    route_id="DEMO-RT-VSIP2A-CATLAI",
                    vehicle_id="DEMO-51C-268.89",
                    driver_id="DEMO-DRV-001",
                    co_driver="DEMO-DRV-002",
                    status="Đang vận chuyển",
                    pickup_date=str(today),
                    delivery_date=str(today + datetime.timedelta(days=1)),
                    packaging_spec="Pallet quấn màng PE",
                    volume_m3=24,
                ),
                DeliveryOrderDetail(
                    so_id="DEMO-SO-2026-001",
                    sku="DEMO-FMCG-PALLET",
                    description="Hàng tiêu dùng đóng pallet giao cảng Cát Lái",
                    qty=18,
                    uom="PALLET",
                    unit_price=233333.33,
                    amount=4200000,
                    weight_kg=8500,
                ),
                ShipmentCost(
                    do_id="DEMO-DO-2026-001",
                    fuel_cost=1162200,
                    driver_cost=650000,
                    toll_fee=320000,
                    warehouse_fee=0,
                    total_cost=2132200,
                    selling_price=4200000,
                    margin_pct=49.23,
                ),
                VehicleTracking(
                    do_id="DEMO-DO-2026-001",
                    vehicle_id="DEMO-51C-268.89",
                    lat=10.8769,
                    lng=106.7734,
                    speed_kmh=48,
                    remaining_distance_km=18.6,
                    eta=eta,
                    last_update=datetime.datetime.utcnow(),
                ),
            ],
        )

        db.commit()

        counts = {}
        for model, name in [
            (VehicleType, "vehicle_types"),
            (Vehicle, "vehicles"),
            (Driver, "drivers"),
            (Route, "routes"),
            (Location, "locations"),
            (Customer, "customers"),
            (Quotation, "quotations"),
            (SalesOrder, "sales_orders"),
            (DeliveryOrder, "delivery_orders"),
            (VehicleTracking, "vehicle_tracking"),
        ]:
            counts[name] = db.query(model).count()

        print("Seed demo PostgreSQL master data completed.")
        for name, count in counts.items():
            print(f"{name}={count}")
        print("Demo tracking DO=DEMO-DO-2026-001")
    finally:
        db.close()


if __name__ == "__main__":
    main()
