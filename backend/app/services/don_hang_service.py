"""Nghiệp vụ Đơn hàng khách (Sale Order).

Đơn hàng là NGUỒN của mọi Packing List. Mỗi dòng hàng trên đơn có số lượng đặt;
đóng gói bao nhiêu cũng không được vượt số đó. Phần còn lại chưa đóng (`con_lai`)
là con số mà màn đóng gói dựa vào.
"""

import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from models import Customer, PackingList, PackingListItem, SalesOrder, SalesOrderLine
from services.loi import LoiNghiepVu


def _ma_don(db):
    nam = datetime.datetime.utcnow().year
    dem = db.query(func.count(SalesOrder.id)).filter(SalesOrder.id.like(f"SO-{nam}-%")).scalar() or 0
    return f"SO-{nam}-{dem + 1:04d}"


def nap(db, so_id):
    don = (
        db.query(SalesOrder)
        .options(selectinload(SalesOrder.lines))
        .filter(SalesOrder.id == so_id)
        .first()
    )
    if not don:
        raise LoiNghiepVu("SO_NOT_FOUND", f"Không tìm thấy đơn hàng {so_id}", 404)
    return don


def da_dong_theo_dong(db, so_id):
    """Trả về {so_line_id: (đã đóng thùng, đã đóng cái)}.

    Chỉ tính các Packing List CÒN HIỆU LỰC. Packing List đã huỷ phải được trả số
    lượng về cho đơn, nếu không thì huỷ một lần là mất hàng khỏi đơn vĩnh viễn.
    """
    hang = (
        db.query(
            PackingListItem.so_line_id,
            func.coalesce(func.sum(PackingListItem.case_qty), 0),
            func.coalesce(func.sum(PackingListItem.piece_qty), 0),
        )
        .join(PackingList, PackingList.id == PackingListItem.packing_list_id)
        .filter(PackingList.so_id == so_id, PackingList.status != "cancelled")
        .group_by(PackingListItem.so_line_id)
        .all()
    )
    return {dong: (int(thung or 0), int(cai or 0)) for dong, thung, cai in hang}


def _dong_ra_dict(dong, da_dong):
    thung_da, cai_da = da_dong.get(dong.id, (0, 0))
    return {
        "id": dong.id,
        "line_no": dong.line_no,
        "barcode": dong.barcode,
        "product_code": dong.product_code,
        "description": dong.description,
        "description_en": dong.description_en,
        "vat_kind": dong.vat_kind,
        "vat_percent": dong.vat_percent,
        "pack_size": dong.pack_size,
        "unit_quantity": dong.unit_quantity,
        "uom": dong.uom,
        "case_qty": dong.case_qty,
        "piece_qty": dong.piece_qty,
        "packed_case_qty": thung_da,
        "packed_piece_qty": cai_da,
        "remaining_case_qty": max(dong.case_qty - thung_da, 0),
        "remaining_piece_qty": max(dong.piece_qty - cai_da, 0),
        "unit_price": dong.unit_price,
        "discount": dong.discount,
        "amount": dong.amount,
        "weight_kg": dong.weight_kg,
        "cube_m3": dong.cube_m3,
    }


def ra_dict(db, don, kem_dong=True):
    da_dong = da_dong_theo_dong(db, don.id) if kem_dong else {}
    so_pl = (
        db.query(func.count(PackingList.id))
        .filter(PackingList.so_id == don.id, PackingList.status != "cancelled")
        .scalar()
        or 0
    )
    data = {
        "id": don.id,
        "po_number": don.po_number,
        "order_date": don.order_date,
        "shipping_date": don.shipping_date,
        "customer_id": don.customer_id,
        "ship_to_code": don.ship_to_code,
        "ship_to_name": don.ship_to_name,
        "ship_to_address": don.ship_to_address,
        "vendor_code": don.vendor_code,
        "vendor_name": don.vendor_name,
        "vendor_address": don.vendor_address,
        "tax_number": don.tax_number,
        "currency": don.currency,
        "zone": don.zone,
        "note": don.note,
        "status": don.status,
        "packing_list_count": int(so_pl),
        "created_at": don.created_at,
    }
    if kem_dong:
        dong_list = [_dong_ra_dict(d, da_dong) for d in don.lines]
        data["lines"] = dong_list
        data["total_amount"] = sum(d["amount"] for d in dong_list)
        data["total_case_qty"] = sum(d["case_qty"] for d in dong_list)
        data["remaining_case_qty"] = sum(d["remaining_case_qty"] for d in dong_list)
        data["remaining_piece_qty"] = sum(d["remaining_piece_qty"] for d in dong_list)
        data["fully_packed"] = data["remaining_case_qty"] == 0 and data["remaining_piece_qty"] == 0
    return data


def danh_sach(db, q=None, trang_thai=None, trang=1, moi_trang=25):
    cau = db.query(SalesOrder)
    if trang_thai:
        cau = cau.filter(SalesOrder.status == trang_thai)
    if q:
        tim = f"%{q.strip()}%"
        cau = cau.filter(
            SalesOrder.id.ilike(tim)
            | SalesOrder.po_number.ilike(tim)
            | SalesOrder.ship_to_name.ilike(tim)
            | SalesOrder.vendor_name.ilike(tim)
        )
    tong = cau.count()
    hang = (
        cau.order_by(SalesOrder.created_at.desc())
        .offset((trang - 1) * moi_trang)
        .limit(moi_trang)
        .all()
    )
    return {
        "items": [ra_dict(db, d, kem_dong=False) for d in hang],
        "total": tong,
        "page": trang,
        "page_size": moi_trang,
    }


def tao(db, payload, nguoi):
    dong_vao = payload.get("lines") or []
    if not dong_vao:
        raise LoiNghiepVu("SO_NO_LINES", "Đơn hàng phải có ít nhất một dòng hàng")

    po = (payload.get("po_number") or "").strip()
    if not po:
        raise LoiNghiepVu("SO_NO_PO", "Đơn hàng phải có số PO")
    if db.query(SalesOrder).filter(SalesOrder.po_number == po).first():
        raise LoiNghiepVu("SO_PO_DUPLICATE", f"Số PO {po} đã tồn tại", 409)

    # Chủ dự án chốt: thông tin khách và nhà cung cấp phải CHỌN từ danh mục,
    # không gõ tay trên phiếu. Có id thì lấy từ danh mục và ghi đè mọi ô gõ tay.
    khach = None
    if payload.get("customer_id"):
        khach = db.query(Customer).filter(Customer.id == payload["customer_id"]).first()
        if not khach:
            raise LoiNghiepVu("CUST_NOT_FOUND", "Không tìm thấy khách hàng đã chọn", 404)
        payload = {
            **payload,
            "ship_to_code": khach.code,
            "ship_to_name": khach.name,
            "ship_to_address": khach.address,
        }
    if payload.get("vendor_id"):
        ncc = db.query(Customer).filter(Customer.id == payload["vendor_id"]).first()
        if not ncc:
            raise LoiNghiepVu("CUST_NOT_FOUND", "Không tìm thấy nhà cung cấp đã chọn", 404)
        payload = {
            **payload,
            "vendor_code": ncc.code,
            "vendor_name": ncc.name,
            "vendor_address": ncc.address,
            "tax_number": payload.get("tax_number") or ncc.tax_number,
        }
    if not khach:
        raise LoiNghiepVu("SO_NO_CUSTOMER", "Đơn hàng phải chọn khách hàng từ danh mục")

    don = SalesOrder(
        id=_ma_don(db),
        po_number=po,
        order_date=payload.get("order_date"),
        shipping_date=payload.get("shipping_date"),
        customer_id=payload.get("customer_id"),
        ship_to_code=payload.get("ship_to_code"),
        ship_to_name=payload.get("ship_to_name"),
        ship_to_address=payload.get("ship_to_address"),
        vendor_code=payload.get("vendor_code"),
        vendor_name=payload.get("vendor_name"),
        vendor_address=payload.get("vendor_address"),
        tax_number=payload.get("tax_number"),
        currency=payload.get("currency") or "LAK",
        zone=payload.get("zone"),
        note=payload.get("note"),
        status="new",
        created_by=nguoi,
    )
    db.add(don)
    db.flush()

    for chi_so, d in enumerate(dong_vao, start=1):
        mo_ta = (d.get("description") or "").strip()
        if not mo_ta:
            raise LoiNghiepVu("SO_LINE_NO_DESC", f"Dòng {chi_so} thiếu mô tả hàng")
        thung = int(d.get("case_qty") or 0)
        cai = int(d.get("piece_qty") or 0)
        if thung < 0 or cai < 0:
            raise LoiNghiepVu("SO_LINE_QTY_NEGATIVE", f"Dòng {chi_so} có số lượng âm")
        if thung + cai <= 0:
            raise LoiNghiepVu("SO_LINE_QTY_ZERO", f"Dòng {chi_so} phải có số lượng lớn hơn 0")
        db.add(
            SalesOrderLine(
                so_id=don.id,
                line_no=int(d.get("line_no") or chi_so),
                barcode=d.get("barcode"),
                product_code=d.get("product_code"),
                description=mo_ta,
                description_en=d.get("description_en"),
                vat_kind=d.get("vat_kind"),
                vat_percent=float(d.get("vat_percent") or 0),
                pack_size=int(d.get("pack_size") or 1),
                unit_quantity=d.get("unit_quantity"),
                case_qty=thung,
                piece_qty=cai,
                uom=d.get("uom") or "CT",
                unit_price=float(d.get("unit_price") or 0),
                discount=float(d.get("discount") or 0),
                amount=float(d.get("amount") or 0),
                weight_kg=float(d.get("weight_kg") or 0),
                cube_m3=float(d.get("cube_m3") or 0),
            )
        )
    db.flush()
    db.refresh(don)
    return don


def cap_nhat_trang_thai_theo_dong_goi(db, so_id):
    """Trạng thái đơn được TÍNH RA, không ai đặt tay.

    Đặt tay là mở đường cho đơn nói một đằng còn Packing List nói một nẻo. Ở đây
    trạng thái luôn suy ra từ dữ liệu thật: đã đóng hết chưa, đã có chuyến chưa,
    đã giao xong chưa.
    """
    don = nap(db, so_id)
    if don.status == "cancelled":
        return don

    ds_pl = (
        db.query(PackingList)
        .filter(PackingList.so_id == so_id, PackingList.status != "cancelled")
        .all()
    )
    if not ds_pl:
        don.status = "new"
        return don

    da_dong = da_dong_theo_dong(db, so_id)
    du_hang = all(
        da_dong.get(d.id, (0, 0))[0] >= d.case_qty and da_dong.get(d.id, (0, 0))[1] >= d.piece_qty
        for d in don.lines
    )

    if all(pl.status == "delivered" for pl in ds_pl) and du_hang:
        don.status = "delivered"
    elif any(pl.status in ("dispatched", "delivered") for pl in ds_pl):
        don.status = "delivering"
    elif du_hang:
        don.status = "packed"
    else:
        don.status = "packing"
    return don


def huy(db, so_id, ly_do, nguoi):
    don = nap(db, so_id)
    dang_chay = [
        pl
        for pl in db.query(PackingList).filter(PackingList.so_id == so_id).all()
        if pl.status not in ("cancelled", "ready")
    ]
    if dang_chay:
        raise LoiNghiepVu(
            "SO_HAS_ACTIVE_PACKING",
            "Đơn đã có Packing List rời bãi nên không huỷ được",
            409,
            {"packing_lists": [pl.id for pl in dang_chay]},
        )
    don.status = "cancelled"
    don.note = ((don.note or "") + f"\n[HUỶ] {ly_do or ''} ({nguoi})").strip()
    return don
