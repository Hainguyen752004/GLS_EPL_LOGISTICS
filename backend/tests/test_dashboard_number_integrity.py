"""Các con số trên Bảng điều khiển phải đo đúng thứ mà nhãn của chúng nói.

Người dùng nhìn thấy hai "doanh thu" lệch 19 triệu cách nhau vài trăm pixel
trên cùng một trang, và ô "Số Xe Hoạt Động" thực chất đếm lệnh giao hàng.
"""

import importlib

import pytest


def _seed(db, models):
    db.add(models.Customer(id="CUS-DASH", name="Khách Dashboard"))
    db.commit()
    db.add(models.DeliveryOrder(
        id="DO-DASH-1", customer_id="CUS-DASH",
        # Nhan phai KHOP ma: mot lenh da giao thi nhan la "Da giao". Ban cu
        # de "In Transit" o day, va phep dem theo nhan cua bang dieu khien
        # dem ca no — dung kieu troi giua nhan va ma ma he da bo.
        canonical_status="delivered", status="Đã giao",
    ))
    db.commit()
    db.add(models.ARInvoice(
        id="INV-DASH-1", do_id="DO-DASH-1", customer_id="CUS-DASH",
        canonical_status="posted", status="Posted",
        invoice_date="2026-08-20", amount=10000000, total=11000000,
        is_active=True,
    ))
    db.commit()


def test_revenue_ytd_is_recognized_revenue_not_max_of_two_metrics(app_client):
    """revenue_ytd phải là doanh thu ĐÃ GHI SỔ (AR), không phải max().

    max(tổng đơn hàng, tổng hóa đơn) là phép tính không có ý nghĩa kế toán:
    nó lấy doanh thu ký kết khi con số đó lớn hơn, rồi gắn nhãn "Doanh thu
    hóa đơn thực tế (AR)".
    """
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _seed(db, models)

    payload = client.get("/api/dashboard/stats").json()

    # Không còn Đơn hàng: doanh thu ký kết luôn 0, chỉ còn doanh thu ghi sổ (AR).
    assert payload["booked_revenue_so"] == 0  # buoc Don hang da bo
    assert payload["recognized_revenue_ar"] == 11000000
    assert payload["revenue_ytd"] == payload["recognized_revenue_ar"], (
        "revenue_ytd phải khớp doanh thu ghi sổ để không mâu thuẫn với "
        "/api/tms/reporting/transport-revenue trên cùng một màn hình"
    )
    # (Phép so với max() đã bỏ: booked_revenue_so luôn 0 sau khi trục xuất SO nên max() trùng AR.)


def test_two_revenue_metrics_are_reported_separately(app_client):
    """Cả hai chỉ tiêu đều hữu ích — nhưng phải ở hai trường riêng."""
    client, _, _ = app_client

    payload = client.get("/api/dashboard/stats").json()

    assert "booked_revenue_so" in payload
    assert "recognized_revenue_ar" in payload


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
