"""Các con số trên Bảng điều khiển phải đo đúng thứ mà nhãn của chúng nói.

Người dùng nhìn thấy hai "doanh thu" lệch 19 triệu cách nhau vài trăm pixel
trên cùng một trang, và ô "Số Xe Hoạt Động" thực chất đếm lệnh giao hàng.
"""

import importlib

import pytest


def _seed(db, models):
    db.add(models.Customer(id="CUS-DASH", name="Khách Dashboard"))
    db.commit()
    db.add(models.SalesOrder(
        id="SO-DASH-1", customer_id="CUS-DASH",
        canonical_status="confirmed", status="Confirmed",
        total_amount=90000000,
    ))
    db.commit()
    db.add(models.DeliveryOrder(
        id="DO-DASH-1", so_id="SO-DASH-1", customer_id="CUS-DASH",
        canonical_status="delivered", status="In Transit",
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

    # Đơn hàng 90tr lớn hơn hóa đơn 11tr — đúng tình huống mà max() chọn sai.
    assert payload["booked_revenue_so"] >= 90000000
    assert payload["recognized_revenue_ar"] == 11000000
    assert payload["revenue_ytd"] == payload["recognized_revenue_ar"], (
        "revenue_ytd phải khớp doanh thu ghi sổ để không mâu thuẫn với "
        "/api/tms/reporting/transport-revenue trên cùng một màn hình"
    )
    assert payload["revenue_ytd"] != max(
        payload["booked_revenue_so"], payload["recognized_revenue_ar"]
    ), "vẫn đang dùng max() của hai chỉ tiêu khác bản chất"


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
        # delivery_orders.so_id là UNIQUE (mỗi đơn hàng một lệnh giao hàng),
        # nên mỗi lệnh thêm vào cần một đơn hàng riêng.
        for index in (2, 3):
            db.add(models.SalesOrder(
                id=f"SO-DASH-{index}", customer_id="CUS-DASH",
                canonical_status="confirmed", status="Confirmed",
                total_amount=1000000,
            ))
            db.commit()
            db.add(models.DeliveryOrder(
                id=f"DO-DASH-{index}", so_id=f"SO-DASH-{index}", customer_id="CUS-DASH",
                canonical_status="in_transit", status="In Transit",
            ))
            db.commit()

    payload = client.get("/api/dashboard/stats").json()

    assert payload["in_transit_orders"] == 3, "phải đếm lệnh giao hàng đang chạy"
    assert payload["active_vehicles"] == 1, (
        "phải đếm phương tiện; trước đây trường này trả về số lệnh giao hàng"
    )
    assert payload["active_vehicles"] != payload["in_transit_orders"]
