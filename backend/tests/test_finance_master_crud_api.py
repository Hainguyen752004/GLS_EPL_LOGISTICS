def _ok(client, method, path, payload=None):
    call = getattr(client, method)
    response = call(path, json=payload) if payload is not None else call(path)
    assert response.status_code == 200, response.text
    return response.json()


def test_finance_master_crud_endpoints_cover_all_demo_tabs(app_client):
    client, _, _ = app_client

    _ok(client, "post", "/api/master-data/tax-codes", {
        "code": "VAT8", "rate": "0.08", "mode": "exclusive", "effective_from": "2026-01-01"
    })
    _ok(client, "put", "/api/master-data/tax-codes/VAT8", {
        "rate": "0.1", "mode": "exclusive", "effective_from": "2026-01-01"
    })
    _ok(client, "post", "/api/master-data/tax-codes/VAT8/status", {"is_active": False})
    _ok(client, "post", "/api/master-data/tax-codes/VAT8/status", {"is_active": True})
    _ok(client, "delete", "/api/master-data/tax-codes/VAT8")

    _ok(client, "post", "/api/master-data/accounting-periods", {
        "id": "2026-08", "starts_at": "2026-08-01T00:00:00", "ends_at": "2026-08-31T23:59:59",
        "status": "open",
    })
    _ok(client, "put", "/api/master-data/accounting-periods/2026-08", {
        "starts_at": "2026-08-01T00:00:00", "ends_at": "2026-08-31T23:59:59", "status": "open",
    })
    _ok(client, "post", "/api/master-data/accounting-periods/2026-08/status", {"status": "closed"})
    _ok(client, "post", "/api/master-data/accounting-periods/2026-08/status", {"status": "open"})
    _ok(client, "delete", "/api/master-data/accounting-periods/2026-08")

    _ok(client, "post", "/api/tms/carriers", {
        "id": "CARRIER-DEMO", "name": "Carrier Demo", "is_internal": True, "status": "active"
    })
    _ok(client, "put", "/api/tms/carriers/CARRIER-DEMO", {
        "name": "Carrier Demo Updated", "is_internal": False, "status": "active"
    })
    _ok(client, "post", "/api/tms/carriers/CARRIER-DEMO/status", {"status": "inactive"})
    _ok(client, "post", "/api/tms/carriers/CARRIER-DEMO/status", {"status": "active"})
    _ok(client, "delete", "/api/tms/carriers/CARRIER-DEMO")

    _ok(client, "post", "/api/master-data/account-mappings", {
        "mapping_key": "ap.freight.payable", "account_code": "3311", "effective_from": "2026-01-01T00:00:00"
    })
    _ok(client, "put", "/api/master-data/account-mappings/ap.freight.payable", {
        "account_code": "3312", "effective_from": "2026-01-01T00:00:00"
    })
    _ok(client, "post", "/api/master-data/account-mappings/ap.freight.payable/status", {"status": "inactive"})
    _ok(client, "post", "/api/master-data/account-mappings/ap.freight.payable/status", {"status": "active"})
    _ok(client, "delete", "/api/master-data/account-mappings/ap.freight.payable")
