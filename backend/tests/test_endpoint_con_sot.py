"""Ba endpoint cuoi cung khong co dau vet nao trong bo test.

    DELETE /api/drivers/{did}
    GET    /api/parking-labels/{label_id}/qr.svg
    GET    /api/tms/reporting/transport-revenue/export.csv

`delete_driver` khi doc ky thi co ba cho sai, va ca ba deu im lang:

  1. KHONG tim thay van tra ve "Đã xóa nhân sự" — go nham mot ma la nhan
     duoc mot loi khang dinh sai.
  2. Khong tim ra theo ma thi TIM THEO TEN, va `.first()` chon tuy y mot
     nguoi khi hai tai xe trung ten. Mot thao tac xoa khong duoc phep doan.
  3. Khong kiem dang-su-dung, khac han `delete_vehicle` ngay ben tren.

Hai endpoint con lai la duong XUAT DU LIEU: mot tra ve anh QR de dan len
kien hang, mot tra ve CSV bao cao doanh thu. Ca hai deu de hong am tham —
tra ve dung 200 nhung noi dung rong hoac sai kieu, va khong ai biet cho toi
luc mo tep ra.
"""
import csv
import io


# --- DELETE /api/drivers/{did} -----------------------------------------


def _tai_xe(client, ma, ten="Tai xe test"):
    r = client.post("/api/drivers", json={"id": ma, "name": ten,
                                          "status": "Ranh (San sang)"})
    assert r.status_code in (200, 201), r.text
    return ma


def test_xoa_tai_xe_khong_ton_tai_phai_bao_404_chu_khong_noi_da_xoa(app_client):
    client, _, _ = app_client
    r = client.delete("/api/drivers/DRV-KHONG-CO-AI")
    assert r.status_code == 404, r.text
    assert "Đã xóa" not in r.text, r.text


def test_khong_duoc_xoa_theo_HO_TEN(app_client):
    """Duong cu nhan ca ho ten. Hai tai xe trung ten la `.first()` chon tuy y
    mot nguoi — va nguoi bi xoa khong phai nguoi dinh xoa."""
    client, _, _ = app_client
    _tai_xe(client, "DRV-TRUNG-1", "Nguyen Van A")
    _tai_xe(client, "DRV-TRUNG-2", "Nguyen Van A")

    r = client.delete("/api/drivers/Nguyen Van A")
    assert r.status_code == 404, r.text

    con = {d["id"] for d in client.get("/api/drivers").json()}
    assert {"DRV-TRUNG-1", "DRV-TRUNG-2"} <= con, con


def test_xoa_tai_xe_ranh_thi_duoc(app_client):
    client, _, _ = app_client
    _tai_xe(client, "DRV-XOA-OK")
    r = client.delete("/api/drivers/DRV-XOA-OK")
    assert r.status_code == 200, r.text
    assert "DRV-XOA-OK" in r.json()["message"]
    assert "DRV-XOA-OK" not in {d["id"] for d in client.get("/api/drivers").json()}


def test_khong_duoc_xoa_tai_xe_dang_gan_voi_don(app_client, workflow_builder):
    """Giong `delete_vehicle`: dang duoc dung thi 409, khong de lai tham
    chieu mo coi trong DO."""
    import importlib

    client, _, _ = app_client
    ma = _tai_xe(client, "DRV-DANG-CHAY")
    workflow_builder.master_data()

    # Ghi DO thang vao CSDL. `POST /api/delivery-orders` doi mot phong bi
    # khac han (bat buoc `so_id`, cam moi truong ngoai danh sach), va di
    # duong do chi de dung mot cot `driver_id` la keo ca luong tao don vao
    # mot bai kiem ve XOA TAI XE.
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.DeliveryOrder(
            id="DO-GIU-DRV", customer_id="CUS-T1", route_id="RT-T1",
            vehicle_id="VEH-T1", driver_id=ma, status="Chờ vận chuyển"))
        db.commit()

    r = client.delete("/api/drivers/" + ma)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "LOCKED_RECORD", r.text
    # Va tai xe phai con nguyen.
    assert ma in {d["id"] for d in client.get("/api/drivers").json()}


# --- GET /api/parking-labels/{label_id}/qr.svg -------------------------


def test_qr_cua_nhan_khong_ton_tai_bao_404(app_client):
    client, _, _ = app_client
    r = client.get("/api/parking-labels/NHAN-KHONG-CO/qr.svg")
    assert r.status_code == 404, r.text


def test_qr_tra_ve_anh_svg_that_va_khong_duoc_cache(app_client):
    """Anh QR chua `qr_token` — ai giu duoc anh la quet duoc kien hang, nen
    header phai la `no-store`. Va noi dung phai la SVG that chu khong phai
    mot phan hoi 200 rong."""
    client, _, _ = app_client
    import importlib

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        nhan = db.query(models.ParkingLabel).first()
        if nhan is None:
            # Tu dung lay mot nhan de kiem, thay vi bo qua bai kiem: bo qua
            # nghia la endpoint nay VAN khong duoc chay lan nao.
            # Nap theo TUNG BAC va commit sau moi bac. SQLite trong bo test
            # nay bat `PRAGMA foreign_keys=ON`, va mot `flush()` chung cho ca
            # ba ban ghi khong bao dam thu tu chen giua ba bang khac nhau.
            db.add(models.Customer(id="CUS-QR", name="Khach QR"))
            db.add(models.Route(id="RT-QR", name="Tuyen QR", distance_km=10))
            db.commit()
            db.add(models.DeliveryOrder(id="DO-QR", customer_id="CUS-QR",
                                        route_id="RT-QR", status="Chờ vận chuyển"))
            db.commit()
            db.add(models.ParkingList(id="PL-QR", do_id="DO-QR", version=1))
            db.commit()
            db.add(models.ParkingLabel(id="PLB-QR", parking_list_id="PL-QR",
                                       package_no=1, package_total=1,
                                       qr_token="token-qr-kiem-thu", status="ready"))
            db.commit()
            nhan = db.query(models.ParkingLabel).first()
        ma, token = nhan.id, nhan.qr_token

    r = client.get("/api/parking-labels/" + ma + "/qr.svg")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/svg+xml"), r.headers
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    than = r.content.decode("utf-8")
    assert "<svg" in than and "</svg>" in than, than[:200]
    # Token KHONG duoc nam tho trong anh duoi dang van ban doc duoc — no da
    # nam trong duong dan ma QR ma hoa, do la du.
    assert len(than) > 200, len(than)
    assert token not in than, "token khong duoc in tho ra SVG"


# --- GET /api/tms/reporting/transport-revenue/export.csv ---------------


def test_xuat_csv_doi_quyen_finance_read(app_client):
    client, _, _ = app_client
    r = client.get("/api/tms/reporting/transport-revenue/export.csv")
    # Khong co quyen tai chinh thi phai bi chan, khong duoc tra bang du lieu.
    assert r.status_code in (401, 403), (r.status_code, r.text[:200])


def test_xuat_csv_co_BOM_va_dung_23_cot(app_client):
    """Tep nay duoc mo bang Excel. Thieu BOM la moi chu tieng Viet thanh
    ky tu la, va do khong phai loi Excel — do la loi cua ben xuat tep."""
    import importlib

    client, _, _ = app_client
    models = importlib.import_module("models")
    database = importlib.import_module("database")
    with database.SessionLocal() as db:
        db.merge(models.Role(id="FIN_CSV", permissions='["finance_read"]'))
        db.merge(models.User(id="csv-user", username="csv-user", role_id="FIN_CSV"))
        # Bao cao doi tien te chuc nang. Thieu no thi endpoint tra 422 va bai
        # kiem bi bo qua — tuc duong xuat CSV van khong duoc chay lan nao.
        db.merge(models.FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
        db.merge(models.CurrencyDefinition(code="VND", minor_units=0))
        db.commit()

    r = client.get("/api/tms/reporting/transport-revenue/export.csv",
                   headers={"X-Test-Principal": "csv-user"})
    if r.status_code in (401, 403):
        import pytest
        pytest.skip("Khong cap duoc quyen finance_read qua duong nay: " + r.text[:120])
    if r.status_code == 422:
        import pytest
        pytest.skip("Chua cau hinh tien te chuc nang: " + r.text[:120])
    assert r.status_code == 200, r.text[:300]

    than = r.content.decode("utf-8")
    assert than.startswith("﻿"), "thieu BOM, Excel se doc sai tieng Viet"
    assert "attachment" in r.headers.get("content-disposition", ""), r.headers
    assert ".csv" in r.headers.get("content-disposition", ""), r.headers

    dong = list(csv.reader(io.StringIO(than.lstrip("﻿"))))
    assert dong, "tep rong"
    assert dong[0][0] == "STT", dong[0]
    assert len(dong[0]) == 23, (len(dong[0]), dong[0])
    # Moi dong du lieu phai co dung so cot nhu tieu de — lech cot la Excel
    # doc sang o khac ma khong bao gi.
    for d in dong[1:]:
        assert len(d) == len(dong[0]), d


def test_xuat_csv_thieu_cau_hinh_thi_422_chu_khong_no_500(app_client):
    """Ban JSON cua bao cao co `try/except DomainError -> raise_http`, ban CSV
    thi khong he co. Cung mot nguyen nhan — chua cau hinh tien te chuc nang —
    ma mot ben tra 422 kem loi doc duoc, con ben nay nem DomainError khong ai
    bat: nguoi dung bam "Xuat CSV" va nhan 500 Internal Server Error."""
    import importlib

    client, _, _ = app_client
    models = importlib.import_module("models")
    database = importlib.import_module("database")
    with database.SessionLocal() as db:
        db.merge(models.Role(id="FIN_CSV2", permissions='["finance_read"]'))
        db.merge(models.User(id="csv-user-2", username="csv-user-2", role_id="FIN_CSV2"))
        # CO Y khong tao FinanceControlConfig: day chinh la tinh huong can kiem.
        db.query(models.FinanceControlConfig).delete()
        db.commit()

    r = client.get("/api/tms/reporting/transport-revenue/export.csv",
                   headers={"X-Test-Principal": "csv-user-2"})
    assert r.status_code != 500, r.text[:300]
    assert r.status_code in (401, 403, 422), (r.status_code, r.text[:200])
    if r.status_code == 422:
        # Loi phai doc duoc, khong phai mot trang loi tron.
        assert "tiền tệ" in r.text or "FINANCE_CONFIG" in r.text, r.text[:200]
