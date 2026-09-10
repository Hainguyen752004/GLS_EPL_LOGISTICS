"""Giá thành hai tầng: công thức theo loại xe, ghi đè theo từng chiếc.

Chủ dự án chốt mô hình này thay vì "mỗi chiếc một công thức riêng": đội xe khoảng
500 chiếc, nên đó là 500 công thức phải bảo trì — đổi giá dầu phải sửa 500 chỗ,
và rất dễ có xe bị bỏ sót rồi tính sai giá mà không ai biết.

Điều quan trọng nhất cần khóa lại: **xe không ghi đè thì không có dòng nào trong
bảng**, và nó kế thừa nguyên vẹn. Nhờ vậy sửa công thức của loại xe vẫn có tác
dụng cho cả đội.
"""
import json
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, CostFormula, Vehicle, VehicleType, VehicleCostOverride
from services import vehicle_cost_service as svc
from services.errors import DomainError


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Vehicle(id="51C-111.11", type="Container 20FT"))
    session.add(Vehicle(id="51C-222.22", type="Container 20FT"))
    session.add(Vehicle(id="51C-333.33", type="Loai chua co cong thuc"))
    session.add(CostFormula(
        id="CF-20FT",
        name="Container 20FT",
        formula_expression=json.dumps({
            "vehicle_type_id": "Container 20FT",
            "currency": "VND",
            "components": {"fuel": 6250, "driver": 500000, "toll": 300000, "wh": 200000, "rate": 1500},
        }),
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _by_component(result):
    return {row["component"]: row for row in result["components"]}


# --------------------------------------------------------------------------
# Kế thừa
# --------------------------------------------------------------------------

def test_vehicle_without_overrides_inherits_everything(db):
    result = svc.effective_cost(db, "51C-111.11")
    assert result["override_count"] == 0
    assert result["has_type_formula"] is True
    rows = _by_component(result)
    assert rows["fuel"]["value"] == 6250
    assert rows["driver"]["value"] == 500000
    assert all(not row["is_overridden"] for row in result["components"])


def test_named_vehicle_uses_terms_and_vnd_formula(db):
    db.add(VehicleType(id="VT20", name="Container 20FT"))
    db.add(CostFormula(id="00-USD", name="USD", formula_expression=json.dumps({
        "vehicle_type_id": "VT20", "currency": "USD", "components": {"fuel": 2},
    })))
    db.add(CostFormula(id="01-VND", name="VND", formula_expression=json.dumps({
        "vehicle_type_id": "VT20", "currency": "VND",
        "components": {"fuel": "6250", "warehouse": 100000, "freight_rate": 1200},
        "terms": [{"key": "fuel", "rate": 4800}],
    })))
    db.commit()
    result = svc.effective_cost(db, "51C-111.11")
    rows = _by_component(result)
    assert result["currency"] == "VND"
    assert rows["fuel"]["value"] == 4800
    assert rows["wh"]["value"] == 100000
    assert rows["rate"]["value"] == 1200


def test_no_rows_are_stored_for_a_vehicle_that_inherits(db):
    """Kế thừa KHÔNG được sinh bản ghi.

    Nếu mỗi xe đều có bản ghi sao chép giá trị của loại xe thì sửa công thức
    loại xe sẽ không còn tác dụng — đúng thứ mô hình hai tầng sinh ra để tránh.
    """
    svc.effective_cost(db, "51C-111.11")
    assert db.query(VehicleCostOverride).count() == 0


def test_vehicle_type_without_a_formula_reports_it(db):
    result = svc.effective_cost(db, "51C-333.33")
    assert result["has_type_formula"] is False
    assert all(row["inherited"] == 0 for row in result["components"])


# --------------------------------------------------------------------------
# Ghi đè
# --------------------------------------------------------------------------

def test_override_changes_only_that_component_and_only_that_vehicle(db):
    svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": 7100, "note": "Xe cu, ton dau hon"}], "kd")
    db.commit()

    changed = _by_component(svc.effective_cost(db, "51C-111.11"))
    assert changed["fuel"]["value"] == 7100
    assert changed["fuel"]["is_overridden"] is True
    assert changed["fuel"]["inherited"] == 6250, "phai van thay duoc con so goc"
    assert changed["fuel"]["note"] == "Xe cu, ton dau hon"
    # Cac cau phan khac van ke thua.
    assert changed["driver"]["value"] == 500000
    assert changed["driver"]["is_overridden"] is False

    # Chiec cung loai KHONG bi anh huong.
    other = _by_component(svc.effective_cost(db, "51C-222.22"))
    assert other["fuel"]["value"] == 6250
    assert other["fuel"]["is_overridden"] is False


def test_changing_the_type_formula_still_moves_every_inheriting_vehicle(db):
    """Đây là lý do tồn tại của mô hình hai tầng.

    Đổi giá dầu ở loại xe phải kéo theo cả đội, trừ những chiếc đã ghi đè.
    """
    svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": 7100}], "kd")
    db.commit()

    formula = db.get(CostFormula, "CF-20FT")
    payload = json.loads(formula.formula_expression)
    payload["components"]["fuel"] = 8000
    formula.formula_expression = json.dumps(payload)
    db.commit()

    assert _by_component(svc.effective_cost(db, "51C-222.22"))["fuel"]["value"] == 8000, "xe ke thua phai doi theo"
    assert _by_component(svc.effective_cost(db, "51C-111.11"))["fuel"]["value"] == 7100, "xe da ghi de thi giu nguyen"


def test_empty_list_returns_the_vehicle_to_full_inheritance(db):
    svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": 7100}], "kd")
    db.commit()
    svc.replace_overrides(db, "51C-111.11", [], "kd")
    db.commit()
    assert db.query(VehicleCostOverride).count() == 0
    assert _by_component(svc.effective_cost(db, "51C-111.11"))["fuel"]["value"] == 6250


def test_overrides_are_replaced_not_merged(db):
    svc.replace_overrides(db, "51C-111.11", [
        {"component": "fuel", "value": 7100},
        {"component": "toll", "value": 400000},
    ], "kd")
    db.commit()
    svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": 7200}], "kd")
    db.commit()
    rows = svc.list_overrides(db, "51C-111.11")
    assert [row["component"] for row in rows] == ["fuel"], "ghi de cu phai bien mat, khong con mo coi"


# --------------------------------------------------------------------------
# Chặn dữ liệu sai
# --------------------------------------------------------------------------

def test_unknown_component_is_rejected(db):
    with pytest.raises(DomainError) as error:
        svc.replace_overrides(db, "51C-111.11", [{"component": "khong_co_that", "value": 1}], "kd")
    assert error.value.code == "OVERRIDE_COMPONENT_INVALID"


def test_duplicate_component_is_rejected(db):
    with pytest.raises(DomainError) as error:
        svc.replace_overrides(db, "51C-111.11", [
            {"component": "fuel", "value": 1},
            {"component": "fuel", "value": 2},
        ], "kd")
    assert error.value.code == "OVERRIDE_COMPONENT_DUPLICATE"


@pytest.mark.parametrize("value", [-1, "khong phai so", float("inf")])
def test_invalid_value_is_rejected(db, value):
    with pytest.raises(DomainError) as error:
        svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": value}], "kd")
    assert error.value.code in ("OVERRIDE_VALUE_INVALID", "OVERRIDE_VALUE_TOO_LARGE")


def test_unknown_vehicle_is_rejected(db):
    for call in (lambda: svc.effective_cost(db, "KHONG-CO"),
                 lambda: svc.replace_overrides(db, "KHONG-CO", [], "kd")):
        with pytest.raises(DomainError) as error:
            call()
        assert error.value.code == "VEHICLE_NOT_FOUND"


def test_missing_key_leaves_overrides_untouched(db):
    """Không gửi `overrides` nghĩa là "không đụng tới", khác hẳn gửi mảng rỗng."""
    svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": 7100}], "kd")
    db.commit()
    svc.replace_overrides(db, "51C-111.11", None, "kd")
    assert db.query(VehicleCostOverride).count() == 1


def test_dynamic_component_and_expression_are_inherited_by_vehicle(db):
    formula = db.get(CostFormula, "CF-20FT")
    payload = json.loads(formula.formula_expression)
    payload["terms"] = [
        {"key": "fuel", "label": "Fuel", "kind": "cost", "factor": "per_km", "rate": 4800},
        {"key": "dep", "label": "Depreciation", "kind": "cost", "factor": "per_km", "rate": 900},
        {"key": "rate", "label": "Freight", "kind": "revenue", "factor": "per_kg", "rate": 1200},
    ]
    payload["expressions"] = {"COST": "(fuel + dep) * km", "REV": "rate * kg", "PROFIT": "REV - COST"}
    formula.formula_expression = json.dumps(payload)
    db.commit()
    svc.replace_overrides(db, "51C-111.11", [{"component": "dep", "value": 1100, "note": "Older vehicle"}])
    db.commit()
    result = svc.effective_cost(db, "51C-111.11")
    assert _by_component(result)["dep"]["inherited"] == 900
    assert _by_component(result)["dep"]["value"] == 1100
    assert result["expressions"] == payload["expressions"]
    assert next(t for t in result["terms"] if t["key"] == "dep")["rate"] == 1100
    assert _by_component(svc.effective_cost(db, "51C-222.22"))["dep"]["value"] == 900


def test_invalid_replacement_does_not_delete_existing_override(db):
    svc.replace_overrides(db, "51C-111.11", [{"component": "fuel", "value": 7100}])
    db.commit()
    with pytest.raises(DomainError):
        svc.replace_overrides(db, "51C-111.11", [{"component": "unknown", "value": 1}])
    assert svc.list_overrides(db, "51C-111.11")[0]["value"] == 7100


def test_duplicate_legacy_formula_uses_same_order_as_catalog(db):
    db.add(CostFormula(id="ZZ-20FT", name="Current catalog entry", formula_expression=json.dumps({
        "vehicle_type_id": "Container 20FT", "currency": "VND",
        "terms": [{"key": "fuel", "rate": 4800}],
    })))
    db.commit()
    result = svc.effective_cost(db, "51C-111.11")
    assert result["type_formula_id"] == "ZZ-20FT"
    assert _by_component(result)["fuel"]["value"] == 4800


def test_fleet_overview_matches_vehicle_price_and_has_persisted_history(db):
    svc.replace_overrides(db, "51C-111.11", [{"component":"fuel", "value":7100, "note":"Older vehicle"}], "planner")
    db.commit()
    result = svc.fleet_overview(db)
    vehicle = next(v for v in result["vehicles"] if v["vehicle_id"] == "51C-111.11")
    assert vehicle["components"] == svc.effective_cost(db, "51C-111.11")["components"]
    assert result["history"][0]["actor"] == "planner"
    assert "7100" in result["history"][0]["message"]
    svc.replace_overrides(db, "51C-111.11", [], "planner")
    db.commit()
    assert "chuẩn" in svc.fleet_overview(db)["history"][0]["message"]
