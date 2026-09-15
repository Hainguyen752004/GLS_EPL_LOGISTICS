"""Nghiệp vụ Giao hàng — cắt gọn từ core của EPL_System.

Giữ lại đúng thứ bản demo cần: một chuyến chở nhiều Packing List, có xe và tài
xế, đi qua các mốc và ký nhận theo TỪNG Packing List. Bỏ hẳn điều phối, công
thức giá thành, sắp ca và quyết toán — người Lào không dùng và cũng không hiểu.
"""

import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from models import (
    Delivery,
    DeliveryEvent,
    Driver,
    PackingList,
    PackingListPOD,
    Vehicle,
)
from services import don_hang_service, packing_service
from services.loi import LoiNghiepVu

CHUOI_TRANG_THAI = ["planned", "loading", "in_transit", "arrived", "delivered"]


def _bay_gio():
    return datetime.datetime.utcnow()


def _ma_chuyen(db):
    nam = datetime.datetime.utcnow().year
    dem = db.query(func.count(Delivery.id)).filter(Delivery.code.like(f"GH-{nam}-%")).scalar() or 0
    return f"GH-{nam}-{dem + 1:04d}"


def nap(db, gh_id):
    gh = (
        db.query(Delivery)
        .options(
            selectinload(Delivery.packing_lists).selectinload(PackingList.order),
            selectinload(Delivery.packing_lists).selectinload(PackingList.pod),
            selectinload(Delivery.events),
        )
        .filter(Delivery.id == gh_id)
        .first()
    )
    if not gh:
        raise LoiNghiepVu("DL_NOT_FOUND", f"Không tìm thấy chuyến giao hàng {gh_id}", 404)
    return gh


def ghi_su_kien(db, gh, loai, nguoi, ghi_chu=None):
    db.add(
        DeliveryEvent(
            delivery_id=gh.id, event_type=loai, actor=nguoi, note=ghi_chu, occurred_at=_bay_gio()
        )
    )


def ra_dict(gh, day_du=True):
    data = {
        "id": gh.id,
        "code": gh.code,
        "vehicle_id": gh.vehicle_id,
        "driver_id": gh.driver_id,
        "plate_head": gh.plate_head,
        "plate_trailer": gh.plate_trailer,
        "driver_name": gh.driver_name,
        "driver_phone": gh.driver_phone,
        "route_name": gh.route_name,
        "planned_depart_at": gh.planned_depart_at,
        "departed_at": gh.departed_at,
        "arrived_at": gh.arrived_at,
        "completed_at": gh.completed_at,
        "status": gh.status,
        "note": gh.note,
        "created_at": gh.created_at,
        "packing_list_count": len([p for p in gh.packing_lists if p.status != "cancelled"]),
    }
    if not day_du:
        return data
    data["packing_lists"] = [
        {
            **packing_service.ra_dict(pl, day_du=False),
            "pod_received_by": pl.pod.received_by if pl.pod else None,
            "pod_result": pl.pod.result if pl.pod else None,
        }
        for pl in gh.packing_lists
        if pl.status != "cancelled"
    ]
    data["total_cases"] = sum(p["total_cases"] for p in data["packing_lists"])
    data["total_weight_kg"] = round(sum(p["total_weight_kg"] for p in data["packing_lists"]), 3)
    data["events"] = [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "occurred_at": ev.occurred_at,
            "actor": ev.actor,
            "note": ev.note,
        }
        for ev in gh.events
    ]
    return data


def tao(db, payload, nguoi):
    ds_pl = payload.get("packing_list_ids") or []
    if not ds_pl:
        raise LoiNghiepVu("DL_NO_PACKING_LIST", "Chuyến giao hàng phải chở ít nhất một Packing List")

    xe = None
    if payload.get("vehicle_id"):
        xe = db.query(Vehicle).filter(Vehicle.id == payload["vehicle_id"]).first()
        if not xe:
            raise LoiNghiepVu("DL_VEHICLE_NOT_FOUND", "Không tìm thấy xe", 404)
    tx = None
    if payload.get("driver_id"):
        tx = db.query(Driver).filter(Driver.id == payload["driver_id"]).first()
        if not tx:
            raise LoiNghiepVu("DL_DRIVER_NOT_FOUND", "Không tìm thấy tài xế", 404)

    ma = _ma_chuyen(db)
    gh = Delivery(
        id=ma,
        code=ma,
        vehicle_id=xe.id if xe else None,
        driver_id=tx.id if tx else None,
        plate_head=xe.plate_head if xe else payload.get("plate_head"),
        plate_trailer=xe.plate_trailer if xe else payload.get("plate_trailer"),
        driver_name=tx.full_name if tx else payload.get("driver_name"),
        driver_phone=tx.phone if tx else payload.get("driver_phone"),
        route_name=payload.get("route_name"),
        note=payload.get("note"),
        status="planned",
    )
    db.add(gh)
    db.flush()

    _xep_hang(db, gh, ds_pl, nguoi)
    ghi_su_kien(db, gh, "created", nguoi, f"{len(ds_pl)} Packing List")
    db.flush()
    return nap(db, gh.id)


def _xep_hang(db, gh, ds_pl, nguoi):
    for pl_id in ds_pl:
        pl = packing_service.nap(db, pl_id)
        if pl.status == "cancelled":
            raise LoiNghiepVu("PL_CANCELLED", f"Packing List {pl_id} đã huỷ", 409)
        if pl.delivery_id and pl.delivery_id != gh.id:
            raise LoiNghiepVu(
                "PL_ON_OTHER_DELIVERY",
                f"Packing List {pl_id} đang nằm trên chuyến khác",
                409,
                {"delivery_id": pl.delivery_id},
            )
        if pl.status not in ("ready", "parked", "gate_in"):
            raise LoiNghiepVu(
                "PL_NOT_READY_TO_LOAD",
                f"Packing List {pl_id} không ở trạng thái xếp lên xe được",
                409,
                {"status": pl.status},
            )
        pl.delivery_id = gh.id
        packing_service.ghi_su_kien(db, pl, "assigned_delivery", nguoi, gh.code)


def them_packing_list(db, gh_id, ds_pl, nguoi):
    gh = nap(db, gh_id)
    if gh.status not in ("planned", "loading"):
        raise LoiNghiepVu(
            "DL_LOCKED", "Chuyến đã xuất phát nên không xếp thêm hàng được", 409
        )
    _xep_hang(db, gh, ds_pl, nguoi)
    ghi_su_kien(db, gh, "packing_list_added", nguoi, ", ".join(ds_pl))
    db.flush()
    return nap(db, gh.id)


def bo_packing_list(db, gh_id, pl_id, nguoi):
    gh = nap(db, gh_id)
    if gh.status not in ("planned", "loading"):
        raise LoiNghiepVu("DL_LOCKED", "Chuyến đã xuất phát nên không bỏ hàng ra được", 409)
    pl = packing_service.nap(db, pl_id)
    if pl.delivery_id != gh.id:
        raise LoiNghiepVu("PL_NOT_ON_DELIVERY", "Packing List không nằm trên chuyến này", 409)
    if pl.status in ("loaded", "dispatched", "delivered"):
        raise LoiNghiepVu("PL_ALREADY_LOADED", "Packing List đã bốc lên xe", 409)
    pl.delivery_id = None
    packing_service.ghi_su_kien(db, pl, "removed_delivery", nguoi, gh.code)
    ghi_su_kien(db, gh, "packing_list_removed", nguoi, pl_id)
    db.flush()
    return nap(db, gh.id)


def doi_trang_thai(db, gh_id, trang_thai_moi, nguoi, ghi_chu=None):
    gh = nap(db, gh_id)
    if gh.status == "cancelled":
        raise LoiNghiepVu("DL_CANCELLED", "Chuyến đã huỷ", 409)
    if trang_thai_moi not in CHUOI_TRANG_THAI:
        raise LoiNghiepVu("DL_STATUS_UNKNOWN", f"Trạng thái không hợp lệ: {trang_thai_moi}")
    hien = CHUOI_TRANG_THAI.index(gh.status)
    moi = CHUOI_TRANG_THAI.index(trang_thai_moi)
    if moi <= hien:
        raise LoiNghiepVu("DL_STATUS_BACKWARD", "Không lùi trạng thái của chuyến", 409)
    if moi > hien + 1:
        raise LoiNghiepVu("DL_STATUS_SKIP", "Phải đi lần lượt từng bước, không nhảy cóc", 409)

    ds = [p for p in gh.packing_lists if p.status != "cancelled"]
    if not ds:
        raise LoiNghiepVu("DL_NO_PACKING_LIST", "Chuyến không còn Packing List nào", 409)

    if trang_thai_moi == "in_transit":
        # Xuất phát là mốc mà hàng rời bãi: mọi Packing List trên xe phải theo.
        for pl in ds:
            while pl.status != "dispatched":
                ke_tiep = packing_service.CHUOI_TRANG_THAI[
                    packing_service.CHUOI_TRANG_THAI.index(pl.status) + 1
                ]
                packing_service.doi_trang_thai(db, pl.id, ke_tiep, nguoi, f"Theo chuyến {gh.code}")
                pl = packing_service.nap(db, pl.id)
        gh.departed_at = _bay_gio()
    elif trang_thai_moi == "arrived":
        gh.arrived_at = _bay_gio()
    elif trang_thai_moi == "delivered":
        thieu = [p.id for p in ds if not p.pod]
        if thieu:
            raise LoiNghiepVu(
                "DL_MISSING_POD",
                "Còn Packing List chưa có bằng chứng giao hàng",
                409,
                {"packing_lists": thieu},
            )
        gh.completed_at = _bay_gio()

    gh.status = trang_thai_moi
    ghi_su_kien(db, gh, trang_thai_moi, nguoi, ghi_chu)
    db.flush()
    return nap(db, gh.id)


def ghi_pod(db, pl_id, payload, nguoi):
    """Ký nhận cho MỘT Packing List. Sau bước này nó mới thành đã giao."""
    pl = packing_service.nap(db, pl_id)
    if pl.status == "cancelled":
        raise LoiNghiepVu("PL_CANCELLED", "Packing List đã huỷ", 409)
    if pl.status not in ("dispatched", "delivered"):
        raise LoiNghiepVu(
            "PL_NOT_DISPATCHED",
            "Packing List chưa rời bãi nên chưa ký nhận được",
            409,
            {"status": pl.status},
        )
    nguoi_nhan = (payload.get("received_by") or "").strip()
    if not nguoi_nhan:
        raise LoiNghiepVu("POD_NO_RECEIVER", "Phải ghi tên người nhận hàng")

    ket_qua = payload.get("result") or "full"
    if ket_qua not in ("full", "short", "failed", "returned"):
        raise LoiNghiepVu("POD_RESULT_UNKNOWN", f"Kết quả giao không hợp lệ: {ket_qua}")

    pod = pl.pod or PackingListPOD(packing_list_id=pl.id)
    pod.delivery_id = pl.delivery_id
    pod.received_by = nguoi_nhan
    pod.received_at = _bay_gio()
    pod.result = ket_qua
    pod.goods_condition = payload.get("goods_condition")
    pod.note = payload.get("note")
    pod.signature_data = payload.get("signature_data")
    db.add(pod)
    db.flush()
    # Quan hệ `pod` của đối tượng này đã được nạp là None từ trước khi ghi, nên
    # phải làm nó hết hạn. Không làm thì bước đổi trạng thái ngay dưới đây đọc
    # lại vẫn thấy None và từ chối bằng PL_NO_POD — trong khi POD vừa ghi xong.
    db.expire(pl, ["pod"])

    packing_service.ghi_su_kien(db, pl, "pod_recorded", nguoi, f"{nguoi_nhan} · {ket_qua}")
    if pl.status == "dispatched":
        packing_service.doi_trang_thai(db, pl.id, "delivered", nguoi, "Đã ký nhận")
    db.flush()
    return packing_service.nap(db, pl.id)


def danh_sach(db, q=None, trang_thai=None, trang=1, moi_trang=25):
    cau = db.query(Delivery).options(selectinload(Delivery.packing_lists))
    if trang_thai:
        cau = cau.filter(Delivery.status == trang_thai)
    if q:
        tim = f"%{q.strip()}%"
        cau = cau.filter(
            Delivery.code.ilike(tim)
            | Delivery.plate_head.ilike(tim)
            | Delivery.driver_name.ilike(tim)
            | Delivery.route_name.ilike(tim)
        )
    tong = cau.count()
    hang = (
        cau.order_by(Delivery.created_at.desc())
        .offset((trang - 1) * moi_trang)
        .limit(moi_trang)
        .all()
    )
    return {
        "items": [ra_dict(gh, day_du=False) for gh in hang],
        "total": tong,
        "page": trang,
        "page_size": moi_trang,
    }


def huy(db, gh_id, ly_do, nguoi):
    gh = nap(db, gh_id)
    if gh.status in ("in_transit", "arrived", "delivered"):
        raise LoiNghiepVu("DL_ALREADY_OUT", "Chuyến đã xuất phát nên không huỷ được", 409)
    for pl in gh.packing_lists:
        if pl.status not in ("loaded", "dispatched", "delivered"):
            pl.delivery_id = None
            packing_service.ghi_su_kien(db, pl, "removed_delivery", nguoi, "Chuyến bị huỷ")
    gh.status = "cancelled"
    gh.note = ((gh.note or "") + f"\n[HUỶ] {ly_do or ''} ({nguoi})").strip()
    ghi_su_kien(db, gh, "cancelled", nguoi, ly_do)
    db.flush()
    return nap(db, gh.id)


def thong_ke(db):
    dem = dict(db.query(Delivery.status, func.count(Delivery.id)).group_by(Delivery.status).all())
    return {
        "total": sum(dem.values()),
        "planned": dem.get("planned", 0),
        "loading": dem.get("loading", 0),
        "in_transit": dem.get("in_transit", 0),
        "arrived": dem.get("arrived", 0),
        "delivered": dem.get("delivered", 0),
        "cancelled": dem.get("cancelled", 0),
    }
