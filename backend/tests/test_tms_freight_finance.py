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


def test_cost_idempotency_scope_and_reversal_are_persisted(db_session):
    from models import IdempotencyRecord, FreightActualCost
    assert {"actor", "method", "path", "idempotency_key", "request_hash", "response_json"} <= set(IdempotencyRecord.__table__.c.keys())
    assert any(set(c.columns.keys()) == {"actor", "method", "path", "idempotency_key"} for c in IdempotencyRecord.__table__.constraints if hasattr(c, "columns"))
    assert FreightActualCost.__table__.c.version.type.python_type is int


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


def _concurrent_cost_database(may_kiem):
    import models

    engine = may_kiem()
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    seed = sessions()
    order = _delivered_order(seed)
    from models import Carrier, CurrencyDefinition, FinanceControlConfig
    seed.add_all([
        CurrencyDefinition(code="VND", minor_units=0),
        FinanceControlConfig(id="GLOBAL", functional_currency="VND"),
        Carrier(id="INTERNAL", name="Internal", is_internal=True),
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
    from models import Carrier, CurrencyDefinition, FinanceControlConfig
    from services.tms_cost_service import approve_cost, create_cost, save_charge_item, submit_cost

    order = _delivered_order(db_session, suffix=f"-AP-{suffix}")
    if db_session.get(CurrencyDefinition, "VND") is None:
        db_session.add(CurrencyDefinition(code="VND", minor_units=0))
    if db_session.get(FinanceControlConfig, "GLOBAL") is None:
        db_session.add(FinanceControlConfig(id="GLOBAL", functional_currency="VND"))
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
