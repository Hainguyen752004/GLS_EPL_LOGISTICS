import datetime
from conftest import bao_gia_hop_le, dieu_phoi_qua_chuyen


WORKFLOW_ROUTES = {
    ("GET", "/api/quotations"),
    ("POST", "/api/quotations"),
    ("PUT", "/api/quotations/{qid}"),
    ("PUT", "/api/quotations/{qid}/approve"),
    ("PUT", "/api/quotations/{qid}/status"),
    ("DELETE", "/api/quotations/{qid}"),
    ("GET", "/api/delivery-orders"),
    ("GET", "/api/delivery-orders/analysis"),
    ("PUT", "/api/delivery-orders/{do_id}"),
    ("PUT", "/api/delivery-orders/{do_id}/status"),
    ("PUT", "/api/delivery-orders/{do_id}/dispatch"),
    ("DELETE", "/api/delivery-orders/{do_id}"),
    ("GET", "/api/pod/{do_id}"),
    ("POST", "/api/pod/{do_id}"),
}


def _routes(app):
    for route in app.routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from included.routes
        elif hasattr(route, "path"):
            yield route


def test_public_workflow_urls_are_preserved(app_client):
    client, _, _ = app_client
    actual = {(method, route.path) for route in _routes(client.app)
              for method in (getattr(route, "methods", set()) or set())}
    assert WORKFLOW_ROUTES <= actual


def test_collection_and_pod_gets_return_entity_shapes(app_client):
    client, _, _ = app_client
    for url in ("/api/quotations", "/api/delivery-orders"):
        response = client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"items", "total", "page", "page_size"}
        assert isinstance(payload["items"], list)


def test_delivery_order_analysis_groups_real_backend_statuses(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-ANA-L", approve=True)
    near_late = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)).isoformat()
    workflow_builder.delivery_order("DO-ANA-L", "QT-ANA-L", pickup_window_start=near_late,
                                    pickup_window_end=None, delivery_window_start=None, delivery_window_end=None)
    workflow_builder.quotation("QT-ANA-P", approve=True)
    workflow_builder.delivery_order("DO-ANA-P", "QT-ANA-P", approve=True, pickup_window_start=None,
                                    pickup_window_end=None, delivery_window_start=None, delivery_window_end=None)
    workflow_builder.quotation("QT-ANA-A", approve=True)
    workflow_builder.delivery_order("DO-ANA-A", "QT-ANA-A", approve=True)
    # Dieu phoi QUA CHUYEN — duong dieu phoi le da dong phan ghi.
    dieu_phoi_qua_chuyen(client, "DO-ANA-A")
    workflow_builder.quotation("QT-ANA-I", approve=True)
    workflow_builder.delivery_order("DO-ANA-I", "QT-ANA-I", approve=True)
    assert client.post(
        "/api/incidents",
        json={
            "do_id": "DO-ANA-I",
            "vehicle_id": "VEH-T1",
            "incident_type": "Kẹt xe",
            "location": "Cảng Cát Lái",
            "reporter": "Điều phối",
        },
    ).status_code == 200

    payload = client.get("/api/delivery-orders/analysis").json()
    by_id = {record["id"]: record for record in payload["records"]}
    assert by_id["DO-ANA-L"]["stage"] == "near_late"
    assert by_id["DO-ANA-L"]["operational_status"] == "Gần trễ"
    # DO-ANA-P duoc dung KHONG co ngay lay lan ngay giao nao, nen no thuoc ro
    # "thieu han giao" chu khong phai "cho van chuyen". Truoc day hai truong
    # hop nay lan vao nhau, nen khong ai thay la don dang thieu ngay - du no
    # khong lap ke hoach duoc va cung khong do tre duoc.
    assert by_id["DO-ANA-P"]["stage"] == "undated"
    assert by_id["DO-ANA-P"]["operational_status"] == "Thiếu hạn giao"
    assert by_id["DO-ANA-P"]["due_at"] is None
    # Trang thai goc khong doi: ro chi la cach xep de nhin, khong phai trang thai.
    assert by_id["DO-ANA-P"]["canonical_status"] == "pending"
    assert by_id["DO-ANA-A"]["stage"] == "active"
    assert by_id["DO-ANA-A"]["operational_status"] == "Đang vận chuyển"
    assert by_id["DO-ANA-I"]["stage"] == "incident"
    assert by_id["DO-ANA-I"]["operational_status"] == "Gặp sự cố"
    # Ro "cancelled" them ngay 09/09: DO da huy phai ra khoi hang doi dieu phoi,
    # truoc do no roi vao nhanh else roi bi do han giao nen hien o tab "Gan tre".
    assert set(payload["buckets"]) == {
        "incident", "overdue", "undated", "near_late", "pending", "active",
        "completed", "cancelled"
    }
    assert payload["buckets"]["near_late"]["count"] >= 1
    assert payload["buckets"]["undated"]["count"] >= 1
    assert payload["buckets"]["active"]["count"] >= 1
    assert payload["buckets"]["incident"]["count"] >= 1


def _assert_envelope(response, identity_key, identity):
    assert response.status_code == 200
    assert set(response.json()) == {"message", "data"}
    assert response.json()["data"][identity_key] == identity


def test_every_workflow_mutation_and_pod_get_contract(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _assert_envelope(client.post("/api/quotations", json=bao_gia_hop_le(id="QT-DEL")), "id", "QT-DEL")
    _assert_envelope(client.delete("/api/quotations/QT-DEL"), "id", "QT-DEL")
    _assert_envelope(client.post("/api/quotations", json=bao_gia_hop_le(id="QT-APP")), "id", "QT-APP")
    _assert_envelope(client.put("/api/quotations/QT-APP/approve"), "id", "QT-APP")
    workflow_builder.quotation("QT-C", approve=False)
    _assert_envelope(client.put("/api/quotations/QT-C/status", json={"status": "Approved"}), "id", "QT-C")
    workflow_builder.quotation("QT-DO", approve=True)
    workflow_builder.delivery_order("DO-DEL", "QT-DO")
    _assert_envelope(client.delete("/api/delivery-orders/DO-DEL"), "id", "DO-DEL")
    workflow_builder.quotation("QT-RUN", approve=True)
    workflow_builder.delivery_order("DO-RUN", "QT-RUN")
    # `PUT /api/delivery-orders/{id}/dispatch` da dong phan ghi, nen no khong
    # con tra phong bi thanh cong. Phong bi cua buoc dieu phoi kiem o
    # `test_dispatch_command_contract.py` (duong chuyen).
    dieu_phoi_qua_chuyen(client, "DO-RUN")
    pod = client.get("/api/pod/DO-RUN")
    assert pod.status_code == 404
    assert pod.json()["error"]["code"] == "POD_NOT_FOUND"
