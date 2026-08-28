import importlib
from decimal import Decimal


def _seed_invoice_source(client, delivered=True):
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.Customer(id="CUS-AR-001", name="Khach hang AR"))
        db.commit()
        db.add(models.SalesOrder(
            id="SO-AR-001",
            customer_id="CUS-AR-001",
            canonical_status="confirmed",
            status="Confirmed",
            currency_code="VND",
            exchange_rate_snapshot=Decimal("1"),
            tax_rate_snapshot=Decimal("10"),
            total_amount=Decimal("4200000"),
        ))
        db.commit()
        db.add(models.DeliveryOrder(
            id="DO-AR-001",
            so_id="SO-AR-001",
            customer_id="CUS-AR-001",
            canonical_status="delivered" if delivered else "pending",
            status="Delivered" if delivered else "Pending",
        ))
        db.commit()


def test_ar_invoice_uses_persisted_contract_amount_and_reads_back(app_client):
    client, _, _ = app_client
    _seed_invoice_source(client)

    response = client.post(
        "/api/invoices/post",
        json={
            "id": "INV-AR-001",
            "do_id": "DO-AR-001",
            "posted_at": "2026-08-20T08:30:00+07:00",
        },
        headers={"Idempotency-Key": "invoice-ar-001"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["id"] == "INV-AR-001"
    assert payload["do_id"] == "DO-AR-001"
    assert payload["canonical_status"] == "posted"
    assert payload["amount"] == 4200000.0
    assert payload["vat_amount"] == 420000.0
    assert payload["total"] == 4620000.0
    assert payload["posted_at"].endswith("Z")

    loaded = client.get("/api/invoices")
    assert loaded.status_code == 200
    rows = loaded.json()
    rows = rows.get("items", rows) if isinstance(rows, dict) else rows
    assert [row["id"] for row in rows] == ["INV-AR-001"]

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        invoice = db.get(models.ARInvoice, "INV-AR-001")
        assert invoice.amount == Decimal("4200000.000000")
        assert invoice.vat_amount == Decimal("420000.000000")
        assert invoice.total == Decimal("4620000.000000")
        assert db.query(models.JournalBatch).filter_by(
            source_type="ar_invoice", source_id="INV-AR-001"
        ).count() == 1
        assert db.query(models.JournalLine).count() == 3


def test_ar_invoice_post_is_idempotent_per_delivery_order(app_client):
    client, _, _ = app_client
    _seed_invoice_source(client)
    request = {
        "id": "INV-AR-REPLAY",
        "do_id": "DO-AR-001",
        "posted_at": "2026-08-20T08:30:00Z",
    }

    first = client.post(
        "/api/invoices/post", json=request,
        headers={"Idempotency-Key": "invoice-ar-replay"},
    )
    replay = client.post(
        "/api/invoices/post", json=request,
        headers={"Idempotency-Key": "invoice-ar-replay"},
    )

    assert first.status_code == replay.status_code == 200
    assert first.json()["data"]["id"] == replay.json()["data"]["id"]
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.query(models.ARInvoice).count() == 1
        assert db.query(models.JournalBatch).count() == 1
        assert db.query(models.JournalLine).count() == 3


def test_ar_invoice_rejects_untrusted_totals_unknown_fields_and_naive_time(app_client):
    client, _, _ = app_client
    _seed_invoice_source(client)
    base = {
        "id": "INV-AR-INVALID",
        "do_id": "DO-AR-001",
        "posted_at": "2026-08-20T08:30:00+07:00",
    }

    assert client.post("/api/invoices/post", json={**base, "total": 1}).status_code == 422
    assert client.post("/api/invoices/post", json={**base, "approved": True}).status_code == 422
    assert client.post("/api/invoices/post", json={
        **base, "posted_at": "2026-08-20T08:30:00",
    }).status_code == 422


def test_ar_invoice_requires_delivered_delivery_order(app_client):
    client, _, _ = app_client
    _seed_invoice_source(client, delivered=False)

    response = client.post("/api/invoices/post", json={
        "do_id": "DO-AR-001",
        "posted_at": "2026-08-20T08:30:00+07:00",
    })

    assert response.status_code == 409


def test_ar_invoice_journal_converts_foreign_currency_to_functional_currency(app_client):
    client, _, _ = app_client
    _seed_invoice_source(client)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.merge(models.CurrencyDefinition(code="VND", minor_units=0, is_active=True))
        db.merge(models.CurrencyDefinition(code="USD", minor_units=2, is_active=True))
        db.merge(models.FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
        order = db.get(models.SalesOrder, "SO-AR-001")
        order.currency_code = "USD"
        order.exchange_rate_snapshot = Decimal("25000")
        order.total_amount = Decimal("100")
        db.commit()

    response = client.post("/api/invoices/post", json={
        "id": "INV-AR-FX", "do_id": "DO-AR-001",
        "posted_at": "2026-08-20T08:30:00+07:00",
    })
    assert response.status_code == 200, response.text
    with database.SessionLocal() as db:
        lines = db.query(models.JournalLine).order_by(models.JournalLine.id).all()
        receivable, revenue, vat = lines
        assert receivable.transaction_amount == Decimal("110.000000")
        assert receivable.debit == Decimal("2750000.000000")
        assert revenue.credit == Decimal("2500000.000000")
        assert vat.credit == Decimal("250000.000000")
        assert all(line.currency_code == "VND" for line in lines)
        assert all(line.transaction_currency == "USD" for line in lines)
