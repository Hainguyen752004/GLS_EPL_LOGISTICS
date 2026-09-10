from conftest import bao_gia_hop_le, dieu_phoi_qua_chuyen, san_sang_dieu_phoi


def _create_master_data(client):
    assert client.post("/api/customers", json={"id": "CUS-T1", "name": "Khách Test"}).status_code in (200, 201)
    assert client.post("/api/routes", json={"id": "RT-T1", "name": "Tuyến Test", "distance_km": 10, "segments_json": "[]"}).status_code in (200, 201)
    assert client.post("/api/vehicles", json={"id": "VEH-T1", "type": "Xe tải", "status": "Sẵn sàng"}).status_code in (200, 201)
    assert client.post("/api/drivers", json={"id": "DRV-T1", "name": "Tài xế Test", "status": "🟢 Rảnh (Sẵn sàng)"}).status_code in (200, 201)


def _create_pending_do(client, suffix):
    assert client.post("/api/quotations", json=bao_gia_hop_le(id=f"QT-{suffix}", selling_price=3_500_000)).status_code == 200
    assert client.put(f"/api/quotations/QT-{suffix}/approve").status_code == 200
    assert client.post(f"/api/quotations/QT-{suffix}/send", json={}).status_code == 200
    assert client.post(f"/api/quotations/QT-{suffix}/accept", json={"dos": [{"id": f"DO-{suffix}", "quantity": 1}]}).status_code == 200


def _entity(client, collection, entity_id):
    return next(row for row in client.get(collection).json()["items"] if row["id"] == entity_id)


def test_approved_quotation_cannot_be_deleted(app_client):
    client, _, _ = app_client
    _create_master_data(client)

    create = client.post("/api/quotations", json=bao_gia_hop_le(id="QT-T1"))
    assert create.status_code == 200
    approve = client.put("/api/quotations/QT-T1/approve")
    assert approve.status_code == 200
    before = _entity(client, "/api/quotations", "QT-T1")

    delete = client.delete("/api/quotations/QT-T1")

    assert delete.status_code == 409
    assert delete.json()["detail"] == {"code": "LOCKED_RECORD", "message": "Báo giá đã duyệt chỉ được xem, không được xóa.", "navigation_targets": ["quotations"]}
    after = _entity(client, "/api/quotations", "QT-T1")
    assert (after["canonical_status"], after["version"]) == (before["canonical_status"], before["version"])


def test_pending_delivery_order_can_be_deleted(app_client):
    client, _, _ = app_client
    _create_master_data(client)
    _create_pending_do(client, "T3")

    delete = client.delete("/api/delivery-orders/DO-T3")

    assert delete.status_code == 200
    assert not any(row["id"] == "DO-T3" for row in client.get("/api/delivery-orders").json()["items"])


def test_in_transit_delivery_order_cannot_be_deleted(app_client):
    client, _, _ = app_client
    _create_master_data(client)
    _create_pending_do(client, "RUN")
    # Dieu phoi QUA CHUYEN: duong dieu phoi le da dong phan ghi.
    dieu_phoi_qua_chuyen(client, "DO-RUN")
    before = _entity(client, "/api/delivery-orders", "DO-RUN")
    delete = client.delete("/api/delivery-orders/DO-RUN")
    after = _entity(client, "/api/delivery-orders", "DO-RUN")
    assert delete.status_code == 409
    assert delete.json()["detail"] == {
        "code": "LOCKED_RECORD",
        "message": "Lệnh giao hàng đang vận chuyển hoặc đã kết thúc chỉ được xem, không được xóa.",
        "navigation_targets": ["delivery-orders"],
    }
    assert (after["canonical_status"], after["version"]) == (before["canonical_status"], before["version"])


def test_vehicle_crud_is_persistent_and_in_use_vehicle_cannot_be_deleted(app_client):
    client, _, _ = app_client
    _create_master_data(client)

    update = client.post("/api/vehicles", json={
        "id": "VEH-T1",
        "brand": "Isuzu",
        "type": "Xe tải lạnh",
        "weight_capacity": 12000,
        "status": "Sẵn sàng",
    })
    assert update.status_code in (200, 201)
    vehicles = client.get("/api/vehicles").json()
    persisted = next(row for row in vehicles if row["id"] == "VEH-T1")
    assert persisted["brand"] == "Isuzu"
    assert persisted["type"] == "Xe tải lạnh"
    assert persisted["weight_capacity"] == 12000

    _create_pending_do(client, "VEHLOCK")
    dieu_phoi_qua_chuyen(client, "DO-VEHLOCK")

    delete = client.delete("/api/vehicles/VEH-T1")

    assert delete.status_code == 409
    assert delete.json()["detail"] == {
        "code": "LOCKED_RECORD",
        "message": "Xe đang được dùng bởi DO/Trip/Tracking, không được xóa khỏi Master Data.",
        "navigation_targets": ["dispatch", "tracking", "master-data/vehicles"],
    }
    assert any(row["id"] == "VEH-T1" for row in client.get("/api/vehicles").json())


def test_invalid_transition_does_not_change_status_or_version(app_client):
    client, _, _ = app_client
    _create_master_data(client)
    assert client.post("/api/quotations", json=bao_gia_hop_le(id="QT-BAD")).status_code == 200
    before = _entity(client, "/api/quotations", "QT-BAD")
    response = client.put("/api/quotations/QT-BAD/status", json={"status": "Draft"})
    after = _entity(client, "/api/quotations", "QT-BAD")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_TRANSITION"
    assert (after["canonical_status"], after["version"]) == (before["canonical_status"], before["version"])


def test_dispatch_updates_actor_timestamp_and_version(app_client):
    client, _, _ = app_client
    _create_master_data(client); _create_pending_do(client, "VER")
    before = _entity(client, "/api/delivery-orders", "DO-VER")
    dieu_phoi_qua_chuyen(client, "DO-VER", dau={"X-Test-Principal": "dispatcher"})
    after = _entity(client, "/api/delivery-orders", "DO-VER")
    assert after["canonical_status"] == "in_transit"
    assert after["updated_by"] == "dispatcher"
    assert after["updated_at"] != before["updated_at"]
    assert after["version"] == before["version"] + 1


def test_masterdata_to_pending_delivery_order_flow(app_client):
    client, _, _ = app_client
    _create_master_data(client)

    qt = client.post("/api/quotations", json=bao_gia_hop_le(id="QT-E2E", selling_price=2_500_000))
    assert qt.status_code == 200
    assert qt.json()["data"]["canonical_status"] == "draft"

    approved_qt = client.put("/api/quotations/QT-E2E/approve")
    assert approved_qt.status_code == 200
    assert approved_qt.json()["data"]["canonical_status"] == "approved"

    assert client.post("/api/quotations/QT-E2E/send", json={}).status_code == 200
    accepted = client.post("/api/quotations/QT-E2E/accept", json={"dos": [{"id": "DO-E2E", "quantity": 1}]})
    assert accepted.status_code == 200, accepted.text
    delivery = _entity(client, "/api/delivery-orders", "DO-E2E")
    assert delivery["canonical_status"] == "pending"
    assert delivery["quotation_id"] == "QT-E2E"


def test_dispatch_requires_pod_before_delivery(app_client):
    client, _, _ = app_client
    _create_master_data(client)
    _create_pending_do(client, "FULL")
    dieu_phoi_qua_chuyen(client, "DO-FULL")
    assert _entity(client, "/api/delivery-orders", "DO-FULL")["canonical_status"] == "in_transit"

    tracking = client.get("/api/tracking/DO-FULL")
    assert tracking.status_code == 200
    assert tracking.json()["vehicle_id"] == "VEH-T1"

    delivered_without_pod = client.put("/api/delivery-orders/DO-FULL/status", json={"status": "Delivered"})
    assert delivered_without_pod.status_code == 409
    assert delivered_without_pod.json()["detail"]["code"] == "ATOMIC_COMPLETION_REQUIRED"
