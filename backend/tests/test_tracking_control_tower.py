import importlib
from datetime import datetime, timedelta, timezone


def test_tower_keeps_orders_without_gps_and_distinguishes_stale(app_client):
    client, _, _ = app_client
    models = importlib.import_module('models')
    database = importlib.import_module('database')
    with database.SessionLocal() as db:
        db.add_all([
            models.DeliveryOrder(id='CT-NONE', canonical_status='in_transit'),
            models.DeliveryOrder(id='CT-STALE', canonical_status='arrived'),
            models.DeliveryOrder(id='CT-DONE', canonical_status='delivered'),
        ])
        db.flush()
        db.add(models.VehicleTracking(do_id='CT-STALE', lat=10.7, lng=106.7,
            speed_kmh=0, last_update=datetime.now(timezone.utc) - timedelta(hours=1)))
        db.commit()
    response = client.get('/api/tracking/control-tower')
    assert response.status_code == 200, response.text
    result = response.json()
    rows = {row['do_id']: row for row in result['items']}
    assert set(rows) == {'CT-NONE', 'CT-STALE'}
    assert rows['CT-NONE']['gps']['status'] == 'missing'
    assert rows['CT-NONE']['gps']['lat'] is None
    assert rows['CT-NONE']['gps']['speed_kmh'] is None
    assert rows['CT-STALE']['gps']['status'] == 'stale'
    assert rows['CT-STALE']['gps']['speed_kmh'] == 0
    assert result['kpis']['gps_unavailable'] == 2
    assert result['kpis']['awaiting_pod'] == 1


def test_tower_missing_coordinates_never_become_zero(app_client):
    client, _, _ = app_client
    models = importlib.import_module('models')
    database = importlib.import_module('database')
    with database.SessionLocal() as db:
        db.add(models.DeliveryOrder(id='CT-NULL', canonical_status='in_transit'))
        db.flush()
        db.add(models.VehicleTracking(do_id='CT-NULL', lat=None, lng=None, speed_kmh=0))
        db.commit()
    response = client.get('/api/tracking/control-tower')
    assert response.status_code == 200, response.text
    row = response.json()['items'][0]
    assert row['gps']['status'] == 'missing'
    assert row['gps']['speed_kmh'] is None
    assert row['predicted_eta'] is None
    assert row['deviation_km'] is None


def test_tower_enriches_known_route_segments_with_reference_coordinates(app_client):
    client, _, _ = app_client
    m = importlib.import_module('models')
    database = importlib.import_module('database')
    tracking_control_service = importlib.import_module('services.tracking_control_service')
    assert tracking_control_service.normalize_location('Vành đai 3') == 'vanh dai 3'
    with database.SessionLocal() as db:
        db.add(m.Route(id='CT-RT', name='VSIP II-A -> Cat Lai', distance_km=44.7, segments_json='''[
            {"origin":"Kho VSIP II-A, Binh Duong","destination":"Vanh dai 3","distance_km":18.2},
            {"origin":"Vanh dai 3","destination":"Cang Cat Lai, TP. Thu Duc","distance_km":26.5}
        ]'''))
        db.flush()
        db.add(m.DeliveryOrder(id='CT-ROUTE', canonical_status='in_transit', route_id='CT-RT'))
        db.commit()
    response = client.get('/api/tracking/control-tower')
    assert response.status_code == 200, response.text
    segments = response.json()['items'][0]['route_segments']
    assert segments[0]['origin_lat'] == 11.0497
    assert segments[0]['origin_lng'] == 106.7428
    assert segments[0]['destination_lat'] == 10.8769
    assert segments[0]['destination_lng'] == 106.7734
    assert segments[1]['origin_lat'] == 10.8769
    assert segments[1]['origin_lng'] == 106.7734
    assert segments[1]['destination_lat'] == 10.7567
    assert segments[1]['destination_lng'] == 106.7828


def test_trip_positions_do_not_leak_between_trucks_and_return_stays_visible(app_client):
    client, _, _ = app_client
    m = importlib.import_module('models')
    database = importlib.import_module('database')
    now = datetime.now(timezone.utc)
    with database.SessionLocal() as db:
        db.add(m.Location(id='CT-LOC', name='Test location'))
        db.add_all([m.Vehicle(id='CT-V1'), m.Vehicle(id='CT-V2')])
        db.flush()
        db.add(m.FreightOrder(id='CT-FO', pickup_location_id='CT-LOC', delivery_location_id='CT-LOC',
            pickup_window_start=now, pickup_window_end=now, delivery_window_start=now,
            delivery_window_end=now, max_weight_kg=1000, max_volume_m3=10, max_pallet_count=10))
        db.add(m.DeliveryOrder(id='CT-RETURN', canonical_status='delivered'))
        db.flush()
        for i in [1, 2]:
            db.add(m.TransportTrip(id=f'CT-T{i}', freight_order_id='CT-FO', status='in_transit', vehicle_id=f'CT-V{i}'))
        db.flush()
        for i in [1, 2]:
            db.add(m.TripDeliveryOrder(trip_id=f'CT-T{i}', do_id='CT-RETURN'))
        db.add(m.VehicleTracking(do_id='CT-RETURN', vehicle_id='CT-V1', lat=10, lng=106, last_update=now))
        db.add(m.TransportEvent(id='CT-E', freight_order_id='CT-FO', trip_id='CT-T2', event_type='gps_ping',
            event_time=now, lat=11, lng=107, source='device', idempotency_key='CT-E', payload_hash='test', recorded_by='test'))
        db.commit()
    result = client.get('/api/tracking/control-tower').json()
    rows = {r['trip_id']: r for r in result['items']}
    assert set(rows) == {'CT-T1', 'CT-T2'}
    assert rows['CT-T1']['gps']['status'] == 'missing'
    assert rows['CT-T2']['gps']['lat'] == 11
    assert rows['CT-T2']['gps']['status'] == 'fresh'
    assert rows['CT-T1']['events'] == []
    assert len(rows['CT-T2']['events']) == 1
    assert result['kpis']['returning'] == 2


def test_incident_persists_and_rejects_unknown_order(app_client):
    client, _, _ = app_client
    m = importlib.import_module('models')
    database = importlib.import_module('database')
    with database.SessionLocal() as db:
        db.add_all([m.Vehicle(id='CT-V'), m.Vehicle(id='CT-OTHER')])
        db.flush()
        db.add(m.DeliveryOrder(id='CT-INC', canonical_status='in_transit', vehicle_id='CT-V'))
        db.commit()
    payload = {'do_id': 'CT-INC', 'vehicle_id': 'CT-V', 'incident_type': 'Traffic', 'location': 'Test', 'reporter': 'Tester'}
    assert client.post('/api/incidents', json=payload).status_code == 200
    result = client.get('/api/tracking/control-tower').json()
    assert result['kpis']['incidents'] == 1
    assert result['items'][0]['incidents'][0]['incident_type'] == 'Traffic'
    payload['do_id'] = 'MISSING-DO'
    assert client.post('/api/incidents', json=payload).status_code == 404
    payload['do_id'] = 'CT-INC'
    payload['vehicle_id'] = 'CT-OTHER'
    assert client.post('/api/incidents', json=payload).status_code == 409
    payload['reporter'] = '   '
    assert client.post('/api/incidents', json=payload).status_code == 422
