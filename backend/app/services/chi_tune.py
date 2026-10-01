# -*- coding: utf-8 -*-
"""CHI TẠM ỨNG ở hệ kế toán anh Tune — chủ dự án chốt 01/10/2026: "chi thật là anh Tune xong update trạng thái về bên mình".

Luồng:
  1. Bãi lập phiếu, in tờ đề nghị tạm ứng (PTU). KT Chi phí VC kiểm, GHI SỔ mục IV trên trang điều xe.
  2. Ghi sổ xong → bên em tạo PHIẾU CHI bên anh Tune: loại "Chi trước" (DOTY 59), đối tượng = tài xế, Nợ/Có theo bảng định
     khoản của bên em (`chung_tu.dinh_khoan("PC_TU")`: xe nhà Nợ 1601 / Có 1011), CHƯA ghi sổ (PostMode None).
  3. Thủ quỹ chi tiền cho tài xế và GHI SỔ phiếu đó ngay trong hệ anh Tune.
  4. Bên em đọc lại phiếu: `Master.STATUS` 12 (ghi sổ chính) hoặc 13 (ghi sổ tạm) là ĐÃ CHI → mục IV "đã chi", tờ PTU
     "đã cấp", tài xế mới xuất phát. Trang điều xe chưa ra Internet nên bên em HỎI LẠI (lúc mở tờ, lúc bấm Xuất phát, nút
     Cập nhật), không chờ bên kia gọi sang.

Đường bên anh Tune (đã thử thật trên API chạy ở máy, DB demo Lào, 01/10):
    POST /api/v1/accounting/cmpayment-receipt/save-and-commit     tạo phiếu chính, trả RealId
    GET  /api/v1/accounting/cmpayment-receipt/{id}?voucherType=CMP đọc Master (DOCUMENTNO, STATUS, POSTNAME, POSTDATE)
    POST /api/v1/accounting/cmpayment-receipt/list                 chống trùng: theo đối tượng + DOC_REFDOCUMENTNO = số PTU
    POST /api/v1/accounting/cmpayment-receipt/delete               bỏ phiếu CHƯA ghi sổ khi số tạm ứng đổi
    POST /api/v1/master-data/staff/list · staff/upsert              đối tượng tài xế (`EPLTX-<Driver.id>`)
    GET  /api/v1/common/GetAllCurrency · GetFinancyCicle           mã tiền, mã kỳ — tra theo tên / ngày, không ghi cứng

Điều phải giữ:
  * API phiếu chi KHÔNG có Idempotency-Key. Trước mỗi lần tạo, tìm phiếu đã có cùng đối tượng + số PTU — có thì dùng lại,
    không tạo trùng (mất mạng giữa chừng không có nghĩa là bên đó chưa lưu).
  * Lỗi có thể về HTTP 200 kèm `Success: false` — đọc thân.
  * Phiếu bên đó đã ghi sổ thì bên em không xoá, không sửa: số tạm ứng đổi sau đó thì phần chênh tính lúc tất toán tài xế.
  * Token, gốc API dùng chung với `gui_tune.cau_hinh()`; thử local thì đặt QLSX_BASE_URL=http://127.0.0.1:5090.
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from fastapi import HTTPException

from models import ChiTune, DoiTuongTune, Driver, TripLog, TripSection, Voucher
from services import chung_tu as CT
from services import gui_tune as GT

CHO_GIAY = 40
DA_GHI_SO = (12, 13)                      # CMPaymentReceiptConstants.PostedFinalStatus / PostedTempStatus
_BO_NHO = {}                              # mã tiền, kỳ — 10 phút
CAU_CHI_O_KE_TOAN = ("Tạm ứng chi ở hệ kế toán (chủ dự án 01/10): thủ quỹ chi tiền và ghi sổ phiếu chi tạm ứng bên đó, "
                     "trang này tự ghi \"đã chi\".")


def _cfg(ten, mac_dinh):
    v = (os.getenv(ten) or "").strip()
    return int(v) if v.isdigit() else mac_dinh


def chi_o_ke_toan():
    """True = tạm ứng chi ở hệ anh Tune (mặc định từ 01/10). `EPL_CHI_TAM_UNG=tai_cho` → Quỹ chi trên trang điều xe như cũ
    (dự phòng khi hệ kế toán chưa nối được)."""
    return (os.getenv("EPL_CHI_TAM_UNG") or "ke_toan").strip().lower() != "tai_cho"


def _loi(ma, loi, http=422):
    raise HTTPException(http, {"ma": ma, "loi": loi})


def _goi(method, duong, body=None):
    """→ Result của phong bì bên kia. Lỗi mạng / HTTP / Success=false → HTTPException nói rõ."""
    goc, token = GT.cau_hinh()
    if not token:
        _loi("CHUA_CO_TOKEN", "Chưa có token hệ kế toán (QLSX_ACCESS_TOKEN hoặc EPL_ACC_CODE_TOKEN trong .env).", 503)
    yc = urllib.request.Request(goc + duong, data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                method=method, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                                                        "Accept": "application/json", "User-Agent": "EPL-LAO-Logistics/1.0 (tam ung)"})
    try:
        with urllib.request.urlopen(yc, timeout=CHO_GIAY) as t:
            ma, tho = t.status, t.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        ma, tho = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                                          # noqa: BLE001 — mất mạng, DNS, hết giờ
        _loi("KHONG_GOI_DUOC", "Không gọi được hệ kế toán (%s): %s" % (urlsplit(goc).netloc, e), 502)
    try:
        than = json.loads(tho) if tho.strip() else None
    except ValueError:
        than = None
    if ma == 401 or (isinstance(than, dict) and than.get("Code") == 401):
        _loi("QLSX_TOKEN_HET_HAN", "Token hệ kế toán sai hoặc đã hết hạn — xin token mới, đặt QLSX_ACCESS_TOKEN.", 502)
    if isinstance(than, dict) and than.get("Success") is True:
        return than.get("Result")
    cau = (than or {}).get("Message") if isinstance(than, dict) else (tho or "")[:300]
    _loi("BEN_KE_TOAN_TU_CHOI", "Hệ kế toán trả HTTP %s: %s" % (ma, cau or "không rõ lý do"), 502 if ma >= 500 else 422)


def _nho(khoa, ham):
    v = _BO_NHO.get(khoa)
    if v and time.time() - v[0] < 600:
        return v[1]
    kq = ham()
    _BO_NHO[khoa] = (time.time(), kq)
    return kq


def ma_tien(ten="LAK"):
    ds = _nho("tien", lambda: _goi("GET", "/api/v1/common/GetAllCurrency") or [])
    ma = next((c.get("CUR_AUTOID") for c in ds if str(c.get("CUR_NAME") or "").upper() == ten), None)
    if not ma:
        _loi("THIEU_TIEN_TE", "Hệ kế toán chưa có tiền %s trong danh mục tiền tệ." % ten)
    return int(ma)


def ma_ky(ngay):
    """FICI_AUTOID của kỳ chứa `ngay` (kỳ còn mở). FiciAutoId là ID kỳ, không phải YYYYMM."""
    ds = _nho("ky", lambda: _goi("GET", "/api/v1/common/GetFinancyCicle") or [])
    d = ngay.isoformat()
    for k in ds:
        if str(k.get("FICI_DATEFROM") or "")[:10] <= d <= str(k.get("FICI_DATETO") or "")[:10] and k.get("FICI_ISACTIVE") is not False:
            if k.get("FICI_ISCLOSE"):
                _loi("KY_DA_DONG", "Kỳ %s bên hệ kế toán đã đóng — không lập phiếu chi được." % k.get("FICI_NAME"))
            return int(k["FICI_AUTOID"])
    _loi("THIEU_KY", "Hệ kế toán chưa có kỳ cho ngày %s." % d)


def doi_tuong_tai_xe(db, driver_id, ten):
    """OBJ_AUTOID bên kế toán của tài xế; chưa có thì tìm theo mã `EPLTX-<id>` (lần trước tạo rồi mà chưa kịp nhớ), không có
    nữa mới tạo nhân viên mới."""
    if not driver_id:
        _loi("THIEU_TAI_XE", "Phiếu chưa có tài xế — không lập phiếu chi tạm ứng được.", 409)
    r = db.get(DoiTuongTune, ("tai_xe", driver_id))
    if r is not None:
        return r.obj_id
    so = "EPLTX-" + driver_id
    tim = _goi("POST", "/api/v1/master-data/staff/list", {"PageIndex": 1, "ObjKey": so}) or {}
    oid = next((x.get("ObjId") for x in (tim.get("Data") or []) if x.get("ObjectNo") == so), None)
    if not oid:
        tx = db.get(Driver, driver_id)
        oid = _goi("POST", "/api/v1/master-data/staff/upsert", {
            "ObjectNo": so, "ObjectName": (ten or (tx.name if tx else "") or so)[:100],
            "CountryAutoId": _cfg("QLSX_COUNTRY_ID", 11), "ObjectOfOrganization": _cfg("QLSX_ORG_ID", 1368),
            "HandPhone": getattr(tx, "phone", None), "Description": "Tài xế trang điều xe EPL Lào"})
    if not oid:
        _loi("KHONG_TAO_DUOC_DOI_TUONG", "Hệ kế toán không trả mã đối tượng cho tài xế %s." % (ten or driver_id), 502)
    db.add(DoiTuongTune(loai="tai_xe", ref_id=driver_id, obj_id=int(oid), object_no=so))
    db.flush()
    return int(oid)


def dung_goi(db, p, v, obj):
    tien = round(v.amount_lak or 0)
    if tien <= 0:
        _loi("TAM_UNG_BANG_KHONG", "Tờ tạm ứng %s chưa có số tiền — KT Chi phí nhập giá mục IV trước." % v.doc_no, 409)
    no, _, co, _ = CT.dinh_khoan("PC_TU", company=p.company, section="travel", tien_te="LAK", phuong_thuc="cash")
    if not no or not co:
        _loi("THIEU_DINH_KHOAN", "Chưa có định khoản cho phiếu chi tạm ứng (%s / %s)." % (no, co))
    lak, hom_nay = ma_tien("LAK"), dt.date.today()
    mo_ta = "Tạm ứng chuyến %s · xe %s · %s" % (p.doc_no, p.truck_no or "—", p.driver_name or "—")
    if p.company == "joint":
        mo_ta += " · xe thuê của %s" % (p.owner_name or "—")
    return {
        "TmpId": 0, "RealId": 0, "VoucherType": "CMP", "SessionId": "epllao-%s-%d" % (v.id, int(time.time())), "PostMode": "None",
        "Header": {"CountryId": _cfg("QLSX_COUNTRY_ID", 11), "OrgId": _cfg("QLSX_ORG_ID", 1368), "FiciAutoId": ma_ky(hom_nay),
                   "DotyAutoId": _cfg("QLSX_DOTY_CHI_TAM_UNG", 59), "ObjectId": obj, "CurrencyId": lak,
                   "DocumentDate": hom_nay.isoformat(), "RefDocumentNo": v.doc_no, "Description": mo_ta[:250],
                   "IsCash": True, "IsLocal": True, "IsDirect": True, "ExchangeRate": 1, "Amount": tien, "BaseAmount": tien,
                   "ContactName": (p.driver_name or "")[:100] or None},
        "Relations": [],
        "Entries": [{"SourceLineKey": "EPLLAO:%s:PTU" % v.id, "ObjectId": obj, "CurrencyId": lak, "DebitAccount": no,
                     "CreditAccount": co, "Amount": tien, "BaseAmount": tien, "ExchangeRate": 1, "EntryTypeId": 11,
                     "Description": "Tạm ứng tiền mặt đi đường %s" % p.doc_no, "ValidateMoney": True}],
    }


def _tim_phieu_da_co(obj, so_ptu):
    """Phiếu chi bên kế toán đã có cho tờ PTU này (cùng đối tượng, cùng số tham chiếu) — chống tạo trùng."""
    hom_nay = dt.date.today()
    kq = _goi("POST", "/api/v1/accounting/cmpayment-receipt/list", {
        "PageIndex": 1, "PageSize": 50, "VoucherType": "CMP", "OrgAutoId": _cfg("QLSX_ORG_ID", 1368), "ObjectId": obj, "DateType": 0,
        "DateFrom": (hom_nay - dt.timedelta(days=45)).isoformat(), "DateTo": (hom_nay + dt.timedelta(days=1)).isoformat()}) or {}
    return [x for x in (kq.get("Rows") or []) if (x.get("DOC_REFDOCUMENTNO") or "") == so_ptu]


def _ghi_nhat_ky(db, p, ten, vai, viec):
    db.add(TripLog(trip_id=p.id, user_name=ten, role=vai, action=viec))


def _ap_da_chi(db, p, v, rec):
    """Bên kế toán đã ghi sổ → mục IV "đã chi", tờ PTU "đã cấp" (Tất toán đếm "đã ứng" theo tờ này)."""
    ai = "%s (hệ kế toán)" % (rec.post_by or "thủ quỹ")
    s = db.query(TripSection).filter(TripSection.trip_id == p.id, TripSection.section == "travel").first()
    if s is not None and s.status == "booked":
        s.status = "paid"
        _ghi_nhat_ky(db, p, ai, "cash", "sec_travel:pay")
    if v is not None and v.status == "cho":
        v.status, v.granted_by, v.granted_at = "da_cap", ai, rec.post_at or dt.datetime.utcnow()


GIO_KE_TOAN = dt.timedelta(hours=7)        # giờ máy chủ hệ kế toán (Việt Nam / Lào, UTC+7) — DB bên em lưu UTC


def _ngay_gio(s):
    """POSTDATE bên kế toán (giờ địa phương, không kèm múi) → UTC không múi như mọi cột giờ bên em."""
    try:
        return dt.datetime.fromisoformat(str(s)[:19]) - GIO_KE_TOAN if s else None
    except ValueError:
        return None


def dong_bo(db, rec, p=None, v=None):
    """Đọc lại phiếu bên kế toán; đã ghi sổ thì áp sang bên em. Trả rec. Lỗi mạng thì giữ nguyên, ném HTTPException."""
    if rec is None or rec.status != "da_gui" or not rec.real_id:
        return rec
    from models import Trip
    p = p or db.get(Trip, rec.trip_id)
    v = v or db.get(Voucher, rec.voucher_id)
    try:
        kq = _goi("GET", "/api/v1/accounting/cmpayment-receipt/%d?voucherType=CMP" % rec.real_id) or {}
    except HTTPException as e:
        if (e.detail or {}).get("ma") == "BEN_KE_TOAN_TU_CHOI":
            rec.status, rec.error_code = "loi", "PHIEU_CHI_MAT"
            rec.error_message = "Không đọc được phiếu chi %s bên kế toán (đã xoá?): %s" % (rec.document_no or rec.real_id, e.detail.get("loi"))
            db.commit()
        raise
    m = kq.get("Master") or {}
    rec.checked_at = dt.datetime.utcnow()
    rec.document_no = m.get("DOCUMENTNO") or rec.document_no
    rec.tune_status = int(m.get("STATUS") or 0)
    if rec.tune_status in DA_GHI_SO:
        rec.status, rec.post_by, rec.post_at = "da_chi", m.get("POSTNAME") or None, _ngay_gio(m.get("POSTDATE"))
        rec.error_code = rec.error_message = None
        if p is not None:
            _ap_da_chi(db, p, v, rec)
    db.commit()
    return rec


def gui(db, p, v, user):
    """Tạo (hoặc dùng lại) phiếu chi tạm ứng bên kế toán cho tờ PTU `v`. Ghi kết quả — kể cả khi hỏng — rồi mới trả / ném."""
    rec = db.get(ChiTune, v.id)
    if rec is not None and rec.status == "da_gui":
        try:
            dong_bo(db, rec, p, v)
        except HTTPException:
            pass
    if rec is not None and rec.status == "da_chi":
        _ap_da_chi(db, p, v, rec)                       # mục IV mở lại rồi ghi sổ lại: tiền đã chi rồi, chênh tính lúc tất toán
        db.commit()
        return rec
    now = dt.datetime.utcnow()
    if rec is None:
        rec = ChiTune(voucher_id=v.id, trip_id=p.id, status="loi", attempts=0, first_attempt_at=now)
        db.add(rec)
    rec.attempts, rec.last_attempt_at, rec.sent_by = (rec.attempts or 0) + 1, now, getattr(user, "full_name", None)
    try:
        obj = rec.obj_id = doi_tuong_tai_xe(db, p.driver_id, p.driver_name)
        body = dung_goi(db, p, v, obj)
        rec.amount_lak, rec.request_body = body["Header"]["Amount"], json.dumps(body, ensure_ascii=False)
        # số tạm ứng đổi khi phiếu bên kia chưa ghi sổ: bỏ phiếu cũ (của đúng tờ này) rồi lập phiếu đúng số
        da_co = _tim_phieu_da_co(obj, v.doc_no)
        dung_lai = None
        for x in da_co:
            if abs(float(x.get("CM_AMOUNT") or 0) - rec.amount_lak) < 0.5 and dung_lai is None:
                dung_lai = x
            elif int(x.get("ST_AUTOID") or 0) not in DA_GHI_SO:
                _goi("POST", "/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(x["DOC_DOCUMENTID"]), "VoucherType": "CMP"})
        if dung_lai is not None:
            rec.real_id, rec.document_no = int(dung_lai["DOC_DOCUMENTID"]), dung_lai.get("DOC_DOCUMENTNO")
            rec.response_body = json.dumps({"dung_lai": dung_lai}, ensure_ascii=False, default=str)[:20000]
        else:
            kq = _goi("POST", "/api/v1/accounting/cmpayment-receipt/save-and-commit", body) or {}
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
        dong_bo(db, rec, p, v)                          # lấy số phiếu bên đó; có khi thủ quỹ đã ghi sổ ngay
    except HTTPException:
        pass
    return rec


def gui_sau_ghi_so(db, p, user):
    """Gọi sau khi KT Chi phí ghi sổ mục IV. Không có tờ tạm ứng (không có tiền mặt) thì thôi. Hỏng thì ghi lỗi lên tờ —
    ghi sổ mục IV vẫn giữ; tài xế chỉ chưa xuất phát được cho tới khi gửi lại được và thủ quỹ chi."""
    if not chi_o_ke_toan():
        return None
    from routes.phieu_linh import dam_bao_tam_ung      # tờ PTU theo số tiền mặt LÚC GHI SỔ (Bãi in tờ trước khi có giá)
    v = dam_bao_tam_ung(db, p, user)
    if v is None or v.status == "huy":
        return None
    db.commit()
    try:
        return gui(db, p, v, user)
    except HTTPException:
        return db.get(ChiTune, v.id)


def cua_phieu(db, p, cap_nhat=False):
    """Bản ghi chi tạm ứng của một phiếu (có thể None); `cap_nhat` → hỏi lại bên kế toán nếu đang chờ chi."""
    rec = db.query(ChiTune).filter(ChiTune.trip_id == p.id).first()
    if cap_nhat and rec is not None and rec.status == "da_gui":
        try:
            dong_bo(db, rec, p)
        except HTTPException:
            pass
    return rec


def rut(db, trip_id=None, voucher_id=None):
    """Phiếu bên em bị xoá / tờ tạm ứng bị huỷ: phiếu chi bên kế toán CHƯA ghi sổ thì xoá bên đó và bỏ bản ghi; đã ghi sổ (tiền
    đã tới tay tài xế) thì chặn 409 — phải đối soát ở hệ kế toán trước. Không gọi được bên đó thì cũng chặn: không để phiếu
    chi mồ côi chờ thủ quỹ chi cho một chuyến không còn."""
    q = db.query(ChiTune)
    q = q.filter(ChiTune.voucher_id == voucher_id) if voucher_id else q.filter(ChiTune.trip_id == trip_id)
    for rec in q.all():
        if rec.status == "da_gui" and rec.real_id:
            dong_bo(db, rec)
        if rec.status == "da_chi":
            _loi("DA_CHI_O_KE_TOAN", "Phiếu chi tạm ứng %s bên hệ kế toán đã ghi sổ (tiền đã chi) — không xoá / huỷ được ở đây, "
                                     "đối soát ở hệ kế toán trước." % (rec.document_no or rec.real_id), 409)
        if rec.real_id:
            _goi("POST", "/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(rec.real_id), "VoucherType": "CMP"})
        db.delete(rec)
    db.flush()


def cau_chan_chi(db, p):
    """Câu báo khi Quỹ bấm chi mục IV trên trang điều xe lúc tạm ứng chi ở hệ kế toán — kèm số phiếu chi bên đó nếu có."""
    r = cua_phieu(db, p, cap_nhat=True)
    return CAU_CHI_O_KE_TOAN + (" Phiếu chi bên đó: %s." % (r.document_no or r.real_id) if r is not None and r.real_id else "")


def xuat(rec, thay_tien=True):
    if rec is None:
        return None
    return {"status": rec.status, "document_no": rec.document_no, "real_id": rec.real_id, "tune_status": rec.tune_status,
            "obj_id": rec.obj_id,
            "amount_lak": rec.amount_lak if thay_tien else None, "post_by": rec.post_by,
            "post_at": rec.post_at.isoformat(timespec="minutes") + "+00:00" if rec.post_at else None,
            "error_code": rec.error_code, "error_message": rec.error_message, "attempts": rec.attempts,
            "last_attempt_at": rec.last_attempt_at.isoformat(timespec="minutes") if rec.last_attempt_at else None,
            "checked_at": rec.checked_at.isoformat(timespec="minutes") if rec.checked_at else None}
