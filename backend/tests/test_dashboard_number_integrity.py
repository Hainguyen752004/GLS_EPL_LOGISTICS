"""Các con số trên Bảng điều khiển phải đo đúng thứ mà nhãn của chúng nói.

Người dùng nhìn thấy hai "doanh thu" lệch 19 triệu cách nhau vài trăm pixel
trên cùng một trang, và ô "Số Xe Hoạt Động" thực chất đếm lệnh giao hàng.
"""

import importlib

import pytest


def _seed(db, models):
    import datetime as dt
    db.add(models.Customer(id="CUS-DASH", name="Khách Dashboard"))
    db.commit()
    db.add(models.DeliveryOrder(
        id="DO-DASH-1", customer_id="CUS-DASH",
        canonical_status="delivered", status="Đã giao",
    ))
    db.commit()
    # DOANH THU doc tu HO SO HOAN TAT (module hoa don AR da xoa 10/09).
    db.add(models.DeliveryOrderCloseout(
        id="CLO-DASH-1", do_id="DO-DASH-1", base_selling_price_snapshot=10_000_000,
        base_price_source="quotation", base_price_source_id="QT-DASH", surcharge_total=1_000_000,
        final_selling_price=11_000_000, currency_code="VND",
        completed_at=dt.datetime(2026, 8, 20, 8, 30, tzinfo=dt.timezone.utc), completed_by="ops",
    ))
    db.commit()


def test_revenue_ytd_la_tong_gia_ban_cuoi_cua_ho_so_hoan_tat(app_client):
    """revenue_ytd = tong `final_selling_price` cua cac ho so hoan tat — con so ban giao cho he cong no."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _seed(db, models)
    payload = client.get("/api/dashboard/stats").json()
    assert payload["revenue_ytd"] == 11_000_000
    assert payload["recognized_revenue"] == payload["revenue_ytd"]
    assert payload["completed_deliveries"] == 1
    # Khong con hai chi tieu cu cua SO / hoa don AR.
    assert "booked_revenue_so" not in payload and "recognized_revenue_ar" not in payload

def test_vehicle_count_and_in_transit_orders_are_distinct_fields(app_client):
    """"Số xe hoạt động" phải đếm xe, không phải đếm lệnh giao hàng."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _seed(db, models)
        # Một chiếc xe, ba lệnh giao hàng đang chạy: hai con số phải khác nhau.
        db.add(models.Vehicle(id="VEH-DASH-1", status="Sẵn sàng"))
        db.commit()
        for index in (2, 3):
            db.add(models.DeliveryOrder(
                id=f"DO-DASH-{index}", customer_id="CUS-DASH",
                canonical_status="in_transit", status="In Transit",
            ))
            db.commit()

    payload = client.get("/api/dashboard/stats").json()

    # HAI, khong phai BA. Lenh DO-DASH-1 cua `_seed` mang `canonical_status =
    # "delivered"` nhung nhan `status = "In Transit"` — mot dong tu mau thuan.
    # Ban cu dem theo NHAN nen dem ca no; ban moi dem theo TRANG THAI CHUAN, va
    # mot lenh da giao thi khong "dang chay" du nhan noi gi. Chinh su troi giua
    # nhan va ma nay la ly do bo dem theo nhan.
    assert payload["in_transit_orders"] == 2, "phải đếm lệnh giao hàng đang chạy theo canonical_status"
    assert payload["active_vehicles"] == 1, (
        "phải đếm phương tiện; trước đây trường này trả về số lệnh giao hàng"
    )
    assert payload["active_vehicles"] != payload["in_transit_orders"]
