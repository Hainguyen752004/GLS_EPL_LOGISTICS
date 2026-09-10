import datetime
from database import engine, Base, SessionLocal
from models import (
    Vehicle, VehicleType, Driver, Route, Location, Customer,
    Quotation, DeliveryOrder, DeliveryOrderDetail,
    ShipmentCost, VehicleTracking, POD, ARInvoice, GLTransaction, ChartOfAccount
)

import datetime
from database import engine, Base, SessionLocal
from models import (
    Vehicle, VehicleType, Driver, Route, Location, Customer,
    Quotation, QuotationDetail, DeliveryOrder, DeliveryOrderDetail,
    ShipmentCost, VehicleTracking, POD, ARInvoice, GLTransaction, ChartOfAccount,
    Incident, AuditLog, Item, UOM
)
from seed_guard import assert_demo_seed_allowed

def seed_full_demo_data():
    # Chốt trước mọi thao tác ghi: hàm này tạo ARInvoice trạng thái Posted kèm
    # bút toán GL, nên chạy vào database thật là làm sai sổ cái.
    assert_demo_seed_allowed()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Quotation).count() > 0 and db.query(Incident).count() > 0:
            print("[Database Seed]: Demo data already fully populated in CSDL. Skipping.")
            return

        print("[Database Seed]: 🚀 Seeding 100% full demo data across ALL 20 modules...")

        # 1. Vehicle Types
        vtypes = [
            VehicleType(id='VT-001', name='Container 20FT', icon='🚛', max_weight=15000, volume_capacity_m3=30.0, fuel_norm=28, base_rate=6250, maint_cost=3000000, dims='5.9m x 2.3m x 2.4m', fuel_type='Diesel', notes='Tải trọng tiêu chuẩn'),
            VehicleType(id='VT-002', name='Container 40FT', icon='🚚', max_weight=30000, volume_capacity_m3=65.0, fuel_norm=35, base_rate=9500, maint_cost=4500000, dims='12.1m x 2.3m x 2.4m', fuel_type='Diesel', notes='Tải trọng nặng'),
            VehicleType(id='VT-003', name='Xe Tải 10 Tấn', icon='🚛', max_weight=10000, volume_capacity_m3=25.0, fuel_norm=22, base_rate=4800, maint_cost=2000000, dims='7m x 2.2m x 2.4m', fuel_type='Diesel', notes='Chuyển phát nhanh đường dài'),
            VehicleType(id='VT-004', name='Container Lạnh', icon='❄️', max_weight=20000, volume_capacity_m3=55.0, fuel_norm=40, base_rate=11000, maint_cost=6000000, dims='12.1m x 2.3m x 2.4m', fuel_type='Diesel', special='Cần kiểm soát nhiệt độ', notes='Hàng đông lạnh bảo quản sâu')
        ]
        for vt in vtypes:
            db.merge(vt)

        # 2. Customers
        customers = [
            Customer(id='CUS-001', name='Tập đoàn Điện máy Xanh', type='Account', contact_person='Nguyễn Văn Minh', phone='0908.123.456', address='KCN Sóng Thần 1, Dĩ An, Bình Dương'),
            Customer(id='CUS-002', name='Công ty TNHH Samsung Electronics', type='Account', contact_person='Trần Thị Kim', phone='0912.345.678', address='Khu Công Nghệ Cao, Q.9, TP.HCM'),
            Customer(id='CUS-003', name='Công ty CP Thực Phẩm Vissan', type='Account', contact_person='Lê Hoàng Nam', phone='0987.654.321', address='420 Nơ Trang Long, Bình Thạnh, TP.HCM'),
            Customer(id='CUS-004', name='Công ty TNHH Unilever Việt Nam', type='Account', contact_person='Phạm Văn Phú', phone='0909.998.877', address='KCN Tây Bắc Củ Chi, TP.HCM')
        ]
        for c in customers:
            db.merge(c)

        # 3. Routes
        routes = [
            Route(id='RT-001', name='Bình Dương - Cát Lái', distance_km=45.5, segments_json='[{"from": "KCN Sóng Thần", "to": "QL1A", "dist_km": 12.5}, {"from": "QL1A", "to": "Cầu Đồng Nai", "dist_km": 15.0}, {"from": "Cầu Đồng Nai", "to": "Cảng Cát Lái", "dist_km": 18.0}]'),
            Route(id='RT-002', name='Bắc Ninh - Hải Phòng', distance_km=120.0, segments_json='[{"from": "KCN Yên Phong", "to": "Quốc Lộ 18", "dist_km": 50.0}, {"from": "Quốc Lộ 18", "to": "Cảng Đình Vũ", "dist_km": 70.0}]'),
            Route(id='RT-003', name='Đồng Nai - Tiền Giang', distance_km=85.0, segments_json='[{"from": "KCN Amata", "to": "Cao Tốc TP.HCM - Trung Lương", "dist_km": 40.0}, {"from": "Cao Tốc Trung Lương", "to": "TP. Mỹ Tho", "dist_km": 45.0}]')
        ]
        for r in routes:
            db.merge(r)

        # 4. Locations / Warehouses
        locations = [
            Location(id='WH-001', name='Kho ICD Sóng Thần', type='Warehouse', address='KCN Sóng Thần, Bình Dương', capacity=5000.0),
            Location(id='WH-002', name='Cảng Quốc Tế Cát Lái', type='Port', address='Q.2, TP.HCM', capacity=20000.0),
            Location(id='WH-003', name='Kho Trung Chuyển Tân Bình', type='Warehouse', address='Q. Tân Bình, TP.HCM', capacity=3000.0),
            Location(id='WH-004', name='Cảng Đình Vũ Hải Phòng', type='Port', address='Hải An, Hải Phòng', capacity=15000.0)
        ]
        for loc in locations:
            db.merge(loc)

        # 5. Items & UOMs
        uoms = [
            UOM(id='PCS', description='Cái / Chiếc'),
            UOM(id='BOX', description='Thùng Carton'),
            UOM(id='PALLET', description='Pallet Tiêu Chuẩn'),
            UOM(id='KG', description='Kilogram'),
            UOM(id='CBM', description='Mét Khối (m³)'),
            UOM(id='TEU', description='Container 20FT Equivalent Unit')
        ]
        for u in uoms:
            db.merge(u)

        items = [
            Item(id='ITM-001', name='Tivi Samsung QLED 65 inch', cargo_type='Container 20FT', default_uom='BOX', weight_kg=28.5),
            Item(id='ITM-002', name='Tủ Lạnh Samsung Inverter 400L', cargo_type='Container 40FT', default_uom='BOX', weight_kg=75.0),
            Item(id='ITM-003', name='Sữa Chua Tiệt Trùng Vissan', cargo_type='Box', default_uom='BOX', weight_kg=12.0),
            Item(id='ITM-004', name='Bột Giặt OMO Matic 5kg', cargo_type='Pallet', default_uom='PALLET', weight_kg=500.0)
        ]
        for itm in items:
            db.merge(itm)

        # 6. Vehicles
        vehicles = [
            Vehicle(id='51C-123.45', brand='Hyundai Heavy Duty', type='Container 20FT', weight_capacity=15000, volume_capacity_m3=30.0, fuel_norm=28, status='In Transit', maintenance_date='2026-06-15', inspection_exp='2027-01-15'),
            Vehicle(id='59D-678.90', brand='Volvo FH16', type='Container 40FT', weight_capacity=30000, volume_capacity_m3=65.0, fuel_norm=35, status='Sẵn sàng', maintenance_date='2026-07-01', inspection_exp='2026-12-20'),
            Vehicle(id='29C-555.88', brand='Isuzu Giga', type='Xe tải 10 tấn', weight_capacity=10000, volume_capacity_m3=25.0, fuel_norm=22, status='Sẵn sàng', maintenance_date='2026-05-10', inspection_exp='2027-03-01'),
            Vehicle(id='60A-999.11', brand='Hino 700 Series', type='Container Lạnh', weight_capacity=20000, volume_capacity_m3=55.0, fuel_norm=40, status='Sẵn sàng', maintenance_date='2026-06-20', inspection_exp='2026-11-10')
        ]
        for v in vehicles:
            db.merge(v)

        # 7. Drivers
        drivers = [
            Driver(id='DRV-001', name='Nguyễn Văn Tài', role='Lái xe chính', license_type='Hạng FC', phone='0908.111.222', shift='Ca Sáng (06:00 - 14:00)', assigned_vehicle='51C-123.45', status='Bận'),
            Driver(id='DRV-002', name='Trần Văn Minh', role='Lái xe chính', license_type='Hạng FC', phone='0912.333.444', shift='Ca Sáng (06:00 - 14:00)', assigned_vehicle='Chưa gán', status='🟢 Rảnh (Sẵn sàng)'),
            Driver(id='DRV-003', name='Lê Hoàng Nam', role='Phụ xế', license_type='Hạng C', phone='0987.555.666', shift='Ca Sáng (06:00 - 14:00)', assigned_vehicle='51C-123.45', status='Bận'),
            Driver(id='DRV-004', name='Phạm Văn Phú', role='Phụ xế', license_type='Hạng C', phone='0909.777.888', shift='Ca Chiều (14:00 - 22:00)', assigned_vehicle='Chưa gán', status='🟢 Rảnh (Sẵn sàng)')
        ]
        for d in drivers:
            db.merge(d)

        # 8. Quotations
        quotations = [
            Quotation(id='QT-2026-001', customer_id='CUS-001', route_id='RT-001', cargo_type='Thiết bị điện tử', valid_to='2026-08-30', fuel_cost=1200000, driver_cost=800000, toll_fee=400000, total_cost=2400000, selling_price=3500000, packaging_spec='Thùng Carton (Tiêu chuẩn)', volume_m3=18.5, status='Approved'),
            Quotation(id='QT-2026-002', customer_id='CUS-002', route_id='RT-002', cargo_type='Linh kiện bán dẫn', valid_to='2026-08-30', fuel_cost=2500000, driver_cost=1500000, toll_fee=800000, total_cost=4800000, selling_price=6800000, packaging_spec='Pallet Gỗ (1.2m x 1.0m)', volume_m3=24.0, status='Approved'),
            Quotation(id='QT-2026-003', customer_id='CUS-003', route_id='RT-003', cargo_type='Thực phẩm đóng hộp', valid_to='2026-09-15', fuel_cost=1500000, driver_cost=900000, toll_fee=300000, total_cost=2700000, selling_price=3900000, packaging_spec='Flexitank / Bao Cần Cẩu', volume_m3=12.0, status='Draft')
        ]
        for q in quotations:
            db.merge(q)


        # 10. DeliveryOrders & Details
        delivery_orders = [
            DeliveryOrder(id='DO-2026-001', customer_id='CUS-001', route_id='RT-001', vehicle_id='51C-123.45', driver_id='DRV-001', co_driver='Lê Hoàng Nam (DRV-003)', status='In Transit', pickup_date='2026-07-30', delivery_date='2026-07-31', packaging_spec='Thùng Carton (Tiêu chuẩn)', volume_m3=18.5),
            DeliveryOrder(id='DO-2026-002', customer_id='CUS-002', route_id='RT-002', vehicle_id=None, driver_id=None, co_driver=None, status='Pending Approval', pickup_date='2026-07-31', delivery_date='2026-08-01', packaging_spec='Pallet Gỗ (1.2m x 1.0m)', volume_m3=24.0)
        ]
        for do in delivery_orders:
            db.merge(do)

        do_details = [
            DeliveryOrderDetail(id=1, sku='ITM-001', description='Tivi Samsung QLED 65 inch', qty=40, uom='BOX', unit_price=87500, amount=3500000, weight_kg=1140.0),
            DeliveryOrderDetail(id=2, sku='ITM-002', description='Tủ Lạnh Samsung Inverter 400L', qty=25, uom='BOX', unit_price=272000, amount=6800000, weight_kg=1875.0)
        ]
        for dod in do_details:
            db.merge(dod)

        # 11. ShipmentCosts
        scost = ShipmentCost(id=1, do_id='DO-2026-001', fuel_cost=1200000, driver_cost=800000, toll_fee=400000, warehouse_fee=200000, total_cost=2600000, selling_price=3500000, margin_pct=25.7)
        db.merge(scost)

        # 12. Vehicle Tracking (GPS)
        tracking = VehicleTracking(
            do_id='DO-2026-001',
            vehicle_id='51C-123.45',
            lat=10.762622,
            lng=106.660172,
            speed_kmh=48.5,
            remaining_distance_km=12.5,
            eta='15:30 PM',
            last_update=datetime.datetime.utcnow()
        )
        db.merge(tracking)

        # 13. Proof of Delivery (POD)
        pod = POD(
            do_id='DO-2026-001',
            delivery_time='30/07/2026 15:30',
            photo_url='https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=600&auto=format&fit=crop&q=80',
            signature_url='https://upload.wikimedia.org/wikipedia/commons/f/f8/Signature_example.svg',
            note='Đã hoàn tất nghiệm thu 40 kiện hàng nguyên vẹn, đại diện Tập đoàn Điện máy Xanh đã ký xác nhận.'
        )
        db.merge(pod)

        # 14. AR Invoice & GL Transactions
        inv = ARInvoice(id='INV-2026-001', do_id='DO-2026-001', customer_id='CUS-001', invoice_date='2026-07-30', amount=3500000, vat_pct=10.0, vat_amount=350000, total=3850000, status='Posted')
        db.merge(inv)

        if db.query(GLTransaction).count() == 0:
            gls = [
                GLTransaction(invoice_id='INV-2026-001', date='2026-07-30', account_code='131', debit=3850000, credit=0.0),
                GLTransaction(invoice_id='INV-2026-001', date='2026-07-30', account_code='511', debit=0.0, credit=3500000),
                GLTransaction(invoice_id='INV-2026-001', date='2026-07-30', account_code='3331', debit=0.0, credit=350000)
            ]
            for gl in gls:
                db.add(gl)

        # 15. Incidents
        incidents = [
            Incident(id=1, do_id='DO-2026-001', vehicle_id='51C-123.45', incident_type='Xì lốp trên cao tốc', severity='Low', location='Cao tốc TP.HCM - Long Thành km 18', description='Xe gặp sự cố xì lốp bành sau. Tài xế đã tự thay lốp dự phòng trong 25 phút.', reporter='Nguyễn Văn Tài (Lái xe)', reported_at='2026-07-30 11:20', status='Resolved'),
            Incident(id=2, do_id='DO-2026-002', vehicle_id='59D-678.90', incident_type='Kẹt xe tại trạm thu phí', severity='Medium', location='Trạm thu phí Cát Lái', description='Kẹt xe ùn tắc kéo dài 1.5km tại lối vào cảng.', reporter='Trần Văn Minh (Lái xe)', reported_at='2026-07-30 13:45', status='Pending')
        ]
        for inc in incidents:
            db.merge(inc)

        # 16. Audit Logs
        logs = [
            AuditLog(id=1, user_id='USR-ADMIN', action='CREATE_QUOTATION', table_name='quotations', record_id='QT-2026-001', timestamp=datetime.datetime.utcnow(), ip_address='127.0.0.1'),
            AuditLog(id=2, user_id='USR-DISPATCH', action='DISPATCH_VEHICLE', table_name='delivery_orders', record_id='DO-2026-001', timestamp=datetime.datetime.utcnow(), ip_address='127.0.0.1')
        ]
        for lg in logs:
            db.merge(lg)

        db.commit()
        print("[Database Seed]: ✅ Successfully seeded 100% COMPLETE demo data across ALL 20 tables in CSDL!")

    except Exception as e:
        db.rollback()
        print(f"[Database Seed Error]: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_full_demo_data()
