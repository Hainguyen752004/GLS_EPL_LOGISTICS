# -*- coding: utf-8 -*-
"""SỔ KHO HÀNG KHÁCH GỬI ở bãi Thà Bốc — lại ở TRANG ĐIỀU XE từ 05/10 (bỏ kho tạm 8031). Quặng ở bãi là hàng của khách, không phải
tài sản kho EPL nên không sang kho QLSX anh Tune; sổ `goods_moves` bên này dùng lại (chép đúng luật bên kho tạm —
EPL_KETOAN services/kho_hang.py: tồn lô = nhập + điều chỉnh − xuất, lô = một DO gom, phiếu giao thay toàn bộ phần xuất của nó,
kiểm tồn từng lô, lô đã có phiếu giao khác lấy thì không xoá / gỡ được). Cùng giao dịch với phiếu: lưu hỏng thì rollback là xong.

services/kho_ke_toan.py rẽ sang đây khi kho_qlsx.bat(); dữ liệu cũ bên kho tạm chép về bằng tools/may_thu/chuyen_ton_dau_qlsx.py
(--hang-khach). Điều chỉnh lô và màn Kho hàng chưa có ở đây (kho tạm tắt thì tắt theo) — ghi rõ ở báo cáo.
"""
import datetime as dt

from fastapi import HTTPException

from models import GoodsMove, Trip

DEPOT = "Thà Bốc"
SAI = 0.0005


def _khoa_lo(db, *lo):
    """Khoá dòng phiếu gom của các lô (theo thứ tự mã) rồi mới đọc tồn — hai phiếu giao cùng lấy một lô không cùng lọt."""
    ids = sorted({x for x in lo if x})
    if ids:
        db.query(Trip.id).filter(Trip.id.in_(ids)).order_by(Trip.id).with_for_update().all()


def ton_lo(db, lo_trip_id, tru_phieu_id=None):
    vao = sum(m.qty_t for m in db.query(GoodsMove).filter(GoodsMove.lo_trip_id == lo_trip_id, GoodsMove.kind.in_(("in", "adj"))))
    q = db.query(GoodsMove).filter(GoodsMove.lo_trip_id == lo_trip_id, GoodsMove.kind == "out")
    if tru_phieu_id:
        q = q.filter(GoodsMove.trip_id != tru_phieu_id)
    return round(vao - sum(m.qty_t for m in q), 3)


def danh_sach_lo(db, con_hang=True, tru_phieu_id=None):
    """Lô còn hàng — cùng khoá với kho tạm: lo_trip_id, doc_no, goods_name, ngay, nhap_t, dieu_chinh_t, con_t, customer_name,
    origin, truck_no."""
    lo = {}
    for m in db.query(GoodsMove).filter(GoodsMove.kind == "in").order_by(GoodsMove.move_date):
        o = lo.setdefault(m.lo_trip_id, {"lo_trip_id": m.lo_trip_id, "doc_no": m.trip_doc_no, "goods_name": m.goods_name,
                                         "ngay": m.move_date, "nhap_t": 0.0})
        o["nhap_t"] += m.qty_t
    ra = []
    for k, o in lo.items():
        p = db.get(Trip, k) if k else None
        o["nhap_t"] = round(o["nhap_t"], 3)
        o["dieu_chinh_t"] = round(sum(m.qty_t for m in db.query(GoodsMove).filter(GoodsMove.lo_trip_id == k, GoodsMove.kind == "adj")), 3)
        o["con_t"] = ton_lo(db, k, tru_phieu_id)
        o["ngay"] = o["ngay"].isoformat() if o["ngay"] else None
        o.update(customer_name=p.customer_name if p else None, origin=p.origin if p else None, truck_no=p.truck_no if p else None)
        if not con_hang or o["con_t"] > SAI:
            ra.append(o)
    return sorted(ra, key=lambda x: (x["ngay"] or "", x["doc_no"] or ""))


def cua_phieu(db, trip_id):
    """{da_nhap, ton_lo, lay_boi, xuat} — như /api/lien-thong/kho-hang/phieu/{id} của kho tạm."""
    nhap = db.query(GoodsMove.id).filter(GoodsMove.trip_id == trip_id, GoodsMove.kind == "in").first() is not None
    lay = db.query(GoodsMove).filter(GoodsMove.lo_trip_id == trip_id, GoodsMove.kind == "out", GoodsMove.trip_id != trip_id).all()
    xuat = db.query(GoodsMove).filter(GoodsMove.trip_id == trip_id, GoodsMove.kind == "out").all()
    return {"da_nhap": nhap, "ton_lo": ton_lo(db, trip_id) if nhap else None, "lay_boi": sorted({m.trip_doc_no or "?" for m in lay}),
            "xuat": [{"goods_name": m.goods_name, "qty_t": m.qty_t, "lo_trip_id": m.lo_trip_id} for m in xuat]}


def nhap(db, trip, dong, ngay, by_user):
    """Phiếu gom về tới bãi → nhập theo số thực nhập đã chia sẵn. Gọi lại không nhập trùng → {da_co, so_dong}."""
    if db.query(GoodsMove.id).filter(GoodsMove.trip_id == trip.id, GoodsMove.kind == "in").first():
        return {"da_co": True}
    n = 0
    for x in dong or []:
        sl = round(float(x.get("qty_t") or 0), 3)
        if sl <= 0:
            continue
        db.add(GoodsMove(move_date=ngay or dt.date.today(), kind="in", goods_name=x.get("goods_name") or "—", qty_t=sl, trip_id=trip.id,
                         trip_doc_no=trip.doc_no, lo_trip_id=trip.id, depot=DEPOT, by_user=by_user))
        n += 1
    db.flush()
    return {"da_co": False, "so_dong": n}


def xuat(db, trip, dong, ngay, by_user):
    """Lưu phiếu giao → THAY toàn bộ phần xuất của phiếu, kiểm tồn từng lô (cộng các dòng cùng lô) → {cu}."""
    dong = [x for x in (dong or []) if round(float(x.get("qty_t") or 0), 3) > 0]
    can = {}
    for x in dong:
        lo = str(x.get("lo_trip_id") or "").strip()
        if not lo or not db.query(GoodsMove.id).filter(GoodsMove.lo_trip_id == lo, GoodsMove.kind == "in").first():
            raise HTTPException(422, {"ma": "LO_CHUA_NHAP", "loi": "Lô hàng phải là một phiếu gom đã nhập kho bãi."})
        can[lo] = can.get(lo, 0) + float(x.get("qty_t") or 0)
    _khoa_lo(db, *can)
    for lo, sl in can.items():
        con = ton_lo(db, lo, tru_phieu_id=trip.id)
        if sl - con > SAI:
            g = db.query(GoodsMove).filter(GoodsMove.lo_trip_id == lo, GoodsMove.kind == "in").first()
            raise HTTPException(409, {"ma": "VUOT_TON", "loi": "Lô %s (%s) chỉ còn %s tấn, không lấy được %s tấn." % (
                g.trip_doc_no if g else lo, g.goods_name if g else "", round(con, 3), round(sl, 3))})
    cu_q = db.query(GoodsMove).filter(GoodsMove.trip_id == trip.id, GoodsMove.kind == "out")
    cu = [{"goods_name": m.goods_name, "qty_t": m.qty_t, "lo_trip_id": m.lo_trip_id} for m in cu_q]
    cu_q.delete(synchronize_session=False)
    for x in dong:
        db.add(GoodsMove(move_date=ngay or dt.date.today(), kind="out", goods_name=x.get("goods_name") or "—",
                         qty_t=round(float(x["qty_t"]), 3), trip_id=trip.id, trip_doc_no=trip.doc_no, lo_trip_id=x.get("lo_trip_id"),
                         depot=DEPOT, by_user=by_user))
    db.flush()
    return {"cu": cu}


def huy(db, trip_id):
    """Xoá phiếu → xoá mọi dòng sổ của phiếu (nhập / xuất / điều chỉnh lô của nó). Lô đã có phiếu giao khác lấy → 409."""
    _khoa_lo(db, trip_id)
    c = cua_phieu(db, trip_id)
    if c["lay_boi"]:
        raise HTTPException(409, {"ma": "LO_DA_XUAT", "loi": "Lô hàng của phiếu này đã xuất cho phiếu giao %s — xoá phiếu giao trước."
                                                           % ", ".join(c["lay_boi"])})
    ds = db.query(GoodsMove).filter((GoodsMove.trip_id == trip_id) | (GoodsMove.lo_trip_id == trip_id)).all()
    for m in ds:
        db.delete(m)
    db.flush()
    return {"ok": True, "so_dong": len(ds)}
