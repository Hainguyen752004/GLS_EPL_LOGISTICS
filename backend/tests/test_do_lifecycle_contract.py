import datetime
import importlib


def _create_pending_do(client, workflow_builder, suffix, **overrides):
    workflow_builder.quotation(f"QT-{suffix}", approve=True)
    workflow_builder.sales_order(f"SO-{suffix}", f"QT-{suffix}", confirm=True)
    payload = {"id": f"DO-{suffix}", "so_id": f"SO-{suffix}", **overrides}
    response = client.post("/api/delivery-orders", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_confirmed_sales_order_creates_pending_delivery_order(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()

    delivery = _create_pending_do(client, workflow_builder, "PENDING")

    assert delivery["canonical_status"] == "pending"
    assert delivery["status"] == "Chờ vận chuyển"


def test_delivery_order_has_no_approval_step_and_dispatches_from_pending(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _create_pending_do(client, workflow_builder, "DISPATCH")

    approval = client.put(
        "/api/delivery-orders/DO-DISPATCH/status",
        json={"status": "Approved"},
    )
    assert approval.status_code == 409
    assert approval.json()["detail"]["code"] == "INVALID_STATUS"

    dispatched = client.put(
        "/api/delivery-orders/DO-DISPATCH/dispatch",
        json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"},
    )
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["data"]["canonical_status"] == "in_transit"
    assert dispatched.json()["data"]["status"] == "Đang vận chuyển"


def test_legacy_delivery_dispatch_rejects_vehicle_capacity_without_mutating_state(
    app_client, workflow_builder
):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")

    workflow_builder.quotation("QT-CAPACITY", approve=True)
    workflow_builder.sales_order("SO-CAPACITY", "QT-CAPACITY", confirm=False)
    assert client.put("/api/sales-orders/SO-CAPACITY", json={
        "weight_kg": 12_000,
        "volume_m3": 42,
        "pallet_count": 24,
    }).status_code == 200
    assert client.put("/api/sales-orders/SO-CAPACITY/confirm").status_code == 200
    assert client.post("/api/delivery-orders", json={
        "id": "DO-CAPACITY", "so_id": "SO-CAPACITY",
    }).status_code == 200

    with database.SessionLocal() as db:
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.weight_capacity = 10_000
        vehicle.volume_capacity_m3 = 30
        vehicle.pallet_capacity = 20
        original_vehicle_status = vehicle.status
        original_driver_status = db.get(models.Driver, "DRV-T1").status
        db.commit()

    response = client.put("/api/delivery-orders/DO-CAPACITY/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1",
    })

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "CAPACITY_EXCEEDED"
    assert "12.000/10.000 kg" in response.json()["detail"]["message"]
    with database.SessionLocal() as db:
        delivery = db.get(models.DeliveryOrder, "DO-CAPACITY")
        vehicle = db.get(models.Vehicle, "VEH-T1")
        driver = db.get(models.Driver, "DRV-T1")
        assert delivery.canonical_status == "pending"
        assert delivery.vehicle_id is None
        assert delivery.driver_id is None
        assert vehicle.status == original_vehicle_status
        assert driver.status == original_driver_status


def test_pending_delivery_order_can_be_cancelled(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _create_pending_do(client, workflow_builder, "CANCEL")

    cancelled = client.put(
        "/api/delivery-orders/DO-CANCEL/status",
        json={"status": "Cancelled"},
    )

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["canonical_status"] == "cancelled"
    assert cancelled.json()["data"]["status"] == "Đã hủy"


def test_pending_delivery_order_with_active_trip_cannot_be_cancelled(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _create_pending_do(client, workflow_builder, "ACTIVE-TRIP")

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    base = datetime.datetime(2026, 8, 20, 1, 0)
    with database.SessionLocal() as db:
        db.add_all([
            models.Location(id="LOC-ACTIVE-A", name="Kho A"),
            models.Location(id="LOC-ACTIVE-B", name="Kho B"),
        ])
        db.flush()
        db.add(models.FreightOrder(
            id="FO-ACTIVE",
            pickup_location_id="LOC-ACTIVE-A",
            delivery_location_id="LOC-ACTIVE-B",
            pickup_window_start=base,
            pickup_window_end=base + datetime.timedelta(hours=1),
            delivery_window_start=base + datetime.timedelta(hours=2),
            delivery_window_end=base + datetime.timedelta(hours=3),
            total_weight_kg=1,
            total_volume_m3=1,
            total_pallet_count=1,
            max_weight_kg=1,
            max_volume_m3=1,
            max_pallet_count=1,
        ))
        db.flush()
        db.add(models.TransportTrip(id="TRIP-ACTIVE", freight_order_id="FO-ACTIVE", status="planned"))
        db.flush()
        db.add(models.TripDeliveryOrder(trip_id="TRIP-ACTIVE", do_id="DO-ACTIVE-TRIP"))
        db.commit()

    response = client.put(
        "/api/delivery-orders/DO-ACTIVE-TRIP/status",
        json={"status": "Cancelled"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACTIVE_TRIP_EXISTS"
    with database.SessionLocal() as db:
        assert db.get(models.DeliveryOrder, "DO-ACTIVE-TRIP").canonical_status == "pending"


def test_delivery_order_commands_reject_unknown_fields(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-STRICT", approve=True)
    workflow_builder.sales_order("SO-STRICT", "QT-STRICT", confirm=True)

    create = client.post(
        "/api/delivery-orders",
        json={"id": "DO-STRICT", "so_id": "SO-STRICT", "approved": True},
    )
    assert create.status_code == 422

    valid = client.post(
        "/api/delivery-orders",
        json={"id": "DO-STRICT", "so_id": "SO-STRICT"},
    )
    assert valid.status_code == 200

    assert client.put(
        "/api/delivery-orders/DO-STRICT",
        json={"origin": "Kho A", "unexpected": "value"},
    ).status_code == 422


def test_delivery_order_commands_reject_naive_datetimes(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-TZ", approve=True)
    workflow_builder.sales_order("SO-TZ", "QT-TZ", confirm=True)

    create_fields = (
        "pickup_window_start", "pickup_window_end",
        "delivery_window_start", "delivery_window_end",
        "pickup_date", "delivery_date",
    )
    for field in create_fields:
        response = client.post(
            "/api/delivery-orders",
            json={"id": "DO-TZ", "so_id": "SO-TZ", field: "2026-08-20T08:00:00"},
        )
        assert response.status_code == 422, (field, response.text)

    created = client.post(
        "/api/delivery-orders",
        json={"id": "DO-TZ", "so_id": "SO-TZ", "pickup_window_start": "2026-08-20T08:00:00+07:00"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["pickup_window_start"] == "2026-08-20T01:00:00Z"

    for field in create_fields:
        response = client.put(
            "/api/delivery-orders/DO-TZ",
            json={field: "2026-08-20T08:00:00"},
        )
        assert response.status_code == 422, (field, response.text)

    for field in ("departure_at", "planned_departure_at"):
        response = client.put(
            "/api/delivery-orders/DO-TZ/dispatch",
            json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1", field: "2026-08-20T08:00:00"},
        )
        assert response.status_code == 422, (field, response.text)
    assert client.put(
        "/api/delivery-orders/DO-STRICT/status",
        json={"status": "Cancelled", "reason": "not-yet-supported"},
    ).status_code == 422
    assert client.put(
        "/api/delivery-orders/DO-STRICT/dispatch",
        json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "force": True},
    ).status_code == 422


def test_analysis_tach_qua_han_va_thieu_han_thanh_ro_rieng(app_client, workflow_builder):
    """Bay ro, va don qua han khong con nam chung voi don con thoi gian.

    Ban truoc chi co nam ro va gop hai truong hop khac han nhau vao
    "Cho van chuyen":

      - DON QUA HAN chi duoc danh dau bang co `is_overdue`, ma man hinh khong
        doc co do. Mot DO qua han ba tuan va mot DO con hai tuan nua moi den
        han khong the nam cung mot cho.

      - DON THIEU HAN GIAO (khong co ngay lay lan ngay giao nao) cung roi vao
        do, nen khong ai thay la no thieu — du no khong lap ke hoach duoc va
        cung khong do tre duoc.
    """
    client, _, _ = app_client
    workflow_builder.master_data()
    now = datetime.datetime(2026, 8, 20, 5, 0, tzinfo=datetime.timezone.utc)
    cases = {
        "OVERDUE": "2026-08-20T11:59:59+07:00",
        "NEAR": "2026-08-21T12:00:00+07:00",
        "PENDING": "2026-08-21T12:00:01+07:00",
    }
    for suffix, due in cases.items():
        _create_pending_do(
            client,
            workflow_builder,
            suffix,
            pickup_window_start=due,
        )

    _create_pending_do(client, workflow_builder, "NAIVE")

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    workflow = importlib.import_module("services.workflow_service")
    with database.SessionLocal() as db:
        db.get(models.DeliveryOrder, "DO-NAIVE").pickup_window_start = datetime.datetime(
            2026, 8, 21, 4, 0
        )
        db.commit()
        payload = workflow.delivery_order_analysis(db, now=now)

    assert set(payload["buckets"]) == {
        "incident", "overdue", "undated", "near_late", "pending", "active", "completed"
    }
    # Thu tu cap bach phai duoc tra ve, de man hinh mo san dung tab thay vi mo
    # cung mot ro co the dang rong.
    assert payload["urgency"] == [
        "incident", "overdue", "undated", "near_late", "pending", "active", "completed"
    ]
    records = {record["id"]: record for record in payload["records"]}
    # Qua han la mot RO RIENG, khong con la mot co gan tren "cho van chuyen".
    assert records["DO-OVERDUE"]["stage"] == "overdue"
    assert records["DO-OVERDUE"]["is_overdue"] is True
    assert records["DO-OVERDUE"]["is_near_late"] is False
    assert "quá hạn" in records["DO-OVERDUE"]["reason"]
    assert records["DO-NEAR"]["stage"] == "near_late"
    assert records["DO-NEAR"]["is_near_late"] is True
    assert records["DO-PENDING"]["stage"] == "pending"
    assert records["DO-PENDING"]["is_overdue"] is False
    assert records["DO-NAIVE"]["stage"] == "near_late"
    assert records["DO-NAIVE"]["due_at"].endswith("+00:00")
    assert records["DO-NAIVE"]["due_at_local"].endswith("+07:00")

    # DO khong co ngay nao ca phai vao ro RIENG "thieu han giao".
    #
    # Truoc day no lan vao "Cho van chuyen" nen khong ai thay la no thieu, du
    # no khong lap ke hoach duoc va cung khong do tre duoc. Trong co so du lieu
    # that dang co ba DO nhu vay.
    _create_pending_do(client, workflow_builder, "NODATE")
    with database.SessionLocal() as db:
        don = db.get(models.DeliveryOrder, "DO-NODATE")
        for field in (
            "planned_departure_at", "pickup_window_start", "pickup_date",
            "delivery_window_start", "delivery_date", "delivery_window_end",
            "planned_arrival_at",
        ):
            setattr(don, field, None)
        db.commit()
        payload = workflow.delivery_order_analysis(db, now=now)

    ro = {record["id"]: record for record in payload["records"]}["DO-NODATE"]
    assert ro["stage"] == "undated"
    assert ro["due_at"] is None
    # Khong co han thi khong the qua han: bao "qua han" o day la bia ra mot cai
    # han khong ton tai.
    assert ro["is_overdue"] is False
    assert ro["is_near_late"] is False
    assert "chưa có ngày" in ro["reason"]
    assert payload["buckets"]["undated"]["count"] == 1


def test_incident_is_derived_without_changing_canonical_status(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    _create_pending_do(client, workflow_builder, "INCIDENT")

    incident = client.post(
        "/api/incidents",
        json={
            "do_id": "DO-INCIDENT",
            "vehicle_id": "VEH-T1",
            "incident_type": "Kẹt xe",
            "location": "Cảng Cát Lái",
            "reporter": "Điều phối",
        },
    )
    assert incident.status_code == 200, incident.text

    analysis = client.get("/api/delivery-orders/analysis").json()
    record = next(row for row in analysis["records"] if row["id"] == "DO-INCIDENT")
    assert record["stage"] == "incident"
    assert record["canonical_status"] == "pending"
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        assert db.get(models.DeliveryOrder, "DO-INCIDENT").canonical_status == "pending"
