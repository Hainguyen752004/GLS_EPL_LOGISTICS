# -*- coding: utf-8 -*-
"""Tuyến đường — mang sang từ EPL_System, cắt còn thứ họ dùng: chặng A → B → C, km từng chặng, BOT.

Không hình đường bộ, không toạ độ, không ETA. Một tuyến có ít nhất hai điểm: điểm đi (seq 1) và điểm
đến (seq cuối). Chọn tuyến trên phiếu xuất xe thì điểm đi/đến tự điền và BOT tự thành dòng phí cao tốc.
"""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Route, RouteStop, Trip
from services.bao_mat import can_vai, nguoi_hien_tai

router = APIRouter()
SUA = can_vai("yard", "acct")


def _so(v, ten):
    if v in (None, ""):
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số." % ten})


def xuat_tuyen(db, r, chi_tiet=False):
    diem = db.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.seq).all()
    ra = {"id": r.id, "name": r.name, "origin": r.origin, "destination": r.destination, "total_km": r.total_km,
          "toll_lak": r.toll_lak, "note": r.note, "active": r.active, "so_diem": len(diem),
          "stops": [{"id": s.id, "seq": s.seq, "name": s.name, "km_from_prev": s.km_from_prev, "note": s.note} for s in diem]}
    if chi_tiet:
        ra["so_phieu"] = db.query(Trip).filter(Trip.route_id == r.id).count()
    return ra


def _ghi_diem(db, r, stops):
    """Thay toàn bộ điểm của tuyến. Điểm đầu/cuối cập nhật lại origin/destination và tổng km."""
    if not isinstance(stops, list) or len(stops) < 2:
        raise HTTPException(422, {"ma": "THIEU_DIEM", "loi": "Tuyến phải có ít nhất điểm đi và điểm đến."})
    db.query(RouteStop).filter(RouteStop.route_id == r.id).delete()
    tong = 0.0
    for i, s in enumerate(stops, 1):
        ten = str((s or {}).get("name") or "").strip()
        if not ten:
            raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Điểm thứ %d chưa có tên." % i})
        km = _so(s.get("km_from_prev"), "km điểm %d" % i) if i > 1 else 0.0
        tong += km
        db.add(RouteStop(route_id=r.id, seq=i, name=ten, km_from_prev=km, note=s.get("note")))
    r.origin, r.destination, r.total_km = stops[0]["name"].strip(), stops[-1]["name"].strip(), round(tong, 1)


@router.get("/api/routes")
def ds(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [xuat_tuyen(db, r) for r in db.query(Route).order_by(Route.active.desc(), Route.name).all()]


@router.get("/api/routes/{rid}")
def xem(rid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    r = db.get(Route, rid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tuyến này."})
    return xuat_tuyen(db, r, chi_tiet=True)


@router.post("/api/routes")
def them(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA)):
    ten = str(data.get("name") or "").strip()
    if not ten:
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Tuyến phải có tên."})
    r = Route(name=ten, toll_lak=_so(data.get("toll_lak"), "BOT"), note=data.get("note"))
    db.add(r); db.flush()
    _ghi_diem(db, r, data.get("stops"))
    db.commit()
    return xuat_tuyen(db, r, chi_tiet=True)


@router.put("/api/routes/{rid}")
def sua(rid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA)):
    r = db.get(Route, rid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tuyến này."})
    if "name" in data:
        r.name = str(data["name"]).strip() or r.name
    if "toll_lak" in data: r.toll_lak = _so(data["toll_lak"], "BOT")
    if "note" in data: r.note = data["note"]
    if "active" in data: r.active = bool(data["active"])
    if "stops" in data: _ghi_diem(db, r, data["stops"])
    db.commit()
    return xuat_tuyen(db, r, chi_tiet=True)
