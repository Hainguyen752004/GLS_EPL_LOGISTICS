from conftest import bao_gia_hop_le


def test_quote_to_so_to_do_preserves_route_context_not_route_id_as_origin(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()

    quote = client.post("/api/quotations", json=bao_gia_hop_le(**{
        "id": "QT-CTX",
        "origin": "Kho Bình Dương",
        "destination": "Cảng Cát Lái",
        "pickup_window_start": "2026-08-12T08:00:00",
        "pickup_window_end": "2026-08-12T09:00:00",
        "delivery_window_start": "2026-08-12T11:00:00",
        "delivery_window_end": "2026-08-12T12:00:00",
        "weight_kg": 1200,
        "pallet_count": 4,
        "cargo_type": "Hàng tiêu dùng",
    }))
    assert quote.status_code == 200, quote.text
    assert client.put("/api/quotations/QT-CTX/approve").status_code == 200

    all_data = client.get("/api/data/all").json()
    quote_row = next(row for row in all_data["quotations"] if row["id"] == "QT-CTX")
    assert quote_row["origin"] == "Kho Bình Dương"
    assert quote_row["destination"] == "Cảng Cát Lái"
    assert quote_row["pickup_window_start"] == "2026-08-12T08:00:00"
    assert quote_row["delivery_window_end"] == "2026-08-12T12:00:00"
    assert quote_row["weight_kg"] == 1200
    assert quote_row["pallet_count"] == 4

    so = client.post("/api/sales-orders", json={"id": "SO-CTX", "quotation_id": "QT-CTX"})
    assert so.status_code == 200
    so_data = so.json()["data"]
    assert so_data["origin"] == "Kho Bình Dương"
    assert so_data["destination"] == "Cảng Cát Lái"
    assert so_data["route_id"] == "RT-T1"
    assert so_data["pickup_window_start"] == "2026-08-12T08:00:00"
    assert so_data["delivery_window_end"] == "2026-08-12T12:00:00"

    assert client.put("/api/sales-orders/SO-CTX/confirm").status_code == 200
    delivery = client.post("/api/delivery-orders", json={"id": "DO-CTX", "so_id": "SO-CTX"})
    assert delivery.status_code == 200
    do_data = delivery.json()["data"]
    assert do_data["route_id"] == "RT-T1"
    assert do_data["origin"] == "Kho Bình Dương"
    assert do_data["destination"] == "Cảng Cát Lái"
    assert do_data["pickup_window_start"] == "2026-08-12T01:00:00Z"
    assert do_data["delivery_window_end"] == "2026-08-12T05:00:00Z"
    assert do_data["weight_kg"] == 1200
    assert do_data["pallet_count"] == 4


def test_sales_order_requires_approved_quotation_with_route_context(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    response = client.post("/api/quotations", json=bao_gia_hop_le(id="QT-NO-ORIGIN"))
    assert response.status_code == 200, response.text
    assert client.put("/api/quotations/QT-NO-ORIGIN/approve").status_code == 200

    so = client.post("/api/sales-orders", json={"id": "SO-NO-ORIGIN", "quotation_id": "QT-NO-ORIGIN"})
    assert so.status_code == 200
    assert so.json()["data"]["origin"] == "Tuyến Test"
    assert so.json()["data"]["destination"] == "Tuyến Test"
