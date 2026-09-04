from services.errors import conflict


def _number(value):
    return float(value or 0)


def _display(value):
    number = _number(value)
    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")
    return f"{number:,.2f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")


def declares_no_cargo(weight_kg=0, volume_m3=0, pallet_count=0):
    """Đơn hàng chưa khai bất kỳ con số hàng hóa nào.

    Con số 0 ở đây gần như luôn nghĩa là "chưa ai điền", chứ không phải "xe chạy
    rỗng" — và khi cả ba đều bằng 0 thì việc kiểm năng lực xe không kiểm được gì
    cả: một container 30 tấn vẫn lọt lên xe tải 2 tấn.

    Hàm này KHÔNG tự chặn, vì chuyến chạy rỗng là có thật trong vận tải. Nó chỉ
    trả lời câu hỏi để chỗ gọi quyết định — xem `require_vehicle_capacity`.
    """
    return not any((_number(weight_kg), _number(volume_m3), _number(pallet_count)))


def undeclared_vehicle_capacity(vehicle):
    """Những năng lực mà chính chiếc xe chưa được khai báo trong Master Data."""
    return [
        label
        for label, value in (
            ("tải trọng", getattr(vehicle, "weight_capacity", 0)),
            ("thể tích", getattr(vehicle, "volume_capacity_m3", 0)),
            ("số pallet", getattr(vehicle, "pallet_capacity", 0)),
        )
        if not _number(value)
    ]


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

    # Xe chưa khai năng lực thì so sánh với 0 sẽ báo "8.500/0 kg" — đúng về số
    # nhưng không nói được phải sửa ở đâu. Tách riêng để câu lỗi chỉ thẳng vào
    # hồ sơ xe.
    undeclared = [
        label
        for label, required, capacity, _unit in checks
        if _number(required) > 0 and not _number(capacity)
    ]
    if undeclared:
        raise conflict(
            "VEHICLE_CAPACITY_UNDECLARED",
            f"Xe {vehicle.id} chưa khai báo {', '.join(undeclared)} trong Master Data, "
            f"nên không kiểm được {subject} có vừa xe hay không.",
            ["master-data/vehicles"],
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
