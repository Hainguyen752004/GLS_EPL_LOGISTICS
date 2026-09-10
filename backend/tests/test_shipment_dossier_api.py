def test_delivery_order_dossier_is_scoped_to_requested_order(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation(id="QT-DOSSIER-A", approve=True)
    workflow_builder.delivery_order(id="DO-DOSSIER-A", quotation_id="QT-DOSSIER-A")

    response = client.get("/api/delivery-orders/DO-DOSSIER-A/dossier")

    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload["delivery_orders"]] == ["DO-DOSSIER-A"]
    assert [row["id"] for row in payload["quotations"]] == ["QT-DOSSIER-A"]
    assert payload["freight_actual_costs"] == []
    assert payload["ap_invoices"] == []
    assert payload["settlements"] == []


def test_delivery_order_dossier_returns_not_found_for_unknown_order(app_client):
    client, _, _ = app_client
    response = client.get("/api/delivery-orders/DO-NOT-FOUND/dossier")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DELIVERY_ORDER_NOT_FOUND"


def test_broad_bootstrap_does_not_expose_finance_identity_or_audit_data(app_client, workflow_builder):
    client, _, _ = app_client
    import importlib

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    workflow_builder.master_data()
    workflow_builder.quotation(id="QT-BOOTSTRAP-SEC", approve=True)
    workflow_builder.delivery_order(id="DO-BOOTSTRAP-SEC", quotation_id="QT-BOOTSTRAP-SEC")
    with database.SessionLocal() as db:
        db.add(models.Role(id="SEC-FINANCE", permissions='["finance_read"]'))
        db.add(models.User(id="sec-user", username="sec-user", role_id="SEC-FINANCE"))
        db.add(models.AuditLog(
            user_id="sec-user",
            action="READ_FINANCE",
            table_name="ar_invoices",
            record_id="INV-BOOTSTRAP-SEC",
            ip_address="127.0.0.1",
        ))
        db.add(models.ARInvoice(
            id="INV-BOOTSTRAP-SEC",
            do_id="DO-BOOTSTRAP-SEC",
            customer_id="CUS-T1",
            invoice_date="2026-08-27",
            amount=100000,
            vat_pct=0,
            vat_amount=0,
            total=100000,
            status="Posted",
        ))
        db.commit()

    response = client.get("/api/data/all")

    assert response.status_code == 200
    payload = response.json()
    for key in ("invoices", "freight_actual_costs", "ap_invoices", "settlements", "roles", "users", "audit_logs"):
        assert payload[key] == [], f"{key} must be loaded from its authorized module endpoint"
