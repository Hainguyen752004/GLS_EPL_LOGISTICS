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
    POST /api/de-nghi-thu/cap-nhat                       đọc lại thu tiền các SO của tháng từ hệ anh Tune (chỉ xem)
    GET  /api/trips/{tid}/chi-ke-toan · POST             phiếu chi tạm ứng (mục IV) bên hệ kế toán
    GET  /api/trips/{tid}/chi-muc-ke-toan · POST …/{muc} phiếu chi "Chi khác" mục V / VI bên hệ kế toán (01/10)
    POST /api/chi-ke-toan/cap-nhat                       hỏi lại mọi phiếu chi đang chờ thủ quỹ (tạm ứng, mục V–VI)
    GET  /api/but-toan-cho                               bút toán chờ gửi (khoản không qua tiền, chờ API bên kế toán)

Từ 01/10 (chủ dự án bỏ trang kế toán tạm, số bên đó là số thử): trạng thái thu KHÔNG đọc cờ hoá đơn / thu tiền của trang tạm
(trips.invoiced · inv_no · collected_lak); "đã tạo SO" theo lần gửi SO, "đã thu" đọc lại từ công nợ khách bên hệ anh Tune.

Tiền: vai không thấy tiền CHI (Bãi) không nhận số tiền chi; vai không thấy tiền BÁN không nhận cước / đề nghị thu.
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import MUC_CHI, ChiMucTune, ChiTune, ChungTu, FuelPlace, GuiSoTune, Trip, TripExpense, TripSection, Voucher
from services import but_toan_cho as BTC
from services import gui_but_toan_tune as GBT
from services import chi_muc_tune as CMT
from services import chi_tune as CHI
from services import chung_tu as CT
from services import de_nghi_thu as DNT
from services import gui_tune as GT
from services import so_nhien_lieu as NL
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
    """Tờ đề nghị thu bên em (cờ da_day / loi_day là của đường đẩy chứng từ cũ sang trang tạm — 01/10 không còn ý nghĩa, không
    gửi nữa; tờ đã sang bên công nợ hay chưa xem ở `so_ke_toan`)."""
    return None if c is None else {"id": c.id, "so": c.so, "ngay": c.ngay.isoformat() if c.ngay else None,
                                    "tien": c.tien, "tien_te": c.tien_te, "tien_lak": c.tien_lak}


def _so_cua(db, ma):
    """{trip_id: GuiSoTune} cho danh sách."""
    return {b.trip_id: b for b in db.query(GuiSoTune).filter(GuiSoTune.trip_id.in_(list(ma)))} if ma else {}


# ---------------------------------------------------------------- mỗi DO một dòng
@router.get("/api/de-nghi-theo-do")
def theo_do(thang: str = "", q: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _chan_tai_xe(user)
    if user.role in KHONG_XEM_THEO_DO:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không có màn Đề nghị theo DO." % user.role})
    chi, ban = thay_tien_chi(user.role), thay_tien_ban(user.role)
    ds = _loc_phieu(db, thang, q)
    ma = [p.id for p in ds]
    vs, muc, dong, cts, cmt = defaultdict(list), defaultdict(dict), defaultdict(list), defaultdict(list), defaultdict(list)
    if ma:
        for v in db.query(Voucher).filter(Voucher.trip_id.in_(ma)).order_by(Voucher.doc_no).all():
            vs[v.trip_id].append(v)
        for s in db.query(TripSection).filter(TripSection.trip_id.in_(ma)).all():
            muc[s.trip_id][s.section] = s.status
        for d in db.query(TripExpense).filter(TripExpense.trip_id.in_(ma)).all():
            dong[d.trip_id].append(d)
        for c in db.query(ChungTu).filter(ChungTu.trip_id.in_(ma)).all():
            cts[c.trip_id].append(c)
        for r in db.query(ChiMucTune).filter(ChiMucTune.trip_id.in_(ma)).order_by(ChiMucTune.lan).all():
            cmt[r.trip_id].append(r)
    so_kt = _so_cua(db, ma)
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
                if s in CMT.MUC:
                    # chi mục V / VI ở hệ kế toán (01/10): lần chi gần nhất bên đó (chờ thủ quỹ · đã chi · lỗi)
                    lan = [r for r in cmt[p.id] if r.section == s and r.status != "huy"]
                    m[s]["ke_toan"] = CMT.xuat(lan[-1], thay_tien=chi) if lan else None
        x["muc"] = m
        c = next((c for c in cts[p.id] if c.loai == DNT.LOAI), None)
        b = so_kt.get(p.id)
        x["thu"] = {"trang_thai": DNT.trang_thai(p, c, b), "pdt": _xuat_pdt(c) if ban else ({"so": c.so} if c else None),
                    "da_tao_so": bool(b is not None and b.status == "synced"),
                    "order_code": b.order_code if b is not None and b.status == "synced" else None}
        if ban:
            t = tinh_phieu(p, dong[p.id], DNT.da_thu_lak(p, b))
            x["thu"].update({"doanh_thu": t["doanh_thu"], "ccy": t["ccy"], "doanh_thu_lak": t["doanh_thu_lak"],
                             "da_thu_lak": t["da_thu_lak"], "con_lai_lak": t["con_lai_lak"], "so_ke_toan": GT.xuat(b)})
        # tờ đề nghị thu (PDT) không còn "đẩy" — sang bên công nợ là gửi SO (01/10) — nên không vào phép đếm đã đối chiếu
        ho = [c for c in cts[p.id] if c.loai != DNT.LOAI]
        x["ho_so"] = {"tong": len(ho), "da_day": sum(1 for c in ho if c.da_day), "loi": sum(1 for c in ho if c.loi_day and not c.da_day)}
        ra.append(x)
    return {"thang": _thang(thang)[0].strftime("%Y-%m"), "thay_tien_chi": chi, "thay_tien_ban": ban, "ds": ra,
            "gioi_han": GIOI_HAN if len(ra) >= GIOI_HAN else None}


# ---------------------------------------------------------------- đề nghị thu
@router.get("/api/de-nghi-thu")
def ds_de_nghi_thu(thang: str = "", q: str = "", cap_nhat: int = 0, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """DO đã về (và DO đã khoá): tờ đề nghị thu, số cước, trạng thái bên công nợ. `cap_nhat=1` → đọc lại thu tiền các SO
    trong danh sách từ hệ anh Tune trước (chỉ xem); không thì dùng bản đọc lần trước. `doc_ke_toan` báo lần đọc này."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    ds = [p for p in _loc_phieu(db, thang, q) if p.transport_status == "arrived" or p.locked]
    ma = [p.id for p in ds]
    dong, pdt = defaultdict(list), {}
    if ma:
        for d in db.query(TripExpense).filter(TripExpense.trip_id.in_(ma)).all():
            dong[d.trip_id].append(d)
        for c in db.query(ChungTu).filter(ChungTu.loai == DNT.LOAI, ChungTu.nguon_bang == "trips", ChungTu.nguon_id.in_(ma)).all():
            pdt[c.nguon_id] = c
    so = _so_cua(db, ma)
    doc = None
    if cap_nhat and so:
        doc = DNT.doc_thu_tune(db, list(so.values()), ep=True)
        db.commit()
    ra = []
    for p in ds:
        b = so.get(p.id)
        t = tinh_phieu(p, dong[p.id], DNT.da_thu_lak(p, b))
        c = pdt.get(p.id)
        ra.append({**_co_ban(p), "trang_thai": DNT.trang_thai(p, c, b), "pdt": _xuat_pdt(c), "so_ke_toan": GT.xuat(b),
                   "contract_no": p.contract_no,
                   "pod_no": p.pod_no, "pod_date": p.pod_date.isoformat() if p.pod_date else None,
                   "locked_by": p.locked_by, "locked_at": p.locked_at.isoformat(timespec="minutes") if p.locked_at else None,
                   "tan_tinh": t["tan_tinh"], "don_gia": t["don_gia"], "cach_tinh": t["cach_tinh"], "ccy": t["ccy"],
                   "doanh_thu": t["doanh_thu"], "doanh_thu_lak": t["doanh_thu_lak"], "da_thu_lak": t["da_thu_lak"],
                   "con_lai_lak": t["con_lai_lak"], "da_tao_so": bool(b is not None and b.status == "synced")})
    return {"thang": _thang(thang)[0].strftime("%Y-%m"), "ds": ra, "gioi_han": GIOI_HAN if len(ra) >= GIOI_HAN else None,
            "doc_ke_toan": doc}


@router.post("/api/de-nghi-thu/cap-nhat")
def cap_nhat_de_nghi_thu(data: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Nút Cập nhật màn Phiếu đề nghị thu: đọc lại thu tiền mọi SO của DO trong tháng (`thang`, mặc định tháng này) từ công nợ
    khách bên hệ anh Tune — chỉ xem, không ghi gì sang bên đó. Trả {da_doc, loi}."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    dau, cuoi = _thang((data or {}).get("thang") or "")
    cac = (db.query(GuiSoTune).join(Trip, Trip.id == GuiSoTune.trip_id)
           .filter(GuiSoTune.status == "synced", Trip.doc_date >= dau, Trip.doc_date <= cuoi).limit(GIOI_HAN).all())
    kq = DNT.doc_thu_tune(db, cac, ep=True)
    db.commit()
    return kq


def _phieu(db, tid):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    return p


@router.get("/api/trips/{tid}/de-nghi-thu")
def mot_de_nghi_thu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Nội dung tờ đề nghị thu để in. Bên công nợ đã tạo SO thì in đúng số của tờ đã gửi; chưa thì là số theo phiếu lúc này."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    p = _phieu(db, tid)
    c = DNT.cua(db, p)
    b = DNT.so_cua(db, p)
    t, pl = DNT.noi_dung(db, p, so=b)
    if c is not None and b is not None and b.status == "synced":
        pl = CT.xuat(c)["payload"] or pl          # bên công nợ đã tạo SO theo tờ này: in đúng số của tờ
    return {**pl, "trip_id": p.id, "trang_thai": DNT.trang_thai(p, c, b), "pdt": _xuat_pdt(c), "locked": bool(p.locked),
            "locked_by": p.locked_by, "locked_at": p.locked_at.isoformat(timespec="minutes") if p.locked_at else None,
            "so_ke_toan": GT.xuat(b), "da_tao_so": bool(b is not None and b.status == "synced"),
            "da_thu_lak": t["da_thu_lak"], "con_lai_lak": t["con_lai_lak"]}


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
    trong `loi` để màn nói rõ phải sửa gì trước khi bấm gửi. Xe thuê có dầu / phụ tùng kho xuất bán: `nhien_lieu` là phần SO
    nhiên liệu cho đối tác gửi cùng nút (02/10) — {can, trang_thai, body, tom_tat, loi, gui_lai_goi_cu}."""
    _chan_tai_xe(user); _chan_tien_ban(user)
    p = _phieu(db, tid)
    return dict(GT.xem_truoc(db, p), nhien_lieu=NL.xem_truoc(db, p))


@router.post("/api/trips/{tid}/tao-so")
def tao_so(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gửi DO đã về + đã khoá sang bên công nợ; bên đó tạo SO và ghi công nợ khách. Đã có SO thì trả lại, không gọi nữa.
    Cùng nút (02/10): xe thuê có dầu / phụ tùng kho xuất bán → SO NHIÊN LIỆU cho đối tác (services/so_nhien_lieu.py). Hai phần gửi
    độc lập: SO cước đã có mà SO nhiên liệu chưa thì bấm lại chỉ gửi phần thiếu. Phần nào hỏng → HTTP lỗi của phần đó, `detail` kèm
    kết quả phần kia (`trang_thai` cước, `nhien_lieu`). → {trang_thai, da_co_truoc, nhien_lieu: {trang_thai, da_co_truoc} | null}."""
    if user.role not in GUI_SO:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                  "loi": "Chỉ KT Thu/Chi Viêng Chăn (người khoá phiếu) hoặc Sếp gửi đề nghị thu sang bên công nợ."})
    p = _phieu(db, tid)
    kq, da_co, loi = None, None, None
    try:
        kq, da_co = GT.gui(db, p, user)
    except HTTPException as e:
        loi = e
    nl, loi_nl = None, None
    try:
        r = NL.gui(db, p, user)
        nl = {"trang_thai": r[0], "da_co_truoc": r[1]} if r is not None else None
    except HTTPException as e:
        loi_nl = e
        nl = {"trang_thai": NL.xuat(NL.so_cua(db, p)), "da_co_truoc": False,
              "loi": e.detail if isinstance(e.detail, dict) else {"loi": str(e.detail)}}
    if loi is not None or loi_nl is not None:
        e = loi if loi is not None else loi_nl
        d = dict(e.detail) if isinstance(e.detail, dict) else {"ma": "LOI", "loi": str(e.detail)}
        if loi is None:
            d["loi"] = "SO cước %s. Chưa tạo SO nhiên liệu: %s" % ("đã có" if da_co else "đã tạo", d.get("loi") or d.get("ma"))
        d.update({"trang_thai": kq if loi is None else GT.xuat(DNT.so_cua(db, p)), "da_co_truoc": da_co, "nhien_lieu": nl})
        raise HTTPException(e.status_code, d)
    return {"trang_thai": kq, "da_co_truoc": da_co, "nhien_lieu": nl}


# ---------------------------------------------------------------- tạm ứng: phiếu chi bên hệ kế toán (01/10)
GUI_CHI = ("expacct", "admin")      # KT Chi phí VC (người ghi sổ mục IV) và Sếp
KHONG_XEM_CHI = ("driver", "depot", "parts", "repair")


@router.get("/api/trips/{tid}/chi-ke-toan")
def xem_chi_ke_toan(tid: str, cap_nhat: int = 0, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Phiếu chi tạm ứng bên hệ kế toán của phiếu này. `cap_nhat=1` → hỏi lại bên đó (thủ quỹ ghi sổ chưa)."""
    p = _phieu(db, tid)
    if user.role in KHONG_XEM_CHI and not (user.role == "driver" and user.driver_id and user.driver_id == p.driver_id):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem phiếu chi tạm ứng." % user.role})
    r = CHI.cua_phieu(db, p, cap_nhat=bool(cap_nhat))
    return dict(CHI.xuat(r, thay_tien=thay_tien_chi(user.role)) or {}, o_ke_toan=CHI.chi_o_ke_toan(),
                muc_travel=_muc_iv(db, p))


@router.post("/api/trips/{tid}/chi-ke-toan")
def gui_chi_ke_toan(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gửi (lại) phiếu chi tạm ứng sang hệ kế toán — thường tự gửi lúc KT Chi phí ghi sổ mục IV; nút này cho lần hỏng."""
    if user.role not in GUI_CHI:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Chi phí VC hoặc Sếp gửi phiếu chi tạm ứng sang kế toán."})
    if not CHI.chi_o_ke_toan():
        raise HTTPException(409, {"ma": "CHI_TAI_CHO", "loi": "Tạm ứng đang chi trên trang điều xe (EPL_CHI_TAM_UNG=tai_cho)."})
    p = _phieu(db, tid)
    if _muc_iv(db, p) not in ("booked", "paid"):
        raise HTTPException(409, {"ma": "MUC_IV_CHUA_GHI_SO", "loi": "Mục IV phiếu %s chưa ghi sổ — KT Chi phí ghi sổ trước." % p.doc_no})
    from routes.phieu_linh import dam_bao_tam_ung
    v = dam_bao_tam_ung(db, p, user)
    if v is None:
        raise HTTPException(409, {"ma": "KHONG_CO_TAM_UNG", "loi": "Phiếu %s không có khoản tiền mặt tạm ứng." % p.doc_no})
    db.commit()
    r = CHI.gui(db, p, v, user)
    return dict(CHI.xuat(r) or {}, o_ke_toan=True, muc_travel=_muc_iv(db, p))


@router.post("/api/chi-ke-toan/cap-nhat")
def cap_nhat_chi_ke_toan(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Hỏi lại hệ kế toán mọi phiếu chi đang chờ thủ quỹ — tạm ứng (mục IV) và chi mục V–VI (01/10), mới gửi trước, tối đa 40
    mỗi loại — nút Cập nhật ở màn Phiếu đề nghị chi."""
    if user.role in KHONG_XEM_CHI:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem phiếu chi tạm ứng." % user.role})
    cho = (db.query(ChiTune).filter(ChiTune.status == "da_gui").order_by(ChiTune.last_attempt_at.desc().nullslast())
           .limit(40).all())
    cho_muc = (db.query(ChiMucTune).filter(ChiMucTune.status == "da_gui").order_by(ChiMucTune.last_attempt_at.desc().nullslast())
               .limit(40).all())
    da_chi, loi, dung = 0, None, False
    for dong_bo, r in [(CHI.dong_bo, r) for r in cho] + [(CMT.dong_bo, r) for r in cho_muc]:
        if dung:
            break
        try:
            if dong_bo(db, r).status == "da_chi":
                da_chi += 1
        except HTTPException as e:
            loi = (e.detail or {}).get("loi") if isinstance(e.detail, dict) else str(e.detail)
            if (e.detail or {}).get("ma") in ("KHONG_GOI_DUOC", "QLSX_TOKEN_HET_HAN", "CHUA_CO_TOKEN"):
                dung = True                          # bên kia không vào được thì dừng, không gọi 80 lần hỏng
    return {"da_hoi": len(cho) + len(cho_muc), "moi_da_chi": da_chi, "loi": loi}


# ---------------------------------------------------------------- chi mục V–VI: phiếu chi "Chi khác" bên hệ kế toán (01/10)
def _muc(db, p, muc):
    s = db.query(TripSection).filter(TripSection.trip_id == p.id, TripSection.section == muc).first()
    return s.status if s else "wait"


@router.get("/api/trips/{tid}/chi-muc-ke-toan")
def xem_chi_muc_ke_toan(tid: str, cap_nhat: int = 0, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Chi mục V (sửa chữa) · VI (chi khác) bên hệ kế toán của phiếu: các lần phiếu chi, khoản quỹ trả ngay, phần còn phải chi.
    `cap_nhat=1` → hỏi lại bên đó (thủ quỹ ghi sổ chưa). Vai không thấy tiền chi (Bãi) nhận trạng thái, không nhận số tiền."""
    p = _phieu(db, tid)
    if user.role in KHONG_XEM_CHI:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem phiếu chi bên kế toán." % user.role})
    lan = CMT.cua_phieu(db, p, cap_nhat=bool(cap_nhat))
    tien = thay_tien_chi(user.role)
    return {"o_ke_toan": CHI.chi_o_ke_toan(),
            **{m: dict(CMT.tom_tat(db, p, m, [r for r in lan if r.section == m], thay_tien=tien), muc=_muc(db, p, m)) for m in CMT.MUC}}


@router.post("/api/trips/{tid}/chi-muc-ke-toan/{muc}")
def gui_chi_muc_ke_toan(tid: str, muc: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gửi (lại) phiếu chi mục V / VI sang hệ kế toán — thường tự gửi lúc KT Chi phí ghi sổ mục; nút này cho lần hỏng."""
    if user.role not in GUI_CHI:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Chi phí VC hoặc Sếp gửi phiếu chi sang kế toán."})
    if muc not in CMT.MUC:
        raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Chi ở hệ kế toán chỉ cho mục V (repair), VI (other)."})
    if not CHI.chi_o_ke_toan():
        raise HTTPException(409, {"ma": "CHI_TAI_CHO", "loi": "Đang chi trên trang điều xe (EPL_CHI_TAM_UNG=tai_cho)."})
    p = _phieu(db, tid)
    if _muc(db, p, muc) not in ("booked", "paid"):
        raise HTTPException(409, {"ma": "MUC_CHUA_GHI_SO", "loi": "Mục %s phiếu %s chưa ghi sổ — KT Chi phí ghi sổ trước."
                                                                  % (CMT.TEN_MUC[muc], p.doc_no)})
    CMT.gui(db, p, muc, user)
    return dict(CMT.tom_tat(db, p, muc), muc=_muc(db, p, muc))


# ---------------------------------------------------------------- bút toán chờ gửi (01/10)
@router.get("/api/but-toan-cho")
def ds_but_toan_cho(nguon: str = "", status: str = "", trip_id: str = "", thang: str = "", tu: str = "", den: str = "",
                    gioi_han: int = 200, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """BÚT TOÁN CHỜ GỬI — khoản không qua tiền sổ kế toán phải ghi (khoá phiếu: thuê xe Nợ 621 / Có 4022, ghi nợ nhà cung cấp
    Nợ 625 · 614 / Có 4021; tất toán…), giữ ở đây chờ hệ anh Tune có API bút toán. Chỉ ĐỌC. Vai: KT Thu/Chi VC, KT Chi phí VC,
    Sếp (services/but_toan_cho.VAI_XEM) — bút toán mang tiền thuê xe liên kết. `status`, `nguon` nhận nhiều giá trị (dấu phẩy);
    `thang` = YYYY-MM theo ngày hạch toán."""
    if user.role not in BTC.VAI_XEM:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem bút toán chờ gửi." % user.role})
    if thang:
        tu, den = _thang(thang)
    try:
        ds = BTC.danh_sach(db, nguon=nguon or None, status=status or None, trip_id=trip_id or None, tu=tu or None,
                           den=den or None, gioi_han=gioi_han)
    except ValueError as e:
        raise HTTPException(422, {"ma": "LOC_SAI", "loi": str(e)})
    so = {}
    ma = {r.trip_id for r in ds if r.trip_id}
    if ma:
        so = dict(db.query(Trip.id, Trip.doc_no).filter(Trip.id.in_(ma)).all())
    from sqlalchemy import func
    from models import ButToanCho
    dem = dict(db.query(ButToanCho.status, func.count(ButToanCho.id)).group_by(ButToanCho.status).all())
    dao = db.query(func.count(ButToanCho.id)).filter(ButToanCho.can_dao.is_(True)).scalar()
    return {"ds": [BTC.xuat(r, so.get(r.trip_id)) for r in ds], "dem": dict(dem, can_dao=dao), "co_duong_gui": GBT.bat(),
            "ghi_chu": ("Gửi sang hệ kế toán đang BẬT (QLSX_GUI_BUT_TOAN): ghi xong tự gửi; hỏng thì bấm Gửi / Gửi hết." if GBT.bat() else
                        "Hệ kế toán chưa có đường nhận bút toán tổng hợp (hợp đồng kế toán 12.12.4) — bút toán nằm đây, đủ hai vế, "
                        "chờ có API thì gửi.")}


def _btc_gui_duoc(user):
    if user.role not in BTC.VAI_XEM:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không gửi bút toán sang kế toán." % user.role})
    if not GBT.bat():
        raise HTTPException(409, {"ma": "GUI_DANG_TAT", "loi": "Chưa bật gửi bút toán sang hệ kế toán (QLSX_GUI_BUT_TOAN) — bên đó "
                                                               "chưa có đường nhận; bút toán nằm ở đây để xem."})


@router.post("/api/but-toan-cho/gui-het")
def gui_het_but_toan(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gửi mọi bút toán chờ gửi (cũ trước) và đảo mọi bản chờ đảo — dừng khi bên kế toán không vào được."""
    _btc_gui_duoc(user)
    return GBT.gui_het(db)


@router.post("/api/but-toan-cho/{bid}/{viec}")
def viec_but_toan(bid: str, viec: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """gui (bản chờ gửi → gửi; bản chờ đảo → đảo) · cap-nhat (hỏi lại số chứng từ bên kế toán)."""
    from models import ButToanCho
    _btc_gui_duoc(user)
    r = db.get(ButToanCho, bid)
    if r is None:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có bút toán này."})
    if viec == "gui":
        if r.status == "da_gui" and r.can_dao:
            GBT.dao(db, r)
        elif r.status == "cho_gui":
            GBT.gui(db, r)
        else:
            raise HTTPException(409, {"ma": "KHONG_GUI", "loi": "Bút toán này đang %s — không có gì để gửi." % r.status})
    elif viec == "cap-nhat":
        GBT.cap_nhat(db, r)
    else:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có việc %s." % viec})
    doc = db.query(Trip.doc_no).filter(Trip.id == r.trip_id).scalar() if r.trip_id else None
    return BTC.xuat(r, doc)


def _muc_iv(db, p):
    s = db.query(TripSection).filter(TripSection.trip_id == p.id, TripSection.section == "travel").first()
    return s.status if s else "wait"
