# -*- coding: utf-8 -*-
"""Bốn bảng báo cáo trong sheet "ລາຍງານ" của Excel: tổng quan, theo dõi phiếu (họ rất
thích bảng này), xe liên kết, tiền chuyến & tiền nước tài xế.

Mọi con số ở đây đều TÍNH LẠI từ phiếu lúc gọi — không có bảng tổng hợp riêng để rồi lệch.
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import ChungTu, Part, Trip, TripExpense, TripSection, Voucher
from routes.phieu import xuat_phieu
from services.bao_mat import nguoi_hien_tai
from services.tinh_toan import tien_dong, tinh_phieu

router = APIRouter()


def _thang(thang):
    """'2026-08' → (đầu, cuối); trống → tháng hiện tại."""
    if thang:
        y, m = int(thang[:4]), int(thang[5:7])
    else:
        h = dt.date.today(); y, m = h.year, h.month
    dau = dt.date(y, m, 1)
    cuoi = dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)
    return dau, cuoi


def _phieu_thang(db, thang):
    dau, cuoi = _thang(thang)
    return (db.query(Trip).filter(Trip.doc_date >= dau, Trip.doc_date <= cuoi)
            .order_by(Trip.doc_date, Trip.doc_no).all()), dau, cuoi


@router.get("/api/bao-cao/tong-quan")
def tong_quan(thang: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    ds, dau, cuoi = _phieu_thang(db, thang)
    dong = defaultdict(list)
    for d in db.query(TripExpense).filter(TripExpense.trip_id.in_([p.id for p in ds] or [""])).all():
        dong[d.trip_id].append(d)
    doanh_thu = chi_lak = tan = 0.0
    chua_thu_usd, chua_thu_so = 0.0, 0
    dem = {"dispatched": 0, "transit": 0, "arrived": 0, "invoiced": 0, "paid": 0}
    theo_muc = {"fuel": 0.0, "travel": 0.0, "repair": 0.0, "other": 0.0}
    for p in ds:
        c = tinh_phieu(p, dong[p.id])
        doanh_thu += c["doanh_thu_usd"]
        # Chi của EPL: xe nhà là tổng chi; xe liên kết là tiền thuê trừ phần giữ lại
        chi_lak += (c["tien_thue_usd"] - c["giu_lai_usd"]) * (p.rate_usd or 22000) if c["lien_ket"] else c["tong_chi_lak"]
        for m in theo_muc: theo_muc[m] += c["chi"][m]
        if p.weight_dest: tan += p.weight_dest
        if p.transport_status == "arrived" and p.finance_status != "paid":
            chua_thu_usd += c["doanh_thu_usd"]; chua_thu_so += 1
        dem[p.transport_status] = dem.get(p.transport_status, 0) + 1
        if p.invoiced: dem["invoiced"] += 1
        if p.finance_status == "paid": dem["paid"] += 1
    # Việc cần chú ý — tính từ dữ liệu, không viết cứng
    chu_y = []
    for p in ds:
        c = tinh_phieu(p, dong[p.id])
        if c["hao_hut_pct"] is not None and c["hao_hut_pct"] > 1.5:
            chu_y.append({"loai": "hao_hut", "doc_no": p.doc_no, "gia_tri": c["hao_hut_pct"]})
        if p.transport_status == "arrived" and not p.invoiced:
            chu_y.append({"loai": "chua_hoa_don", "doc_no": p.doc_no})
        if p.transport_status == "arrived" and p.weight_dest is None:
            chu_y.append({"loai": "chua_can", "doc_no": p.doc_no})
    cho_kiem = (db.query(TripSection).filter(TripSection.trip_id.in_([p.id for p in ds] or [""]),
                                             TripSection.status == "entered").count())
    if cho_kiem:
        chu_y.append({"loai": "cho_kiem", "so": cho_kiem})
    return {"tu": dau.isoformat(), "den": cuoi.isoformat(), "so_phieu": len(ds),
            "doanh_thu_usd": round(doanh_thu, 2), "chi_lak": round(chi_lak), "tan_giao": round(tan, 2),
            "chua_thu_usd": round(chua_thu_usd, 2), "chua_thu_so": chua_thu_so,
            "dem": dem, "chi_theo_muc": {k: round(v) for k, v in theo_muc.items()}, "chu_y": chu_y[:12]}


@router.get("/api/bao-cao/theo-doi")
def theo_doi(thang: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """Bảng "ລາຍງານ ຕິດຕາມໃບຂົນສົ່ງສິນຄ້າ" — một dòng một phiếu, đủ 29 cột như Excel."""
    ds, dau, cuoi = _phieu_thang(db, thang) if thang else (db.query(Trip).order_by(Trip.doc_date, Trip.doc_no).all(), None, None)
    return [xuat_phieu(db, p, day_du=False) for p in ds]


@router.get("/api/bao-cao/xe-lien-ket")
def xe_lien_ket(thang: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    ds = db.query(Trip).filter(Trip.company == "joint").order_by(Trip.doc_date.desc()).all()
    if thang:
        dau, cuoi = _thang(thang)
        ds = [p for p in ds if p.doc_date and dau <= p.doc_date <= cuoi]
    return [xuat_phieu(db, p, day_du=False) for p in ds]


@router.get("/api/bao-cao/tien-tai-xe")
def tien_tai_xe(thang: str = None, db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    """ເງິນຖ້ຽວໂຊເຟີ ແລະ ເງິນເຕີມນ້ຳ — tiền chuyến và tiền nước theo TÀI XẾ, gom từ mục IV.

    Khoản nào là "của tài xế": x_trip (tiền chuyến), x_water (tiền nước), x_vn (tiền đi VN),
    x_phone (điện thoại), x_food (ăn). Trạng thái chi lấy từ mục IV của phiếu.
    """
    ds, dau, cuoi = _phieu_thang(db, thang)
    KHOAN_TAI_XE = {"x_trip", "x_water", "x_vn", "x_phone", "x_food"}
    tong = {}
    for p in ds:
        if not p.driver_name:
            continue
        r = tong.setdefault(p.driver_name, {"driver": p.driver_name, "so_phieu": 0, "khoan": defaultdict(float),
                                            "tong_lak": 0.0, "da_chi": 0, "cho_chi": 0})
        r["so_phieu"] += 1
        tt = {s.section: s.status for s in db.query(TripSection).filter(TripSection.trip_id == p.id).all()}
        for d in db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "travel").all():
            if d.item_key in KHOAN_TAI_XE and d.paid_by_epl:
                v = tien_dong(p, d); r["khoan"][d.item_key] += v; r["tong_lak"] += v
        if tt.get("travel") == "paid": r["da_chi"] += 1
        else: r["cho_chi"] += 1
    ra = []
    for r in tong.values():
        r["khoan"] = {k: round(v) for k, v in r["khoan"].items()}
        r["tong_lak"] = round(r["tong_lak"])
        r["trang_thai"] = "paid" if r["cho_chi"] == 0 else ("partial" if r["da_chi"] else "unpaid")
        ra.append(r)
    return {"tu": dau.isoformat(), "den": cuoi.isoformat(), "rows": sorted(ra, key=lambda x: x["driver"])}


@router.get("/api/dem-viec")
def dem_viec(db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Số việc đang chờ của TỪNG MÀN, để gắn con số nhỏ cạnh mục menu.

    Chỉ đếm việc mà vai ĐANG ĐĂNG NHẬP thật sự phải làm — gắn số vào màn người ta không có quyền
    làm gì thì chỉ tổ gây lo. Không trả khoá nào bằng 0 để giao diện khỏi vẽ pill rỗng.
    """
    r = {}
    vai = user.role
    admin = vai == "admin"

    if vai == "driver":
        r["phieu-cua-toi"] = (db.query(Trip).filter(Trip.driver_id == user.driver_id,
                                                    Trip.transport_status != "arrived").count()
                              if getattr(user, "driver_id", None) else 0)
        return {k: v for k, v in r.items() if v}

    # Phiếu chưa xong: chưa về, hoặc về rồi mà chưa xong phần tiền
    if admin or vai in ("yard", "acct", "expacct", "rev", "cash", "treasury", "fuel"):
        r["theo-doi"] = db.query(Trip).filter(
            (Trip.transport_status != "arrived") | (Trip.finance_status != "paid")).count()

    # Phiếu lĩnh · tạm ứng đang chờ cấp
    cho = db.query(Voucher).filter(Voucher.status == "cho")
    if vai == "depot":
        n = cho.filter(Voucher.kind == "fuel", Voucher.place_id == user.place_id).count()
        if n:
            r["cap-phat"] = n
            r["kho-nhien-lieu"] = n
        return {k: v for k, v in r.items() if v}
    if admin or vai in ("yard", "fuel", "cash", "treasury", "acct", "expacct"):
        r["cap-phat"] = cho.count()
        r["kho-nhien-lieu"] = cho.filter(Voucher.kind == "fuel").count()

    # Phụ tùng dưới tồn tối thiểu
    if admin or vai in ("yard", "fuel", "expacct"):
        r["kho-phu-tung"] = db.query(Part).filter(Part.qty < Part.min_qty).count()

    # Chứng từ bên kế toán chưa đối chiếu
    if admin or vai in ("acct", "expacct", "rev", "cash", "treasury"):
        r["chung-tu"] = db.query(ChungTu).filter(ChungTu.da_day.is_(False)).count()

    return {k: v for k, v in r.items() if v}
