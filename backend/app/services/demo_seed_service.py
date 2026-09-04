import datetime as dt
import hashlib
import json
from decimal import Decimal

from models import (
    AccountingPeriod,
    ARInvoice,
    AuditLog,
    Carrier,
    CostFormula,
    Currency,
    CurrencyDefinition,
    Customer,
    DeliveryOrder,
    DeliveryOrderChargeAdjustment,
    DeliveryOrderCloseout,
    DeliveryOrderDetail,
    DeliveryPODDocument,
    DeliveryPODRecord,
    Driver,
    DriverQualification,
    DriverShiftAssignment,
    EPLExpenseVoucher,
    FinanceControlConfig,
    FreightActualCost,
    FreightChargeItem,
    FreightOrder,
    FreightOrderLegacyLink,
    GLTransaction,
    IdempotencyRecord,
    JournalBatch,
    JournalLine,
    Location,
    Quotation,
    ResourceAssignment,
    Role,
    Route,
    SalesOrder,
    ShipmentCost,
    TransportEvent,
    TransportEventDocument,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
    Vehicle,
    VehicleTracking,
    VehicleType,
    User,
)
from schemas.delivery_completion import DeliveryCompletionRequest
from services.delivery_completion_service import complete_delivery


DEMO_SCENARIOS = {
    "waiting": {
        "quotation_id": "DEMO-QT-2026-001",
        "sales_order_id": "DEMO-SO-2026-001",
        "delivery_order_id": "DEMO-DO-2026-001",
    },
    "tracking": {
        "quotation_id": "DEMO-QT-2026-002",
        "sales_order_id": "DEMO-SO-2026-002",
        "delivery_order_id": "DEMO-DO-2026-002",
        "freight_order_id": "DEMO-FO-2026-002",
        "trip_id": "DEMO-TRIP-2026-002",
        "leg_id": "DEMO-LEG-2026-002",
    },
    "completed": {
        "quotation_id": "DEMO-QT-2026-003",
        "sales_order_id": "DEMO-SO-2026-003",
        "delivery_order_id": "DEMO-DO-2026-003",
        "freight_order_id": "DEMO-FO-2026-003",
        "trip_id": "DEMO-TRIP-2026-003",
        "leg_id": "DEMO-LEG-2026-003",
    },
}

DEMO_FINANCE_ROLE_ID = "DEMO-TMS-FINANCE"
DEMO_API_USER_ID = "demo-dispatcher"


def _ensure_demo_api_user(db):
    permissions = [
        "finance_read",
        "finance_creator",
        "finance_approver",
        "finance_poster",
        "finance_payment",
    ]
    db.merge(Role(id=DEMO_FINANCE_ROLE_ID, permissions=json.dumps(permissions)))
    db.merge(User(
        id=DEMO_API_USER_ID,
        username=DEMO_API_USER_ID,
        role_id=DEMO_FINANCE_ROLE_ID,
    ))

CUSTOMER_ID = "DEMO-CUS-SGNFOOD"
ROUTE_ID = "DEMO-RT-VSIP2A-CATLAI"
ORIGIN_ID = "DEMO-LOC-VSIP2A"
DESTINATION_ID = "DEMO-LOC-CATLAI"
ORIGIN = "Kho VSIP II-A, Bình Dương"
DESTINATION = "Cảng Cát Lái, TP. Thủ Đức"


def _utc(year, month, day, hour=0, minute=0):
    return dt.datetime(year, month, day, hour, minute, tzinfo=dt.timezone.utc)


def _money(value):
    return Decimal(str(value))


def _scenario_ids(key):
    return DEMO_SCENARIOS[key]


def _delete_seeded_workflow(db):
    do_ids = [row[0] for row in db.query(DeliveryOrder.id).filter(
        DeliveryOrder.id.like("DEMO-DO-2026-%")
    ).all()]
    trip_ids = [row[0] for row in db.query(TransportTrip.id).filter(
        TransportTrip.id.like("DEMO-TRIP-2026-%")
    ).all()]
    fo_ids = [row[0] for row in db.query(FreightOrder.id).filter(
        FreightOrder.id.like("DEMO-FO-2026-%")
    ).all()]
    so_ids = [row[0] for row in db.query(SalesOrder.id).filter(
        SalesOrder.id.like("DEMO-SO-2026-%")
    ).all()]
    quotation_ids = [row[0] for row in db.query(Quotation.id).filter(
        Quotation.id.like("DEMO-QT-2026-%")
    ).all()]

    pod_ids = [row[0] for row in db.query(DeliveryPODRecord.id).filter(
        DeliveryPODRecord.do_id.in_(do_ids)
    ).all()] if do_ids else []
    closeout_ids = [row[0] for row in db.query(DeliveryOrderCloseout.id).filter(
        DeliveryOrderCloseout.do_id.in_(do_ids)
    ).all()] if do_ids else []
    invoice_ids = [row[0] for row in db.query(ARInvoice.id).filter(
        ARInvoice.do_id.in_(do_ids)
    ).all()] if do_ids else []
    event_ids = [row[0] for row in db.query(TransportEvent.id).filter(
        TransportEvent.freight_order_id.in_(fo_ids)
    ).all()] if fo_ids else []
    cost_ids = [row[0] for row in db.query(FreightActualCost.id).filter(
        FreightActualCost.trip_id.in_(trip_ids)
    ).all()] if trip_ids else []
    batch_ids = [row[0] for row in db.query(JournalBatch.id).filter(
        JournalBatch.invoice_id.in_(invoice_ids)
    ).all()] if invoice_ids else []

    if pod_ids:
        db.query(DeliveryPODDocument).filter(DeliveryPODDocument.pod_record_id.in_(pod_ids)).delete(synchronize_session=False)
    if closeout_ids:
        db.query(DeliveryOrderChargeAdjustment).filter(
            DeliveryOrderChargeAdjustment.closeout_id.in_(closeout_ids)
        ).delete(synchronize_session=False)
    if batch_ids:
        db.query(JournalLine).filter(JournalLine.batch_id.in_(batch_ids)).delete(synchronize_session=False)
    if invoice_ids:
        db.query(GLTransaction).filter(GLTransaction.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        db.query(JournalBatch).filter(JournalBatch.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        db.query(ARInvoice).filter(ARInvoice.id.in_(invoice_ids)).delete(synchronize_session=False)
    if event_ids:
        db.query(TransportEventDocument).filter(TransportEventDocument.event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(TransportEvent).filter(TransportEvent.id.in_(event_ids)).delete(synchronize_session=False)
    if cost_ids:
        db.query(EPLExpenseVoucher).filter(EPLExpenseVoucher.cost_id.in_(cost_ids)).delete(synchronize_session=False)
        db.query(FreightChargeItem).filter(FreightChargeItem.cost_id.in_(cost_ids)).delete(synchronize_session=False)
        db.query(FreightActualCost).filter(FreightActualCost.id.in_(cost_ids)).delete(synchronize_session=False)
    if do_ids:
        db.query(IdempotencyRecord).filter(
            IdempotencyRecord.path.in_([f"/api/delivery-orders/{do_id}/complete-delivery" for do_id in do_ids])
        ).delete(synchronize_session=False)
        db.query(DeliveryPODRecord).filter(DeliveryPODRecord.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(DeliveryOrderCloseout).filter(DeliveryOrderCloseout.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(VehicleTracking).filter(VehicleTracking.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(FreightOrderLegacyLink).filter(FreightOrderLegacyLink.delivery_order_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(ShipmentCost).filter(ShipmentCost.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.record_id.in_(do_ids)).delete(synchronize_session=False)
    if trip_ids:
        db.query(ResourceAssignment).filter(ResourceAssignment.trip_id.in_(trip_ids)).delete(synchronize_session=False)
        db.query(TransportTripLeg).filter(TransportTripLeg.trip_id.in_(trip_ids)).delete(synchronize_session=False)
        db.query(TripDeliveryOrder).filter(TripDeliveryOrder.trip_id.in_(trip_ids)).delete(synchronize_session=False)
        db.query(TransportTrip).filter(TransportTrip.id.in_(trip_ids)).delete(synchronize_session=False)
    if do_ids:
        db.query(DeliveryOrder).filter(DeliveryOrder.id.in_(do_ids)).delete(synchronize_session=False)
    if fo_ids:
        db.query(FreightOrder).filter(FreightOrder.id.in_(fo_ids)).delete(synchronize_session=False)
    if so_ids:
        db.query(DeliveryOrderDetail).filter(DeliveryOrderDetail.so_id.in_(so_ids)).delete(synchronize_session=False)
        db.query(SalesOrder).filter(SalesOrder.id.in_(so_ids)).delete(synchronize_session=False)
    if quotation_ids:
        db.query(Quotation).filter(Quotation.id.in_(quotation_ids)).delete(synchronize_session=False)
    db.flush()


def _merge_master_data(db):
    db.merge(CurrencyDefinition(code="VND", minor_units=0, is_active=True))
    db.merge(Currency(id="VND", exchange_rate=1))
    db.flush()
    db.merge(FinanceControlConfig(
        id="GLOBAL", functional_currency="VND", distance_variance_threshold=_money(10)
    ))
    # Hạch toán AR (và AP, settlement) đòi một kỳ kế toán đang mở bao trùm thời
    # điểm ghi sổ. Bản demo phải có cấu hình tài chính hợp lệ, nếu không luồng
    # lập hóa đơn sẽ dừng ở MISSING_OPEN_ACCOUNTING_PERIOD.
    _year = dt.datetime.now(dt.timezone.utc).year
    db.merge(AccountingPeriod(
        id=f"DEMO-{_year}",
        starts_at=dt.datetime(_year - 1, 1, 1),
        ends_at=dt.datetime(_year + 1, 12, 31, 23, 59, 59),
        status="open",
    ))
    db.merge(Carrier(
        id="DEMO-CARRIER-INTERNAL", name="Đội xe nội bộ EPL", status="active", is_internal=True
    ))
    db.merge(Customer(
        id=CUSTOMER_ID,
        name="Công ty CP Thực Phẩm Sài Gòn Demo",
        type="Account",
        contact_person="Nguyễn Lan Anh",
        phone="02838212026",
        address="KCN VSIP II-A, Tân Uyên, Bình Dương",
    ))
    db.merge(VehicleType(
        id="DEMO-VT-20FT", name="Container 20FT", max_weight=28000,
        volume_capacity_m3=33.2, pallet_capacity=22, fuel_norm=26, base_rate=6250,
        avg_speed_kmh=45,
        maint_cost=750000, dims="6.06m x 2.44m x 2.59m", fuel_type="Diesel",
        notes="Container tiêu chuẩn cho hàng pallet",
    ))
    vehicles = [
        ("DEMO-51C-268.89", "Hyundai", "Đang vận chuyển"),
        ("DEMO-61H-112.34", "Isuzu", "Sẵn sàng"),
    ]
    for vehicle_id, brand, status in vehicles:
        db.merge(Vehicle(
            id=vehicle_id, brand=brand, type="Container 20FT", weight_capacity=28000,
            volume_capacity_m3=33.2, pallet_capacity=22, fuel_norm=26,
            min_speed_kmh=35, avg_speed_kmh=45, max_speed_kmh=80, status=status,
            engine_no=f"ENG-{vehicle_id}", chassis_no=f"CHS-{vehicle_id}",
            maintenance_date="2026-12-15", insurance_date="2027-06-30",
            inspection_date="2026-07-01", inspection_exp="2027-07-01",
            inspection_place="Trung tâm đăng kiểm 61-05D", engine_cap="12.3 L / 410 HP",
            dimensions="Đầu kéo và moóc 20FT",
        ))
    drivers = [
        ("DEMO-DRV-001", "Nguyễn Văn Minh", "Lái xe chính", "DEMO-51C-268.89", "Bận - đang theo xe"),
        ("DEMO-DRV-002", "Lê Hoàng Nam", "Lái xe chính", "DEMO-61H-112.34", "Rảnh - sẵn sàng"),
        ("DEMO-DRV-003", "Trần Quốc Huy", "Phụ xe", "DEMO-61H-112.34", "Rảnh - sẵn sàng"),
    ]
    for driver_id, name, role, vehicle_id, status in drivers:
        db.merge(Driver(
            id=driver_id, name=name, role=role, license_type="Hạng FC" if role == "Lái xe chính" else "Hạng C",
            phone={"DEMO-DRV-001": "0908268899", "DEMO-DRV-002": "0938667771"}.get(driver_id, "0912112340"),
            assigned_vehicle=vehicle_id, shift="Ca ngày (06:00 - 18:00)", status=status,
        ))
        if role == "Lái xe chính":
            db.merge(DriverQualification(
                driver_id=driver_id, license_type="Hạng FC",
                valid_from=dt.datetime(2026, 1, 1), valid_to=dt.datetime(2027, 12, 31),
                status="active", verified_by="demo-seed",
            ))
    db.flush()
    for index, (driver_id, vehicle_id) in enumerate((
        ("DEMO-DRV-001", "DEMO-51C-268.89"),
        ("DEMO-DRV-002", "DEMO-61H-112.34"),
        ("DEMO-DRV-003", "DEMO-61H-112.34"),
    ), start=1):
        db.merge(DriverShiftAssignment(
            id=f"DEMO-SHIFT-20260824-{index:03d}",
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            shift_type="morning",
            shift_start=_utc(2026, 8, 24, 0),
            shift_end=_utc(2026, 8, 24, 8),
            work_location=ORIGIN,
            notes="Ca demo được lưu trong database",
            status="confirmed",
            created_by="demo-seed",
            updated_by="demo-seed",
        ))
    db.merge(Location(
        id=ORIGIN_ID, name=ORIGIN, type="Warehouse",
        address="KCN VSIP II-A, Tân Uyên, Bình Dương", capacity=12000,
    ))
    db.merge(Location(
        id=DESTINATION_ID, name=DESTINATION, type="Port",
        address="Phường Cát Lái, TP. Thủ Đức, TP.HCM", capacity=50000,
    ))
    segments = [
        {"from": ORIGIN, "to": "Vành đai 3", "dist_km": 18.2},
        {"from": "Vành đai 3", "to": DESTINATION, "dist_km": 26.5},
    ]
    db.merge(Route(
        id=ROUTE_ID, name="VSIP II-A → Cảng Cát Lái", distance_km=44.7,
        segments_json=json.dumps(segments, ensure_ascii=False),
    ))
    db.merge(CostFormula(
        id="DEMO-COST-FORMULA-20FT", name="Container 20FT - Tiêu chuẩn",
        formula_expression=json.dumps({
            "currency": "VND",
            "components": {
                "fuel": "6250", "driver": "500000", "toll": "300000",
                "warehouse": "200000", "freight_rate": "1500",
            },
            # Hang tu cua cong thuc dong: moi hang tu khai ro minh nhan theo
            # gi, nen kiem duoc don vi. Dang cu chi co "unit" de xem, khong ai
            # tinh bang no ca.
            "terms": [
                {"key": "fuel", "label": "Chi phí xăng dầu /km", "operator": "add", "factor": "per_km", "rate": 6250, "builtin": True},
                {"key": "driver", "label": "Phụ cấp chuyến tài xế", "operator": "add", "factor": "per_trip", "rate": 500000, "builtin": True},
                {"key": "toll", "label": "Phí cầu đường / BOT", "operator": "add", "factor": "per_trip", "rate": 300000, "builtin": True},
                {"key": "wh", "label": "Phí bãi & lưu kho", "operator": "add", "factor": "per_trip", "rate": 200000, "builtin": True},
                {"key": "rate", "label": "Cước phí vận chuyển /kg", "operator": "add", "factor": "per_kg", "rate": 1500, "builtin": True},
            ],
        }, ensure_ascii=False),
    ))
    db.flush()


def _seed_sales_chain(db, key, pickup, delivery, price):
    ids = _scenario_ids(key)
    db.add(Quotation(
        id=ids["quotation_id"], canonical_status="approved",
        customer_id=CUSTOMER_ID, route_id=ROUTE_ID, origin=ORIGIN, destination=DESTINATION,
        pickup_window_start=pickup.isoformat(),
        pickup_window_end=(pickup + dt.timedelta(hours=1)).isoformat(),
        delivery_window_start=delivery.isoformat(),
        delivery_window_end=(delivery + dt.timedelta(hours=1)).isoformat(),
        weight_kg=8500, pallet_count=18, cargo_type="Hàng tiêu dùng đóng pallet",
        valid_to="2026-09-30", fuel_cost=1162200, driver_cost=650000,
        toll_fee=320000, total_cost=2132200, selling_price=price,
        packaging_spec="Pallet quấn màng PE", volume_m3=24, status="Đã duyệt",
        created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()
    db.add(SalesOrder(
        id=ids["sales_order_id"], quotation_id=ids["quotation_id"],
        canonical_status="confirmed", customer_id=CUSTOMER_ID, route_id=ROUTE_ID,
        origin=ORIGIN, destination=DESTINATION,
        pickup_window_start=pickup.isoformat(),
        pickup_window_end=(pickup + dt.timedelta(hours=1)).isoformat(),
        delivery_window_start=delivery.isoformat(),
        delivery_window_end=(delivery + dt.timedelta(hours=1)).isoformat(),
        weight_kg=8500, pallet_count=18, status="Đã xác nhận", total_amount=_money(price),
        currency_code="VND", exchange_rate_snapshot=_money(1), tax_rate_snapshot=_money(0),
        order_date="2026-08-22", delivery_date=delivery.date().isoformat(),
        payment_terms="30 ngày", sales_rep="Demo Sales",
        packaging_spec="Pallet quấn màng PE", volume_m3=24,
        created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()
    db.add(DeliveryOrderDetail(
        so_id=ids["sales_order_id"], sku="DEMO-FMCG-PALLET",
        description="18 pallet hàng tiêu dùng, nguyên niêm phong", qty=18,
        uom="PALLET", unit_price=price / 18, amount=price, weight_kg=8500,
    ))


def _seed_delivery_order(db, key, pickup, delivery, status="pending", vehicle_id=None, driver_id=None):
    ids = _scenario_ids(key)
    db.add(DeliveryOrder(
        id=ids["delivery_order_id"], canonical_status=status,
        so_id=ids["sales_order_id"], customer_id=CUSTOMER_ID, route_id=ROUTE_ID,
        origin=ORIGIN, destination=DESTINATION,
        pickup_window_start=pickup, pickup_window_end=pickup + dt.timedelta(hours=1),
        delivery_window_start=delivery, delivery_window_end=delivery + dt.timedelta(hours=1),
        weight_kg=8500, pallet_count=18, vehicle_id=vehicle_id, driver_id=driver_id,
        status="Đang vận chuyển" if status == "in_transit" else "Chờ vận chuyển",
        pickup_date=pickup, delivery_date=delivery,
        planned_departure_at=pickup, planned_arrival_at=delivery,
        planned_return_at=delivery + dt.timedelta(hours=2), avg_speed_kmh=45,
        max_speed_kmh=80, return_speed_kmh=45, load_minutes=30,
        unload_minutes=45, return_distance_km=44.7,
        packaging_spec="Pallet quấn màng PE", volume_m3=24,
        created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()


def _seed_trip(db, key, pickup, delivery, vehicle_id):
    ids = _scenario_ids(key)
    db.add(FreightOrder(
        id=ids["freight_order_id"], pickup_location_id=ORIGIN_ID,
        delivery_location_id=DESTINATION_ID, pickup_window_start=pickup.replace(tzinfo=None),
        pickup_window_end=(pickup + dt.timedelta(hours=1)).replace(tzinfo=None),
        delivery_window_start=delivery.replace(tzinfo=None),
        delivery_window_end=(delivery + dt.timedelta(hours=1)).replace(tzinfo=None),
        total_weight_kg=8500, total_volume_m3=24, total_pallet_count=18,
        max_weight_kg=28000, max_volume_m3=33.2, max_pallet_count=22,
        status="departed", created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()
    db.add(TransportTrip(
        id=ids["trip_id"], freight_order_id=ids["freight_order_id"],
        trip_type="one_way", status="in_transit", vehicle_id=vehicle_id,
        driver_id="DEMO-DRV-001" if vehicle_id == "DEMO-51C-268.89" else "DEMO-DRV-002",
        planned_departure_at=pickup, planned_arrival_at=delivery,
        planned_return_at=delivery + dt.timedelta(hours=2), actual_departure_at=pickup,
        created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()
    db.add(TripDeliveryOrder(
        trip_id=ids["trip_id"], do_id=ids["delivery_order_id"],
        allocation_sequence=1, created_by="demo-seed",
    ))
    db.flush()
    db.add(TransportTripLeg(
        id=ids["leg_id"], trip_id=ids["trip_id"], do_id=ids["delivery_order_id"],
        sequence_no=1, leg_type="delivery", origin=ORIGIN, destination=DESTINATION,
        stop_name=DESTINATION, receiver_name="Nguyễn Văn An", receiver_phone="0908123456",
        delivery_note="Giao đủ 18 pallet, kiểm tra niêm phong và ký POD.",
        distance_km=_money(44.7), avg_speed_kmh=_money(45), dwell_minutes=45,
        planned_departure_at=pickup, planned_arrival_at=delivery,
        actual_departure_at=pickup, status="in_transit",
    ))
    db.add(ResourceAssignment(
        freight_order_id=ids["freight_order_id"], trip_id=ids["trip_id"],
        vehicle_id=vehicle_id,
        driver_id="DEMO-DRV-001" if vehicle_id == "DEMO-51C-268.89" else "DEMO-DRV-002",
        co_driver_id="DEMO-DRV-003" if vehicle_id == "DEMO-61H-112.34" else None,
        assignment_start=pickup, assignment_end=delivery + dt.timedelta(hours=2),
        status="active", created_by="demo-seed",
    ))
    db.add(FreightOrderLegacyLink(
        freight_order_id=ids["freight_order_id"], delivery_order_id=ids["delivery_order_id"]
    ))
    db.flush()


def _seed_tracking(db, pickup, delivery):
    ids = _scenario_ids("tracking")
    db.add(VehicleTracking(
        do_id=ids["delivery_order_id"], vehicle_id="DEMO-51C-268.89",
        lat=10.8769, lng=106.7734, speed_kmh=48,
        remaining_distance_km=18.6, eta=delivery.isoformat(), last_update=pickup.replace(tzinfo=None),
    ))
    event_rows = [
        ("check_in", pickup - dt.timedelta(minutes=30), 11.0497, 106.7428, 0, 44.7, "Xe đã vào kho VSIP II-A"),
        ("pickup", pickup - dt.timedelta(minutes=10), 11.0497, 106.7428, 0, 44.7, "Đã nhận đủ 18 pallet"),
        ("departure", pickup, 10.8769, 106.7734, 48, 18.6, "Xe đang di chuyển về Cát Lái"),
    ]
    for index, (event_type, event_time, lat, lng, speed, distance, note) in enumerate(event_rows, 1):
        key = f"demo-event-{ids['freight_order_id']}-{index}"
        db.add(TransportEvent(
            id=f"DEMO-EVENT-2026-002-{index}", freight_order_id=ids["freight_order_id"],
            trip_id=ids["trip_id"], leg_id=ids["leg_id"], event_type=event_type,
            event_time=event_time.replace(tzinfo=None), lat=lat, lng=lng, speed_kmh=speed,
            distance_km=distance, eta=delivery.isoformat(), location_text=note,
            source="device", device_id="GPS-DEMO-26889", note=note,
            idempotency_key=key, payload_hash=hashlib.sha256(key.encode()).hexdigest(),
            recorded_by="demo-seed",
        ))
    db.flush()


def _complete_demo_delivery(db):
    ids = _scenario_ids("completed")
    payload = DeliveryCompletionRequest.model_validate({
        "trip_id": ids["trip_id"],
        "currency_code": "VND",
        "pod_entries": [{
            "leg_id": ids["leg_id"],
            "vehicle_id": "DEMO-61H-112.34",
            "stop_no": 1,
            "location_text": DESTINATION,
            "receiver_name": "Nguyễn Văn An",
            "receiver_phone": "0908123456",
            "delivery_time": "2026-08-21T14:30:00+07:00",
            "delivery_result": "delivered_full",
            "cargo_condition": "Đủ 18 pallet, nguyên niêm phong, không móp vỡ.",
            "file_field": "pod_file_1",
            "signature_file_field": "signature_file_1",
            "note": "Khách hàng đã kiểm đếm và ký nhận.",
        }],
        "charge_adjustments": [
            {
                "name": "Phí chờ bốc dỡ", "original_amount": "0",
                "actual_amount": "350000", "note": "Chờ thêm 90 phút tại cổng cảng.",
            },
            {
                "name": "Phí cầu đường bổ sung", "original_amount": "0",
                "actual_amount": "120000", "note": "Điều chỉnh tuyến theo yêu cầu khách hàng.",
            },
        ],
    })
    pdf = b"%PDF-1.4\n% EPL demo POD\n1 0 obj<</Type/Catalog>>endobj\n%%EOF"
    complete_delivery(
        db,
        ids["delivery_order_id"],
        payload,
        {"pod_file_1": {
            "file_name": "POD-DEMO-DO-2026-003.pdf",
            "mime_type": "application/pdf",
            "content": pdf,
        }, "signature_file_1": {
            "file_name": "signature-DEMO-DO-2026-003.png",
            "mime_type": "image/png",
            "content": b"demo-signature-image-bytes",
        }},
        "demo-complete-do-2026-003",
        "demo-seed",
        f"/api/delivery-orders/{ids['delivery_order_id']}/complete-delivery",
    )
    assignment = db.query(ResourceAssignment).filter_by(trip_id=ids["trip_id"]).one()
    assignment.status = "completed"
    db.flush()


def _seed_actual_cost(db):
    ids = _scenario_ids("completed")
    cost = FreightActualCost(
        id="DEMO-COST-2026-003", freight_order_id=ids["freight_order_id"],
        trip_id=ids["trip_id"], carrier_id="DEMO-CARRIER-INTERNAL",
        currency_code="VND", functional_currency="VND", exchange_rate_snapshot=_money(1),
        exchange_rate_date=dt.date(2026, 8, 21), exchange_rate_source="demo-seed",
        planned_distance_km=_money(44.7), actual_distance_km=_money(47.2),
        distance_status="gps_verified", distance_variance_percent=_money(5.59),
        distance_variance_warning=False, subtotal_amount=_money(2380000),
        tax_amount=_money(0), total_amount=_money(2380000), status="approved",
        is_active=True, created_by="demo-seed", updated_by="demo-seed",
    )
    rows = [
        ("FUEL", "fuel", "Nhiên liệu thực tế", 1200000),
        ("TOLL", "toll", "Phí cầu đường thực tế", 380000),
        ("DRIVER", "driver", "Phụ cấp tài xế", 800000),
    ]
    cost.items = [
        FreightChargeItem(
            id=f"DEMO-COST-2026-003-{code}", charge_type=charge_type,
            description=description, original_amount=_money(amount), actual_amount=_money(amount),
            increase_amount=_money(0), quantity=_money(1), unit_price=_money(amount),
            tax_code="EXEMPT", tax_rate_snapshot=_money(0), tax_mode="exempt",
            net_amount=_money(amount), tax_amount=_money(0), total_amount=_money(amount),
            rounding_adjustment=_money(0), created_by="demo-seed", updated_by="demo-seed",
        )
        for code, charge_type, description, amount in rows
    ]
    db.add(cost)
    db.flush()
    db.add(EPLExpenseVoucher(
        id="DEMO-EXPENSE-VOUCHER-2026-003",
        trip_id=ids["trip_id"],
        cost_id=cost.id,
        do_id=ids["delivery_order_id"],
        voucher_no="T4-0428-08-EPL-DEMO",
        voucher_date=dt.date(2026, 8, 21),
        vehicle_manager="Anh Phê",
        payment_method="cash",
        contract_no="DEMO-SO-2026-003",
        machine_numbers="ENG-DEMO-61H-112.34 / CHS-DEMO-61H-112.34",
        checked_by="Kế toán demo EPL",
        note="Phiếu chi phí mẫu liên kết chuyến đã hoàn thành.",
        created_by="demo-seed",
        updated_by="demo-seed",
    ))
    db.flush()


def _verify(db):
    waiting = db.get(DeliveryOrder, _scenario_ids("waiting")["delivery_order_id"])
    tracking = db.get(DeliveryOrder, _scenario_ids("tracking")["delivery_order_id"])
    completed = db.get(DeliveryOrder, _scenario_ids("completed")["delivery_order_id"])
    assert waiting and waiting.canonical_status == "pending"
    assert tracking and tracking.canonical_status == "in_transit"
    assert completed and completed.canonical_status == "delivered"
    closeout = db.query(DeliveryOrderCloseout).filter_by(do_id=completed.id).one()
    assert closeout.final_selling_price == _money(4670000)
    assert db.query(EPLExpenseVoucher).filter_by(trip_id="DEMO-TRIP-2026-003").one()
    assert db.query(DeliveryPODDocument).join(
        DeliveryPODRecord, DeliveryPODDocument.pod_record_id == DeliveryPODRecord.id
        ).filter(DeliveryPODRecord.do_id == completed.id).count() == 2


def seed_demo(db, reset=False, verify=False):
    _ensure_demo_api_user(db)
    completed_id = _scenario_ids("completed")["delivery_order_id"]
    complete_set = all(db.get(DeliveryOrder, row["delivery_order_id"]) for row in DEMO_SCENARIOS.values())
    if reset or not complete_set:
        _delete_seeded_workflow(db)
        _merge_master_data(db)

        waiting_pickup = _utc(2026, 8, 24, 1)
        waiting_delivery = _utc(2026, 8, 24, 6)
        _seed_sales_chain(db, "waiting", waiting_pickup, waiting_delivery, 3600000)
        _seed_delivery_order(db, "waiting", waiting_pickup, waiting_delivery)

        tracking_pickup = _utc(2026, 8, 22, 1)
        tracking_delivery = _utc(2026, 8, 22, 6)
        _seed_sales_chain(db, "tracking", tracking_pickup, tracking_delivery, 3950000)
        _seed_delivery_order(
            db, "tracking", tracking_pickup, tracking_delivery, "in_transit",
            "DEMO-51C-268.89", "DEMO-DRV-001",
        )
        _seed_trip(db, "tracking", tracking_pickup, tracking_delivery, "DEMO-51C-268.89")
        _seed_tracking(db, tracking_pickup, tracking_delivery)

        completed_pickup = _utc(2026, 8, 21, 1)
        completed_delivery = _utc(2026, 8, 21, 7, 30)
        _seed_sales_chain(db, "completed", completed_pickup, completed_delivery, 4200000)
        _seed_delivery_order(
            db, "completed", completed_pickup, completed_delivery, "in_transit",
            "DEMO-61H-112.34", "DEMO-DRV-002",
        )
        _seed_trip(db, "completed", completed_pickup, completed_delivery, "DEMO-61H-112.34")
        _complete_demo_delivery(db)
        _seed_actual_cost(db)
        db.commit()
    elif db.get(DeliveryOrder, completed_id) is None:
        raise AssertionError("Demo workflow is incomplete")
    else:
        db.commit()

    if verify:
        _verify(db)
    return {key: dict(value) for key, value in DEMO_SCENARIOS.items()}
