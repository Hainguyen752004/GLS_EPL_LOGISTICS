from services.errors import conflict


def _number(value):
    return float(value or 0)


def _display(value):
    number = _number(value)
    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")
    return f"{number:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")


def require_vehicle_capacity(
    vehicle,
    *,
    weight_kg=0,
    volume_m3=0,
    pallet_count=0,
    subject="Hàng hóa",
):
    checks = (
        ("tải trọng", weight_kg, vehicle.weight_capacity, "kg"),
        ("thể tích", volume_m3, vehicle.volume_capacity_m3, "m³"),
        ("pallet", pallet_count, vehicle.pallet_capacity, "pallet"),
    )
    exceeded = [
        f"{label} {_display(required)}/{_display(capacity)} {unit}"
        for label, required, capacity, unit in checks
        if _number(required) > _number(capacity)
    ]
    if exceeded:
        raise conflict(
            "CAPACITY_EXCEEDED",
            f"{subject} vượt năng lực xe {vehicle.id}: {'; '.join(exceeded)}.",
            ["master-data/vehicles"],
        )
