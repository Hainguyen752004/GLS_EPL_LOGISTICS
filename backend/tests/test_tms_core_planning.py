import datetime as dt
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Customer, Location
from conftest import ket_noi_du_lieu


@pytest.fixture
def db_session(may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def tms_service():
    from services import tms_planning_service
    return tms_planning_service


@pytest.fixture
def tms_master_data(db_session):
    db_session.add(Customer(id="CUS-001", name="Khách hàng kiểm thử"))
    db_session.add_all([
        Location(id="LOC-A", name="Kho A", type="Warehouse"),
        Location(id="LOC-B", name="Kho B", type="Warehouse"),
    ])
    db_session.commit()


def demand_payload(**overrides):
    data = {
        "id": "TD-2026-001",
        "customer_id": "CUS-001",
        "pickup_location_id": "LOC-A",
        "delivery_location_id": "LOC-B",
        "pickup_window_start": "2026-08-11T08:00:00",
        "pickup_window_end": "2026-08-11T10:00:00",
        "delivery_window_start": "2026-08-11T13:00:00",
        "delivery_window_end": "2026-08-11T16:00:00",
        "weight_kg": 1000,
        "volume_m3": 8,
        "pallet_count": 4,
    }
    data.update(overrides)
    return data


def test_demand_to_freight_unit_requires_submitted_state(db_session, tms_service, tms_master_data):
    demand = tms_service.create_demand(db_session, demand_payload(), "planner")
    with pytest.raises(Exception) as error:
        tms_service.create_freight_unit_from_demand(db_session, demand.id, "planner")
    assert getattr(error.value, "code", None) == "DEMAND_NOT_SUBMITTED"

    tms_service.submit_demand(db_session, demand.id, demand.version, "planner")
    unit = tms_service.create_freight_unit_from_demand(db_session, demand.id, "planner")
    assert unit.demand_id == demand.id
    assert (unit.weight_kg, unit.volume_m3, unit.pallet_count) == (1000, 8, 4)


def test_consolidation_totals_multiple_units_and_rejects_capacity(db_session, tms_service, tms_master_data):
    units = []
    for index, weight in enumerate((1000, 1500), start=1):
        payload = demand_payload(id=f"TD-2026-00{index}", weight_kg=weight)
        demand = tms_service.create_demand(db_session, payload, "planner")
        tms_service.submit_demand(db_session, demand.id, demand.version, "planner")
        units.append(tms_service.create_freight_unit_from_demand(db_session, demand.id, "planner"))

    with pytest.raises(Exception) as error:
        tms_service.create_freight_order(db_session, {
            "id": "FO-2026-001", "freight_unit_ids": [u.id for u in units],
            "max_weight_kg": 2000, "max_volume_m3": 30, "max_pallet_count": 20,
        }, "planner")
    assert getattr(error.value, "code", None) == "CAPACITY_EXCEEDED"

    order = tms_service.create_freight_order(db_session, {
        "id": "FO-2026-001", "freight_unit_ids": [u.id for u in units],
        "max_weight_kg": 3000, "max_volume_m3": 30, "max_pallet_count": 20,
    }, "planner")
    assert order.total_weight_kg == 2500
    assert len(order.units) == 2


def test_demand_validates_time_windows(db_session, tms_service, tms_master_data):
    with pytest.raises(Exception) as error:
        tms_service.create_demand(db_session, demand_payload(
            pickup_window_start="2026-08-11T10:00:00",
            pickup_window_end="2026-08-11T08:00:00",
        ), "planner")
    assert getattr(error.value, "code", None) == "INVALID_TIME_WINDOW"


def test_tms_api_runs_demand_to_freight_order_vertical_slice(app_client):
    client, database_file, _ = app_client
    with ket_noi_du_lieu(database_file) as connection:
        connection.execute("INSERT INTO customers(id,name) VALUES (?,?)", ("CUS-001", "Khách hàng API"))
        connection.executemany(
            "INSERT INTO locations(id,name,type) VALUES (?,?,?)",
            [("LOC-A", "Kho A", "Warehouse"), ("LOC-B", "Kho B", "Warehouse")],
        )
    headers = {"X-Test-Principal": "planner-api"}
    created = client.post("/api/tms/demands", json=demand_payload(), headers=headers)
    assert created.status_code == 200
    assert created.json()["data"]["status"] == "draft"
    submitted = client.put(
        "/api/tms/demands/TD-2026-001/submit",
        json={"expected_version": created.json()["data"]["version"]}, headers=headers,
    )
    assert submitted.status_code == 200
    unit = client.post("/api/tms/freight-units/from-demand/TD-2026-001", headers=headers)
    assert unit.status_code == 200
    order = client.post("/api/tms/freight-orders", json={
        "id": "FO-2026-001", "freight_unit_ids": [unit.json()["data"]["id"]],
        "max_weight_kg": 2000, "max_volume_m3": 20, "max_pallet_count": 10,
    }, headers=headers)
    assert order.status_code == 200
    assert order.json()["data"]["total_weight_kg"] == 1000
