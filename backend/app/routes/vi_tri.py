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
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Trip, VehiclePosition
from services.bao_mat import nguoi_hien_tai

router = APIRouter()

NGUONG_GIAY = 20          # hai điểm gần nhau dưới ngần này giây thì bỏ điểm sau
NGUONG_CU_PHUT = 15       # quá ngần này phút thì coi là GPS cũ (giống ngưỡng của EPL_System)
GPS_XEM_NGAY = 31         # "điểm mới nhất" chỉ tìm trong 31 ngày gần đây — bảng GPS chia theo tháng thì PostgreSQL chỉ
                          # mở 1–2 bảng con thay vì mọi tháng (điểm cũ hơn thế đằng nào cũng là "GPS cũ")


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


@router.post("/api/trips/{tid}/vi-tri")
def gui_vi_tri(tid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role == "driver" and p.driver_id != user.driver_id:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế chỉ gửi vị trí cho phiếu của mình."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không gửi vị trí xe." % user.role})
    if p.transport_status == "arrived":
        raise HTTPException(409, {"ma": "PHIEU_DA_TOI", "loi": "Phiếu đã tới nơi, không nhận thêm vị trí."})

    lat = _so(d.get("lat"), "lat", -90, 90)
    lng = _so(d.get("lng"), "lng", -180, 180)
    if lat is None or lng is None:
        raise HTTPException(422, {"ma": "THIEU_TOA_DO", "loi": "Thiếu toạ độ."})

    bay_gio = dt.datetime.utcnow()
    # chỉ cần biết có điểm nào trong NGUONG_GIAY giây vừa qua không — tìm trong 1 phút gần nhất là đủ (và chỉ chạm
    # bảng con tháng này, không lục cả năm)
    gan_day = (db.query(VehiclePosition).filter(VehiclePosition.trip_id == p.id,
                                                VehiclePosition.ts >= bay_gio - dt.timedelta(seconds=60))
               .order_by(VehiclePosition.ts.desc()).first())
    if gan_day and gan_day.ts and (bay_gio - gan_day.ts).total_seconds() < NGUONG_GIAY:
        return {"ghi": False, "ly_do": "qua_day", "vi_tri": xuat_vi_tri(gan_day, bay_gio)}

    v = VehiclePosition(trip_id=p.id, vehicle_id=p.vehicle_id, driver_id=p.driver_id, ts=bay_gio,
                        lat=lat, lng=lng, accuracy_m=_so(d.get("accuracy_m"), "accuracy_m"),
                        speed_kmh=_so(d.get("speed_kmh"), "speed_kmh"),
                        heading=_so(d.get("heading"), "heading"),
                        source=d.get("source") or "driver_app", by_user=user.full_name)
    db.add(v); db.commit()
    return {"ghi": True, "vi_tri": xuat_vi_tri(v, bay_gio)}


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
