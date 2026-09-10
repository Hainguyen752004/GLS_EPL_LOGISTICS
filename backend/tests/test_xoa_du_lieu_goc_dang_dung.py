"""Khong duoc xoa du lieu goc dang co chung tu tham chieu.

`delete_vehicle` va `delete_driver` kiem rat can than truoc khi xoa, nhung
`delete_route`, `delete_customer` va `delete_vehicle_type` thi khong. Chinh
chu thich o dau `master_data_routes.py` da ghi dieu do tu truoc — "khong co
kiem tra dang-su-dung nao — khac voi delete_vehicle von kiem rat can than" —
ma no van chua duoc sua.

Hau qua khong phai la mot loi de thay. Xoa mot tuyen duong dang duoc bao gia
tham chieu thi `distance_km` bien mat, ma do chinh la thu nuoi phep tinh gia
cuoc va ETA. Xoa mot khach hang thi bao cao doanh thu theo khach khong con
biet dong tien thuoc ve ai. Ca hai am tham: khong mot loi bao nao, chi la
nhung con so tu dung sai.
"""
import importlib


def _du_lieu_goc(app_client):
    """Mot khach, mot tuyen, va mot bao gia tham chieu ca hai."""
    client, _, _ = app_client
    assert client.post("/api/customers", json={
        "id": "CUS-KHOA", "name": "Khach co chung tu"}).status_code in (200, 201)
    assert client.post("/api/routes", json={
        "id": "RT-KHOA", "name": "Tuyen co chung tu",
        "distance_km": 44, "segments_json": "[]"}).status_code in (200, 201)

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.Quotation(id="QT-KHOA", customer_id="CUS-KHOA",
                                route_id="RT-KHOA", status="Bản nháp"))
        db.commit()


def test_khong_xoa_duoc_tuyen_duong_dang_co_bao_gia(app_client):
    client, _, _ = app_client
    _du_lieu_goc(app_client)

    r = client.delete("/api/routes/RT-KHOA")
    assert r.status_code == 409, r.text
    than = r.json()["detail"]
    assert than["code"] == "LOCKED_RECORD", than
    # Loi phai NOI RO vuong o dau, khong chi noi "khong xoa duoc".
    assert "báo giá" in than["message"], than["message"]

    # Va tuyen phai con nguyen.
    ds = client.get("/api/routes").json()
    assert "RT-KHOA" in {t["id"] for t in ds}


def test_khong_xoa_duoc_khach_hang_dang_co_bao_gia(app_client):
    client, _, _ = app_client
    _du_lieu_goc(app_client)

    r = client.delete("/api/customers/CUS-KHOA")
    assert r.status_code == 409, r.text
    than = r.json()["detail"]
    assert than["code"] == "LOCKED_RECORD", than
    assert "báo giá" in than["message"], than["message"]

    ds = client.get("/api/customers").json()
    assert "CUS-KHOA" in {k["id"] for k in ds}


def test_xoa_duoc_khi_khong_con_chung_tu_nao(app_client):
    """Chot chan phai mo ra khi da het rang buoc — khong thi no chi la mot
    cach khac de noi 'khong bao gio xoa duoc'."""
    client, _, _ = app_client
    assert client.post("/api/customers", json={
        "id": "CUS-RANH", "name": "Khach chua co gi"}).status_code in (200, 201)
    assert client.post("/api/routes", json={
        "id": "RT-RANH", "name": "Tuyen chua dung",
        "distance_km": 10, "segments_json": "[]"}).status_code in (200, 201)

    assert client.delete("/api/routes/RT-RANH").status_code == 200
    assert client.delete("/api/customers/CUS-RANH").status_code == 200


def test_khong_xoa_duoc_loai_xe_con_xe_dang_thuoc_loai_do(app_client):
    """`Vehicle.type` la chuoi tu do doi chieu voi `VehicleType.name`, nen xoa
    loai xe la lam phep tra tai trong va gia thanh mat nguon."""
    client, _, _ = app_client
    assert client.post("/api/vehicle-types", json={
        "id": "VT-KHOA", "name": "Xe tai kiem thu", "max_weight": 10000,
    }).status_code in (200, 201)
    assert client.post("/api/vehicles", json={
        "id": "VEH-KHOA", "type": "Xe tai kiem thu", "status": "Sẵn sàng",
    }).status_code in (200, 201)

    r = client.delete("/api/vehicle-types/VT-KHOA")
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "LOCKED_RECORD", r.text


def test_xoa_loai_xe_khong_ton_tai_bao_404_khong_phai_200(app_client):
    """Truoc day tra ve than "Không tìm thấy loại phương tiện" voi MA TRANG
    THAI 200. Giao dien kiem `res.ok`, thay 200, va bao da xoa — than noi mot
    dieu, ma trang thai noi dieu nguoc lai, va giao dien tin ma trang thai."""
    client, _, _ = app_client
    r = client.delete("/api/vehicle-types/VT-KHONG-CO")
    assert r.status_code == 404, r.text

def test_khong_xoa_duoc_loai_xe_khi_xe_ghi_theo_MA_loai(app_client, workflow_builder):
    """Cùng lỗ hổng, nhưng với xe ghi theo MÃ loại xe thay vì TÊN.

    LỖI ĐÃ XẢY RA THẬT: `POST /api/vehicles` chuẩn hoá `type` về mã loại xe
    (nhận cả tên rồi đổi sang mã). Cửa chặn xoá lúc đó chỉ so theo TÊN, nên
    với mọi xe tạo sau thay đổi ấy nó không khớp gì cả và loại xe bị xoá tự do
    — đúng lỗ hổng mà nó được dựng để bịt. Bài kiểm cũ vẫn xanh vì nó gửi tên,
    và tên được đổi thành mã trước khi lưu.

    Nên phải kiểm CẢ HAI đường ghi: gửi tên, và gửi mã.
    """
    client, _, _ = app_client
    workflow_builder.master_data()
    assert client.post("/api/vehicle-types", json={
        "id": "VT-MA", "name": "Xe tai theo ma", "max_weight": 12000,
    }).status_code in (200, 201)
    assert client.post("/api/vehicles", json={
        "id": "VEH-MA", "type": "VT-MA", "status": "Sẵn sàng",
    }).status_code in (200, 201)

    r = client.delete("/api/vehicle-types/VT-MA")
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "LOCKED_RECORD"

    # Đổi loại cho xe rồi mới xoá được.
    assert client.post("/api/vehicle-types", json={
        "id": "VT-MA-2", "name": "Xe tai thay the", "max_weight": 12000,
    }).status_code in (200, 201)
    # `POST /api/vehicles` la duong VUA TAO VUA SUA (upsert), khong co PUT.
    assert client.post("/api/vehicles", json={
        "id": "VEH-MA", "type": "VT-MA-2",
    }).status_code in (200, 201)
    assert client.delete("/api/vehicle-types/VT-MA").status_code == 200
