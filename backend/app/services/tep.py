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
TEP_TOI_DA = 8 * 1024 * 1024
TEP_KIEU = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
            "image/heic": ".heic", "application/pdf": ".pdf"}
# Ảnh thì không nhận PDF — khung ảnh xe hiển thị bằng thẻ <img>.
ANH_KIEU = {k: v for k, v in TEP_KIEU.items() if k != "application/pdf"}
THU_MUC_ANH_XE = os.path.join(TEP_DIR, "xe")
