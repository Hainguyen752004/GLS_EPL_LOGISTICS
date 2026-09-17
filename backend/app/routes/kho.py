# -*- coding: utf-8 -*-
"""Mô-đun kho: kho nhiên liệu (ສາງນໍ້າມັນ · TK 625/371) và kho phụ tùng (ສາງອາໄຫຼ່ · TK 614/371).

Cả hai là SỔ KHO kiểu 2016: nhập một dòng, xuất một dòng, tồn = cộng dồn. Không có lô, không
FIFO, không định mức tiêu hao — Excel của họ không có mấy thứ đó.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FuelMove, Part, PartMove
from services import chung_tu as CT
from services.bao_mat import can_vai, nguoi_hien_tai

router = APIRouter()
SUA_KHO = can_vai("yard", "fuel", "acct")


def _ngay(v):
    if not v:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD."})


def _so(v, ten, bat_buoc=False):
    if v in (None, ""):
        if bat_buoc:
            raise HTTPException(422, {"ma": "THIEU", "loi": "Thiếu %s." % ten})
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "%s phải là số." % ten})


# ---------------------------------------------------------------- kho nhiên liệu
@router.get("/api/fuel-moves")
def so_nhien_lieu(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    ds = db.query(FuelMove).order_by(FuelMove.move_date, FuelMove.id).all()
    ton = 0.0; ra = []
    for m in ds:
        ton += m.qty_l if m.kind == "in" else -m.qty_l
        ra.append({"id": m.id, "move_date": m.move_date.isoformat(), "doc_no": m.doc_no, "kind": m.kind,
                   "truck_no": m.truck_no, "qty_in": m.qty_l if m.kind == "in" else 0,
                   "qty_out": m.qty_l if m.kind == "out" else 0, "balance": round(ton, 1),
                   "unit_price": m.unit_price, "currency": m.currency, "note": m.note, "by_user": m.by_user})
    ra.reverse()          # mới nhất lên đầu, nhưng tồn đã tính theo thứ tự thời gian
    return {"ton_lit": round(ton, 1), "rows": ra}


@router.post("/api/fuel-moves")
def ghi_nhien_lieu(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_KHO)):
    kind = data.get("kind")
    if kind not in ("in", "out"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "kind phải là in (nhập) hoặc out (xuất)."})
    qty = _so(data.get("qty_l"), "số lít", bat_buoc=True)
    if qty <= 0:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số lít phải lớn hơn 0."})
    if kind == "out" and not str(data.get("truck_no") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_XE", "loi": "Xuất nhiên liệu phải ghi xe nhận."})
    m = FuelMove(move_date=_ngay(data.get("move_date")), doc_no=(data.get("doc_no") or "").strip() or None,
                 kind=kind, truck_no=(data.get("truck_no") or "").strip() or None, qty_l=qty,
                 unit_price=_so(data.get("unit_price"), "đơn giá"), currency=str(data.get("currency") or "LAK").upper(),
                 note=data.get("note"), by_user=user.full_name)
    db.add(m); db.flush()
    if kind == "in":
        CT.ghi(db, "PNK_NL", nguon_bang="fuel_moves", nguon_id=m.id, ngay=m.move_date, doi_tuong_loai="ncc",
               tien=qty * (m.unit_price or 0), tien_te=m.currency, by_user=user.full_name,
               mo_ta="Nhập %s lít dầu · %s" % (qty, m.doc_no or ""), payload={"qty_l": qty, "unit_price": m.unit_price})
    db.commit()
    return so_nhien_lieu(db, user)


@router.delete("/api/fuel-moves/{mid}")
def xoa_nhien_lieu(mid: str, db: Session = Depends(get_db), user=Depends(can_vai("fuel"))):
    m = db.get(FuelMove, mid)
    if not m:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có dòng này."})
    CT.rut(db, nguon_bang="fuel_moves", nguon_id=m.id)
    db.delete(m); db.commit()
    return so_nhien_lieu(db, user)


# ---------------------------------------------------------------- kho phụ tùng
def _xuat_pt(p):
    return {"id": p.id, "name": p.name, "unit": p.unit, "qty": p.qty, "min_qty": p.min_qty,
            "unit_price": p.unit_price, "last_date": p.last_date.isoformat() if p.last_date else None,
            "last_truck": p.last_truck, "active": p.active,
            "status": "st_low" if (p.min_qty or 0) > 0 and p.qty <= p.min_qty else "st_ok"}


@router.get("/api/parts")
def ds_phu_tung(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_xuat_pt(p) for p in db.query(Part).filter(Part.active.is_(True)).order_by(Part.name).all()]


@router.post("/api/parts")
def them_phu_tung(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_KHO)):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Phụ tùng phải có tên."})
    p = Part(name=data["name"].strip(), unit=data.get("unit") or "u_pc", qty=_so(data.get("qty"), "tồn"),
             min_qty=_so(data.get("min_qty"), "tồn tối thiểu"), unit_price=_so(data.get("unit_price"), "đơn giá"))
    db.add(p); db.commit(); db.refresh(p)
    return _xuat_pt(p)


@router.put("/api/parts/{pid}")
def sua_phu_tung(pid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_KHO)):
    p = db.get(Part, pid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phụ tùng này."})
    if "name" in data: p.name = str(data["name"]).strip()
    if "unit" in data: p.unit = data["unit"]
    if "min_qty" in data: p.min_qty = _so(data["min_qty"], "tồn tối thiểu")
    if "unit_price" in data: p.unit_price = _so(data["unit_price"], "đơn giá")
    if "active" in data: p.active = bool(data["active"])
    db.commit(); db.refresh(p)
    return _xuat_pt(p)


@router.get("/api/parts/{pid}/moves")
def so_phu_tung(pid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [{"id": m.id, "move_date": m.move_date.isoformat(), "kind": m.kind, "qty": m.qty,
             "truck_no": m.truck_no, "trip_doc_no": m.trip_doc_no, "note": m.note, "by_user": m.by_user}
            for m in db.query(PartMove).filter(PartMove.part_id == pid).order_by(PartMove.move_date.desc()).all()]


@router.post("/api/parts/{pid}/moves")
def nhap_xuat_phu_tung(pid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_KHO)):
    p = db.get(Part, pid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phụ tùng này."})
    kind = data.get("kind")
    if kind not in ("in", "out"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "kind phải là in hoặc out."})
    qty = _so(data.get("qty"), "số lượng", bat_buoc=True)
    if qty <= 0:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số lượng phải lớn hơn 0."})
    if kind == "out" and qty > (p.qty or 0):
        raise HTTPException(409, {"ma": "KHONG_DU", "loi": "Tồn %s không đủ để xuất %s." % (p.qty, qty)})
    ngay = _ngay(data.get("move_date"))
    m = PartMove(part_id=p.id, move_date=ngay, kind=kind, qty=qty, truck_no=(data.get("truck_no") or "").strip() or None,
                 trip_doc_no=data.get("trip_doc_no"), note=data.get("note"), by_user=user.full_name)
    p.qty = (p.qty or 0) + (qty if kind == "in" else -qty)
    if kind == "out":
        p.last_date, p.last_truck = ngay, m.truck_no
    db.add(m); db.flush()
    CT.ghi(db, "PNK_PT" if kind == "in" else "PXK_PT", nguon_bang="part_moves", nguon_id=m.id, ngay=ngay,
           doi_tuong_loai="ncc" if kind == "in" else "kho", doi_tuong_ten=p.name,
           tien=qty * (p.unit_price or 0), tien_te="LAK", section="repair", by_user=user.full_name,
           mo_ta="%s %s %s%s" % ("Nhập" if kind == "in" else "Xuất", qty, p.name, (" · xe " + m.truck_no) if m.truck_no else ""),
           payload={"part_id": p.id, "qty": qty, "unit_price": p.unit_price, "truck_no": m.truck_no, "trip_doc_no": m.trip_doc_no})
    db.commit(); db.refresh(p)
    return _xuat_pt(p)
