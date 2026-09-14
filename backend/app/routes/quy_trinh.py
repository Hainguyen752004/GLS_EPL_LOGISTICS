# -*- coding: utf-8 -*-
"""Quy trình & trách nhiệm — sheet "ໜ້າວຽກ": bước nào ai nhập, ai kiểm, ai ghi sổ, ai chi.

Bảng này là MÔ TẢ, không phải cấu hình: nó chính là bộ luật đang chạy trong
services/phan_quyen.py, in ra cho người dùng đọc. Sửa luật thì sửa ở đó, bảng này đổi theo.
"""
from fastapi import APIRouter

from services.phan_quyen import QUYEN

router = APIRouter()

# (khoá i18n của bước, mục kỹ thuật, mã tài khoản)
BUOC = [
    ("wfr1", "info",   ""),
    ("wfr2", "trans",  ""),
    ("wfr3", "fuel",   "625/371"),
    ("wfr4", "travel", "625/402"),
    ("wfr5", "repair", "614/402 · 614/371"),
    ("wfr6", "other",  "625/402"),
]


def _vai_lam(quyen, muc):
    return [vai for vai, q in QUYEN.items() if vai != "admin" and muc in q[quyen]]


@router.get("/api/quy-trinh")
def quy_trinh():
    rows = []
    for khoa, muc, tk in BUOC:
        rows.append({"khoa": khoa, "muc": muc, "acct": tk,
                     "nhap": _vai_lam("edit", muc), "kiem": _vai_lam("verify", muc),
                     "ghi_so": _vai_lam("book", muc), "chi": _vai_lam("pay", muc)})
    return {"phieu_xuat_xe": rows,
            "hoa_don": [{"khoa": "wfr7", "nhap": ["rev"], "kiem": ["rev"], "acct": "1211/70 · 1211/402"}]}
