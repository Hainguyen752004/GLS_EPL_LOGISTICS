# -*- coding: utf-8 -*-
"""Nhà cung cấp — ຕິດຕາມຜູ້ສະໜອງ. Phí chip Lào/Việt, lốp, cầu đường, trạm dầu Việt Nam ghi nợ…

DANH MỤC nhà cung cấp (tên, khoản mục, mã tài khoản, kỳ trả, khách được cấn trừ) ở đây — phiếu (dòng dầu ghi nợ tại
trạm), tất toán tài xế (khoản trả nhà cung cấp theo đợt không phải tiền tài xế) và Bãi cần nó.

Từ 28/09 (đợt 7d) PHẦN TIỀN ở trang kế toán (Tiền vận chuyển → Theo dõi nhà cung cấp): các lần trả (supplier_payments),
tờ PC_NCC, còn nợ. Bên này vẫn TÍNH phần phát sinh từ phiếu (tổng các dòng chi EPL ứng có khoản mục / trạm của nhà cung
cấp đó) cho trang kế toán hỏi qua đường máy (/api/lien-thong/ncc); nợ phải trả = phát sinh − đã trả tính ở bên đó.
Các đường /api/suppliers/{id}/payments trả 409 "đã dời".
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Supplier, Trip, TripExpense
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi
from services.tinh_toan import MAC_DINH, tien_dong

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Trả nhà cung cấp, công nợ nhà cung cấp nay làm ở trang kế toán (Tiền vận chuyển → Theo dõi nhà cung cấp)."}


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


def _tong_ngay_lo(db, cac_ngay):
    """Như _tong_thang cho NHIỀU NGÀY trong một lượt SQL (gom theo ngày lập phiếu) — cùng thứ tự `cac_ngay`."""
    tien = _tien_lak_sql()
    goc = (db.query(TripExpense).join(Trip, Trip.id == TripExpense.trip_id)
           .filter(TripExpense.paid_by_epl.is_(True), Trip.doc_date >= min(cac_ngay), Trip.doc_date <= max(cac_ngay)))
    ra = {d: {"ma": {}, "khoan": {}} for d in cac_ngay}
    for d, sid, n, x in (goc.filter(TripExpense.supplier_id.isnot(None), TripExpense.ghi_no.is_(True))
                         .with_entities(Trip.doc_date, TripExpense.supplier_id, func.count(TripExpense.id), func.sum(tien))
                         .group_by(Trip.doc_date, TripExpense.supplier_id)):
        if d in ra:
            ra[d]["ma"][sid] = [n, float(x or 0)]
    for d, k, n, x, g in (goc.filter(TripExpense.supplier_id.is_(None), TripExpense.item_key.isnot(None))
                          .with_entities(Trip.doc_date, TripExpense.item_key, func.count(TripExpense.id), func.sum(tien),
                                         func.sum(case((TripExpense.ghi_no.is_(True), tien), else_=0.0)))
                          .group_by(Trip.doc_date, TripExpense.item_key)):
        if d in ra:
            ra[d]["khoan"][k] = [n, float(x or 0), float(g or 0)]
    return [ra[d] for d in cac_ngay]


def _tong_thang_lo(db, cac_thang):
    """_tong_thang cho NHIỀU tháng trong một lượt SQL (gom theo tháng) — trả danh sách cùng thứ tự `cac_thang`."""
    tien = _tien_lak_sql()
    thg = func.date_trunc("month", Trip.doc_date)
    goc = (db.query(TripExpense).join(Trip, Trip.id == TripExpense.trip_id)
           .filter(TripExpense.paid_by_epl.is_(True), Trip.doc_date >= min(cac_thang),
                   Trip.doc_date < dt.date(max(cac_thang).year + (max(cac_thang).month == 12), max(cac_thang).month % 12 + 1, 1)))
    ra = {d: {"ma": {}, "khoan": {}} for d in cac_thang}
    for t, sid, n, x in (goc.filter(TripExpense.supplier_id.isnot(None), TripExpense.ghi_no.is_(True))
                         .with_entities(thg, TripExpense.supplier_id, func.count(TripExpense.id), func.sum(tien))
                         .group_by(thg, TripExpense.supplier_id)):
        if t.date() in ra:
            ra[t.date()]["ma"][sid] = [n, float(x or 0)]
    for t, k, n, x, g in (goc.filter(TripExpense.supplier_id.is_(None), TripExpense.item_key.isnot(None))
                          .with_entities(thg, TripExpense.item_key, func.count(TripExpense.id), func.sum(tien),
                                         func.sum(case((TripExpense.ghi_no.is_(True), tien), else_=0.0)))
                          .group_by(thg, TripExpense.item_key)):
        if t.date() in ra:
            ra[t.date()]["khoan"][k] = [n, float(x or 0), float(g or 0)]
    return [ra[d] for d in cac_thang]


def _tong_khong_ngay(db):
    """Như _tong_thang, cho các phiếu CHƯA CÓ ngày lập (doc_date trống)."""
    tien = _tien_lak_sql()
    goc = (db.query(TripExpense).join(Trip, Trip.id == TripExpense.trip_id)
           .filter(TripExpense.paid_by_epl.is_(True), Trip.doc_date.is_(None)))
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
    """Số dòng · phát sinh · ghi nợ của CẢ danh sách (đã trả ở trang kế toán từ đợt 7d). Nợ nhà cung cấp là số CỘNG DỒN từ trước tới nay, nên
    càng dùng lâu càng nhiều dòng: cộng theo từng tháng (mỗi tháng đệm riêng) rồi gộp — mỗi lần mở chỉ phải cộng lại
    tháng nào có dòng chi vừa đổi (thường là tháng này), không phải cả mấy năm."""
    from services import dem_bao_cao as DEM
    theo_ma, theo_khoan = defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0, 0.0])
    lo, hi = db.query(func.min(Trip.doc_date), func.max(Trip.doc_date)).one()
    ngay = [lo + dt.timedelta(days=i) for i in range((hi - lo).days + 1)] if lo else []
    # Đệm theo NGÀY (4 năm ≈ 1.460 ngày, một câu đọc phiên bản cho cả nhóm): ghi vào phiếu hôm nay thì chỉ hôm nay tính lại.
    # Ngày nào còn thiếu thì tính MỘT LƯỢT cho cả nhóm, chứ không từng ngày một.
    viec = [(("ncc-ngay", d.isoformat()), [d.isoformat()], None) for d in ngay]
    # phiếu KHÔNG CÓ NGÀY không thuộc tháng nào nhưng nợ nhà cung cấp là số cộng dồn — vẫn phải tính (luôn tính mới,
    # thường không có dòng nào nên câu này rất nhẹ)
    khong_ngay = _tong_khong_ngay(db)
    for g in DEM.lay_nhieu(db, viec, tinh_lo=lambda thieu: _tong_ngay_lo(db, [ngay[i] for i in thieu])) + [khong_ngay]:
        for sid, (n, x) in g["ma"].items():
            theo_ma[sid][0] += n; theo_ma[sid][1] += x
        for k, (n, x, y) in g["khoan"].items():
            o = theo_khoan[k]; o[0] += n; o[1] += x; o[2] += y
    ra = {}
    for x in cac_ncc:
        n1, t1 = theo_ma.get(x.id, (0, 0.0)) if x.id in theo_ma else (0, 0.0)
        n2, t2, g2 = theo_khoan[x.item_key] if (x.item_key and x.item_key in theo_khoan) else (0, 0.0, 0.0)
        ra[x.id] = {"so_dong": n1 + n2, "phat_sinh": t1 + t2, "ghi_no": t1 + g2}
    return ra


def _xuat(db, s, tong=None, kem_tien=False):
    """`tong` (từ _tong_lo) là số đã cộng sẵn cho cả danh sách — có thì không hỏi DB từng nhà cung cấp. `kem_tien`: phát
    sinh và ghi nợ (LAK) — chỉ đường máy của trang kế toán dùng; màn danh mục bên này không có cột tiền."""
    if tong is not None:
        n, phat_sinh, ghi_no = tong["so_dong"], tong["phat_sinh"], tong["ghi_no"]
    else:
        dong = _dong_cua(db, s)
        n = len(dong)
        phat_sinh = sum(tien_dong(p, d) for d, p in dong)
        ghi_no = sum(tien_dong(p, d) for d, p in dong if d.ghi_no)
    r = {"id": s.id, "name": s.name, "item_key": s.item_key, "acct_code": s.acct_code,
         "payment_term": s.payment_term, "note": s.note, "active": s.active,
         "customer_id": s.customer_id, "customer_name": s.customer_name, "so_dong": n}
    if kem_tien:
        r.update({"phat_sinh_lak": round(phat_sinh), "ghi_no_lak": round(ghi_no)})
    return r


def ds_tien(db):
    """Danh mục + phát sinh / ghi nợ từ phiếu, cho màn Theo dõi nhà cung cấp bên trang kế toán (đường máy)."""
    cac = db.query(Supplier).order_by(Supplier.active.desc(), Supplier.name).all()
    tong = _tong_lo(db, cac)
    return [_xuat(db, s, tong[s.id], kem_tien=True) for s in cac]


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
        # Bãi không thấy mã tài khoản (anh Khampla A2); chủ dự án chốt 23/09: màn Theo dõi NCC của Bãi giữ danh sách ·
        # số dòng · kỳ trả. Tiền (phát sinh, đã trả, còn nợ) ở trang kế toán từ đợt 7d — màn này không còn cột tiền.
        for r in ra:
            r.pop("acct_code", None)
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


# ---------------------------------------------------------------- các lần trả: đã dời (đợt 7d)
@router.get("/api/suppliers/{sid}/payments")
def cac_lan_tra(sid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/suppliers/{sid}/payments")
def tra(sid: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)
