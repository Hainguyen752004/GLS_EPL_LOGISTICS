import sqlite3


def _completed_source_order(client, workflow_builder, database_file):
    workflow_builder.master_data()
    workflow_builder.quotation(approve=True)
    workflow_builder.sales_order(confirm=True)
    workflow_builder.delivery_order()
    with sqlite3.connect(database_file) as connection:
        connection.execute(
            """
            INSERT INTO delivery_order_details
                (so_id, sku, description, qty, uom, unit_price, amount, weight_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("SO-T1", "SKU-CAFE-01", "Cafe sua hoa tan", 24, "PCS", 10000, 240000, 12.5),
        )


def test_generate_parking_list_from_delivery_order_is_persistent_and_idempotent(
    app_client, workflow_builder
):
    client, database_file, _ = app_client
    _completed_source_order(client, workflow_builder, database_file)
    payload = {
        "store_id": "60017",
        "store_name": "KP CO., LTD",
        "wave": "2",
        "gate": "7",
        "box_count": 2,
    }

    first = client.post("/api/parking-lists/from-do/DO-T1", json=payload)
    second = client.post("/api/parking-lists/from-do/DO-T1", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    data = first.json()["data"]
    assert second.json()["data"]["id"] == data["id"]
    assert data["do_id"] == "DO-T1"
    assert data["status"] == "ready"
    assert data["box_count"] == 2
    assert data["total_pieces"] == 24
    assert data["items"][0]["sku"] == "SKU-CAFE-01"
    assert data["items"][0]["description"] == "Cafe sua hoa tan"
    assert [label["package_no"] for label in data["labels"]] == [1, 2]
    assert all(label["qr_token"] not in {"DO-T1", "SO-T1"} for label in data["labels"])

    listed = client.get("/api/parking-lists", params={"q": "60017"})
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["total"] == 1


def test_auto_generate_can_split_one_delivery_order_into_multiple_packing_lists(
    app_client, workflow_builder
):
    client, database_file, _ = app_client
    _completed_source_order(client, workflow_builder, database_file)
    with sqlite3.connect(database_file) as connection:
        connection.execute(
            "UPDATE delivery_orders SET pallet_count = 4, weight_kg = 120, volume_m3 = 8 WHERE id = ?",
            ("DO-T1",),
        )

    response = client.post(
        "/api/parking-lists/auto-from-do/DO-T1",
        json={"list_count": 2},
    )

    assert response.status_code == 200, response.text
    batch = response.json()["data"]
    assert batch["do_id"] == "DO-T1"
    assert batch["list_count"] == 2
    assert len(batch["items"]) == 2
    assert [item["version"] for item in batch["items"]] == [1, 2]
    assert [item["box_count"] for item in batch["items"]] == [2, 2]
    assert [item["total_pieces"] for item in batch["items"]] == [12, 12]
    assert sum(item["total_weight_kg"] for item in batch["items"]) == 120
    assert sum(item["total_cube_m3"] for item in batch["items"]) == 8
    assert sum(
        row["piece_qty"]
        for item in batch["items"]
        for row in item["items"]
    ) == 24
    assert all(len(item["labels"]) == 2 for item in batch["items"])


def test_auto_generate_rejects_more_packing_lists_than_packages(
    app_client, workflow_builder
):
    client, database_file, _ = app_client
    _completed_source_order(client, workflow_builder, database_file)
    with sqlite3.connect(database_file) as connection:
        connection.execute(
            "UPDATE delivery_orders SET pallet_count = 2 WHERE id = ?",
            ("DO-T1",),
        )

    response = client.post(
        "/api/parking-lists/auto-from-do/DO-T1",
        json={"list_count": 3},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "PACKING_LIST_COUNT_EXCEEDS_PACKAGES"


def test_parking_qr_returns_only_public_operational_snapshot(app_client, workflow_builder):
    client, database_file, _ = app_client
    _completed_source_order(client, workflow_builder, database_file)
    created = client.post(
        "/api/parking-lists/from-do/DO-T1",
        json={"store_id": "60017", "store_name": "KP CO., LTD", "box_count": 1},
    )
    assert created.status_code == 200, created.text
    label = created.json()["data"]["labels"][0]

    scanned = client.get(f"/api/parking-qr/{label['qr_token']}")

    assert scanned.status_code == 200, scanned.text
    public = scanned.json()["data"]
    assert public == {
        "parking_list_id": created.json()["data"]["id"],
        "do_id": "DO-T1",
        "package_no": 1,
        "package_total": 1,
        "status": "ready",
        "store_id": "60017",
        "store_name": "KP CO., LTD",
    }
    assert "customer_id" not in public
    assert "items" not in public


def test_parking_list_status_is_driven_by_qr_scans(app_client, workflow_builder):
    client, database_file, _ = app_client
    _completed_source_order(client, workflow_builder, database_file)
    created = client.post("/api/parking-lists/from-do/DO-T1", json={"box_count": 2})
    parking_id = created.json()["data"]["id"]
    labels = created.json()["data"]["labels"]

    invalid = client.post(
        f"/api/parking-qr/{labels[0]['qr_token']}/scan",
        json={"action": "gate_entry"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_PARKING_SCAN_ORDER"

    # MOT lan quet KHONG du de ca phieu chuyen trang thai — day la cho da sua.
    #
    # Truoc day hai buoc dau (`yard_arrival`, `gate_entry`) chuyen ca phieu ngay
    # khi quet MOT kien, con buoc bocc hang thi doi du moi kien. Hai nghia khac
    # nhau tren cung mot dai trang thai, va ket qua la man hinh ghi "da qua
    # cong" khi moi mot trong hai kien qua cong. Nguoi doc tin con so do.
    #
    # Gio ca ba buoc dung chung mot khuon: danh dau tung nhan, va chi chuyen ca
    # phieu khi MOI nhan da qua buoc do.
    mot_kien = client.post(
        f"/api/parking-qr/{labels[0]['qr_token']}/scan",
        json={"action": "yard_arrival"},
    )
    assert mot_kien.status_code == 200, mot_kien.text
    assert mot_kien.json()["data"]["status"] == "ready", (
        "quet mot kien chua duoc chuyen ca phieu sang 'parked'")
    assert [row["status"] for row in mot_kien.json()["data"]["labels"]] == ["parked", "ready"]

    parked = client.post(
        f"/api/parking-qr/{labels[1]['qr_token']}/scan",
        json={"action": "yard_arrival"},
    )
    assert parked.status_code == 200, parked.text
    assert parked.json()["data"]["status"] == "parked", "du kien roi thi phai chuyen"

    # Cung the o buoc qua cong: mot kien chua du.
    mot_qua_cong = client.post(
        f"/api/parking-qr/{labels[0]['qr_token']}/scan",
        json={"action": "gate_entry"},
    )
    assert mot_qua_cong.status_code == 200, mot_qua_cong.text
    assert mot_qua_cong.json()["data"]["status"] == "parked"

    gate = client.post(
        f"/api/parking-qr/{labels[1]['qr_token']}/scan",
        json={"action": "gate_entry"},
    )
    assert gate.status_code == 200, gate.text
    assert gate.json()["data"]["status"] == "gate_in"

    first_package = client.post(
        f"/api/parking-qr/{labels[0]['qr_token']}/scan",
        json={"action": "load_package"},
    )
    assert first_package.status_code == 200, first_package.text
    assert first_package.json()["data"]["status"] == "gate_in"
    assert [row["status"] for row in first_package.json()["data"]["labels"]] == ["loaded", "gate_in"]

    repeated = client.post(
        f"/api/parking-qr/{labels[0]['qr_token']}/scan",
        json={"action": "load_package"},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["data"]["status"] == "gate_in"

    completed = client.post(
        f"/api/parking-qr/{labels[1]['qr_token']}/scan",
        json={"action": "load_package"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["data"]["status"] == "loaded"
    assert all(row["status"] == "loaded" for row in completed.json()["data"]["labels"])

    manual = client.post(f"/api/parking-lists/{parking_id}/status", json={"status": "dispatched"})
    assert manual.status_code == 409
    assert manual.json()["error"]["code"] == "PARKING_STATUS_AUTOMATED"


def test_parking_list_print_history_is_persistent(app_client, workflow_builder):
    client, database_file, _ = app_client
    _completed_source_order(client, workflow_builder, database_file)
    created = client.post("/api/parking-lists/from-do/DO-T1", json={"box_count": 2})
    parking_id = created.json()["data"]["id"]

    first = client.post(f"/api/parking-lists/{parking_id}/print", json={"document_type": "labels"})
    second = client.post(f"/api/parking-lists/{parking_id}/print", json={"document_type": "labels"})
    packing = client.post(f"/api/parking-lists/{parking_id}/print", json={"document_type": "packing_list"})

    assert first.status_code == 200, first.text
    assert all(label["printed_at"] for label in first.json()["data"]["labels"])
    assert all(label["reprint_count"] == 0 for label in first.json()["data"]["labels"])
    assert all(label["reprint_count"] == 1 for label in second.json()["data"]["labels"])
    assert packing.status_code == 200, packing.text

    reloaded = client.get(f"/api/parking-lists/{parking_id}")
    events = [event["event_type"] for event in reloaded.json()["data"]["events"]]
    assert events.count("labels_printed") == 2
    assert events.count("packing_list_printed") == 1
