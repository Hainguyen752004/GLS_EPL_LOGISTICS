# -*- coding: utf-8 -*-
"""TRẢ CHỦ XE LIÊN KẾT — phần trang điều xe còn giữ cho đợt trả ở TRANG KẾ TOÁN (đợt 7b, 28/09).

Đợt trả (từng phiếu, gộp tháng, theo đợt), tờ PC_CX, trừ hàng chủ xe mua ở quầy dời sang trang kế toán. Ở đây còn:

  1. **Danh mục chủ xe** (phí, ngưỡng tấn, mức trừ quá tải, tiền thuê, cách trả) — lập phiếu tự điền theo đó.
  2. **Số "trả chủ xe" của từng phiếu** — tiền thuê × tấn − phí − quá tải − EPL đã ứng (services/tinh_toan → tinh_phieu).
     Trang kế toán hỏi số này khi lập đợt, không gõ tay, không tính lại cách khác.
  3. **Bản chép "đã trả"** trên phiếu: owner_payment_id (mã đợt bên đó), owner_paid, owner_paid_usd / _lak / _by / _at.
     Trang kế toán ghi sang khi lập đợt; bên này kiểm lại ngay lúc ghi (dòng khoá) để không trả hai lần.

Các đường máy ở routes/lien_thong.py → /api/lien-thong/chu-xe/….
"""
import datetime as dt

from fastapi import HTTPException

from models import Owner, Trip, TripExpense, Vehicle
from services.tinh_toan import tinh_phieu


def ds_chu_xe(db):
    """Danh mục chủ xe (kèm xe đang dùng) và phần chờ trả tính từ phiếu đã khoá chưa nằm đợt nào."""
    from collections import defaultdict
    from routes.chu_xe import _cho_tra_lo, xuat_chu_xe
    ds = db.query(Owner).order_by(Owner.active.desc(), Owner.name).all()
    xe = defaultdict(list)
    for oid, so in db.query(Vehicle.owner_id, Vehicle.truck_no).filter(Vehicle.owner_id.in_([o.id for o in ds] or [""]),
                                                                       Vehicle.active.is_(True)):
        xe[oid].append(so)
    cho = _cho_tra_lo(db, ds)
    return [xuat_chu_xe(db, o, None, kem_cong_no=True, xe=xe, cho=cho) for o in ds]


def dong_phieu(db, p, dong=None):
    """Một phiếu cho màn trả chủ xe: số trả và các phần trừ, cùng trạng thái (khoá, đã trả)."""
    k = tinh_phieu(p, db.query(TripExpense).filter(TripExpense.trip_id == p.id).order_by(TripExpense.section, TripExpense.line_no).all()
                   if dong is None else dong)
    return {"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "truck_no": p.truck_no, "customer_name": p.customer_name, "company": p.company, "owner_id": p.owner_id,
            "owner_name": p.owner_name, "locked": bool(p.locked),
            "owner_paid": bool(p.owner_paid or p.owner_payment_id), "owner_payment_id": p.owner_payment_id,
            "tan_tinh": k["tan_tinh"], "hire_ccy": k.get("hire_ccy"), "tien_thue": k.get("tien_thue"), "phi": k.get("phi"),
            "tru_vuot": k.get("tru_vuot"), "ung_truoc": k.get("ung_truoc"), "tra_chu_xe": k.get("tra_chu_xe"),
            "tra_chu_xe_lak": k.get("tra_chu_xe_lak")}


def cho_tra(db, owner_id):
    """Phiếu đã KHOÁ của chủ xe chưa nằm đợt trả nào — cũ trước (hộp Trả gộp)."""
    from routes.chu_xe import _phieu_cho_tra
    o = db.get(Owner, owner_id)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này bên trang điều xe."})
    return [dong_phieu(db, p) for p in _phieu_cho_tra(db, o)]


def so_lieu(db, trip_ids):
    return {p.id: dong_phieu(db, p) for p in db.query(Trip).filter(Trip.id.in_([i for i in trip_ids if i] or [""])).all()}


def _chan(p, ma, chu):
    raise HTTPException(409, {"ma": ma, "loi": chu, "trip_id": p.id, "doc_no": p.doc_no})


def danh_dau_tra(db, user, owner_payment_id, cac_dong):
    """Trang kế toán vừa lập đợt trả gồm các phiếu này → ghi bản chép "đã trả". Kiểm lại ngay lúc ghi (dòng khoá): phiếu
    phải là xe liên kết, đã khoá, chưa trả — giữa lúc bên kia đọc số và lúc ghi, người khác có thể đã trả."""
    from routes.phieu import _ghi_log
    theo = {str(d.get("trip_id")): d for d in (cac_dong or []) if d.get("trip_id")}
    if not owner_payment_id or not theo:
        raise HTTPException(422, {"ma": "THIEU", "loi": "Thiếu đợt trả hoặc phiếu."})
    ds = db.query(Trip).filter(Trip.id.in_(list(theo))).with_for_update().all()
    if len(ds) != len(theo):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Có phiếu không còn bên trang điều xe."})
    for p in ds:
        if p.company != "joint":
            _chan(p, "KHONG_PHAI_LIEN_KET", "Phiếu %s là xe nhà, không có chủ xe để trả." % p.doc_no)
        if not p.locked:
            _chan(p, "CHUA_KHOA", "Phiếu %s chưa khoá; kế toán khoá rồi quỹ mới trả." % p.doc_no)
        if p.owner_payment_id or p.owner_paid:
            _chan(p, "DA_TRA", "Phiếu %s đã trả chủ xe rồi." % p.doc_no)
    bay_gio = dt.datetime.utcnow()
    for p in ds:
        d = theo[p.id]
        p.owner_payment_id = str(owner_payment_id)
        p.owner_paid, p.owner_paid_usd, p.owner_paid_lak = True, d.get("tra_chu_xe"), d.get("tra_chu_xe_lak")
        p.owner_paid_by, p.owner_paid_at = getattr(user, "full_name", None), bay_gio
        _ghi_log(db, p, user, "a_pay_owner")
    db.commit()
    return {p.id: True for p in ds}


def bo_tra(db, user, owner_payment_id, trip_ids):
    """Bên kế toán lưu hỏng sau khi đã ghi sang → các phiếu của đợt đó về "chưa trả"."""
    q = db.query(Trip).filter(Trip.owner_payment_id == str(owner_payment_id or ""))
    if trip_ids:
        q = q.filter(Trip.id.in_([str(i) for i in trip_ids]))
    n = 0
    for p in q.with_for_update().all():
        p.owner_payment_id, p.owner_paid, p.owner_paid_usd, p.owner_paid_lak, p.owner_paid_by, p.owner_paid_at = (None,) * 6
        p.owner_paid = False
        n += 1
    db.commit()
    return {"so_phieu": n}
