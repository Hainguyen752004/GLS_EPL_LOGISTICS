# -*- coding: utf-8 -*-
"""BÀN GIAO cho bên công nợ (anh Khang): header + detail của một DO đã hoàn tất.

Yêu cầu nguyên văn: *"em nhả header và detail của DO hoàn tất cho a là được —
truyền ID header DO thì lấy luôn cả header và detail của nó"*.

Một điểm cuối, một mã DO, trả về đúng hai khối:

  · `header` : DO là gì (khách, tuyến, báo giá gốc, chuyến, xe, tài xế, mốc giao,
               POD), và các con số tổng (cước khách, giá thành chốt/thực tế, khách
               trả thêm, lợi nhuận).
  · `details`: TỪNG DÒNG thu / chi — mỗi dòng mang `acc_code` (mã tài khoản kế
               toán của bên đó, chọn trên công thức giá thành), loại khoản, số kế
               hoạch, số thực tế, khách trả thêm, chênh lệch, nguồn.

Chỉ trả khi DO đã `delivered` (hồ sơ đã chốt): trả sớm hơn thì bên kia lập phiếu
trên số chưa chốt. Toàn bộ số đọc lại từ `get_delivery_order_closeout` — cùng
một nguồn với khối "Hồ sơ đã hoàn tất" trên màn, nên không có hai con số khác
nhau cho cùng một DO.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from models import DeliveryOrder, DeliveryOrderCloseout, TransportTrip, TripDeliveryOrder
from routes.finance_master_routes import require_authenticated_principal
from services.errors import DomainError, conflict, raise_http
import datetime as dt

router = APIRouter(dependencies=[Depends(require_authenticated_principal)])

TRANG_THAI_DA_HOAN_TAT = ("delivered", "completed", "settled")


def _chuyen_con_mo(db, do_id):
    """Mã các chuyến của DO chưa đóng (không phải `completed` / `cancelled`).

    CHỦ DỰ ÁN CHỐT (11/09): *"phải đến điểm cuối và hoàn tất mới quăng qua cho anh Khang"*.
    Một chuyến nhiều điểm giao thì DO hạ ở điểm đầu đã `delivered` trong khi xe còn chạy
    tiếp; bàn giao ngay lúc đó là đưa cho bên công nợ một hồ sơ mà chuyến của nó chưa kết
    thúc — phụ phí, chi phí thực tế của chuyến còn có thể đổi. Nên hồ sơ chỉ được nhả khi
    MỌI chuyến chở DO đó đã đóng.
    """
    return db.scalars(
        __import__("sqlalchemy").select(TripDeliveryOrder.trip_id)
        .join(TransportTrip, TransportTrip.id == TripDeliveryOrder.trip_id)
        .where(TripDeliveryOrder.do_id == do_id,
               TransportTrip.status.notin_(("completed", "cancelled")))
    ).all()


def _gon(d, *khoa):
    return {k: (d or {}).get(k) for k in khoa}


def dong_goi_ban_giao(closeout):
    """Từ gói closeout (đã có trên màn) rút ra header + details cho bên công nợ."""
    do = closeout.get("delivery_order") or {}
    trip = closeout.get("trip") or {}
    com = closeout.get("commercials") or {}
    pods = closeout.get("pod_records") or []
    tong = closeout.get("ledger_totals") or {}
    header = {
        "do_id": closeout.get("do_id") or do.get("id"),
        "status": closeout.get("status") or do.get("canonical_status"),
        # `currency` = tiền của phần THU (khách trả) — giữ nghĩa cũ. Hai khoá dưới nói
        # rõ từng bên: chi phí thực tế của chuyến ghi bằng tiền chức năng (VNĐ) trong
        # khi cước khách theo báo giá có thể là USD / LAK.
        "currency": closeout.get("currency") or "VND",
        "currency_thu": com.get("currency_thu") or closeout.get("currency") or "VND",
        "currency_chi": com.get("currency_chi") or "VND",
        "fx_rate": com.get("fx_rate"),
        "fx_rate_source": com.get("fx_rate_source") or "",
        "customer_id": closeout.get("customer_id") or do.get("customer_id"),
        "quotation_id": closeout.get("quotation_id"),
        "route": _gon(closeout.get("route"), "id", "name", "origin", "destination", "distance_km"),
        "origin": do.get("origin"), "destination": do.get("destination"),
        "weight_kg": do.get("weight_kg"), "volume_m3": do.get("volume_m3"), "pallet_count": do.get("pallet_count"),
        "pickup_window_start": do.get("pickup_window_start"), "pickup_window_end": do.get("pickup_window_end"),
        "delivery_window_start": do.get("delivery_window_start"), "delivery_window_end": do.get("delivery_window_end"),
        "trip_id": trip.get("id"), "trip_status": trip.get("status"),
        "vehicle_id": closeout.get("vehicle_id") or trip.get("vehicle_id") or do.get("vehicle_id"),
        "driver_id": closeout.get("driver_id") or trip.get("driver_id") or do.get("driver_id"),
        "co_driver_id": do.get("co_driver"),
        "actual_departure_at": trip.get("actual_departure_at"),
        "actual_arrival_at": trip.get("actual_arrival_at"),
        "pod_count": len(pods),
        "pod_signed_at": max([p.get("delivery_time") for p in pods if p.get("delivery_time")] or [None]),
        "pod_receiver": next((p.get("receiver_name") for p in pods if p.get("receiver_name")), None),
        # Tổng tiền — cùng nguồn với khối Hồ sơ đã hoàn tất.
        "selling_price": com.get("base_selling_price"),
        "customer_surcharge_total": com.get("customer_surcharge_total"),
        "final_selling_price": com.get("final_selling_price"),
        "quoted_cost": com.get("quoted_cost"),
        "quoted_cost_currency": com.get("quoted_cost_currency") or com.get("currency_thu") or "VND",
        "actual_cost_total": com.get("actual_cost_total"),
        "actual_cost_total_currency": com.get("actual_cost_total_currency") or com.get("currency_chi") or "VND",
        "actual_cost_total_quy_doi": com.get("cost_basis_quy_doi"),
        "margin_amount": com.get("margin_amount"),
        "margin_percent": com.get("margin_percent"),
        "margin_currency": com.get("margin_currency") or com.get("currency_thu") or "VND",
        "margin_unavailable_reason": com.get("margin_unavailable_reason") or "",
        # Đơn vị cước và số lượng tính tiền: thiếu hai trường này thì bên công nợ không
        # dựng được dòng hoá đơn, vì không biết giá tính theo chuyến hay theo kg.
        "price_basis": do.get("price_basis") or "",
        "billed_qty": do.get("billed_qty"),
        "unit_price": do.get("unit_price"),
        "ledger_totals": tong,
        "cost_formula": _gon(closeout.get("cost_formula"), "id", "name", "currency"),
    }
    details = []
    for i, l in enumerate(closeout.get("ledger_lines") or [], start=1):
        details.append({
            "line_no": i,
            "kind": l.get("kind"),                          # thu | chi
            "acc_code": l.get("acc_code") or l.get("cost_index") or "",
            "missing_acc_code": not (l.get("acc_code") or l.get("cost_index")),
            "charge_type": l.get("charge_type"),
            "name": l.get("name"),
            "planned_amount": l.get("planned_amount"),
            "actual_amount": l.get("actual_amount"),
            "customer_extra": l.get("customer_extra"),
            "variance": l.get("variance"),
            "currency": l.get("currency") or "VND",
            "source": l.get("source"),
            "calculation": l.get("calculation"),
            "ref_id": l.get("actual_cost_line_id") or l.get("adjustment_id"),
        })
    return {"header": header, "details": details}


@router.get("/api/handover/delivery-orders/{do_id}")
def ban_giao_do(do_id: str, request: Request, db: Session = Depends(get_db)):
    from routes.delivery_routes import get_delivery_order_closeout
    do = db.get(DeliveryOrder, do_id)
    if do is None:
        raise_http(DomainError("DELIVERY_ORDER_NOT_FOUND", "Không tìm thấy lệnh giao hàng %s." % do_id, 404))
    if str(do.canonical_status or "").lower() not in TRANG_THAI_DA_HOAN_TAT:
        raise_http(conflict("DO_NOT_COMPLETED",
                            "Lệnh %s đang ở trạng thái %s — chỉ bàn giao DO đã hoàn tất (delivered)."
                            % (do_id, do.canonical_status)))
    chuyen_mo = _chuyen_con_mo(db, do_id)
    if chuyen_mo:
        raise_http(conflict("DO_TRIP_CHUA_DONG",
                            "Lệnh %s đã giao nhưng chuyến %s còn chạy tới điểm giao khác — hồ sơ chỉ bàn "
                            "giao khi chuyến đã tới điểm cuối và hoàn tất." % (do_id, ", ".join(chuyen_mo)),
                            ["delivery-completion"]))
    try:
        # Handler closeout là hàm đồng bộ thường (chạy threadpool) — KHÔNG await: 11/09 một chữ await sót
        # ở đây làm API bàn giao chi tiết trả 500 cho mọi DO.
        goi = get_delivery_order_closeout(do_id, request, db)
    except DomainError as loi:
        raise_http(loi)
    closeout = goi.get("data", goi) if isinstance(goi, dict) else goi
    return {"message": "Hồ sơ bàn giao của %s." % do_id, "data": dong_goi_ban_giao(closeout)}


def _ngay(chuoi, ten):
    if not chuoi:
        return None
    try:
        return dt.datetime.fromisoformat(str(chuoi).strip()[:19])
    except ValueError:
        raise_http(DomainError("INVALID_DATE", "Tham số %s phải là ngày ISO (YYYY-MM-DD)." % ten, 422))


@router.get("/api/handover/delivery-orders")
def danh_sach_ban_giao(
    request: Request,
    customer_id: Optional[str] = Query(None, description="Chỉ lấy DO của một khách"),
    completed_from: Optional[str] = Query(None, description="Hoàn tất từ ngày (ISO, gồm cả ngày đó)"),
    completed_to: Optional[str] = Query(None, description="Hoàn tất đến ngày (ISO, gồm cả ngày đó)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """DANH SÁCH DO đã hoàn tất — bước quét của bên công nợ, trước khi gọi chi tiết theo `do_id`.

    Mỗi dòng là header RÚT GỌN (không có sổ thu–chi) đọc từ `delivery_order_closeouts`: DO, khách,
    báo giá gốc, giá bán cuối đã chốt, tiền tệ, lúc hoàn tất, và `detail_url` để lấy header + detail
    đầy đủ. Mới hoàn tất trước. Chỉ những DO đã chốt hồ sơ mới xuất hiện — cùng nguyên tắc với API chi
    tiết: không nhả số chưa chốt.
    """
    tu, den = _ngay(completed_from, "completed_from"), _ngay(completed_to, "completed_to")
    # CHỈ DO MÀ MỌI CHUYẾN CHỞ NÓ ĐÃ ĐÓNG (xem `_chuyen_con_mo`). Viết bằng NOT EXISTS để
    # phân trang và `total` vẫn đúng, không lọc sau khi đã cắt trang.
    from sqlalchemy import exists, and_
    con_mo = exists().where(and_(
        TripDeliveryOrder.do_id == DeliveryOrderCloseout.do_id,
        TransportTrip.id == TripDeliveryOrder.trip_id,
        TransportTrip.status.notin_(("completed", "cancelled")),
    ))
    q = (db.query(DeliveryOrderCloseout, DeliveryOrder)
         .join(DeliveryOrder, DeliveryOrder.id == DeliveryOrderCloseout.do_id)
         .filter(~con_mo))
    if customer_id:
        q = q.filter(DeliveryOrder.customer_id == customer_id)
    if tu:
        q = q.filter(DeliveryOrderCloseout.completed_at >= tu.replace(tzinfo=dt.timezone.utc))
    if den:
        q = q.filter(DeliveryOrderCloseout.completed_at < (den + dt.timedelta(days=1)).replace(tzinfo=dt.timezone.utc))
    tong = q.count()
    dong = (q.order_by(DeliveryOrderCloseout.completed_at.desc(), DeliveryOrderCloseout.do_id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    items = [{
        "do_id": c.do_id,
        "status": d.canonical_status,
        "customer_id": d.customer_id,
        "quotation_id": d.quotation_id,
        "route_id": d.route_id,
        "vehicle_id": d.vehicle_id,
        "driver_id": d.driver_id,
        "selling_price": float(c.base_selling_price_snapshot or 0),
        "customer_surcharge_total": float(c.surcharge_total or 0),
        "final_selling_price": float(c.final_selling_price or 0),
        "currency": c.currency_code,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        "completed_by": c.completed_by,
        "detail_url": "/api/handover/delivery-orders/%s" % c.do_id,
    } for c, d in dong]
    return {"message": "Danh sách %d lệnh giao hàng đã hoàn tất (trang %d)." % (tong, page),
            "data": {"items": items, "total": tong, "page": page, "page_size": page_size}}
