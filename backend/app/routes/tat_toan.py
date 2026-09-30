# -*- coding: utf-8 -*-
"""Tất toán tiền tạm ứng của tài xế — chốt THEO THÁNG.

Tài xế cầm phiếu tạm ứng đi lấy tiền trước mỗi chuyến. Hết tháng phải đối: đã ứng bao nhiêu, đã chi
thật bao nhiêu, rồi bù qua bù lại một lần.

    chênh lệch = đã chi thật − đã ứng
        dương  → công ty CHI BÙ cho tài xế
        âm     → tài xế NỘP LẠI

"Đã ứng" là các phiếu tạm ứng ĐÃ CẤP trong kỳ, chứ không phải số in trên giấy: giấy in rồi mà chưa
ra quỹ lấy tiền thì tài xế chưa cầm đồng nào.

"Đã chi thật" là các dòng chi EPL ứng, không lấy từ kho, thuộc mục IV (đi đường), VI (khác) và các
dòng dầu MUA NGOÀI dọc đường — đúng những khoản tài xế móc tiền túi ứng ra trả.

KHÔNG tính những khoản mà công ty trả thẳng cho nhà cung cấp theo đợt (chipping Lào, chipping Việt,
thẻ đường cao tốc, lốp…). Tiền đó chưa bao giờ đi qua tay tài xế, tính vào là bảng tất toán phình lên
gấp mấy chục lần và người đọc không hiểu vì sao. Nhận biết bằng danh mục nhà cung cấp: khoản mục nào
có nhà cung cấp với kỳ thanh toán "theo đợt" hoặc "nạp thẻ" thì không phải tiền tài xế.

Từ 28/09 (đợt 7c) bản CHỐT tất toán và tờ TT_CHI / TT_THU ở trang kế toán (Tiền vận chuyển → Tất toán tài xế). Bên này
chỉ còn phần TÍNH — số liệu (phiếu, mục IV, phiếu tạm ứng) ở đây — cho trang kế toán hỏi qua đường máy
(routes/lien_thong.py: /api/lien-thong/tat-toan…). Các đường người dùng /api/tat-toan… trả 409 "đã dời". Bảng
driver_settlements bên này đứng yên (đã dời sang, tools/doi_tat_toan.py bên EPL_KETOAN).
"""
import datetime as dt

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, not_, or_

from models import Driver, Trip, TripExpense, Voucher
from services.bao_mat import nguoi_hien_tai
from services.tinh_toan import CACH_TRA, CACH_TRA_MAC_DINH, la_tien_mat_tai_xe, ty_gia
from services import dem_bao_cao as DEM

router = APIRouter()
DA_DOI = {"ma": "DA_DOI_SANG_KE_TOAN", "loi": "Tất toán tài xế nay làm ở trang kế toán (Tiền vận chuyển → Tất toán tài xế)."}


def _ky_hop_le(ky):
    try:
        dt.date.fromisoformat(ky + "-01")
    except (ValueError, TypeError):
        raise HTTPException(422, {"ma": "KY_SAI", "loi": "Kỳ phải dạng YYYY-MM, nhận '%s'." % ky})
    return ky


def _khoang(ky):
    dau = dt.date.fromisoformat(ky + "-01")
    cuoi = dt.date(dau.year + (dau.month == 12), dau.month % 12 + 1, 1) - dt.timedelta(days=1)
    return dau, cuoi


def _phieu_cua(db, driver_id, ky):
    """Phiếu xuất xe của tài xế trong kỳ, tính theo NGÀY XE ĐI (không có thì lấy ngày lập)."""
    dau, cuoi = _khoang(ky)
    # lọc kỳ NGAY TRONG SQL — trước đây nạp mọi phiếu từ trước tới nay của người đó (~700 phiếu / năm) rồi mới lọc
    return db.query(Trip).filter(Trip.driver_id == driver_id, *_trong_ky(dau, cuoi)).all()


def _trong_ky(dau, cuoi):
    """Phiếu XE NHÀ trong kỳ. Xe thuê không tất toán với tài xế: tạm ứng xe thuê là công nợ chủ xe, đã trừ vào tiền trả
    chủ xe (chủ dự án 29/09) — tất toán thêm là một khoản hai lần."""
    ngay = func.coalesce(Trip.out_date, Trip.doc_date)
    return (ngay >= dau, ngay <= cuoi, XE_NHA)


XE_NHA = or_(Trip.company.is_(None), Trip.company != "joint")


def _la_tien_mat_sql():
    """la_tien_mat_tai_xe (services/tinh_toan) viết bằng SQL — CÙNG MỘT LUẬT với phiếu tạm ứng, kể cả cách trả từng dòng
    (Excel anh Khampla, 29/09). HAI BẢN PHẢI ĐI CÙNG NHAU: đổi luật ở bên kia thì đổi cả ở đây (kiem/thu_tat_toan_lo.py so
    hai bản). Trước 29/09 bản này bỏ thêm mọi khoản có nhà cung cấp trả theo đợt THEO TÊN KHOẢN — phí cao tốc trả tiền
    mặt và dầu mua dọc đường cũng rơi mất khỏi "đã chi thật", 11 phiếu trên máy thật lệch với phiếu tạm ứng."""
    khac = sorted(k for k, v in CACH_TRA_MAC_DINH.items() if v != "tien_mat")
    tien_mat = or_(TripExpense.pay_channel == "tien_mat",
                   and_(or_(TripExpense.pay_channel.is_(None), not_(TripExpense.pay_channel.in_(CACH_TRA))),
                        or_(TripExpense.item_key.is_(None), not_(TripExpense.item_key.in_(khac)))))
    return and_(TripExpense.paid_by_epl.is_(True), TripExpense.source.is_distinct_from("kho"),
                TripExpense.section.in_(("fuel", "travel", "other")), TripExpense.ghi_no.isnot(True),
                or_(TripExpense.toll_card_id.is_(None), TripExpense.toll_card_id == ""),
                or_(TripExpense.section == "fuel", tien_mat))


def tinh_ky(db, tai_xe, ky):
    """Tính một dòng tất toán. Không ghi gì vào DB — màn hình xem trước bằng chính hàm này."""
    ds = _phieu_cua(db, tai_xe.id, ky)
    ma_phieu = [p.id for p in ds]
    ung = 0.0
    if ma_phieu:
        for v in db.query(Voucher).filter(Voucher.trip_id.in_(ma_phieu), Voucher.kind == "advance",
                                          Voucher.status == "da_cap").all():
            ung += v.amount_lak or 0
    chi = 0.0
    chi_tiet = []
    for p in ds:
        tien_p = 0.0
        for e in db.query(TripExpense).filter(TripExpense.trip_id == p.id).all():
            if not la_tien_mat_tai_xe(e, p.company):           # cùng luật với phiếu tạm ứng (services/tinh_toan), kể cả cách trả
                continue
            tien_p += (e.qty or 0) * (e.unit_price or 0) * ty_gia(p, e.currency)
        chi += tien_p
        chi_tiet.append({"trip_id": p.id, "doc_no": p.doc_no, "truck_no": p.truck_no,
                         "out_date": (p.out_date or p.doc_date).isoformat() if (p.out_date or p.doc_date) else None,
                         "origin": p.origin, "destination": p.destination, "chi_lak": round(tien_p, 2)})
    # đã tất toán hay chưa: trang kế toán giữ bản chốt từ đợt 7c, tự ghép vào
    return {"driver_id": tai_xe.id, "driver_code": tai_xe.driver_code, "driver_name": tai_xe.name, "period": ky,
            "so_phieu": len(ds), "tong_ung_lak": round(ung, 2), "tong_chi_lak": round(chi, 2),
            "chenh_lech_lak": round(chi - ung, 2), "phieu": chi_tiet}


def tinh_ky_lo(db, cac_tai_xe, ky):
    """tinh_ky cho CẢ danh sách tài xế một lần (24/09, dữ liệu cả năm): năm câu SQL thay cho (1 + số phiếu) câu MỖI
    tài xế — 500 tài xế là ~30.000 câu. Cùng luật, cùng cách làm tròn; kiem/thu_tat_toan_lo.py so với tinh_ky."""
    from routes.nha_cung_cap import _tien_lak_sql
    dau, cuoi = _khoang(ky)
    ids = [t.id for t in cac_tai_xe]
    phieu = defaultdict(list)
    for p in (db.query(Trip.id, Trip.driver_id, Trip.doc_no, Trip.truck_no, Trip.out_date, Trip.doc_date, Trip.origin,
                       Trip.destination).filter(Trip.driver_id.in_(ids or [""]), *_trong_ky(dau, cuoi))
              .order_by(func.coalesce(Trip.out_date, Trip.doc_date), Trip.doc_no)):
        phieu[p.driver_id].append(p)
    trong = (Trip.driver_id.in_(ids or [""]), *_trong_ky(dau, cuoi))
    chi = {tid: float(v or 0) for tid, v in (db.query(TripExpense.trip_id, func.sum(_tien_lak_sql()))
                                             .join(Trip, Trip.id == TripExpense.trip_id)
                                             .filter(*trong, _la_tien_mat_sql()).group_by(TripExpense.trip_id))}
    ung = {did: float(v or 0) for did, v in (db.query(Trip.driver_id, func.sum(Voucher.amount_lak))
                                             .join(Trip, Trip.id == Voucher.trip_id)
                                             .filter(*trong, Voucher.kind == "advance", Voucher.status == "da_cap")
                                             .group_by(Trip.driver_id))}
    ra = []
    for t in cac_tai_xe:
        ds, u = phieu.get(t.id, []), ung.get(t.id, 0.0)
        c = sum(chi.get(p.id, 0.0) for p in ds)
        ra.append({"driver_id": t.id, "driver_code": t.driver_code, "driver_name": t.name, "period": ky,
                   "so_phieu": len(ds), "tong_ung_lak": round(u, 2), "tong_chi_lak": round(c, 2),
                   "chenh_lech_lak": round(c - u, 2),
                   "phieu": [{"trip_id": p.id, "doc_no": p.doc_no, "truck_no": p.truck_no,
                              "out_date": (p.out_date or p.doc_date).isoformat() if (p.out_date or p.doc_date) else None,
                              "origin": p.origin, "destination": p.destination, "chi_lak": round(chi.get(p.id, 0.0), 2)}
                             for p in ds]})
    return ra


def _tt_lo(db, cac_ngay):
    """Phần TẤT TOÁN của từng ngày lập phiếu: {ngày: {driver_id: {"YYYY-MM" kỳ xe đi: [số phiếu, đã chi LAK, đã ứng LAK]}}}.
    Kỳ tính theo NGÀY XE ĐI (không có thì ngày lập) — cùng luật với tinh_ky_lo."""
    from routes.nha_cung_cap import _tien_lak_sql
    loc = (Trip.doc_date.in_(cac_ngay), Trip.driver_id.isnot(None), XE_NHA)
    chi = {tid: float(v or 0) for tid, v in (db.query(TripExpense.trip_id, func.sum(_tien_lak_sql()))
                                             .join(Trip, Trip.id == TripExpense.trip_id)
                                             .filter(*loc, _la_tien_mat_sql()).group_by(TripExpense.trip_id))}
    ung = {tid: float(v or 0) for tid, v in (db.query(Voucher.trip_id, func.sum(Voucher.amount_lak))
                                             .join(Trip, Trip.id == Voucher.trip_id)
                                             .filter(*loc, Voucher.kind == "advance", Voucher.status == "da_cap")
                                             .group_by(Voucher.trip_id))}
    ra = {d.isoformat(): {} for d in cac_ngay}
    for p in db.query(Trip.id, Trip.driver_id, Trip.doc_date, Trip.out_date).filter(*loc):
        ky = (p.out_date or p.doc_date).strftime("%Y-%m")
        o = ra[p.doc_date.isoformat()].setdefault(p.driver_id, {}).setdefault(ky, [0, 0.0, 0.0])
        o[0] += 1; o[1] += chi.get(p.id, 0.0); o[2] += ung.get(p.id, 0.0)
    return ra


def _bang_ky_ngay(db, cac_tai_xe, ky):
    """Như tinh_ky_lo (không kèm danh sách phiếu) nhưng ghép từ các NGÀY: xe đi trong kỳ M thì phiếu lập trong M hoặc
    tháng trước (xe đi sau ngày lập) — nên ghép phần của các ngày từ đầu tháng trước tới cuối tháng M."""
    dau, cuoi = _khoang(ky)
    truoc = dt.date(dau.year - (dau.month == 1), (dau.month - 2) % 12 + 1, 1)
    ngay = [truoc + dt.timedelta(days=i) for i in range((cuoi - truoc).days + 1)]
    viec = [(("tt4", d.isoformat()), [d.isoformat(), "ncc"], None) for d in ngay]    # tt4: chỉ xe nhà (29/09)
    tong = {}
    for phan in DEM.lay_nhieu(db, viec, tinh_lo=lambda thieu: (lambda kq: [kq[ngay[i].isoformat()] for i in thieu])(
            _tt_lo(db, [ngay[i] for i in thieu]))):
        for did, theo_ky in phan.items():
            x = theo_ky.get(ky)
            if x:
                o = tong.setdefault(did, [0, 0.0, 0.0])
                o[0] += x[0]; o[1] += x[1]; o[2] += x[2]
    ra = []
    for t in cac_tai_xe:
        n, c, u = tong.get(t.id, [0, 0.0, 0.0])
        ra.append({"driver_id": t.id, "driver_code": t.driver_code, "driver_name": t.name, "period": ky,
                   "so_phieu": n, "tong_ung_lak": round(u, 2), "tong_chi_lak": round(c, 2), "chenh_lech_lak": round(c - u, 2)})
    return ra


def bang_thang(db, ky):
    """Bảng tất toán cả tháng cho trang kế toán (đường máy): MỌI tài xế đang làm, không kèm danh sách phiếu — bên đó ghép
    bản chốt của nó rồi mới lọc dòng trống (tài xế không phiếu, không ứng, chưa chốt). Ghép từ phần tính sẵn theo ngày."""
    return _bang_ky_ngay(db, db.query(Driver).filter(Driver.active.is_(True)).order_by(Driver.driver_code, Driver.name).all(), ky)


def mot(db, driver_id, ky):
    """Một tài xế một kỳ, kèm danh sách phiếu — khung chi tiết và lúc chốt (trang kế toán)."""
    t = db.get(Driver, driver_id)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    return tinh_ky_lo(db, [t], ky)[0]          # nạp theo lô, không mỗi phiếu một câu


# ---------------------------------------------------------------- đường người dùng cũ: đã dời (đợt 7c)
@router.get("/api/tat-toan")
def bang_ky(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.get("/api/tat-toan/{driver_id}")
def mot_tai_xe(driver_id: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.post("/api/tat-toan")
def chot_ky(user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)


@router.delete("/api/tat-toan/{driver_id}")
def bo_chot(driver_id: str, user=Depends(nguoi_hien_tai)):
    raise HTTPException(409, DA_DOI)
