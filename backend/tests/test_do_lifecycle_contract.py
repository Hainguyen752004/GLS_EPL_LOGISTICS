import datetime
import importlib

from conftest import dieu_phoi_qua_chuyen


def _khung_gio_cho(client, do_id, dau=None, cuoi=None):
    """Dat du bon moc khung gio cho mot lenh — buoc lap chuyen doi ca bon."""
    import datetime as _dt
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    dau = dau or _dt.datetime(2026, 8, 12, 1, 0, tzinfo=_dt.timezone.utc)
    cuoi = cuoi or _dt.datetime(2026, 8, 12, 13, 0, tzinfo=_dt.timezone.utc)
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        do.pickup_window_start = dau
        do.pickup_window_end = dau + _dt.timedelta(hours=3)
        do.delivery_window_start = dau + _dt.timedelta(hours=3)
        do.delivery_window_end = cuoi
        db.commit()


def _create_pending_do(client, workflow_builder, suffix, **overrides):
    workflow_builder.quotation(f"QT-{suffix}", approve=True)
    workflow_builder.delivery_order(f"DO-{suffix}", f"QT-{suffix}", **overrides)
    ds = client.get("/api/delivery-orders?page=1&page_size=200").json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    return next(x for x in ds if x["id"] == f"DO-{suffix}")


def test_bao_gia_duoc_chap_nhan_sinh_lenh_cho_van_chuyen(app_client, workflow_builder):
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

    # Dieu phoi di qua CHUYEN — duong dieu phoi le da dong phan ghi.
    dieu_phoi_qua_chuyen(client, "DO-DISPATCH")
    ds = client.get("/api/delivery-orders?page=1&page_size=50").json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    sau = next(x for x in ds if x["id"] == "DO-DISPATCH")
    assert sau["canonical_status"] == "in_transit"
    assert sau["status"] == "Đang vận chuyển"


def test_legacy_delivery_dispatch_rejects_vehicle_capacity_without_mutating_state(
    app_client, workflow_builder
):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")

    workflow_builder.quotation("QT-CAPACITY", approve=True)
    workflow_builder.delivery_order("DO-CAPACITY", "QT-CAPACITY", weight_kg=12_000, volume_m3=42, pallet_count=24)

    with database.SessionLocal() as db:
        vehicle = db.get(models.Vehicle, "VEH-T1")
        vehicle.weight_capacity = 10_000
        vehicle.volume_capacity_m3 = 30
        vehicle.pallet_capacity = 20
        original_vehicle_status = vehicle.status
        original_driver_status = db.get(models.Driver, "DRV-T1").status
        db.commit()

    # Cua nang luc xe nay o buoc DIEU PHOI CHUYEN. Lap chuyen truoc, roi dieu.
    _khung_gio_cho(client, "DO-CAPACITY")
    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": "TRIP-CAPACITY", "do_ids": ["DO-CAPACITY"], "trip_type": "one_way",
        "planned_departure_at": "2026-08-12T01:00:00+00:00", "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={"Idempotency-Key": "trip-capacity"})
    assert r.status_code in (200, 201), r.text
    response = client.put("/api/tms/trips/TRIP-CAPACITY/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": int((r.json().get("data") or {}).get("version") or 1),
        "assignment_start": "2026-08-12T01:00:00+00:00",
        "assignment_end": "2026-08-12T13:00:00+00:00",
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
        json={"status": "Cancelled", "reason": "Khách huỷ đơn — bài kiểm vòng đời DO"},
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
        json={"status": "Cancelled", "reason": "Khách huỷ đơn — bài kiểm vòng đời DO"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACTIVE_TRIP_EXISTS"
    with database.SessionLocal() as db:
        assert db.get(models.DeliveryOrder, "DO-ACTIVE-TRIP").canonical_status == "pending"


def test_delivery_order_commands_reject_unknown_fields(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-STRICT", approve=True)
    workflow_builder.delivery_order("DO-STRICT", "QT-STRICT")

    assert client.put(
        "/api/delivery-orders/DO-STRICT",
        json={"origin": "Kho A", "unexpected": "value"},
    ).status_code == 422


def test_delivery_order_commands_reject_naive_datetimes(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-TZ", approve=True)
    workflow_builder.delivery_order("DO-TZ", "QT-TZ")

    fields = ("pickup_window_start", "pickup_window_end", "delivery_window_start",
              "delivery_window_end", "pickup_date", "delivery_date")
    for field in fields:
        response = client.put("/api/delivery-orders/DO-TZ", json={field: "2026-08-20T08:00:00"})
        assert response.status_code == 422, (field, response.text)
    updated = client.put("/api/delivery-orders/DO-TZ", json={"pickup_window_start": "2026-08-20T08:00:00+07:00"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["pickup_window_start"] == "2026-08-20T01:00:00Z"

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
        "incident", "overdue", "undated", "near_late", "pending", "active",
        "completed", "cancelled"
    }
    # Thu tu cap bach phai duoc tra ve, de man hinh mo san dung tab thay vi mo
    # cung mot ro co the dang rong.
    # "cancelled" xep CUOI: viec da huy khong bao gio la tab mo san.
    assert payload["urgency"] == [
        "incident", "overdue", "undated", "near_late", "pending", "active",
        "completed", "cancelled"
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


def test_duong_dieu_phoi_le_DA_DONG_PHAN_GHI(app_client, workflow_builder):
    """`PUT /api/delivery-orders/{id}/dispatch` khong con ghi gi ca.

    VI SAO DONG, chu khong va them cua. Ban truoc da co du 5 cua kiem cua dieu
    phoi chuyen, nhung no VAN khong lap Chuyen va khong tao phan cong — nen
    lenh di qua day roi vao mot trang thai khong co duong ra:

      · nop POD -> POD_LINEAGE_INVALID (doi chuyen + thanh vien)
      · doi sang da giao -> ATOMIC_COMPLETION_REQUIRED
      · huy -> bang chuyen trang thai khong cho `in_transit` sang huy
      · lap chuyen de chua -> DELIVERY_ORDER_NOT_PENDING
      · ghi moc -> doi mot phan cong dang mo

    Va xe cung ca to lai bi giu vinh vien, vi moi duong giai phong deu di qua
    chuyen. Them cua khong chua duoc mot ban ghi thieu xuong song.
    """
    client, _, _ = app_client
    workflow_builder.master_data()
    _create_pending_do(client, workflow_builder, "LEGACY")
    workflow_builder.san_sang_dieu_phoi("DO-LEGACY")

    r = client.put("/api/delivery-orders/DO-LEGACY/dispatch",
                   json={"vehicle_id": "VEH-T1", "driver_id": "DRV-T1"})
    assert r.status_code == 409, r.text
    loi = r.json()["detail"]
    assert loi["code"] == "DISPATCH_VIA_TRIP_REQUIRED"
    # Cau bao loi phai NOI DUNG hai buoc phai lam, khong chi noi "khong duoc".
    assert "from-delivery-orders" in loi["message"]
    assert "trips" in loi["message"]

    # Va khong doi gi ca: lenh van cho dieu phoi, xe van san sang.
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, "DO-LEGACY")
        assert do.canonical_status == "pending"
        assert do.vehicle_id is None and do.driver_id is None
        assert db.get(models.Vehicle, "VEH-T1").status == "Sẵn sàng"


def test_dieu_phoi_chuyen_co_DU_CUA_theo_dung_thu_tu(app_client, workflow_builder):
    """Bon cua cua dieu phoi chuyen, theo dung thu tu nguoi dung se vap.

      1. to lai chua co ca lam viec  -> DRIVER_WORK_SCHEDULE_REQUIRED
      2. xe het han phap ly          -> VEHICLE_LEGAL_EXPIRED
      3. tai xe chua co bang lai     -> DRIVER_LICENSE_INVALID
      4. hang dem kien chua quet du  -> PACKING_LIST_REQUIRED
      5. du het                      -> 200, lenh sang dang van chuyen
    """
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    _create_pending_do(client, workflow_builder, "GATE")
    _khung_gio_cho(client, "DO-GATE")

    r = client.post("/api/tms/trips/from-delivery-orders", json={
        "id": "TRIP-GATE", "do_ids": ["DO-GATE"], "trip_type": "one_way",
        "planned_departure_at": "2026-08-12T01:00:00+00:00", "avg_speed_kmh": 40,
        "dwell_minutes": 30, "return_purpose": "none",
    }, headers={"Idempotency-Key": "trip-gate"})
    assert r.status_code in (200, 201), r.text

    def ma_loi():
        tra = client.get("/api/tms/trips/TRIP-GATE")
        pb = int((tra.json()["data"] or {}).get("version") or 1)
        kq = client.put("/api/tms/trips/TRIP-GATE/dispatch", json={
            "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
            "expected_version": pb,
            "assignment_start": "2026-08-12T01:00:00+00:00",
            "assignment_end": "2026-08-12T13:00:00+00:00",
        })
        return kq.status_code, (kq.json().get("detail") or {}).get("code")

    # 1. To lai chua co ca lam viec nao phu chuyen.
    assert ma_loi() == (409, "DRIVER_WORK_SCHEDULE_REQUIRED")
    assert client.post("/api/tms/scheduling/driver-shifts", json={
        "id": "SHIFT-GATE", "driver_id": "DRV-T1", "shift_type": "custom",
        "availability_kind": "work", "shift_start": "2025-01-01T00:00:00+00:00",
        "shift_end": "2028-12-31T00:00:00+00:00", "status": "confirmed",
    }).status_code in (200, 201)
    # 2. Xe cua bo dung khong co han phap ly nao.
    assert ma_loi() == (409, "VEHICLE_LEGAL_EXPIRED")
    with database.SessionLocal() as db:
        xe = db.get(models.Vehicle, "VEH-T1")
        xe.inspection_exp = xe.insurance_date = xe.maintenance_date = "2028-12-31"
        db.get(models.Driver, "DRV-T1").license_type = "FC"
        db.commit()
    # 3. Chua co bang lai.
    assert ma_loi() == (409, "DRIVER_LICENSE_INVALID")
    assert client.post("/api/tms/driver-qualifications", json={
        "driver_id": "DRV-T1", "license_type": "FC", "valid_from": "2025-01-01",
        "valid_to": "2028-12-31", "status": "active",
    }).status_code in (200, 201)
    # 4. Hang dem theo kien (quy cach mac dinh "Thung Carton") chua co Packing List.
    assert ma_loi() == (409, "PACKING_LIST_REQUIRED")
    from conftest import quet_du_kien
    quet_du_kien(client, "DO-GATE")
    # 5. Du het.
    tra = client.get("/api/tms/trips/TRIP-GATE")
    pb = int((tra.json()["data"] or {}).get("version") or 1)
    r = client.put("/api/tms/trips/TRIP-GATE/dispatch", json={
        "vehicle_id": "VEH-T1", "driver_id": "DRV-T1", "co_driver_id": None,
        "expected_version": pb,
        "assignment_start": "2026-08-12T01:00:00+00:00",
        "assignment_end": "2026-08-12T13:00:00+00:00",
    })
    assert r.status_code == 200, r.text
    with database.SessionLocal() as db:
        assert db.get(models.DeliveryOrder, "DO-GATE").canonical_status == "in_transit"


