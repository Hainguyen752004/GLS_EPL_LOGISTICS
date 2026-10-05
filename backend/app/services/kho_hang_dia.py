# -*- coding: utf-8 -*-
"""SỔ KHO HÀNG KHÁCH GỬI ở bãi Thà Bốc — lại ở TRANG ĐIỀU XE từ 05/10 (bỏ kho tạm 8031). Quặng ở bãi là hàng của khách, không phải
tài sản kho EPL nên không sang kho QLSX anh Tune; sổ `goods_moves` bên này dùng lại (chép đúng luật bên kho tạm —
EPL_KETOAN services/kho_hang.py: tồn lô = nhập + điều chỉnh − xuất, lô = một DO gom, phiếu giao thay toàn bộ phần xuất của nó,
kiểm tồn từng lô, lô đã có phiếu giao khác lấy thì không xoá / gỡ được). Cùng giao dịch với phiếu: lưu hỏng thì rollback là xong.

services/kho_ke_toan.py rẽ sang đây khi kho_qlsx.bat(); dữ liệu cũ bên kho tạm chép về bằng tools/may_thu/chuyen_ton_dau_qlsx.py
(--hang-khach).

05/10 (chủ dự án duyệt "máy tự tạo phiếu") — chép cách làm của kho tạm (EPL_KETOAN kho_hang.py + chung_tu_kho.py):
  · TỜ TỰ SINH, tiền = 0, chỉ tấn (services/chung_tu.py: ngoài bảng, một vế, mã cấu hình `ma_hang_khach_gui`), số theo
    CT.ghi (LOAI/YYMM/0001):
      PNK_HH — DO gom báo "Xe đã tới" (một DO gom = một tờ = một lô), số tấn = CÂN BÃI (bắt buộc: 422 THIEU_CAN_BAI);
      PXK_HH — DO giao (một DO giao = một tờ, các dòng theo lô): sinh / THAY nội dung (giữ số) mỗi lần lưu đổi phần xuất, rút khi
               phiếu giao không còn lấy hàng; tờ đã đối chiếu thì không sửa lặng lẽ (409 TO_DA_DOI_CHIEU);
      DC_HH  — đơn điều chỉnh (bảng dieu_chinh_hang) được duyệt.
    Xoá DO → rút tờ CHƯA đối chiếu (CT.rut, chỉ ba loại tờ kho hàng); tờ đã đối chiếu giữ như mọi tờ khác.
  · ĐIỀU CHỈNH (cân sai, hao ở bãi, kiểm kê, đóng lô dư lẻ): Bãi lập → chờ duyệt, CHƯA đổi tồn; KT Thu/Chi Viêng Chăn (acct) hoặc
    Sếp duyệt → dòng adj (qty_t có dấu) + DC_HH; từ chối phải ghi lý do. Duyệt mà tồn lô âm → 409.
  · ĐỌC: mọi lô gom MỘT câu GROUP BY (`_bang_lo`) — trước 05/10 mỗi lô 3–4 truy vấn. `danh_sach_lo` giữ khuôn cũ cho ô chọn lô.
  · Xoá DO vẫn XOÁ CỨNG dòng sổ: chính DO bị xoá cứng (routes/phieu.xoa_phieu) và goods_moves.trip_id ON DELETE CASCADE — đánh dấu
    huỷ thì dòng vẫn mất theo DO; muốn giữ phải đổi khoá ngoại + thêm cột trên bảng cũ. Dấu vết còn ở tờ đã đối chiếu.
"""
import datetime as dt
import json

from fastapi import HTTPException
from sqlalchemy import and_, case, exists, func, or_

from models import ChungTu, DieuChinhHang, GoodsMove, Trip, TripGoods, bay_gio
from services import chung_tu as CT

DEPOT = "Thà Bốc"
SAI = 0.0005
TO_HANG = ("PNK_HH", "PXK_HH")             # tờ nguồn "trips" của kho hàng (DC_HH nguồn "goods_moves")
VAI_LAP_DC = ("yard", "admin")             # Bãi (Admin Thà Bốc) lập đơn điều chỉnh
VAI_DUYET_DC = ("acct", "admin")           # KT Thu/Chi Viêng Chăn — người xác nhận mục II (cân, hàng) — và Sếp
TRANG_THAI_DC = ("cho", "da_duyet", "tu_choi")


def _iso(d):
    return d.isoformat() if d else None


def _pl(to):
    try:
        return json.loads(to.payload) if to is not None and to.payload else {}
    except ValueError:
        return {}


def _ten(nguoi):
    if nguoi is None:
        return None
    return getattr(nguoi, "full_name", None) or getattr(nguoi, "username", None)


def _khoa_lo(db, *lo):
    """Khoá dòng phiếu gom của các lô (theo thứ tự mã) rồi mới đọc tồn — hai phiếu giao cùng lấy một lô không cùng lọt."""
    ids = sorted({x for x in lo if x})
    if ids:
        db.query(Trip.id).filter(Trip.id.in_(ids)).order_by(Trip.id).with_for_update().all()


def _dk_xuat(tru_phieu_id=None):
    """Dòng xuất được tính vào tồn — bỏ phần phiếu giao `tru_phieu_id` đang giữ (sửa chính phiếu đó)."""
    if not tru_phieu_id:
        return GoodsMove.kind == "out"
    return and_(GoodsMove.kind == "out", or_(GoodsMove.trip_id.is_(None), GoodsMove.trip_id != tru_phieu_id))


def ton_lo(db, lo_trip_id, tru_phieu_id=None):
    """Tồn một lô = nhập + điều chỉnh (có dấu) − xuất — một câu SUM."""
    G = GoodsMove
    v = (db.query(func.sum(case((G.kind.in_(("in", "adj")), G.qty_t), (_dk_xuat(tru_phieu_id), -G.qty_t), else_=0.0)))
         .filter(G.lo_trip_id == lo_trip_id).scalar())
    return round(float(v or 0), 3)


def _bang_lo(db, *, lo_ids=None, tru_phieu_id=None, q=None, khach=None, chi_con=False, moi_truoc=False):
    """MỌI LÔ trong MỘT câu: gom goods_moves theo lô (nhập · điều chỉnh · xuất · ngày nhập · ngày xuất cuối · tên hàng), nối DO gom
    (khách, nơi lấy, xe) và tờ PNK_HH. Lô = có ít nhất một dòng nhập. → [{lo, doc_no, ten, ngay, xuat_cuoi, nhap, dc, xuat, ton,
    khach, origin, truck_no, so_pnk}]."""
    G = GoodsMove
    la_nhap = G.kind == "in"
    sub = (db.query(G.lo_trip_id.label("lo"),
                    func.coalesce(func.sum(case((la_nhap, G.qty_t), else_=0.0)), 0.0).label("nhap"),
                    func.coalesce(func.sum(case((G.kind == "adj", G.qty_t), else_=0.0)), 0.0).label("dc"),
                    func.coalesce(func.sum(case((_dk_xuat(tru_phieu_id), G.qty_t), else_=0.0)), 0.0).label("xuat"),
                    func.min(case((la_nhap, G.move_date))).label("ngay"),
                    func.max(case((G.kind == "out", G.move_date))).label("xuat_cuoi"),
                    func.min(case((la_nhap, G.goods_name))).label("ten"),
                    func.min(case((la_nhap, G.trip_doc_no))).label("so"))
           .filter(G.lo_trip_id.isnot(None)))
    if lo_ids is not None:
        sub = sub.filter(G.lo_trip_id.in_(sorted(lo_ids)))
    sub = sub.group_by(G.lo_trip_id).having(func.count(case((la_nhap, 1))) > 0).subquery()
    ton = sub.c.nhap + sub.c.dc - sub.c.xuat
    qr = (db.query(sub.c.lo, sub.c.nhap, sub.c.dc, sub.c.xuat, sub.c.ngay, sub.c.xuat_cuoi, sub.c.ten, sub.c.so,
                   Trip.doc_no, Trip.customer_name, Trip.origin, Trip.truck_no, ChungTu.so.label("so_pnk"))
          .outerjoin(Trip, Trip.id == sub.c.lo)
          .outerjoin(ChungTu, and_(ChungTu.loai == "PNK_HH", ChungTu.nguon_bang == "trips", ChungTu.nguon_id == sub.c.lo)))
    if chi_con:
        qr = qr.filter(ton > SAI)
    if (q or "").strip():
        k = "%" + q.strip() + "%"
        qr = qr.filter(or_(Trip.doc_no.ilike(k), sub.c.so.ilike(k), Trip.customer_name.ilike(k), sub.c.ten.ilike(k),
                           Trip.truck_no.ilike(k), ChungTu.so.ilike(k)))
    if (khach or "").strip():
        k = khach.strip()
        qr = qr.filter(or_(Trip.customer_id == k, Trip.customer_name.ilike("%" + k + "%")))
    qr = qr.order_by(sub.c.ngay.desc() if moi_truoc else sub.c.ngay, func.coalesce(Trip.doc_no, sub.c.so))
    ra = []
    for r in qr.all():
        ra.append({"lo": r.lo, "doc_no": r.doc_no or r.so, "ten": r.ten, "ngay": r.ngay, "xuat_cuoi": r.xuat_cuoi,
                   "nhap": round(r.nhap, 3), "dc": round(r.dc, 3), "xuat": round(r.xuat, 3), "ton": round(r.nhap + r.dc - r.xuat, 3),
                   "khach": r.customer_name, "origin": r.origin, "truck_no": r.truck_no, "so_pnk": r.so_pnk})
    return ra


def danh_sach_lo(db, con_hang=True, tru_phieu_id=None):
    """Lô còn hàng — cùng khoá với kho tạm (ô chọn lô của phiếu giao, màn Xem kho): lo_trip_id, doc_no, goods_name, ngay, nhap_t,
    dieu_chinh_t, con_t, customer_name, origin, truck_no. 05/10: một câu GROUP BY (`_bang_lo`)."""
    return [{"lo_trip_id": o["lo"], "doc_no": o["doc_no"], "goods_name": o["ten"], "ngay": _iso(o["ngay"]), "nhap_t": o["nhap"],
             "dieu_chinh_t": o["dc"], "con_t": o["ton"], "customer_name": o["khach"], "origin": o["origin"], "truck_no": o["truck_no"]}
            for o in _bang_lo(db, tru_phieu_id=tru_phieu_id, chi_con=con_hang)]


def _item_lo(o, hom_nay=None):
    """Một lô theo giao ước màn Kho hàng (GET /api/kho-hang/ton)."""
    con = o["ton"] > SAI
    den = (hom_nay or dt.date.today()) if con else (o["xuat_cuoi"] or hom_nay or dt.date.today())
    return {"lo_id": o["lo"], "lo_doc_no": o["doc_no"], "khach": o["khach"], "loai_hang": o["ten"], "ngay_nhap": _iso(o["ngay"]),
            "tan_nhap": o["nhap"], "tan_xuat": o["xuat"], "tan_dieu_chinh": o["dc"], "ton": o["ton"],
            "so_ngay_ton": (den - o["ngay"]).days if o["ngay"] else None, "so_phieu_nhap": o["so_pnk"],
            "trang_thai": "con" if con else "het", "noi_lay": o["origin"], "xe": o["truck_no"]}


def ton_kho(db, q=None, khach=None, chi_con=True, gioi_han=2000):
    """Tồn kho hàng theo lô + tổng. Còn hàng: lô cũ trước (hàng nằm lâu nhất lên đầu); xem cả lô hết: mới trước."""
    ds = [_item_lo(o) for o in _bang_lo(db, q=q, khach=khach, chi_con=chi_con, moi_truoc=not chi_con)]
    con = [x for x in ds if x["trang_thai"] == "con"]
    return {"items": ds[:max(1, min(int(gioi_han or 2000), 5000))],
            "tong": {"so_lo": len(ds), "tan_ton": round(sum(x["ton"] for x in con), 3), "so_lo_con": len(con)}}


def cua_phieu(db, trip_id):
    """{da_nhap, ton_lo, lay_boi, xuat} — như /api/lien-thong/kho-hang/phieu/{id} của kho tạm."""
    nhap = db.query(GoodsMove.id).filter(GoodsMove.trip_id == trip_id, GoodsMove.kind == "in").first() is not None
    lay = db.query(GoodsMove).filter(GoodsMove.lo_trip_id == trip_id, GoodsMove.kind == "out", GoodsMove.trip_id != trip_id).all()
    xuat = db.query(GoodsMove).filter(GoodsMove.trip_id == trip_id, GoodsMove.kind == "out").all()
    return {"da_nhap": nhap, "ton_lo": ton_lo(db, trip_id) if nhap else None, "lay_boi": sorted({m.trip_doc_no or "?" for m in lay}),
            "xuat": [{"goods_name": m.goods_name, "qty_t": m.qty_t, "lo_trip_id": m.lo_trip_id} for m in xuat]}


# ---------------------------------------------------------------- ghi (phiếu gọi qua KK.GiaoDichKho)
def _ghi_pnk(db, trip, ngay, tan, boc_len, hao_hut, ten, by_user, bu=False):
    pl = {"tan": tan, "boc_len": boc_len, "hao_hut": hao_hut, "hang": ten, "lo": trip.id, "lo_doc_no": trip.doc_no,
          "khach": trip.customer_name, "xe": trip.truck_no}
    if bu:
        pl["sinh_bu"] = True                  # sinh sau từ dòng sổ đã có (DO nhập trước 05/10 / chép từ kho tạm)
    return CT.ghi(db, "PNK_HH", nguon_bang="trips", nguon_id=trip.id, trip=trip, ngay=ngay, doi_tuong_loai="kho", doi_tuong_ten=DEPOT,
                  tien=0, tien_te="LAK", by_user=by_user, mo_ta="Nhập kho hàng từ %s · %s tấn" % (trip.doc_no, tan), payload=pl)


def nhap(db, trip, dong, ngay, by_user, tan=None, boc_len=None, hao_hut=None):
    """Phiếu gom về tới bãi → nhập theo số thực nhập (cân bãi) đã chia sẵn + tờ PNK_HH. Gọi lại không nhập trùng →
    {da_co, so_dong, chung_tu}. Đã nhập mà chưa có tờ (DO nhập trước 05/10) → sinh tờ từ dòng sổ đã có (`dam_bao_to`)."""
    if db.query(GoodsMove.id).filter(GoodsMove.trip_id == trip.id, GoodsMove.kind == "in").first():
        to = dam_bao_to(db, trip, by_user)
        return {"da_co": True, "chung_tu": to.so if to is not None else None}
    ngay = ngay or dt.date.today()
    n, ten = 0, []
    for x in dong or []:
        sl = round(float(x.get("qty_t") or 0), 3)
        if sl <= 0:
            continue
        db.add(GoodsMove(move_date=ngay, kind="in", goods_name=x.get("goods_name") or "—", qty_t=sl, trip_id=trip.id,
                         trip_doc_no=trip.doc_no, lo_trip_id=trip.id, depot=DEPOT, by_user=by_user))
        n += 1
        ten.append(x.get("goods_name") or "—")
    db.flush()
    if not n:
        return {"da_co": False, "so_dong": 0}
    tong = round(float(tan if tan is not None else sum(float(x.get("qty_t") or 0) for x in dong)), 3)
    to = _ghi_pnk(db, trip, ngay, tong, boc_len, hao_hut, ten, by_user)
    return {"da_co": False, "so_dong": n, "chung_tu": to.so}


def dam_bao_to(db, trip, by_user=None):
    """TỜ THEO DO, IDEMPOTENT (05/10): DO gom đã có dòng nhập mà chưa có PNK_HH / DO giao đã có dòng xuất mà chưa có PXK_HH →
    sinh tờ từ CHÍNH dòng sổ đang có (không đụng sổ, không nhập / xuất lại). Đã có tờ → trả tờ đó. Không có dòng sổ → None.
    Gọi khi báo tới lại / lưu lại phiếu và từ công cụ sinh bù (tools/may_thu/sinh_bu_to_kho_hang.py). `by_user`: dùng khi dòng sổ
    không ghi người làm."""
    G = GoodsMove
    if trip.kind == "gom":
        to = CT.tim(db, "PNK_HH", "trips", trip.id)
        if to is not None:
            return to
        ms = db.query(G).filter(G.trip_id == trip.id, G.kind == "in").order_by(G.move_date, G.created_at).all()
        if not ms:
            return None
        tan = round(sum(m.qty_t for m in ms), 3)
        hang = db.query(TripGoods).filter(TripGoods.trip_id == trip.id, TripGoods.loai == "hang").all()
        boc = round(sum(g.qty_t for g in hang), 3) if hang else trip.weight_origin
        hao = round(boc - tan, 3) if boc is not None else None
        return _ghi_pnk(db, trip, ms[0].move_date, tan, boc, hao, [m.goods_name for m in ms], ms[0].by_user or by_user, bu=True)
    if trip.kind == "giao":
        to = CT.tim(db, "PXK_HH", "trips", trip.id)
        if to is not None:
            return to
        ms = db.query(G).filter(G.trip_id == trip.id, G.kind == "out", G.qty_t > 0).order_by(G.move_date, G.created_at).all()
        if not ms:
            return None
        return _to_xuat(db, trip, [{"goods_name": m.goods_name, "qty_t": m.qty_t, "lo_trip_id": m.lo_trip_id} for m in ms],
                        ms[0].move_date, ms[0].by_user or by_user, bu=True)
    return None


def _chan_doi_chieu(to):
    if to is not None and to.da_day:
        raise HTTPException(409, {"ma": "TO_DA_DOI_CHIEU", "loi": "Tờ %s đã đối chiếu với kế toán — nhờ kế toán bỏ đánh dấu đối chiếu "
                                                                 "(Sổ chứng từ) rồi mới đổi phần xuất kho hàng của phiếu." % to.so})


def _to_xuat(db, trip, dong, ngay, by_user, bu=False):
    """Tờ PXK_HH của một DO giao theo phần xuất MỚI: chưa có → sinh; có mà khác → thay nội dung (giữ số); không còn lấy hàng → rút."""
    to = CT.tim(db, "PXK_HH", "trips", trip.id)
    if not dong:
        if to is not None:
            _chan_doi_chieu(to)
            CT.rut(db, nguon_bang="trips", nguon_id=trip.id, loai="PXK_HH")
            db.expunge(to)
        return None
    lo_so = dict(db.query(Trip.id, Trip.doc_no).filter(Trip.id.in_({x.get("lo_trip_id") for x in dong})).all())
    gop = {}
    for x in dong:
        k = (x.get("lo_trip_id"), x.get("goods_name") or "—")
        gop[k] = round(gop.get(k, 0) + float(x["qty_t"]), 3)
    ds = [{"hang": h, "tan": t, "lo": lo, "lo_doc_no": lo_so.get(lo)} for (lo, h), t in sorted(gop.items(), key=lambda z: (lo_so.get(z[0][0]) or "", z[0][1]))]
    tong = round(sum(x["tan"] for x in ds), 3)
    pl = {"tan": tong, "dong": ds, "khach": trip.customer_name, "xe": trip.truck_no}
    if bu:
        pl["sinh_bu"] = True
    mo_ta = "Xuất kho hàng đi giao %s · %s tấn" % (trip.doc_no, tong)
    if to is None:
        return CT.ghi(db, "PXK_HH", nguon_bang="trips", nguon_id=trip.id, trip=trip, ngay=ngay, doi_tuong_loai="kho", doi_tuong_ten=DEPOT,
                      tien=0, tien_te="LAK", by_user=by_user, mo_ta=mo_ta, payload=pl)
    gon = lambda d: sorted((z.get("lo"), z.get("hang"), round(float(z.get("tan") or 0), 3)) for z in (d or []))   # noqa: E731
    if gon(_pl(to).get("dong")) == gon(ds) and to.ngay == ngay:
        return to
    _chan_doi_chieu(to)
    to.payload = json.dumps(pl, ensure_ascii=False, default=str)
    to.mo_ta, to.ngay, to.by_user, to.trip_doc_no, to.ts = mo_ta, ngay, by_user, trip.doc_no, bay_gio()
    db.flush()
    return to


def xuat(db, trip, dong, ngay, by_user):
    """Lưu phiếu giao → THAY toàn bộ phần xuất của phiếu, kiểm tồn từng lô (cộng các dòng cùng lô), sinh / thay / rút tờ PXK_HH
    → {cu, chung_tu}."""
    dong = [x for x in (dong or []) if round(float(x.get("qty_t") or 0), 3) > 0]
    ngay = ngay or dt.date.today()
    can = {}
    for x in dong:
        lo = str(x.get("lo_trip_id") or "").strip()
        if not lo or not db.query(GoodsMove.id).filter(GoodsMove.lo_trip_id == lo, GoodsMove.kind == "in").first():
            raise HTTPException(422, {"ma": "LO_CHUA_NHAP", "loi": "Lô hàng phải là một phiếu gom đã nhập kho bãi."})
        x["lo_trip_id"] = lo
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
        db.add(GoodsMove(move_date=ngay, kind="out", goods_name=x.get("goods_name") or "—",
                         qty_t=round(float(x["qty_t"]), 3), trip_id=trip.id, trip_doc_no=trip.doc_no, lo_trip_id=x.get("lo_trip_id"),
                         depot=DEPOT, by_user=by_user))
    db.flush()
    to = _to_xuat(db, trip, dong, ngay, by_user)
    return {"cu": cu, "chung_tu": to.so if to is not None else None}


def huy(db, trip_id):
    """Xoá phiếu → xoá mọi dòng sổ của phiếu (nhập / xuất / điều chỉnh lô của nó), xoá đơn điều chỉnh của lô, rút tờ PNK_HH /
    PXK_HH / DC_HH chưa đối chiếu. Lô đã có phiếu giao khác lấy → 409."""
    _khoa_lo(db, trip_id)
    c = cua_phieu(db, trip_id)
    if c["lay_boi"]:
        raise HTTPException(409, {"ma": "LO_DA_XUAT", "loi": "Lô hàng của phiếu này đã xuất cho phiếu giao %s — xoá phiếu giao trước."
                                                           % ", ".join(c["lay_boi"])})
    ds = db.query(GoodsMove).filter((GoodsMove.trip_id == trip_id) | (GoodsMove.lo_trip_id == trip_id)).all()
    for m in ds:
        if m.kind == "adj":
            CT.rut(db, nguon_bang="goods_moves", nguon_id=m.id, loai="DC_HH")
        db.delete(m)
    n_don = db.query(DieuChinhHang).filter(DieuChinhHang.lo_trip_id == trip_id).delete(synchronize_session=False)
    n_to = CT.rut(db, nguon_bang="trips", nguon_id=trip_id, loai=TO_HANG)
    db.flush()
    return {"ok": True, "so_dong": len(ds), "so_don_dieu_chinh": n_don, "so_to_rut": n_to}


# ---------------------------------------------------------------- điều chỉnh lô (Bãi lập · KT Thu/Chi VC duyệt)
def _so_tan(v):
    if isinstance(v, bool):
        v = None
    try:
        return float(v) if isinstance(v, (int, float)) else float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số tấn điều chỉnh phải là số: âm là giảm, dương là tăng."})


def _nhap_cua_lo(db, lo_id):
    return db.query(GoodsMove).filter(GoodsMove.lo_trip_id == lo_id, GoodsMove.kind == "in").first() if lo_id else None


def _vuot(lo_so, con, giam, viec):
    raise HTTPException(409, {"ma": "VUOT_TON", "loi": "Lô %s chỉ còn %s tấn — %s %s tấn thì tồn lô âm. Kiểm lại số với phiếu giao đã "
                                                       "lấy hàng của lô." % (lo_so or "?", round(con, 3), viec, round(giam, 3))})


def lap_dieu_chinh(db, lo_id, tan, ly_do, nguoi):
    """Bãi lập đơn điều chỉnh một lô → `cho` (chưa đổi tồn). Giảm quá tồn hiện tại thì chặn ngay (409)."""
    lo_id = str(lo_id or "").strip()
    hang = _nhap_cua_lo(db, lo_id)
    if not hang:
        raise HTTPException(422, {"ma": "LO_SAI", "loi": "Lô điều chỉnh phải là một phiếu gom đã nhập kho bãi."})
    sl = round(_so_tan(tan), 3)
    if abs(sl) < SAI:
        raise HTTPException(422, {"ma": "SO_KHONG", "loi": "Số tấn điều chỉnh phải khác 0 (âm là giảm, dương là tăng)."})
    ly_do = (ly_do or "").strip()
    if len(ly_do) < 3:
        raise HTTPException(422, {"ma": "THIEU_LY_DO", "loi": "Điều chỉnh kho hàng phải ghi lý do (cân sai, hao ở bãi, kiểm kê…)."})
    if sl < 0:
        con = ton_lo(db, lo_id)
        if con + sl < -SAI:
            _vuot(hang.trip_doc_no, con, -sl, "giảm")
    d = DieuChinhHang(lo_trip_id=lo_id, tan=sl, ly_do=ly_do[:2000], trang_thai="cho", ngay=dt.date.today(), nguoi_lap=_ten(nguoi),
                      lap_luc=bay_gio())
    db.add(d)
    db.flush()
    return d


def duyet_dieu_chinh(db, don_id, dong_y, ghi_chu, nguoi):
    """Duyệt → dòng goods_moves kind=adj (có dấu) + tờ DC_HH; tồn lô âm → 409. Từ chối → phải ghi lý do. Đơn đã xử lý → 409."""
    d = db.query(DieuChinhHang).filter(DieuChinhHang.id == don_id).with_for_update().first()
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có đơn điều chỉnh này."})
    if d.trang_thai != "cho":
        raise HTTPException(409, {"ma": "DA_XU_LY", "loi": "Đơn điều chỉnh này đã %s (%s) — không xử lý lại được." % (
            "duyệt" if d.trang_thai == "da_duyet" else "từ chối", d.nguoi_duyet or "")})
    ghi_chu = (ghi_chu or "").strip() or None
    if not dong_y:
        if not ghi_chu:
            raise HTTPException(422, {"ma": "THIEU_GHI_CHU", "loi": "Từ chối đơn điều chỉnh thì ghi lý do để Bãi biết."})
        d.trang_thai, d.nguoi_duyet, d.duyet_luc, d.ghi_chu = "tu_choi", _ten(nguoi), bay_gio(), ghi_chu
        db.flush()
        return d
    _khoa_lo(db, d.lo_trip_id)
    hang = _nhap_cua_lo(db, d.lo_trip_id)
    if not hang:
        raise HTTPException(409, {"ma": "LO_SAI", "loi": "Lô của đơn này không còn trong kho bãi."})
    con = ton_lo(db, d.lo_trip_id)
    if con + d.tan < -SAI:
        _vuot(hang.trip_doc_no, con, -d.tan, "duyệt giảm")
    lo = db.get(Trip, d.lo_trip_id)
    so_lo = lo.doc_no if lo else hang.trip_doc_no
    hom_nay = dt.date.today()
    m = GoodsMove(move_date=hom_nay, kind="adj", goods_name=hang.goods_name, qty_t=round(d.tan, 3), trip_id=d.lo_trip_id,
                  trip_doc_no=so_lo, lo_trip_id=d.lo_trip_id, depot=DEPOT, note=d.ly_do, by_user=_ten(nguoi))
    db.add(m)
    db.flush()
    to = CT.ghi(db, "DC_HH", nguon_bang="goods_moves", nguon_id=m.id, trip=lo, ngay=hom_nay, doi_tuong_loai="kho", doi_tuong_ten=DEPOT,
                tien=0, tien_te="LAK", by_user=_ten(nguoi),
                mo_ta="Điều chỉnh kho lô %s: %s%s tấn — %s" % (so_lo, "+" if d.tan > 0 else "", round(d.tan, 3), d.ly_do),
                payload={"chieu": "tang" if d.tan > 0 else "giam", "tan": round(abs(d.tan), 3), "tan_co_dau": round(d.tan, 3),
                         "lo": d.lo_trip_id, "lo_doc_no": so_lo, "hang": hang.goods_name, "ly_do": d.ly_do, "don_id": d.id,
                         "nguoi_lap": d.nguoi_lap, "nguoi_duyet": _ten(nguoi), "ton_truoc": con, "ton_sau": round(con + d.tan, 3)})
    d.trang_thai, d.nguoi_duyet, d.duyet_luc, d.ngay_duyet, d.ghi_chu = "da_duyet", _ten(nguoi), bay_gio(), hom_nay, ghi_chu
    d.goods_move_id, d.so_phieu = m.id, to.so
    db.flush()
    return d


def xuat_don(d, o=None):
    """Một đơn điều chỉnh cho màn hình. `o`: dòng lô từ `_bang_lo` (số lô, khách, hàng, tồn hiện tại)."""
    return {"id": d.id, "lo_id": d.lo_trip_id, "lo_doc_no": o["doc_no"] if o else None, "khach": o["khach"] if o else None,
            "loai_hang": o["ten"] if o else None, "ton_lo": o["ton"] if o else None,
            "so_phieu": d.so_phieu, "ngay": _iso(d.ngay_duyet if d.trang_thai == "da_duyet" and d.ngay_duyet else d.ngay),
            "ngay_lap": _iso(d.ngay), "tan": d.tan, "ly_do": d.ly_do, "trang_thai": d.trang_thai, "nguoi_lap": d.nguoi_lap,
            "lap_luc": d.lap_luc.isoformat(timespec="seconds") if d.lap_luc else None, "nguoi_duyet": d.nguoi_duyet,
            "duyet_luc": d.duyet_luc.isoformat(timespec="seconds") if d.duyet_luc else None, "ghi_chu": d.ghi_chu}


def mot_don(db, d):
    ds = _bang_lo(db, lo_ids={d.lo_trip_id})
    return xuat_don(d, ds[0] if ds else None)


def ds_dieu_chinh(db, trang_thai=None, lo_id=None, gioi_han=500):
    q = db.query(DieuChinhHang)
    if trang_thai:
        if trang_thai not in TRANG_THAI_DC:
            raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "trang_thai phải là cho, da_duyet hoặc tu_choi."})
        q = q.filter(DieuChinhHang.trang_thai == trang_thai)
    if lo_id:
        q = q.filter(DieuChinhHang.lo_trip_id == lo_id)
    # chờ duyệt: cũ trước (người duyệt làm lần lượt); còn lại: mới trước
    q = q.order_by(DieuChinhHang.lap_luc if trang_thai == "cho" else DieuChinhHang.lap_luc.desc())
    rows = q.limit(max(1, min(int(gioi_han or 500), 2000))).all()
    lo = {o["lo"]: o for o in _bang_lo(db, lo_ids={r.lo_trip_id for r in rows})} if rows else {}
    return [xuat_don(r, lo.get(r.lo_trip_id)) for r in rows]


# ---------------------------------------------------------------- đọc cho màn Kho hàng / bản in
def mot_lo(db, lo_id):
    """Chi tiết một lô: phiếu nhập (PNK_HH, cân mỏ / cân bãi / hao hụt), các lần xuất theo DO giao (PXK_HH), đơn điều chỉnh."""
    ds = _bang_lo(db, lo_ids={lo_id})
    if not ds:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lô hàng này trong kho bãi."})
    o = ds[0]
    p = db.get(Trip, lo_id)
    pnk = CT.tim(db, "PNK_HH", "trips", lo_id)
    pl = _pl(pnk)
    can_mo = pl.get("boc_len") if pl.get("boc_len") is not None else (p.weight_origin if p else None)
    hao = pl.get("hao_hut") if pl.get("hao_hut") is not None else (round(can_mo - o["nhap"], 3) if can_mo is not None else None)
    nhap = {"so_phieu": pnk.so if pnk else None, "ngay": _iso(o["ngay"]), "do_no": o["doc_no"], "xe": p.truck_no if p else o["truck_no"],
            "tai_xe": p.driver_name if p else None, "can_mo": can_mo, "can_bai": p.weight_dest if p else None, "hao_hut": hao,
            "tan": o["nhap"], "nguoi_xac_nhan": pnk.by_user if pnk else None}
    G = GoodsMove
    xs = (db.query(G.trip_id, func.sum(G.qty_t).label("tan"), func.min(G.move_date).label("ngay"), Trip.doc_no, Trip.truck_no,
                   Trip.customer_name, Trip.destination, ChungTu.so)
          .outerjoin(Trip, Trip.id == G.trip_id)
          .outerjoin(ChungTu, and_(ChungTu.loai == "PXK_HH", ChungTu.nguon_bang == "trips", ChungTu.nguon_id == G.trip_id))
          .filter(G.lo_trip_id == lo_id, G.kind == "out")
          .group_by(G.trip_id, Trip.doc_no, Trip.truck_no, Trip.customer_name, Trip.destination, ChungTu.so)
          .order_by(func.min(G.move_date), Trip.doc_no).all())
    xuat_ra = [{"so_phieu": r.so, "ngay": _iso(r.ngay), "do_no": r.doc_no, "trip_id": r.trip_id, "xe": r.truck_no,
                "khach_nhan": r.customer_name, "noi_giao": r.destination, "tan": round(r.tan or 0, 3)} for r in xs]
    return {"lo": _item_lo(o), "nhap": nhap, "xuat": xuat_ra, "dieu_chinh": [xuat_don(d, o) for d in db.query(DieuChinhHang)
                                                                               .filter(DieuChinhHang.lo_trip_id == lo_id)
                                                                               .order_by(DieuChinhHang.lap_luc).all()]}


def to_kho_hang(db, trip):
    """Tờ kho hàng để in của một DO: DO gom → PNK_HH, DO giao → PXK_HH. Chưa có tờ → 404 CHUA_CO_TO."""
    loai = "PNK_HH" if trip.kind == "gom" else "PXK_HH"
    to = CT.tim(db, loai, "trips", trip.id)
    if to is None:
        raise HTTPException(404, {"ma": "CHUA_CO_TO", "loi": ("DO gom này chưa có phiếu nhập kho hàng — phiếu tự sinh khi Bãi bấm Xe đã tới "
                                                            "(có cân bãi)." if trip.kind == "gom" else
                                                            "DO giao này chưa có phiếu xuất kho hàng — phiếu tự sinh khi lưu phiếu giao có "
                                                            "lấy hàng từ lô.")})
    pl = _pl(to)
    if trip.kind == "gom":
        dong = [{"lo_doc_no": pl.get("lo_doc_no") or trip.doc_no, "tan": pl.get("tan"), "loai_hang": ", ".join(pl.get("hang") or []) or None,
                 "lo_id": trip.id}]
        can_mo = pl.get("boc_len") if pl.get("boc_len") is not None else trip.weight_origin
        can_bai, can_noi_giao, hao = trip.weight_dest, None, pl.get("hao_hut")
        if hao is None and can_mo is not None and can_bai is not None:
            hao = round(can_mo - can_bai, 3)
    else:
        dong = [{"lo_doc_no": x.get("lo_doc_no"), "tan": x.get("tan"), "loai_hang": x.get("hang"), "lo_id": x.get("lo")}
                for x in pl.get("dong") or []]
        can_mo, can_bai, can_noi_giao = None, pl.get("tan"), trip.weight_dest
        hao = round(can_bai - can_noi_giao, 3) if can_bai is not None and can_noi_giao is not None else None
    hang = sorted({x["loai_hang"] for x in dong if x.get("loai_hang")})
    return {"loai": loai, "loai_ten": CT.LOAI[loai][0], "loai_ten_lo": CT.LOAI[loai][1], "so": to.so, "ngay": _iso(to.ngay),
            "do_no": trip.doc_no, "trip_id": trip.id, "khach": trip.customer_name, "loai_hang": ", ".join(hang) or None,
            "xe": trip.truck_no, "tai_xe": trip.driver_name, "dong": dong, "tong_tan": pl.get("tan"),
            "can_mo": can_mo, "can_bai": can_bai, "can_noi_giao": can_noi_giao, "hao_hut": hao,
            "nguoi_xac_nhan": to.by_user, "kho": DEPOT, "da_doi_chieu": bool(to.da_day), "chung_tu_id": to.id}


def doi_soat(db, ngay):
    """Đối soát một ngày: DO gom đã tới ↔ PNK_HH, DO giao có lấy hàng ↔ PXK_HH; `lech` = DO thiếu tờ. Ngày DO gom = ngày về
    (trống thì ngày phiếu), ngày DO giao = ngày xuất (trống thì ngày phiếu) — đúng ngày ghi sổ / ngày tờ."""
    gom = (db.query(Trip.id, Trip.doc_no).filter(Trip.kind == "gom", Trip.transport_status == "arrived",
                                                 func.coalesce(Trip.back_date, Trip.doc_date) == ngay).all())
    co_hang = exists().where(and_(TripGoods.trip_id == Trip.id, TripGoods.loai == "hang", TripGoods.qty_t > 0))
    giao = (db.query(Trip.id, Trip.doc_no).filter(Trip.kind == "giao", func.coalesce(Trip.out_date, Trip.doc_date) == ngay, co_hang)
            .all())
    ids = [r.id for r in gom] + [r.id for r in giao]
    co_to = set(db.query(ChungTu.loai, ChungTu.nguon_id).filter(ChungTu.loai.in_(TO_HANG), ChungTu.nguon_bang == "trips",
                                                                ChungTu.nguon_id.in_(ids)).all()) if ids else set()
    dem = dict(db.query(ChungTu.loai, func.count(ChungTu.id)).filter(ChungTu.loai.in_(TO_HANG), ChungTu.ngay == ngay)
               .group_by(ChungTu.loai).all())
    lech = ([{"do_no": r.doc_no, "trip_id": r.id, "thieu": "PNK_HH"} for r in gom if ("PNK_HH", r.id) not in co_to]
            + [{"do_no": r.doc_no, "trip_id": r.id, "thieu": "PXK_HH"} for r in giao if ("PXK_HH", r.id) not in co_to])
    return {"ngay": ngay.isoformat(), "do_gom_da_toi": len(gom), "phieu_nhap": dem.get("PNK_HH", 0), "do_giao": len(giao),
            "phieu_xuat": dem.get("PXK_HH", 0), "lech": sorted(lech, key=lambda x: (x["thieu"], x["do_no"] or ""))}
