# -*- coding: utf-8 -*-
"""Ai được làm gì trên phiếu xuất xe — chép nguyên sheet "ໜ້າວຽກ" (Trách nhiệm) trong Excel.

Mỗi mục I–VI của phiếu đi qua một chuỗi trạng thái, mỗi bước do MỘT vai làm:

    Admin Thà Bốc NHẬP  →  Kế toán KIỂM  →  Kế toán GHI SỔ  →  Quỹ CHI
      (yard)              (acct/fuel)       (acct/fuel)        (treasury/cash)

  · Mục III nhiên liệu đi qua kế toán KHO NHIÊN LIỆU (fuel) và Quỹ Viêng Chăn (treasury).
  · Mục IV–VI đi qua kế toán THU CHI (acct) và Quỹ tiền mặt lẻ Thà Bốc (cash).
  · Mục I–II chỉ tới "đã kiểm" — không có tiền để chi.
  · Kế toán doanh thu (rev) xuất hoá đơn và ghi thu tiền ở mức PHIẾU, không đụng từng mục.
  · Admin làm được mọi việc, kể cả mở khoá mục đã duyệt.

Quy tắc khoá: người nhập chỉ sửa được khi mục còn ở "chờ" hoặc "đã nhập". Kế toán đã kiểm
là khoá — muốn sửa phải "trả lại" (return) cho Bãi.
"""
from fastapi import HTTPException

from models import CHUOI, MUC

QUYEN = {
    "yard":     {"edit": set(MUC), "verify": set(), "book": set(), "pay": set()},
    "acct":     {"edit": set(), "verify": {"info", "trans", "travel", "repair", "other"},
                 "book": {"travel", "repair", "other"}, "pay": set()},
    "fuel":     {"edit": set(), "verify": {"fuel"}, "book": {"fuel"}, "pay": set()},
    # Thủ kho tại điểm đổ: không duyệt mục nào, việc của họ là CẤP DẦU theo phiếu lĩnh.
    "depot":    {"edit": set(), "verify": set(), "book": set(), "pay": set()},
    "treasury": {"edit": set(), "verify": set(), "book": set(), "pay": {"fuel"}},
    "cash":     {"edit": set(), "verify": set(), "book": set(), "pay": {"travel", "repair", "other"}},
    "rev":      {"edit": set(), "verify": set(), "book": set(), "pay": set()},
    "driver":   {"edit": set(), "verify": set(), "book": set(), "pay": set()},   # tài xế không đụng mục nào
    "admin":    {"edit": set(MUC), "verify": set(MUC), "book": set(MUC), "pay": set(MUC)},
}

# hành động → (trạng thái đích, quyền cần có, trạng thái nguồn hợp lệ)
HANH_DONG = {
    "send":   ("entered",  "edit",   {"wait"}),
    "verify": ("verified", "verify", {"entered"}),
    "return": ("wait",     "verify", {"entered", "verified"}),
    "book":   ("booked",   "book",   {"verified"}),
    "pay":    ("paid",     "pay",    {"booked"}),
    "unlock": ("entered",  None,     None),          # chỉ admin
}


def duoc_sua_muc(vai, muc, trang_thai):
    """Vai này còn sửa được nội dung mục này không?"""
    if vai == "admin":
        return True
    return muc in QUYEN.get(vai, QUYEN["yard"])["edit"] and trang_thai in ("wait", "entered")


def chuyen_muc(vai, muc, trang_thai_hien_tai, hanh_dong):
    """Trả trạng thái mới, hoặc bật lỗi 403/409 nói rõ vì sao."""
    if muc not in MUC:
        raise HTTPException(422, {"ma": "MUC_SAI", "loi": "Không có mục %s." % muc})
    if hanh_dong not in HANH_DONG:
        raise HTTPException(422, {"ma": "HANH_DONG_SAI", "loi": "Không có hành động %s." % hanh_dong})
    dich, quyen, nguon = HANH_DONG[hanh_dong]
    if hanh_dong == "unlock":
        if vai != "admin":
            raise HTTPException(403, {"ma": "CHI_ADMIN", "loi": "Chỉ quản trị mới mở khoá mục đã duyệt."})
        return dich
    if vai != "admin" and muc not in QUYEN.get(vai, QUYEN["yard"])[quyen]:
        raise HTTPException(403, {"ma": "KHONG_CO_QUYEN",
                                  "loi": "Vai %s không được %s mục %s." % (vai, hanh_dong, muc)})
    if trang_thai_hien_tai not in nguon:
        raise HTTPException(409, {"ma": "SAI_BUOC",
                                  "loi": "Mục %s đang ở '%s', không thể %s." % (muc, trang_thai_hien_tai, hanh_dong)})
    if dich not in CHUOI[muc]:
        raise HTTPException(409, {"ma": "SAI_BUOC", "loi": "Mục %s không có bước %s." % (muc, dich)})
    return dich
