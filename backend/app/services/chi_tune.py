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

from models import ChiChuXeTune, ChiTune, DoiTuongTune, Driver, Owner, Trip, TripLog, TripSection, Voucher
from services import chung_tu as CT
from services import gui_tune as GT

CHO_GIAY = 40
DA_GHI_SO = (12, 13)                      # CMPaymentReceiptConstants.PostedFinalStatus / PostedTempStatus
_BO_NHO = {}                              # mã tiền, kỳ — 10 phút
# câu báo NGƯỜI DÙNG — không ghi chú nội bộ (ngày chốt, ai chốt) vào đây (rà 01/10: lộ "(chủ dự án 01/10)" lên màn)
CAU_CHI_O_KE_TOAN = ("Tạm ứng chi ở hệ kế toán: thủ quỹ chi tiền và ghi sổ phiếu chi tạm ứng bên đó, "
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
        GT.quen_token()                                 # tài khoản tích hợp: lần sau đăng nhập lại
        _loi("QLSX_TOKEN_HET_HAN", "Token hệ kế toán sai hoặc đã hết hạn — đặt tài khoản tích hợp QLSX_USERNAME / QLSX_PASSWORD "
                                   "(tự lấy token mới) hoặc token mới QLSX_ACCESS_TOKEN.", 502)
    if isinstance(than, dict) and than.get("Success") is True:
        return than.get("Result")
    cau = ((than or {}).get("Message") if isinstance(than, dict) else (tho or "")[:300]) or "không rõ lý do"
    if "khoản không hợp lệ" in cau and isinstance(body, dict) and body.get("Entries"):
        tk = sorted({str(x.get(k)) for x in body["Entries"] for k in ("DebitAccount", "CreditAccount") if x.get(k)})
        cau += " — phiếu dùng tài khoản %s; mã nào chưa có trong danh mục tài khoản Lào bên kế toán thì bên đó từ chối "                "(1371, 4021, 4022 đang chờ mở — hợp đồng mục 1.1)" % ", ".join(tk)
    _loi("BEN_KE_TOAN_TU_CHOI", ("Hệ kế toán từ chối: %s" if ma < 300 else "Hệ kế toán trả HTTP %s: %%s" % ma) % cau,
         502 if ma >= 500 else 422)


def _nho(khoa, ham):
    v = _BO_NHO.get(khoa)
    if v and time.time() - v[0] < 600:
        return v[1]
    kq = ham()
    _BO_NHO[khoa] = (time.time(), kq)
    return kq


def ma_tien(ten="LAK"):
    """CUR_AUTOID của một tiền. `GetAllCurrency` chỉ trả tiền ĐANG BẬT (spPUBCURRENCYSelectAllActive) — tiền có mà đang tắt
    (máy demo 01/10: USD mã 2 đang tắt) thì đặt tay `QLSX_TIEN_<MÃ>=<id>` trong .env, hoặc bên kế toán bật tiền đó."""
    tay = (os.getenv("QLSX_TIEN_%s" % ten) or "").strip()
    if tay.isdigit():
        return int(tay)
    ds = _nho("tien", lambda: _goi("GET", "/api/v1/common/GetAllCurrency") or [])
    ma = next((c.get("CUR_AUTOID") for c in ds if str(c.get("CUR_NAME") or "").upper() == ten), None)
    if not ma:
        _loi("THIEU_TIEN_TE", "Tiền %s chưa bật trong danh mục tiền tệ bên kế toán (đường GetAllCurrency chỉ trả tiền đang bật: %s). "
                              "Bên kế toán bật tiền %s, hoặc đặt QLSX_TIEN_%s=<mã> trong .env." % (
                                  ten, ", ".join(str(c.get("CUR_NAME")) for c in ds) or "—", ten, ten))
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


# loại đối tượng bên em → (đường danh mục bên kế toán, tiền tố mã OBJ_OBJECTNO, tên gọi)
LOAI_DOI_TUONG = {"tai_xe": ("staff", "EPLTX-", "tài xế"), "chu_xe": ("suppliers", "EPLCX-", "chủ xe liên kết"),
                  "khach": ("customers", "EPLKH-", "khách"), "ncc": ("suppliers", "EPLNCC-", "nhà cung cấp")}


def doi_tuong(db, loai, ref_id, ten, sdt=None, dia_chi=None, to_chuc=None, ma=None):
    """OBJ_AUTOID bên kế toán của một người bên em (tài xế → nhân viên, chủ xe → nhà cung cấp, khách → khách hàng). Chưa nhớ
    thì tìm theo mã (lần trước tạo rồi mà chưa kịp nhớ), không có nữa mới tạo. `ma` = mã có sẵn (mã khách kế toán đã gán)."""
    duong, tien_to, goi_la = LOAI_DOI_TUONG[loai]
    if not ref_id:
        _loi("THIEU_DOI_TUONG", "Phiếu chưa có %s — không lập chứng từ bên kế toán được." % goi_la, 409)
    r = db.get(DoiTuongTune, (loai, ref_id))
    if r is not None and (ma is None or r.object_no == ma):
        return r.obj_id
    so = ma or (tien_to + ref_id)
    tim = _goi("POST", "/api/v1/master-data/%s/list" % duong, {"PageIndex": 1, "ObjKey": so}) or {}
    oid = next((x.get("ObjId") for x in (tim.get("Data") or []) if x.get("ObjectNo") == so), None)
    if not oid and ma:
        _loi("MA_KHONG_CO_BEN_KE_TOAN", "Mã %s %s không có trong danh mục bên kế toán." % (goi_la, ma), 422)
    if not oid:
        than = {"ObjectNo": so, "ObjectName": (ten or so)[:100], "CountryAutoId": _cfg("QLSX_COUNTRY_ID", 11),
                "ObjectOfOrganization": _cfg("QLSX_ORG_ID", 1368), "HandPhone": sdt or None, "Address": dia_chi or None,
                "Description": "%s trang điều xe EPL Lào" % goi_la.capitalize()}
        if to_chuc is not None:
            than["IsOrganization"] = bool(to_chuc)
        oid = _goi("POST", "/api/v1/master-data/%s/upsert" % duong, than)
    if not oid:
        _loi("KHONG_TAO_DUOC_DOI_TUONG", "Hệ kế toán không trả mã đối tượng cho %s %s." % (goi_la, ten or ref_id), 502)
    if r is not None:
        db.delete(r)
        db.flush()
    db.add(DoiTuongTune(loai=loai, ref_id=ref_id, obj_id=int(oid), object_no=so))
    db.flush()
    return int(oid)


def doi_tuong_tai_xe(db, driver_id, ten):
    tx = db.get(Driver, driver_id) if driver_id else None
    return doi_tuong(db, "tai_xe", driver_id, ten or (tx.name if tx else None), sdt=getattr(tx, "phone", None))


def doi_tuong_phieu(db, p):
    """Đối tượng của phiếu chi tạm ứng: xe nhà → tài xế (người cầm tiền, Nợ 1601); xe thuê → CHỦ XE (EPL ứng là trừ vào tiền
    trả chủ xe, Nợ 4022 — chung_tu.dinh_khoan)."""
    if p.company == "joint":
        o = db.get(Owner, p.owner_id) if p.owner_id else None
        return doi_tuong(db, "chu_xe", p.owner_id, p.owner_name or (o.name if o else None), sdt=getattr(o, "phone", None), to_chuc=False)
    return doi_tuong_tai_xe(db, p.driver_id, p.driver_name)


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
MAT = "PHIEU_CHI_MAT"                       # phiếu bên kế toán không còn (đã xoá tay) — gửi lại thì lập phiếu mới


def danh_mat(db, rec):
    """Phiếu chi bên kế toán đã bị xoá: `GET cmpayment-receipt/{id}` VẪN trả Success true, `Master` null, `Entries` rỗng (thử thật
    01/10) — không báo lỗi. Đánh bản ghi "loi · PHIEU_CHI_MAT" để không kẹt "chờ chi" mãi; gửi lại thì lập phiếu mới, rút / huỷ
    thì coi như đã rút xong (không gọi delete lên phiếu không còn)."""
    rec.status, rec.error_code = "loi", MAT
    rec.error_message = "Phiếu chi %s không còn bên hệ kế toán (đã xoá) — bấm gửi lại để lập phiếu mới." % (rec.document_no or rec.real_id)
    rec.checked_at = dt.datetime.utcnow()
    db.commit()
    return rec


def doc_phieu(db, rec):
    """Master của phiếu chi `rec.real_id` bên kế toán; phiếu không còn → đánh PHIEU_CHI_MAT, trả None. Bên đó từ chối đọc →
    cũng PHIEU_CHI_MAT rồi ném lại; lỗi mạng → ném, bản ghi giữ nguyên."""
    try:
        kq = _goi("GET", "/api/v1/accounting/cmpayment-receipt/%d?voucherType=CMP" % rec.real_id) or {}
    except HTTPException as e:
        if (e.detail or {}).get("ma") == "BEN_KE_TOAN_TU_CHOI":
            rec.status, rec.error_code = "loi", MAT
            rec.error_message = "Không đọc được phiếu chi %s bên kế toán (đã xoá?): %s" % (rec.document_no or rec.real_id, e.detail.get("loi"))
            db.commit()
        raise
    m = kq.get("Master") if isinstance(kq, dict) else None
    if not m:
        danh_mat(db, rec)
        return None
    return m


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
    p = p or db.get(Trip, rec.trip_id)
    v = v or db.get(Voucher, rec.voucher_id)
    m = doc_phieu(db, rec)
    if m is None:
        return rec                                      # phiếu bên đó đã bị xoá: PHIEU_CHI_MAT, gửi lại thì lập phiếu mới
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
        obj = rec.obj_id = doi_tuong_phieu(db, p)
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
            try:
                dong_bo(db, rec)
            except HTTPException:
                if rec.error_code != MAT:
                    raise
        if rec.status == "da_chi":
            _loi("DA_CHI_O_KE_TOAN", "Phiếu chi tạm ứng %s bên hệ kế toán đã ghi sổ (tiền đã chi) — không xoá / huỷ được ở đây, "
                                     "đối soát ở hệ kế toán trước." % (rec.document_no or rec.real_id), 409)
        if rec.real_id and rec.error_code != MAT:      # phiếu bên đó đã mất thì coi như đã rút xong
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


# ================================================================ trả chủ xe liên kết (01/10)
def _dong_chu_xe(db, owner_id):
    """Phiếu xe thuê đã khoá, chưa trả, KHÔNG nằm trong đề nghị trả còn hiệu lực (đang chờ chi / đã chi)."""
    from services import tra_chu_xe as TC
    dang = set()
    for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id == owner_id, ChiChuXeTune.status.in_(("da_gui", "da_chi"))):
        dang.update(json.loads(r.trip_ids or "[]"))
    return [x for x in TC.cho_tra(db, owner_id) if x["id"] not in dang and not x["owner_paid"]]


def cho_tra_chu_xe(db, owner_id, thay_tien=True):
    """Màn Xe liên kết: phiếu chờ đề nghị trả + các lần đề nghị (mới trước)."""
    ds = db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id == owner_id).order_by(ChiChuXeTune.created_at.desc()).limit(30).all()
    return {"cho": _dong_chu_xe(db, owner_id), "de_nghi": [xuat_chu_xe(r, thay_tien) for r in ds], "o_ke_toan": chi_o_ke_toan()}


def de_nghi_tra_chu_xe(db, owner_id, trip_ids, phuong_thuc, user):
    """Lập phiếu chi "Chi khác" bên kế toán cho chủ xe: Nợ 4022 phải trả chủ xe / Có tiền (mặt hoặc ngân hàng, theo tiền thuê).
    Các phiếu phải cùng chủ xe, đã khoá, chưa trả, chưa nằm đề nghị khác, cùng tiền thuê. Số chi là SỐ TRẢ THỰC = Σ phiếu − hàng
    chủ xe mua ở quầy (tra_chu_xe.tru_hang_quay — kho tạm tắt thì 503, không lập); phải dương. Phiếu bán bị trừ được GIỮ CHỖ ở
    kho tạm TRƯỚC khi gọi hệ kế toán."""
    from services import tai_khoan as TK
    from services import tra_chu_xe as TC
    o = db.get(Owner, owner_id)
    if o is None:
        _loi("KHONG_THAY", "Không có chủ xe này.", 404)
    if phuong_thuc not in ("cash", "bank"):
        _loi("CACH_TRA_SAI", "Cách trả phải là tiền mặt (cash) hoặc chuyển khoản (bank).")
    con = {x["id"]: x for x in _dong_chu_xe(db, owner_id)}
    chon = [con[i] for i in dict.fromkeys(trip_ids or []) if i in con]
    if not chon or len(chon) != len(set(trip_ids or [])):
        _loi("PHIEU_KHONG_HOP_LE", "Có phiếu không còn chờ trả (chưa khoá, đã trả, hoặc đang nằm đề nghị khác) — tải lại danh sách.", 409)
    tien = {x["hire_ccy"] or "LAK" for x in chon}
    if len(tien) != 1:
        _loi("KHAC_TIEN", "Các phiếu chọn khác tiền thuê (%s) — mỗi đề nghị một loại tiền." % ", ".join(sorted(tien)))
    ccy = tien.pop()
    kq = TC.tru_hang_quay(db, owner_id, chon, user)               # hàng chủ xe mua ở quầy chờ trừ — kho tạm tắt thì 503
    if (kq["tra_thuc"] or 0) <= 0:
        _loi("KHONG_CON_PHAI_TRA", "Còn phải trả %s %s ≤ 0 (tổng phiếu %s, đã trừ hàng mua ở quầy %s, EPL đã ứng trừ sẵn trên phiếu) — "
                                   "không lập phiếu chi." % (kq["tra_thuc"], ccy, kq["tong"], kq["tru"]), 409)
    now = dt.datetime.utcnow()
    so = "TCX-%s-%s" % (now.strftime("%y%m%d%H%M%S"), owner_id[:4])
    rec = ChiChuXeTune(owner_id=owner_id, trip_ids=json.dumps([x["id"] for x in chon]), currency=ccy, amount=kq["tra_thuc"],
                       amount_lak=kq["tra_thuc_lak"], phuong_thuc=phuong_thuc, ref_no=so, status="loi", attempts=0,
                       created_by=getattr(user, "full_name", None), tru_hang=json.dumps(dict(kq, chot=False), ensure_ascii=False))
    db.add(rec)
    db.flush()
    TC.giu_hang_quay(db, rec.ref_no, owner_id, [h["id"] for h in kq["hang"]], user)   # giữ chỗ TRƯỚC khi gọi hệ kế toán; lỗi → ném
    _gui_chu_xe(db, rec, o, chon, TK, user)
    return rec


def _tru(rec):
    try:
        return json.loads(rec.tru_hang) if rec.tru_hang else None
    except ValueError:
        return None


def _gui_chu_xe(db, rec, o, chon, TK, user=None):
    from services import tra_chu_xe as TC
    rec.attempts, rec.last_attempt_at = (rec.attempts or 0) + 1, dt.datetime.utcnow()
    try:
        obj = rec.obj_id = doi_tuong(db, "chu_xe", o.id, o.name, sdt=getattr(o, "phone", None), to_chuc=False)
        co = TK.ma_tien(rec.phuong_thuc, rec.currency)
        ma_cur, hom_nay = ma_tien(rec.currency), dt.date.today()
        ty = round((rec.amount_lak or 0) / rec.amount, 6) if rec.amount else 1
        # dòng phiếu chi = SỐ TRẢ THỰC từng phiếu sau khi trừ hàng quầy (đề nghị cũ chưa có tru_hang: trừ 0); phiếu trừ hết thì bỏ
        kq = _tru(rec) or TC.tinh_tru(chon, [])
        dong = [d for d in kq["dong"] if d.get("tra_thuc")]
        dien_giai = "Trả chủ xe liên kết %s: %s" % (o.name, ", ".join(x["doc_no"] for x in chon))
        if kq.get("hang"):
            dien_giai += " · trừ hàng mua ở quầy %s" % ", ".join(str(h.get("doc_no")) for h in kq["hang"])
        body = {"TmpId": 0, "RealId": 0, "VoucherType": "CMP", "SessionId": "epllao-cx-%s" % rec.id, "PostMode": "None",
                "Header": {"CountryId": _cfg("QLSX_COUNTRY_ID", 11), "OrgId": _cfg("QLSX_ORG_ID", 1368), "FiciAutoId": ma_ky(hom_nay),
                           "DotyAutoId": _cfg("QLSX_DOTY_TRA_CHU_XE", 60), "ObjectId": obj, "CurrencyId": ma_cur,
                           "DocumentDate": hom_nay.isoformat(), "RefDocumentNo": rec.ref_no, "Description": dien_giai[:250],
                           "IsCash": rec.phuong_thuc == "cash", "IsLocal": rec.currency == "LAK", "IsDirect": True,
                           "ExchangeRate": 1 if rec.currency == "LAK" else ty, "Amount": rec.amount,
                           "BaseAmount": rec.amount_lak if rec.currency != "LAK" else rec.amount, "ContactName": (o.name or "")[:100] or None},
                "Relations": [],
                "Entries": [{"SourceLineKey": "EPLLAO:%s:TCX:%s" % (rec.id, d["trip_id"]), "ObjectId": obj, "CurrencyId": ma_cur,
                             "DebitAccount": TK.CHU_XE, "CreditAccount": co, "Amount": d["tra_thuc"],
                             "BaseAmount": d["tra_thuc_lak"] if rec.currency != "LAK" else d["tra_thuc"],
                             # tỷ giá RIÊNG từng dòng = Kíp khoá trên phiếu / nguyên tệ: máy chủ anh Tune nay tự tính base
                             # dòng = Amount × ExchangeRate (ce95b3c+) — gửi tỷ giá chung thì Kíp từng phiếu bị dịch (rà 01/10)
                             "ExchangeRate": 1 if rec.currency == "LAK" else (round(d["tra_thuc_lak"] / d["tra_thuc"], 10) if d["tra_thuc"] else ty),
                             "EntryTypeId": 11,
                             "Description": ("Trả chủ xe phiếu %s" % d["doc_no"]) + (" · trừ hàng mua ở quầy" if (d.get("tru") or 0) > 0 else ""),
                             "ValidateMoney": True} for d in dong]}
        rec.request_body = json.dumps(body, ensure_ascii=False)
        cu = [x for x in _tim_phieu_da_co(obj, rec.ref_no)]
        if cu:
            rec.real_id, rec.document_no = int(cu[0]["DOC_DOCUMENTID"]), cu[0].get("DOC_DOCUMENTNO")
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
        dong_bo_chu_xe(db, rec, user)
    except HTTPException:
        pass


def gui_lai_chu_xe(db, rec, user):
    """Lần trước hỏng: gửi lại đúng các phiếu đó nếu còn chờ trả."""
    from services import tai_khoan as TK
    if rec.status != "loi":
        _loi("KHONG_GUI_LAI", "Đề nghị này đang %s — không gửi lại." % rec.status, 409)
    o = db.get(Owner, rec.owner_id)
    ids = json.loads(rec.trip_ids or "[]")
    con = {x["id"]: x for x in _dong_chu_xe(db, rec.owner_id)}
    if any(i not in con for i in ids):
        if (_tru(rec) or {}).get("hang"):
            from services import tra_chu_xe as TC
            TC.tha_hang_quay(db, rec.ref_no, user)        # phiếu bán đang giữ chỗ về chờ trừ; kho tạm tắt → ném, đề nghị giữ "lỗi"
        rec.status = "huy"
        db.commit()
        _loi("PHIEU_KHONG_HOP_LE", "Có phiếu trong đề nghị không còn chờ trả — lập đề nghị mới.", 409)
    _gui_chu_xe(db, rec, o, [con[i] for i in ids], TK, user)      # dùng lại rec.tru_hang (số trả thực lúc lập)
    return rec


def _chot_hang(db, rec, user=None):
    """Đề nghị đã chi (phiếu chi bên kế toán đã ghi sổ): chốt các phiếu bán bị trừ "TUNE:<số phiếu chi>" ở kho tạm + bút toán chờ
    Nợ 4022 / Có 707 (tra_chu_xe.chot_hang_quay). Lỗi thì KHÔNG ném — tiền đã đi, phiếu bán vẫn giữ chỗ; lần gọi sau thử lại."""
    from services import tra_chu_xe as TC
    t = _tru(rec)
    if rec.status != "da_chi" or not t or not t.get("hang") or t.get("chot"):
        return
    try:
        TC.chot_hang_quay(db, rec.ref_no, rec.document_no or rec.real_id, rec.owner_id, [h["id"] for h in t["hang"]], user,
                          by_user="%s (hệ kế toán)" % (rec.post_by or "thủ quỹ"))
        t["chot"] = True
        rec.tru_hang = json.dumps(t, ensure_ascii=False)
        db.commit()
    except Exception as e:                              # noqa: BLE001 — kho tạm tắt / lỗi: giữ "chưa chốt", lần sau thử lại
        db.rollback()
        rec.error_message = "Đã chi; chưa chốt hàng quầy bị trừ ở kho tạm (thử lại lần cập nhật sau): %s" % (
            (e.detail or {}).get("loi") if isinstance(e, HTTPException) and isinstance(e.detail, dict) else e)
        db.commit()


def dong_bo_chu_xe(db, rec, user=None):
    """Đọc lại phiếu chi trả chủ xe; đã ghi sổ thì các phiếu thành "đã trả chủ xe" (tra_chu_xe.danh_dau_tra), rồi chốt hàng quầy
    bị trừ (lỗi chốt không ném — đề nghị đã chi mà chưa chốt thì lần gọi sau thử lại)."""
    from types import SimpleNamespace
    from services import tra_chu_xe as TC
    if rec is not None and rec.status == "da_chi":
        _chot_hang(db, rec, user)
        return rec
    if rec is None or rec.status != "da_gui" or not rec.real_id:
        return rec
    m = doc_phieu(db, rec)
    if m is None:
        return rec                                      # phiếu bên đó đã bị xoá: PHIEU_CHI_MAT, gửi lại thì lập phiếu mới
    rec.checked_at, rec.document_no = dt.datetime.utcnow(), m.get("DOCUMENTNO") or rec.document_no
    rec.tune_status = int(m.get("STATUS") or 0)
    if rec.tune_status in DA_GHI_SO:
        rec.status, rec.post_by, rec.post_at = "da_chi", m.get("POSTNAME") or None, _ngay_gio(m.get("POSTDATE"))
        so = TC.so_lieu(db, json.loads(rec.trip_ids or "[]"))
        TC.danh_dau_tra(db, SimpleNamespace(full_name="%s (hệ kế toán)" % (rec.post_by or "thủ quỹ"), role="cash"),
                        "TUNE:%s" % (rec.document_no or rec.real_id),
                        [{"trip_id": i, "tra_chu_xe": x["tra_chu_xe"], "tra_chu_xe_lak": x["tra_chu_xe_lak"]} for i, x in so.items()])
    db.commit()
    _chot_hang(db, rec, user)
    return rec


def huy_chu_xe(db, rec, user=None):
    """Bỏ đề nghị chưa chi: xoá phiếu chi bên kế toán (nếu có), trả các phiếu bán đang giữ chỗ về chờ trừ — các phiếu về lại
    "chờ trả"."""
    if rec.status == "da_gui":
        try:
            dong_bo_chu_xe(db, rec, user)
        except HTTPException:
            if rec.error_code != MAT:
                raise
    if rec.status == "da_chi":
        _loi("DA_CHI_O_KE_TOAN", "Phiếu chi %s đã ghi sổ bên kế toán — không huỷ được ở đây." % (rec.document_no or rec.real_id), 409)
    if rec.real_id and rec.error_code != MAT:          # phiếu bên đó đã mất thì coi như đã rút xong
        _goi("POST", "/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(rec.real_id), "VoucherType": "CMP"})
    if (_tru(rec) or {}).get("hang"):
        from services import tra_chu_xe as TC
        TC.tha_hang_quay(db, rec.ref_no, user)            # phiếu bán giữ chỗ về chờ trừ; lỗi → ném
    rec.status = "huy"
    db.commit()
    return rec


def xuat_chu_xe(rec, thay_tien=True):
    return {"id": rec.id, "owner_id": rec.owner_id, "trip_ids": json.loads(rec.trip_ids or "[]"), "ref_no": rec.ref_no,
            "currency": rec.currency, "amount": rec.amount if thay_tien else None, "amount_lak": rec.amount_lak if thay_tien else None,
            "phuong_thuc": rec.phuong_thuc, "status": rec.status, "document_no": rec.document_no, "real_id": rec.real_id,
            "tune_status": rec.tune_status, "post_by": rec.post_by,
            "post_at": rec.post_at.isoformat(timespec="minutes") + "+00:00" if rec.post_at else None,
            "error_code": rec.error_code, "error_message": rec.error_message, "attempts": rec.attempts, "created_by": rec.created_by,
            "created_at": rec.created_at.isoformat(timespec="minutes") + "+00:00" if rec.created_at else None,
            "tru_hang": _xuat_tru(rec, thay_tien)}


def _xuat_tru(rec, thay_tien=True):
    t = _tru(rec)
    if not t:
        return None
    return {"tong": t.get("tong") if thay_tien else None, "tru": t.get("tru") if thay_tien else None,
            "tru_lak": t.get("tru_lak") if thay_tien else None, "hang": [h.get("doc_no") for h in t.get("hang") or []],
            "chot": bool(t.get("chot"))}


# ================================================================ công nợ khách — chỉ XEM (01/10)
def _da_tra(d):
    """Đã thu của MỘT chứng từ nợ. RETK_MONEYPAID chỉ là tiền trả lúc chốt phiếu bán — SO thu sau bằng phiếu thu công nợ vẫn để
    0 dù RCTD_DEBTMONEY đã về 0 (rà 01/10: dòng "Đã thu 0 · Còn lại 0 · Đã thu đủ", lệch với Summary.TotalCollected). Có đủ
    tiền và còn nợ thì đã thu = tiền − còn nợ (khớp Summary); thiếu thì giữ số bên đó gửi."""
    tien, con = d.get("RETK_PAYMENTAMOUNT"), d.get("RCTD_DEBTMONEY")
    try:
        return max(float(d.get("RETK_MONEYPAID") or 0), round(float(tien) - float(con), 6))
    except (TypeError, ValueError):
        return d.get("RETK_MONEYPAID")


def cong_no_khach(db, k):
    """Công nợ của khách bên hệ kế toán: POST /api/v1/sales/debt/customer-detail. Khách chưa có mã bên kế toán thì None (chưa
    có SO nào bên đó). Trả gọn: tổng, tuổi nợ, từng chứng từ nợ (SO), các lần thu, đơn hàng."""
    if not (k.code or "").strip():
        return None
    obj = doi_tuong(db, "khach", k.id, k.name, ma=k.code.strip())
    db.commit()
    kq = _goi("POST", "/api/v1/sales/debt/customer-detail", {"CustomerObjectId": obj, "OrgId": _cfg("QLSX_ORG_ID", 1368)}) or {}
    s = kq.get("Summary") or {}
    return {
        "customer_code": k.code, "obj_id": obj,
        "tong": {"no": s.get("TotalDebt"), "con_no": s.get("CurrentDebt"), "qua_han": s.get("OverdueDebt"), "da_thu": s.get("TotalCollected"),
                 "so_chung_tu": s.get("UnsettledCount"), "qua_han_ngay": s.get("MaxOverdueDays"), "rui_ro": s.get("RiskLevel")},
        "tuoi_no": [{"ma": a.get("BucketCode"), "ten": a.get("BucketName"), "tien": a.get("Amount"), "pct": a.get("PercentValue")}
                    for a in (kq.get("Aging") or [])],
        "no": [{"so": d.get("OrderCode"), "phieu_ban": d.get("RETK_CODE"), "ngay": d.get("RETK_TIMECLOSETICKET"), "han": d.get("RCTD_EXPIRE"),
                "tien": d.get("RETK_PAYMENTAMOUNT"), "da_tra": _da_tra(d), "con_no": d.get("RCTD_DEBTMONEY"),
                "ccy": d.get("CurrencyCode"), "trang_thai": d.get("DebtStatus"), "tuoi": d.get("AgingDays")} for d in (kq.get("Debts") or [])],
        "thu": kq.get("Collections") or [],
        "don": [{"so": o.get("OrderCode"), "ngay": o.get("OrderDate"), "tien": o.get("FinalTotalAmount"), "ccy": o.get("CurrencyCode"),
                 "trang_thai": o.get("StatusName")} for o in (kq.get("Orders") or [])],
    }
