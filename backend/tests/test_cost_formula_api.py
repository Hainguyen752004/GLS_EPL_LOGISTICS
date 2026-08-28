import json


def test_cost_formula_api_persists_currency_and_components(app_client):
    client, _, _ = app_client

    payload = {
        "id": "preset-1",
        "vehicle_type_id": "VT-20FT",
        "name": "Container 20FT",
        "currency": "USD",
        "fuel": "6,250",
        "driver": "500,000",
        "toll": "300,000",
        "warehouse": "200,000",
        "freight_rate": "1,500",
        "tokens": [{"code": "DISTANCE", "type": "var"}],
    }
    saved = client.post("/api/cost-formulas", json=payload)
    listed = client.get("/api/cost-formulas")

    assert saved.status_code == 200, saved.text
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json() if item["id"] == "vehicle-type::VT-20FT::USD")
    assert row["currency"] == "USD"
    assert row["vehicle_type_id"] == "VT-20FT"
    assert row["components"]["fuel"] == "6,250"
    assert row["components"]["warehouse"] == "200,000"

    import database
    import models

    with database.SessionLocal() as db:
        entity = db.get(models.CostFormula, "vehicle-type::VT-20FT::USD")
        assert entity is not None
        stored = json.loads(entity.formula_expression)
        assert stored["currency"] == "USD"
        assert stored["vehicle_type_id"] == "VT-20FT"
        assert stored["components"]["freight_rate"] == "1,500"


def test_cost_formula_api_keeps_vehicle_types_isolated(app_client):
    client, _, _ = app_client

    for vehicle_type_id, fuel in (("VT-TRUCK10", "4,800"), ("VT-20FT", "6,250")):
        response = client.post("/api/cost-formulas", json={
            "id": f"vehicle-type::{vehicle_type_id}",
            "vehicle_type_id": vehicle_type_id,
            "name": vehicle_type_id,
            "currency": "VND",
            "fuel": fuel,
        })
        assert response.status_code == 200, response.text

    rows = {row["vehicle_type_id"]: row for row in client.get("/api/cost-formulas").json() if row["vehicle_type_id"]}
    assert rows["VT-TRUCK10"]["components"]["fuel"] == "4,800"
    assert rows["VT-20FT"]["components"]["fuel"] == "6,250"


def test_cost_formula_api_keeps_currencies_isolated_for_same_vehicle_type(app_client):
    client, _, _ = app_client

    for currency, fuel in (("VND", "6250"), ("LAK", "12000"), ("USD", "0.30"), ("THB", "10.50")):
        response = client.post("/api/cost-formulas", json={
            "id": "client-id-must-not-control-storage",
            "vehicle_type_id": "VT-20FT",
            "name": "Container 20FT",
            "currency": currency,
            "fuel": fuel,
        })
        assert response.status_code == 200, response.text

    rows = {
        row["currency"]: row
        for row in client.get("/api/cost-formulas").json()
        if row["vehicle_type_id"] == "VT-20FT"
    }
    assert set(rows) == {"VND", "LAK", "USD", "THB"}
    assert rows["VND"]["id"] == "vehicle-type::VT-20FT::VND"
    assert rows["LAK"]["components"]["fuel"] == "12000"
    assert rows["USD"]["components"]["fuel"] == "0.30"
    assert rows["THB"]["components"]["fuel"] == "10.50"


def test_closeout_selects_formula_by_exact_vehicle_type_id(app_client):
    _, _, _ = app_client

    import database
    import models
    from main import _select_closeout_formula

    with database.SessionLocal() as db:
        db.merge(models.VehicleType(id="VT-TRUCK10", name="Xe tải thùng 10 tấn"))
        db.merge(models.Vehicle(id="TRUCK-01", type="Xe tải thùng 10 tấn"))
        db.merge(models.CostFormula(
            id="aaa-xetaithung10tan-legacy",
            name="Xe tải thùng 10 tấn legacy sai loại",
            formula_expression=json.dumps({"vehicle_type_id": "VT-20FT", "components": {"fuel": "9,500"}}),
        ))
        db.merge(models.CostFormula(
            id="formula-truck-private",
            name="Định mức vận hành nội bộ",
            formula_expression=json.dumps({"vehicle_type_id": "VT-TRUCK10", "components": {"fuel": "4,800"}}),
        ))
        db.commit()

        selected = _select_closeout_formula(db, models.DeliveryOrder(vehicle_id="TRUCK-01"))
        assert selected.id == "formula-truck-private"


def test_closeout_selects_formula_by_vehicle_type_and_currency(app_client):
    _, _, _ = app_client

    import database
    import models
    from main import _select_closeout_formula

    with database.SessionLocal() as db:
        db.merge(models.VehicleType(id="VT-20FT", name="Container 20FT"))
        db.merge(models.Vehicle(id="CONT-01", type="VT-20FT"))
        for currency, fuel in (("VND", "6250"), ("LAK", "12000")):
            db.merge(models.CostFormula(
                id=f"vehicle-type::VT-20FT::{currency}",
                name="Container 20FT",
                formula_expression=json.dumps({
                    "vehicle_type_id": "VT-20FT",
                    "currency": currency,
                    "components": {"fuel": fuel},
                }),
            ))
        db.commit()

        delivery_order = models.DeliveryOrder(vehicle_id="CONT-01")
        selected = _select_closeout_formula(db, delivery_order, "LAK")
        assert selected.id == "vehicle-type::VT-20FT::LAK"
