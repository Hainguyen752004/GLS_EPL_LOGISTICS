# -*- coding: utf-8 -*-
"""Mô-đun kho: kho nhiên liệu (ສາງນໍ້າມັນ · TK 625/371) và kho phụ tùng (ສາງອາໄຫຼ່ · TK 614/371).

Cả hai là SỔ KHO kiểu 2016: nhập một dòng, xuất một dòng, tồn = cộng dồn. Không có lô, không
FIFO, không định mức tiêu hao — Excel của họ không có mấy thứ đó.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FuelMove, FuelPlace, Part, PartMove, Supplier
from services import chung_tu as CT
from services import gia_von as GV
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi

router = APIRouter()
# Nhập, xuất tay, chuyển kho dầu: KT kho xăng dầu (Thà Bốc / Viêng Chăn) và kế toán — anh Khampla A1/A3: "ບັນຊີສາງ"
# lập đơn mua và nhập kho. Bãi xem được số lít tồn nhưng không thấy giá dầu (A2) nên không ghi sổ kho.
SUA_KHO = can_vai("fuel", "acct")
# Kho phụ tùng là của THỦ KHO PHỤ TÙNG Thà Bốc (anh Khampla C1.2) — trước đây Bãi và kế toán làm
# thay. Tổ sửa chữa xem được tồn nhưng không tự nhập xuất; họ lấy phụ tùng qua dòng mục V trên phiếu.
SUA_PHU_TUNG = can_vai("parts")


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
# Sổ kho dầu tính TỪNG KHO (anh Khampla C5.2: 7 kho) và giá BÌNH QUÂN (C5.3). Dầu mua ở Việt Nam đi
# qua kho (A3): nhập 1.000 lít vào "kho xe" → phiếu xuất xe lấy 600 lít từ kho đó → chuyển 400 lít còn
# lại về Thà Bốc hay một kho hiện trường bằng PHIẾU CHUYỂN KHO.
def _kho_epl(db, pid, ten="kho"):
    x = db.get(FuelPlace, pid) if pid else None
    if not x or x.owner_type != "epl":
        raise HTTPException(422, {"ma": "KHO_SAI", "loi": "Phải chọn %s dầu của EPL." % ten})
    return x


def _dong_so(db, m, ten_kho, ton):
    return {"id": m.id, "move_date": m.move_date.isoformat(), "doc_no": m.doc_no, "kind": m.kind,
            "truck_no": m.truck_no, "qty_in": m.qty_l if m.kind == "in" else 0,
            "qty_out": m.qty_l if m.kind == "out" else 0, "balance": round(ton, 1),
            "place_id": m.place_id, "place_name": ten_kho, "transfer_no": m.transfer_no,
            "unit_price": m.unit_price, "currency": m.currency, "unit_cost_lak": m.unit_cost_lak,
            "supplier_id": m.supplier_id, "note": m.note, "by_user": m.by_user}


@router.get("/api/fuel-moves")
def so_nhien_lieu(place_id: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    goc = GV.kho_goc(db)
    kho = db.query(FuelPlace).filter(FuelPlace.owner_type == "epl").order_by(FuelPlace.code).all()
    ten = {k.id: k.name for k in kho}
    q = db.query(FuelMove)
    if place_id:
        q = q.filter((FuelMove.place_id == place_id) | (FuelMove.place_id.is_(None))) if place_id == goc else q.filter(FuelMove.place_id == place_id)
    ton = {}; ra = []
    for m in q.order_by(FuelMove.move_date, FuelMove.created_at.asc().nullsfirst(), FuelMove.id).all():
        k = m.place_id or goc
        ton[k] = ton.get(k, 0.0) + (m.qty_l if m.kind == "in" else -m.qty_l)
        ra.append(_dong_so(db, m, ten.get(k), ton[k]))
    ra.reverse()          # mới nhất lên đầu, nhưng tồn đã tính theo thứ tự thời gian
    ds_kho = []
    for k in kho:
        lit, gia = GV.ton_dau(db, k.id)
        ds_kho.append({"id": k.id, "code": k.code, "name": k.name, "active": k.active, "ton_lit": lit, "gia_bq": gia})
    tong = sum(x["ton_lit"] for x in ds_kho if (not place_id or x["id"] == place_id))
    kq = {"ton_lit": round(tong, 1), "rows": ra, "kho": ds_kho, "place_id": place_id,
          "gia_bq": next((x["gia_bq"] for x in ds_kho if x["id"] == (place_id or goc)), 0)}
    if not thay_tien_chi(user.role):
        # Bãi thấy số lít, không thấy giá dầu (anh Khampla A2)
        kq.pop("gia_bq", None)
        for x in ds_kho: x.pop("gia_bq", None)
        for r in ra:
            for c in ("unit_price", "currency", "unit_cost_lak"): r.pop(c, None)
    return kq


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
    kho = _kho_epl(db, data.get("place_id") or GV.kho_goc(db))
    ngay = _ngay(data.get("move_date"))
    ncc = db.get(Supplier, data.get("supplier_id")) if data.get("supplier_id") else None
    if kind == "in":
        tien_te = str(data.get("currency") or "LAK").upper()
        gia = _so(data.get("unit_price"), "đơn giá")
        ty_gia = _so(data.get("rate_to_lak"), "tỷ giá") or GV.ty_gia_lak(db, tien_te)
        gia_lak = gia * (1.0 if tien_te == "LAK" else ty_gia)
    else:
        lit, gia_lak = GV.ton_dau(db, kho.id)
        if qty > lit + 0.001:
            raise HTTPException(409, {"ma": "KHONG_DU", "loi": "%s chỉ còn %s lít, không đủ xuất %s lít." % (kho.name, lit, qty)})
        tien_te, gia = "LAK", gia_lak
    m = FuelMove(move_date=ngay, doc_no=(data.get("doc_no") or "").strip() or None,
                 kind=kind, truck_no=(data.get("truck_no") or "").strip() or None, qty_l=qty,
                 unit_price=gia, currency=tien_te, unit_cost_lak=round(gia_lak, 4), place_id=kho.id,
                 supplier_id=ncc.id if ncc else None, note=data.get("note"), by_user=user.full_name)
    db.add(m); db.flush()
    if kind == "in":
        CT.ghi(db, "PNK_NL", nguon_bang="fuel_moves", nguon_id=m.id, ngay=m.move_date, doi_tuong_loai="ncc",
               doi_tuong_ten=ncc.name if ncc else None, tien=qty * (gia or 0), tien_te=tien_te, tien_lak=round(qty * gia_lak),
               by_user=user.full_name, mo_ta="Nhập %s lít dầu vào %s · %s" % (qty, kho.name, m.doc_no or ""),
               payload={"qty_l": qty, "unit_price": gia, "currency": tien_te, "unit_cost_lak": gia_lak,
                        "place_id": kho.id, "place_name": kho.name, "supplier_id": m.supplier_id, "doc_no": m.doc_no})
    db.commit()
    return so_nhien_lieu(data.get("view_place_id"), db, user)


def _so_chuyen_moi(db, ngay):
    tien_to = "CK-%s-" % ngay.strftime("%y%m")
    cu = [r[0] for r in db.query(FuelMove.transfer_no).filter(FuelMove.transfer_no.like(tien_to + "%")).distinct().all()]
    n = max([int(x.rsplit("-", 1)[-1]) for x in cu if x.rsplit("-", 1)[-1].isdigit()] or [0])
    return "%s%03d" % (tien_to, n + 1)


@router.post("/api/fuel-transfers")
def chuyen_kho(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_KHO)):
    """PHIẾU CHUYỂN KHO dầu: kho A → kho B. Hai dòng sổ kho cùng một số CK-…: ra ở A, vào ở B, mang theo giá
    bình quân của A lúc chuyển. Tiền không đổi chủ (vẫn là kho 1371 của EPL) nên tờ chứng từ không có định khoản."""
    tu = _kho_epl(db, data.get("from_place_id"), "kho chuyển đi")
    den = _kho_epl(db, data.get("to_place_id"), "kho nhận")
    if tu.id == den.id:
        raise HTTPException(422, {"ma": "CUNG_KHO", "loi": "Kho chuyển đi và kho nhận phải khác nhau."})
    qty = _so(data.get("qty_l"), "số lít", bat_buoc=True)
    if qty <= 0:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số lít phải lớn hơn 0."})
    lit, gia = GV.ton_dau(db, tu.id)
    if qty > lit + 0.001:
        raise HTTPException(409, {"ma": "KHONG_DU", "loi": "%s chỉ còn %s lít, không đủ chuyển %s lít." % (tu.name, lit, qty)})
    ngay = _ngay(data.get("move_date"))
    so = _so_chuyen_moi(db, ngay)
    ghi = (data.get("note") or "").strip() or None
    ra = FuelMove(move_date=ngay, doc_no=so, kind="out", qty_l=qty, unit_price=gia, currency="LAK", unit_cost_lak=gia,
                  place_id=tu.id, transfer_no=so, note="Chuyển sang %s%s" % (den.name, (" — " + ghi) if ghi else ""), by_user=user.full_name)
    db.add(ra); db.flush()
    vao = FuelMove(move_date=ngay, doc_no=so, kind="in", qty_l=qty, unit_price=gia, currency="LAK", unit_cost_lak=gia,
                   place_id=den.id, transfer_no=so, note="Nhận từ %s%s" % (tu.name, (" — " + ghi) if ghi else ""), by_user=user.full_name)
    db.add(vao); db.flush()
    CT.ghi(db, "CK_NL", nguon_bang="fuel_transfers", nguon_id=so, ngay=ngay, doi_tuong_loai="kho", doi_tuong_ten=den.name,
           tien=round(qty * gia), tien_te="LAK", by_user=user.full_name,
           mo_ta="Chuyển %s lít dầu %s → %s" % (qty, tu.name, den.name),
           payload={"transfer_no": so, "qty_l": qty, "unit_cost_lak": gia, "from_place_id": tu.id, "from_place": tu.name,
                    "to_place_id": den.id, "to_place": den.name})
    db.commit()
    return {"transfer_no": so, "qty_l": qty, "from": tu.name, "to": den.name, **so_nhien_lieu(None, db, user)}


@router.delete("/api/fuel-moves/{mid}")
def xoa_nhien_lieu(mid: str, db: Session = Depends(get_db), user=Depends(can_vai("fuel"))):
    m = db.get(FuelMove, mid)
    if not m:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có dòng này."})
    if m.transfer_no:
        # phiếu chuyển kho là HAI dòng — xoá một nửa thì kho này mất dầu mà kho kia không có
        for x in db.query(FuelMove).filter(FuelMove.transfer_no == m.transfer_no).all():
            db.delete(x)
        CT.rut(db, nguon_bang="fuel_transfers", nguon_id=m.transfer_no)
    else:
        CT.rut(db, nguon_bang="fuel_moves", nguon_id=m.id)
        db.delete(m)
    db.commit()
    return so_nhien_lieu(None, db, user)


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
def them_phu_tung(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_PHU_TUNG)):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Phụ tùng phải có tên."})
    p = Part(name=data["name"].strip(), unit=data.get("unit") or "u_pc", qty=_so(data.get("qty"), "tồn"),
             min_qty=_so(data.get("min_qty"), "tồn tối thiểu"), unit_price=_so(data.get("unit_price"), "đơn giá"))
    db.add(p); db.commit(); db.refresh(p)
    return _xuat_pt(p)


@router.put("/api/parts/{pid}")
def sua_phu_tung(pid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_PHU_TUNG)):
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
    return [{"id": m.id, "move_date": m.move_date.isoformat(), "kind": m.kind, "qty": m.qty, "unit_price": m.unit_price,
             "truck_no": m.truck_no, "trip_doc_no": m.trip_doc_no, "note": m.note, "by_user": m.by_user}
            for m in db.query(PartMove).filter(PartMove.part_id == pid).order_by(PartMove.move_date.desc()).all()]


@router.post("/api/parts/{pid}/moves")
def nhap_xuat_phu_tung(pid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_PHU_TUNG)):
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
    gia_nhap = _so(data.get("unit_price"), "đơn giá") if kind == "in" and data.get("unit_price") not in (None, "") else None
    if kind == "in":
        GV.nhap_phu_tung(p, qty, gia_nhap)          # giá bình quân (C5.3); nhập không ghi giá thì giữ giá cũ
    m = PartMove(part_id=p.id, move_date=ngay, kind=kind, qty=qty, truck_no=(data.get("truck_no") or "").strip() or None,
                 trip_doc_no=data.get("trip_doc_no"), note=data.get("note"), by_user=user.full_name,
                 unit_price=gia_nhap if gia_nhap else p.unit_price)
    p.qty = (p.qty or 0) + (qty if kind == "in" else -qty)
    if kind == "out":
        p.last_date, p.last_truck = ngay, m.truck_no
    db.add(m); db.flush()
    CT.ghi(db, "PNK_PT" if kind == "in" else "PXK_PT", nguon_bang="part_moves", nguon_id=m.id, ngay=ngay,
           doi_tuong_loai="ncc" if kind == "in" else "kho", doi_tuong_ten=None if kind == "in" else p.name,  # nhập: NCC chưa có ô, đừng lấy tên phụ tùng làm đối tượng
           tien=qty * (m.unit_price or 0), tien_te="LAK", section="repair", by_user=user.full_name,
           mo_ta="%s %s %s%s" % ("Nhập" if kind == "in" else "Xuất", qty, p.name, (" · xe " + m.truck_no) if m.truck_no else ""),
           payload={"part_id": p.id, "qty": qty, "unit_price": p.unit_price, "truck_no": m.truck_no, "trip_doc_no": m.trip_doc_no})
    db.commit(); db.refresh(p)
    return _xuat_pt(p)
