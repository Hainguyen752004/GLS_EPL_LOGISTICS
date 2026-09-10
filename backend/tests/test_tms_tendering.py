import datetime as dt
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Carrier, Customer, FreightOrder, Location
from conftest import ket_noi_du_lieu


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Customer(id="CUS-TENDER", name="Khách hàng Tender"))
    session.add_all([Location(id="A", name="Kho A"), Location(id="B", name="Kho B")])
    # Dữ liệu gốc vào TRƯỚC: `FreightOrder.pickup_location_id` khai `ForeignKey`
    # mà không khai `relationship()`, nên SQLAlchemy không có căn cứ nào để xếp
    # `locations` đi trước và nó xếp theo tên bảng — `freight_orders` trước.
    session.flush()
    session.add(FreightOrder(
        id="FO-TENDER-001", pickup_location_id="A", delivery_location_id="B",
        pickup_window_start=dt.datetime(2026, 8, 11, 8), pickup_window_end=dt.datetime(2026, 8, 11, 10),
        delivery_window_start=dt.datetime(2026, 8, 11, 13), delivery_window_end=dt.datetime(2026, 8, 11, 16),
        total_weight_kg=2000, total_volume_m3=10, total_pallet_count=5,
        max_weight_kg=3000, max_volume_m3=20, max_pallet_count=10,
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close(); engine.dispose()


@pytest.fixture
def tender_service():
    from services import tms_tender_service
    return tms_tender_service


def test_tender_collects_offers_and_awards_exactly_one_carrier(db, tender_service):
    first = tender_service.create_carrier(db, {"id": "CAR-001", "name": "Carrier Một"}, "buyer")
    second = tender_service.create_carrier(db, {"id": "CAR-002", "name": "Carrier Hai"}, "buyer")
    tender = tender_service.publish_tender(db, {
        "id": "TND-001", "freight_order_id": "FO-TENDER-001",
        "response_deadline": "2026-08-10T18:00:00",
    }, "buyer", now=lambda: dt.datetime(2026, 8, 10, 9))
    offer1 = tender_service.submit_offer(db, tender.id, {
        "id": "OFR-001", "carrier_id": first.id, "amount": 2_500_000, "currency_code": "VND"
    }, "carrier-1", now=lambda: dt.datetime(2026, 8, 10, 10))
    offer2 = tender_service.submit_offer(db, tender.id, {
        "id": "OFR-002", "carrier_id": second.id, "amount": 2_300_000, "currency_code": "VND"
    }, "carrier-2", now=lambda: dt.datetime(2026, 8, 10, 10))

    awarded = tender_service.award_offer(db, tender.id, offer2.id, tender.version, "buyer")
    assert awarded.status == "awarded"
    assert awarded.awarded_carrier_id == second.id
    assert offer2.status == "accepted"
    assert offer1.status == "rejected"

    with pytest.raises(Exception) as error:
        tender_service.award_offer(db, tender.id, offer1.id, awarded.version, "buyer")
    assert getattr(error.value, "code", None) == "TENDER_ALREADY_AWARDED"


def test_tender_rejects_late_offer_and_duplicate_carrier_offer(db, tender_service):
    carrier = tender_service.create_carrier(db, {"id": "CAR-001", "name": "Carrier Một"}, "buyer")
    tender = tender_service.publish_tender(db, {
        "id": "TND-001", "freight_order_id": "FO-TENDER-001",
        "response_deadline": "2026-08-10T12:00:00",
    }, "buyer", now=lambda: dt.datetime(2026, 8, 10, 9))
    with pytest.raises(Exception) as error:
        tender_service.submit_offer(db, tender.id, {
            "id": "OFR-LATE", "carrier_id": carrier.id, "amount": 100,
        }, "carrier", now=lambda: dt.datetime(2026, 8, 10, 12, 1))
    assert getattr(error.value, "code", None) == "TENDER_EXPIRED"


def test_tender_api_vertical_slice(app_client):
    client, database_file, _ = app_client
    with ket_noi_du_lieu(database_file) as connection:
        connection.executemany("INSERT INTO locations(id,name,type) VALUES (?,?,?)", [("A", "Kho A", "Warehouse"), ("B", "Kho B", "Warehouse")])
        connection.execute("""INSERT INTO freight_orders(
            id,pickup_location_id,delivery_location_id,pickup_window_start,pickup_window_end,
            delivery_window_start,delivery_window_end,total_weight_kg,total_volume_m3,total_pallet_count,
            max_weight_kg,max_volume_m3,max_pallet_count,status,version,created_at,updated_at,created_by,updated_by
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            "FO-API-001", "A", "B", "2026-08-11 08:00:00", "2026-08-11 10:00:00",
            "2026-08-11 13:00:00", "2026-08-11 16:00:00", 1000, 8, 4, 2000, 20, 10,
            "planned", 1, "2026-08-10 09:00:00", "2026-08-10 09:00:00", "test", "test",
        ))
    headers = {"X-Test-Principal": "buyer"}
    assert client.post("/api/tms/carriers", json={"id": "CAR-API", "name": "Carrier API"}, headers=headers).status_code == 200
    tender = client.post("/api/tms/tenders", json={
        "id": "TND-API", "freight_order_id": "FO-API-001", "response_deadline": "2099-08-10T18:00:00"
    }, headers=headers)
    assert tender.status_code == 200
    offer = client.post("/api/tms/tenders/TND-API/offers", json={
        "id": "OFR-API", "carrier_id": "CAR-API", "amount": 123456, "currency_code": "VND"
    }, headers={"X-Test-Principal": "carrier-api"})
    assert offer.status_code == 200
    award = client.put("/api/tms/tenders/TND-API/award", json={
        "offer_id": "OFR-API", "expected_version": tender.json()["data"]["version"]
    }, headers=headers)
    assert award.status_code == 200
    assert award.json()["data"]["awarded_carrier_id"] == "CAR-API"
