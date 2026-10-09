# -*- coding: utf-8 -*-
"""GỬI BÚT TOÁN CHỜ sang hệ kế toán anh Tune — khoản không qua tiền (services/but_toan_cho.py) thành chứng từ bút toán bên đó.

Đường bên anh Tune (GLS-QLSX-APIs `feat/HonTunedaHai@b9227aa`, LogisticsJournalEntryController; cần script
20261001_logistics_journal_entry.sql + mục cấu hình LogisticsJournalEntry — thiếu thì 503):
    POST {goc}/api/v1/integrations/logistics/journal-entries            Idempotency-Key = SourceRef
         {SourceRef, DocumentDate, Description, FiciAutoId?,
          Entries: [{DebitAccount, CreditAccount, Amount, ExchangeRate, CurrencyId, ObjectId, Note}]}
         (CountryId / OrgId gửi kèm nhưng bên đó lấy từ cấu hình; BaseAmount bên đó tự tính)
         → 201 Result {SourceRef, DocumentId, DocumentNo, StatusId (13 ghi sổ tạm), IsExisting} · gửi lại cùng nội dung → 200 IsExisting
         400 ErrorDetail {ErrorCode INVALID_ACCOUNTS, InvalidAccounts[]} · 409 LOGISTICS_JOURNAL_52512 cùng SourceRef khác nội dung
    POST {goc}/api/v1/integrations/logistics/journal-entries/reverse    {SourceRef} → Result {DocumentId, Reversed}
         Reversed=false + DocumentId null = không còn chứng từ đang hoạt động (đã gỡ trước đó) · 409 52515/52516 = chặn gỡ
    GET  {goc}/api/v1/integrations/logistics/journal-entries/{SourceRef} → Result {DocumentId, DocumentNo, StatusId, …} | 404

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
from services import loi_dich as LD

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


def _chi_tiet_loi(than):
    """ErrorDetail của phong bì lỗi bên đó → (ErrorCode | None, InvalidAccounts | None)."""
    ed = than.get("ErrorDetail") if isinstance(than, dict) else None
    if not isinstance(ed, dict):
        return None, None
    return ed.get("ErrorCode"), ed.get("InvalidAccounts")


BEN_DO_CHUA_BAT = ("LOGISTICS_JOURNAL_DISABLED", "LOGISTICS_JOURNAL_CONFIG_REQUIRED", "LOGISTICS_JOURNAL_SCRIPT_REQUIRED")


def _ket_qua(ma, than):
    """(Result | None, mã lỗi, câu lỗi). Thành công chỉ khi Success true (hoặc 2xx không phong bì) kèm Result.
    Lỗi bên đó có thể về HTTP 200 kèm `Success: false` và mã thật ở `Code` (lỗi chưa bắt: Code 500) — xếp theo mã thật đó."""
    if isinstance(than, dict) and than.get("Success") is True and isinstance(than.get("Result"), dict):
        return than["Result"], None, None
    if 200 <= ma < 300 and isinstance(than, dict) and than.get("DocumentId"):
        return than, None, None
    cau = ((than or {}).get("Message") or (than or {}).get("message")) if isinstance(than, dict) else None
    ma_ben_do, sai_ed = _chi_tiet_loi(than)
    that = than.get("Code") if isinstance(than, dict) and than.get("Success") is False and isinstance(than.get("Code"), int) else ma
    if ma_ben_do in BEN_DO_CHUA_BAT:
        return None, "BEN_DO_CHUA_BAT", "Hệ kế toán chưa bật đường nhận bút toán — bút toán giữ chờ gửi, bật xong bấm Gửi hết."
    if that >= 500 or ma >= 500:
        return None, "HTTP_5XX", "Hệ kế toán trả lỗi máy chủ (%s): %s" % (that, cau or "không rõ")
    if that == 404:
        return None, "KHONG_CO_DUONG", "Hệ kế toán chưa có đường nhận bút toán (404) — bên đó chưa áp bản mới."
    if that in (401, 403) or ma_ben_do == "LOGISTICS_JOURNAL_FORBIDDEN":
        return None, "KHONG_DUOC_PHEP", "Hệ kế toán chưa cho tài khoản kết nối gửi bút toán — nhờ bên kế toán cấp quyền."
    if that in (400, 409, 422) or (isinstance(than, dict) and than.get("Success") is False):
        r = (than or {}).get("Result") if isinstance(than, dict) else None
        sai = sai_ed or ((r or {}).get("InvalidAccounts") or (r or {}).get("Accounts") if isinstance(r, dict)
                         else (r if isinstance(r, list) else None))
        doan_chu = not ma_ben_do and that == 400 and any(t in (cau or "").lower() for t in ("tài khoản", "account"))
        if sai or ma_ben_do == "INVALID_ACCOUNTS" or doan_chu:
            return None, "TAI_KHOAN_SAI", "Hệ kế toán từ chối: %s%s" % (cau or "tài khoản không có trong danh mục",
                                                                       " (%s)" % ", ".join(str(x) for x in sai) if sai else "")
        if ma_ben_do == "LOGISTICS_JOURNAL_52512":
            return None, "KHAC_NOI_DUNG", ("Hệ kế toán đã có chứng từ cùng mã nguồn nhưng khác số liệu (từ một lần gửi trước) "
                                          "và chưa gỡ được — nhờ kế toán kiểm chứng từ đó trong hệ kế toán.")
        return None, "BEN_KE_TOAN_TU_CHOI", "Hệ kế toán từ chối: %s" % (cau or "không rõ lý do")
    return None, "HTTP_%s" % that, "Hệ kế toán trả HTTP %s: %s" % (that, cau or "")


def _http(ma_loi):
    """Mã HTTP trang điều xe trả cho người bấm: 502 khi lỗi phía bên kia / chưa rõ, 422 khi bên kia từ chối dữ liệu."""
    return 502 if ma_loi in ("HTTP_5XX", "KHONG_GOI_DUOC", "BEN_DO_CHUA_BAT", "KHONG_CO_DUONG", "KHONG_DUOC_PHEP") else 422


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


# Diễn giải / ghi chú dòng bên kế toán nằm ở PUBDOCUMENT.DOC_DESCRIPTION / PUBENTRY.ET_NOTE nvarchar(200) (DB Lào, đo 03/10) — thủ
# tục bên đó không cắt ngầm mà từ chối (52508); cắt ở 250 như trước thì diễn giải 201–250 ký tự làm hỏng cả bút toán.
DAI_DIEN_GIAI = 200


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
             "Note": (d.get("dien_giai") or rec.dien_giai or "")[:DAI_DIEN_GIAI] or None}
        entries.append(e)
    body = {"SourceRef": rec.source_ref, "DocumentDate": rec.ngay.isoformat(), "CountryId": CHI._cfg("QLSX_COUNTRY_ID", 11),
            "OrgId": CHI._cfg("QLSX_ORG_ID", 1368), "Description": (rec.dien_giai or rec.source_ref)[:DAI_DIEN_GIAI], "Entries": entries}
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


def hoi(db, rec, cho=CHO_GIAY):
    """GET journal-entries/{SourceRef}: bên đó có chứng từ chưa. Có → ghi số chứng từ (bản cho_gui thành da_gui). Trả Result | None."""
    ma, than = _goi("GET", DUONG + "/" + quote(rec.source_ref, safe=""), cho=cho)
    if ma == 404 and _chi_tiet_loi(than)[0] == "JOURNAL_ENTRY_NOT_FOUND":
        return None                                     # bên đó trả lời rõ: không có chứng từ (404 khác = chưa có đường)
    r, ma_loi, cau = _ket_qua(ma, than)
    if r is None:
        _loi(ma_loi, cau, _http(ma_loi))
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
        r, ma_loi, cau, ma = _post(db, rec, cho)
        if r is None and ma_loi == "KHAC_NOI_DUNG":
            # bên đó đã lưu chứng từ cùng SourceRef từ một lần gửi mất phản hồi, rồi nguồn đổi số: gỡ chứng từ cũ (bên đó cho
            # POST lại cùng SourceRef sau khi gỡ) rồi gửi bản đúng — không để hai sổ lệch nhau
            _go(rec)
            r, ma_loi, cau, ma = _post(db, rec, cho)
        if r is None:
            _loi(ma_loi, cau, _http(ma_loi))
        _ghi_ket_qua(rec, r)
    except HTTPException as e:
        d = e.detail if isinstance(e.detail, dict) else {}
        rec.error_code, rec.loi_gui = d.get("ma") or "LOI", d.get("loi") or str(e.detail)
        if commit:
            db.commit()
        raise
    return _xong(db, rec, commit)


def _post(db, rec, cho):
    body = dung_goi(db, rec)
    rec.request_body = json.dumps(body, ensure_ascii=False)
    ma, than = _goi("POST", DUONG, body, key=rec.source_ref, cho=cho)
    rec.response_body = (json.dumps(than, ensure_ascii=False, default=str) if than is not None else "")[:20000]
    return _ket_qua(ma, than) + (ma,)


def _go(rec):
    """POST reverse cho SourceRef của bản này. Gỡ xong (hoặc bên đó không còn chứng từ đang hoạt động) → trả; không → ném."""
    ma, than = _goi("POST", DUONG + "/reverse", {"SourceRef": rec.source_ref}, key=rec.source_ref + ":dao")
    r, ma_loi, cau = _ket_qua(ma, than)
    if r is None:                                       # 404 ở đây = chưa có đường (bên đó không bao giờ trả 404 khi gỡ)
        _loi(ma_loi, cau, _http(ma_loi))
    # Reversed=false + DocumentId null = bên đó không còn chứng từ đang hoạt động của SourceRef này (lần gỡ trước đã xong
    # mà mất phản hồi) — coi như đã gỡ. Bị chặn gỡ (đã khoá / ghi sổ chính thức) bên đó trả 409, không về đây.
    if r.get("Reversed") is False and r.get("DocumentId") is not None:
        _loi("CHUA_DAO", "Hệ kế toán chưa gỡ được chứng từ %s." % (rec.so_ben_ke_toan or rec.source_ref), 409)


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
        _go(rec)
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
            if d.get("ma") in ("KHONG_GOI_DUOC", "QLSX_TOKEN_HET_HAN", "CHUA_CO_TOKEN", "KHONG_CO_DUONG", "KHONG_DUOC_PHEP",
                               "BEN_DO_CHUA_BAT"):
                break
    return LD.them_dich(ra)                   # chi_tiet_loi: câu lỗi kèm bản Lào / Anh (services/loi_dich)
