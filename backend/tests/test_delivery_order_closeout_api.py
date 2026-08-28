import importlib


def test_delivered_demo_do_exposes_closeout_price_table_from_database(app_client):
    client, _, _ = app_client
    database = importlib.import_module("database")
    seed_service = importlib.import_module("services.demo_seed_service")

    with database.SessionLocal() as db:
        ids = seed_service.seed_demo(db, reset=True, verify=True)

    completed = ids["completed"]
    response = client.get(f"/api/delivery-orders/{completed['delivery_order_id']}/closeout")

    assert response.status_code == 200
    data = response.json()
    assert data["do_id"] == "DEMO-DO-2026-003"
    assert data["sales_order_id"] == "DEMO-SO-2026-003"
    assert data["quotation_id"] == "DEMO-QT-2026-003"
    assert data["status"] == "delivered"
    assert data["currency"] == "VND"
    assert data["cost_formula"]["id"] == "DEMO-COST-FORMULA-20FT"
    assert data["cost_formula"]["components"]["fuel"] == "6250"
    assert data["configured_cost_lines"] == [
        {
            "code": "fuel",
            "name": "Chi phí xăng dầu",
            "original_amount": 279375.0,
            "calculation": "44.7 km × 6.250 VND",
        },
        {
            "code": "driver",
            "name": "Phụ cấp chuyến tài xế",
            "original_amount": 500000.0,
            "calculation": "Theo chuyến",
        },
        {
            "code": "toll",
            "name": "Phí cầu đường / BOT",
            "original_amount": 300000.0,
            "calculation": "Theo chuyến",
        },
        {
            "code": "warehouse",
            "name": "Phí bãi và lưu kho",
            "original_amount": 200000.0,
            "calculation": "Theo chuyến",
        },
        {
            "code": "freight_rate",
            "name": "Cước vận chuyển theo tải trọng",
            "original_amount": 12750000.0,
            "calculation": "8.500 kg × 1.500 VND",
        },
    ]
    assert data["commercials"]["base_selling_price"] == 4200000.0
    assert data["commercials"]["customer_surcharge_total"] == 470000.0
    assert data["commercials"]["selling_price"] == 4670000.0
    assert data["commercials"]["actual_cost_total"] == 2380000.0
    assert data["commercials"]["margin_amount"] == 2290000.0
    assert [line["charge_type"] for line in data["actual_cost_lines"]] == ["driver", "fuel", "toll"]
    assert [pod["stop_no"] for pod in data["pod_records"]] == [1]
    assert data["pod_records"][0]["receiver_name"] == "Nguyễn Văn An"
    assert {document["file_name"] for document in data["pod_documents"]} == {
        "POD-DEMO-DO-2026-003.pdf",
        "signature-DEMO-DO-2026-003.png",
    }
    assert data["trip"]["id"] == "DEMO-TRIP-2026-003"
