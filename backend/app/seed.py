"""Gieo dữ liệu mẫu cho bản demo.

Đơn mẫu lấy NGUYÊN VĂN từ phiếu Purchase Order của CP ALL Laos mà chủ dự án đưa:
PO 6003990191, ba dòng bánh BISKIO, đơn giá 343.000 LAK, thành tiền 686.000 LAK.
Giữ đúng số của phiếu thật để người Lào mở lên là nhận ra ngay phiếu của họ.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, tao_luoc_do
from models import Customer, Driver, SalesOrder, SalesOrderLine, Vehicle


def _ma():
    return uuid.uuid4().hex[:12].upper()


KHACH = [
    {
        "code": "KHO-VTE",
        "name": "Kho Vientiane (Thà Bốc)",
        "kind": "depot",
        "address": "Ban Thabok, Vientiane Capital",
        "phone": "+856 21 000 000",
        "contact_name": "Kho xuất hàng",
        "lat": 17.9757,
        "lng": 102.6331,
    },
    {
        "code": "CPALL-LAOS",
        "name": "CP ALL Laos Co., Ltd.",
        "kind": "customer",
        "tax_number": "083753885-0-00",
        "address": "Souphaouvong Road, Xiengngeun Village, Sikhottabong District, Vientiane Capital",
        "phone": "+856 21 000 111",
        "contact_name": "7-Eleven Laos",
        "lat": 17.9660,
        "lng": 102.5870,
    },
    {
        "code": "KPA-TRADE",
        "name": "KPA Trade Import-Export Sole Co Ltd",
        "kind": "vendor",
        "tax_number": "2052891-31",
        "address": "Thatluang Tai Village, Xaysettha District, Vientiane Capital",
        "phone": "+856 20 555 222",
        "contact_name": "KPA Logistics",
        "lat": 17.9750,
        "lng": 102.6410,
    },
    {
        "code": "PTTLAO-DONEKOY",
        "name": "PTTLAO DONEKOY",
        "kind": "customer",
        "tax_number": "60039",
        "address": "Sisattanak, Vientiane Capital 00000",
        "phone": "+856 20 777 333",
        "contact_name": "Cửa hàng Donekoy",
        "lat": 17.9380,
        "lng": 102.6250,
    },
    {
        "code": "PTTLAO-SIKHAY",
        "name": "PTTLAO SIKHAY",
        "kind": "customer",
        "tax_number": "60041",
        "address": "Sikhay, Sikhottabong District, Vientiane Capital",
        "phone": "+856 20 888 444",
        "contact_name": "Cửa hàng Sikhay",
        "lat": 17.9790,
        "lng": 102.5720,
    },
]

XE = [
    {
        "plate_head": "ກທ 1234",
        "plate_trailer": "ກທ 5678",
        "internal_no": "341",
        "vehicle_type": "Container 20FT",
        "payload_kg": 20000,
        "cube_m3": 33.2,
    },
    {
        "plate_head": "ກທ 2468",
        "plate_trailer": "ກທ 1357",
        "internal_no": "342",
        "vehicle_type": "Container 40FT",
        "payload_kg": 30000,
        "cube_m3": 67,
    },
    {
        "plate_head": "ກທ 9090",
        "plate_trailer": None,
        "internal_no": "118",
        "vehicle_type": "Xe tải 10 tấn",
        "payload_kg": 10000,
        "cube_m3": 45,
    },
]

TAI_XE = [
    {"code": "DRV-001", "full_name": "Somsak Phommachanh", "phone": "+856 20 111 222", "licence_class": "FC"},
    {"code": "DRV-002", "full_name": "Bounma Sisouvong", "phone": "+856 20 333 444", "licence_class": "FC"},
    {"code": "DRV-003", "full_name": "Khamla Vongsa", "phone": "+856 20 555 666", "licence_class": "C"},
]

# Ba dòng của phiếu PO 6003990191 — số liệu giữ nguyên từ ảnh chụp phiếu thật.
DONG_PO = [
    {
        "line_no": 1,
        "barcode": "8858954206236",
        "product_code": "4111396",
        "description": "BISKIO ໄຂ່ໄດໂນປິສກິດຊັອກໂກແລັດ 15g_ຟ12",
        "description_en": "BISKIO DINO EGG SURPRISE Biscuit Chocolate 15g_P12",
        "vat_kind": "EXC",
        "vat_percent": 10.0,
        "pack_size": 12,
        "unit_quantity": "2CT",
        "case_qty": 24,
        "piece_qty": 288,
        "uom": "CT",
        "unit_price": 343000.0,
        "discount": 0.0,
        "amount": 686000.0,
        "weight_kg": 6.5,
        "cube_m3": 0.035,
    },
    {
        "line_no": 2,
        "barcode": "8858954214934",
        "product_code": "4111398",
        "description": "BISKIO ໄຂ່ຄູໂຣມິປິສກິດຊັອກໂກແລັດ 30g_ຟ12",
        "description_en": "BISKIO KUROMI EGG SURPRISE Biscuit Choco 30g_P12",
        "vat_kind": "EXC",
        "vat_percent": 10.0,
        "pack_size": 12,
        "unit_quantity": "2CT",
        "case_qty": 24,
        "piece_qty": 288,
        "uom": "CT",
        "unit_price": 343000.0,
        "discount": 0.0,
        "amount": 686000.0,
        "weight_kg": 9.2,
        "cube_m3": 0.042,
    },
    {
        "line_no": 3,
        "barcode": "8858954213524",
        "product_code": "4111400",
        "description": "BISKIO ໄຂ່ແຄຣແບປິສກິດຊັອກໂກແລັດ 30g_ຟ12",
        "description_en": "BISKIO CAR BEARS EGG SURPRISE Biscuit Choco 30g_P12",
        "vat_kind": "EXC",
        "vat_percent": 10.0,
        "pack_size": 12,
        "unit_quantity": "2CT",
        "case_qty": 24,
        "piece_qty": 288,
        "uom": "CT",
        "unit_price": 343000.0,
        "discount": 0.0,
        "amount": 686000.0,
        "weight_kg": 9.2,
        "cube_m3": 0.042,
    },
]


def gieo():
    tao_luoc_do()
    db = SessionLocal()
    try:
        for k in KHACH:
            co = db.query(Customer).filter(Customer.code == k["code"]).first()
            if co:
                # Cập nhật loại và toạ độ cho bản ghi gieo từ trước — không tạo trùng.
                for kh, gt in k.items():
                    setattr(co, kh, gt)
            else:
                db.add(Customer(id=_ma(), **k))
        for v in XE:
            if not db.query(Vehicle).filter(Vehicle.plate_head == v["plate_head"]).first():
                db.add(Vehicle(id=_ma(), **v))
        for t in TAI_XE:
            if not db.query(Driver).filter(Driver.code == t["code"]).first():
                db.add(Driver(id=_ma(), **t))
        db.flush()

        po = "6003990191"
        if db.query(SalesOrder).filter(SalesOrder.po_number == po).first():
            print("Đơn mẫu đã có, không gieo lại.")
            db.commit()
            return

        khach = db.query(Customer).filter(Customer.code == "PTTLAO-DONEKOY").first()
        don = SalesOrder(
            id="SO-2026-0001",
            po_number=po,
            order_date="2026-09-14",
            shipping_date="2026-09-17",
            customer_id=khach.id if khach else None,
            ship_to_code="60039",
            ship_to_name="PTTLAO DONEKOY",
            ship_to_address="Sisattanak, Vientiane Capital 00000",
            vendor_code="2052891-31",
            vendor_name="KPA Trade Import-Export Sole Co Ltd",
            vendor_address="Thatluang Tai Village, Xaysettha District, Vientiane Capital 00000",
            tax_number="083753885-0-00",
            currency="LAK",
            zone="L0",
            status="new",
            created_by="seed",
        )
        db.add(don)
        db.flush()
        for d in DONG_PO:
            db.add(SalesOrderLine(so_id=don.id, **d))
        db.commit()
        print(f"Đã gieo đơn mẫu {don.id} (PO {po}) với {len(DONG_PO)} dòng hàng.")
    finally:
        db.close()


if __name__ == "__main__":
    gieo()
