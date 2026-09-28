# -*- coding: utf-8 -*-
"""Bốn bảng báo cáo trong sheet "ລາຍງານ" của Excel: tổng quan, theo dõi phiếu (họ rất
thích bảng này), xe liên kết, tiền chuyến & tiền nước tài xế.

Mọi con số ở đây đều TÍNH LẠI từ phiếu lúc gọi — không có bảng tổng hợp riêng để rồi lệch.

**Tiền tệ trong báo cáo.** Mỗi phiếu có tiền cước riêng (USD · LAK · CNY · THB), nên cộng thẳng các
con số của nhiều phiếu là cộng táo với cam. Quy tắc ở đây: mọi TỔNG đều quy về **LAK** (tiền gốc,
tỷ giá khoá trên từng phiếu), và đi kèm một ô `*_tien` chia theo từng loại tiền để người đọc thấy
"trong 215 triệu LAK đó có 8.101 USD và 12.000 CNY". Không có con số tổng nào mang nhãn USD nữa.
"""
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from database import get_db
from models import (ChungTu, Customer, Invoice, InvoicePayment, Part, Route, RouteStop, Supplier, TollCard,
                    TollCardMove, Trip, TripEvent, TripExpense, TripPayment, TripSection, Voucher)
from fastapi import Body
from routes.phieu import CO_TOI_DA, da_thu_theo_phieu, loc_phieu, nap_lo, xuat_phieu
from routes.theo_doi import NGAY_COI_LA_LAU
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import QUYEN, thay_tien_ban, thay_tien_chi, viec_dang_cho
from services.tinh_toan import tien_dong, tinh_phieu, ty_gia
from services import dem_bao_cao as DEM

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


def _gon(d):
    """Gom tiền theo từng loại: {"USD": 8101.36, "CNY": 12000}. LAK không có số lẻ."""
    return {k: (round(v) if k in ("LAK", "VND") else round(v, 2)) for k, v in sorted(d.items()) if round(v, 2)}


def _phieu_thang(db, thang):
    dau, cuoi = _thang(thang)
    return (db.query(Trip).filter(Trip.doc_date >= dau, Trip.doc_date <= cuoi)
            .order_by(Trip.doc_date, Trip.doc_no).all()), dau, cuoi


# ---------------------------------------------------------------- nạp GỌN cho báo cáo (24/09, dữ liệu cả năm)
# Một tháng ~30.000 phiếu × ~5 dòng chi. Nạp nguyên đối tượng ORM (bảng phiếu hơn 100 cột) mất 20+ giây, gần như
# toàn bộ là kéo dữ liệu qua mạng — phép tính chỉ chưa tới 1 giây. Nên: phiếu chỉ lấy ĐÚNG các cột tinh_phieu và
# báo cáo cần; dòng chi CỘNG SẴN trong SQL theo phiếu × mục × tiền tệ × ai trả (tinh_phieu chỉ cần tổng từng nhóm
# đó, nên ra đúng từng con số như cộng từng dòng); lọc theo KHOẢNG NGÀY, không gửi danh sách 30.000 mã.
COT_TINH = (Trip.id, Trip.doc_no, Trip.doc_date, Trip.out_date, Trip.back_date, Trip.company, Trip.customer_id,
            Trip.customer_name, Trip.driver_name, Trip.truck_no, Trip.route_id, Trip.transport_status,
            Trip.finance_status, Trip.invoiced, Trip.locked, Trip.weight_origin, Trip.weight_dest, Trip.price,
            Trip.price_ccy, Trip.price_mode, Trip.hire_price, Trip.hire_ccy, Trip.fee_pct, Trip.over_limit_t,
            Trip.over_price, Trip.rate_usd, Trip.rate_thb, Trip.rate_vnd, Trip.rate_cny, Trip.odo_out, Trip.odo_back)


def _trong(dau, cuoi):
    return (Trip.doc_date >= dau, Trip.doc_date <= cuoi)


def _phieu_gon(db, dau, cuoi, *loc):
    return (db.query(*COT_TINH).filter(*_trong(dau, cuoi), *loc).order_by(Trip.doc_date, Trip.doc_no).all())


def _dong_gon(db, dau, cuoi, *loc):
    """{trip_id: [nhóm dòng chi]} — mỗi nhóm có section · currency · paid_by_epl · qty=1 · unit_price=tổng tiền nhóm."""
    tien = func.sum(func.coalesce(TripExpense.qty, 0) * func.coalesce(TripExpense.unit_price, 0))
    q = (db.query(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl,
                  literal(1.0).label("qty"), tien.label("unit_price"))
         .join(Trip, Trip.id == TripExpense.trip_id).filter(*_trong(dau, cuoi), *loc)
         .group_by(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl))
    dong = defaultdict(list)
    for r in q:
        dong[r.trip_id].append(r)
    return dong


def _da_thu_gon(db, dau, cuoi, *loc):
    q = (db.query(TripPayment.trip_id, func.coalesce(func.sum(TripPayment.amount_lak), 0))
         .join(Trip, Trip.id == TripPayment.trip_id).filter(*_trong(dau, cuoi), *loc).group_by(TripPayment.trip_id))
    return {t: float(v or 0) for t, v in q}


@router.get("/api/bao-cao/tong-quan")
def tong_quan(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    dau, cuoi = _thang(thang)
    t = _gop_tq(_theo_ngay(db, "tq", _cac_ngay(dau, cuoi), _tq_lo).values())
    chu_y = list(t["chu_y"])
    if t["cho_kiem"]:
        chu_y.append({"loai": "cho_kiem", "so": t["cho_kiem"]})
    ra = {"tu": dau.isoformat(), "den": cuoi.isoformat(), "so_phieu": t["so_phieu"],
          "doanh_thu_lak": round(t["doanh_thu"]), "doanh_thu_tien": _gon(t["theo_tien"]),
          "chi_lak": round(t["chi_lak"]), "tan_giao": round(t["tan"], 2),
          "chua_thu_lak": round(t["chua_thu_lak"]), "chua_thu_tien": _gon(t["chua_thu_tien"]), "chua_thu_so": t["chua_thu_so"],
          "dem": t["dem"], "chi_theo_muc": {k: round(v) for k, v in t["theo_muc"].items()}, "chu_y": chu_y[:12]}
    # Vai không được thấy tiền bán thì máy chủ BỎ HẲN các khoá đó, không chỉ giấu ở giao diện.
    if not thay_tien_ban(user.role):
        for k in ("doanh_thu_lak", "doanh_thu_tien", "chua_thu_lak", "chua_thu_tien", "chua_thu_so"):
            ra.pop(k, None)
    if not thay_tien_chi(user.role):
        # anh Khampla A2 (23/09): Bãi không thấy cả tiền CHI — tổng chi và cơ cấu chi
        ra.pop("chi_lak", None); ra.pop("chi_theo_muc", None)
    return ra


# ================================================================ báo cáo tháng = cộng các NGÀY đã tính sẵn
# Dữ liệu cả năm (24/09): tháng này bị ghi liên tục (nghìn chuyến / ngày). Đệm cả tháng thì mỗi lần ghi là cả tháng
# phải cộng lại; đệm từng NGÀY thì ghi vào phiếu hôm nay chỉ hôm nay phải cộng lại — 29 ngày kia vẫn nguyên. Mỗi ngày
# chỉ giữ những con số CỘNG DỒN được (tổng, số đếm, danh sách đã cắt ngắn); phần nào phụ thuộc "hôm nay" (đi lâu, trễ)
# thì giữ dạng thô (ngày xuất xe) và tính lúc ghép. Công thức vẫn là tinh_phieu — kiem/thu_bao_cao_cu_moi.py so từng số.
def _cac_ngay(dau, cuoi):
    return [dau + dt.timedelta(days=i) for i in range((cuoi - dau).days + 1)]


def _theo_ngay(db, loai, cac_ngay, tinh_lo):
    return DEM.lay_ngay(db, loai, cac_ngay, lambda thieu: tinh_lo(db, thieu))


def _dong_loc(db, *loc):
    """{trip_id: [nhóm dòng chi]} cộng sẵn trong SQL theo mục × tiền tệ × ai trả — như _dong_gon, lọc tuỳ ý."""
    tien = func.sum(func.coalesce(TripExpense.qty, 0) * func.coalesce(TripExpense.unit_price, 0))
    q = (db.query(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl,
                  literal(1.0).label("qty"), tien.label("unit_price"))
         .join(Trip, Trip.id == TripExpense.trip_id).filter(*loc)
         .group_by(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl))
    dong = defaultdict(list)
    for r in q:
        dong[r.trip_id].append(r)
    return dong


def _da_thu_loc(db, *loc):
    q = (db.query(TripPayment.trip_id, func.coalesce(func.sum(TripPayment.amount_lak), 0))
         .join(Trip, Trip.id == TripPayment.trip_id).filter(*loc).group_by(TripPayment.trip_id))
    return {t: float(v or 0) for t, v in q}


def _chi_epl(p, c):
    """Chi của EPL: xe nhà là tổng chi; xe liên kết là tiền thuê trừ phần giữ lại (đã tính sẵn ra LAK)."""
    return (c["tien_thue_lak"] - c["giu_lai"] * ty_gia(p, c["hire_ccy"])) if c["lien_ket"] else c["tong_chi_lak"]


def _tq_trong(cho_kiem=0):
    return {"so_phieu": 0, "doanh_thu": 0.0, "theo_tien": {}, "chi_lak": 0.0,
            "theo_muc": {"fuel": 0.0, "travel": 0.0, "repair": 0.0, "other": 0.0}, "tan": 0.0,
            "chua_thu_lak": 0.0, "chua_thu_so": 0, "chua_thu_tien": {},
            "dem": {"dispatched": 0, "transit": 0, "arrived": 0, "invoiced": 0, "paid": 0}, "chu_y": [], "cho_kiem": cho_kiem}


def _cong(a, b):
    for k, v in b.items():
        a[k] = a.get(k, 0) + v


def _tq_lo(db, cac_ngay):
    """Phần TỔNG QUAN của từng ngày — cùng phép tính với tổng quan tháng trước 24/09, chỉ chia theo ngày lập phiếu."""
    loc = (Trip.doc_date.in_(cac_ngay),)
    ds = db.query(*COT_TINH).filter(*loc).order_by(Trip.doc_date, Trip.doc_no).all()
    dong, thu = _dong_loc(db, *loc), _da_thu_loc(db, *loc)
    cho_kiem = dict(db.query(Trip.doc_date, func.count(TripSection.id)).join(Trip, Trip.id == TripSection.trip_id)
                    .filter(*loc, TripSection.status == "entered").group_by(Trip.doc_date).all())
    ra = {d.isoformat(): _tq_trong(cho_kiem.get(d, 0)) for d in cac_ngay}
    for p in ds:
        o = ra[p.doc_date.isoformat()]
        c = tinh_phieu(p, dong[p.id], thu.get(p.id, 0))
        o["so_phieu"] += 1
        o["doanh_thu"] += c["doanh_thu_lak"]
        o["theo_tien"][c["ccy"]] = o["theo_tien"].get(c["ccy"], 0.0) + c["doanh_thu"]
        o["chi_lak"] += _chi_epl(p, c)
        for m in o["theo_muc"]: o["theo_muc"][m] += c["chi"][m]
        if p.weight_dest: o["tan"] += p.weight_dest
        # Chưa thu = phần hoá đơn CHƯA VỀ TIỀN, không phải cả doanh thu của phiếu chưa đánh dấu "đã thu".
        if p.transport_status == "arrived" and c["con_lai_lak"] > 0:
            o["chua_thu_lak"] += c["con_lai_lak"]; o["chua_thu_so"] += 1
            o["chua_thu_tien"][c["ccy"]] = o["chua_thu_tien"].get(c["ccy"], 0.0) + c["con_lai"]
        o["dem"][p.transport_status] = o["dem"].get(p.transport_status, 0) + 1
        if p.invoiced: o["dem"]["invoiced"] += 1
        if p.finance_status == "paid": o["dem"]["paid"] += 1
        # Việc cần chú ý — mỗi ngày giữ 12 dòng đầu là đủ: cả tháng cũng chỉ hiện 12 dòng đầu theo thứ tự phiếu
        for x in ([{"loai": "hao_hut", "doc_no": p.doc_no, "gia_tri": c["hao_hut_pct"]}]
                  if c["hao_hut_pct"] is not None and c["hao_hut_pct"] > 1.5 else []) \
                + ([{"loai": "chua_hoa_don", "doc_no": p.doc_no}] if p.transport_status == "arrived" and not p.invoiced else []) \
                + ([{"loai": "chua_can", "doc_no": p.doc_no}] if p.transport_status == "arrived" and p.weight_dest is None else []):
            if len(o["chu_y"]) < 12:
                o["chu_y"].append(x)
    return ra


def _gop_tq(cac):
    t = _tq_trong()
    for o in cac:                            # theo thứ tự ngày
        for k in ("so_phieu", "doanh_thu", "chi_lak", "tan", "chua_thu_lak", "chua_thu_so", "cho_kiem"):
            t[k] += o[k]
        for k in ("theo_tien", "theo_muc", "chua_thu_tien", "dem"):
            _cong(t[k], o[k])
        t["chu_y"].extend(o["chu_y"][:max(0, 12 - len(t["chu_y"]))])
    return t


def _gom_thang(db, dau, cuoi, tq=None):
    """Bốn con số của một tháng — cùng công thức với /api/bao-cao/tong-quan để hai màn không lệch nhau."""
    t = _gop_tq((tq or _theo_ngay(db, "tq", _cac_ngay(dau, cuoi), _tq_lo)).get(d.isoformat()) for d in _cac_ngay(dau, cuoi))
    return {"doanh_thu_lak": round(t["doanh_thu"]), "chi_lak": round(t["chi_lak"]),
            "tan_giao": round(t["tan"], 2), "chua_thu_lak": round(t["chua_thu_lak"])}


def _lui_thang(y, m, n):
    """Lùi n tháng từ (y, m)."""
    t = (y * 12 + (m - 1)) - n
    return t // 12, t % 12 + 1


def _xh_trong():
    return {"tn": None, "hao": [], "hao_tong": 0, "hao_vuot": 0, "hao_sum": 0.0, "hao_n": 0, "xe": {},
            "ve": [0, 0, 0], "su_co": 0, "muc": {}, "cho_hd": [0, None], "cho_thu": [0, None],
            "dang_chay": 0, "cho_hoa_don": 0, "chua_thu_ve": 0.0, "khong_ve": {}, "tg": [], "tg_tong": 0}


def _xh_lo(db, cac_ngay):
    """Phần XU HƯỚNG của từng ngày (theo ngày · hao hụt · theo xe · vận hành · xem nhanh · dòng thời gian)."""
    loc = (Trip.doc_date.in_(cac_ngay),)
    ds = db.query(*COT_TINH).filter(*loc).order_by(Trip.doc_date, Trip.doc_no).all()
    dong, thu = _dong_loc(db, *loc), _da_thu_loc(db, *loc)
    ra = {d.isoformat(): _xh_trong() for d in cac_ngay}
    vi_tri = {}                              # trip_id → (ngày, thứ tự trong ngày) — để biết phiếu nào "đầu tiên"
    su_co = {t for (t,) in db.query(TripEvent.trip_id).join(Trip, Trip.id == TripEvent.trip_id)
             .filter(*loc, TripEvent.status == "reported").distinct()}
    ma_diem = {}                             # trip_id → {seq: ngày}
    for e in (db.query(TripEvent.trip_id, TripEvent.stop_seq, TripEvent.ts).join(Trip, Trip.id == TripEvent.trip_id)
              .filter(*loc, TripEvent.kind == "arrive_stop")):
        if e.stop_seq and e.ts:
            d0 = e.ts.date()
            cu = ma_diem.setdefault(e.trip_id, {})
            if e.stop_seq not in cu or d0 < cu[e.stop_seq]: cu[e.stop_seq] = d0
    so_diem = {}                             # route_id → số điểm trên tuyến
    for r_id, n in db.query(RouteStop.route_id, RouteStop.seq).all():
        so_diem[r_id] = max(so_diem.get(r_id, 0), n or 0)
    ct = defaultdict(dict)                   # trip_id → {loai: ngày}
    for c in (db.query(ChungTu.trip_id, ChungTu.loai, ChungTu.ngay).join(Trip, Trip.id == ChungTu.trip_id)
              .filter(*loc, ChungTu.loai.in_(("HD", "PT")))):
        ct[c.trip_id][c.loai] = c.ngay
    xong_ra = defaultdict(list)              # dòng thời gian đã thanh toán & đã về: mỗi ngày chỉ cần 60 dòng mới nhất
    for i, p in enumerate(ds):
        k = p.doc_date.isoformat()
        o = ra[k]
        vi_tri[p.id] = (k, i)
        c = tinh_phieu(p, dong[p.id], thu.get(p.id, 0))
        if o["tn"] is None:
            o["tn"] = {"doanh_thu_lak": 0.0, "chi_lak": 0.0}
        o["tn"]["doanh_thu_lak"] += c["doanh_thu_lak"]; o["tn"]["chi_lak"] += c["tong_chi_lak"]
        if p.weight_origin and p.weight_dest is not None:
            pct = round((p.weight_origin - p.weight_dest) / p.weight_origin * 100, 2)
            o["hao"].append({"doc_no": p.doc_no, "so_xe": p.truck_no, "can_dau": p.weight_origin, "can_cuoi": p.weight_dest, "pct": pct})
            o["hao_tong"] += 1; o["hao_vuot"] += pct > HAO_HUT_NGUONG
            if c["hao_hut_pct"] is not None: o["hao_sum"] += c["hao_hut_pct"]; o["hao_n"] += 1
        if p.truck_no:
            x = o["xe"].setdefault(p.truck_no, {"so_xe": p.truck_no, "so_chuyen": 0, "tan": 0.0, "km": 0.0, "doanh_thu_lak": 0.0})
            x["so_chuyen"] += 1
            x["tan"] += p.weight_dest or p.weight_origin or 0
            if p.odo_back is not None and p.odo_out is not None and p.odo_back >= p.odo_out:
                x["km"] += p.odo_back - p.odo_out
            x["doanh_thu_lak"] += c["doanh_thu_lak"]
        # Số ngày trung bình chỉ tính chuyến ĐÃ VỀ (chuyến đang chạy thì số ngày còn tăng từng ngày)
        ngay_di = p.out_date or p.doc_date
        if ngay_di and p.transport_status == "arrived" and p.back_date:
            n_ngay = (p.back_date - ngay_di).days
            o["ve"][0] += 1; o["ve"][1] += n_ngay; o["ve"][2] += n_ngay <= NGAY_COI_LA_LAU
        if p.id in su_co: o["su_co"] += 1
        if p.locked and not p.invoiced:
            o["cho_hd"][0] += 1; o["cho_hd"][1] = o["cho_hd"][1] or p.id
        if p.invoiced and p.finance_status != "paid":
            o["cho_thu"][0] += 1; o["cho_thu"][1] = o["cho_thu"][1] or p.id
        if p.transport_status in ("dispatched", "transit"): o["dang_chay"] += 1
        if p.transport_status == "arrived" and not p.invoiced: o["cho_hoa_don"] += 1
        if p.transport_status == "arrived": o["chua_thu_ve"] += c["con_lai_lak"]
        if p.transport_status != "arrived" and ngay_di is not None:           # "đi lâu" tính lúc ghép (theo hôm nay)
            o["khong_ve"][ngay_di.isoformat()] = o["khong_ve"].get(ngay_di.isoformat(), 0) + 1
        # dòng thời gian: mốc từ sự kiện "tới điểm" và từ Sổ chứng từ
        diem = ma_diem.get(p.id, {})
        n_diem = so_diem.get(p.route_id, 0)
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
        dong_tg = {"doc_no": p.doc_no, "so_xe": p.truck_no, "khach": p.customer_name,
                   "trang_thai": "planned" if p.transport_status == "dispatched" else p.transport_status,
                   "moc": moc, "_di": ngay_di.isoformat() if ngay_di else None, "_chua_ve": p.transport_status != "arrived",
                   "_k": [k, i]}             # vị trí gốc (ngày, thứ tự phiếu) — hoà nhau thì đứng như danh sách phiếu
        o["tg_tong"] += 1
        if moc["thanh_toan"] is None or dong_tg["_chua_ve"]:
            o["tg"].append(dong_tg)
        else:
            xong_ra[k].append(dong_tg)
    for k, cac in xong_ra.items():           # đã thanh toán + đã về: nhóm cuối của Gantt, chỉ 60 dòng mới nhất mỗi ngày
        ra[k]["tg"].extend(sorted(cac, key=lambda r: (_dao(r["moc"].get("xuat_xe") or r["moc"].get("lap_phieu") or ""), r["_k"][1]))[:GANTT_TOI_DA])
    # việc đang chờ theo (mục, trạng thái) — vai nào lo mục nào thì tính lúc ghép (một phần dùng cho mọi vai)
    for tid, sec, st in (db.query(TripSection.trip_id, TripSection.section, TripSection.status)
                         .join(Trip, Trip.id == TripSection.trip_id).filter(*loc)):
        k, i = vi_tri.get(tid, (None, None))
        if k is None:
            continue
        m = ra[k]["muc"].setdefault("%s|%s" % (sec, st), [0, None, None])
        m[0] += 1
        if m[2] is None or i < m[2]:
            m[1], m[2] = tid, i
    for o in ra.values():
        o["hao"] = sorted(o["hao"], key=lambda x: -x["pct"])[:HAO_HUT_TOI_DA]
    return ra


@router.get("/api/bao-cao/xu-huong")
def xu_huong(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Số liệu xu hướng cho màn Tổng quan: so tháng trước, sáu tháng gần nhất, theo ngày, hao hụt,
    hiệu suất xe, vận hành, xem nhanh, và dòng thời gian từng chuyến.

    Mốc dòng thời gian lấy từ dữ liệu THẬT, không suy diễn: ngày lập phiếu · ngày xuất xe · các mốc
    "tới điểm" Bãi đã bấm trên tuyến (điểm 2 = về bãi, điểm 3 = cửa khẩu, điểm cuối = nơi giao) ·
    ngày hoá đơn và ngày thu lấy từ Sổ chứng từ (HD, PT). Mốc nào chưa có thì để trống, màn hình vẽ
    đoạn đó là "đang diễn ra".
    Dữ liệu cả năm (24/09): ghép từ phần tính sẵn của từng NGÀY (xem _xh_lo, _tq_lo) — chỉ ngày có dữ liệu vừa đổi
    mới phải tính lại."""
    vai = user.role
    dau, cuoi = _thang(thang)
    hom_nay = dt.date.today()

    # ---- tháng trước và sáu tháng gần nhất (cũ → mới, kể cả tháng đang xem) — MỘT lượt đệm cho cả 180 ngày
    y, m = dau.year, dau.month
    khoang = []
    for i in range(5, -1, -1):
        yy, mm = _lui_thang(y, m, i)
        d1 = dt.date(yy, mm, 1)
        khoang.append((i, yy, mm, d1, dt.date(yy + (mm == 12), (mm % 12) + 1, 1) - dt.timedelta(days=1)))
    tq = _theo_ngay(db, "tq", [d for _, _, _, d1, d2 in khoang for d in _cac_ngay(d1, d2)], _tq_lo)
    sau_thang = {"nhan": [], "doanh_thu_lak": [], "chi_lak": [], "tan_giao": [], "chua_thu_lak": []}
    thang_truoc = None
    for i, yy, mm, d1, d2 in khoang:
        g = _gom_thang(db, d1, d2, tq=tq)
        sau_thang["nhan"].append("%02d/%02d" % (mm, yy % 100))
        for k in ("doanh_thu_lak", "chi_lak", "tan_giao", "chua_thu_lak"):
            sau_thang[k].append(g[k])
        if i == 1:
            thang_truoc = g

    # ---- ghép phần của từng ngày trong tháng đang xem
    ngay = _theo_ngay(db, "xh", _cac_ngay(dau, cuoi), _xh_lo)
    theo_ngay, hao_hut, xe = {}, [], {}
    hao_tong = hao_vuot = hao_n = 0; hao_sum = 0.0
    ve = [0, 0, 0]
    muc, cho_hd, cho_thu = {}, [0, None], [0, None]
    xn = {"dang_chay": 0, "su_co": 0, "cho_hoa_don": 0, "di_lau": 0}
    chua_thu_ve = 0.0
    dong_thoi_gian, dong_thoi_gian_tong = [], 0
    for k in sorted(ngay):
        o = ngay[k]
        if o["tn"] is not None:
            theo_ngay[k] = o["tn"]
        hao_hut.extend(o["hao"]); hao_tong += o["hao_tong"]; hao_vuot += o["hao_vuot"]
        hao_sum += o["hao_sum"]; hao_n += o["hao_n"]
        for sx, v in o["xe"].items():
            x = xe.setdefault(sx, {"so_xe": sx, "so_chuyen": 0, "tan": 0.0, "km": 0.0, "doanh_thu_lak": 0.0})
            for f in ("so_chuyen", "tan", "km", "doanh_thu_lak"):
                x[f] += v[f]
        for j in range(3):
            ve[j] += o["ve"][j]
        for mk, (n, tid, _i) in o["muc"].items():
            mm_ = muc.setdefault(mk, [0, None])
            mm_[0] += n
            mm_[1] = mm_[1] or tid           # ngày sớm hơn đứng trước
        for dich, nguon in ((cho_hd, o["cho_hd"]), (cho_thu, o["cho_thu"])):
            dich[0] += nguon[0]; dich[1] = dich[1] or nguon[1]
        for f in ("dang_chay", "su_co", "cho_hoa_don"):
            xn[f] += o[f]
        chua_thu_ve += o["chua_thu_ve"]
        for di, n in o["khong_ve"].items():
            if (hom_nay - dt.date.fromisoformat(di)).days > NGAY_COI_LA_LAU:
                xn["di_lau"] += n
        dong_thoi_gian_tong += o["tg_tong"]
        dong_thoi_gian.extend(o["tg"])
    van_hanh = {
        "nguong_ngay": NGAY_COI_LA_LAU,
        "dung_han_pct": round(ve[2] / ve[0] * 100, 1) if ve[0] else None,
        "so_chuyen_tinh": ve[0],
        "ngay_tb": round(ve[1] / ve[0], 1) if ve[0] else None,
        "hao_hut_tb_pct": round(hao_sum / hao_n, 2) if hao_n else None,
    }
    # "Việc của tôi": mục đang chờ CHÍNH vai này làm, kèm phiếu đầu tiên để bấm vào chip là mở thẳng chỗ phải làm.
    # KT Doanh thu KHÔNG phụ trách mục nào — việc của họ ở MỨC PHIẾU: đã khoá chưa xuất hoá đơn, hoá đơn chưa thu đủ.
    if vai == "rev":
        viec_toi, viec_phieu = cho_hd[0] + cho_thu[0], cho_hd[1] or cho_thu[1]
    else:
        viec_toi, viec_phieu = 0, None
        for mk in sorted(muc, key=lambda z: z):
            sec, st = mk.split("|", 1)
            if viec_dang_cho(vai, sec, None if st == "None" else st):
                viec_toi += muc[mk][0]
        # phiếu đầu tiên (ngày sớm nhất, thứ tự phiếu) có việc của vai này
        for k in sorted(ngay):
            cands = [(i, tid) for mk, (n, tid, i) in ngay[k]["muc"].items()
                     if viec_dang_cho(vai, mk.split("|", 1)[0], None if mk.split("|", 1)[1] == "None" else mk.split("|", 1)[1])]
            if cands:
                viec_phieu = min(cands)[1]
                break
    xem_nhanh = {
        "dang_chay": xn["dang_chay"], "di_lau": xn["di_lau"], "su_co": xn["su_co"], "cho_hoa_don": xn["cho_hoa_don"],
        "viec_toi": viec_toi, "viec_phieu": viec_phieu,
        "phieu_linh_cho": db.query(Voucher).filter(Voucher.status == "cho").count(),
        "chua_thu_lak": round(chua_thu_ve),
    }
    # Dữ liệu cả năm (24/09): một tháng ~30.000 chuyến — biểu đồ một cột mỗi chuyến, Gantt một dòng mỗi chuyến là treo
    # trình duyệt. Trả 50 chuyến hao hụt NẶNG NHẤT và 60 dòng thời gian CẦN NHÌN NHẤT, kèm số đếm thật của cả tháng.
    hao_hut_dem = {"tong": hao_tong, "vuot": hao_vuot, "nguong": HAO_HUT_NGUONG}
    hao_hut = sorted(hao_hut, key=lambda x: -x["pct"])[:HAO_HUT_TOI_DA]
    for r in dong_thoi_gian:                 # "trễ" tính theo HÔM NAY, lúc ghép
        r["late"] = bool(r["_chua_ve"] and r["_di"] is not None
                         and (hom_nay - dt.date.fromisoformat(r["_di"])).days > NGAY_COI_LA_LAU)

    def uu_tien(r):
        """đi lâu → đang chạy → chưa xuất bến → đã thanh toán; trong mỗi nhóm, xuất xe mới nhất lên trước."""
        xong = r["moc"].get("thanh_toan") is not None
        nhom = 0 if r["late"] else 1 if (not xong and r["trang_thai"] != "planned") else 2 if not xong else 3
        return nhom, _dao(r["moc"].get("xuat_xe") or r["moc"].get("lap_phieu") or ""), r["_k"][0], r["_k"][1]
    dong_thoi_gian = [{"doc_no": r["doc_no"], "so_xe": r["so_xe"], "khach": r["khach"], "trang_thai": r["trang_thai"],
                       "late": r["late"], "moc": r["moc"]} for r in sorted(dong_thoi_gian, key=uu_tien)[:GANTT_TOI_DA]]

    for x in xe.values():
        x["tan"] = round(x["tan"], 2); x["km"] = round(x["km"]); x["doanh_thu_lak"] = round(x["doanh_thu_lak"])
    # Vai không được thấy tiền bán: bỏ hẳn mọi khoá doanh thu, kể cả trong dãy sáu tháng và theo xe.
    if not thay_tien_ban(vai):
        xem_nhanh.pop("chua_thu_lak", None)
        sau_thang.pop("doanh_thu_lak", None); sau_thang.pop("chua_thu_lak", None)
        if thang_truoc:
            thang_truoc.pop("doanh_thu_lak", None); thang_truoc.pop("chua_thu_lak", None)
        for x in xe.values(): x.pop("doanh_thu_lak", None)
        theo_ngay_ra = [{"ngay": k, "chi_lak": round(v["chi_lak"])} for k, v in sorted(theo_ngay.items())]
    else:
        theo_ngay_ra = [{"ngay": k, "doanh_thu_lak": round(v["doanh_thu_lak"]), "chi_lak": round(v["chi_lak"])}
                        for k, v in sorted(theo_ngay.items())]
    if not thay_tien_chi(vai):
        # A2: Bãi không thấy tiền chi — bỏ dãy chi theo tháng, theo ngày
        sau_thang.pop("chi_lak", None)
        if thang_truoc:
            thang_truoc.pop("chi_lak", None)
        theo_ngay_ra = []
    return {
        "thang": dau.strftime("%Y-%m"), "thang_truoc": thang_truoc, "sau_thang": sau_thang,
        "theo_ngay": theo_ngay_ra,
        "hao_hut": hao_hut, "xe": sorted(xe.values(), key=lambda x: -(x.get("doanh_thu_lak") or x["tan"])),
        "van_hanh": van_hanh, "xem_nhanh": xem_nhanh, "dong_thoi_gian": dong_thoi_gian,
        "hao_hut_dem": hao_hut_dem, "dong_thoi_gian_tong": dong_thoi_gian_tong,
    }


HAO_HUT_NGUONG = 1.5        # % — cùng ngưỡng với "việc cần chú ý" của tổng quan
HAO_HUT_TOI_DA = 50
GANTT_TOI_DA = 60


def _dao(chuoi):
    """Khoá sắp xếp NGƯỢC cho chuỗi ngày ISO (mới nhất lên trước); chưa có ngày thì xuống cuối nhóm."""
    return "".join(chr(0x10FFFF - ord(c)) for c in chuoi) if chuoi else chr(0x10FFFF) * 11


def _trang_phieu(response, qs, trang, co):
    """Phân trang chung cho các bảng một-dòng-một-phiếu: X-Tong = tổng số dòng khớp; không có `co` thì trả CẢ THÁNG
    (xuất Excel cần đủ), có `co` thì một trang (tối đa CO_TOI_DA)."""
    response.headers["X-Tong"] = str(qs.order_by(None).count())
    qs = qs.order_by(Trip.doc_date, Trip.doc_no)
    if co:
        co = max(1, min(int(co), CO_TOI_DA))
        qs = qs.offset((max(1, int(trang or 1)) - 1) * co).limit(co)
    return qs.all()


def _loc_td(qs, q=None, transport_status=None, finance_status=None, company=None):
    """Bộ lọc của bảng theo dõi — chạy trong SQL (trước đây lọc trên trình duyệt, phải tải cả tháng về)."""
    if transport_status: qs = qs.filter(Trip.transport_status == transport_status)
    if finance_status: qs = qs.filter(Trip.finance_status == finance_status)
    if company: qs = qs.filter(Trip.company == company)
    return loc_phieu(qs, q)


@router.get("/api/bao-cao/theo-doi/tong")
def theo_doi_tong(thang: str = None, q: str = None, transport_status: str = None, finance_status: str = None,
                  company: str = None, quy: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Dòng TỔNG của bảng theo dõi trên TOÀN BỘ phiếu khớp bộ lọc (không chỉ trang đang xem) — cộng riêng từng loại
    tiền; `quy` (LAK · USD · …) thì mọi phiếu quy theo tỷ giá đã khoá trên chính phiếu đó, còn một con số. Cùng cách
    cộng với giao diện trước đây (modules/theo-doi: cong / ve_tien)."""
    dau, cuoi = _thang(thang)
    # ghép từ phần tính sẵn của từng NGÀY cho đúng bộ lọc này (tính một lần cho mọi vai, bỏ khoá theo vai trên bản chép)
    loc = (q or "", transport_status or "", finance_status or "", company or "", (quy or "").strip().upper())
    cac = _cac_ngay(dau, cuoi)
    viec = [(("tdt", d.isoformat()) + loc, [d.isoformat()], None) for d in cac]
    tong = {"so_phieu": 0, "tong_chi_lak": 0.0, "doanh_thu": {}, "da_thu": {}, "con_lai": {}, "lai": {}}
    for phan in DEM.lay_nhieu(db, viec, tinh_lo=lambda thieu: _tdt_lo(db, [cac[i] for i in thieu], *loc)):
        tong["so_phieu"] += phan["so_phieu"]; tong["tong_chi_lak"] += phan["tong_chi_lak"]
        for k in ("doanh_thu", "da_thu", "con_lai", "lai"):
            _cong(tong[k], phan[k])
    ra = {"so_phieu": tong["so_phieu"], "tong_chi_lak": round(tong["tong_chi_lak"]),
          **{k: _tron_tien(tong[k]) for k in ("doanh_thu", "da_thu", "con_lai", "lai")}}
    if not thay_tien_ban(user.role):
        for k in ("doanh_thu", "da_thu", "con_lai", "lai"):
            ra.pop(k, None)
    if not thay_tien_chi(user.role):
        ra.pop("tong_chi_lak", None)
    return ra


def _tdt_lo(db, cac_ngay, q, transport_status, finance_status, company, quy):
    """Phần DÒNG TỔNG của từng ngày cho một bộ lọc: số phiếu · tổng chi LAK · bốn khoản theo từng loại tiền."""
    loc = _loc_td(db.query(Trip.id).filter(Trip.doc_date.in_(cac_ngay)), q or None, transport_status or None,
                  finance_status or None, company or None).subquery()
    ds = db.query(*COT_TINH).filter(Trip.id.in_(db.query(loc.c.id))).all()
    dong = _dong_loc(db, Trip.id.in_(db.query(loc.c.id)))
    thu = _da_thu_loc(db, Trip.id.in_(db.query(loc.c.id)))
    dich = (quy or "").strip().upper() or None
    ra = {d.isoformat(): {"so_phieu": 0, "tong_chi_lak": 0.0, "doanh_thu": {}, "da_thu": {}, "con_lai": {}, "lai": {}}
          for d in cac_ngay}
    for p in ds:
        o = ra[p.doc_date.isoformat()]
        c = tinh_phieu(p, dong.get(p.id, []), thu.get(p.id, 0))
        o["so_phieu"] += 1
        o["tong_chi_lak"] += c.get("tong_chi_lak") or 0
        for k in ("doanh_thu", "da_thu", "con_lai", "lai"):
            v = c.get(k)
            if v is None:
                continue
            ma = c["ccy"]
            if dich and dich != ma:
                v, ma = v * ty_gia(p, ma) / ty_gia(p, dich), dich
            o[k][ma] = o[k].get(ma, 0.0) + v
    return [ra[d.isoformat()] for d in cac_ngay]


def _theo_doi_tong_tinh(db, dau, cuoi, q, transport_status, finance_status, company, quy):
    """Cách tính cả tháng một lượt (trước 24/09) — GIỮ làm thước đo: kiem/thu_bao_cao_cu_moi.py so với bản theo ngày."""
    loc = _loc_td(db.query(Trip.id).filter(*_trong(dau, cuoi)), q, transport_status, finance_status, company)
    con = loc.subquery()
    ds = db.query(*COT_TINH).filter(Trip.id.in_(db.query(con.c.id))).all()
    dong = defaultdict(list)
    for r in (db.query(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl,
                       literal(1.0).label("qty"),
                       func.sum(func.coalesce(TripExpense.qty, 0) * func.coalesce(TripExpense.unit_price, 0)).label("unit_price"))
              .filter(TripExpense.trip_id.in_(db.query(con.c.id)))
              .group_by(TripExpense.trip_id, TripExpense.section, TripExpense.currency, TripExpense.paid_by_epl)):
        dong[r.trip_id].append(r)
    thu = {t: float(v or 0) for t, v in (db.query(TripPayment.trip_id, func.coalesce(func.sum(TripPayment.amount_lak), 0))
                                         .filter(TripPayment.trip_id.in_(db.query(con.c.id))).group_by(TripPayment.trip_id))}
    dich = (quy or "").strip().upper() or None
    tong = {"doanh_thu": defaultdict(float), "da_thu": defaultdict(float), "con_lai": defaultdict(float), "lai": defaultdict(float)}
    chi = 0.0
    for p in ds:
        c = tinh_phieu(p, dong.get(p.id, []), thu.get(p.id, 0))
        for k in tong:
            v = c.get(k)
            if v is None:
                continue
            ma = c["ccy"]
            if dich and dich != ma:
                v, ma = v * ty_gia(p, ma) / ty_gia(p, dich), dich
            tong[k][ma] += v
        chi += c.get("tong_chi_lak") or 0
    ra = {"so_phieu": len(ds), "tong_chi_lak": round(chi)}
    for k, v in tong.items():
        ra[k] = _tron_tien(v)
    return ra


def _tron_tien(theo_tien):
    """{mã tiền: số} làm tròn đúng loại tiền: LAK · VND số chẵn, tiền khác 2 chữ số lẻ (giữ cả loại tiền bằng 0)."""
    return {m: (round(x) if m in ("LAK", "VND") else round(x, 2)) for m, x in theo_tien.items()}


@router.get("/api/bao-cao/theo-doi")
def theo_doi(response: Response, thang: str = None, trang: int = 1, co: int = None, q: str = None,
             transport_status: str = None, finance_status: str = None, company: str = None,
             db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bảng "ລາຍງານ ຕິດຕາມໃບຂົນສົ່ງສິນຄ້າ" — một dòng một phiếu, đủ 29 cột như Excel.

    Vai không được thấy tiền bán thì các cột cước, doanh thu, lãi **không có trong gói trả về** —
    không phải chỉ ẩn cột ở giao diện.
    Dữ liệu cả năm (24/09): không ghi tháng thì là THÁNG NÀY — trước đây là mọi phiếu từ trước tới nay."""
    dau, cuoi = _thang(thang)
    ds = _trang_phieu(response, _loc_td(db.query(Trip).filter(*_trong(dau, cuoi)), q, transport_status, finance_status, company),
                      trang, co)
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    nap = nap_lo(db, ds)
    return [xuat_phieu(db, p, day_du=False, da_thu=thu.get(p.id, 0), vai=user.role, nap=nap) for p in ds]


@router.get("/api/bao-cao/can-tru")
def can_tru(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """CẤN TRỪ CUỐI THÁNG với khách — gộp hai thứ khách đã trả hộ EPL (anh Khampla C5.1 · C6.1).

    Bên Lào có hai chỗ tiền chạy ngược chiều với cước:
      · **Thẻ cao tốc** khách cấp và nạp tiền — EPL quẹt bao nhiêu thì khách đã trả hộ bấy nhiêu.
      · **Trạm dầu bên Việt Nam** ghi nợ — cuối tháng không trả tiền mặt mà trừ vào cước của khách
        đứng ra với trạm.

    Cả hai đều là "khách trả hộ", nên bảng này đặt chúng cạnh **cước phải thu trong tháng** để ra
    một con số: còn phải thu bao nhiêu sau khi cấn trừ. Bên mình CHỈ GHI VÀ HIỆN — bút toán cấn trừ
    là việc của bên kế toán anh Khang, đúng như mọi chỗ khác.
    """
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem cấn trừ cước." % user.role})
    dau, cuoi = _thang(thang)
    return _can_tru_tinh(db, thang, dau, cuoi)


def _ct_lo(db, cac_ngay):
    """Hai phần NẶNG của cấn trừ, cho từng ngày lập phiếu:
       "kh":   {customer_id: [tên, cước LAK]}                       — cước phải thu theo khách
       "tram": {supplier_id: [số dòng, nợ LAK]}                      — dòng dầu GHI NỢ tại trạm (EPL ứng)
    Trạm nào cấn trừ cho khách nào thì đọc MỚI từ danh mục lúc ghép — đổi khách của trạm là đúng ngay, không chờ đệm."""
    from routes.nha_cung_cap import _tien_lak_sql
    loc = (Trip.doc_date.in_(cac_ngay), Trip.customer_id.isnot(None))
    ds = db.query(*COT_TINH).filter(*loc).order_by(Trip.doc_date, Trip.doc_no).all()
    dong = _dong_loc(db, *loc)
    ra = {d.isoformat(): {"kh": {}, "tram": {}} for d in cac_ngay}
    for p in ds:
        k = tinh_phieu(p, dong.get(p.id, []))
        o = ra[p.doc_date.isoformat()]["kh"].setdefault(p.customer_id, [p.customer_name, 0.0])
        o[1] += k["doanh_thu_lak"]
    for d, sid, n, x in (db.query(Trip.doc_date, TripExpense.supplier_id, func.count(TripExpense.id), func.sum(_tien_lak_sql()))
                         .join(Trip, Trip.id == TripExpense.trip_id)
                         .filter(Trip.doc_date.in_(cac_ngay), TripExpense.supplier_id.isnot(None),
                                 TripExpense.ghi_no.is_(True), TripExpense.paid_by_epl.is_(True))
                         .group_by(Trip.doc_date, TripExpense.supplier_id)):
        ra[d.isoformat()]["tram"][sid] = [int(n), float(x or 0)]
    return ra


def _can_tru_tinh(db, thang, dau, cuoi):
    """Cước phải thu theo khách ghép từ phần tính sẵn của từng NGÀY (chỉ ngày có dữ liệu vừa đổi mới tính lại); thẻ
    cao tốc, trạm dầu Việt Nam và phần đã ghi cấn trừ là bảng nhỏ — luôn đọc MỚI, không đệm (ghi_can_tru dùng bảng này)."""
    sau = cuoi + dt.timedelta(days=1)
    theo_khach = {}

    def o_cua(kid, ten):
        return theo_khach.setdefault(kid or "", {"customer_id": kid, "customer_name": ten or "—",
                                                 "cuoc_lak": 0.0, "the_lak": 0.0, "dau_vn_lak": 0.0,
                                                 "da_ghi_lak": 0.0, "the": [], "tram": []})

    # 1. cước phải thu trong tháng — ghép từ các ngày, theo thứ tự ngày (giữ đúng thứ tự khách xuất hiện như trước)
    phan_ngay = list(_theo_ngay(db, "ct2", _cac_ngay(dau, cuoi), _ct_lo).values())
    for phan in phan_ngay:
        for kid, (ten, lak) in phan["kh"].items():
            o_cua(kid, ten)["cuoc_lak"] += lak
    tram_thang = {}
    for phan in phan_ngay:
        for sid, (n, x) in phan["tram"].items():
            o = tram_thang.setdefault(sid, [0, 0.0]); o[0] += n; o[1] += x

    # 2. thẻ cao tốc do khách cấp — phần EPL đã quẹt trong tháng
    for t in db.query(TollCard).filter(TollCard.kind == "khach").all():
        ds_m = (db.query(TollCardMove).filter(TollCardMove.card_id == t.id, TollCardMove.kind == "chi",
                                              TollCardMove.move_date >= dau, TollCardMove.move_date < sau).all())
        chi = sum(m.amount for m in ds_m)
        if not chi:
            continue
        o = o_cua(t.customer_id, t.customer_name)
        o["the_lak"] += chi          # thẻ nạp bằng Kíp; thẻ tiền khác thì bảng ghi rõ ở dòng chi tiết
        o["the"].append({"card_no": t.card_no, "currency": t.currency, "chi": round(chi, 2)})

    # 3. trạm dầu Việt Nam ghi nợ — cấn trừ vào cước của khách đứng ra với trạm
    for s_ in db.query(Supplier).filter(Supplier.customer_id.isnot(None)).all():
        # nợ ghi tại trạm trong tháng — ghép từ phần tính sẵn của từng ngày (4 năm: quét thẳng mất 1–2 s mỗi trạm)
        so_dong, no = tram_thang.get(s_.id, [0, 0.0])
        if not no:
            continue
        o = o_cua(s_.customer_id, s_.customer_name)
        o["dau_vn_lak"] += no
        o["tram"].append({"name": s_.name, "so_dong": so_dong, "no_lak": round(no)})

    # 4. phần đã GHI thành phiếu thu "cấn trừ" của tháng này (ref CT-YYYYMM) — đọc từ chính sổ thu tiền
    ref = "CT-%s" % dau.strftime("%Y%m")
    da_ghi = _da_ghi_can_tru(db, ref)
    ra = []
    for o in theo_khach.values():
        o["cuoc_lak"] = round(o["cuoc_lak"]); o["the_lak"] = round(o["the_lak"]); o["dau_vn_lak"] = round(o["dau_vn_lak"])
        o["can_tru_lak"] = o["the_lak"] + o["dau_vn_lak"]
        o["da_ghi_lak"] = round(da_ghi.get(o["customer_id"], 0.0))
        o["chua_ghi_lak"] = o["can_tru_lak"] - o["da_ghi_lak"]   # phần chưa ghi thành phiếu thu
        o["con_thu_lak"] = o["cuoc_lak"] - o["can_tru_lak"]
        if o["can_tru_lak"] or o["cuoc_lak"]:
            ra.append(o)
    ra.sort(key=lambda x: -x["can_tru_lak"])
    return {"thang": (thang or dt.date.today().strftime("%Y-%m"))[:7], "ds": ra,
            "tong_cuoc_lak": sum(o["cuoc_lak"] for o in ra),
            "tong_can_tru_lak": sum(o["can_tru_lak"] for o in ra),
            "tong_con_thu_lak": sum(o["con_thu_lak"] for o in ra)}


def _da_ghi_can_tru(db, ref):
    """{customer_id: LAK đã ghi} của các phiếu thu cách thu `offset` mang ref này. Thu ở tờ gộp thì
    chỉ đếm dòng invoice_payments (dòng rải xuống phiếu là con của nó, đếm nữa là gấp đôi)."""
    ra = {}
    for x, hd in (db.query(InvoicePayment, Invoice).join(Invoice, Invoice.id == InvoicePayment.invoice_id)
                  .filter(InvoicePayment.method == "offset", InvoicePayment.ref == ref).all()):
        ra[hd.customer_id] = ra.get(hd.customer_id, 0.0) + (x.amount_lak or 0)
    for x, p in (db.query(TripPayment, Trip).join(Trip, Trip.id == TripPayment.trip_id)
                 .filter(TripPayment.method == "offset", TripPayment.ref == ref,
                         TripPayment.invoice_payment_id.is_(None)).all()):
        ra[p.customer_id] = ra.get(p.customer_id, 0.0) + (x.amount_lak or 0)
    return ra


@router.post("/api/bao-cao/can-tru/ghi")
def ghi_can_tru(data: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """GHI CẤN TRỪ THÁNG cho một khách: những gì khách đã trả hộ (thẻ cao tốc · nợ trạm dầu VN) trong
    tháng mà chưa ghi, biến thành **phiếu thu cách thu "cấn trừ"** trên chính hoá đơn của khách đó.

    Cách ghi không có gì mới: gọi đúng hai hàm ghi thu đang dùng cho nút "Ghi một lần thu" — thu ở tờ
    gộp thì rải về phiếu, thu ở phiếu lẻ thì ghi thẳng — chỉ khác `method = offset`. Nên sổ thu tiền
    vẫn một kiểu dòng, tờ PT vẫn một kiểu tờ, và trạng thái từng phiếu tự đổi như mọi lần thu khác.

    Thứ tự bù: hoá đơn gộp cũ trước, rồi phiếu lẻ cũ trước. "Đã ghi" không cần cột đánh dấu: nó là
    tổng các phiếu thu `offset` mang ref `CT-YYYYMM` của khách — đọc từ chính sổ thu tiền, nên gọi lại
    bao nhiêu lần cũng chỉ ghi phần còn thiếu. Khách trả hộ nhiều hơn cước còn phải thu thì phần dư để
    lại tháng sau — không ghi thu dư.
    """
    from routes.phieu import ghi_thu_phieu
    from routes.hoa_don import ghi_thu_hoa_don, xuat_hd
    if user.role not in ("rev", "admin"):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Chỉ kế toán doanh thu ghi cấn trừ."})
    kh = db.get(Customer, str(data.get("customer_id") or ""))
    if not kh:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có khách hàng này."})
    thang = data.get("thang")
    bang = can_tru(thang, db, user)
    o = next((x for x in bang["ds"] if x["customer_id"] == kh.id), None)
    chua_ghi = float(o["chua_ghi_lak"]) if o else 0.0
    if chua_ghi <= 0:
        raise HTTPException(409, {"ma": "KHONG_CO_GI", "loi": "Tháng này khách %s không còn khoản trả hộ nào chưa ghi." % kh.name})
    _ds, dau, cuoi = _phieu_thang(db, thang)
    ref = "CT-%s" % dau.strftime("%Y%m")
    ngay = _ngay_ct(data.get("pay_date")) or dt.date.today()

    # ---- chỗ để bù: hoá đơn gộp còn nợ (cũ trước), rồi phiếu lẻ đã xuất hoá đơn còn nợ (cũ trước)
    dich = []        # (loại, đối tượng, còn lại LAK)
    for hd in (db.query(Invoice).filter(Invoice.customer_id == kh.id).order_by(Invoice.inv_date, Invoice.inv_no).all()):
        r = xuat_hd(db, hd)
        if r["con_lai_lak"] > 0:
            dich.append(("hd", hd, float(r["con_lai_lak"])))
    ds_p = db.query(Trip).filter(Trip.customer_id == kh.id, Trip.invoiced.is_(True), Trip.invoice_id.is_(None),
                                 Trip.finance_status != "paid").order_by(Trip.doc_date, Trip.doc_no).all()
    thu = da_thu_theo_phieu(db, [p.id for p in ds_p])
    for p in ds_p:
        k = tinh_phieu(p, db.query(TripExpense).filter(TripExpense.trip_id == p.id).all(), thu.get(p.id, 0))
        if k["con_lai_lak"] > 0:
            dich.append(("phieu", p, float(k["con_lai_lak"])))
    if not dich:
        raise HTTPException(409, {"ma": "KHONG_CON_NO", "loi": "Khách %s không còn hoá đơn nào chưa thu để cấn trừ vào." % kh.name})

    # ---- bù dần: mỗi đích một tờ PT cách thu "cấn trừ"; hết chỗ bù thì phần còn lại để tháng sau
    con = chua_ghi
    phieu_thu = []
    ghi_chu = "Cấn trừ tháng %s: khách trả hộ qua thẻ cao tốc / trạm dầu Việt Nam" % dau.strftime("%m/%Y")
    for loai, dt_, con_lai in dich:
        if con <= 0.5:
            break
        tien_lak = round(min(con, con_lai))
        if tien_lak <= 0:
            continue
        if loai == "hd":
            ghi_thu_hoa_don(db, dt_, user, tien_lak, "LAK", 1.0, "offset", ngay=ngay, ref=ref, note=ghi_chu)
            phieu_thu.append({"loai": "hoa_don_gop", "so": dt_.inv_no, "tien_lak": tien_lak})
        else:
            ghi_thu_phieu(db, dt_, user, tien_lak, "LAK", 1.0, "offset", ngay=ngay, ref=ref, note=ghi_chu)
            phieu_thu.append({"loai": "phieu", "so": dt_.doc_no, "tien_lak": tien_lak})
        con -= tien_lak
    db.commit()
    return {"customer_id": kh.id, "customer_name": kh.name, "thang": dau.strftime("%Y-%m"), "ref": ref,
            "ghi_lak": round(chua_ghi - con), "de_lai_lak": round(con), "phieu_thu": phieu_thu}


def _ngay_ct(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "Ngày phải dạng YYYY-MM-DD, nhận '%s'." % v})


@router.get("/api/bao-cao/xe-lien-ket")
def xe_lien_ket(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    # Bảng này CHỈ là biên lợi nhuận: nhận giá 2, thuê lại giá 1, lời 1. Vai không được thấy tiền bán
    # thì chặn hẳn ở máy chủ, không chỉ giấu mục trên thanh điều hướng.
    if not thay_tien_ban(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem bảng lãi xe liên kết." % user.role})
    # Dữ liệu cả năm (24/09): lọc tháng trong SQL; không ghi tháng thì là THÁNG NÀY (trước đây: mọi phiếu liên kết).
    dau, cuoi = _thang(thang)
    ds = (db.query(Trip).filter(Trip.company == "joint", *_trong(dau, cuoi)).order_by(Trip.doc_date.desc()).all())
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    nap = nap_lo(db, ds)
    return [xuat_phieu(db, p, day_du=False, da_thu=thu.get(p.id, 0), nap=nap) for p in ds]


@router.get("/api/bao-cao/tien-tai-xe")
def tien_tai_xe(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """ເງິນຖ້ຽວໂຊເຟີ ແລະ ເງິນເຕີມນ້ຳ — tiền chuyến và tiền nước theo TÀI XẾ, gom từ mục IV.

    Bãi KHÔNG xem (chủ dự án chốt 23/09): phiếu đã giấu tiền mục IV với Bãi, màn này cộng lại đúng số đó.

    Khoản nào là "của tài xế": x_trip (tiền chuyến), x_water (tiền nước), x_vn (tiền đi VN),
    x_phone (điện thoại), x_food (ăn). Trạng thái chi lấy từ mục IV của phiếu.
    """
    if not thay_tien_chi(user.role):
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Bãi không xem tiền chuyến & nước của tài xế."})
    dau, cuoi = _thang(thang)
    # ghép từ phần tính sẵn của từng NGÀY (chỉ ngày có dữ liệu vừa đổi mới tính lại)
    tong = {}
    for o in _theo_ngay(db, "tx", _cac_ngay(dau, cuoi), _tx_lo).values():     # theo thứ tự ngày
        for ten, x in o.items():
            r = tong.setdefault(ten, {"driver": ten, "so_phieu": 0, "khoan": {}, "tong_lak": 0.0, "da_chi": 0, "cho_chi": 0})
            for f in ("so_phieu", "tong_lak", "da_chi", "cho_chi"):
                r[f] += x[f]
            _cong(r["khoan"], x["khoan"])
    ra = []
    for r in tong.values():
        r["khoan"] = {k: round(v) for k, v in r["khoan"].items()}
        r["tong_lak"] = round(r["tong_lak"])
        r["trang_thai"] = "paid" if r["cho_chi"] == 0 else ("partial" if r["da_chi"] else "unpaid")
        ra.append(r)
    return {"tu": dau.isoformat(), "den": cuoi.isoformat(), "rows": sorted(ra, key=lambda x: x["driver"])}


KHOAN_TAI_XE = {"x_trip", "x_water", "x_vn", "x_phone", "x_food"}


def _tx_lo(db, cac_ngay):
    """Phần TIỀN CHUYẾN TÀI XẾ của từng ngày: {tên tài xế: số phiếu · từng khoản · tổng · đã chi / chờ chi mục IV}."""
    loc = (Trip.doc_date.in_(cac_ngay),)
    ds = (db.query(*COT_TINH).filter(*loc, Trip.driver_name.isnot(None), Trip.driver_name != "")
          .order_by(Trip.doc_date, Trip.doc_no).all())
    muc_iv = {t: st for t, st in (db.query(TripSection.trip_id, TripSection.status).join(Trip, Trip.id == TripSection.trip_id)
                                  .filter(*loc, TripSection.section == "travel"))}
    dong = defaultdict(list)
    for d in (db.query(TripExpense.trip_id, TripExpense.item_key, TripExpense.qty, TripExpense.unit_price, TripExpense.currency)
              .join(Trip, Trip.id == TripExpense.trip_id)
              .filter(*loc, TripExpense.section == "travel", TripExpense.paid_by_epl.is_(True),
                      TripExpense.item_key.in_(KHOAN_TAI_XE))):
        dong[d.trip_id].append(d)
    ra = {d.isoformat(): {} for d in cac_ngay}
    for p in ds:
        r = ra[p.doc_date.isoformat()].setdefault(p.driver_name, {"so_phieu": 0, "khoan": {}, "tong_lak": 0.0, "da_chi": 0, "cho_chi": 0})
        r["so_phieu"] += 1
        for d in dong.get(p.id, []):
            v = tien_dong(p, d); r["khoan"][d.item_key] = r["khoan"].get(d.item_key, 0.0) + v; r["tong_lak"] += v
        if muc_iv.get(p.id) == "paid": r["da_chi"] += 1
        else: r["cho_chi"] += 1
    return ra


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

    # "Phiếu lĩnh · tạm ứng đang chờ cấp" đi theo màn Cấp phát, Kho nhiên liệu sang trang kế toán (28/09)
    if vai == "depot":
        return {}

    # "Phụ tùng dưới tồn tối thiểu" đi theo màn Kho phụ tùng sang trang kế toán (28/09) — tồn không còn ở đây

    # Chứng từ bên kế toán chưa đối chiếu
    if admin or vai in ("acct", "expacct", "rev", "cash", "treasury"):
        r["chung-tu"] = db.query(ChungTu).filter(ChungTu.da_day.is_(False)).count()

    return {k: v for k, v in r.items() if v}
