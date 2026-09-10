import datetime as dt
import importlib
from decimal import Decimal


def test_demo_seed_builds_three_complete_workflow_scenarios(app_client):
    _, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    seed_service = importlib.import_module("services.demo_seed_service")

    with database.SessionLocal() as db:
        first = seed_service.seed_demo(db, reset=True, verify=True)
        second = seed_service.seed_demo(db, reset=False, verify=True)

        assert first == second
        assert first["waiting"]["delivery_order_id"] == "DEMO-DO-2026-001"
        assert first["tracking"]["delivery_order_id"] == "DEMO-DO-2026-002"
        assert first["completed"]["delivery_order_id"] == "DEMO-DO-2026-003"
        # Ma ca truc mang NGAY HOM NAY, khong ghim mot ngay co dinh.
        #
        # Ban truoc do dung "DEMO-SHIFT-20260824-%". Bo nap da doi sang tinh moc
        # theo hom nay, va do la mot sua loi that: man xep ca chi mo TUAN CHUA
        # NGAY HOM NAY, nen ca truc ghim thang 8 khong bao gio hien ra o do — do
        # duoc, luoi xep ca trong tron.
        #
        # Bai kiem gio khoa CA HAI dieu, thay vi ghim ngay:
        #   · ca truc phai la cua hom nay (tinh tien to tu ngay hien tai);
        #   · va cap tai xe / xe phai dung.
        hom_nay = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
        shifts = db.query(models.DriverShiftAssignment).filter(
            models.DriverShiftAssignment.id.like("DEMO-SHIFT-%s-%%" % hom_nay)
        ).order_by(models.DriverShiftAssignment.id).all()
        assert [(row.driver_id, row.vehicle_id) for row in shifts] == [
            ("DEMO-DRV-001", "DEMO-51C-268.89"),
            ("DEMO-DRV-002", "DEMO-61H-112.34"),
            ("DEMO-DRV-003", "DEMO-61H-112.34"),
        ], "ca truc cua chuoi nghiep vu phai mang ngay hom nay"
        co_driver = db.get(models.Driver, "DEMO-DRV-003")
        assert co_driver.role == "Phụ xe"
        assert "Rảnh" in co_driver.status

        waiting = db.get(models.DeliveryOrder, first["waiting"]["delivery_order_id"])
        tracking = db.get(models.DeliveryOrder, first["tracking"]["delivery_order_id"])
        completed = db.get(models.DeliveryOrder, first["completed"]["delivery_order_id"])

        assert waiting.canonical_status == "pending"
        assert waiting.vehicle_id is None
        assert db.query(models.TripDeliveryOrder).filter_by(do_id=waiting.id).count() == 0

        assert tracking.canonical_status == "in_transit"
        tracking_trip = db.get(models.TransportTrip, first["tracking"]["trip_id"])
        assert tracking_trip.status == "in_transit"
        assert tracking.vehicle_id == "DEMO-51C-268.89"
        assert tracking.driver_id == "DEMO-DRV-001"
        gps = db.get(models.VehicleTracking, tracking.id)
        assert gps.speed_kmh == 48
        assert gps.remaining_distance_km == 18.6
        events = db.query(models.TransportEvent).filter_by(
            freight_order_id=first["tracking"]["freight_order_id"]
        ).order_by(models.TransportEvent.event_time).all()
        assert [event.event_type for event in events] == ["check_in", "pickup", "departure"]

        assert completed.canonical_status == "delivered"
        completed_trip = db.get(models.TransportTrip, first["completed"]["trip_id"])
        assert completed_trip.status == "completed"
        completed_assignment = db.query(models.ResourceAssignment).filter_by(
            trip_id=completed_trip.id
        ).one()
        assert completed_assignment.driver_id == "DEMO-DRV-002"
        assert completed_assignment.co_driver_id == "DEMO-DRV-003"
        assert completed_assignment.status == "completed"
        closeout = db.query(models.DeliveryOrderCloseout).filter_by(do_id=completed.id).one()
        assert closeout.base_selling_price_snapshot == Decimal("4200000")
        assert closeout.surcharge_total == Decimal("470000")
        assert closeout.final_selling_price == Decimal("4670000")
        adjustments = db.query(models.DeliveryOrderChargeAdjustment).filter_by(
            closeout_id=closeout.id
        ).order_by(models.DeliveryOrderChargeAdjustment.line_no).all()
        assert [(row.name, row.increase_amount) for row in adjustments] == [
            ("Phí chờ bốc dỡ", Decimal("350000")),
            ("Phí cầu đường bổ sung", Decimal("120000")),
        ]
        pod = db.query(models.DeliveryPODRecord).filter_by(do_id=completed.id).one()
        assert pod.receiver_name == "Nguyễn Văn An"
        assert pod.receiver_phone == "0908123456"
        assert pod.delivery_result == "delivered_full"
        documents = db.query(models.DeliveryPODDocument).filter_by(pod_record_id=pod.id).all()
        assert {document.file_name for document in documents} == {
            "POD-DEMO-DO-2026-003.pdf",
            "signature-DEMO-DO-2026-003.png",
        }
        pod_document = next(document for document in documents if document.mime_type == "application/pdf")
        assert pod_document.content.startswith(b"%PDF")

        cost = db.query(models.FreightActualCost).filter_by(
            trip_id=completed_trip.id, is_active=True
        ).one()
        assert cost.total_amount == Decimal("2380000")
        assert [item.description for item in cost.items] == [
            "Nhiên liệu thực tế",
            "Phí cầu đường thực tế",
            "Phụ cấp tài xế",
        ]


def test_demo_seed_reset_removes_only_seeded_workflow_records(app_client):
    _, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    seed_service = importlib.import_module("services.demo_seed_service")

    with database.SessionLocal() as db:
        seed_service.seed_demo(db, reset=True, verify=True)
        db.add(models.Customer(id="USER-CUSTOMER", name="Dữ liệu người dùng"))
        db.commit()

        seed_service.seed_demo(db, reset=True, verify=True)

        assert db.get(models.Customer, "USER-CUSTOMER") is not None
        # Ý của phép kiểm này là "nạp lại KHÔNG nhân đôi", nên số phải buộc vào
        # bảng khai tình huống chứ không phải một con số cứng. Trước đây nó ghi
        # thẳng 3, nên thêm một tình huống mới là bài đỏ ngay — mà đỏ vì lý do
        # chẳng liên quan gì tới điều nó muốn giữ.
        mong = len(seed_service.DEMO_SCENARIOS)
        assert mong >= 3, "bảng khai tình huống bị hụt"
        assert db.query(models.DeliveryOrder).filter(
            models.DeliveryOrder.id.like("DEMO-DO-2026-%")
        ).count() == mong
