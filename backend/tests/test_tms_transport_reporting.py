import datetime as dt
import importlib
import json
from decimal import Decimal


def _seed_reporting_case(app_client, *, invoice_status="posted"):
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add_all([
            models.CurrencyDefinition(code="VND", minor_units=0),
            models.CurrencyDefinition(code="LAK", minor_units=0),
            models.CurrencyDefinition(code="THB", minor_units=2),
            models.CurrencyDefinition(code="USD", minor_units=2),
            models.CurrencyDefinition(code="CNY", minor_units=2),
            models.FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
            models.CurrencyRateHistory(
                currency_code="LAK", functional_currency="VND",
                rate_date=dt.date(2026, 8, 21), rate=Decimal("1.25"), source="BOL",
            ),
            models.CurrencyRateHistory(
                currency_code="THB", functional_currency="VND",
                rate_date=dt.date(2026, 8, 21), rate=Decimal("720"), source="BOL",
            ),
            models.CurrencyRateHistory(
                currency_code="USD", functional_currency="VND",
                rate_date=dt.date(2026, 8, 21), rate=Decimal("25000"), source="BOL",
            ),
            models.CurrencyRateHistory(
                currency_code="CNY", functional_currency="VND",
                rate_date=dt.date(2026, 8, 21), rate=Decimal("3500"), source="BOL",
            ),
            models.Role(
                id="REPORTING",
                permissions=json.dumps(["finance_read", "finance_creator"]),
            ),
            models.User(id="report-user", username="report-user", role_id="REPORTING"),
            models.Customer(id="CUS-RPT", name="Bai Inve"),
            models.Route(id="RT-RPT", name="EPL - Thanaleng", distance_km=42.5),
            models.Location(id="LOC-A", name="Cong ty EPL", type="Warehouse"),
            models.Location(id="LOC-B", name="Thanaleng", type="Port"),
            models.Vehicle(
                id="LAO-341", type="HOWO-430", status="San sang",
                engine_no="7891 / 6921 / 970",
            ),
            models.Driver(
                id="DRV-RPT", name="Anh Van Dac", role="Lai xe chinh",
                assigned_vehicle="LAO-341", status="Ranh",
            ),
            models.Carrier(
                id="EPL-INTERNAL", name="EPL", status="active", is_internal=True,
            ),
        ])
        db.commit()
        db.add_all([
            models.SalesOrder(
                id="SO-RPT-001", canonical_status="confirmed", status="Confirmed",
                order_date="2026-08-20", delivery_date="2026-08-21",
                customer_id="CUS-RPT", route_id="RT-RPT",
                origin="Cong ty EPL", destination="Thanaleng",
                weight_kg=41230, total_amount=Decimal("1600000"),
                currency_code="VND", packaging_spec="Quang sat",
            ),
        ])
        db.commit()
        db.add_all([
            models.DeliveryOrder(
                id="DO-RPT-001", canonical_status="delivered", status="Da giao",
                so_id="SO-RPT-001", customer_id="CUS-RPT", route_id="RT-RPT",
                origin="Cong ty EPL", destination="Thanaleng",
                vehicle_id="LAO-341", driver_id="DRV-RPT", weight_kg=41230,
                pickup_date=dt.datetime(2026, 8, 21, 7, 30),
                delivery_date=dt.datetime(2026, 8, 21, 11, 30),
            ),
            models.DeliveryOrderDetail(
                so_id="SO-RPT-001", sku="ORE", description="Quang sat",
                qty=1, uom="Tnu", weight_kg=41230,
            ),
        ])
        db.commit()
        db.add_all([
            models.FreightOrder(
                id="FO-RPT-001", pickup_location_id="LOC-A", delivery_location_id="LOC-B",
                pickup_window_start=dt.datetime(2026, 8, 21, 7),
                pickup_window_end=dt.datetime(2026, 8, 21, 8),
                delivery_window_start=dt.datetime(2026, 8, 21, 11),
                delivery_window_end=dt.datetime(2026, 8, 21, 12),
                total_weight_kg=41230, total_volume_m3=1, total_pallet_count=1,
                max_weight_kg=50000, max_volume_m3=60, max_pallet_count=30,
                status="delivered",
            ),
        ])
        db.commit()
        db.add_all([
            models.TransportTrip(
                id="TRIP-RPT-001", freight_order_id="FO-RPT-001",
                trip_type="one_way", status="completed", vehicle_id="LAO-341",
                driver_id="DRV-RPT",
                actual_departure_at=dt.datetime(2026, 8, 21, 7, 30),
                actual_arrival_at=dt.datetime(2026, 8, 21, 11, 30),
            ),
        ])
        db.commit()
        db.add_all([
            models.TripDeliveryOrder(
                trip_id="TRIP-RPT-001", do_id="DO-RPT-001", allocation_sequence=1,
            ),
        ])
        db.commit()
        db.add_all([
            models.TransportTripLeg(
                id="LEG-RPT-001", trip_id="TRIP-RPT-001", do_id="DO-RPT-001",
                sequence_no=1, leg_type="delivery", origin="Cong ty EPL",
                destination="Thanaleng", distance_km=Decimal("42.5"),
                avg_speed_kmh=Decimal("45"), dwell_minutes=30, status="completed",
            ),
        ])
        db.commit()
        db.add_all([
            models.ARInvoice(
                id="INV-RPT-001", do_id="DO-RPT-001", customer_id="CUS-RPT",
                canonical_status=invoice_status, status=invoice_status.title(), is_active=True,
                invoice_date="2026-08-21", amount=Decimal("1600000"),
                vat_pct=Decimal("0"), vat_amount=Decimal("0"),
                total=Decimal("1600000"), currency_code="VND",
                exchange_rate_snapshot=Decimal("1"),
            ),
            models.FreightActualCost(
                id="COST-RPT-001", freight_order_id="FO-RPT-001",
                trip_id="TRIP-RPT-001", carrier_id="EPL-INTERNAL",
                currency_code="VND", functional_currency="VND",
                exchange_rate_snapshot=Decimal("1"),
                exchange_rate_date=dt.date(2026, 8, 21),
                exchange_rate_source="functional", planned_distance_km=Decimal("42.5"),
                actual_distance_km=Decimal("42.5"), subtotal_amount=Decimal("400000"),
                tax_amount=Decimal("0"), total_amount=Decimal("400000"),
                status="approved", is_active=True, created_by="maker", updated_by="checker",
                approved_by="checker", approved_at=dt.datetime(2026, 8, 21, 13),
            ),
        ])
        db.commit()
    return client, {"X-Test-Principal": "report-user"}


def test_transport_revenue_report_has_epl_columns_charts_and_recognized_totals(app_client):
    client, headers = _seed_reporting_case(app_client)

    response = client.get(
        "/api/tms/reporting/transport-revenue?date_from=2026-08-01&date_to=2026-08-31",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["summary"] == {
        "recognized_revenue": 1600000.0,
        "approved_cost": 400000.0,
        "gross_profit": 1200000.0,
        "margin_percent": 75.0,
        "trip_count": 1,
        "currency_code": "VND",
    }
    row = payload["rows"][0]
    assert row["dispatch_order_no"] == "DO-RPT-001"
    assert row["invoice_no"] == "INV-RPT-001"
    assert row["driver_name"] == "Anh Van Dac"
    assert row["tractor_plate"] == "LAO-341"
    assert row["cargo_type"] == "Quang sat"
    assert row["weight_tons"] == 41.23
    assert row["totals"]["VND"] == 1600000.0
    assert row["totals"]["LAK"] == 1280000.0
    assert row["totals"]["USD"] == 64.0
    assert "trailer_plate" in row["missing_fields"]
    assert payload["charts"]["trend"][0]["revenue"] == 1600000.0
    assert payload["charts"]["by_customer"][0]["label"] == "Bai Inve"


def test_transport_revenue_excludes_unposted_ar_from_recognized_totals(app_client):
    client, headers = _seed_reporting_case(app_client, invoice_status="draft")

    response = client.get("/api/tms/reporting/transport-revenue", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["summary"]["recognized_revenue"] == 0.0
    assert payload["summary"]["trip_count"] == 0
    assert payload["exceptions"][0]["code"] == "AR_NOT_POSTED"


def test_expense_voucher_persists_header_and_cost_lines(app_client):
    client, headers = _seed_reporting_case(app_client)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        cost = db.get(models.FreightActualCost, "COST-RPT-001")
        cost.status = "draft"
        cost.approved_by = None
        cost.approved_at = None
        db.commit()
    command_headers = {**headers, "Idempotency-Key": "voucher-rpt-001"}
    request = {
        "voucher_no": "T4-0428-08/EPL",
        "voucher_date": "2026-08-21",
        "do_id": "DO-RPT-001",
        "vehicle_manager": "Anh Phe",
        "payment_method": "cash",
        "contract_no": "HD-2026-08",
        "machine_numbers": "7891 / 6921 / 970",
        "checked_by": "Ke toan A",
        "note": "Chi phi chuyen quang sat",
        "currency_code": "VND",
        "carrier_id": "EPL-INTERNAL",
        "lines": [
            {
                "name": "Nhien lieu diesel",
                "original_amount": "19000000",
                "actual_amount": "19300150",
                "note": "695 lit",
            },
            {
                "name": "Chi phi boc xep hang hoa",
                "original_amount": "0",
                "actual_amount": "1833500",
            },
        ],
    }

    saved = client.put(
        "/api/tms/reporting/trips/TRIP-RPT-001/expense-voucher",
        json=request,
        headers=command_headers,
    )
    assert saved.status_code == 200, saved.text

    loaded = client.get(
        "/api/tms/reporting/expense-vouchers/TRIP-RPT-001",
        headers=headers,
    )
    assert loaded.status_code == 200, loaded.text
    data = loaded.json()["data"]
    assert data["voucher_no"] == "T4-0428-08/EPL"
    assert data["vehicle"]["plate"] == "LAO-341"
    assert data["vehicle"]["engine_no"] == "7891 / 6921 / 970"
    assert data["driver"]["name"] == "Anh Van Dac"
    assert data["customer"]["name"] == "Bai Inve"
    assert data["cost"]["total_amount"] == 21133650.0
    assert [line["name"] for line in data["cost"]["lines"]] == [
        "Nhien lieu diesel", "Chi phi boc xep hang hoa",
    ]
