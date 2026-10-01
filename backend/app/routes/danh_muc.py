# -*- coding: utf-8 -*-
"""Dữ liệu gốc: khách hàng · xe (đầu kéo) · rơ-moóc · tài xế & bằng lái · tỷ giá.

Xe và tài xế mang sang từ module của EPL_System theo yêu cầu bên Lào, cắt những gì họ không
dùng (tốc độ, ETA, GPS, ca kíp, tổ đội). Thêm RƠ-MOÓC là thực thể riêng: hư rơ-moóc này thì
tháo ra lắp cái khác vào đầu kéo, có lịch sử lắp/tháo.

Mỗi danh mục: xem · thêm · sửa · ngưng dùng (không xoá cứng — phiếu cũ còn trỏ tới).
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import (CACH_XUAT_HOA_DON, CACH_TINH_CUOC, TIEN_TE, TRANG_THAI_TAI_XE, TRANG_THAI_XE, Customer, CustomerRate, Driver, DriverLicense, ExchangeRate, Owner,
                    ExchangeRateLog,
                    Route, Trailer, TrailerAssignment, Trip, TripExpense, Vehicle)
from services import goi_ke_toan as KT
from services import gui_tune as GT
from services import tai_khoan as TK
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_gia_kho, thay_tien_chi
from routes import anh as ANH
from services.tinh_toan import tien_dong

router = APIRouter()
SUA_DANH_MUC = can_vai("yard", "acct")       # Bãi và Kế toán được sửa danh mục
SUA_BANG_GIA = can_vai("acct", "admin")      # giá là tiền: chỉ KT Thu/Chi VC (người kiểm mục II) và Sếp
XEM_BANG_GIA = can_vai("acct", "expacct", "rev", "treasury", "cash", "admin")   # Bãi không thấy tiền
# Mã khách = mã khách bên kế toán (nối sang sổ công nợ anh Tune). Excel "ໜ້າວຽກ": ລົງຂໍ້ມູນ ລູກຄ້າ — Bãi Thà Bốc nhập,
# ບັນຊີລາຍຈ່າຍ/ຮັບ ວຽງຈັນ (KT Thu/Chi VC) xác nhận → Bãi nhập thông tin khách, còn MÃ do KT Thu/Chi VC hoặc Sếp gán (30/09).
GAN_MA_KHACH = ("acct", "admin")
NGAY_CANH_BAO = 30                            # giấy tờ hết hạn trong 30 ngày → cờ vàng


def _dict(o):
    ra = {}
    for c in o.__table__.columns:
        v = getattr(o, c.name)
        ra[c.name] = v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v
    return ra


def _ngay(v, ten):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ô %s phải là ngày YYYY-MM-DD." % ten})


def _so(v, ten):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số." % ten})


def _ap(o, data, cot, ngay=(), so=()):
    for k in cot:
        if k not in data:
            continue
        v = data[k]
        if k in ngay: v = _ngay(v, k)
        elif k in so: v = _so(v, k)
        elif isinstance(v, str): v = v.strip() or None
        setattr(o, k, v)


def _ty_gia_sc(db, ma):
    """Tỷ giá đang áp dụng — dòng của lệnh sửa chữa không gắn phiếu nên không có tỷ giá khoá."""
    ma = (ma or "LAK").upper()
    if ma == "LAK":
        return 1.0
    r = db.get(ExchangeRate, ma)
    return float(r.rate_to_lak) if r and r.rate_to_lak else {"USD": 22000, "THB": 700, "VND": 1.2, "CNY": 3000}.get(ma, 1)


def _han(ngay):
    """Trạng thái giấy tờ: expired · soon · ok · none."""
    if not ngay:
        return "none"
    con = (ngay - dt.date.today()).days
    return "expired" if con < 0 else ("soon" if con <= NGAY_CANH_BAO else "ok")


# ================================================================ khách hàng
@router.get("/api/customers")
def ds_khach(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [_dict(c) for c in db.query(Customer).order_by(Customer.active.desc(), Customer.name).all()]


@router.post("/api/customers")
def them_khach(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    if not str(data.get("name") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Khách hàng phải có tên."})
    c = Customer(); _ap(c, data, ("name", "phone", "address", "note"))
    _ap_cach_hoa_don(c, data)
    _ap_ma_loai(db, c, data, user)
    db.add(c); db.commit(); db.refresh(c)
    return _dict(c)


LOAI_KHACH = ("person", "company")


def _ap_ma_loai(db, c, data, user):
    """MÃ KHÁCH = mã khách bên kế toán (anh Tune, OBJ_OBJECTNO ≤ 50 ký tự) — chủ dự án chốt 30/09 dùng một ô chung; gửi đi
    trong phiếu đề nghị thu / bàn giao DO nên theo đúng luật mã bên đó (`gui_tune.loi_ma_khach`), không trùng khách khác. Chỉ vai trong
    GAN_MA_KHACH gán / đổi mã; vai khác gửi lại đúng mã đang có thì bỏ qua (form sửa gửi cả ô). Loại khách: cá nhân · công ty."""
    if "code" in data:
        ma = str(data.get("code") or "").strip()
        if ma != (c.code or "") and user.role not in GAN_MA_KHACH:
            raise HTTPException(403, {"ma": "MA_KHACH_KE_TOAN",
                                      "loi": "Mã khách là mã bên kế toán — chỉ KT Thu/Chi Viêng Chăn hoặc Sếp gán / đổi."})
        if ma:
            if GT.loi_ma_khach(ma):
                raise HTTPException(422, {"ma": "MA_KHACH_SAI", "loi": GT.loi_ma_khach(ma)})
            trung = (db.query(Customer.id).filter(func.lower(Customer.code) == ma.lower(), Customer.id != (c.id or "")).first())
            if trung:
                raise HTTPException(409, {"ma": "MA_KHACH_TRUNG", "loi": "Mã khách %s đã dùng cho khách khác." % ma})
        c.code = ma or None
    if "cust_type" in data:
        v = (data.get("cust_type") or "").strip().lower() or None
        if v and v not in LOAI_KHACH:
            raise HTTPException(422, {"ma": "LOAI_KHACH_SAI", "loi": "Loại khách phải là cá nhân hoặc công ty."})
        c.cust_type = v


def _ap_cach_hoa_don(c, data):
    """Cờ `invoice_mode` (C8.2): phieu = mỗi phiếu một hoá đơn · thang = gộp một tờ cuối tháng."""
    if "invoice_mode" not in data:
        return
    v = (data.get("invoice_mode") or "phieu").strip().lower()
    if v not in CACH_XUAT_HOA_DON:
        raise HTTPException(422, {"ma": "CACH_HOA_DON_SAI", "loi": "Cách xuất hoá đơn phải là %s." % " · ".join(CACH_XUAT_HOA_DON)})
    c.invoice_mode = v


@router.put("/api/customers/{cid}")
def sua_khach(cid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    c = db.get(Customer, cid)
    if not c:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    _ap_ma_loai(db, c, data, user)             # kiểm quyền mã TRƯỚC khi ghi ô khác — bị chặn thì không đổi gì
    _ap(c, data, ("name", "phone", "address", "note", "active"))
    _ap_cach_hoa_don(c, data)
    db.commit(); db.refresh(c)
    return _dict(c)


# ================================================================ bảng giá khách × tuyến (K3)
def tim_gia(db, customer_id, route_id, goods_type=None, ngay=None):
    """Dòng giá mới nhất còn hiệu lực cho khách × tuyến (× loại hàng) tại ngày `ngay`. Không có thì None."""
    if not customer_id or not route_id:
        return None
    ngay = ngay or dt.date.today()
    q = (db.query(CustomerRate).filter(CustomerRate.customer_id == customer_id, CustomerRate.route_id == route_id,
                                        CustomerRate.active.is_(True)))
    ds = [r for r in q.all() if r.valid_from is None or r.valid_from <= ngay]
    if goods_type:
        cung = [r for r in ds if r.goods_type == goods_type]
        ds = cung or [r for r in ds if r.goods_type == "iron_ore"]   # không có giá riêng loại hàng → dùng giá quặng
    if not ds:
        return None
    ds.sort(key=lambda r: (r.valid_from or dt.date.min, r.created_at or dt.datetime.min), reverse=True)
    return ds[0]


def _xuat_gia(db, r):
    d = _dict(r)
    t = db.get(Route, r.route_id); k = db.get(Customer, r.customer_id)
    d["route_name"] = t.name if t else None
    d["customer_name"] = k.name if k else None
    return d


def _tien_te(v, ten, mac_dinh=None):
    """Ô chọn tiền tệ của hợp đồng. Gõ mã lạ thì báo rõ — nhầm tiền là nhầm tiền thật."""
    if v in (None, ""):
        return mac_dinh
    m = str(v).strip().upper()
    if m not in TIEN_TE:
        raise HTTPException(422, {"ma": "TIEN_TE_SAI", "loi": "Ô %s phải là một trong %s, nhận '%s'." % (ten, ", ".join(TIEN_TE), v)})
    return m


def _ap_gia(db, r, data):
    if "route_id" in data:
        if not db.get(Route, data["route_id"] or ""):
            raise HTTPException(422, {"ma": "TUYEN_SAI", "loi": "Không có tuyến này."})
        r.route_id = data["route_id"]
    if "goods_type" in data: r.goods_type = (data["goods_type"] or "iron_ore").strip()
    # Hợp đồng ký bằng tiền gì thì bảng giá ghi tiền đó: khách Trung Quốc trả Nhân dân tệ, khách
    # trong nước trả Kíp. Không quy đổi sẵn về USD — quy đổi sẵn là mất con số hai bên đã ký.
    if "price_ccy" in data: r.price_ccy = _tien_te(data["price_ccy"], "price_ccy", "USD")
    if "price_mode" in data:
        m = (str(data["price_mode"] or "ton").strip().lower() or "ton")
        if m not in CACH_TINH_CUOC:
            raise HTTPException(422, {"ma": "CACH_TINH_SAI", "loi": "Cách tính phải là 'ton' hoặc 'chuyen'."})
        r.price_mode = m
    if "hire_ccy" in data: r.hire_ccy = _tien_te(data["hire_ccy"], "hire_ccy")
    if "price" in data:
        gia = _so(data["price"], "price")
        if gia is None or gia <= 0:
            raise HTTPException(422, {"ma": "GIA_SAI", "loi": "Đơn giá mỗi tấn phải lớn hơn 0."})
        r.price = gia
    if "hire_price" in data: r.hire_price = _so(data["hire_price"], "hire_price")
    if "valid_from" in data: r.valid_from = _ngay(data["valid_from"], "valid_from")
    if "note" in data: r.note = (data["note"] or "").strip() or None
    if "active" in data: r.active = bool(data["active"])


@router.get("/api/customers/{cid}/cong-no-ke-toan")
def cong_no_khach_ke_toan(cid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Công nợ của khách BÊN HỆ KẾ TOÁN anh Tune (01/10, chỉ xem): SO bên đó sinh từ phiếu đề nghị thu, các lần thu tiền bên
    đó. Khách chưa có mã bên kế toán → {"co": false}. Không vào được bên đó → 502 báo rõ, màn vẫn hiện phần còn lại."""
    from services import chi_tune as CHI
    from services.phan_quyen import thay_tien_ban
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem công nợ khách." % user.role})
    kh = db.get(Customer, cid)
    if not kh:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    kq = CHI.cong_no_khach(db, kh)
    if kq is not None:
        # đọc rồi thì chép luôn thu tiền vào từng SO của khách (bản đọc lại — màn Đề nghị thu, cột trái màn Khách hàng dùng)
        from models import GuiSoTune
        from services import de_nghi_thu as DNT
        so = {}
        for b, p in (db.query(GuiSoTune, Trip).join(Trip, Trip.id == GuiSoTune.trip_id)
                     .filter(Trip.customer_id == kh.id, GuiSoTune.status == "synced").all()):
            cu = (b.thu_trang_thai, b.thu_da_thu, b.thu_con_no)
            DNT.ap_thu(b, kq.get("no") or [], kq.get("don") or [])
            if b.thu_trang_thai in DNT.TAI_CHINH:
                p.finance_status = DNT.TAI_CHINH[b.thu_trang_thai]
            if (b.thu_trang_thai, b.thu_da_thu, b.thu_con_no) != cu:
                p.updated_at = dt.datetime.utcnow()         # bộ đệm báo cáo tháng tính lại
            if b.order_code:
                so[b.order_code] = {"trip_id": p.id, "doc_no": p.doc_no}
        db.commit()
        kq["do_cua_so"] = so                                     # SO bên đó ↔ DO bên em
    return {"co": kq is not None, **(kq or {})}


@router.get("/api/customers-cong-no")
def cong_no_moi_khach(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Công nợ GỌN của mọi khách một lần — cột trái màn Khách hàng (nút lọc "Còn nợ"). Từ 01/10 (bỏ trang kế toán tạm, số bên
    đó là số thử) công nợ khách CHỈ ở hệ anh Tune: đây cộng các SO bên đó đã tạo cho DO của từng khách (gui_so_tune) theo BẢN ĐỌC
    LẠI thu tiền gần nhất (de_nghi_thu.doc_thu_tune) — không gọi mạng, nên một trang nhiều khách vẫn nhanh. SO chưa đọc lại lần
    nào thì tính còn nợ cả SO (`chua_doc` đếm số SO đó); số chính xác của một khách: /api/customers/{cid}/cong-no-ke-toan.
    Vai không thấy tiền bán thì 403."""
    from models import GuiSoTune
    from services.phan_quyen import thay_tien_ban
    from services.tinh_toan import ty_gia
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem công nợ khách." % user.role})
    ra = {}
    for b, p in (db.query(GuiSoTune, Trip).join(Trip, Trip.id == GuiSoTune.trip_id)
                 .filter(GuiSoTune.status == "synced", Trip.customer_id.isnot(None)).all()):
        o = ra.setdefault(p.customer_id, {"so_to": 0, "so_to_no": 0, "tong_tien": {}, "con_no_tien": {}, "tong_lak": 0,
                                          "da_thu_lak": 0, "con_no_lak": 0, "chua_doc": 0, "doc_luc": None,
                                          "nguon": "he_ke_toan"})
        ccy = (b.currency or p.price_ccy or "USD").upper()
        tong = float(b.thu_tong if b.thu_tong is not None else (b.total_amount or 0))
        da = float(b.thu_da_thu or 0)
        con = float(b.thu_con_no) if b.thu_con_no is not None else max(0.0, tong - da)
        r = ty_gia(p, ccy)
        o["so_to"] += 1
        o["tong_tien"][ccy] = round(o["tong_tien"].get(ccy, 0) + tong, 2)
        o["tong_lak"] += round(tong * r)
        o["da_thu_lak"] += round(da * r)
        if con > 0.005:
            o["so_to_no"] += 1
            o["con_no_tien"][ccy] = round(o["con_no_tien"].get(ccy, 0) + con, 2)
            o["con_no_lak"] += round(con * r)
        if b.thu_doc_luc is None:
            o["chua_doc"] += 1
        elif o["doc_luc"] is None or b.thu_doc_luc < o["doc_luc"]:
            o["doc_luc"] = b.thu_doc_luc                                    # lần đọc CŨ nhất trong các SO của khách
    for o in ra.values():
        o["doc_luc"] = o["doc_luc"].isoformat(timespec="minutes") + "+00:00" if o["doc_luc"] else None
    return ra


@router.get("/api/customers/{cid}/bang-gia")
def ds_gia(cid: str, db: Session = Depends(get_db), _=Depends(XEM_BANG_GIA)):
    if not db.get(Customer, cid):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    ds = db.query(CustomerRate).filter(CustomerRate.customer_id == cid).all()
    ds.sort(key=lambda r: (not r.active, r.route_id, -(r.valid_from or dt.date.min).toordinal()))
    return [_xuat_gia(db, r) for r in ds]


@router.post("/api/customers/{cid}/bang-gia")
def them_gia(cid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_BANG_GIA)):
    if not db.get(Customer, cid):
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    if not data.get("route_id"):
        raise HTTPException(422, {"ma": "THIEU_TUYEN", "loi": "Phải chọn tuyến."})
    if "price" not in data:
        raise HTTPException(422, {"ma": "GIA_SAI", "loi": "Phải có đơn giá mỗi tấn."})
    r = CustomerRate(customer_id=cid, created_by=user.full_name); _ap_gia(db, r, data)
    db.add(r); db.commit(); db.refresh(r)
    return _xuat_gia(db, r)


@router.put("/api/bang-gia/{gid}")
def sua_gia(gid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_BANG_GIA)):
    r = db.get(CustomerRate, gid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có dòng giá này."})
    _ap_gia(db, r, data); db.commit(); db.refresh(r)
    return _xuat_gia(db, r)


@router.delete("/api/bang-gia/{gid}")
def xoa_gia(gid: str, db: Session = Depends(get_db), _=Depends(SUA_BANG_GIA)):
    r = db.get(CustomerRate, gid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có dòng giá này."})
    db.delete(r); db.commit()
    return {"ok": True}


@router.get("/api/bang-gia/tra")
def tra_gia(customer_id: str, route_id: str, goods_type: str = None, ngay: str = None,
            db: Session = Depends(get_db), _=Depends(XEM_BANG_GIA)):
    """Màn phiếu hỏi: khách này đi tuyến này giá bao nhiêu? Trả {} nếu chưa có trong bảng."""
    r = tim_gia(db, customer_id, route_id, goods_type, _ngay(ngay, "ngay") if ngay else None)
    return _xuat_gia(db, r) if r else {}


# ================================================================ xe (đầu kéo)
COT_XE = ("truck_no", "brand_model", "year", "plate_head", "owner_type", "owner_id", "owner_name", "engine_no", "chassis_no",
          "insurance_exp", "inspection_exp", "road_permit_exp", "odometer_km", "next_service_km", "status", "depot", "note",
          "service_date", "fuel_norm", "capacity_t", "inspection_place", "engine_cap", "box_size", "tyre")
NGAY_XE = ("insurance_exp", "inspection_exp", "road_permit_exp", "service_date")
SO_XE = ("year", "odometer_km", "next_service_km", "fuel_norm", "capacity_t")


def xuat_xe(db, v, chi_tiet=False, vai=None):
    r = _dict(v)
    r["giay_to"] = {"insurance": _han(v.insurance_exp), "inspection": _han(v.inspection_exp), "road_permit": _han(v.road_permit_exp)}
    r["can_bao_duong"] = bool(v.odometer_km and v.next_service_km and v.odometer_km >= v.next_service_km)
    if v.trailer_id:
        t = db.get(Trailer, v.trailer_id)
        r["trailer"] = _dict(t) if t else None
    if chi_tiet:
        # Chi phí sửa chữa của xe này — gom từ mục V các phiếu (không có bảng bảo dưỡng riêng)
        sua = []
        for e, p in (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
                     .filter(Trip.vehicle_id == v.id, TripExpense.section == "repair").order_by(Trip.doc_date.desc()).limit(50).all()):
            sua.append({"doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None, "item_key": e.item_key,
                        "item_name": e.item_name, "qty": e.qty, "unit_price": e.unit_price, "currency": e.currency,
                        "source": e.source, "acct_code": TK.tk_dong(p.company, e), "tien_lak": round(tien_dong(p, e))})
        # Gộp thêm LỆNH SỬA CHỮA RIÊNG (C7.3): xe nằm bãi đại tu hay bảo dưỡng định kỳ không gắn
        # phiếu nào, nhưng vẫn là tiền sửa của chính chiếc xe này — tab Sửa chữa phải thấy cả hai nguồn.
        # Lệnh ở trang kế toán từ 28/09 (đợt 6): hỏi bên đó; bên đó tắt thì màn Xe vẫn mở, báo rõ phần thiếu.
        r["sua_chua_lenh_loi"] = None
        try:
            for e in KT.goi(db, "GET", "/api/lien-thong/sua-chua/xe/" + v.id) or []:
                e["tien_lak"] = round((e.get("qty") or 0) * (e.get("unit_price") or 0) * _ty_gia_sc(db, e.get("currency")))
                sua.append(e)
        except HTTPException as loi:
            r["sua_chua_lenh_loi"] = (loi.detail or {}).get("loi") if isinstance(loi.detail, dict) else str(loi.detail)
        sua.sort(key=lambda x: x["doc_date"] or "", reverse=True)
        if vai is not None:
            # Bãi không thấy tiền sửa (A2 · 23/09); thủ kho, tổ sửa chữa không thấy giá vốn dòng lấy kho (30/09)
            for x in sua:
                if not thay_tien_chi(vai) or (x.get("source") == "kho" and not thay_gia_kho(vai)):
                    x["unit_price"] = None; x["tien_lak"] = None
        r["sua_chua"] = sua
        r["anh_chinh"] = ANH.anh_chinh(ANH.XE, db, v.id)
        r["anh"] = ANH.ds_anh(ANH.XE, db, v.id)
        r["so_phieu"] = db.query(Trip).filter(Trip.vehicle_id == v.id).count()
        # Phiếu gần đây của xe này — màn Xe cần để bấm sang phiếu, và để biết xe đang chạy phiếu nào.
        ds_phieu = (db.query(Trip).filter(Trip.vehicle_id == v.id).order_by(Trip.doc_date.desc(), Trip.doc_no.desc()).limit(12).all())
        r["phieu_gan_day"] = [{"doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
                               "customer_name": p.customer_name, "origin": p.origin, "destination": p.destination,
                               "weight": p.weight_dest if p.weight_dest is not None else p.weight_origin,
                               "transport_status": p.transport_status, "finance_status": p.finance_status}
                              for p in ds_phieu]
        dang = next((p for p in ds_phieu if p.transport_status != "arrived"), None)
        r["phieu_hien_tai"] = dang.doc_no if dang else None
        r["lich_su_ro_mooc"] = [{"trailer_id": a.trailer_id, "plate": (db.get(Trailer, a.trailer_id) or Trailer()).plate,
                                 "attached_at": a.attached_at.isoformat() if a.attached_at else None,
                                 "detached_at": a.detached_at.isoformat() if a.detached_at else None, "reason": a.reason, "by_user": a.by_user}
                                for a in db.query(TrailerAssignment).filter(TrailerAssignment.vehicle_id == v.id)
                                .order_by(TrailerAssignment.attached_at.desc()).limit(20).all()]
    return r


def _phu_xe(db, ds):
    """Số phiếu đã chạy và phiếu ĐANG chạy của nhiều xe — như _phu_tai_xe: hai truy vấn cho cả danh sách, không hỏi từng xe.
    Màn Xe cần hai số này ở bảng (cột trạng thái có số phiếu đang chạy, ô tìm theo số phiếu) — trước 01/10 chỉ hồ sơ có."""
    ids = [v.id for v in ds if v.id]
    if not ids:
        return {}, {}
    from services import dem_bao_cao as DEM
    tat = DEM.dem_phieu_theo(db, "sp-xe", Trip.vehicle_id)
    dem = {i: tat[i] for i in ids if i in tat}
    dang = {}
    for vid, so in (db.query(Trip.vehicle_id, Trip.doc_no).filter(Trip.vehicle_id.in_(ids), Trip.transport_status != "arrived")
                    .order_by(Trip.doc_date.desc(), Trip.doc_no.desc())):
        dang.setdefault(vid, so)
    return dem, dang


@router.get("/api/vehicles")
def ds_xe(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    ds = db.query(Vehicle).order_by(Vehicle.active.desc(), Vehicle.owner_type, Vehicle.truck_no).all()
    anh = ANH.anh_chinh_map(ANH.XE, db)      # ảnh đại diện lấy MỘT lượt cho cả danh sách
    dem, dang = _phu_xe(db, ds)
    ra = []
    for v in ds:
        r = xuat_xe(db, v)
        r["anh_chinh"] = anh.get(v.id)
        r["so_phieu"] = dem.get(v.id, 0)                 # cùng tên trường với hồ sơ một xe
        r["phieu_hien_tai"] = dang.get(v.id)
        ra.append(r)
    return ra


@router.get("/api/vehicles/{vid}")
def xem_xe(vid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    return xuat_xe(db, v, chi_tiet=True, vai=user.role)


def _kiem_xe(data, v):
    if not str(getattr(v, "truck_no", "") or "").strip():
        raise HTTPException(422, {"ma": "THIEU_SO_XE", "loi": "Xe phải có số hiệu (ເບີລົດ)."})
    if v.owner_type not in ("EPL", "joint"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "owner_type phải là EPL hoặc joint."})
    if v.owner_type == "joint" and not (v.owner_name or "").strip() and not v.owner_id:
        raise HTTPException(422, {"ma": "THIEU_CHU_XE", "loi": "Xe liên kết phải chọn chủ xe (hoặc ghi tên)."})
    if v.owner_type != "joint":
        v.owner_id = None
    if v.status not in TRANG_THAI_XE:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái xe phải là %s." % ", ".join(TRANG_THAI_XE)})


def _chep_ten_chu(db, v):
    """Chọn chủ xe từ danh mục thì tên chép theo danh mục — một nguồn, không gõ lệch."""
    if v.owner_id:
        o = db.get(Owner, v.owner_id)
        if not o:
            raise HTTPException(422, {"ma": "CHU_XE_SAI", "loi": "Không có chủ xe này trong danh mục."})
        v.owner_name = o.name


@router.post("/api/vehicles")
def them_xe(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    v = Vehicle(); _ap(v, data, COT_XE, NGAY_XE, SO_XE); v.status = v.status or "available"; v.owner_type = v.owner_type or "EPL"
    _chep_ten_chu(db, v)
    _kiem_xe(data, v)
    db.add(v); db.commit(); db.refresh(v)
    return xuat_xe(db, v)


@router.put("/api/vehicles/{vid}")
def sua_xe(vid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    _ap(v, data, COT_XE + ("active",), NGAY_XE, SO_XE)
    _chep_ten_chu(db, v)
    _kiem_xe(data, v)
    db.commit(); db.refresh(v)
    return xuat_xe(db, v)


# ================================================================ rơ-moóc
COT_RM = ("plate", "trailer_type", "capacity_t", "year", "owner_type", "owner_name", "insurance_exp", "inspection_exp",
          "status", "note", "depot", "chassis_no", "inspection_place")


def xuat_rm(db, t):
    r = _dict(t)
    r["giay_to"] = {"insurance": _han(t.insurance_exp), "inspection": _han(t.inspection_exp)}
    x = db.query(Vehicle).filter(Vehicle.trailer_id == t.id).first()
    r["dang_lap_xe"] = {"id": x.id, "truck_no": x.truck_no, "plate_head": x.plate_head} if x else None
    return r


@router.get("/api/trailers")
def ds_rm(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    return [xuat_rm(db, t) for t in db.query(Trailer).order_by(Trailer.active.desc(), Trailer.plate).all()]


@router.get("/api/trailers/{tid}")
def xem_rm(tid: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Một rơ-moóc kèm LỊCH SỬ lắp/tháo của chính nó — màn Xe cần để xem một cái rơ-moóc đã đi qua
    những đầu kéo nào, chứ không phải dò ngược từ từng xe."""
    t = db.get(Trailer, tid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có rơ-moóc này."})
    r = xuat_rm(db, t)
    r["lich_su_lap"] = [{"vehicle_id": a.vehicle_id, "truck_no": (db.get(Vehicle, a.vehicle_id) or Vehicle()).truck_no,
                         "attached_at": a.attached_at.isoformat() if a.attached_at else None,
                         "detached_at": a.detached_at.isoformat() if a.detached_at else None,
                         "reason": a.reason, "by_user": a.by_user}
                        for a in db.query(TrailerAssignment).filter(TrailerAssignment.trailer_id == t.id)
                        .order_by(TrailerAssignment.attached_at.desc()).limit(20).all()]
    return r


@router.post("/api/trailers")
def them_rm(data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    t = Trailer(); _ap(t, data, COT_RM, ("insurance_exp", "inspection_exp"), ("capacity_t", "year"))
    if not (t.plate or "").strip():
        raise HTTPException(422, {"ma": "THIEU_BIEN", "loi": "Rơ-moóc phải có biển số."})
    t.status = t.status or "available"; t.owner_type = t.owner_type or "EPL"
    db.add(t); db.commit(); db.refresh(t)
    return xuat_rm(db, t)


@router.put("/api/trailers/{tid}")
def sua_rm(tid: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    t = db.get(Trailer, tid)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có rơ-moóc này."})
    _ap(t, data, COT_RM + ("active",), ("insurance_exp", "inspection_exp"), ("capacity_t", "year"))
    # biển đổi thì cập nhật bản chép trên đầu kéo đang lắp
    x = db.query(Vehicle).filter(Vehicle.trailer_id == t.id).first()
    if x: x.plate_trailer = t.plate
    db.commit(); db.refresh(t)
    return xuat_rm(db, t)


@router.get("/api/vehicles/{vid}/lich")
def lich_xe(vid: str, tuan: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Lịch một tuần của xe: ngày nào chạy phiếu nào, ngày nào nằm sửa.

    Không có bảng lịch riêng — lịch chính là dữ liệu đã có: phiếu xuất xe trải từ ngày xuất tới ngày
    về, và các ngày có dòng chi sửa chữa (mục V) hoặc sự cố đã ghi. Ngày không có gì thì xe rảnh.
    """
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    try:
        d0 = dt.date.fromisoformat(tuan) if tuan else dt.date.today()
    except ValueError:
        raise HTTPException(422, {"ma": "TUAN_SAI", "loi": "Tuần phải ghi dạng YYYY-MM-DD."})
    d0 = d0 - dt.timedelta(days=d0.weekday())          # về thứ Hai
    d7 = d0 + dt.timedelta(days=6)
    theo_ngay = {}

    def them(ngay, loai, chu):
        if ngay and d0 <= ngay <= d7:
            theo_ngay.setdefault(ngay, []).append({"loai": loai, "text": chu})

    ten_tuyen = {r.id: r.name for r in db.query(Route).all()}
    for p in db.query(Trip).filter(Trip.vehicle_id == v.id).all():
        di = p.out_date or p.doc_date
        if not di:
            continue
        ve = p.back_date or (d7 if p.transport_status != "arrived" else di)
        # Phiếu cũ nhiều khi để trống điểm đi/đến vì đã chọn tuyến — lấy tên tuyến cho khỏi ra "· →"
        duong = ("%s → %s" % (p.origin, p.destination)) if (p.origin and p.destination) else (ten_tuyen.get(p.route_id) or "")
        chu = ("%s · %s" % (p.doc_no.replace("/EPL", ""), duong)).strip(" ·")
        n = di
        while n <= min(ve, d7):
            them(n, "trip", chu)
            n += dt.timedelta(days=1)
    for e, p in (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
                 .filter(Trip.vehicle_id == v.id, TripExpense.section == "repair").all()):
        them(p.doc_date, "rep", (e.item_name or e.item_key or "").strip() or "sửa chữa")
    return {"tu": d0.isoformat(), "den": d7.isoformat(),
            "ngay": [{"ngay": k.isoformat(), "su_kien": x} for k, x in sorted(theo_ngay.items())]}


@router.post("/api/vehicles/{vid}/trailer")
def lap_ro_mooc(vid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    """Lắp rơ-moóc vào đầu kéo. Rơ-moóc đang ở xe khác thì TỰ THÁO khỏi xe đó (ghi lịch sử) rồi lắp sang.
    Gửi trailer_id rỗng = tháo rơ-moóc hiện tại."""
    v = db.get(Vehicle, vid)
    if not v:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có xe này."})
    ly_do = (data.get("reason") or "").strip() or None
    bay_gio = dt.datetime.utcnow()

    def thao(xe):
        if not xe.trailer_id: return
        a = (db.query(TrailerAssignment).filter(TrailerAssignment.vehicle_id == xe.id, TrailerAssignment.trailer_id == xe.trailer_id,
                                                TrailerAssignment.detached_at.is_(None)).first())
        if a: a.detached_at = bay_gio; a.reason = a.reason or ly_do
        rm = db.get(Trailer, xe.trailer_id)
        if rm and rm.status == "attached": rm.status = "available"
        xe.trailer_id = None; xe.plate_trailer = None

    tid = (data.get("trailer_id") or "").strip()
    if not tid:
        thao(v); db.commit(); return xuat_xe(db, v, chi_tiet=True, vai=user.role)
    t = db.get(Trailer, tid)
    if not t or not t.active:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có rơ-moóc này."})
    if t.status == "maintenance":
        raise HTTPException(409, {"ma": "RO_MOOC_DANG_SUA", "loi": "Rơ-moóc %s đang sửa, không lắp được." % t.plate})
    khac = db.query(Vehicle).filter(Vehicle.trailer_id == t.id, Vehicle.id != v.id).first()
    if khac: thao(khac)
    thao(v)
    v.trailer_id = t.id; v.plate_trailer = t.plate; t.status = "attached"
    db.add(TrailerAssignment(trailer_id=t.id, vehicle_id=v.id, attached_at=bay_gio, reason=ly_do, by_user=user.full_name))
    db.commit()
    return xuat_xe(db, v, chi_tiet=True, vai=user.role)


# ================================================================ tài xế & bằng lái
COT_TX = ("driver_code", "name", "name_latin", "phone", "dob", "id_card", "address", "role", "hire_date",
          "license_no", "license_type", "license_class_hr", "license_status",
          "license_valid_from", "license_valid_to", "default_vehicle_id", "status", "note")
NGAY_TX = ("dob", "hire_date", "license_valid_from", "license_valid_to")
TRANG_THAI_BANG = ("active", "suspended", "revoked")


def _phu_tai_xe(db, ds):
    """Số phiếu đã chạy và phiếu ĐANG chạy của nhiều tài xế — hai truy vấn cho cả danh sách, không hỏi
    lại từng người. Màn Tài xế cần hai số này ngay ở bảng để biết ai đang bận."""
    ids = [d.id for d in ds if d.id]
    if not ids:
        return {}, {}
    # số phiếu từ trước tới nay: cộng từ số đếm từng tháng (đệm theo tháng) — đếm thẳng cả bảng thì tăng theo dữ liệu
    from services import dem_bao_cao as DEM
    tat = DEM.dem_phieu_theo(db, "sp-tai-xe", Trip.driver_id)
    dem = {i: tat[i] for i in ids if i in tat}
    dang = {}
    # chỉ hai cột cần dùng — không nạp nguyên phiếu (hơn 100 cột) của mọi chuyến đang chạy
    for tid, so in (db.query(Trip.driver_id, Trip.doc_no).filter(Trip.driver_id.in_(ids), Trip.transport_status != "arrived")
                    .order_by(Trip.doc_date.desc())):
        dang.setdefault(tid, so)
    return dem, dang


def _phu_bang_xe(db, ds):
    """Số xe mặc định và NƠI CẤP của bằng hiện hành cho cả danh sách — hai câu thay cho hai câu MỖI tài xế
    (500 tài xế là 1.000 câu, 24 giây). Chọn dòng bằng đúng thứ tự cũ: verified_at giảm dần, lấy dòng đầu."""
    xe = {}
    ma_xe = {d.default_vehicle_id for d in ds if d.default_vehicle_id}
    if ma_xe:
        xe = dict(db.query(Vehicle.id, Vehicle.truck_no).filter(Vehicle.id.in_(ma_xe)).all())
    bang = {}
    ids = [d.id for d in ds if d.license_no]
    if ids:
        for did, so, noi in (db.query(DriverLicense.driver_id, DriverLicense.license_no, DriverLicense.issued_by)
                             .filter(DriverLicense.driver_id.in_(ids)).order_by(DriverLicense.verified_at.desc())):
            bang.setdefault((did, so), noi)
    return xe, bang


def xuat_tai_xe(db, d, chi_tiet=False, dem=None, dang=None, xe=None, bang=None):
    r = _dict(d)
    r["bang_lai"] = _han(d.license_valid_to)
    if d.default_vehicle_id:
        if xe is not None:
            r["default_vehicle"] = xe.get(d.default_vehicle_id)
        else:
            x = db.get(Vehicle, d.default_vehicle_id); r["default_vehicle"] = x.truck_no if x else None
    # Nơi cấp của bằng HIỆN HÀNH nằm ở dòng lịch sử cùng số bằng — hồ sơ tài xế không giữ riêng.
    if d.license_no:
        if bang is not None:
            r["license_issued_by"] = bang.get((d.id, d.license_no))
        else:
            l = (db.query(DriverLicense).filter(DriverLicense.driver_id == d.id, DriverLicense.license_no == d.license_no)
                 .order_by(DriverLicense.verified_at.desc()).first())
            r["license_issued_by"] = l.issued_by if l else None
    r["so_phieu"] = dem.get(d.id, 0) if dem is not None else db.query(Trip).filter(Trip.driver_id == d.id).count()
    if dang is not None:
        r["phieu_hien_tai"] = dang.get(d.id)
    else:
        p = (db.query(Trip).filter(Trip.driver_id == d.id, Trip.transport_status != "arrived")
             .order_by(Trip.doc_date.desc().nullslast()).first())
        r["phieu_hien_tai"] = p.doc_no if p else None
    if chi_tiet:
        r["licenses"] = [_dict(l) for l in db.query(DriverLicense).filter(DriverLicense.driver_id == d.id)
                         .order_by(DriverLicense.valid_to.desc().nullslast()).all()]
        r["phieu_gan_day"] = [{"id": p.id, "doc_no": p.doc_no, "doc_date": p.doc_date.isoformat() if p.doc_date else None,
                               "truck_no": p.truck_no, "origin": p.origin, "destination": p.destination, "transport_status": p.transport_status}
                              for p in db.query(Trip).filter(Trip.driver_id == d.id).order_by(Trip.doc_date.desc()).limit(10).all()]
        r["anh_chinh"] = ANH.anh_chinh(ANH.TAI_XE, db, d.id)
        r["anh"] = ANH.ds_anh(ANH.TAI_XE, db, d.id)
    return r


@router.get("/api/drivers")
def ds_tai_xe(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    ds = db.query(Driver).order_by(Driver.active.desc(), Driver.name).all()
    dem, dang = _phu_tai_xe(db, ds)
    xe, bang = _phu_bang_xe(db, ds)
    anh = ANH.anh_chinh_map(ANH.TAI_XE, db)
    ra = []
    for d in ds:
        r = xuat_tai_xe(db, d, dem=dem, dang=dang, xe=xe, bang=bang)
        r["anh_chinh"] = anh.get(d.id)
        ra.append(r)
    return ra


@router.get("/api/drivers/{did}/lich")
def lich_tai_xe(did: str, tuan: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Lịch một tuần của tài xế — cùng cách nghĩ với lịch xe: không có bảng lịch riêng, lịch chính là
    các phiếu người này cầm, trải từ ngày xuất tới ngày về. Ngày không có phiếu thì rảnh."""
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    try:
        d0 = dt.date.fromisoformat(tuan) if tuan else dt.date.today()
    except ValueError:
        raise HTTPException(422, {"ma": "TUAN_SAI", "loi": "Tuần phải ghi dạng YYYY-MM-DD."})
    d0 = d0 - dt.timedelta(days=d0.weekday())
    d7 = d0 + dt.timedelta(days=6)
    theo_ngay = {}
    ten_tuyen = {r.id: r.name for r in db.query(Route).all()}
    # chỉ những phiếu có thể chạm tuần này: lập trong 60 ngày trước tuần, hoặc chưa về — không nạp cả năm của người đó
    for p in (db.query(Trip).filter(Trip.driver_id == d.id, Trip.doc_date <= d7,
                                    or_(Trip.doc_date >= d0 - dt.timedelta(days=60), Trip.transport_status != "arrived"))):
        di = p.out_date or p.doc_date
        if not di:
            continue
        ve = p.back_date or (d7 if p.transport_status != "arrived" else di)
        duong = ("%s → %s" % (p.origin, p.destination)) if (p.origin and p.destination) else (ten_tuyen.get(p.route_id) or "")
        chu = ("%s · %s" % (p.doc_no.replace("/EPL", ""), duong)).strip(" ·")
        n = di
        while n <= min(ve, d7):
            if d0 <= n <= d7:
                theo_ngay.setdefault(n, []).append({"loai": "trip", "text": chu})
            n += dt.timedelta(days=1)
    return {"tu": d0.isoformat(), "den": d7.isoformat(),
            "ngay": [{"ngay": k.isoformat(), "su_kien": x} for k, x in sorted(theo_ngay.items())]}


@router.get("/api/drivers/{did}")
def xem_tai_xe(did: str, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    return xuat_tai_xe(db, d, chi_tiet=True)


def _kiem_tx(d):
    if not (d.name or "").strip():
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Tài xế phải có tên."})
    if d.role not in ("main", "co"):
        raise HTTPException(422, {"ma": "VAI_SAI", "loi": "role phải là main (lái chính) hoặc co (phụ xe)."})
    if d.license_status and d.license_status not in TRANG_THAI_BANG:
        raise HTTPException(422, {"ma": "TRANG_THAI_BANG_SAI", "loi": "Trạng thái bằng lái phải là %s." % ", ".join(TRANG_THAI_BANG)})
    if d.status not in TRANG_THAI_TAI_XE:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái phải là %s." % ", ".join(TRANG_THAI_TAI_XE)})
    if d.license_valid_from and d.license_valid_to and d.license_valid_to < d.license_valid_from:
        raise HTTPException(422, {"ma": "HAN_SAI", "loi": "Hạn bằng lái phải sau ngày cấp."})


@router.post("/api/drivers")
def them_tai_xe(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    d = Driver(); _ap(d, data, COT_TX, NGAY_TX); d.role = d.role or "main"; d.status = d.status or "available"
    _kiem_tx(d)
    db.add(d); db.flush()
    if d.license_no:
        db.add(DriverLicense(driver_id=d.id, license_no=d.license_no, license_type=d.license_type, valid_from=d.license_valid_from,
                             valid_to=d.license_valid_to, verified_by=user.full_name))
    db.commit(); db.refresh(d)
    return xuat_tai_xe(db, d, chi_tiet=True)


@router.put("/api/drivers/{did}")
def sua_tai_xe(did: str, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(SUA_DANH_MUC)):
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    _ap(d, data, COT_TX + ("active",), NGAY_TX)
    _kiem_tx(d)
    db.commit(); db.refresh(d)
    return xuat_tai_xe(db, d, chi_tiet=True)


@router.post("/api/drivers/{did}/licenses")
def them_bang_lai(did: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_DANH_MUC)):
    """Ghi một bằng lái mới / lần gia hạn — đồng thời cập nhật bằng HIỆN HÀNH trên hồ sơ tài xế."""
    d = db.get(Driver, did)
    if not d:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    so = str(data.get("license_no") or "").strip()
    if not so:
        raise HTTPException(422, {"ma": "THIEU_SO", "loi": "Bằng lái phải có số."})
    l = DriverLicense(driver_id=d.id, license_no=so, license_type=(data.get("license_type") or "").strip() or None,
                      valid_from=_ngay(data.get("valid_from"), "valid_from"), valid_to=_ngay(data.get("valid_to"), "valid_to"),
                      issued_by=data.get("issued_by"), note=data.get("note"), verified_by=user.full_name)
    if l.valid_from and l.valid_to and l.valid_to < l.valid_from:
        raise HTTPException(422, {"ma": "HAN_SAI", "loi": "Hạn bằng lái phải sau ngày cấp."})
    db.add(l)
    d.license_no, d.license_type, d.license_valid_from, d.license_valid_to = l.license_no, l.license_type, l.valid_from, l.valid_to
    # Cấp bằng mới thì bằng cũ bị treo cũng hết chuyện: bằng hiện hành là bằng vừa ghi.
    d.license_status = "active"
    db.commit(); db.refresh(d)
    return xuat_tai_xe(db, d, chi_tiet=True)


# ================================================================ tỷ giá
#
# LAK là tiền gốc của hệ này: mọi tỷ giá đọc là "một đơn vị tiền đó ăn bao nhiêu Kíp". Bảng này chỉ
# là tỷ giá MẶC ĐỊNH cho phiếu lập mới — phiếu đã lập khoá tỷ giá riêng của nó (`trips.rate_usd`…),
# nên sửa ở đây không bao giờ làm đổi con số trên tờ phiếu đã in. Mỗi lần đổi ghi một dòng lịch sử.
SUA_TY_GIA = can_vai("acct", "rev")          # kế toán thu/chi và kế toán doanh thu Viêng Chăn


@router.get("/api/rates")
def ds_ty_gia(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Dạng phẳng {mã: tỷ giá} — mọi màn đang gọi đường này, giữ nguyên hình dạng."""
    ra = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
    ra.setdefault("LAK", 1.0)
    return ra


@router.get("/api/rates/chi-tiet")
def chi_tiet_ty_gia(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Cho màn Tỷ giá: số đang áp dụng, số lần trước, mức thay đổi, ai đặt, đặt lúc nào."""
    cu = {r.code: r for r in db.query(ExchangeRate).all()}
    log = (db.query(ExchangeRateLog).order_by(ExchangeRateLog.ts.desc()).limit(200).all())
    ds = []
    for ma in TIEN_TE:
        if ma == "LAK":
            continue
        r = cu.get(ma)
        truoc = next((x.rate_cu for x in log if x.code == ma and x.rate_cu), None)
        gt = r.rate_to_lak if r else None
        doi = (gt - truoc) if (gt is not None and truoc) else None
        ds.append({"code": ma, "rate_to_lak": gt, "truoc": truoc, "doi": doi,
                   "doi_pct": round(doi / truoc * 100, 3) if (doi is not None and truoc) else None,
                   "by_user": r.by_user if r else None,
                   "cap_nhat": r.updated_at.isoformat() if (r and r.updated_at) else None})
    return {"ds": ds, "goc": "LAK",
            "lich_su": [{"id": x.id, "code": x.code, "rate_to_lak": x.rate_to_lak, "rate_cu": x.rate_cu,
                         "ap_dung_tu": x.ap_dung_tu.isoformat() if x.ap_dung_tu else None,
                         "nguon": x.nguon, "by_user": x.by_user, "ghi_chu": x.ghi_chu,
                         "ts": x.ts.isoformat() if x.ts else None} for x in log]}


@router.put("/api/rates")
def sua_ty_gia(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA_TY_GIA)):
    """Đặt tỷ giá mặc định cho phiếu lập mới. Chỉ ghi lịch sử khi con số THẬT SỰ đổi."""
    ngay = _ngay(data.get("ap_dung_tu"), "ap_dung_tu") or dt.date.today()
    ghi_chu = (data.get("ghi_chu") or "").strip() or None
    doi = []
    for ma in [m for m in TIEN_TE if m != "LAK"]:
        if ma not in data or data[ma] in (None, ""):
            continue
        gt = _so(data[ma], ma)
        if not gt or gt <= 0:
            raise HTTPException(422, {"ma": "SO_SAI", "loi": "Tỷ giá %s phải lớn hơn 0." % ma})
        r = db.get(ExchangeRate, ma)
        truoc = r.rate_to_lak if r else None
        if r is not None and abs((truoc or 0) - gt) < 1e-9:
            continue                              # gõ lại đúng số cũ thì không ghi một dòng lịch sử rỗng
        if r is None:
            r = ExchangeRate(code=ma)
        r.rate_to_lak, r.by_user, r.updated_at = gt, user.full_name, dt.datetime.utcnow()
        db.add(r)
        db.add(ExchangeRateLog(code=ma, rate_to_lak=gt, rate_cu=truoc, ap_dung_tu=ngay,
                               nguon="tay", by_user=user.full_name, ghi_chu=ghi_chu))
        doi.append(ma)
    db.commit()
    ra = ds_ty_gia(db, user)
    ra["_da_doi"] = doi
    return ra
