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

Tất toán xong là khoá kỳ: phiếu trong kỳ không sửa ngược được nữa, vì số đã chốt với tài xế rồi.
"""
import datetime as dt

from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, func, not_, or_
from sqlalchemy.orm import Session

from database import get_db
from models import Driver, DriverSettlement, Supplier, Trip, TripExpense, Voucher
from services.bao_mat import can_vai, nguoi_hien_tai
from services.tinh_toan import la_tien_mat_tai_xe, ty_gia
from services import chung_tu as CT
from services import dem_bao_cao as DEM

router = APIRouter()
CHOT = can_vai("expacct", "cash", "treasury")


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
    ngay = func.coalesce(Trip.out_date, Trip.doc_date)
    return (ngay >= dau, ngay <= cuoi)


def _la_tien_mat_sql(bo_qua):
    """la_tien_mat_tai_xe (services/tinh_toan) viết bằng SQL, cộng thêm luật bỏ khoản trả nhà cung cấp theo đợt.
    HAI BẢN PHẢI ĐI CÙNG NHAU: đổi luật ở bên kia thì đổi cả ở đây (kiem/thu_tat_toan_lo.py so hai bản)."""
    dk = [TripExpense.paid_by_epl.is_(True), TripExpense.source.is_distinct_from("kho"),
          TripExpense.section.in_(("fuel", "travel", "other")), TripExpense.ghi_no.isnot(True),
          or_(TripExpense.toll_card_id.is_(None), TripExpense.toll_card_id == "")]
    if bo_qua:
        dk.append(or_(TripExpense.item_key.is_(None), not_(TripExpense.item_key.in_(sorted(bo_qua)))))
    return and_(*dk)


# Kỳ thanh toán nào KHÔNG phải tiền mặt tài xế đưa ngay tại chỗ.
KY_TRA_SAU = ("t_monthly", "t_prepaid")


def _khoan_khong_phai_tien_tai_xe(db):
    """Khoản mục do công ty trả thẳng cho nhà cung cấp, không đi qua tay tài xế."""
    return {s.item_key for s in db.query(Supplier).filter(Supplier.payment_term.in_(KY_TRA_SAU)).all() if s.item_key}


def tinh_ky(db, tai_xe, ky):
    """Tính một dòng tất toán. Không ghi gì vào DB — màn hình xem trước bằng chính hàm này."""
    bo_qua = _khoan_khong_phai_tien_tai_xe(db)
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
            if not la_tien_mat_tai_xe(e):           # cùng luật với phiếu tạm ứng (services/tinh_toan)
                continue
            if e.item_key in bo_qua:                 # công ty trả nhà cung cấp theo đợt, không phải tiền tài xế
                continue
            tien_p += (e.qty or 0) * (e.unit_price or 0) * ty_gia(p, e.currency)
        chi += tien_p
        chi_tiet.append({"trip_id": p.id, "doc_no": p.doc_no, "truck_no": p.truck_no,
                         "out_date": (p.out_date or p.doc_date).isoformat() if (p.out_date or p.doc_date) else None,
                         "origin": p.origin, "destination": p.destination, "chi_lak": round(tien_p, 2)})
    da_chot = db.query(DriverSettlement).filter(DriverSettlement.driver_id == tai_xe.id,
                                                DriverSettlement.period == ky).first()
    return {"driver_id": tai_xe.id, "driver_code": tai_xe.driver_code, "driver_name": tai_xe.name, "period": ky,
            "so_phieu": len(ds), "tong_ung_lak": round(ung, 2), "tong_chi_lak": round(chi, 2),
            "chenh_lech_lak": round(chi - ung, 2), "phieu": chi_tiet,
            "da_tat_toan": bool(da_chot),
            "tat_toan": ({"settled_by": da_chot.settled_by,
                          "settled_at": da_chot.settled_at.isoformat() if da_chot.settled_at else None,
                          "chenh_lech_lak": da_chot.chenh_lech_lak, "note": da_chot.note} if da_chot else None)}


def tinh_ky_lo(db, cac_tai_xe, ky):
    """tinh_ky cho CẢ danh sách tài xế một lần (24/09, dữ liệu cả năm): năm câu SQL thay cho (1 + số phiếu) câu MỖI
    tài xế — 500 tài xế là ~30.000 câu. Cùng luật, cùng cách làm tròn; kiem/thu_tat_toan_lo.py so với tinh_ky."""
    from routes.nha_cung_cap import _tien_lak_sql
    dau, cuoi = _khoang(ky)
    bo_qua = _khoan_khong_phai_tien_tai_xe(db)
    ids = [t.id for t in cac_tai_xe]
    phieu = defaultdict(list)
    for p in (db.query(Trip.id, Trip.driver_id, Trip.doc_no, Trip.truck_no, Trip.out_date, Trip.doc_date, Trip.origin,
                       Trip.destination).filter(Trip.driver_id.in_(ids or [""]), *_trong_ky(dau, cuoi))
              .order_by(func.coalesce(Trip.out_date, Trip.doc_date), Trip.doc_no)):
        phieu[p.driver_id].append(p)
    trong = (Trip.driver_id.in_(ids or [""]), *_trong_ky(dau, cuoi))
    chi = {tid: float(v or 0) for tid, v in (db.query(TripExpense.trip_id, func.sum(_tien_lak_sql()))
                                             .join(Trip, Trip.id == TripExpense.trip_id)
                                             .filter(*trong, _la_tien_mat_sql(bo_qua)).group_by(TripExpense.trip_id))}
    ung = {did: float(v or 0) for did, v in (db.query(Trip.driver_id, func.sum(Voucher.amount_lak))
                                             .join(Trip, Trip.id == Voucher.trip_id)
                                             .filter(*trong, Voucher.kind == "advance", Voucher.status == "da_cap")
                                             .group_by(Trip.driver_id))}
    chot = {c.driver_id: c for c in db.query(DriverSettlement).filter(DriverSettlement.driver_id.in_(ids or [""]),
                                                                      DriverSettlement.period == ky)}
    ra = []
    for t in cac_tai_xe:
        ds, u, da_chot = phieu.get(t.id, []), ung.get(t.id, 0.0), chot.get(t.id)
        c = sum(chi.get(p.id, 0.0) for p in ds)
        ra.append({"driver_id": t.id, "driver_code": t.driver_code, "driver_name": t.name, "period": ky,
                   "so_phieu": len(ds), "tong_ung_lak": round(u, 2), "tong_chi_lak": round(c, 2),
                   "chenh_lech_lak": round(c - u, 2),
                   "phieu": [{"trip_id": p.id, "doc_no": p.doc_no, "truck_no": p.truck_no,
                              "out_date": (p.out_date or p.doc_date).isoformat() if (p.out_date or p.doc_date) else None,
                              "origin": p.origin, "destination": p.destination, "chi_lak": round(chi.get(p.id, 0.0), 2)}
                             for p in ds],
                   "da_tat_toan": bool(da_chot),
                   "tat_toan": ({"settled_by": da_chot.settled_by,
                                 "settled_at": da_chot.settled_at.isoformat() if da_chot.settled_at else None,
                                 "chenh_lech_lak": da_chot.chenh_lech_lak, "note": da_chot.note} if da_chot else None)})
    return ra


@router.get("/api/tat-toan")
def bang_ky(ky: str = "", chi_tiet: int = 1, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bảng tất toán cả tháng: mỗi tài xế một dòng. Tài xế chỉ thấy dòng của chính mình.
    `chi_tiet=0`: không kèm danh sách phiếu của từng người (500 tài xế × cả tháng phiếu là vài MB) — màn hình lấy
    chi tiết của người đang chọn qua /api/tat-toan/{driver_id}."""
    ky = _ky_hop_le(ky or dt.date.today().strftime("%Y-%m"))
    q = db.query(Driver).filter(Driver.active.is_(True))
    if user.role == "driver":
        q = q.filter(Driver.id == (user.driver_id or "~"))
    if user.role == "driver":
        ds = tinh_ky_lo(db, q.order_by(Driver.driver_code, Driver.name).all(), ky)
    else:
        # đệm theo kỳ: kỳ tính theo NGÀY XE ĐI nên phiếu lập cuối tháng trước cũng có thể thuộc kỳ này → phụ thuộc cả
        # tháng trước lẫn tháng này, cộng các khoá riêng: chốt tất toán ('tt'), danh mục tài xế ('tx'), NCC ('ncc')
        dau, _ = _khoang(ky)
        truoc = (dau - dt.timedelta(days=1)).strftime("%Y-%m")
        ds = DEM.lay(db, ("tat-toan", ky), [truoc, ky, "tt", "tx", "ncc"],
                     lambda: tinh_ky_lo(db, q.order_by(Driver.driver_code, Driver.name).all(), ky), theo_ngay=False)
    ds = [dict(d) for d in ds]                  # bản chép — bản đệm dùng chung, không sửa tại chỗ
    if not chi_tiet:
        for d in ds:
            d.pop("phieu", None)
    return {"ky": ky, "dong": [d for d in ds if d["so_phieu"] or d["tong_ung_lak"] or d["da_tat_toan"]],
            "tong_ung_lak": round(sum(d["tong_ung_lak"] for d in ds), 2),
            "tong_chi_lak": round(sum(d["tong_chi_lak"] for d in ds), 2)}


@router.get("/api/tat-toan/{driver_id}")
def mot_tai_xe(driver_id: str, ky: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    t = db.get(Driver, driver_id)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    if user.role == "driver" and user.driver_id != driver_id:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Tài xế chỉ xem tất toán của mình."})
    return tinh_ky_lo(db, [t], _ky_hop_le(ky or dt.date.today().strftime("%Y-%m")))[0]   # nạp theo lô, không mỗi phiếu một câu


@router.post("/api/tat-toan")
def chot_ky(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(CHOT)):
    """Chốt một tài xế trong một tháng. Chốt rồi thì không chốt lại, muốn sửa phải bỏ chốt."""
    t = db.get(Driver, d.get("driver_id") or "")
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    ky = _ky_hop_le(d.get("period") or "")
    if db.query(DriverSettlement).filter(DriverSettlement.driver_id == t.id, DriverSettlement.period == ky).first():
        raise HTTPException(409, {"ma": "DA_TAT_TOAN", "loi": "Kỳ %s của tài xế này đã tất toán rồi." % ky})
    k = tinh_ky(db, t, ky)
    if not k["so_phieu"]:
        raise HTTPException(422, {"ma": "KY_TRONG", "loi": "Kỳ %s tài xế không có phiếu nào." % ky})
    x = DriverSettlement(driver_id=t.id, driver_name=t.name, period=ky, so_phieu=k["so_phieu"],
                         tong_ung_lak=k["tong_ung_lak"], tong_chi_lak=k["tong_chi_lak"],
                         chenh_lech_lak=k["chenh_lech_lak"], settled_by=user.full_name,
                         settled_at=dt.datetime.utcnow(), note=d.get("note"))
    db.add(x); db.flush()
    ch = k["chenh_lech_lak"]
    if abs(ch) >= 1:
        CT.ghi(db, "TT_CHI" if ch > 0 else "TT_THU", nguon_bang="driver_settlements", nguon_id=x.id, phuong_thuc="cash",
               ngay=dt.date.today(), doi_tuong_loai="tai_xe", doi_tuong_ten=t.name, tien=abs(ch), tien_te="LAK",
               section="travel", by_user=user.full_name,
               mo_ta="Tất toán kỳ %s · %s" % (ky, "công ty chi bù" if ch > 0 else "tài xế nộp lại"),
               payload={"period": ky, "tong_ung_lak": k["tong_ung_lak"], "tong_chi_lak": k["tong_chi_lak"], "driver_id": t.id})
    db.commit()
    return tinh_ky(db, t, ky)


@router.delete("/api/tat-toan/{driver_id}")
def bo_chot(driver_id: str, ky: str = "", db: Session = Depends(get_db), user=Depends(can_vai("expacct"))):
    """Bỏ chốt để sửa lại. Cố ý hẹp quyền: chỉ kế toán và quản trị."""
    x = (db.query(DriverSettlement)
         .filter(DriverSettlement.driver_id == driver_id, DriverSettlement.period == _ky_hop_le(ky)).first())
    if not x:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Kỳ này chưa tất toán."})
    CT.rut(db, nguon_bang="driver_settlements", nguon_id=x.id)
    db.delete(x); db.commit()
    return {"ok": True}
