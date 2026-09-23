# -*- coding: utf-8 -*-
"""ĐẨY CHỨNG TỪ sang module kế toán của anh Khang (Golden SME) — phiếu thu, phiếu chi, nhập kho, xuất
kho, hoá đơn… để bên đó vào sổ. Bên mình KHÔNG có sổ kế toán: đây chỉ là bưu tá.

Hợp đồng JSON đề nghị với anh Khang ở `DOCS/md/HOP_DONG_API_ANH_KHANG.md`. Tóm tắt:

    POST {EPL_KE_TOAN_API}/api/v1/epl-lao/vouchers      Authorization: Bearer <token>
    { "source": "EPL_LAO", "ref": "<số chứng từ bên mình>", "type": "PC_TU", "date": "2026-09-21", … }
    → 200/201 { "id": "<mã bên kế toán>" }               → tờ được đánh "đã đẩy", giữ mã của họ
    → 409 { "id": … }  (ref đã có)                         → cũng coi là đã đẩy, lấy mã trả về
    → khác / không nối được                                → tờ giữ nguyên, ghi lỗi để bấm đẩy lại

`ref` = số chứng từ bên mình (`PC_TU/2609/0003`) làm khoá chống trùng: đẩy hai lần cùng một tờ thì bên
kia chỉ có một phiếu. Cấu hình lấy từ bảng `cau_hinh` (Sếp đặt trong màn hình, không cần khởi động
lại), không có thì rơi về biến môi trường EPL_KE_TOAN_API / EPL_KE_TOAN_TOKEN. Token không bao giờ
ra tới trình duyệt.
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request

from services import mang as MANG

from models import CauHinh, ChungTu
from services import chung_tu as CT

DUONG_VOUCHERS = "/api/v1/epl-lao/vouchers"
HET_GIO = 15
# Loại chứng từ → nhóm nghiệp vụ bên kế toán hay dùng để rẽ phiếu (thu · chi · nhập kho · xuất kho · hoá đơn · khác)
NHOM = {
    "PT": "receipt", "PT_BAN": "receipt", "TT_THU": "receipt",
    "PC_TU": "payment", "PC_SC": "payment", "PC_NCC": "payment", "PC_CX": "payment", "TT_CHI": "payment",
    "PNK_NL": "stock_in", "PNK_PT": "stock_in", "PNK_HH": "stock_in",
    "PXK_NL": "stock_out", "PXK_PT": "stock_out", "PXK_HH": "stock_out", "PXK_BAN": "stock_out",
    "DC_HH": "stock_adjust", "CK_NL": "stock_transfer",
    "HD": "invoice", "HD_BAN": "invoice",
}


# ---------------------------------------------------------------- cấu hình
def cau_hinh(db, khoa, mac_dinh=""):
    r = db.get(CauHinh, khoa)
    if r and (r.gia_tri or "").strip():
        return r.gia_tri.strip()
    return (os.getenv("EPL_" + khoa.upper()) or mac_dinh).strip()


def dat_cau_hinh(db, khoa, gia_tri, user=None):
    r = db.get(CauHinh, khoa)
    if not r:
        r = CauHinh(khoa=khoa); db.add(r)
    r.gia_tri = (gia_tri or "").strip()
    r.cap_nhat = dt.datetime.utcnow()
    r.by_user = getattr(user, "full_name", None)
    return r


def trang_thai(db):
    """Đã cấu hình chưa, và lần đẩy gần nhất ra sao — để màn Sổ chứng từ nói thật với người dùng."""
    goc = cau_hinh(db, "ke_toan_api")
    tong = db.query(ChungTu).count()
    da = db.query(ChungTu).filter(ChungTu.da_day.is_(True)).count()
    loi = db.query(ChungTu).filter(ChungTu.loi_day.isnot(None), ChungTu.da_day.is_(False)).count()
    cuoi = db.query(ChungTu).filter(ChungTu.day_luc.isnot(None)).order_by(ChungTu.day_luc.desc()).first()
    return {"cau_hinh": bool(goc), "api": goc, "co_token": bool(cau_hinh(db, "ke_toan_token")),
            "tong": tong, "da_day": da, "chua_day": tong - da, "loi": loi,
            "day_gan_nhat": cuoi.day_luc.isoformat() if cuoi and cuoi.day_luc else None}


# ---------------------------------------------------------------- gói tin
def goi_tin(c):
    """Một tờ chứng từ bên mình → gói JSON gửi bên kế toán. Chỉ đổi tên trường, không tính lại gì."""
    try:
        pl = json.loads(c.payload) if c.payload else {}
    except ValueError:
        pl = {}
    ten = CT.LOAI.get(c.loai, (c.loai, c.loai, False))
    return {
        "source": "EPL_LAO",
        "ref": c.so,
        "type": c.loai,
        "type_name": ten[0],
        "group": NHOM.get(c.loai, "other"),
        "date": c.ngay.isoformat() if c.ngay else None,
        "trip_no": c.trip_doc_no,
        "party": {"kind": c.doi_tuong_loai, "name": c.doi_tuong_ten},
        "amount": {"value": c.tien, "currency": c.tien_te or "LAK", "lak": c.tien_lak},
        "entry": {"debit": c.no, "debit_name": c.no_ten, "credit": c.co, "credit_name": c.co_ten},
        "memo": c.mo_ta,
        "lines": pl,
        "created_by": c.by_user,
        "created_at": c.ts.isoformat() if c.ts else None,
    }


# ---------------------------------------------------------------- đẩy
def _goi_http(url, token, than):
    d = json.dumps(than, ensure_ascii=False).encode("utf-8")
    dau = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
    if token:
        dau["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=d, headers=dau, method="POST")
    try:
        with MANG.mo(r, timeout=HET_GIO) as t:
            return t.status, _doc_json(t.read())
    except urllib.error.HTTPError as e:
        return e.code, _doc_json(e.read())
    except (urllib.error.URLError, OSError) as e:
        return 0, {"loi": str(getattr(e, "reason", e))}


def _doc_json(b):
    try:
        return json.loads(b.decode("utf-8")) if b else {}
    except ValueError:
        return {"raw": b[:300].decode("utf-8", "replace")}


def day_mot(db, c, user=None):
    """Đẩy một tờ. Trả (ok, thông báo). Thành công thì tờ được đánh đã đẩy kèm mã bên kia; hỏng thì ghi lỗi
    lên chính tờ đó để người dùng thấy và bấm đẩy lại — không im lặng, không nuốt."""
    goc = cau_hinh(db, "ke_toan_api")
    if not goc:
        return False, "Chưa cấu hình địa chỉ API kế toán."
    if c.da_day:
        return True, "Đã đẩy từ trước."
    url = goc.rstrip("/") + DUONG_VOUCHERS
    ma, tra = _goi_http(url, cau_hinh(db, "ke_toan_token"), goi_tin(c))
    c.lan_thu = (c.lan_thu or 0) + 1
    if ma in (200, 201, 409) and isinstance(tra, dict):
        c.da_day = True
        c.day_luc = dt.datetime.utcnow()
        c.ma_ben_ke_toan = str(tra.get("id") or tra.get("Id") or tra.get("voucher_id") or "") or None
        c.loi_day = None
        return True, "Đã đẩy" + (" (bên kia đã có từ trước)" if ma == 409 else "")
    chu = tra.get("loi") or tra.get("message") or tra.get("error") or tra.get("raw") or ("HTTP %s" % ma)
    c.loi_day = ("%s — %s" % (ma or "không nối được", chu))[:400]
    c.day_luc = dt.datetime.utcnow()
    return False, c.loi_day


def day_hang_loat(db, user=None, loai=None, gioi_han=200):
    """Đẩy mọi tờ chưa đẩy (cũ trước), tối đa `gioi_han` tờ một lượt. Trả tóm tắt để màn hình hiện."""
    q = db.query(ChungTu).filter(ChungTu.da_day.is_(False))
    if loai:
        q = q.filter(ChungTu.loai == loai)
    ds = q.order_by(ChungTu.ngay, ChungTu.ts).limit(gioi_han).all()
    ket = {"thu": 0, "xong": 0, "loi": 0, "chi_tiet_loi": []}
    for c in ds:
        ket["thu"] += 1
        ok, tb = day_mot(db, c, user)
        if ok:
            ket["xong"] += 1
        else:
            ket["loi"] += 1
            if len(ket["chi_tiet_loi"]) < 10:
                ket["chi_tiet_loi"].append({"so": c.so, "loi": tb})
            if not cau_hinh(db, "ke_toan_api"):
                break
    return ket
