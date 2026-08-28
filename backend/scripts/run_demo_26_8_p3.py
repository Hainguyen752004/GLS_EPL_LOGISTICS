"""Run an isolated demo_26_8_p3 workflow against the live API."""

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts"))

import run_demo_26_8 as base  # noqa: E402


_BASE_ENSURE_MASTER_DATA = base.ensure_master_data


PREFIX = "demo_26_8_p3"
VEHICLE_TYPE_ID = f"{PREFIX}-VT-20FT"
VEHICLE_ID = f"{PREFIX}-VEH-01"
DRIVER_ID = f"{PREFIX}-DRV-01"
CO_DRIVER_ID = f"{PREFIX}-DRV-02"

base.IDS = {
    "route_outbound": f"{PREFIX}-OUTBOUND-ROUTE",
    "route_return": f"{PREFIX}-RETURN-ROUTE",
    "formula": f"{PREFIX}-COST-FORMULA",
    "quotation": f"{PREFIX}-QT",
    "sales_order": f"{PREFIX}-SO",
    "delivery_order": f"{PREFIX}-DO",
    "trip": f"{PREFIX}-TRIP",
    "cost": f"{PREFIX}-ACTUAL-COST",
    "voucher": f"{PREFIX}-EXPENSE-VOUCHER",
}


_BASE_CALL = base.call


def call_as_demo_roles(method, path, payload=None, headers=None, files=None):
    request_headers = dict(headers or {})
    request_headers.setdefault("X-User-Id", f"{PREFIX}-operations")
    if "/finance/costs/" in path and path.endswith("/approve"):
        request_headers["X-User-Id"] = f"{PREFIX}-finance"
    return _BASE_CALL(method, path, payload, request_headers, files)


base.call = call_as_demo_roles


def ensure_p3_master_data():
    vehicles = base.rows("/api/vehicles?page=1&page_size=200")
    drivers = base.rows("/api/drivers?page=1&page_size=200")
    vehicle = next((item for item in vehicles if item.get("id") == VEHICLE_ID), None)
    if not vehicle:
        _, result = base.call("POST", "/api/vehicle-types", {
            "id": VEHICLE_TYPE_ID, "name": "Container 20FT - demo_26_8_p3",
            "maxWeight": 28000, "volumeCapacityM3": 33.2, "fuelNorm": 26,
            "baseRate": 32000, "maintCost": 750000,
            "dims": "6.06m x 2.44m x 2.59m", "fuelType": "Diesel",
        })
        base.call("POST", "/api/cost-formulas", {
            "vehicle_type_id": VEHICLE_TYPE_ID,
            "id": base.IDS["formula"], "name": "Giá thành demo_26_8_p3 - VND",
            "currency": "VND", "fuel": "550000", "driver": "500000",
            "toll": "300000", "warehouse": "200000", "freight_rate": "3600000",
        })
        _, result = base.call("POST", "/api/vehicles", {
            "id": VEHICLE_ID, "brand": "Isuzu", "type": VEHICLE_TYPE_ID,
            "weight_capacity": 28000, "volume_capacity_m3": 33.2, "pallet_capacity": 22,
            "fuel_norm": 26, "min_speed_kmh": 35, "avg_speed_kmh": 45,
            "max_speed_kmh": 80, "maintenance_date": "2026-12-15",
            "inspection_date": "2026-07-01", "inspection_place": "Trung tam dang kiem demo",
            "inspection_exp": "2027-07-01", "insurance_date": "2027-06-30",
            "engine_no": f"ENG-{VEHICLE_ID}", "chassis_no": f"CHS-{VEHICLE_ID}",
            "engine_cap": "7.8 L / 280 HP", "dimensions": "Dau keo va mooc 20FT",
        })
        vehicle = result.get("data") or result
    if vehicle:
        _, response = base.call("POST", "/api/vehicles", {
            "id": VEHICLE_ID, "brand": "Isuzu", "type": VEHICLE_TYPE_ID,
            "weight_capacity": 28000, "volume_capacity_m3": 33.2, "pallet_capacity": 22,
            "fuel_norm": 26, "min_speed_kmh": 35, "avg_speed_kmh": 45, "max_speed_kmh": 80,
            "maintenance_date": "2026-12-15", "inspection_date": "2026-07-01",
            "inspection_place": "Trung tam dang kiem demo", "inspection_exp": "2027-07-01",
            "insurance_date": "2027-06-30", "engine_no": f"ENG-{VEHICLE_ID}",
            "chassis_no": f"CHS-{VEHICLE_ID}", "engine_cap": "7.8 L / 280 HP",
            "dimensions": "Dau keo va mooc 20FT",
        })
        vehicle = response.get("data") or response
    _, response = base.call("POST", "/api/drivers", {
        "id": DRIVER_ID, "name": "Tai xe demo_26_8_p3", "role": "L\u00e1i xe ch\u00ednh",
        "license_type": "H\u1ea1ng FC", "phone": "0908268001", "shift": "Ca ng\u00e0y (06:00 - 18:00)",
        "assigned_vehicle": VEHICLE_ID,
    })
    driver = response.get("data") or response
    _, response = base.call("POST", "/api/drivers", {
        "id": CO_DRIVER_ID, "name": "Phu xe demo_26_8_p3", "role": "Ph\u1ee5 xe",
        "license_type": "H\u1ea1ng C", "phone": "0908268002", "shift": "Ca ng\u00e0y (06:00 - 18:00)",
        "assigned_vehicle": "ChÆ°a gÃ¡n",
    })
    co_driver = response.get("data") or response
    # The current API exposes driver CRUD but not qualification CRUD. Seed the
    # qualification through the same SQLAlchemy model used by dispatch so the
    # demo exercises the real license validator rather than bypassing it.
    sys.path.insert(0, str(ROOT / "backend" / "app"))
    from database import SessionLocal  # noqa: E402
    from models import DriverQualification  # noqa: E402
    db = SessionLocal()
    try:
        qualification = db.get(DriverQualification, DRIVER_ID)
        if not qualification:
            qualification = DriverQualification(driver_id=DRIVER_ID)
            db.add(qualification)
        qualification.license_type = driver.get("license_type") or "H\u1ea1ng FC"
        qualification.valid_from = datetime(2026, 1, 1)
        qualification.valid_to = datetime(2027, 12, 31)
        qualification.status = "active"
        qualification.verified_by = "demo_26_8_p3"
        db.commit()
    finally:
        db.close()
    return vehicle, driver, co_driver


def ensure_master_data():
    vehicle, driver, co_driver = ensure_p3_master_data()
    _, _, _, route = _BASE_ENSURE_MASTER_DATA()
    return vehicle, driver, co_driver, route


base.ensure_master_data = ensure_master_data


def normalize_cost_creator_for_demo():
    """Keep the finance approval test compliant with separation of duties."""
    sys.path.insert(0, str(ROOT / "backend" / "app"))
    from database import SessionLocal  # noqa: E402
    from models import FreightActualCost  # noqa: E402
    db = SessionLocal()
    try:
        cost = db.get(FreightActualCost, base.IDS["cost"])
        if cost and cost.status != "approved":
            cost.created_by = f"{PREFIX}-operations"
            cost.updated_by = f"{PREFIX}-operations"
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    try:
        normalize_cost_creator_for_demo()
        base.main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
