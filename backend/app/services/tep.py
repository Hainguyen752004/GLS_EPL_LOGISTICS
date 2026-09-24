# -*- coding: utf-8 -*-
"""Chỗ chứa tệp dùng chung — ບ່ອນເກັບໄຟລ໌.

Phiếu quặng của khách và ảnh xe đều nằm ở ĐÂY, chỉ khác thư mục con:

    <EPL_LAO_TEP>/<trip_id>/…      tệp đính kèm phiếu xuất xe
    <EPL_LAO_TEP>/xe/<vehicle_id>/…  ảnh xe

Một chỗ chứa thì một chỗ sao lưu, và giới hạn dung lượng chỉ đặt một lần. Hằng số để ở tệp riêng
(không để trong routes/phieu.py) vì cả hai route đều cần, mà hai route đó đã gọi lẫn nhau — nhập
chéo thêm một vòng nữa là vòng lặp nhập.
"""
import os

TEP_DIR = os.getenv("EPL_LAO_TEP") or os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tep"))
TEP_TOI_DA = 10 * 1024 * 1024        # MỖI LẦN TẢI tối đa 10 MB (chủ dự án chốt 24/09: nghìn chuyến / ngày, ảnh gửi liên tục)
ANH_TOI_DA = 1 * 1024 * 1024         # ảnh: giao diện nén còn ≤ 200 KB (js/nen_anh.js); quá 1 MB là máy không nén được
PDF_TOI_DA = 2 * 1024 * 1024         # PDF không nén được trong trình duyệt — chặn quá 2 MB, khuyên chụp ảnh thay


def loi_co_tep(kieu, so_byte):
    """Câu lỗi nếu tệp quá cỡ theo LOẠI (ảnh 1 MB · PDF 2 MB), không thì None."""
    if kieu == "application/pdf" and so_byte > PDF_TOI_DA:
        return "PDF %.1f MB, tối đa 2 MB. Nên chụp ảnh thay vì PDF — ảnh được nén còn dưới 200 KB." % (so_byte / 1048576)
    if kieu.startswith("image/") and so_byte > ANH_TOI_DA:
        return "Ảnh %.1f MB chưa được nén (tối đa 1 MB). Tải lại trang rồi chọn ảnh lại; ảnh HEIC thì chụp ở chế độ JPG." % (so_byte / 1048576)
    return None
TEP_KIEU = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
            "image/heic": ".heic", "application/pdf": ".pdf"}
# Ảnh thì không nhận PDF — khung ảnh xe hiển thị bằng thẻ <img>.
ANH_KIEU = {k: v for k, v in TEP_KIEU.items() if k != "application/pdf"}
THU_MUC_ANH_XE = os.path.join(TEP_DIR, "xe")
THU_MUC_HOP_DONG = os.path.join(TEP_DIR, "hop_dong")      # bản scan hợp đồng (routes/hop_dong.py)
