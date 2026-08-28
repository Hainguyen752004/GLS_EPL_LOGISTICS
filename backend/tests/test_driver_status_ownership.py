import importlib


def test_driver_master_save_cannot_create_or_override_operational_status(app_client):
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")

    created = client.post(
        "/api/drivers",
        json={
            "id": "DRV-STATUS-OWNER",
            "name": "Tài xế trạng thái hệ thống",
            "status": "Bận - Đang theo xe",
            "assigned_vehicle": "VEH-MANUAL",
        },
    )
    assert created.status_code == 200
    assert "Rảnh" in created.json()["data"]["status"]

    with database.SessionLocal() as db:
        driver = db.get(models.Driver, "DRV-STATUS-OWNER")
        driver.status = "Đang thực hiện TRIP-REAL-001"
        driver.assigned_vehicle = "VEH-REAL-001"
        db.commit()

    edited = client.post(
        "/api/drivers",
        json={
            "id": "DRV-STATUS-OWNER",
            "name": "Tên hồ sơ đã sửa",
            "phone": "0909000111",
            "status": "Rảnh - Sẵn sàng",
            "assigned_vehicle": "Chưa gán",
        },
    )
    assert edited.status_code == 200
    payload = edited.json()["data"]
    assert payload["name"] == "Tên hồ sơ đã sửa"
    assert payload["phone"] == "0909000111"
    assert payload["status"] == "Đang thực hiện TRIP-REAL-001"
    assert payload["assigned_vehicle"] == "VEH-REAL-001"
