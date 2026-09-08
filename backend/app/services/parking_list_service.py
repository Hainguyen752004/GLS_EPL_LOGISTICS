import datetime
import secrets
from uuid import uuid4

from sqlalchemy.orm import selectinload

from models import (
    Customer,
    DeliveryOrder,
    DeliveryOrderDetail,
    ParkingEvent,
    ParkingLabel,
    ParkingList,
    ParkingListItem,
    Route,
    TripDeliveryOrder,
)
from services import packing_control_policy
from services.errors import DomainError, conflict


TRANSITIONS = {
    # `draft` DA BO. `generate_from_do` tao phieu thang o `ready`, nen khong
    # duong nao dan tai `draft` ca — mot trang thai khong bao gio xay ra la bay
    # cho nguoi doc ma sau: ho viet nhanh xu ly cho no, viet bai kiem cho no, va
    # ca hai deu la cong viec cho mot tinh huong khong ton tai.
    "ready": {"parked", "cancelled"},
    "parked": {"gate_in", "cancelled"},
    "gate_in": {"loaded", "cancelled"},
    "loaded": {"dispatched", "cancelled"},
    "dispatched": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}

AUTOMATED_STATUSES = {"ready", "parked", "gate_in", "loaded", "dispatched", "delivered"}


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _load(db, parking_id):
    item = (
        db.query(ParkingList)
        .options(
            selectinload(ParkingList.items),
            selectinload(ParkingList.labels),
            selectinload(ParkingList.events),
        )
        .filter(ParkingList.id == parking_id)
        .first()
    )
    if not item:
        raise DomainError("PARKING_LIST_NOT_FOUND", "Không tìm thấy Parking List.", 404)
    return item


def _label_dict(label):
    return {
        "id": label.id,
        "package_no": label.package_no,
        "package_total": label.package_total,
        "qr_token": label.qr_token,
        "status": label.status,
        "printed_at": label.printed_at,
        "reprint_count": label.reprint_count,
        "qr_path": f"/api/parking-labels/{label.id}/qr.svg",
    }


def serialize(item, include_events=True):
    data = {
        "id": item.id,
        "do_id": item.do_id,
        "so_id": item.so_id,
        "trip_id": item.trip_id,
        "version": item.version,
        "customer_id": item.customer_id,
        "store_id": item.store_id,
        "store_name": item.store_name,
        "route_code": item.route_code,
        "route_name": item.route_name,
        "wave": item.wave,
        "gate": item.gate,
        "box_count": item.box_count,
        "total_pieces": item.total_pieces,
        "total_weight_kg": item.total_weight_kg,
        "total_cube_m3": item.total_cube_m3,
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "items": [
            {
                "id": row.id,
                "source_detail_id": row.source_detail_id,
                "barcode": row.barcode,
                "item_id_laos": row.item_id_laos,
                "item_id_thai": row.item_id_thai,
                "sku": row.sku,
                "description": row.description,
                "case_qty": row.case_qty,
                "piece_qty": row.piece_qty,
                "uom": row.uom,
                "weight_kg": row.weight_kg,
                "cube_m3": row.cube_m3,
                "note": row.note,
            }
            for row in item.items
        ],
        "labels": [_label_dict(label) for label in item.labels],
    }
    if include_events:
        data["events"] = [
            {
                "id": event.id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at,
                "actor": event.actor,
                "note": event.note,
            }
            for event in item.events
        ]
    return data


def generate_from_do(db, do_id, payload, actor):
    delivery = db.get(DeliveryOrder, do_id)
    if not delivery:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy DO {do_id}.", 404)
    existing = (
        db.query(ParkingList)
        .filter(ParkingList.do_id == do_id, ParkingList.status != "cancelled")
        .order_by(ParkingList.version.desc())
        .first()
    )
    if existing:
        return _load(db, existing.id)

    latest_version = db.query(ParkingList).filter(ParkingList.do_id == do_id).count() + 1
    customer = db.get(Customer, delivery.customer_id) if delivery.customer_id else None
    route = db.get(Route, delivery.route_id) if delivery.route_id else None
    trip_link = (
        db.query(TripDeliveryOrder)
        .filter(TripDeliveryOrder.do_id == do_id)
        .order_by(TripDeliveryOrder.created_at.desc())
        .first()
    )
    details = (
        db.query(DeliveryOrderDetail)
        .filter(DeliveryOrderDetail.so_id == delivery.so_id)
        .order_by(DeliveryOrderDetail.id)
        .all()
    )
    total_pieces = sum(max(int(row.qty or 0), 0) for row in details)
    parking = ParkingList(
        id=f"PL-{uuid4().hex[:20].upper()}",
        do_id=delivery.id,
        so_id=delivery.so_id,
        trip_id=trip_link.trip_id if trip_link else None,
        version=latest_version,
        customer_id=delivery.customer_id,
        store_id=(payload.get("store_id") or delivery.customer_id or "").strip() or None,
        store_name=(payload.get("store_name") or (customer.name if customer else "")).strip() or None,
        route_code=delivery.route_id,
        route_name=route.name if route else None,
        wave=(payload.get("wave") or "").strip() or None,
        gate=(payload.get("gate") or "").strip() or None,
        box_count=payload.get("box_count") or 1,
        total_pieces=total_pieces,
        total_weight_kg=float(delivery.weight_kg or sum(float(row.weight_kg or 0) for row in details)),
        total_cube_m3=float(delivery.volume_m3 or 0),
        status="ready",
        created_by=actor,
        updated_by=actor,
    )
    db.add(parking)
    for row in details:
        parking.items.append(ParkingListItem(
            source_detail_id=row.id,
            sku=row.sku,
            description=row.description,
            piece_qty=max(int(row.qty or 0), 0),
            uom=row.uom,
            weight_kg=float(row.weight_kg or 0),
        ))
    for package_no in range(1, parking.box_count + 1):
        parking.labels.append(ParkingLabel(
            id=f"LBL-{uuid4().hex[:20].upper()}",
            package_no=package_no,
            package_total=parking.box_count,
            qr_token=secrets.token_urlsafe(32),
            status="ready",
        ))
    parking.events.append(ParkingEvent(event_type="generated", actor=actor, note="Sinh từ DO/SO"))
    db.flush()
    return _load(db, parking.id)


def _split_integer(total, count):
    base, remainder = divmod(max(int(total or 0), 0), count)
    return [base + (1 if index < remainder else 0) for index in range(count)]


def _split_total(total, weights):
    value = float(total or 0)
    count = len(weights)
    if not count:
        return []
    denominator = sum(max(int(weight or 0), 0) for weight in weights)
    ratios = (
        [max(int(weight or 0), 0) / denominator for weight in weights]
        if denominator > 0
        else [1 / count] * count
    )
    parts = []
    allocated = 0.0
    for index, ratio in enumerate(ratios):
        part = value - allocated if index == count - 1 else round(value * ratio, 6)
        parts.append(round(part, 6))
        allocated += part
    return parts


def _next_version(db, do_id):
    latest = (
        db.query(ParkingList.version)
        .filter(ParkingList.do_id == do_id)
        .order_by(ParkingList.version.desc())
        .first()
    )
    return int(latest[0] if latest else 0) + 1


def _create_auto_snapshot(
    db,
    delivery,
    customer,
    route,
    trip_link,
    details,
    quantities,
    version,
    box_count,
    total_weight_kg,
    total_cube_m3,
    actor,
    note,
):
    parking = ParkingList(
        id=f"PL-{uuid4().hex[:20].upper()}",
        do_id=delivery.id,
        so_id=delivery.so_id,
        trip_id=trip_link.trip_id if trip_link else None,
        version=version,
        customer_id=delivery.customer_id,
        store_id=delivery.customer_id,
        store_name=customer.name if customer else None,
        route_code=delivery.route_id,
        route_name=route.name if route else None,
        box_count=max(int(box_count or 1), 1),
        total_pieces=sum(quantities),
        total_weight_kg=float(total_weight_kg or 0),
        total_cube_m3=float(total_cube_m3 or 0),
        status="ready",
        created_by=actor,
        updated_by=actor,
    )
    db.add(parking)
    for row, quantity in zip(details, quantities):
        source_quantity = max(int(row.qty or 0), 0)
        source_weight = float(row.weight_kg or 0)
        allocated_weight = (
            round(source_weight * quantity / source_quantity, 6)
            if source_quantity > 0
            else 0
        )
        parking.items.append(ParkingListItem(
            source_detail_id=row.id,
            sku=row.sku,
            description=row.description,
            piece_qty=quantity,
            uom=row.uom,
            weight_kg=allocated_weight,
        ))
    for package_no in range(1, parking.box_count + 1):
        parking.labels.append(ParkingLabel(
            id=f"LBL-{uuid4().hex[:20].upper()}",
            package_no=package_no,
            package_total=parking.box_count,
            qr_token=secrets.token_urlsafe(32),
            status="ready",
        ))
    parking.events.append(ParkingEvent(event_type="generated", actor=actor, note=note))
    db.flush()
    return parking


def generate_many_from_do(db, do_id, list_count, actor):
    delivery = db.get(DeliveryOrder, do_id)
    if not delivery:
        raise DomainError("DELIVERY_ORDER_NOT_FOUND", f"Không tìm thấy DO {do_id}.", 404)

    total_packages = max(int(delivery.pallet_count or 0), 1)
    if list_count > total_packages:
        raise DomainError(
            "PACKING_LIST_COUNT_EXCEEDS_PACKAGES",
            f"DO chỉ có {total_packages} kiện/pallet, không thể chia thành {list_count} Packing List.",
            422,
        )

    customer = db.get(Customer, delivery.customer_id) if delivery.customer_id else None
    route = db.get(Route, delivery.route_id) if delivery.route_id else None
    trip_link = (
        db.query(TripDeliveryOrder)
        .filter(TripDeliveryOrder.do_id == do_id)
        .order_by(TripDeliveryOrder.created_at.desc())
        .first()
    )
    details = (
        db.query(DeliveryOrderDetail)
        .filter(DeliveryOrderDetail.so_id == delivery.so_id)
        .order_by(DeliveryOrderDetail.id)
        .all()
    )
    box_counts = _split_integer(total_packages, list_count)
    allocations_by_detail = [
        _split_integer(max(int(row.qty or 0), 0), list_count)
        for row in details
    ]
    piece_counts = [
        sum(allocations[index] for allocations in allocations_by_detail)
        for index in range(list_count)
    ]
    source_weight = delivery.weight_kg or sum(float(row.weight_kg or 0) for row in details)
    weights = _split_total(source_weight, piece_counts)
    cubes = _split_total(delivery.volume_m3, piece_counts)
    first_version = _next_version(db, do_id)
    created = []
    for index in range(list_count):
        quantities = [allocations[index] for allocations in allocations_by_detail]
        created.append(_create_auto_snapshot(
            db,
            delivery,
            customer,
            route,
            trip_link,
            details,
            quantities,
            first_version + index,
            box_counts[index],
            weights[index],
            cubes[index],
            actor,
            f"Tự động chia từ DO/SO ({index + 1}/{list_count})",
        ))

    return {
        "do_id": do_id,
        "list_count": list_count,
        "total_packages": total_packages,
        "items": [serialize(_load(db, item.id)) for item in created],
    }


def list_parking_lists(db, q=None, status=None, page=1, page_size=25):
    query = db.query(ParkingList)
    if status:
        query = query.filter(ParkingList.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            ParkingList.id.ilike(pattern)
            | ParkingList.do_id.ilike(pattern)
            | ParkingList.store_id.ilike(pattern)
            | ParkingList.store_name.ilike(pattern)
            | ParkingList.route_code.ilike(pattern)
        )
    total = query.count()
    rows = (
        query.order_by(ParkingList.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [serialize(_load(db, row.id), include_events=False) for row in rows], "total": total, "page": page, "page_size": page_size}


def transition(db, parking_id, target, actor, note=None):
    item = db.query(ParkingList).filter(ParkingList.id == parking_id).with_for_update().first()
    if not item:
        raise DomainError("PARKING_LIST_NOT_FOUND", "Không tìm thấy Parking List.", 404)
    if target not in TRANSITIONS:
        raise DomainError("PARKING_STATUS_INVALID", "Trạng thái Parking List không hợp lệ.", 422)
    if target != "cancelled":
        raise conflict(
            "PARKING_STATUS_AUTOMATED",
            "Trạng thái vận hành được cập nhật từ QR, điều phối và POD; không được chuyển tay.",
        )
    if target not in TRANSITIONS.get(item.status, set()):
        raise conflict("INVALID_PARKING_TRANSITION", f"Không thể chuyển từ {item.status} sang {target}.")
    item.status = target
    item.updated_at = _now()
    item.updated_by = actor
    for label in item.labels:
        label.status = target
    item.events.append(ParkingEvent(event_type=target, actor=actor, note=note))
    db.flush()
    return _load(db, item.id)


def _append_event(item, event_type, actor, note=None):
    item.events.append(ParkingEvent(event_type=event_type, actor=actor, note=note))


def _set_status(item, target, actor, note=None, update_all_labels=True):
    item.status = target
    item.updated_at = _now()
    item.updated_by = actor
    if update_all_labels:
        for label in item.labels:
            label.status = target
    _append_event(item, target, actor, note)


def scan_label(db, token, action, actor, note=None):
    label = (
        db.query(ParkingLabel)
        .filter(ParkingLabel.qr_token == token)
        .with_for_update()
        .first()
    )
    if not label:
        raise DomainError("PARKING_QR_NOT_FOUND", "Mã QR không hợp lệ hoặc đã hết hiệu lực.", 404)

    item = (
        db.query(ParkingList)
        .filter(ParkingList.id == label.parking_list_id)
        .with_for_update()
        .first()
    )
    if not item:
        raise DomainError("PARKING_LIST_NOT_FOUND", "Không tìm thấy Packing List.", 404)
    _load(db, item.id)

    # BA BUOC QUET DUNG CHUNG MOT KHUON, va do la mot sua loi.
    #
    # Truoc day hai buoc dau (`yard_arrival`, `gate_entry`) chuyen CA PHIEU sang
    # trang thai moi ngay khi quet MOT kien, con buoc bocc hang thi doi du moi
    # kien. Hai nghia khac nhau tren cung mot dai trang thai: man hinh ghi "da
    # qua cong" khi moi mot trong muoi kien qua cong, va nguoi doc tin con so
    # do. Do khong chan xe roi ben — cua `require_loaded_for_dispatch` van doi
    # `loaded`, tuc doi du kien — nhung no lam hai trang thai giua duong noi sai.
    #
    # Gio ca ba buoc: danh dau TUNG NHAN, va chi chuyen ca phieu khi MOI nhan da
    # qua buoc do.
    BUOC = {
        "yard_arrival": ("ready", "parked", "vào bãi chờ",
                         "Chỉ được quét vào bãi khi Packing List đang sẵn sàng in tem."),
        "gate_entry": ("parked", "gate_in", "qua cổng",
                       "Phải quét vào bãi chờ trước khi qua cổng."),
        "load_package": ("gate_in", "loaded", "bốc lên xe",
                         "Phải qua cổng trước khi quét kiện bốc hàng."),
    }
    if action not in BUOC:
        raise DomainError("PARKING_SCAN_ACTION_INVALID", "Hành động quét QR không hợp lệ.", 422)

    truoc, moc, viec, loi_thu_tu = BUOC[action]
    if item.status == moc:
        return _load(db, item.id)
    if item.status != truoc:
        raise conflict("INVALID_PARKING_SCAN_ORDER", loi_thu_tu)

    if label.status != moc:
        label.status = moc
        item.updated_at = _now()
        item.updated_by = actor
        _append_event(
            item,
            "package_%s" % moc,
            actor,
            note or "Đã quét kiện %s/%s %s" % (label.package_no, label.package_total, viec),
        )
    labels = db.query(ParkingLabel).filter(ParkingLabel.parking_list_id == item.id).all()
    if labels and all(row.status == moc for row in labels):
        _set_status(item, moc, actor,
                    "Đã quét đủ %s kiện %s" % (len(labels), viec),
                    update_all_labels=False)

    db.flush()
    return _load(db, item.id)


#: Trang thai Packing List duoc coi la DA QUET DU KIEN.
DA_DU_KIEN = {"loaded", "dispatched", "delivered"}


def require_loaded_for_dispatch(db, do_ids):
    """Chan xuat ben khi hang chua duoc kiem soat du.

    BAN TRUOC CHI SOI PHIEU DA TON TAI, va do la mot lo hong that: don khong co
    Packing List thi di qua tu do. Nghia la quy tac "phai quet du kien" bi tat
    bang cach KHONG lap phieu — mot cua ma ai cung tat duoc thi khong phai cua.

    Gio quy tac gan vao LOAI HANG, do du lieu quyet chu khong do nguoi bam:
    hang dem duoc theo kien thi PHAI co phieu da quet du; hang nguyen khoi thi
    khong dem kien nhung PHAI co so niem phong. Xem `packing_control_policy` de
    biet vi sao khong ap mot quy tac cho ca hai loai.
    """
    if not do_ids:
        return

    rows = (
        db.query(ParkingList)
        .filter(ParkingList.do_id.in_(do_ids), ParkingList.status != "cancelled")
        .with_for_update()
        .all()
    )

    # Phieu CO nhung chua quet du kien: chan truoc, va bao dung phieu nao dang
    # thieu — do la loi cu the nhat, nguoi dung biet phai di quet tiep o dau.
    blocked = [row for row in rows if row.status not in DA_DU_KIEN]
    if blocked:
        summary = ", ".join(f"{row.id} ({row.status})" for row in blocked[:5])
        raise conflict(
            "PACKING_LIST_NOT_LOADED",
            f"Chưa thể xuất bến. Cần quét đủ kiện cho Packing List: {summary}.",
            ["parking-list"],
        )

    # Roi den quy tac theo loai hang: don nao PHAI co phieu ma khong co phieu
    # nao, va don nguyen khoi nao thieu so niem phong.
    du_kien_theo_don = {
        str(row.do_id) for row in rows if row.status in DA_DU_KIEN
    }
    don_hang = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.id.in_(do_ids))
        .all()
    )
    for don in don_hang:
        packing_control_policy.kiem_dieu_kien_xuat_ben(
            don, str(don.id) in du_kien_theo_don)


def sync_do_status(db, do_id, target, actor, note=None):
    rows = (
        db.query(ParkingList)
        .filter(ParkingList.do_id == do_id, ParkingList.status != "cancelled")
        .with_for_update()
        .all()
    )
    for item in rows:
        if target == "dispatched":
            if item.status in {"dispatched", "delivered"}:
                continue
            if item.status != "loaded":
                raise conflict("PACKING_LIST_NOT_LOADED", f"Packing List {item.id} chưa bốc đủ kiện.")
            _set_status(item, "dispatched", actor, note)
        elif target == "delivered":
            if item.status == "delivered":
                continue
            if item.status == "loaded":
                _set_status(item, "dispatched", actor, note or "Đồng bộ từ chuyến giao hàng")
            if item.status != "dispatched":
                raise conflict("PACKING_LIST_NOT_DISPATCHED", f"Packing List {item.id} chưa xuất bãi.")
            _set_status(item, "delivered", actor, note)
        else:
            raise DomainError("PARKING_SYNC_TARGET_INVALID", "Trạng thái đồng bộ không hợp lệ.", 422)
    db.flush()


def record_print(db, parking_id, document_type, actor):
    item = db.query(ParkingList).filter(ParkingList.id == parking_id).with_for_update().first()
    if not item:
        raise DomainError("PARKING_LIST_NOT_FOUND", "Không tìm thấy Parking List.", 404)

    now = _now()
    if document_type == "labels":
        for label in item.labels:
            if label.printed_at is not None:
                label.reprint_count = int(label.reprint_count or 0) + 1
            label.printed_at = now
        event_type = "labels_printed"
        note = f"In {len(item.labels)} tem kiện"
    elif document_type == "packing_list":
        event_type = "packing_list_printed"
        note = "In Packing List"
    else:
        raise DomainError("PARKING_PRINT_TYPE_INVALID", "Loại tài liệu in không hợp lệ.", 422)

    item.updated_at = now
    item.updated_by = actor
    item.events.append(ParkingEvent(event_type=event_type, actor=actor, note=note))
    db.flush()
    return _load(db, item.id)
