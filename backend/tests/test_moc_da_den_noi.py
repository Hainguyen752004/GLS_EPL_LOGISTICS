"""Moc "Da den noi" cho lenh giao hang, va tien VAN cho POD.

Chu du an hoi "khi xe den noi la bao cai gi?" — va cau hoi lo ra mot cho hut.
He thong co HAI lop trang thai chay song song:

  · DO (`delivery_orders.canonical_status`): pending -> in_transit -> delivered
  · Chuyen hang (`freight_orders.status`): check_in -> pickup -> departure ->
    arrival -> unloading -> delivered

Su kien `arrival` chi doi lop thu hai. DO van la `in_transit`, nen man hinh
KHONG phan biet duoc xe con tren duong hay da toi bai cho boc do. `arrived` co
trong danh sach trang thai hop le cua DO (migration v002) nhung KHONG co duong
nao dat no — kiem tren Postgres that: `DEMO-FO-2026-002` dang `departed`, DO
cua no `DEMO-DO-2026-002` van `in_transit`.

Chu du an chot: hien moc "Da den noi", nhung TIEN VAN CHO POD. Va ca hai duong
bao deu can — GPS tu gui su kien, nguoi dieu hanh bam tay duoc khi GPS loi.
"""
import importlib

import pytest


def _du_lieu_goc():
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    with database.SessionLocal() as db:
        if db.get(models.Customer, 'CUS-DN') is None:
            db.add(models.Customer(id='CUS-DN', name='Khach den noi'))
            db.add(models.Route(id='RT-DN', name='Tuyen den noi', distance_km=50))
            db.add(models.Vehicle(id='XE-DN', type='Xe tải thùng 10 tấn',
                                  status='Sẵn sàng'))
            db.add(models.Driver(id='TX-DN', name='Tai xe den noi',
                                 status='Sẵn sàng'))
            db.commit()


def _don(do_id, trang_thai='in_transit', co_xe=True):
    _du_lieu_goc()
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    with database.SessionLocal() as db:
        db.add(models.DeliveryOrder(
            id=do_id, customer_id='CUS-DN', route_id='RT-DN',
            vehicle_id='XE-DN' if co_xe else None,
            driver_id='TX-DN' if co_xe else None,
            canonical_status=trang_thai, status='Đang vận chuyển'))
        db.commit()
    return do_id


def _chuyen_hang(ma_fo, do_id=None):
    """Mot FreightOrder toi thieu, du cac cot NOT NULL.

    `freight_orders` doi hai diem va bon moc thoi gian — day chi la vo boc de
    goi duoc ham dong bo, khong phai mot chuyen hang that.
    """
    import datetime as _dt
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    with database.SessionLocal() as db:
        for ma in ('LOC-DN-A', 'LOC-DN-B'):
            if db.get(models.Location, ma) is None:
                db.add(models.Location(id=ma, name='Diem ' + ma))
        db.commit()
        moc = _dt.datetime(2026, 9, 8, 7, 0)
        db.add(models.FreightOrder(
            id=ma_fo, pickup_location_id='LOC-DN-A', delivery_location_id='LOC-DN-B',
            pickup_window_start=moc, pickup_window_end=moc + _dt.timedelta(hours=2),
            delivery_window_start=moc + _dt.timedelta(hours=6),
            delivery_window_end=moc + _dt.timedelta(hours=10),
            max_weight_kg=10000, max_volume_m3=45, max_pallet_count=20,
            status='departed'))
        db.commit()
        if do_id:
            db.add(models.FreightOrderLegacyLink(
                freight_order_id=ma_fo, delivery_order_id=do_id))
            db.commit()
    return ma_fo


def _doc(do_id):
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    with database.SessionLocal() as db:
        don = db.get(models.DeliveryOrder, do_id)
        return None if don is None else (don.canonical_status, don.status)


def _doi(client, do_id, status):
    return client.put('/api/delivery-orders/%s/status' % do_id,
                      json={'status': status})


def test_dang_van_chuyen_thi_ghi_duoc_moc_den_noi(app_client):
    client, _, _ = app_client
    do_id = _don('DO-DN-1')

    r = _doi(client, do_id, 'arrived')
    assert r.status_code == 200, r.text
    canon, nhan = _doc(do_id)
    assert canon == 'arrived', canon
    # Nhan phai NOI RA la con cho POD — day dung la moc ma nguoi ta hay tuong
    # da xong roi di chot tien.
    assert 'đến nơi' in nhan and 'POD' in nhan, nhan


def test_da_den_noi_roi_thi_khong_ghi_lai(app_client):
    """`arrived -> arrived` phai bi tu choi, khong duoc bao thanh cong lan hai."""
    client, _, _ = app_client
    do_id = _don('DO-DN-2')
    assert _doi(client, do_id, 'arrived').status_code == 200
    assert _doi(client, do_id, 'arrived').status_code == 409


def test_da_den_noi_thi_di_tiep_sang_da_giao_duoc(app_client):
    client, _, _ = app_client
    do_id = _don('DO-DN-3')
    assert _doi(client, do_id, 'arrived').status_code == 200
    # Duong doi trang thai truc tiep bi chan boi chot hoan tat nguyen khoi,
    # chu KHONG phai boi bang chuyen trang thai — do la dieu can khang dinh.
    r = _doi(client, do_id, 'delivered')
    assert r.status_code != 409 or r.json()['detail']['code'] != 'INVALID_TRANSITION', r.text


def test_van_di_thang_in_transit_sang_delivered_duoc(app_client):
    """Khong phai chuyen nao cung gui duoc moc den noi.

    GPS mat tin hieu, tai xe khong bao — chan duong cu lai thi moi chuyen nhu
    vay bi ket o `in_transit` mai.
    """
    client, _, _ = app_client
    do_id = _don('DO-DN-4')
    r = _doi(client, do_id, 'delivered')
    assert r.status_code != 409 or r.json()['detail']['code'] != 'INVALID_TRANSITION', r.text


def test_chua_xuat_ben_thi_khong_nhay_thang_sang_den_noi(app_client):
    """`pending -> arrived` la vo ly: chua chay thi khong the den."""
    client, _, _ = app_client
    do_id = _don('DO-DN-5', trang_thai='pending')
    r = _doi(client, do_id, 'arrived')
    assert r.status_code == 409, r.text
    assert r.json()['detail']['code'] == 'INVALID_TRANSITION', r.text
    assert _doc(do_id)[0] == 'pending'


def test_da_giao_roi_thi_khong_quay_lai_den_noi(app_client):
    client, _, _ = app_client
    do_id = _don('DO-DN-6', trang_thai='delivered')
    assert _doi(client, do_id, 'arrived').status_code == 409


def test_moc_den_noi_cung_doi_co_xe_va_tai_xe(app_client):
    """Cung chot voi `in_transit`: khong co xe thi "den noi" la mot cau noi doi."""
    client, _, _ = app_client
    do_id = _don('DO-DN-7', co_xe=False)
    r = _doi(client, do_id, 'arrived')
    assert r.status_code == 409, r.text
    assert r.json()['detail']['code'] == 'NOT_DISPATCHED', r.text


def test_su_kien_arrival_cua_chuyen_hang_dong_bo_luon_DO(app_client):
    """Duong GPS: thiet bi gui `arrival`, DO tu sang `arrived`.

    Kiem THANG ham dong bo, vi de di qua ca chuoi sau su kien thi bai kiem
    thanh mot bai kiem ve chuoi su kien chu khong ve viec dong bo.
    """
    client, _, _ = app_client
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    execution = importlib.import_module('services.tms_execution_service')

    do_id = _don('DO-DN-8')
    _chuyen_hang('FO-DN-8', do_id)
    with database.SessionLocal() as db:

        order = db.get(models.FreightOrder, 'FO-DN-8')
        execution._dong_bo_moc_do(db, order, 'arrival', 'kiem-thu')
        db.commit()

    assert _doc(do_id)[0] == 'arrived'


def test_su_kien_khac_arrival_thi_khong_doi_gi(app_client):
    """`delivered` KHONG dong bo o day.

    Hoan tat giao con doi POD, anh ky nhan va chot gia trong CUNG mot giao
    dich — do la viec cua `complete_delivery`, khong phai cua mot su kien GPS.
    """
    client, _, _ = app_client
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    execution = importlib.import_module('services.tms_execution_service')

    do_id = _don('DO-DN-9')
    _chuyen_hang('FO-DN-9', do_id)
    with database.SessionLocal() as db:
        order = db.get(models.FreightOrder, 'FO-DN-9')
        for su_kien in ('check_in', 'pickup', 'departure', 'unloading', 'delivered'):
            execution._dong_bo_moc_do(db, order, su_kien, 'kiem-thu')
        db.commit()

    assert _doc(do_id)[0] == 'in_transit'


def test_chuyen_hang_khong_noi_voi_DO_nao_thi_khong_vo(app_client):
    """Khong phai chuyen hang nao cung co lien ket sang DO cu."""
    client, _, _ = app_client
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    execution = importlib.import_module('services.tms_execution_service')

    _chuyen_hang('FO-DN-10')
    with database.SessionLocal() as db:
        order = db.get(models.FreightOrder, 'FO-DN-10')
        execution._dong_bo_moc_do(db, order, 'arrival', 'kiem-thu')
        db.commit()


def test_moc_den_noi_KHONG_mo_quyet_toan_chi_phi(app_client):
    """Day la chot quan trong nhat: den noi KHONG dong nghia duoc chot tien.

    Tien chi chot sau khi co POD ky nhan. `_save_trip_cost_rows` doi Trip
    `completed`, va Trip chi `completed` khi nop POD cho moi chang giao.
    """
    import inspect as _inspect
    cost = importlib.import_module('services.tms_cost_service')
    nguon = _inspect.getsource(cost._save_trip_cost_rows)
    assert 'TRIP_NOT_COMPLETED' in nguon, nguon[:400]
    assert 'trip.status != "completed"' in nguon, (
        'moc mo quyet toan phai la Trip completed, khong phai `arrived`')
    # Va tuyet doi khong duoc noi long thanh `arrived`.
    assert '"arrived"' not in nguon, (
        'quyet toan khong duoc mo o moc da den noi — chua co POD thi chua co '
        'chung tu doi chieu')
