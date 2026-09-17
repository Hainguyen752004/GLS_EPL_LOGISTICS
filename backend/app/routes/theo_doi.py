# -*- coding: utf-8 -*-
"""Bảng theo dõi tuyến — một lần gọi ra đủ số cho cả màn "trung tâm điều hành".

Bố cục lấy từ màn "Theo dõi và kiểm soát" của EPL_System: dải ô số ở trên, danh sách chuyến bên
trái, chi tiết chuyến ở giữa, hồ sơ chuyến bên phải. Nhưng số liệu thì của bên Lào, không bịa:

  · KHÔNG có GPS. Bên Lào không gắn thiết bị, "xe tới điểm X" là do Bãi bấm khi tài xế gọi về.
    Nên chỗ bản đồ vệ tinh của EPL_System ở đây là TIẾN ĐỘ TRÊN TUYẾN — thứ họ thật sự có.
  · KHÔNG có hạn giao hàng. Excel của họ không có ô đó. Thay bằng "đi lâu chưa về": xe rời bãi
    quá nhiều ngày mà chưa báo tới nơi thì đáng để người điều hành nhìn.

Gộp vào một đường để màn không phải gọi N+1 lần: danh sách chuyến đang chạy có thể vài chục dòng,
mỗi dòng cần số chặng, số sự cố đang mở và trạng thái sáu mục.
"""
import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Route, RouteStop, Trip, TripEvent, TripSection, Voucher
from services.bao_mat import nguoi_hien_tai

router = APIRouter()

NGAY_COI_LA_LAU = 5          # rời bãi quá ngần này ngày mà chưa báo tới nơi thì gắn cờ


@router.get("/api/theo-doi")
def bang_theo_doi(tat_ca: int = 0, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    q = db.query(Trip)
    if user.role == "driver":
        q = q.filter(Trip.driver_id == (user.driver_id or "__khong_co__"))
    tat = q.order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).all()
    ds = tat if tat_ca else [p for p in tat if p.transport_status != "arrived" or p.finance_status != "paid"]
    ma = [p.id for p in ds]

    # ---- gom dữ liệu phụ trong vài truy vấn, không lặp từng phiếu
    su_kien = db.query(TripEvent).filter(TripEvent.trip_id.in_(ma)).all() if ma else []
    muc = db.query(TripSection).filter(TripSection.trip_id.in_(ma)).all() if ma else []
    phieu_linh = db.query(Voucher).filter(Voucher.trip_id.in_(ma), Voucher.status == "cho").all() if ma else []
    ma_tuyen = {p.route_id for p in ds if p.route_id}
    chang = {}
    if ma_tuyen:
        for s in db.query(RouteStop).filter(RouteStop.route_id.in_(ma_tuyen)).order_by(RouteStop.seq).all():
            chang.setdefault(s.route_id, []).append(s)
    tuyen = {r.id: r for r in db.query(Route).filter(Route.id.in_(ma_tuyen)).all()} if ma_tuyen else {}

    theo_phieu = {}
    for e in su_kien:
        theo_phieu.setdefault(e.trip_id, []).append(e)
    muc_cua = {}
    for m in muc:
        muc_cua.setdefault(m.trip_id, {})[m.section] = m.status
    linh_cua = {}
    for v in phieu_linh:
        linh_cua[v.trip_id] = linh_cua.get(v.trip_id, 0) + 1

    hom_nay = dt.date.today()
    ra, kpi = [], {"dang_chay": 0, "chua_xuat_ben": 0, "di_lau": 0, "cho_hoa_don": 0,
                   "su_co_mo": 0, "chua_thu_tien": 0, "cho_cap_phat": 0}
    for p in ds:
        ev = theo_phieu.get(p.id, [])
        diem = chang.get(p.route_id, [])
        da_toi = [e.stop_seq for e in ev if e.kind == "arrive_stop" and e.stop_seq]
        toi = max(da_toi) if da_toi else (1 if p.transport_status != "dispatched" else 0)
        # Sự cố ĐANG MỞ = tài xế báo mà chưa ai duyệt hoặc từ chối.
        mo = len([e for e in ev if e.status == "reported"])
        ngay_di = p.out_date or p.doc_date
        lau = (p.transport_status != "arrived" and ngay_di is not None
               and (hom_nay - ngay_di).days > NGAY_COI_LA_LAU)
        cho_linh = linh_cua.get(p.id, 0)

        if p.transport_status in ("dispatched", "transit"): kpi["dang_chay"] += 1
        if p.transport_status == "dispatched": kpi["chua_xuat_ben"] += 1
        if lau: kpi["di_lau"] += 1
        if p.transport_status == "arrived" and not p.invoiced: kpi["cho_hoa_don"] += 1
        if mo: kpi["su_co_mo"] += 1
        if p.finance_status != "paid": kpi["chua_thu_tien"] += 1
        if cho_linh: kpi["cho_cap_phat"] += cho_linh

        ra.append({
            "id": p.id, "doc_no": p.doc_no, "company": p.company, "owner_name": p.owner_name,
            "truck_no": p.truck_no, "plate_head": p.plate_head, "plate_trailer": p.plate_trailer,
            "driver_name": p.driver_name, "customer_name": p.customer_name,
            "origin": p.origin, "destination": p.destination,
            "route_name": tuyen[p.route_id].name if p.route_id in tuyen else None,
            "out_date": ngay_di.isoformat() if ngay_di else None,
            "back_date": p.back_date.isoformat() if p.back_date else None,
            "transport_status": p.transport_status, "finance_status": p.finance_status,
            "invoiced": p.invoiced, "weight_origin": p.weight_origin, "weight_dest": p.weight_dest,
            "so_diem": len(diem), "stop_reached": toi,
            "tong_km": round(sum(s.km_from_prev or 0 for s in diem), 1),
            "su_co_mo": mo, "cho_cap_phat": cho_linh, "di_lau": lau,
            "so_ngay_di": (hom_nay - ngay_di).days if ngay_di else None,
            "sections": muc_cua.get(p.id, {}),
        })

    return {"luc": dt.datetime.now().isoformat(timespec="seconds"), "kpi": kpi,
            "so_tat_ca": len(tat), "chuyen": ra}


@router.get("/api/theo-doi/su-co")
def so_su_co(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Sổ sự cố — mọi diễn biến bất thường của mọi phiếu, mới nhất lên đầu.

    Gồm sự cố, sửa xe và khai đổ dầu dọc đường. Ghi chú thường không phải việc cần xử lý nên
    không đưa vào sổ này.
    """
    q = db.query(TripEvent).filter(TripEvent.kind.in_(("incident", "repair", "refuel")))
    ds = q.order_by(TripEvent.ts.desc()).limit(200).all()
    ma = {e.trip_id for e in ds}
    phieu = {p.id: p for p in db.query(Trip).filter(Trip.id.in_(ma)).all()} if ma else {}
    if user.role == "driver":
        ds = [e for e in ds if phieu.get(e.trip_id) and phieu[e.trip_id].driver_id == user.driver_id]
    ra = []
    for e in ds:
        p = phieu.get(e.trip_id)
        ra.append({"id": e.id, "trip_id": e.trip_id, "doc_no": p.doc_no if p else None,
                   "truck_no": p.truck_no if p else None, "driver_name": p.driver_name if p else None,
                   "ts": e.ts.isoformat() if e.ts else None, "kind": e.kind,
                   "incident_type": e.incident_type, "note": e.note, "status": e.status or "approved",
                   "reported_cost": e.reported_cost, "currency": e.currency, "qty_l": e.qty_l,
                   "by_user": e.by_user, "approved_by": e.approved_by,
                   "approved_at": e.approved_at.isoformat() if e.approved_at else None})
    return ra
