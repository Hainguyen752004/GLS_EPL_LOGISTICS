import datetime as dt
import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select

from models import (
    AuditLog,
    Carrier,
    CurrencyRateHistory,
    Customer,
    DeliveryOrder,
    DeliveryOrderCloseout,
    Driver,
    EPLExpenseVoucher,
    FinanceControlConfig,
    FreightActualCost,
    FreightOrder,
    Quotation,
    TransportTrip,
    TransportTripLeg,
    TripDeliveryOrder,
    Vehicle,
)
from services import tms_cost_service
from services.errors import DomainError, conflict
from services.tms_money import resolve_exchange_rate


REPORT_CURRENCIES = ("VND", "LAK", "THB", "USD", "CNY")


def _number(value):
    return float(value or 0)


def _cost_total(cost):
    """Use the header total, with a line-total fallback for legacy records."""
    header_total = Decimal(cost.total_amount or 0)
    if header_total != 0:
        return header_total
    return sum(
        ((Decimal(item.total_amount or 0) or Decimal(item.actual_amount or 0))
         + Decimal(item.rounding_adjustment or 0) for item in (cost.items or [])),
        Decimal("0"),
    )


def _date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return dt.date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _functional_config(db):
    config = db.get(FinanceControlConfig, "GLOBAL")
    if config is None:
        raise DomainError(
            "FINANCE_CONFIG_REQUIRED",
            "Chưa cấu hình tiền tệ chức năng cho báo cáo tài chính.",
            422,
        )
    return config.functional_currency


def _rate_to_functional(db, currency_code, functional_currency, recognition_date):
    if currency_code == functional_currency:
        return Decimal("1")
    return db.scalar(
        select(CurrencyRateHistory.rate)
        .where(
            CurrencyRateHistory.currency_code == currency_code,
            CurrencyRateHistory.functional_currency == functional_currency,
            CurrencyRateHistory.rate_date <= recognition_date,
            CurrencyRateHistory.is_active.is_(True),
        )
        .order_by(CurrencyRateHistory.rate_date.desc(), CurrencyRateHistory.id.desc())
        .limit(1)
    )


def _converted_totals(db, amount_functional, functional_currency, recognition_date):
    totals = {}
    missing = []
    for code in REPORT_CURRENCIES:
        rate = _rate_to_functional(db, code, functional_currency, recognition_date)
        if rate is None:
            totals[code] = None
            missing.append(f"exchange_rate_{code}")
        else:
            totals[code] = _number(Decimal(amount_functional) / Decimal(rate))
    return totals, missing


def _ho_so_hoan_tat(db, do_id):
    """Ho so hoan tat (closeout) cua DO — NGUON DOANH THU cua bao cao.

    Truoc day bao cao doc hoa don AR; module ke toan da xoa (10/09) nen doanh thu
    ghi nhan = gia ban cuoi chot luc hoan tat giao hang, dung con so ban giao cho
    he cong no. DO hoan thanh ma chua co ho so hoan tat thi la ngoai le, khong doan.
    """
    return db.scalar(select(DeliveryOrderCloseout).where(DeliveryOrderCloseout.do_id == do_id).limit(1))


def _ty_gia_ve_chuc_nang(db, currency_code, functional_currency, on_date, missing):
    """Ty gia quy doi ve tien te chuc nang; thieu thi ghi vao `missing` va dung 1."""
    if not currency_code or currency_code == functional_currency:
        return Decimal(1)
    try:
        return Decimal(resolve_exchange_rate(db, currency_code, functional_currency, on_date or dt.date.today()).rate)
    except DomainError:
        missing.append("exchange_rate_%s" % currency_code)
        return Decimal(1)


def _active_cost(db, trip_id):
    return db.scalar(
        select(FreightActualCost)
        .where(FreightActualCost.trip_id == trip_id, FreightActualCost.is_active.is_(True))
        .order_by(FreightActualCost.updated_at.desc())
        .limit(1)
    )


def _add_aggregate(bucket, label, revenue, cost):
    item = bucket[label]
    item["revenue"] += revenue
    item["cost"] += cost
    item["gross_profit"] += revenue - cost
    item["trip_count"] += 1


def get_transport_revenue(
    db,
    date_from=None,
    date_to=None,
    customer_id=None,
    vehicle_id=None,
    currency_code=None,
):
    functional_currency = _functional_config(db)
    links = db.execute(
        select(TripDeliveryOrder, TransportTrip, DeliveryOrder)
        .join(TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id)
        .join(DeliveryOrder, DeliveryOrder.id == TripDeliveryOrder.do_id)
        .where(TransportTrip.status.in_(("completed", "settled")))
        .order_by(TransportTrip.actual_departure_at, TripDeliveryOrder.allocation_sequence)
    ).all()

    rows = []
    exceptions = []
    trend = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0, "gross_profit": 0.0, "trip_count": 0})
    by_customer = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0, "gross_profit": 0.0, "trip_count": 0})
    by_route = defaultdict(lambda: {"revenue": 0.0, "cost": 0.0, "gross_profit": 0.0, "trip_count": 0})
    by_cargo = defaultdict(int)
    by_currency = defaultdict(float)

    for link, trip, delivery in links:
        if customer_id and delivery.customer_id != customer_id:
            continue
        if vehicle_id and trip.vehicle_id != vehicle_id:
            continue
        ho_so = _ho_so_hoan_tat(db, delivery.id)
        recognition_date = _date(ho_so.completed_at if ho_so else None) or _date(
            trip.actual_departure_at or trip.planned_departure_at or delivery.pickup_date
        )
        if date_from and (recognition_date is None or recognition_date < date_from):
            continue
        if date_to and (recognition_date is None or recognition_date > date_to):
            continue
        if ho_so is None:
            exceptions.append({
                "code": "CLOSEOUT_MISSING",
                "trip_id": trip.id,
                "do_id": delivery.id,
                "message": "DO đã hoàn thành nhưng chưa có hồ sơ hoàn tất (chốt giá).",
            })
            continue
        if currency_code and ho_so.currency_code != currency_code:
            continue

        customer = db.get(Customer, delivery.customer_id) if delivery.customer_id else None
        vehicle = db.get(Vehicle, trip.vehicle_id or delivery.vehicle_id) if (trip.vehicle_id or delivery.vehicle_id) else None
        driver = db.get(Driver, trip.driver_id or delivery.driver_id) if (trip.driver_id or delivery.driver_id) else None
        freight_order = db.get(FreightOrder, trip.freight_order_id)
        carrier = None
        cost = _active_cost(db, trip.id)
        if cost and cost.carrier_id:
            carrier = db.get(Carrier, cost.carrier_id)
        detail = None
        leg = db.scalar(
            select(TransportTripLeg)
            .where(TransportTripLeg.trip_id == trip.id, TransportTripLeg.do_id == delivery.id)
            .order_by(TransportTripLeg.sequence_no)
            .limit(1)
        )

        missing_fx = []
        ty_gia = _ty_gia_ve_chuc_nang(db, ho_so.currency_code, functional_currency, recognition_date, missing_fx)
        revenue = Decimal(ho_so.final_selling_price or 0) * ty_gia

        # GIÁ THÀNH CỦA MỘT CHUYẾN = GIÁ THÀNH KẾ HOẠCH + CHÊNH LỆCH ĐÃ DUYỆT.
        #
        # Trước đây cột này chỉ lấy `freight_actual_costs.total_amount`, và con
        # số đó KHÔNG phải tổng chi phí: bảng chi phí thực ghi từng dòng theo
        # `original` và `actual`, rồi cộng đúng phần VƯỢT
        # (`net_amount = increase`). Nó là một chứng từ CHÊNH LỆCH.
        #
        # Hệ quả đo được: một chuyến cước 2,2 triệu, giá thành kế hoạch 1,5
        # triệu, dầu vượt 5% -> bảng chênh lệch ghi 17.227 đ, và báo cáo kết
        # luận lãi gộp 99%. Với một báo giá biên 31% thì con số đó vô lý, và nó
        # là con số đầu tiên người xem báo cáo nhìn vào.
        #
        # Giá thành kế hoạch lấy từ BÁO GIÁ mà lệnh giao hàng kế thừa — đúng
        # con số công thức loại xe đã tính cho một chuyến, và cũng là con số
        # màn Báo giá đang hiện. Một chuyến = một DO, nên không phải chia.
        ke_hoach = Decimal("0")
        bao_gia = None
        if getattr(delivery, "quotation_id", None):
            bao_gia = db.get(Quotation, delivery.quotation_id)
        if bao_gia is not None:
            ke_hoach = Decimal(bao_gia.total_cost or 0)

        chenh_lech = Decimal("0")
        if cost is not None and cost.status == "approved":
            chenh_lech = _cost_total(cost) * Decimal(cost.exchange_rate_snapshot or 1)
        approved_cost = ke_hoach + chenh_lech
        totals, missing = _converted_totals(db, revenue, functional_currency, recognition_date)
        missing.extend(missing_fx)
        if vehicle is None:
            missing.append("tractor_plate")
        missing.append("trailer_plate")
        if not vehicle or not vehicle.engine_no:
            missing.append("vehicle_code")

        profit = revenue - approved_cost
        margin = (profit / revenue * Decimal("100")) if revenue else Decimal("0")
        cargo_type = (detail.description if detail else None) or (bao_gia.cargo_type if bao_gia is not None else None)
        origin = delivery.origin or (leg.origin if leg else None)
        destination = delivery.destination or (leg.destination if leg else None)
        customer_name = customer.name if customer else delivery.customer_id
        route_label = delivery.route_id or f"{origin} - {destination}"
        row = {
            "trip_id": trip.id,
            "do_id": delivery.id,
            "departure_date": _date(trip.actual_departure_at or trip.planned_departure_at),
            "dispatch_order_no": delivery.id,
            "recognition_date": recognition_date,
            "closeout_id": ho_so.id,
            "origin": origin,
            "destination": destination,
            "agency_company": carrier.name if carrier else None,
            "driver_name": driver.name if driver else None,
            "tractor_plate": vehicle.id if vehicle else None,
            "trailer_plate": None,
            "vehicle_code": vehicle.engine_no if vehicle else None,
            "customer_name": customer_name,
            "cargo_type": cargo_type,
            "trip_count": 1,
            "uom": detail.uom if detail else None,
            "weight_tons": round(_number(delivery.weight_kg or (freight_order.total_weight_kg if freight_order else 0)) / 1000, 3),
            "unit_prices": dict(totals),
            "totals": totals,
            "revenue_functional": _number(revenue),
            # BA CON SỐ, không gộp thành một: người đọc báo cáo cần biết chi phí
            # vượt kế hoạch bao nhiêu, và một cột tổng duy nhất che mất điều đó.
            "planned_cost_functional": _number(ke_hoach),
            "cost_variance_functional": _number(chenh_lech),
            "approved_cost_functional": _number(approved_cost),
            "gross_profit": _number(profit),
            "margin_percent": round(_number(margin), 2),
            "currency_code": ho_so.currency_code,
            "note": None,
            "missing_fields": sorted(set(missing)),
        }
        rows.append(row)
        date_key = recognition_date.isoformat() if recognition_date else "Chưa có ngày"
        _add_aggregate(trend, date_key, _number(revenue), _number(approved_cost))
        _add_aggregate(by_customer, customer_name or "Chưa có khách hàng", _number(revenue), _number(approved_cost))
        _add_aggregate(by_route, route_label or "Chưa có tuyến", _number(revenue), _number(approved_cost))
        by_cargo[cargo_type or "Chưa phân loại"] += 1
        by_currency[ho_so.currency_code] += _number(ho_so.final_selling_price)

    recognized_revenue = sum(row["revenue_functional"] for row in rows)
    approved_cost = sum(row["approved_cost_functional"] for row in rows)
    gross_profit = recognized_revenue - approved_cost
    margin_percent = round(gross_profit / recognized_revenue * 100, 2) if recognized_revenue else 0.0

    def aggregate_rows(source):
        return [{"label": label, **values} for label, values in source.items()]

    return {
        "summary": {
            "recognized_revenue": recognized_revenue,
            "approved_cost": approved_cost,
            "gross_profit": gross_profit,
            "margin_percent": margin_percent,
            "trip_count": len(rows),
            "currency_code": functional_currency,
        },
        "rows": rows,
        "charts": {
            "trend": aggregate_rows(trend),
            "by_customer": sorted(aggregate_rows(by_customer), key=lambda item: item["revenue"], reverse=True),
            "by_route": sorted(aggregate_rows(by_route), key=lambda item: item["revenue"], reverse=True),
            "by_cargo": [{"label": label, "value": value} for label, value in by_cargo.items()],
            "by_currency": [{"label": label, "value": value} for label, value in by_currency.items()],
        },
        "exceptions": exceptions,
    }


def save_expense_voucher(db, trip_id, data, method, path, key, actor, permissions):
    trip = db.get(TransportTrip, trip_id)
    if trip is None:
        raise DomainError("TRIP_NOT_FOUND", "Không tìm thấy chuyến vận tải.", 404)
    if data.get("do_id"):
        link = db.get(TripDeliveryOrder, (trip_id, data["do_id"]))
        if link is None:
            raise DomainError("DO_NOT_IN_TRIP", "DO không thuộc chuyến vận tải đã chọn.", 422)

    cost = db.scalar(select(FreightActualCost).where(
        FreightActualCost.trip_id == trip_id,
        FreightActualCost.is_active.is_(True),
    ))
    if cost is None or cost.status == "draft":
        cost_result = tms_cost_service.save_trip_cost_rows(
            db, trip_id, data, method, f"{path}/actual-cost", key, actor, permissions
        )
        cost = db.get(FreightActualCost, cost_result.id)
    voucher = db.scalar(select(EPLExpenseVoucher).where(EPLExpenseVoucher.trip_id == trip_id))
    values = {
        "cost_id": cost.id,
        "do_id": data.get("do_id"),
        "voucher_no": data["voucher_no"],
        "voucher_date": data["voucher_date"],
        "vehicle_manager": data.get("vehicle_manager"),
        "payment_method": data.get("payment_method") or "cash",
        "contract_no": data.get("contract_no"),
        "machine_numbers": data.get("machine_numbers"),
        "checked_by": data.get("checked_by"),
        "note": data.get("note"),
    }
    if voucher is None:
        voucher = EPLExpenseVoucher(
            id=str(uuid.uuid4()), trip_id=trip_id, created_by=actor, updated_by=actor, **values
        )
        db.add(voucher)
    else:
        changed = any(getattr(voucher, field) != value for field, value in values.items())
        for field, value in values.items():
            setattr(voucher, field, value)
        if changed:
            voucher.version += 1
            voucher.updated_at = dt.datetime.utcnow()
            voucher.updated_by = actor
    db.add(AuditLog(
        user_id=actor,
        action="SAVE_EPL_EXPENSE_VOUCHER",
        table_name="epl_expense_vouchers",
        record_id=voucher.id,
        timestamp=dt.datetime.utcnow(),
        ip_address=db.info.get("request_ip"),
    ))
    db.flush()
    return voucher


def _voucher_entity(db, identifier):
    return db.get(EPLExpenseVoucher, identifier) or db.scalar(
        select(EPLExpenseVoucher).where(EPLExpenseVoucher.trip_id == identifier)
    )


def serialize_expense_voucher(db, voucher):
    trip = db.get(TransportTrip, voucher.trip_id)
    cost = db.get(FreightActualCost, voucher.cost_id)
    do_id = voucher.do_id or db.scalar(
        select(TripDeliveryOrder.do_id)
        .where(TripDeliveryOrder.trip_id == voucher.trip_id)
        .order_by(TripDeliveryOrder.allocation_sequence)
        .limit(1)
    )
    delivery = db.get(DeliveryOrder, do_id) if do_id else None
    vehicle = db.get(Vehicle, trip.vehicle_id) if trip and trip.vehicle_id else None
    driver = db.get(Driver, trip.driver_id) if trip and trip.driver_id else None
    customer = db.get(Customer, delivery.customer_id) if delivery and delivery.customer_id else None
    actual_total = sum((Decimal(item.actual_amount or 0) for item in cost.items), Decimal("0"))
    increase_total = sum((Decimal(item.increase_amount or 0) for item in cost.items), Decimal("0"))
    return {
        "id": voucher.id,
        "trip_id": voucher.trip_id,
        "do_id": do_id,
        "voucher_no": voucher.voucher_no,
        "voucher_date": voucher.voucher_date,
        "vehicle_manager": voucher.vehicle_manager,
        "payment_method": voucher.payment_method,
        "contract_no": voucher.contract_no,
        "machine_numbers": voucher.machine_numbers,
        "checked_by": voucher.checked_by,
        "note": voucher.note,
        "version": voucher.version,
        "vehicle": {
            "plate": vehicle.id if vehicle else None,
            "type": vehicle.type if vehicle else None,
            "engine_no": vehicle.engine_no if vehicle else None,
        },
        "driver": {"id": driver.id, "name": driver.name} if driver else None,
        "customer": {"id": customer.id, "name": customer.name} if customer else None,
        "shipment": {
            "origin": delivery.origin if delivery else None,
            "destination": delivery.destination if delivery else None,
            "cargo_type": delivery.packaging_spec if delivery else None,
            "weight_kg": delivery.weight_kg if delivery else None,
        },
        "cost": {
            "id": cost.id,
            "currency_code": cost.currency_code,
            "status": cost.status,
            "total_amount": _number(actual_total),
            "increase_amount": _number(increase_total),
            "version": cost.version,
            "lines": [{
                "id": item.id,
                "name": item.description,
                "original_amount": _number(item.original_amount),
                "actual_amount": _number(item.actual_amount),
                "increase_amount": _number(item.increase_amount),
                "note": item.note,
            } for item in cost.items],
        },
    }


def get_expense_voucher(db, identifier):
    voucher = _voucher_entity(db, identifier)
    if voucher is None:
        raise DomainError("EXPENSE_VOUCHER_NOT_FOUND", "Không tìm thấy phiếu chi phí.", 404)
    return serialize_expense_voucher(db, voucher)


def list_expense_vouchers(db):
    vouchers = db.scalars(
        select(EPLExpenseVoucher).order_by(EPLExpenseVoucher.voucher_date.desc(), EPLExpenseVoucher.voucher_no)
    ).all()
    return [serialize_expense_voucher(db, voucher) for voucher in vouchers]
