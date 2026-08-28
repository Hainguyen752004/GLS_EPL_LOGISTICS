import datetime as dt
from decimal import Decimal

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from database import get_db
from models import (
    AuditLog,
    DeliveryOrder,
    FreightOrder,
    Location,
    Route,
    ResourceAssignment,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
)
from services.errors import DomainError
from services import tms_trip_service as trip_service
from routes.tms_planning_routes import router as tms_router


NOW = dt.datetime(2026, 8, 13, 8, 0, tzinfo=dt.timezone.utc)


def _route(route_id, name, origin, destination, distance=120):
    import json

    return Route(
        id=route_id,
        name=name,
        distance_km=distance,
        segments_json=json.dumps([{
            "origin": origin,
            "destination": destination,
            "distance_km": distance,
        }]),
    )


def _timed_delivery_order(order_id, route_id):
    return DeliveryOrder(
        id=order_id,
        route_id=route_id,
        origin="Kho A" if route_id.endswith("OUT") else "Điểm B",
        destination="Điểm B" if route_id.endswith("OUT") else "Kho A",
        pickup_window_start=NOW,
        pickup_window_end=NOW + dt.timedelta(hours=1),
        delivery_window_start=NOW + dt.timedelta(hours=4),
        delivery_window_end=NOW + dt.timedelta(hours=8),
        weight_kg=100,
        volume_m3=1,
        pallet_count=1,
    )


def _utc(value):
    return value.replace(tzinfo=dt.timezone.utc) if value.tzinfo is None else value.astimezone(dt.timezone.utc)


def _freight_order(order_id="FO-TRIP-001"):
    return FreightOrder(
        id=order_id,
        pickup_location_id="LOC-A",
        delivery_location_id="LOC-B",
        pickup_window_start=NOW,
        pickup_window_end=NOW + dt.timedelta(hours=1),
        delivery_window_start=NOW + dt.timedelta(hours=4),
        delivery_window_end=NOW + dt.timedelta(hours=8),
        total_weight_kg=1000,
        total_volume_m3=10,
        total_pallet_count=5,
        max_weight_kg=2000,
        max_volume_m3=20,
        max_pallet_count=10,
    )


def test_trip_schema_supports_one_do_in_many_trips_and_many_legs(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-schema.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        Location(id="LOC-A", name="Kho A"),
        Location(id="LOC-B", name="Điểm B"),
        DeliveryOrder(id="DO-TRIP-001"),
        _freight_order(),
    ])
    db.flush()

    trip_out = TransportTrip(
        id="TRIP-OUT-001", freight_order_id="FO-TRIP-001",
        trip_type="one_way", status="draft", version=1,
    )
    trip_return = TransportTrip(
        id="TRIP-RETURN-001", freight_order_id="FO-TRIP-001",
        trip_type="backhaul", status="draft", version=1,
    )
    db.add_all([trip_out, trip_return])
    db.flush()
    db.add_all([
        TripDeliveryOrder(trip_id=trip_out.id, do_id="DO-TRIP-001"),
        TripDeliveryOrder(trip_id=trip_return.id, do_id="DO-TRIP-001"),
        TransportTripLeg(
            id="LEG-OUT-001", trip_id=trip_out.id, do_id="DO-TRIP-001",
            sequence_no=1, leg_type="delivery", origin="Kho A",
            destination="Điểm B", distance_km=120, avg_speed_kmh=40,
            dwell_minutes=30, status="planned",
        ),
        TransportTripLeg(
            id="LEG-RETURN-001", trip_id=trip_return.id, do_id="DO-TRIP-001",
            sequence_no=1, leg_type="backhaul", origin="Điểm B",
            destination="Kho A", distance_km=120, avg_speed_kmh=40,
            dwell_minutes=0, status="planned",
        ),
    ])
    db.commit()

    assert db.query(TripDeliveryOrder).filter_by(do_id="DO-TRIP-001").count() == 2
    assert db.query(TransportTripLeg).count() == 2
    db.close()
    engine.dispose()


def test_trip_models_enforce_types_statuses_positive_version_and_leg_sequence():
    trip_checks = {str(item.sqltext) for item in TransportTrip.__table__.constraints if hasattr(item, "sqltext")}
    leg_checks = {str(item.sqltext) for item in TransportTripLeg.__table__.constraints if hasattr(item, "sqltext")}

    assert any("trip_type IN" in check and "backhaul" in check and "multi_stop" in check for check in trip_checks)
    assert any("status IN" in check and "settled" in check and "cancelled" in check for check in trip_checks)
    assert any("version > 0" in check for check in trip_checks)
    assert any("sequence_no > 0" in check for check in leg_checks)
    assert any("distance_km >= 0" in check and "avg_speed_kmh > 0" in check for check in leg_checks)

    unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in TransportTripLeg.__table__.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("trip_id", "sequence_no") in unique_sets


def test_trip_eta_columns_are_timezone_aware_and_lineage_columns_exist():
    for name in (
        "planned_departure_at", "planned_arrival_at", "planned_return_at",
        "actual_departure_at", "actual_arrival_at", "actual_return_at",
    ):
        assert getattr(TransportTrip, name).property.columns[0].type.timezone is True

    for table_name in (
        "resource_assignments", "transport_events", "delivery_pod_records",
        "freight_actual_costs",
    ):
        columns = {column.name for column in Base.metadata.tables[table_name].columns}
        assert {"trip_id", "leg_id"}.issubset(columns)


def test_create_trip_from_do_persists_return_route_and_calculates_return_eta(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-create-return.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        _route("RT-OUT", "Kho A - Điểm B", "Kho A", "Điểm B"),
        _route("RT-RETURN", "Điểm B - Kho A", "Điểm B", "Kho A"),
        _timed_delivery_order("DO-OUT", "RT-OUT"),
        _timed_delivery_order("DO-RETURN", "RT-RETURN"),
    ])
    db.commit()

    payload = trip_service.create_trip_from_delivery_orders(db, {
        "id": "TRIP-CREATE-RETURN",
        "do_ids": ["DO-OUT"],
        "trip_type": "round_trip",
        "planned_departure_at": NOW,
        "avg_speed_kmh": "60",
        "dwell_minutes": 30,
        "return_purpose": "backhaul",
        "return_route_id": "RT-RETURN",
        "return_do_id": "DO-RETURN",
    }, actor="dispatcher")

    assert [leg["leg_type"] for leg in payload["legs"]] == ["delivery", "backhaul"]
    assert payload["legs"][1]["do_id"] == "DO-RETURN"
    assert payload["legs"][1]["origin"] == "Điểm B"
    assert payload["legs"][1]["destination"] == "Kho A"
    assert payload["planned_return_at"] is not None
    assert payload["return_distance_km"] == "120.000"

    with pytest.raises(DomainError) as error:
        trip_service.create_trip_from_delivery_orders(db, {
            "id": "TRIP-MISSING-RETURN-ROUTE",
            "do_ids": ["DO-OUT"],
            "trip_type": "round_trip",
            "planned_departure_at": NOW,
            "avg_speed_kmh": "60",
            "return_purpose": "empty_return",
        }, actor="dispatcher")
    assert error.value.code == "RETURN_ROUTE_REQUIRED"
    db.close()
    engine.dispose()


def test_trip_scoped_assignment_cost_and_pod_indexes_preserve_legacy_rows():
    expected = {
        "resource_assignments": {
            "uq_legacy_assignment_freight_order",
            "uq_active_assignment_trip",
        },
        "freight_actual_costs": {
            "uq_legacy_active_cost_freight_order",
            "uq_active_cost_trip",
        },
        "delivery_pod_records": {
            "uq_legacy_delivery_pod_vehicle_stop",
            "uq_trip_delivery_pod_vehicle_stop",
        },
    }
    for table_name, names in expected.items():
        assert names.issubset({index.name for index in Base.metadata.tables[table_name].indexes})

    assert ResourceAssignment.__table__.c.freight_order_id.unique is not True


def test_create_round_trip_with_multiple_dos_and_sequential_eta(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-service.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.info["audit_ip"] = "10.0.0.8"
    db.add_all([
        Location(id="LOC-A", name="Kho A"),
        Location(id="LOC-B", name="Điểm B"),
        DeliveryOrder(id="DO-001"),
        DeliveryOrder(id="DO-002"),
        _freight_order(),
    ])
    db.commit()

    trip = trip_service.create_trip(db, {
        "id": "TRIP-001", "freight_order_id": "FO-TRIP-001",
        "trip_type": "round_trip", "do_ids": ["DO-001", "DO-002"],
    }, actor="dispatcher")
    trip_service.add_leg(db, trip.id, {
        "id": "LEG-001", "do_id": "DO-001", "sequence_no": 1,
        "leg_type": "delivery", "origin": "Kho A", "destination": "Điểm B",
        "distance_km": "120", "avg_speed_kmh": "40", "dwell_minutes": 0,
        "planned_departure_at": NOW.isoformat(),
    }, expected_version=1, actor="dispatcher")
    trip_service.add_leg(db, trip.id, {
        "id": "LEG-002", "do_id": None, "sequence_no": 2,
        "leg_type": "empty_return", "origin": "Điểm B", "destination": "Kho A",
        "distance_km": "120", "avg_speed_kmh": "60", "dwell_minutes": 30,
    }, expected_version=2, actor="dispatcher")
    db.commit()

    db.refresh(trip)
    legs = db.query(TransportTripLeg).filter_by(trip_id=trip.id).order_by(TransportTripLeg.sequence_no).all()
    assert db.query(TripDeliveryOrder).filter_by(trip_id=trip.id).count() == 2
    assert _utc(legs[0].planned_arrival_at) == NOW + dt.timedelta(hours=3)
    assert _utc(legs[1].planned_departure_at) == NOW + dt.timedelta(hours=3, minutes=30)
    assert _utc(legs[1].planned_arrival_at) == NOW + dt.timedelta(hours=5, minutes=30)
    assert _utc(trip.planned_return_at) == NOW + dt.timedelta(hours=5, minutes=30)
    assert db.query(AuditLog).filter(AuditLog.record_id.in_([trip.id, "LEG-001", "LEG-002"])).count() == 3
    assert {row.ip_address for row in db.query(AuditLog).all()} == {"10.0.0.8"}
    db.close()
    engine.dispose()


def test_trip_relationship_summary_supports_many_dos_per_vehicle_and_split_do_return_distance(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-many-many.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        Location(id="LOC-A", name="Kho A"),
        Location(id="LOC-B", name="Điểm B"),
        DeliveryOrder(id="DO-SPLIT-001"),
        DeliveryOrder(id="DO-GROUP-002"),
        _freight_order(),
    ])
    db.commit()

    trip_a = trip_service.create_trip(db, {
        "id": "TRIP-VH-A", "freight_order_id": "FO-TRIP-001",
        "trip_type": "round_trip", "do_ids": ["DO-SPLIT-001", "DO-GROUP-002"],
        "vehicle_id": "VH-A",
    }, actor="planner")
    trip_b = trip_service.create_trip(db, {
        "id": "TRIP-VH-B", "freight_order_id": "FO-TRIP-001",
        "trip_type": "one_way", "do_ids": ["DO-SPLIT-001"],
        "vehicle_id": "VH-B",
    }, actor="planner")
    trip_service.add_leg(db, trip_a.id, {
        "id": "LEG-A-OUT", "do_id": "DO-SPLIT-001", "sequence_no": 1,
        "leg_type": "delivery", "origin": "Kho A", "destination": "Điểm B",
        "distance_km": "80", "avg_speed_kmh": "40", "dwell_minutes": 0,
        "planned_departure_at": NOW.isoformat(),
    }, expected_version=1, actor="planner")
    trip_service.add_leg(db, trip_a.id, {
        "id": "LEG-A-RETURN", "sequence_no": 2,
        "leg_type": "empty_return", "origin": "Điểm B", "destination": "Kho A",
        "distance_km": "80", "avg_speed_kmh": "50", "dwell_minutes": 15,
    }, expected_version=2, actor="planner")
    trip_service.add_leg(db, trip_b.id, {
        "id": "LEG-B-OUT", "do_id": "DO-SPLIT-001", "sequence_no": 1,
        "leg_type": "delivery", "origin": "Kho A", "destination": "Điểm B",
        "distance_km": "30", "avg_speed_kmh": "30", "dwell_minutes": 0,
        "planned_departure_at": NOW.isoformat(),
    }, expected_version=1, actor="planner")
    db.commit()

    payload = trip_service.serialize_trip(db, trip_a)

    assert payload["relationship_summary"]["do_count"] == 2
    assert payload["relationship_summary"]["vehicle_count_for_dos"]["DO-SPLIT-001"] == 2
    assert payload["relationship_summary"]["has_many_dos_on_trip"] is True
    assert payload["relationship_summary"]["has_split_do_across_trips"] is True
    assert Decimal(payload["return_distance_km"]) == Decimal("80")
    assert Decimal(payload["total_distance_km"]) == Decimal("160")
    assert payload["planned_return_at"].startswith("2026-08-13T11:51:00")
    db.close()
    engine.dispose()


def test_backhaul_requires_a_do_but_empty_return_does_not(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-rules.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        Location(id="LOC-A", name="Kho A"), Location(id="LOC-B", name="Điểm B"),
        DeliveryOrder(id="DO-001"), _freight_order(),
    ])
    db.commit()
    trip = trip_service.create_trip(db, {
        "id": "TRIP-002", "freight_order_id": "FO-TRIP-001",
        "trip_type": "backhaul", "do_ids": ["DO-001"],
    }, actor="dispatcher")

    with pytest.raises(DomainError) as caught:
        trip_service.add_leg(db, trip.id, {
            "id": "LEG-BAD", "sequence_no": 1, "leg_type": "backhaul",
            "origin": "B", "destination": "A", "distance_km": 10,
            "avg_speed_kmh": 40, "dwell_minutes": 0,
            "planned_departure_at": NOW.isoformat(),
        }, expected_version=1, actor="dispatcher")
    assert caught.value.code == "BACKHAUL_DO_REQUIRED"
    assert "đơn giao hàng" in caught.value.message.lower()
    db.rollback()
    db.close()
    engine.dispose()


def test_backhaul_can_attach_a_new_return_do_to_an_existing_trip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-new-backhaul-do.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        Location(id="LOC-A", name="Kho A"),
        Location(id="LOC-B", name="Diem B"),
        DeliveryOrder(id="DO-OUTBOUND"),
        DeliveryOrder(id="DO-BACKHAUL"),
        _freight_order(),
    ])
    db.commit()
    trip = trip_service.create_trip(db, {
        "id": "TRIP-BACKHAUL-NEW-DO",
        "freight_order_id": "FO-TRIP-001",
        "trip_type": "backhaul",
        "do_ids": ["DO-OUTBOUND"],
    }, actor="dispatcher")

    trip_service.add_leg(db, trip.id, {
        "id": "LEG-OUTBOUND",
        "do_id": "DO-OUTBOUND",
        "sequence_no": 1,
        "leg_type": "delivery",
        "origin": "Kho A",
        "destination": "Diem B",
        "distance_km": 120,
        "avg_speed_kmh": 40,
        "dwell_minutes": 30,
        "planned_departure_at": NOW.isoformat(),
    }, expected_version=1, actor="dispatcher")
    trip_service.add_leg(db, trip.id, {
        "id": "LEG-BACKHAUL",
        "do_id": "DO-BACKHAUL",
        "sequence_no": 2,
        "leg_type": "backhaul",
        "origin": "Diem B",
        "destination": "Kho A",
        "distance_km": 120,
        "avg_speed_kmh": 40,
        "dwell_minutes": 30,
    }, expected_version=2, actor="dispatcher")
    db.commit()

    payload = trip_service.serialize_trip(db, trip)
    assert payload["delivery_order_ids"] == ["DO-OUTBOUND", "DO-BACKHAUL"]
    assert payload["relationship_summary"]["do_count"] == 2
    assert payload["legs"][-1]["do_id"] == "DO-BACKHAUL"
    assert payload["legs"][-1]["leg_type"] == "backhaul"
    assert payload["planned_return_at"] == payload["legs"][-1]["planned_arrival_at"]
    db.close()
    engine.dispose()


def test_trip_api_requires_auth_and_creates_trip_with_leg_eta(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trip-api.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all([
        Location(id="LOC-A", name="Kho A"), Location(id="LOC-B", name="Diem B"),
        DeliveryOrder(id="DO-API-001"), _freight_order("FO-API-001"),
    ])
    db.commit()
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    unauth_app = FastAPI()
    unauth_app.include_router(tms_router)
    unauth_app.dependency_overrides[get_db] = override_db
    client = TestClient(unauth_app)
    unauth = client.get("/api/tms/trips")
    assert unauth.status_code == 401
    assert unauth.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"

    auth_app = FastAPI()

    @auth_app.middleware("http")
    async def trusted_user(request: Request, call_next):
        request.state.principal = "dispatcher"
        return await call_next(request)

    auth_app.include_router(tms_router)
    auth_app.dependency_overrides[get_db] = override_db
    client = TestClient(auth_app)
    created = client.post(
        "/api/tms/trips",
        json={
            "id": "TRIP-API-001",
            "freight_order_id": "FO-API-001",
            "trip_type": "round_trip",
            "do_ids": ["DO-API-001"],
        },
        headers={"Idempotency-Key": "trip-api-create"},
    )
    assert created.status_code == 200
    assert created.json()["data"]["id"] == "TRIP-API-001"
    assert created.json()["data"]["delivery_order_ids"] == ["DO-API-001"]

    leg = client.post(
        "/api/tms/trips/TRIP-API-001/legs",
        json={
            "id": "LEG-API-001", "do_id": "DO-API-001", "sequence_no": 1,
            "leg_type": "delivery", "origin": "Kho A", "destination": "Diem B",
            "distance_km": "90", "avg_speed_kmh": "45", "dwell_minutes": 15,
            "planned_departure_at": NOW.isoformat(), "expected_version": 1,
        },
        headers={"Idempotency-Key": "trip-api-leg"},
    )
    assert leg.status_code == 200
    assert leg.json()["data"]["planned_arrival_at"].startswith("2026-08-13T10:00:00")

    detail = client.get("/api/tms/trips/TRIP-API-001")
    assert detail.status_code == 200
    assert detail.json()["data"]["legs"][0]["id"] == "LEG-API-001"
    assert detail.json()["data"]["planned_arrival_at"].startswith("2026-08-13T10:00:00")

    engine.dispose()
