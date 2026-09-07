"""Luong huy lenh giao hang: backend da co, giao dien thi chua.

`update_delivery_status` cho phep chuyen `pending -> cancelled` va co chot an
toan (con chuyen van tai dang hoat dong thi tu choi bang 409
`ACTIVE_TRIP_EXISTS`). Nhung chua co bai kiem nao di qua duong `cancelled`,
va giao dien thi khong co mot nut nao goi no — chu `cancelled` chi xuat hien
trong cac bo loc, tuc man hinh NHAN RA don da huy nhung khong HUY duoc don.

He qua that: khach huy don thi nguoi dieu hanh khong ghi nhan duoc. Ho chi
con hai lua chon, va ca hai deu sai — de don nam o "Cho van chuyen" mai (lam
sai moi con so dem va moi canh bao qua han), hoac XOA don di (mat luon lich
su mot viec da that su xay ra).
"""
import importlib

import pytest

MA_DO = "DO-HUY-1"


def _don_cho_van_chuyen(app_client, do_id=MA_DO):
    """Mot DO o trang thai `pending`, ghi thang vao CSDL."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        if db.get(models.Customer, "CUS-HUY") is None:
            db.add(models.Customer(id="CUS-HUY", name="Khach huy don"))
            db.add(models.Route(id="RT-HUY", name="Tuyen huy", distance_km=20))
            db.commit()
        db.add(models.DeliveryOrder(
            id=do_id, customer_id="CUS-HUY", route_id="RT-HUY",
            status="Chờ vận chuyển", canonical_status="pending"))
        db.commit()
    return do_id


def _trang_thai(app_client, do_id):
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        don = db.get(models.DeliveryOrder, do_id)
        return None if don is None else (don.canonical_status, don.status)


def test_huy_don_dang_cho_van_chuyen(app_client):
    client, _, _ = app_client
    do_id = _don_cho_van_chuyen(app_client)

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "cancelled"})
    assert r.status_code == 200, r.text

    canon, nhan = _trang_thai(app_client, do_id)
    assert canon == "cancelled", canon
    # Nhan tieng Viet phai doi theo, khong de lai "Chờ vận chuyển".
    assert "Chờ vận chuyển" not in nhan, nhan


def test_huy_roi_thi_khong_huy_lai_duoc(app_client):
    """`cancelled` la trang thai KET. Huy lai phai bi tu choi, khong duoc bao
    thanh cong lan hai."""
    client, _, _ = app_client
    do_id = _don_cho_van_chuyen(app_client, "DO-HUY-2")
    assert client.put("/api/delivery-orders/%s/status" % do_id,
                      json={"status": "cancelled"}).status_code == 200

    lai = client.put("/api/delivery-orders/%s/status" % do_id,
                     json={"status": "cancelled"})
    assert lai.status_code == 409, lai.text


def test_don_da_huy_khong_di_tiep_duoc_sang_dang_van_chuyen(app_client):
    """Huy roi thi khong duoc xuat ben nua. Neu chuyen duoc, mot don da huy
    van xuat hien tren man dieu do va co the duoc gan xe."""
    client, _, _ = app_client
    do_id = _don_cho_van_chuyen(app_client, "DO-HUY-3")
    client.put("/api/delivery-orders/%s/status" % do_id, json={"status": "cancelled"})

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "in_transit"})
    assert r.status_code == 409, r.text
    canon, _ = _trang_thai(app_client, do_id)
    assert canon == "cancelled", canon


def test_khong_huy_duoc_khi_con_chuyen_dang_chay(app_client):
    """Chot an toan cua backend: con TransportTrip chua ket thuc thi 409
    `ACTIVE_TRIP_EXISTS` — huy don ma chuyen van chay la xe di giao mot don
    khong con ton tai."""
    client, _, _ = app_client
    do_id = _don_cho_van_chuyen(app_client, "DO-HUY-4")

    import datetime as dt

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        # `TransportTrip.freight_order_id` la NOT NULL, va `FreightOrder` doi
        # hai dia diem cung sau moc thoi gian — nap du theo tung bac de khoa
        # ngoai duoc thoa man o moi buoc.
        gio = dt.datetime(2026, 9, 10, 6, 0)
        db.add(models.Location(id="LOC-HUY-A", name="Kho A"))
        db.add(models.Location(id="LOC-HUY-B", name="Kho B"))
        db.commit()
        db.add(models.FreightOrder(
            id="FO-HUY-4",
            pickup_location_id="LOC-HUY-A", delivery_location_id="LOC-HUY-B",
            pickup_window_start=gio, pickup_window_end=gio + dt.timedelta(hours=2),
            delivery_window_start=gio + dt.timedelta(hours=4),
            delivery_window_end=gio + dt.timedelta(hours=6),
            max_weight_kg=10000, max_volume_m3=30, max_pallet_count=10,
            status="dispatched"))
        db.commit()
        db.add(models.TransportTrip(id="TRIP-HUY-4", freight_order_id="FO-HUY-4",
                                    status="in_transit"))
        db.commit()
        db.add(models.TripDeliveryOrder(trip_id="TRIP-HUY-4", do_id=do_id))
        db.commit()

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "cancelled"})
    assert r.status_code == 409, r.text
    assert "ACTIVE_TRIP_EXISTS" in r.text, r.text
    # Va don phai con nguyen trang thai cu.
    canon, _ = _trang_thai(app_client, do_id)
    assert canon == "pending", canon


def test_huy_don_khong_ton_tai_bao_404(app_client):
    client, _, _ = app_client
    r = client.put("/api/delivery-orders/DO-KHONG-CO/status",
                   json={"status": "cancelled"})
    assert r.status_code == 404, r.text
    assert "Đã" not in r.text, r.text
