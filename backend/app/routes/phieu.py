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

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (CHUOI, LOAI_SU_CO, MUC, MUC_CHI, SU_KIEN, TRANG_THAI_TAI_CHINH, TRANG_THAI_VAN_CHUYEN,
                    Customer, Driver, ExchangeRate, FuelMove, FuelPlace, Part, PartMove, Route, RouteStop, Trip,
                    TripEvent, TripExpense, TripLog, TripSection, Vehicle)
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import chuyen_muc, duoc_sua_muc
from services.tinh_toan import tinh_phieu

router = APIRouter()

# Khoản mục chuẩn của từng mục chi — chép từ Excel; người dùng vẫn gõ tên tự do được.
KHOAN_MUC = {
    "fuel":   ["diesel"],
    "travel": ["x_water", "x_vn", "x_chip_lao", "x_chip_vn", "x_bridge", "x_toll", "x_trip",
               "x_phone", "x_food", "x_parking", "x_border"],
    "repair": ["x_tire", "x_air", "x_oil", "x_brake", "x_tow"],
    "other":  ["x_misc"],
}
MA_TK = ["625/371", "625/402", "614/371", "614/402", "4022/371", "4022/402", "1211/70", "1211/402"]
COT_PHIEU = ("doc_no", "doc_date", "out_date", "back_date", "company", "owner_name", "vehicle_id",
             "truck_no", "brand_model", "plate_head", "plate_trailer", "driver_id", "driver_name",
             "odo_out", "odo_back", "customer_id", "customer_name", "route_id", "goods_type", "ore_bill_no",
             "ore_bill_date", "origin", "destination", "weight_origin", "weight_dest", "price_usd",
             "hire_price_usd", "fee_pct", "over_limit_t", "over_price_usd", "rate_usd", "rate_thb",
             "rate_vnd", "note")
COT_NGAY = ("doc_date", "out_date", "back_date", "ore_bill_date")
COT_SO = ("odo_out", "odo_back", "weight_origin", "weight_dest", "price_usd", "hire_price_usd",
          "fee_pct", "over_limit_t", "over_price_usd", "rate_usd", "rate_thb", "rate_vnd")
# Trường nào thuộc mục nào — để khoá theo trạng thái duyệt của mục
MUC_CUA_COT = {
    "info":  {"doc_date", "out_date", "back_date", "company", "owner_name", "vehicle_id", "truck_no",
              "brand_model", "plate_head", "plate_trailer", "driver_id", "driver_name", "odo_out", "odo_back"},
    "trans": {"customer_id", "customer_name", "route_id", "goods_type", "ore_bill_no", "ore_bill_date", "origin",
              "destination", "weight_origin", "weight_dest", "price_usd", "hire_price_usd", "fee_pct",
              "over_limit_t", "over_price_usd"},
}


def ma_tk_mac_dinh(company, section, source=None, place=None):
    """Định khoản theo quy trình của họ: xe nhà 625/614, xe liên kết 4022; kho …/371, mua ngoài …/402."""
    if section == "fuel" and source is None:
        source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    duoi = "371" if source == "kho" else "402"
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
            "part_id": d.part_id, "stock_move_id": d.stock_move_id, "note": d.note}


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


def _diem_tuyen(db, phieu):
    if not phieu.route_id:
        return []
    return [{"seq": s.seq, "name": s.name, "km_from_prev": s.km_from_prev}
            for s in db.query(RouteStop).filter(RouteStop.route_id == phieu.route_id).order_by(RouteStop.seq).all()]


def xuat_phieu(db, phieu, day_du=True):
    dong = _dong_chi(db, phieu)
    ra = {c: getattr(phieu, c) for c in COT_PHIEU}
    for c in COT_NGAY:
        ra[c] = ra[c].isoformat() if ra[c] else None
    ra.update({"id": phieu.id, "transport_status": phieu.transport_status,
               "finance_status": phieu.finance_status, "invoiced": phieu.invoiced,
               "created_by": phieu.created_by,
               "created_at": phieu.created_at.isoformat() if phieu.created_at else None,
               "tinh": tinh_phieu(phieu, dong),
               "sections": {s.section: s.status for s in _muc_cua(db, phieu).values()}})
    if day_du:
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
        ra["stop_reached"] = max(da_toi) if da_toi else (1 if phieu.transport_status != "dispatched" else 0)
    return ra


# ---------------------------------------------------------------- danh sách & xem
@router.get("/api/khoan-muc")
def khoan_muc():
    return {"items": KHOAN_MUC, "acct_codes": MA_TK, "chain": {k: list(v) for k, v in CHUOI.items()},
            "acct_default": {"EPL": {m: ma_tk_mac_dinh("EPL", m, "kho" if m in ("fuel", "repair") else None) for m in MUC_CHI},
                             "joint": {m: ma_tk_mac_dinh("joint", m, "kho" if m in ("fuel", "repair") else None) for m in MUC_CHI}},
            "acct_rule": {"EPL": {"kho": {"fuel": "625/371", "repair": "614/371"}, "mua": {"fuel": "625/402", "repair": "614/402", "travel": "625/402", "other": "625/402"}},
                          "joint": {"kho": {"fuel": "4022/371", "repair": "4022/371"}, "mua": {"fuel": "4022/402", "repair": "4022/402", "travel": "4022/402", "other": "4022/402"}}},
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
    return [xuat_phieu(db, p, day_du=False) for p in ds]


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
        if muc_tt is not None:
            muc = next((m for m, cot in MUC_CUA_COT.items() if c in cot), None)
            if muc and not duoc_sua_muc(user.role, muc, muc_tt[muc]):
                raise HTTPException(409, {"ma": "MUC_DA_KHOA",
                                          "loi": "Mục %s đã khoá (%s); phải trả lại mới sửa được." % (muc, muc_tt[muc])})
        v = data[c]
        if c in COT_NGAY: v = _ngay(v)
        elif c in COT_SO: v = _so(v, c)
        elif isinstance(v, str): v = v.strip() or None
        setattr(p, c, v)
    # Chép tên/biển từ danh mục nếu chỉ gửi mã
    if p.vehicle_id and not data.get("truck_no"):
        x = db.get(Vehicle, p.vehicle_id)
        if x:
            p.truck_no, p.brand_model, p.plate_head, p.plate_trailer = x.truck_no, x.brand_model, x.plate_head, x.plate_trailer
            if x.owner_type == "joint" and not p.owner_name: p.owner_name = x.owner_name
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
    if p.company not in ("EPL", "joint"):
        raise HTTPException(422, {"ma": "LOAI_SAI", "loi": "company phải là EPL hoặc joint."})
    if p.company == "joint" and p.hire_price_usd is None:
        p.hire_price_usd = p.price_usd     # mặc định bằng giá nhận — người lập sửa sau


def _nguon_theo_diem(db, d):
    """Kho hay mua là do ĐIỂM ĐỔ quyết định: kho của EPL thì lĩnh (kho), trạm bán dầu thì mua.
    Phiếu cũ chưa có điểm đổ thì vẫn đọc khoá cũ fp_yard/fp_vn để không mất dữ liệu."""
    if d.get("place_id"):
        x = db.get(FuelPlace, d["place_id"])
        if x:
            return "kho" if x.owner_type == "epl" else "mua"
    return "kho" if (d.get("place") or "fp_yard") == "fp_yard" else "mua"


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
        place_id=d.get("place_id") or None, supplier_id=d.get("supplier_id") or None,
        paid_by_epl=bool(d.get("paid_by_epl", True)),
        acct_code=d.get("acct_code") or ma_tk_mac_dinh(p.company, m, source, d.get("place")),
        source=source, part_id=d.get("part_id") or None, stock_move_id=d.get("stock_move_id") or None, note=d.get("note"))


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
        giu = {e.id: e for e in cu.values() if e.stock_move_id}
        da_gui = {d.get("id") for d in theo_muc[m]}
        for e in giu.values():
            if e.id not in da_gui:
                raise HTTPException(409, {"ma": "DA_XUAT_KHO", "loi": "Dòng '%s' đã xuất kho, không xoá được trên phiếu." % (e.item_name or e.item_key)})
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


@router.post("/api/trips")
def lap_phieu(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Bãi Thà Bốc lập phiếu xuất xe."})
    p = Trip(doc_no=str(data.get("doc_no") or _so_phieu_moi(db)).strip(), created_by=user.full_name)
    if db.query(Trip).filter(Trip.doc_no == p.doc_no).first():
        raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu %s đã có." % p.doc_no})
    # Tỷ giá mặc định lấy từ bảng tỷ giá, rồi khoá vào phiếu
    tg = {r.code: r.rate_to_lak for r in db.query(ExchangeRate).all()}
    p.rate_usd, p.rate_thb, p.rate_vnd = tg.get("USD", 22000), tg.get("THB", 700), tg.get("VND", 1.2)
    _ap_truong(db, p, data, user)
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
    _doi_trang_thai_xe_tai_xe(db, p, "on_trip", "on_trip")
    _ghi_log(db, p, user, "a_create")
    db.commit()
    return xuat_phieu(db, p)


@router.put("/api/trips/{tid}")
def sua_phieu(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    muc_tt = {m: s.status for m, s in _muc_cua(db, p).items()}
    if "doc_no" in data and str(data["doc_no"]).strip() != p.doc_no:
        if db.query(Trip).filter(Trip.doc_no == str(data["doc_no"]).strip()).first():
            raise HTTPException(409, {"ma": "TRUNG_SO", "loi": "Số phiếu đã có."})
    _ap_truong(db, p, data, user, muc_tt)
    if "expenses" in data:
        _ap_dong_chi(db, p, data["expenses"], user, muc_tt)
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


@router.post("/api/trips/{tid}/sections/{muc}/{hanh_dong}")
def duyet_muc(tid: str, muc: str, hanh_dong: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    ds = _muc_cua(db, p)
    s = ds[muc] if muc in ds else None
    if s is None:
        raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Không có mục %s." % muc})
    if muc in MUC_CHI and hanh_dong == "send" and not any(d.section == muc for d in _dong_chi(db, p)):
        raise HTTPException(409, {"ma": "MUC_TRONG", "loi": "Mục %s chưa có dòng chi nào để gửi kiểm." % muc})
    s.status = chuyen_muc(user.role, muc, s.status, hanh_dong)
    if muc == "fuel" and hanh_dong == "book":
        _xuat_kho_nhien_lieu(db, p, user)
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
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Bãi Thà Bốc ghi diễn biến trên đường."})
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


# ---------------------------------------------------------------- mức phiếu
@router.post("/api/trips/{tid}/transport-status")
def doi_trang_thai_van_chuyen(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """ອອກລົດ → ກຳລັງຈັດສົ່ງ → ຮອດແລ້ວ. Bãi Thà Bốc ghi khi xe báo về. Xe về thì xe & tài xế rảnh lại,
    công-tơ-mét của xe cập nhật theo số lúc về."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin", "driver"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Bãi Thà Bốc hoặc tài xế của phiếu cập nhật trạng thái xe."})
    _cua_tai_xe(db, p, user)
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
        if p.vehicle_id and p.odo_back:
            x = db.get(Vehicle, p.vehicle_id)
            if x and (x.odometer_km or 0) < p.odo_back: x.odometer_km = p.odo_back
    else:
        _doi_trang_thai_xe_tai_xe(db, p, "on_trip", "on_trip")
    p.transport_status = moi
    _ghi_log(db, p, user, "st_%s" % moi)
    db.commit()
    return xuat_phieu(db, p)


@router.post("/api/trips/{tid}/invoice")
def xuat_hoa_don(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu xuất hoá đơn."})
    if _muc_cua(db, p)["trans"].status != "verified":
        raise HTTPException(409, {"ma": "CHUA_KIEM", "loi": "Mục II (vận chuyển) phải được kiểm xong trước khi xuất hoá đơn."})
    p.invoiced = True
    _ghi_log(db, p, user, "a_invoice")
    db.commit()
    return xuat_phieu(db, p)


@router.post("/api/trips/{tid}/finance-status")
def doi_trang_thai_tai_chinh(tid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu ghi thu tiền."})
    moi = data.get("status")
    if moi not in TRANG_THAI_TAI_CHINH:
        raise HTTPException(422, {"ma": "TRANG_THAI_SAI", "loi": "Trạng thái phải là %s." % ", ".join(TRANG_THAI_TAI_CHINH)})
    if moi != "unpaid" and not p.invoiced:
        raise HTTPException(409, {"ma": "CHUA_HOA_DON", "loi": "Chưa xuất hoá đơn thì chưa ghi thu."})
    p.finance_status = moi
    _ghi_log(db, p, user, "fin_%s" % moi)
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
    """Admin / Bãi DUYỆT báo hỏng của tài xế → mở phiếu, thêm dòng sửa chữa vào mục V với số tiền duyệt
    (mặc định = số tài xế báo). Nguồn: kho (chọn phụ tùng, trừ tồn ngay) hoặc mua ngoài. Hoặc TỪ CHỐI.

    Khai đổ dầu dọc đường (kind='refuel') cũng duyệt ở đây, nhưng rơi vào MỤC III nguồn mua."""
    p = db.get(Trip, tid)
    e = db.get(TripEvent, eid)
    if not p or not e or e.trip_id != p.id:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có báo hỏng này."})
    duoc = ("yard", "acct", "fuel", "admin") if e.kind == "refuel" else ("yard", "admin")
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
    k = tinh_phieu(p, _dong_chi(db, p))
    return {"doc_no": p.doc_no, "so_phieu_thu": "PT-" + p.doc_no.replace("/", "-"), "doc_date": p.doc_date.isoformat() if p.doc_date else None,
            "customer_name": p.customer_name, "origin": p.origin, "destination": p.destination, "truck_no": p.truck_no,
            "tan_tinh": k["tan_tinh"], "price_usd": p.price_usd, "doanh_thu_usd": k["doanh_thu_usd"], "doanh_thu_lak": k["doanh_thu_lak"],
            "rate_usd": p.rate_usd, "acct_code": "1211/70", "invoiced": p.invoiced, "finance_status": p.finance_status,
            "trans_status": _muc_cua(db, p)["trans"].status}


@router.delete("/api/trips/{tid}")
def xoa_phieu(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Chỉ xoá được phiếu chưa mục nào qua bước kiểm và chưa xuất kho gì — đã kiểm là chứng từ, không xoá."""
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    if user.role not in ("yard", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ Bãi Thà Bốc hoặc quản trị xoá phiếu."})
    if any(s.status not in ("wait", "entered") for s in _muc_cua(db, p).values()) and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_DUYET", "loi": "Phiếu đã có mục được kiểm, không xoá được."})
    if any(e.stock_move_id for e in _dong_chi(db, p)) and user.role != "admin":
        raise HTTPException(409, {"ma": "DA_XUAT_KHO", "loi": "Phiếu đã có dòng xuất kho, không xoá được."})
    _doi_trang_thai_xe_tai_xe(db, p, "available", "available")
    db.query(TripEvent).filter(TripEvent.trip_id == p.id).delete()
    db.query(TripExpense).filter(TripExpense.trip_id == p.id).delete()
    db.query(TripSection).filter(TripSection.trip_id == p.id).delete()
    db.query(TripLog).filter(TripLog.trip_id == p.id).delete()
    db.delete(p); db.commit()
    return {"ok": True}
