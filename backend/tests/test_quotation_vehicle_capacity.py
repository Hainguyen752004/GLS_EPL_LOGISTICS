def _seed_quote_master(client):
    assert client.post('/api/customers', json={'id': 'CUS-CAP-QT', 'name': 'Capacity Customer'}).status_code in (200, 201)
    assert client.post('/api/routes', json={'id': 'RT-CAP-QT', 'name': 'Capacity Route', 'distance_km': 10, 'segments_json': '[]'}).status_code in (200, 201)


def test_quotation_rejects_vehicle_type_below_cargo_weight(app_client):
    client, _, _ = app_client
    _seed_quote_master(client)
    response = client.post('/api/vehicle-types', json={
        'id': 'VT-20T', 'name': 'Xe 20 tan', 'maxWeight': 20000,
        'volumeCapacityM3': 40, 'palletCapacity': 20,
    })
    assert response.status_code == 200

    response = client.post('/api/quotations', json={
        'id': 'QT-OVERLOAD', 'customer_id': 'CUS-CAP-QT', 'route_id': 'RT-CAP-QT',
        'cargo_type': 'Xe 20 tan', 'weight_kg': 30000, 'volume_m3': 20, 'pallet_count': 10,
    })

    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'CAPACITY_EXCEEDED'


def test_vehicle_type_recommendations_only_return_sufficient_types_in_best_fit_order(app_client):
    client, _, _ = app_client
    for payload in (
        {'id': 'VT-40T', 'name': 'Xe 40 tan', 'maxWeight': 40000, 'volumeCapacityM3': 60, 'palletCapacity': 30},
        {'id': 'VT-35T', 'name': 'Xe 35 tan', 'maxWeight': 35000, 'volumeCapacityM3': 50, 'palletCapacity': 24},
        {'id': 'VT-20T', 'name': 'Xe 20 tan', 'maxWeight': 20000, 'volumeCapacityM3': 40, 'palletCapacity': 20},
    ):
        assert client.post('/api/vehicle-types', json=payload).status_code == 200
    assert client.post('/api/vehicles', json={
        'id': '51C-CAP-35', 'brand': 'Test', 'type': 'Xe 35 tan',
        'weight_capacity': 35000, 'volumeCapacityM3': 50, 'palletCapacity': 24,
    }).status_code == 200

    response = client.get('/api/vehicle-types/recommendations', params={
        'weight_kg': 30000, 'volume_m3': 20, 'pallet_count': 10,
    })

    assert response.status_code == 200
    data = response.json()['data']
    assert [item['id'] for item in data['suitable']] == ['VT-35T', 'VT-40T']
    assert [item['id'] for item in data['unsuitable']] == ['VT-20T']
    assert data['suitable'][0]['ready_vehicle_count'] == 1
    assert data['suitable'][0]['ready_vehicle_ids'] == ['51C-CAP-35']
