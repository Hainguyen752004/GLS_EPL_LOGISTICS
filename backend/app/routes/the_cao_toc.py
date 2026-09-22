# -*- coding: utf-8 -*-
"""Thẻ cao tốc — ບັດທາງດ່ວນ (anh Khampla C6.1, 22/09).

Câu họ trả lời: muốn **theo dõi số dư thẻ**, mỗi chuyến qua trạm thì trừ từ thẻ; và có **hai kiểu**
— khách cấp thẻ rồi nạp tiền (cuối tháng cấn trừ vào cước của chính khách đó), hoặc khách không cấp
thì quỹ Thà Bốc bỏ tiền.

Cách làm ở đây cố ý giống hệt kho nhiên liệu, vì đó là thứ họ đã quen:

  · Thẻ là một "kho tiền" nhỏ: `toll_cards.balance` là số dư sổ, cộng dồn từ `toll_card_moves`.
  · Nạp tiền = một dòng `nap`. Qua trạm = một dòng `chi`, sinh **khi kế toán GHI SỔ mục IV** —
    đúng lúc dòng xuất kho nhiên liệu được sinh, không sớm hơn. Bãi còn sửa dòng chi thì thẻ chưa
    bị trừ; ghi sổ rồi thì trừ đúng một lần (`trip_expenses.card_move_id` chống trừ hai lần).
  · Số dư lệch với trạm (ai đó quẹt mà không khai) thì ghi một dòng `dieu_chinh` kèm lý do, chứ
    không sửa thẳng con số — sửa thẳng thì tháng sau không ai biết vì sao lệch.

Cấn trừ cuối tháng: `GET /api/the-cao-toc/cong-no?thang=` cộng phần EPL đã tiêu trên thẻ **của từng
khách** — đó là số trừ vào cước phải thu của khách ấy. Bên mình chỉ ghi và hiện; hạch toán cấn trừ
là việc của bên kế toán anh Khang.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (DONG_THE, LOAI_THE, TIEN_TE, Customer, Driver, TollCard, TollCardMove, Trip,
                    TripExpense, Vehicle)
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_ban

router = APIRouter()

SUA_THE = can_vai("acct")                         # danh mục thẻ là thoả thuận với khách → kế toán VC giữ
NAP_THE = can_vai("acct", "cash", "treasury")     # quỹ nạp tiền; kế toán nạp hộ khi khách chuyển khoản


def _so(v, ten, bat_buoc=False):
    if v in (None, ""):
        if bat_buoc:
            raise HTTPException(422, {"ma": "THIEU_SO", "loi": "Thiếu %s." % ten})
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


def xuat(db, t, kem_dong=False):
    r = {"id": t.id, "card_no": t.card_no, "name": t.name, "kind": t.kind,
         "customer_id": t.customer_id, "customer_name": t.customer_name,
         "driver_id": t.driver_id, "driver_name": t.driver_name,
         "vehicle_id": t.vehicle_id, "truck_no": t.truck_no,
         "currency": t.currency, "balance": t.balance, "active": bool(t.active), "note": t.note}
    if kem_dong:
        ds = (db.query(TollCardMove).filter(TollCardMove.card_id == t.id)
              .order_by(TollCardMove.move_date.desc(), TollCardMove.created_at.desc()).limit(200).all())
        r["moves"] = [{"id": m.id, "move_date": m.move_date.isoformat() if m.move_date else None,
                       "kind": m.kind, "amount": m.amount, "balance_after": m.balance_after,
                       "trip_doc_no": m.trip_doc_no, "ref": m.ref, "note": m.note, "by_user": m.by_user}
                      for m in ds]
    return r


# ================================================================ danh mục thẻ
@router.get("/api/the-cao-toc")
def ds_the(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Mọi vai xem được — Bãi phải biết thẻ nào còn tiền để giao cho tài xế."""
    return [xuat(db, t) for t in db.query(TollCard).order_by(TollCard.active.desc(), TollCard.card_no).all()]


@router.get("/api/the-cao-toc/cong-no")
def cong_no(thang: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Cuối tháng cấn trừ với khách: khách cấp thẻ, EPL tiêu trên thẻ bao nhiêu thì trừ vào cước bấy nhiêu."""
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem cấn trừ cước." % user.role})
    thang = (thang or dt.date.today().strftime("%Y-%m"))[:7]
    try:
        dau = dt.date.fromisoformat(thang + "-01")
    except ValueError:
        raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải dạng YYYY-MM, nhận '%s'." % thang})
    sau = dt.date(dau.year + (1 if dau.month == 12 else 0), 1 if dau.month == 12 else dau.month + 1, 1)
    the = db.query(TollCard).filter(TollCard.kind == "khach").all()
    theo_khach = {}
    for t in the:
        ds = (db.query(TollCardMove).filter(TollCardMove.card_id == t.id,
                                            TollCardMove.move_date >= dau, TollCardMove.move_date < sau).all())
        o = theo_khach.setdefault(t.customer_id or "", {
            "customer_id": t.customer_id, "customer_name": t.customer_name or "—", "currency": t.currency,
            "the": [], "nap": 0.0, "chi": 0.0, "dieu_chinh": 0.0})
        chi = sum(m.amount for m in ds if m.kind == "chi")
        nap = sum(m.amount for m in ds if m.kind == "nap")
        dc = sum(m.amount for m in ds if m.kind == "dieu_chinh")
        o["nap"] += nap; o["chi"] += chi; o["dieu_chinh"] += dc
        o["the"].append({"id": t.id, "card_no": t.card_no, "balance": t.balance, "currency": t.currency,
                         "nap": nap, "chi": chi, "so_luot": len([m for m in ds if m.kind == "chi"])})
    ds_ra = []
    for o in theo_khach.values():
        o["can_tru"] = round(o["chi"], 2)      # số trừ vào cước phải thu của khách tháng này
        ds_ra.append(o)
    ds_ra.sort(key=lambda o: o["customer_name"])
    return {"thang": thang, "ds": ds_ra, "tong_can_tru": round(sum(o["can_tru"] for o in ds_ra), 2)}


@router.get("/api/the-cao-toc/{cid}")
def xem_the(cid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    t = db.get(TollCard, cid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có thẻ này."})
    return xuat(db, t, kem_dong=True)


def _ap(db, t, data):
    if "card_no" in data:
        so = str(data.get("card_no") or "").strip()
        if not so:
            raise HTTPException(422, {"ma": "THIEU_SO_THE", "loi": "Thẻ phải có số."})
        t.card_no = so
    if "kind" in data:
        if data["kind"] not in LOAI_THE:
            raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Loại thẻ phải là %s." % " · ".join(LOAI_THE)})
        t.kind = data["kind"]
    if "currency" in data:
        ma = str(data.get("currency") or "LAK").upper()
        if ma not in TIEN_TE:
            raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền tệ phải là một trong %s." % ", ".join(TIEN_TE)})
        t.currency = ma
    for c in ("name", "note"):
        if c in data:
            setattr(t, c, (data[c] or "").strip() or None)
    if "customer_id" in data:
        kh = db.get(Customer, str(data["customer_id"])) if data["customer_id"] else None
        if data["customer_id"] and not kh:
            raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
        t.customer_id, t.customer_name = (kh.id, kh.name) if kh else (None, None)
    if "driver_id" in data:
        d = db.get(Driver, str(data["driver_id"])) if data["driver_id"] else None
        if data["driver_id"] and not d:
            raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
        t.driver_id, t.driver_name = (d.id, d.name) if d else (None, None)
    if "vehicle_id" in data:
        x = db.get(Vehicle, str(data["vehicle_id"])) if data["vehicle_id"] else None
        if data["vehicle_id"] and not x:
            raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
        t.vehicle_id, t.truck_no = (x.id, x.truck_no) if x else (None, None)
    if "active" in data:
        t.active = bool(data["active"])
    if t.kind == "khach" and not t.customer_id:
        raise HTTPException(422, {"ma": "THIEU_KHACH", "loi": "Thẻ do khách cấp thì phải ghi khách nào — cuối tháng còn cấn trừ vào cước của họ."})


@router.post("/api/the-cao-toc")
def them_the(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_THE)):
    t = TollCard(); _ap(db, t, data)
    if db.query(TollCard).filter(TollCard.card_no == t.card_no).first():
        raise HTTPException(409, {"ma": "TRUNG_SO_THE", "loi": "Thẻ số %s đã có trong danh mục." % t.card_no})
    t.balance = _so(data.get("balance"), "số dư") or 0
    db.add(t); db.commit(); db.refresh(t)
    return xuat(db, t, kem_dong=True)


@router.put("/api/the-cao-toc/{cid}")
def sua_the(cid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_THE)):
    t = db.get(TollCard, cid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có thẻ này."})
    # Số dư KHÔNG sửa thẳng: muốn đổi thì ghi một dòng điều chỉnh có lý do.
    _ap(db, t, data)
    db.commit(); db.refresh(t)
    return xuat(db, t, kem_dong=True)


# ================================================================ nạp tiền · điều chỉnh
def ghi_dong(db, t, kind, so_tien, user, ngay=None, trip=None, expense=None, ref=None, note=None):
    """Một dòng thẻ; `so_tien` luôn là số DƯƠNG, chiều do `kind` quyết định."""
    if kind not in DONG_THE:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "Loại dòng phải là %s." % " · ".join(DONG_THE)})
    so_tien = float(so_tien or 0)
    if so_tien <= 0 and kind != "dieu_chinh":
        raise HTTPException(422, {"ma": "SO_TIEN_SAI", "loi": "Số tiền phải lớn hơn 0."})
    t.balance = (t.balance or 0) + (so_tien if kind == "nap" else -so_tien if kind == "chi" else so_tien)
    m = TollCardMove(card_id=t.id, move_date=ngay or dt.date.today(), kind=kind, amount=abs(so_tien),
                     balance_after=t.balance, trip_id=trip.id if trip is not None else None,
                     trip_doc_no=trip.doc_no if trip is not None else None,
                     expense_id=expense.id if expense is not None else None,
                     ref=ref, note=note, by_user=user.full_name)
    db.add(m); db.flush()
    return m


@router.post("/api/the-cao-toc/{cid}/nap")
def nap_tien(cid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(NAP_THE)):
    t = db.get(TollCard, cid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có thẻ này."})
    if not t.active:
        raise HTTPException(409, {"ma": "THE_NGUNG", "loi": "Thẻ %s đã ngưng dùng." % t.card_no})
    ghi_dong(db, t, "nap", _so(data.get("amount"), "số tiền", bat_buoc=True), user,
             ngay=_ngay(data.get("move_date")), ref=(data.get("ref") or "").strip() or None,
             note=(data.get("note") or "").strip() or None)
    db.commit(); db.refresh(t)
    return xuat(db, t, kem_dong=True)


@router.post("/api/the-cao-toc/{cid}/dieu-chinh")
def dieu_chinh(cid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_THE)):
    """Số dư sổ lệch với trạm thì ghi một dòng có LÝ DO, không sửa thẳng con số."""
    t = db.get(TollCard, cid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có thẻ này."})
    so = _so(data.get("amount"), "số tiền", bat_buoc=True)   # dương là tăng, âm là giảm
    ly_do = (data.get("note") or "").strip()
    if not ly_do:
        raise HTTPException(422, {"ma": "THIEU_LY_DO", "loi": "Điều chỉnh số dư phải ghi lý do."})
    ghi_dong(db, t, "dieu_chinh", so, user, ngay=_ngay(data.get("move_date")), note=ly_do)
    db.commit(); db.refresh(t)
    return xuat(db, t, kem_dong=True)


# ================================================================ trừ thẻ khi ghi sổ mục IV
def tru_the_theo_phieu(db, p, user):
    """Ghi sổ mục IV → trừ thẻ cho các dòng phí cầu đường đã chọn thẻ. Gọi từ routes/phieu.py.

    Trừ ở bước GHI SỔ chứ không phải lúc Bãi gõ dòng: trước đó dòng còn sửa tới sửa lui, trừ sớm thì
    số dư thẻ nhảy loạn. `card_move_id` trên dòng chi bảo đảm không trừ hai lần.
    """
    dong = (db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "travel",
                                         TripExpense.toll_card_id.isnot(None),
                                         TripExpense.card_move_id.is_(None)).all())
    for d in dong:
        t = db.get(TollCard, d.toll_card_id)
        if t is None:
            continue
        tien = (d.qty or 0) * (d.unit_price or 0)
        if tien <= 0:
            continue
        if (d.currency or "LAK").upper() != (t.currency or "LAK").upper():
            raise HTTPException(409, {"ma": "KHAC_TIEN_THE",
                                      "loi": "Dòng %s ghi bằng %s mà thẻ %s nạp bằng %s — chọn thẻ cùng tiền hoặc sửa dòng chi."
                                             % (d.item_key or d.item_name or "", d.currency, t.card_no, t.currency)})
        m = ghi_dong(db, t, "chi", tien, user, ngay=p.back_date or p.out_date or dt.date.today(),
                     trip=p, expense=d, note="Qua trạm theo phiếu %s" % p.doc_no)
        d.card_move_id = m.id
