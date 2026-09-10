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
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from models import DeliveryOrder
from routes.finance_master_routes import require_authenticated_principal
from services.errors import DomainError, conflict, raise_http

router = APIRouter(dependencies=[Depends(require_authenticated_principal)])

TRANG_THAI_DA_HOAN_TAT = ("delivered", "completed", "settled")


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
        "currency": closeout.get("currency") or "VND",
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
        "actual_cost_total": com.get("actual_cost_total"),
        "margin_amount": com.get("margin_amount"),
        "margin_percent": com.get("margin_percent"),
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
            "source": l.get("source"),
            "calculation": l.get("calculation"),
            "ref_id": l.get("actual_cost_line_id") or l.get("adjustment_id"),
        })
    return {"header": header, "details": details}


@router.get("/api/handover/delivery-orders/{do_id}")
async def ban_giao_do(do_id: str, request: Request, db: Session = Depends(get_db)):
    from routes.delivery_routes import get_delivery_order_closeout
    do = db.get(DeliveryOrder, do_id)
    if do is None:
        raise_http(DomainError("DELIVERY_ORDER_NOT_FOUND", "Không tìm thấy lệnh giao hàng %s." % do_id, 404))
    if str(do.canonical_status or "").lower() not in TRANG_THAI_DA_HOAN_TAT:
        raise_http(conflict("DO_NOT_COMPLETED",
                            "Lệnh %s đang ở trạng thái %s — chỉ bàn giao DO đã hoàn tất (delivered)."
                            % (do_id, do.canonical_status)))
    try:
        goi = await get_delivery_order_closeout(do_id, request, db)
    except DomainError as loi:
        raise_http(loi)
    closeout = goi.get("data", goi) if isinstance(goi, dict) else goi
    return {"message": "Hồ sơ bàn giao của %s." % do_id, "data": dong_goi_ban_giao(closeout)}
