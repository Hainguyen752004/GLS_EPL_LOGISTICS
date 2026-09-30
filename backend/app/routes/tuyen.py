# -*- coding: utf-8 -*-
"""Tuyến đường — mang sang từ EPL_System, cắt còn thứ họ dùng: chặng A → B → C, km từng chặng, BOT.

Không hình đường bộ, không toạ độ, không ETA. Một tuyến có ít nhất hai điểm: điểm đi (seq 1) và điểm
đến (seq cuối). Chọn tuyến trên phiếu xuất xe thì điểm đi/đến tự điền và BOT tự thành dòng phí cao tốc.
"""
import json

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import FuelPlace, Route, RouteStop, Trip
from services.bao_mat import can_vai, nguoi_hien_tai
from services.phan_quyen import thay_tien_chi
from services.tinh_toan import CACH_TRA

router = APIRouter()
SUA = can_vai("yard", "acct")


def _so(v, ten):
    if v in (None, ""):
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "SO_SAI", "loi": "Ô %s phải là số." % ten})


def km_ca_chuyen(r):
    """Km một chuyến xe chạy trên tuyến: chiều đi (tổng các chặng) + chiều về (xe quay lại điểm đi, nếu có)."""
    return round((r.total_km or 0) + (r.return_km or 0), 1)


def _km_ve(v):
    km = _so(v, "km chiều về")
    if km < 0:
        raise HTTPException(422, {"ma": "SO_AM", "loi": "Km chiều về không được âm."})
    return round(km, 1)


# ---------------------------------------------------------------- chi phí gợi ý (30/09)
MUC_GOI_Y = ("fuel", "travel", "other")
TIEN_TE_GOI_Y = ("LAK", "VND", "THB", "USD", "CNY")
# Tờ Excel mẫu của họ (ໃບບິນອອກລົດ — chuyến ra cảng Việt Nam): mục IV đúng từng dòng, SL 1, đơn giá trên tờ.
# Phí cao tốc KHÔNG nằm ở đây: nó là ô BOT của tuyến, lập phiếu thì tự thành dòng x_toll.
EXCEL_DI_DUONG = (("x_water", 60000), ("x_vn", 430000), ("x_chip_lao", 620000), ("x_chip_vn", 1500000),
                  ("x_trip", 1800000), ("x_phone", 150000))


def bo_chung(db):
    """BỘ CHUNG theo Excel cho tuyến chưa có bộ riêng: 100 L ở kho Thà Bốc + 750 L dầu Việt Nam qua KHO XE (tờ Excel
    ghi 625/371 — lĩnh qua kho, A3) + mục IV như tờ Excel. Kho nào không có trong danh mục thì bỏ dòng đó."""
    ds = []
    for ma, lit in (("KHO-TB", 100), ("KHO-XE-VN", 750)):
        x = db.query(FuelPlace).filter(FuelPlace.code == ma, FuelPlace.active.is_(True)).first()
        if x:
            ds.append({"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": x.id})
    ds += [{"section": "travel", "item_key": k, "qty": 1, "unit_price": g, "currency": "LAK"} for k, g in EXCEL_DI_DUONG]
    return ds


def doc_mau(r):
    try:
        return json.loads(r.cost_template) if r and r.cost_template else []
    except ValueError:
        return []


def goi_y_cua(db, r, chung=None):
    """(bộ gợi ý, nguồn): bộ riêng của tuyến, không có thì bộ chung Excel."""
    mau = doc_mau(r)
    return (mau, "tuyen") if mau else ((chung if chung is not None else bo_chung(db)), "chung")


def gia_goi_y(db, route_id, m, d):
    """Đơn giá gợi ý cho MỘT dòng Bãi vừa khai (Bãi không nhập tiền): khớp dòng cùng mục + cùng khoản mục (dầu: cùng nơi
    đổ) trong bộ gợi ý của tuyến. Trả (đơn giá, tiền tệ) hoặc None."""
    r = db.get(Route, route_id) if route_id else None
    if r is None:
        return None
    ds, _ = goi_y_cua(db, r)
    for x in ds:
        if x.get("section") != m or x.get("unit_price") in (None, ""):
            continue
        if m == "fuel":
            if (x.get("place_id") or None) != (d.get("place_id") or None):
                continue
        elif (x.get("item_key") or None) != (d.get("item_key") or None) or \
                (not x.get("item_key") and (x.get("item_name") or "").strip() != (d.get("item_name") or "").strip()):
            continue
        return float(x["unit_price"]), str(x.get("currency") or "LAK").upper()
    return None


def _bo_gia(ds):
    return [{k: v for k, v in x.items() if k not in ("unit_price", "currency")} for x in ds]


def _ghi_mau(db, r, ds, user):
    """Ghi bộ gợi ý. Vai không được thấy tiền chi (Bãi) thì đơn giá gửi lên bị bỏ, dòng cũ giữ giá kế toán đã đặt."""
    from routes.phieu import KHOAN_MUC           # phieu.py nạp tuyen.py — nạp ngược trong hàm cho khỏi vòng
    if ds is None:
        return
    if not isinstance(ds, list):
        raise HTTPException(422, {"ma": "GOI_Y_SAI", "loi": "Bộ chi phí gợi ý phải là danh sách dòng."})
    dat_gia = thay_tien_chi(user.role)
    khoa = lambda x: (x.get("section"), x.get("item_key") or "", (x.get("item_name") or "").strip(), x.get("place_id") or "")
    gia_cu = {khoa(x): (x.get("unit_price"), x.get("currency")) for x in doc_mau(r)}
    moi = []
    for i, d in enumerate(ds, 1):
        m = d.get("section")
        if m not in MUC_GOI_Y:
            raise HTTPException(422, {"ma": "GOI_Y_SAI", "loi": "Dòng %d: mục phải là nhiên liệu, đi đường hoặc chi khác." % i})
        key = (d.get("item_key") or "").strip() or ("diesel" if m == "fuel" else None)
        ten = (d.get("item_name") or "").strip() or None
        if key == "x_toll":
            continue                              # phí cao tốc là ô BOT của tuyến
        if key and key not in KHOAN_MUC.get(m, ()):
            raise HTTPException(422, {"ma": "GOI_Y_SAI", "loi": "Dòng %d: khoản mục không có trong danh mục." % i})
        if not key and not ten:
            raise HTTPException(422, {"ma": "GOI_Y_SAI", "loi": "Dòng %d: chọn khoản mục hoặc gõ tên khoản." % i})
        sl = _so(d.get("qty"), "số lượng")
        if sl < 0:
            raise HTTPException(422, {"ma": "SO_AM", "loi": "Dòng %d: số lượng không được âm." % i})
        x = {"section": m, "item_key": key, "qty": sl}
        if not key:
            x["item_name"] = ten
        if m == "fuel":
            pid = d.get("place_id") or None
            if pid and not db.get(FuelPlace, pid):
                raise HTTPException(422, {"ma": "GOI_Y_SAI", "loi": "Dòng %d: nơi đổ không có trong danh mục." % i})
            x["place_id"] = pid
        else:
            c = (d.get("pay_channel") or "").strip() or None
            if c and c not in CACH_TRA:
                raise HTTPException(422, {"ma": "CACH_TRA_SAI", "loi": "Dòng %d: cách trả không có trong danh sách." % i})
            if c:
                x["pay_channel"] = c
        if dat_gia:
            if d.get("unit_price") not in (None, ""):
                g = _so(d.get("unit_price"), "đơn giá")
                tt = str(d.get("currency") or "LAK").strip().upper()
                if g < 0 or tt not in TIEN_TE_GOI_Y:
                    raise HTTPException(422, {"ma": "SO_SAI", "loi": "Dòng %d: đơn giá không âm, tiền tệ LAK · VND · THB · USD · CNY." % i})
                x["unit_price"], x["currency"] = g, tt
        else:
            g, tt = gia_cu.get(khoa(x), (None, None))
            if g is not None:
                x["unit_price"], x["currency"] = g, tt
        moi.append(x)
    r.cost_template = json.dumps(moi, ensure_ascii=False) if moi else None


def xuat_tuyen(db, r, chi_tiet=False, vai=None, chung=None):
    diem = db.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.seq).all()
    ra = {"id": r.id, "name": r.name, "origin": r.origin, "destination": r.destination, "total_km": r.total_km,
          "return_km": r.return_km or 0, "round_km": km_ca_chuyen(r), "toll_lak": r.toll_lak, "note": r.note, "active": r.active, "so_diem": len(diem),
          "stops": [{"id": s.id, "seq": s.seq, "name": s.name, "km_from_prev": s.km_from_prev,
                     "lat": s.lat, "lng": s.lng, "note": s.note} for s in diem]}
    if chi_tiet:
        ra["so_phieu"] = db.query(Trip).filter(Trip.route_id == r.id).count()
    goi_y, nguon = goi_y_cua(db, r, chung)
    mau = doc_mau(r)
    if vai is not None and not thay_tien_chi(vai):       # Bãi không thấy tiền (anh Khampla A2)
        goi_y, mau = _bo_gia(goi_y), _bo_gia(mau)
    ra["cost_template"], ra["goi_y"], ra["goi_y_nguon"] = mau, goi_y, nguon
    return ra


def _toa_do(v, nho_nhat, lon_nhat, ten, i):
    if v in (None, ""):
        return None
    try:
        x = float(str(v).replace(",", ""))
    except ValueError:
        raise HTTPException(422, {"ma": "TOA_DO_SAI", "loi": "Điểm %d: %s phải là số." % (i, ten)})
    if not (nho_nhat <= x <= lon_nhat):
        raise HTTPException(422, {"ma": "TOA_DO_SAI",
                                  "loi": "Điểm %d: %s phải từ %s đến %s." % (i, ten, nho_nhat, lon_nhat)})
    return x


def _ghi_diem(db, r, stops):
    """Thay toàn bộ điểm của tuyến. Điểm đầu/cuối cập nhật lại origin/destination và tổng km."""
    if not isinstance(stops, list) or len(stops) < 2:
        raise HTTPException(422, {"ma": "THIEU_DIEM", "loi": "Tuyến phải có ít nhất điểm đi và điểm đến."})
    db.query(RouteStop).filter(RouteStop.route_id == r.id).delete()
    tong = 0.0
    for i, s in enumerate(stops, 1):
        ten = str((s or {}).get("name") or "").strip()
        if not ten:
            raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Điểm thứ %d chưa có tên." % i})
        km = _so(s.get("km_from_prev"), "km điểm %d" % i) if i > 1 else 0.0
        tong += km
        # Toạ độ không bắt buộc; có thì phải nằm trong khoảng hợp lệ, không thì chấm bay ra biển.
        lat, lng = _toa_do(s.get("lat"), -90, 90, "vĩ độ", i), _toa_do(s.get("lng"), -180, 180, "kinh độ", i)
        db.add(RouteStop(route_id=r.id, seq=i, name=ten, km_from_prev=km, lat=lat, lng=lng, note=s.get("note")))
    r.origin, r.destination, r.total_km = stops[0]["name"].strip(), stops[-1]["name"].strip(), round(tong, 1)


@router.get("/api/routes")
def ds(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    chung = bo_chung(db)                          # một lần cho cả danh sách
    return [xuat_tuyen(db, r, vai=user.role, chung=chung) for r in db.query(Route).order_by(Route.active.desc(), Route.name).all()]


@router.get("/api/tuyen-bo-chung")
def xem_bo_chung(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bộ chi phí gợi ý CHUNG theo tờ Excel (nút "Chép bộ chung" ở hộp sửa tuyến). Bãi không nhận đơn giá."""
    ds = bo_chung(db)
    return ds if thay_tien_chi(user.role) else _bo_gia(ds)


@router.get("/api/routes/{rid}")
def xem(rid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    r = db.get(Route, rid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tuyến này."})
    return xuat_tuyen(db, r, chi_tiet=True, vai=user.role)


@router.post("/api/routes")
def them(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    ten = str(data.get("name") or "").strip()
    if not ten:
        raise HTTPException(422, {"ma": "THIEU_TEN", "loi": "Tuyến phải có tên."})
    r = Route(name=ten, toll_lak=_so(data.get("toll_lak"), "BOT"), return_km=_km_ve(data.get("return_km")), note=data.get("note"))
    db.add(r); db.flush()
    _ghi_diem(db, r, data.get("stops"))
    _ghi_mau(db, r, data.get("cost_template"), user)
    db.commit()
    return xuat_tuyen(db, r, chi_tiet=True, vai=user.role)


@router.put("/api/routes/{rid}")
def sua(rid: str, data: dict = Body(...), db: Session = Depends(get_db), user=Depends(SUA)):
    r = db.get(Route, rid)
    if not r:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tuyến này."})
    if "name" in data:
        r.name = str(data["name"]).strip() or r.name
    if "toll_lak" in data: r.toll_lak = _so(data["toll_lak"], "BOT")
    if "return_km" in data: r.return_km = _km_ve(data["return_km"])
    if "note" in data: r.note = data["note"]
    if "active" in data: r.active = bool(data["active"])
    if "stops" in data: _ghi_diem(db, r, data["stops"])
    if "cost_template" in data: _ghi_mau(db, r, data["cost_template"], user)
    db.commit()
    return xuat_tuyen(db, r, chi_tiet=True, vai=user.role)
