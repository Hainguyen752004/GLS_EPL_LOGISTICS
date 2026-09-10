# -*- coding: utf-8 -*-
"""Acc code DÙNG CHUNG theo khoản mục — đặt một lần, mọi loại xe cùng khoản mục kế thừa.

Chủ dự án (10/09), kèm hai ảnh: đã gán Acc code 1091 cho "Chi phí xăng dầu /km"
trên Container 20FT, sang Xe tải thùng 10 tấn cùng khoản mục đó lại trống và phải
chọn lại. *"Những chi phí giống nhau thì lưu lại chung cái acc code được không —
khi phát sinh chi phí khác thì mới chọn lại."*

CÁCH GIẢI. Acc code là thuộc tính của KHOẢN MỤC, không phải của loại xe. Nên:

  1. Mỗi khoản mục có một KHOÁ CHUNG: năm khoản mục có sẵn dùng `key`
     (`fuel`, `driver`, `toll`, `wh`, `rate`); khoản mục người dùng tự thêm dùng
     TÊN đã chuẩn hoá (bỏ dấu, thường, gộp khoảng trắng) — vì `key` của chúng
     là `term_N` theo vị trí, sang loại xe khác là số khác.
  2. Bảng dùng chung nằm ở `account_mappings` với tiền tố `khoan_muc::` — đúng
     chỗ "Mapping tài khoản" mà chủ dự án từng chỉ, và không thêm bảng mới.
  3. Lúc LƯU một công thức: dòng nào chưa có Acc code thì KẾ THỪA từ bảng chung;
     dòng nào có Acc code thì GHI vào bảng chung và LAN sang mọi công thức khác
     có cùng khoản mục — lan vào dòng đang trống hoặc đang mang đúng mã chung
     cũ (dòng mang một mã thứ ba lạ thì giữ, để không phá dữ liệu tay). Một
     khoản mục = một Acc code trên mọi loại xe; "phát sinh chi phí khác thì mới
     chọn lại" nghĩa là khoản mục MỚI (tên khác) mới cần chọn mã.

Không đụng ô chọn Acc code trên từng dòng (chủ dự án đã chốt giữ cách đó ở A20).
"""
import json
import re
import unicodedata

from models import AccountMapping, CostFormula

TIEN_TO = "khoan_muc::"
KHOA_CO_SAN = {"fuel", "driver", "toll", "wh", "rate"}


def _chuan_hoa_ten(ten):
    chu = unicodedata.normalize("NFD", str(ten or ""))
    chu = "".join(c for c in chu if unicodedata.category(c) != "Mn")
    chu = chu.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"\s+", " ", chu).strip()


def khoa_chung(term):
    """Khoá dùng chung của một khoản mục, hoặc "" nếu không định danh được."""
    if not isinstance(term, dict):
        return ""
    key = str(term.get("key") or "").strip().lower()
    if key in KHOA_CO_SAN:
        return TIEN_TO + key
    ten = _chuan_hoa_ten(term.get("label"))
    return TIEN_TO + "ten::" + ten[:80] if ten else ""


def bang_chung(db):
    """{khoá chung: acc code} đang có trong Mapping tài khoản."""
    ra = {}
    for m in db.query(AccountMapping).filter(AccountMapping.mapping_key.like(TIEN_TO + "%")).all():
        ma = str(m.account_code or "").strip()
        if ma:
            ra[m.mapping_key] = ma
    return ra


def ke_thua(terms, bang):
    """Điền Acc code chung vào những dòng còn trống. Trả số dòng đã điền."""
    n = 0
    for t in terms if isinstance(terms, list) else []:
        if not isinstance(t, dict) or str(t.get("cost_index") or "").strip():
            continue
        k = khoa_chung(t)
        if k and k in bang:
            t["cost_index"] = bang[k]
            n += 1
    return n


def ghi_nhan_va_lan(db, terms, formula_id, bang=None):
    """Ghi Acc code của các dòng có mã vào bảng chung, rồi lan sang công thức khác.

    Trả `{khoá chung: (mã cũ, mã mới)}` cho những khoá đã đổi. Không commit —
    người gọi commit cùng với công thức đang lưu.
    """
    bang = dict(bang if bang is not None else bang_chung(db))
    doi = {}
    for t in terms if isinstance(terms, list) else []:
        if not isinstance(t, dict):
            continue
        ma = str(t.get("cost_index") or "").strip()
        k = khoa_chung(t)
        if not ma or not k:
            continue
        cu = bang.get(k)
        if cu == ma:
            continue
        m = db.get(AccountMapping, k) or AccountMapping(mapping_key=k)
        m.account_code = ma
        db.add(m)
        bang[k] = ma
        doi[k] = (cu, ma)
    if not doi:
        return doi
    # Lan sang công thức khác: chỉ dòng trống hoặc đang theo mã chung cũ.
    for row in db.query(CostFormula).all():
        if row.id == formula_id:
            continue
        try:
            goi = json.loads(row.formula_expression or "{}")
        except (TypeError, ValueError):
            continue
        hang_tu = goi.get("terms") if isinstance(goi, dict) else None
        if not isinstance(hang_tu, list):
            continue
        sua = False
        for t in hang_tu:
            if not isinstance(t, dict):
                continue
            k = khoa_chung(t)
            if k not in doi:
                continue
            cu, moi = doi[k]
            hien = str(t.get("cost_index") or "").strip()
            if hien == "" or hien == (cu or ""):
                t["cost_index"] = moi
                sua = True
        if sua:
            row.formula_expression = json.dumps(goi, ensure_ascii=False)
    return doi
