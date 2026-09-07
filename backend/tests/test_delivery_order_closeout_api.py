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
    # Bon dong CHI PHI. Ban truoc con mot dong thu nam —
    # `freight_rate` "Cuoc van chuyen theo tai trong" 12.750.000 d — nam trong
    # danh sach nay, va do la mot loi nghiem trong: cuoc phi /kg la tien THU
    # CUA KHACH, khong phai khoan chi. Cong no vao thi "gia thanh" cua chuyen
    # nay thanh 14.029.375 d trong khi gia ban chi 4.200.000 d — moi chuyen
    # deu lo nang tren giay. Cong thuc da phan biet san bang `terms[].kind`
    # (`cost` / `revenue`), nen chi can ton trong no.
    #
    # Ten dong lay tu `terms[].label` chu khong viet cung trong ma nguon, nen
    # doi nhan trong Cong thuc gia thanh la man nay doi theo.
    assert data["configured_cost_lines"] == [
        {
            "code": "fuel",
            "name": "Chi phí xăng dầu /km",
            "original_amount": 279375.0,
            "calculation": "44.7 km × 6.250 VND",
        },
        {
            "code": "driver",
            "name": "Phụ cấp chuyến tài xế",
            "original_amount": 500000.0,
            "calculation": "Theo chuyến × 500.000 VND",
        },
        {
            "code": "toll",
            "name": "Phí cầu đường / BOT",
            "original_amount": 300000.0,
            "calculation": "Theo chuyến × 300.000 VND",
        },
        {
            "code": "warehouse",
            "name": "Phí bãi & lưu kho",
            "original_amount": 200000.0,
            "calculation": "Theo chuyến × 200.000 VND",
        },
    ]
    # Va cuoc /kg KHONG duoc lan vao day nua.
    assert "freight_rate" not in [d["code"] for d in data["configured_cost_lines"]]
    # Tong gia thanh phai nho hon gia ban — khong thi con so vo nghia.
    tong_chi = sum(d["original_amount"] for d in data["configured_cost_lines"])
    assert tong_chi == 1279375.0, tong_chi
    assert tong_chi < data["commercials"]["base_selling_price"], tong_chi
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
