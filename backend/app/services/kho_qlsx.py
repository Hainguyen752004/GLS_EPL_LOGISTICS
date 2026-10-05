# -*- coding: utf-8 -*-
"""KHO EPL Ở HỆ ANH TUNE (QLSX) — chủ dự án duyệt 05/10: kho EPL chuyển hẳn sang source anh Tune, bỏ kho tạm EPL_KETOAN 8031.

Công tắc `KHO_NGUON` (biến môi trường): `qlsx` (mặc định) — tồn, giá vốn, xuất / huỷ xuất phụ tùng đi qua API kho bên đó;
`kho_tam` — đường cũ qua kho tạm (services/goi_ke_toan.py), chỉ để quay lui. Mọi chỗ gọi kho vẫn đi qua services/kho_ke_toan.py
(KK.*, KK.GiaoDichKho) — tệp đó rẽ sang đây khi bat().

API bên anh Tune (GLS-QLSX-APIs LogisticsStockController, cùng gốc + token với gui_tune.cau_hinh — tài khoản tích hợp 846):
    GET  /api/v1/integrations/logistics/stock-balance?warehouseCodes=&itemCodes=&asOfDate=   → {rows:[{warehouseCode, itemCode,
         qty, avgUnitCost, amount, inQty, outQty…}]}
    POST /api/v1/integrations/logistics/stock-issues   (Idempotency-Key = SourceRef)  {Purpose INTERNAL|PARTNER_SALE, DocumentDate,
         ObjectCode (EPLCX-… bắt buộc với PARTNER_SALE), SalesOrderCode?, Description, Lines:[{ItemCode, WarehouseCode, Qty, Note}]}
         → {documentId, documentNo, lines:[{itemCode, warehouseCode, qty, unitCost, amount}], replayed}; vượt tồn → 409
         LOGISTICS_STOCK_INSUFFICIENT
    GET  …/stock-issues/{sourceRef} · POST …/stock-issues/cancel {SourceRef, Reason} · POST …/stock-receipts (Idempotency-Key)
         {DocTypeId 53|40, DocumentDate, ObjectCode?, Description, Lines:[{ItemCode, WarehouseCode, Qty, UnitCost}]}

Mã: kho = fuel_places.code (KHO-TB…), kho phụ tùng KHO-PT (KHO_PT_MA); dầu EPLNL-diesel, phụ tùng EPLPT-<parts.id>.
SourceRef ổn định, không có "/": `EPLLAO:<khoá>` (khoá = "trip_expense:<mã dòng>"…). Dòng chi đã xuất mang
stock_move_id = "qlsx:<số phiếu kho>" (cùng tiền tố với cấp dầu theo phiếu đề nghị — services/ban_giao_dau.TIEN_TO_MV).
Mất mạng / bên kia lỗi 5xx: báo rõ, không ghi gì nửa vời (GiaoDichKho gửi lệnh huỷ theo đúng SourceRef nếu chưa rõ bên kia ghi chưa).
"""
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit

from fastapi import HTTPException

from services import gui_tune as GT

DUONG = "/api/v1/integrations/logistics"
TIEN_TO_MV = "qlsx:"
MA_DAU = "EPLNL-diesel"
TIEN_TO_PT = "EPLPT-"
KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,99}$")


def nguon():
    return (os.getenv("KHO_NGUON") or "qlsx").strip().lower()


def bat():
    """Kho đi qua hệ anh Tune (mặc định). `KHO_NGUON=kho_tam` → đường cũ qua kho tạm."""
    return nguon() != "kho_tam"


def kho_pt():
    return (os.getenv("KHO_PT_MA") or "KHO-PT").strip()


def ma_pt(part_id):
    return TIEN_TO_PT + str(part_id)


def sr(khoa):
    """SourceRef / Idempotency-Key từ khoá chống trùng của dòng ("trip_expense:<mã>") — ổn định, chỉ [A-Za-z0-9_.:-], ≤ 100."""
    k = re.sub(r"[^A-Za-z0-9_.:\-]", ".", "EPLLAO:" + str(khoa))[:100]
    if not KEY.match(k):
        _loi("KHO_KHOA_SAI", "Không dựng được khoá kho hợp lệ từ %s." % khoa)
    return k


def la_mv(mv):
    return bool(mv) and str(mv).startswith(TIEN_TO_MV)


def _loi(ma, loi, http=422, **them):
    raise HTTPException(http, dict({"ma": ma, "loi": loi}, **them))


def _goi(method, duong, body=None, key=None):
    """→ (http, thân dict | None). Mất mạng → 503 KHO_QLSX_KHONG_GOI_DUOC (chưa rõ bên kia ghi chưa — `chua_ro` trong detail)."""
    goc, token = GT.cau_hinh()
    if not token:
        _loi("CHUA_CO_TOKEN", "Chưa có token hệ kế toán (tài khoản tích hợp QLSX trong .env) — chưa gọi được kho.", 503)
    dau = {"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "EPL-LAO-Logistics/1.0 (kho)"}
    if body is not None:
        dau["Content-Type"] = "application/json"
    if key:
        dau["Idempotency-Key"] = key
    yc = urllib.request.Request(goc + duong, data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                                method=method, headers=dau)
    try:
        with urllib.request.urlopen(yc, timeout=GT.CHO_GIAY) as t:
            ma, tho = t.status, t.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        ma, tho = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                                        # noqa: BLE001 — mất mạng, hết giờ
        _loi("KHO_QLSX_KHONG_GOI_DUOC", "Không gọi được kho bên hệ kế toán (%s): %s — bên này chưa ghi gì, thử lại sau."
             % (urlsplit(goc).netloc, e), 503, chua_ro=True)
    try:
        than = json.loads(tho) if tho.strip() else None
    except ValueError:
        than = None
    if ma == 401:
        GT.quen_token()
    return ma, than


def _ket(ma, than, viec):
    """Envelope {Success, Code, Message, Result, ErrorDetail{ErrorCode}} → Result, hoặc HTTPException nói rõ."""
    if isinstance(than, dict) and than.get("Success") is True:
        return than.get("Result")
    d = than if isinstance(than, dict) else {}
    ma_loi = (d.get("ErrorDetail") or {}).get("ErrorCode") if isinstance(d.get("ErrorDetail"), dict) else None
    cau = d.get("Message") or "Kho bên hệ kế toán trả HTTP %s." % ma
    if ma_loi == "LOGISTICS_STOCK_INSUFFICIENT":
        _loi("VUOT_TON", "Kho không đủ hàng để %s: %s" % (viec, cau), 409, ma_qlsx=ma_loi)
    if ma == 401:
        _loi("QLSX_TOKEN_HET_HAN", "Token hệ kế toán sai hoặc đã hết hạn — lần sau máy đăng nhập lại.", 502)
    if (ma or 0) >= 500 or ma_loi == "LOGISTICS_STOCK_DATABASE_ERROR":
        _loi(ma_loi or "KHO_QLSX_LOI", "Kho bên hệ kế toán lỗi khi %s: %s" % (viec, cau), 503, chua_ro=True)
    _loi(ma_loi or "KHO_QLSX_TU_CHOI", "Kho bên hệ kế toán từ chối %s: %s" % (viec, cau), ma if ma in (400, 403, 404, 409, 422) else 422)


# ---------------------------------------------------------------- đọc
def ton(db, kho=(), hang=(), ngay=None):
    """Dòng tồn {warehouseCode, itemCode, qty, avgUnitCost, amount, inQty, outQty…}; nhớ trong một yêu cầu (db.info)."""
    k = ("_ton_qlsx", tuple(sorted(kho)), tuple(sorted(hang)), ngay)
    bang = db.info.setdefault("_ton_qlsx", {})
    if k not in bang:
        q = []
        if kho:
            q.append("warehouseCodes=" + quote(",".join(sorted(kho))))
        if hang:
            q.append("itemCodes=" + quote(",".join(sorted(hang))))
        if ngay:
            q.append("asOfDate=" + ngay.isoformat())
        ma, than = _goi("GET", DUONG + "/stock-balance" + ("?" + "&".join(q) if q else ""))
        bang[k] = list((_ket(ma, than, "đọc tồn") or {}).get("rows") or [])
    return bang[k]


def quen_ton(db):
    db.info.pop("_ton_qlsx", None)


def doc(db, source_ref):
    ma, than = _goi("GET", DUONG + "/stock-issues/" + quote(source_ref, safe=""))
    if ma == 404:
        return None
    return _ket(ma, than, "đọc phiếu xuất %s" % source_ref)


# ---------------------------------------------------------------- ghi
def xuat(db, source_ref, dong, *, muc_dich="INTERNAL", ngay=None, mo_ta=None, ma_doi_tuong=None, so_ban=None):
    """Phiếu xuất kho (loại 48, giá vốn bình quân di động) → Result {documentId, documentNo, lines[{unitCost, amount…}]}."""
    body = {"Purpose": muc_dich, "DocumentDate": ngay.isoformat() if ngay else None, "ObjectCode": ma_doi_tuong or None,
            "SalesOrderCode": so_ban or None, "Description": (mo_ta or source_ref)[:200], "Lines": dong}
    ma, than = _goi("POST", DUONG + "/stock-issues", {k: v for k, v in body.items() if v is not None}, key=source_ref)
    quen_ton(db)
    return _ket(ma, than, "xuất kho")


def huy(db, source_ref, ly_do):
    """Huỷ phiếu xuất theo SourceRef (trả tồn). Bên kia không thấy (404) = chưa từng ghi / đã huỷ → coi như xong."""
    ma, than = _goi("POST", DUONG + "/stock-issues/cancel", {"SourceRef": source_ref, "Reason": (ly_do or "Huỷ từ trang điều xe")[:500]})
    quen_ton(db)
    if ma == 404:
        return None
    return _ket(ma, than, "huỷ phiếu xuất %s" % source_ref)


def nhap(source_ref, dong, *, loai=53, ngay=None, mo_ta=None, ma_doi_tuong=None):
    """Phiếu nhập kho (DocTypeId 53 tồn đầu / 40 nhập mua) — công cụ chuyển tồn đầu dùng. Gọi lại cùng khoá → bản cũ (replayed)."""
    body = {"DocTypeId": loai, "DocumentDate": ngay.isoformat() if ngay else None, "ObjectCode": ma_doi_tuong or None,
            "Description": (mo_ta or source_ref)[:200], "Lines": dong}
    ma, than = _goi("POST", DUONG + "/stock-receipts", {k: v for k, v in body.items() if v is not None}, key=source_ref)
    return _ket(ma, than, "nhập kho")


def don_gia(kq):
    """Đơn giá vốn (LAK) của phiếu xuất một dòng: Σ amount / Σ qty các dòng trả về."""
    ds = (kq or {}).get("lines") or []
    sl = sum(float(x.get("qty") or 0) for x in ds)
    return round(sum(float(x.get("amount") or 0) for x in ds) / sl, 4) if sl else 0.0
