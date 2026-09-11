# -*- coding: utf-8 -*-
"""Đóng / mở lại sự cố từ phiếu ở màn Theo dõi.

1. Đóng mà không ghi cách xử lý -> 422, sự cố vẫn mở.
2. Đóng có ghi chú -> Resolved; ghi chú, người và giờ nối vào mô tả;
   KPI "có sự cố mở" của tháp theo dõi về 0.
3. Mở lại -> Open, KPI lên 1.
4. Trạng thái lạ -> 422; id không có -> 404.
"""
import importlib

from conftest import API_TEST_HEADERS

GIO = dict(API_TEST_HEADERS)


def _su_co(client):
    m = importlib.import_module('models')
    database = importlib.import_module('database')
    with database.SessionLocal() as db:
        db.add(m.Vehicle(id='SC-V'))
        db.flush()
        db.add(m.DeliveryOrder(id='SC-DO', canonical_status='in_transit', vehicle_id='SC-V'))
        db.commit()
    r = client.post('/api/incidents', json={'do_id': 'SC-DO', 'vehicle_id': 'SC-V', 'incident_type': 'Hỏng xe',
                                            'location': 'Bến Lức', 'reporter': 'Tài xế', 'description': 'Nổ lốp'}, headers=GIO)
    assert r.status_code == 200, r.text
    return r.json()['data']


def test_dong_su_co_phai_ghi_cach_xu_ly_va_doi_kpi(app_client):
    client, _, _ = app_client
    inc = _su_co(client)
    assert client.get('/api/tracking/control-tower', headers=GIO).json()['kpis']['incidents'] == 1

    r = client.put(f"/api/incidents/{inc['id']}/status", json={'status': 'Resolved'}, headers=GIO)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'INCIDENT_NOTE_REQUIRED'

    r = client.put(f"/api/incidents/{inc['id']}/status",
                   json={'status': 'Resolved', 'note': 'Thay lốp dự phòng, xe chạy tiếp 10:40'}, headers=GIO)
    assert r.status_code == 200, r.text
    d = r.json()['data']
    assert d['status'] == 'Resolved'
    assert 'Nổ lốp' in d['description'] and 'Thay lốp dự phòng' in d['description'] and 'Đã xử lý' in d['description']
    assert client.get('/api/tracking/control-tower', headers=GIO).json()['kpis']['incidents'] == 0
    danh_sach = client.get('/api/incidents', headers=GIO).json()
    assert any(x['id'] == inc['id'] and x['status'] == 'Resolved' for x in danh_sach)

    r = client.put(f"/api/incidents/{inc['id']}/status", json={'status': 'Open', 'note': 'Xe lại báo rung'}, headers=GIO)
    assert r.status_code == 200 and r.json()['data']['status'] == 'Open'
    assert client.get('/api/tracking/control-tower', headers=GIO).json()['kpis']['incidents'] == 1


def test_dong_su_co_tu_choi_dau_vao_sai(app_client):
    client, _, _ = app_client
    inc = _su_co(client)
    r = client.put(f"/api/incidents/{inc['id']}/status", json={'status': 'Done', 'note': 'x'}, headers=GIO)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'INCIDENT_STATUS_INVALID'
    r = client.put('/api/incidents/999999/status', json={'status': 'Resolved', 'note': 'x'}, headers=GIO)
    assert r.status_code == 404
