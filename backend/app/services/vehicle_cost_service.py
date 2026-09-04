"""Giá thành hai tầng: công thức theo loại xe, ghi đè theo từng chiếc.

Công thức thuộc về **loại xe**. Từng chiếc xe chỉ ghi đè vài con số khi thực tế
khác đi — xe cũ tốn dầu hơn, xe trả góp gánh thêm khấu hao, xe ở bãi xa chịu phí
điều động khác.

Cố ý không cho mỗi chiếc một công thức riêng: đội xe khoảng 500 chiếc, nên đó là
500 công thức phải bảo trì. Đổi giá dầu phải sửa 500 chỗ, và rất dễ có xe bị bỏ
sót rồi tính sai giá mà không ai biết.
"""
import datetime as dt
import uuid
from decimal import Decimal, InvalidOperation

from models import CostFormula, Vehicle, VehicleCostOverride
from routes.shared import serialize_cost_formula
from services.errors import DomainError

# Các cấu phần chi phí ghi đè được. Khớp với các ô trên màn Công thức giá thành.
COMPONENTS = {
    "fuel": "Chi phí xăng dầu / 1 km",
    "driver": "Phụ cấp chuyến tài xế",
    "toll": "Phí cầu đường / trạm BOT",
    "wh": "Phí bãi & lưu kho",
    "rate": "Cước phí vận chuyển / 1 kg hàng",
}


def _decimal(value, field):
    if value in (None, ""):
        return Decimal(0)
    if isinstance(value, bool):
        raise DomainError("OVERRIDE_VALUE_INVALID", f"{field} không hợp lệ.", 422)
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("OVERRIDE_VALUE_INVALID", f"{field} không hợp lệ.", 422) from None
    if not result.is_finite() or result < 0:
        raise DomainError("OVERRIDE_VALUE_INVALID", f"{field} phải là số không âm.", 422)
    if result.adjusted() + 1 > 18:
        raise DomainError("OVERRIDE_VALUE_TOO_LARGE", f"{field} vượt quá Numeric(24,6).", 422)
    return result


def list_overrides(db, vehicle_id):
    rows = (
        db.query(VehicleCostOverride)
        .filter(VehicleCostOverride.vehicle_id == vehicle_id)
        .order_by(VehicleCostOverride.component)
        .all()
    )
    return [
        {
            "component": row.component,
            "label": COMPONENTS.get(row.component, row.component),
            "value": float(row.value or 0),
            "note": row.note or "",
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "updated_by": row.updated_by or "",
        }
        for row in rows
    ]


def replace_overrides(db, vehicle_id, rows, actor="system"):
    """Ghi lại toàn bộ phần ghi đè của một xe.

    Gửi mảng rỗng nghĩa là "xe này quay về kế thừa hoàn toàn từ loại xe" — và
    lúc đó bảng không còn dòng nào cho xe đó, đúng ý đồ: chỉ lưu phần chênh lệch.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise DomainError("VEHICLE_NOT_FOUND", f"Không tìm thấy xe {vehicle_id}.", 404)
    if rows is None:
        return list_overrides(db, vehicle_id)
    if not isinstance(rows, list):
        raise DomainError("OVERRIDES_INVALID", "Danh sách ghi đè phải là một mảng.", 422)

    db.query(VehicleCostOverride).filter(
        VehicleCostOverride.vehicle_id == vehicle_id
    ).delete(synchronize_session=False)

    seen = set()
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    for row in rows:
        if not isinstance(row, dict):
            raise DomainError("OVERRIDES_INVALID", "Mỗi dòng ghi đè phải là một đối tượng.", 422)
        component = str(row.get("component") or "").strip()
        if component not in COMPONENTS:
            raise DomainError(
                "OVERRIDE_COMPONENT_INVALID",
                f"Cấu phần chi phí '{component}' không hợp lệ.",
                422,
            )
        if component in seen:
            raise DomainError(
                "OVERRIDE_COMPONENT_DUPLICATE",
                f"Cấu phần '{COMPONENTS[component]}' bị ghi đè hai lần.",
                422,
            )
        seen.add(component)
        db.add(VehicleCostOverride(
            id=str(uuid.uuid4()),
            vehicle_id=vehicle_id,
            component=component,
            value=_decimal(row.get("value"), COMPONENTS[component]),
            note=str(row.get("note") or "").strip()[:500] or None,
            updated_at=now,
            updated_by=str(actor)[:64],
        ))
    db.flush()
    return list_overrides(db, vehicle_id)


def effective_cost(db, vehicle_id):
    """Giá thành THỰC TẾ của một chiếc xe: công thức loại xe + phần ghi đè.

    Trả về cả `inherited` lẫn `overridden` cho từng cấu phần, để giao diện nói
    rõ con số nào là kế thừa và con số nào bị đổi — thay vì hiện một dãy số mà
    không ai biết nó từ đâu ra.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise DomainError("VEHICLE_NOT_FOUND", f"Không tìm thấy xe {vehicle_id}.", 404)

    # Cong thuc duoc luu duoi dang JSON trong formula_expression, va gan voi
    # loai xe qua khoa vehicle_type_id ben trong JSON do — khong phai mot cot
    # rieng. Duyet qua tung ban ghi thay vi loc bang SQL vi ly do do.
    formula = None
    if vehicle.type:
        for row in db.query(CostFormula).order_by(CostFormula.id).all():
            payload = serialize_cost_formula(row)
            if str(payload.get("vehicle_type_id") or "") == str(vehicle.type):
                formula = payload
                break

    components_map = (formula or {}).get("components") or {}

    def _base(key):
        raw = components_map.get(key)
        if isinstance(raw, dict):
            raw = raw.get("value")
        try:
            return float(str(raw).replace(",", "")) if raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    base = {key: _base(key) for key in COMPONENTS}
    overrides = {row["component"]: row for row in list_overrides(db, vehicle_id)}

    components = []
    for key, label in COMPONENTS.items():
        override = overrides.get(key)
        components.append({
            "component": key,
            "label": label,
            "inherited": base[key],
            "value": override["value"] if override else base[key],
            "is_overridden": bool(override),
            "note": override["note"] if override else "",
        })
    return {
        "vehicle_id": vehicle.id,
        "vehicle_type": vehicle.type or "",
        "has_type_formula": formula is not None,
        "type_formula_id": (formula or {}).get("id"),
        "override_count": len(overrides),
        "components": components,
    }
