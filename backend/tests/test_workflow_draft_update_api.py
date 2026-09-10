from conftest import bao_gia_hop_le, dieu_phoi_qua_chuyen
def _data(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_draft_quotation_and_delivery_order_can_be_updated(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()

    quote = _data(client.post("/api/quotations", json=bao_gia_hop_le(**{
        "id": "QT-UPD",
        "origin": "Kho A",
        "destination": "Cang A",
        "selling_price": 3_100_000,
    })))
    assert quote["selling_price"] == 3_100_000

    quote = _data(client.put("/api/quotations/QT-UPD", json={
        "customer_id": "CUS-T1",
        "route_id": "RT-T1",
        "origin": "Kho B",
        "destination": "Cang B",
        "selling_price": 3_500_000,
        "fuel_cost": 700_000,
        "driver_cost": 800_000,
        "toll_fee": 1_000_000,
        "total_cost": 2_500_000,
    }))
    assert quote["origin"] == "Kho B"
    assert quote["destination"] == "Cang B"
    assert quote["selling_price"] == 3_500_000
    assert quote["canonical_status"] == "draft"

    duyet = client.put("/api/quotations/QT-UPD/approve")
    assert duyet.status_code == 200, duyet.text
    # Duyet lan hai: luong bao gia moi tra 409 INVALID_TRANSITION (da duyet roi), khong lap.
    assert client.put("/api/quotations/QT-UPD/approve").status_code == 409
    workflow_builder.delivery_order("DO-UPD", "QT-UPD")

    delivery = _data(client.put("/api/delivery-orders/DO-UPD", json={
        "route_id": "RT-T1",
        "origin": "Kho DO",
        "destination": "Cang DO",
        "pickup_date": "2026-08-21T08:00:00+07:00",
        "delivery_date": "2026-08-21T12:00:00+07:00",
        "weight_kg": 1800,
        "pallet_count": 5,
    }))
    assert delivery["origin"] == "Kho DO"
    assert delivery["destination"] == "Cang DO"
    assert delivery["pickup_date"] == "2026-08-21T01:00:00Z"
    assert delivery["delivery_date"] == "2026-08-21T05:00:00Z"
    assert delivery["canonical_status"] == "pending"


def test_locked_workflow_rows_reject_update(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()

    workflow_builder.quotation("QT-LOCK", approve=True)
    quote_update = client.put("/api/quotations/QT-LOCK", json={
        "customer_id": "CUS-T1",
        "route_id": "RT-T1",
        "origin": "Should Not Save",
    })
    assert quote_update.status_code == 409
    assert quote_update.json()["detail"]["code"] == "LOCKED_RECORD"

    workflow_builder.delivery_order("DO-LOCK", "QT-LOCK", approve=True)
    dieu_phoi_qua_chuyen(client, "DO-LOCK")
    do_update = client.put("/api/delivery-orders/DO-LOCK", json={"origin": "Should Not Save"})
    assert do_update.status_code == 409
    assert do_update.json()["detail"]["code"] == "LOCKED_RECORD"


def test_route_post_updates_existing_route_instead_of_duplicate_error(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.route("RT-UPD")

    response = client.post("/api/routes", json={
        "id": "RT-UPD",
        "name": "Tuyen da sua",
        "distance_km": 44.7,
        "segments_json": '[{"origin":"Kho","destination":"Cang","distance_km":44.7}]',
    })

    route = _data(response)
    assert route["id"] == "RT-UPD"
    assert route["name"] == "Tuyen da sua"
    assert route["distance_km"] == 44.7
