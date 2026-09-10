from conftest import ket_noi_du_lieu
def test_data_all_feeds_tms_cockpit_sections(app_client):
    client, _, _ = app_client

    response = client.get("/api/data/all")

    assert response.status_code == 200
    payload = response.json()
    for key in [
        "tax_codes",
        "accounting_periods",
        "carriers",
        "account_mappings",
        "freight_actual_costs",
        "ap_invoices",
        "settlements",
        "freight_orders",
        "tenders",
        "tender_offers",
        "transport_events",
        "pods",
        "roles",
        "users",
        "audit_logs",
    ]:
        assert key in payload
        assert isinstance(payload[key], list)


def test_data_all_redacts_role_user_and_audit_data(app_client):
    import sqlite3

    client, database_file, _ = app_client
    with ket_noi_du_lieu(database_file) as connection:
        connection.execute("INSERT INTO roles(id, permissions) VALUES (?, ?)", ("BROKEN", "{not-json"))
        connection.execute("INSERT INTO users(id, username, role_id) VALUES (?, ?, ?)", ("u1", "demo.user", "BROKEN"))
        connection.execute(
            "INSERT INTO audit_logs(user_id, action, table_name, record_id, timestamp, ip_address) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)",
            ("u1", "demo_action", "delivery_orders", "DO-1", "127.0.0.1"),
        )

    response = client.get("/api/data/all")

    assert response.status_code == 200
    payload = response.json()
    assert payload["roles"] == []
    assert payload["users"] == []
    assert payload["audit_logs"] == []


def test_data_all_serializes_nonempty_freight_orders_from_real_model_fields(app_client):
    import datetime as dt
    import importlib

    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add_all([
            models.Location(id="LOC-A", name="Kho A"),
            models.Location(id="LOC-B", name="Cang B"),
        ])
        db.flush()
        db.add(models.FreightOrder(
            id="FO-DASHBOARD",
            pickup_location_id="LOC-A",
            delivery_location_id="LOC-B",
            pickup_window_start=dt.datetime(2026, 8, 25, 8),
            pickup_window_end=dt.datetime(2026, 8, 25, 9),
            delivery_window_start=dt.datetime(2026, 8, 25, 12),
            delivery_window_end=dt.datetime(2026, 8, 25, 13),
            total_weight_kg=8500,
            total_volume_m3=24,
            total_pallet_count=18,
            max_weight_kg=28000,
            max_volume_m3=33.2,
            max_pallet_count=22,
        ))
        db.commit()

    response = client.get("/api/data/all")

    assert response.status_code == 200
    order = next(row for row in response.json()["freight_orders"] if row["id"] == "FO-DASHBOARD")
    assert order == {
        "id": "FO-DASHBOARD",
        "status": "planned",
        "pickup_location_id": "LOC-A",
        "delivery_location_id": "LOC-B",
        "total_weight_kg": 8500.0,
        "total_volume_m3": 24.0,
        "total_pallet_count": 18,
        "version": 1,
    }
