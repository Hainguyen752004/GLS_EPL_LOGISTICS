# -*- coding: utf-8 -*-
"""Hoá đơn GỘP THÁNG — ໃບເກັບເງິນລວມເດືອນ (anh Khampla 22/09, C8.2 · B3).

Câu hỏi của bên mình: "một hoá đơn cho một phiếu, hay gộp nhiều phiếu trong tháng?" Anh Khampla
trả lời: **cả hai** — khách có hợp đồng thì cuối tháng gộp một tờ, khách vãng lai thì mỗi phiếu
một tờ như cũ. Nên danh mục khách có cờ `invoice_mode`:

  · `phieu` (mặc định) — kế toán doanh thu bấm "Xuất hoá đơn" ngay trên từng phiếu, y như trước.
  · `thang` — nút đó bị chặn; cuối tháng vào màn Hoá đơn gộp, chọn khách và tháng, bấm
    "Gộp hoá đơn tháng" → MỘT tờ `HD` mang nhiều dòng phiếu.

Hai điều phải giữ cho đúng:

1. **Tiền của tờ gộp = cộng doanh thu từng phiếu**, không gõ tay, không tính lại theo cách khác —
   để tờ gộp và bảng theo dõi từng phiếu không bao giờ nói hai con số.
2. **Thu tiền ghi ở TỜ GỘP, nhưng phải phân bổ xuống từng phiếu.** Khách chuyển một cục cho cả
   tháng; nếu chỉ ghi ở tờ gộp thì mọi phiếu trong tháng vẫn treo "chưa thu", báo cáo theo phiếu
   sai hết. Nên mỗi lần thu sinh một `invoice_payments` (một tờ PT) rồi rải xuống `trip_payments`
   theo THỨ TỰ NGÀY PHIẾU — phiếu cũ trả trước, đúng cách họ đối chiếu công nợ. Trạng thái từng
   phiếu vẫn do tổng `trip_payments` quyết định như mọi phiếu khác, không có đường tính thứ hai.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (PHUONG_THUC_THU, TIEN_TE, Customer, Invoice, InvoicePayment, Trip, TripPayment)
from routes.phieu import (LECH_COI_LA_DU, _dong_chi, _muc_cua, _tinh_lai_trang_thai_thu, da_thu_theo_phieu)
from services import chung_tu as CT
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import thay_tien_ban
from services.tinh_toan import tinh_phieu, ty_gia

router = APIRouter()


def _ngay(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


def _so(v, ten):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số, nhận '%s'." % (ten, v)})


def _thang(v):
    """Tháng dạng YYYY-MM. Không gửi thì lấy tháng này."""
    s = str(v or "")[:7]
    if not s:
        return dt.date.today().strftime("%Y-%m")
    try:
        dt.date.fromisoformat(s + "-01")
    except ValueError:
        raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải dạng YYYY-MM, nhận '%s'." % v})
    return s


def _khoang(period):
    """(ngày đầu tháng, ngày đầu tháng sau) — lọc theo nửa khoảng [dau, sau)."""
    dau = dt.date.fromisoformat(period + "-01")
    sau = dt.date(dau.year + (1 if dau.month == 12 else 0), 1 if dau.month == 12 else dau.month + 1, 1)
    return dau, sau


def _xem_duoc(user):
    """Hoá đơn là TIỀN BÁN — Bãi và tài xế không xem."""
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem hoá đơn." % user.role})


def _lap_duoc(user):
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu lập và thu hoá đơn gộp."})


# ---------------------------------------------------------------- số hoá đơn gộp: HDT-202609-01
def _so_moi(db, period):
    dau = "HDT-%s-" % period.replace("-", "")
    n = db.query(func.count(Invoice.id)).filter(Invoice.inv_no.like(dau + "%")).scalar() or 0
    for _lan in range(200):
        n += 1
        so = "%s%02d" % (dau, n)
        if db.query(Invoice).filter(Invoice.inv_no == so).first() is None:
            return so
    raise HTTPException(409, {"ma": "TRUNG_SO_HOA_DON", "loi": "Không cấp được số hoá đơn gộp, thử lại giúp em."})


# ---------------------------------------------------------------- phiếu vào được tờ gộp
def _du_dieu_kien(db, p):
    """Phiếu vào được tờ gộp khi: đã kiểm mục II, đã KHOÁ, chưa nằm tờ nào, và có doanh thu."""
    if p.invoice_id or p.invoiced or not p.locked:
        return False
    return _muc_cua(db, p)["trans"].status == "verified"


def _dong_phieu(db, p, da_thu=0.0):
    k = tinh_phieu(p, _dong_chi(db, p), da_thu)
    return {"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "truck_no": p.truck_no, "driver_name": p.driver_name, "origin": p.origin, "destination": p.destination,
            "ore_bill_no": p.ore_bill_no, "weight_dest": p.weight_dest, "weight_origin": p.weight_origin,
            "tan_tinh": k["tan_tinh"], "price": p.price, "cach_tinh": k["cach_tinh"], "ccy": k["ccy"],
            "doanh_thu": k["doanh_thu"], "doanh_thu_lak": k["doanh_thu_lak"],
            "da_thu_lak": round(da_thu), "con_lai_lak": round(k["doanh_thu_lak"] - da_thu),
            "finance_status": p.finance_status}


@router.get("/api/hoa-don-gop/cho-gop")
def cho_gop(period: str = "", customer_id: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Khách nào đang có phiếu chờ gộp trong tháng — mỗi khách tách theo TIỀN CƯỚC.

    Tách theo tiền vì một tờ hoá đơn chỉ mang một loại tiền: khách ký hai tuyến, tuyến này USD
    tuyến kia Kíp, thì cuối tháng là hai tờ chứ không phải một tờ cộng hai thứ tiền vào nhau.
    """
    _xem_duoc(user)
    period = _thang(period)
    dau, sau = _khoang(period)
    q = (db.query(Trip).join(Customer, Customer.id == Trip.customer_id)
         .filter(Customer.invoice_mode == "thang", Trip.locked.is_(True), Trip.invoice_id.is_(None),
                 Trip.invoiced.is_(False), Trip.doc_date >= dau, Trip.doc_date < sau))
    if customer_id:
        q = q.filter(Trip.customer_id == customer_id)
    nhom = {}
    for p in q.order_by(Trip.doc_date, Trip.doc_no).all():
        if not _du_dieu_kien(db, p):
            continue
        k = tinh_phieu(p, _dong_chi(db, p))
        khoa = (p.customer_id, k["ccy"])
        o = nhom.setdefault(khoa, {"customer_id": p.customer_id, "customer_name": p.customer_name,
                                   "ccy": k["ccy"], "period": period, "phieu": [], "tong": 0.0, "tong_lak": 0.0})
        o["phieu"].append(_dong_phieu(db, p))
        o["tong"] += k["doanh_thu"]; o["tong_lak"] += k["doanh_thu_lak"]
    ds = []
    for o in nhom.values():
        o["tong"] = round(o["tong"], 2); o["tong_lak"] = round(o["tong_lak"])
        o["so_phieu"] = len(o["phieu"])
        ds.append(o)
    ds.sort(key=lambda o: (o["customer_name"] or "", o["ccy"]))
    return {"period": period, "ds": ds}


# ---------------------------------------------------------------- xuất một tờ
def xuat_hd(db, hd, day_du=False):
    r = {"id": hd.id, "inv_no": hd.inv_no, "customer_id": hd.customer_id, "customer_name": hd.customer_name,
         "period": hd.period, "inv_date": hd.inv_date.isoformat() if hd.inv_date else None,
         "currency": hd.currency, "amount": hd.amount, "amount_lak": hd.amount_lak, "so_phieu": hd.so_phieu,
         "note": hd.note, "by_user": hd.by_user,
         "created_at": hd.created_at.isoformat() if hd.created_at else None}
    phieu = db.query(Trip).filter(Trip.invoice_id == hd.id).order_by(Trip.doc_date, Trip.doc_no).all()
    da = da_thu_theo_phieu(db, [p.id for p in phieu])
    r["da_thu_lak"] = round(sum(da.get(p.id, 0) for p in phieu))
    r["con_lai_lak"] = round(hd.amount_lak - r["da_thu_lak"])
    r["finance_status"] = ("unpaid" if r["da_thu_lak"] <= LECH_COI_LA_DU
                           else ("paid" if r["con_lai_lak"] <= LECH_COI_LA_DU else "partial"))
    if day_du:
        r["phieu"] = [_dong_phieu(db, p, da.get(p.id, 0)) for p in phieu]
        r["thu_tien"] = [_xuat_thu(x) for x in db.query(InvoicePayment)
                         .filter(InvoicePayment.invoice_id == hd.id)
                         .order_by(InvoicePayment.pay_date, InvoicePayment.created_at).all()]
        c = CT.tim(db, "HD", "invoices", hd.id)
        r["chung_tu"] = c.so if c is not None else None
    return r


def _xuat_thu(x):
    return {"id": x.id, "invoice_id": x.invoice_id, "pay_date": x.pay_date.isoformat() if x.pay_date else None,
            "amount": x.amount, "currency": x.currency, "rate_to_lak": x.rate_to_lak, "amount_lak": x.amount_lak,
            "method": x.method, "ref": x.ref, "note": x.note, "by_user": x.by_user,
            "created_at": x.created_at.isoformat() if x.created_at else None}


@router.get("/api/hoa-don-gop")
def ds_hoa_don(period: str = "", customer_id: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _xem_duoc(user)
    q = db.query(Invoice)
    if period:
        q = q.filter(Invoice.period == _thang(period))
    if customer_id:
        q = q.filter(Invoice.customer_id == customer_id)
    return [xuat_hd(db, h) for h in q.order_by(Invoice.period.desc(), Invoice.inv_no.desc()).all()]


@router.get("/api/hoa-don-gop/{hid}")
def xem_hoa_don(hid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    _xem_duoc(user)
    hd = db.get(Invoice, hid)
    if not hd:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có hoá đơn gộp này."})
    return xuat_hd(db, hd, day_du=True)


# ---------------------------------------------------------------- gộp hoá đơn tháng
@router.post("/api/hoa-don-gop")
def gop_thang(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gộp mọi phiếu đủ điều kiện của MỘT khách × MỘT tháng × MỘT loại tiền thành một tờ."""
    _lap_duoc(user)
    kh = db.get(Customer, str(data.get("customer_id") or ""))
    if not kh:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    if kh.invoice_mode != "thang":
        raise HTTPException(409, {"ma": "KHONG_GOP_THANG",
                                  "loi": "Khách %s đang để mỗi phiếu một hoá đơn. Muốn gộp tháng thì đổi cách xuất hoá đơn trong danh mục khách hàng." % kh.name})
    period = _thang(data.get("period"))
    dau, sau = _khoang(period)
    ma = (data.get("currency") or "").strip().upper() or None
    if ma and ma not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền tệ phải là một trong %s." % ", ".join(TIEN_TE)})
    ds = (db.query(Trip).filter(Trip.customer_id == kh.id, Trip.locked.is_(True), Trip.invoice_id.is_(None),
                                Trip.invoiced.is_(False), Trip.doc_date >= dau, Trip.doc_date < sau)
          .order_by(Trip.doc_date, Trip.doc_no).all())
    chon, tong, tong_lak, chi_tiet = [], 0.0, 0.0, []
    for p in ds:
        if not _du_dieu_kien(db, p):
            continue
        k = tinh_phieu(p, _dong_chi(db, p))
        if (k["doanh_thu"] or 0) <= 0:
            continue
        if ma is None:
            ma = k["ccy"]
        elif k["ccy"] != ma:
            continue                      # tiền khác thì thuộc tờ khác — gọi lại với currency đó
        chon.append(p); tong += k["doanh_thu"]; tong_lak += k["doanh_thu_lak"]
        chi_tiet.append({"doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
                         "tan_tinh": k["tan_tinh"], "don_gia": p.price, "cach_tinh": k["cach_tinh"],
                         "thanh_tien": k["doanh_thu"], "thanh_tien_lak": k["doanh_thu_lak"],
                         "rate_to_lak": ty_gia(p, k["ccy"])})
    if not chon:
        raise HTTPException(409, {"ma": "KHONG_CO_PHIEU",
                                  "loi": "Tháng %s không có phiếu nào của %s đã khoá và chưa xuất hoá đơn." % (period, kh.name)})
    tong = round(tong, 2) if ma not in ("LAK", "VND") else round(tong)
    hd = Invoice(inv_no=_so_moi(db, period), customer_id=kh.id, customer_name=kh.name, period=period,
                 inv_date=_ngay(data.get("inv_date")) or dt.date.today(), currency=ma, amount=tong,
                 amount_lak=round(tong_lak), so_phieu=len(chon),
                 note=(data.get("note") or "").strip() or None, by_user=user.full_name)
    db.add(hd); db.flush()
    for p in chon:
        p.invoice_id = hd.id
        p.invoiced = True
    CT.ghi(db, "HD", nguon_bang="invoices", nguon_id=hd.id, ngay=hd.inv_date, doi_tuong_loai="khach",
           doi_tuong_ten=kh.name, tien=tong, tien_te=ma, tien_lak=round(tong_lak), by_user=user.full_name,
           mo_ta="Hoá đơn gộp tháng %s · %s · %d phiếu" % (period, kh.name, len(chon)),
           payload={"inv_no": hd.inv_no, "period": period, "currency": ma, "so_phieu": len(chon), "phieu": chi_tiet})
    db.commit()
    return xuat_hd(db, hd, day_du=True)


@router.delete("/api/hoa-don-gop/{hid}")
def huy_hoa_don(hid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Gộp nhầm tháng thì huỷ tờ, các phiếu quay về "chưa xuất hoá đơn" — nhưng chỉ khi CHƯA thu
    đồng nào và tờ HD chưa đẩy sang kế toán."""
    _lap_duoc(user)
    hd = db.get(Invoice, hid)
    if not hd:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có hoá đơn gộp này."})
    if db.query(InvoicePayment).filter(InvoicePayment.invoice_id == hd.id).first() is not None:
        raise HTTPException(409, {"ma": "DA_THU", "loi": "Hoá đơn %s đã có lần thu tiền, không huỷ được. Xoá các lần thu trước." % hd.inv_no})
    c = CT.tim(db, "HD", "invoices", hd.id)
    if c is not None and c.da_day:
        raise HTTPException(409, {"ma": "DA_DAY_KE_TOAN",
                                  "loi": "Hoá đơn %s đã đẩy sang kế toán, không huỷ được. Nhờ bên kế toán ghi bút toán đảo." % c.so})
    for p in db.query(Trip).filter(Trip.invoice_id == hd.id).all():
        p.invoice_id = None
        p.invoiced = False
    if c is not None:
        db.delete(c)
    db.delete(hd)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- thu tiền theo tờ gộp, rải xuống phiếu
def _con_lai_tung_phieu(db, hd):
    """[(phiếu, còn lại LAK)] theo THỨ TỰ NGÀY PHIẾU — phiếu cũ trả trước."""
    phieu = db.query(Trip).filter(Trip.invoice_id == hd.id).order_by(Trip.doc_date, Trip.doc_no).all()
    da = da_thu_theo_phieu(db, [p.id for p in phieu])
    ra = []
    for p in phieu:
        k = tinh_phieu(p, _dong_chi(db, p))
        ra.append((p, k["doanh_thu_lak"] - da.get(p.id, 0)))
    return ra


@router.post("/api/hoa-don-gop/{hid}/thu-tien")
def thu_tien(hid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Khách trả một cục cho cả tờ gộp → một tờ PT, rồi PHÂN BỔ xuống từng phiếu theo ngày phiếu.

    Phân bổ để trạng thái từng phiếu vẫn đúng: không có nó thì cả tháng treo "chưa thu" trong khi
    tiền đã về. Tiền trả có thể khác tiền ghi trên hoá đơn, y như thu theo phiếu.
    """
    _lap_duoc(user)
    hd = db.get(Invoice, hid)
    if not hd:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có hoá đơn gộp này."})
    tien = _so(data.get("amount"), "amount")
    if not tien or tien <= 0:
        raise HTTPException(422, {"ma": "SO_TIEN_SAI", "loi": "Số tiền thu phải lớn hơn 0."})
    ma = (data.get("currency") or "").strip().upper()
    if ma not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Tiền tệ phải là một trong %s." % ", ".join(TIEN_TE)})
    con = _con_lai_tung_phieu(db, hd)
    if not con:
        raise HTTPException(409, {"ma": "HOA_DON_TRONG", "loi": "Hoá đơn %s không còn phiếu nào." % hd.inv_no})
    tg = _so(data.get("rate_to_lak"), "rate_to_lak")
    if tg is None:
        tg = ty_gia(con[0][0], ma)             # không gửi thì lấy tỷ giá khoá trên phiếu đầu của tờ
    if ma == "LAK":
        tg = 1.0
    if tg <= 0:
        raise HTTPException(422, {"ma": "TY_GIA_SAI", "loi": "Tỷ giá phải lớn hơn 0."})
    pt = (data.get("method") or "bank").strip()
    if pt not in PHUONG_THUC_THU:
        raise HTTPException(422, {"ma": "PHUONG_THUC_SAI", "loi": "Cách thu phải là %s." % ", ".join(PHUONG_THUC_THU)})
    tien_lak = round(tien * tg)
    con_lai_lak = round(sum(max(v, 0) for _p, v in con))
    if tien_lak > con_lai_lak + LECH_COI_LA_DU and not data.get("cho_thu_du"):
        raise HTTPException(409, {"ma": "THU_QUA_HOA_DON",
                                  "loi": "Hoá đơn %s còn %s LAK mà lần thu này %s LAK. Thu dư thì phải xác nhận."
                                         % (hd.inv_no, con_lai_lak, tien_lak),
                                  "con_lai_lak": con_lai_lak})
    ghi_thu_hoa_don(db, hd, user, tien, ma, tg, pt, ngay=_ngay(data.get("pay_date")),
                    ref=(data.get("ref") or "").strip() or None, note=(data.get("note") or "").strip() or None)
    db.commit()
    return xuat_hd(db, hd, day_du=True)


def ghi_thu_hoa_don(db, hd, user, tien, ma, tg, pt, ngay=None, ref=None, note=None):
    """Ghi MỘT lần khách trả cho tờ gộp và RẢI xuống từng phiếu theo ngày. Dùng chung cho nút thu tiền
    và nút cấn trừ tháng (cách thu `offset`)."""
    ngay = ngay or dt.date.today()
    tien_lak = round(tien * tg)
    con = _con_lai_tung_phieu(db, hd)
    x = InvoicePayment(invoice_id=hd.id, pay_date=ngay, amount=tien, currency=ma, rate_to_lak=tg,
                       amount_lak=tien_lak, method=pt, ref=ref, note=note, by_user=user.full_name)
    db.add(x); db.flush()

    # ---- rải xuống từng phiếu: phiếu cũ trả trước; thừa thì dồn vào phiếu cuối
    con_lai = tien_lak
    chia = []
    for i, (p, thieu) in enumerate(con):
        if con_lai <= 0:
            break
        cuoi = (i == len(con) - 1)
        phan = con_lai if cuoi else min(con_lai, max(round(thieu), 0))
        if phan <= 0:
            continue
        db.add(TripPayment(trip_id=p.id, pay_date=ngay, amount=round(phan / tg, 2), currency=ma, rate_to_lak=tg,
                           amount_lak=phan, method=pt, ref=x.ref,
                           note="Phân bổ từ hoá đơn gộp %s" % hd.inv_no, by_user=user.full_name,
                           invoice_payment_id=x.id))
        chia.append({"doc_no": p.doc_no, "phan_bo_lak": phan})
        con_lai -= phan
    db.flush()
    for p, _v in con:
        _tinh_lai_trang_thai_thu(db, p)
    CT.ghi(db, "PT", nguon_bang="invoice_payments", nguon_id=x.id, ngay=ngay, doi_tuong_loai="khach",
           doi_tuong_ten=hd.customer_name, tien=tien, tien_te=ma, tien_lak=tien_lak, by_user=user.full_name,
           phuong_thuc=pt, mo_ta="Thu tiền khách hoá đơn gộp %s · %s %s" % (hd.inv_no, tien, ma),
           payload={"inv_no": hd.inv_no, "period": hd.period, "rate_to_lak": tg, "method": pt, "ref": x.ref,
                    "hoa_don_ccy": hd.currency, "hoa_don": hd.amount, "hoa_don_lak": hd.amount_lak,
                    "phan_bo": chia})
    return x


@router.delete("/api/hoa-don-thu/{pid}")
def xoa_thu_tien(pid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Xoá một lần thu của tờ gộp — xoá luôn phần đã rải xuống các phiếu, rồi tính lại trạng thái."""
    _lap_duoc(user)
    x = db.get(InvoicePayment, pid)
    if not x:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lần thu này."})
    hd = db.get(Invoice, x.invoice_id)
    c = CT.tim(db, "PT", "invoice_payments", x.id)
    if c is not None and c.da_day:
        raise HTTPException(409, {"ma": "DA_DAY_KE_TOAN",
                                  "loi": "Phiếu thu %s đã đẩy sang kế toán, không xoá được. Nhờ bên kế toán ghi bút toán đảo." % c.so})
    phieu = [db.get(Trip, t) for (t,) in db.query(TripPayment.trip_id)
             .filter(TripPayment.invoice_payment_id == x.id).distinct().all()]
    for d in db.query(TripPayment).filter(TripPayment.invoice_payment_id == x.id).all():
        db.delete(d)
    if c is not None:
        db.delete(c)
    db.delete(x); db.flush()
    for p in phieu:
        if p is not None:
            _tinh_lai_trang_thai_thu(db, p)
    db.commit()
    return xuat_hd(db, hd, day_du=True) if hd else {"ok": True}
