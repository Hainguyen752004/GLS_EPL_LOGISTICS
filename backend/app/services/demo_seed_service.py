import datetime as dt
import hashlib
import json
from decimal import Decimal

from models import (
    AuditLog,
    Carrier,
    CostFormula,
    Currency,
    CurrencyDefinition,
    Customer,
    DeliveryOrder,
    DeliveryOrderChargeAdjustment,
    DeliveryOrderCloseout,
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
    IdempotencyRecord,
    Location,
    ParkingEvent,
    ParkingLabel,
    ParkingList,
    ParkingListItem,
    Quotation,
    QuotationItem,
    ResourceAssignment,
    Role,
    Route,
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
from services import demo_operational_seed
from services import demo_master_seed


DEMO_SCENARIOS = {
    "waiting": {
        "quotation_id": "DEMO-QT-2026-001",
        "delivery_order_id": "DEMO-DO-2026-001",
    },
    "tracking": {
        "quotation_id": "DEMO-QT-2026-002",
        "delivery_order_id": "DEMO-DO-2026-002",
        "freight_order_id": "DEMO-FO-2026-002",
        "trip_id": "DEMO-TRIP-2026-002",
        "leg_id": "DEMO-LEG-2026-002",
    },
    "completed": {
        "quotation_id": "DEMO-QT-2026-003",
        "delivery_order_id": "DEMO-DO-2026-003",
        "freight_order_id": "DEMO-FO-2026-003",
        "trip_id": "DEMO-TRIP-2026-003",
        "leg_id": "DEMO-LEG-2026-003",
    },
    # Xe DA DEN NOI nhung CHUA co POD. Day la trang thai quyet dinh cua quy
    # tac quyet toan: dang van chuyen thi CAM sua tien, den noi va ky POD roi
    # moi chot duoc gia cuoi. Khong co tinh huong nay thi man Hoan tat giao
    # hang khong the hien duoc cho chan do.
    "arrived": {
        "quotation_id": "DEMO-QT-2026-004",
        "delivery_order_id": "DEMO-DO-2026-004",
        "freight_order_id": "DEMO-FO-2026-004",
        "trip_id": "DEMO-TRIP-2026-004",
        "leg_id": "DEMO-LEG-2026-004",
    },
    # Mot don CHO VAN CHUYEN tren TUYEN KHAC, KHACH KHAC va LOAI XE KHAC.
    # Ba tinh huong dau deu di chung mot tuyen, nen bo loc tuyen, bo loc loai
    # xe va bo loc khach o cac man deu chi co mot lua chon that.
    "second_route": {
        "quotation_id": "DEMO-QT-2026-005",
        "delivery_order_id": "DEMO-DO-2026-005",
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


def _moc_tuong_doi(gio_lech, phut_lech=0):
    """Mot moc cach GIO HIEN TAI mot khoang, lam tron ve phut.

    VI SAO CAN, ngoai `_moc`. `_moc` neo vao mot GIO TRONG NGAY (vi du 08:00),
    nen mot chuyen "dang chay" co the roi vao qua khu hoac tuong lai tuy luc nap
    du lieu. Hai hau qua do duoc tren man hinh:

      · Chuyen dang chay ma khung gio da qua thi bi dem la QUA HAN, trong khi
        cau chuyen muon ke la "xe dang tren duong".
      · Khung gio qua rong so voi quang duong lam TOC DO tinh ra vo ly: 44,7 km
        trong bay tieng ra 6,4 km/h, va con so do hien ngay tren thap kiem soat.

    Neo tuong doi thi chuyen dang chay LUON dang o giua duong vao luc mo man, va
    toc do suy ra tu khung gio luon nam trong khoang that.
    """
    moc = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=gio_lech, minutes=phut_lech)
    return moc.replace(second=0, microsecond=0)


def _moc(lech_ngay, gio_utc, phut=0):
    """Mot moc thoi gian tinh THEO HOM NAY, khong ghim ngay co dinh.

    VI SAO DOI. Nam tinh huong mau truoc day ghim cung 21-25/08/2026, voi ly do
    ghi trong chu thich la "de bai kiem doi chieu duoc so tien va moc thoi
    gian". Nhung KHONG bai kiem nao doc cac moc do (da soi lai ca thu muc
    `tests/`), con cai gia phai tra thi rat that va do duoc tren man hinh:

      · Man Dieu phoi loc DO theo NGAY DANG CHON, nen don thang 8 khong bao gio
        hien -> cot "DO cho xep" trong tron.
      · Man Theo doi so `last_update` cua GPS voi gio hien tai, nen moc thang 8
        cu 17 ngay -> dai so lieu bao "Mat GPS" cho MOI xe. Dung theo du lieu,
        nhung tren mot thap kiem soat thi do la bao dong gia.
      · Bang chuyen hien "13:00 23/08/2026" cho mot chuyen dang chay.

    Gio: `lech_ngay` la so ngay lech so voi hom nay (am la qua khu), `gio_utc`
    la gio UTC — cong 7 de ra gio Viet Nam, dung quy uoc san co cua bo nap.
    """
    hom_nay = dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=lech_ngay)
    return dt.datetime(hom_nay.year, hom_nay.month, hom_nay.day,
                       gio_utc, phut, tzinfo=dt.timezone.utc)


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
    quotation_ids = [row[0] for row in db.query(Quotation.id).filter(
        Quotation.id.like("DEMO-QT-2026-%")
    ).all()]

    pod_ids = [row[0] for row in db.query(DeliveryPODRecord.id).filter(
        DeliveryPODRecord.do_id.in_(do_ids)
    ).all()] if do_ids else []
    closeout_ids = [row[0] for row in db.query(DeliveryOrderCloseout.id).filter(
        DeliveryOrderCloseout.do_id.in_(do_ids)
    ).all()] if do_ids else []
    event_ids = [row[0] for row in db.query(TransportEvent.id).filter(
        TransportEvent.freight_order_id.in_(fo_ids)
    ).all()] if fo_ids else []
    cost_ids = [row[0] for row in db.query(FreightActualCost.id).filter(
        FreightActualCost.trip_id.in_(trip_ids)
    ).all()] if trip_ids else []

    if pod_ids:
        db.query(DeliveryPODDocument).filter(DeliveryPODDocument.pod_record_id.in_(pod_ids)).delete(synchronize_session=False)
    if closeout_ids:
        db.query(DeliveryOrderChargeAdjustment).filter(
            DeliveryOrderChargeAdjustment.closeout_id.in_(closeout_ids)
        ).delete(synchronize_session=False)
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
        # Packing List phai di TRUOC delivery_orders: `parking_lists.do_id` tro
        # vao chinh bang do. Bo nap tung bao `FOREIGN KEY constraint failed` o
        # lan nap lai thu hai vi thieu doan nay.
        #
        # Xoa TUONG MINH tung bang con thay vi dua vao `ondelete="CASCADE"`:
        # SQLite chi thuc thi cascade khi da bat `PRAGMA foreign_keys`, con bo
        # nap thi phai chay giong nhau tren ca SQLite lan PostgreSQL.
        pl_ids = [row[0] for row in db.query(ParkingList.id).filter(
            ParkingList.do_id.in_(do_ids)
        ).all()]
        if pl_ids:
            db.query(ParkingEvent).filter(
                ParkingEvent.parking_list_id.in_(pl_ids)
            ).delete(synchronize_session=False)
            db.query(ParkingLabel).filter(
                ParkingLabel.parking_list_id.in_(pl_ids)
            ).delete(synchronize_session=False)
            db.query(ParkingListItem).filter(
                ParkingListItem.parking_list_id.in_(pl_ids)
            ).delete(synchronize_session=False)
            db.query(ParkingList).filter(
                ParkingList.id.in_(pl_ids)
            ).delete(synchronize_session=False)
        db.query(DeliveryPODRecord).filter(DeliveryPODRecord.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(DeliveryOrderCloseout).filter(DeliveryOrderCloseout.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(VehicleTracking).filter(VehicleTracking.do_id.in_(do_ids)).delete(synchronize_session=False)
        db.query(FreightOrderLegacyLink).filter(FreightOrderLegacyLink.delivery_order_id.in_(do_ids)).delete(synchronize_session=False)
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
        # Khau hao + bao duong /km, suy tu gia xe va chi phi bao duong thang —
        # cung ham voi cac loai xe o `demo_master_seed`.
        dep_cost_per_km=demo_master_seed.khau_hao_moi_km(1_450_000_000, 750000),
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
            id=f"DEMO-SHIFT-{_moc(0, 0).strftime('%Y%m%d')}-{index:03d}",
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            shift_type="morning",
            # Ca truc cua chuoi nghiep vu cung phai la HOM NAY: man xep ca mo
            # tuan chua ngay hom nay, nen ca thang 8 khong bao gio hien ra.
            shift_start=_moc(0, 0),
            shift_end=_moc(0, 8),
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
        # BOT theo TUYEN. Dung CHUNG ham voi `demo_master_seed` chu khong dat
        # mot con so o day: hai cho tinh doc lap thi hai tuyen dai bang nhau se
        # ra hai muc BOT khac nhau, va khong ai giai thich duoc vi sao.
        bot_fee=demo_master_seed.bot_theo_tuyen(
            [(x["from"], x["to"], x["dist_km"]) for x in segments]),
    ))
    db.merge(CostFormula(
        id="DEMO-COST-FORMULA-20FT", name="Container 20FT - Tiêu chuẩn",
        formula_expression=json.dumps({
            "currency": "VND",
            # Khoa noi voi loai xe. Truoc day cong thuc nay khong khai no, va no
            # chi duoc tra ra nho MOT TRUONG HOP DAC BIET viet cung cho chuoi
            # "20ft" trong phep tra du phong. Khai ro thi phep tra di duong
            # chinh, va cac loai xe khac khong phai co mot truong hop dac biet
            # rieng.
            "vehicle_type_id": "DEMO-VT-20FT",
            "components": {
                "fuel": "6250", "driver": "500000", "toll": "300000",
                "warehouse": "200000", "freight_rate": "1500",
            },
            # Hang tu cua cong thuc dong: moi hang tu khai ro minh nhan theo
            # gi, nen kiem duoc don vi. Dang cu chi co "unit" de xem, khong ai
            # tinh bang no ca.
            #
            # `cost_index` la MA COSTINDEX cua EPL — ma phan loai cua he ke toan
            # ben cong no, do nguoi lam tai chinh dat tren cong thuc va di theo
            # khoan muc toi ho so hoan tat. Nam ma duoi day la ma MAU cho bo
            # demo (CP = chi phi, TH = thu), doi tren man Cong thuc gia thanh la
            # moi noi doi theo — khong co cho nao khac viet cung chung.
            "terms": [
                {"key": "fuel", "label": "Chi phí xăng dầu /km", "operator": "add", "factor": "per_km", "kind": "cost", "rate": 6250, "builtin": True, "cost_index": "EPL-CP-XD"},
                {"key": "driver", "label": "Phụ cấp chuyến tài xế", "operator": "add", "factor": "per_trip", "kind": "cost", "rate": 500000, "builtin": True, "cost_index": "EPL-CP-TX"},
                {"key": "toll", "label": "Phí cầu đường / BOT", "operator": "add", "factor": "per_trip", "kind": "cost", "rate": 300000, "builtin": True, "cost_index": "EPL-CP-BOT"},
                {"key": "wh", "label": "Phí bãi & lưu kho", "operator": "add", "factor": "per_trip", "kind": "cost", "rate": 200000, "builtin": True, "cost_index": "EPL-CP-BAI"},
                {"key": "rate", "label": "Cước phí vận chuyển /kg", "operator": "add", "factor": "per_kg", "kind": "revenue", "rate": 1500, "builtin": True, "cost_index": "EPL-TH-CUOC"},
            ],
        }, ensure_ascii=False),
    ))
    db.flush()


def _seed_sales_chain(db, key, pickup, delivery, price, tuyen=None,
                      khach=None, di=None, den=None, kg=8500, pallet=18, m3=24):
    """Bao gia cuoc -> don hang van chuyen -> dong hang cua don.

    Tuyen, khach va hai diem CO MAC DINH dung bang gia tri truoc day khoa cung,
    nen ba loi goi cu khong doi mot chu nao — va cac bai kiem dang doi chieu so
    tien cua chung van dung y nguyen.
    """
    tuyen = tuyen or ROUTE_ID
    khach = khach or CUSTOMER_ID
    di = di or ORIGIN
    den = den or DESTINATION
    ids = _scenario_ids(key)
    db.add(Quotation(
        id=ids["quotation_id"], canonical_status="approved",
        customer_id=khach, route_id=tuyen, origin=di, destination=den,
        pickup_window_start=pickup.isoformat(),
        pickup_window_end=(pickup + dt.timedelta(hours=1)).isoformat(),
        delivery_window_start=delivery.isoformat(),
        delivery_window_end=(delivery + dt.timedelta(hours=1)).isoformat(),
        weight_kg=kg, pallet_count=pallet, cargo_type="Hàng tiêu dùng đóng pallet",
        # Han hieu luc dat theo NGAY HOM NAY cong ba muoi, khong dat mot ngay
        # co dinh: duong duyet bao gia chan bao gia HET HAN, nen mot ngay co
        # dinh se lam ca bo du lieu mau khong duyet duoc sau ngay do — va khong
        # ai hieu vi sao hom nay khac hom qua.
        valid_to=(_moc_tuong_doi(0).date() + dt.timedelta(days=30)).isoformat(),
        fuel_cost=1162200, driver_cost=650000,
        toll_fee=320000, total_cost=2132200, selling_price=price,
        # DON VI TINH CUOC. Bo du lieu mau la hang container nen bao theo
        # CHUYEN — mot cont mot gia. `unit_price` bang `selling_price` vi don vi
        # la chuyen; hai con so nay chi khac nhau khi bao theo tan/m3/kg.
        price_basis="per_trip", unit_price=price,
        currency_code="VND", fx_rate=1.0,
        payment_terms="30 ngày sau hoá đơn", sales_rep="Trần Anh",
        trips_per_month=24, waiting_surcharge=200000,
        notes_customer="Giá chưa gồm VAT. Phụ phí lưu bãi tính theo thực tế.",
        notes_ops="Cổng B chỉ nhận đến 16:30 — gọi trước 30 phút.",
        packaging_spec="Pallet quấn màng PE", volume_m3=m3, status="Đã duyệt",
        created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()
    # MOT DONG HANG HOA cho moi bao gia. So DO tach ra bang tong so luong o bang
    # nay, nen bao gia khong co dong nao thi khong tach duoc DO nao — va man
    # hinh se hien "0 DO du kien" ma khong noi vi sao.
    db.merge(QuotationItem(
        id="%s-IT01" % ids["quotation_id"], quotation_id=ids["quotation_id"],
        line_no=1, name="Hàng tiêu dùng đóng pallet",
        quantity=max(1, int(pallet / 12) or 1), uom="Pallet",
        note="quấn màng PE, không xếp chồng",
    ))
    db.flush()


def _seed_delivery_order(db, key, pickup, delivery, status="pending",
                         vehicle_id=None, driver_id=None, tuyen=None, khach=None,
                         di=None, den=None, kg=8500, pallet=18, m3=24, km_ve=44.7):
    tuyen = tuyen or ROUTE_ID
    khach = khach or CUSTOMER_ID
    di = di or ORIGIN
    den = den or DESTINATION
    ids = _scenario_ids(key)
    bao_gia = db.get(Quotation, ids["quotation_id"])
    if bao_gia is not None:
        # Co DO nghia la khach DA CHAP NHAN bao gia (DO chi sinh sau buoc do).
        bao_gia.canonical_status = "accepted"
        bao_gia.status = "Đã chấp nhận"
    db.add(DeliveryOrder(
        id=ids["delivery_order_id"], canonical_status=status,
        customer_id=khach, route_id=tuyen,
        # DO sinh tu bao gia: mang `quotation_id` va gia KHOA `unit_price` (khong con SO).
        quotation_id=ids["quotation_id"],
        unit_price=getattr(bao_gia, "unit_price", None),
        origin=di, destination=den,
        pickup_window_start=pickup, pickup_window_end=pickup + dt.timedelta(hours=1),
        delivery_window_start=delivery, delivery_window_end=delivery + dt.timedelta(hours=1),
        weight_kg=kg, pallet_count=pallet, vehicle_id=vehicle_id, driver_id=driver_id,
        # Nhan tieng Viet phai noi dung TUNG trang thai. Truoc day chi co hai
        # nhanh, nen mot DO `arrived` se hien la "Cho van chuyen" — nguoc han
        # su that, va nguoi dieu phoi se tuong xe chua di.
        status={
            "in_transit": "Đang vận chuyển",
            "arrived": "Đã đến nơi",
            "delivered": "Đã hoàn tất",
            "cancelled": "Đã hủy",
        }.get(status, "Chờ vận chuyển"),
        pickup_date=pickup, delivery_date=delivery,
        planned_departure_at=pickup, planned_arrival_at=delivery,
        planned_return_at=delivery + dt.timedelta(hours=2), avg_speed_kmh=45,
        max_speed_kmh=80, return_speed_kmh=45, load_minutes=30,
        unload_minutes=45, return_distance_km=km_ve,
        packaging_spec="Pallet quấn màng PE", volume_m3=m3,
        created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()


def _seed_trip(db, key, pickup, delivery, vehicle_id, ma_di=None, ma_den=None,
               trang_thai_lenh="departed",
               di=None, den=None, driver_id=None):
    """Freight Order + chuyen + chang + phan cong nguon luc cho mot tinh huong.

    Cac tham so diem CO MAC DINH dung bang gia tri truoc day khoa cung, nen hai
    loi goi cu khong doi mot chu nao.
    """
    ma_di = ma_di or ORIGIN_ID
    ma_den = ma_den or DESTINATION_ID
    di = di or ORIGIN
    den = den or DESTINATION
    # Tai xe cua chuyen phai KHOP voi tai xe da gan cho lenh giao hang. Truoc
    # day cho nay chon bang mot dieu kien viet cung theo bien so, nen them mot
    # xe moi la roi vao nhanh mac dinh: don ghi DEMO-DRV-004 ma chuyen ghi
    # DEMO-DRV-002 — do duoc tren PostgreSQL that, va nguoi dieu phoi mo hai
    # man se thay hai ten khac nhau cho cung mot chuyen giao.
    #
    # Mac dinh giu dung dieu kien cu, nen hai loi goi cu khong doi mot chu nao.
    tai_xe = driver_id or (
        "DEMO-DRV-001" if vehicle_id == "DEMO-51C-268.89" else "DEMO-DRV-002")
    ids = _scenario_ids(key)
    db.add(FreightOrder(
        id=ids["freight_order_id"], pickup_location_id=ma_di,
        delivery_location_id=ma_den, pickup_window_start=pickup.replace(tzinfo=None),
        pickup_window_end=(pickup + dt.timedelta(hours=1)).replace(tzinfo=None),
        delivery_window_start=delivery.replace(tzinfo=None),
        delivery_window_end=(delivery + dt.timedelta(hours=1)).replace(tzinfo=None),
        total_weight_kg=8500, total_volume_m3=24, total_pallet_count=18,
        max_weight_kg=28000, max_volume_m3=33.2, max_pallet_count=22,
        # Trang thai lenh phai KHOP voi chuoi moc da ghi.
        #
        # `record_event` doi CA HAI: so moc da ghi, VA trang thai lenh hien tai
        # (`order.status != expected_status` thi tu choi). Ghim "departed" cho moi
        # tinh huong thi tinh huong "da den noi" — khong co su kien nao — roi vao
        # the ket: dem theo su kien thi moc ke tiep la `check_in`, nhung trang
        # thai lenh la `departed` nen may chu tu choi. Chuyen do khong ghi duoc
        # moc nao ca, va nut tren man Theo doi bam vao chi ra loi.
        status=trang_thai_lenh, created_by="demo-seed", updated_by="demo-seed",
    ))
    db.flush()
    db.add(TransportTrip(
        id=ids["trip_id"], freight_order_id=ids["freight_order_id"],
        trip_type="one_way", status="in_transit", vehicle_id=vehicle_id,
        driver_id=tai_xe,
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
        sequence_no=1, leg_type="delivery", origin=di, destination=den,
        stop_name=den, receiver_name="Nguyễn Văn An", receiver_phone="0908123456",
        delivery_note="Giao đủ 18 pallet, kiểm tra niêm phong và ký POD.",
        distance_km=_money(44.7), avg_speed_kmh=_money(45), dwell_minutes=45,
        planned_departure_at=pickup, planned_arrival_at=delivery,
        actual_departure_at=pickup, status="in_transit",
    ))
    db.add(ResourceAssignment(
        freight_order_id=ids["freight_order_id"], trip_id=ids["trip_id"],
        vehicle_id=vehicle_id,
        driver_id=tai_xe,
        co_driver_id="DEMO-DRV-003" if vehicle_id == "DEMO-61H-112.34" else None,
        assignment_start=pickup, assignment_end=delivery + dt.timedelta(hours=2),
        status="active", created_by="demo-seed",
    ))
    db.add(FreightOrderLegacyLink(
        freight_order_id=ids["freight_order_id"], delivery_order_id=ids["delivery_order_id"]
    ))
    db.flush()


def _seed_moc_den_noi(db, pickup, delivery):
    """Bon moc chinh cua tinh huong "da den noi": check_in, lay hang, xuat ben, den.

    VI SAO CAN. `record_event` doi CA HAI dieu kien: so moc da ghi, va trang thai
    lenh van chuyen. Tinh huong nay truoc day khong co su kien nao ma trang thai
    lenh lai la `departed`, nen no roi vao the ket — dem theo su kien thi moc ke
    tiep la `check_in`, con trang thai lenh thi doi mot moc khac, va may chu tu
    choi moi thu. Nut "ghi moc tiep theo" tren man Theo doi bam vao chi ra loi.

    Ghi thang vao bang, khong qua `record_event`: du lieu mau dung LAI mot trang
    thai da dat duoc, con `record_event` la duong cho nguoi dung di tung buoc.

    Toa do lay doc theo tuyen Song Than -> Cat Lai, de bon moc nay ve ra mot vet
    di hop ly tren ban do chu khong dồn vao mot diem.
    """
    ids = _scenario_ids("arrived")
    tong = (delivery - pickup).total_seconds()
    moc = [
        ("check_in", 0.00, 10.8894, 106.7294, 0, "Xe vào bãi Sóng Thần"),
        ("pickup", 0.12, 10.8894, 106.7294, 0, "Đã nhận đủ 20 pallet, niêm phong SL-4471"),
        ("departure", 0.20, 10.8700, 106.7400, 38, "Xe xuất bến, đi Cát Lái"),
        ("arrival", 0.95, 10.7567, 106.7828, 0, "Xe tới cổng B Cảng Cát Lái, chờ ký nhận"),
    ]
    for i, (loai, ti_le, lat, lng, toc_do, ghi_chu) in enumerate(moc, 1):
        luc = pickup + dt.timedelta(seconds=tong * ti_le)
        khoa = "demo-event-%s-%d" % (ids["freight_order_id"], i)
        db.add(TransportEvent(
            id="DEMO-EVENT-2026-004-%d" % i, freight_order_id=ids["freight_order_id"],
            trip_id=ids["trip_id"], leg_id=ids["leg_id"], event_type=loai,
            event_time=luc.replace(tzinfo=None), lat=lat, lng=lng, speed_kmh=toc_do,
            distance_km=31.2, eta=delivery.isoformat(), location_text=ghi_chu,
            source="device", device_id="GPS-DEMO-41209", note=ghi_chu,
            idempotency_key=khoa, payload_hash=hashlib.sha256(khoa.encode()).hexdigest(),
            recorded_by="demo-seed",
        ))
    db.flush()


def _seed_tracking_den_noi(db):
    """Vet GPS cho tinh huong "da den noi, chua ky POD".

    VI SAO CAN. Thap kiem soat dem so xe KHONG co vet GPS va bao do la "mat tin
    hieu". Tinh huong "da den noi" truoc day khong duoc nap vet nao, nen tren
    man Theo doi no luon nam trong o "mat GPS" — mot bao dong gia, va no che
    mat ngoai le THAT cua tinh huong nay, la chua ai ky POD.

    Xe da den noi thi thiet bi van gui toa do, chi la toc do bang 0 va quang
    duong con lai bang 0 — do la hinh dang that cua mot chiec xe dang do o cong
    cang cho ky nhan.
    """
    ids = _scenario_ids("arrived")
    moc_gps = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=6)
    db.add(VehicleTracking(
        do_id=ids["delivery_order_id"], vehicle_id="DEMO-51C-412.09",
        lat=10.7626, lng=106.7906, speed_kmh=0,
        remaining_distance_km=0, eta=moc_gps.isoformat(),
        last_update=moc_gps.replace(tzinfo=None),
    ))
    db.flush()


def _seed_tracking(db, pickup, delivery):
    ids = _scenario_ids("tracking")
    # MOC GPS phai TUOI, khong lay theo gio lay hang.
    #
    # Truoc day `last_update` bang dung gio lay hang. Man Theo doi so moc nay
    # voi gio hien tai va coi cu hon 15 phut la "mat tin hieu" — nen chi can
    # xe chay hon 15 phut la dai so lieu bao mat GPS, va voi du lieu ghim thang
    # 8 thi no bao mat GPS cho MOI xe suot 17 ngay. Do la bao dong gia, va tren
    # mot thap kiem soat thi bao dong gia con te hon khong bao: nguoi truc se
    # goi hang chuc tai xe cho mot su co khong ton tai.
    #
    # Bon phut truoc la dung hinh dang cua mot thiet bi GPS dang gui binh
    # thuong: du moi de khong bi bao mat, du cu de thay ro day la so lieu do
    # duoc chu khong phai gio hien tai.
    moc_gps = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=4)
    db.add(VehicleTracking(
        do_id=ids["delivery_order_id"], vehicle_id="DEMO-51C-268.89",
        lat=10.8769, lng=106.7734, speed_kmh=48,
        remaining_distance_km=18.6, eta=delivery.isoformat(),
        last_update=moc_gps.replace(tzinfo=None),
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


def _complete_demo_delivery(db, giao_luc=None):
    """Ky POD va xuat hoa don cho tinh huong "da xong".

    `giao_luc` phai la MOC THAT cua tinh huong do. Truoc day gio ky POD
    ghim cung "2026-08-21T14:30" trong khi cac moc khac da doi theo hom
    nay — nen ho so hien mot chuyen giao hom nay ma chu ky nhan de thang
    8, va do la thu nguoi xem demo nhin ra ngay.
    """
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
            "delivery_time": (giao_luc or _moc(-2, 7, 30)).isoformat(),
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


def _seed_actual_cost(db, ngay=None):
    ids = _scenario_ids("completed")
    cost = FreightActualCost(
        id="DEMO-COST-2026-003", freight_order_id=ids["freight_order_id"],
        trip_id=ids["trip_id"], carrier_id="DEMO-CARRIER-INTERNAL",
        currency_code="VND", functional_currency="VND", exchange_rate_snapshot=_money(1),
        exchange_rate_date=(ngay or _moc(-2, 1).date()), exchange_rate_source="demo-seed",
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
        voucher_date=(ngay or _moc(-2, 1).date()),
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
    # Hai tinh huong moi: kiem CA trang thai lan tuyen. Chi kiem trang thai thi
    # mot loi truyen sai tuyen se lot, va bo loc tuyen lai chi co mot lua chon.
    den_noi = db.get(DeliveryOrder, _scenario_ids("arrived")["delivery_order_id"])
    assert den_noi and den_noi.canonical_status == "arrived"
    assert den_noi.route_id == "DEMO-RT-SONGTHAN-CATLAI"
    # Chuyen va don phai ghi CUNG mot tai xe. Lech nhau thi hai man hien hai
    # ten khac nhau cho cung mot chuyen giao.
    chuyen_den_noi = db.get(TransportTrip, _scenario_ids("arrived")["trip_id"])
    assert chuyen_den_noi and chuyen_den_noi.driver_id == den_noi.driver_id, (
        "chuyen ghi tai xe %s ma don ghi %s"
        % (chuyen_den_noi.driver_id if chuyen_den_noi else None, den_noi.driver_id))
    tuyen_hai = db.get(DeliveryOrder, _scenario_ids("second_route")["delivery_order_id"])
    assert tuyen_hai and tuyen_hai.canonical_status == "pending"
    assert tuyen_hai.route_id == "DEMO-RT-LONGAN-CAIMEP"
    assert tuyen_hai.customer_id == "DEMO-CUS-NIDEC"

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
        # Danh muc mo rong: them loai xe, xe, tuyen, khach hang va tai xe.
        #
        # Ban demo truoc chi co MOT loai xe, MOT tuyen, HAI xe va MOT khach. Voi
        # bay nhieu thi phan lon man hinh khong the hien duoc dieu chung sinh ra
        # de lam: bang so sanh gia thanh giua cac loai xe chi co mot dong, o chon
        # tuyen chi co mot lua chon, va bo loc bai chi co mot muc. Nguoi xem khong
        # phan biet duoc "man nay chi hien it nhu vay" voi "man nay hong".
        #
        # Nap TRUOC khi dung chuoi nghiep vu: chuoi do tro vao tuyen, loai xe va
        # khach hang.
        demo_master_seed.nap_danh_muc(db)

        # CHO DIEU PHOI: lay hang hai gio nua, giao sau do ba gio. Gio lay phai
        # o TUONG LAI — mot don vua cho dieu phoi vua da tre gio lay thi doc ra
        # nhu he thong bo quen no.
        waiting_pickup = _moc_tuong_doi(2)
        waiting_delivery = _moc_tuong_doi(5)
        _seed_sales_chain(db, "waiting", waiting_pickup, waiting_delivery, 3600000)
        _seed_delivery_order(db, "waiting", waiting_pickup, waiting_delivery)

        # DANG CHAY: lay hang mot gio truoc, du kien giao mot gio nua — nen xe
        # luon dang o KHOANG GIUA tuyen vao luc mo man, va toc do suy ra tu khung
        # gio nay nam trong khoang that cua duong noi thanh.
        tracking_pickup = _moc_tuong_doi(-1)
        tracking_delivery = _moc_tuong_doi(1)
        _seed_sales_chain(db, "tracking", tracking_pickup, tracking_delivery, 3950000)
        _seed_delivery_order(
            db, "tracking", tracking_pickup, tracking_delivery, "in_transit",
            "DEMO-51C-268.89", "DEMO-DRV-001",
        )
        _seed_trip(db, "tracking", tracking_pickup, tracking_delivery, "DEMO-51C-268.89")
        _seed_tracking(db, tracking_pickup, tracking_delivery)

        # DA XONG: hai ngay truoc, da ky POD va da xuat hoa don — day la
        # chuyen duy nhat di het duoc den buoc doi soat.
        completed_pickup = _moc(-2, 1)
        completed_delivery = _moc(-2, 7, 30)
        _seed_sales_chain(db, "completed", completed_pickup, completed_delivery, 4200000)
        _seed_delivery_order(
            db, "completed", completed_pickup, completed_delivery, "in_transit",
            "DEMO-61H-112.34", "DEMO-DRV-002",
        )
        _seed_trip(db, "completed", completed_pickup, completed_delivery, "DEMO-61H-112.34")
        _complete_demo_delivery(db, completed_delivery)
        _seed_actual_cost(db, completed_pickup.date())

        # TINH HUONG 4 — xe DA DEN NOI, chua co POD.
        #
        # Day la trang thai quyet dinh cua quy tac quyet toan: dang van chuyen
        # thi CAM sua tien, den noi va ky POD roi moi chot duoc gia cuoi. Ba
        # tinh huong dau khong co trang thai nay, nen man Hoan tat giao hang
        # khong the hien duoc cho chan do.
        # DA DEN NOI, chua ky POD: lay hang ba gio truoc, han giao con nua gio
        # nua. CO Y chua qua han: ngoai le cua tinh huong nay la CHUA KY POD, va
        # cong them mot canh bao qua han thi hai ngoai le che nhau — nguoi truc
        # khong biet cai nao moi la viec phai xu.
        den_noi_pickup = _moc_tuong_doi(-3)
        den_noi_delivery = _moc_tuong_doi(0, 30)
        _seed_sales_chain(
            db, "arrived", den_noi_pickup, den_noi_delivery, 4350000,
            tuyen="DEMO-RT-SONGTHAN-CATLAI", di="Bãi Sóng Thần",
            den=DESTINATION, kg=12000, pallet=20, m3=28,
        )
        _seed_delivery_order(
            db, "arrived", den_noi_pickup, den_noi_delivery, "arrived",
            "DEMO-51C-412.09", "DEMO-DRV-004",
            tuyen="DEMO-RT-SONGTHAN-CATLAI", di="Bãi Sóng Thần",
            den=DESTINATION, kg=12000, pallet=20, m3=28, km_ve=31.2,
        )
        # Don DA DEN NOI thi PHAI co chuyen: "den noi" nghia la da co xe chay
        # toi. Thieu chuyen thi ho so quyet toan tra ve rong — do duoc: cot gia
        # o man Hoan tat giao hang ghi "0 VND" trong khi don hang la 4.350.000 d,
        # vi ho so do lan theo duong DO -> Freight Order -> chuyen.
        _seed_trip(
            db, "arrived", den_noi_pickup, den_noi_delivery, "DEMO-51C-412.09",
            ma_di="DEMO-LOC-SONGTHAN", ma_den=DESTINATION_ID,
            di="Bãi Sóng Thần", den=DESTINATION,
            # Cung tai xe voi lenh giao hang, khong de nhanh mac dinh chon ho.
            driver_id="DEMO-DRV-004",
            # Trang thai lenh phai la `arrived`, khop voi bon moc ghi ben duoi.
            trang_thai_lenh="arrived",
        )
        _seed_tracking_den_noi(db)
        _seed_moc_den_noi(db, den_noi_pickup, den_noi_delivery)

        # TINH HUONG 5 — cho van chuyen, TUYEN KHAC va KHACH KHAC.
        #
        # Ba tinh huong dau deu di chung mot tuyen va mot khach, nen bo loc
        # tuyen va bo loc khach o cac man deu chi co mot lua chon that — nhin
        # nhu bo loc hong, trong khi no dang noi that.
        # CHO DIEU PHOI, tuyen khac: lay hang bon gio nua. Khung gio dai hon ba
        # tinh huong tren vi tuyen nay 112 km, khong phai 44,7 km — dat cung mot
        # khung cho ca hai thi toc do suy ra cua mot trong hai se vo ly.
        tuyen_hai_pickup = _moc_tuong_doi(4)
        tuyen_hai_delivery = _moc_tuong_doi(8)
        _seed_sales_chain(
            db, "second_route", tuyen_hai_pickup, tuyen_hai_delivery, 7900000,
            tuyen="DEMO-RT-LONGAN-CAIMEP", khach="DEMO-CUS-NIDEC",
            di="Kho Long An", den="Cảng Cái Mép", kg=14200, pallet=24, m3=42,
        )
        _seed_delivery_order(
            db, "second_route", tuyen_hai_pickup, tuyen_hai_delivery,
            tuyen="DEMO-RT-LONGAN-CAIMEP", khach="DEMO-CUS-NIDEC",
            di="Kho Long An", den="Cảng Cái Mép", kg=14200, pallet=24, m3=42,
            km_ve=112.0,
        )
        # Lop VAN HANH: ca truc, bao duong, Packing List — neo theo TUAN HIEN TAI.
        #
        # Chuoi nghiep vu tren neo vao ngay co dinh (thang 8/2026) de bai kiem
        # doi chieu duoc so tien va moc thoi gian. Nhung man xep ca, luoi lich xe
        # va man dieu phoi lai mo TUAN CHUA NGAY HOM NAY, nen du lieu thang 8
        # khong bao gio hien ra o do: do duoc, man xep ca bao "Chua xep 3" va
        # luoi bao duong trong tron. Hai lop tach roi han — lop co dinh de kiem,
        # lop theo tuan de man hinh co gi ma xem.
        demo_operational_seed.nap_lop_van_hanh(
            db, [row["delivery_order_id"] for row in DEMO_SCENARIOS.values()])
        db.commit()
    elif db.get(DeliveryOrder, completed_id) is None:
        raise AssertionError("Demo workflow is incomplete")
    else:
        db.commit()

    if verify:
        _verify(db)
    return {key: dict(value) for key, value in DEMO_SCENARIOS.items()}
