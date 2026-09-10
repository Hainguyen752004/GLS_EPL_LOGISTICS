import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import threading

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.orm import sessionmaker

from database import Base


@pytest.fixture
def db_session(tmp_path, may_kiem):
    import models  # register all mapped tables before creating the isolated schema

    # PostgreSQL cuong che khoa ngoai san. Ban truoc phai bat tay
    # `PRAGMA foreign_keys=ON` vi mac dinh cua SQLite la TAT — va `PRAGMA` khong
    # phai cau lenh cua PostgreSQL, de lai la loi ngay o buoc mo ket noi.
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_master_money_models_use_required_numeric_precision_and_constraints(db_session):
    from models import CurrencyDefinition, CurrencyRateHistory, FinanceControlConfig, TaxCode

    db_session.add_all([
        CurrencyDefinition(code="VND", minor_units=0),
        CurrencyDefinition(code="USD", minor_units=2),
        CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 10), rate=Decimal("26123.12345678"), source="SBV"),
        TaxCode(code="VAT10", effective_from=dt.date(2026, 1, 1), rate=Decimal("0.10000000"), mode="exclusive"),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND", enforce_creator_approver_sod=True, require_distinct_poster=True, distance_variance_threshold=Decimal("10.00000000")),
    ])
    db_session.commit()

    tables = inspect(db_session.bind).get_table_names()
    assert {"currency_definitions", "currency_rate_history", "tax_codes", "finance_control_config"} <= set(tables)
    assert CurrencyRateHistory.__table__.c.rate.type.precision == 18
    assert CurrencyRateHistory.__table__.c.rate.type.scale == 8
    assert TaxCode.__table__.c.rate.type.precision == 18
    assert TaxCode.__table__.c.rate.type.scale == 8


def test_master_currency_missing_has_vietnamese_message_and_navigation(db_session):
    from services.tms_money import require_currency

    with pytest.raises(Exception) as caught:
        require_currency(db_session, "USD")
    error = caught.value
    assert error.code == "MISSING_CURRENCY"
    assert "Thiếu" in error.message and "Master Data" in error.message
    assert error.navigation_targets == ["master-data/currencies"]


def test_money_quantizes_currency_master_round_half_up(db_session):
    from models import CurrencyDefinition
    from services.tms_money import quantize_currency

    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0), CurrencyDefinition(code="USD", minor_units=2), CurrencyDefinition(code="KWD", minor_units=3)])
    db_session.flush()
    assert quantize_currency(db_session, Decimal("1.5"), "VND") == Decimal("2")
    assert quantize_currency(db_session, Decimal("1.005"), "USD") == Decimal("1.01")
    assert quantize_currency(db_session, Decimal("1.2345"), "KWD") == Decimal("1.235")


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("exclusive", (Decimal("200.00"), Decimal("20.00"), Decimal("220.00"))),
        ("inclusive", (Decimal("181.82"), Decimal("18.18"), Decimal("200.00"))),
        ("exempt", (Decimal("200.00"), Decimal("0.00"), Decimal("200.00"))),
    ],
)
def test_money_calculates_charge_tax_modes(db_session, mode, expected):
    from models import CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_money import calculate_charge_line

    db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.add(FinanceControlConfig(id="GLOBAL", functional_currency="USD"))
    db_session.add(TaxCode(code=f"T-{mode}", effective_from=dt.date(2020, 1, 1), rate=Decimal("0.10"), mode=mode))
    db_session.flush()
    result = calculate_charge_line(db_session, Decimal("2"), Decimal("100"), f"T-{mode}", mode)
    assert (result["net_amount"], result["tax_amount"], result["total_amount"]) == expected
    assert result["tax_code"] == f"T-{mode}"
    assert result["tax_rate"] == Decimal("0.10000000")
    assert result["tax_mode"] == mode
    assert type(result) is dict


def test_money_supports_multiple_rates_by_calculating_each_line(db_session):
    from models import CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_money import calculate_charge_line

    db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.add(FinanceControlConfig(id="GLOBAL", functional_currency="USD"))
    db_session.add_all([TaxCode(code="LOW", effective_from=dt.date(2020, 1, 1), rate=Decimal(".05"), mode="exclusive"), TaxCode(code="HIGH", effective_from=dt.date(2020, 1, 1), rate=Decimal(".10"), mode="exclusive")])
    db_session.flush()
    low = calculate_charge_line(db_session, Decimal("1"), Decimal("100"), "LOW", "exclusive")
    high = calculate_charge_line(db_session, Decimal("1"), Decimal("100"), "HIGH", "exclusive")
    assert low["tax_amount"] + high["tax_amount"] == Decimal("15.00")


def test_money_allocates_residual_to_largest_absolute_amount_then_line_id():
    from services.tms_money import allocate_rounding_residual

    lines = [("B", Decimal("10.00")), ("A", Decimal("10.00")), ("C", Decimal("4.00"))]
    assert allocate_rounding_residual(lines, Decimal("0.02"), 2) == {
        "A": Decimal("0.02"), "B": Decimal("0.00"), "C": Decimal("0.00")
    }
    assert allocate_rounding_residual(lines, Decimal("-0.01"), 2)["A"] == Decimal("-0.01")


def test_money_converts_to_functional_currency(db_session):
    from models import CurrencyDefinition, CurrencyRateHistory, FinanceControlConfig
    from services.tms_money import to_functional

    db_session.add_all([CurrencyDefinition(code="USD", minor_units=2), CurrencyDefinition(code="VND", minor_units=0)])
    db_session.flush()
    db_session.add_all([FinanceControlConfig(id="GLOBAL", functional_currency="VND"), CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 10), rate=Decimal("26000"), source="SBV")])
    db_session.flush()
    result = to_functional(db_session, Decimal("1.25"), "USD", dt.date(2026, 8, 10))
    assert result == {
        "transaction_amount": Decimal("1.25"),
        "transaction_currency": "USD",
        "functional_amount": Decimal("32500"),
        "functional_currency": "VND",
        "exchange_rate_snapshot": Decimal("26000.00000000"),
        "rate_date": dt.date(2026, 8, 10),
        "source": "SBV",
    }
    assert type(result) is dict


@pytest.mark.parametrize("bad", [True, False, 1.2, float("nan"), float("inf"), Decimal("NaN"), Decimal("Infinity")])
def test_money_rejects_bool_float_nan_and_infinity(db_session, bad):
    from models import CurrencyDefinition
    from services.tms_money import quantize_currency

    db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.flush()
    with pytest.raises(Exception) as caught:
        quantize_currency(db_session, bad, "USD")
    assert caught.value.code == "INVALID_DECIMAL"


def test_money_sqlalchemy_types_have_canonical_precision_and_scale():
    from models import DISTANCE_TYPE, MONEY_TYPE, QUANTITY_TYPE, RATE_TYPE

    assert (MONEY_TYPE.precision, MONEY_TYPE.scale) == (24, 6)
    assert (QUANTITY_TYPE.precision, QUANTITY_TYPE.scale) == (18, 4)
    assert (RATE_TYPE.precision, RATE_TYPE.scale) == (18, 8)
    assert (DISTANCE_TYPE.precision, DISTANCE_TYPE.scale) == (18, 3)


def test_master_tax_and_finance_missing_include_navigation_targets(db_session):
    from services.tms_money import require_finance_config, require_tax_code

    for call, code, target in (
        (lambda: require_tax_code(db_session, "VAT10", dt.date(2026, 8, 10)), "MISSING_TAX_CODE", "master-data/tax-codes"),
        (lambda: require_finance_config(db_session), "MISSING_FINANCE_CONFIG", "master-data/finance-controls"),
    ):
        with pytest.raises(Exception) as caught:
            call()
        assert caught.value.code == code
        assert "Thiếu" in caught.value.message and "Master Data" in caught.value.message
        assert caught.value.navigation_targets == [target]


def test_master_resolves_latest_effective_exchange_rate_deterministically(db_session):
    from models import CurrencyDefinition, CurrencyRateHistory
    from services.tms_money import resolve_exchange_rate

    db_session.add_all([CurrencyDefinition(code="USD", minor_units=2), CurrencyDefinition(code="VND", minor_units=0)])
    db_session.flush()
    db_session.add_all([
        CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 9), rate=Decimal("26000"), source="Z", is_active=True),
        CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 10), rate=Decimal("26100"), source="B", is_active=True),
        CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 10), rate=Decimal("26200"), source="A", is_active=True),
        CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 11), rate=Decimal("99999"), source="A", is_active=True),
        CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 8, 10), rate=Decimal("88888"), source="0", is_active=False),
    ])
    db_session.commit()

    snapshot = resolve_exchange_rate(db_session, "usd", "vnd", dt.date(2026, 8, 10))
    assert (snapshot.rate, snapshot.source) == (Decimal("26200.00000000"), "A")


def test_master_missing_exchange_rate_has_navigation_target(db_session):
    from models import CurrencyDefinition
    from services.tms_money import resolve_exchange_rate

    db_session.add_all([CurrencyDefinition(code="USD", minor_units=2), CurrencyDefinition(code="VND", minor_units=0)])
    db_session.flush()
    with pytest.raises(Exception) as caught:
        resolve_exchange_rate(db_session, "USD", "VND", dt.date(2026, 8, 10))
    assert caught.value.code == "MISSING_EXCHANGE_RATE"
    assert caught.value.navigation_targets == ["master-data/exchange-rates"]


def test_money_rejects_amount_precision_over_money_24_6(db_session):
    from models import CurrencyDefinition
    from services.tms_money import quantize_currency

    db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.flush()
    with pytest.raises(Exception) as caught:
        quantize_currency(db_session, Decimal("1000000000000000000.000000"), "USD")
    assert caught.value.code == "DECIMAL_OUT_OF_RANGE"


def test_money_residual_preserves_numeric_ids_and_uses_numeric_tie_break():
    from services.tms_money import allocate_rounding_residual

    result = allocate_rounding_residual([(10, Decimal("5")), (2, Decimal("5"))], Decimal("0.01"), 2)
    assert result == {10: Decimal("0.00"), 2: Decimal("0.01")}


@pytest.mark.parametrize(
    "lines, code",
    [
        ([(1, Decimal("2")), (1, Decimal("3"))], "DUPLICATE_ROUNDING_LINE_ID"),
        ([(1, Decimal("2")), ("2", Decimal("3"))], "INCOMPARABLE_ROUNDING_LINE_IDS"),
    ],
)
def test_money_residual_rejects_duplicate_or_mixed_ids(lines, code):
    from services.tms_money import allocate_rounding_residual

    with pytest.raises(Exception) as caught:
        allocate_rounding_residual(lines, Decimal("0.01"), 2)
    assert caught.value.code == code


def test_finance_config_is_global_and_fails_closed_on_ambiguity(db_session):
    from models import CurrencyDefinition, FinanceControlConfig
    from services.tms_money import require_finance_config

    db_session.add(CurrencyDefinition(code="VND", minor_units=0))
    db_session.flush()
    db_session.add(FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
    db_session.flush()
    assert require_finance_config(db_session).id == "GLOBAL"
    with pytest.raises(Exception):
        db_session.add(FinanceControlConfig(id="OTHER", functional_currency="VND"))
        db_session.flush()


def test_tax_code_history_resolves_latest_active_effective_row(db_session):
    from models import TaxCode
    from services.tms_money import require_tax_code

    db_session.add_all([
        TaxCode(code="VAT", effective_from=dt.date(2025, 1, 1), effective_to=dt.date(2025, 12, 31), rate=Decimal(".08"), mode="exclusive"),
        TaxCode(code="VAT", effective_from=dt.date(2026, 1, 1), rate=Decimal(".10"), mode="exclusive"),
        TaxCode(code="VAT", effective_from=dt.date(2026, 6, 1), rate=Decimal(".12"), mode="exclusive", is_active=False),
    ])
    db_session.flush()
    assert require_tax_code(db_session, "VAT", dt.date(2026, 8, 10)).rate == Decimal(".10000000")
    assert require_tax_code(db_session, "VAT", "2026-08-10").rate == Decimal(".10000000")


def test_tax_code_rejects_invalid_effective_date_stably(db_session):
    from services.tms_money import require_tax_code

    with pytest.raises(Exception) as caught:
        require_tax_code(db_session, "VAT", "not-a-date")
    assert caught.value.code == "INVALID_EFFECTIVE_DATE"
    assert caught.value.status_code == 422


def test_sqlite_enforces_master_checks_and_foreign_keys(db_session):
    from models import CurrencyDefinition, CurrencyRateHistory, TaxCode

    db_session.add(CurrencyDefinition(code="BAD", minor_units=7))
    with pytest.raises(Exception):
        db_session.flush()
    db_session.rollback()
    db_session.add(TaxCode(code="BAD", effective_from=dt.date(2026, 2, 1), effective_to=dt.date(2026, 1, 1), rate=Decimal(".1"), mode="exclusive"))
    with pytest.raises(Exception):
        db_session.flush()
    db_session.rollback()
    db_session.add(CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 1, 1), rate=Decimal("1"), source="X"))
    with pytest.raises(Exception):
        db_session.flush()


def test_exchange_rate_requires_active_currency_masters(db_session):
    from models import CurrencyDefinition, CurrencyRateHistory
    from services.tms_money import resolve_exchange_rate

    db_session.add_all([CurrencyDefinition(code="USD", minor_units=2, is_active=False), CurrencyDefinition(code="VND", minor_units=0)])
    db_session.flush()
    db_session.add(CurrencyRateHistory(currency_code="USD", functional_currency="VND", rate_date=dt.date(2026, 1, 1), rate=Decimal("1"), source="X"))
    db_session.flush()
    with pytest.raises(Exception) as caught:
        resolve_exchange_rate(db_session, "USD", "VND", dt.date(2026, 8, 10))
    assert caught.value.code == "MISSING_CURRENCY"


def _delivered_order(db_session, status="delivered", suffix=""):
    from models import FreightOrder, Location
    db_session.add_all([Location(id=f"COST-A{suffix}", name="A"), Location(id=f"COST-B{suffix}", name="B")])
    db_session.flush()
    order = FreightOrder(
        id=f"FO-COST{suffix}", pickup_location_id=f"COST-A{suffix}", delivery_location_id=f"COST-B{suffix}",
        pickup_window_start=dt.datetime(2026, 8, 10, 8), pickup_window_end=dt.datetime(2026, 8, 10, 9),
        delivery_window_start=dt.datetime(2026, 8, 10, 10), delivery_window_end=dt.datetime(2026, 8, 10, 11),
        max_weight_kg=1, max_volume_m3=1, max_pallet_count=1, status=status,
    )
    db_session.add(order)
    db_session.flush()
    return order


def test_cost_models_use_canonical_types_and_one_active_cost(db_session):
    from models import DISTANCE_TYPE, MONEY_TYPE, QUANTITY_TYPE, FreightActualCost, FreightChargeItem
    assert FreightActualCost.__table__.c.total_amount.type is MONEY_TYPE
    assert FreightActualCost.__table__.c.actual_distance_km.type is DISTANCE_TYPE
    assert FreightChargeItem.__table__.c.quantity.type is QUANTITY_TYPE
    order = _delivered_order(db_session)
    db_session.add_all([
        FreightActualCost(id="C1", freight_order_id=order.id, carrier_id="X", currency_code="VND"),
        FreightActualCost(id="C2", freight_order_id=order.id, carrier_id="X", currency_code="VND"),
    ])
    with pytest.raises(Exception):
        db_session.commit()


def test_cost_create_is_delivered_only_and_audits_ip(db_session):
    from models import AuditLog, Carrier, CurrencyDefinition, FinanceControlConfig
    from services.tms_cost_service import create_cost
    order = _delivered_order(db_session, "dispatched")
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0), FinanceControlConfig(id="GLOBAL", functional_currency="VND"), Carrier(id="INTERNAL", name="Nội bộ", is_internal=True)])
    db_session.flush()
    with pytest.raises(Exception) as caught:
        create_cost(db_session, order.id, {"id": "C1", "carrier_id": "INTERNAL", "currency_code": "VND", "planned_distance_km": "10"}, "POST", "/costs", "create-1", "maker", {"finance_creator"})
    assert caught.value.code == "FREIGHT_ORDER_NOT_DELIVERED"
    order.status = "delivered"
    db_session.info["audit_ip"] = "127.0.0.7"
    cost = create_cost(db_session, order.id, {"id": "C1", "carrier_id": "INTERNAL", "currency_code": "VND", "planned_distance_km": "10"}, "POST", "/costs", "create-2", "maker", {"finance_creator"})
    assert cost.status == "draft" and cost.created_by == "maker"
    assert db_session.query(AuditLog).filter_by(record_id="C1").one().ip_address == "127.0.0.7"


def test_cost_distance_haversine_orders_filters_and_handles_planned_zero(db_session):
    from models import TransportEvent
    from services.tms_cost_service import calculate_actual_distance
    order = _delivered_order(db_session)
    base = dt.datetime(2026, 8, 10, 8)
    for ident, minute, lat, lng in (("E3", 3, 0, 1), ("E1", 1, 0, 0), ("E2", 2, 0, 0), ("BAD", 0, 99, 0)):
        db_session.add(TransportEvent(id=ident, freight_order_id=order.id, event_type="x", event_time=base + dt.timedelta(minutes=minute), recorded_at=base, lat=lat, lng=lng, source="manual", idempotency_key=ident, payload_hash=ident, recorded_by="x"))
    db_session.flush()
    result = calculate_actual_distance(db_session, order.id, Decimal("0"))
    assert result["status"] == "calculated"
    assert result["actual_distance_km"] == Decimal("111.195")
    assert result["variance_percent"] is None


def test_cost_items_totals_cas_submit_approve_and_sod(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import add_charge_item, approve_cost, create_cost, submit_cost
    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="USD", minor_units=2), FinanceControlConfig(id="GLOBAL", functional_currency="USD"), TaxCode(code="VAT", effective_from=dt.date(2020, 1, 1), rate=Decimal(".1"), mode="exclusive"), Carrier(id="CAR", name="Carrier", is_internal=True)])
    db_session.flush()
    cost = create_cost(db_session, order.id, {"id": "C1", "carrier_id": "CAR", "currency_code": "USD"}, "POST", "/costs", "create", "maker", {"finance_creator"})
    item = add_charge_item(db_session, cost.id, {"id": "I1", "charge_type": "toll", "quantity": "2", "unit_price": "10", "tax_code": "VAT", "tax_mode": "exclusive", "expected_version": 1}, "maker", {"finance_creator"})
    assert item.total_amount == Decimal("22.00") and cost.total_amount == Decimal("22.00") and cost.version == 2
    with pytest.raises(Exception) as caught:
        submit_cost(db_session, cost.id, 1, "POST", f"/costs/{cost.id}/submit", "submit-bad", "maker", {"finance_creator"})
    assert caught.value.code == "VERSION_CONFLICT"
    submit_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/submit", "submit", "maker", {"finance_creator"})
    with pytest.raises(Exception) as caught:
        approve_cost(db_session, cost.id, 3, "POST", f"/costs/{cost.id}/approve", "approve-bad", "maker", {"finance_approver"})
    assert caught.value.code == "SEPARATION_OF_DUTIES"
    assert approve_cost(db_session, cost.id, 3, "POST", f"/costs/{cost.id}/approve", "approve", "checker", {"finance_approver"}).status == "approved"


def test_cost_idempotency_scope_and_reversal_are_persisted(db_session):
    from models import IdempotencyRecord, FreightActualCost
    assert {"actor", "method", "path", "idempotency_key", "request_hash", "response_json"} <= set(IdempotencyRecord.__table__.c.keys())
    assert any(set(c.columns.keys()) == {"actor", "method", "path", "idempotency_key"} for c in IdempotencyRecord.__table__.constraints if hasattr(c, "columns"))
    assert FreightActualCost.__table__.c.version.type.python_type is int


def test_cost_save_item_idempotency_and_reverse_creates_negative_link(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import approve_cost, create_cost, reverse_cost, save_charge_item, submit_cost
    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="USD", minor_units=2), FinanceControlConfig(id="GLOBAL", functional_currency="USD"), TaxCode(code="VAT", effective_from=dt.date(2020, 1, 1), rate=Decimal(".1"), mode="exclusive"), Carrier(id="CAR", name="Carrier", is_internal=True)])
    db_session.flush()
    cost = create_cost(db_session, order.id, {"id": "C1", "carrier_id": "CAR", "currency_code": "USD"}, "POST", "/costs", "create", "maker", {"finance_creator"})
    data = {"id": "I1", "charge_type": "toll", "quantity": "2", "unit_price": "10", "tax_code": "VAT", "tax_mode": "exclusive"}
    first = save_charge_item(db_session, cost.id, data, 1, "POST", f"/costs/{cost.id}/items", "same", "maker", {"finance_creator"})
    assert save_charge_item(db_session, cost.id, data, 1, "POST", f"/costs/{cost.id}/items", "same", "maker", {"finance_creator"}).id == first.id
    with pytest.raises(Exception) as caught:
        save_charge_item(db_session, cost.id, {**data, "unit_price": "11"}, 1, "POST", f"/costs/{cost.id}/items", "same", "maker", {"finance_creator"})
    assert caught.value.code == "IDEMPOTENCY_KEY_REUSED"
    submit_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/submit", "submit", "maker", {"finance_creator"})
    approve_cost(db_session, cost.id, 3, "POST", f"/costs/{cost.id}/approve", "approve", "checker", {"finance_approver"})
    with pytest.raises(Exception) as caught:
        reverse_cost(db_session, cost.id, {"expected_version": 4, "reason": ""}, "POST", f"/costs/{cost.id}/reverse", "reverse", "poster", {"finance_poster"})
    assert caught.value.code == "REVERSAL_REASON_REQUIRED"
    reversal = reverse_cost(db_session, cost.id, {"expected_version": 4, "reason": "Sai hóa đơn"}, "POST", f"/costs/{cost.id}/reverse", "reverse", "poster", {"finance_poster"})
    assert reversal.reversal_of_cost_id == cost.id and reversal.total_amount == -cost.total_amount
    assert cost.status == "reversed" and not cost.is_active and not reversal.is_active
    assert cost.reversed_by_cost_id == reversal.id
    assert len(reversal.items) == 1
    assert (reversal.items[0].net_amount, reversal.items[0].tax_amount, reversal.items[0].total_amount) == (
        -cost.items[0].net_amount, -cost.items[0].tax_amount, -cost.items[0].total_amount)


def test_cost_document_commands_validate_url_checksum_duplicate_and_draft(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import (create_cost, delete_draft_cost_document,
        save_cost_document, submit_cost, update_cost_document)
    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="CAR", name="Carrier", is_internal=True)])
    db_session.flush()
    cost = create_cost(db_session, order.id, {"id": "C1", "carrier_id": "CAR", "currency_code": "VND"}, "POST", "/costs", "create", "maker", {"finance_creator"})
    for url in ("http://unsafe.test/a.pdf", "ftp://unsafe/a.pdf", "   "):
        with pytest.raises(Exception) as caught:
            save_cost_document(db_session, cost.id, {"storage_url": url, "checksum": "sha256:" + "a" * 64}, 1, "POST", f"/costs/{cost.id}/documents", "doc-bad-" + url, "maker", {"finance_creator"})
        assert caught.value.code == "COST_DOCUMENT_INVALID"
    checksum = "sha256:" + "a" * 64
    doc = save_cost_document(db_session, cost.id, {"id": "D1", "storage_url": "/uploads/a.pdf", "checksum": " " + checksum + " "}, 1, "POST", f"/costs/{cost.id}/documents", "doc", "maker", {"finance_creator"})
    assert doc.checksum == checksum and cost.version == 2
    with pytest.raises(Exception) as caught:
        save_cost_document(db_session, cost.id, {"id": "D2", "storage_url": "/uploads/b.pdf", "checksum": checksum}, 2, "POST", f"/costs/{cost.id}/documents", "doc-dup", "maker", {"finance_creator"})
    assert caught.value.code == "COST_DOCUMENT_DUPLICATE"
    submit_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/submit", "submit", "maker", {"finance_creator"})
    with pytest.raises(Exception) as caught:
        update_cost_document(db_session, cost.id, doc.id, {"storage_url": "https://files.test/c.pdf"}, 3, "PUT", f"/costs/{cost.id}/documents/{doc.id}", "put", "maker", {"finance_creator"})
    assert caught.value.code == "COST_NOT_DRAFT"
    with pytest.raises(Exception) as caught:
        delete_draft_cost_document(db_session, cost.id, doc.id, 3, "DELETE", f"/costs/{cost.id}/documents/{doc.id}", "delete", "maker", {"finance_creator"})
    assert caught.value.code == "COST_NOT_DRAFT"


def test_cost_transition_uses_cas_and_postgresql_lock():
    from sqlalchemy.dialects import postgresql
    from models import FreightActualCost
    from services.tms_cost_service import cost_lock_statement, cost_transition_statement
    lock_sql = str(cost_lock_statement("C1").compile(dialect=postgresql.dialect()))
    update_sql = str(cost_transition_statement("C1", 2, "draft", "submitted", "maker").compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in lock_sql
    assert "freight_actual_costs.version =" in update_sql
    assert "freight_actual_costs.status =" in update_sql


def test_cost_model_requires_complete_fx_snapshot_and_blocks_self_reversal():
    from models import FreightActualCost
    table = FreightActualCost.__table__
    assert not table.c.functional_currency.nullable
    assert not table.c.exchange_rate_date.nullable
    assert not table.c.exchange_rate_source.nullable
    check_sql = " ".join(str(c.sqltext) for c in table.constraints if hasattr(c, "sqltext"))
    assert "reversal_of_cost_id <> id" in check_sql


def test_idempotency_replay_is_snapshot_and_permission_precedes_replay(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import create_cost
    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0), FinanceControlConfig(id="GLOBAL", functional_currency="VND"), Carrier(id="CAR", name="Carrier", is_internal=True)])
    db_session.flush()
    first = create_cost(db_session, order.id, {"id": "C1", "carrier_id": "CAR", "currency_code": "VND"}, "POST", "/tenant/a/costs", "same", "maker", {"finance_creator"})
    first.status = "submitted"
    replay = create_cost(db_session, order.id, {"id": "C1", "carrier_id": "CAR", "currency_code": "VND"}, "POST", "/tenant/a/costs", "same", "maker", {"finance_creator"})
    assert replay.status == "draft"
    with pytest.raises(Exception) as caught:
        create_cost(db_session, order.id, {"id": "C1", "carrier_id": "CAR", "currency_code": "VND"}, "POST", "/tenant/a/costs", "same", "maker", set())
    assert caught.value.code == "FINANCE_PERMISSION_DENIED"


def _concurrent_cost_database(may_kiem):
    import models

    # Bai kiem GHI DONG THOI tu hai luong. Tren SQLite phai noi rong
    # `busy_timeout` vi mot tep SQLite chi cho MOT nguoi ghi mot luc, va khoa
    # o muc ca TEP — nen phep kiem "hai nguoi ghi cung luc" o day thuc ra chi
    # kiem duoc rang mot nguoi phai xep hang. PostgreSQL khoa o muc DONG va co
    # giao dich that, nen day moi la cho kiem duoc dung dieu bai nay muon noi.
    engine = may_kiem()
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    seed = sessions()
    order = _delivered_order(seed)
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    seed.add_all([
        CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True),
        TaxCode(code="EXEMPT", effective_from=dt.date(2020, 1, 1), rate=Decimal("0"), mode="exempt"),
    ])
    seed.commit()
    seed.close()
    return engine, sessions, order.id


def test_cost_same_key_simultaneous_replays_one_atomic_result(tmp_path, may_kiem):
    from models import AuditLog, FreightActualCost, IdempotencyRecord
    from services.tms_cost_service import create_cost

    engine, sessions, order_id = _concurrent_cost_database(may_kiem)
    gate = threading.Barrier(2)

    def invoke():
        session = sessions()
        try:
            gate.wait()
            result = create_cost(session, order_id,
                {"id": "C-RACE", "carrier_id": "INTERNAL", "currency_code": "VND"},
                "POST", "/costs", "same-key", "maker", {"finance_creator"})
            session.commit()
            return result.id
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: invoke(), range(2))) == ["C-RACE", "C-RACE"]
    verify = sessions()
    assert verify.query(FreightActualCost).count() == 1
    assert verify.query(AuditLog).filter_by(record_id="C-RACE").count() == 1
    assert verify.query(IdempotencyRecord).filter_by(idempotency_key="same-key").count() == 1
    verify.close(); engine.dispose()


def test_cost_different_keys_same_version_has_one_winner(tmp_path, may_kiem):
    from models import AuditLog, FreightActualCost, FreightChargeItem, IdempotencyRecord
    from services.tms_cost_service import create_cost, save_charge_item

    engine, sessions, order_id = _concurrent_cost_database(may_kiem)
    seed = sessions()
    create_cost(seed, order_id, {"id": "C-CAS", "carrier_id": "INTERNAL", "currency_code": "VND"},
                "POST", "/costs", "create", "maker", {"finance_creator"})
    seed.commit(); seed.close()
    gate = threading.Barrier(2)

    def invoke(index):
        session = sessions()
        try:
            gate.wait()
            save_charge_item(session, "C-CAS", {"id": f"I-{index}", "charge_type": "toll",
                "quantity": "1", "unit_price": "10", "tax_code": "EXEMPT", "tax_mode": "exempt"},
                1, "POST", "/costs/C-CAS/items", f"item-{index}", "maker", {"finance_creator"})
            session.commit(); return "won"
        except Exception as error:
            session.rollback(); return getattr(error, "code", type(error).__name__)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, range(2)))
    assert sorted(outcomes) == ["VERSION_CONFLICT", "won"]
    verify = sessions()
    assert verify.get(FreightActualCost, "C-CAS").version == 2
    assert verify.query(FreightChargeItem).count() == 1
    assert verify.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key.like("item-%")).count() == 1
    assert verify.query(AuditLog).filter_by(table_name="freight_charge_items").count() == 1
    verify.close(); engine.dispose()


def test_cost_documents_different_keys_same_version_have_one_winner(tmp_path, may_kiem):
    from models import AuditLog, FreightCostDocument, IdempotencyRecord
    from services.tms_cost_service import create_cost, save_cost_document

    engine, sessions, order_id = _concurrent_cost_database(may_kiem)
    seed = sessions()
    create_cost(seed, order_id, {"id": "C-DOC-CAS", "carrier_id": "INTERNAL", "currency_code": "VND"},
                "POST", "/costs", "create-doc-cas", "maker", {"finance_creator"})
    seed.commit(); seed.close()
    gate = threading.Barrier(2)

    def invoke(index):
        session = sessions()
        try:
            gate.wait()
            save_cost_document(session, "C-DOC-CAS", {"id": f"D-{index}",
                "storage_url": f"/uploads/{index}.pdf", "checksum": "sha256:" + str(index) * 64}, 1,
                "POST", "/costs/C-DOC-CAS/documents", f"doc-{index}", "maker", {"finance_creator"})
            session.commit(); return "won"
        except Exception as error:
            session.rollback(); return getattr(error, "code", type(error).__name__)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, range(2)))
    assert sorted(outcomes) == ["VERSION_CONFLICT", "won"]
    verify = sessions()
    assert verify.query(FreightCostDocument).count() == 1
    assert verify.query(AuditLog).filter_by(table_name="freight_cost_documents").count() == 1
    assert verify.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key.like("doc-%")).count() == 1
    verify.close(); engine.dispose()


def test_cost_injected_failure_after_idempotency_rolls_back_partial_command(db_session):
    from models import (AuditLog, Carrier, CurrencyDefinition, FinanceControlConfig,
                        FreightActualCost, FreightChargeItem, IdempotencyRecord, TaxCode)
    from services.tms_cost_service import create_cost, save_charge_item

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True),
        TaxCode(code="EXEMPT", effective_from=dt.date(2020, 1, 1), rate=Decimal("0"), mode="exempt")])
    db_session.commit()
    create_cost(db_session, order.id, {"id": "C-INJECT", "carrier_id": "INTERNAL", "currency_code": "VND"},
                "POST", "/costs", "create-inject", "maker", {"finance_creator"})
    db_session.commit()
    db_session.info["finance_failure_hook"] = lambda stage: (_ for _ in ()).throw(RuntimeError(stage))
    with pytest.raises(RuntimeError, match="after_idempotency"):
        save_charge_item(db_session, "C-INJECT", {"id": "I-INJECT", "charge_type": "toll", "quantity": "1",
            "unit_price": "10", "tax_code": "EXEMPT", "tax_mode": "exempt"}, 1, "POST",
            "/costs/C-INJECT/items", "item-inject", "maker", {"finance_creator"})
    db_session.rollback(); db_session.info.pop("finance_failure_hook")
    assert db_session.get(FreightActualCost, "C-INJECT").version == 1
    assert db_session.query(FreightChargeItem).filter_by(id="I-INJECT").count() == 0
    assert db_session.query(AuditLog).filter_by(record_id="I-INJECT").count() == 0
    assert db_session.query(IdempotencyRecord).filter_by(idempotency_key="item-inject").count() == 0


def test_cost_carrier_policy_award_precedence_internal_only_and_missing_navigation(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, Tender
    from services.tms_cost_service import create_cost

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="AWARDED", name="Awarded", is_internal=False),
        Carrier(id="INTERNAL", name="Internal", is_internal=True),
        Tender(id="T-AWARD", freight_order_id=order.id, response_deadline=dt.datetime(2026, 8, 9),
               status="awarded", awarded_carrier_id="AWARDED")])
    db_session.flush()
    cost = create_cost(db_session, order.id, {"id": "C-AWARD", "carrier_id": "INTERNAL", "currency_code": "VND"},
                       "POST", "/costs", "award", "maker", {"finance_creator"})
    assert cost.carrier_id == "AWARDED"
    db_session.rollback()

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="EXTERNAL", name="External", is_internal=False)])
    db_session.flush()
    with pytest.raises(Exception) as missing:
        create_cost(db_session, order.id, {"id": "C-NO-INTERNAL", "carrier_id": "EXTERNAL", "currency_code": "VND"},
                    "POST", "/costs", "no-internal", "maker", {"finance_creator"})
    assert missing.value.code == "MISSING_CARRIER"
    assert missing.value.navigation_targets == ["master-data/carriers"]
    db_session.rollback()

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INACTIVE", name="Inactive", is_internal=True, status="inactive")])
    db_session.flush()
    with pytest.raises(Exception) as inactive:
        create_cost(db_session, order.id, {"id": "C-INACTIVE", "carrier_id": "INACTIVE", "currency_code": "VND"},
                    "POST", "/costs", "inactive", "maker", {"finance_creator"})
    assert inactive.value.code == "MISSING_CARRIER"
    assert inactive.value.navigation_targets == ["master-data/carriers"]


def test_cost_gps_insufficient_and_configured_variance_threshold(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TransportEvent
    from services.tms_cost_service import calculate_actual_distance, create_cost, submit_cost

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND", distance_variance_threshold=Decimal("10")),
        Carrier(id="INTERNAL", name="Internal", is_internal=True)])
    db_session.flush()
    base = dt.datetime(2026, 8, 10, 8)
    db_session.add(TransportEvent(id="ONLY", freight_order_id=order.id, event_type="gps", event_time=base,
        recorded_at=base, lat=0, lng=0, source="gps", idempotency_key="only", payload_hash="only", recorded_by="gps"))
    db_session.flush()
    assert calculate_actual_distance(db_session, order.id, Decimal("100"))["status"] == "insufficient_gps_data"
    db_session.add(TransportEvent(id="SECOND", freight_order_id=order.id, event_type="gps",
        event_time=base + dt.timedelta(minutes=1), recorded_at=base, lat=0, lng=1, source="gps",
        idempotency_key="second", payload_hash="second", recorded_by="gps"))
    cost = create_cost(db_session, order.id, {"id": "C-GPS", "carrier_id": "INTERNAL",
        "currency_code": "VND", "planned_distance_km": "100"}, "POST", "/costs", "gps-create",
        "maker", {"finance_creator"})
    submit_cost(db_session, cost.id, 1, "POST", f"/costs/{cost.id}/submit", "gps-submit",
                "maker", {"finance_creator"})
    assert cost.actual_distance_km == Decimal("111.195")
    assert cost.distance_variance_warning is True


def test_cost_outer_rollback_removes_header_audit_and_idempotency(db_session):
    from models import (AuditLog, Carrier, CurrencyDefinition, FinanceControlConfig,
                        FreightActualCost, FreightChargeItem, FreightCostDocument,
                        IdempotencyRecord, TaxCode)
    from services.tms_cost_service import create_cost, save_charge_item, save_cost_document, submit_cost

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True),
        TaxCode(code="EXEMPT", effective_from=dt.date(2020, 1, 1), rate=Decimal("0"), mode="exempt")])
    db_session.commit()
    create_cost(db_session, order.id, {"id": "C-ROLLBACK", "carrier_id": "INTERNAL", "currency_code": "VND"},
                "POST", "/costs", "rollback", "maker", {"finance_creator"})
    save_charge_item(db_session, "C-ROLLBACK", {"id": "I-ROLLBACK", "charge_type": "toll",
        "quantity": "1", "unit_price": "10", "tax_code": "EXEMPT", "tax_mode": "exempt"},
        1, "POST", "/costs/C-ROLLBACK/items", "rollback-item", "maker", {"finance_creator"})
    save_cost_document(db_session, "C-ROLLBACK", {"id": "D-ROLLBACK", "storage_url": "/uploads/a.pdf",
        "checksum": "sha256:" + "b" * 64}, 2, "POST", "/costs/C-ROLLBACK/documents", "rollback-doc", "maker", {"finance_creator"})
    submit_cost(db_session, "C-ROLLBACK", 3, "POST", "/costs/C-ROLLBACK/submit",
                "rollback-submit", "maker", {"finance_creator"})
    db_session.rollback()
    assert db_session.query(FreightActualCost).filter_by(id="C-ROLLBACK").count() == 0
    assert db_session.query(AuditLog).filter_by(record_id="C-ROLLBACK").count() == 0
    assert db_session.query(FreightChargeItem).filter_by(id="I-ROLLBACK").count() == 0
    assert db_session.query(FreightCostDocument).filter_by(id="D-ROLLBACK").count() == 0
    assert db_session.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key.like("rollback%")).count() == 0


def test_cost_concurrent_reverse_has_one_winner(tmp_path, may_kiem):
    from models import AuditLog, FreightActualCost, IdempotencyRecord
    from services.tms_cost_service import approve_cost, create_cost, reverse_cost, submit_cost

    engine, sessions, order_id = _concurrent_cost_database(may_kiem)
    seed = sessions()
    create_cost(seed, order_id, {"id": "C-REVERSE", "carrier_id": "INTERNAL", "currency_code": "VND"},
                "POST", "/costs", "create-reverse", "maker", {"finance_creator"})
    submit_cost(seed, "C-REVERSE", 1, "POST", "/costs/C-REVERSE/submit", "submit-reverse",
                "maker", {"finance_creator"})
    approve_cost(seed, "C-REVERSE", 2, "POST", "/costs/C-REVERSE/approve", "approve-reverse",
                 "checker", {"finance_approver"})
    seed.commit(); seed.close()
    gate = threading.Barrier(2)

    def invoke(index):
        session = sessions()
        try:
            gate.wait()
            reverse_cost(session, "C-REVERSE", {"expected_version": 3, "reason": "Correction"},
                         "POST", "/costs/C-REVERSE/reverse", f"reverse-{index}",
                         f"poster-{index}", {"finance_poster"})
            session.commit(); return "won"
        except Exception as error:
            session.rollback(); return getattr(error, "code", type(error).__name__)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, range(2)))
    assert sorted(outcomes) == ["VERSION_CONFLICT", "won"]
    verify = sessions()
    assert verify.query(FreightActualCost).filter_by(reversal_of_cost_id="C-REVERSE").count() == 1
    assert verify.query(AuditLog).filter_by(action="REVERSE_FREIGHT_ACTUAL_COST").count() == 1
    assert verify.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key.like("reverse-%")).count() == 1
    verify.close(); engine.dispose()


def test_cost_items_are_immutable_after_submit_and_permission_fails_closed(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import (approve_cost, create_cost, delete_draft_charge_item,
        reverse_cost, save_charge_item, submit_cost, update_charge_item)

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True),
        TaxCode(code="EXEMPT", effective_from=dt.date(2020, 1, 1), rate=Decimal("0"), mode="exempt")])
    db_session.flush()
    with pytest.raises(Exception) as denied:
        create_cost(db_session, order.id, {"carrier_id": "INTERNAL", "currency_code": "VND"},
                    "POST", "/costs", "denied", "maker", set())
    assert denied.value.code == "FINANCE_PERMISSION_DENIED" and denied.value.status_code == 403
    cost = create_cost(db_session, order.id, {"id": "C-IMMUTABLE", "carrier_id": "INTERNAL", "currency_code": "VND"},
                       "POST", "/costs", "create-immutable", "maker", {"finance_creator"})
    save_charge_item(db_session, cost.id, {"id": "I-IMMUTABLE", "charge_type": "toll", "quantity": "1",
        "unit_price": "10", "tax_code": "EXEMPT", "tax_mode": "exempt"}, 1, "POST",
        f"/costs/{cost.id}/items", "item-immutable", "maker", {"finance_creator"})
    submit_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/submit", "submit-immutable",
                "maker", {"finance_creator"})
    for command in (
        lambda: update_charge_item(db_session, cost.id, "I-IMMUTABLE", {"expected_version": 3, "unit_price": "11"}, "maker", {"finance_creator"}),
        lambda: delete_draft_charge_item(db_session, cost.id, "I-IMMUTABLE", 3, "DELETE",
            f"/costs/{cost.id}/items/I-IMMUTABLE", "delete-immutable", "maker", {"finance_creator"}),
    ):
        with pytest.raises(Exception) as caught:
            command()
        assert caught.value.code == "COST_NOT_DRAFT"
    with pytest.raises(Exception) as denied_approver:
        approve_cost(db_session, cost.id, 3, "POST", f"/costs/{cost.id}/approve", "deny-approve",
                     "checker", {"finance_creator"})
    assert denied_approver.value.code == "FINANCE_PERMISSION_DENIED"
    approve_cost(db_session, cost.id, 3, "POST", f"/costs/{cost.id}/approve", "allow-approve",
                 "checker", {"finance_approver"})
    with pytest.raises(Exception) as denied_poster:
        reverse_cost(db_session, cost.id, {"expected_version": 4, "reason": "Correction"}, "POST",
                     f"/costs/{cost.id}/reverse", "deny-reverse", "poster", {"finance_approver"})
    assert denied_poster.value.code == "FINANCE_PERMISSION_DENIED"


def test_cost_reversal_replays_and_rejects_double_or_cycle(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig
    from services.tms_cost_service import approve_cost, create_cost, reverse_cost, submit_cost

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True)])
    db_session.flush()
    cost = create_cost(db_session, order.id, {"id": "C-REV-BEHAVIOR", "carrier_id": "INTERNAL", "currency_code": "VND"},
                       "POST", "/costs", "create-rev-behavior", "maker", {"finance_creator"})
    submit_cost(db_session, cost.id, 1, "POST", f"/costs/{cost.id}/submit", "submit-rev-behavior",
                "maker", {"finance_creator"})
    approve_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/approve", "approve-rev-behavior",
                 "checker", {"finance_approver"})
    payload = {"expected_version": 3, "reason": "Correction"}
    reversal = reverse_cost(db_session, cost.id, payload, "POST", f"/costs/{cost.id}/reverse",
                            "reverse-replay", "poster", {"finance_poster"})
    replay = reverse_cost(db_session, cost.id, payload, "POST", f"/costs/{cost.id}/reverse",
                          "reverse-replay", "poster", {"finance_poster"})
    assert replay.id == reversal.id
    with pytest.raises(Exception) as reused:
        reverse_cost(db_session, cost.id, {**payload, "reason": "Different"}, "POST",
                     f"/costs/{cost.id}/reverse", "reverse-replay", "poster", {"finance_poster"})
    assert reused.value.code == "IDEMPOTENCY_KEY_REUSED"
    with pytest.raises(Exception) as double:
        reverse_cost(db_session, cost.id, {"expected_version": 4, "reason": "Again"}, "POST",
                     f"/costs/{cost.id}/reverse", "reverse-again", "poster", {"finance_poster"})
    assert double.value.code == "COST_REVERSAL_INVALID"
    with pytest.raises(Exception) as cycle:
        reverse_cost(db_session, reversal.id, {"expected_version": 1, "reason": "Cycle"}, "POST",
                     f"/costs/{reversal.id}/reverse", "reverse-cycle", "poster", {"finance_poster"})
    assert cycle.value.code == "COST_REVERSAL_INVALID"


def test_cost_document_rejects_traversal_credentials_ports_hosts_and_bad_checksum(db_session, monkeypatch):
    from services.tms_cost_service import _validated_document_identity

    monkeypatch.setenv("FINANCE_DOCUMENT_HTTPS_HOSTS", "files.example")
    valid_checksum = "sha256:" + "a" * 64
    assert _validated_document_identity({"storage_url": "/uploads/folder/a.pdf", "checksum": valid_checksum}) == (
        "/uploads/folder/a.pdf", valid_checksum)
    assert _validated_document_identity({"storage_url": "https://files.example/a.pdf", "checksum": valid_checksum})[0] == "https://files.example/a.pdf"
    for url, checksum in (
        ("/uploads/../secret", valid_checksum), ("/uploads/%2e%2e/secret", valid_checksum),
        ("/uploads/a\\b", valid_checksum), ("/uploads/a%5cb", valid_checksum),
        ("/uploads/a\x00b", valid_checksum), ("/uploads/a%00b", valid_checksum),
        ("https://evil.example/a", valid_checksum), ("https://u:p@files.example/a", valid_checksum),
        ("https://files.example:444/a", valid_checksum), ("/uploads/a", "abc"),
    ):
        with pytest.raises(Exception) as caught:
            _validated_document_identity({"storage_url": url, "checksum": checksum})
        assert caught.value.code == "COST_DOCUMENT_INVALID"

    for url in ("https://files.example:not-a-port/a", "https://files.example:99999/a"):
        with pytest.raises(Exception) as malformed:
            _validated_document_identity({"storage_url": url, "checksum": valid_checksum})
        assert malformed.value.code == "DOCUMENT_URL_INVALID"


@pytest.mark.parametrize("value", [None, True, False, 0, -1, "1", 1.0])
def test_cost_all_transitions_reject_invalid_expected_version(db_session, value):
    from services.tms_cost_service import _expected_version

    with pytest.raises(Exception) as caught:
        _expected_version(value)
    assert caught.value.code == "EXPECTED_VERSION_INVALID"


def test_cost_corrupt_idempotency_replay_is_stable_domain_error(db_session):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, IdempotencyRecord
    from services.tms_cost_service import _canonical_hash, create_cost

    order = _delivered_order(db_session)
    db_session.add_all([CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True)])
    payload = {"freight_order_id": order.id, "id": "C-CORRUPT", "carrier_id": "INTERNAL", "currency_code": "VND"}
    db_session.add(IdempotencyRecord(actor="maker", method="POST", path="/costs",
        idempotency_key="corrupt", operation="POST:/costs:maker", request_hash=_canonical_hash(payload),
        response_json="null"))
    db_session.flush()
    with pytest.raises(Exception) as caught:
        create_cost(db_session, order.id, {"id": "C-CORRUPT", "carrier_id": "INTERNAL", "currency_code": "VND"},
                    "POST", "/costs", "corrupt", "maker", {"finance_creator"})
    assert caught.value.code == "IDEMPOTENCY_RECORD_CORRUPT" and caught.value.status_code == 409


def _approved_cost_for_ap(db_session, suffix="1"):
    from models import Carrier, CurrencyDefinition, FinanceControlConfig, TaxCode
    from services.tms_cost_service import approve_cost, create_cost, save_charge_item, submit_cost

    order = _delivered_order(db_session, suffix=f"-AP-{suffix}")
    if db_session.get(CurrencyDefinition, "VND") is None:
        db_session.add(CurrencyDefinition(code="VND", minor_units=0))
    if db_session.get(FinanceControlConfig, "GLOBAL") is None:
        db_session.add(FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
    if db_session.scalar(select(TaxCode).where(TaxCode.code == "VAT10", TaxCode.effective_from == dt.date(2020, 1, 1))) is None:
        db_session.add(TaxCode(code="VAT10", effective_from=dt.date(2020, 1, 1), rate=Decimal("0.10"), mode="exclusive"))
    db_session.add(Carrier(id=f"CAR-{suffix}", name=f"Carrier {suffix}", tax_code=f"TAX-{suffix}", is_internal=True))
    db_session.flush()
    cost = create_cost(db_session, order.id, {"id": f"COST-AP-{suffix}", "carrier_id": f"CAR-{suffix}", "currency_code": "VND"},
                       "POST", "/costs", f"cost-{suffix}", "maker", {"finance_creator"})
    save_charge_item(db_session, cost.id, {"id": f"ITEM-AP-{suffix}", "charge_type": "toll", "quantity": "2",
        "unit_price": "100", "tax_code": "VAT10", "tax_mode": "exclusive"}, 1, "POST",
        f"/costs/{cost.id}/items", f"item-{suffix}", "maker", {"finance_creator"})
    submit_cost(db_session, cost.id, 2, "POST", f"/costs/{cost.id}/submit", f"submit-{suffix}", "maker", {"finance_creator"})
    approve_cost(db_session, cost.id, 3, "POST", f"/costs/{cost.id}/approve", f"approve-{suffix}", "checker", {"finance_approver"})
    return cost


def test_ap_create_snapshots_approved_cost_and_normalizes_vendor_number(db_session):
    from models import APInvoice
    from services.tms_ap_service import create_ap_from_cost

    cost = _approved_cost_for_ap(db_session, "CREATE")
    ap = create_ap_from_cost(db_session, cost.id, {"vendor_invoice_no": "  vn  001 ",
        "invoice_date": "2026-08-10", "due_date": "2026-09-10"}, "POST", "/ap-invoices",
        "ap-create", "ap-maker", {"finance_creator"})
    db_session.flush()
    assert isinstance(ap, APInvoice)
    assert (ap.normalized_vendor_invoice_no, ap.carrier_name_snapshot, ap.carrier_tax_code_snapshot) == ("VN 001", "Carrier CREATE", "TAX-CREATE")
    assert (ap.subtotal_amount, ap.tax_amount, ap.total_amount) == (Decimal("200"), Decimal("20"), Decimal("220"))
    assert ap.functional_total_amount == Decimal("220")
    assert len(ap.lines) == 1 and ap.lines[0].charge_item_id == "ITEM-AP-CREATE"


def test_ap_lifecycle_permissions_sod_period_and_posting_seam(db_session):
    from models import AccountMapping, AccountingPeriod
    from services.tms_ap_service import create_ap_from_cost, transition_ap

    cost = _approved_cost_for_ap(db_session, "FLOW")
    ap = create_ap_from_cost(db_session, cost.id, {"vendor_invoice_no": "FLOW-1", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", "flow-create", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "submit", 1, "POST", f"/ap-invoices/{ap.id}/submit", "flow-submit", "ap-maker", {"finance_creator"})
    with pytest.raises(Exception) as sod:
        transition_ap(db_session, ap.id, "approve", 2, "POST", f"/ap-invoices/{ap.id}/approve", "flow-sod", "ap-maker", {"finance_approver"})
    assert sod.value.code == "SEPARATION_OF_DUTIES"
    transition_ap(db_session, ap.id, "approve", 2, "POST", f"/ap-invoices/{ap.id}/approve", "flow-approve", "checker", {"finance_approver"})
    with pytest.raises(Exception) as missing_period:
        transition_ap(db_session, ap.id, "post", 3, "POST", f"/ap-invoices/{ap.id}/post", "flow-post-missing", "poster", {"finance_poster"})
    assert missing_period.value.navigation_targets == ["master-data/accounting-periods"]
    db_session.add(AccountingPeriod(id="2026-08", starts_at=dt.datetime(2026, 8, 1), ends_at=dt.datetime(2026, 8, 31, 23, 59), status="open"))
    db_session.add_all([AccountMapping(mapping_key="carrier_expense:toll", account_code="642"),
        AccountMapping(mapping_key="input_tax", account_code="133"), AccountMapping(mapping_key="accounts_payable", account_code="331")])
    db_session.info["ap_post_callback"] = lambda invoice: f"J-{invoice.id}"
    posted = transition_ap(db_session, ap.id, "post", 3, "POST", f"/ap-invoices/{ap.id}/post", "flow-post", "poster", {"finance_poster"})
    assert posted.status == "posted" and posted.posting_reference == f"J-{ap.id}"


def test_ap_reversal_is_negative_single_and_blocks_cost_reversal(db_session):
    from models import AccountMapping, AccountingPeriod
    from services.tms_ap_service import create_ap_from_cost, reverse_ap, transition_ap
    from services.tms_cost_service import reverse_cost

    cost = _approved_cost_for_ap(db_session, "REV")
    ap = create_ap_from_cost(db_session, cost.id, {"vendor_invoice_no": "REV-1", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", "rev-create", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "submit", 1, "POST", f"/ap-invoices/{ap.id}/submit", "rev-submit", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "approve", 2, "POST", f"/ap-invoices/{ap.id}/approve", "rev-approve", "checker", {"finance_approver"})
    db_session.add(AccountingPeriod(id="2026-08", starts_at=dt.datetime(2026, 8, 1), ends_at=dt.datetime(2026, 8, 31, 23, 59), status="open"))
    db_session.add_all([AccountMapping(mapping_key="carrier_expense:toll", account_code="642"),
        AccountMapping(mapping_key="input_tax", account_code="133"), AccountMapping(mapping_key="accounts_payable", account_code="331")])
    db_session.info["ap_post_callback"] = lambda invoice: f"J-{invoice.id}"
    transition_ap(db_session, ap.id, "post", 3, "POST", f"/ap-invoices/{ap.id}/post", "rev-post", "poster", {"finance_poster"})
    with pytest.raises(Exception) as blocked:
        reverse_cost(db_session, cost.id, {"expected_version": 4, "reason": "wrong order"}, "POST", f"/costs/{cost.id}/reverse", "cost-rev-blocked", "poster", {"finance_poster"})
    assert blocked.value.code == "COST_HAS_ACTIVE_AP"
    credit = reverse_ap(db_session, ap.id, {"expected_version": 4, "reason": "carrier correction", "reversal_date": "2026-08-10"},
        "POST", f"/ap-invoices/{ap.id}/reverse", "ap-reverse", "poster", {"finance_poster"})
    assert credit.document_kind == "credit_memo" and credit.total_amount == Decimal("-220")
    with pytest.raises(Exception) as cycle:
        reverse_ap(db_session, credit.id, {"expected_version": 1, "reason": "cycle"}, "POST", f"/ap-invoices/{credit.id}/reverse", "ap-cycle", "poster", {"finance_poster"})
    assert cycle.value.code == "AP_REVERSAL_INVALID"


def test_ap_expected_version_is_validated_for_all_transitions(db_session):
    from services.tms_ap_service import create_ap_from_cost, reverse_ap, transition_ap

    cost = _approved_cost_for_ap(db_session, "VERSION")
    ap = create_ap_from_cost(db_session, cost.id, {"vendor_invoice_no": "VER-1", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", "ver-create", "ap-maker", {"finance_creator"})

    for command in (
        lambda: transition_ap(db_session, ap.id, "submit", True, "POST", f"/ap-invoices/{ap.id}/submit", "ver-submit", "ap-maker", {"finance_creator"}),
        lambda: reverse_ap(db_session, ap.id, {"expected_version": "1", "reason": "Sai"}, "POST", f"/ap-invoices/{ap.id}/reverse", "ver-reverse", "poster", {"finance_poster"}),
    ):
        with pytest.raises(Exception) as caught:
            command()
        assert caught.value.code == "EXPECTED_VERSION_INVALID"


def test_ap_duplicate_vendor_and_active_cost_conflicts_leave_session_usable(db_session):
    from services.tms_ap_service import create_ap_from_cost

    cost_one = _approved_cost_for_ap(db_session, "DUP1")
    first = create_ap_from_cost(db_session, cost_one.id, {"vendor_invoice_no": "dup-001", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", "dup-create-1", "ap-maker", {"finance_creator"})
    db_session.flush()

    with pytest.raises(Exception) as active_cost:
        create_ap_from_cost(db_session, cost_one.id, {"vendor_invoice_no": "dup-002", "invoice_date": "2026-08-10"},
            "POST", "/ap-invoices", "dup-create-2", "ap-maker", {"finance_creator"})
    assert active_cost.value.code == "AP_DUPLICATE"
    assert db_session.get(type(first), first.id).id == first.id

    cost_two = _approved_cost_for_ap(db_session, "DUP2")
    cost_two.carrier_id = cost_one.carrier_id
    db_session.flush()
    with pytest.raises(Exception) as vendor_dup:
        create_ap_from_cost(db_session, cost_two.id, {"vendor_invoice_no": "  DUP-001  ", "invoice_date": "2026-08-10"},
            "POST", "/ap-invoices", "dup-create-3", "ap-maker", {"finance_creator"})
    assert vendor_dup.value.code == "AP_DUPLICATE"
    assert create_ap_from_cost(db_session, cost_two.id, {"vendor_invoice_no": "dup-003", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", "dup-create-4", "ap-maker", {"finance_creator"}).status == "draft"


def test_ap_posting_service_unavailable_does_not_mutate_state_or_idempotency(db_session):
    from models import APInvoice, AccountMapping, AccountingPeriod, AuditLog, IdempotencyRecord
    from services.tms_ap_service import create_ap_from_cost, transition_ap

    cost = _approved_cost_for_ap(db_session, "POSTFAIL")
    ap = create_ap_from_cost(db_session, cost.id, {"vendor_invoice_no": "POSTFAIL-1", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", "postfail-create", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "submit", 1, "POST", f"/ap-invoices/{ap.id}/submit", "postfail-submit", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "approve", 2, "POST", f"/ap-invoices/{ap.id}/approve", "postfail-approve", "checker", {"finance_approver"})
    db_session.add(AccountingPeriod(id="2026-08", starts_at=dt.datetime(2026, 8, 1), ends_at=dt.datetime(2026, 8, 31, 23, 59), status="open"))
    db_session.add_all([AccountMapping(mapping_key="carrier_expense:toll", account_code="642"),
        AccountMapping(mapping_key="input_tax", account_code="133"), AccountMapping(mapping_key="accounts_payable", account_code="331")])

    with pytest.raises(Exception) as unavailable:
        transition_ap(db_session, ap.id, "post", 3, "POST", f"/ap-invoices/{ap.id}/post", "postfail-post", "poster", {"finance_poster"})
    assert unavailable.value.code == "AP_POSTING_SERVICE_UNAVAILABLE"
    assert (ap.status, ap.version, ap.posted_by, ap.posted_at) == ("approved", 3, None, None)
    assert db_session.get(APInvoice, ap.id).status == "approved"
    assert db_session.query(AuditLog).filter_by(action="POST_AP_INVOICE", record_id=ap.id).count() == 0
    assert db_session.query(IdempotencyRecord).filter_by(idempotency_key="postfail-post").count() == 0


def _approved_ap_for_journal(db_session, suffix="JOURNAL", expense_account="642", tax_account="133", payable_account="331"):
    from models import AccountMapping, AccountingPeriod
    from services.tms_ap_service import create_ap_from_cost, transition_ap

    cost = _approved_cost_for_ap(db_session, suffix)
    ap = create_ap_from_cost(db_session, cost.id, {"vendor_invoice_no": f"{suffix}-1", "invoice_date": "2026-08-10"},
        "POST", "/ap-invoices", f"{suffix}-create", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "submit", 1, "POST", f"/ap-invoices/{ap.id}/submit", f"{suffix}-submit", "ap-maker", {"finance_creator"})
    transition_ap(db_session, ap.id, "approve", 2, "POST", f"/ap-invoices/{ap.id}/approve", f"{suffix}-approve", "checker", {"finance_approver"})
    db_session.add(AccountingPeriod(id=f"{suffix}-2026-08", starts_at=dt.datetime(2026, 8, 1), ends_at=dt.datetime(2026, 8, 31, 23, 59), status="open"))
    db_session.add_all([AccountMapping(mapping_key="carrier_expense:toll", account_code=expense_account),
        AccountMapping(mapping_key="input_tax", account_code=tax_account), AccountMapping(mapping_key="accounts_payable", account_code=payable_account)])
    db_session.info["ap_post_callback"] = lambda invoice: f"J-{invoice.id}"
    transition_ap(db_session, ap.id, "post", 3, "POST", f"/ap-invoices/{ap.id}/post", f"{suffix}-post", "poster", {"finance_poster"})
    return ap


def test_journal_model_supports_multi_source_and_functional_amount_columns(db_session):
    from models import JournalBatch, JournalLine, MONEY_TYPE, RATE_TYPE

    assert JournalBatch.__table__.c.invoice_id.nullable is True
    assert {"source_type", "source_id"} <= set(JournalBatch.__table__.c.keys())
    assert JournalLine.__table__.c.transaction_amount.type is MONEY_TYPE
    assert JournalLine.__table__.c.exchange_rate.type is RATE_TYPE
    assert JournalLine.__table__.c.functional_debit.type is MONEY_TYPE
    assert JournalLine.__table__.c.functional_credit.type is MONEY_TYPE


def test_journal_posts_ap_invoice_balanced_and_exactly_once(db_session):
    from models import AuditLog, JournalBatch, JournalLine
    from services.tms_journal_service import post_ap_journal

    ap = _approved_ap_for_journal(db_session, "JOURNAL")
    batch = post_ap_journal(db_session, ap.id, "POST", f"/ap-invoices/{ap.id}/journal", "journal-key", "poster", {"finance_poster"})
    replay = post_ap_journal(db_session, ap.id, "POST", f"/ap-invoices/{ap.id}/journal", "journal-key", "poster", {"finance_poster"})

    assert replay.id == batch.id
    assert (batch.source_type, batch.source_id, batch.invoice_id, batch.status) == ("ap_invoice", ap.id, None, "posted")
    lines = db_session.query(JournalLine).filter_by(batch_id=batch.id).order_by(JournalLine.account_code).all()
    assert [(line.account_code, line.functional_debit, line.functional_credit) for line in lines] == [
        ("133", Decimal("20"), Decimal("0")),
        ("331", Decimal("0"), Decimal("220")),
        ("642", Decimal("200"), Decimal("0")),
    ]
    assert sum(line.functional_debit for line in lines) == sum(line.functional_credit for line in lines)
    assert db_session.query(JournalBatch).filter_by(source_type="ap_invoice", source_id=ap.id).count() == 1
    assert db_session.query(AuditLog).filter_by(action="POST_AP_JOURNAL", record_id=batch.id).count() == 1


def test_journal_uses_account_mapping_not_hardcoded_accounts(db_session):
    from models import JournalLine
    from services.tms_journal_service import post_ap_journal

    ap = _approved_ap_for_journal(db_session, "JMAP", expense_account="6418", tax_account="1338", payable_account="3318")
    batch = post_ap_journal(db_session, ap.id, "POST", f"/ap-invoices/{ap.id}/journal", "journal-map", "poster", {"finance_poster"})
    assert [line.account_code for line in db_session.query(JournalLine).filter_by(batch_id=batch.id).order_by(JournalLine.account_code)] == [
        "1338", "3318", "6418"
    ]


def test_settlement_create_and_partial_full_payment_journal(db_session):
    from models import AccountMapping, FreightSettlement, JournalBatch, JournalLine, SettlementPayment
    from services.tms_settlement_service import create_settlement, post_payment

    ap = _approved_ap_for_journal(db_session, "SETTLE")
    db_session.add(AccountMapping(mapping_key="bank:cash", account_code="112"))
    settlement = create_settlement(db_session, ap.id, {"id": "SET-1", "settlement_period": "2026-08"},
        "POST", f"/ap-invoices/{ap.id}/settlements", "settle-create", "settler", {"finance_payment"})
    assert isinstance(settlement, FreightSettlement)
    assert (settlement.approved_amount, settlement.paid_amount, settlement.remaining_amount, settlement.status) == (
        Decimal("220"), Decimal("0"), Decimal("220"), "open")

    first = post_payment(db_session, settlement.id, {"id": "PAY-1", "amount": "100", "payment_method": "cash",
        "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "pay-1",
        "cashier", {"finance_payment"})
    assert isinstance(first, SettlementPayment)
    assert (settlement.paid_amount, settlement.remaining_amount, settlement.status, settlement.version) == (
        Decimal("100"), Decimal("120"), "partially_paid", 2)
    batch = db_session.get(JournalBatch, first.posting_reference)
    assert (batch.source_type, batch.source_id) == ("ap_payment", first.id)
    assert [(line.account_code, line.functional_debit, line.functional_credit) for line in db_session.query(JournalLine).filter_by(batch_id=batch.id).order_by(JournalLine.account_code)] == [
        ("112", Decimal("0"), Decimal("100")),
        ("331", Decimal("100"), Decimal("0")),
    ]

    post_payment(db_session, settlement.id, {"id": "PAY-2", "amount": "120", "payment_method": "cash",
        "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "pay-2",
        "cashier", {"finance_payment"})
    assert (settlement.paid_amount, settlement.remaining_amount, settlement.status) == (Decimal("220"), Decimal("0"), "paid")


def test_settlement_rejects_overpayment_wrong_currency_and_replays_payment(db_session):
    from models import AccountMapping
    from services.tms_settlement_service import create_settlement, post_payment

    ap = _approved_ap_for_journal(db_session, "SETTLE-ERR")
    db_session.add(AccountMapping(mapping_key="bank:cash", account_code="112"))
    settlement = create_settlement(db_session, ap.id, {}, "POST", f"/ap-invoices/{ap.id}/settlements",
        "settle-err-create", "settler", {"finance_payment"})

    first = post_payment(db_session, settlement.id, {"id": "PAY-REPLAY", "amount": "50", "payment_method": "cash",
        "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "same-pay",
        "cashier", {"finance_payment"})
    assert post_payment(db_session, settlement.id, {"id": "PAY-REPLAY", "amount": "50", "payment_method": "cash",
        "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "same-pay",
        "cashier", {"finance_payment"}).id == first.id
    with pytest.raises(Exception) as reused:
        post_payment(db_session, settlement.id, {"id": "PAY-REPLAY", "amount": "51", "payment_method": "cash",
            "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "same-pay",
            "cashier", {"finance_payment"})
    assert reused.value.code == "IDEMPOTENCY_KEY_REUSED"
    with pytest.raises(Exception) as currency:
        post_payment(db_session, settlement.id, {"amount": "10", "currency_code": "USD", "payment_method": "cash",
            "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "wrong-currency",
            "cashier", {"finance_payment"})
    assert currency.value.code == "PAYMENT_CURRENCY_INVALID"
    with pytest.raises(Exception) as overpaid:
        post_payment(db_session, settlement.id, {"amount": "999", "payment_method": "cash",
            "posting_date": "2026-08-10"}, "POST", f"/settlements/{settlement.id}/payments", "overpaid",
            "cashier", {"finance_payment"})
    assert overpaid.value.code == "PAYMENT_OVER_AMOUNT"


def test_payment_reverse_restores_settlement_and_posts_reversal_journal(db_session):
    from models import AccountMapping, JournalBatch, SettlementPayment
    from services.tms_settlement_service import create_settlement, post_payment, reverse_payment

    ap = _approved_ap_for_journal(db_session, "PAYREV")
    db_session.add(AccountMapping(mapping_key="bank:cash", account_code="111"))
    db_session.flush()
    settlement = create_settlement(db_session, ap.id, {"id": "SET-REV"}, "POST",
        f"/ap-invoices/{ap.id}/settlements", "set-rev", "payer", {"finance_payment"})
    payment = post_payment(db_session, settlement.id, {"id": "PAY-REV", "amount": "70",
        "payment_method": "cash", "posting_date": "2026-08-10"}, "POST",
        f"/settlements/{settlement.id}/payments", "pay-rev", "payer", {"finance_payment"})

    reversal = reverse_payment(db_session, payment.id, {"id": "PAY-REV-R", "reason": "Sai chứng từ"},
        "POST", f"/settlement-payments/{payment.id}/reverse", "reverse-pay", "payer", {"finance_payment"})

    assert isinstance(reversal, SettlementPayment)
    assert reversal.reversal_of_payment_id == payment.id
    assert payment.status == "reversed"
    assert settlement.status == "open"
    assert settlement.paid_amount == Decimal("0")
    assert db_session.query(JournalBatch).filter_by(source_type="payment_reversal", source_id=reversal.id).one()


def test_payment_uses_rate_history_and_posts_realized_fx_gain(db_session):
    from models import AccountMapping, CurrencyDefinition, CurrencyRateHistory, JournalLine
    from services.tms_settlement_service import create_settlement, post_payment

    ap = _approved_ap_for_journal(db_session, "FXGAIN")
    if db_session.get(CurrencyDefinition, "USD") is None:
        db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.add(CurrencyRateHistory(currency_code="USD", functional_currency="VND",
        rate_date=dt.date(2026, 8, 10), rate=Decimal("25000"), source="BANK"))
    db_session.add_all([
        AccountMapping(mapping_key="bank:cash", account_code="111"),
        AccountMapping(mapping_key="fx_gain", account_code="515"),
        AccountMapping(mapping_key="fx_loss", account_code="635"),
    ])
    db_session.flush()
    ap.currency_code = "USD"
    ap.functional_currency = "VND"
    ap.exchange_rate_snapshot = Decimal("26000")
    ap.total_amount = Decimal("220")
    ap.functional_total_amount = Decimal("5720000")
    db_session.flush()
    settlement = create_settlement(db_session, ap.id, {"id": "SET-FX"}, "POST",
        f"/ap-invoices/{ap.id}/settlements", "set-fx", "payer", {"finance_payment"})

    payment = post_payment(db_session, settlement.id, {"id": "PAY-FX", "amount": "100",
        "payment_method": "cash", "posting_date": "2026-08-10"}, "POST",
        f"/settlements/{settlement.id}/payments", "pay-fx", "payer", {"finance_payment"})

    assert payment.exchange_rate_snapshot == Decimal("25000.00000000")
    lines = {(line.account_code, Decimal(line.functional_debit), Decimal(line.functional_credit))
             for line in db_session.query(JournalLine).filter_by(batch_id=payment.posting_reference)}
    assert ("331", Decimal("2600000"), Decimal("0")) in lines
    assert ("111", Decimal("0"), Decimal("2500000")) in lines
    assert ("515", Decimal("0"), Decimal("100000")) in lines


def test_payment_posts_realized_fx_loss_when_payment_rate_is_higher(db_session):
    from models import AccountMapping, CurrencyDefinition, CurrencyRateHistory, JournalLine
    from services.tms_settlement_service import create_settlement, post_payment

    ap = _approved_ap_for_journal(db_session, "FXLOSS")
    if db_session.get(CurrencyDefinition, "USD") is None:
        db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.add(CurrencyRateHistory(currency_code="USD", functional_currency="VND",
        rate_date=dt.date(2026, 8, 10), rate=Decimal("27000"), source="BANK"))
    db_session.add_all([
        AccountMapping(mapping_key="bank:cash", account_code="111"),
        AccountMapping(mapping_key="fx_gain", account_code="515"),
        AccountMapping(mapping_key="fx_loss", account_code="635"),
    ])
    db_session.flush()
    ap.currency_code = "USD"
    ap.functional_currency = "VND"
    ap.exchange_rate_snapshot = Decimal("26000")
    ap.total_amount = Decimal("220")
    ap.functional_total_amount = Decimal("5720000")
    db_session.flush()
    settlement = create_settlement(db_session, ap.id, {"id": "SET-FX-LOSS"}, "POST",
        f"/ap-invoices/{ap.id}/settlements", "set-fx-loss", "payer", {"finance_payment"})

    payment = post_payment(db_session, settlement.id, {"id": "PAY-FX-LOSS", "amount": "100",
        "payment_method": "cash", "posting_date": "2026-08-10"}, "POST",
        f"/settlements/{settlement.id}/payments", "pay-fx-loss", "payer", {"finance_payment"})

    lines = {(line.account_code, Decimal(line.functional_debit), Decimal(line.functional_credit))
             for line in db_session.query(JournalLine).filter_by(batch_id=payment.posting_reference)}
    assert ("331", Decimal("2600000"), Decimal("0")) in lines
    assert ("111", Decimal("0"), Decimal("2700000")) in lines
    assert ("635", Decimal("100000"), Decimal("0")) in lines


def test_payment_reversal_reverses_ap_carrying_amount_and_realized_fx(db_session):
    from models import AccountMapping, CurrencyDefinition, CurrencyRateHistory, JournalLine
    from services.tms_settlement_service import create_settlement, post_payment, reverse_payment

    ap = _approved_ap_for_journal(db_session, "FXREV")
    if db_session.get(CurrencyDefinition, "USD") is None:
        db_session.add(CurrencyDefinition(code="USD", minor_units=2))
    db_session.add(CurrencyRateHistory(currency_code="USD", functional_currency="VND",
        rate_date=dt.date(2026, 8, 10), rate=Decimal("25000"), source="BANK"))
    db_session.add_all([
        AccountMapping(mapping_key="bank:cash", account_code="111"),
        AccountMapping(mapping_key="fx_gain", account_code="515"),
        AccountMapping(mapping_key="fx_loss", account_code="635"),
    ])
    db_session.flush()
    ap.currency_code = "USD"
    ap.functional_currency = "VND"
    ap.exchange_rate_snapshot = Decimal("26000")
    ap.total_amount = Decimal("220")
    ap.functional_total_amount = Decimal("5720000")
    db_session.flush()
    settlement = create_settlement(db_session, ap.id, {"id": "SET-FX-REV"}, "POST",
        f"/ap-invoices/{ap.id}/settlements", "set-fx-rev", "payer", {"finance_payment"})
    payment = post_payment(db_session, settlement.id, {"id": "PAY-FX-REV", "amount": "100",
        "payment_method": "cash", "posting_date": "2026-08-10"}, "POST",
        f"/settlements/{settlement.id}/payments", "pay-fx-rev", "payer", {"finance_payment"})

    reversal = reverse_payment(db_session, payment.id, {"id": "PAY-FX-REV-R", "reason": "Sai tỷ giá"},
        "POST", f"/settlement-payments/{payment.id}/reverse", "reverse-fx-payment", "payer", {"finance_payment"})

    lines = {(line.account_code, Decimal(line.functional_debit), Decimal(line.functional_credit))
             for line in db_session.query(JournalLine).filter_by(batch_id=reversal.posting_reference)}
    assert ("111", Decimal("2500000"), Decimal("0")) in lines
    assert ("331", Decimal("0"), Decimal("2600000")) in lines
    assert ("515", Decimal("100000"), Decimal("0")) in lines


def test_payment_rejects_closed_or_missing_accounting_period(db_session):
    from models import AccountMapping, AccountingPeriod
    from services.tms_settlement_service import create_settlement, post_payment

    ap = _approved_ap_for_journal(db_session, "PAYCLOSED")
    db_session.add(AccountMapping(mapping_key="bank:cash", account_code="111"))
    db_session.add(AccountingPeriod(id="CLOSED-2026-09", starts_at=dt.datetime(2026, 9, 1),
        ends_at=dt.datetime(2026, 9, 30, 23, 59), status="closed"))
    settlement = create_settlement(db_session, ap.id, {"id": "SET-CLOSED"}, "POST",
        f"/ap-invoices/{ap.id}/settlements", "set-closed", "payer", {"finance_payment"})

    with pytest.raises(Exception) as caught:
        post_payment(db_session, settlement.id, {"id": "PAY-CLOSED", "amount": "10",
            "payment_method": "cash", "posting_date": "2026-09-10"}, "POST",
            f"/settlements/{settlement.id}/payments", "pay-closed", "payer", {"finance_payment"})
    assert caught.value.code == "MISSING_OPEN_ACCOUNTING_PERIOD"
    assert caught.value.navigation_targets == ["master-data/accounting-periods"]


def test_finance_api_auth_permissions_and_payment_flow(db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import database
    from models import AccountMapping, Role, User
    from routes.tms_finance_routes import router

    ap = _approved_ap_for_journal(db_session, "API")
    db_session.add_all([
        AccountMapping(mapping_key="bank:cash", account_code="111"),
        Role(id="PAYMENT", permissions='["finance_read","finance_payment"]'),
        Role(id="READONLY", permissions='["finance_read"]'),
        User(id="payer", username="payer", role_id="PAYMENT"),
        User(id="viewer", username="viewer", role_id="READONLY"),
    ])
    db_session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[database.get_db] = lambda: db_session

    @app.middleware("http")
    async def principal(request, call_next):
        if request.headers.get("X-Test-Principal"):
            request.state.principal = request.headers["X-Test-Principal"]
        return await call_next(request)

    client = TestClient(app)
    assert client.get("/api/tms/finance/settlements").status_code == 401
    denied = client.post(f"/api/tms/finance/ap-invoices/{ap.id}/settlements",
        json={}, headers={"X-Test-Principal": "viewer", "Idempotency-Key": "api-denied"})
    assert denied.status_code == 403
    created = client.post(f"/api/tms/finance/ap-invoices/{ap.id}/settlements",
        json={"id": "SET-API"}, headers={"X-Test-Principal": "payer", "Idempotency-Key": "api-set"})
    assert created.status_code == 200
    assert created.json()["data"]["id"] == "SET-API"
    paid = client.post("/api/tms/finance/settlements/SET-API/payments",
        json={"id": "PAY-API", "amount": "10", "payment_method": "cash", "posting_date": "2026-08-10"},
        headers={"X-Test-Principal": "payer", "Idempotency-Key": "api-pay"})
    assert paid.status_code == 200
    reversed_payment = client.post("/api/tms/finance/settlement-payments/PAY-API/reverse",
        json={"id": "PAY-API-R", "reason": "Khách yêu cầu đối soát lại"},
        headers={"X-Test-Principal": "payer", "Idempotency-Key": "api-pay-r"})
    assert reversed_payment.status_code == 200
    assert reversed_payment.json()["data"]["reversal_of_payment_id"] == "PAY-API"


def test_finance_permission_resolver_fails_closed_for_bad_role_json(db_session):
    from models import Role, User
    from services.finance_authorization import resolve_finance_context

    db_session.add_all([
        Role(id="BROKEN", permissions="{not-json"),
        User(id="broken", username="broken", role_id="BROKEN"),
    ])
    db_session.flush()
    with pytest.raises(Exception) as caught:
        resolve_finance_context(db_session, "broken", {"finance_read"})
    assert caught.value.code == "FINANCE_PERMISSION_INVALID"
