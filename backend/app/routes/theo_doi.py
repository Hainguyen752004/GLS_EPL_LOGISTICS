# -*- coding: utf-8 -*-
"""Bảng theo dõi tuyến — một lần gọi ra đủ số cho cả màn "trung tâm điều hành".

Bố cục lấy từ màn "Theo dõi và kiểm soát" của EPL_System: dải ô số ở trên, danh sách chuyến bên
trái, chi tiết chuyến ở giữa, hồ sơ chuyến bên phải. Nhưng số liệu thì của bên Lào, không bịa:

  · Vị trí xe lấy theo thứ tự: GPS THẬT do điện thoại tài xế gửi về (bảng vehicle_positions) →
    nếu không có hoặc quá cũ thì lùi về MỐC ĐÃ XÁC NHẬN TỚI do Bãi bấm. Không nội suy vị trí giữa
    hai chặng: không biết thì không vẽ, chứ không đoán.
  · KHÔNG có hạn giao hàng. Excel của họ không có ô đó. Thay bằng "đi lâu chưa về": xe rời bãi
    quá nhiều ngày mà chưa báo tới nơi thì đáng để người điều hành nhìn.

Gộp vào một đường để màn không phải gọi N+1 lần: danh sách chuyến đang chạy có thể vài chục dòng,
mỗi dòng cần số chặng, số sự cố đang mở và trạng thái sáu mục.
"""
import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import and_, exists, func, not_, or_
from sqlalchemy.orm import Session

from database import get_db
from models import GuiSoTune, Route, RouteStop, Trip, TripEvent, TripSection, VehiclePosition, Voucher
from routes.phieu import loc_phieu
from routes.vi_tri import NGUONG_CU_PHUT, vi_tri_moi_nhat, xuat_vi_tri
from services.bao_mat import nguoi_hien_tai

router = APIRouter()

NGAY_COI_LA_LAU = 5          # rời bãi quá ngần này ngày mà chưa báo tới nơi thì gắn cờ
CO_MAC_DINH, CO_TOI_DA = 300, 1000
CHAY = ("dispatched", "transit")


def _dieu_kien_o(o, hom_nay, gps_moi):
    """Điều kiện SQL của từng ô số — bấm ô là máy chủ lọc đúng tập đó (trước đây lọc trên trình duyệt, cần tải hết)."""
    su_co = exists().where(and_(TripEvent.trip_id == Trip.id, TripEvent.status == "reported"))
    # chỉ tờ đề nghị xuất kho NHIÊN LIỆU (kind fuel) — tờ tạm ứng (advance) không phải việc cấp phát ở kho (rà 01/10: đếm
    # gộp ra 32 trong khi thật 2)
    cho_linh = exists().where(and_(Voucher.trip_id == Trip.id, Voucher.status == "cho", Voucher.kind == "fuel"))
    co_gps = exists().where(and_(VehiclePosition.trip_id == Trip.id, VehiclePosition.ts >= gps_moi))
    ngay_di = func.coalesce(Trip.out_date, Trip.doc_date)
    # 01/10 (bỏ trang kế toán tạm): hoá đơn là SO bên hệ anh Tune — "chờ hoá đơn" = xe đã về mà chưa có SO bên đó. Cờ
    # trips.invoiced là bản chép của trang tạm, không ai ghi nữa. Giữ tên ô cho giao diện.
    co_so = exists().where(and_(GuiSoTune.trip_id == Trip.id, GuiSoTune.status == "synced"))
    return {
        "dang_chay": Trip.transport_status.in_(CHAY),
        "chua_xuat_ben": Trip.transport_status == "dispatched",
        "di_lau": and_(Trip.transport_status != "arrived", ngay_di < hom_nay - dt.timedelta(days=NGAY_COI_LA_LAU)),
        "cho_hoa_don": and_(Trip.transport_status == "arrived", not_(co_so)),
        "su_co_mo": su_co,
        "chua_thu_tien": Trip.finance_status != "paid",
        "cho_cap_phat": cho_linh,
        "gps_thieu": and_(Trip.transport_status.in_(CHAY), not_(co_gps)),
    }.get(o)


@router.get("/api/theo-doi")
def bang_theo_doi(tat_ca: int = 0, o: str = None, q: str = None, co: int = CO_MAC_DINH,
                  db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Dữ liệu cả năm (chủ dự án chốt 24/09): ô số đếm bằng SQL trên TOÀN BỘ phiếu còn việc; danh sách lọc theo ô
    đang bấm (`o`), chữ tìm (`q`), "chỉ phiếu còn việc" (mặc định) hay tất cả (`tat_ca=1`), tối đa `co` phiếu mới nhất.
    `so_khop` là số phiếu khớp bộ lọc — danh sách có thể ngắn hơn khi vượt `co`."""
    goc = db.query(Trip)
    if user.role == "driver":
        goc = goc.filter(Trip.driver_id == (user.driver_id or "__khong_co__"))
    con_viec = or_(Trip.transport_status != "arrived", Trip.finance_status != "paid")
    hom_nay = dt.date.today()
    gps_moi = dt.datetime.utcnow() - dt.timedelta(minutes=NGUONG_CU_PHUT)

    # ---- ô số: MỘT câu COUNT(*) FILTER cho cả 7 ô, trên tập phiếu còn việc (chỉ mục một phần ix_trips_con_viec)
    O = ("dang_chay", "chua_xuat_ben", "di_lau", "cho_hoa_don", "su_co_mo", "chua_thu_tien", "gps_thieu")
    dem = (goc.filter(con_viec).order_by(None)
           .with_entities(*[func.count().filter(_dieu_kien_o(k, hom_nay, gps_moi)).label(k) for k in O]).one())
    kpi = {k: int(getattr(dem, k) or 0) for k in O}
    kpi["cho_cap_phat"] = int(db.query(func.count(Voucher.id)).join(Trip, Trip.id == Voucher.trip_id)
                              .filter(Voucher.status == "cho", Voucher.kind == "fuel", con_viec, *( [Trip.driver_id == (user.driver_id or "__khong_co__")] if user.role == "driver" else []))
                              .scalar() or 0)

    loc = goc if tat_ca else goc.filter(con_viec)
    dk = _dieu_kien_o(o, hom_nay, gps_moi) if o else None
    if dk is not None:
        loc = loc.filter(dk)
    loc = loc_phieu(loc, q)
    co = max(1, min(int(co or CO_MAC_DINH), CO_TOI_DA))
    from routes.phieu import TRAN_DEM
    n_khop = loc.order_by(None).limit(TRAN_DEM + 1).count()        # đếm có trần — tất cả phiếu cả năm là tăng theo dữ liệu
    so_khop, khop_tran = min(n_khop, TRAN_DEM), n_khop > TRAN_DEM
    ds = loc.order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).limit(co).all()
    ma = [p.id for p in ds]

    # ---- gom dữ liệu phụ trong vài truy vấn, không lặp từng phiếu
    su_kien = db.query(TripEvent).filter(TripEvent.trip_id.in_(ma)).all() if ma else []
    muc = db.query(TripSection).filter(TripSection.trip_id.in_(ma)).all() if ma else []
    phieu_linh = db.query(Voucher).filter(Voucher.trip_id.in_(ma), Voucher.status == "cho", Voucher.kind == "fuel").all() if ma else []
    ma_tuyen = {p.route_id for p in ds if p.route_id}
    chang = {}
    if ma_tuyen:
        for s in db.query(RouteStop).filter(RouteStop.route_id.in_(ma_tuyen)).order_by(RouteStop.seq).all():
            chang.setdefault(s.route_id, []).append(s)
    tuyen = {r.id: r for r in db.query(Route).filter(Route.id.in_(ma_tuyen)).all()} if ma_tuyen else {}
    gps = vi_tri_moi_nhat(db, ma)          # GPS thật mới nhất của từng phiếu
    co_so = {t for (t,) in db.query(GuiSoTune.trip_id).filter(GuiSoTune.trip_id.in_(ma), GuiSoTune.status == "synced")} if ma else set()

    theo_phieu = {}
    for e in su_kien:
        theo_phieu.setdefault(e.trip_id, []).append(e)
    muc_cua = {}
    for m in muc:
        muc_cua.setdefault(m.trip_id, {})[m.section] = m.status
    linh_cua = {}
    for v in phieu_linh:
        linh_cua[v.trip_id] = linh_cua.get(v.trip_id, 0) + 1

    ra = []
    gio_utc = dt.datetime.utcnow()
    for p in ds:
        ev = theo_phieu.get(p.id, [])
        diem = chang.get(p.route_id, [])
        da_toi = [e.stop_seq for e in ev if e.kind == "arrive_stop" and e.stop_seq]
        toi = max(da_toi) if da_toi else (1 if p.transport_status != "dispatched" else 0)
        # Xe ĐÃ BÁO TỚI NƠI thì coi như đã qua hết chặng, dù Bãi không bấm đủ từng mốc trên đường.
        if p.transport_status == "arrived" and diem:
            toi = max(toi, len(diem))
        # Sự cố ĐANG MỞ = tài xế báo mà chưa ai duyệt hoặc từ chối.
        mo = len([e for e in ev if e.status == "reported"])
        ngay_di = p.out_date or p.doc_date
        lau = (p.transport_status != "arrived" and ngay_di is not None
               and (hom_nay - ngay_di).days > NGAY_COI_LA_LAU)
        cho_linh = linh_cua.get(p.id, 0)

        g = gps.get(p.id)
        gps_ra = xuat_vi_tri(g, gio_utc) if g else None

        # Điểm đi / điểm đến: phiếu nào bỏ trống thì lấy theo tuyến, đừng để màn hiện hai gạch ngang.
        diem_dau = diem[0].name if diem else None
        diem_cuoi = diem[-1].name if diem else None
        # Vị trí trên bản đồ = ĐIỂM ĐÃ XÁC NHẬN TỚI gần nhất. Không GPS nên không bịa vị trí giữa
        # hai chặng; chấm đứng ở mốc cuối cùng mà Bãi đã bấm.
        # Xe đã báo tới nơi thì đứng ở điểm cuối, dù Bãi không bấm đủ từng chặng trên đường.
        toi_ve = len(diem) if p.transport_status == "arrived" else max(toi, 1)
        moc = None
        for st in diem:
            if st.lat is not None and st.lng is not None and st.seq <= toi_ve:
                moc = st
        ra.append({
            "id": p.id, "doc_no": p.doc_no, "company": p.company, "owner_name": p.owner_name,
            "truck_no": p.truck_no, "plate_head": p.plate_head, "plate_trailer": p.plate_trailer,
            "driver_name": p.driver_name, "customer_name": p.customer_name,
            "origin": p.origin or diem_dau, "destination": p.destination or diem_cuoi,
            "stops": [{"seq": st.seq, "name": st.name, "km_from_prev": st.km_from_prev,
                       "lat": st.lat, "lng": st.lng} for st in diem],
            # vi_tri = chấm vẽ lên bản đồ. GPS thật còn mới thì dùng nó; không thì lùi về mốc.
            "vi_tri": ({"lat": gps_ra["lat"], "lng": gps_ra["lng"], "seq": None, "name": None,
                        "nguon": "gps", "tuoi_phut": gps_ra["tuoi_phut"], "speed_kmh": gps_ra["speed_kmh"]}
                       if (gps_ra and not gps_ra["cu"])
                       else ({"lat": moc.lat, "lng": moc.lng, "seq": moc.seq, "name": moc.name,
                              "nguon": "moc"} if moc else None)),
            "gps": gps_ra,
            "route_name": tuyen[p.route_id].name if p.route_id in tuyen else None,
            "out_date": ngay_di.isoformat() if ngay_di else None,
            "back_date": p.back_date.isoformat() if p.back_date else None,
            "transport_status": p.transport_status, "finance_status": p.finance_status,
            "invoiced": p.id in co_so,            # đã có SO bên hệ anh Tune (tên cũ giữ cho giao diện)
            "weight_origin": p.weight_origin, "weight_dest": p.weight_dest,
            "so_diem": len(diem), "stop_reached": toi,
            "tong_km": round(sum(s.km_from_prev or 0 for s in diem), 1),
            "su_co_mo": mo, "cho_cap_phat": cho_linh, "di_lau": lau,
            # Xe còn ngoài đường thì đếm tới hôm nay; xe đã về thì đếm tới ngày về — không thì
            # một chuyến xong từ tháng trước cứ mỗi ngày lại "đi thêm một ngày".
            "so_ngay_di": ((p.back_date if p.transport_status == "arrived" and p.back_date else hom_nay)
                           - ngay_di).days if ngay_di else None,
            "sections": muc_cua.get(p.id, {}),
        })

    return {"luc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "kpi": kpi,
            "so_khop": so_khop, "so_khop_tran": khop_tran, "co": co, "chuyen": ra}


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
