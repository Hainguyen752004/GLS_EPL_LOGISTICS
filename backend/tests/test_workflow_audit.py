import sqlite3
from conftest import bao_gia_hop_le, dieu_phoi_qua_chuyen, ket_noi_du_lieu


def _audits(database_file):
    with ket_noi_du_lieu(database_file) as connection:
        return connection.execute("SELECT user_id, action, record_id FROM audit_logs ORDER BY id").fetchall()


def test_successful_workflow_operations_record_actor_and_action(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.master_data()
    headers = {"X-Test-Principal": "audit-user"}
    assert client.post("/api/quotations", json=bao_gia_hop_le(id="QT-A"), headers=headers).status_code == 200
    assert client.put("/api/quotations/QT-A/approve", headers=headers).status_code == 200
    assert client.post("/api/quotations/QT-A/send", json={}, headers=headers).status_code == 200
    assert client.post("/api/quotations/QT-A/accept", json={"dos": [{"id": "DO-A", "quantity": 1}]}, headers=headers).status_code == 200
    # Dieu phoi QUA CHUYEN: duong dieu phoi le da dong phan ghi.
    dieu_phoi_qua_chuyen(client, "DO-A", dau=headers)
    assert client.post("/api/quotations", json=bao_gia_hop_le(id="QT-X"), headers=headers).status_code == 200
    assert client.delete("/api/quotations/QT-X", headers=headers).status_code == 200
    assert client.post("/api/quotations", json=bao_gia_hop_le(id="QT-SX"), headers=headers).status_code == 200
    assert client.put("/api/quotations/QT-SX/approve", headers=headers).status_code == 200
    assert client.post("/api/quotations/QT-SX/send", json={}, headers=headers).status_code == 200
    assert client.post("/api/quotations/QT-SX/accept", json={"dos": [{"id": "DO-X", "quantity": 1}]}, headers=headers).status_code == 200
    assert client.delete("/api/delivery-orders/DO-X", headers=headers).status_code == 200
    # "DISPATCH_DELIVERY" khong con: dieu phoi le da dong phan ghi, va dieu
    # phoi di qua chuyen nen no ghi "CREATE_TRANSPORT_TRIP" + "DISPATCH_TRIP".
    expected = {"CREATE_QUOTATION", "APPROVE_QUOTATION",
                "CREATE_TRANSPORT_TRIP", "DISPATCH_TRIP",
                "DELETE_QUOTATION", "DELETE_DELIVERY_ORDER"}
    rows = _audits(database_file)
    assert expected <= {action for user, action, record_id in rows if user == "audit-user"}


def test_rejected_lock_and_transition_do_not_write_audit(app_client, workflow_builder):
    client, database_file, _ = app_client
    workflow_builder.master_data().quotation("QT-R", approve=True)
    before = _audits(database_file)
    assert client.delete("/api/quotations/QT-R", headers={"X-User-Id": "rejected"}).status_code == 409
    assert client.put("/api/quotations/QT-R/status", json={"status": "Approved"}, headers={"X-User-Id": "rejected"}).status_code == 409
    assert _audits(database_file) == before
