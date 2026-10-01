# -*- coding: utf-8 -*-
"""CHI MỤC V–VI ở hệ kế toán anh Tune — chủ dự án chốt 01/10/2026: bỏ trang kế toán tạm, khoản đi qua tiền thành phiếu chi bên
anh Tune. Thay tờ PC_SC ("Phiếu chi sửa chữa · chi khác") mà trước đây Quỹ tiền mặt bấm "Chi" trên trang điều xe rồi trang tạm
kéo về.

Luồng (cùng khuôn tạm ứng — services/chi_tune.py):
  1. KT Chi phí VC kiểm, GHI SỔ mục V (sửa chữa) hoặc VI (chi khác) trên trang điều xe.
  2. Ghi sổ xong → bên em tạo PHIẾU CHI "Chi khác" (DOTY 60) bên anh Tune, CHƯA ghi sổ (PostMode None), cho đúng các dòng QUỸ
     TRẢ NGAY của mục (`dong_quy_chi`). Đối tượng: xe nhà → tài xế; xe thuê → chủ xe (`chi_tune.doi_tuong_phieu`). Định khoản
     theo bảng của bên em `chung_tu.dinh_khoan("PC_SC")`: xe nhà Nợ 614 (V) · 625 (VI) / Có 1011; xe thuê Nợ 4022 / Có 1011.
  3. Thủ quỹ chi tiền và GHI SỔ phiếu đó ở hệ anh Tune.
  4. Bên em đọc lại: `Master.STATUS` 12 / 13 → mục "đã chi". Hỏi lại lúc mở phiếu (cap_nhat), lúc Quỹ bấm Chi, nút Cập nhật.

Dòng QUỸ TRẢ NGAY (giữ đúng luật rà định khoản 30/09 của tờ PC_SC cũ): mục V, EPL chịu, mua ngoài (không lấy kho), không phải
tiền mặt tài xế cầm đi theo tờ tạm ứng, không ghi nợ trạm / nhà cung cấp, không trừ thẻ, và không phải khoản mục Theo dõi nhà
cung cấp đã tính là nợ NCC. Mục VI không có dòng nào như thế (mỗi dòng hoặc tiền mặt theo tờ tạm ứng, hoặc trả cùng lương, hoặc
ghi nợ nhà cung cấp) — mục VI không có tiền quỹ chi thì không lập phiếu, Quỹ bấm Chi trên trang điều xe như cũ. Các dòng ghi nợ
nhà cung cấp vào sổ bằng BÚT TOÁN CHỜ lúc khoá phiếu (services/but_toan_cho.py), không qua đây.

Mục mở lại (báo hỏng mới, Sếp mở khoá mục) → phiếu chi CHƯA ghi sổ bị rút bên đó; ghi sổ lại thì lập phiếu theo dòng mới. Dòng đã
nằm trong phiếu bên đó đã ghi sổ thì không vào phiếu sau (`lan` kế tiếp chỉ mang dòng mới) — tiền đã chi thì không chi lại.

API phiếu chi không có Idempotency-Key: trước mỗi lần tạo, tìm phiếu cùng đối tượng + số tham chiếu (`ref_no`) — có thì dùng
lại. Gọi hàm có sẵn của chi_tune (_goi, ma_tien, ma_ky, doi_tuong_phieu, _tim_phieu_da_co) — một chỗ nói chuyện với bên đó.
"""
import datetime as dt
import json
import time

from fastapi import HTTPException

from models import ChiMucTune, Trip, TripExpense, TripLog, TripSection
from services import chi_tune as CHI
from services import chung_tu as CT
from services.tinh_toan import la_tien_mat_tai_xe, tien_dong

MUC = ("repair", "other")
TEN_MUC = {"repair": "V", "other": "VI"}
TEN_MUC_VI = {"repair": "V sửa chữa", "other": "VI chi khác"}
CAU_CHI_O_KE_TOAN = ("Chi mục %s ở hệ kế toán (chủ dự án 01/10): thủ quỹ chi tiền và ghi sổ phiếu chi \"Chi khác\" bên đó, "
                     "trang này tự ghi \"đã chi\".")


def _loi(ma, loi, http=422):
    raise HTTPException(http, {"ma": ma, "loi": loi})


def _dong_phieu(db, p):
    return (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())


def dong_quy_chi(db, p, muc, cac_dong=None):
    """Các dòng của mục `muc` mà QUỸ TRẢ NGAY bằng tiền mặt — đúng tập dòng tờ PC_SC cũ (rà định khoản 30/09)."""
    if muc != "repair":
        return []                                   # mục VI: không có dòng quỹ trả ngay (xem đầu tệp)
    from routes.nha_cung_cap import khoan_muc_ncc
    ncc = khoan_muc_ncc(db)
    cac_dong = cac_dong if cac_dong is not None else _dong_phieu(db, p)
    return [d for d in cac_dong if d.section == muc and d.paid_by_epl and d.source != "kho"
            and not la_tien_mat_tai_xe(d, p.company) and not d.ghi_no and not d.toll_card_id
            and not (d.supplier_id is None and d.item_key in ncc)]


def _lak(p, d):
    return round(tien_dong(p, d))


def cac_lan(db, trip_id, muc=None):
    q = db.query(ChiMucTune).filter(ChiMucTune.trip_id == trip_id)
    if muc:
        q = q.filter(ChiMucTune.section == muc)
    return q.order_by(ChiMucTune.section, ChiMucTune.lan).all()


def _ids(rec):
    try:
        return set(json.loads(rec.expense_ids or "[]"))
    except ValueError:
        return set()


def con_phai_chi(db, p, muc, cac_dong=None, recs=None):
    """Dòng quỹ trả ngay CHƯA nằm trong phiếu chi nào bên kế toán đã ghi sổ (tiền > 0)."""
    recs = recs if recs is not None else cac_lan(db, p.id, muc)
    da = set().union(*[_ids(r) for r in recs if r.status == "da_chi"]) if recs else set()
    return [d for d in dong_quy_chi(db, p, muc, cac_dong) if d.id not in da and _lak(p, d) > 0]


def _so_de_nghi(p, muc, lan):
    return ("PCSC-%s-%s-%d" % (TEN_MUC[muc], p.doc_no, lan))[:64]


def dung_goi(db, p, muc, rec, dong, obj):
    """Gói phiếu chi "Chi khác" (CMP) cho các dòng `dong` của mục `muc`. Tiền Kíp — dòng VND / THB quy theo tỷ giá khoá trên phiếu."""
    tien = sum(_lak(p, d) for d in dong)
    if tien <= 0:
        _loi("CHI_MUC_BANG_KHONG", "Mục %s phiếu %s không còn khoản quỹ trả ngay — không lập phiếu chi." % (TEN_MUC[muc], p.doc_no), 409)
    no, _, co, _ = CT.dinh_khoan("PC_SC", company=p.company, section=muc, tien_te="LAK", phuong_thuc="cash")
    if not no or not co:
        _loi("THIEU_DINH_KHOAN", "Chưa có định khoản cho phiếu chi mục %s (%s / %s)." % (TEN_MUC[muc], no, co))
    lak, hom_nay = CHI.ma_tien("LAK"), dt.date.today()
    mo_ta = "Chi mục %s phiếu %s · xe %s · %s" % (TEN_MUC_VI[muc], p.doc_no, p.truck_no or "—", p.driver_name or "—")
    if p.company == "joint":
        mo_ta += " · xe thuê của %s" % (p.owner_name or "—")
    return {
        "TmpId": 0, "RealId": 0, "VoucherType": "CMP", "SessionId": "epllao-sc-%s-%d" % (rec.id, int(time.time())), "PostMode": "None",
        "Header": {"CountryId": CHI._cfg("QLSX_COUNTRY_ID", 11), "OrgId": CHI._cfg("QLSX_ORG_ID", 1368), "FiciAutoId": CHI.ma_ky(hom_nay),
                   "DotyAutoId": CHI._cfg("QLSX_DOTY_CHI_KHAC", CHI._cfg("QLSX_DOTY_TRA_CHU_XE", 60)), "ObjectId": obj, "CurrencyId": lak,
                   "DocumentDate": hom_nay.isoformat(), "RefDocumentNo": rec.ref_no, "Description": mo_ta[:250],
                   "IsCash": True, "IsLocal": True, "IsDirect": True, "ExchangeRate": 1, "Amount": tien, "BaseAmount": tien,
                   "ContactName": ((p.owner_name if p.company == "joint" else p.driver_name) or "")[:100] or None},
        "Relations": [],
        "Entries": [{"SourceLineKey": "EPLLAO:%s:%s" % (p.id, d.id), "ObjectId": obj, "CurrencyId": lak, "DebitAccount": no,
                     "CreditAccount": co, "Amount": _lak(p, d), "BaseAmount": _lak(p, d), "ExchangeRate": 1, "EntryTypeId": 11,
                     "Description": ("Mục %s · %s · %s × %s %s" % (TEN_MUC[muc], d.item_name or d.item_key or "—", _so(d.qty),
                                                                    _so(d.unit_price), d.currency or "LAK"))[:250],
                     "ValidateMoney": True} for d in dong],
    }


def _so(v):
    v = float(v or 0)
    return ("%d" % v) if v == int(v) else ("%g" % v)


def _ghi_nhat_ky(db, p, ten, vai, viec):
    db.add(TripLog(trip_id=p.id, user_name=ten, role=vai, action=viec))


def ap_da_chi(db, p, muc, recs=None):
    """Mục đang "đã ghi sổ", mọi khoản quỹ trả ngay đã nằm trong phiếu chi bên kế toán ĐÃ GHI SỔ, không còn phiếu chờ → "đã chi"."""
    recs = recs if recs is not None else cac_lan(db, p.id, muc)
    s = db.query(TripSection).filter(TripSection.trip_id == p.id, TripSection.section == muc).first()
    if s is None or s.status != "booked":
        return False
    if any(r.status in ("da_gui", "loi") for r in recs) or not any(r.status == "da_chi" for r in recs):
        return False
    if con_phai_chi(db, p, muc, recs=recs):
        return False
    cuoi = max((r for r in recs if r.status == "da_chi"), key=lambda r: r.lan)
    s.status = "paid"
    _ghi_nhat_ky(db, p, "%s (hệ kế toán)" % (cuoi.post_by or "thủ quỹ"), "cash", "sec_%s:pay" % muc)
    return True


def dong_bo(db, rec, p=None):
    """Đọc lại phiếu bên kế toán; đã ghi sổ thì đánh da_chi và (nếu đủ) mục "đã chi". Trả rec. Lỗi mạng: giữ nguyên, ném."""
    if rec is None or rec.status != "da_gui" or not rec.real_id:
        return rec
    p = p or db.get(Trip, rec.trip_id)
    m = CHI.doc_phieu(db, rec)          # phiếu bên đó đã bị xoá (Master null) → PHIEU_CHI_MAT, không kẹt "chờ chi"
    if m is None:
        return rec
    rec.checked_at = dt.datetime.utcnow()
    rec.document_no = m.get("DOCUMENTNO") or rec.document_no
    rec.tune_status = int(m.get("STATUS") or 0)
    if rec.tune_status in CHI.DA_GHI_SO:
        rec.status, rec.post_by, rec.post_at = "da_chi", m.get("POSTNAME") or None, CHI._ngay_gio(m.get("POSTDATE"))
        rec.error_code = rec.error_message = None
        db.flush()
        if p is not None:
            ap_da_chi(db, p, rec.section)
    db.commit()
    return rec


def _xoa_ben_kia(rec):
    if rec.real_id and rec.error_code != CHI.MAT:      # phiếu bên đó đã mất thì coi như đã rút xong
        CHI._goi("POST", "/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(rec.real_id), "VoucherType": "CMP"})


def gui(db, p, muc, user):
    """Tạo (hoặc dùng lại) phiếu chi bên kế toán cho các khoản quỹ trả ngay CÒN PHẢI CHI của mục. Ghi kết quả — kể cả khi hỏng —
    rồi mới trả / ném. Không còn khoản nào: rút phiếu chờ (nếu có), trả None."""
    if muc not in MUC:
        _loi("MUC_SAI", "Chi ở hệ kế toán chỉ cho mục V, VI (nhận %s)." % muc)
    recs = cac_lan(db, p.id, muc)
    for r in recs:
        if r.status == "da_gui":
            try:
                dong_bo(db, r, p)
            except HTTPException:
                pass
    con = con_phai_chi(db, p, muc, recs=recs)
    cho = [r for r in recs if r.status in ("da_gui", "loi")]
    if not con:
        for r in cho:                                   # dòng không còn là khoản quỹ trả: bỏ phiếu chờ bên kia
            _xoa_ben_kia(r)
            r.status = "huy"
        ap_da_chi(db, p, muc, recs)
        db.commit()
        return None
    rec = cho[-1] if cho else None
    for r in cho[:-1]:
        _xoa_ben_kia(r)
        r.status = "huy"
    now = dt.datetime.utcnow()
    if rec is None:
        lan = max((r.lan for r in recs), default=0) + 1
        rec = ChiMucTune(trip_id=p.id, section=muc, lan=lan, ref_no=_so_de_nghi(p, muc, lan), expense_ids="[]",
                         status="loi", attempts=0)
        db.add(rec)
        db.flush()
    rec.attempts, rec.last_attempt_at, rec.sent_by = (rec.attempts or 0) + 1, now, getattr(user, "full_name", None)
    try:
        obj = rec.obj_id = CHI.doi_tuong_phieu(db, p)
        da_co = CHI._tim_phieu_da_co(obj, rec.ref_no)
        if any(int(x.get("ST_AUTOID") or 0) in CHI.DA_GHI_SO for x in da_co):
            # lần trước tưởng hỏng mà bên kia đã lưu VÀ thủ quỹ đã ghi sổ: nhận là đã chi theo dòng cũ, khoản mới sang lần sau
            x = next(x for x in da_co if int(x.get("ST_AUTOID") or 0) in CHI.DA_GHI_SO)
            rec.real_id, rec.document_no, rec.status = int(x["DOC_DOCUMENTID"]), x.get("DOC_DOCUMENTNO"), "da_gui"
            db.commit()
            dong_bo(db, rec, p)
            if rec.status != "da_chi":
                _loi("PHIEU_CHI_LECH", "Phiếu chi %s bên kế toán báo đã ghi sổ trong danh sách nhưng đọc lại thì chưa — đối soát bên đó."
                     % (rec.document_no or rec.real_id), 409)
            return gui(db, p, muc, user)
        body = dung_goi(db, p, muc, rec, con, obj)
        rec.expense_ids = json.dumps([d.id for d in con])
        rec.amount_lak, rec.request_body = body["Header"]["Amount"], json.dumps(body, ensure_ascii=False)
        dung_lai = None
        for x in da_co:
            if abs(float(x.get("CM_AMOUNT") or 0) - rec.amount_lak) < 0.5 and dung_lai is None:
                dung_lai = x
            else:                                       # số đổi khi phiếu bên kia chưa ghi sổ: bỏ phiếu cũ, lập phiếu đúng số
                CHI._goi("POST", "/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(x["DOC_DOCUMENTID"]), "VoucherType": "CMP"})
        if dung_lai is not None:
            rec.real_id, rec.document_no = int(dung_lai["DOC_DOCUMENTID"]), dung_lai.get("DOC_DOCUMENTNO")
            rec.response_body = json.dumps({"dung_lai": dung_lai}, ensure_ascii=False, default=str)[:20000]
        else:
            kq = CHI._goi("POST", "/api/v1/accounting/cmpayment-receipt/save-and-commit", body) or {}
            rec.response_body = json.dumps(kq, ensure_ascii=False, default=str)[:20000]
            if not kq.get("RealId"):
                _loi("KHONG_CO_REALID", "Hệ kế toán không trả số phiếu chi: %s" % (kq.get("Message") or ""), 502)
            rec.real_id = int(kq["RealId"])
        rec.status, rec.error_code, rec.error_message = "da_gui", None, None
        db.commit()
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {}
        rec.status, rec.error_code, rec.error_message = "loi", d.get("ma"), d.get("loi") or str(e.detail)
        db.commit()
        raise
    try:
        dong_bo(db, rec, p)                             # lấy số phiếu bên đó; có khi thủ quỹ đã ghi sổ ngay
    except HTTPException:
        pass
    return rec


def gui_sau_ghi_so(db, p, muc, user):
    """Gọi sau khi KT Chi phí ghi sổ mục V / VI. Không có khoản quỹ trả ngay thì thôi. Hỏng thì lỗi nằm trên bản ghi — ghi sổ mục
    vẫn giữ; KT Chi phí gửi lại ở màn Phiếu đề nghị chi."""
    if not CHI.chi_o_ke_toan() or muc not in MUC:
        return None
    if not con_phai_chi(db, p, muc) and not any(r.status in ("da_gui", "loi") for r in cac_lan(db, p.id, muc)):
        return None
    try:
        return gui(db, p, muc, user)
    except HTTPException:
        return next(iter(r for r in reversed(cac_lan(db, p.id, muc)) if r.status in ("da_gui", "loi")), None)


def cua_phieu(db, p, muc=None, cap_nhat=False):
    """Các lần chi mục V / VI bên kế toán của phiếu; `cap_nhat` → hỏi lại bên đó bản đang chờ."""
    recs = cac_lan(db, p.id, muc)
    if cap_nhat:
        for r in recs:
            if r.status == "da_gui":
                try:
                    dong_bo(db, r, p)
                except HTTPException:
                    break                               # bên kia không vào được: không gọi tiếp
    return recs


def rut_cho(db, p, muc):
    """Mục mở lại (có dòng mới / Sếp mở khoá mục): phiếu chi CHƯA ghi sổ bên kia rút đi — không để thủ quỹ chi theo số đang được
    kiểm lại. Đã ghi sổ thì giữ (tiền đã chi). Không gọi được bên kia thì để nguyên, lần ghi sổ sau tự xử lý."""
    for r in cac_lan(db, p.id, muc):
        if r.status not in ("da_gui", "loi"):
            continue
        try:
            if r.status == "da_gui":
                dong_bo(db, r, p)
            if r.status in ("da_gui", "loi"):
                _xoa_ben_kia(r)
                r.status = "huy"
        except HTTPException:
            continue
    db.flush()


def rut(db, trip_id):
    """Phiếu bên em bị xoá: phiếu chi CHƯA ghi sổ bên kia thì xoá bên đó và bỏ bản ghi; đã ghi sổ (tiền đã chi) → chặn 409, đối
    soát ở hệ kế toán trước. Không gọi được bên kia thì cũng chặn — không để phiếu chi mồ côi chờ thủ quỹ chi."""
    for r in cac_lan(db, trip_id):
        if r.status == "da_gui" and r.real_id:
            try:
                dong_bo(db, r)
            except HTTPException:
                if r.error_code != CHI.MAT:
                    raise
        if r.status == "da_chi":
            _loi("DA_CHI_O_KE_TOAN", "Phiếu chi mục %s %s bên hệ kế toán đã ghi sổ (tiền đã chi) — không xoá được ở đây, đối soát ở hệ "
                                     "kế toán trước." % (TEN_MUC.get(r.section, r.section), r.document_no or r.real_id), 409)
        if r.status != "huy":
            _xoa_ben_kia(r)
        db.delete(r)
    db.flush()


def cau_chan_chi(db, p, muc, recs=None):
    """Câu báo khi Quỹ bấm Chi mục V / VI trên trang điều xe lúc khoản đó chi ở hệ kế toán — kèm số phiếu chi bên đó nếu có."""
    recs = recs if recs is not None else cac_lan(db, p.id, muc)
    cho = [r for r in recs if r.status in ("da_gui", "loi")]
    cau = CAU_CHI_O_KE_TOAN % TEN_MUC.get(muc, muc)
    if cho and cho[-1].real_id:
        return cau + " Phiếu chi bên đó: %s." % (cho[-1].document_no or cho[-1].real_id)
    if cho:
        return cau + " Chưa tạo được phiếu chi bên đó (%s) — KT Chi phí gửi lại ở màn Phiếu đề nghị chi." % (
            cho[-1].error_message or cho[-1].error_code)
    return cau + " Phiếu chi chưa sang bên đó — KT Chi phí gửi ở màn Phiếu đề nghị chi."


def xuat(rec, thay_tien=True):
    if rec is None:
        return None
    return {"id": rec.id, "section": rec.section, "lan": rec.lan, "ref_no": rec.ref_no, "status": rec.status,
            "document_no": rec.document_no, "real_id": rec.real_id, "tune_status": rec.tune_status, "obj_id": rec.obj_id,
            "expense_ids": sorted(_ids(rec)), "amount_lak": rec.amount_lak if thay_tien else None, "post_by": rec.post_by,
            "post_at": rec.post_at.isoformat(timespec="minutes") + "+00:00" if rec.post_at else None,
            "error_code": rec.error_code, "error_message": rec.error_message, "attempts": rec.attempts, "sent_by": rec.sent_by,
            "last_attempt_at": rec.last_attempt_at.isoformat(timespec="minutes") if rec.last_attempt_at else None,
            "checked_at": rec.checked_at.isoformat(timespec="minutes") if rec.checked_at else None}


def tom_tat(db, p, muc, recs=None, cac_dong=None, thay_tien=True):
    """Trạng thái chi mục ở hệ kế toán cho màn hình: các lần, phần quỹ trả ngay, phần còn phải chi."""
    recs = recs if recs is not None else cac_lan(db, p.id, muc)
    quy = dong_quy_chi(db, p, muc, cac_dong)
    con = con_phai_chi(db, p, muc, cac_dong, recs)
    ra = {"o_ke_toan": CHI.chi_o_ke_toan(), "lan": [xuat(r, thay_tien) for r in recs], "so_dong_quy": len(quy),
          "so_dong_con": len(con), "can_chi": bool(quy)}
    if thay_tien:
        ra.update({"tien_quy_lak": sum(_lak(p, d) for d in quy), "tien_con_lak": sum(_lak(p, d) for d in con)})
    return ra
