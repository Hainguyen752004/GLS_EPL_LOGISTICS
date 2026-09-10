import json


def test_fleet_comparison_endpoint_returns_real_vehicle_and_audit(app_client):
    client, _, _ = app_client
    import database
    from models import Vehicle
    with database.SessionLocal() as db:
        db.add(Vehicle(id='COMPARE-V1',type='COMPARE-TYPE'))
        db.commit()
    result=client.post('/api/cost-formulas',json={'vehicle_type_id':'COMPARE-TYPE','terms':[{'key':'fuel','rate':4800}]})
    assert result.status_code == 200
    saved=client.put('/api/vehicles/COMPARE-V1/cost-overrides',json={'overrides':[{'component':'fuel','value':5200,'note':'Older vehicle'}]})
    assert saved.status_code == 200
    response=client.get('/api/cost-formulas/fleet-overview')
    assert response.status_code == 200
    data=response.json()['data']
    vehicle=next(v for v in data['vehicles'] if v['vehicle_id']=='COMPARE-V1')
    assert vehicle['terms'][0]['rate'] == 5200
    assert any(h['vehicle_id']=='COMPARE-V1' and '5200' in h['message'] for h in data['history'])


def test_formula_rejects_stale_editor_and_records_actor(app_client):
    client, _, _ = app_client
    body = {'vehicle_type_id': 'CONCURRENT-CF', 'terms': [{'key':'fuel','rate':4800}]}
    first = client.post('/api/cost-formulas', json=body)
    assert first.status_code == 200
    token = first.json()['data']['updated_at']
    second = client.post('/api/cost-formulas', json={**body,
        'expected_updated_at':token,'terms':[{'key':'fuel','rate':5000}]})
    assert second.status_code == 200
    stale = client.post('/api/cost-formulas', json={**body,'expected_updated_at':token})
    assert stale.status_code == 409
    row = next(r for r in client.get('/api/cost-formulas').json() if r['vehicle_type_id']=='CONCURRENT-CF')
    assert row['terms'][0]['rate'] == 5000
    assert row['history'][0]['actor']


def test_expressions_roundtrip_and_server_evaluation(app_client):
    client, _, _ = app_client
    expressions = {"COST": "fuel * km", "REV": "max(rate * kg, 2500000)", "PROFIT": "REV - COST"}
    response = client.post('/api/cost-formulas', json={
        'vehicle_type_id': 'EXPRESSION-TEST', 'currency':'VND',
        'terms':[{'key':'fuel','rate':4800},{'key':'rate','rate':1200}], 'expressions':expressions,
    })
    assert response.status_code == 200, response.text
    formula_id = response.json()['data']['id']
    row = next(r for r in client.get('/api/cost-formulas').json() if r['id'] == formula_id)
    assert row['expressions'] == expressions
    preview = client.post('/api/cost-formulas/evaluate', json={'formula_id':formula_id,'trip':{'km':100,'tonnes':0}})
    assert preview.status_code == 200, preview.text
    assert preview.json()['data']['revenue'] == 2500000
    assert preview.json()['data']['cost'] == 480000
    rejected = client.post('/api/cost-formulas', json={
        'vehicle_type_id':'EXPRESSION-TEST','expressions':{**expressions,'COST':'fuel / 0'},
        'terms':[{'key':'fuel','rate':4800},{'key':'rate','rate':1200}],
    })
    assert rejected.status_code == 422
    row = next(r for r in client.get('/api/cost-formulas').json() if r['id'] == formula_id)
    assert row['expressions'] == expressions


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
    from routes.delivery_routes import _select_closeout_formula

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
    from routes.delivery_routes import _select_closeout_formula

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
