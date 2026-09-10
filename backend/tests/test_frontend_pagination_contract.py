from pathlib import Path


APP_JS = Path(__file__).resolve().parents[2] / "frontend" / "js" / "app.js"


def test_primary_workflow_loaders_consume_canonical_paginated_items():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function paginatedItems(payload)" in source
    assert "crmQuotations = data;" in source
    assert "eplDeliveryOrders = await fetchAllPaginated(`${API_BASE}/api/delivery-orders`)" in source
    assert "trips = paginatedItems(payload)" in source
    assert "fetchAllPaginated(`${API_BASE}/api/quotations`, 200)" in source


def test_delivery_order_secondary_loaders_do_not_treat_page_as_array():
    source = APP_JS.read_text(encoding="utf-8")

    assert "fetchAllPaginated(`${API_BASE}/api/delivery-orders`, 200)" in source
    assert "const dos = paginatedItems(await resDo.json())" in source
    assert "fetchAllPaginated(`${API_BASE}/api/delivery-orders`, 200).catch(() => null)" in source
    assert "eplDeliveryOrders = Array.isArray(deliveryOrders) ? deliveryOrders : []" in source
