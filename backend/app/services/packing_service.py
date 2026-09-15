"""Nghiệp vụ Packing List — trái tim của bản demo.

Hai điều bản demo phải làm cho đúng:

1. **Không đóng quá số đã đặt.** Mỗi lần thêm hàng vào một Packing List đều phải
   so với phần còn lại của dòng hàng trên đơn. Đóng vượt là kho giao thừa hàng
   mà đơn không có căn cứ.

2. **Truy ngược được.** Mỗi dòng trong Packing List phải gắn với đúng
   `so_line_id`. Người giao hàng quét tem một kiện là hệ thống nói được kiện đó
   thuộc đơn nào, Packing List nào, dòng hàng nào.
"""

import datetime
import hashlib
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from models import (
    Delivery,
    PackingEvent,
    PackingLabel,
    PackingList,
    PackingListItem,
    PackingListPOD,
    SalesOrder,
    SalesOrderLine,
)
from services import don_hang_service
from services.loi import LoiNghiepVu

# Thứ tự các bước của một Packing List. Chỉ đi tới, không nhảy cóc.
CHUOI_TRANG_THAI = ["ready", "parked", "gate_in", "loaded", "dispatched", "delivered"]


def _bay_gio():
    return datetime.datetime.utcnow()


def _ma_pl(so_id, seq):
    return f"PL-{so_id.replace('SO-', '')}-{seq:02d}"


def _token(pl_id, so_kien):
    goc = f"{pl_id}|{so_kien}|{uuid.uuid4().hex}"
    return hashlib.sha256(goc.encode("utf-8")).hexdigest()[:32].upper()


def nap(db, pl_id):
    pl = (
        db.query(PackingList)
        .options(
            selectinload(PackingList.items).selectinload(PackingListItem.so_line),
            selectinload(PackingList.labels),
            selectinload(PackingList.events),
            selectinload(PackingList.order),
            selectinload(PackingList.pod),
        )
        .filter(PackingList.id == pl_id)
        .first()
    )
    if not pl:
        raise LoiNghiepVu("PL_NOT_FOUND", f"Không tìm thấy Packing List {pl_id}", 404)
    return pl


def ghi_su_kien(db, pl, loai, nguoi, ghi_chu=None):
    db.add(
        PackingEvent(
            packing_list_id=pl.id, event_type=loai, actor=nguoi, note=ghi_chu, occurred_at=_bay_gio()
        )
    )


def ra_dict(pl, day_du=True):
    don = pl.order
    data = {
        "id": pl.id,
        "so_id": pl.so_id,
        "po_number": don.po_number if don else None,
        "seq": pl.seq,
        "delivery_id": pl.delivery_id,
        "store_code": pl.store_code,
        "store_name": pl.store_name,
        "route_name": pl.route_name,
        "wave": pl.wave,
        "gate": pl.gate,
        "box_count": pl.box_count,
        "total_cases": pl.total_cases,
        "total_pieces": pl.total_pieces,
        "total_weight_kg": pl.total_weight_kg,
        "total_cube_m3": pl.total_cube_m3,
        "status": pl.status,
        "note": pl.note,
        "created_at": pl.created_at,
        "updated_at": pl.updated_at,
    }
    if not day_du:
        return data

    data["items"] = [
        {
            "id": it.id,
            "so_line_id": it.so_line_id,
            "so_id": pl.so_id,
            "line_no": it.so_line.line_no if it.so_line else None,
            "barcode": it.barcode,
            "product_code": it.product_code,
            "description": it.description,
            "description_en": it.description_en,
            "case_qty": it.case_qty,
            "piece_qty": it.piece_qty,
            "uom": it.uom,
            "weight_kg": it.weight_kg,
            "cube_m3": it.cube_m3,
            "note": it.note,
        }
        for it in pl.items
    ]
    data["labels"] = [
        {
            "id": lb.id,
            "package_no": lb.package_no,
            "package_total": lb.package_total,
            "qr_token": lb.qr_token,
            "status": lb.status,
            "printed_at": lb.printed_at,
            "reprint_count": lb.reprint_count,
            "scanned_at": lb.scanned_at,
        }
        for lb in pl.labels
    ]
    data["events"] = [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "occurred_at": ev.occurred_at,
            "actor": ev.actor,
            "note": ev.note,
        }
        for ev in pl.events
    ]
    if pl.pod:
        data["pod"] = {
            "received_by": pl.pod.received_by,
            "received_at": pl.pod.received_at,
            "result": pl.pod.result,
            "goods_condition": pl.pod.goods_condition,
            "note": pl.pod.note,
            "has_signature": bool(pl.pod.signature_data),
        }
    return data


def _tinh_tong(pl):
    pl.total_cases = sum(it.case_qty for it in pl.items)
    pl.total_pieces = sum(it.piece_qty for it in pl.items)
    pl.total_weight_kg = round(sum(it.weight_kg for it in pl.items), 3)
    pl.total_cube_m3 = round(sum(it.cube_m3 for it in pl.items), 3)


def _dung_tem(db, pl, so_kien):
    """Dựng lại bộ tem cho đúng số kiện. Tem đã quét thì KHÔNG đụng tới."""
    da_quet = [lb for lb in pl.labels if lb.scanned_at]
    if da_quet and so_kien < len(da_quet):
        raise LoiNghiepVu(
            "PL_LABEL_SCANNED",
            "Đã có kiện được quét nên không giảm số kiện xuống dưới số đó được",
            409,
        )
    for lb in list(pl.labels):
        if not lb.scanned_at:
            db.delete(lb)
    db.flush()
    con = sorted([lb for lb in pl.labels if lb.scanned_at], key=lambda x: x.package_no)
    for lb in con:
        lb.package_total = so_kien
    co_san = {lb.package_no for lb in con}
    for so in range(1, so_kien + 1):
        if so in co_san:
            continue
        db.add(
            PackingLabel(
                id=uuid.uuid4().hex.upper(),
                packing_list_id=pl.id,
                package_no=so,
                package_total=so_kien,
                qr_token=_token(pl.id, so),
                status="ready",
            )
        )
    pl.box_count = so_kien


def _kiem_con_lai(db, so_id, xin_them, bo_qua_pl=None):
    """`xin_them` là {so_line_id: (thùng, cái)}. Ném lỗi nếu vượt phần còn lại."""
    don = don_hang_service.nap(db, so_id)
    theo_dong = {d.id: d for d in don.lines}

    da_dong = {}
    hang = (
        db.query(
            PackingListItem.so_line_id,
            func.coalesce(func.sum(PackingListItem.case_qty), 0),
            func.coalesce(func.sum(PackingListItem.piece_qty), 0),
        )
        .join(PackingList, PackingList.id == PackingListItem.packing_list_id)
        .filter(PackingList.so_id == so_id, PackingList.status != "cancelled")
    )
    if bo_qua_pl:
        hang = hang.filter(PackingList.id != bo_qua_pl)
    for dong, thung, cai in hang.group_by(PackingListItem.so_line_id).all():
        da_dong[dong] = (int(thung or 0), int(cai or 0))

    vuot = []
    for dong_id, (thung, cai) in xin_them.items():
        dong = theo_dong.get(dong_id)
        if not dong:
            raise LoiNghiepVu(
                "PL_LINE_NOT_IN_SO",
                "Có dòng hàng không thuộc đơn này",
                400,
                {"so_line_id": dong_id},
            )
        da_t, da_c = da_dong.get(dong_id, (0, 0))
        if da_t + thung > dong.case_qty or da_c + cai > dong.piece_qty:
            vuot.append(
                {
                    "so_line_id": dong_id,
                    "line_no": dong.line_no,
                    "description": dong.description,
                    "ordered_case": dong.case_qty,
                    "packed_case": da_t,
                    "requested_case": thung,
                    "ordered_piece": dong.piece_qty,
                    "packed_piece": da_c,
                    "requested_piece": cai,
                }
            )
    if vuot:
        raise LoiNghiepVu(
            "PL_OVER_ORDERED",
            "Đóng vượt số lượng đã đặt trên đơn",
            409,
            {"lines": vuot},
        )
    return don, theo_dong


def _ghi_hang(db, pl, don, theo_dong, dong_vao):
    for it in list(pl.items):
        db.delete(it)
    db.flush()
    pl.items = []
    for d in dong_vao:
        dong = theo_dong[int(d["so_line_id"])]
        thung = int(d.get("case_qty") or 0)
        cai = int(d.get("piece_qty") or 0)
        pl.items.append(
            PackingListItem(
                packing_list_id=pl.id,
                so_line_id=dong.id,
                barcode=dong.barcode,
                product_code=dong.product_code,
                description=dong.description,
                description_en=dong.description_en,
                case_qty=thung,
                piece_qty=cai,
                uom=dong.uom,
                weight_kg=round(dong.weight_kg * thung, 3),
                cube_m3=round(dong.cube_m3 * thung, 3),
                note=d.get("note"),
            )
        )
    db.flush()


def _gom_xin_them(dong_vao):
    gom = {}
    for d in dong_vao:
        khoa = int(d.get("so_line_id") or 0)
        if not khoa:
            raise LoiNghiepVu(
                "PL_ITEM_NO_SO_LINE",
                "Mỗi dòng hàng trong Packing List phải chỉ rõ thuộc dòng nào của đơn",
            )
        thung = int(d.get("case_qty") or 0)
        cai = int(d.get("piece_qty") or 0)
        if thung < 0 or cai < 0:
            raise LoiNghiepVu("PL_ITEM_QTY_NEGATIVE", "Số lượng đóng gói không được âm")
        if thung + cai <= 0:
            raise LoiNghiepVu("PL_ITEM_QTY_ZERO", "Mỗi dòng hàng phải có số lượng lớn hơn 0")
        cu_t, cu_c = gom.get(khoa, (0, 0))
        gom[khoa] = (cu_t + thung, cu_c + cai)
    if not gom:
        raise LoiNghiepVu("PL_NO_ITEMS", "Packing List phải có ít nhất một dòng hàng")
    return gom


def tao(db, so_id, payload, nguoi):
    dong_vao = payload.get("items") or []
    xin = _gom_xin_them(dong_vao)
    don, theo_dong = _kiem_con_lai(db, so_id, xin)
    if don.status == "cancelled":
        raise LoiNghiepVu("SO_CANCELLED", "Đơn đã huỷ nên không đóng gói được", 409)

    seq = (
        db.query(func.coalesce(func.max(PackingList.seq), 0))
        .filter(PackingList.so_id == so_id)
        .scalar()
        or 0
    ) + 1

    pl = PackingList(
        id=_ma_pl(so_id, seq),
        so_id=so_id,
        seq=seq,
        store_code=payload.get("store_code") or don.ship_to_code,
        store_name=payload.get("store_name") or don.ship_to_name,
        route_name=payload.get("route_name"),
        wave=payload.get("wave"),
        gate=payload.get("gate"),
        note=payload.get("note"),
        status="ready",
        created_by=nguoi,
    )
    db.add(pl)
    db.flush()

    _ghi_hang(db, pl, don, theo_dong, dong_vao)
    _tinh_tong(pl)
    _dung_tem(db, pl, max(int(payload.get("box_count") or pl.total_cases or 1), 1))
    ghi_su_kien(db, pl, "created", nguoi, f"Tạo từ đơn {so_id}")
    don_hang_service.cap_nhat_trang_thai_theo_dong_goi(db, so_id)
    db.flush()
    return nap(db, pl.id)


def sua(db, pl_id, payload, nguoi):
    pl = nap(db, pl_id)
    if pl.status not in ("ready", "parked"):
        raise LoiNghiepVu(
            "PL_LOCKED",
            "Packing List đã qua cổng nên không sửa hàng hoá được nữa",
            409,
            {"status": pl.status},
        )
    dong_vao = payload.get("items") or []
    xin = _gom_xin_them(dong_vao)
    don, theo_dong = _kiem_con_lai(db, pl.so_id, xin, bo_qua_pl=pl.id)

    for khoa in ("store_code", "store_name", "route_name", "wave", "gate", "note"):
        if khoa in payload:
            setattr(pl, khoa, payload.get(khoa))

    _ghi_hang(db, pl, don, theo_dong, dong_vao)
    _tinh_tong(pl)
    _dung_tem(db, pl, max(int(payload.get("box_count") or pl.box_count or 1), 1))
    ghi_su_kien(db, pl, "updated", nguoi)
    don_hang_service.cap_nhat_trang_thai_theo_dong_goi(db, pl.so_id)
    db.flush()
    return nap(db, pl.id)


def tao_tu_dong(db, so_id, so_luong, nguoi):
    """Chia phần CÒN LẠI của đơn thành `so_luong` Packing List.

    Chia đều nhưng KHÔNG được làm sai tổng: phần dư được rải vào các phiếu đầu,
    mỗi phiếu một đơn vị, nên cộng lại vẫn đúng bằng số còn lại của đơn.
    """
    if so_luong < 1 or so_luong > 50:
        raise LoiNghiepVu("PL_COUNT_RANGE", "Số Packing List phải từ 1 đến 50")

    don = don_hang_service.nap(db, so_id)
    if don.status == "cancelled":
        raise LoiNghiepVu("SO_CANCELLED", "Đơn đã huỷ nên không đóng gói được", 409)
    da_dong = don_hang_service.da_dong_theo_dong(db, so_id)

    con_lai = []
    for dong in don.lines:
        da_t, da_c = da_dong.get(dong.id, (0, 0))
        con_lai.append((dong, max(dong.case_qty - da_t, 0), max(dong.piece_qty - da_c, 0)))
    if all(t == 0 and c == 0 for _, t, c in con_lai):
        raise LoiNghiepVu("PL_NOTHING_LEFT", "Đơn đã đóng đủ hàng, không còn gì để chia", 409)

    phan = [[] for _ in range(so_luong)]
    for dong, thung, cai in con_lai:
        if thung <= 0 and cai <= 0:
            continue
        for chi_so in range(so_luong):
            t = thung // so_luong + (1 if chi_so < thung % so_luong else 0)
            c = cai // so_luong + (1 if chi_so < cai % so_luong else 0)
            if t or c:
                phan[chi_so].append({"so_line_id": dong.id, "case_qty": t, "piece_qty": c})

    ket_qua = []
    for nhom in phan:
        if not nhom:
            continue
        ket_qua.append(tao(db, so_id, {"items": nhom}, nguoi))
    if not ket_qua:
        raise LoiNghiepVu("PL_NOTHING_LEFT", "Không chia được phiếu nào từ phần còn lại", 409)
    return ket_qua


def doi_trang_thai(db, pl_id, trang_thai_moi, nguoi, ghi_chu=None):
    pl = nap(db, pl_id)
    if pl.status == "cancelled":
        raise LoiNghiepVu("PL_CANCELLED", "Packing List đã huỷ", 409)
    if trang_thai_moi not in CHUOI_TRANG_THAI:
        raise LoiNghiepVu("PL_STATUS_UNKNOWN", f"Trạng thái không hợp lệ: {trang_thai_moi}")

    hien = CHUOI_TRANG_THAI.index(pl.status)
    moi = CHUOI_TRANG_THAI.index(trang_thai_moi)
    if moi <= hien:
        raise LoiNghiepVu(
            "PL_STATUS_BACKWARD",
            "Không lùi trạng thái của Packing List",
            409,
            {"current": pl.status, "requested": trang_thai_moi},
        )
    if moi > hien + 1:
        raise LoiNghiepVu(
            "PL_STATUS_SKIP",
            "Phải đi lần lượt từng bước, không nhảy cóc",
            409,
            {"current": pl.status, "requested": trang_thai_moi},
        )
    if trang_thai_moi == "loaded" and not pl.delivery_id:
        raise LoiNghiepVu(
            "PL_NO_DELIVERY",
            "Phải xếp Packing List lên một chuyến giao hàng trước khi bốc hàng",
            409,
        )
    if trang_thai_moi == "delivered" and not pl.pod:
        raise LoiNghiepVu(
            "PL_NO_POD",
            "Phải nộp bằng chứng giao hàng trước khi chuyển sang đã giao",
            409,
        )

    pl.status = trang_thai_moi
    ghi_su_kien(db, pl, trang_thai_moi, nguoi, ghi_chu)
    don_hang_service.cap_nhat_trang_thai_theo_dong_goi(db, pl.so_id)
    db.flush()
    return nap(db, pl.id)


def huy(db, pl_id, ly_do, nguoi):
    pl = nap(db, pl_id)
    if pl.status in ("dispatched", "delivered"):
        raise LoiNghiepVu(
            "PL_ALREADY_OUT", "Packing List đã rời bãi nên không huỷ được", 409
        )
    pl.status = "cancelled"
    pl.delivery_id = None
    ghi_su_kien(db, pl, "cancelled", nguoi, ly_do)
    don_hang_service.cap_nhat_trang_thai_theo_dong_goi(db, pl.so_id)
    db.flush()
    return nap(db, pl.id)


def in_tem(db, pl_id, nguoi, in_lai=False):
    pl = nap(db, pl_id)
    for lb in pl.labels:
        if lb.printed_at and not in_lai:
            continue
        if lb.printed_at:
            lb.reprint_count += 1
        lb.printed_at = _bay_gio()
        lb.status = "printed"
    ghi_su_kien(db, pl, "label_printed", nguoi, "In lại" if in_lai else None)
    db.flush()
    return nap(db, pl.id)


def quet_tem(db, token, nguoi, buoc=None):
    """Quét một tem QR. Đây là đường mà người ở chốt và người giao hàng dùng.

    Trả về đủ dây truy ngược: kiện -> Packing List -> đơn hàng -> từng dòng hàng.
    """
    lb = db.query(PackingLabel).filter(PackingLabel.qr_token == (token or "").strip()).first()
    if not lb:
        raise LoiNghiepVu("LABEL_NOT_FOUND", "Không nhận ra tem QR này", 404)
    pl = nap(db, lb.packing_list_id)
    if pl.status == "cancelled":
        raise LoiNghiepVu("PL_CANCELLED", "Packing List của tem này đã huỷ", 409)

    lan_dau = lb.scanned_at is None
    if lan_dau:
        lb.scanned_at = _bay_gio()
        lb.status = "scanned"
        ghi_su_kien(db, pl, "label_scanned", nguoi, f"Kiện {lb.package_no}/{lb.package_total}")

    # Quét đủ kiện thì tự bước sang trạng thái kế tiếp — quét lặp không làm tăng.
    da_quet = sum(1 for x in pl.labels if x.scanned_at)
    if buoc and da_quet >= pl.box_count:
        try:
            doi_trang_thai(db, pl.id, buoc, nguoi, "Quét đủ kiện")
        except LoiNghiepVu:
            pass
    db.flush()
    pl = nap(db, pl.id)
    return {
        "label": {
            "package_no": lb.package_no,
            "package_total": lb.package_total,
            "first_scan": lan_dau,
            "scanned_count": da_quet,
        },
        "packing_list": ra_dict(pl),
        "sales_order": don_hang_service.ra_dict(db, pl.order),
    }


def danh_sach(db, q=None, trang_thai=None, so_id=None, delivery_id=None, trang=1, moi_trang=25):
    cau = db.query(PackingList).options(selectinload(PackingList.order))
    if trang_thai:
        cau = cau.filter(PackingList.status == trang_thai)
    if so_id:
        cau = cau.filter(PackingList.so_id == so_id)
    if delivery_id:
        cau = cau.filter(PackingList.delivery_id == delivery_id)
    if q:
        tim = f"%{q.strip()}%"
        cau = cau.filter(
            PackingList.id.ilike(tim)
            | PackingList.so_id.ilike(tim)
            | PackingList.store_name.ilike(tim)
            | PackingList.route_name.ilike(tim)
        )
    tong = cau.count()
    hang = (
        cau.order_by(PackingList.created_at.desc())
        .offset((trang - 1) * moi_trang)
        .limit(moi_trang)
        .all()
    )
    return {
        "items": [ra_dict(pl, day_du=False) for pl in hang],
        "total": tong,
        "page": trang,
        "page_size": moi_trang,
    }


def thong_ke(db):
    dem = dict(
        db.query(PackingList.status, func.count(PackingList.id))
        .group_by(PackingList.status)
        .all()
    )
    return {
        "total": sum(dem.values()),
        "ready": dem.get("ready", 0),
        "parked": dem.get("parked", 0),
        "gate_in": dem.get("gate_in", 0),
        "loaded": dem.get("loaded", 0),
        "dispatched": dem.get("dispatched", 0),
        "delivered": dem.get("delivered", 0),
        "cancelled": dem.get("cancelled", 0),
    }
