# -*- coding: utf-8 -*-
"""Bốn bảng báo cáo trong sheet "ລາຍງານ" của Excel: tổng quan, theo dõi phiếu (họ rất
thích bảng này), xe liên kết, tiền chuyến & tiền nước tài xế.

Mọi con số ở đây đều TÍNH LẠI từ phiếu lúc gọi — không có bảng tổng hợp riêng để rồi lệch.
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ChungTu, Part, Route, RouteStop, Trip, TripEvent, TripExpense, TripSection, Voucher
from routes.phieu import xuat_phieu
from routes.theo_doi import NGAY_COI_LA_LAU
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import QUYEN, thay_tien_ban, viec_dang_cho
from services.tinh_toan import tien_dong, tinh_phieu

router = APIRouter()


def _thang(thang):
    """'2026-08' → (đầu, cuối); trống → tháng hiện tại. Gõ sai thì báo 422, không để máy chủ nổ 500."""
    if thang:
        try:
            y, m = int(thang[:4]), int(thang[5:7])
            dt.date(y, m, 1)
        except (ValueError, TypeError):
            raise HTTPException(422, {"ma": "THANG_SAI", "loi": "Tháng phải ghi dạng YYYY-MM, ví dụ 2026-08."})
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
def tong_quan(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
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
    ra = {"tu": dau.isoformat(), "den": cuoi.isoformat(), "so_phieu": len(ds),
          "doanh_thu_usd": round(doanh_thu, 2), "chi_lak": round(chi_lak), "tan_giao": round(tan, 2),
          "chua_thu_usd": round(chua_thu_usd, 2), "chua_thu_so": chua_thu_so,
          "dem": dem, "chi_theo_muc": {k: round(v) for k, v in theo_muc.items()}, "chu_y": chu_y[:12]}
    # Vai không được thấy tiền bán thì máy chủ BỎ HẲN các khoá đó, không chỉ giấu ở giao diện.
    if not thay_tien_ban(user.role):
        for k in ("doanh_thu_usd", "chua_thu_usd", "chua_thu_so"):
            ra.pop(k, None)
    return ra


# ================================================================ xu hướng (màn Tổng quan)
def _dong_theo_phieu(db, ds):
    """Tất cả dòng chi của một nhóm phiếu, gom sẵn theo phiếu — tránh gọi lại từng phiếu một."""
    dong = defaultdict(list)
    if ds:
        for d in db.query(TripExpense).filter(TripExpense.trip_id.in_([p.id for p in ds])).all():
            dong[d.trip_id].append(d)
    return dong


def _gom_thang(db, dau, cuoi):
    """Bốn con số của một tháng — cùng công thức với /api/bao-cao/tong-quan để hai màn không lệch nhau."""
    ds = (db.query(Trip).filter(Trip.doc_date >= dau, Trip.doc_date <= cuoi).all())
    dong = _dong_theo_phieu(db, ds)
    r = {"doanh_thu_usd": 0.0, "chi_lak": 0.0, "tan_giao": 0.0, "chua_thu_usd": 0.0}
    for p in ds:
        c = tinh_phieu(p, dong[p.id])
        r["doanh_thu_usd"] += c["doanh_thu_usd"]
        r["chi_lak"] += (c["tien_thue_usd"] - c["giu_lai_usd"]) * (p.rate_usd or 22000) if c["lien_ket"] else c["tong_chi_lak"]
        if p.weight_dest: r["tan_giao"] += p.weight_dest
        if p.transport_status == "arrived" and p.finance_status != "paid":
            r["chua_thu_usd"] += c["doanh_thu_usd"]
    return {"doanh_thu_usd": round(r["doanh_thu_usd"], 2), "chi_lak": round(r["chi_lak"]),
            "tan_giao": round(r["tan_giao"], 2), "chua_thu_usd": round(r["chua_thu_usd"], 2)}


def _lui_thang(y, m, n):
    """Lùi n tháng từ (y, m)."""
    t = (y * 12 + (m - 1)) - n
    return t // 12, t % 12 + 1


@router.get("/api/bao-cao/xu-huong")
def xu_huong(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Số liệu xu hướng cho màn Tổng quan: so tháng trước, sáu tháng gần nhất, theo ngày, hao hụt,
    hiệu suất xe, vận hành, xem nhanh, và dòng thời gian từng chuyến.

    Mốc dòng thời gian lấy từ dữ liệu THẬT, không suy diễn: ngày lập phiếu · ngày xuất xe · các mốc
    "tới điểm" Bãi đã bấm trên tuyến (điểm 2 = về bãi, điểm 3 = cửa khẩu, điểm cuối = nơi giao) ·
    ngày hoá đơn và ngày thu lấy từ Sổ chứng từ (HD, PT). Mốc nào chưa có thì để trống, màn hình vẽ
    đoạn đó là "đang diễn ra".
    """
    ds, dau, cuoi = _phieu_thang(db, thang)
    dong = _dong_theo_phieu(db, ds)
    hom_nay = dt.date.today()

    # ---- tháng trước và sáu tháng gần nhất (cũ → mới, kể cả tháng đang xem)
    y, m = dau.year, dau.month
    sau_thang = {"nhan": [], "doanh_thu_usd": [], "chi_lak": [], "tan_giao": [], "chua_thu_usd": []}
    thang_truoc = None
    for i in range(5, -1, -1):
        yy, mm = _lui_thang(y, m, i)
        d1 = dt.date(yy, mm, 1)
        d2 = dt.date(yy + (mm == 12), (mm % 12) + 1, 1) - dt.timedelta(days=1)
        g = _gom_thang(db, d1, d2)
        sau_thang["nhan"].append("%02d/%02d" % (mm, yy % 100))
        for k in ("doanh_thu_usd", "chi_lak", "tan_giao", "chua_thu_usd"):
            sau_thang[k].append(g[k])
        if i == 1:
            thang_truoc = g

    # ---- theo ngày · hao hụt · hiệu suất xe · vận hành
    theo_ngay, hao_hut, xe = defaultdict(lambda: {"doanh_thu_usd": 0.0, "chi_usd": 0.0}), [], {}
    ngay_di_ds, hao_ds, dung_han = [], [], 0
    for p in ds:
        c = tinh_phieu(p, dong[p.id])
        if p.doc_date:
            o = theo_ngay[p.doc_date.isoformat()]
            o["doanh_thu_usd"] += c["doanh_thu_usd"]
            o["chi_usd"] += c["tong_chi_usd"]
        if p.weight_origin and p.weight_dest is not None:
            hao_hut.append({"doc_no": p.doc_no, "so_xe": p.truck_no, "can_dau": p.weight_origin, "can_cuoi": p.weight_dest})
            if c["hao_hut_pct"] is not None: hao_ds.append(c["hao_hut_pct"])
        if p.truck_no:
            x = xe.setdefault(p.truck_no, {"so_xe": p.truck_no, "so_chuyen": 0, "tan": 0.0, "km": 0.0, "doanh_thu_usd": 0.0})
            x["so_chuyen"] += 1
            x["tan"] += p.weight_dest or p.weight_origin or 0
            if p.odo_back is not None and p.odo_out is not None and p.odo_back >= p.odo_out:
                x["km"] += p.odo_back - p.odo_out
            x["doanh_thu_usd"] += c["doanh_thu_usd"]
        # Số ngày trung bình chỉ tính chuyến ĐÃ VỀ: chuyến đang chạy thì "số ngày" còn tăng từng ngày,
        # trộn vào sẽ kéo trung bình lên và làm con số vô nghĩa. Chuyến đang chạy đã có ô "Đi lâu" lo.
        ngay_di = p.out_date or p.doc_date
        if ngay_di and p.transport_status == "arrived" and p.back_date:
            n_ngay = (p.back_date - ngay_di).days
            ngay_di_ds.append(n_ngay)
            if n_ngay <= NGAY_COI_LA_LAU: dung_han += 1

    van_hanh = {
        "nguong_ngay": NGAY_COI_LA_LAU,
        "dung_han_pct": round(dung_han / len(ngay_di_ds) * 100, 1) if ngay_di_ds else None,
        "so_chuyen_tinh": len(ngay_di_ds),
        "ngay_tb": round(sum(ngay_di_ds) / len(ngay_di_ds), 1) if ngay_di_ds else None,
        "hao_hut_tb_pct": round(sum(hao_ds) / len(hao_ds), 2) if hao_ds else None,
    }

    # ---- xem nhanh: đúng những con số màn Theo dõi tuyến đang đếm, để hai màn không nói khác nhau
    su_co = {e.trip_id for e in db.query(TripEvent).filter(TripEvent.status == "reported").all()}
    linh_cho = db.query(Voucher).filter(Voucher.status == "cho").count()
    # "Việc của tôi": mục đang chờ CHÍNH vai này làm (Bãi nhập · kế toán kiểm/ghi sổ · quỹ chi),
    # kèm phiếu đầu tiên để bấm vào chip là mở thẳng chỗ phải làm. Đếm chung tất cả rồi gắn cho mọi
    # vai thì con số không nói lên việc của ai cả.
    viec_toi, viec_phieu = 0, None
    co_phieu = {p.id for p in ds}
    for sec in db.query(TripSection).filter(TripSection.trip_id.in_([p.id for p in ds] or [""])).all():
        if viec_dang_cho(user.role, sec.section, sec.status):
            viec_toi += 1
            if viec_phieu is None and sec.trip_id in co_phieu: viec_phieu = sec.trip_id
    xem_nhanh = {
        "dang_chay": len([p for p in ds if p.transport_status in ("dispatched", "transit")]),
        "di_lau": len([p for p in ds if p.transport_status != "arrived" and (p.out_date or p.doc_date)
                       and (hom_nay - (p.out_date or p.doc_date)).days > NGAY_COI_LA_LAU]),
        "su_co": len([p for p in ds if p.id in su_co]),
        "cho_hoa_don": len([p for p in ds if p.transport_status == "arrived" and not p.invoiced]),
        "viec_toi": viec_toi, "viec_phieu": viec_phieu,
        "phieu_linh_cho": linh_cho,
        "chua_thu": round(sum(tinh_phieu(p, dong[p.id])["doanh_thu_usd"] for p in ds
                              if p.transport_status == "arrived" and p.finance_status != "paid"), 2),
    }

    # ---- dòng thời gian: mốc từ sự kiện "tới điểm" và từ Sổ chứng từ
    ma_diem = {}                      # trip_id → {seq: ngày}
    for e in db.query(TripEvent).filter(TripEvent.trip_id.in_([p.id for p in ds] or [""]),
                                        TripEvent.kind == "arrive_stop").all():
        if e.stop_seq and e.ts:
            d0 = e.ts.date()
            cu = ma_diem.setdefault(e.trip_id, {})
            if e.stop_seq not in cu or d0 < cu[e.stop_seq]: cu[e.stop_seq] = d0
    so_diem = {}                      # route_id → số điểm trên tuyến
    for r_id, n in db.query(RouteStop.route_id, RouteStop.seq).all():
        so_diem[r_id] = max(so_diem.get(r_id, 0), n or 0)
    ct = defaultdict(dict)            # trip_id → {loai: ngày}
    for c in db.query(ChungTu).filter(ChungTu.trip_id.in_([p.id for p in ds] or [""]),
                                      ChungTu.loai.in_(("HD", "PT"))).all():
        ct[c.trip_id][c.loai] = c.ngay

    dong_thoi_gian = []
    for p in ds:
        diem = ma_diem.get(p.id, {})
        n_diem = so_diem.get(p.route_id, 0)
        ngay_di = p.out_date or p.doc_date
        lau = (p.transport_status != "arrived" and ngay_di is not None
               and (hom_nay - ngay_di).days > NGAY_COI_LA_LAU)
        cang = diem.get(n_diem) if n_diem else None
        if cang is None and p.transport_status == "arrived": cang = p.back_date
        moc = {
            "lap_phieu": p.doc_date.isoformat() if p.doc_date else None,
            "xuat_xe": p.out_date.isoformat() if p.out_date else None,
            "toi_bai": diem[2].isoformat() if 2 in diem else None,
            "cua_khau": diem[3].isoformat() if (n_diem >= 4 and 3 in diem) else None,
            "cang": cang.isoformat() if cang else None,
            "hoa_don": ct[p.id]["HD"].isoformat() if ct[p.id].get("HD") else None,
            "thanh_toan": ct[p.id]["PT"].isoformat() if ct[p.id].get("PT") else None,
        }
        dong_thoi_gian.append({
            "doc_no": p.doc_no, "so_xe": p.truck_no, "khach": p.customer_name,
            "trang_thai": "planned" if p.transport_status == "dispatched" else p.transport_status,
            "late": bool(lau), "moc": moc,
        })

    for x in xe.values():
        x["tan"] = round(x["tan"], 2); x["km"] = round(x["km"]); x["doanh_thu_usd"] = round(x["doanh_thu_usd"], 2)
    # Vai không được thấy tiền bán: bỏ hẳn mọi khoá doanh thu, kể cả trong dãy sáu tháng và theo xe.
    if not thay_tien_ban(user.role):
        xem_nhanh.pop("chua_thu", None)
        sau_thang.pop("doanh_thu_usd", None); sau_thang.pop("chua_thu_usd", None)
        if thang_truoc:
            thang_truoc.pop("doanh_thu_usd", None); thang_truoc.pop("chua_thu_usd", None)
        for x in xe.values(): x.pop("doanh_thu_usd", None)
        theo_ngay_ra = [{"ngay": k, "chi_usd": round(v["chi_usd"], 2)} for k, v in sorted(theo_ngay.items())]
    else:
        theo_ngay_ra = [{"ngay": k, "doanh_thu_usd": round(v["doanh_thu_usd"], 2), "chi_usd": round(v["chi_usd"], 2)}
                        for k, v in sorted(theo_ngay.items())]
    return {
        "thang": dau.strftime("%Y-%m"), "thang_truoc": thang_truoc, "sau_thang": sau_thang,
        "theo_ngay": theo_ngay_ra,
        "hao_hut": hao_hut, "xe": sorted(xe.values(), key=lambda x: -(x.get("doanh_thu_usd") or x["tan"])),
        "van_hanh": van_hanh, "xem_nhanh": xem_nhanh, "dong_thoi_gian": dong_thoi_gian,
    }


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
