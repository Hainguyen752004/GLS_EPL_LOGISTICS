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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (ChungTu, Customer, Invoice, InvoicePayment, Part, Route, RouteStop, Supplier, TollCard,
                    TollCardMove, Trip, TripEvent, TripExpense, TripPayment, TripSection, Voucher)
from fastapi import Body
from routes.phieu import da_thu_theo_phieu, xuat_phieu
from routes.theo_doi import NGAY_COI_LA_LAU
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import QUYEN, thay_tien_ban, viec_dang_cho
from services.tinh_toan import tien_dong, tinh_phieu, ty_gia

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


@router.get("/api/bao-cao/tong-quan")
def tong_quan(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    ds, dau, cuoi = _phieu_thang(db, thang)
    dong = defaultdict(list)
    for d in db.query(TripExpense).filter(TripExpense.trip_id.in_([p.id for p in ds] or [""])).all():
        dong[d.trip_id].append(d)
    doanh_thu = chi_lak = tan = 0.0
    chua_thu_lak, chua_thu_so = 0.0, 0
    theo_tien, chua_thu_tien = defaultdict(float), defaultdict(float)
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    dem = {"dispatched": 0, "transit": 0, "arrived": 0, "invoiced": 0, "paid": 0}
    theo_muc = {"fuel": 0.0, "travel": 0.0, "repair": 0.0, "other": 0.0}
    for p in ds:
        c = tinh_phieu(p, dong[p.id], thu.get(p.id, 0))
        doanh_thu += c["doanh_thu_lak"]
        theo_tien[c["ccy"]] += c["doanh_thu"]
        # Chi của EPL: xe nhà là tổng chi; xe liên kết là tiền thuê trừ phần giữ lại (đã tính sẵn ra LAK)
        chi_lak += (c["tien_thue_lak"] - c["giu_lai"] * ty_gia(p, c["hire_ccy"])) if c["lien_ket"] else c["tong_chi_lak"]
        for m in theo_muc: theo_muc[m] += c["chi"][m]
        if p.weight_dest: tan += p.weight_dest
        # Chưa thu = phần hoá đơn CHƯA VỀ TIỀN, không phải cả doanh thu của phiếu chưa đánh dấu "đã thu".
        # Khách trả một phần thì chỉ còn thiếu phần kia, con số phải nói đúng như vậy.
        if p.transport_status == "arrived" and c["con_lai_lak"] > 0:
            chua_thu_lak += c["con_lai_lak"]; chua_thu_so += 1
            chua_thu_tien[c["ccy"]] += c["con_lai"]
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
          "doanh_thu_lak": round(doanh_thu), "doanh_thu_tien": _gon(theo_tien),
          "chi_lak": round(chi_lak), "tan_giao": round(tan, 2),
          "chua_thu_lak": round(chua_thu_lak), "chua_thu_tien": _gon(chua_thu_tien), "chua_thu_so": chua_thu_so,
          "dem": dem, "chi_theo_muc": {k: round(v) for k, v in theo_muc.items()}, "chu_y": chu_y[:12]}
    # Vai không được thấy tiền bán thì máy chủ BỎ HẲN các khoá đó, không chỉ giấu ở giao diện.
    if not thay_tien_ban(user.role):
        for k in ("doanh_thu_lak", "doanh_thu_tien", "chua_thu_lak", "chua_thu_tien", "chua_thu_so"):
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
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    r = {"doanh_thu_lak": 0.0, "chi_lak": 0.0, "tan_giao": 0.0, "chua_thu_lak": 0.0}
    for p in ds:
        c = tinh_phieu(p, dong[p.id], thu.get(p.id, 0))
        r["doanh_thu_lak"] += c["doanh_thu_lak"]
        r["chi_lak"] += (c["tien_thue_lak"] - c["giu_lai"] * ty_gia(p, c["hire_ccy"])) if c["lien_ket"] else c["tong_chi_lak"]
        if p.weight_dest: r["tan_giao"] += p.weight_dest
        if p.transport_status == "arrived" and c["con_lai_lak"] > 0:
            r["chua_thu_lak"] += c["con_lai_lak"]
    return {"doanh_thu_lak": round(r["doanh_thu_lak"]), "chi_lak": round(r["chi_lak"]),
            "tan_giao": round(r["tan_giao"], 2), "chua_thu_lak": round(r["chua_thu_lak"])}


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
    sau_thang = {"nhan": [], "doanh_thu_lak": [], "chi_lak": [], "tan_giao": [], "chua_thu_lak": []}
    thang_truoc = None
    for i in range(5, -1, -1):
        yy, mm = _lui_thang(y, m, i)
        d1 = dt.date(yy, mm, 1)
        d2 = dt.date(yy + (mm == 12), (mm % 12) + 1, 1) - dt.timedelta(days=1)
        g = _gom_thang(db, d1, d2)
        sau_thang["nhan"].append("%02d/%02d" % (mm, yy % 100))
        for k in ("doanh_thu_lak", "chi_lak", "tan_giao", "chua_thu_lak"):
            sau_thang[k].append(g[k])
        if i == 1:
            thang_truoc = g

    # ---- theo ngày · hao hụt · hiệu suất xe · vận hành
    theo_ngay, hao_hut, xe = defaultdict(lambda: {"doanh_thu_lak": 0.0, "chi_lak": 0.0}), [], {}
    ngay_di_ds, hao_ds, dung_han = [], [], 0
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    for p in ds:
        c = tinh_phieu(p, dong[p.id], thu.get(p.id, 0))
        if p.doc_date:
            o = theo_ngay[p.doc_date.isoformat()]
            o["doanh_thu_lak"] += c["doanh_thu_lak"]
            o["chi_lak"] += c["tong_chi_lak"]
        if p.weight_origin and p.weight_dest is not None:
            hao_hut.append({"doc_no": p.doc_no, "so_xe": p.truck_no, "can_dau": p.weight_origin, "can_cuoi": p.weight_dest})
            if c["hao_hut_pct"] is not None: hao_ds.append(c["hao_hut_pct"])
        if p.truck_no:
            x = xe.setdefault(p.truck_no, {"so_xe": p.truck_no, "so_chuyen": 0, "tan": 0.0, "km": 0.0, "doanh_thu_lak": 0.0})
            x["so_chuyen"] += 1
            x["tan"] += p.weight_dest or p.weight_origin or 0
            if p.odo_back is not None and p.odo_out is not None and p.odo_back >= p.odo_out:
                x["km"] += p.odo_back - p.odo_out
            x["doanh_thu_lak"] += c["doanh_thu_lak"]
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
    # KT Doanh thu KHÔNG phụ trách mục nào — việc của họ nằm ở MỨC PHIẾU: phiếu đã khoá chưa xuất
    # hoá đơn, và hoá đơn chưa thu đủ tiền. Trước đây ô "Việc của tôi" của họ luôn là 0, đọc như thể
    # họ không có việc gì (nợ kỹ thuật 3.4).
    if user.role == "rev":
        cho_hd = [p for p in ds if p.locked and not p.invoiced]
        cho_thu = [p for p in ds if p.invoiced and p.finance_status != "paid"]
        viec_toi = len(cho_hd) + len(cho_thu)
        viec_phieu = (cho_hd or cho_thu or [None])[0]
        viec_phieu = viec_phieu.id if viec_phieu is not None else None
    xem_nhanh = {
        "dang_chay": len([p for p in ds if p.transport_status in ("dispatched", "transit")]),
        "di_lau": len([p for p in ds if p.transport_status != "arrived" and (p.out_date or p.doc_date)
                       and (hom_nay - (p.out_date or p.doc_date)).days > NGAY_COI_LA_LAU]),
        "su_co": len([p for p in ds if p.id in su_co]),
        "cho_hoa_don": len([p for p in ds if p.transport_status == "arrived" and not p.invoiced]),
        "viec_toi": viec_toi, "viec_phieu": viec_phieu,
        "phieu_linh_cho": linh_cho,
        "chua_thu_lak": round(sum(tinh_phieu(p, dong[p.id], thu.get(p.id, 0))["con_lai_lak"] for p in ds
                                  if p.transport_status == "arrived")),
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
        x["tan"] = round(x["tan"], 2); x["km"] = round(x["km"]); x["doanh_thu_lak"] = round(x["doanh_thu_lak"])
    # Vai không được thấy tiền bán: bỏ hẳn mọi khoá doanh thu, kể cả trong dãy sáu tháng và theo xe.
    if not thay_tien_ban(user.role):
        xem_nhanh.pop("chua_thu_lak", None)
        sau_thang.pop("doanh_thu_lak", None); sau_thang.pop("chua_thu_lak", None)
        if thang_truoc:
            thang_truoc.pop("doanh_thu_lak", None); thang_truoc.pop("chua_thu_lak", None)
        for x in xe.values(): x.pop("doanh_thu_lak", None)
        theo_ngay_ra = [{"ngay": k, "chi_lak": round(v["chi_lak"])} for k, v in sorted(theo_ngay.items())]
    else:
        theo_ngay_ra = [{"ngay": k, "doanh_thu_lak": round(v["doanh_thu_lak"]), "chi_lak": round(v["chi_lak"])}
                        for k, v in sorted(theo_ngay.items())]
    return {
        "thang": dau.strftime("%Y-%m"), "thang_truoc": thang_truoc, "sau_thang": sau_thang,
        "theo_ngay": theo_ngay_ra,
        "hao_hut": hao_hut, "xe": sorted(xe.values(), key=lambda x: -(x.get("doanh_thu_lak") or x["tan"])),
        "van_hanh": van_hanh, "xem_nhanh": xem_nhanh, "dong_thoi_gian": dong_thoi_gian,
    }


@router.get("/api/bao-cao/theo-doi")
def theo_doi(thang: str = None, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bảng "ລາຍງານ ຕິດຕາມໃບຂົນສົ່ງສິນຄ້າ" — một dòng một phiếu, đủ 29 cột như Excel.

    Vai không được thấy tiền bán thì các cột cước, doanh thu, lãi **không có trong gói trả về** —
    không phải chỉ ẩn cột ở giao diện."""
    ds, dau, cuoi = _phieu_thang(db, thang) if thang else (db.query(Trip).order_by(Trip.doc_date, Trip.doc_no).all(), None, None)
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    return [xuat_phieu(db, p, day_du=False, da_thu=thu.get(p.id, 0), vai=user.role) for p in ds]


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
    ds, dau, cuoi = _phieu_thang(db, thang)
    sau = cuoi + dt.timedelta(days=1)
    theo_khach = {}

    def o_cua(kid, ten):
        return theo_khach.setdefault(kid or "", {"customer_id": kid, "customer_name": ten or "—",
                                                 "cuoc_lak": 0.0, "the_lak": 0.0, "dau_vn_lak": 0.0,
                                                 "da_ghi_lak": 0.0, "the": [], "tram": []})

    # 1. cước phải thu trong tháng (theo phiếu đã xuất hoá đơn hoặc đã khoá — tức là đã chốt tiền)
    dong = defaultdict(list)
    for d in db.query(TripExpense).filter(TripExpense.trip_id.in_([p.id for p in ds] or [""])).all():
        dong[d.trip_id].append(d)
    for p in ds:
        if not p.customer_id:
            continue
        k = tinh_phieu(p, dong.get(p.id, []))
        o_cua(p.customer_id, p.customer_name)["cuoc_lak"] += k["doanh_thu_lak"]

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
        no = 0.0; so_dong = 0
        for d, p in (db.query(TripExpense, Trip).join(Trip, Trip.id == TripExpense.trip_id)
                     .filter(TripExpense.supplier_id == s_.id, TripExpense.ghi_no.is_(True),
                             TripExpense.paid_by_epl.is_(True)).all()):
            if not p.doc_date or not (dau <= p.doc_date <= cuoi):
                continue
            no += tien_dong(p, d); so_dong += 1
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
    ds = db.query(Trip).filter(Trip.company == "joint").order_by(Trip.doc_date.desc()).all()
    if thang:
        dau, cuoi = _thang(thang)
        ds = [p for p in ds if p.doc_date and dau <= p.doc_date <= cuoi]
    thu = da_thu_theo_phieu(db, [p.id for p in ds])
    return [xuat_phieu(db, p, day_du=False, da_thu=thu.get(p.id, 0)) for p in ds]


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
