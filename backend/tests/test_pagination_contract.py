import pytest


@pytest.mark.parametrize(
    "path",
    ["/api/quotations", "/api/sales-orders", "/api/delivery-orders", "/api/tms/trips"],
)
def test_primary_workflow_lists_use_bounded_pagination(app_client, path):
    client, _, _ = app_client

    response = client.get(path, params={"page": 1, "page_size": 200})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"items", "total", "page", "page_size"}
    assert payload["page"] == 1
    assert payload["page_size"] == 200
    assert isinstance(payload["items"], list)
    assert isinstance(payload["total"], int)

    too_large = client.get(path, params={"page_size": 201})
    assert too_large.status_code == 422


def test_quotation_pagination_is_stable_and_reports_total(workflow_builder, app_client):
    client, _, _ = app_client
    workflow_builder.master_data()
    for quote_id in ("QT-PAGE-001", "QT-PAGE-003", "QT-PAGE-002"):
        workflow_builder.quotation(id=quote_id)

    first = client.get("/api/quotations", params={"page": 1, "page_size": 2}).json()
    second = client.get("/api/quotations", params={"page": 2, "page_size": 2}).json()

    assert first["total"] == second["total"] == 3
    assert [row["id"] for row in first["items"]] == ["QT-PAGE-003", "QT-PAGE-002"]
    assert [row["id"] for row in second["items"]] == ["QT-PAGE-001"]


def test_route_list_supports_paginated_master_data_loading(app_client):
    client, _, _ = app_client

    response = client.get(
        "/api/routes",
        params={"paginated": True, "page": 1, "page_size": 200},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"items", "total", "page", "page_size"}
    assert payload["page"] == 1
    assert payload["page_size"] == 200
    assert isinstance(payload["items"], list)
    assert isinstance(payload["total"], int)
