# -*- coding: utf-8 -*-
"""CHI TẠM ỨNG ở hệ kế toán anh Tune — chủ dự án chốt 01/10/2026: "chi thật là anh Tune xong update trạng thái về bên mình".

Luồng:
  1. Bãi lập phiếu, in tờ đề nghị tạm ứng (PTU). KT Chi phí VC kiểm, GHI SỔ mục IV trên trang điều xe.
  2. Ghi sổ xong → bên em tạo PHIẾU CHI bên anh Tune: loại "Chi trước" (DOTY 59), đối tượng = tài xế, Nợ/Có theo bảng định
     khoản của bên em (`chung_tu.dinh_khoan("PC_TU")`: xe nhà Nợ 1601 / Có 1011), CHƯA ghi sổ (PostMode None). Từ 02/10 mỗi
     dòng tiền mặt của tờ là một dòng định khoản (`dong_tam_ung`) — trước đó một dòng tổng.
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
    # 06/10: kèm mã HTTP thật (`http`) và mã trong phong bì (`code` — lỗi chưa bắt bên đó về HTTP 200 kèm Success false, Code 500)
    # để người gọi phân biệt "bên kia không có / từ chối" (4xx) với "bên kia đang lỗi máy chủ" (5xx) — doc_phieu
    code = than.get("Code") if isinstance(than, dict) and isinstance(than.get("Code"), int) else None
    raise HTTPException(502 if ma >= 500 else 422, {
        "ma": "BEN_KE_TOAN_TU_CHOI", "loi": ("Hệ kế toán từ chối: %s" if ma < 300 else "Hệ kế toán trả HTTP %s: %%s" % ma) % cau,
        "http": ma, "code": code})


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


def doi_tuong(db, loai, ref_id, ten, sdt=None, dia_chi=None, to_chuc=None, ma=None, chi_tim=False):
    """OBJ_AUTOID bên kế toán của một người bên em (tài xế → nhân viên, chủ xe → nhà cung cấp, khách → khách hàng). Chưa nhớ
    thì tìm theo mã (lần trước tạo rồi mà chưa kịp nhớ), không có nữa mới tạo. `ma` = mã có sẵn (mã khách kế toán đã gán).
    `chi_tim=True` (06/10): CHỈ TÌM, KHÔNG TẠO — mọi đường ĐỌC (công nợ khách / đối tác: màn xem, đồng bộ nền) dùng chế độ này, vì
    tạo là một lần GHI vào danh mục bên kế toán; không thấy thì trả None. Chỉ đường lập chứng từ (phiếu chi, SO, bút toán…) tạo."""
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
    if not oid and chi_tim:
        return None                                     # đường đọc: chưa có bên kế toán thì thôi, không upsert
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


def _so(v):
    v = float(v or 0)
    return ("%d" % v) if v == int(v) else ("%g" % v)


def dong_tam_ung(db, p, v, tien):
    """Các dòng định khoản của phiếu chi tạm ứng (02/10, chủ dự án: "bao nhiêu dòng tạm ứng thì bấy nhiêu dòng chi bên kế toán").

    Đúng bộ dòng mà số tạm ứng đếm (phieu_linh.dam_bao_tam_ung — tinh_toan.la_tien_mat_tai_xe: dầu mục III mua dọc đường trả
    tiền mặt, mục IV, VI tiền mặt khi xe đi), mỗi dòng Kíp theo tỷ giá khoá trên phiếu, cùng cách cộng của tờ PTU. Dòng 0 đồng
    bỏ. → [(dòng chi, tiền LAK, diễn giải)], Σ = `tien` (tiền đầu phiếu = số tờ PTU làm tròn): phần lệch do làm tròn từng dòng
    (tối đa nửa Kíp mỗi dòng) dồn vào DÒNG CUỐI và diễn giải dòng đó ghi rõ. Lệch quá phần làm tròn — tờ PTU không còn khớp các
    dòng (tờ đã cấp tại quỹ rồi dòng đổi…) — thì chặn 409, không chia bừa."""
    from models import TripExpense
    from services.ban_giao import _ten
    from services.tinh_toan import la_tien_mat_tai_xe, ty_gia
    dong = [d for d in (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
                        .order_by(TripExpense.section, TripExpense.line_no).all()) if la_tien_mat_tai_xe(d, p.company)]
    ra = []
    for d in dong:
        lak = round((d.qty or 0) * (d.unit_price or 0) * ty_gia(p, d.currency))     # = phieu_linh._lak
        if lak <= 0:
            continue
        ccy = d.currency or "LAK"
        if d.section == "fuel":
            dg = "Mục III · dầu mua %s lít × %s %s · %s" % (_so(d.qty), _so(d.unit_price), ccy, p.doc_no)
        else:
            dg = "Mục %s · %s · %s × %s %s · %s" % ({"travel": "IV", "other": "VI"}.get(d.section, d.section), _ten(db, d)[0] or "—",
                                                  _so(d.qty), _so(d.unit_price), ccy, p.doc_no)
        ra.append([d, lak, dg])
    lech = tien - sum(x[1] for x in ra)
    if not ra or abs(lech) > max(1, len(ra)):
        _loi("TAM_UNG_LECH_DONG", "Tờ tạm ứng %s ghi %s LAK mà các dòng tiền mặt hiện có cộng %s LAK — tờ không còn khớp dòng chi, không lập "
                                  "phiếu chi được. Đối soát tờ tạm ứng (KT Chi phí) rồi gửi lại." % (
                                      v.doc_no, "{:,}".format(tien), "{:,}".format(sum(x[1] for x in ra))), 409)
    if lech:
        ra[-1][1] += lech
        ra[-1][2] += " · %+d LAK làm tròn tổng phiếu" % lech
    return [tuple(x) for x in ra]


def dung_goi(db, p, v, obj):
    tien = round(v.amount_lak or 0)
    if tien <= 0:
        _loi("TAM_UNG_BANG_KHONG", "Tờ tạm ứng %s chưa có số tiền — KT Chi phí nhập giá mục IV trước." % v.doc_no, 409)
    no, _, co, _ = CT.dinh_khoan("PC_TU", company=p.company, section="travel", tien_te="LAK", phuong_thuc="cash")
    if not no or not co:
        _loi("THIEU_DINH_KHOAN", "Chưa có định khoản cho phiếu chi tạm ứng (%s / %s)." % (no, co))
    dong = dong_tam_ung(db, p, v, tien)
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
        # mỗi dòng tạm ứng một dòng định khoản (02/10), cùng đối tượng đầu phiếu; khoá dòng theo mã dòng chi như phiếu chi mục V
        # (chi_muc_tune) — màn Tổng hợp thu chi bên kế toán khoá dòng theo DO:<do_id>:exp:<id>
        "Entries": [{"SourceLineKey": "EPLLAO:%s:%s" % (p.id, d.id), "ObjectId": obj, "CurrencyId": lak, "DebitAccount": no,
                     "CreditAccount": co, "Amount": t, "BaseAmount": t, "ExchangeRate": 1, "EntryTypeId": 11,
                     "Description": dg[:250], "ValidateMoney": True} for d, t, dg in dong],
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


# 06/10: mã "từ chối" KHÔNG có nghĩa phiếu đã mất — quyền / token / quá tải / hết giờ bên kia
KHONG_PHAI_MAT = (401, 403, 408, 429)


def _that_su_mat(e):
    """Lỗi đọc phiếu `e` (HTTPException) có phải bên kế toán KHÔNG CÒN / không nhận phiếu này (4xx thật) không. Lỗi máy chủ bên
    kia (HTTP ≥ 500, hoặc HTTP 200 kèm Success false · Code ≥ 500), mất mạng, token… → không: giữ trạng thái, lượt sau hỏi lại."""
    d = e.detail if isinstance(e.detail, dict) else {}
    if d.get("ma") != "BEN_KE_TOAN_TU_CHOI":
        return False
    ma = d["code"] if isinstance(d.get("code"), int) else d.get("http") if isinstance(d.get("http"), int) else e.status_code
    return ma < 500 and e.status_code < 500 and ma not in KHONG_PHAI_MAT


def doc_phieu(db, rec):
    """Master của phiếu chi `rec.real_id` bên kế toán; phiếu không còn → đánh PHIEU_CHI_MAT, trả None. Bên đó từ chối đọc (4xx
    thật — không thấy / không nhận) → cũng PHIEU_CHI_MAT rồi ném lại. 06/10: bên đó lỗi máy chủ (5xx, kể cả HTTP 200 kèm Code 500),
    mất mạng, token / quyền → ném, bản ghi GIỮ NGUYÊN (lỗi tạm — lượt sau / lần bấm sau hỏi lại); trước đây 5xx cũng bị đánh mất."""
    try:
        kq = _goi("GET", "/api/v1/accounting/cmpayment-receipt/%d?voucherType=CMP" % rec.real_id) or {}
    except HTTPException as e:
        if _that_su_mat(e):
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


# ================================================================ trả chủ xe liên kết (01/10) · tất toán đối tác (02/10)
def _can_tru_cua(db, rec):
    """Các lần cấn trừ SO nhiên liệu của một đề nghị (can_tru_tune), cũ trước."""
    from models import CanTruTune
    return db.query(CanTruTune).filter(CanTruTune.de_nghi_id == rec.id).order_by(CanTruTune.created_at, CanTruTune.order_code).all()


def _dang_giu(db, owner_id, bo_qua=None):
    """{Trip.id: đề nghị} — phiếu đang nằm trong một đề nghị trả CÒN HIỆU LỰC của chủ xe: chờ chi / đã chi, hoặc đề nghị lỗi mà đã có
    lần cấn trừ SO nhiên liệu chưa bỏ (lập đề nghị khác là cấn trừ hai lần — phải bỏ đề nghị đó trước). `bo_qua`: mã đề nghị không
    tính (gửi lại chính nó)."""
    from models import CanTruTune
    ra = {}
    for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id == owner_id, ChiChuXeTune.status.in_(("da_gui", "da_chi", "loi"))):
        if r.id == bo_qua:
            continue
        if r.status == "loi" and db.query(CanTruTune.id).filter(CanTruTune.de_nghi_id == r.id, CanTruTune.status != "huy").first() is None:
            continue
        for i in json.loads(r.trip_ids or "[]"):
            ra[i] = r
    return ra


def _dong_chu_xe(db, owner_id, bo_qua=None):
    """Phiếu xe thuê đã khoá, chưa trả, KHÔNG nằm trong đề nghị trả còn hiệu lực (_dang_giu)."""
    from services import tra_chu_xe as TC
    dang = _dang_giu(db, owner_id, bo_qua)
    return [x for x in TC.cho_tra(db, owner_id) if x["id"] not in dang and not x["owner_paid"]]


def cho_tra_chu_xe(db, owner_id, thay_tien=True):
    """Màn Xe liên kết: phiếu chờ đề nghị trả + các lần đề nghị (mới trước)."""
    ds = db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id == owner_id).order_by(ChiChuXeTune.created_at.desc()).limit(30).all()
    return {"cho": _dong_chu_xe(db, owner_id), "de_nghi": [xuat_chu_xe(r, thay_tien) for r in ds], "o_ke_toan": chi_o_ke_toan()}


def chuan_bi_can_tru(db, chon):
    """Trước khi lập đề nghị: phiếu có dầu / phụ tùng kho xuất bán phải có SO nhiên liệu (chặn, nói rõ "tạo SO trước"); đọc lại CÒN
    NỢ các SO từ hệ kế toán — bắt buộc đọc được, không cấn trừ theo số cũ — rồi tính lại phần cấn trừ / còn trả từng phiếu
    (tra_chu_xe.phan_tra). `chon`: dòng dong_phieu của các phiếu chọn. Commit phần đọc lại."""
    from services import so_nhien_lieu as NL
    from services import tra_chu_xe as TC
    thieu = [x for x in chon if x.get("cho_so")]
    if thieu:
        _loi("CHUA_TAO_SO_NHIEN_LIEU", "Phiếu %s có dầu / phụ tùng kho EPL xuất bán cho đối tác mà chưa có SO nhiên liệu — KT Thu/Chi bấm «Tạo SO "
                                       "bên kế toán» (màn Đề nghị thu) cho phiếu đó trước, rồi mới lập đề nghị trả." % ", ".join(
                                           x.get("doc_no") or x["id"] for x in thieu), 409)
    so = [b for b in (NL.so_cua(db, db.get(Trip, x["id"])) for x in chon) if b is not None and b.status == "synced"]
    if not so:
        return chon
    kq = NL.doc_thu(db, so)
    db.commit()
    hong = [b for b in so if b.thu_loi]
    if kq["loi"] or hong:
        _loi("KHONG_DOC_DUOC_SO_NHIEN_LIEU", "Không đọc được còn nợ SO nhiên liệu %s từ hệ kế toán (%s) — chưa cấn trừ được, thử lại sau."
             % (", ".join(b.order_code for b in hong) or "", kq["loi"] or hong[0].thu_loi), 502)
    lai = TC.so_lieu(db, [x["id"] for x in chon])                 # tính lại theo còn nợ vừa đọc
    return [dict(x, **{c: lai[x["id"]][c] for c in TC.COT_TAT_TOAN if c in lai.get(x["id"], {})}) for x in chon]


def de_nghi_tra_chu_xe(db, owner_id, trip_ids, phuong_thuc, user):
    """Lập ĐỀ NGHỊ TRẢ ĐỐI TÁC (chủ xe liên kết) — tất toán đối tác, chủ dự án chốt 02/10:
      1. phiếu chọn: cùng chủ xe, đã khoá, chưa trả, chưa nằm đề nghị khác, cùng tiền thuê;
      2. phiếu có xuất bán phải có SO nhiên liệu; đọc lại còn nợ SO → mỗi phiếu: còn trả = tiền thuê − phí − quá tải − tạm ứng EPL
         đưa − nợ NCC EPL trả thay − phần SO nhiên liệu còn nợ cấn trừ (tra_chu_xe.phan_tra);
      3. trừ hàng chủ xe mua ở quầy (tra_chu_xe.tru_hang_quay — kho tạm tắt thì 503, không lập; kho QLSX 06/10: SO bán hàng còn nợ
         của đối tác bên hệ kế toán, đọc không được thì không lập) → SỐ TRẢ THỰC;
      4. bên kế toán: CẤN TRỪ từng SO nhiên liệu và (06/10) từng SO bán hàng mua ở quầy bị trừ (collection-offset → phiếu TKN), rồi
         phiếu chi "Chi khác" Nợ 4022 / Có tiền cho phần còn lại (mỗi phiếu xe một dòng). Còn lại ≤ 0 (cấn trừ hết) thì không có phiếu
         chi: đề nghị xong khi cấn trừ xong, các phiếu thành "đã trả" ("TUNE:<số đề nghị>").
    Phiếu bán quầy bị trừ được GIỮ CHỖ ở kho tạm TRƯỚC khi gọi hệ kế toán. Hỏng giữa chừng → đề nghị "loi", gửi lại làm tiếp đúng
    bước hỏng (cùng khoá); bỏ đề nghị thì bỏ cả cấn trừ đã làm."""
    from models import CanTruTune
    from services import so_nhien_lieu as NL
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
    chon = chuan_bi_can_tru(db, chon)
    can = [x for x in chon if (x.get("can_tru_lak") or 0) > 0]
    # hàng chủ xe mua ở quầy chờ trừ — kho tạm: phiếu bán kho tạm (tắt thì 503); kho QLSX (06/10): SO bán hàng còn nợ của đối tác bên
    # hệ kế toán (đọc không được thì ném, không lập — không trả dư cho đối tác)
    kq = TC.tru_hang_quay(db, owner_id, TC.sau_can_tru(chon), user)
    quay = [h for h in kq["hang"] if h.get("loai") == TC.LOAI_QUAY]
    if (kq["tra_thuc"] or 0) <= 0 and not can and not quay:
        _loi("KHONG_CON_PHAI_TRA", "Còn phải trả %s %s ≤ 0 (tổng phiếu %s, đã trừ hàng mua ở quầy %s, EPL đã ứng trừ sẵn trên phiếu) — "
                                   "không lập phiếu chi." % (kq["tra_thuc"], ccy, kq["tong"], kq["tru"]), 409)
    now = dt.datetime.utcnow()
    so = "TCX-%s-%s" % (now.strftime("%y%m%d%H%M%S"), owner_id[:4])
    kq["can_tru"] = [{"trip_id": x["id"], "doc_no": x.get("doc_no"), "order_code": x.get("so_nhien_lieu"), "can_tru": x.get("can_tru"),
                      "can_tru_lak": x.get("can_tru_lak"), "tra_truoc_can_tru": x.get("tra_truoc_can_tru")} for x in can]
    rec = ChiChuXeTune(owner_id=owner_id, trip_ids=json.dumps([x["id"] for x in chon]), currency=ccy, amount=max(0, kq["tra_thuc"]),
                       amount_lak=max(0, kq["tra_thuc_lak"]), phuong_thuc=phuong_thuc, ref_no=so, status="loi", attempts=0,
                       created_by=getattr(user, "full_name", None), tru_hang=json.dumps(dict(kq, chot=False), ensure_ascii=False))
    db.add(rec)
    db.flush()
    for x in can:
        p = db.get(Trip, x["id"])
        ma_so = x["so_nhien_lieu"]
        ly_do = NL.ly_do_can_tru(p.doc_no)          # NGẮN: bên kế toán tự ghép số đề nghị, số SO, số TKN vào diễn giải (UAT 03/10)
        db.add(CanTruTune(de_nghi_id=rec.id, trip_id=p.id, do_id=NL.ma_do(p), order_code=ma_so, currency=NL.TIEN, amount=x["can_tru_lak"],
                          ref_no=so, idempotency_key=NL.khoa_can_tru(so, ma_so), status="loi", created_by=getattr(user, "full_name", None),
                          request_body=json.dumps(NL.goi_can_tru(ma_so, x["can_tru_lak"], so, ly_do), ensure_ascii=False,
                                                  separators=(",", ":"))))
    # 06/10: SO bán hàng đối tác mua ở quầy (hệ kế toán) bị trừ → CẤN TRỪ cả SO đó (collection-offset, cùng đường SO nhiên liệu): một SO
    # một dòng can_tru_tune, không theo chuyến (trip_id trống), tiền theo tiền của SO. Cấn trừ là cách "giữ chỗ" bên đó — bỏ đề nghị thì
    # huy_chu_xe gỡ cùng các lần cấn trừ khác.
    for h in quay:
        db.add(CanTruTune(de_nghi_id=rec.id, trip_id=None, do_id=None, order_code=h["so"], currency=h["currency"], amount=h["total"],
                          ref_no=so, idempotency_key=NL.khoa_can_tru(so, h["so"]), status="loi", created_by=getattr(user, "full_name", None),
                          request_body=json.dumps(NL.goi_can_tru(h["so"], h["total"], so, NL.ly_do_quay(), tien=h["currency"],
                                                                 ty_gia=h.get("ty_gia")), ensure_ascii=False, separators=(",", ":"))))
    db.flush()
    TC.giu_hang_quay(db, rec.ref_no, owner_id, _hang_kho_tam(kq), user)   # phiếu bán kho tạm: giữ chỗ TRƯỚC khi gọi hệ kế toán; lỗi → ném
    db.commit()
    try:
        _tien_hanh(db, rec, o, TK, user)
    except HTTPException as e:
        if isinstance(e.detail, dict):                   # đề nghị đã lập (trạng thái "loi") — màn biết số để gửi lại / bỏ
            e.detail.setdefault("so", rec.ref_no)
            e.detail.setdefault("de_nghi_id", rec.id)
        raise
    return rec


def _tru(rec):
    try:
        return json.loads(rec.tru_hang) if rec.tru_hang else None
    except ValueError:
        return None


def _hang_kho_tam(t):
    """Mã các PHIẾU BÁN KHO TẠM bị trừ trong một đề nghị (giữ chỗ / chốt / trả lại ở kho tạm). SO bán hàng ở hệ kế toán (06/10,
    loai so_quay) không thuộc đây — chúng đi bằng cấn trừ (can_tru_tune)."""
    from services import tra_chu_xe as TC
    return [h["id"] for h in (t or {}).get("hang") or [] if h.get("loai") != TC.LOAI_QUAY]


def _tra_tung_phieu(db, rec):
    """Số TRẢ THỰC từng phiếu của đề nghị (sau cấn trừ, sau hàng quầy) — ghi vào bản chép "đã trả" trên phiếu. Đề nghị cũ chưa
    lưu số từng phiếu thì tính lại theo tinh_phieu."""
    from services import tra_chu_xe as TC
    t = _tru(rec)
    if t and t.get("dong"):
        return [{"trip_id": d["trip_id"], "tra_chu_xe": d.get("tra_thuc"), "tra_chu_xe_lak": d.get("tra_thuc_lak")} for d in t["dong"]]
    so = TC.so_lieu(db, json.loads(rec.trip_ids or "[]"))
    return [{"trip_id": i, "tra_chu_xe": x["tra_chu_xe"], "tra_chu_xe_lak": x["tra_chu_xe_lak"]} for i, x in so.items()]


def _tien_hanh(db, rec, o, TK, user=None):
    """Làm (tiếp) một đề nghị: cấn trừ từng SO nhiên liệu (gửi lại đúng khoá), rồi phiếu chi phần còn lại; cấn trừ hết thì đề nghị xong
    ngay. Hỏng ở bước nào → đề nghị "loi" kèm câu lỗi, ném lại; gửi lại làm tiếp từ bước hỏng."""
    from types import SimpleNamespace
    from services import so_nhien_lieu as NL
    from services import tra_chu_xe as TC
    cts = [ct for ct in _can_tru_cua(db, rec) if ct.status != "huy"]
    for ct in cts:
        if ct.status == "da_gui":
            continue
        try:
            NL.gui_can_tru(db, ct)
        except HTTPException as e:
            d = e.detail if isinstance(e.detail, dict) else {}
            rec.status, rec.error_code = "loi", d.get("ma")
            rec.error_message = "Cấn trừ %s %s: %s" % (NL.ten_so(ct), ct.order_code, d.get("loi") or str(e.detail))
            rec.attempts, rec.last_attempt_at = (rec.attempts or 0) + 1, dt.datetime.utcnow()
            db.commit()
            raise
    if (rec.amount or 0) > 0:
        _gui_chu_xe(db, rec, o, TK, user)
        return rec
    # cấn trừ hết: không có phiếu chi — đề nghị xong, các phiếu "đã trả" theo số đề nghị
    rec.status, rec.error_code, rec.error_message = "da_chi", None, None
    rec.post_by, rec.post_at = getattr(user, "full_name", None), dt.datetime.utcnow()
    TC.danh_dau_tra(db, SimpleNamespace(full_name="%s (cấn trừ SO nhiên liệu)" % (getattr(user, "full_name", None) or "kế toán"),
                                        role="acct"), TC.TIEN_TO_TUNE + rec.ref_no, _tra_tung_phieu(db, rec))
    return rec


def _gui_chu_xe(db, rec, o, TK, user=None):
    from services import tra_chu_xe as TC
    rec.attempts, rec.last_attempt_at = (rec.attempts or 0) + 1, dt.datetime.utcnow()
    try:
        obj = rec.obj_id = doi_tuong(db, "chu_xe", o.id, o.name, sdt=getattr(o, "phone", None), to_chuc=False)
        co = TK.ma_tien(rec.phuong_thuc, rec.currency)
        ma_cur, hom_nay = ma_tien(rec.currency), dt.date.today()
        ty = round((rec.amount_lak or 0) / rec.amount, 6) if rec.amount else 1
        # dòng phiếu chi = SỐ TRẢ THỰC từng phiếu sau cấn trừ SO nhiên liệu và hàng quầy (đề nghị cũ chưa có tru_hang: theo phiếu);
        # phiếu trừ hết thì bỏ
        kq = _tru(rec) or TC.tinh_tru(list(TC.so_lieu(db, json.loads(rec.trip_ids or "[]")).values()), [])
        dong = [d for d in kq["dong"] if d.get("tra_thuc")]
        dien_giai = "Trả chủ xe liên kết %s: %s" % (o.name, ", ".join(str(d.get("doc_no")) for d in kq["dong"]))
        if kq.get("can_tru"):
            dien_giai += " · đã cấn trừ SO nhiên liệu %s" % ", ".join(str(c.get("order_code")) for c in kq["can_tru"])
        if kq.get("hang"):
            # 06/10: SO bán hàng ở hệ kế toán (so_quay) — đã cấn trừ bằng TKN như SO nhiên liệu; phiếu bán kho tạm (cũ) — trừ thẳng
            dien_giai += (" · đã cấn trừ mua ở quầy SO %s" if any(h.get("loai") == TC.LOAI_QUAY for h in kq["hang"])
                          else " · trừ hàng mua ở quầy %s") % ", ".join(str(h.get("doc_no")) for h in kq["hang"])
        can = {c["trip_id"] for c in kq.get("can_tru") or []}
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
                             "Description": ("Trả chủ xe phiếu %s" % d["doc_no"]) + (" · sau cấn trừ SO nhiên liệu" if d["trip_id"] in can else "")
                                            + (" · trừ hàng mua ở quầy" if (d.get("tru") or 0) > 0 else ""),
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
    """Lần trước hỏng: làm tiếp đúng bước hỏng (cấn trừ còn thiếu, rồi phiếu chi) cho đúng các phiếu đó nếu còn chờ trả — số trả
    thực, phần cấn trừ đứng yên như lúc lập. Có phiếu không còn chờ trả → bỏ đề nghị (gỡ cấn trừ, trả hàng quầy) rồi báo lập mới."""
    from services import tai_khoan as TK
    if rec.status != "loi":
        _loi("KHONG_GUI_LAI", "Đề nghị này đang %s — không gửi lại." % rec.status, 409)
    o = db.get(Owner, rec.owner_id)
    ids = json.loads(rec.trip_ids or "[]")
    con = {x["id"]: x for x in _dong_chu_xe(db, rec.owner_id, bo_qua=rec.id)}
    if any(i not in con for i in ids):
        huy_chu_xe(db, rec, user)                         # gỡ cấn trừ + phiếu bán giữ chỗ; lỗi → ném, đề nghị giữ "lỗi"
        _loi("PHIEU_KHONG_HOP_LE", "Có phiếu trong đề nghị không còn chờ trả — đã bỏ đề nghị, lập đề nghị mới.", 409)
    return _tien_hanh(db, rec, o, TK, user)


def _chot_hang(db, rec, user=None):
    """Đề nghị đã chi (phiếu chi bên kế toán đã ghi sổ): chốt các phiếu bán bị trừ "TUNE:<số phiếu chi>" ở kho tạm + bút toán chờ
    Nợ 4022 / Có 707 (tra_chu_xe.chot_hang_quay). Lỗi thì KHÔNG ném — tiền đã đi, phiếu bán vẫn giữ chỗ; lần gọi sau thử lại."""
    from services import tra_chu_xe as TC
    t = _tru(rec)
    if rec.status != "da_chi" or not t or not t.get("hang") or t.get("chot"):
        return
    try:
        # 06/10: SO bán hàng ở hệ kế toán (so_quay) đã cấn trừ bằng TKN — bên đó ghi bút toán cấn trừ cùng lúc, không chốt / không ghi
        # Nợ 4022 / Có 707 ở đây (ghi nữa là trừ phải trả đối tác hai lần); chỉ phiếu bán kho tạm (cũ) mới chốt
        ids = _hang_kho_tam(t)
        if ids:
            TC.chot_hang_quay(db, rec.ref_no, rec.document_no or rec.real_id, rec.owner_id, ids, user,
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
    """Đọc lại phiếu chi trả chủ xe; đã ghi sổ thì các phiếu thành "đã trả" (tra_chu_xe.danh_dau_tra — số trả thực từng phiếu của
    đề nghị), rồi chốt hàng quầy bị trừ (lỗi chốt không ném — đề nghị đã chi mà chưa chốt thì lần gọi sau thử lại)."""
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
        TC.danh_dau_tra(db, SimpleNamespace(full_name="%s (hệ kế toán)" % (rec.post_by or "thủ quỹ"), role="cash"),
                        "TUNE:%s" % (rec.document_no or rec.real_id), _tra_tung_phieu(db, rec))
    db.commit()
    _chot_hang(db, rec, user)
    return rec


def huy_chu_xe(db, rec, user=None):
    """Bỏ đề nghị chưa xong: xoá phiếu chi bên kế toán (nếu có, chưa ghi sổ), BỎ CẤN TRỪ SO nhiên liệu đã làm (collection-offset/cancel),
    trả các phiếu bán đang giữ chỗ về chờ trừ — các phiếu về lại "chờ trả". Đã chi (hoặc cấn trừ hết đã xong) → 409. Hỏng giữa
    chừng → giữ phần đã bỏ (ghi lại), ném; bấm bỏ lần nữa làm tiếp."""
    from services import so_nhien_lieu as NL
    if rec.status == "da_gui":
        try:
            dong_bo_chu_xe(db, rec, user)
        except HTTPException:
            if rec.error_code != MAT:
                raise
    if rec.status == "da_chi":
        _loi("DA_CHI_O_KE_TOAN", ("Phiếu chi %s đã ghi sổ bên kế toán — không huỷ được ở đây." % (rec.document_no or rec.real_id))
             if rec.real_id else "Đề nghị %s đã cấn trừ xong SO nhiên liệu, các phiếu đã trả — không huỷ được ở đây; đối soát ở hệ kế "
                                 "toán." % rec.ref_no, 409)
    if rec.real_id and rec.error_code != MAT:          # phiếu bên đó đã mất thì coi như đã rút xong
        _goi("POST", "/api/v1/accounting/cmpayment-receipt/delete", {"DocumentId": int(rec.real_id), "VoucherType": "CMP"})
        rec.real_id, rec.status = None, "loi"          # đã rút bên đó: lần bỏ sau không gọi xoá lần nữa
        rec.error_message = "Đang bỏ đề nghị — đã rút phiếu chi %s bên kế toán." % (rec.document_no or "")
        db.commit()
    try:
        for ct in _can_tru_cua(db, rec):
            NL.huy_can_tru(db, ct)
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {}
        rec.status, rec.error_code, rec.error_message = "loi", d.get("ma"), "Đang bỏ đề nghị — %s" % (d.get("loi") or e.detail)
        db.commit()
        raise
    db.commit()
    if _hang_kho_tam(_tru(rec)):                          # 06/10: SO bán hàng ở hệ kế toán đã gỡ cùng các lần cấn trừ ở trên
        from services import tra_chu_xe as TC
        TC.tha_hang_quay(db, rec.ref_no, user)            # phiếu bán giữ chỗ về chờ trừ; lỗi → ném
    rec.status = "huy"
    db.commit()
    return rec


def xuat_chu_xe(rec, thay_tien=True):
    from sqlalchemy.orm import object_session
    from services import so_nhien_lieu as NL
    db = object_session(rec)
    cts = _can_tru_cua(db, rec) if db is not None and rec.id else []
    return {"id": rec.id, "owner_id": rec.owner_id, "trip_ids": json.loads(rec.trip_ids or "[]"), "ref_no": rec.ref_no,
            "currency": rec.currency, "amount": rec.amount if thay_tien else None, "amount_lak": rec.amount_lak if thay_tien else None,
            "phuong_thuc": rec.phuong_thuc, "status": rec.status, "document_no": rec.document_no, "real_id": rec.real_id,
            "tune_status": rec.tune_status, "post_by": rec.post_by,
            "post_at": rec.post_at.isoformat(timespec="minutes") + "+00:00" if rec.post_at else None,
            "error_code": rec.error_code, "error_message": rec.error_message, "attempts": rec.attempts, "created_by": rec.created_by,
            "created_at": rec.created_at.isoformat(timespec="minutes") + "+00:00" if rec.created_at else None,
            "tru_hang": _xuat_tru(rec, thay_tien),
            # cấn trừ SO nhiên liệu của đề nghị (02/10)
            "can_tru": [dict(NL.xuat_can_tru(ct), **({} if thay_tien else {"tien": None})) for ct in cts]}


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
    # 06/10: đường ĐỌC — chỉ tìm (khách có mã mà bên kế toán không có → báo MA_KHONG_CO_BEN_KE_TOAN như cũ, không tạo)
    obj = doi_tuong(db, "khach", k.id, k.name, ma=k.code.strip(), chi_tim=True)
    db.commit()
    return cong_no_doi_tuong(obj, k.code)


def cong_no_doi_tac(db, o):
    """Công nợ của ĐỐI TÁC (chủ xe liên kết) bên hệ kế toán — SO nhiên liệu đứng tên đối tác (02/10). Đối tác là đối tượng
    EPLCX-<owner_id> (tạo khi lập phiếu chi / SO nhiên liệu đầu tiên); đường đọc này không tạo (06/10)."""
    # 06/10: đường ĐỌC (màn Tất toán đối tác, cấn trừ, đồng bộ nền) — chỉ tìm, không upsert danh mục bên kế toán. Đối tác chưa có
    # bên đó thì chưa có SO / công nợ nào: trả công nợ rỗng, không gọi customer-detail
    ma = LOAI_DOI_TUONG["chu_xe"][1] + o.id
    obj = doi_tuong(db, "chu_xe", o.id, o.name, sdt=getattr(o, "phone", None), to_chuc=False, chi_tim=True)
    db.commit()
    if obj is None:
        return {"customer_code": ma, "obj_id": None, "tong": {}, "tuoi_no": [], "no": [], "thu": [], "don": [], "chua_co_doi_tuong": True}
    return cong_no_doi_tuong(obj, ma)


def cong_no_doi_tuong(obj, ma):
    """customer-detail của một đối tượng bên kế toán (OBJ_AUTOID `obj`), dịch gọn."""
    kq = _goi("POST", "/api/v1/sales/debt/customer-detail", {"CustomerObjectId": obj, "OrgId": _cfg("QLSX_ORG_ID", 1368)}) or {}
    s = kq.get("Summary") or {}
    return {
        "customer_code": ma, "obj_id": obj,
        "tong": {"no": s.get("TotalDebt"), "con_no": s.get("CurrentDebt"), "qua_han": s.get("OverdueDebt"), "da_thu": s.get("TotalCollected"),
                 "so_chung_tu": s.get("UnsettledCount"), "qua_han_ngay": s.get("MaxOverdueDays"), "rui_ro": s.get("RiskLevel")},
        "tuoi_no": [{"ma": a.get("BucketCode"), "ten": a.get("BucketName"), "tien": a.get("Amount"), "pct": a.get("PercentValue")}
                    for a in (kq.get("Aging") or [])],
        # `nguon` (06/10) = TicketOrder.OrderSource bên đó gắn vào dòng nợ: LOGISTICS (SO cước) · LOGISTICS_FUEL (SO nhiên liệu) · khác
        # = SO bán hàng thường (mua ở quầy…) — tra_chu_xe.so_quay tách SO quầy theo trường này; DB bên đó chưa áp script thì None
        "no": [{"so": d.get("OrderCode"), "phieu_ban": d.get("RETK_CODE"), "ngay": d.get("RETK_TIMECLOSETICKET"), "han": d.get("RCTD_EXPIRE"),
                "tien": d.get("RETK_PAYMENTAMOUNT"), "da_tra": _da_tra(d), "con_no": d.get("RCTD_DEBTMONEY"),
                "ccy": d.get("CurrencyCode"), "trang_thai": d.get("DebtStatus"), "tuoi": d.get("AgingDays"),
                "nguon": d.get("OrderSource")} for d in (kq.get("Debts") or [])],
        "thu": kq.get("Collections") or [],
        "don": [{"so": o.get("OrderCode"), "ngay": o.get("OrderDate"), "tien": o.get("FinalTotalAmount"), "ccy": o.get("CurrencyCode"),
                 "trang_thai": o.get("StatusName")} for o in (kq.get("Orders") or [])],
    }
