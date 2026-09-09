import datetime as dt
import math
import uuid
import hashlib
import json
import os
import re
from contextlib import nullcontext
from urllib.parse import unquote, urlparse
from types import SimpleNamespace
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from models import (AuditLog, Carrier, IdempotencyRecord, FinanceControlConfig, FreightActualCost,
                    FreightChargeItem, FreightCostDocument, FreightOrder, Tender,
                    TransportEvent, TransportTrip, TransportTripLeg)
from services.errors import DomainError, conflict, missing_master
from services.tms_money import (_decimal, calculate_charge_line, quantize_currency,
                                require_currency, require_finance_config, to_functional)


CHARGE_TYPES = {"fuel", "toll", "driver", "waiting", "loading", "unloading",
                "carrier_base", "surcharge", "discount", "other"}


def save_trip_cost_rows(db, trip_id, data, method, path, key, actor, permissions):
    """Replace a Trip's user-defined cost rows and recalculate the increase total."""
    _require_permission(permissions, "finance_creator")
    actor = _actor(actor)
    return _idempotent(
        db,
        actor,
        method,
        path,
        key,
        {"trip_id": trip_id, **data},
        lambda: _save_trip_cost_rows(db, trip_id, data, actor),
    )


def _save_trip_cost_rows(db, trip_id, data, actor):
    trip = db.execute(
        select(TransportTrip).where(TransportTrip.id == trip_id).with_for_update()
    ).scalar_one_or_none()
    if trip is None:
        raise DomainError("TRIP_NOT_FOUND", "Không tìm thấy chuyến vận chuyển.", 404)
    if trip.status != "completed":
        raise conflict(
            "TRIP_NOT_COMPLETED",
            "Chỉ được quyết toán chi phí sau khi chuyến đã hoàn thành POD.",
        )
    order = db.get(FreightOrder, trip.freight_order_id)
    if order is None:
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy lệnh vận chuyển.", 404)
    currency = require_currency(db, data.get("currency_code"))
    require_finance_config(db)
    carrier_id = data.get("carrier_id")
    carrier = db.get(Carrier, carrier_id) if carrier_id else db.scalar(
        select(Carrier).where(
            Carrier.status == "active", Carrier.is_internal.is_(True)
        ).order_by(Carrier.id)
    )
    if carrier is None or carrier.status != "active":
        raise missing_master("carrier", "nhà vận chuyển nội bộ đang hoạt động")
    cost = db.scalar(select(FreightActualCost).where(
        FreightActualCost.trip_id == trip.id,
        FreightActualCost.is_active.is_(True),
    ))
    if cost is not None and cost.status != "draft":
        raise conflict(
            "COST_NOT_DRAFT",
            "Chi phí đã gửi duyệt nên không thể sửa các khoản phát sinh.",
        )
    if cost is None:
        fx = to_functional(db, Decimal(0), currency.code, dt.date.today())
        planned_distance = db.scalar(select(
            func.coalesce(func.sum(TransportTripLeg.distance_km), 0)
        ).where(TransportTripLeg.trip_id == trip.id)) or Decimal(0)
        cost = FreightActualCost(
            id=data.get("id") or str(uuid.uuid4()),
            freight_order_id=order.id,
            trip_id=trip.id,
            carrier_id=carrier.id,
            currency_code=currency.code,
            functional_currency=fx["functional_currency"],
            exchange_rate_snapshot=fx["exchange_rate_snapshot"],
            exchange_rate_date=fx["rate_date"],
            exchange_rate_source=fx["source"],
            planned_distance_km=planned_distance,
            created_by=actor,
            updated_by=actor,
        )
        db.add(cost)
        db.flush()
    else:
        cost.currency_code = currency.code
        cost.carrier_id = carrier.id
        cost.updated_at = _now()
        cost.updated_by = actor
        cost.version += 1
        cost.items.clear()
        db.flush()
    for line_data in data["lines"]:
        original = _decimal(line_data["original_amount"], "Giá ban đầu", 24, 6)
        actual = _decimal(line_data["actual_amount"], "Giá thực tế", 24, 6)
        increase = actual - original
        if increase < 0:
            raise DomainError(
                "ACTUAL_COST_BELOW_ORIGINAL",
                "Giá thực tế không được nhỏ hơn giá ban đầu.",
                422,
            )
        # MA KHOAN MUC, khong con viet cung "other".
        #
        # Ban truoc dat `charge_type="other"` cho MOI dong. Ten that van con o
        # `description` ("Chi phi xang dau /km"), nhung ma phan loai — thu duy
        # nhat MAY doc duoc — bi bo di. Do duoc tren du lieu demo that: ca bon
        # dong chi phi cua mot chuyen deu ra "Khoan khac", nen he cong no khach
        # hang khong tach duoc xang dau voi cau duong.
        #
        # `khoan_muc_tu` de o `khoan_muc_chi_phi` — MOT cho duy nhat giu
        # phep anh xa, dung chung voi phieu thu/chi. Hai ban anh xa se troi khoi
        # nhau, va luc do bang chi phi va phieu noi hai chuyen khac nhau ve cung
        # mot khoan tien.
        from services.khoan_muc_chi_phi import khoan_muc_tu
        cost.items.append(FreightChargeItem(
            id=line_data.get("id") or str(uuid.uuid4()),
            charge_type=khoan_muc_tu(
                line_data.get("charge_type") or line_data.get("key"),
                line_data["name"]),
            description=line_data["name"],
            original_amount=original,
            actual_amount=actual,
            increase_amount=increase,
            note=line_data.get("note"),
            quantity=Decimal(1),
            unit_price=increase,
            tax_code="EXEMPT",
            tax_rate_snapshot=Decimal(0),
            tax_mode="exempt",
            net_amount=increase,
            tax_amount=Decimal(0),
            total_amount=increase,
            rounding_adjustment=Decimal(0),
            created_by=actor,
            updated_by=actor,
        ))
    _recalculate(cost)
    _audit(db, "SAVE_TRIP_ACTUAL_COST", "freight_actual_costs", cost.id, actor)
    db.flush()
    return cost


def _now():
    return dt.datetime.utcnow()


def _require_permission(permissions, required):
    if not permissions or required not in set(permissions):
        raise DomainError("FINANCE_PERMISSION_DENIED", "Bạn không có quyền thực hiện nghiệp vụ tài chính này.", 403)


def _actor(actor):
    if not str(actor or "").strip():
        raise DomainError("ACTOR_REQUIRED", "Không xác định được người thực hiện.", 403)
    return str(actor).strip()


def _audit(db, action, table, record_id, actor):
    db.add(AuditLog(user_id=actor, action=action, table_name=table, record_id=str(record_id),
                    timestamp=_now(), ip_address=db.info.get("audit_ip")))


def _cost_for_update(db, cost_id):
    cost = db.execute(cost_lock_statement(cost_id)).scalar_one_or_none()
    if cost is None:
        raise DomainError("FREIGHT_COST_NOT_FOUND", "Không tìm thấy chi ph? thực tế.", 404)
    return cost


def cost_lock_statement(cost_id):
    return select(FreightActualCost).where(FreightActualCost.id == cost_id).with_for_update()


def cost_transition_statement(cost_id, expected_version, from_status, to_status, actor):
    return update(FreightActualCost).where(
        FreightActualCost.id == cost_id,
        FreightActualCost.version == expected_version,
        FreightActualCost.status == from_status,
    ).values(status=to_status, version=expected_version + 1,
             updated_at=_now(), updated_by=actor)


def _draft_with_version(db, cost_id, expected_version):
    expected_version = _expected_version(expected_version)
    cost = _cost_for_update(db, cost_id)
    if cost.version != expected_version:
        raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    if cost.status != "draft":
        raise conflict("COST_NOT_DRAFT", "Chỉ được sửa chi ph? ở trạng thái nháp.")
    return cost


def _expected_version(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DomainError("EXPECTED_VERSION_INVALID", "Phiên bản dự kiến phải là số nguyên dương.", 422)
    return value


def _bump(db, cost, expected_version, actor):
    result = db.execute(update(FreightActualCost).where(
        FreightActualCost.id == cost.id, FreightActualCost.version == expected_version,
        FreightActualCost.status == "draft",
    ).values(version=expected_version + 1, updated_at=_now(), updated_by=actor))
    if result.rowcount != 1:
        raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    cost.version = expected_version + 1


def _carrier(db, order_id, explicit_id):
    tender = db.scalar(select(Tender).where(Tender.freight_order_id == order_id, Tender.status == "awarded"))
    carrier_id = tender.awarded_carrier_id if tender is not None else explicit_id
    carrier = db.get(Carrier, carrier_id) if carrier_id else None
    if carrier is None or carrier.status != "active" or (tender is None and not carrier.is_internal):
        raise missing_master("carrier", "nhà vận chuyển đang hoạt động (hoặc carrier nội bộ đã cấu hình)")
    return carrier


def create_cost(db, freight_order_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    actor = _actor(actor)
    return _idempotent(db, actor, method, path, key,
        {"freight_order_id": freight_order_id, **data},
        lambda: _create_cost(db, freight_order_id, data, actor, permissions))


def _create_cost(db, freight_order_id, data, actor, permissions):
    _require_permission(permissions, "finance_creator")
    order = db.execute(select(FreightOrder).where(FreightOrder.id == freight_order_id).with_for_update()).scalar_one_or_none()
    if order is None:
        raise DomainError("FREIGHT_ORDER_NOT_FOUND", "Không tìm thấy lệnh vận chuyển.", 404)
    if order.status != "delivered":
        raise conflict("FREIGHT_ORDER_NOT_DELIVERED", "Chỉ lệnh vận chuyển đã giao mới được chốt chi ph?.")
    if db.scalar(select(FreightActualCost.id).where(FreightActualCost.freight_order_id == order.id, FreightActualCost.is_active.is_(True))):
        raise conflict("ACTIVE_COST_EXISTS", "Lệnh vận chuyển đã có chi ph? đang hoạt động.")
    if data.get("reversal_of_cost_id") is not None:
        raise DomainError("REVERSAL_SOURCE_NOT_ALLOWED", "Không được chỉ định chứng từ đảo khi tạo chi ph? thông thường.", 422)
    currency = require_currency(db, data.get("currency_code"))
    config = require_finance_config(db)
    carrier = _carrier(db, order.id, data.get("carrier_id"))
    planned = _decimal(data.get("planned_distance_km", 0), "Quãng đường kế hoạch", 18, 3)
    if planned < 0:
        raise DomainError("DISTANCE_INVALID", "Quãng đường không được âm.", 422)
    fx = to_functional(db, Decimal(0), currency.code, data.get("rate_date") or dt.date.today())
    cost = FreightActualCost(
        id=data.get("id") or str(uuid.uuid4()), freight_order_id=order.id, carrier_id=carrier.id,
        currency_code=currency.code, functional_currency=fx["functional_currency"],
        exchange_rate_snapshot=fx["exchange_rate_snapshot"], exchange_rate_date=fx["rate_date"],
        exchange_rate_source=fx["source"], planned_distance_km=planned, created_by=actor, updated_by=actor,
    )
    db.add(cost)
    _audit(db, "CREATE_FREIGHT_ACTUAL_COST", "freight_actual_costs", cost.id, actor)
    try:
        db.flush()
    except IntegrityError:
        raise conflict("ACTIVE_COST_EXISTS", "Lệnh vận chuyển đã có chi ph? đang hoạt động.") from None
    return cost


def _recalculate(cost):
    cost.subtotal_amount = sum((item.net_amount + item.rounding_adjustment for item in cost.items), Decimal(0))
    cost.tax_amount = sum((item.tax_amount for item in cost.items), Decimal(0))
    cost.total_amount = sum((item.total_amount + item.rounding_adjustment for item in cost.items), Decimal(0))


def add_charge_item(db, cost_id, data, actor, permissions):
    _require_permission(permissions, "finance_creator")
    actor = _actor(actor)
    expected = data.get("expected_version")
    cost = _draft_with_version(db, cost_id, expected)
    charge_type = data.get("charge_type")
    if charge_type not in CHARGE_TYPES:
        raise DomainError("CHARGE_TYPE_INVALID", "Loại chi ph? không hợp lệ.", 422)
    unit_price = _decimal(data.get("unit_price"), "Đơn giá", 24, 6)
    if charge_type == "discount":
        unit_price = -abs(unit_price)
    elif unit_price < 0:
        raise DomainError("CHARGE_AMOUNT_NEGATIVE", "Chỉ dòng chiết khấu được phép âm.", 422)
    line = calculate_charge_line(db, data.get("quantity"), unit_price, data.get("tax_code"), data.get("tax_mode"))
    item = FreightChargeItem(id=data.get("id") or str(uuid.uuid4()), cost_id=cost.id,
        charge_type=charge_type, description=data.get("description"), quantity=_decimal(data.get("quantity"), "Số lượng", 18, 4),
        unit_price=unit_price, tax_code=line["tax_code"], tax_rate_snapshot=line["tax_rate"], tax_mode=line["tax_mode"],
        net_amount=line["net_amount"], tax_amount=line["tax_amount"], total_amount=line["total_amount"],
        created_by=actor, updated_by=actor)
    db.add(item); _recalculate(cost); _bump(db, cost, expected, actor)
    _audit(db, "ADD_FREIGHT_CHARGE_ITEM", "freight_charge_items", item.id, actor); db.flush()
    return item


def update_charge_item(db, cost_id, item_id, data, actor, permissions):
    _require_permission(permissions, "finance_creator"); actor = _actor(actor)
    cost = _draft_with_version(db, cost_id, data.get("expected_version"))
    item = next((x for x in cost.items if x.id == item_id), None)
    if item is None: raise DomainError("CHARGE_ITEM_NOT_FOUND", "Không tìm thấy dòng chi ph?.", 404)
    charge_type = data.get("charge_type", item.charge_type)
    if charge_type not in CHARGE_TYPES: raise DomainError("CHARGE_TYPE_INVALID", "Loại chi ph? không hợp lệ.", 422)
    quantity = data.get("quantity", item.quantity); unit_price = _decimal(data.get("unit_price", item.unit_price), "Đơn giá", 24, 6)
    if charge_type == "discount": unit_price = -abs(unit_price)
    elif unit_price < 0: raise DomainError("CHARGE_AMOUNT_NEGATIVE", "Chỉ dòng chiết khấu được phép âm.", 422)
    line = calculate_charge_line(db, quantity, unit_price, data.get("tax_code", item.tax_code), data.get("tax_mode", item.tax_mode))
    item.charge_type, item.description, item.quantity, item.unit_price = charge_type, data.get("description", item.description), _decimal(quantity, "Số lượng", 18, 4), unit_price
    item.tax_code, item.tax_rate_snapshot, item.tax_mode = line["tax_code"], line["tax_rate"], line["tax_mode"]
    item.net_amount, item.tax_amount, item.total_amount = line["net_amount"], line["tax_amount"], line["total_amount"]
    item.updated_at, item.updated_by = _now(), actor
    _recalculate(cost); _bump(db, cost, data["expected_version"], actor)
    _audit(db, "UPDATE_FREIGHT_CHARGE_ITEM", "freight_charge_items", item.id, actor); db.flush(); return item


def delete_charge_item(db, cost_id, item_id, expected_version, actor, permissions):
    _require_permission(permissions, "finance_creator"); actor = _actor(actor)
    cost = _draft_with_version(db, cost_id, expected_version)
    item = next((x for x in cost.items if x.id == item_id), None)
    if item is None: raise DomainError("CHARGE_ITEM_NOT_FOUND", "Không tìm thấy dòng chi ph?.", 404)
    db.delete(item); cost.items.remove(item); _recalculate(cost); _bump(db, cost, expected_version, actor)
    _audit(db, "DELETE_FREIGHT_CHARGE_ITEM", "freight_charge_items", item_id, actor); db.flush(); return cost


def add_cost_document(db, cost_id, data, actor, permissions):
    _require_permission(permissions, "finance_creator"); actor = _actor(actor)
    expected = data.get("expected_version"); cost = _draft_with_version(db, cost_id, expected)
    url, checksum = _validated_document_identity(data, db)
    if db.scalar(select(FreightCostDocument.id).where(
            FreightCostDocument.cost_id == cost.id,
            FreightCostDocument.checksum == checksum)):
        raise conflict("COST_DOCUMENT_DUPLICATE", "Chứng từ trùng checksum.")
    doc = FreightCostDocument(id=data.get("id") or str(uuid.uuid4()), cost_id=cost.id,
        document_type=data.get("document_type") or "carrier_document", storage_url=url, checksum=checksum,
        file_name=data.get("file_name"), mime_type=data.get("mime_type"), vendor_invoice_no=data.get("vendor_invoice_no"),
        document_date=data.get("document_date"), created_by=actor, updated_by=actor)
    db.add(doc); _bump(db, cost, expected, actor); _audit(db, "ADD_FREIGHT_COST_DOCUMENT", "freight_cost_documents", doc.id, actor); db.flush(); return doc


def _update_cost_document(db, cost_id, document_id, data, actor, permissions):
    _require_permission(permissions, "finance_creator"); actor = _actor(actor)
    expected = data.get("expected_version"); cost = _draft_with_version(db, cost_id, expected)
    doc = db.get(FreightCostDocument, document_id)
    if doc is None or doc.cost_id != cost.id: raise DomainError("COST_DOCUMENT_NOT_FOUND", "Không tìm thấy chứng từ chi ph?.", 404)
    url, checksum = _validated_document_identity({
        "storage_url": data.get("storage_url", doc.storage_url),
        "checksum": data.get("checksum", doc.checksum),
    }, db)
    if db.scalar(select(FreightCostDocument.id).where(
            FreightCostDocument.cost_id == cost.id,
            FreightCostDocument.checksum == checksum,
            FreightCostDocument.id != doc.id)):
        raise conflict("COST_DOCUMENT_DUPLICATE", "Chứng từ trùng checksum.")
    data = {**data, "storage_url": url, "checksum": checksum}
    for field in ("document_type", "storage_url", "file_name", "mime_type", "checksum", "vendor_invoice_no", "document_date"):
        if field in data: setattr(doc, field, data[field])
    doc.updated_at, doc.updated_by = _now(), actor; _bump(db, cost, expected, actor)
    _audit(db, "UPDATE_FREIGHT_COST_DOCUMENT", "freight_cost_documents", doc.id, actor); db.flush(); return doc


def _delete_cost_document(db, cost_id, document_id, expected_version, actor, permissions):
    _require_permission(permissions, "finance_creator"); actor = _actor(actor)
    cost = _draft_with_version(db, cost_id, expected_version); doc = db.get(FreightCostDocument, document_id)
    if doc is None or doc.cost_id != cost.id: raise DomainError("COST_DOCUMENT_NOT_FOUND", "Không tìm thấy chứng từ chi ph?.", 404)
    db.delete(doc); _bump(db, cost, expected_version, actor); _audit(db, "DELETE_FREIGHT_COST_DOCUMENT", "freight_cost_documents", document_id, actor); db.flush(); return cost


def calculate_actual_distance(db, freight_order_id, planned_distance_km=Decimal(0)):
    events = db.scalars(select(TransportEvent).where(TransportEvent.freight_order_id == freight_order_id)
        .order_by(TransportEvent.event_time, TransportEvent.recorded_at, TransportEvent.id)).all()
    points = []
    for event in events:
        if event.lat is None or event.lng is None or not (-90 <= event.lat <= 90 and -180 <= event.lng <= 180): continue
        point = (event.lat, event.lng)
        if not points or points[-1] != point: points.append(point)
    if len(points) < 2:
        return {"status": "insufficient_gps_data", "actual_distance_km": Decimal("0.000"), "variance_percent": None}
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2); dp = math.radians(lat2-lat1); dl = math.radians(lon2-lon1)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        total += 6371.0088 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    actual = Decimal(str(total)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    planned = _decimal(planned_distance_km, "Quãng đường kế hoạch", 18, 3)
    variance = None if planned == 0 else ((actual-planned) / planned * 100).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    return {"status": "calculated", "actual_distance_km": actual, "variance_percent": variance}


def submit_cost(db, cost_id, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    actor = _actor(actor)
    payload = {"cost_id": cost_id, "expected_version": expected_version}
    return _idempotent(db, actor, method, path, key, payload,
        lambda: _submit_cost(db, cost_id, expected_version, actor, permissions))


def _submit_cost(db, cost_id, expected_version, actor, permissions):
    _require_permission(permissions, "finance_creator"); cost = _draft_with_version(db, cost_id, expected_version)
    result = calculate_actual_distance(db, cost.freight_order_id, cost.planned_distance_km)
    cost.actual_distance_km, cost.distance_status, cost.distance_variance_percent = result["actual_distance_km"], result["status"], result["variance_percent"]
    config = require_finance_config(db)
    cost.distance_variance_warning = result["variance_percent"] is not None and abs(result["variance_percent"]) > config.distance_variance_threshold
    changed = db.execute(cost_transition_statement(cost.id, expected_version, "draft", "submitted", actor))
    if changed.rowcount != 1: raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    cost.version = expected_version + 1; cost.status = "submitted"; cost.submitted_at = _now(); cost.submitted_by = actor
    _audit(db, "SUBMIT_FREIGHT_ACTUAL_COST", "freight_actual_costs", cost.id, actor); db.flush(); return cost


def approve_cost(db, cost_id, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_approver")
    actor = _actor(actor)
    payload = {"cost_id": cost_id, "expected_version": expected_version}
    return _idempotent(db, actor, method, path, key, payload,
        lambda: _approve_cost(db, cost_id, expected_version, actor, permissions))


def _approve_cost(db, cost_id, expected_version, actor, permissions):
    _require_permission(permissions, "finance_approver"); expected_version = _expected_version(expected_version); cost = _cost_for_update(db, cost_id)
    if cost.version != expected_version: raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    if cost.status != "submitted": raise conflict("COST_NOT_SUBMITTED", "Chỉ được duyệt chi ph? đã submit.")
    config = require_finance_config(db)
    if config.enforce_creator_approver_sod and actor == cost.created_by:
        raise DomainError("SEPARATION_OF_DUTIES", "Người tạo không được đồng thời duyệt chi ph?.", 403)
    changed = db.execute(cost_transition_statement(cost.id, expected_version, "submitted", "approved", actor))
    if changed.rowcount != 1: raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    cost.status="approved"; cost.version = expected_version + 1; cost.approved_at=_now(); cost.approved_by=actor; cost.updated_at=_now(); cost.updated_by=actor
    _audit(db, "APPROVE_FREIGHT_ACTUAL_COST", "freight_actual_costs", cost.id, actor); db.flush(); return cost


def reverse_cost(db, cost_id, data, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_poster"); actor = _actor(actor)
    expected, reason = _expected_version(data.get("expected_version")), str(data.get("reason") or "").strip()
    if not reason: raise DomainError("REVERSAL_REASON_REQUIRED", "Lý do đảo chi ph? là bắt buộc.", 422)
    return _idempotent(db, actor, method, path, key, data,
                       lambda: _reverse_cost(db, cost_id, expected, reason, actor))


def _reverse_cost(db, cost_id, expected, reason, actor):
    from models import APInvoice

    cost = _cost_for_update(db, cost_id)
    if cost.version != expected: raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    if cost.status != "approved" or cost.reversal_of_cost_id: raise conflict("COST_REVERSAL_INVALID", "Chỉ được đảo chi ph? gốc đã duyệt.")
    if db.scalar(select(FreightActualCost.id).where(FreightActualCost.reversal_of_cost_id == cost.id)):
        raise conflict("COST_ALREADY_REVERSED", "Chi phí đã có chứng từ đảo.")
    if db.scalar(select(APInvoice.id).where(APInvoice.cost_id == cost.id, APInvoice.is_active.is_(True))):
        raise conflict("COST_HAS_ACTIVE_AP", "Chi phí đã có AP đang hoạt động. Vui lòng đảo AP trước khi đảo chi phí.")
    reversal_id = str(uuid.uuid4())
    changed = db.execute(update(FreightActualCost).where(FreightActualCost.id == cost.id,
        FreightActualCost.version == expected, FreightActualCost.status == "approved").values(
        status="reversed", is_active=False, version=expected + 1, reversed_at=_now(), reversed_by=actor,
        reversed_by_cost_id=reversal_id, updated_at=_now(), updated_by=actor))
    if changed.rowcount != 1: raise conflict("VERSION_CONFLICT", "Chi phí đã thay đổi. Vui lòng tải lại dữ liệu.")
    cost.status, cost.is_active, cost.version = "reversed", False, expected + 1
    cost.reversed_by_cost_id = reversal_id
    reversal = FreightActualCost(id=reversal_id, freight_order_id=cost.freight_order_id, carrier_id=cost.carrier_id,
        currency_code=cost.currency_code, functional_currency=cost.functional_currency,
        exchange_rate_snapshot=cost.exchange_rate_snapshot, exchange_rate_date=cost.exchange_rate_date,
        exchange_rate_source=cost.exchange_rate_source, planned_distance_km=cost.planned_distance_km,
        actual_distance_km=cost.actual_distance_km, distance_status=cost.distance_status,
        distance_variance_percent=cost.distance_variance_percent, distance_variance_warning=cost.distance_variance_warning,
        subtotal_amount=-cost.subtotal_amount, tax_amount=-cost.tax_amount, total_amount=-cost.total_amount,
        status="reversed", is_active=False, reversal_of_cost_id=cost.id, reversal_reason=reason,
        created_by=actor, updated_by=actor, reversed_by=actor, reversed_at=_now())
    db.add(reversal)
    for item in cost.items:
        db.add(FreightChargeItem(id=str(uuid.uuid4()), cost_id=reversal.id,
            charge_type=item.charge_type, description=item.description, quantity=item.quantity,
            unit_price=item.unit_price, tax_code=item.tax_code,
            tax_rate_snapshot=item.tax_rate_snapshot, tax_mode=item.tax_mode,
            net_amount=-item.net_amount, tax_amount=-item.tax_amount,
            total_amount=-item.total_amount, rounding_adjustment=-item.rounding_adjustment,
            created_by=actor, updated_by=actor))
    _audit(db, "REVERSE_FREIGHT_ACTUAL_COST", "freight_actual_costs", reversal.id, actor); db.flush(); return reversal


def _canonical_hash(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validated_document_identity(data, db=None):
    url = str(data.get("storage_url") or "").strip()
    checksum = str(data.get("checksum") or "").strip()
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise DomainError("DOCUMENT_URL_INVALID", "URL chứng từ không hợp lệ.", 422) from None
    valid_checksum = bool(re.fullmatch(r"sha256:[0-9a-fA-F]{64}", checksum))
    valid_url = False
    if url.startswith("/uploads/") and "\\" not in url and "\x00" not in url:
        decoded = unquote(url)
        segments = decoded.split("/")[2:]
        valid_url = ("\\" not in decoded and "\x00" not in decoded and bool(segments)
                     and all(segment not in ("", ".", "..") for segment in segments))
        if valid_url:
            url = "/uploads/" + "/".join(segments)
    elif parsed.scheme == "https" and hostname and not parsed.username and not parsed.password and port is None:
        configured = str(os.getenv("FINANCE_DOCUMENT_HTTPS_HOSTS") or "")
        if db is not None:
            config = require_finance_config(db)
            configured = ",".join(part for part in (config.document_https_hosts, configured) if part)
        allowed = {host.strip().lower() for host in configured.split(",") if host.strip()}
        valid_url = hostname.lower() in allowed
    if not valid_checksum or not valid_url:
        raise DomainError("COST_DOCUMENT_INVALID", "Chứng từ phải có HTTPS hoặc /uploads URL và checksum.", 422)
    return url, checksum.lower()


def _idempotent(db, actor, method, path, key, payload, operation):
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise DomainError("IDEMPOTENCY_KEY_INVALID", "Khóa idempotency phải có từ 1 đến 128 ký tự.", 422)
    if not isinstance(method, str) or not method.strip() or not isinstance(path, str) or not path.strip():
        raise DomainError("IDEMPOTENCY_SCOPE_INVALID", "Method và path idempotency là bắt buộc.", 422)
    method, path, key, digest = method.strip().upper(), path.strip(), key.strip(), _canonical_hash(payload)
    # SQLite ignores SELECT .. FOR UPDATE.  Acquire its database write lock before
    # the idempotency lookup so competing sessions observe a completed command,
    # rather than both executing it and racing during flush.
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite" and not db.in_transaction():
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    filters = (IdempotencyRecord.actor == actor, IdempotencyRecord.method == method,
               IdempotencyRecord.path == path, IdempotencyRecord.idempotency_key == key)
    existing = db.scalar(select(IdempotencyRecord).where(*filters))
    if existing:
        if existing.request_hash != digest: raise conflict("IDEMPOTENCY_KEY_REUSED", "Khóa idempotency đã được dùng với nội dung khác.")
        return _replay_snapshot(existing)
    try:
        # A SQLite SAVEPOINT can become the effective outer transaction when the
        # driver deferred BEGIN, causing release to survive Session.rollback().
        # BEGIN IMMEDIATE above supplies concurrency and preserves caller-owned
        # transaction atomicity, so only databases with real row locks need the
        # conflict-isolating savepoint.
        with (db.begin_nested() if dialect != "sqlite" else nullcontext()):
            result = operation()
            db.flush()
            snapshot = {column.key: getattr(result, column.key) for column in result.__table__.columns}
            db.add(IdempotencyRecord(actor=actor, method=method, path=path, idempotency_key=key,
                operation=f"{method}:{path}:{actor}", request_hash=digest,
                response_json=json.dumps(snapshot, ensure_ascii=False, default=str)))
            db.flush()
            failure_hook = db.info.get("finance_failure_hook")
            if failure_hook:
                failure_hook("after_idempotency")
    except IntegrityError:
        existing = db.scalar(select(IdempotencyRecord).where(*filters))
        if existing and existing.request_hash != digest: raise conflict("IDEMPOTENCY_KEY_REUSED", "Khóa idempotency đã được dùng với nội dung khác.") from None
        if existing:
            return _replay_snapshot(existing)
        raise conflict("IDEMPOTENCY_CONFLICT", "Xung đột khi ghi nhận yêu cầu.") from None
    return result


def _replay_snapshot(record):
    try:
        snapshot = json.loads(record.response_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = None
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("id"), (str, int)):
        raise conflict("IDEMPOTENCY_RECORD_CORRUPT", "Bản ghi idempotency không hợp lệ. Vui lòng liên hệ quản trị viên.")
    return SimpleNamespace(**snapshot)


def save_charge_item(db, cost_id, data, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    payload = {**data, "expected_version": expected_version}
    def command():
        exists = data.get("id") and db.get(FreightChargeItem, data["id"])
        if exists:
            return update_charge_item(db, cost_id, data["id"], payload, actor, permissions)
        return add_charge_item(db, cost_id, payload, actor, permissions)
    return _idempotent(db, _actor(actor), method, path, key, payload, command)


def save_cost_document(db, cost_id, data, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    payload = {**data, "expected_version": expected_version}
    def command():
        exists = data.get("id") and db.get(FreightCostDocument, data["id"])
        if exists:
            return _update_cost_document(db, cost_id, data["id"], payload, actor, permissions)
        return add_cost_document(db, cost_id, payload, actor, permissions)
    return _idempotent(db, _actor(actor), method, path, key, payload, command)


def update_cost_document(db, cost_id, document_id, data, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    payload = {**data, "expected_version": expected_version}
    return _idempotent(db, _actor(actor), method, path, key, payload,
        lambda: _update_cost_document(db, cost_id, document_id, payload, actor, permissions))


def delete_draft_cost_document(db, cost_id, document_id, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    payload = {"expected_version": expected_version}
    return _idempotent(db, _actor(actor), method, path, key, payload,
        lambda: _delete_cost_document(db, cost_id, document_id, expected_version, actor, permissions))


def delete_draft_charge_item(db, cost_id, item_id, expected_version, method, path, key, actor, permissions):
    _require_permission(permissions, "finance_creator")
    payload = {"expected_version": expected_version}
    return _idempotent(db, _actor(actor), method, path, key, payload,
        lambda: delete_charge_item(db, cost_id, item_id, expected_version, actor, permissions))


# Stable concise aliases used by service consumers.
add_document = add_cost_document
update_document = _update_cost_document
delete_document = _delete_cost_document
delete_cost_document = _delete_cost_document
add_item = add_charge_item
update_item = update_charge_item
delete_item = delete_charge_item
