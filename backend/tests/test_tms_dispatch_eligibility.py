import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Driver, DriverQualification, DriverShiftAssignment, FreightOrder, Location, ResourceAssignment, Vehicle


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([Location(id="A", name="Kho A"), Location(id="B", name="Kho B")])
    # NẠP DỮ LIỆU GỐC THÀNH MỘT LƯỢT RIÊNG, không gộp vào lượt chốt cuối.
    #
    # `FreightOrder.pickup_location_id` khai `ForeignKey("locations.id")` nhưng
    # KHÔNG khai `relationship()`. SQLAlchemy xếp thứ tự chèn theo RELATIONSHIP
    # chứ không theo cột khoá ngoại trần — nên khi không có relationship, nó
    # không biết `locations` phải đi trước và xếp theo tên bảng: `freight_orders`
    # trước `locations`. PostgreSQL cưỡng chế khoá ngoại nên vỡ ngay, còn SQLite
    # trong dự án tắt `PRAGMA foreign_keys` nên chuyện này ẩn nhiều tháng.
    session.flush()
    session.add(FreightOrder(
        id="FO-DSP-001", pickup_location_id="A", delivery_location_id="B",
        pickup_window_start=dt.datetime(2026, 8, 11, 8), pickup_window_end=dt.datetime(2026, 8, 11, 10),
        delivery_window_start=dt.datetime(2026, 8, 11, 13), delivery_window_end=dt.datetime(2026, 8, 11, 16),
        total_weight_kg=2000, total_volume_m3=10, total_pallet_count=4,
        max_weight_kg=3000, max_volume_m3=20, max_pallet_count=10,
    ))
    session.add(Vehicle(
        id="51C-001", type="Xe tải", status="Sẵn sàng", weight_capacity=3000,
        volume_capacity_m3=20, pallet_capacity=10, inspection_exp="2027-01-01", insurance_date="2027-01-01",
        maintenance_date="2027-01-01",
    ))
    session.add(Driver(id="DRV-001", name="Tài xế Một", status="🟢 Rảnh (Sẵn sàng)", license_type="FC"))
    session.add(DriverQualification(
        driver_id="DRV-001", license_type="FC", valid_from=dt.datetime(2025, 1, 1),
        valid_to=dt.datetime(2027, 1, 1), status="active",
    ))
    session.add(DriverShiftAssignment(
        id="SHIFT-FO-001", driver_id="DRV-001", shift_type="custom",
        availability_kind="work", shift_start=dt.datetime(2026, 8, 11, 7),
        shift_end=dt.datetime(2026, 8, 11, 17), status="confirmed",
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close(); engine.dispose()


@pytest.fixture
def dispatch_service():
    from services import tms_dispatch_service
    return tms_dispatch_service


def book_required_appointments(db, service):
    service.book_appointment(db, {
        "id": "APT-PICK", "freight_order_id": "FO-DSP-001", "appointment_type": "pickup",
        "location_id": "A", "scheduled_start": "2026-08-11T08:00:00", "scheduled_end": "2026-08-11T09:00:00",
    }, "warehouse")
    service.book_appointment(db, {
        "id": "APT-DEL", "freight_order_id": "FO-DSP-001", "appointment_type": "delivery",
        "location_id": "B", "scheduled_start": "2026-08-11T13:00:00", "scheduled_end": "2026-08-11T14:00:00",
    }, "warehouse")


def test_dispatch_requires_both_warehouse_appointments(db, dispatch_service):
    with pytest.raises(Exception) as error:
        dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
            "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
        }, "dispatcher")
    assert getattr(error.value, "code", None) == "WAREHOUSE_APPOINTMENT_REQUIRED"


def test_dispatch_checks_legal_capacity_and_creates_time_assignment(db, dispatch_service):
    book_required_appointments(db, dispatch_service)
    order = dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
        "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
    }, "dispatcher")
    assert order.status == "dispatched"
    assert order.version == 2
    assert order.resource_assignments[0].vehicle_id == "51C-001"


@pytest.mark.parametrize(
    ("order_field", "vehicle_field", "required", "capacity", "message_part"),
    [
        ("total_weight_kg", "weight_capacity", 3_001, 3_000, "3.001/3.000 kg"),
        ("total_volume_m3", "volume_capacity_m3", 21, 20, "21/20 m³"),
        ("total_pallet_count", "pallet_capacity", 11, 10, "11/10 pallet"),
    ],
)
def test_dispatch_rejects_each_capacity_dimension_without_assignment(
    db, dispatch_service, order_field, vehicle_field, required, capacity, message_part
):
    book_required_appointments(db, dispatch_service)
    order = db.get(FreightOrder, "FO-DSP-001")
    vehicle = db.get(Vehicle, "51C-001")
    setattr(order, order_field, required)
    setattr(vehicle, vehicle_field, capacity)
    original_vehicle_status = vehicle.status
    original_driver_status = db.get(Driver, "DRV-001").status
    db.flush()

    with pytest.raises(Exception) as error:
        dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
            "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
        }, "dispatcher")

    assert getattr(error.value, "code", None) == "CAPACITY_EXCEEDED"
    assert message_part in str(error.value.message)
    assert db.query(ResourceAssignment).count() == 0
    assert order.status == "planned"
    assert order.version == 1
    assert vehicle.status == original_vehicle_status
    assert db.get(Driver, "DRV-001").status == original_driver_status


def test_dispatch_rejects_expired_vehicle_and_overlapping_resource(db, dispatch_service):
    book_required_appointments(db, dispatch_service)
    vehicle = db.get(Vehicle, "51C-001")
    vehicle.insurance_date = "2026-08-10"
    with pytest.raises(Exception) as error:
        dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
            "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
        }, "dispatcher")
    assert getattr(error.value, "code", None) == "VEHICLE_LEGAL_EXPIRED"


def test_dispatch_rejects_vehicle_or_driver_time_overlap(db, dispatch_service):
    book_required_appointments(db, dispatch_service)
    db.add(FreightOrder(
        id="FO-OTHER", pickup_location_id="A", delivery_location_id="B",
        pickup_window_start=dt.datetime(2026, 8, 11, 7), pickup_window_end=dt.datetime(2026, 8, 11, 9),
        delivery_window_start=dt.datetime(2026, 8, 11, 12), delivery_window_end=dt.datetime(2026, 8, 11, 15),
        total_weight_kg=1, total_volume_m3=1, total_pallet_count=1,
        max_weight_kg=1, max_volume_m3=1, max_pallet_count=1,
    ))
    db.flush()
    db.add(ResourceAssignment(
        freight_order_id="FO-OTHER", vehicle_id="51C-001", driver_id="DRV-001",
        assignment_start=dt.datetime(2026, 8, 11, 7), assignment_end=dt.datetime(2026, 8, 11, 15),
        status="active",
    ))
    db.flush()
    with pytest.raises(Exception) as error:
        dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
            "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
        }, "dispatcher")
    assert getattr(error.value, "code", None) == "RESOURCE_TIME_OVERLAP"


def test_dispatch_eligibility_api_routes_are_public_and_persist_qualification(app_client):
    client, _, _ = app_client
    assert client.get("/api/tms/warehouse-appointments").status_code == 200
    assert client.get("/api/tms/resource-assignments").status_code == 200
    assert client.post("/api/drivers", json={
        "id": "DRV-API-ELIGIBLE", "name": "Tài xế API", "license_type": "FC",
    }).status_code in (200, 201)
    response = client.post("/api/tms/driver-qualifications", json={
        "driver_id": "DRV-API-ELIGIBLE", "license_type": "FC",
        "valid_from": "2026-01-01T00:00:00", "valid_to": "2027-01-01T00:00:00",
    }, headers={"X-Test-Principal": "admin-demo"})
    assert response.status_code == 200
    assert response.json()["data"]["driver_id"] == "DRV-API-ELIGIBLE"
    qualifications = client.get("/api/tms/driver-qualifications").json()
    assert qualifications[0]["verified_by"] == "admin-demo"


# ---------------------------------------------------------------------------
# CỬA CHẶN BẰNG LÁI — năm trạng thái làm điều phối bị chặn.
#
# VÌ SAO CẦN NHỮNG BÀI NÀY. Cửa chặn bằng lái là cửa chặn DUY NHẤT trong
# `_require_dispatch_eligibility` mà trước đây không có bài kiểm nào, dù nó là
# cửa chặn dễ vướng nhất trong vận hành thật (bằng hết hạn theo thời gian, chứ
# không phải do ai làm sai).
#
# VÀ CHÚNG CÒN MỘT VIỆC THỨ HAI: giữ cho màn "Tài xế & Bằng lái" nói cùng một
# câu với máy chủ. Màn đó (`frontend/js/bang-lai-tai-xe.js`, hàm `ketLuan`) sao
# lại đúng năm điều kiện dưới đây để kết luận ai bị chặn, và có một bài kiểm
# phía giao diện (`frontend/tests/bang-lai-tai-xe.test.js`) chạy CÙNG một bảng
# trường hợp. Sửa điều kiện ở service mà không sửa cả hai chỗ thì một trong hai
# bộ kiểm sẽ đỏ — đó là điều mong muốn, vì nếu hai bên trôi khỏi nhau thì màn
# hình báo "đủ điều kiện" rồi điều phối vẫn chặn, và người dùng mất niềm tin
# vào cả hai.
# ---------------------------------------------------------------------------

def _chan_vi_bang_lai(db, dispatch_service):
    book_required_appointments(db, dispatch_service)
    with pytest.raises(Exception) as error:
        dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
            "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
        }, "dispatcher")
    return getattr(error.value, "code", None)


def test_dispatch_blocked_when_qualification_row_is_missing(db, dispatch_service):
    db.query(DriverQualification).filter(DriverQualification.driver_id == "DRV-001").delete()
    db.flush()
    assert _chan_vi_bang_lai(db, dispatch_service) == "DRIVER_LICENSE_INVALID"


def test_dispatch_blocked_when_qualification_is_not_active(db, dispatch_service):
    db.query(DriverQualification).filter(
        DriverQualification.driver_id == "DRV-001").first().status = "suspended"
    db.flush()
    assert _chan_vi_bang_lai(db, dispatch_service) == "DRIVER_LICENSE_INVALID"


def test_dispatch_blocked_when_qualification_not_yet_effective(db, dispatch_service):
    # Chuyến chạy 11/08/2026, bằng chỉ có hiệu lực từ 01/09/2026.
    q = db.query(DriverQualification).filter(DriverQualification.driver_id == "DRV-001").first()
    q.valid_from = dt.datetime(2026, 9, 1)
    q.valid_to = dt.datetime(2028, 1, 1)
    db.flush()
    assert _chan_vi_bang_lai(db, dispatch_service) == "DRIVER_LICENSE_INVALID"


def test_dispatch_blocked_when_qualification_has_expired(db, dispatch_service):
    q = db.query(DriverQualification).filter(DriverQualification.driver_id == "DRV-001").first()
    q.valid_to = dt.datetime(2026, 8, 10)      # hết hạn một ngày trước chuyến
    db.flush()
    assert _chan_vi_bang_lai(db, dispatch_service) == "DRIVER_LICENSE_INVALID"


def test_dispatch_blocked_when_license_class_differs_from_driver_record(db, dispatch_service):
    # Hai bảng ghi hai hạng khác nhau. Đây là trạng thái NGƯỜI DÙNG KHÔNG TỰ
    # SUY RA ĐƯỢC: cả hai giá trị đều hợp lệ, chỉ có việc chúng không bằng nhau
    # là sai — nên màn "Tài xế & Bằng lái" phải nêu rõ cả hai giá trị, và khi
    # người dùng đổi hạng thì ghi cả hai bảng.
    db.query(DriverQualification).filter(
        DriverQualification.driver_id == "DRV-001").first().license_type = "C"
    db.flush()
    assert db.get(Driver, "DRV-001").license_type == "FC"
    assert _chan_vi_bang_lai(db, dispatch_service) == "DRIVER_LICENSE_INVALID"


def test_dispatch_passes_when_qualification_matches_on_the_trip_date(db, dispatch_service):
    """Mặt còn lại: đúng cả năm điều kiện thì đi được.

    Không có bài này thì năm bài trên vẫn xanh kể cả khi cửa chặn chặn TẤT CẢ.
    """
    book_required_appointments(db, dispatch_service)
    order = dispatch_service.dispatch_freight_order(db, "FO-DSP-001", {
        "vehicle_id": "51C-001", "driver_id": "DRV-001", "expected_version": 1,
    }, "dispatcher")
    assert order.status == "dispatched"
