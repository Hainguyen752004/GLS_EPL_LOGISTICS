import datetime


WORKFLOW_ROUTES = {
    ("GET", "/api/quotations"),
    ("POST", "/api/quotations"),
    ("PUT", "/api/quotations/{qid}"),
    ("PUT", "/api/quotations/{qid}/approve"),
    ("PUT", "/api/quotations/{qid}/status"),
    ("DELETE", "/api/quotations/{qid}"),
    ("GET", "/api/sales-orders"),
    ("POST", "/api/sales-orders"),
    ("PUT", "/api/sales-orders/{so_id}"),
    ("PUT", "/api/sales-orders/{so_id}/confirm"),
    ("PUT", "/api/sales-orders/{so_id}/status"),
    ("DELETE", "/api/sales-orders/{so_id}"),
    ("GET", "/api/delivery-orders"),
    ("GET", "/api/delivery-orders/analysis"),
    ("POST", "/api/delivery-orders"),
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
    for url in ("/api/quotations", "/api/sales-orders", "/api/delivery-orders"):
        response = client.get(url)
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"items", "total", "page", "page_size"}
        assert isinstance(payload["items"], list)


def test_delivery_order_analysis_groups_real_backend_statuses(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-ANA-L", approve=True)
    workflow_builder.sales_order("SO-ANA-L", "QT-ANA-L", confirm=True)
    near_late = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)).isoformat()
    assert client.post(
        "/api/delivery-orders",
        json={"id": "DO-ANA-L", "so_id": "SO-ANA-L", "pickup_window_start": near_late},
    ).status_code == 200
    workflow_builder.quotation("QT-ANA-P", approve=True)
    workflow_builder.sales_order("SO-ANA-P", "QT-ANA-P", confirm=True)
    workflow_builder.delivery_order("DO-ANA-P", "SO-ANA-P", approve=True)
    workflow_builder.quotation("QT-ANA-A", approve=True)
    workflow_builder.sales_order("SO-ANA-A", "QT-ANA-A", confirm=True)
    workflow_builder.delivery_order("DO-ANA-A", "SO-ANA-A", approve=True)
    assert client.put(
        "/api/delivery-orders/DO-ANA-A/dispatch",
        json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"},
    ).status_code == 200
    workflow_builder.quotation("QT-ANA-I", approve=True)
    workflow_builder.sales_order("SO-ANA-I", "QT-ANA-I", confirm=True)
    workflow_builder.delivery_order("DO-ANA-I", "SO-ANA-I", approve=True)
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
    assert by_id["DO-ANA-P"]["stage"] == "pending"
    assert by_id["DO-ANA-P"]["operational_status"] == "Chờ vận chuyển"
    assert by_id["DO-ANA-P"]["canonical_status"] == "pending"
    assert by_id["DO-ANA-A"]["stage"] == "active"
    assert by_id["DO-ANA-A"]["operational_status"] == "Đang vận chuyển"
    assert by_id["DO-ANA-I"]["stage"] == "incident"
    assert by_id["DO-ANA-I"]["operational_status"] == "Gặp sự cố"
    assert set(payload["buckets"]) == {"near_late", "pending", "active", "completed", "incident"}
    assert payload["buckets"]["near_late"]["count"] >= 1
    assert payload["buckets"]["pending"]["count"] >= 1
    assert payload["buckets"]["active"]["count"] >= 1
    assert payload["buckets"]["incident"]["count"] >= 1


def _assert_envelope(response, identity_key, identity):
    assert response.status_code == 200
    assert set(response.json()) == {"message", "data"}
    assert response.json()["data"][identity_key] == identity


def test_every_workflow_mutation_and_pod_get_contract(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _assert_envelope(client.post("/api/quotations", json={"id": "QT-DEL", "customer_id": "CUS-T1", "route_id": "RT-T1"}), "id", "QT-DEL")
    _assert_envelope(client.delete("/api/quotations/QT-DEL"), "id", "QT-DEL")
    _assert_envelope(client.post("/api/quotations", json={"id": "QT-APP", "customer_id": "CUS-T1", "route_id": "RT-T1"}), "id", "QT-APP")
    _assert_envelope(client.put("/api/quotations/QT-APP/approve"), "id", "QT-APP")
    workflow_builder.quotation("QT-C", approve=False)
    _assert_envelope(client.put("/api/quotations/QT-C/status", json={"status": "Approved"}), "id", "QT-C")
    workflow_builder.quotation("QT-SO", approve=True)
    _assert_envelope(client.post("/api/sales-orders", json={"id": "SO-DEL", "quotation_id": "QT-SO"}), "id", "SO-DEL")
    _assert_envelope(client.delete("/api/sales-orders/SO-DEL"), "id", "SO-DEL")
    workflow_builder.sales_order("SO-C", "QT-SO")
    _assert_envelope(client.put("/api/sales-orders/SO-C/confirm"), "id", "SO-C")
    workflow_builder.quotation("QT-S", approve=True)
    workflow_builder.sales_order("SO-S", "QT-S")
    _assert_envelope(client.put("/api/sales-orders/SO-S/status", json={"status": "Confirmed"}), "id", "SO-S")
    workflow_builder.quotation("QT-DO", approve=True)
    workflow_builder.sales_order("SO-DO", "QT-DO", confirm=True)
    _assert_envelope(client.post("/api/delivery-orders", json={"id": "DO-DEL", "so_id": "SO-DO"}), "id", "DO-DEL")
    _assert_envelope(client.delete("/api/delivery-orders/DO-DEL"), "id", "DO-DEL")
    workflow_builder.delivery_order("DO-RUN", "SO-DO")
    _assert_envelope(client.put("/api/delivery-orders/DO-RUN/dispatch", json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"}), "id", "DO-RUN")
    pod = client.get("/api/pod/DO-RUN")
    assert pod.status_code == 404
    assert pod.json()["error"]["code"] == "POD_NOT_FOUND"
