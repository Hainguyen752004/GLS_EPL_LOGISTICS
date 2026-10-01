# -*- coding: utf-8 -*-
"""GỬI BÚT TOÁN CHỜ sang hệ kế toán anh Tune — khoản không qua tiền (services/but_toan_cho.py) thành chứng từ bút toán bên đó.

Đường bên anh Tune (giao ước 01/10, đang dựng — chưa có trên máy chủ thật):
    POST {goc}/api/v1/integrations/logistics/journal-entries            Idempotency-Key = SourceRef
         {SourceRef, DocumentDate, CountryId, OrgId, FiciAutoId?, Description,
          Entries: [{DebitAccount, CreditAccount, Amount, ExchangeRate, CurrencyId, ObjectId, Note}]}
         → Result {DocumentId, DocumentNo, StatusId, IsExisting}      400: tài khoản sai danh mục (kèm danh sách)
    POST {goc}/api/v1/integrations/logistics/journal-entries/reverse    {SourceRef} → Result {DocumentId, Reversed}
    GET  {goc}/api/v1/integrations/logistics/journal-entries/{SourceRef} → Result {DocumentId, DocumentNo, StatusId} | 404

CỜ `QLSX_GUI_BUT_TOAN` (mặc định TẮT): bên đó phải áp script DB mới chạy được đường này. Tắt thì bút toán chỉ nằm ở trang
này để xem, như trước. Bật thì: ghi bút toán (khoá phiếu, tất toán…) tự gửi luôn — hỏng thì giữ "chờ gửi", ghi lỗi, gửi lại
bằng nút Gửi / Gửi hết; huỷ / rút bản đã gửi thì gửi đảo — đảo chưa được thì đánh "chờ đảo", Gửi hết thử lại.

Điều phải giữ (như gui_tune / chi_tune):
  * Idempotency-Key = SourceRef ổn định — gửi lại sau mất mạng / hết giờ không ghi hai lần (bên đó trả IsExisting).
  * Kết quả chưa rõ (mất mạng, 5xx) → lần sau HỎI LẠI (GET) trước khi gửi: bên đó đã có thì nhận số chứng từ đó.
  * Bản đã đảo mà nguồn ghi lại (mở khoá rồi khoá lại) → SourceRef mới "…-2", "…-3" (but_toan_cho._dat tăng `phien`).
  * Lỗi có thể về HTTP 200 kèm `Success: false` — đọc thân. 401 → bỏ token nhớ, đăng nhập lại (gui_tune.cau_hinh).
  * Token và gốc API dùng chung gui_tune.cau_hinh(); thử local: QLSX_BASE_URL. Không in token.
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit

from fastapi import HTTPException

from services import gui_tune as GT

DUONG = "/api/v1/integrations/logistics/journal-entries"
CHO_GIAY = 30
CHO_GIAY_TU_GUI = 8                       # tự gửi lúc ghi (khoá phiếu): không để người bấm khoá chờ lâu khi bên kia chậm / tắt
CHUA_RO = ("KHONG_GOI_DUOC", "HTTP_5XX")


def bat():
    """Có gửi bút toán sang hệ kế toán không — QLSX_GUI_BUT_TOAN=1 / true / bat / on. Mặc định tắt."""
    return (os.getenv("QLSX_GUI_BUT_TOAN") or "").strip().lower() in ("1", "true", "bat", "on", "yes")


def _loi(ma, loi, http=422):
    raise HTTPException(http, {"ma": ma, "loi": loi})


def _goi(method, duong, body=None, key=None, cho=CHO_GIAY):
    """→ (http, thân dict | None). Mất mạng → HTTPException 502 KHONG_GOI_DUOC; 401 → 502 QLSX_TOKEN_HET_HAN."""
    goc, token = GT.cau_hinh()
    if not token:
        _loi("CHUA_CO_TOKEN", "Chưa có token hệ kế toán (QLSX_ACCESS_TOKEN / tài khoản tích hợp / EPL_ACC_CODE_TOKEN).", 503)
    dau = {"Authorization": "Bearer " + token, "Content-Type": "application/json", "Accept": "application/json",
           "User-Agent": "EPL-LAO-Logistics/1.0 (but toan)"}
    if key:
        dau["Idempotency-Key"] = key
    yc = urllib.request.Request(goc + duong, data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                method=method, headers=dau)
    try:
        with urllib.request.urlopen(yc, timeout=cho) as t:
            ma, tho = t.status, t.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        ma, tho = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                                          # noqa: BLE001 — mất mạng, DNS, hết giờ: chưa rõ bên kia ghi chưa
        _loi("KHONG_GOI_DUOC", "Không gọi được hệ kế toán (%s): %s" % (urlsplit(goc).netloc, e), 502)
    try:
        than = json.loads(tho) if tho.strip() else None
    except ValueError:
        than = None
    if ma == 401 or (isinstance(than, dict) and than.get("Code") == 401):
        GT.quen_token()
        _loi("QLSX_TOKEN_HET_HAN", "Token hệ kế toán sai hoặc đã hết hạn — lần gửi sau máy đăng nhập lại.", 502)
    return ma, than


def _ket_qua(ma, than):
    """(Result | None, mã lỗi, câu lỗi). Thành công chỉ khi Success true (hoặc 2xx không phong bì) kèm Result."""
    if isinstance(than, dict) and than.get("Success") is True and isinstance(than.get("Result"), dict):
        return than["Result"], None, None
    if 200 <= ma < 300 and isinstance(than, dict) and than.get("DocumentId"):
        return than, None, None
    cau = ((than or {}).get("Message") or (than or {}).get("message")) if isinstance(than, dict) else None
    if ma >= 500:
        return None, "HTTP_5XX", "Hệ kế toán trả HTTP %s: %s" % (ma, cau or "lỗi máy chủ")
    if ma == 404:
        return None, "KHONG_CO_DUONG", "Hệ kế toán chưa có đường nhận bút toán (404) — bên đó chưa áp bản mới."
    if ma == 400 or (isinstance(than, dict) and than.get("Success") is False):
        r = (than or {}).get("Result") if isinstance(than, dict) else None
        sai = (r or {}).get("InvalidAccounts") or (r or {}).get("Accounts") if isinstance(r, dict) else (r if isinstance(r, list) else None)
        if sai or "tài khoản" in (cau or "").lower() or "account" in (cau or "").lower():
            return None, "TAI_KHOAN_SAI", "Hệ kế toán từ chối: %s%s" % (cau or "tài khoản không có trong danh mục",
                                                                       " (%s)" % ", ".join(str(x) for x in sai) if sai else "")
        return None, "BEN_KE_TOAN_TU_CHOI", "Hệ kế toán từ chối: %s" % (cau or "không rõ lý do")
    return None, "HTTP_%s" % ma, "Hệ kế toán trả HTTP %s: %s" % (ma, cau or "")


# ---------------------------------------------------------------- gói
def _doi_tuong(db, dtg):
    """OBJ_AUTOID bên kế toán cho {loai, ref_id} của một dòng (chi_tune.doi_tuong: EPLTX- · EPLCX- · EPLNCC- · EPLKH-)."""
    from models import Customer, Driver, Owner, Supplier
    from services import chi_tune as CHI
    if not dtg or not dtg.get("ref_id"):
        return None
    loai, i = dtg.get("loai"), dtg["ref_id"]
    if loai == "tai_xe":
        x = db.get(Driver, i)
        return CHI.doi_tuong_tai_xe(db, i, x.name if x else None)
    if loai == "chu_xe":
        x = db.get(Owner, i)
        return CHI.doi_tuong(db, "chu_xe", i, x.name if x else None, sdt=getattr(x, "phone", None), to_chuc=False)
    if loai == "ncc":
        x = db.get(Supplier, i)
        return CHI.doi_tuong(db, "ncc", i, x.name if x else None, to_chuc=True)
    if loai == "khach":
        x = db.get(Customer, i)
        return CHI.doi_tuong(db, "khach", i, x.name if x else None, sdt=getattr(x, "phone", None), dia_chi=getattr(x, "address", None),
                             to_chuc=getattr(x, "cust_type", None) == "company", ma=((x.code or "").strip() or None) if x else None)
    return None


def _ty_gia(d):
    if (d.get("ccy") or "LAK") == "LAK":
        return 1
    if d.get("ty_gia"):
        return float(d["ty_gia"])
    if d.get("tien_lak") and d.get("tien"):
        return round(float(d["tien_lak"]) / float(d["tien"]), 6)
    return 1


def dung_goi(db, rec):
    """Gói POST journal-entries từ một bút toán chờ. Đối tượng: `doi_tuong` của dòng (không có thì `doi_tuong_no`)."""
    from services import chi_tune as CHI
    dong = json.loads(rec.dong or "[]")
    if not dong:
        _loi("BUT_TOAN_RONG", "Bút toán %s không có dòng nào." % rec.source_ref, 409)
    tien = {}
    entries = []
    for d in dong:
        ccy = d.get("ccy") or "LAK"
        if ccy not in tien:
            tien[ccy] = CHI.ma_tien(ccy)
        e = {"DebitAccount": d["no"], "CreditAccount": d["co"], "Amount": d["tien"], "ExchangeRate": _ty_gia(d),
             "CurrencyId": tien[ccy], "ObjectId": _doi_tuong(db, d.get("doi_tuong") or d.get("doi_tuong_no")),
             "Note": (d.get("dien_giai") or rec.dien_giai or "")[:250] or None}
        entries.append(e)
    body = {"SourceRef": rec.source_ref, "DocumentDate": rec.ngay.isoformat(), "CountryId": CHI._cfg("QLSX_COUNTRY_ID", 11),
            "OrgId": CHI._cfg("QLSX_ORG_ID", 1368), "Description": (rec.dien_giai or rec.source_ref)[:250], "Entries": entries}
    try:
        body["FiciAutoId"] = CHI.ma_ky(rec.ngay)
    except HTTPException as e:
        if (e.detail or {}).get("ma") in ("KY_DA_DONG",):
            raise                                       # kỳ đã đóng: bên đó không ghi được, nói rõ
        # tuỳ chọn trong giao ước — không tra được kỳ thì để bên kia tự chọn theo ngày
    return body


def _ghi_ket_qua(rec, r):
    rec.status, rec.can_dao = "da_gui", False
    rec.ma_ben_ke_toan = str(r.get("DocumentId")) if r.get("DocumentId") is not None else rec.ma_ben_ke_toan
    rec.so_ben_ke_toan = r.get("DocumentNo") or rec.so_ben_ke_toan
    rec.tune_status = int(r["StatusId"]) if str(r.get("StatusId") or "").lstrip("-").isdigit() else rec.tune_status
    rec.gui_luc, rec.loi_gui, rec.error_code = dt.datetime.utcnow(), None, None


def hoi(db, rec):
    """GET journal-entries/{SourceRef}: bên đó có chứng từ chưa. Có → ghi số chứng từ (bản cho_gui thành da_gui). Trả Result | None."""
    ma, than = _goi("GET", DUONG + "/" + quote(rec.source_ref, safe=""))
    if ma == 404:
        return None
    r, ma_loi, cau = _ket_qua(ma, than)
    if r is None:
        _loi(ma_loi, cau, 502 if ma >= 500 else 422)
    _ghi_ket_qua(rec, r)
    return r


def gui(db, rec, commit=True, cho=CHO_GIAY):
    """Gửi MỘT bút toán cho_gui. Thành công → da_gui (số chứng từ bên kia). Hỏng → giữ cho_gui, ghi lỗi + số lần thử, ném lại.
    `commit=False`: gọi giữa giao dịch của người khác (tự gửi lúc ghi) — không commit, người gọi commit."""
    if rec is None or rec.status != "cho_gui":
        return rec
    rec.attempts = (rec.attempts or 0) + 1
    try:
        if rec.error_code in CHUA_RO and hoi(db, rec) is not None:       # lần trước chưa rõ: bên đó có rồi thì nhận luôn
            return _xong(db, rec, commit)
        body = dung_goi(db, rec)
        rec.request_body = json.dumps(body, ensure_ascii=False)
        ma, than = _goi("POST", DUONG, body, key=rec.source_ref, cho=cho)
        rec.response_body = (json.dumps(than, ensure_ascii=False, default=str) if than is not None else "")[:20000]
        r, ma_loi, cau = _ket_qua(ma, than)
        if r is None:
            _loi(ma_loi, cau, 502 if ma >= 500 else 422)
        _ghi_ket_qua(rec, r)
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {}
        rec.error_code, rec.loi_gui = d.get("ma") or "LOI", d.get("loi") or str(e.detail)
        if commit:
            db.commit()
        raise
    return _xong(db, rec, commit)


def _xong(db, rec, commit):
    if commit:
        db.commit()
    else:
        db.flush()
    return rec


def tu_gui(db, rec):
    """Ghi bút toán xong (but_toan_cho.ghi) mà cờ bật → gửi ngay, giữa giao dịch của người ghi. Hỏng thì thôi (lỗi nằm trên bản
    ghi, Gửi hết gửi lại) — không làm hỏng việc khoá phiếu / chốt tất toán."""
    if not bat() or rec is None or rec.status != "cho_gui":
        return rec
    try:
        gui(db, rec, commit=False, cho=CHO_GIAY_TU_GUI)
    except HTTPException:
        pass
    return rec


def dao(db, rec, commit=True):
    """Gửi bút toán đảo cho bản đã gửi (nguồn bị huỷ). Đảo xong → huy (can_dao bỏ). Chưa đảo được → can_dao, ném lại."""
    if rec is None or rec.status != "da_gui":
        return rec
    rec.attempts = (rec.attempts or 0) + 1
    try:
        ma, than = _goi("POST", DUONG + "/reverse", {"SourceRef": rec.source_ref}, key=rec.source_ref + ":dao")
        r, ma_loi, cau = _ket_qua(ma, than)
        if r is None and ma == 404:
            r = {"Reversed": True}                      # bên đó không có chứng từ này nữa — coi như đã đảo
        if r is None:
            _loi(ma_loi, cau, 502 if ma >= 500 else 422)
        if r.get("Reversed") is False:
            _loi("CHUA_DAO", "Hệ kế toán chưa đảo được chứng từ %s." % (rec.so_ben_ke_toan or rec.source_ref), 409)
        rec.status, rec.can_dao, rec.huy_luc = "huy", False, dt.datetime.utcnow()
        rec.loi_gui = rec.error_code = None
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {}
        rec.can_dao, rec.error_code, rec.loi_gui = True, d.get("ma") or "LOI", d.get("loi") or str(e.detail)
        if commit:
            db.commit()
        raise
    return _xong(db, rec, commit)


def cap_nhat(db, rec):
    """Hỏi lại bên kế toán một bản đã gửi (số chứng từ, trạng thái)."""
    if rec is None or rec.status != "da_gui":
        return rec
    hoi(db, rec)
    db.commit()
    return rec


def gui_het(db, gioi_han=100):
    """Nút Gửi hết: gửi mọi bản cho_gui (cũ trước) và đảo mọi bản chờ đảo. Bên kia không vào được (mất mạng, token) thì dừng."""
    from models import ButToanCho
    ds = (db.query(ButToanCho).filter((ButToanCho.status == "cho_gui") | ((ButToanCho.status == "da_gui") & ButToanCho.can_dao.is_(True)))
          .order_by(ButToanCho.ngay, ButToanCho.created_at).limit(gioi_han).all())
    ra = {"thu": 0, "da_gui": 0, "da_dao": 0, "loi": 0, "chi_tiet_loi": []}
    for r in ds:
        ra["thu"] += 1
        try:
            if r.status == "da_gui":
                dao(db, r)
                ra["da_dao"] += 1
            else:
                gui(db, r)
                ra["da_gui"] += 1
        except HTTPException as e:
            d = e.detail if isinstance(e.detail, dict) else {}
            ra["loi"] += 1
            if len(ra["chi_tiet_loi"]) < 10:
                ra["chi_tiet_loi"].append({"source_ref": r.source_ref, "ma": d.get("ma"), "loi": d.get("loi")})
            if d.get("ma") in ("KHONG_GOI_DUOC", "QLSX_TOKEN_HET_HAN", "CHUA_CO_TOKEN", "KHONG_CO_DUONG"):
                break
    return ra
