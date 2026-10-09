# -*- coding: utf-8 -*-
"""Tất toán tiền tạm ứng của tài xế — chốt THEO THÁNG.

Tài xế cầm phiếu tạm ứng đi lấy tiền trước mỗi chuyến. Hết tháng phải đối: đã ứng bao nhiêu, đã chi
thật bao nhiêu, rồi bù qua bù lại một lần.

    chênh lệch = đã chi thật − đã ứng
        dương  → công ty CHI BÙ cho tài xế
        âm     → tài xế NỘP LẠI

"Đã ứng" là các phiếu tạm ứng ĐÃ CẤP trong kỳ, chứ không phải số in trên giấy: giấy in rồi mà chưa
ra quỹ lấy tiền thì tài xế chưa cầm đồng nào. Từ 01/10 tạm ứng chi ở hệ kế toán anh Tune: số ứng là số trên PHIẾU CHI
bên đó đã ghi sổ (chi_tune.amount_lak) — tờ tạm ứng còn chờ có thể đã được tính lại theo dòng chi sau lúc gửi.

"Đã chi thật" là các dòng chi EPL ứng, không lấy từ kho, thuộc mục IV (đi đường), VI (khác) và các
dòng dầu MUA NGOÀI dọc đường — đúng những khoản tài xế móc tiền túi ứng ra trả.

KHÔNG tính những khoản mà công ty trả thẳng cho nhà cung cấp theo đợt (chipping Lào, chipping Việt,
thẻ đường cao tốc, lốp…). Tiền đó chưa bao giờ đi qua tay tài xế, tính vào là bảng tất toán phình lên
gấp mấy chục lần và người đọc không hiểu vì sao. Nhận biết bằng danh mục nhà cung cấp: khoản mục nào
có nhà cung cấp với kỳ thanh toán "theo đợt" hoặc "nạp thẻ" thì không phải tiền tài xế.

CHỐT ở đây, TIỀN ở hệ kế toán anh Tune (chủ dự án 01/10: bỏ phần tiền trang kế toán tạm, cắt sổ 01/10 — số tất toán cũ
bên đó là số thử, bỏ). KT Chi phí VC chốt từng tài xế một kỳ → bản chốt (driver_settlements) + quyết toán QT_TU Nợ 625 /
Có 1601 thành bút toán chờ gửi + phần chênh thành phiếu chi "Chi khác" (TT_CHI) hoặc phiếu thu "Thu khác" (TT_THU) bên đó,
đứng tên tài xế; thủ quỹ bên đó chi / thu và ghi sổ, bên này hỏi lại — services/chi_tat_toan_tune.py.
"""
import datetime as dt

from collections import defaultdict

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import and_, func, not_, or_
from sqlalchemy.orm import Session

from database import get_db
from models import ChiTune, Driver, Trip, TripExpense, Voucher
from services.bao_mat import nguoi_hien_tai
from services.tinh_toan import CACH_TRA, CACH_TRA_MAC_DINH, cach_tra, la_tien_mat_tai_xe, ty_gia
from services import dem_bao_cao as DEM

router = APIRouter()


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
# Tờ tạm ứng đã cấp: số ứng là số phiếu chi bên kế toán ĐÃ GHI SỔ (tiền tới tay tài xế), không có thì số của tờ (chi tại chỗ).
DA_CHI_KE_TOAN = and_(ChiTune.voucher_id == Voucher.id, ChiTune.status == "da_chi")
UNG_LAK = func.coalesce(ChiTune.amount_lak, Voucher.amount_lak)


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
        for (lak,) in (db.query(UNG_LAK).select_from(Voucher).outerjoin(ChiTune, DA_CHI_KE_TOAN)
                       .filter(Voucher.trip_id.in_(ma_phieu), Voucher.kind == "advance", Voucher.status == "da_cap")):
            ung += lak or 0
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
    return {"driver_id": tai_xe.id, "driver_code": tai_xe.driver_code, "driver_name": tai_xe.name,
            "driver_latin": tai_xe.name_latin, "period": ky,
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
    ung = {did: float(v or 0) for did, v in (db.query(Trip.driver_id, func.sum(UNG_LAK)).select_from(Voucher)
                                             .join(Trip, Trip.id == Voucher.trip_id).outerjoin(ChiTune, DA_CHI_KE_TOAN)
                                             .filter(*trong, Voucher.kind == "advance", Voucher.status == "da_cap")
                                             .group_by(Trip.driver_id))}
    ra = []
    for t in cac_tai_xe:
        ds, u = phieu.get(t.id, []), ung.get(t.id, 0.0)
        c = sum(chi.get(p.id, 0.0) for p in ds)
        ra.append({"driver_id": t.id, "driver_code": t.driver_code, "driver_name": t.name, "driver_latin": t.name_latin,
                   "period": ky, "so_phieu": len(ds), "tong_ung_lak": round(u, 2), "tong_chi_lak": round(c, 2),
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
    ung = {tid: float(v or 0) for tid, v in (db.query(Voucher.trip_id, func.sum(UNG_LAK)).select_from(Voucher)
                                             .join(Trip, Trip.id == Voucher.trip_id).outerjoin(ChiTune, DA_CHI_KE_TOAN)
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
    # tt5: số ứng theo phiếu chi đã ghi sổ bên kế toán (01/10) · tt4: chỉ xe nhà (29/09)
    viec = [(("tt5", d.isoformat()), [d.isoformat(), "ncc"], None) for d in ngay]
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
        ra.append({"driver_id": t.id, "driver_code": t.driver_code, "driver_name": t.name, "driver_latin": t.name_latin,
                   "period": ky, "so_phieu": n, "tong_ung_lak": round(u, 2), "tong_chi_lak": round(c, 2), "chenh_lech_lak": round(c - u, 2)})
    return ra


def bang_thang(db, ky):
    """Bảng tất toán cả tháng: MỌI tài xế đang làm, không kèm danh sách phiếu — màn Tất toán (services/chi_tat_toan_tune.bang)
    ghép bản chốt rồi mới lọc dòng trống (tài xế không phiếu, không ứng, chưa chốt). Ghép từ phần tính sẵn theo ngày."""
    return _bang_ky_ngay(db, db.query(Driver).filter(Driver.active.is_(True)).order_by(Driver.driver_code, Driver.name).all(), ky)


def mot(db, driver_id, ky):
    """Một tài xế một kỳ, kèm danh sách phiếu — khung chi tiết và lúc chốt. Mỗi phiếu thêm chi tiết từng dòng tiền (02/10 — màn
    Tất toán tài xế là bảng tính chi tiết): `chi_tiet_phieu`."""
    t = db.get(Driver, driver_id)
    if not t:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có tài xế này."})
    d = tinh_ky_lo(db, [t], ky)[0]             # nạp theo lô, không mỗi phiếu một câu
    ct = chi_tiet_phieu(db, [x["trip_id"] for x in d["phieu"]])
    for x in d["phieu"]:
        x.update(ct.get(x["trip_id"]) or {"dong": [], "da_ung_lak": 0, "da_chi_that_lak": 0, "chenh_lak": 0})
    return d


MUC_SO = {"fuel": "III", "travel": "IV", "other": "VI"}


def _cach(d, company):
    """Cách trả một dòng cho bảng tất toán: kho · the (trừ thẻ cao tốc) · ncc (ghi nợ trạm / nhà cung cấp) · luong · tien_mat."""
    if d.source == "kho":
        return "kho"
    if getattr(d, "toll_card_id", None):
        return "the"
    if d.ghi_no:
        return "ncc"
    c = cach_tra(d, company) if d.section in ("travel", "other") else "tien_mat"
    return c if c in ("ncc", "luong") else "tien_mat"


def chi_tiet_phieu(db, trip_ids):
    """{trip_id: {dong, da_ung_lak, da_chi_that_lak, chenh_lak}} — TỪNG DÒNG TIỀN mục III, IV, VI của mỗi phiếu xe nhà (giao ước
    màn Tất toán tài xế, 02/10). Bốn câu cho cả kỳ (dòng chi, phiếu, tờ tạm ứng, phiếu chi bên kế toán).

      dong[]   {muc III|IV|VI, khoan, sl, don_gia, tien_te, tien_lak, cach_tra: tien_mat | luong | ncc | the | kho,
                nguon: tam_ung (nằm trong số đã ứng theo tờ PTU) | tu_chi (tài xế tự bỏ tiền ngoài tạm ứng — dầu mua dọc đường…) |
                cung_luong | ncc | the | kho (không vào tất toán, hiện cho tài xế thấy đủ), so_ptu, phieu_chi}
      da_ung_lak       tờ PTU ĐÃ CẤP: số phiếu chi bên kế toán đã ghi sổ, không có thì số của tờ (cùng luật tinh_ky)
      da_chi_that_lak  Σ dòng tiền mặt tài xế (tinh_toan.la_tien_mat_tai_xe — cùng luật tờ tạm ứng)
      chenh_lak        da_chi_that − da_ung (dương: công ty chi bù)
    Dòng nào nằm trong số đã ứng: tờ PTU chỉ giữ tổng — chia theo chung_tu_dong_do._trong_tam_ung (cùng cách gói DO)."""
    from services.ban_giao import _ten
    from services.chung_tu_dong_do import _trong_tam_ung
    ids = [i for i in trip_ids if i] or [""]
    phieu = {p.id: p for p in db.query(Trip).filter(Trip.id.in_(ids))}
    dong = defaultdict(list)
    for d in (db.query(TripExpense).filter(TripExpense.trip_id.in_(ids), TripExpense.section.in_(tuple(MUC_SO)))
              .order_by(TripExpense.trip_id, TripExpense.section, TripExpense.line_no)):
        dong[d.trip_id].append(d)
    ptu = {v.trip_id: v for v in db.query(Voucher).filter(Voucher.trip_id.in_(ids), Voucher.kind == "advance", Voucher.status != "huy")}
    chi = {r.voucher_id: r for r in db.query(ChiTune).filter(ChiTune.trip_id.in_(ids))}
    ra = {}
    for tid, p in phieu.items():
        v = ptu.get(tid)
        rc = chi.get(v.id) if v is not None else None
        tm = [d for d in dong[tid] if la_tien_mat_tai_xe(d, p.company)]
        lak = {d.id: round((d.qty or 0) * (d.unit_price or 0) * ty_gia(p, d.currency)) for d in dong[tid]}
        so_ung = (rc.amount_lak if rc is not None and rc.amount_lak is not None else (v.amount_lak if v is not None else 0))
        trong = _trong_tam_ung(p, tm, so_ung)[0] if v is not None else set()
        da_ung = 0.0
        if v is not None and v.status == "da_cap":
            da_ung = rc.amount_lak if (rc is not None and rc.status == "da_chi" and rc.amount_lak is not None) else (v.amount_lak or 0)
        ds = []
        for d in dong[tid]:
            cach = _cach(d, p.company)
            if d in tm:
                nguon = "tam_ung" if d.id in trong else "tu_chi"
            else:
                nguon = {"luong": "cung_luong", "tien_mat": "tu_chi"}.get(cach, cach)
            ten = _ten(db, d)
            # item_key + khoan_lo (03/10): màn dịch tên khoản theo khoá chuẩn khi có; dòng tự gõ / phụ tùng thì khoan_lo = tên gõ
            ds.append({"id": d.id, "muc": MUC_SO.get(d.section), "khoan": ten[0], "khoan_lo": ten[1], "item_key": d.item_key,
                       "sl": d.qty, "don_gia": d.unit_price,
                       "tien_te": d.currency or "LAK", "tien_lak": lak[d.id], "cach_tra": cach, "nguon": nguon,
                       "tinh_tat_toan": d in tm,
                       "so_ptu": v.doc_no if (v is not None and nguon == "tam_ung") else None,
                       "phieu_chi": rc.document_no if (rc is not None and nguon == "tam_ung") else None})
        chi_that = sum(lak[d.id] for d in tm)
        ra[tid] = {"dong": ds, "da_ung_lak": round(da_ung), "da_chi_that_lak": round(chi_that), "chenh_lak": round(chi_that - da_ung),
                   "so_ptu": v.doc_no if v is not None else None, "phieu_chi_tam_ung": rc.document_no if rc is not None else None}
    return ra


# ---------------------------------------------------------------- màn Tất toán tài xế (01/10: tiền ở hệ kế toán anh Tune)
def _ky_hoac_thang_nay(ky):
    return _ky_hop_le(ky or dt.date.today().strftime("%Y-%m"))


@router.get("/api/tat-toan")
def bang_ky(ky: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bảng tháng: số tính từ phiếu + bản chốt + phiếu chi / thu bên kế toán (đang chờ thì hỏi lại) + bút toán QT_TU."""
    from services import chi_tat_toan_tune as TTT
    TTT.chan_vai(user, TTT.XEM_TT, "xem tất toán tài xế")
    return TTT.bang(db, _ky_hoac_thang_nay(ky))


@router.get("/api/tat-toan/{driver_id}")
def mot_tai_xe(driver_id: str, ky: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    from services import chi_tat_toan_tune as TTT
    TTT.chan_vai(user, TTT.XEM_TT, "xem tất toán tài xế")
    return TTT.mot(db, driver_id, _ky_hoac_thang_nay(ky))


@router.post("/api/tat-toan")
def chot_ky(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """{driver_id, period: YYYY-MM, note?, phuong_thuc?: cash|bank} → bản chốt + QT_TU (bút toán chờ) + phiếu chênh bên kế toán."""
    from services import chi_tat_toan_tune as TTT
    TTT.chan_vai(user, TTT.CHOT_TT, "chốt tất toán (việc của KT Chi phí VC)")
    if not d.get("driver_id"):
        raise HTTPException(422, {"ma": "THIEU_TAI_XE", "loi": "Chưa chọn tài xế."})
    return TTT.chot(db, user, str(d["driver_id"]), str(d.get("period") or ""), d.get("note"), d.get("phuong_thuc") or "cash")


@router.post("/api/tat-toan/{driver_id}/{viec}")
def viec_tat_toan(driver_id: str, viec: str, ky: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """cap-nhat (hỏi lại hệ kế toán — mọi vai xem được) · gui-lai (lần gửi phiếu chênh trước hỏng — KT Chi phí, Sếp)."""
    from services import chi_tat_toan_tune as TTT
    # 09/10: tên việc bằng chữ (trước chèn mã thô "gui-lai tất toán") — cụm có bản Lào / Anh (loi_dich)
    TTT.chan_vai(user, TTT.CHOT_TT if viec == "gui-lai" else TTT.XEM_TT,
                 {"cap-nhat": "cập nhật tất toán", "gui-lai": "gửi lại phiếu tất toán"}.get(viec, "%s tất toán" % viec))
    return TTT.viec_tt(db, user, driver_id, _ky_hop_le(ky), viec)


@router.delete("/api/tat-toan/{driver_id}")
def bo_chot(driver_id: str, ky: str = "", db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """Bỏ chốt để sửa lại — chỉ khi phiếu chênh bên kế toán chưa ghi sổ và QT_TU chưa gửi."""
    from services import chi_tat_toan_tune as TTT
    TTT.chan_vai(user, TTT.CHOT_TT, "bỏ chốt tất toán (việc của KT Chi phí VC)")
    return TTT.bo_chot(db, user, driver_id, _ky_hop_le(ky))


# ================================================================ G6 (06/10): CHI THẬT mục IV sau khi đã chi
# Chủ dự án chốt "KT Chi phí chỉnh chi thật mục IV": tài xế cầm tạm ứng đi (mục IV "đã chi" — phiếu chi tạm ứng bên kế toán đã ghi
# sổ), về khai chi thật ÍT hơn (hoặc nhiều hơn). Trước đây chỉ Sếp mở khoá mục mới sửa được đơn giá — mà mở khoá là rút / lập lại phiếu
# chi tạm ứng đã đưa tiền. Nay KT Chi phí VC (và Sếp) sửa SỐ CHI THẬT của từng dòng TIỀN MẶT TÀI XẾ CẦM mục IV, XE NHÀ, cho tới khi
# kỳ tất toán tài xế chứa DO đó đã chốt. KHÔNG đụng phiếu chi tạm ứng, tờ PTU, chứng từ PC_TU, bút toán: tạm ứng là tiền đã đưa —
# "đã ứng" giữ nguyên, "đã chi thật" theo số mới, chênh lệch đi vào tất toán tài xế (chi bù / nộp lại). Mỗi lần sửa một dòng nhật ký
# phiếu: "chi_that {json}" (dòng, khoản, cũ → mới, tiền tệ, ghi chú) — người và giờ là của dòng nhật ký.
TIEN_TO_NK = "chi_that "
XEM_CHI_THAT = ("expacct", "admin", "cash", "treasury")


def _loi3(http, ma, vi, lo, en):
    raise HTTPException(http, {"ma": ma, "loi": vi, "loi_lo": lo, "loi_en": en})


def ky_cua_phieu(p):
    """Kỳ tất toán chứa DO: tháng của NGÀY XE ĐI (không có thì ngày lập) — cùng luật _phieu_cua."""
    n = p.out_date or p.doc_date
    return n.strftime("%Y-%m") if n else None


def _ban_chot_cua(db, p):
    from models import DriverSettlement
    ky = ky_cua_phieu(p)
    if not p.driver_id or not ky:
        return None
    return db.query(DriverSettlement).filter(DriverSettlement.driver_id == p.driver_id, DriverSettlement.period == ky).first()


def _chan_chi_that(p, vai, muc_iv, chot):
    """None = sửa được; còn lại {ma, loi, loi_lo, loi_en, http} nói vì sao không (cùng câu cho API và giao diện)."""
    from services.phan_quyen import SUA_CHI_THAT
    thang = (lambda k: "%s/%s" % (k[5:7], k[:4]) if k else "")(ky_cua_phieu(p))
    if vai not in SUA_CHI_THAT:
        return {"http": 403, "ma": "KHONG_CO_QUYEN", "loi": "Chỉ KT Chi phí VC (và Sếp) sửa số chi thật mục IV.",
                "loi_lo": "ສະເພາະບັນຊີລາຍຈ່າຍ ວຽງຈັນ (ແລະ ຫົວໜ້າ) ແກ້ລາຍຈ່າຍຕົວຈິງ ໝວດ IV.",
                "loi_en": "Only the Vientiane cost accountant (and the owner) can edit actual spending in section IV."}
    if p.company == "joint":
        return {"http": 409, "ma": "XE_THUE", "loi": "Phiếu xe thuê: tạm ứng là công nợ chủ xe, không tất toán với tài xế — chỉ sửa chi thật "
                                                     "cho xe nhà.",
                "loi_lo": "ໃບລົດເຊົ່າ: ເງິນລ່ວງໜ້າເປັນໜີ້ເຈົ້າຂອງລົດ, ບໍ່ສະສາງກັບໂຊເຟີ — ແກ້ລາຍຈ່າຍຕົວຈິງໄດ້ສະເພາະລົດບໍລິສັດ.",
                "loi_en": "Hired truck: the advance is owed by the truck owner, not settled with the driver — actual spending is edited "
                          "for company trucks only."}
    if muc_iv != "paid":
        return {"http": 409, "ma": "CHUA_CHI", "loi": "Mục IV chưa chi tạm ứng — KT Chi phí nhập / sửa đơn giá lúc kiểm mục IV như thường.",
                "loi_lo": "ໝວດ IV ຍັງບໍ່ໄດ້ຈ່າຍເງິນລ່ວງໜ້າ — ບັນຊີລາຍຈ່າຍໃສ່ / ແກ້ລາຄາຕອນກວດໝວດ IV ຕາມປົກກະຕິ.",
                "loi_en": "Section IV advance is not paid yet — the cost accountant enters / edits prices when checking section IV."}
    if not p.driver_id:
        return {"http": 409, "ma": "THIEU_TAI_XE", "loi": "Phiếu chưa gắn tài xế trong danh mục — không biết kỳ tất toán nào.",
                "loi_lo": "ໃບນີ້ຍັງບໍ່ໄດ້ຜູກໂຊເຟີໃນລາຍການ — ບໍ່ຮູ້ງວດສະສາງ.",
                "loi_en": "The slip has no driver from the list — the settlement period is unknown."}
    if chot is not None:
        ai = " — %s %s" % (chot.settled_by or "", chot.settled_at.strftime("%d/%m/%Y") if chot.settled_at else "")
        return {"http": 409, "ma": "KY_DA_CHOT",
                "loi": "Kỳ %s của tài xế %s đã chốt tất toán%s: số chi thật đã khoá. Muốn sửa: bỏ chốt ở màn Tất toán tài xế (khi phiếu "
                       "chênh bên kế toán chưa ghi sổ), sửa, rồi chốt lại." % (thang, p.driver_name or "", ai),
                "loi_lo": "ງວດ %s ຂອງໂຊເຟີ %s ປິດສະສາງແລ້ວ%s: ລາຍຈ່າຍຕົວຈິງຖືກລັອກ. ຢາກແກ້: ຍົກເລີກການປິດຢູ່ໜ້າສະສາງໂຊເຟີ (ເມື່ອໃບສ່ວນຕ່າງ"
                          "ຢູ່ບັນຊີຍັງບໍ່ລົງບັນຊີ), ແກ້, ແລ້ວປິດຄືນ." % (thang, p.driver_name or "", ai),
                "loi_en": "Period %s for driver %s is already settled%s: actual spending is locked. To change it: reopen on the Driver "
                          "settlement screen (while the difference voucher is not posted), edit, then close again."
                          % (thang, p.driver_name or "", ai)}
    return None


def _dong_tien_mat_iv(db, p):
    """Dòng mục IV là TIỀN MẶT TÀI XẾ CẦM (cùng luật tờ tạm ứng / tất toán — la_tien_mat_tai_xe), theo thứ tự trên phiếu."""
    return [e for e in db.query(TripExpense).filter(TripExpense.trip_id == p.id, TripExpense.section == "travel")
            .order_by(TripExpense.line_no) if la_tien_mat_tai_xe(e, p.company)]


def _nhat_ky_chi_that(db, p):
    import json
    from models import TripLog
    ra = []
    for l in (db.query(TripLog).filter(TripLog.trip_id == p.id, TripLog.action.like(TIEN_TO_NK + "%"))
              .order_by(TripLog.ts.desc()).limit(100)):
        try:
            x = json.loads(l.action[len(TIEN_TO_NK):])
        except ValueError:
            continue
        x.update({"ts": l.ts.isoformat() if l.ts else None, "user": l.user_name, "role": l.role})
        ra.append(x)
    return ra


def xuat_chi_that(db, p, vai):
    """Gói màn "Chi thật mục IV" (phiếu xuất xe): sửa được không và vì sao, từng dòng tiền mặt (đang ghi = SL × đơn giá), nhật ký."""
    from models import TripSection
    muc_iv = (db.query(TripSection.status).filter(TripSection.trip_id == p.id, TripSection.section == "travel").scalar()) or "wait"
    chot = _ban_chot_cua(db, p)
    chan = _chan_chi_that(p, vai, muc_iv, chot)
    return {"trip_id": p.id, "doc_no": p.doc_no, "ky": ky_cua_phieu(p), "muc_iv": muc_iv, "duoc_sua": chan is None,
            "ly_do": {k: v for k, v in chan.items() if k != "http"} if chan else None,
            "tat_toan": ({"status": chot.status, "settled_by": chot.settled_by,
                          "settled_at": chot.settled_at.isoformat(timespec="minutes") if chot.settled_at else None} if chot else None),
            "dong": [{"id": e.id, "line_no": e.line_no, "item_key": e.item_key, "item_name": e.item_name, "qty": e.qty,
                      "unit_price": e.unit_price, "currency": e.currency or "LAK",
                      "chi_that": round((e.qty or 0) * (e.unit_price or 0), 6), "note": e.note} for e in _dong_tien_mat_iv(db, p)],
            "nhat_ky": _nhat_ky_chi_that(db, p)}


@router.get("/api/trips/{tid}/chi-that")
def xem_chi_that(tid: str, db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    if user.role not in XEM_CHI_THAT:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN", "loi": "Vai %s không xem chi thật mục IV." % user.role})
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    return xuat_chi_that(db, p, user.role)


@router.post("/api/trips/{tid}/chi-that")
def sua_chi_that(tid: str, d: dict = Body(...), db: Session = Depends(get_db), user=Depends(nguoi_hien_tai)):
    """{dong: [{id, chi_that}], ghi_chu?} — `chi_that` là THÀNH TIỀN thật của dòng theo tiền tệ của dòng (≥ 0). Máy giữ số lượng, đặt
    đơn giá = chi thật ÷ số lượng (số lượng 0 thì thành 1 × chi thật). Dòng không đổi thì bỏ qua, không ghi nhật ký."""
    import json
    from models import TripLog, TripSection
    from services.tinh_toan import lam_tron
    p = db.get(Trip, tid)
    if not p:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có phiếu này."})
    muc_iv = (db.query(TripSection.status).filter(TripSection.trip_id == p.id, TripSection.section == "travel").scalar()) or "wait"
    chan = _chan_chi_that(p, user.role, muc_iv, _ban_chot_cua(db, p))
    if chan:
        raise HTTPException(chan.pop("http"), chan)
    gui = d.get("dong")
    if not isinstance(gui, list) or not gui:
        raise HTTPException(422, {"ma": "THIEU_DONG", "loi": "Chưa có dòng nào để sửa chi thật."})
    ghi_chu = (str(d.get("ghi_chu") or "").strip() or None)
    dong = {e.id: e for e in _dong_tien_mat_iv(db, p)}
    sua = []
    for x in gui:
        x = x if isinstance(x, dict) else {}
        e = dong.get(str(x.get("id") or ""))
        if e is None:
            _loi3(409, "KHONG_PHAI_TIEN_MAT", "Chỉ sửa chi thật dòng TIỀN MẶT tài xế cầm của mục IV (không phải dòng thẻ, trả cùng lương, nợ "
                                              "nhà cung cấp, hay dòng của phiếu khác).",
                  "ແກ້ລາຍຈ່າຍຕົວຈິງໄດ້ສະເພາະແຖວເງິນສົດທີ່ໂຊເຟີຖືໄປ ໝວດ IV.",
                  "Only section IV cash lines carried by the driver can be edited (not card, salary or supplier lines).")
        try:
            v = float(str(x.get("chi_that")).replace(",", ""))
        except (TypeError, ValueError):
            v = None
        if v is None or v != v or v < 0:
            _loi3(422, "SO_SAI", "Chi thật phải là số không âm, nhận '%s'." % x.get("chi_that"),
                  "ລາຍຈ່າຍຕົວຈິງຕ້ອງເປັນຕົວເລກບໍ່ຕິດລົບ.", "Actual spending must be a non-negative number.")
        moi = lam_tron(v, e.currency or "LAK")
        cu = round((e.qty or 0) * (e.unit_price or 0), 6)
        if abs(moi - cu) < 1e-6:
            continue
        sua.append((e, cu, moi))
    for e, cu, moi in sua:
        if (e.qty or 0) <= 0:
            e.qty = 1
        e.unit_price = round(moi / e.qty, 6)
        db.add(TripLog(trip_id=p.id, user_name=user.full_name, role=user.role,
                       action=TIEN_TO_NK + json.dumps({"dong": e.line_no, "dong_id": e.id, "item_key": e.item_key, "item_name": e.item_name,
                                                       "cu": cu, "moi": moi, "tien_te": e.currency or "LAK", "ghi_chu": ghi_chu},
                                                      ensure_ascii=False)))
    if sua:
        db.commit()
    return xuat_chi_that(db, p, user.role)
