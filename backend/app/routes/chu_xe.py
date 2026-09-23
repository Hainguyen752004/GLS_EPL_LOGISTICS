# -*- coding: utf-8 -*-
"""Chủ xe liên kết (ເຈົ້າຂອງລົດຮ່ວມ) — danh mục và sổ trả tiền.

Anh Khampla trả lời 22/09 (C4.2, C4.3): phí 2 %/phiếu và mức quá tải **khác nhau theo từng chủ xe /
hợp đồng**, và chủ xe được trả theo **ba kiểu** — từng phiếu ngay sau khoá (xe ngoài không hợp đồng),
gộp cuối tháng, hay theo đợt đã thoả thuận. Trước đây phần mềm chỉ có ba ô mặc định trên từng phiếu và
một nút trả từng phiếu.

Mô hình ở đây cố ý đơn giản:
  · `owners`: mỗi chủ xe một dòng, mang mặc định phí, ngưỡng tấn, mức trừ quá tải, tiền thuê, cách trả.
    Lập phiếu cho xe của chủ đó thì ba ô kia tự điền theo — kế toán vẫn sửa được trên phiếu.
  · `owner_payments`: MỘT LẦN TRẢ gồm MỘT HAY NHIỀU PHIẾU đã khoá của cùng chủ xe, cùng tiền thuê.
    Số tiền = tổng "trả chủ xe" của các phiếu trong đợt — không gõ tay, để khớp chứng từ từng phiếu.
    "Từng phiếu" là đợt một phiếu; "gộp tháng" là đợt gồm các phiếu trong tháng; "theo đợt" là đợt
    gồm những phiếu hai bên chốt trả lần này.
  · Phiếu nằm trong đợt nào thì `trips.owner_payment_id` trỏ tới đó — đó chính là "đã trả chủ xe".
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (CACH_TRA_CHU_XE, PHUONG_THUC_THU, TIEN_TE, Owner, OwnerPayment, Sale, Trip, TripExpense, Vehicle)
from services import chung_tu as CT
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_ban
from services.tinh_toan import tinh_phieu

router = APIRouter()

SUA_CHU_XE = can_vai("acct")                    # phí, mức trừ, cách trả là điều khoản hợp đồng — kế toán VC giữ
TRA_CHU_XE = can_vai("cash", "treasury")        # hai quỹ là người chi tiền
COT = ("name", "phone", "address", "fee_pct", "over_limit_t", "over_price", "hire_ccy", "pay_mode", "note")
COT_SO = ("fee_pct", "over_limit_t", "over_price")
COT_TIEN = ("fee_pct", "over_limit_t", "over_price", "hire_ccy")   # Bãi không thấy — đây là phần trừ tiền của chủ xe


def _so(v, ten):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số, nhận '%s'." % (ten, v)})


def _ngay(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


def _dong_chi(db, p):
    return db.query(TripExpense).filter(TripExpense.trip_id == p.id).order_by(TripExpense.section, TripExpense.line_no).all()


def xuat_chu_xe(db, o, user=None, kem_cong_no=False):
    r = {"id": o.id, "name": o.name, "phone": o.phone, "address": o.address, "pay_mode": o.pay_mode or "phieu",
         "note": o.note, "active": bool(o.active),
         "so_xe": [v.truck_no for v in db.query(Vehicle).filter(Vehicle.owner_id == o.id, Vehicle.active.is_(True)).all()]}
    if user is None or thay_tien_ban(user.role):
        r.update({"fee_pct": o.fee_pct, "over_limit_t": o.over_limit_t, "over_price": o.over_price, "hire_ccy": o.hire_ccy or "USD"})
        if kem_cong_no:
            r["cho_tra"] = _cho_tra(db, o)
    return r


def _phieu_cho_tra(db, o):
    """Phiếu đã KHOÁ của chủ xe này mà chưa nằm trong đợt trả nào."""
    return (db.query(Trip).filter(Trip.owner_id == o.id, Trip.company == "joint", Trip.locked.is_(True),
                                  Trip.owner_payment_id.is_(None)).order_by(Trip.doc_date, Trip.doc_no).all())


def _dong_phieu(db, p):
    k = tinh_phieu(p, _dong_chi(db, p))
    return {"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "truck_no": p.truck_no, "customer_name": p.customer_name, "tan_tinh": k["tan_tinh"],
            "hire_ccy": k.get("hire_ccy"), "tien_thue": k.get("tien_thue"), "phi": k.get("phi"), "tru_vuot": k.get("tru_vuot"),
            "ung_truoc": k.get("ung_truoc"), "tra_chu_xe": k.get("tra_chu_xe"), "tra_chu_xe_lak": k.get("tra_chu_xe_lak"),
            "owner_payment_id": p.owner_payment_id}


def _cho_tra(db, o):
    ds = [_dong_phieu(db, p) for p in _phieu_cho_tra(db, o)]
    tong = {}
    for d in ds:
        if d["tra_chu_xe"] and d["tra_chu_xe"] > 0:
            tong[d["hire_ccy"]] = round(tong.get(d["hire_ccy"], 0) + d["tra_chu_xe"], 2)
    ban = _ban_cho_tru(db, o.id)
    return {"so_phieu": len(ds), "tong": tong, "tong_lak": sum(d["tra_chu_xe_lak"] or 0 for d in ds),
            "ban_cho_tru_lak": round(sum(b.total_lak or 0 for b in ban)), "so_phieu_ban": len(ban)}


def _ban_cho_tru(db, owner_id):
    """Phiếu bán hàng (xăng, phụ tùng) chủ xe mua ở quầy, CHƯA trừ vào đợt trả nào — cũ trước."""
    return (db.query(Sale).filter(Sale.owner_id == owner_id, Sale.owner_payment_id.is_(None), Sale.status != "paid")
            .order_by(Sale.sale_date, Sale.doc_no).all())


def _xuat_ban(b):
    return {"id": b.id, "doc_no": b.doc_no, "sale_date": b.sale_date.isoformat() if b.sale_date else None,
            "total": b.total, "currency": b.currency, "total_lak": b.total_lak, "owner_payment_id": b.owner_payment_id}


# ================================================================ danh mục
@router.get("/api/owners")
def ds_chu_xe(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Mọi vai xem được tên và xe (Bãi cần chọn chủ xe khi thêm xe); phí và số tiền chờ trả chỉ vai thấy tiền bán."""
    return [xuat_chu_xe(db, o, user, kem_cong_no=True)
            for o in db.query(Owner).order_by(Owner.active.desc(), Owner.name).all()]


def _ap(o, data):
    for k in COT:
        if k not in data:
            continue
        v = data[k]
        if k in COT_SO:
            v = _so(v, k)
        elif isinstance(v, str):
            v = v.strip() or None
        setattr(o, k, v)
    if not (o.name or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Chủ xe phải có tên."})
    o.pay_mode = o.pay_mode or "phieu"
    if o.pay_mode not in CACH_TRA_CHU_XE:
        raise HTTPException(422, {"ma": "CACH_TRA_SAI", "loi": "Cách trả phải là %s." % ", ".join(CACH_TRA_CHU_XE)})
    o.hire_ccy = (o.hire_ccy or "USD").upper()
    if o.hire_ccy not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền thuê phải là một trong %s." % ", ".join(TIEN_TE)})
    if o.fee_pct is None: o.fee_pct = 2
    if o.over_limit_t is None: o.over_limit_t = 40
    if o.over_price is None: o.over_price = 1
    if o.fee_pct < 0 or o.fee_pct > 100:
        raise HTTPException(422, {"ma": "PHI_SAI", "loi": "Phí phải từ 0 đến 100 %."})


@router.post("/api/owners")
def them_chu_xe(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_CHU_XE)):
    o = Owner(); _ap(o, data)
    db.add(o); db.commit(); db.refresh(o)
    return xuat_chu_xe(db, o, user, kem_cong_no=True)


@router.put("/api/owners/{oid}")
def sua_chu_xe(oid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_CHU_XE)):
    o = db.get(Owner, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này."})
    _ap(o, data)
    if "active" in data:
        o.active = bool(data["active"])
    # Tên đổi thì xe và phiếu cũ vẫn giữ tên đã chép — nhưng danh mục xe nên theo tên mới
    for v in db.query(Vehicle).filter(Vehicle.owner_id == o.id).all():
        v.owner_name = o.name
    db.commit(); db.refresh(o)
    return xuat_chu_xe(db, o, user, kem_cong_no=True)


# ================================================================ công nợ và trả tiền
@router.get("/api/owners/{oid}/cong-no")
def cong_no_chu_xe(oid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Phiếu đã khoá chưa trả (để chọn vào một đợt) và các đợt đã trả của chủ xe này."""
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem công nợ chủ xe." % user.role})
    o = db.get(Owner, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này."})
    dot = (db.query(OwnerPayment).filter(OwnerPayment.owner_id == o.id).order_by(OwnerPayment.pay_date.desc(), OwnerPayment.created_at.desc()).all())
    ds_dot = []
    for x in dot:
        phieu = db.query(Trip).filter(Trip.owner_payment_id == x.id).order_by(Trip.doc_date).all()
        ban = db.query(Sale).filter(Sale.owner_payment_id == x.id).order_by(Sale.sale_date).all()
        ds_dot.append({"id": x.id, "pay_date": x.pay_date.isoformat() if x.pay_date else None, "amount": x.amount,
                       "gross": x.gross if x.gross is not None else x.amount, "sales_deducted": x.sales_deducted or 0,
                       "ban": [b.doc_no for b in ban],
                       "currency": x.currency, "amount_lak": x.amount_lak, "method": x.method, "ref": x.ref, "note": x.note,
                       "by_user": x.by_user, "phieu": [p.doc_no for p in phieu]})
    return {"chu_xe": xuat_chu_xe(db, o, user), "cho_tra": [_dong_phieu(db, p) for p in _phieu_cho_tra(db, o)],
            "ban_cho_tru": [_xuat_ban(b) for b in _ban_cho_tru(db, o.id)],
            "tong": _cho_tra(db, o), "da_tra": ds_dot}


def tra_nhieu_phieu(db, user, phieu, pay_date=None, method="cash", ref=None, note=None, owner=None):
    """Lập MỘT đợt trả gồm các phiếu đã cho. Dùng chung cho nút trả từng phiếu và trả gộp.

    Tiền = tổng "trả chủ xe" của các phiếu — không gõ tay. Các phiếu phải cùng chủ xe, cùng tiền thuê,
    đã khoá, chưa trả, và số phải trả > 0."""
    if not phieu:
        raise HTTPException(422, {"ma": "THIEU_PHIEU", "loi": "Chưa chọn phiếu nào để trả."})
    if method not in PHUONG_THUC_THU:
        raise HTTPException(422, {"ma": "PHUONG_THUC_SAI", "loi": "Cách chi phải là %s." % ", ".join(PHUONG_THUC_THU)})
    ccy, tong, tong_lak, chi_tiet = None, 0.0, 0, []
    for p in phieu:
        if p.company != "joint":
            raise HTTPException(422, {"ma": "KHONG_PHAI_LIEN_KET", "loi": "Phiếu %s là xe nhà, không có chủ xe để trả." % p.doc_no})
        if owner is not None and p.owner_id != owner.id:
            raise HTTPException(422, {"ma": "KHAC_CHU_XE", "loi": "Phiếu %s không phải của chủ xe %s." % (p.doc_no, owner.name)})
        if not p.locked:
            raise HTTPException(409, {"ma": "CHUA_KHOA", "loi": "Phiếu %s chưa khoá; kế toán khoá rồi quỹ mới trả." % p.doc_no})
        if p.owner_payment_id or p.owner_paid:
            raise HTTPException(409, {"ma": "DA_TRA", "loi": "Phiếu %s đã trả chủ xe rồi." % p.doc_no})
        k = tinh_phieu(p, _dong_chi(db, p))
        if (k.get("tra_chu_xe") or 0) <= 0:
            raise HTTPException(422, {"ma": "KHONG_CO_TIEN", "loi": "Phiếu %s số phải trả là %s %s, không có gì để chi." % (p.doc_no, k.get("tra_chu_xe"), k.get("hire_ccy"))})
        if ccy is None:
            ccy = k["hire_ccy"]
        elif k["hire_ccy"] != ccy:
            raise HTTPException(422, {"ma": "KHAC_TIEN", "loi": "Các phiếu trong một đợt phải cùng tiền thuê (%s ≠ %s ở %s). Tách làm hai đợt." % (ccy, k["hire_ccy"], p.doc_no)})
        tong += k["tra_chu_xe"]; tong_lak += k["tra_chu_xe_lak"]
        chi_tiet.append({"doc_no": p.doc_no, "tien_thue": k["tien_thue"], "phi": k["phi"], "tru_vuot": k["tru_vuot"],
                         "ung_truoc": k["ung_truoc"], "tra_chu_xe": k["tra_chu_xe"]})
    tong = round(tong, 2) if ccy not in ("LAK", "VND") else round(tong)
    ty = (tong_lak / tong) if tong else 1
    # Chủ xe mua xăng/phụ tùng ở quầy "trừ vào tiền trả" (chủ dự án 23/09: deal 1tr6, mua 3 trăm → trả 1tr3).
    # Trừ từng phiếu bán, cũ trước, tới chừng nào còn tiền để trừ; phiếu không vừa thì để đợt sau — không trừ
    # dở một phiếu, để mỗi phiếu bán hoặc đã trừ hẳn, hoặc chưa.
    chu_id = owner.id if owner else phieu[0].owner_id
    con_lak, tru_lak, ban_tru = tong_lak, 0, []
    for b in _ban_cho_tru(db, chu_id):
        if (b.total_lak or 0) <= con_lak + 0.5:
            con_lak -= b.total_lak or 0; tru_lak += b.total_lak or 0; ban_tru.append(b)
    tru = (tru_lak / ty) if ty else 0
    tru = round(tru, 2) if ccy not in ("LAK", "VND") else round(tru)
    thuc_chi = round(tong - tru, 2) if ccy not in ("LAK", "VND") else round(tong - tru)
    x = OwnerPayment(owner_id=chu_id, pay_date=pay_date or dt.date.today(),
                     amount=thuc_chi, currency=ccy, rate_to_lak=ty, amount_lak=round(tong_lak - tru_lak),
                     gross=tong, sales_deducted=tru,
                     method=method, ref=ref, note=note, by_user=user.full_name)
    db.add(x); db.flush()
    for b in ban_tru:
        b.owner_payment_id, b.status = x.id, "offset"
    bay_gio = dt.datetime.utcnow()
    for p in phieu:
        k = tinh_phieu(p, _dong_chi(db, p))
        p.owner_payment_id = x.id
        p.owner_paid, p.owner_paid_usd, p.owner_paid_lak = True, k["tra_chu_xe"], k["tra_chu_xe_lak"]
        p.owner_paid_by, p.owner_paid_at = user.full_name, bay_gio
    ten_chu = (owner.name if owner else phieu[0].owner_name) or ""
    if thuc_chi > 0:
        # Phiếu chi = số THỰC CHI sau khi trừ hàng mua ở quầy. Phần đã trừ không đi qua quỹ: nó đã nằm ở tờ
        # HD_BAN của từng phiếu bán (Nợ 4022 / Có 70), nên khoản phải trả chủ xe giảm đúng bằng chừng đó.
        CT.ghi(db, "PC_CX", nguon_bang="owner_payments", nguon_id=x.id, trip=phieu[0] if len(phieu) == 1 else None,
               ngay=x.pay_date, doi_tuong_loai="chu_xe", doi_tuong_ten=ten_chu, tien=thuc_chi, tien_te=ccy,
               tien_lak=round(tong_lak - tru_lak), by_user=user.full_name, phuong_thuc=method, company="joint",
               mo_ta="Trả chủ xe %s · %d phiếu: %s%s" % (ten_chu, len(phieu), ", ".join(p.doc_no for p in phieu),
                                                          (" · trừ %d phiếu bán hàng" % len(ban_tru)) if ban_tru else ""),
               payload={"phieu": chi_tiet, "currency": ccy, "method": method, "ref": ref, "note": note,
                        "gross": tong, "sales_deducted": tru, "ban_tru": [b.doc_no for b in ban_tru]})
    return x


@router.post("/api/owners/{oid}/tra")
def tra_chu_xe_gop(oid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(TRA_CHU_XE)):
    """Quỹ trả một đợt: gộp tháng hay theo đợt đều là chọn danh sách phiếu rồi bấm trả."""
    o = db.get(Owner, oid)
    if not o:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chủ xe này."})
    ids = [str(i) for i in (data.get("trip_ids") or []) if i]
    phieu = [db.get(Trip, i) for i in ids]
    if any(p is None for p in phieu):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Có phiếu không tồn tại trong danh sách gửi lên."})
    tra_nhieu_phieu(db, user, phieu, pay_date=_ngay(data.get("pay_date")), method=(data.get("method") or "cash").strip(),
                    ref=(data.get("ref") or "").strip() or None, note=(data.get("note") or "").strip() or None, owner=o)
    db.commit()
    return cong_no_chu_xe(oid, db, user)
