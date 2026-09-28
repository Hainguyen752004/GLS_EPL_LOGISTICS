# -*- coding: utf-8 -*-
"""DOANH THU — phần trang điều xe còn giữ cho hoá đơn / thu tiền ở TRANG KẾ TOÁN (đợt 7a, 28/09).

Hoá đơn từng phiếu, hoá đơn gộp tháng, sổ thu tiền, in phiếu thu dời sang trang kế toán. Hai thứ vẫn ở đây vì chúng là
của PHIẾU:

  1. **Số cước của phiếu** — doanh thu tính từ tấn, đơn giá, cách tính cước, tỷ giá khoá trên phiếu (services/tinh_toan
     → tinh_phieu). Trang kế toán hỏi số này khi xuất hoá đơn, không tính lại theo cách khác — để tờ hoá đơn và phiếu
     không bao giờ nói hai con số.
  2. **Bản chép trạng thái** trên phiếu: đã xuất hoá đơn, số tờ gộp, tổng đã thu, ngày thu gần nhất, trạng thái thu.
     Trang kế toán ghi sang mỗi lần xuất / huỷ hoá đơn, thu / xoá lần thu. Nhờ bản chép, khoá phiếu, chặn mở khoá, chặn
     báo hỏng khi đã thu đủ và mọi báo cáo bên này chạy như cũ mà không phải hỏi sang. Trang điều xe tắt thì trang kế
     toán CHẶN việc ghi (chủ dự án chốt 28/09: không xếp hàng gửi sau), nên bản chép không bao giờ lệch.

Các đường máy ở routes/lien_thong.py → /api/lien-thong/doanh-thu/….
"""
import datetime as dt

from fastapi import HTTPException

from models import TIEN_TE, Customer, Trip, TripExpense, TripSection
from services.tinh_toan import tinh_phieu, ty_gia


def _ngay(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


def _thang(v):
    s = str(v or "")[:7] or dt.date.today().strftime("%Y-%m")
    try:
        dt.date.fromisoformat(s + "-01")
    except ValueError:
        raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải dạng YYYY-MM, nhận '%s'." % v})
    return s


def _khoang(period):
    dau = dt.date.fromisoformat(period + "-01")
    sau = dt.date(dau.year + (1 if dau.month == 12 else 0), 1 if dau.month == 12 else dau.month + 1, 1)
    return dau, sau


def so_lieu(db, p, dong=None, muc_ii=None, kh=None):
    """Số cước và bản chép trạng thái của MỘT phiếu — đúng các ô màn hoá đơn bên trang kế toán cần.
    `dong` / `muc_ii` / `kh` nạp sẵn (danh sách cả tháng) thì không hỏi DB từng phiếu."""
    from routes.phieu import _dong_chi, _muc_cua
    k = tinh_phieu(p, _dong_chi(db, p) if dong is None else dong, float(p.collected_lak or 0))
    if muc_ii is None:
        muc_ii = _muc_cua(db, p)["trans"].status
    if kh is None:
        kh = db.get(Customer, p.customer_id) if p.customer_id else None
    return {"id": p.id, "doc_no": p.doc_no, "kind": p.kind, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "customer_id": p.customer_id, "customer_name": p.customer_name, "company": p.company,
            "inv_mode": (kh.invoice_mode if kh else None) or "phieu",
            "truck_no": p.truck_no, "driver_name": p.driver_name, "origin": p.origin, "destination": p.destination,
            "ore_bill_no": p.ore_bill_no, "weight_origin": p.weight_origin, "weight_dest": p.weight_dest,
            "tan_tinh": k["tan_tinh"], "price": p.price, "cach_tinh": k["cach_tinh"], "ccy": k["ccy"],
            "doanh_thu": k["doanh_thu"], "doanh_thu_lak": k["doanh_thu_lak"],
            "da_thu_lak": round(float(p.collected_lak or 0)), "con_lai_lak": round(k["doanh_thu_lak"] - float(p.collected_lak or 0)),
            "ty_gia": {m: ty_gia(p, m) for m in TIEN_TE},
            "trans_status": muc_ii, "locked": bool(p.locked), "transport_status": p.transport_status,
            "invoiced": bool(p.invoiced), "invoice_id": p.invoice_id, "inv_no": p.inv_no,
            "invoiced_date": p.invoiced_date.isoformat() if p.invoiced_date else None,
            "finance_status": p.finance_status}


def ds_phieu(db, q="", locked=None, invoiced=None, gioi_han=50):
    """Ô chọn phiếu của màn Hoá đơn vận chuyển bên trang kế toán: 50 phiếu mới nhất, hoặc tìm theo số phiếu / số xe /
    khách trên TOÀN BỘ phiếu (dữ liệu cả năm) — như ô chọn phiếu bên này."""
    from sqlalchemy import or_
    qs = db.query(Trip)
    if q:
        t = "%%%s%%" % q.strip()
        qs = qs.filter(or_(Trip.doc_no.ilike(t), Trip.truck_no.ilike(t), Trip.customer_name.ilike(t), Trip.plate_head.ilike(t)))
    if locked is not None:
        qs = qs.filter(Trip.locked.is_(bool(locked)))
    if invoiced is not None:
        qs = qs.filter(Trip.invoiced.is_(bool(invoiced)))
    ds = qs.order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).limit(max(1, min(int(gioi_han or 50), 200))).all()
    return [{"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
             "truck_no": p.truck_no, "company": p.company, "customer_name": p.customer_name, "locked": bool(p.locked),
             "invoiced": bool(p.invoiced), "invoice_id": p.invoice_id, "inv_no": p.inv_no,
             "finance_status": p.finance_status} for p in ds]


def _chan(p, ma, chu):
    raise HTTPException(409, {"ma": ma, "loi": chu, "trip_id": p.id, "doc_no": p.doc_no})


def kiem_xuat(db, p, kieu):
    """Phiếu lên hoá đơn được không. `kieu`: "phieu" (hoá đơn riêng từng phiếu) · "thang" (vào tờ gộp tháng).
    Đúng các điều kiện bên này đã chặn trước khi dời: kiểm xong mục II, đã KHOÁ, chưa lên hoá đơn, đúng cách xuất
    hoá đơn của khách."""
    from routes.phieu import _muc_cua
    if p.invoiced or p.invoice_id:
        _chan(p, "DA_HOA_DON", "Phiếu %s đã xuất hoá đơn rồi%s." % (p.doc_no, (" (tờ gộp %s)" % p.inv_no) if p.inv_no else ""))
    if _muc_cua(db, p)["trans"].status != "verified":
        _chan(p, "CHUA_KIEM", "Mục II (vận chuyển) của phiếu %s phải được kiểm xong trước khi xuất hoá đơn." % p.doc_no)
    if not p.locked:
        _chan(p, "CHUA_KHOA", "Kế toán phải kiểm lại và KHOÁ phiếu %s (bước 14) rồi mới xuất hoá đơn." % p.doc_no)
    kh = db.get(Customer, p.customer_id) if p.customer_id else None
    thang = kh is not None and kh.invoice_mode == "thang"
    if kieu == "phieu" and thang:
        _chan(p, "GOP_THANG", "Khách %s xuất hoá đơn GỘP THÁNG — cuối tháng dùng \"Gộp hoá đơn tháng\", không xuất riêng từng phiếu." % kh.name)
    if kieu == "thang" and not thang:
        _chan(p, "KHONG_GOP_THANG", "Khách của phiếu %s đang để mỗi phiếu một hoá đơn, không vào tờ gộp tháng." % p.doc_no)


def cho_gop(db, period="", customer_id=""):
    """Khách nào đang có phiếu chờ gộp trong tháng — mỗi khách tách theo TIỀN CƯỚC (một tờ chỉ mang một loại tiền:
    khách ký hai tuyến, tuyến này USD tuyến kia Kíp, thì cuối tháng là hai tờ)."""
    period = _thang(period)
    dau, sau = _khoang(period)
    if customer_id:
        kh = db.get(Customer, customer_id)
        if not kh:
            raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
        if kh.invoice_mode != "thang":
            raise HTTPException(409, {"ma": "KHONG_GOP_THANG",
                                      "loi": "Khách %s đang để mỗi phiếu một hoá đơn. Muốn gộp tháng thì đổi cách xuất hoá đơn trong danh mục khách hàng." % kh.name})
    q = (db.query(Trip).join(Customer, Customer.id == Trip.customer_id)
         .filter(Customer.invoice_mode == "thang", Trip.locked.is_(True), Trip.invoice_id.is_(None),
                 Trip.invoiced.is_(False), Trip.doc_date >= dau, Trip.doc_date < sau))
    if customer_id:
        q = q.filter(Trip.customer_id == customer_id)
    ds_p = q.order_by(Trip.doc_date, Trip.doc_no).all()
    ma = [p.id for p in ds_p]
    muc_ii = {t: st for t, st in (db.query(TripSection.trip_id, TripSection.status)
                                  .filter(TripSection.trip_id.in_(ma or [""]), TripSection.section == "trans"))}
    dong = {}
    for d in (db.query(TripExpense).filter(TripExpense.trip_id.in_(ma or [""]))
              .order_by(TripExpense.trip_id, TripExpense.section, TripExpense.line_no)):
        dong.setdefault(d.trip_id, []).append(d)
    kh = {c.id: c for c in db.query(Customer).filter(Customer.id.in_({p.customer_id for p in ds_p} or {""}))}
    nhom = {}
    for p in ds_p:
        if muc_ii.get(p.id) != "verified":
            continue
        r = so_lieu(db, p, dong=dong.get(p.id, []), muc_ii="verified", kh=kh.get(p.customer_id))
        if (r["doanh_thu"] or 0) <= 0:
            continue
        o = nhom.setdefault((p.customer_id, r["ccy"]), {"customer_id": p.customer_id, "customer_name": p.customer_name,
                                                        "ccy": r["ccy"], "period": period, "phieu": [], "tong": 0.0, "tong_lak": 0.0})
        o["phieu"].append(r)
        o["tong"] += r["doanh_thu"]; o["tong_lak"] += r["doanh_thu_lak"]
    ds = []
    for o in nhom.values():
        o["tong"] = round(o["tong"], 2) if o["ccy"] not in ("LAK", "VND") else round(o["tong"])
        o["tong_lak"] = round(o["tong_lak"])
        o["so_phieu"] = len(o["phieu"])
        ds.append(o)
    ds.sort(key=lambda o: (o["customer_name"] or "", o["ccy"]))
    return {"period": period, "ds": ds}


def _khoa_phieu(db, trip_ids):
    """Nạp các phiếu KHOÁ DÒNG (FOR UPDATE) theo đúng thứ tự gửi — hai người cùng bấm thì người sau chờ, không ghi đè."""
    ids = [str(i) for i in (trip_ids or []) if i]
    if not ids:
        raise HTTPException(422, {"ma": "THIEU_PHIEU", "loi": "Chưa gửi phiếu nào."})
    co = {p.id: p for p in db.query(Trip).filter(Trip.id.in_(ids)).with_for_update().all()}
    thieu = [i for i in ids if i not in co]
    if thieu:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu %s bên trang điều xe." % ", ".join(thieu)})
    return [co[i] for i in ids]


def danh_dau_hoa_don(db, user, trip_ids, kieu, invoice_id=None, inv_no=None, ngay=None):
    """Trang kế toán vừa lập hoá đơn cho các phiếu này → ghi bản chép "đã xuất hoá đơn". Kiểm lại điều kiện ngay lúc
    ghi (dòng đã khoá) — giữa lúc bên kia đọc số và lúc ghi, phiếu có thể đã bị mở khoá hoặc lên tờ khác."""
    from routes.phieu import _ghi_log
    ds = _khoa_phieu(db, trip_ids)
    for p in ds:
        kiem_xuat(db, p, kieu)
    ngay = _ngay(ngay) or dt.date.today()
    for p in ds:
        p.invoiced = True
        p.invoice_id = invoice_id or None
        p.inv_no = inv_no or None
        p.invoiced_date = ngay
        _ghi_log(db, p, user, "a_invoice")
    db.commit()
    return [so_lieu(db, p) for p in ds]


def bo_hoa_don(db, user, trip_ids):
    """Trang kế toán huỷ hoá đơn (gộp nhầm tháng) hoặc lưu hỏng sau khi đã ghi sang → phiếu về "chưa xuất hoá đơn".
    Phiếu còn tiền đã thu thì không bỏ: bên đó phải xoá các lần thu trước."""
    ds = _khoa_phieu(db, trip_ids)
    for p in ds:
        if (p.collected_lak or 0) > 0:
            _chan(p, "DA_THU", "Phiếu %s đã có tiền thu — xoá các lần thu trước khi huỷ hoá đơn." % p.doc_no)
    for p in ds:
        p.invoiced, p.invoice_id, p.inv_no, p.invoiced_date = False, None, None, None
    db.commit()
    return [so_lieu(db, p) for p in ds]


def ghi_da_thu(db, user, cac_dong, nhat_ky=None):
    """Bản chép TỔNG ĐÃ THU của từng phiếu sau một lần thu / xoá lần thu bên trang kế toán:
    [{trip_id, collected_lak, last_paid_date}]. Trạng thái thu tính lại ở đây theo đúng một luật như trước (so tổng đã
    thu với doanh thu quy Kíp của phiếu). `nhat_ky`: "thu" → ghi nhật ký phiếu fin_<trạng thái>; "xoa" → fin_undo;
    None → không ghi (thu theo tờ gộp rải xuống, như trước)."""
    from routes.phieu import _ghi_log, _tinh_lai_trang_thai_thu
    theo_ma = {str(d.get("trip_id")): d for d in (cac_dong or []) if d.get("trip_id")}
    ds = _khoa_phieu(db, list(theo_ma))
    ra = {}
    for p in ds:
        d = theo_ma[p.id]
        try:
            lak = float(d.get("collected_lak") or 0)
        except (TypeError, ValueError):
            raise HTTPException(422, {"ma": "SO_SAI", "loi": "collected_lak của phiếu %s phải là số." % p.doc_no})
        if not p.invoiced and lak > 0:
            _chan(p, "CHUA_HOA_DON", "Phiếu %s chưa xuất hoá đơn thì chưa ghi thu tiền." % p.doc_no)
        p.collected_lak = round(lak)
        p.last_paid_date = _ngay(d.get("last_paid_date"))
        _tinh_lai_trang_thai_thu(db, p)
        if nhat_ky == "thu":
            _ghi_log(db, p, user, "fin_%s" % p.finance_status)
        elif nhat_ky == "xoa":
            _ghi_log(db, p, user, "fin_undo")
        ra[p.id] = p.finance_status
    db.commit()
    return ra
