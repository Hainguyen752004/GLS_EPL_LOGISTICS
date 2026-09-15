"""Dọn dữ liệu rác của bài kiểm rồi gieo một bộ demo đi được trọn luồng.

Sau khi chạy, mở trang lên là đã có sẵn:
  · một đơn CHƯA đóng gì   → để bấm thử đóng gói từ đầu;
  · một đơn ĐANG đóng dở   → để thấy cột "còn lại" hoạt động;
  · một đơn ĐÃ lên chuyến và đang trên đường → để thử quét tem và ký nhận.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, tao_luoc_do
from models import (
    Customer,
    Delivery,
    DeliveryEvent,
    Driver,
    PackingEvent,
    PackingLabel,
    PackingList,
    PackingListItem,
    PackingListPOD,
    SalesOrder,
    SalesOrderLine,
    Vehicle,
)
from services import don_hang_service, giao_hang_service, packing_service, theo_doi_service
import seed

NGUOI = "demo"

HANG = [
    ("8858954206236", "4111396", "BISKIO ໄຂ່ໄດໂນປິສກິດຊັອກໂກແລັດ 15g_ຟ12",
     "BISKIO DINO EGG SURPRISE Biscuit Chocolate 15g_P12", 6.5, 0.035),
    ("8858954214934", "4111398", "BISKIO ໄຂ່ຄູໂຣມິປິສກິດຊັອກໂກແລັດ 30g_ຟ12",
     "BISKIO KUROMI EGG SURPRISE Biscuit Choco 30g_P12", 9.2, 0.042),
    ("8858954213524", "4111400", "BISKIO ໄຂ່ແຄຣແບປິສກິດຊັອກໂກແລັດ 30g_ຟ12",
     "BISKIO CAR BEARS EGG SURPRISE Biscuit Choco 30g_P12", 9.2, 0.042),
    ("8850987123456", "4222100", "ນ້ຳດື່ມ ຂວດ 600ml_ຟ24",
     "Drinking water 600ml bottle_P24", 14.4, 0.028),
]


def _dong(i, thung):
    ma_vach, ma_hang, mo_ta, mo_ta_en, kg, m3 = HANG[i]
    return {
        "line_no": i + 1,
        "barcode": ma_vach,
        "product_code": ma_hang,
        "description": mo_ta,
        "description_en": mo_ta_en,
        "vat_kind": "EXC",
        "vat_percent": 10,
        "pack_size": 12,
        "unit_quantity": "2CT",
        "case_qty": thung,
        "piece_qty": thung * 12,
        "uom": "CT",
        "unit_price": 343000,
        "discount": 0,
        "amount": 343000 * thung,
        "weight_kg": kg,
        "cube_m3": m3,
    }


def don_sach(db):
    """Xoá dữ liệu do bài kiểm sinh ra. Chỉ đụng vào PO có tiền tố của bài kiểm."""
    xoa = (
        db.query(SalesOrder)
        .filter(SalesOrder.po_number.like("KIEM-%") | SalesOrder.po_number.like("HTTP-%"))
        .all()
    )
    for don in xoa:
        for pl in db.query(PackingList).filter(PackingList.so_id == don.id).all():
            db.query(PackingListPOD).filter(PackingListPOD.packing_list_id == pl.id).delete()
            db.query(PackingEvent).filter(PackingEvent.packing_list_id == pl.id).delete()
            db.query(PackingLabel).filter(PackingLabel.packing_list_id == pl.id).delete()
            db.query(PackingListItem).filter(PackingListItem.packing_list_id == pl.id).delete()
            gh_id = pl.delivery_id
            db.delete(pl)
            if gh_id:
                db.flush()
                con = db.query(PackingList).filter(PackingList.delivery_id == gh_id).count()
                if con == 0:
                    db.query(DeliveryEvent).filter(DeliveryEvent.delivery_id == gh_id).delete()
                    gh = db.query(Delivery).filter(Delivery.id == gh_id).first()
                    if gh:
                        db.delete(gh)
        db.query(SalesOrderLine).filter(SalesOrderLine.so_id == don.id).delete()
        db.delete(don)
    db.commit()
    return len(xoa)


def _tao_don(db, po, ship_to, ship_code, dong):
    co = db.query(SalesOrder).filter(SalesOrder.po_number == po).first()
    if co:
        return co
    khach = db.query(Customer).filter(Customer.code == ship_code).first()
    ncc = db.query(Customer).filter(Customer.code == "KPA-TRADE").first()
    return don_hang_service.tao(
        db,
        {
            "po_number": po,
            "order_date": "2026-09-14",
            "shipping_date": "2026-09-17",
            "customer_id": khach.id if khach else None,
            "vendor_id": ncc.id if ncc else None,
            "tax_number": "083753885-0-00",
            "currency": "LAK",
            "zone": "L0",
            "lines": dong,
        },
        NGUOI,
    )


def gieo():
    tao_luoc_do()
    seed.gieo()

    db = SessionLocal()
    try:
        bo = don_sach(db)
        if bo:
            print(f"Đã dọn {bo} đơn rác của bài kiểm.")

        # Đơn gieo từ trước khi có danh mục thì chưa gắn customer_id. Gắn lại theo
        # mã hoặc tên điểm giao, để màn Theo dõi biết điểm đến của chuyến.
        for don in db.query(SalesOrder).filter(SalesOrder.customer_id.is_(None)).all():
            kh = (
                db.query(Customer).filter(Customer.code == (don.ship_to_code or "")).first()
                or db.query(Customer).filter(Customer.name == (don.ship_to_name or "")).first()
                or db.query(Customer).filter(Customer.tax_number == (don.ship_to_code or "")).first()
            )
            if kh:
                don.customer_id = kh.id
                don.ship_to_code = kh.code
                don.ship_to_address = don.ship_to_address or kh.address
        db.commit()

        # 1) Đơn chưa đóng gì — chính là phiếu PO thật đã gieo ở seed.py
        print("Đơn 1 (chưa đóng): SO-2026-0001 / PO 6003990191")

        # 2) Đơn đang đóng dở
        d2 = _tao_don(db, "6003990192", "PTTLAO SIKHAY", "PTTLAO-SIKHAY",
                      [_dong(0, 20), _dong(1, 12), _dong(3, 30)])
        db.commit()
        if not db.query(PackingList).filter(PackingList.so_id == d2.id).count():
            d2 = don_hang_service.nap(db, d2.id)
            packing_service.tao(
                db, d2.id,
                {
                    "items": [
                        {"so_line_id": d2.lines[0].id, "case_qty": 8, "piece_qty": 96},
                        {"so_line_id": d2.lines[2].id, "case_qty": 10, "piece_qty": 120},
                    ],
                    "box_count": 18,
                    "route_name": "Kho Vientiane → PTTLAO SIKHAY",
                    "wave": "W1",
                    "gate": "B",
                },
                NGUOI,
            )
            db.commit()
        print(f"Đơn 2 (đóng dở): {d2.id} / PO 6003990192")

        # 3) Đơn đã đóng đủ, đã lên chuyến và đang trên đường
        d3 = _tao_don(db, "6003990193", "PTTLAO DONEKOY", "PTTLAO-DONEKOY",
                      [_dong(1, 10), _dong(2, 10)])
        db.commit()
        if not db.query(PackingList).filter(PackingList.so_id == d3.id).count():
            packing_service.tao_tu_dong(db, d3.id, 2, NGUOI)
            db.commit()

            ds = db.query(PackingList).filter(PackingList.so_id == d3.id).all()
            xe = db.query(Vehicle).first()
            tx = db.query(Driver).first()
            gh = giao_hang_service.tao(
                db,
                {
                    "packing_list_ids": [p.id for p in ds],
                    "vehicle_id": xe.id if xe else None,
                    "driver_id": tx.id if tx else None,
                    "route_name": "Vientiane → Donekoy",
                },
                NGUOI,
            )
            db.commit()
            giao_hang_service.doi_trang_thai(db, gh.id, "loading", NGUOI)
            db.commit()
            giao_hang_service.doi_trang_thai(db, gh.id, "in_transit", NGUOI)
            db.commit()
            giao_hang_service.doi_trang_thai(db, gh.id, "arrived", NGUOI)
            db.commit()
            # Ký nhận MỘT phiếu thôi, để còn một phiếu cho người xem tự bấm thử.
            giao_hang_service.ghi_pod(
                db, ds[0].id,
                {"received_by": "Somchai", "result": "full", "goods_condition": "Nguyên kiện"},
                NGUOI,
            )
            db.commit()
            print(f"Đơn 3 (đang giao): {d3.id} / chuyến {gh.code}")
        else:
            print(f"Đơn 3 (đang giao): {d3.id} — đã có sẵn")

        # Vệt GPS mô phỏng cho mọi chuyến đang chạy mà chưa có mốc nào
        from models import VehiclePosition
        for gh in db.query(Delivery).filter(Delivery.status.in_(["in_transit", "arrived"])).all():
            if db.query(VehiclePosition).filter(VehiclePosition.delivery_id == gh.id).count():
                continue
            gh = giao_hang_service.nap(db, gh.id)
            try:
                for _ in range(4):
                    theo_doi_service.mo_phong_chay_tiep(db, gh.id, 0.2, NGUOI)
                db.commit()
                print(f"  Đã gieo vệt GPS mô phỏng cho {gh.code}")
            except Exception as loi:  # noqa: BLE001
                db.rollback()
                print(f"  Bỏ qua vệt GPS cho {gh.code}: {loi}")

        print("\nXong. Chạy: python chay.py  →  http://127.0.0.1:8042")
    finally:
        db.close()


if __name__ == "__main__":
    gieo()
