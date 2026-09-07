"""Man Hoan tat giao phai noi DUNG cai dang thieu, va khong chan DO da giao.

Hien trang do duoc tren Postgres that cua du an:

  · `DEMO-61H-112.34` co `type = ''` — chiec xe KHONG co loai xe.
  · Cong thuc gia thanh VND thi CO SAN cho hai loai xe khac.

Nhung `/api/delivery-orders/{id}/closeout` bao:

    "Chua cau hinh gia thanh VND cho loai xe cua DEMO-61H-112.34."

Nguoi dung doc cau do se di tao cong thuc — va van khong het loi, vi cai
thieu la LOAI XE cua chiec xe, khong phai cong thuc. Mot loi chi sai cho thi
te hon la khong bao gi: no khien nguoi ta sua dung thu khong hong.

Va chot dat sai vi tri. `DEMO-DO-2026-003` da o trang thai `delivered` — ho
so cua no da chot xong, man "Da hoan tat" chi XEM lai chu khong tinh lai gia
thanh. Doi cong thuc o day la chan mot viec khong can den no, va hau qua la
khong xem duoc ho so cua mot chuyen da giao xong.
"""
import importlib

import pytest


def _du_lieu_goc(khach='CUS-CO', tuyen='RT-CO'):
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    with database.SessionLocal() as db:
        if db.get(models.Customer, khach) is None:
            db.add(models.Customer(id=khach, name='Khach closeout'))
            db.add(models.Route(id=tuyen, name='Tuyen closeout', distance_km=40))
            db.commit()


def _dung_don(do_id, loai_xe, trang_thai='in_transit', ma_xe=None):
    """Mot DO co SO tien VND, gan mot chiec xe voi `loai_xe` cho truoc."""
    _du_lieu_goc()
    database = importlib.import_module('database')
    models = importlib.import_module('models')
    ma_xe = ma_xe or ('XE-' + do_id)
    # Ghi du lieu goc TRUOC roi commit, sau do moi ghi DO. Ghi chung mot lan
    # thi SQLite bao `FOREIGN KEY constraint failed`: cac cot khoa ngoai o day
    # khong co `relationship`, nen SQLAlchemy khong biet thu tu phu thuoc va co
    # the chen DO truoc chiec xe.
    with database.SessionLocal() as db:
        if db.get(models.Vehicle, ma_xe) is None:
            db.add(models.Vehicle(id=ma_xe, type=loai_xe, status='Sẵn sàng'))
        if db.get(models.Driver, 'TX-CO') is None:
            db.add(models.Driver(id='TX-CO', name='Tai xe closeout', status='Sẵn sàng'))
        db.add(models.SalesOrder(
            id='SO-' + do_id, customer_id='CUS-CO', currency_code='VND',
            total_amount=5000000, status='confirmed'))
        db.commit()
    with database.SessionLocal() as db:
        db.add(models.DeliveryOrder(
            id=do_id, customer_id='CUS-CO', route_id='RT-CO',
            so_id='SO-' + do_id, vehicle_id=ma_xe, driver_id='TX-CO',
            weight_kg=1000, canonical_status=trang_thai,
            status='Đang vận chuyển' if trang_thai == 'in_transit' else 'Đã giao'))
        db.commit()
    return do_id


def _closeout(client, do_id):
    return client.get('/api/delivery-orders/%s/closeout' % do_id)


def test_xe_chua_gan_loai_thi_noi_dung_chuyen_do(app_client):
    """Khong duoc bao la thieu cong thuc, vi tao cong thuc cung khong het loi."""
    client, _, _ = app_client
    do_id = _dung_don('DO-CO-1', loai_xe='')

    r = _closeout(client, do_id)
    assert r.status_code == 409, r.text
    ct = r.json()['detail']
    assert ct['code'] == 'VEHICLE_TYPE_REQUIRED', ct
    # Phai noi ra chuyen loai xe, va KHONG duoc noi la thieu cong thuc.
    assert 'loại xe' in ct['message'], ct['message']
    assert 'Chưa cấu hình giá thành' not in ct['message'], ct['message']
    # Va chi duong sang dung cho sua duoc.
    assert 'master-data/vehicles' in ct['navigation_targets'], ct


def test_do_da_giao_thi_xem_duoc_ho_so_du_thieu_cong_thuc(app_client):
    """Ho so da chot roi thi khong can cong thuc de XEM lai."""
    client, _, _ = app_client
    do_id = _dung_don('DO-CO-2', loai_xe='', trang_thai='delivered')

    r = _closeout(client, do_id)
    assert r.status_code == 200, r.text
    # Va no phai tra ve mot phong bi dung duoc, khong phai None tran ra ngoai.
    body = r.json()
    # Khoa la `cost_formula`, khong phai `formula`.
    assert isinstance(body.get('cost_formula'), dict), body.get('cost_formula')
    assert isinstance(body.get('configured_cost_lines'), list)


def test_don_da_huy_cung_khong_bi_chan(app_client):
    """Don da huy cung la trang thai KET — xem lai khong can cong thuc."""
    client, _, _ = app_client
    do_id = _dung_don('DO-CO-3', loai_xe='', trang_thai='cancelled')
    assert _closeout(client, do_id).status_code == 200


def test_co_loai_xe_ma_thieu_cong_thuc_thi_noi_ro_LOAI_nao(app_client):
    """Loi phai neu ten LOAI XE, khong phai bien so.

    Bien so khong giup gi: cong thuc gan theo LOAI xe, nen nguoi dung can
    biet loai nao dang thieu de them dung cho.
    """
    client, _, _ = app_client
    do_id = _dung_don('DO-CO-4', loai_xe='Xe tải hộp 3.5 tấn')

    r = _closeout(client, do_id)
    assert r.status_code == 409, r.text
    ct = r.json()['detail']
    assert ct['code'] == 'COST_FORMULA_REQUIRED', ct
    assert 'Xe tải hộp 3.5 tấn' in ct['message'], ct['message']
    assert ct.get('vehicle_type') == 'Xe tải hộp 3.5 tấn', ct
    assert ct['navigation_targets'], 'phải chỉ đường sang chỗ sửa được'


def test_do_khong_ton_tai_van_la_404(app_client):
    """Chot moi khong duoc lam nhoe mat 404 cu."""
    client, _, _ = app_client
    r = _closeout(client, 'DO-KHONG-CO-THAT')
    assert r.status_code == 404, r.text
    assert r.json()['detail']['code'] == 'DELIVERY_ORDER_NOT_FOUND'
