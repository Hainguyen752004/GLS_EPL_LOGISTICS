# -*- coding: utf-8 -*-
"""KHO HÀNG ở bãi Thà Bốc — chỗ quặng nằm giữa hai chặng.

Bãi Thà Bốc đứng giữa như một bưu cục: xe đi mỏ chở hàng về **nhập kho** (DO gom), rồi xe khác lấy
hàng trong kho **xuất kho** đi giao cho khách (DO giao). Hai DO nối nhau qua chính lô hàng đó:

    DO gom (mỏ → bãi) ──nhập kho──► LÔ HÀNG ở bãi ──xuất kho──► DO giao (bãi → cảng)

Quy ước trong mã:
  · **lô** = một DO gom. Tồn của lô = tấn đã nhập trừ tấn các DO giao đã lấy.
  · Không có bảng tồn riêng: tồn luôn tính cộng dồn từ `goods_moves`, để không bao giờ lệch với sổ.
  · Dòng hàng của DO giao ghi `tu_phieu_id` = DO gom lấy ra — đó là dây nối, và cũng là cách tra ngược
    "lô này đã đi những chuyến nào".
  · Chênh lệch cân ghi thành MỘT DÒNG `hao_hut` trên phiếu cho người đọc thấy ngay, thay vì bắt họ trừ nhẩm.
"""
import datetime as dt

from fastapi import HTTPException

from models import GoodsMove, Trip, TripGoods
from services import chung_tu as CT

DEPOT = "Thà Bốc"


# ---------------------------------------------------------------- đọc
def ton_lo(db, lo_trip_id, tru_phieu_id=None):
    """Còn bao nhiêu tấn trong lô (một DO gom). `tru_phieu_id`: bỏ qua phần DO giao này đang giữ,
    dùng khi sửa chính phiếu đó để nó không tự trừ mình hai lần."""
    vao = sum(m.qty_t for m in db.query(GoodsMove).filter(GoodsMove.lo_trip_id == lo_trip_id,
                                                          GoodsMove.kind == "in").all())
    q = db.query(GoodsMove).filter(GoodsMove.lo_trip_id == lo_trip_id, GoodsMove.kind == "out")
    if tru_phieu_id:
        q = q.filter(GoodsMove.trip_id != tru_phieu_id)
    ra = sum(m.qty_t for m in q.all())
    return round(vao - ra, 3)


def danh_sach_lo(db, con_hang=True, tru_phieu_id=None):
    """Các lô trong kho: lô nào, của DO gom nào, hàng gì, nhập bao nhiêu, còn bao nhiêu."""
    lo = {}
    for m in db.query(GoodsMove).filter(GoodsMove.kind == "in").order_by(GoodsMove.move_date).all():
        o = lo.setdefault(m.lo_trip_id, {"lo_trip_id": m.lo_trip_id, "doc_no": m.trip_doc_no,
                                         "goods_name": m.goods_name, "ngay": m.move_date, "nhap_t": 0.0})
        o["nhap_t"] += m.qty_t
    ra = []
    for k, o in lo.items():
        p = db.get(Trip, k) if k else None
        o["nhap_t"] = round(o["nhap_t"], 3)
        o["con_t"] = ton_lo(db, k, tru_phieu_id)
        o["ngay"] = o["ngay"].isoformat() if o["ngay"] else None
        o["customer_name"] = p.customer_name if p else None
        o["origin"] = p.origin if p else None
        o["truck_no"] = p.truck_no if p else None
        if not con_hang or o["con_t"] > 0.0005:
            ra.append(o)
    return sorted(ra, key=lambda x: (x["ngay"] or "", x["doc_no"] or ""))


def so_kho(db, tu=None, den=None):
    """Sổ nhập xuất, cũ trước mới sau, kèm tồn cộng dồn."""
    q = db.query(GoodsMove)
    if tu: q = q.filter(GoodsMove.move_date >= tu)
    if den: q = q.filter(GoodsMove.move_date <= den)
    ds = sorted(q.all(), key=lambda m: (m.move_date, m.created_at or dt.datetime.min))
    ton, ra = 0.0, []
    for m in ds:
        ton += m.qty_t if m.kind == "in" else -m.qty_t
        ra.append({"id": m.id, "ngay": m.move_date.isoformat() if m.move_date else None, "kind": m.kind,
                   "goods_name": m.goods_name, "qty_t": m.qty_t, "doc_no": m.trip_doc_no,
                   "trip_id": m.trip_id, "lo_trip_id": m.lo_trip_id, "ton_t": round(ton, 3),
                   "note": m.note, "by_user": m.by_user})
    return ra, round(ton, 3)


def dong_hang(db, trip_id):
    """Các dòng hàng của một phiếu, kèm số phiếu của lô để màn hình khỏi phải tra thêm."""
    ra = []
    for g in db.query(TripGoods).filter(TripGoods.trip_id == trip_id).order_by(TripGoods.loai).all():   # 'hang' trước, 'hao_hut' sau
        lo = db.get(Trip, g.tu_phieu_id) if g.tu_phieu_id else None
        ra.append({"id": g.id, "loai": g.loai, "goods_name": g.goods_name, "qty_t": g.qty_t,
                   "tu_phieu_id": g.tu_phieu_id, "tu_phieu_doc_no": lo.doc_no if lo else None, "note": g.note})
    return ra


# ---------------------------------------------------------------- ghi
def _xoa_dong_xuat(db, trip):
    for m in db.query(GoodsMove).filter(GoodsMove.trip_id == trip.id, GoodsMove.kind == "out").all():
        db.delete(m)


def dat_dong_hang(db, trip, dong, user):
    """Ghi lại toàn bộ dòng hàng của một phiếu (thay thế, không cộng dồn).

    DO giao: mỗi dòng phải chỉ rõ lấy từ lô nào và không được lấy quá tồn của lô; ghi xong thì sổ kho
    có ngay dòng XUẤT tương ứng. DO gom: chỉ ghi hàng bốc ở mỏ, hàng chỉ vào kho khi xe VỀ TỚI BÃI.
    """
    if dong is None:
        return
    cu = {g.id: g for g in db.query(TripGoods).filter(TripGoods.trip_id == trip.id).all()}
    for g in cu.values():
        db.delete(g)
    db.flush()
    _xoa_dong_xuat(db, trip)
    db.flush()

    moi = []
    for d in dong:
        loai = (d.get("loai") or "hang").strip()
        if loai not in ("hang", "hao_hut"):
            raise HTTPException(422, {"ma": "LOAI_HANG_SAI", "loi": "Dòng hàng chỉ có loại 'hang' hoặc 'hao_hut'."})
        ten = (d.get("goods_name") or "").strip()
        if not ten:
            raise HTTPException(422, {"ma": "THIEU_TEN_HANG", "loi": "Dòng hàng phải có tên mặt hàng."})
        try:
            sl = float(str(d.get("qty_t") or 0).replace(",", ""))
        except ValueError:
            raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số tấn phải là số."})
        if sl < 0:
            raise HTTPException(422, {"ma": "SO_AM", "loi": "Số tấn không được âm."})
        lo = (d.get("tu_phieu_id") or "").strip() or None
        if trip.kind == "giao" and loai == "hang":
            if not lo:
                raise HTTPException(422, {"ma": "THIEU_LO", "loi": "Phiếu giao hàng phải chỉ rõ lấy hàng từ phiếu gom nào."})
            g = db.get(Trip, lo)
            if not g or g.kind != "gom":
                raise HTTPException(422, {"ma": "LO_SAI", "loi": "Lô hàng phải là một phiếu gom hàng đã nhập kho."})
            con = ton_lo(db, lo, tru_phieu_id=trip.id)
            if sl - con > 0.0005:
                raise HTTPException(409, {"ma": "KHONG_DU_HANG",
                                          "loi": "Lô %s chỉ còn %s tấn, không lấy được %s tấn." % (g.doc_no, round(con, 2), round(sl, 2))})
        g = TripGoods(trip_id=trip.id, loai=loai, goods_name=ten, qty_t=sl,
                      tu_phieu_id=lo if loai == "hang" else None, note=(d.get("note") or "").strip() or None)
        db.add(g); moi.append(g)
        if trip.kind == "giao" and loai == "hang" and sl > 0:
            db.add(GoodsMove(move_date=trip.out_date or trip.doc_date or dt.date.today(), kind="out",
                             goods_name=ten, qty_t=sl, trip_id=trip.id, trip_doc_no=trip.doc_no,
                             lo_trip_id=lo, depot=DEPOT, by_user=getattr(user, "full_name", None)))
    db.flush()
    # Cân đầu của DO giao chính là tổng tấn lấy ra khỏi kho; DO gom thì là tổng tấn bốc ở mỏ.
    tong = round(sum(g.qty_t for g in moi if g.loai == "hang"), 3)
    if tong:
        trip.weight_origin = tong
    _ghi_chung_tu_xuat(db, trip, user)


def _ghi_chung_tu_xuat(db, trip, user):
    if trip.kind != "giao":
        return
    tong = round(sum(g.qty_t for g in db.query(TripGoods).filter(TripGoods.trip_id == trip.id,
                                                                 TripGoods.loai == "hang").all()), 3)
    if tong <= 0:
        return
    CT.ghi(db, "PXK_HH", nguon_bang="trips", nguon_id=trip.id, trip=trip,
           ngay=trip.out_date or trip.doc_date, doi_tuong_loai="kho", doi_tuong_ten=DEPOT,
           tien=None, tien_lak=None, by_user=getattr(user, "full_name", None),
           mo_ta="Xuất kho hàng đi giao %s · %s tấn" % (trip.doc_no, tong),
           payload={"tan": tong, "dong": [{"hang": g.goods_name, "tan": g.qty_t, "lo": g.tu_phieu_id}
                                          for g in db.query(TripGoods).filter(TripGoods.trip_id == trip.id,
                                                                              TripGoods.loai == "hang").all()]})


def nhap_kho(db, trip, user):
    """DO gom về tới bãi → hàng vào kho. Gọi lại lần nữa không nhập trùng.

    Nhập theo **cân tại bãi** nếu có (đó mới là số thật vào kho); chênh với cân ở mỏ ghi thành một
    dòng hao hụt trên chính DO gom để hai bên cân đối.
    """
    if trip.kind != "gom":
        return
    if db.query(GoodsMove).filter(GoodsMove.trip_id == trip.id, GoodsMove.kind == "in").count():
        return
    hang = db.query(TripGoods).filter(TripGoods.trip_id == trip.id, TripGoods.loai == "hang").all()
    if not hang:
        return
    bocLen = round(sum(g.qty_t for g in hang), 3)
    thucNhap = trip.weight_dest if trip.weight_dest is not None else bocLen
    ngay = trip.back_date or trip.doc_date or dt.date.today()
    # Chia số thực nhập theo tỷ lệ các dòng hàng (thường chỉ có một dòng).
    for g in hang:
        phan = round(thucNhap * (g.qty_t / bocLen), 3) if bocLen else 0
        if phan <= 0:
            continue
        db.add(GoodsMove(move_date=ngay, kind="in", goods_name=g.goods_name, qty_t=phan,
                         trip_id=trip.id, trip_doc_no=trip.doc_no, lo_trip_id=trip.id, depot=DEPOT,
                         by_user=getattr(user, "full_name", None)))
    hao = round(bocLen - thucNhap, 3)
    if abs(hao) > 0.0005:
        db.add(TripGoods(trip_id=trip.id, loai="hao_hut", goods_name=hang[0].goods_name, qty_t=hao,
                         note="Cân mỏ %s t − cân bãi %s t" % (bocLen, thucNhap)))
    db.flush()
    CT.ghi(db, "PNK_HH", nguon_bang="trips", nguon_id=trip.id, trip=trip, ngay=ngay,
           doi_tuong_loai="kho", doi_tuong_ten=DEPOT, by_user=getattr(user, "full_name", None),
           mo_ta="Nhập kho hàng từ %s · %s tấn" % (trip.doc_no, round(thucNhap, 3)),
           payload={"tan": round(thucNhap, 3), "boc_len": bocLen, "hao_hut": hao})


def ghi_hao_hut_giao(db, trip):
    """DO giao xong: chênh giữa tấn lấy khỏi kho và tấn cân ở nơi giao ghi thành một dòng hao hụt."""
    if trip.kind != "giao" or trip.weight_dest is None:
        return
    lay = round(sum(g.qty_t for g in db.query(TripGoods).filter(TripGoods.trip_id == trip.id,
                                                                TripGoods.loai == "hang").all()), 3)
    if not lay:
        return
    for g in db.query(TripGoods).filter(TripGoods.trip_id == trip.id, TripGoods.loai == "hao_hut").all():
        db.delete(g)
    hao = round(lay - trip.weight_dest, 3)
    if abs(hao) > 0.0005:
        ten = db.query(TripGoods).filter(TripGoods.trip_id == trip.id, TripGoods.loai == "hang").first()
        db.add(TripGoods(trip_id=trip.id, loai="hao_hut", goods_name=ten.goods_name if ten else "—",
                         qty_t=hao, note="Xuất kho %s t − cân nơi giao %s t" % (lay, trip.weight_dest)))
    db.flush()


def kiem_xoa(db, trip):
    """Không cho xoá một DO gom mà hàng của nó đã có người lấy đi giao."""
    if trip.kind != "gom":
        return
    lay = db.query(GoodsMove).filter(GoodsMove.lo_trip_id == trip.id, GoodsMove.kind == "out").all()
    if lay:
        so = ", ".join(sorted({m.trip_doc_no or "?" for m in lay}))
        raise HTTPException(409, {"ma": "LO_DA_XUAT",
                                  "loi": "Lô hàng của phiếu này đã xuất cho phiếu giao %s — xoá phiếu giao trước." % so})
