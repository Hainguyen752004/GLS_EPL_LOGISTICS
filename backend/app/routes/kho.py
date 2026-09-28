# -*- coding: utf-8 -*-
"""Mô-đun kho: kho nhiên liệu (ສາງນໍ້າມັນ · TK 625/371) và kho phụ tùng (ສາງອາໄຫຼ່ · TK 614/371).

Cả hai là SỔ KHO kiểu 2016: nhập một dòng, xuất một dòng, tồn = cộng dồn. Không có lô, không
FIFO, không định mức tiêu hao — Excel của họ không có mấy thứ đó.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FuelMove, FuelPlace, Part, Supplier
from services import chung_tu as CT
from services import gia_von as GV
from services import kho_ke_toan as KK
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi

router = APIRouter()
# Nhập, xuất tay, chuyển kho dầu: KT kho xăng dầu (Thà Bốc / Viêng Chăn) và kế toán — anh Khampla A1/A3: "ບັນຊີສາງ"
# lập đơn mua và nhập kho. Bãi xem được số lít tồn nhưng không thấy giá dầu (A2) nên không ghi sổ kho.
SUA_KHO = can_vai("fuel", "acct")
# Kho phụ tùng là của THỦ KHO PHỤ TÙNG Thà Bốc (anh Khampla C1.2) — trước đây Bãi và kế toán làm
# thay. Tổ sửa chữa xem được tồn nhưng không tự nhập xuất; họ lấy phụ tùng qua dòng mục V trên phiếu.


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


# ---------------------------------------------------------------- kho phụ tùng — ở trang kế toán từ 28/09
# Danh mục, tồn, giá bình quân và sổ nhập xuất phụ tùng dời sang trang kế toán. Bảng parts bên này chỉ còn là bản chép
# danh mục (khoá ngoại của dòng chi mục V, dòng lệnh sửa, dòng bán). Ô chọn phụ tùng trên phiếu hỏi tồn / giá thẳng
# bên đó; nhập / xuất / sửa danh mục làm ở trang kế toán (Kho → Kho phụ tùng).
DA_DOI_PT = {"ma": "DA_DOI_SANG_KE_TOAN",
             "loi": "Kho phụ tùng nay quản lý ở trang kế toán (Kho → Kho phụ tùng). Ở đây chỉ còn danh mục để chọn trên phiếu."}


@router.get("/api/parts")
def ds_phu_tung(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Phụ tùng đang dùng kèm tồn và giá bình quân HIỆN TẠI của trang kế toán. Trang kế toán tắt thì vẫn trả danh mục
    bản chép (không tồn, không giá, `khong_noi`) để phiếu mở được; xuất kho lúc đó sẽ bị chặn và báo rõ."""
    try:
        ds = [x for x in KK.ds_phu_tung(db) if x.get("active")]
    except HTTPException:
        ds = [{"id": p.id, "name": p.name, "unit": p.unit, "qty": None, "min_qty": p.min_qty, "unit_price": None,
               "active": p.active, "status": None, "khong_noi": True}
              for p in db.query(Part).filter(Part.active.is_(True)).order_by(Part.name).all()]
    if not thay_tien_chi(user.role):            # Bãi không thấy giá (anh Khampla A2)
        for r in ds: r.pop("unit_price", None)
    return ds


@router.post("/api/parts")
def them_phu_tung(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)


@router.put("/api/parts/{pid}")
def sua_phu_tung(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)


@router.get("/api/parts/{pid}/moves")
def so_phu_tung(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)


@router.post("/api/parts/{pid}/moves")
def nhap_xuat_phu_tung(pid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI_PT)
