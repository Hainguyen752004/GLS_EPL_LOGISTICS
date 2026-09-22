# -*- coding: utf-8 -*-
"""Phiếu xuất xe đi vận chuyển — ໃບເບີກລົດອອກໄປຂົນສົ່ງ. Trái tim của bản Lào.

Một phiếu = một tờ giấy họ đang dùng: sáu mục I–VI, mỗi mục một trạng thái duyệt riêng,
ai làm gì ghi vào nhật ký. Không có Trip, không có DO, không có báo giá.

Hai quy tắc từ tài liệu quy trình của họ ("EPL flow of Logistics") và lời anh chủ dự án:
  · CÓ TRONG KHO → phiếu XUẤT KHO (định khoản …/371); KHÔNG CÓ → phiếu CHI mua ngoài (…/402).
    Nhiên liệu đổ ở kho Thà Bốc → khi kế toán kho GHI SỔ mục III thì tự sinh dòng xuất kho.
    Phụ tùng lấy từ kho khi sửa xe → trừ tồn kho ngay lúc khai.
  · Xe nhà định khoản 625/… và 614/…; xe liên kết định khoản 4022/… (chi hộ nhà thầu phụ).
"""
import datetime as dt
import mimetypes
import os
import re

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (GoodsMove, Invoice, Owner, TripAttachment, TripGoods, TripPayment, ma_moi, CHUOI, LOAI_DO, LOAI_SU_CO, MUC, MUC_CHI,
                    CACH_TINH_CUOC, PHUONG_THUC_THU, SU_KIEN, TIEN_TE, TRANG_THAI_TAI_CHINH, TRANG_THAI_VAN_CHUYEN,
                    Customer, Driver, ExchangeRate, FuelMove, FuelPlace, Part, PartMove, Route, RouteStop, Trip,
                    TripEvent, TripExpense, TripLog, TripSection, Vehicle)
from services.bao_mat import doc_phien, nguoi_hien_tai
from services.phan_quyen import chuyen_muc, duoc_sua_muc, duoc_sua_tien
from routes.danh_muc import tim_gia
from services.tinh_toan import chuan_tien, doi as doi_tien, lam_tron, tien_cuoc, tien_dong, tien_thue_xe, tinh_phieu, ty_gia
from services import kho_hang as KH
from services import chung_tu as CT
from routes import the_cao_toc as THE

router = APIRouter()

# Khoản mục chuẩn của từng mục chi — chép từ Excel; người dùng vẫn gõ tên tự do được.
KHOAN_MUC = {
    "fuel":   ["diesel"],
    "travel": ["x_water", "x_vn", "x_chip_lao", "x_chip_vn", "x_bridge", "x_toll", "x_trip",
               "x_phone", "x_food", "x_parking", "x_border"],
    "repair": ["x_tire", "x_air", "x_oil", "x_brake", "x_tow"],
    "other":  ["x_misc"],
}
# Mã kho 1371 và nhà cung cấp 4021 theo anh Khampla (22/09): cấp con của 137 và 402.
MA_TK = ["625/1371", "625/4021", "614/1371", "614/4021", "4022/1371", "4022/4021", "1211/70", "1211/4021"]
COT_PHIEU = ("doc_no", "kind", "doc_date", "out_date", "back_date", "company", "owner_name", "vehicle_id",
             "truck_no", "brand_model", "plate_head", "plate_trailer", "driver_id", "driver_name",
             "odo_out", "odo_back", "customer_id", "customer_name", "route_id", "goods_type", "ore_bill_no",
             "ore_bill_date", "origin", "destination", "weight_origin", "weight_dest", "price", "price_ccy", "price_mode",
             "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price", "rate_usd", "rate_thb",
             "rate_vnd", "rate_cny", "note")
COT_NGAY = ("doc_date", "out_date", "back_date", "ore_bill_date")
# Ô tiền của mục II: Bãi không thấy, người kiểm mục II (KT Thu/Chi VC) sửa được khi khác hợp đồng
COT_TIEN = ("price", "price_ccy", "price_mode", "hire_price", "hire_ccy", "fee_pct", "over_limit_t", "over_price",
            "ore_bill_no", "ore_bill_date")
# Số và ngày phiếu quặng: kế toán nhập KHI NHẬN GIẤY (anh Khampla, C3.7). Bãi chỉ đính kèm ảnh.
COT_KE_TOAN = ("ore_bill_no", "ore_bill_date")
COT_SO = ("odo_out", "odo_back", "weight_origin", "weight_dest", "price", "hire_price",
          "fee_pct", "over_limit_t", "over_price", "rate_usd", "rate_thb", "rate_vnd", "rate_cny")
COT_TIEN_TE = ("price_ccy", "hire_ccy")          # ô CHỌN tiền tệ, không phải số
# Trường nào thuộc mục nào — để khoá theo trạng thái duyệt của mục
MUC_CUA_COT = {
    "info":  {"doc_date", "out_date", "back_date", "kind", "company", "owner_name", "vehicle_id", "truck_no",
              "brand_model", "plate_head", "plate_trailer", "driver_id", "driver_name", "odo_out", "odo_back"},
    "trans": {"customer_id", "customer_name", "route_id", "goods_type", "ore_bill_no", "ore_bill_date", "origin",
              "destination", "weight_origin", "weight_dest", "price", "price_ccy", "price_mode", "hire_price", "hire_ccy",
              "fee_pct", "over_limit_t", "over_price"},
}


def ma_tk_mac_dinh(company, section, source=None, place=None):
    """Định khoản theo quy trình của họ: xe nhà 625/614, xe liên kết 4022; kho …/1371, mua ngoài …/4021."""
    if section == "fuel" and source is None:
        source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    duoi = "1371" if source == "kho" else "4021"
    if company == "joint":
        return "4022/" + duoi
    return ("614/" if section == "repair" else "625/") + duoi


def _ngay(v):
    if v in (None, ""):
        return None
    if isinstance(v, dt.date):
        return v
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


def _tien_te(v, ten, bat_buoc=False):
    """Ô chọn tiền tệ. Gõ bậy thì báo rõ chứ không lặng lẽ đổi thành LAK — nhầm tiền là nhầm tiền thật."""
    if v in (None, ""):
        return "USD" if bat_buoc else None
    m = str(v).strip().upper()
    if m not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Ô %s phải là một trong %s, nhận '%s'." % (ten, ", ".join(TIEN_TE), v)})
    return m


def _ghi_log(db, phieu, user, hanh_dong):
    db.add(TripLog(trip_id=phieu.id, user_name=user.full_name, role=user.role, action=hanh_dong))


def _muc_cua(db, phieu):
    ds = {s.section: s for s in db.query(TripSection).filter(TripSection.trip_id == phieu.id).all()}
    for m in MUC:                       # phiếu cũ thiếu dòng nào thì bù "wait"
        if m not in ds:
            s = TripSection(trip_id=phieu.id, section=m, status="wait"); db.add(s); ds[m] = s
    return ds


def _dong_chi(db, phieu):
    return (db.query(TripExpense).filter(TripExpense.trip_id == phieu.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())


def _xuat_dong(d):
    return {"id": d.id, "section": d.section, "line_no": d.line_no, "item_key": d.item_key,
            "item_name": d.item_name, "qty": d.qty, "unit_price": d.unit_price, "currency": d.currency,
            "place": d.place, "place_id": d.place_id, "supplier_id": d.supplier_id, "paid_by_epl": d.paid_by_epl, "acct_code": d.acct_code, "source": d.source,
            "part_id": d.part_id, "stock_move_id": d.stock_move_id,
            "toll_card_id": d.toll_card_id, "card_move_id": d.card_move_id,
            "ghi_no": bool(d.ghi_no), "note": d.note}


def _xuat_su_kien(e):
    return {"id": e.id, "ts": e.ts.isoformat() if e.ts else None, "kind": e.kind, "stop_seq": e.stop_seq,
            "incident_type": e.incident_type, "note": e.note, "expense_id": e.expense_id, "by_user": e.by_user,
            "status": e.status or "approved", "reported_cost": e.reported_cost, "currency": e.currency,
            "qty_l": e.qty_l, "place_id": e.place_id, "supplier_id": e.supplier_id,
            "approved_by": e.approved_by, "approved_at": e.approved_at.isoformat() if e.approved_at else None}


def _cua_tai_xe(db, p, user):
    """Vai tài xế chỉ được đụng phiếu của chính mình."""
    if user.role != "driver":
        return
    if not user.driver_id or p.driver_id != user.driver_id:
        raise HTTPException(403, {"ma": "KHONG_PHAI_PHIEU_CUA_BAN", "loi": "Đây không phải phiếu của bạn."})


def _dong_tam_ung(p, cac_dong):
    """Các dòng TIỀN MẶT tài xế cầm đi: mọi khoản EPL ứng trừ những gì xuất từ kho (dầu kho, phụ tùng kho)."""
    return [d for d in cac_dong if d.paid_by_epl and d.source != "kho" and d.section in ("fuel", "travel", "other")]


def da_thu_theo_phieu(db, trip_ids):
    """Tổng đã thu (LAK) của nhiều phiếu trong MỘT truy vấn — danh sách 200 phiếu thì đừng hỏi 200 lần."""
    ids = [i for i in (trip_ids or []) if i]
    if not ids:
        return {}
    q = (db.query(TripPayment.trip_id, func.coalesce(func.sum(TripPayment.amount_lak), 0))
         .filter(TripPayment.trip_id.in_(ids)).group_by(TripPayment.trip_id))
    return {t: float(v or 0) for t, v in q.all()}


def _da_thu(db, phieu):
    return float(db.query(func.coalesce(func.sum(TripPayment.amount_lak), 0))
                 .filter(TripPayment.trip_id == phieu.id).scalar() or 0)


def _diem_tuyen(db, phieu):
    if not phieu.route_id:
        return []
    return [{"seq": s.seq, "name": s.name, "km_from_prev": s.km_from_prev}
            for s in db.query(RouteStop).filter(RouteStop.route_id == phieu.route_id).order_by(RouteStop.seq).all()]


def xuat_phieu(db, phieu, day_du=True, da_thu=None):
    dong = _dong_chi(db, phieu)
    if da_thu is None:
        da_thu = _da_thu(db, phieu)
    ra = {c: getattr(phieu, c) for c in COT_PHIEU}
    for c in COT_NGAY:
        ra[c] = ra[c].isoformat() if ra[c] else None
    tuyen = db.get(Route, phieu.route_id) if phieu.route_id else None
    hd_gop = db.get(Invoice, phieu.invoice_id) if phieu.invoice_id else None
    kh = db.get(Customer, phieu.customer_id) if phieu.customer_id else None
    ra.update({"id": phieu.id, "transport_status": phieu.transport_status,
               "finance_status": phieu.finance_status, "invoiced": phieu.invoiced,
               # Hoá đơn gộp tháng (C8.2): phiếu nằm trong tờ nào, và khách này có gộp không —
               # để màn phiếu ẩn nút "xuất hoá đơn"/"ghi thu" và chỉ sang tờ gộp.
               "invoice_id": phieu.invoice_id, "inv_no": hd_gop.inv_no if hd_gop else None,
               "inv_mode": (kh.invoice_mode if kh else None) or "phieu",
               "locked": bool(phieu.locked), "locked_by": phieu.locked_by,
               "locked_at": phieu.locked_at.isoformat() if phieu.locked_at else None,
               "owner_id": phieu.owner_id, "owner_payment_id": phieu.owner_payment_id,
               "owner_paid": bool(phieu.owner_paid or phieu.owner_payment_id), "owner_paid_usd": phieu.owner_paid_usd,
               "owner_paid_lak": phieu.owner_paid_lak, "owner_paid_by": phieu.owner_paid_by,
               "owner_paid_at": phieu.owner_paid_at.isoformat() if phieu.owner_paid_at else None,
               "odo_est": (phieu.odo_out + tuyen.total_km) if (phieu.odo_out and tuyen and tuyen.total_km) else None,
               "attachments": db.query(TripAttachment).filter(TripAttachment.trip_id == phieu.id).count(),
               "created_by": phieu.created_by,
               "created_at": phieu.created_at.isoformat() if phieu.created_at else None,
               "tinh": tinh_phieu(phieu, dong, da_thu),
               "sections": {s.section: s.status for s in _muc_cua(db, phieu).values()}})
    if day_du:
        ra["thu_tien"] = [_xuat_thu(x) for x in db.query(TripPayment)
                          .filter(TripPayment.trip_id == phieu.id)
                          .order_by(TripPayment.pay_date, TripPayment.created_at).all()]
        ra["goods"] = KH.dong_hang(db, phieu.id)
        ra["ton_lo"] = KH.ton_lo(db, phieu.id) if phieu.kind == "gom" else None
        ra["expenses"] = [_xuat_dong(d) for d in dong]
        ra["logs"] = [{"ts": l.ts.isoformat() if l.ts else None, "user": l.user_name, "role": l.role,
                       "action": l.action}
                      for l in db.query(TripLog).filter(TripLog.trip_id == phieu.id)
                      .order_by(TripLog.ts.desc()).limit(60).all()]
        su_kien = db.query(TripEvent).filter(TripEvent.trip_id == phieu.id).order_by(TripEvent.ts).all()
        ra["events"] = [_xuat_su_kien(e) for e in su_kien]
        ra["route_stops"] = _diem_tuyen(db, phieu)
        # điểm xa nhất đã tới trên tuyến — để vẽ tiến độ
        da_toi = [e.stop_seq for e in su_kien if e.kind == "arrive_stop" and e.stop_seq]
        toi = max(da_toi) if da_toi else (1 if phieu.transport_status != "dispatched" else 0)
        # Xe ĐÃ BÁO TỚI NƠI thì coi như đã qua hết chặng, dù Bãi không bấm đủ từng mốc trên đường.
        # Không vậy thì màn theo dõi ghi "Đã giao hàng" mà vẫn "1/4 chặng" — hai câu đá nhau.
        if phieu.transport_status == "arrived" and ra["route_stops"]:
            toi = max(toi, len(ra["route_stops"]))
        ra["stop_reached"] = toi
    return ra


# ---------------------------------------------------------------- danh sách & xem
@router.get("/api/khoan-muc")
def khoan_muc():
    return {"items": KHOAN_MUC, "acct_codes": MA_TK, "chain": {k: list(v) for k, v in CHUOI.items()},
            "acct_default": {"EPL": {m: ma_tk_mac_dinh("EPL", m, "kho" if m in ("fuel", "repair") else None) for m in MUC_CHI},
                             "joint": {m: ma_tk_mac_dinh("joint", m, "kho" if m in ("fuel", "repair") else None) for m in MUC_CHI}},
            "acct_rule": {"EPL": {"kho": {"fuel": "625/1371", "repair": "614/1371"}, "mua": {"fuel": "625/4021", "repair": "614/4021", "travel": "625/4021", "other": "625/4021"}},
                          "joint": {"kho": {"fuel": "4022/1371", "repair": "4022/1371"}, "mua": {"fuel": "4022/4021", "repair": "4022/4021", "travel": "4022/4021", "other": "4022/4021"}}},
            "event_kinds": list(SU_KIEN), "incident_types": list(LOAI_SU_CO)}


@router.get("/api/trips")
def ds_phieu(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai),
             transport_status: str = None, finance_status: str = None, company: str = None, q: str = None):
    qs = db.query(Trip)
    if _.role == "driver":                       # tài xế chỉ thấy phiếu của mình
        qs = qs.filter(Trip.driver_id == (_.driver_id or "__khong_co__"))
    if transport_status: qs = qs.filter(Trip.transport_status == transport_status)
    if finance_status: qs = qs.filter(Trip.finance_status == finance_status)
    if company: qs = qs.filter(Trip.company == company)
    ds = qs.order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).all()
    if q:
        t = q.strip().lower()
        ds = [p for p in ds if t in " ".join(str(x or "") for x in (
            p.doc_no, p.driver_name, p.truck_no, p.customer_name, p.plate_head, p.plate_trailer,
            p.origin, p.destination, p.ore_bill_no)).lower()]
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    return [xuat_phieu(db, p, day_du=False, da_thu=thu.get(p.id, 0)) for p in ds]


@router.get("/api/trips/{tid}")
def xem_phieu(tid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, _)
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- lập & sửa
def _so_phieu_moi(db):
    """T4-0428-08/EPL → số kế tiếp trong tháng hiện tại. Chỉ là gợi ý, người lập sửa được."""
    thang = dt.date.today().strftime("%m")
    cuoi = (db.query(Trip).filter(Trip.doc_no.like("T4-%%-%s/EPL" % thang))
            .order_by(Trip.doc_no.desc()).first())
    so = 1
    if cuoi:
        try:
            so = int(cuoi.doc_no.split("-")[1]) + 1
        except (IndexError, ValueError):
            so = 1
    return "T4-%04d-%s/EPL" % (so, thang)


@router.get("/api/trips-so-moi")
def so_moi(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return {"doc_no": _so_phieu_moi(db)}


def _ap_truong(db, p, data, user, muc_tt=None):
    """Ghi các trường vào phiếu. Khi sửa, chỉ ghi trường của mục còn được sửa."""
    for c in COT_PHIEU:
        if c not in data:
            continue
        if c in COT_KE_TOAN and user.role not in ("acct", "admin"):
            # Bãi gửi cả bản phiếu lên khi lưu; ô không đổi thì bỏ qua, ô đổi thì từ chối rõ.
            moi_gt = _ngay(data[c]) if c in COT_NGAY else ((str(data[c]).strip() or None) if data[c] is not None else None)
            if moi_gt != getattr(p, c):
                raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Số và ngày phiếu quặng do kế toán nhập khi nhận giấy; Bãi chỉ đính kèm ảnh."})
            continue
        if muc_tt is not None:
            muc = next((m for m, cot in MUC_CUA_COT.items() if c in cot), None)
            if muc and not duoc_sua_muc(user.role, muc, muc_tt[muc]) and not (c in COT_TIEN and duoc_sua_tien(user.role, muc, muc_tt[muc])):
                raise HTTPException(409, {"ma": "MUC_DA_KHOA",
                                          "loi": "Mục %s đã khoá (%s); phải trả lại mới sửa được." % (muc, muc_tt[muc])})
        v = data[c]
        if c in COT_NGAY: v = _ngay(v)
        elif c in COT_SO: v = _so(v, c)
        elif c in COT_TIEN_TE: v = _tien_te(v, c, bat_buoc=(c == "price_ccy"))
        elif c == "price_mode":
            v = (str(v or "ton").strip().lower() or "ton")
            if v not in CACH_TINH_CUOC:
                raise HTTPException(422, {"ma": "CACH_TINH_SAI", "loi": "Cách tính cước phải là 'ton' (theo tấn) hoặc 'chuyen' (trọn chuyến)."})
        elif isinstance(v, str): v = v.strip() or None
        setattr(p, c, v)
    # Chép tên/biển từ danh mục nếu chỉ gửi mã
    if p.vehicle_id and not data.get("truck_no"):
        x = db.get(Vehicle, p.vehicle_id)
        if x:
            p.truck_no, p.brand_model, p.plate_head, p.plate_trailer = x.truck_no, x.brand_model, x.plate_head, x.plate_trailer
            if x.owner_type == "joint":
                # Xe của chủ xe liên kết thì phiếu là phiếu xe liên kết — không bắt người lập chọn lại.
                if "company" not in data: p.company = "joint"
                if not p.owner_name: p.owner_name = x.owner_name
                if x.owner_id: p.owner_id = x.owner_id
    if p.driver_id and not data.get("driver_name"):
        d = db.get(Driver, p.driver_id)
        if d: p.driver_name = d.name
    if p.customer_id and not data.get("customer_name"):
        k = db.get(Customer, p.customer_id)
        if k: p.customer_name = k.name
    # Tuyến: điền điểm đi/đến nếu người lập chưa gõ
    if p.route_id:
        r = db.get(Route, p.route_id)
        if not r:
            raise HTTPException(422, {"ma": "TUYEN_SAI", "loi": "Không có tuyến này."})
        if not p.origin: p.origin = r.origin
        if not p.destination: p.destination = r.destination
    # Không gửi loại xe thì mặc định xe nhà — cột có default ở CSDL nhưng phép kiểm chạy TRƯỚC khi ghi.
    if not p.company:
        p.company = "EPL"
    if p.company not in ("EPL", "joint"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "company phải là EPL hoặc joint."})
    # K3: Bãi không thấy tiền nên không gửi giá; có khách + tuyến trong bảng giá thì máy điền đơn giá hợp đồng.
    # Chỉ điền khi phiếu CHƯA có giá — kế toán đã gõ giá khác hợp đồng thì giữ của kế toán.
    if p.customer_id and p.route_id and not p.price:
        g = tim_gia(db, p.customer_id, p.route_id, p.goods_type, p.doc_date)
        if g:
            # Giá hợp đồng mang theo TIỀN TỆ của hợp đồng đó: khách Trung Quốc ký bằng Nhân dân tệ
            # thì phiếu phải là Nhân dân tệ, không được rơi về USD.
            p.price, p.price_ccy = g.price, chuan_tien(g.price_ccy, "USD")
            p.price_mode = g.price_mode or "ton"
            if p.hire_price is None and g.hire_price:
                p.hire_price, p.hire_ccy = g.hire_price, chuan_tien(g.hire_ccy or g.price_ccy, "USD")
    if not p.price_ccy:
        p.price_ccy = "USD"
    if not p.price_mode:
        p.price_mode = "ton"
    if p.company == "joint" and p.hire_price is None:
        p.hire_price, p.hire_ccy = p.price, p.price_ccy   # mặc định bằng giá nhận — người lập sửa sau


def _nguon_theo_diem(db, d):
    """Kho hay mua là do ĐIỂM ĐỔ quyết định: kho của EPL thì lĩnh (kho), trạm bán dầu thì mua.
    Phiếu cũ chưa có điểm đổ thì vẫn đọc khoá cũ fp_yard/fp_vn để không mất dữ liệu."""
    if d.get("place_id"):
        x = db.get(FuelPlace, d["place_id"])
        if x:
            return "kho" if x.owner_type == "epl" else "mua"
    return "kho" if (d.get("place") or "fp_yard") == "fp_yard" else "mua"


def _ncc_theo_diem(db, d):
    """Nhà cung cấp của điểm đổ (trạm ngoài). Kho của mình thì không có ai để nợ."""
    if db is None or not d.get("place_id"):
        return None
    dd = db.get(FuelPlace, str(d["place_id"]))
    return dd.supplier_id if (dd is not None and dd.owner_type != "epl") else None


def _dong_tu_du_lieu(p, m, i, d, db=None):
    """Dựng một dòng chi từ dữ liệu gửi lên; áp định khoản mặc định theo xe nhà/liên kết và nguồn kho/mua."""
    source = d.get("source")
    if m == "fuel":
        source = _nguon_theo_diem(db, d) if db is not None else ("kho" if (d.get("place") or "fp_yard") == "fp_yard" else "mua")
    elif m == "repair":
        if source not in ("kho", "mua"):
            source = "kho" if d.get("part_id") else "mua"
    else:
        source = None
    return TripExpense(
        trip_id=p.id, section=m, line_no=i,
        item_key=(d.get("item_key") or None), item_name=(d.get("item_name") or None),
        qty=_so(d.get("qty"), "qty") or 0, unit_price=_so(d.get("unit_price"), "unit_price") or 0,
        currency=str(d.get("currency") or "LAK").upper(), place=d.get("place"),
        place_id=d.get("place_id") or None,
        # Đổ ở TRẠM NGOÀI thì dòng chi mang luôn nhà cung cấp của trạm đó — công nợ trạm dầu (C5.1)
        # phải tra được từ dòng chi, chứ không bắt người đọc lần từ điểm đổ sang nhà cung cấp.
        supplier_id=(d.get("supplier_id") or _ncc_theo_diem(db, d) or None),
        paid_by_epl=bool(d.get("paid_by_epl", True)),
        acct_code=d.get("acct_code") or ma_tk_mac_dinh(p.company, m, source, d.get("place")),
        source=source, part_id=d.get("part_id") or None, stock_move_id=d.get("stock_move_id") or None,
        # Phí cầu đường trả bằng thẻ (C6.1): dòng nhớ thẻ nào, thẻ bị trừ lúc kế toán ghi sổ mục IV.
        toll_card_id=(d.get("toll_card_id") or None) if m == "travel" else None,
        # Ghi nợ tại trạm (C5.1): chỉ có nghĩa với khoản MUA NGOÀI — hàng lấy từ kho mình thì nợ ai.
        ghi_no=bool(d.get("ghi_no")) and source != "kho", note=d.get("note"))


def _ap_dong_chi(db, p, cac_dong, user, muc_tt):
    """Thay TOÀN BỘ dòng chi của những mục được gửi lên. Mục đã khoá thì từ chối.
    Dòng đã sinh phiếu xuất kho (stock_move_id) được giữ nguyên số lượng — xuất rồi không sửa trên phiếu."""
    theo_muc = {}
    for i, d in enumerate(cac_dong or []):
        m = d.get("section")
        if m not in MUC_CHI:
            raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Dòng %d: mục %s không hợp lệ." % (i + 1, m)})
        theo_muc.setdefault(m, []).append(d)
    for m in theo_muc:
        if not duoc_sua_muc(user.role, m, muc_tt[m]):
            raise HTTPException(409, {"ma": "MUC_DA_KHOA",
                                      "loi": "Mục %s đã khoá (%s), không sửa được dòng chi." % (m, muc_tt[m])})
        cu = {e.id: e for e in db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == m).all()}
        # Dòng đã sinh phiếu xuất kho là CHỨNG TỪ KHO — không xoá, không đổi số trên phiếu. Người
        # dùng bỏ nó khỏi danh sách gửi lên thì từ chối cả lần lưu và nói rõ dòng nào.
        # Dòng đã TRỪ THẺ cao tốc cũng vậy: số dư thẻ đã giảm thật, không xoá lặng lẽ trên phiếu.
        giu = {e.id: e for e in cu.values() if e.stock_move_id or e.card_move_id}
        da_gui = {d.get("id") for d in theo_muc[m]}
        for e in giu.values():
            if e.id not in da_gui:
                raise HTTPException(409, {"ma": "DA_XUAT_KHO" if e.stock_move_id else "DA_TRU_THE",
                                          "loi": "Dòng '%s' đã %s, không xoá được trên phiếu."
                                                 % (e.item_name or e.item_key, "xuất kho" if e.stock_move_id else "trừ vào thẻ cao tốc")})
        for e in cu.values():
            if e.id in giu: continue
            db.delete(e)
        db.flush()
        i = 0
        for d in theo_muc[m]:
            i += 1
            e = giu.get(d.get("id"))
            if e:
                e.line_no = i; e.note = d.get("note"); e.acct_code = d.get("acct_code") or e.acct_code
                continue
            db.add(_dong_tu_du_lieu(p, m, i, d, db))


def _doi_trang_thai_xe_tai_xe(db, p, trang_thai_xe, trang_thai_tai_xe):
    if p.vehicle_id:
        x = db.get(Vehicle, p.vehicle_id)
        if x and x.status != "inactive": x.status = trang_thai_xe
    if p.driver_id:
        d = db.get(Driver, p.driver_id)
        if d and d.status != "inactive": d.status = trang_thai_tai_xe


def _ghi_do(db, p, user):
    CT.ghi(db, "DO", nguon_bang="trips", nguon_id=p.id, trip=p, ngay=p.doc_date or dt.date.today(),
           doi_tuong_loai="khach", doi_tuong_ten=p.customer_name, by_user=user.full_name,
           mo_ta="Phiếu xuất xe %s · %s → %s" % (p.doc_no, p.origin or "", p.destination or ""),
           payload={"truck_no": p.truck_no, "driver_name": p.driver_name, "company": p.company})


@router.post("/api/trips")
def lap_phieu(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc lập phiếu xuất xe."})
    loai_do = (data.get("kind") or "giao").strip()
    if loai_do not in LOAI_DO:
        raise HTTPException(422, {"ma": "LOAI_DO_SAI", "loi": "Loại phiếu phải là 'gom' (đi lấy hàng) hoặc 'giao' (đi giao hàng)."})
    p = Trip(doc_no=str(data.get("doc_no") or _so_phieu_moi(db)).strip(), kind=loai_do, created_by=user.full_name)
    if db.query(Trip).filter(Trip.doc_no == p.doc_no).first():
        raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu %s đã có." % p.doc_no})
    # Tỷ giá mặc định lấy từ bảng tỷ giá, rồi khoá vào phiếu
    tg = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
    p.rate_usd, p.rate_thb = tg.get("USD", 22000), tg.get("THB", 700)
    p.rate_vnd, p.rate_cny = tg.get("VND", 1.2), tg.get("CNY", 3000)
    _ap_truong(db, p, data, user)
    # C4.2 (anh Khampla): phí, ngưỡng tấn, mức trừ quá tải, tiền thuê là ĐIỀU KHOẢN của từng chủ xe —
    # ô nào người lập không gửi thì lấy theo hồ sơ chủ xe, không lấy hằng số chung.
    if p.company == "joint" and p.owner_id:
        o = db.get(Owner, p.owner_id)
        if o:
            if "fee_pct" not in data: p.fee_pct = o.fee_pct
            if "over_limit_t" not in data: p.over_limit_t = o.over_limit_t
            if "over_price" not in data: p.over_price = o.over_price
            if not p.hire_ccy: p.hire_ccy = o.hire_ccy
    db.add(p); db.flush()
    muc_tt = {m: "wait" for m in MUC}
    for m in MUC:
        db.add(TripSection(trip_id=p.id, section=m, status="wait"))
    dong = list(data.get("expenses") or [])
    # BOT thuộc ĐƯỜNG: tuyến có phí cao tốc mà phiếu chưa có dòng x_toll → tự thêm
    if p.route_id:
        r = db.get(Route, p.route_id)
        if r and (r.toll_lak or 0) > 0 and not any(d.get("item_key") == "x_toll" for d in dong):
            dong.append({"section": "travel", "item_key": "x_toll", "qty": 1, "unit_price": r.toll_lak, "currency": "LAK"})
    _ap_dong_chi(db, p, dong, user, muc_tt)
    KH.dat_dong_hang(db, p, data.get("goods"), user)
    _doi_trang_thai_xe_tai_xe(db, p, "on_trip", "on_trip")
    _ghi_log(db, p, user, "a_create")
    db.flush(); _ghi_do(db, p, user); db.commit()
    return xuat_phieu(db, p)


VAI_SAU_KHOA = ("acct", "expacct", "rev", "treasury", "cash", "fuel", "admin")   # vai còn được thao tác khi phiếu đã khoá


def _chan_khoa(p, user):
    """Bước 14: phiếu đã khoá thì Bãi và tài xế không ghi thêm gì; kế toán, quỹ, kho vẫn kiểm và chi tiếp."""
    if p.locked and user.role not in VAI_SAU_KHOA:
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu %s đã khoá (%s). Muốn sửa phải nhờ kế toán mở khoá." % (p.doc_no, p.locked_by or "")})


@router.put("/api/trips/{tid}")
def sua_phieu(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _chan_khoa(p, user)
    muc_tt = {m: s.status for m, s in _muc_cua(db, p).items()}
    # ---- Luật hàng và kho (hai DO):
    #  · Loại phiếu không đổi được nữa khi đã có dòng hàng hay dòng sổ kho — đổi là phiếu gom mang dòng xuất kho.
    #  · Phiếu GOM đã nhập kho thì dòng hàng và hai ô cân ĐÓNG: sổ kho đã ghi theo số đó, sửa phiếu mà không
    #    sửa sổ thì hai bên nói hai số. Muốn khác thì xoá phiếu giao đã lấy hàng rồi làm lại, hoặc lập phiếu
    #    điều chỉnh — không âm thầm sửa lịch sử kho.
    #  · Phiếu GIAO đã tới nơi vẫn sửa được (cân cuối gõ nhầm là chuyện thường), nhưng sửa xong máy tính lại
    #    dòng hao hụt ngay bên dưới.
    co_so_kho = db.query(GoodsMove).filter(GoodsMove.trip_id == p.id).count() > 0
    co_dong_hang = db.query(TripGoods).filter(TripGoods.trip_id == p.id).count() > 0
    if "kind" in data and (data["kind"] or p.kind) != p.kind and (co_so_kho or co_dong_hang):
        raise HTTPException(409, {"ma": "KHONG_DOI_LOAI",
                                  "loi": "Phiếu đã có dòng hàng hoặc đã ghi sổ kho, không đổi loại gom/giao được nữa."})
    da_nhap_kho = p.kind == "gom" and db.query(GoodsMove).filter(GoodsMove.trip_id == p.id, GoodsMove.kind == "in").count() > 0
    if da_nhap_kho and ("goods" in data or any(k in data for k in ("weight_origin", "weight_dest"))):
        raise HTTPException(409, {"ma": "HANG_DA_NHAP_KHO",
                                  "loi": "Hàng của phiếu gom này đã vào kho bãi; dòng hàng và cân không sửa được nữa."})
    if "doc_no" in data and str(data["doc_no"]).strip() != p.doc_no:
        if db.query(Trip).filter(Trip.doc_no == str(data["doc_no"]).strip()).first():
            raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu đã có."})
    _ap_truong(db, p, data, user, muc_tt)
    if "expenses" in data:
        _ap_dong_chi(db, p, data["expenses"], user, muc_tt)
    if "goods" in data:
        if not duoc_sua_muc(user.role, "trans", muc_tt["trans"]) and user.role != "admin":
            raise HTTPException(409, {"ma": "MUC_DA_KHOA", "loi": "Mục II đã khoá; phải trả lại mới sửa được dòng hàng."})
        KH.dat_dong_hang(db, p, data["goods"], user)
    # Phiếu giao đã tới nơi: dòng hàng hay cân cuối vừa đổi thì dòng hao hụt phải tính lại theo số mới.
    if p.kind == "giao" and p.transport_status == "arrived" and ("goods" in data or "weight_dest" in data or "weight_origin" in data):
        KH.ghi_hao_hut_giao(db, p)
    _ghi_log(db, p, user, "a_save")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- duyệt từng mục
def _xuat_kho_nhien_lieu(db, p, user):
    """Kế toán kho GHI SỔ mục III → mỗi dòng dầu đổ ở kho Thà Bốc chưa xuất thì sinh một dòng xuất kho.
    Đúng câu trong quy trình của họ: "Fuel storage will be responsible for check and issues"."""
    for e in _dong_chi(db, p):
        if e.section != "fuel" or e.source != "kho" or e.stock_move_id or not e.paid_by_epl:
            continue
        m = FuelMove(move_date=p.out_date or p.doc_date or dt.date.today(), doc_no=p.doc_no, kind="out",
                     truck_no=p.truck_no, qty_l=e.qty or 0, unit_price=e.unit_price or 0, currency=e.currency or "LAK",
                     note="Xuất theo phiếu %s" % p.doc_no, by_user=user.full_name, expense_id=e.id)
        db.add(m); db.flush()
        e.stock_move_id = m.id
        CT.ghi(db, "PXK_NL", nguon_bang="fuel_moves", nguon_id=m.id, trip=p, ngay=m.move_date, doi_tuong_loai="kho",
               tien=(e.qty or 0) * (e.unit_price or 0), tien_te=e.currency or "LAK", tien_lak=tien_dong(p, e),
               section="fuel", by_user=user.full_name, mo_ta="Xuất %s lít dầu theo phiếu %s (ghi sổ)" % (e.qty, p.doc_no),
               payload={"qty_l": e.qty, "unit_price": e.unit_price, "currency": e.currency, "truck_no": p.truck_no})


@router.post("/api/trips/{tid}/sections/{muc}/{hanh_dong}")
def duyet_muc(tid: str, muc: str, hanh_dong: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _chan_khoa(p, user)
    ds = _muc_cua(db, p)
    s = ds[muc] if muc in ds else None
    if s is None:
        raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Không có mục %s." % muc})
    # Hỏi QUYỀN trước, hỏi nội dung sau: vai không được đụng mục này thì phải nghe "không có quyền",
    # chứ nghe "mục còn trống" là câu trả lời của người khác — họ sẽ đi nhập cho đầy rồi vẫn bị chặn.
    moi_trang_thai = chuyen_muc(user.role, muc, s.status, hanh_dong)
    if muc in MUC_CHI and hanh_dong == "send" and not any(d.section == muc for d in _dong_chi(db, p)):
        raise HTTPException(409, {"ma": "MUC_TRONG", "loi": "Mục %s chưa có dòng chi nào để gửi kiểm." % muc})
    s.status = moi_trang_thai
    if muc == "fuel" and hanh_dong == "book":
        _xuat_kho_nhien_lieu(db, p, user)
    if muc == "travel" and hanh_dong == "book":
        # Phí cầu đường trả bằng thẻ: ghi sổ là lúc trừ thẻ, đúng như dòng xuất kho nhiên liệu ở trên.
        THE.tru_the_theo_phieu(db, p, user)
    if hanh_dong == "pay" and muc in ("repair", "other"):
        # Quỹ chi các khoản của mục này: khoản mua ngoài / chi khác. Dòng lấy kho đã có PXK_PT riêng.
        dong = [d for d in _dong_chi(db, p) if d.section == muc and d.paid_by_epl and d.source != "kho"]
        tong = sum(tien_dong(p, d) for d in dong)
        if tong > 0:
            CT.ghi(db, "PC_SC", nguon_bang="trip_sections", nguon_id="%s:%s" % (p.id, muc), trip=p, ngay=dt.date.today(), phuong_thuc="cash",
                   doi_tuong_loai="tai_xe", doi_tuong_ten=p.driver_name, tien=tong, tien_te="LAK", section=muc,
                   by_user=user.full_name, mo_ta="Chi mục %s phiếu %s" % ({"repair": "V sửa chữa", "other": "VI khác"}[muc], p.doc_no),
                   payload={"lines": [{"item": d.item_key or d.item_name, "qty": d.qty, "unit_price": d.unit_price,
                                       "currency": d.currency, "acct_code": d.acct_code} for d in dong]})
    _ghi_log(db, p, user, "sec_%s:%s" % (muc, hanh_dong))
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- diễn biến trên đường
@router.get("/api/trips/{tid}/events")
def ds_su_kien(tid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_xuat_su_kien(e) for e in db.query(TripEvent).filter(TripEvent.trip_id == tid).order_by(TripEvent.ts).all()]


@router.post("/api/trips/{tid}/events")
def ghi_su_kien(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bãi ghi diễn biến khi tài xế gọi về: tới điểm X · sự cố · sửa xe · ghi chú.

    SỬA XE trên đường sinh ngay một dòng chi vào MỤC V của phiếu:
      · lấy phụ tùng từ kho (source=kho, part_id) → trừ tồn kho ngay, định khoản …/371;
      · mua ngoài / garage (source=mua)            → công nợ nhà cung cấp, định khoản …/402.
    Mục V đang ở bước sau "đã nhập" thì quay về "đã nhập" để kế toán kiểm lại — có chi mới thì phải kiểm lại.
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    # Diễn biến (tới điểm · sự cố · ghi chú) là việc của Bãi; nhưng DÒNG CHI SỬA CHỮA kèm theo là tiền
    # của mục V, nên phải do TỔ SỬA CHỮA khai (anh Khampla C1.2) — họ mới biết lấy kho hay ra gara.
    if data.get("repair"):
        if user.role not in ("repair", "admin"):
            raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                      "loi": "Khoản sửa chữa do tổ sửa chữa Thà Bốc khai, không phải vai %s." % user.role})
    elif user.role not in ("yard", "repair", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc ghi diễn biến trên đường."})
    if p.finance_status == "paid":
        raise HTTPException(409, {"ma": "PHIEU_DA_XONG", "loi": "Phiếu đã thu tiền xong, không ghi thêm diễn biến."})
    kind = data.get("kind")
    if kind not in SU_KIEN:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "kind phải là %s." % ", ".join(SU_KIEN)})
    e = TripEvent(trip_id=p.id, kind=kind, note=(data.get("note") or "").strip() or None, by_user=user.full_name)
    diem = _diem_tuyen(db, p)
    if data.get("stop_seq") not in (None, ""):
        seq = int(data["stop_seq"])
        if diem and not any(d["seq"] == seq for d in diem):
            raise HTTPException(422, {"ma": "DIEM_SAI", "loi": "Tuyến không có điểm số %d." % seq})
        e.stop_seq = seq
    if kind == "arrive_stop":
        if e.stop_seq is None:
            raise HTTPException(422, {"ma": "THIEU_DIEM", "loi": "Tới điểm nào? Cần stop_seq."})
        if p.transport_status == "dispatched":
            p.transport_status = "transit"       # đã tới một điểm là đã lăn bánh
    if kind in ("incident", "repair"):
        lt = data.get("incident_type") or ("breakdown" if kind == "repair" else "other")
        if lt not in LOAI_SU_CO:
            raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "incident_type phải là %s." % ", ".join(LOAI_SU_CO)})
        e.incident_type = lt
    db.add(e); db.flush()

    sua = data.get("repair")
    if sua:
        source = sua.get("source")
        if source not in ("kho", "mua"):
            raise HTTPException(422, {"ma": "NGUON_SAI", "loi": "Sửa xe phải ghi nguồn: kho (xuất kho) hay mua (mua ngoài)."})
        qty = _so(sua.get("qty"), "qty") or 1
        gia = _so(sua.get("unit_price"), "unit_price")
        part = None
        if source == "kho":
            part = db.get(Part, sua.get("part_id") or "")
            if not part:
                raise HTTPException(422, {"ma": "THIEU_PHU_TUNG", "loi": "Lấy từ kho thì phải chọn phụ tùng."})
            if (part.qty or 0) < qty:
                raise HTTPException(409, {"ma": "KHONG_DU", "loi": "Kho chỉ còn %s %s, không đủ xuất %s." % (part.qty, part.name, qty)})
            if gia is None: gia = part.unit_price or 0
        if gia is None:
            raise HTTPException(422, {"ma": "THIEU_GIA", "loi": "Mua ngoài thì phải ghi đơn giá."})
        so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "repair").count()
        dong = TripExpense(trip_id=p.id, section="repair", line_no=so_dong + 1,
                           item_key=(sua.get("item_key") or None) if not part else None,
                           item_name=(sua.get("item_name") or (part.name if part else None)),
                           qty=qty, unit_price=gia, currency=str(sua.get("currency") or "LAK").upper(),
                           paid_by_epl=bool(sua.get("paid_by_epl", True)), source=source, part_id=part.id if part else None,
                           acct_code=ma_tk_mac_dinh(p.company, "repair", source), note=e.note)
        db.add(dong); db.flush()
        if part:
            mv = PartMove(part_id=part.id, move_date=dt.date.today(), kind="out", qty=qty, truck_no=p.truck_no,
                          trip_doc_no=p.doc_no, note="Sửa xe trên đường — %s" % (e.note or ""), by_user=user.full_name, expense_id=dong.id)
            part.qty = (part.qty or 0) - qty; part.last_date = dt.date.today(); part.last_truck = p.truck_no
            db.add(mv); db.flush(); dong.stock_move_id = mv.id
            CT.ghi(db, "PXK_PT", nguon_bang="part_moves", nguon_id=mv.id, trip=p, ngay=mv.move_date, doi_tuong_loai="kho",
                   doi_tuong_ten=part.name, tien=qty * (dong.unit_price or 0), tien_te=dong.currency, tien_lak=tien_dong(p, dong),
                   section="repair", by_user=user.full_name, mo_ta="Xuất %s %s sửa xe %s" % (qty, part.name, p.truck_no),
                   payload={"part_id": part.id, "qty": qty, "unit_price": dong.unit_price, "currency": dong.currency, "truck_no": p.truck_no})
        e.expense_id = dong.id
        # Khoản sửa xe khai từ màn theo dõi là dữ liệu ĐÃ NHẬP: mục V vào thẳng hàng chờ kế toán kiểm.
        # Mục đã qua bước kiểm/ghi sổ/chi thì kéo về "đã nhập" và ghi rõ là mở lại vì có chi mới.
        s = _muc_cua(db, p)["repair"]
        if s.status not in ("wait", "entered"):
            _ghi_log(db, p, user, "sec_repair:reopen")
        s.status = "entered"
        if p.vehicle_id and e.incident_type == "breakdown":
            x = db.get(Vehicle, p.vehicle_id)
            if x: x.status = "maintenance"
    _ghi_log(db, p, user, "ev_%s" % kind)
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- đổi xe giữa đường (C2.2, anh Khampla 22/09)
@router.post("/api/trips/{tid}/doi-xe")
def doi_xe(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Xe hỏng nặng giữa đường → đổi xe khác chở tiếp, TRÊN CÙNG MỘT PHIẾU.

    Anh Khampla C2.2: chuyện này có thật và xảy ra khi mục I đã kiểm xong. Không thể bắt họ lập
    phiếu mới — hàng, khách, tuyến, tiền đã chi vẫn là của chuyến này; lập phiếu mới là tách đôi
    một chuyến trong mọi báo cáo.

    Nên: ghi xe mới vào phiếu, để lại MỘT dòng diễn biến nói rõ đổi từ xe nào sang xe nào và vì sao
    (xe cũ vẫn tra được), rồi kéo **mục I về "đã nhập"** để kế toán kiểm lại — thông tin xe đã khác
    thì chữ ký kiểm cũ không còn đúng. Xe cũ chuyển sang *đang sửa* nếu lý do là hỏng; xe mới sang
    *đang chạy*.
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc đổi xe — họ là người điều xe."})
    _chan_khoa(p, user)
    if p.transport_status == "arrived":
        raise HTTPException(409, {"ma": "PHIEU_DA_TOI", "loi": "Xe đã tới nơi rồi, không đổi xe nữa."})
    xe_moi = db.get(Vehicle, str(data.get("vehicle_id") or ""))
    if not xe_moi:
        raise HTTPException(422, {"ma": "THIEU_XE", "loi": "Đổi sang xe nào? Cần vehicle_id."})
    if xe_moi.id == p.vehicle_id:
        raise HTTPException(409, {"ma": "CUNG_XE", "loi": "Xe mới trùng xe đang chạy (%s)." % (p.truck_no or "")})
    if not xe_moi.active:
        raise HTTPException(409, {"ma": "XE_NGUNG", "loi": "Xe %s đã ngưng dùng." % xe_moi.truck_no})
    ly_do = (data.get("ly_do") or data.get("reason") or "").strip()
    if not ly_do:
        raise HTTPException(422, {"ma": "THIEU_LY_DO", "loi": "Đổi xe phải ghi lý do — kế toán kiểm lại mục I sẽ đọc câu này."})
    xe_cu = db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
    cu_ten = p.truck_no or (xe_cu.truck_no if xe_cu else "")
    cu_bien = p.plate_head or ""
    # Xe cũ nghỉ: hỏng thì vào xưởng, lý do khác (điều xe) thì về rảnh.
    if xe_cu is not None and xe_cu.status != "inactive":
        xe_cu.status = "maintenance" if data.get("xe_cu_hong", True) else "idle"
    p.vehicle_id = xe_moi.id
    p.truck_no, p.brand_model = xe_moi.truck_no, xe_moi.brand_model
    p.plate_head, p.plate_trailer = xe_moi.plate_head, xe_moi.plate_trailer
    # Xe liên kết và xe nhà tính tiền khác nhau, nên đổi xe là đổi luôn bên chủ xe của phiếu.
    if xe_moi.owner_type == "joint":
        p.company, p.owner_id, p.owner_name = "joint", xe_moi.owner_id, xe_moi.owner_name
        chu = db.get(Owner, xe_moi.owner_id) if xe_moi.owner_id else None
        if chu is not None:
            if p.fee_pct is None: p.fee_pct = chu.fee_pct
            if p.over_limit_t is None: p.over_limit_t = chu.over_limit_t
            if p.over_price is None: p.over_price = chu.over_price
            if not p.hire_ccy: p.hire_ccy = chu.hire_ccy
    else:
        p.company, p.owner_id, p.owner_name = "EPL", None, None
    if data.get("odo_out") not in (None, ""):
        p.odo_out = _so(data.get("odo_out"), "odo_out")
    elif xe_moi.odometer_km is not None:
        p.odo_out = xe_moi.odometer_km
    if xe_moi.status != "inactive":
        xe_moi.status = "on_trip"
    tx = None
    if data.get("driver_id"):
        tx = db.get(Driver, str(data["driver_id"]))
        if not tx:
            raise HTTPException(422, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
        cu_tx = db.get(Driver, p.driver_id) if p.driver_id else None
        if cu_tx is not None and cu_tx.id != tx.id and cu_tx.status != "inactive":
            cu_tx.status = "idle"
        p.driver_id, p.driver_name = tx.id, tx.name
        if tx.status != "inactive":
            tx.status = "on_trip"
    ghi_chu = "Đổi xe %s%s → %s%s · %s%s" % (
        cu_ten, (" (%s)" % cu_bien) if cu_bien else "", xe_moi.truck_no,
        (" (%s)" % xe_moi.plate_head) if xe_moi.plate_head else "", ly_do,
        (" · đổi tài xế sang %s" % tx.name) if tx is not None else "")
    e = TripEvent(trip_id=p.id, kind="change_truck", note=ghi_chu, by_user=user.full_name,
                  stop_seq=int(data["stop_seq"]) if str(data.get("stop_seq") or "").isdigit() else None)
    db.add(e)
    # Mục I nói về xe: đổi xe thì chữ ký kiểm cũ không còn đúng, kéo về "đã nhập" để kiểm lại.
    s = _muc_cua(db, p)["info"]
    if s.status not in ("wait", "entered"):
        _ghi_log(db, p, user, "sec_info:reopen")
    s.status = "entered"
    _ghi_log(db, p, user, "a_change_truck")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- tài xế báo đã về (C2.1, anh Khampla 22/09)
@router.post("/api/trips/{tid}/bao-ve")
def bao_ve(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Tài xế báo NGÀY VỀ và KM VỀ qua điện thoại — đúng người biết hai con số đó.

    Chỉ ghi hai số và đánh mốc "tới điểm cuối"; KHÔNG tự chuyển phiếu sang "đã tới": cân tại bãi
    hoặc tại cảng là việc của Bãi, Bãi bấm *Xe đã tới* thì hai ô ngày về, km về đã được điền sẵn."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tài xế của phiếu (hoặc Bãi) báo xe về."})
    _cua_tai_xe(db, p, user)
    _chan_khoa(p, user)
    if p.transport_status == "arrived":
        raise HTTPException(409, {"ma": "PHIEU_DA_TOI", "loi": "Phiếu đã ghi xe tới nơi rồi."})
    ngay = _ngay(data.get("back_date")) or dt.date.today()
    km = _so(data.get("odo_back"), "odo_back")
    if km is not None and p.odo_out is not None and km < p.odo_out:
        raise HTTPException(422, {"ma": "KM_SAI", "loi": "Km về (%s) không thể nhỏ hơn km lúc đi (%s)." % (round(km), round(p.odo_out))})
    p.back_date = ngay
    if km is not None:
        p.odo_back = km
    if p.transport_status == "dispatched":
        p.transport_status = "transit"
    diem = _diem_tuyen(db, p)
    if diem:
        cuoi = max(d["seq"] for d in diem)
        if not db.query(TripEvent).filter(TripEvent.trip_id == p.id, TripEvent.kind == "arrive_stop", TripEvent.stop_seq == cuoi).count():
            db.add(TripEvent(trip_id=p.id, kind="arrive_stop", stop_seq=cuoi, by_user=user.full_name,
                             note="Tài xế báo đã về · km %s" % (round(km) if km is not None else "—")))
    _ghi_log(db, p, user, "drv_back")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- mức phiếu
@router.post("/api/trips/{tid}/transport-status")
def doi_trang_thai_van_chuyen(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """ອອກລົດ → ກຳລັງຈັດສົ່ງ → ຮອດແລ້ວ. Admin Thà Bốc ghi khi xe báo về. Xe về thì xe & tài xế rảnh lại,
    công-tơ-mét của xe cập nhật theo số lúc về."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin", "driver"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc hoặc tài xế của phiếu cập nhật trạng thái xe."})
    _cua_tai_xe(db, p, user)
    _chan_khoa(p, user)
    moi = data.get("status")
    if moi not in TRANG_THAI_VAN_CHUYEN:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái phải là %s." % ", ".join(TRANG_THAI_VAN_CHUYEN)})
    if moi == "transit" and user.role != "admin":
        # XUẤT PHÁT chỉ khi tài xế đã cầm tiền tạm ứng: mục IV (đi đường) phải ở "đã chi". Đây là đúng thứ tự
        # anh chủ dự án mô tả — lập phiếu → in phiếu chi → duyệt → tài xế lấy tiền → mới bấm đi.
        if _dong_tam_ung(p, _dong_chi(db, p)) and _muc_cua(db, p)["travel"].status != "paid":
            raise HTTPException(409, {"ma": "CHUA_NHAN_TAM_UNG",
                                      "loi": "Chưa chi tiền tạm ứng (mục IV chưa 'đã chi') — tài xế chưa nhận tiền thì chưa xuất phát."})
    if moi == "arrived":
        if data.get("weight_dest") not in (None, ""): p.weight_dest = _so(data["weight_dest"], "weight_dest")
        if data.get("back_date"): p.back_date = _ngay(data["back_date"])
        if data.get("odo_back") not in (None, ""): p.odo_back = _so(data["odo_back"], "odo_back")
        _doi_trang_thai_xe_tai_xe(db, p, "available", "available")
        # Xe về tới nơi: DO gom thì hàng VÀO KHO bãi (sinh phiếu nhập kho), DO giao thì chốt dòng hao hụt.
        if p.kind == "gom":
            KH.nhap_kho(db, p, user)
        else:
            KH.ghi_hao_hut_giao(db, p)
        if p.vehicle_id and p.odo_back:
            x = db.get(Vehicle, p.vehicle_id)
            if x and (x.odometer_km or 0) < p.odo_back: x.odometer_km = p.odo_back
    else:
        _doi_trang_thai_xe_tai_xe(db, p, "on_trip", "on_trip")
    p.transport_status = moi
    _ghi_log(db, p, user, "st_%s" % moi)
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- bước 14: kiểm lại toàn phiếu rồi khoá
def _canh_bao_khoa(db, p):
    """Những chỗ kế toán phải nhìn trước khi khoá. Chỉ CẢNH BÁO, không chặn: số thật đôi khi lệch thật."""
    cb = []
    tuyen = db.get(Route, p.route_id) if p.route_id else None
    if p.odo_out and p.odo_back and tuyen and tuyen.total_km:
        uoc = p.odo_out + tuyen.total_km
        lech = (p.odo_back - uoc) / tuyen.total_km * 100
        if abs(lech) > 10:
            cb.append({"ma": "KM_LECH", "loi": "Km về thật %s lệch %.0f%% so với ước tính %s (tuyến %s km)."
                       % (round(p.odo_back), lech, round(uoc), round(tuyen.total_km))})
    if p.weight_origin and p.weight_dest is not None:
        hao = (p.weight_origin - p.weight_dest) / p.weight_origin * 100
        if hao > 1.5:
            cb.append({"ma": "HAO_HUT", "loi": "Hao hụt %.2f%% vượt mức 1,5%%." % hao})
    if p.weight_dest is None:
        cb.append({"ma": "THIEU_CAN_CUOI", "loi": "Chưa có cân cuối." if p.kind == "giao" else "Chưa có cân tại bãi khi xe về."})
    if not db.query(TripGoods).filter(TripGoods.trip_id == p.id, TripGoods.loai == "hang").count():
        cb.append({"ma": "THIEU_DONG_HANG", "loi": "Phiếu chưa ghi dòng hàng (mặt hàng, số tấn)."})
    if not p.odo_back:
        cb.append({"ma": "THIEU_KM_VE", "loi": "Chưa có km về thật."})
    if not db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind == "ore_bill").count():
        cb.append({"ma": "THIEU_PHIEU_QUANG", "loi": "Chưa đính kèm phiếu quặng của khách."})
    tt = {m: s.status for m, s in _muc_cua(db, p).items()}
    dong = _dong_chi(db, p)
    for m in MUC_CHI:
        if any(d.section == m for d in dong) and tt.get(m) in ("wait", "entered"):
            cb.append({"ma": "MUC_CHUA_KIEM", "loi": "Mục %s có dòng chi nhưng chưa kiểm." % m})
    return cb


@router.get("/api/trips/{tid}/kiem-lai")
def kiem_lai(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bảng rà trước khi khoá: kế toán bấm 'Kiểm lại' thấy ngay lệch gì."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    return {"canh_bao": _canh_bao_khoa(db, p), "locked": bool(p.locked)}


@router.post("/api/trips/{tid}/khoa")
def khoa_phieu(tid: str, data: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Xe về → kế toán rà lại cả phiếu → KHOÁ. Có cảnh báo thì phải gửi {"xac_nhan": true} mới khoá."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("acct", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán Viêng Chăn khoá phiếu."})
    if p.locked:
        raise HTTPException(409, {"ma": "DA_KHOA", "loi": "Phiếu đã khoá rồi."})
    if p.transport_status != "arrived":
        raise HTTPException(409, {"ma": "XE_CHUA_VE", "loi": "Xe chưa về (trạng thái %s) thì chưa khoá phiếu." % p.transport_status})
    cb = _canh_bao_khoa(db, p)
    if cb and not data.get("xac_nhan"):
        raise HTTPException(409, {"ma": "CO_CANH_BAO", "loi": "Phiếu còn %d điểm cần xem; xem rồi xác nhận khoá." % len(cb), "canh_bao": cb})
    p.locked, p.locked_by, p.locked_at = True, user.full_name, dt.datetime.utcnow()
    _ghi_log(db, p, user, "a_lock" if not cb else "a_lock_warn")
    db.commit()
    ra = xuat_phieu(db, p); ra["canh_bao"] = cb
    return ra


@router.post("/api/trips/{tid}/mo-khoa")
def mo_khoa_phieu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("acct", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán Viêng Chăn mở khoá."})
    if p.invoiced and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_HOA_DON", "loi": "Đã xuất hoá đơn thì không mở khoá được."})
    p.locked, p.locked_by, p.locked_at = False, None, None
    _ghi_log(db, p, user, "a_unlock_slip")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- xe liên kết: chi trả chủ xe → PC_CX
@router.post("/api/trips/{tid}/tra-chu-xe")
def tra_chu_xe(tid: str, data: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Quỹ chi tiền cho chủ xe liên kết một lần cho cả phiếu: giá thuê × tấn − 2% − vượt tấn − EPL đã ứng."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("cash", "treasury", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ quỹ chi trả chủ xe."})
    if p.company != "joint":
        raise HTTPException(422, {"ma": "KHONG_PHAI_LIEN_KET", "loi": "Phiếu này là xe nhà, không có chủ xe để trả."})
    if not p.locked:
        raise HTTPException(409, {"ma": "CHUA_KHOA", "loi": "Kế toán phải khoá phiếu rồi quỹ mới trả chủ xe."})
    if p.owner_paid or p.owner_payment_id:
        raise HTTPException(409, {"ma": "DA_TRA", "loi": "Đã trả chủ xe phiếu này rồi (%s)." % (p.owner_paid_by or "")})
    # Trả từng phiếu = một đợt gồm đúng một phiếu; cùng hàm với trả gộp để chứng từ và sổ trả giống nhau.
    from routes.chu_xe import tra_nhieu_phieu
    o = db.get(Owner, p.owner_id) if p.owner_id else None
    tra_nhieu_phieu(db, user, [p], method=(data.get("method") or "cash"), note=data.get("note"), owner=o)
    _ghi_log(db, p, user, "a_pay_owner")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- tệp đính kèm (phiếu quặng của khách)
TEP_DIR = os.getenv("EPL_LAO_TEP") or os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "tep"))
TEP_TOI_DA = 8 * 1024 * 1024
TEP_KIEU = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/heic": ".heic", "application/pdf": ".pdf"}


def _xoa_tep_dia(a):
    try:
        os.remove(os.path.join(TEP_DIR, a.trip_id, a.stored))
    except OSError:
        pass


def _xuat_tep(a):
    return {"id": a.id, "trip_id": a.trip_id, "kind": a.kind, "filename": a.filename, "content_type": a.content_type,
            "size": a.size, "note": a.note, "by_user": a.by_user, "ts": a.ts.isoformat() if a.ts else None,
            "url": "/api/tep/%s" % a.id, "la_anh": (a.content_type or "").startswith("image/")}


@router.get("/api/trips/{tid}/tep")
def ds_tep(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)
    return [_xuat_tep(a) for a in db.query(TripAttachment).filter(TripAttachment.trip_id == p.id).order_by(TripAttachment.ts).all()]


@router.post("/api/trips/{tid}/tep")
async def them_tep(tid: str, tep: UploadFile = File(...), kind: str = Form("ore_bill"), note: str = Form(""),
                   db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bãi (hoặc kế toán) chụp phiếu quặng của khách đưa lên. Ảnh hoặc PDF, tối đa 8 MB."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "acct", "rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Bãi hoặc kế toán đính kèm tệp."})
    _chan_khoa(p, user)
    kieu = (tep.content_type or mimetypes.guess_type(tep.filename or "")[0] or "").lower()
    if kieu not in TEP_KIEU:
        raise HTTPException(422, {"ma": "KIEU_TEP", "loi": "Chỉ nhận ảnh (JPG, PNG, WEBP, HEIC) hoặc PDF."})
    du = await tep.read()
    if len(du) > TEP_TOI_DA:
        raise HTTPException(422, {"ma": "TEP_QUA_LON", "loi": "Tệp %.1f MB, tối đa 8 MB." % (len(du) / 1048576)})
    if not du:
        raise HTTPException(422, {"ma": "TEP_RONG", "loi": "Tệp rỗng."})
    a = TripAttachment(trip_id=p.id, kind=kind if kind in ("ore_bill", "other") else "ore_bill",
                       filename=re.sub(r"[^\w.\-() ]+", "_", tep.filename or "tep")[:120], content_type=kieu,
                       size=len(du), note=(note or None), by_user=user.full_name)
    a.id = ma_moi()
    a.stored = a.id + TEP_KIEU[kieu]
    os.makedirs(os.path.join(TEP_DIR, p.id), exist_ok=True)
    with open(os.path.join(TEP_DIR, p.id, a.stored), "wb") as f:
        f.write(du)
    db.add(a)
    _ghi_log(db, p, user, "a_attach")
    db.commit()
    return _xuat_tep(a)


@router.get("/api/tep/{aid}")
def mo_tep(aid: str, request: Request, tk: str = "", db: Session = Depends(get_db)):
    """Trả tệp. Thẻ <img> không gửi header nên nhận phiên qua ?tk=…; không có phiên thì từ chối."""
    a = db.get(TripAttachment, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tệp này."})
    dau = request.headers.get("Authorization", "")
    token = tk or (dau[7:].strip() if dau.lower().startswith("bearer ") else "")
    if not token or not doc_phien(token):
        raise HTTPException(401, {"ma": "CHUA_DANG_NHAP", "loi": "Vui lòng đăng nhập."})
    duong = os.path.join(TEP_DIR, a.trip_id, a.stored)
    if not os.path.exists(duong):
        raise HTTPException(404, {"ma": "MAT_TEP", "loi": "Tệp không còn trên máy chủ."})
    return FileResponse(duong, media_type=a.content_type, filename=a.filename,
                        content_disposition_type="inline")


@router.delete("/api/tep/{aid}")
def xoa_tep(aid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    a = db.get(TripAttachment, aid)
    if not a:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tệp này."})
    p = db.get(Trip, a.trip_id)
    if user.role not in ("acct", "admin") and a.by_user != user.full_name:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ người đưa lên hoặc kế toán xoá tệp."})
    if p: _chan_khoa(p, user)
    _xoa_tep_dia(a)
    db.delete(a)
    if p: _ghi_log(db, p, user, "a_detach")
    db.commit()
    return {"ok": True}


@router.post("/api/trips/{tid}/invoice")
def xuat_hoa_don(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu xuất hoá đơn."})
    # B4 (anh Khampla 22/09): khách trả cước RIÊNG cho chặng gom, nên phiếu gom cũng xuất hoá đơn như phiếu giao.
    if _muc_cua(db, p)["trans"].status != "verified":
        raise HTTPException(409, {"ma": "CHUA_KIEM", "loi": "Mục II (vận chuyển) phải được kiểm xong trước khi xuất hoá đơn."})
    if not p.locked:
        raise HTTPException(409, {"ma": "CHUA_KHOA", "loi": "Kế toán phải kiểm lại và KHOÁ phiếu (bước 14) rồi mới xuất hoá đơn."})
    kh = db.get(Customer, p.customer_id) if p.customer_id else None
    if kh is not None and kh.invoice_mode == "thang":
        raise HTTPException(409, {"ma": "GOP_THANG", "loi": "Khách %s xuất hoá đơn GỘP THÁNG — cuối tháng dùng \"Gộp hoá đơn tháng\", không xuất riêng từng phiếu." % kh.name})
    p.invoiced = True
    k = tinh_phieu(p, _dong_chi(db, p))
    CT.ghi(db, "HD", nguon_bang="trips", nguon_id=p.id, trip=p, ngay=dt.date.today(), doi_tuong_loai="khach",
           doi_tuong_ten=p.customer_name, tien=k["doanh_thu"], tien_te=k["ccy"], tien_lak=k["doanh_thu_lak"],
           by_user=user.full_name,
           mo_ta=("Hoá đơn vận chuyển %s · trọn chuyến %s %s" % (p.doc_no, p.price, k["ccy"]) if k["cach_tinh"] == "chuyen"
                  else "Hoá đơn vận chuyển %s · %s t × %s %s" % (p.doc_no, k["tan_tinh"], p.price, k["ccy"])),
           payload={"tan_tinh": k["tan_tinh"], "don_gia": p.price, "currency": k["ccy"], "cach_tinh": k["cach_tinh"],
                    "rate_to_lak": ty_gia(p, k["ccy"])})
    _ghi_log(db, p, user, "a_invoice")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- khách trả tiền: sổ thu từng lần
#
# Trước đây chỗ này là một cái nút "đã thu" bật `finance_status` sang `paid`. Nó không ghi khách trả
# bao nhiêu, bằng tiền gì, ngày nào — trong khi thực tế bên Lào hoá đơn ghi USD mà khách chuyển LAK
# hoặc Nhân dân tệ, và trả làm nhiều lần. Giờ mỗi lần tiền về là MỘT DÒNG, trạng thái phiếu do tổng
# các dòng đó quyết định, không ai bấm tay nữa.
LECH_COI_LA_DU = 1.0          # lệch dưới 1 LAK thì coi là trả đủ — làm tròn tỷ giá thôi, không phải nợ


def _xuat_thu(x):
    return {"id": x.id, "trip_id": x.trip_id, "pay_date": x.pay_date.isoformat() if x.pay_date else None,
            "amount": x.amount, "currency": x.currency, "rate_to_lak": x.rate_to_lak,
            "amount_lak": x.amount_lak, "method": x.method, "ref": x.ref, "note": x.note,
            # Dòng do một lần thu của hoá đơn gộp rải xuống — màn phiếu không cho xoá lẻ dòng này.
            "invoice_payment_id": x.invoice_payment_id,
            "by_user": x.by_user, "created_at": x.created_at.isoformat() if x.created_at else None}


def _tinh_lai_trang_thai_thu(db, p):
    """Trạng thái tài chính = so TỔNG ĐÃ THU với tiền hoá đơn, cả hai quy về LAK."""
    da = _da_thu(db, p)
    tong = tinh_phieu(p, _dong_chi(db, p))["doanh_thu_lak"]
    if da <= LECH_COI_LA_DU:
        p.finance_status = "unpaid"
    elif tong - da <= LECH_COI_LA_DU:
        p.finance_status = "paid"
    else:
        p.finance_status = "partial"
    return da, tong


@router.get("/api/trips/{tid}/thu-tien")
def ds_thu_tien(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)
    k = tinh_phieu(p, _dong_chi(db, p), _da_thu(db, p))
    ds = (db.query(TripPayment).filter(TripPayment.trip_id == p.id)
          .order_by(TripPayment.pay_date, TripPayment.created_at).all())
    return {"ds": [_xuat_thu(x) for x in ds], "hoa_don": k["doanh_thu"], "hoa_don_lak": k["doanh_thu_lak"],
            "ccy": k["ccy"], "da_thu": k["da_thu"], "da_thu_lak": k["da_thu_lak"],
            "con_lai": k["con_lai"], "con_lai_lak": k["con_lai_lak"],
            "finance_status": p.finance_status, "invoiced": bool(p.invoiced)}


@router.post("/api/trips/{tid}/thu-tien")
def ghi_thu_tien(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Kế toán doanh thu ghi MỘT lần khách trả tiền.

    Tiền trả có thể khác tiền ghi trên hoá đơn — hoá đơn USD, khách chuyển LAK là chuyện thường ở
    đây. Nên dòng thu mang tiền tệ và tỷ giá NGÀY THU của chính nó; không gửi tỷ giá thì lấy tỷ giá
    khoá trên phiếu làm mặc định (và màn hình ghi rõ là đang dùng tỷ giá của phiếu).
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu ghi thu tiền."})
    if not p.invoiced:
        raise HTTPException(409, {"ma": "CHUA_HOA_DON", "loi": "Chưa xuất hoá đơn thì chưa ghi thu tiền."})
    if p.invoice_id:
        hd = db.get(Invoice, p.invoice_id)
        raise HTTPException(409, {"ma": "THU_QUA_HD_GOP", "loi": "Phiếu này nằm trong hoá đơn gộp %s — ghi thu tiền ở tờ hoá đơn gộp, tiền sẽ tự phân bổ về phiếu."
                                  % (hd.inv_no if hd else ""), "invoice_id": p.invoice_id})
    tien = _so(data.get("amount"), "amount")
    if not tien or tien <= 0:
        raise HTTPException(422, {"ma": "SO_TIEN_SAI", "loi": "Số tiền thu phải lớn hơn 0."})
    ma = _tien_te(data.get("currency"), "currency", bat_buoc=True)
    tg = _so(data.get("rate_to_lak"), "rate_to_lak")
    if tg is None:
        tg = ty_gia(p, ma)                       # không gửi thì dùng tỷ giá khoá trên phiếu
    if tg <= 0:
        raise HTTPException(422, {"ma": "TY_GIA_SAI", "loi": "Tỷ giá phải lớn hơn 0."})
    if ma == "LAK":
        tg = 1.0
    pt = (data.get("method") or "bank").strip()
    if pt not in PHUONG_THUC_THU:
        raise HTTPException(422, {"ma": "PHUONG_THUC_SAI", "loi": "Cách thu phải là %s." % ", ".join(PHUONG_THUC_THU)})
    tien_lak = round(tien * tg)
    k = tinh_phieu(p, _dong_chi(db, p), _da_thu(db, p))
    if tien_lak > k["con_lai_lak"] + LECH_COI_LA_DU and not data.get("cho_thu_du"):
        raise HTTPException(409, {"ma": "THU_QUA_HOA_DON",
                                  "loi": "Hoá đơn còn %s %s (%s LAK) mà lần thu này %s LAK. Thu dư thì phải xác nhận."
                                         % (k["con_lai"], k["ccy"], round(k["con_lai_lak"]), tien_lak),
                                  "con_lai_lak": k["con_lai_lak"]})
    x = TripPayment(trip_id=p.id, pay_date=_ngay(data.get("pay_date")) or dt.date.today(),
                    amount=tien, currency=ma, rate_to_lak=tg, amount_lak=tien_lak, method=pt,
                    ref=(data.get("ref") or "").strip() or None, note=(data.get("note") or "").strip() or None,
                    by_user=user.full_name)
    db.add(x); db.flush()
    CT.ghi(db, "PT", nguon_bang="trip_payments", nguon_id=x.id, trip=p, ngay=x.pay_date, doi_tuong_loai="khach",
           doi_tuong_ten=p.customer_name, tien=tien, tien_te=ma, tien_lak=tien_lak, by_user=user.full_name,
           phuong_thuc=pt, mo_ta="Thu tiền khách phiếu %s · %s %s" % (p.doc_no, tien, ma),
           payload={"rate_to_lak": tg, "method": pt, "ref": x.ref, "hoa_don_ccy": k["ccy"],
                    "hoa_don": k["doanh_thu"], "hoa_don_lak": k["doanh_thu_lak"]})
    _tinh_lai_trang_thai_thu(db, p)
    _ghi_log(db, p, user, "fin_%s" % p.finance_status)
    db.commit()
    return xuat_phieu(db, p)


@router.delete("/api/thu-tien/{pid}")
def xoa_thu_tien(pid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Ghi nhầm thì xoá — nhưng chỉ khi tờ phiếu thu CHƯA đẩy sang kế toán. Đẩy rồi thì bên kia đã
    vào sổ, xoá lặng lẽ bên này là hai bên nói hai số."""
    x = db.get(TripPayment, pid)
    if not x:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có lần thu này."})
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu sửa sổ thu tiền."})
    if x.invoice_payment_id:
        raise HTTPException(409, {"ma": "THUOC_HD_GOP", "loi": "Dòng này do lần thu của hoá đơn gộp phân bổ xuống — xoá lần thu ở tờ hoá đơn gộp, không xoá lẻ từng phiếu."})
    p = db.get(Trip, x.trip_id)
    c = CT.tim(db, "PT", "trip_payments", x.id)
    if c is not None and c.da_day:
        raise HTTPException(409, {"ma": "DA_DAY_KE_TOAN",
                                  "loi": "Phiếu thu %s đã đẩy sang kế toán, không xoá được. Nhờ bên kế toán ghi bút toán đảo." % c.so})
    if c is not None:
        db.delete(c)
    db.delete(x); db.flush()
    _tinh_lai_trang_thai_thu(db, p)
    _ghi_log(db, p, user, "fin_undo")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- tài xế báo hỏng → admin duyệt → vào mục V
@router.post("/api/trips/{tid}/bao-hong")
def bao_hong(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """TÀI XẾ báo sự cố / hỏng xe trên đường, kèm số tiền dự kiến. Chỉ là BÁO — chưa thành chi phí.
    Admin hoặc Bãi duyệt (đường /duyet bên dưới) mới sinh dòng chi vào mục V với số tiền đã duyệt."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tài xế của phiếu (hoặc Bãi) báo hỏng."})
    _cua_tai_xe(db, p, user)
    if p.transport_status == "arrived" or p.finance_status == "paid":
        raise HTTPException(409, {"ma": "PHIEU_DA_XONG", "loi": "Phiếu đã về / đã thu tiền, không báo hỏng nữa."})
    lt = data.get("incident_type") or "breakdown"
    if lt not in LOAI_SU_CO:
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "incident_type phải là %s." % ", ".join(LOAI_SU_CO)})
    ghi = (data.get("note") or "").strip()
    if not ghi:
        raise HTTPException(422, {"ma": "THIEU_MO_TA", "loi": "Báo hỏng phải ghi hỏng gì."})
    tien = _so(data.get("reported_cost"), "reported_cost")
    e = TripEvent(trip_id=p.id, kind="incident", incident_type=lt, note=ghi, by_user=user.full_name,
                  status="reported", reported_cost=tien, currency=str(data.get("currency") or "LAK").upper())
    if data.get("stop_seq") not in (None, ""):
        e.stop_seq = int(data["stop_seq"])
    db.add(e)
    _ghi_log(db, p, user, "ev_reported")
    db.commit()
    return xuat_phieu(db, p)


def _duyet_do_dau(db, p, e, data, user):
    """Duyệt khai đổ dầu của tài xế → một dòng mục III, nguồn MUA (không đụng kho).

    Số lít và đơn giá lấy theo số tài xế khai, người duyệt sửa được. Tiền tệ thường là VND vì dầu
    mua bên Việt Nam; quy đổi về LAK dùng tỷ giá ghi trên chính phiếu này.
    """
    lit = _so(data.get("qty_l"), "qty_l") or e.qty_l or 0
    gia = _so(data.get("unit_price"), "unit_price")
    if gia is None:
        gia = e.reported_cost or 0
    if lit <= 0 or gia <= 0:
        raise HTTPException(422, {"ma": "THIEU_SO", "loi": "Phải có số lít và đơn giá lớn hơn 0."})
    diem = db.get(FuelPlace, e.place_id) if e.place_id else None
    so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "fuel").count()
    dong = TripExpense(trip_id=p.id, section="fuel", line_no=so_dong + 1, item_key="diesel",
                       qty=lit, unit_price=gia, currency=str(data.get("currency") or e.currency or "VND").upper(),
                       place=None, place_id=e.place_id, supplier_id=e.supplier_id, paid_by_epl=True, source="mua",
                       acct_code=ma_tk_mac_dinh(p.company, "fuel", "mua"),
                       note="Tài xế đổ dọc đường%s%s" % (" tại " + diem.name if diem else "",
                                                         " — " + e.note if e.note else ""))
    db.add(dong); db.flush()
    e.status, e.expense_id = "approved", dong.id
    muc = _muc_cua(db, p)["fuel"]
    if muc.status not in ("wait", "entered"):
        _ghi_log(db, p, user, "sec_fuel:reopen")
    muc.status = "entered"
    _ghi_log(db, p, user, "ev_refuel_approved")
    db.commit()
    return xuat_phieu(db, p)


@router.post("/api/trips/{tid}/bao-nhien-lieu")
def bao_nhien_lieu(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """TÀI XẾ khai đổ dầu DỌC ĐƯỜNG — chiều về từ Việt Nam phải mua dầu chạy về.

    Đây là dầu MUA NGOÀI, không phải lĩnh kho, nên không có phiếu xuất kho: nó thành một dòng chi
    mục III nguồn "mua", định khoản …/402, và ghi rõ mua ở trạm nào của nhà cung cấp nào. Khai xong
    chỉ là BÁO, kế toán duyệt mới thành dòng chi thật — giống hệt cách báo hỏng.
    """
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("driver", "yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ tài xế của phiếu (hoặc Bãi) khai đổ dầu."})
    _cua_tai_xe(db, p, user)
    if p.finance_status == "paid":
        raise HTTPException(409, {"ma": "PHIEU_DA_XONG", "loi": "Phiếu đã thu tiền xong, không khai thêm."})
    lit = _so(data.get("qty_l"), "qty_l") or 0
    if lit <= 0:
        raise HTTPException(422, {"ma": "THIEU_SO_LIT", "loi": "Phải khai đổ bao nhiêu lít."})
    diem = db.get(FuelPlace, data.get("place_id") or "")
    if not diem:
        raise HTTPException(422, {"ma": "THIEU_NOI_DO", "loi": "Phải chọn nơi đổ."})
    if diem.owner_type == "epl":
        raise HTTPException(422, {"ma": "NOI_DO_LA_KHO",
                                  "loi": "%s là kho của công ty, lĩnh dầu ở kho thì dùng phiếu lĩnh." % diem.name})
    e = TripEvent(trip_id=p.id, kind="refuel", note=(data.get("note") or "").strip() or None,
                  by_user=user.full_name, status="reported", qty_l=lit,
                  reported_cost=_so(data.get("unit_price"), "unit_price") or 0,
                  currency=str(data.get("currency") or "VND").upper(), place_id=diem.id,
                  supplier_id=(data.get("supplier_id") or diem.supplier_id or None))
    db.add(e)
    _ghi_log(db, p, user, "ev_refuel_reported")
    db.commit()
    return xuat_phieu(db, p)


@router.post("/api/trips/{tid}/events/{eid}/duyet")
def duyet_bao_hong(tid: str, eid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """TỔ SỬA CHỮA duyệt báo hỏng của tài xế → mở phiếu, thêm dòng sửa chữa vào mục V với số tiền duyệt
    (mặc định = số tài xế báo). Nguồn: kho (chọn phụ tùng, trừ tồn ngay) hoặc mua ngoài. Hoặc TỪ CHỐI.

    Người duyệt là **tổ sửa chữa Thà Bốc** (`repair`), không phải Admin Bãi: anh Khampla C1.2 nói tổ sửa
    là người riêng, và chính họ mới biết hỏng gì, lấy phụ tùng kho hay mang ra gara.

    Khai đổ dầu dọc đường (kind='refuel') cũng duyệt ở đây, nhưng rơi vào MỤC III nguồn mua nên vẫn do
    Bãi hoặc KT kho xăng dầu duyệt."""
    p = db.get(Trip, tid)
    e = db.get(TripEvent, eid)
    if not p or not e or e.trip_id != p.id:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có báo hỏng này."})
    duoc = ("yard", "fuel", "admin") if e.kind == "refuel" else ("repair", "admin")
    if user.role not in duoc:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                  "loi": "Vai %s không được duyệt khai báo này." % user.role})
    if e.status != "reported":
        raise HTTPException(409, {"ma": "DA_XU_LY", "loi": "Báo hỏng này đã được xử lý (%s)." % e.status})
    e.approved_by, e.approved_at = user.full_name, dt.datetime.utcnow()
    if data.get("reject"):
        e.status = "rejected"; e.note = (e.note or "") + (" — " + data["reason"] if data.get("reason") else "")
        _ghi_log(db, p, user, "ev_rejected"); db.commit()
        return xuat_phieu(db, p)
    if e.kind == "refuel":
        return _duyet_do_dau(db, p, e, data, user)
    source = data.get("source") or "mua"
    if source not in ("kho", "mua"):
        raise HTTPException(422, {"ma": "NGUON_SAI", "loi": "Nguồn phải là kho hay mua."})
    qty = _so(data.get("qty"), "qty") or 1
    gia = _so(data.get("unit_price"), "unit_price")
    tien_te = str(data.get("currency") or e.currency or "LAK").upper()
    part = None
    if source == "kho":
        part = db.get(Part, data.get("part_id") or "")
        if not part:
            raise HTTPException(422, {"ma": "THIEU_PHU_TUNG", "loi": "Lấy từ kho thì phải chọn phụ tùng."})
        if (part.qty or 0) < qty:
            raise HTTPException(409, {"ma": "KHONG_DU", "loi": "Kho chỉ còn %s %s." % (part.qty, part.name)})
        if gia is None: gia = part.unit_price or 0
    if gia is None:
        gia = e.reported_cost if e.reported_cost is not None else None
    if gia is None:
        raise HTTPException(422, {"ma": "THIEU_GIA", "loi": "Chưa có số tiền: tài xế không báo và người duyệt chưa nhập."})
    so_dong = db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "repair").count()
    dong = TripExpense(trip_id=p.id, section="repair", line_no=so_dong + 1, item_key=None,
                       item_name=(data.get("item_name") or (part.name if part else e.note))[:120],
                       qty=qty, unit_price=gia, currency=tien_te, paid_by_epl=True, source=source,
                       part_id=part.id if part else None, acct_code=ma_tk_mac_dinh(p.company, "repair", source), note=e.note)
    db.add(dong); db.flush()
    if part:
        mv = PartMove(part_id=part.id, move_date=dt.date.today(), kind="out", qty=qty, truck_no=p.truck_no, trip_doc_no=p.doc_no,
                      note="Sửa xe trên đường (tài xế báo) — %s" % (e.note or ""), by_user=user.full_name, expense_id=dong.id)
        part.qty = (part.qty or 0) - qty; part.last_date = dt.date.today(); part.last_truck = p.truck_no
        db.add(mv); db.flush(); dong.stock_move_id = mv.id
        CT.ghi(db, "PXK_PT", nguon_bang="part_moves", nguon_id=mv.id, trip=p, ngay=mv.move_date, doi_tuong_loai="kho",
               doi_tuong_ten=part.name, tien=qty * (dong.unit_price or 0), tien_te=dong.currency, tien_lak=tien_dong(p, dong),
               section="repair", by_user=user.full_name, mo_ta="Xuất %s %s sửa xe %s" % (qty, part.name, p.truck_no),
               payload={"part_id": part.id, "qty": qty, "unit_price": dong.unit_price, "currency": dong.currency, "truck_no": p.truck_no})
    e.status = "approved"; e.kind = "repair"; e.expense_id = dong.id
    s = _muc_cua(db, p)["repair"]
    if s.status not in ("wait", "entered"):
        _ghi_log(db, p, user, "sec_repair:reopen")
    s.status = "entered"
    if p.vehicle_id and e.incident_type == "breakdown":
        x = db.get(Vehicle, p.vehicle_id)
        if x: x.status = "maintenance"
    _ghi_log(db, p, user, "ev_approved")
    db.commit()
    return xuat_phieu(db, p)


# ---------------------------------------------------------------- chứng từ: phiếu chi tạm ứng & phiếu thu
@router.get("/api/trips/{tid}/phieu-chi")
def phieu_chi(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """PHIẾU CHI TẠM ỨNG cho tài xế — sinh ngay từ phiếu xuất xe: mọi khoản tiền mặt EPL ứng (dầu đổ
    trạm ngoài, đi đường, khác); KHÔNG gồm dầu kho và phụ tùng kho (đó là phiếu xuất kho). Trạng thái
    duyệt lấy theo mục IV của phiếu: đã nhập → đã kiểm → đã ghi sổ → đã chi (tài xế đã cầm tiền)."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    _cua_tai_xe(db, p, user)
    dong = _dong_tam_ung(p, _dong_chi(db, p))
    r = {"USD": p.rate_usd or 22000, "THB": p.rate_thb or 700, "VND": p.rate_vnd or 1.2, "LAK": 1.0}
    ds = []
    tong = 0.0
    for d in dong:
        lak = (d.qty or 0) * (d.unit_price or 0) * r.get((d.currency or "LAK").upper(), 1.0)
        tong += lak
        ds.append({"section": d.section, "item_key": d.item_key, "item_name": d.item_name, "qty": d.qty, "unit_price": d.unit_price,
                   "currency": d.currency, "acct_code": d.acct_code, "tien_lak": round(lak)})
    tt = {s.section: s.status for s in _muc_cua(db, p).values()}
    return {"doc_no": p.doc_no, "so_phieu_chi": "PC-" + p.doc_no.replace("/", "-"), "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "driver_name": p.driver_name, "truck_no": p.truck_no, "plate_head": p.plate_head, "plate_trailer": p.plate_trailer,
            "origin": p.origin, "destination": p.destination, "company": p.company, "owner_name": p.owner_name,
            "dong": ds, "tong_lak": round(tong), "trang_thai": tt.get("travel", "wait"),
            "tra_tien_xong": tt.get("travel") == "paid", "created_by": p.created_by}


@router.get("/api/trips/{tid}/phieu-thu")
def phieu_thu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """PHIẾU THU tiền khách theo hoá đơn vận chuyển — định khoản 1211/70 như quy trình của họ."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role == "driver":
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế không xem phiếu thu."})
    k = tinh_phieu(p, _dong_chi(db, p), _da_thu(db, p))
    return {"doc_no": p.doc_no, "so_phieu_thu": "PT-" + p.doc_no.replace("/", "-"), "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "customer_name": p.customer_name, "origin": p.origin, "destination": p.destination, "truck_no": p.truck_no,
            "tan_tinh": k["tan_tinh"], "don_gia": p.price, "ccy": k["ccy"],
            "doanh_thu": k["doanh_thu"], "doanh_thu_lak": k["doanh_thu_lak"],
            "da_thu": k["da_thu"], "da_thu_lak": k["da_thu_lak"], "con_lai": k["con_lai"], "con_lai_lak": k["con_lai_lak"],
            "rate_to_lak": ty_gia(p, k["ccy"]), "acct_code": "1211/70", "invoiced": p.invoiced,
            "finance_status": p.finance_status, "trans_status": _muc_cua(db, p)["trans"].status,
            "thu_tien": [_xuat_thu(x) for x in db.query(TripPayment).filter(TripPayment.trip_id == p.id)
                         .order_by(TripPayment.pay_date, TripPayment.created_at).all()]}


@router.delete("/api/trips/{tid}")
def xoa_phieu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Chỉ xoá được phiếu chưa mục nào qua bước kiểm và chưa xuất kho gì — đã kiểm là chứng từ, không xoá."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Admin Thà Bốc hoặc Sếp xoá phiếu."})
    if any(s.status not in ("wait", "entered") for s in _muc_cua(db, p).values()) and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_DUYET", "loi": "Phiếu đã có mục được kiểm, không xoá được."})
    if any(e.stock_move_id for e in _dong_chi(db, p)) and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_XUAT_KHO", "loi": "Phiếu đã có dòng xuất kho, không xoá được."})
    _chan_khoa(p, user)
    KH.kiem_xoa(db, p)
    _doi_trang_thai_xe_tai_xe(db, p, "available", "available")
    db.query(TripEvent).filter(TripEvent.trip_id == p.id).delete()
    for a in db.query(TripAttachment).filter(TripAttachment.trip_id == p.id).all():
        _xoa_tep_dia(a); db.delete(a)
    db.query(TripExpense).filter(TripExpense.trip_id == p.id).delete()
    db.query(TripSection).filter(TripSection.trip_id == p.id).delete()
    db.query(TripLog).filter(TripLog.trip_id == p.id).delete()
    CT.rut(db, trip_id=p.id)
    db.delete(p); db.commit()
    return {"ok": True}
