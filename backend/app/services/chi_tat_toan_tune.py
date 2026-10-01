# -*- coding: utf-8 -*-
"""TẤT TOÁN TÀI XẾ và TRẢ NHÀ CUNG CẤP qua hệ kế toán anh Tune — chủ dự án chốt 01/10/2026: bỏ phần tiền của trang kế toán
tạm, cắt sổ hôm nay, từ giờ mọi việc tiền chỉ ở hệ anh Tune. Khoản ĐI QUA TIỀN thành phiếu chi / thu bên đó; khoản KHÔNG qua
tiền thành bút toán chờ gửi ở đây (services/but_toan_cho.py), chờ bên đó có API bút toán.

Tất toán tài xế (xe nhà, chốt theo tháng — số tính ở routes/tat_toan.py):
  · QT_TU   Nợ 625 / Có 1601  = số tài xế ĐÃ CHI THẬT. Không qua tiền → bút toán chờ, nguồn "tat_toan".
  · TT_CHI  Nợ 1601 / Có tiền = chênh dương (công ty chi bù)  → phiếu chi "Chi khác" (DOTY 60) đứng tên tài xế (nhân viên EPLTX-…).
  · TT_THU  Nợ tiền / Có 1601 = chênh âm (tài xế nộp lại)    → phiếu thu "Thu khác" (DOTY 17), cùng đối tượng.
  Chênh dưới 1 Kíp: không lập phiếu, chốt xong ngay. Thủ quỹ bên đó chi / thu rồi GHI SỔ; bên em hỏi lại (STATUS 12/13) →
  bản chốt "xong". Chốt xong 1601 của tài xế về 0 cho kỳ đó.

Trả nhà cung cấp:
  · PC_NCC  Nợ 4021 / Có tiền → phiếu chi "Chi khác" (DOTY 60) đứng tên nhà cung cấp (master-data/suppliers, EPLNCC-<id>).
  Phần GHI NỢ (Nợ 625 · 614 / Có 4021, lúc khoá phiếu) là bút toán chờ do khoá phiếu ghi (but_toan_cho, nguồn no_ncc).

Mỗi phiếu bên đó một dòng phieu_tien_tune, khoá (nguon, ma_nguon). Như services/chi_tune.py: bên đó KHÔNG có Idempotency-Key —
trước khi tạo, tìm phiếu cùng đối tượng + cùng số tham chiếu, có thì dùng lại; lỗi có khi về HTTP 200 kèm Success false;
phiếu bên đó đã ghi sổ thì không xoá, không sửa ở đây.
"""
import datetime as dt
import json
import time

from fastapi import HTTPException
from sqlalchemy import func

from models import ButToanCho, ChiTune, Driver, DriverSettlement, ExchangeRate, PhieuTienTune, Supplier, Trip
from services import chi_tune as CHI
from services import chung_tu as CT

NGUON_TT, NGUON_NCC = "tat_toan", "ncc"
# loại tờ → (VoucherType, biến môi trường DOTY, DOTY mặc định — đọc ở cmpayment-receipt/document-types 01/10)
LOAI = {"TT_CHI": ("CMP", "QLSX_DOTY_CHI_KHAC", 60), "TT_THU": ("CMR", "QLSX_DOTY_THU_KHAC", 17),
        "PC_NCC": ("CMP", "QLSX_DOTY_CHI_KHAC", 60)}
CACH_TRA = ("cash", "bank")

# ai làm gì (bảng Nhiệm Vụ của khách, quy trình bước 19): KT Chi phí VC lập tất toán, quỹ chi / thu ở hệ kế toán
XEM_TT = ("expacct", "cash", "treasury", "admin")
CHOT_TT = ("expacct", "admin")
XEM_NCC = ("acct", "expacct", "fuel", "rev", "treasury", "cash", "admin")
DE_NGHI_NCC = ("expacct", "admin")


def _loi(ma, loi, http=422, **them):
    raise HTTPException(http, {"ma": ma, "loi": loi, **them})


def chan_vai(user, vai, viec):
    if user.role not in vai:
        _loi("KHONG_CO_QUYEN", "Vai %s không được %s." % (user.role, viec), 403)


def _btc():
    """services/but_toan_cho (agent B). Chưa có thì báo rõ, không tự dựng bảng."""
    try:
        from services import but_toan_cho as BTC
    except ImportError:
        _loi("CHUA_CO_BUT_TOAN_CHO", "Trang điều xe chưa có sổ bút toán chờ gửi (services/but_toan_cho) — chưa ghi được quyết toán "
                                     "tạm ứng QT_TU, nên chưa chốt tất toán được.", 503)
    return BTC


def _ten(user):
    return getattr(user, "full_name", None)


def _gio(t):
    return t.isoformat(timespec="minutes") + "+00:00" if t else None


# ================================================================ một phiếu bên hệ kế toán
def _doi_tuong(db, rec):
    if rec.doi_tuong_loai == "tai_xe":
        return CHI.doi_tuong_tai_xe(db, rec.doi_tuong_id, rec.doi_tuong_ten)
    s = db.get(Supplier, rec.doi_tuong_id) if rec.doi_tuong_id else None
    return CHI.doi_tuong(db, "ncc", rec.doi_tuong_id, rec.doi_tuong_ten or (s.name if s else None), to_chuc=True)


def _dien_giai(rec):
    try:
        return (json.loads(rec.chi_tiet or "{}").get("dien_giai") or "")[:250] or rec.ref_no
    except ValueError:
        return rec.ref_no


def _dung_goi(rec, obj):
    vt, bien, mac_dinh = LOAI[rec.loai]
    lak = rec.currency == "LAK"
    ma_cur, hom_nay = CHI.ma_tien(rec.currency), dt.date.today()
    ty = 1 if lak else round((rec.amount_lak or 0) / rec.amount, 6)
    goc = rec.amount if lak else rec.amount_lak
    dg = _dien_giai(rec)
    return {
        "TmpId": 0, "RealId": 0, "VoucherType": vt, "SessionId": "epllao-%s-%s-%d" % (rec.nguon, rec.id, int(time.time())),
        "PostMode": "None",
        "Header": {"CountryId": CHI._cfg("QLSX_COUNTRY_ID", 11), "OrgId": CHI._cfg("QLSX_ORG_ID", 1368), "FiciAutoId": CHI.ma_ky(hom_nay),
                   "DotyAutoId": CHI._cfg(bien, mac_dinh), "ObjectId": obj, "CurrencyId": ma_cur, "DocumentDate": hom_nay.isoformat(),
                   "RefDocumentNo": rec.ref_no, "Description": dg, "IsCash": rec.phuong_thuc == "cash", "IsLocal": lak,
                   "IsDirect": True, "ExchangeRate": ty, "Amount": rec.amount, "BaseAmount": goc,
                   "ContactName": (rec.doi_tuong_ten or "")[:100] or None},
        "Relations": [],
        "Entries": [{"SourceLineKey": "EPLLAO:%s:%s" % (rec.loai, rec.id), "ObjectId": obj, "CurrencyId": ma_cur,
                     "DebitAccount": rec.no, "CreditAccount": rec.co, "Amount": rec.amount, "BaseAmount": goc, "ExchangeRate": ty,
                     "EntryTypeId": 11, "Description": dg, "ValidateMoney": True}],
    }


def _tim_da_co(rec, obj):
    """Phiếu bên kế toán đã có cho bản ghi này (cùng loại phiếu, cùng đối tượng, cùng số tham chiếu) — chống tạo trùng."""
    hom_nay = dt.date.today()
    tu = min(hom_nay - dt.timedelta(days=45), (rec.created_at or dt.datetime.utcnow()).date() - dt.timedelta(days=2))
    kq = CHI._goi("POST", "/api/v1/accounting/cmpayment-receipt/list", {
        "PageIndex": 1, "PageSize": 50, "VoucherType": rec.voucher_type, "OrgAutoId": CHI._cfg("QLSX_ORG_ID", 1368), "ObjectId": obj,
        "DateType": 0, "DateFrom": tu.isoformat(), "DateTo": (hom_nay + dt.timedelta(days=1)).isoformat()}) or {}
    return [x for x in (kq.get("Rows") or []) if (x.get("DOC_REFDOCUMENTNO") or "") == rec.ref_no]


def gui(db, rec, user=None):
    """Tạo (hoặc dùng lại) phiếu chi / thu bên kế toán cho `rec`, CHƯA ghi sổ. Ghi kết quả — kể cả khi hỏng — rồi mới trả / ném."""
    if rec.status in ("da_chi", "huy"):
        return rec
    if rec.status == "da_gui" and rec.real_id:
        try:
            dong_bo(db, rec)
        except HTTPException:
            pass
        return rec
    rec.attempts, rec.last_attempt_at = (rec.attempts or 0) + 1, dt.datetime.utcnow()
    try:
        obj = rec.obj_id = _doi_tuong(db, rec)
        body = _dung_goi(rec, obj)
        rec.request_body = json.dumps(body, ensure_ascii=False)
        cu = _tim_da_co(rec, obj)
        if cu:                                               # lần trước bên đó đã lưu mà bên em chưa kịp nhớ
            rec.real_id, rec.document_no = int(cu[0]["DOC_DOCUMENTID"]), cu[0].get("DOC_DOCUMENTNO")
            rec.response_body = json.dumps({"dung_lai": cu[0]}, ensure_ascii=False, default=str)[:20000]
        else:
            kq = CHI._goi("POST", "/api/v1/accounting/cmpayment-receipt/save-and-commit", body) or {}
            rec.response_body = json.dumps(kq, ensure_ascii=False, default=str)[:20000]
            if not kq.get("RealId"):
                _loi("KHONG_CO_REALID", "Hệ kế toán không trả số phiếu: %s" % (kq.get("Message") or ""), 502)
            rec.real_id = int(kq["RealId"])
        rec.status, rec.error_code, rec.error_message = "da_gui", None, None
        db.commit()
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {}
        rec.status, rec.error_code, rec.error_message = "loi", d.get("ma"), d.get("loi") or str(e.detail)
        db.commit()
        raise
    try:
        dong_bo(db, rec)                                     # lấy số phiếu bên đó; có khi thủ quỹ ghi sổ ngay
    except HTTPException:
        pass
    return rec


def dong_bo(db, rec):
    """Đọc lại phiếu bên kế toán; đã ghi sổ (STATUS 12/13) → "da_chi" và áp sang nguồn. Lỗi mạng: giữ nguyên, ném lỗi."""
    if rec is None or rec.status != "da_gui" or not rec.real_id:
        return rec
    try:
        kq = CHI._goi("GET", "/api/v1/accounting/cmpayment-receipt/%d?voucherType=%s" % (rec.real_id, rec.voucher_type)) or {}
    except HTTPException as e:
        if (e.detail or {}).get("ma") == "BEN_KE_TOAN_TU_CHOI":
            rec.status, rec.error_code = "loi", "PHIEU_CHI_MAT"
            rec.error_message = "Không đọc được phiếu %s bên kế toán (đã xoá?): %s" % (rec.document_no or rec.real_id, e.detail.get("loi"))
            db.commit()
        raise
    m = kq.get("Master")
    rec.checked_at = dt.datetime.utcnow()
    if not m:
        # phiếu đã bị xoá bên đó: API vẫn trả Success true, Master null (thử 01/10) — không coi là "còn chờ chi"
        rec.status, rec.error_code = "loi", "PHIEU_CHI_MAT"
        rec.error_message = "Phiếu %s không còn bên hệ kế toán (đã xoá?) — bấm gửi lại để lập phiếu mới." % (rec.document_no or rec.real_id)
        db.commit()
        return rec
    rec.document_no = m.get("DOCUMENTNO") or rec.document_no
    rec.tune_status = int(m.get("STATUS") or 0)
    if rec.tune_status in CHI.DA_GHI_SO:
        rec.status, rec.post_by, rec.post_at = "da_chi", m.get("POSTNAME") or None, CHI._ngay_gio(m.get("POSTDATE"))
        rec.error_code = rec.error_message = None
        _ap_da_chi(db, rec)
    db.commit()
    return rec


def _ap_da_chi(db, rec):
    if rec.nguon == NGUON_TT:
        x = db.get(DriverSettlement, rec.ma_nguon.rsplit(":", 1)[-1])
        if x is not None:
            x.status = "xong"


def _hoi_truoc_khi_rut(db, rec):
    """Hỏi lại phiếu đang chờ TRƯỚC mọi thay đổi khác (dong_bo tự commit phần nó đọc về). Phiếu bên đó đã mất (xoá tay) thì
    dong_bo đánh PHIEU_CHI_MAT — coi như không còn gì để rút; lỗi mạng thì ném (chặn)."""
    if rec is None or rec.status != "da_gui" or not rec.real_id:
        return
    try:
        dong_bo(db, rec)
    except HTTPException:
        if rec.error_code != "PHIEU_CHI_MAT":
            raise


def _rut_ben_ke_toan(db, rec):
    """Bỏ phiếu bên kế toán của `rec` (chưa ghi sổ). Đã ghi sổ → 409. Không gọi được → ném (chặn): không để phiếu mồ côi chờ
    thủ quỹ chi cho một việc không còn. Gọi _hoi_truoc_khi_rut trước. KHÔNG commit — người gọi commit cùng việc của nó."""
    if rec.status == "da_chi":
        _loi("DA_CHI_O_KE_TOAN", "Phiếu %s bên hệ kế toán đã ghi sổ (tiền đã đi) — không bỏ được ở đây, đối soát ở hệ kế toán "
                                 "trước." % (rec.document_no or rec.real_id), 409)
    if rec.real_id and rec.error_code != "PHIEU_CHI_MAT":
        ds = [{"DOC_DOCUMENTID": rec.real_id}]
    elif rec.obj_id:
        ds = _tim_da_co(rec, rec.obj_id)                     # lần gửi hỏng giữa chừng: bên đó có thể đã lưu
    else:
        ds = []
    for x in ds:
        if int(x.get("ST_AUTOID") or 0) in CHI.DA_GHI_SO:
            _loi("DA_CHI_O_KE_TOAN", "Phiếu %s bên hệ kế toán đã ghi sổ — không bỏ được ở đây." % x.get("DOC_DOCUMENTNO"), 409)
        CHI._goi("POST", "/api/v1/accounting/cmpayment-receipt/delete",
                 {"DocumentId": int(x["DOC_DOCUMENTID"]), "VoucherType": rec.voucher_type})
    rec.status = "huy"


def xuat(rec, thay_tien=True):
    if rec is None:
        return None
    return {"id": rec.id, "nguon": rec.nguon, "loai": rec.loai, "voucher_type": rec.voucher_type, "ref_no": rec.ref_no,
            "doi_tuong_loai": rec.doi_tuong_loai, "doi_tuong_id": rec.doi_tuong_id, "doi_tuong_ten": rec.doi_tuong_ten,
            "period": rec.period, "currency": rec.currency, "amount": rec.amount if thay_tien else None,
            "amount_lak": rec.amount_lak if thay_tien else None, "phuong_thuc": rec.phuong_thuc, "no": rec.no, "co": rec.co,
            "dien_giai": _dien_giai(rec), "status": rec.status, "document_no": rec.document_no, "real_id": rec.real_id,
            "tune_status": rec.tune_status, "obj_id": rec.obj_id, "post_by": rec.post_by, "post_at": _gio(rec.post_at),
            "error_code": rec.error_code, "error_message": rec.error_message, "attempts": rec.attempts,
            "created_by": rec.created_by, "created_at": _gio(rec.created_at),
            "checked_at": _gio(rec.checked_at)}


# ================================================================ tất toán tài xế
def ma_nguon_tt(x):
    """Khoá nguồn của MỘT lần chốt: tài xế · kỳ · mã bản chốt — bỏ chốt rồi chốt lại là nguồn mới (phiếu cũ đã huỷ giữ dấu vết)."""
    return "%s:%s:%s" % (x.driver_id, x.period, x.id)


def _phieu_tt(db, x):
    return (db.query(PhieuTienTune).filter(PhieuTienTune.nguon == NGUON_TT, PhieuTienTune.ma_nguon == ma_nguon_tt(x)).first()
            if x is not None else None)


def _but_toan_tt(db, x):
    return (db.query(ButToanCho).filter(ButToanCho.nguon == NGUON_TT, ButToanCho.ma_nguon == ma_nguon_tt(x)).first()
            if x is not None else None)


def _ngay_hach_toan(ky):
    """Quyết toán ghi chi phí vào ĐÚNG THÁNG xe chạy: ngày cuối kỳ; kỳ chưa hết thì hôm nay."""
    from routes.tat_toan import _khoang
    return min(_khoang(ky)[1], dt.date.today())


def _gon_bt(r):
    return ({"id": r.id, "status": r.status, "can_dao": bool(r.can_dao), "ngay": r.ngay.isoformat() if r.ngay else None,
             "tong": r.tong, "tien_te": r.tien_te, "so_ben_ke_toan": r.so_ben_ke_toan} if r is not None else None)


def _xuat_chot(x, rec, bt, d=None, day_du=False):
    """Bản chốt + phiếu bên kế toán + bút toán QT_TU. `d` là số tính LÚC NÀY — lệch với số đã chốt (phiếu trong kỳ bị sửa sau
    khi chốt) thì báo `lech`, để KT Chi phí bỏ chốt chốt lại."""
    if x is None:
        return None
    BTC = None
    if day_du and bt is not None:
        try:
            BTC = _btc()
        except HTTPException:
            BTC = None
    return {"id": x.id, "status": x.status, "so_phieu": x.so_phieu, "tong_ung_lak": x.tong_ung_lak, "tong_chi_lak": x.tong_chi_lak,
            "chenh_lech_lak": x.chenh_lech_lak, "settled_by": x.settled_by, "settled_at": _gio(x.settled_at), "note": x.note,
            "lech": bool(d is not None and (abs((d["tong_chi_lak"] or 0) - (x.tong_chi_lak or 0)) >= 1
                                            or abs((d["tong_ung_lak"] or 0) - (x.tong_ung_lak or 0)) >= 1)),
            "phieu_ke_toan": xuat(rec), "quyet_toan": BTC.xuat(bt) if BTC is not None else _gon_bt(bt)}


def bang(db, ky, hoi_lai=30):
    """Bảng tất toán cả tháng: mọi tài xế có phiếu / có ứng / đã chốt. Phiếu bên kế toán đang chờ thì hỏi lại (tối đa `hoi_lai`
    phiếu, dừng ở lỗi mạng đầu tiên — bảng vẫn hiện, trạng thái cũ)."""
    from routes import tat_toan as TT
    ds = TT.bang_thang(db, ky)
    chot = {x.driver_id: x for x in db.query(DriverSettlement).filter(DriverSettlement.period == ky)}
    ma = {ma_nguon_tt(x): x for x in chot.values()}
    phieu = {r.ma_nguon: r for r in db.query(PhieuTienTune).filter(PhieuTienTune.nguon == NGUON_TT, PhieuTienTune.ma_nguon.in_(list(ma) or [""]))}
    bt = {r.ma_nguon: r for r in db.query(ButToanCho).filter(ButToanCho.nguon == NGUON_TT, ButToanCho.ma_nguon.in_(list(ma) or [""]))}
    for r in [r for r in phieu.values() if r.status == "da_gui"][:hoi_lai]:
        try:
            dong_bo(db, r)
        except HTTPException:
            break
    dong = []
    for d in ds:
        x = chot.get(d["driver_id"])
        k = ma_nguon_tt(x) if x is not None else None
        d["da_tat_toan"] = x is not None
        d["tat_toan"] = _xuat_chot(x, phieu.get(k), bt.get(k), d)
        if d["so_phieu"] or d["tong_ung_lak"] or x is not None:
            dong.append(d)
    return {"ky": ky, "dong": dong, "tong_ung_lak": round(sum(d["tong_ung_lak"] for d in ds), 2),
            "tong_chi_lak": round(sum(d["tong_chi_lak"] for d in ds), 2),
            "cho_chi": sum(1 for d in dong if (d["tat_toan"] or {}).get("status") == "cho_chi")}


def _ban_chot(db, driver_id, ky):
    return db.query(DriverSettlement).filter(DriverSettlement.driver_id == driver_id, DriverSettlement.period == ky).first()


def mot(db, driver_id, ky, cap_nhat=True):
    """Một tài xế một kỳ, kèm danh sách phiếu, bản chốt, phiếu bên kế toán (hỏi lại nếu đang chờ), bút toán QT_TU đầy đủ."""
    from routes import tat_toan as TT
    d = TT.mot(db, driver_id, ky)
    x = _ban_chot(db, driver_id, ky)
    rec = _phieu_tt(db, x)
    if cap_nhat and rec is not None and rec.status == "da_gui":
        try:
            dong_bo(db, rec)
        except HTTPException:
            pass
    d["da_tat_toan"] = x is not None
    d["tat_toan"] = _xuat_chot(x, rec, _but_toan_tt(db, x), d, day_du=True)
    d["tam_ung_cho"] = _tam_ung_cho(db, driver_id, ky, hoi_lai=False)
    return d


def _tam_ung_cho(db, driver_id, ky, hoi_lai=True):
    """Phiếu chi tạm ứng bên kế toán của các chuyến trong kỳ CHƯA chi xong (đang chờ thủ quỹ, hoặc gửi hỏng mà tờ tạm ứng còn
    chờ) — tiền đó chưa tới tay tài xế nhưng có thể tới sau, tất toán bây giờ là lệch."""
    from models import Voucher
    from routes.tat_toan import _khoang, _trong_ky
    dau, cuoi = _khoang(ky)
    ids = [i for (i,) in db.query(Trip.id).filter(Trip.driver_id == driver_id, *_trong_ky(dau, cuoi))]
    ds = (db.query(ChiTune).join(Voucher, Voucher.id == ChiTune.voucher_id)
          .filter(ChiTune.trip_id.in_(ids or [""]), ChiTune.status.in_(("da_gui", "loi")), Voucher.status == "cho").all())
    if hoi_lai:
        for r in [r for r in ds if r.status == "da_gui"]:
            try:
                CHI.dong_bo(db, r)
            except HTTPException:
                break
        ds = [r for r in ds if r.status in ("da_gui", "loi")]
    so = {p.id: p.doc_no for p in db.query(Trip.id, Trip.doc_no).filter(Trip.id.in_([r.trip_id for r in ds] or [""]))}
    return [{"trip_id": r.trip_id, "doc_no": so.get(r.trip_id), "status": r.status, "document_no": r.document_no,
             "error_message": r.error_message} for r in ds]


def chot(db, user, driver_id, ky, note=None, phuong_thuc="cash"):
    """Chốt một tài xế một kỳ: bản chốt + QT_TU (bút toán chờ) + phiếu chi bù / thu hoàn bên kế toán (nếu chênh ≥ 1 Kíp).
    Chốt rồi thì không chốt lại; muốn sửa thì bỏ chốt (khi phiếu bên kế toán chưa ghi sổ) rồi chốt lại."""
    from routes import tat_toan as TT
    ky = TT._ky_hop_le(ky)
    phuong_thuc = (phuong_thuc or "cash").strip()
    if phuong_thuc not in CACH_TRA:
        _loi("CACH_TRA_SAI", "Cách chi / thu phải là tiền mặt (cash) hoặc chuyển khoản (bank).")
    t = db.get(Driver, driver_id)
    if t is None:
        _loi("KHONG_THAY", "Không có tài xế này.", 404)
    if _ban_chot(db, driver_id, ky) is not None:
        _loi("DA_TAT_TOAN", "Kỳ %s của tài xế %s đã tất toán rồi." % (ky, t.name), 409)
    cho = _tam_ung_cho(db, driver_id, ky)
    if cho:
        _loi("TAM_UNG_CHUA_CHI_XONG", "Kỳ %s còn tạm ứng chưa chi xong ở hệ kế toán (%s) — thủ quỹ chi xong, hoặc huỷ tờ tạm ứng, "
                                      "rồi mới tất toán." % (ky, ", ".join(x["doc_no"] or x["trip_id"] for x in cho)), 409, phieu=cho)
    k = TT.mot(db, driver_id, ky)
    if not k["so_phieu"]:
        _loi("KY_TRONG", "Kỳ %s tài xế %s không có phiếu xe nhà nào." % (ky, t.name))
    chi, ung = round(k["tong_chi_lak"] or 0), round(k["tong_ung_lak"] or 0)
    ch = chi - ung
    BTC = _btc() if chi >= 1 else None
    x = DriverSettlement(driver_id=driver_id, driver_name=t.name, period=ky, so_phieu=k["so_phieu"], tong_ung_lak=ung,
                         tong_chi_lak=chi, chenh_lech_lak=ch, status="cho_chi" if abs(ch) >= 1 else "xong",
                         settled_by=_ten(user), settled_at=dt.datetime.utcnow(), note=(note or "").strip() or None)
    db.add(x)
    db.flush()
    ma, ten_tx = ma_nguon_tt(x), "%s%s" % (t.name, (" (%s)" % t.driver_code) if t.driver_code else "")
    thang = "%s/%s" % (ky[5:7], ky[:4])
    if BTC is not None:
        no, _, co, _ = CT.dinh_khoan("QT_TU", company="EPL", section="travel", tien_te="LAK")
        BTC.ghi(db, NGUON_TT, ma, _ngay_hach_toan(ky),
                [{"no": no, "co": co, "tien": chi, "ccy": "LAK", "doi_tuong": {"loai": "tai_xe", "ref_id": driver_id},
                  "dien_giai": "Quyết toán tạm ứng kỳ %s · %s · đã chi thật %s phiếu" % (thang, ten_tx, k["so_phieu"])}],
                "Quyết toán tạm ứng tài xế %s kỳ %s" % (ten_tx, thang), by_user=_ten(user))
    rec = None
    if abs(ch) >= 1:
        loai = "TT_CHI" if ch > 0 else "TT_THU"
        no, _, co, _ = CT.dinh_khoan(loai, company="EPL", section="travel", tien_te="LAK", phuong_thuc=phuong_thuc)
        dg = "Tất toán tạm ứng kỳ %s · %s · đã chi thật %s − đã ứng %s → %s" % (
            thang, ten_tx, format(chi, ","), format(ung, ","), "công ty chi bù" if ch > 0 else "tài xế nộp lại")
        rec = PhieuTienTune(nguon=NGUON_TT, ma_nguon=ma, loai=loai, voucher_type=LOAI[loai][0], doi_tuong_loai="tai_xe",
                            doi_tuong_id=driver_id, doi_tuong_ten=t.name, period=ky, currency="LAK", amount=abs(ch), amount_lak=abs(ch),
                            phuong_thuc=phuong_thuc, ref_no="TTX-%s-%s" % (ky.replace("-", ""), x.id[:8]), no=no, co=co,
                            chi_tiet=json.dumps({"dien_giai": dg, "so_phieu": k["so_phieu"], "tong_ung_lak": ung, "tong_chi_lak": chi,
                                                 "phieu": [p["doc_no"] for p in k.get("phieu") or []]}, ensure_ascii=False),
                            status="loi", created_by=_ten(user))
        db.add(rec)
    db.commit()
    if rec is not None:
        try:
            gui(db, rec, user)
        except HTTPException:
            pass            # lỗi đã ghi lên bản ghi; bản chốt giữ — "gửi lại" khi bên kế toán nhận được
    return mot(db, driver_id, ky, cap_nhat=False)


def bo_chot(db, user, driver_id, ky):
    """Bỏ chốt để sửa lại: phiếu bên kế toán chưa ghi sổ thì bỏ bên đó, bút toán QT_TU chưa gửi thì rút. Đã chi / đã gửi → 409."""
    from routes import tat_toan as TT
    x = _ban_chot(db, driver_id, TT._ky_hop_le(ky))
    if x is None:
        _loi("KHONG_THAY", "Kỳ %s của tài xế này chưa tất toán." % ky, 404)
    rec, bt = _phieu_tt(db, x), _but_toan_tt(db, x)
    _hoi_truoc_khi_rut(db, rec)
    if rec is not None and rec.status == "da_chi":
        _loi("DA_CHI_O_KE_TOAN", "Phiếu %s bên hệ kế toán đã ghi sổ (tiền đã đi) — không bỏ chốt được ở đây, đối soát ở hệ kế toán "
                                 "trước." % (rec.document_no or rec.real_id), 409)
    if bt is not None and bt.status == "da_gui":             # chặn TRƯỚC khi đụng phiếu bên kế toán
        _btc().rut(db, NGUON_TT, ma_nguon_tt(x), by_user=_ten(user))           # → 409 BUT_TOAN_DA_GUI
    try:
        if rec is not None and rec.status != "huy":
            _rut_ben_ke_toan(db, rec)
        if bt is not None:
            _btc().rut(db, NGUON_TT, ma_nguon_tt(x), by_user=_ten(user))
        db.delete(x)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    return {"ok": True, "driver_id": driver_id, "period": ky}


def viec_tt(db, user, driver_id, ky, viec):
    """cap-nhat (hỏi lại hệ kế toán) · gui-lai (lần gửi trước hỏng)."""
    from routes import tat_toan as TT
    x = _ban_chot(db, driver_id, TT._ky_hop_le(ky))
    if x is None:
        _loi("KHONG_THAY", "Kỳ %s của tài xế này chưa tất toán." % ky, 404)
    rec = _phieu_tt(db, x)
    if rec is None:
        _loi("KHONG_CO_PHIEU", "Kỳ này chênh dưới 1 Kíp — không có phiếu chi / thu bên kế toán.", 409)
    if viec == "cap-nhat":
        dong_bo(db, rec)
    elif viec == "gui-lai":
        if rec.status != "loi":
            _loi("KHONG_GUI_LAI", "Phiếu tất toán đang %s — không gửi lại." % rec.status, 409)
        try:
            gui(db, rec, user)
        except HTTPException:
            pass
    else:
        _loi("KHONG_THAY", "Không có việc %s." % viec, 404)
    return mot(db, driver_id, ky, cap_nhat=False)


# ================================================================ trả nhà cung cấp
def _tra_theo_ncc(db, sids=None):
    """{supplier_id: [đã chi LAK, đang chờ chi LAK]} từ các đề nghị trả bên kế toán."""
    q = (db.query(PhieuTienTune.doi_tuong_id, PhieuTienTune.status, func.sum(PhieuTienTune.amount_lak))
         .filter(PhieuTienTune.nguon == NGUON_NCC, PhieuTienTune.status.in_(("da_gui", "da_chi"))))
    if sids is not None:
        q = q.filter(PhieuTienTune.doi_tuong_id.in_(list(sids) or [""]))
    ra = {}
    for sid, st, t in q.group_by(PhieuTienTune.doi_tuong_id, PhieuTienTune.status):
        o = ra.setdefault(sid, [0.0, 0.0])
        o[0 if st == "da_chi" else 1] += float(t or 0)
    return ra


def _ghep_ncc(r, tra):
    da, cho = tra.get(r["id"], (0.0, 0.0))
    r["da_tra_lak"], r["cho_chi_lak"] = round(da), round(cho)
    r["con_no_lak"] = round(r["phat_sinh_lak"] - da - cho)            # phát sinh từ phiếu − đã chi − đang chờ chi
    return r


def ds_cong_no(db):
    """Theo dõi nhà cung cấp: danh mục + phát sinh / ghi nợ từ phiếu (routes/nha_cung_cap) + đã trả, chờ chi, còn nợ."""
    from routes import nha_cung_cap as NCC
    tra = _tra_theo_ncc(db)
    return [_ghep_ncc(r, tra) for r in NCC.ds_tien(db)]


def cong_no_ncc(db, s):
    from routes import nha_cung_cap as NCC
    return _ghep_ncc(NCC._xuat(db, s, kem_tien=True), _tra_theo_ncc(db, [s.id]))


def _ncc(db, sid):
    s = db.get(Supplier, sid)
    if s is None:
        _loi("KHONG_THAY", "Không có nhà cung cấp này.", 404)
    return s


def cua_ncc(db, sid, hoi_lai=True):
    """Màn trả một nhà cung cấp: công nợ + các lần đề nghị trả (mới trước); đề nghị đang chờ thì hỏi lại hệ kế toán."""
    s = _ncc(db, sid)
    ds = (db.query(PhieuTienTune).filter(PhieuTienTune.nguon == NGUON_NCC, PhieuTienTune.doi_tuong_id == sid)
          .order_by(PhieuTienTune.created_at.desc()).limit(50).all())
    if hoi_lai:
        for r in [r for r in ds if r.status == "da_gui"]:
            try:
                dong_bo(db, r)
            except HTTPException:
                break
    return {"ncc": cong_no_ncc(db, s), "de_nghi": [xuat(r) for r in ds], "o_ke_toan": True}


def _so(v, ten):
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        _loi("SO_SAI", "Ô %s phải là số, nhận '%s'." % (ten, v))
    if not x > 0:
        _loi("SO_SAI", "Ô %s phải lớn hơn 0." % ten)
    return x


def de_nghi_tra_ncc(db, user, sid, d):
    """{so_tien, tien_te?: LAK, ty_gia?, phuong_thuc: cash|bank, ghi_chu?, xac_nhan?} → phiếu chi "Chi khác" bên kế toán (chưa
    ghi sổ), Nợ 4021 / Có tiền, đứng tên nhà cung cấp. Trả theo đợt nên số gõ tay; vượt số còn nợ thì phải xác nhận (trừ nhà
    cung cấp trả trước — nạp thẻ)."""
    from services.tinh_toan import TIEN_TE, lam_tron
    s = _ncc(db, sid)
    phuong_thuc = (d.get("phuong_thuc") or "cash").strip()
    if phuong_thuc not in CACH_TRA:
        _loi("CACH_TRA_SAI", "Cách trả phải là tiền mặt (cash) hoặc chuyển khoản (bank).")
    ccy = (d.get("tien_te") or "LAK").strip().upper()
    if ccy not in TIEN_TE:
        _loi("TIEN_TE_SAI", "Tiền trả phải là một trong %s." % ", ".join(TIEN_TE))
    tien = lam_tron(_so(d.get("so_tien"), "số tiền"), ccy)
    if ccy == "LAK":
        ty = 1.0
    elif d.get("ty_gia") not in (None, ""):
        ty = _so(d.get("ty_gia"), "tỷ giá")
    else:
        r = db.get(ExchangeRate, ccy)
        ty = float(r.rate_to_lak) if r is not None and r.rate_to_lak else None
        if not ty:
            _loi("TY_GIA_SAI", "Chưa có tỷ giá %s → LAK — gõ tỷ giá của lần trả." % ccy)
    lak = round(tien * ty)
    no_ = cong_no_ncc(db, s)
    if lak > no_["con_no_lak"] + 1 and s.payment_term != "t_prepaid" and not d.get("xac_nhan"):
        _loi("TRA_QUA_NO", "Số trả %s LAK vượt số còn nợ %s LAK của %s (đã trừ phần đang chờ chi) — kiểm lại, hoặc xác nhận trả "
                           "trước." % (format(lak, ","), format(no_["con_no_lak"], ","), s.name), 409, con_no_lak=no_["con_no_lak"])
    ghi_chu = (d.get("ghi_chu") or d.get("note") or "").strip() or None
    no, _, co, _ = CT.dinh_khoan("PC_NCC", tien_te=ccy, phuong_thuc=phuong_thuc)
    now = dt.datetime.utcnow()
    so = "TNCC-%s-%s" % (now.strftime("%y%m%d%H%M%S"), sid[:4])
    dg = "Trả nhà cung cấp %s%s" % (s.name, (" · " + ghi_chu) if ghi_chu else "")
    rec = PhieuTienTune(nguon=NGUON_NCC, ma_nguon=so, loai="PC_NCC", voucher_type=LOAI["PC_NCC"][0], doi_tuong_loai="ncc",
                        doi_tuong_id=s.id, doi_tuong_ten=s.name, currency=ccy, amount=tien, amount_lak=lak, phuong_thuc=phuong_thuc,
                        ref_no=so, no=no, co=co, status="loi", created_by=_ten(user),
                        chi_tiet=json.dumps({"dien_giai": dg, "ghi_chu": ghi_chu, "ty_gia": ty, "con_no_truoc_lak": no_["con_no_lak"],
                                             "item_key": s.item_key, "acct_code": s.acct_code}, ensure_ascii=False))
    db.add(rec)
    db.commit()
    try:
        gui(db, rec, user)
    except HTTPException:
        pass                # lỗi nằm trên đề nghị (status loi) — màn hiện câu lỗi, bấm gửi lại
    return rec


def _ban_ghi_ncc(db, rid):
    r = db.get(PhieuTienTune, rid)
    if r is None or r.nguon != NGUON_NCC:
        _loi("KHONG_THAY", "Không có đề nghị trả nhà cung cấp này.", 404)
    return r


def viec_ncc(db, user, rid, viec):
    """cap-nhat (hỏi lại hệ kế toán) · gui-lai (lần trước hỏng) · huy (bỏ đề nghị chưa chi, rút phiếu chi bên đó)."""
    r = _ban_ghi_ncc(db, rid)
    if viec == "cap-nhat":
        dong_bo(db, r)
    elif viec == "gui-lai":
        if r.status != "loi":
            _loi("KHONG_GUI_LAI", "Đề nghị này đang %s — không gửi lại." % r.status, 409)
        try:
            gui(db, r, user)
        except HTTPException:
            pass
    elif viec == "huy":
        if r.status == "huy":
            return r
        _hoi_truoc_khi_rut(db, r)
        try:
            _rut_ben_ke_toan(db, r)
            db.commit()
        except HTTPException:
            db.rollback()
            raise
    else:
        _loi("KHONG_THAY", "Không có việc %s." % viec, 404)
    return r
