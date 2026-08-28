from sqlalchemy import func, or_

from models import Vehicle, VehicleType
from services.errors import conflict


DIMENSIONS = (
    ("weight", "weight_kg", "max_weight", "kg"),
    ("volume", "volume_m3", "volume_capacity_m3", "m³"),
    ("pallet", "pallet_count", "pallet_capacity", "pallet"),
)


def evaluate_vehicle_type_capacity(vehicle_type, demand):
    reasons = []
    ratios = []
    for dimension, demand_key, capacity_key, unit in DIMENSIONS:
        required = float(demand.get(demand_key) or 0)
        capacity = float(getattr(vehicle_type, capacity_key, 0) or 0)
        if required <= 0:
            continue
        if capacity <= 0:
            reasons.append({
                "dimension": dimension,
                "code": "CAPACITY_NOT_CONFIGURED",
                "required": required,
                "capacity": capacity,
                "unit": unit,
            })
            continue
        ratios.append(required / capacity)
        if required > capacity:
            reasons.append({
                "dimension": dimension,
                "code": "CAPACITY_EXCEEDED",
                "required": required,
                "capacity": capacity,
                "unit": unit,
            })
    return {
        "fits": not reasons,
        "reasons": reasons,
        "utilization_pct": round(max(ratios, default=0) * 100, 1),
        "fit_score": sum(ratios) / len(ratios) if ratios else 0,
    }


def find_vehicle_type(db, value):
    normalized = str(value or "").strip().lower()
    if not normalized:
        return None
    return db.query(VehicleType).filter(or_(
        func.lower(VehicleType.id) == normalized,
        func.lower(VehicleType.name) == normalized,
    )).first()


def require_quotation_vehicle_capacity(db, data):
    vehicle_type = find_vehicle_type(db, data.get("cargo_type"))
    if not vehicle_type:
        return None
    result = evaluate_vehicle_type_capacity(vehicle_type, data)
    if not result["fits"]:
        details = ", ".join(
            f'{item["required"]:g}/{item["capacity"]:g} {item["unit"]}'
            for item in result["reasons"]
        )
        raise conflict(
            "CAPACITY_EXCEEDED",
            f"Loại xe {vehicle_type.name} không đủ năng lực cho lô hàng ({details}).",
            ["master-data/vehicle-types", "quotations"],
        )
    return vehicle_type


def recommend_vehicle_types(db, demand):
    suitable = []
    unsuitable = []
    vehicles = db.query(Vehicle).all()
    for vehicle_type in db.query(VehicleType).all():
        evaluation = evaluate_vehicle_type_capacity(vehicle_type, demand)
        matching = [
            vehicle for vehicle in vehicles
            if str(vehicle.type or "").strip().lower() in {
                str(vehicle_type.id).lower(), str(vehicle_type.name).lower()
            }
        ]
        ready_vehicles = [vehicle for vehicle in matching if _is_ready_status(vehicle.status)]
        item = {
            "id": vehicle_type.id,
            "name": vehicle_type.name,
            "max_weight": vehicle_type.max_weight or 0,
            "volume_capacity_m3": vehicle_type.volume_capacity_m3 or 0,
            "pallet_capacity": vehicle_type.pallet_capacity or 0,
            "ready_vehicle_count": len(ready_vehicles),
            "ready_vehicle_ids": sorted(vehicle.id for vehicle in ready_vehicles),
            "utilization_pct": evaluation["utilization_pct"],
            "reasons": evaluation["reasons"],
        }
        (suitable if evaluation["fits"] else unsuitable).append((evaluation["fit_score"], item))
    suitable.sort(key=lambda pair: (-pair[0], -pair[1]["ready_vehicle_count"], pair[1]["max_weight"]))
    unsuitable.sort(key=lambda pair: pair[1]["max_weight"])
    return {
        "suitable": [item for _, item in suitable],
        "unsuitable": [item for _, item in unsuitable],
    }


def _is_ready_status(status):
    normalized = str(status or "").strip().lower()
    busy_markers = (
        "busy", "in transit", "đang vận chuyển", "đang thực hiện",
        "bận", "maintenance", "sửa chữa",
    )
    if any(marker in normalized for marker in busy_markers):
        return False
    return normalized in {"available", "ready"} or "sẵn sàng" in normalized or "rảnh" in normalized
