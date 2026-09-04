"""Sửa một xe không được xóa trắng những trường không gửi kèm.

Lỗi tìm được khi thử từng nút Thêm / Sửa / Xóa của hai bảng Master Data trên máy
chủ thật: `POST /api/vehicles` dựng một đối tượng `Vehicle` mới với mọi trường
lấy từ `data.get(..., mặc_định)` rồi `db.merge()`. Nghĩa là sửa `brand` và
`weight_capacity` của một xe đã có bãi "Bãi Sóng Thần" thì **bãi biến thành
NULL**, không một thông báo nào.

Ở đội 500 xe đó là mất dữ liệu thầm lặng: sửa tải trọng một xe là mất luôn thông
tin bãi của xe đó. Đọc mã nguồn không thấy được — phải gọi thử mới lộ ra.
"""
import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_file = tmp_path / "fleet.sqlite3"
    monkeypatch.setenv("DATABASE_MODE", "sqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_file.as_posix()}")
    monkeypatch.setenv("EPL_ENV_FILE", str(tmp_path / "no-env-file"))
    monkeypatch.delenv("EPL_REQUIRE_API_TOKEN", raising=False)
    for name in [key for key in sys.modules if key in ("main", "database", "models") or key.startswith(("routes", "services", "migrations"))]:
        sys.modules.pop(name, None)

    database = importlib.import_module("database")
    main = importlib.import_module("main")
    database.Base.metadata.create_all(bind=database.engine)
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        database.engine.dispose()


def _vehicle(client, vid):
    rows = client.get("/api/vehicles?paginated=true&page=1&page_size=200").json()["items"]
    return next((row for row in rows if row["id"] == vid), None)


FULL = {
    "id": "51C-777.77",
    "brand": "Hyundai",
    "type": "Container 20FT",
    "weight_capacity": 15000,
    "volume_capacity_m3": 33,
    "pallet_capacity": 20,
    "fuel_norm": 26,
    "depot": "Bãi Sóng Thần",
    "depot_code": "st",
    "engine_no": "ENG-123",
    "chassis_no": "CHS-456",
    "inspection_place": "Trung tâm 50-03V",
}


def test_creating_a_vehicle_stores_every_field(client):
    assert client.post("/api/vehicles", json=FULL).status_code == 200
    row = _vehicle(client, FULL["id"])
    assert row is not None
    assert row["brand"] == "Hyundai"
    assert float(row["weight_capacity"]) == 15000
    assert row["depot"] == "Bãi Sóng Thần"
    # Mã bãi là khóa lọc nên luôn chuẩn hóa về chữ in.
    assert row["depot_code"] == "ST"
    assert row["engine_no"] == "ENG-123"


def test_partial_edit_keeps_the_fields_it_did_not_send(client):
    """Đây là lỗi chính: sửa tải trọng không được làm mất bãi."""
    client.post("/api/vehicles", json=FULL)

    response = client.post("/api/vehicles", json={
        "id": FULL["id"], "brand": "Isuzu", "weight_capacity": 20000,
    })
    assert response.status_code == 200

    row = _vehicle(client, FULL["id"])
    assert row["brand"] == "Isuzu", "trường đã gửi phải đổi"
    assert float(row["weight_capacity"]) == 20000
    # Và mọi trường KHÔNG gửi phải còn nguyên.
    assert row["depot"] == "Bãi Sóng Thần", "bãi bị xóa trắng — đúng lỗi đã sửa"
    assert row["depot_code"] == "ST"
    assert row["type"] == "Container 20FT"
    assert row["engine_no"] == "ENG-123"
    assert row["chassis_no"] == "CHS-456"
    assert row["inspection_place"] == "Trung tâm 50-03V"
    assert float(row["volume_capacity_m3"]) == 33
    assert int(row["pallet_capacity"]) == 20
    assert float(row["fuel_norm"]) == 26


def test_sending_an_empty_string_does_clear_the_field(client):
    """Gửi chuỗi rỗng là CỐ Ý xóa — khác hẳn không gửi gì.

    Phải phân biệt được hai việc này, nếu không người dùng sẽ không xóa được
    thông tin bãi của một xe.
    """
    client.post("/api/vehicles", json=FULL)
    client.post("/api/vehicles", json={"id": FULL["id"], "depot": "", "depot_code": ""})
    row = _vehicle(client, FULL["id"])
    assert not row["depot"], "gửi rỗng thì phải xóa được"
    assert not row["depot_code"]


def test_editing_does_not_create_a_duplicate(client):
    client.post("/api/vehicles", json=FULL)
    client.post("/api/vehicles", json={"id": FULL["id"], "brand": "Isuzu"})
    rows = client.get("/api/vehicles?paginated=true&page=1&page_size=200").json()["items"]
    assert len([row for row in rows if row["id"] == FULL["id"]]) == 1


def test_editing_keeps_the_operational_status(client):
    """Trạng thái xe do luồng điều phối đặt, không phải do form Master Data.

    Ghi đè nó khi sửa hồ sơ xe sẽ "giải phóng" một chiếc đang chạy chuyến.
    """
    client.post("/api/vehicles", json=FULL)
    client.post("/api/vehicles", json={"id": FULL["id"], "brand": "Isuzu"})
    row = _vehicle(client, FULL["id"])
    assert row["status"] == "Sẵn sàng"


def test_a_new_vehicle_still_gets_sensible_defaults(client):
    """Xe mới chỉ gửi biển số thì các mặc định vẫn phải được đặt."""
    assert client.post("/api/vehicles", json={"id": "51C-888.88"}).status_code == 200
    row = _vehicle(client, "51C-888.88")
    assert row["brand"] == "Hyundai"
    assert float(row["volume_capacity_m3"]) == 30.0
    assert float(row["avg_speed_kmh"]) == 45.0
    assert row["depot"] is None, "xe mới chưa gán bãi thì phải là NULL, không phải chuỗi rỗng"


def test_bad_number_is_rejected_not_silently_zeroed(client):
    client.post("/api/vehicles", json=FULL)
    response = client.post("/api/vehicles", json={"id": FULL["id"], "weight_capacity": "không phải số"})
    assert response.status_code == 422
    # Và bản ghi cũ không bị đụng tới.
    assert float(_vehicle(client, FULL["id"])["weight_capacity"]) == 15000


def test_missing_plate_is_rejected(client):
    assert client.post("/api/vehicles", json={"brand": "Hyundai"}).status_code == 400


def test_delete_really_removes_the_vehicle(client):
    client.post("/api/vehicles", json=FULL)
    assert client.delete(f"/api/vehicles/{FULL['id']}").status_code == 200
    assert _vehicle(client, FULL["id"]) is None
