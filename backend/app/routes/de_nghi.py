# -*- coding: utf-8 -*-
"""PHIẾU ĐỀ NGHỊ theo DO (sếp 30/09): "DO nào phiếu chi gì, trạng thái gì; DO nào phiếu thu gì, trạng thái gì".

Bên mình chỉ làm logistics, phiếu của mình là phiếu ĐỀ NGHỊ:
  · đề nghị CHI đi theo từng bước — tạm ứng (PTU), xuất nhiên liệu (PLNL, mỗi kho một tờ), chi các mục III–VI khi
    kế toán ghi sổ (quỹ chi);
  · đề nghị THU sinh một lần khi DO xong (khoá phiếu) — PDT, gửi bên công nợ (anh Tune) lập SO, hoá đơn, thu tiền.
Bên kho / bên tiền làm việc thật; bên này chỉ XEM trạng thái bên đó chép sang.

    GET  /api/de-nghi-theo-do?thang=YYYY-MM&q=&loc=      mỗi DO một dòng: đề nghị chi, đề nghị thu, hồ sơ gửi kế toán
    GET  /api/de-nghi-thu?thang=&q=&trang_thai=          DO đã về: tờ đề nghị thu và trạng thái bên công nợ
    GET  /api/trips/{tid}/de-nghi-thu                    nội dung tờ để in
    POST /api/trips/{tid}/de-nghi-thu                    lập tờ cho phiếu đã khoá mà chưa có (phiếu khoá trước 30/09)
    GET  /api/trips/{tid}/tao-so                         xem trước gói gửi bên công nợ (không gọi mạng) + lần gửi trước
    POST /api/trips/{tid}/tao-so                         gửi DO sang bên công nợ (anh Tune) → SO + công nợ khách bên đó

Tiền: vai không thấy tiền CHI (Bãi) không nhận số tiền chi; vai không thấy tiền BÁN không nhận cước / đề nghị thu.
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import MUC_CHI, ChungTu, FuelPlace, Trip, TripExpense, TripSection, Voucher
from services import chung_tu as CT
from services import de_nghi_thu as DNT
from services import gui_tune as GT
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import thay_tien_ban, thay_tien_chi
from services.tinh_toan import tien_dong, tinh_phieu

router = APIRouter()
GIOI_HAN = 400


def _thang(thang):
    try:
        dau = dt.date.fromisoformat((thang or dt.date.today().strftime("%Y-%m"))[:7] + "-01")
    except ValueError:
        raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải có dạng YYYY-MM."})
    cuoi = (dau.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return dau, cuoi


def _loc_phieu(db, thang, q):
    dau, cuoi = _thang(thang)
    qs = db.query(Trip).filter(Trip.doc_date >= dau, Trip.doc_date <= cuoi)
    if q:
        k = "%" + q.strip() + "%"
        qs = qs.filter(or_(Trip.doc_no.ilike(k), Trip.truck_no.ilike(k), Trip.driver_name.ilike(k), Trip.customer_name.ilike(k)))
    return qs.order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).limit(GIOI_HAN).all()


def _co_ban(p):
    return {"trip_id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None, "kind": p.kind,
            "company": p.company, "owner_name": p.owner_name if p.company == "joint" else None, "truck_no": p.truck_no,
            "driver_name": p.driver_name, "customer_name": p.customer_name, "origin": p.origin, "destination": p.destination,
            "transport_status": p.transport_status, "locked": bool(p.locked), "pod": bool(p.pod_no or p.pod_at)}


def _chan_tai_xe(user):
    if user.role == "driver":
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế xem phiếu của mình ở màn Phiếu của tôi."})


# vai có màn Đề nghị theo DO — đúng như menu (js/chung.js): mọi vai trừ tài xế và ba vai một việc ở kho / xưởng
KHONG_XEM_THEO_DO = ("driver", "depot", "parts", "repair")


def _chan_tien_ban(user):
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Đề nghị thu là tiền cước — vai %s không xem." % user.role})


def _xuat_pdt(c):
    return None if c is None else {"id": c.id, "so": c.so, "ngay": c.ngay.isoformat() if c.ngay else None, "da_day": bool(c.da_day),
                                    "ma_ben_ke_toan": c.ma_ben_ke_toan, "loi_day": c.loi_day, "tien": c.tien, "tien_te": c.tien_te,
                                    "tien_lak": c.tien_lak}


# ---------------------------------------------------------------- mỗi DO một dòng
@router.get("/api/de-nghi-theo-do")
def theo_do(thang: str = "", q: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _chan_tai_xe(user)
    if user.role in KHONG_XEM_THEO_DO:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không có màn Đề nghị theo DO." % user.role})
    chi, ban = thay_tien_chi(user.role), thay_tien_ban(user.role)
    ds = _loc_phieu(db, thang, q)
    ma = [p.id for p in ds]
    vs, muc, dong, cts = defaultdict(list), defaultdict(dict), defaultdict(list), defaultdict(list)
    if ma:
        for v in db.query(Voucher).filter(Voucher.trip_id.in_(ma)).order_by(Voucher.doc_no).all():
            vs[v.trip_id].append(v)
        for s in db.query(TripSection).filter(TripSection.trip_id.in_(ma)).all():
            muc[s.trip_id][s.section] = s.status
        for d in db.query(TripExpense).filter(TripExpense.trip_id.in_(ma)).all():
            dong[d.trip_id].append(d)
        for c in db.query(ChungTu).filter(ChungTu.trip_id.in_(ma)).all():
            cts[c.trip_id].append(c)
    kho = {k.id: k.name for k in db.query(FuelPlace).all()}
    ra = []
    for p in ds:
        x = _co_ban(p)
        tu = [v for v in vs[p.id] if v.kind == "advance" and v.status != "huy"]
        x["tam_ung"] = [{"id": v.id, "so": v.doc_no, "status": v.status, **({"amount_lak": v.amount_lak} if chi else {})} for v in tu]
        x["nhien_lieu"] = [{"id": v.id, "so": v.doc_no, "status": v.status, "place_name": kho.get(v.place_id), "qty_l": v.qty_l,
                            "granted_qty": v.granted_qty} for v in vs[p.id] if v.kind == "fuel" and v.status != "huy"]
        m = {}
        for s in MUC_CHI:
            ds_dong = [d for d in dong[p.id] if d.section == s and (p.company != "joint" or d.paid_by_epl)]
            if ds_dong:
                m[s] = {"status": muc[p.id].get(s, "wait"), "so_dong": len(ds_dong),
                        **({"tien_lak": round(sum(tien_dong(p, d) for d in ds_dong))} if chi else {})}
        x["muc"] = m
        c = next((c for c in cts[p.id] if c.loai == DNT.LOAI), None)
        x["thu"] = {"trang_thai": DNT.trang_thai(p, c), "pdt": _xuat_pdt(c) if ban else ({"so": c.so, "da_day": bool(c.da_day)} if c else None),
                    "invoiced": bool(p.invoiced), "inv_no": p.inv_no}
        if ban:
            t = tinh_phieu(p, dong[p.id], p.collected_lak or 0)
            x["thu"].update({"doanh_thu": t["doanh_thu"], "ccy": t["ccy"], "doanh_thu_lak": t["doanh_thu_lak"],
                             "da_thu_lak": t["da_thu_lak"], "con_lai_lak": t["con_lai_lak"]})
        x["ho_so"] = {"tong": len(cts[p.id]), "da_day": sum(1 for c in cts[p.id] if c.da_day),
                      "loi": sum(1 for c in cts[p.id] if c.loi_day and not c.da_day)}
        ra.append(x)
    return {"thang": _thang(thang)[0].strftime("%Y-%m"), "thay_tien_chi": chi, "thay_tien_ban": ban, "ds": ra,
            "gioi_han": GIOI_HAN if len(ra) >= GIOI_HAN else None}


# ---------------------------------------------------------------- đề nghị thu
@router.get("/api/de-nghi-thu")
def ds_de_nghi_thu(thang: str = "", q: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """DO đã về (và DO đã khoá): tờ đề nghị thu, số cước, trạng thái bên công nợ."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    ds = [p for p in _loc_phieu(db, thang, q) if p.transport_status == "arrived" or p.locked]
    ma = [p.id for p in ds]
    dong, pdt = defaultdict(list), {}
    if ma:
        for d in db.query(TripExpense).filter(TripExpense.trip_id.in_(ma)).all():
            dong[d.trip_id].append(d)
        for c in db.query(ChungTu).filter(ChungTu.loai == DNT.LOAI, ChungTu.nguon_bang == "trips", ChungTu.nguon_id.in_(ma)).all():
            pdt[c.nguon_id] = c
    so_kt = GT.cua_nhieu(db, ma)
    ra = []
    for p in ds:
        t = tinh_phieu(p, dong[p.id], p.collected_lak or 0)
        c = pdt.get(p.id)
        ra.append({**_co_ban(p), "trang_thai": DNT.trang_thai(p, c), "pdt": _xuat_pdt(c), "so_ke_toan": so_kt.get(p.id),
                   "contract_no": p.contract_no,
                   "pod_no": p.pod_no, "pod_date": p.pod_date.isoformat() if p.pod_date else None,
                   "locked_by": p.locked_by, "locked_at": p.locked_at.isoformat(timespec="minutes") if p.locked_at else None,
                   "tan_tinh": t["tan_tinh"], "don_gia": t["don_gia"], "cach_tinh": t["cach_tinh"], "ccy": t["ccy"],
                   "doanh_thu": t["doanh_thu"], "doanh_thu_lak": t["doanh_thu_lak"], "da_thu_lak": t["da_thu_lak"],
                   "con_lai_lak": t["con_lai_lak"], "invoiced": bool(p.invoiced), "inv_no": p.inv_no,
                   "invoiced_date": p.invoiced_date.isoformat() if p.invoiced_date else None,
                   "last_paid_date": p.last_paid_date.isoformat() if p.last_paid_date else None})
    return {"thang": _thang(thang)[0].strftime("%Y-%m"), "ds": ra, "gioi_han": GIOI_HAN if len(ra) >= GIOI_HAN else None}


def _phieu(db, tid):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    return p


@router.get("/api/trips/{tid}/de-nghi-thu")
def mot_de_nghi_thu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Nội dung tờ đề nghị thu để in. Có tờ rồi thì in đúng số của tờ (đã gửi thì là số bên công nợ đã nhận);
    chưa có thì là bản xem trước theo phiếu lúc này."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    p = _phieu(db, tid)
    c = DNT.cua(db, p)
    t, pl = DNT.noi_dung(db, p)
    if c is not None and c.da_day:
        pl = CT.xuat(c)["payload"] or pl
    return {**pl, "trip_id": p.id, "trang_thai": DNT.trang_thai(p, c), "pdt": _xuat_pdt(c), "locked": bool(p.locked),
            "locked_by": p.locked_by, "locked_at": p.locked_at.isoformat(timespec="minutes") if p.locked_at else None,
            "invoiced": bool(p.invoiced), "inv_no": p.inv_no, "da_thu_lak": t["da_thu_lak"], "con_lai_lak": t["con_lai_lak"]}


@router.post("/api/trips/{tid}/de-nghi-thu")
def lap_de_nghi_thu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Phiếu khoá trước ngày có đề nghị thu (30/09) chưa có tờ: kế toán Viêng Chăn lập bù. Gọi lại trả tờ đã có."""
    if user.role not in ("acct", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán Viêng Chăn lập phiếu đề nghị thu."})
    p = _phieu(db, tid)
    if not p.locked:
        raise HTTPException(409, {"ma": "CHUA_KHOA", "loi": "Phiếu %s chưa khoá — DO xong (xe về, có biên bản giao nhận, khoá phiếu) "
                                                           "mới đề nghị thu." % p.doc_no})
    c = DNT.ghi(db, p, user)
    db.commit()
    return _xuat_pdt(c)


# ---------------------------------------------------------------- gửi bên công nợ (anh Tune) — hợp đồng kế toán, mục 3.2
GUI_SO = ("acct", "admin")          # người khoá phiếu (KT Thu/Chi Viêng Chăn) và Sếp


@router.get("/api/trips/{tid}/tao-so")
def xem_tao_so(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gói SẼ gửi và trạng thái lần gửi trước. Không gọi mạng. Lỗi dữ liệu (thiếu mã khách, thiếu tuyến, cước THB…) nằm
    trong `loi` để màn nói rõ phải sửa gì trước khi bấm gửi."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    return GT.xem_truoc(db, _phieu(db, tid))


@router.post("/api/trips/{tid}/tao-so")
def tao_so(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gửi DO đã về + đã khoá sang bên công nợ; bên đó tạo SO và ghi công nợ khách. Đã có SO thì trả lại, không gọi nữa."""
    if user.role not in GUI_SO:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                  "loi": "Chỉ KT Thu/Chi Viêng Chăn (người khoá phiếu) hoặc Sếp gửi đề nghị thu sang bên công nợ."})
    kq, da_co = GT.gui(db, _phieu(db, tid), user)
    return {"trang_thai": kq, "da_co_truoc": da_co}
