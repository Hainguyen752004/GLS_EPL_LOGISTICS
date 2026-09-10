import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Driver, FreightOrder, Location, ResourceAssignment, Vehicle
from services import tms_scheduling_service


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Vehicle(id="VEH-01", type="Truck", status="busy"),
        Driver(id="DRV-MAIN", name="Main driver", status="busy"),
        Driver(id="DRV-CO", name="Co-driver", status="busy"),
        Location(id="SC-A", name="Kho A"),
        Location(id="SC-B", name="Kho B"),
    ])
    # Địa điểm vào TRƯỚC — SQLAlchemy xếp thứ tự chèn theo `relationship()`, mà
    # `FreightOrder` chỉ khai cột `ForeignKey` trần, nên thiếu lượt này thì nó
    # xếp `freight_orders` trước `locations`.
    session.flush()
    # LỆNH VẬN CHUYỂN `FO-TRIP-01` PHẢI CÓ THẬT.
    #
    # Bản trước không tạo nó: fixture chỉ dựng một `ResourceAssignment` trỏ vào
    # `freight_order_id="FO-TRIP-01"` — một lệnh không tồn tại. Chạy được trên
    # SQLite vì SQLite trong dự án tắt `PRAGMA foreign_keys`, nhưng
    # `resource_assignments_freight_order_id_fkey` trên PostgreSQL từ chối. Tức
    # cả nhóm bài kiểm về đụng lịch tổ lái đang chốt hành vi trên một trạng thái
    # dữ liệu mà cơ sở dữ liệu thật không cho phép tồn tại.
    session.add(FreightOrder(
        id="FO-TRIP-01", pickup_location_id="SC-A", delivery_location_id="SC-B",
        pickup_window_start=dt.datetime(2026, 8, 24, 8),
        pickup_window_end=dt.datetime(2026, 8, 24, 10),
        delivery_window_start=dt.datetime(2026, 8, 26, 13),
        delivery_window_end=dt.datetime(2026, 8, 26, 17),
        total_weight_kg=1000, total_volume_m3=5, total_pallet_count=2,
        max_weight_kg=3000, max_volume_m3=20, max_pallet_count=10,
        status="dispatched",
    ))
    session.flush()
    session.add(ResourceAssignment(
        freight_order_id="FO-TRIP-01",
        trip_id=None,
        vehicle_id="VEH-01",
        driver_id="DRV-MAIN",
        co_driver_id="DRV-CO",
        assignment_start=dt.datetime(2026, 8, 24, 8),
        assignment_end=dt.datetime(2026, 8, 26, 17),
        status="active",
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize("driver_id", ["DRV-MAIN", "DRV-CO"])
def test_manual_shift_cannot_overlap_active_trip_crew(db, driver_id):
    with pytest.raises(Exception) as error:
        tms_scheduling_service.save_driver_shift(db, {
            "id": f"SHIFT-{driver_id}",
            "driver_id": driver_id,
            "shift_type": "morning",
            "shift_start": "2026-08-25T06:00:00Z",
            "shift_end": "2026-08-25T14:00:00Z",
            "status": "planned",
        })
    assert getattr(error.value, "code", None) == "DRIVER_ACTIVE_TRIP_OVERLAP"


def test_manual_shift_cannot_assign_vehicle_before_trip_returns(db):
    with pytest.raises(Exception) as error:
        tms_scheduling_service.save_driver_shift(db, {
            "id": "SHIFT-VEHICLE-OVERLAP",
            "driver_id": "DRV-CO",
            "vehicle_id": "VEH-01",
            "shift_type": "morning",
            "shift_start": "2026-08-25T06:00:00Z",
            "shift_end": "2026-08-25T14:00:00Z",
            "status": "planned",
        })
    assert getattr(error.value, "code", None) in {"DRIVER_ACTIVE_TRIP_OVERLAP", "VEHICLE_ACTIVE_TRIP_OVERLAP"}


def test_weekly_schedule_creates_real_overnight_shifts(db):
    result = tms_scheduling_service.save_weekly_driver_schedule(db, {
        "driver_id": "DRV-MAIN",
        "weekdays": [0, 2, 4],
        "start_time": "22:00",
        "end_time": "06:00",
        "effective_start": "2026-09-07",
        "effective_end": "2026-09-13",
        "shift_type": "night",
    })

    assert result["created_count"] == 3
    rows = tms_scheduling_service.list_driver_shifts(
        db, "2026-09-07T00:00:00Z", "2026-09-14T00:00:00Z"
    )
    assert [row["shift_start"] for row in rows] == [
        "2026-09-07T22:00:00Z",
        "2026-09-09T22:00:00Z",
        "2026-09-11T22:00:00Z",
    ]
    assert all(row["shift_end"].endswith("06:00:00Z") for row in rows)


def test_weekly_schedule_supports_multiday_work_window(db):
    result = tms_scheduling_service.save_weekly_driver_schedule(db, {
        "driver_id": "DRV-MAIN",
        "weekdays": [0],
        "start_time": "08:00",
        "end_time": "17:00",
        "end_day_offset": 1,
        "effective_start": "2026-09-07",
        "effective_end": "2026-09-07",
        "shift_type": "custom",
    })

    assert result["created_count"] == 1
    assert result["shifts"][0]["shift_start"] == "2026-09-07T08:00:00Z"
    assert result["shifts"][0]["shift_end"] == "2026-09-08T17:00:00Z"


def test_weekly_schedule_converts_browser_local_time_to_utc(db):
    result = tms_scheduling_service.save_weekly_driver_schedule(db, {
        "driver_id": "DRV-MAIN",
        "weekdays": [0],
        "start_time": "06:00",
        "end_time": "14:00",
        "end_day_offset": 0,
        "timezone_offset_minutes": -420,
        "effective_start": "2026-09-07",
        "effective_end": "2026-09-07",
        "shift_type": "morning",
    })

    assert result["shifts"][0]["shift_start"] == "2026-09-06T23:00:00Z"
    assert result["shifts"][0]["shift_end"] == "2026-09-07T07:00:00Z"
