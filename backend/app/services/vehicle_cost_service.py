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

from models import CostFormula, Vehicle, VehicleType, VehicleCostOverride, AuditLog
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


def _type_formula(db, vehicle):
    if not vehicle.type:
        return None
    vehicle_type = db.query(VehicleType).filter(
        (VehicleType.id == vehicle.type) | (VehicleType.name == vehicle.type)
    ).first()
    type_id = vehicle_type.id if vehicle_type else vehicle.type
    # The catalog folds ascending IDs into one entry per type/currency.
    # Use that same winner for legacy duplicates, not the first matching row.
    for row in db.query(CostFormula).order_by(CostFormula.id.desc()).all():
        payload = serialize_cost_formula(row)
        if (str(payload.get("vehicle_type_id") or "") == str(type_id)
                and str(payload.get("currency") or "VND") == "VND"):
            return payload
    return None


def _component_labels(formula):
    # Legacy fields remain readable while new terms carry their own labels.
    return {**COMPONENTS, **{
        t["key"]: t.get("label") or t["key"]
        for t in (formula or {}).get("terms", []) if t.get("key")
    }}


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

    labels = _component_labels(_type_formula(db, vehicle))
    old_rows = {row['component']: row for row in list_overrides(db, vehicle_id)}
    validated = []
    seen = set()
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    for row in rows:
        if not isinstance(row, dict):
            raise DomainError("OVERRIDES_INVALID", "Mỗi dòng ghi đè phải là một đối tượng.", 422)
        component = str(row.get("component") or "").strip()
        if component not in labels:
            raise DomainError(
                "OVERRIDE_COMPONENT_INVALID",
                f"Cấu phần chi phí '{component}' không hợp lệ.",
                422,
            )
        if component in seen:
            raise DomainError(
                "OVERRIDE_COMPONENT_DUPLICATE",
                f"Cấu phần '{labels[component]}' bị ghi đè hai lần.",
                422,
            )
        seen.add(component)
        validated.append(VehicleCostOverride(
            id=str(uuid.uuid4()),
            vehicle_id=vehicle_id,
            component=component,
            value=_decimal(row.get("value"), labels[component]),
            note=str(row.get("note") or "").strip()[:500] or None,
            updated_at=now,
            updated_by=str(actor)[:64],
        ))
    # Validate the entire replacement before touching persisted differences.
    db.query(VehicleCostOverride).filter(
        VehicleCostOverride.vehicle_id == vehicle_id
    ).delete(synchronize_session=False)
    db.add_all(validated)
    new_rows = {row.component: row for row in validated}
    for key in sorted(set(old_rows) | set(new_rows)):
        old, new = old_rows.get(key), new_rows.get(key)
        if old and new and old['value'] == float(new.value) and old['note'] == (new.note or ''):
            continue
        before = str(old['value']) if old else 'chuẩn'
        after = str(new.value) if new else 'chuẩn'
        reason = f" · {new.note}" if new and new.note else ''
        db.add(AuditLog(user_id=str(actor), table_name='vehicle_cost_overrides',
                        record_id=vehicle_id, timestamp=now,
                        action=f"{labels.get(key, key)}: {before} → {after}{reason}"))
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
    formula = _type_formula(db, vehicle)
    return _resolved_cost(vehicle, formula, list_overrides(db, vehicle_id))


def _resolved_cost(vehicle, formula, override_rows):
    labels = _component_labels(formula)

    components_map = (formula or {}).get("components") or {}

    def _base(key):
        term = next((t for t in (formula or {}).get("terms", [])
                     if t.get("key") == key), None)
        aliases = {"wh": "warehouse", "rate": "freight_rate"}
        raw = term.get("rate") if term else components_map.get(key, components_map.get(aliases.get(key)))
        if isinstance(raw, dict):
            raw = raw.get("value")
        try:
            return float(str(raw).replace(",", "")) if raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    base = {key: _base(key) for key in labels}
    overrides = {row["component"]: row for row in override_rows}

    components = []
    for key, label in labels.items():
        override = overrides.get(key)
        components.append({
            "component": key,
            "label": label,
            "inherited": base[key],
            "value": override["value"] if override else base[key],
            "is_overridden": bool(override),
            "note": override["note"] if override else "",
        })
    effective_terms = [
        {**term, "rate": overrides[term["key"]]["value"] if term["key"] in overrides else term.get("rate", 0)}
        for term in (formula or {}).get("terms", [])
    ]
    return {
        "vehicle_id": vehicle.id,
        "vehicle_type": vehicle.type or "",
        "has_type_formula": formula is not None,
        "type_formula_id": (formula or {}).get("id"),
        "currency": "VND",
        "override_count": len(overrides),
        "components": components,
        "terms": effective_terms,
        "expressions": (formula or {}).get("expressions"),
    }


def fleet_overview(db):
    """Load comparison inputs in bulk instead of issuing requests per vehicle."""
    types = db.query(VehicleType).all()
    aliases = {t.name: t.id for t in types}
    aliases.update({t.id: t.id for t in types})
    formulas = {}
    for row in db.query(CostFormula).order_by(CostFormula.id).all():
        formula = serialize_cost_formula(row)
        if formula.get('currency') == 'VND':
            formulas[formula.get('vehicle_type_id')] = formula
    overrides = {}
    for row in db.query(VehicleCostOverride).all():
        overrides.setdefault(row.vehicle_id, []).append({
            'component': row.component, 'value': float(row.value), 'note': row.note or '',
        })
    vehicles = [_resolved_cost(vehicle, formulas.get(aliases.get(vehicle.type, vehicle.type)),
                              overrides.get(vehicle.id, []))
                for vehicle in db.query(Vehicle).order_by(Vehicle.id).all()]
    history = db.query(AuditLog).filter(AuditLog.table_name == 'vehicle_cost_overrides').order_by(
        AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(100).all()
    return {'vehicles': vehicles, 'history': [
        {'vehicle_id': row.record_id, 'actor': row.user_id, 'message': row.action,
         'at': row.timestamp.replace(tzinfo=dt.timezone.utc).isoformat() if row.timestamp else None}
        for row in history]}
