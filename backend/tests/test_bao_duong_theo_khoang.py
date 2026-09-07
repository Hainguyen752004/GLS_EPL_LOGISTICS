"""Liet ke bao duong xe theo KHOANG THOI GIAN, cho man xep lich xe.

Vi sao can duong nay: man "Sap lich xe va tai xe" ve mot luoi xe x ngay, va o
nao trung mot ky bao duong thi phai ke soc de nguoi xep lich khong dieu xe do
di. Muon biet vay thi phai co bao duong cua TAT CA xe trong tuan.

Duong theo tung xe (`/api/vehicles/{id}/maintenance-requests`) khong dung duoc
cho viec do: he thong chay o quy mo ~500 xe, tuc 500 lan goi cho MOT tuan lich.

Hai chot ma bai kiem nay giu:

  1. Loc theo GIAO KHOANG, khong phai "nam gon trong khoang". Mot ky bao duong
     bat dau tu tuan truoc va keo qua tuan nay VAN chan xe trong tuan nay — bo
     no ra khoi ket qua thi luoi hien o do trong va nguoi xep lich dieu xe dang
     nam bai di chay.
  2. Ky CHUA co lich (`planned_start`/`planned_end` rong) thi khong tra ve: no
     khong chan o nao ca, ma de vao chi lam nguoi doc tuong xe dang nam bai.
"""


def _tao_xe(client, ma):
    r = client.post("/api/vehicles", json={
        "id": ma,
        "brand": "Isuzu",
        "type": "Container 20FT",
        "weight_capacity": 28000,
        "maintenance_date": "2027-01-01",
        "inspection_exp": "2027-01-01",
        "insurance_date": "2027-01-01",
    })
    assert r.status_code == 200, r.text


def _tao_ky(client, ma_xe, so, bat_dau, ket_thuc):
    r = client.post(
        f"/api/vehicles/{ma_xe}/maintenance-requests",
        json={
            "request_no": so,
            "category": "preventive",
            "priority": "normal",
            "planned_start": bat_dau,
            "planned_end": ket_thuc,
            "description": "Bao duong dinh ky 5.000 km",
            "workshop": "EPL Workshop",
            "odometer_km": 120000,
            "currency_code": "VND",
        },
        headers={"X-User-Id": "fleet-user"},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


TUAN_DAU = "2026-08-17T00:00:00+07:00"
TUAN_CUOI = "2026-08-24T00:00:00+07:00"


def test_tra_ve_moi_ky_co_giao_voi_khoang(app_client):
    client, _, _ = app_client
    _tao_xe(client, "VEH-KY-01")
    _tao_xe(client, "VEH-KY-02")
    _tao_xe(client, "VEH-KY-03")

    # Nam gon trong tuan.
    _tao_ky(client, "VEH-KY-01", "MR-TRONG-TUAN",
            "2026-08-19T08:00:00+07:00", "2026-08-19T17:00:00+07:00")
    # Bat dau TU TUAN TRUOC va keo qua tuan nay — van chan xe trong tuan nay.
    _tao_ky(client, "VEH-KY-02", "MR-VAT-QUA",
            "2026-08-15T08:00:00+07:00", "2026-08-18T17:00:00+07:00")
    # Han toan ngoai tuan.
    _tao_ky(client, "VEH-KY-03", "MR-NGOAI",
            "2026-09-10T08:00:00+07:00", "2026-09-10T17:00:00+07:00")

    r = client.get("/api/vehicle-maintenance-requests",
                   params={"start": TUAN_DAU, "end": TUAN_CUOI})
    assert r.status_code == 200, r.text
    so = {item["request_no"] for item in r.json()["data"]}

    assert "MR-TRONG-TUAN" in so
    assert "MR-VAT-QUA" in so, (
        "ky bat dau tu tuan truoc va keo qua tuan nay van chan xe, phai tra ve")
    assert "MR-NGOAI" not in so, "ky ngoai khoang khong duoc tra ve"


def test_moi_ky_bao_duong_deu_buoc_phai_co_lich(app_client):
    """Khong tao duoc mot ky bao duong ma khong co gio bat dau/ket thuc.

    Day la dieu KIEN luoi lich xe dua vao: neu mot ky co the ton tai ma khong
    co lich, thi no vua khong ke soc duoc o nao tren luoi, vua lam nguoi xep
    lich tuong xe dang ranh. Phep loc trong `list_requests_in_period` van bo
    qua cac ky thieu lich — de phong du lieu cu — nhung duong API thi chan tu
    dau, va bai kiem nay giu cho no chan.
    """
    client, _, _ = app_client
    _tao_xe(client, "VEH-KY-04")
    r = client.post(
        "/api/vehicles/VEH-KY-04/maintenance-requests",
        json={
            "request_no": "MR-CHUA-LICH",
            "category": "corrective",
            "priority": "normal",
            "description": "Tai xe bao co tieng lach cach, chua dat lich",
            "currency_code": "VND",
        },
        headers={"X-User-Id": "fleet-user"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "INVALID_DATETIME"


def test_khoang_nguoc_thi_bao_loi_ro_rang(app_client):
    client, _, _ = app_client
    r = client.get("/api/vehicle-maintenance-requests",
                   params={"start": TUAN_CUOI, "end": TUAN_DAU})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "INVALID_PERIOD"


def test_thieu_mui_gio_thi_bao_loi_chu_khong_doan(app_client):
    client, _, _ = app_client
    r = client.get("/api/vehicle-maintenance-requests",
                   params={"start": "2026-08-17", "end": "2026-08-24"})
    assert r.status_code == 422, r.text
    # Doan mui gio la doan sai gio bat dau ca dem cua ca mot bai xe.
    assert r.json()["detail"]["code"] == "TIMEZONE_REQUIRED"
