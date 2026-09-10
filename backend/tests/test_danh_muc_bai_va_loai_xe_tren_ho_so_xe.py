# -*- coding: utf-8 -*-
"""Bãi / chi nhánh là DANH MỤC (bảng `locations`), loại xe hiện theo TÊN, chọn theo MÃ.

Chủ dự án soi ảnh màn Đội xe và hỏi ba điều:

1. Cột "Loại phương tiện" hiện `DEMO-VT-TRUCK10` — là MÃ, không phải tên. Vì xe
   lưu mã loại (máy chủ chuẩn hoá khi lưu) mà giao diện hiện thẳng cột `type`.
2. Mở hồ sơ xe thì ô "Loại phương tiện" TRỐNG — vì ô chọn dựng giá trị theo
   TÊN, còn xe lưu MÃ, không khớp.
3. "Bãi / Chi nhánh" và "Mã bãi" là hai ô gõ tự do, không có danh mục nào đứng
   sau. Màn Điều phối gom đội xe "theo bãi" bằng chính chuỗi người ta gõ.

Ba việc khoá lại ở đây:
- `GET /api/vehicles` trả cả `vehicle_type_id` và `vehicle_type_name` (tra theo
  mã HOẶC tên, vì xe cũ có thể còn lưu tên), và `depot_name` tra từ danh mục.
- `GET /api/depots` liệt kê bãi từ `locations` theo loại bãi, kèm số xe / số
  tài xế đang thuộc; `Waypoint` / `RoutePoint` không phải bãi.
- `POST /api/depots` thêm bãi, đòi cả mã và tên.
"""
import importlib

from conftest import API_TEST_HEADERS


def test_ho_so_xe_tra_ten_loai_xe_va_ten_bai(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    assert client.post("/api/vehicle-types", json={
        "id": "VT-TEN", "name": "Xe tải thùng 8 tấn", "max_weight": 8000,
    }).status_code in (200, 201)
    # Xe MOI: gui TEN, may chu chuan hoa ve MA.
    assert client.post("/api/vehicles", json={
        "id": "VEH-TEN-1", "type": "Xe tải thùng 8 tấn", "depot_code": "BAI-A", "depot": "gõ tay",
    }).status_code in (200, 201)
    # Xe CU: con luu TEN trong cot `type` (ghi thang vao CSDL, nhu du lieu truoc chuan hoa).
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.Vehicle(id="VEH-TEN-CU", type="Xe tải thùng 8 tấn"))
        db.add(models.Location(id="BAI-A", name="Bãi Kiểm A", type="Depot"))
        db.commit()

    ds = client.get("/api/vehicles").json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    moi = next(x for x in ds if x["id"] == "VEH-TEN-1")
    cu = next(x for x in ds if x["id"] == "VEH-TEN-CU")
    for x in (moi, cu):
        assert x["vehicle_type_id"] == "VT-TEN", x
        assert x["vehicle_type_name"] == "Xe tải thùng 8 tấn", x
    # Ten bai tra tu DANH MUC theo ma bai, khong phai chuoi go tay.
    assert moi["depot_name"] == "Bãi Kiểm A", moi


def test_danh_muc_bai_doc_tu_locations_va_dem_xe_tai_xe(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        db.add(models.Location(id="BAI-1", name="Bãi Một", type="Depot"))
        db.add(models.Location(id="KHO-2", name="Kho Hai", type="Warehouse"))
        db.add(models.Location(id="DIEM-TUYEN", name="Điểm giữa tuyến", type="RoutePoint"))
        db.add(models.Location(id="DIEM-QUA", name="Vành đai", type="Waypoint"))
        db.commit()
        xe = db.get(models.Vehicle, "VEH-T1")
        xe.depot_code = "BAI-1"
        tx = db.get(models.Driver, "DRV-T1")
        tx.depot_code = "BAI-1"
        db.commit()

    r = client.get("/api/depots")
    assert r.status_code == 200, r.text
    ds = {x["id"]: x for x in r.json()}
    assert set(ds) >= {"BAI-1", "KHO-2"}
    # Diem tren tuyen KHONG phai bai.
    assert "DIEM-TUYEN" not in ds and "DIEM-QUA" not in ds
    assert ds["BAI-1"]["vehicle_count"] == 1
    assert ds["BAI-1"]["driver_count"] == 1
    assert ds["KHO-2"]["vehicle_count"] == 0


def test_them_bai_doi_ca_ma_va_ten(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    r = client.post("/api/depots", json={"id": "BAI-MOI", "name": ""}, headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    r = client.post("/api/depots", json={"id": "BAI-MOI", "name": "Bãi Mới", "type": "RoutePoint"},
                    headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    r = client.post("/api/depots", json={"id": "BAI-MOI", "name": "Bãi Mới", "type": "Depot",
                                         "address": "QL1A"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert any(x["id"] == "BAI-MOI" for x in client.get("/api/depots").json())
