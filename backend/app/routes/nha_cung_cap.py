# -*- coding: utf-8 -*-
"""Theo dõi nhà cung cấp — ຕິດຕາມຜູ້ສະໜອງ. Phí chip Lào/Việt, lốp, cầu đường… trả theo tháng.

Nợ phải trả = tổng các dòng chi trên phiếu có khoản mục của nhà cung cấp đó (và EPL ứng)
− các lần đã thanh toán. Tính lại mỗi lần gọi từ phiếu, không giữ số dư riêng.
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Supplier, SupplierPayment, Trip, TripExpense
from services import chung_tu as CT
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi
from services.tinh_toan import MAC_DINH, tien_dong

router = APIRouter()


def _dong_cua(db, s, dau=None, sau=None):
    """Các dòng chi thuộc về nhà cung cấp này.

    Hai đường vào, cố ý khác nhau:
      · dòng **ghi rõ nhà cung cấp** (`supplier_id`) — chỉ tính khi **GHI NỢ tại trạm** (C5.1): tài xế
        đổ dầu ở Việt Nam mà chưa trả tiền. Tài xế đã trả tiền mặt tại trạm thì EPL không nợ ai cả.
      · dòng chỉ có **khoản mục** trùng (`item_key`, ví dụ phí chip) — cách cũ, giữ nguyên.
    """
    # Lọc NGAY TRONG SQL (24/09, dữ liệu cả năm): trước đây kéo MỌI dòng chi EPL ứng của mọi phiếu (cả năm ~2 triệu
    # dòng) về rồi mới bỏ bớt bằng Python — cho từng nhà cung cấp một.
    q = (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
         .filter(TripExpense.paid_by_epl.is_(True), _cua_ncc(s)))
    if dau is not None:
        q = q.filter(Trip.doc_date >= dau, Trip.doc_date < sau)
    return q.all()


def _cua_ncc(s):
    """Điều kiện SQL "dòng chi này thuộc nhà cung cấp s" — đúng hai đường vào mô tả ở _dong_cua."""
    theo_ma = and_(TripExpense.supplier_id == s.id, TripExpense.ghi_no.is_(True))
    if not s.item_key:
        return theo_ma
    return or_(theo_ma, and_(TripExpense.supplier_id.is_(None), TripExpense.item_key == s.item_key))


def _tien_lak_sql():
    """tien_dong (services/tinh_toan) viết bằng SQL: số lượng × đơn giá × tỷ giá KHOÁ TRÊN PHIẾU; phiếu không ghi tỷ
    giá (hay ghi 0) thì lấy MAC_DINH; mã tiền lạ tính như LAK — y như ty_gia / chuan_tien."""
    ma = func.upper(func.trim(func.coalesce(TripExpense.currency, "")))
    ty = case((ma == "USD", func.coalesce(func.nullif(Trip.rate_usd, 0), MAC_DINH["USD"])),
              (ma == "THB", func.coalesce(func.nullif(Trip.rate_thb, 0), MAC_DINH["THB"])),
              (ma == "VND", func.coalesce(func.nullif(Trip.rate_vnd, 0), MAC_DINH["VND"])),
              (ma == "CNY", func.coalesce(func.nullif(Trip.rate_cny, 0), MAC_DINH["CNY"])),
              else_=1.0)
    return func.coalesce(TripExpense.qty, 0) * func.coalesce(TripExpense.unit_price, 0) * ty


def _tong_thang(db, dau, sau):
    """Cộng dòng chi EPL ứng của MỘT tháng (theo ngày phiếu) cho mọi nhà cung cấp và mọi khoản mục:
    {"ma": {supplier_id: [số dòng, tiền]}, "khoan": {item_key: [số dòng, tiền, tiền ghi nợ]}} — không phụ thuộc danh mục
    nhà cung cấp, nên đệm theo tháng được (services/dem_bao_cao): tháng cũ không đổi thì không cộng lại."""
    tien = _tien_lak_sql()
    goc = (db.query(TripExpense).join(Trip, Trip.id == TripExpense.trip_id)
           .filter(TripExpense.paid_by_epl.is_(True), Trip.doc_date >= dau, Trip.doc_date < sau))
    ma = {sid: [n, float(t or 0)] for sid, n, t in (
        goc.filter(TripExpense.supplier_id.isnot(None), TripExpense.ghi_no.is_(True))
        .with_entities(TripExpense.supplier_id, func.count(TripExpense.id), func.sum(tien)).group_by(TripExpense.supplier_id))}
    khoan = {k: [n, float(t or 0), float(g or 0)] for k, n, t, g in (
        goc.filter(TripExpense.supplier_id.is_(None), TripExpense.item_key.isnot(None))
        .with_entities(TripExpense.item_key, func.count(TripExpense.id), func.sum(tien),
                       func.sum(case((TripExpense.ghi_no.is_(True), tien), else_=0.0)))
        .group_by(TripExpense.item_key))}
    return {"ma": ma, "khoan": khoan}


def _tong_lo(db, cac_ncc):
    """Số dòng · phát sinh · ghi nợ · đã trả của CẢ danh sách. Nợ nhà cung cấp là số CỘNG DỒN từ trước tới nay, nên
    càng dùng lâu càng nhiều dòng: cộng theo từng tháng (mỗi tháng đệm riêng) rồi gộp — mỗi lần mở chỉ phải cộng lại
    tháng nào có dòng chi vừa đổi (thường là tháng này), không phải cả mấy năm."""
    from services import dem_bao_cao as DEM
    theo_ma, theo_khoan = defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0, 0.0])
    lo, hi = db.query(func.min(Trip.doc_date), func.max(Trip.doc_date)).one()
    if lo:
        t, t_cuoi = lo.year * 12 + lo.month - 1, hi.year * 12 + hi.month - 1
        while t <= t_cuoi:
            dau, sau = dt.date(t // 12, t % 12 + 1, 1), dt.date((t + 1) // 12, (t + 1) % 12 + 1, 1)
            g = DEM.lay(db, ("ncc-thang", dau.isoformat()), [dau.strftime("%Y-%m")],
                        lambda: _tong_thang(db, dau, sau), theo_ngay=False)
            for sid, (n, x) in g["ma"].items():
                theo_ma[sid][0] += n; theo_ma[sid][1] += x
            for k, (n, x, y) in g["khoan"].items():
                o = theo_khoan[k]; o[0] += n; o[1] += x; o[2] += y
            t += 1
    tra = {sid: float(t or 0) for sid, t in (db.query(SupplierPayment.supplier_id, func.sum(SupplierPayment.amount_lak))
                                             .group_by(SupplierPayment.supplier_id))}
    ra = {}
    for x in cac_ncc:
        n1, t1 = theo_ma.get(x.id, (0, 0.0)) if x.id in theo_ma else (0, 0.0)
        n2, t2, g2 = theo_khoan[x.item_key] if (x.item_key and x.item_key in theo_khoan) else (0, 0.0, 0.0)
        ra[x.id] = {"so_dong": n1 + n2, "phat_sinh": t1 + t2, "ghi_no": t1 + g2, "da_tra": tra.get(x.id, 0.0)}
    return ra


def _xuat(db, s, tong=None):
    """`tong` (từ _tong_lo) là số đã cộng sẵn cho cả danh sách — có thì không hỏi DB từng nhà cung cấp."""
    if tong is not None:
        n, phat_sinh, ghi_no, da_tra = tong["so_dong"], tong["phat_sinh"], tong["ghi_no"], tong["da_tra"]
    else:
        dong = _dong_cua(db, s)
        n = len(dong)
        phat_sinh = sum(tien_dong(p, d) for d, p in dong)
        ghi_no = sum(tien_dong(p, d) for d, p in dong if d.ghi_no)
        da_tra = sum(x.amount_lak or 0 for x in db.query(SupplierPayment).filter(SupplierPayment.supplier_id == s.id).all())
    return {"id": s.id, "name": s.name, "item_key": s.item_key, "acct_code": s.acct_code,
            "payment_term": s.payment_term, "note": s.note, "active": s.active,
            "customer_id": s.customer_id, "customer_name": s.customer_name,
            "so_dong": n, "phat_sinh_lak": round(phat_sinh), "ghi_no_lak": round(ghi_no),
            "da_tra_lak": round(da_tra), "con_no_lak": round(phat_sinh - da_tra)}


def _ap_khach(db, s, data):
    """Trạm dầu Việt Nam cuối tháng cấn trừ vào cước của khách nào (C5.1)."""
    if "customer_id" not in data:
        return
    kh = db.get(Customer, str(data["customer_id"])) if data["customer_id"] else None
    if data["customer_id"] and not kh:
        raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    s.customer_id, s.customer_name = (kh.id, kh.name) if kh else (None, None)


@router.get("/api/suppliers")
def ds(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    cac = db.query(Supplier).order_by(Supplier.active.desc(), Supplier.name).all()
    tong = _tong_lo(db, cac)
    ra = [_xuat(db, s, tong[s.id]) for s in cac]
    if not thay_tien_chi(user.role):
        # Bãi không thấy tiền, không thấy mã tài khoản (anh Khampla A2); chủ dự án chốt 23/09: màn Theo dõi NCC
        # của Bãi giữ danh sách · số dòng · kỳ trả, bỏ cột tiền. Trả NCC là việc kế toán và quỹ.
        for r in ra:
            for k in ("phat_sinh_lak", "ghi_no_lak", "da_tra_lak", "con_no_lak", "acct_code"):
                r.pop(k, None)
    return ra


@router.post("/api/suppliers")
def them(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("expacct"))):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Nhà cung cấp phải có tên."})
    s = Supplier(name=data["name"].strip(), item_key=data.get("item_key"), acct_code=data.get("acct_code"),
                 payment_term=data.get("payment_term") or "t_monthly", note=data.get("note"))
    _ap_khach(db, s, data)
    db.add(s); db.commit(); db.refresh(s)
    return _xuat(db, s)


@router.put("/api/suppliers/{sid}")
def sua(sid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(can_vai("expacct"))):
    s = db.get(Supplier, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có nhà cung cấp này."})
    for k in ("name", "item_key", "acct_code", "payment_term", "note", "active"):
        if k in data:
            setattr(s, k, data[k].strip() if isinstance(data[k], str) else data[k])
    _ap_khach(db, s, data)
    db.commit(); db.refresh(s)
    return _xuat(db, s)


@router.get("/api/suppliers/{sid}/payments")
def cac_lan_tra(sid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if not thay_tien_chi(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Bãi không xem các lần trả nhà cung cấp."})
    return [{"id": x.id, "pay_date": x.pay_date.isoformat(), "amount_lak": x.amount_lak, "note": x.note, "by_user": x.by_user}
            for x in db.query(SupplierPayment).filter(SupplierPayment.supplier_id == sid)
            .order_by(SupplierPayment.pay_date.desc()).all()]


@router.post("/api/suppliers/{sid}/payments")
def tra(sid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(can_vai("expacct", "cash", "treasury"))):
    s = db.get(Supplier, sid)
    if not s:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có nhà cung cấp này."})
    try:
        tien = float(str(data.get("amount_lak")).replace(",", ""))
    except (TypeError, ValueError):
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số tiền phải là số."})
    if tien <= 0:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Số tiền phải lớn hơn 0."})
    try:
        ngay = dt.date.fromisoformat(str(data.get("pay_date") or dt.date.today())[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD."})
    tra_ncc = SupplierPayment(supplier_id=s.id, pay_date=ngay, amount_lak=tien, note=data.get("note"), by_user=user.full_name)
    db.add(tra_ncc); db.flush()
    CT.ghi(db, "PC_NCC", nguon_bang="supplier_payments", nguon_id=tra_ncc.id, ngay=ngay, doi_tuong_loai="ncc", phuong_thuc="cash",
           doi_tuong_ten=s.name, tien=tien, tien_te="LAK", by_user=user.full_name,
           mo_ta="Trả nhà cung cấp %s%s" % (s.name, (" · " + data["note"]) if data.get("note") else ""),
           payload={"supplier_id": s.id, "item_key": s.item_key, "acct_code": s.acct_code})
    db.commit()
    return _xuat(db, s)
