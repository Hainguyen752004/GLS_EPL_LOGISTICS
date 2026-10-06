# -*- coding: utf-8 -*-
"""Vị trí xe — GPS thật do điện thoại tài xế gửi về.

Trước đây màn Theo dõi chỉ có "mốc đã xác nhận tới" do Bãi bấm tay khi tài xế gọi về. Nay tài xế
bật chia sẻ vị trí trên chính trang của mình (không cần cài app từ chợ ứng dụng — trình duyệt điện
thoại có sẵn Geolocation), máy gửi toạ độ về đây và bản đồ vẽ xe chạy thật.

Ba luật giữ cho dữ liệu sạch:

  1. Tài xế CHỈ gửi được vị trí cho phiếu của chính mình, và chỉ khi phiếu chưa tới nơi. Phiếu đã
     đóng mà vẫn nhận toạ độ là dữ liệu rác.
  2. Điểm gửi quá dày thì bỏ bớt. Điện thoại có thể bắn mỗi giây; giữ hết thì bảng phình vô ích mà
     đường vẽ ra cũng không đẹp hơn. Cách nhau dưới NGUONG_GIAY thì không ghi.
  3. GPS CŨ coi như KHÔNG CÓ. Một chấm từ hôm qua không nói được xe đang ở đâu, nên quá
     NGUONG_CU_PHUT thì màn Theo dõi lùi về mốc đã xác nhận tới và gắn cờ "GPS cũ".

06/10 (chủ dự án: "làm hàng đợi mất mạng luôn"): mất sóng giữa đường thì điện thoại GIỮ điểm kèm GIỜ MÁY (thời điểm thật) rồi
gửi bù theo lô khi có sóng lại — POST /api/trips/{id}/vi-tri/lo. Điểm mang giờ máy hợp lệ thì ghi theo giờ đó (trước đây giờ
lấy theo lúc máy chủ nhận — điểm gửi bù dồn về một lúc); giờ vô lý (tương lai, quá cũ, trước khi lập phiếu, sau khi xe tới)
thì bỏ điểm đó, báo lại số bỏ — không làm hỏng cả lô. Gửi lại cùng lô (mất phản hồi) không ghi trùng: trùng giờ là bỏ.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Trip, TripLog, VehiclePosition
from services.bao_mat import nguoi_hien_tai

router = APIRouter()

NGUONG_GIAY = 20          # hai điểm gần nhau dưới ngần này giây thì bỏ điểm sau
NGUONG_CU_PHUT = 15       # quá ngần này phút thì coi là GPS cũ (giống ngưỡng của EPL_System)
GPS_XEM_NGAY = 31         # "điểm mới nhất" chỉ tìm trong 31 ngày gần đây — bảng GPS chia theo tháng thì PostgreSQL chỉ
                          # mở 1–2 bảng con thay vì mọi tháng (điểm cũ hơn thế đằng nào cũng là "GPS cũ")
# giờ máy (điện thoại tài xế) chấp nhận được — 06/10: lệch tới 10 phút về phía trước (đồng hồ máy chạy nhanh); điểm GPS gửi bù
# cũ nhất 7 ngày (mất sóng lâu hơn thế thì vệt đường không còn ích cho người điều xe); thao tác chờ gửi (xuất phát, báo hỏng,
# khai dầu) cũ nhất 30 ngày
GIO_MAY_TUONG_LAI = dt.timedelta(minutes=10)
GPS_BU_TOI_DA = dt.timedelta(days=7)
THAO_TAC_TOI_DA = dt.timedelta(days=30)
LO_TOI_DA = 500           # điểm mỗi lần gửi bù — máy gửi lô 200 điểm


def doc_gio_may(v):
    """Giờ máy dạng ISO 8601 ("2026-10-06T03:04:05.123Z", có / không múi giờ) → datetime UTC KHÔNG múi (cùng kiểu cột ts —
    models.bay_gio là utcnow). Trống / sai dạng → None. Không có múi giờ thì coi là UTC (máy luôn gửi toISOString)."""
    if v in (None, ""):
        return None
    try:
        t = dt.datetime.fromisoformat(str(v).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is not None:
        t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return t


def gio_may_hop_le(t, p=None, cu_nhat=THAO_TAC_TOI_DA, bay_gio=None):
    """Giờ máy `t` (UTC không múi) có dùng được không: không ở tương lai quá GIO_MAY_TUONG_LAI, không cũ hơn `cu_nhat`, không
    trước lúc lập phiếu `p` quá một ngày (đồng hồ máy để sai ngày)."""
    if t is None:
        return False
    bay_gio = bay_gio or dt.datetime.utcnow()
    if t > bay_gio + GIO_MAY_TUONG_LAI or t < bay_gio - cu_nhat:
        return False
    if p is not None and getattr(p, "created_at", None) and t < p.created_at - dt.timedelta(days=1):
        return False
    return True


def luc_thao_tac(d, p):
    """Giờ THẬT của một thao tác tài xế (xuất phát, báo hỏng, khai dầu — 06/10): `luc` máy gửi kèm, hợp lệ thì dùng; không có /
    vô lý thì None (người gọi dùng giờ máy chủ như trước — đồng hồ điện thoại sai không được làm mất lần báo)."""
    t = doc_gio_may((d or {}).get("luc"))
    return t if gio_may_hop_le(t, p) else None


def moc_toi(db, p):
    """Lúc phiếu được ghi "đã tới" (nhật ký st_arrived mới nhất) — điểm GPS / khai báo gửi bù có giờ máy TRƯỚC mốc này vẫn là của
    chuyến đang chạy. None = chưa tới, hoặc không có nhật ký."""
    if p.transport_status != "arrived":
        return None
    r = (db.query(TripLog.ts).filter(TripLog.trip_id == p.id, TripLog.action == "st_arrived")
         .order_by(TripLog.ts.desc()).first())
    return r[0] if r else None


def _so(v, ten, nho_nhat=None, lon_nhat=None):
    if v in (None, ""):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số." % ten})
    if nho_nhat is not None and not (nho_nhat <= x <= lon_nhat):
        raise HTTPException(422, {"ma": "TOA_DO_SAI", "loi": "Ô %s ngoài khoảng cho phép." % ten})
    return x


def xuat_vi_tri(v, bay_gio=None):
    bay_gio = bay_gio or dt.datetime.utcnow()
    tuoi = (bay_gio - v.ts).total_seconds() / 60.0 if v.ts else None
    return {"lat": v.lat, "lng": v.lng, "ts": v.ts.isoformat() if v.ts else None,
            "tuoi_phut": round(tuoi, 1) if tuoi is not None else None,
            "cu": (tuoi is not None and tuoi > NGUONG_CU_PHUT),
            "speed_kmh": v.speed_kmh, "heading": v.heading, "accuracy_m": v.accuracy_m,
            "source": v.source}


def vi_tri_moi_nhat(db, ma_phieu):
    """Điểm mới nhất của từng phiếu, lấy một lần cho cả danh sách."""
    if not ma_phieu:
        return {}
    # Mỗi phiếu lấy đúng MỘT điểm mới nhất qua chỉ mục (trip_id, ts DESC) — LATERAL … LIMIT 1. Trước 24/09 là
    # "3.000 điểm mới nhất của cả nhóm": 300 xe chạy, mỗi xe 25 giây một điểm thì 3.000 điểm chỉ phủ vài phút
    # gần nhất, xe nào gửi chậm hơn là bị báo "mất GPS" dù GPS vẫn có.
    from sqlalchemy import text
    ma = list(dict.fromkeys(m for m in ma_phieu if m))
    ids = [r[0] for r in db.execute(text(
        "SELECT v.id FROM unnest(CAST(:ma AS varchar[])) AS t(id) "
        "CROSS JOIN LATERAL (SELECT id FROM vehicle_positions WHERE trip_id = t.id AND ts >= :tu ORDER BY ts DESC LIMIT 1) v"),
        {"ma": ma, "tu": dt.datetime.utcnow() - dt.timedelta(days=GPS_XEM_NGAY)})]
    return ({v.trip_id: v for v in db.query(VehiclePosition).filter(VehiclePosition.id.in_(ids),
                                                                  VehiclePosition.ts >= dt.datetime.utcnow() - dt.timedelta(days=GPS_XEM_NGAY + 1))}
            if ids else {})


def _chan_gui(db, tid, user):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role == "driver" and p.driver_id != user.driver_id:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế chỉ gửi vị trí cho phiếu của mình."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không gửi vị trí xe." % user.role})
    return p


@router.post("/api/trips/{tid}/vi-tri")
def gui_vi_tri(tid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Một điểm gửi ngay (còn sóng). `ts` = giờ máy lúc lấy điểm (06/10): hợp lệ thì ghi theo giờ đó, không thì giờ máy chủ."""
    p = _chan_gui(db, tid, user)
    if p.transport_status == "arrived":
        raise HTTPException(409, {"ma": "PHIEU_DA_TOI", "loi": "Phiếu đã tới nơi, không nhận thêm vị trí."})

    lat = _so(d.get("lat"), "lat", -90, 90)
    lng = _so(d.get("lng"), "lng", -180, 180)
    if lat is None or lng is None:
        raise HTTPException(422, {"ma": "THIEU_TOA_DO", "loi": "Thiếu toạ độ."})

    bay_gio = dt.datetime.utcnow()
    may = doc_gio_may(d.get("ts"))
    luc = may if gio_may_hop_le(may, p, GPS_BU_TOI_DA, bay_gio) else bay_gio
    # chỉ cần biết có điểm nào trong NGUONG_GIAY giây quanh lúc lấy điểm không — tìm trong 1 phút quanh đó là đủ (và chỉ chạm
    # bảng con tháng này, không lục cả năm)
    gan_day = (db.query(VehiclePosition).filter(VehiclePosition.trip_id == p.id,
                                                VehiclePosition.ts >= luc - dt.timedelta(seconds=60),
                                                VehiclePosition.ts <= luc + dt.timedelta(seconds=60))
               .order_by(VehiclePosition.ts.desc()).all())
    gan = min(gan_day, key=lambda x: abs((x.ts - luc).total_seconds()), default=None)
    if gan is not None and gan.ts and abs((luc - gan.ts).total_seconds()) < NGUONG_GIAY:
        return {"ghi": False, "ly_do": "qua_day", "vi_tri": xuat_vi_tri(gan_day[0], bay_gio)}

    v = VehiclePosition(trip_id=p.id, vehicle_id=p.vehicle_id, driver_id=p.driver_id, ts=luc,
                        lat=lat, lng=lng, accuracy_m=_so(d.get("accuracy_m"), "accuracy_m"),
                        speed_kmh=_so(d.get("speed_kmh"), "speed_kmh"),
                        heading=_so(d.get("heading"), "heading"),
                        source=d.get("source") or "driver_app", by_user=user.full_name)
    db.add(v); db.commit()
    return {"ghi": True, "vi_tri": xuat_vi_tri(v, bay_gio)}


@router.post("/api/trips/{tid}/vi-tri/lo")
def gui_vi_tri_lo(tid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """GỬI BÙ điểm GPS điện thoại giữ lại lúc mất sóng (06/10). {"diem": [{lat, lng, ts (giờ máy, bắt buộc), accuracy_m?,
    speed_kmh?, heading?}, …]} — tối đa LO_TOI_DA điểm.

    Mỗi điểm GHI THEO GIỜ MÁY nếu hợp lệ; bỏ (đếm theo lý do, không hỏng cả lô): toạ độ sai · giờ trống / sai dạng / tương lai /
    cũ quá GPS_BU_TOI_DA / trước lúc lập phiếu (gio_sai) · sau lúc phiếu ghi "đã tới" (sau_khi_toi) · trùng giờ một điểm đã có
    (trung — gửi lại lô cũ vì mất phản hồi) · cách điểm đã có / vừa nhận dưới NGUONG_GIAY giây (qua_day). Phiếu đã tới vẫn nhận
    điểm có giờ máy TRƯỚC lúc tới (vệt đường của chuyến); không có nhật ký lúc tới thì bỏ hết."""
    p = _chan_gui(db, tid, user)
    ds = d.get("diem")
    if not isinstance(ds, list):
        raise HTTPException(422, {"ma": "THIEU_DIEM", "loi": "Gửi bù phải có danh sách điểm (diem)."})
    if len(ds) > LO_TOI_DA:
        raise HTTPException(422, {"ma": "LO_QUA_LON", "loi": "Một lần gửi bù tối đa %d điểm." % LO_TOI_DA})
    bay_gio = dt.datetime.utcnow()
    toi = moc_toi(db, p) if p.transport_status == "arrived" else None
    bo = {"toa_do_sai": 0, "gio_sai": 0, "sau_khi_toi": 0, "trung": 0, "qua_day": 0}
    hop_le = []
    for x in ds:
        x = x if isinstance(x, dict) else {}
        try:
            lat = _so(x.get("lat"), "lat", -90, 90)
            lng = _so(x.get("lng"), "lng", -180, 180)
            them = {k: _so(x.get(k), k) for k in ("accuracy_m", "speed_kmh", "heading")}
        except HTTPException:
            lat = lng = None
        if lat is None or lng is None:
            bo["toa_do_sai"] += 1
            continue
        t = doc_gio_may(x.get("ts"))
        if not gio_may_hop_le(t, p, GPS_BU_TOI_DA, bay_gio):
            bo["gio_sai"] += 1
            continue
        if p.transport_status == "arrived" and (toi is None or t > toi):
            bo["sau_khi_toi"] += 1
            continue
        hop_le.append((t, lat, lng, them))
    ghi = 0
    if hop_le:
        hop_le.sort(key=lambda z: z[0])
        dau, cuoi = hop_le[0][0] - dt.timedelta(seconds=NGUONG_GIAY), hop_le[-1][0] + dt.timedelta(seconds=NGUONG_GIAY)
        co = sorted(t for (t,) in db.query(VehiclePosition.ts).filter(VehiclePosition.trip_id == p.id, VehiclePosition.ts >= dau,
                                                                       VehiclePosition.ts <= cuoi))
        da_co = set(co)
        for t, lat, lng, them in hop_le:
            if t in da_co:
                bo["trung"] += 1
                continue
            if any(abs((t - c).total_seconds()) < NGUONG_GIAY for c in co):
                bo["qua_day"] += 1
                continue
            db.add(VehiclePosition(trip_id=p.id, vehicle_id=p.vehicle_id, driver_id=p.driver_id, ts=t, lat=lat, lng=lng,
                                   accuracy_m=them["accuracy_m"], speed_kmh=them["speed_kmh"], heading=them["heading"],
                                   source="driver_app", by_user=user.full_name))
            co.append(t); da_co.add(t)
            ghi += 1
        if ghi:
            db.commit()
    return {"nhan": len(ds), "ghi": ghi, "bo": {k: v for k, v in bo.items() if v}}


@router.get("/api/trips/{tid}/vet")
def vet_duong(tid: str, gio: int = 48, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Vệt đường đã đi của một phiếu, để vẽ lên bản đồ. Mặc định 48 giờ gần đây."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role == "driver" and p.driver_id != user.driver_id:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế chỉ xem phiếu của mình."})
    tu = dt.datetime.utcnow() - dt.timedelta(hours=max(1, min(gio, 24 * 30)))
    ds = (db.query(VehiclePosition).filter(VehiclePosition.trip_id == p.id, VehiclePosition.ts >= tu)
          .order_by(VehiclePosition.ts).all())
    return {"trip_id": p.id, "so_diem": len(ds),
            "vet": [{"lat": v.lat, "lng": v.lng, "ts": v.ts.isoformat() if v.ts else None,
                     "speed_kmh": v.speed_kmh} for v in ds]}
