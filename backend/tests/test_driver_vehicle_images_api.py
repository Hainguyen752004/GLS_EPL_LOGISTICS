def test_driver_and_vehicle_image_fields_are_saved_and_returned(app_client):
    client, _, _ = app_client

    vehicle_image = "/uploads/vehicles/vehicle-demo.png"
    driver_photo = "/uploads/drivers/driver-demo.png"

    vehicle_res = client.post("/api/vehicles", json={
        "id": "51C-IMG-01",
        "brand": "Hyundai",
        "type": "Xe tải thùng",
        "image_url": vehicle_image,
    })
    assert vehicle_res.status_code in (200, 201)
    vehicles = client.get("/api/vehicles").json()
    assert next(v for v in vehicles if v["id"] == "51C-IMG-01")["image_url"] == vehicle_image

    driver_res = client.post("/api/drivers", json={
        "id": "DRV-IMG-01",
        "name": "Tài xế Có Ảnh",
        "photo_url": driver_photo,
    })
    assert driver_res.status_code in (200, 201)
    drivers = client.get("/api/drivers").json()
    assert next(d for d in drivers if d["id"] == "DRV-IMG-01")["photo_url"] == driver_photo


def test_vehicle_image_upload_returns_safe_served_url_and_persists_to_vehicle(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    monkeypatch.setenv("EPL_UPLOAD_DIR", str(tmp_path / "uploads"))
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

    upload = client.post(
        "/api/uploads/images",
        data={"entity_type": "vehicles"},
        files={"file": ("xe-demo.png", png_bytes, "image/png")},
    )

    assert upload.status_code == 201
    payload = upload.json()["data"]
    assert payload["url"].startswith("/uploads/vehicles/")
    assert payload["url"].endswith(".png")
    assert ".." not in payload["url"]
    assert (tmp_path / "uploads" / "vehicles" / payload["filename"]).read_bytes() == png_bytes
    served = client.get(payload["url"])
    assert served.status_code == 200
    assert served.content == png_bytes

    vehicle_res = client.post("/api/vehicles", json={
        "id": "51C-UPLOAD-01",
        "brand": "Hyundai",
        "type": "Xe tải thùng",
        "image_url": payload["url"],
    })
    assert vehicle_res.status_code in (200, 201)
    vehicles = client.get("/api/vehicles").json()
    assert next(v for v in vehicles if v["id"] == "51C-UPLOAD-01")["image_url"] == payload["url"]


def test_driver_photo_upload_validates_target_signature_and_size(app_client, tmp_path, monkeypatch):
    client, _, _ = app_client
    monkeypatch.setenv("EPL_UPLOAD_DIR", str(tmp_path / "uploads"))

    bad_target = client.post(
        "/api/uploads/images",
        data={"entity_type": "../drivers"},
        files={"file": ("driver.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert bad_target.status_code == 422
    assert bad_target.json()["detail"]["code"] == "INVALID_UPLOAD_TARGET"

    fake_image = client.post(
        "/api/uploads/images",
        data={"entity_type": "drivers"},
        files={"file": ("driver.png", b"not an image", "image/png")},
    )
    assert fake_image.status_code == 400
    assert fake_image.json()["detail"]["code"] == "INVALID_IMAGE_UPLOAD"

    too_large = client.post(
        "/api/uploads/images",
        data={"entity_type": "drivers"},
        files={"file": ("driver.jpg", b"\xff\xd8\xff" + b"0" * (2 * 1024 * 1024 + 1), "image/jpeg")},
    )
    assert too_large.status_code == 413
    assert too_large.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"
