"""`pending -> in_transit` phai co xe va tai xe.

`update_delivery_status` cho chuyen thang `pending -> in_transit` ma khong doi
DO da duoc dieu phoi xe. Ket qua la mot DO "dang van chuyen" nhung
`vehicle_id` va `driver_id` deu NULL, va khong co ban ghi `vehicle_tracking`
nao. Do dung la hien trang cua `E2E-STRESS-20260807083017-OGJ4-DO` trong co so
du lieu Postgres that — no lam log may chu do lien tuc:

    GET /api/tracking/E2E-STRESS-20260807083017-OGJ4-DO 404 Not Found

Ba he qua thuc te, khong phai gia dinh — bai kiem duoi day chay THAT ca ba:

  1. `/api/tracking/{id}` tra 404, nen xe BIEN MAT khoi ban do dieu do. Nguoi
     dieu do dem xe tren man va tuong so xe dang chay it hon thuc te.
  2. DO do KET MAI o `in_transit`. Doi trang thai truc tiep sang
     `delivered` bi tu choi vi phai hoan tat nguyen khoi; con duong hoan tat
     nguyen khoi thi doi mot Trip co chang giao, ma DO di duong tat nay khong
     thuoc Trip nao.
  3. Xe va tai xe khong bi danh dau dang chay, nen cung chiec xe do van duoc
     dieu cho DO khac.

Moi duong dieu phoi DUNG deu gan xe va tao san ban ghi GPS —
`workflow_service.dispatch`, `tms_dispatch_service`, `tms_execution_service`,
`demo_seed_service`. Nen chot nay khong dong duong nao dang dung.
"""
import importlib


def _du_lieu_goc(app_client):
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        if db.get(models.Customer, "CUS-XB") is None:
            db.add(models.Customer(id="CUS-XB", name="Khach xuat ben"))
            db.add(models.Route(id="RT-XB", name="Tuyen xuat ben", distance_km=30))
            db.add(models.Vehicle(id="XE-XB-01", type="Xe tai 5 tan",
                                  status="Sẵn sàng"))
            db.add(models.Driver(id="TX-XB-01", name="Tai xe xuat ben",
                                 status="Sẵn sàng"))
            db.commit()


def _don(app_client, do_id, vehicle_id=None, driver_id=None):
    """Mot DO `pending`, ghi thang vao CSDL — co hoac khong co xe."""
    _du_lieu_goc(app_client)
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.DeliveryOrder(
            id=do_id, customer_id="CUS-XB", route_id="RT-XB",
            vehicle_id=vehicle_id, driver_id=driver_id,
            status="Chờ vận chuyển", canonical_status="pending"))
        db.commit()
    return do_id


def _doc_don(do_id):
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        return db.get(models.DeliveryOrder, do_id)


def test_chua_dieu_phoi_thi_khong_xuat_ben_duoc(app_client):
    client, _, _ = app_client
    do_id = _don(app_client, "DO-XB-1")

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "in_transit"})
    assert r.status_code == 409, r.text
    body = r.json()
    ma = body.get("detail", {}).get("code") or body.get("error", {}).get("code")
    assert ma == "NOT_DISPATCHED", body

    # Va trang thai phai GIU NGUYEN, khong doi nua vo.
    don = _doc_don(do_id)
    assert don.canonical_status == "pending", don.canonical_status


def test_loi_phai_chi_duong_sang_man_dieu_phoi(app_client):
    """Mot cau 409 chung chung thi nguoi dung khong biet lam gi tiep. Loi nay
    phai noi ra viec can lam VA cho biet di dau."""
    client, _, _ = app_client
    do_id = _don(app_client, "DO-XB-2")

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "in_transit"})
    chi_tiet = r.json().get("detail", {})
    assert "dispatch" in (chi_tiet.get("navigation_targets") or []), chi_tiet
    assert "điều phối" in chi_tiet.get("message", ""), chi_tiet


def test_co_xe_va_tai_xe_thi_xuat_ben_duoc(app_client):
    """Chot chi doi DIEU KIEN, khong chan han duong nay."""
    client, _, _ = app_client
    do_id = _don(app_client, "DO-XB-3",
                 vehicle_id="XE-XB-01", driver_id="TX-XB-01")

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "in_transit"})
    assert r.status_code == 200, r.text
    assert _doc_don(do_id).canonical_status == "in_transit"


def test_thieu_moi_tai_xe_cung_bi_chan(app_client):
    """Co xe ma khong co tai xe thi xe khong tu chay duoc. Chot phai doi CA
    HAI, khong chi doi xe."""
    client, _, _ = app_client
    do_id = _don(app_client, "DO-XB-4", vehicle_id="XE-XB-01")

    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "in_transit"})
    assert r.status_code == 409, r.text
    assert _doc_don(do_id).canonical_status == "pending"


def test_ba_he_qua_that_cua_du_lieu_tu_mau_thuan(app_client):
    """Dung ngay ba he qua ra, tren mot DO dat truc tiep vao trang thai xau.

    Bai nay khong di qua API — no ghi thang vao CSDL de dung lai chinh trang
    thai ma lo hong da sinh ra, roi do xem ba he qua co that hay khong. Neu
    mai nay ai do go chot di, bai nay van cho thay VI SAO chot ton tai.
    """
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    do_id = _don(app_client, "DO-XB-5")
    with database.SessionLocal() as db:
        don = db.get(models.DeliveryOrder, do_id)
        don.canonical_status = "in_transit"
        don.status = "Đang vận chuyển"
        db.commit()

    # (1) Bien mat khoi ban do dieu do — khong co ban ghi vehicle_tracking.
    assert client.get("/api/tracking/%s" % do_id).status_code == 404

    # (2) Ket mai o `in_transit`: KHONG duong nao dua no di tiep duoc.
    #     Duong doi trang thai truc tiep bi tu choi vi phai hoan tat nguyen
    #     khoi; con duong hoan tat nguyen khoi thi doi mot Trip co chang giao,
    #     ma DO di duong tat nay khong thuoc Trip nao.
    r = client.put("/api/delivery-orders/%s/status" % do_id,
                   json={"status": "delivered"})
    assert r.status_code != 200, r.text
    assert r.json()["detail"]["code"] == "ATOMIC_COMPLETION_REQUIRED", r.text

    r2 = client.post("/api/delivery-orders/%s/complete-delivery" % do_id)
    assert r2.status_code != 200, r2.text
    with database.SessionLocal() as db:
        assert db.get(models.DeliveryOrder, do_id).canonical_status == "in_transit"
        # Va no khong thuoc Trip nao — day la ly do thuc su lam no ket.
        assert db.query(models.TripDeliveryOrder).filter(
            models.TripDeliveryOrder.do_id == do_id).count() == 0

    # (3) Xe khong bi danh dau dang chay, nen van dieu duoc cho DO khac.
    with database.SessionLocal() as db:
        xe = db.get(models.Vehicle, "XE-XB-01")
        assert "vận chuyển" not in (xe.status or ""), xe.status
