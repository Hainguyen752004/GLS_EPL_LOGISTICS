import os
from database import engine, Base, SessionLocal
from models import Vehicle, Driver, Route, Customer, Quotation, SalesOrder, DeliveryOrder, ARInvoice, GLTransaction, VehicleType
from seed_guard import assert_demo_seed_allowed

def init_db():
    # Chốt trước mọi thao tác ghi: hàm này db.merge() các ID cố định nên sẽ
    # ghi đè dữ liệu thật nếu trỏ vào database production.
    assert_demo_seed_allowed()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(VehicleType).count() == 0:
            defaults = [
                VehicleType(id='VT-001', name='Container 20FT', icon='🚛', max_weight=15000, fuel_norm=28, base_rate=6250, maint_cost=3000000, dims='5.9m x 2.3m x 2.4m', fuel_type='Diesel', notes='Tải trọng tiêu chuẩn'),
                VehicleType(id='VT-002', name='Container 40FT', icon='🚚', max_weight=30000, fuel_norm=35, base_rate=9500, maint_cost=4500000, dims='12.1m x 2.3m x 2.4m', fuel_type='Diesel', notes='Tải trọng nặng'),
                VehicleType(id='VT-003', name='Xe Tải 10 Tấn', icon='🚛', max_weight=10000, fuel_norm=22, base_rate=4800, maint_cost=2000000, dims='7m x 2.2m x 2.4m', fuel_type='Diesel', notes='Chuyển phát nhanh đường dài'),
                VehicleType(id='VT-004', name='Container Lạnh', icon='❄️', max_weight=20000, fuel_norm=40, base_rate=11000, maint_cost=6000000, dims='12.1m x 2.3m x 2.4m', fuel_type='Diesel', special='Cần kiểm soát nhiệt độ', notes='Hàng đông lạnh bảo quản sâu')
            ]
            db.bulk_save_objects(defaults)
            db.commit()
            print("[Database Seed]: Created initial Vehicle Types in CSDL")

        cus_defaults = [
            Customer(id='CUS-001', name='Tập đoàn Điện máy Xanh', type='Account', contact_person='Nguyễn Văn Minh', phone='0908123456', address='KCN Sóng Thần 1, Dĩ An, Bình Dương'),
            Customer(id='CUS-002', name='Công ty TNHH Samsung Electronics', type='Account', contact_person='Trần Thị Kim', phone='0912345678', address='Khu Công Nghệ Cao, Q.9, TP.HCM'),
            Customer(id='CUS-003', name='Công ty CP Thực Phẩm Vissan', type='Account', contact_person='Lê Hoàng Nam', phone='0987654321', address='420 Nơ Trang Long, Bình Thạnh, TP.HCM'),
            Customer(id='CUS-004', name='Công ty TNHH Unilever Việt Nam', type='Account', contact_person='Phạm Văn Phú', phone='0909998877', address='KCN Tây Bắc Củ Chi, TP.HCM')
        ]
        for c in cus_defaults:
            db.merge(c)
        db.commit()
        print("[Database Seed]: Created initial Customers in CSDL")
    except Exception as e:
        db.rollback()
        print(f"[Database Seed Error]: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
