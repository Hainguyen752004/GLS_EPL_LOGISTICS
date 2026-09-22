# -*- coding: utf-8 -*-
"""Ai được làm gì trên phiếu xuất xe — chép nguyên sheet "ໜ້າວຽກ" (Trách nhiệm) trong Excel.

Mỗi mục I–VI của phiếu đi qua một chuỗi trạng thái, mỗi bước do MỘT vai làm:

    Admin Thà Bốc NHẬP  →  Kế toán KIỂM  →  Kế toán GHI SỔ  →  Quỹ CHI
      (yard)          (acct/expacct/fuel)  (expacct/fuel)     (treasury/cash)

  Đúng bảng "Nhiệm Vụ" trong Excel của khách, KHÔNG gộp vai:
  · Mục I–II   : KT Thu/Chi Viêng Chăn (acct) xác nhận — chỉ tới "đã kiểm", không có tiền để chi.
  · Mục III    : KT kho xăng dầu VC (fuel) xác nhận + ghi sổ; Thủ quỹ VC (treasury) chi.
  · Mục IV–VI  : KT Chi phí VC (expacct) xác nhận + ghi sổ; Quỹ tiền mặt cảng cạn (cash) chi.
  · Mục V      : người NHẬP là TỔ SỬA CHỮA Thà Bốc (repair), không phải Admin Bãi — anh Khampla C1.2:
    kho phụ tùng và tổ sửa là người riêng. Bãi nhập I–IV và VI, không đụng mục V nữa.
  · Kế toán doanh thu (rev) xuất hoá đơn và ghi thu tiền ở mức PHIẾU, không đụng từng mục.
  · Admin làm được mọi việc, kể cả mở khoá mục đã duyệt.

Quy tắc khoá: người nhập chỉ sửa được khi mục còn ở "chờ" hoặc "đã nhập". Kế toán đã kiểm
là khoá — muốn sửa phải "trả lại" (return) cho Bãi.
"""
from fastapi import HTTPException

from models import CHUOI, MUC

# Mục V (sửa chữa) đã rút khỏi Bãi — tổ sửa chữa nhập (anh Khampla C1.2, 22/09).
MUC_CUA_BAI = {m for m in MUC if m != "repair"}

QUYEN = {
    "yard":     {"edit": set(MUC_CUA_BAI), "verify": set(), "book": set(), "pay": set()},
    # Bảng "Nhiệm Vụ" của khách tách hai người: KT Thu/Chi VC xác nhận mục I–II (không có tiền để
    # ghi sổ); KT Chi phí VC xác nhận và ghi sổ mục IV–VI. Người kiểm I–II không được đụng IV–VI.
    "acct":     {"edit": set(), "verify": {"info", "trans"}, "book": set(), "pay": set()},
    "expacct":  {"edit": set(), "verify": {"travel", "repair", "other"},
                 "book": {"travel", "repair", "other"}, "pay": set()},
    "fuel":     {"edit": set(), "verify": {"fuel"}, "book": {"fuel"}, "pay": set()},
    # Thủ kho tại điểm đổ: không duyệt mục nào, việc của họ là CẤP DẦU theo phiếu lĩnh.
    "depot":    {"edit": set(), "verify": set(), "book": set(), "pay": set()},
    # Thủ kho PHỤ TÙNG Thà Bốc: không duyệt mục nào; việc của họ là kho phụ tùng (nhập · xuất).
    "parts":    {"edit": set(), "verify": set(), "book": set(), "pay": set()},
    # TỔ SỬA CHỮA Thà Bốc: nhập mục V, duyệt báo hỏng của tài xế và quyết lấy phụ tùng từ kho hay
    # mua ngoài. Vẫn phải qua KT Chi phí kiểm và ghi sổ, Quỹ tiền mặt chi — không tự chi tiền.
    "repair":   {"edit": {"repair"}, "verify": set(), "book": set(), "pay": set()},
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


def duoc_sua_tien(vai, muc, trang_thai):
    """Ô TIỀN của mục (đơn giá, giá thuê, phí, ngưỡng tấn) là thẩm quyền của người KIỂM mục đó, không phải người
    nhập: Bãi không thấy tiền, nên kế toán kiểm mục II mới là người sửa giá khi chuyến khác hợp đồng. Chỉ sửa
    được khi mục chưa kiểm xong (chờ / đã nhập); kiểm rồi thì trả lại mới sửa, như mọi ô khác."""
    if vai == "admin":
        return True
    return muc in QUYEN.get(vai, QUYEN["yard"])["verify"] and trang_thai in ("wait", "entered")


def thay_tien_ban(vai):
    """Vai này có được thấy TIỀN BÁN không: đơn giá cước, doanh thu, khách chưa trả, giá thuê xe
    liên kết, lãi chuyến. Bãi, tài xế, thủ kho và hai tổ ở Thà Bốc thì KHÔNG — đó là biên lợi nhuận
    của công ty (khách trả giá 2, thuê lại xe ngoài giá 1). Tiền CHI thì họ vẫn thấy vì chính họ chi."""
    return vai not in ("yard", "driver", "depot", "parts", "repair")


def viec_dang_cho(vai, muc, trang_thai):
    """Mục này có đang chờ CHÍNH vai này làm không — để đếm việc cho đúng người.

    Bãi: mục còn "chờ" là chưa nhập. Kế toán: mục "đã nhập" chờ kiểm, "đã kiểm" chờ ghi sổ.
    Quỹ: mục "đã ghi sổ" chờ chi. Đếm chung tất cả rồi gắn cho mọi vai thì con số không nói lên
    việc của ai cả.
    """
    q = QUYEN.get(vai, QUYEN["yard"])
    if trang_thai == "wait":     return muc in q["edit"]
    if trang_thai == "entered":  return muc in q["verify"]
    if trang_thai == "verified": return muc in q["book"]
    if trang_thai == "booked":   return muc in q["pay"]
    return False


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
