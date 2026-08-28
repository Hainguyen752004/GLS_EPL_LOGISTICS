import sqlite3


def _audits(database_file):
    with sqlite3.connect(database_file) as connection:
        return connection.execute("SELECT user_id, action, record_id FROM audit_logs ORDER BY id").fetchall()


def test_successful_workflow_operations_record_actor_and_action(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.master_data()
    headers = {"X-Test-Principal": "audit-user"}
    assert client.post("/api/quotations", json={"id": "QT-A", "customer_id": "CUS-T1", "route_id": "RT-T1"}, headers=headers).status_code == 200
    assert client.put("/api/quotations/QT-A/approve", headers=headers).status_code == 200
    assert client.post("/api/sales-orders", json={"id": "SO-A", "quotation_id": "QT-A"}, headers=headers).status_code == 200
    assert client.put("/api/sales-orders/SO-A/confirm", headers=headers).status_code == 200
    assert client.post("/api/delivery-orders", json={"id": "DO-A", "so_id": "SO-A"}, headers=headers).status_code == 200
    assert client.put("/api/delivery-orders/DO-A/dispatch", json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"}, headers=headers).status_code == 200
    assert client.post("/api/quotations", json={"id": "QT-X", "customer_id": "CUS-T1", "route_id": "RT-T1"}, headers=headers).status_code == 200
    assert client.delete("/api/quotations/QT-X", headers=headers).status_code == 200
    assert client.post("/api/quotations", json={"id": "QT-SX", "customer_id": "CUS-T1", "route_id": "RT-T1"}, headers=headers).status_code == 200
    assert client.put("/api/quotations/QT-SX/approve", headers=headers).status_code == 200
    assert client.post("/api/sales-orders", json={"id": "SO-X", "quotation_id": "QT-SX"}, headers=headers).status_code == 200
    assert client.delete("/api/sales-orders/SO-X", headers=headers).status_code == 200
    assert client.post("/api/sales-orders", json={"id": "SO-DX", "quotation_id": "QT-SX"}, headers=headers).status_code == 200
    assert client.put("/api/sales-orders/SO-DX/confirm", headers=headers).status_code == 200
    assert client.post("/api/delivery-orders", json={"id": "DO-X", "so_id": "SO-DX"}, headers=headers).status_code == 200
    assert client.delete("/api/delivery-orders/DO-X", headers=headers).status_code == 200
    expected = {"CREATE_QUOTATION", "APPROVE_QUOTATION", "CREATE_SALES_ORDER", "CONFIRM_SALES_ORDER", "CREATE_DELIVERY_ORDER", "DISPATCH_DELIVERY", "DELETE_QUOTATION", "DELETE_SALES_ORDER", "DELETE_DELIVERY_ORDER"}
    rows = _audits(database_file)
    assert expected <= {action for user, action, record_id in rows if user == "audit-user"}


def test_rejected_lock_and_transition_do_not_write_audit(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.master_data().quotation("QT-R", approve=True)
    before = _audits(database_file)
    assert client.delete("/api/quotations/QT-R", headers={"X-User-Id": "rejected"}).status_code == 409
    assert client.put("/api/quotations/QT-R/status", json={"status": "Approved"}, headers={"X-User-Id": "rejected"}).status_code == 409
    assert _audits(database_file) == before
