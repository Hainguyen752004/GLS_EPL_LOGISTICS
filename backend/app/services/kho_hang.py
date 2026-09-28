# -*- coding: utf-8 -*-
"""KHO HÀNG ở bãi Thà Bốc — chỗ quặng nằm giữa hai chặng. SỔ KHO ở trang kế toán từ 28/09 (đợt 5).

Bãi Thà Bốc đứng giữa như một bưu cục: xe đi mỏ chở hàng về **nhập kho** (DO gom), rồi xe khác lấy
hàng trong kho **xuất kho** đi giao cho khách (DO giao). Hai DO nối nhau qua chính lô hàng đó:

    DO gom (mỏ → bãi) ──nhập kho──► LÔ HÀNG ở bãi ──xuất kho──► DO giao (bãi → cảng)

Chia hai nơi (chủ dự án chốt 28/09: trang điều xe không xem được kho):
  · Ở ĐÂY: dòng hàng trên phiếu (`trip_goods`) — giấy của chuyến: hàng gì, bao nhiêu tấn, DO giao lấy từ DO gom nào
    (`tu_phieu_id` — dây nối hai DO), dòng `hao_hut` chênh cân.
  · Ở TRANG KẾ TOÁN: sổ kho hàng (`goods_moves`), tồn từng lô, tờ PNK_HH / PXK_HH / DC_HH, màn Kho hàng, điều chỉnh.
    Bảng `goods_moves` bên này đứng yên từ ngày dời (tools/doi_kho_hang.py bên đó đã chép sang), không đọc nữa.
Phiếu đụng tới sổ (xe gom về bãi, lưu phiếu giao có lấy lô, xoá phiếu) thì gọi sang qua `GiaoDichKho`; trang kế
toán tắt → 503, việc đó chưa làm được (chặn và báo rõ). Việc không đụng sổ vẫn chạy như thường.
"""
import datetime as dt

from fastapi import HTTPException

from models import Trip, TripGoods
from services import kho_ke_toan as KK


# ---------------------------------------------------------------- đọc
def ton_lo(db, lo_trip_id):
    """Còn bao nhiêu tấn trong lô (một DO gom) — hỏi trang kế toán. Chưa nhập kho, hay trang kế toán tắt → None
    (mở phiếu không bị chặn vì chuyện này)."""
    try:
        return KK.hang_cua_phieu(db, lo_trip_id).get("ton_lo")
    except HTTPException:
        return None


def dong_hang(db, trip_id):
    """Các dòng hàng của một phiếu, kèm số phiếu của lô để màn hình khỏi phải tra thêm."""
    ra = []
    for g in db.query(TripGoods).filter(TripGoods.trip_id == trip_id).order_by(TripGoods.loai).all():   # 'hang' trước, 'hao_hut' sau
        lo = db.get(Trip, g.tu_phieu_id) if g.tu_phieu_id else None
        ra.append({"id": g.id, "loai": g.loai, "goods_name": g.goods_name, "qty_t": g.qty_t,
                   "tu_phieu_id": g.tu_phieu_id, "tu_phieu_doc_no": lo.doc_no if lo else None, "note": g.note})
    return ra


def co_hang(db, trip_id):
    return db.query(TripGoods.id).filter(TripGoods.trip_id == trip_id, TripGoods.loai == "hang").first() is not None


def da_nhap_kho(db, trip):
    """DO gom đã vào kho bãi chưa. Hàng chỉ vào kho lúc xe VỀ TỚI BÃI (`nhap_kho`), nên phiếu chưa tới nơi thì chưa;
    đã tới thì hỏi trang kế toán — tắt thì chặn (503): không biết sổ đã ghi hay chưa thì không cho sửa cân."""
    if trip.kind != "gom" or not co_hang(db, trip.id):
        return False
    try:
        return bool(KK.hang_cua_phieu(db, trip.id).get("da_nhap"))
    except HTTPException:
        if trip.transport_status != "arrived":
            return False
        raise


# ---------------------------------------------------------------- ghi
def dat_dong_hang(db, trip, dong, user, gd):
    """Ghi lại toàn bộ dòng hàng của một phiếu (thay thế, không cộng dồn).

    DO giao: mỗi dòng phải chỉ rõ lấy từ lô nào; sổ kho bên trang kế toán thay phần XUẤT của phiếu theo dòng mới và
    không cho lấy quá tồn của lô. DO gom: chỉ ghi hàng bốc ở mỏ, hàng chỉ vào kho khi xe VỀ TỚI BÃI.
    """
    if dong is None:
        return
    cu = db.query(TripGoods).filter(TripGoods.trip_id == trip.id).all()
    co_xuat_cu = trip.kind == "giao" and any(g.loai == "hang" and (g.qty_t or 0) > 0 for g in cu)
    for g in cu:
        db.delete(g)
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
        g = TripGoods(trip_id=trip.id, loai=loai, goods_name=ten, qty_t=sl,
                      tu_phieu_id=lo if loai == "hang" else None, note=(d.get("note") or "").strip() or None)
        db.add(g); moi.append(g)
    db.flush()
    # Sổ kho bên trang kế toán: thay phần xuất của phiếu giao (kiểm tồn từng lô ở bên đó). Phiếu giao chưa từng lấy
    # hàng và nay cũng không lấy thì khỏi gọi — lưu phiếu không đụng kho vẫn chạy khi trang kế toán tắt.
    xuat = [{"goods_name": g.goods_name, "qty_t": g.qty_t, "lo_trip_id": g.tu_phieu_id}
            for g in moi if g.loai == "hang" and g.qty_t > 0]
    if trip.kind == "giao" and (xuat or co_xuat_cu):
        gd.xuat_hang(trip, xuat, ngay=trip.out_date or trip.doc_date or dt.date.today())
    # Cân đầu của DO giao chính là tổng tấn lấy ra khỏi kho; DO gom thì là tổng tấn bốc ở mỏ.
    tong = round(sum(g.qty_t for g in moi if g.loai == "hang"), 3)
    if tong:
        trip.weight_origin = tong


def nhap_kho(db, trip, user, gd):
    """DO gom về tới bãi → hàng vào kho (sổ bên trang kế toán). Gọi lại lần nữa không nhập trùng.

    Nhập theo **cân tại bãi** nếu có (đó mới là số thật vào kho); chênh với cân ở mỏ ghi thành một
    dòng hao hụt trên chính DO gom để hai bên cân đối.
    """
    if trip.kind != "gom":
        return
    hang = db.query(TripGoods).filter(TripGoods.trip_id == trip.id, TripGoods.loai == "hang").all()
    if not hang:
        return
    bocLen = round(sum(g.qty_t for g in hang), 3)
    thucNhap = trip.weight_dest if trip.weight_dest is not None else bocLen
    ngay = trip.back_date or trip.doc_date or dt.date.today()
    # Chia số thực nhập theo tỷ lệ các dòng hàng (thường chỉ có một dòng).
    dong = [{"goods_name": g.goods_name, "qty_t": round(thucNhap * (g.qty_t / bocLen), 3) if bocLen else 0} for g in hang]
    hao = round(bocLen - thucNhap, 3)
    r = gd.nhap_hang(trip, dong, ngay=ngay, tan=round(thucNhap, 3), boc_len=bocLen, hao_hut=hao)
    if r.get("da_co"):
        return
    if abs(hao) > 0.0005:
        db.add(TripGoods(trip_id=trip.id, loai="hao_hut", goods_name=hang[0].goods_name, qty_t=hao,
                         note="Cân mỏ %s t − cân bãi %s t" % (bocLen, thucNhap)))
    db.flush()


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
    """Không cho xoá một DO gom mà hàng của nó đã có người lấy đi giao (hỏi sổ bên trang kế toán)."""
    if trip.kind != "gom" or not co_hang(db, trip.id):
        return
    lay = KK.hang_cua_phieu(db, trip.id).get("lay_boi") or []
    if lay:
        raise HTTPException(409, {"ma": "LO_DA_XUAT",
                                  "loi": "Lô hàng của phiếu này đã xuất cho phiếu giao %s — xoá phiếu giao trước." % ", ".join(lay)})


def xoa_so(db, trip, user):
    """Xoá phiếu → xoá dòng sổ kho hàng của nó bên trang kế toán (nhập / xuất / điều chỉnh lô), rút tờ kho."""
    if not db.query(TripGoods.id).filter(TripGoods.trip_id == trip.id).first():
        return
    KK.huy_hang(db, user, trip.id)
