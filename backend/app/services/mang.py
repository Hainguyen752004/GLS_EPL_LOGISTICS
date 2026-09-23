# -*- coding: utf-8 -*-
"""Gọi ra ngoài qua HTTPS — MỘT chỗ dựng ngữ cảnh chứng chỉ cho mọi lời gọi của máy chủ.

Vì sao có tệp này: trên máy Windows chạy thử, `ssl.create_default_context()` của Python đọc kho chứng chỉ của
Windows và chết vì một chứng chỉ hỏng trong kho ("[ASN1: NOT_ENOUGH_DATA] not enough data"). Hệ quả thấy được
trên màn: danh mục Acc code của anh Khang báo "không nối được" dù API vẫn trả đủ 494 mã (curl HTTP 200), và mai
kia đẩy chứng từ sang máy anh Khang qua HTTPS cũng hỏng y như vậy. Dùng bộ chứng chỉ riêng của `certifi` thì không
phụ thuộc kho của máy; không có certifi thì lùi về mặc định như cũ.
"""
import ssl
import urllib.request

_NGU_CANH = None


def ngu_canh_ssl():
    global _NGU_CANH
    if _NGU_CANH is None:
        try:
            import certifi
            _NGU_CANH = ssl.create_default_context(cafile=certifi.where())
        except Exception:  # noqa: BLE001 — không có certifi thì dùng mặc định của máy
            _NGU_CANH = ssl.create_default_context()
    return _NGU_CANH


def mo(yeu_cau, timeout):
    """Như urllib.request.urlopen, nhưng HTTPS thì dùng ngữ cảnh chứng chỉ ở trên."""
    url = yeu_cau.full_url if isinstance(yeu_cau, urllib.request.Request) else str(yeu_cau)
    if url.lower().startswith("https://"):
        return urllib.request.urlopen(yeu_cau, timeout=timeout, context=ngu_canh_ssl())
    return urllib.request.urlopen(yeu_cau, timeout=timeout)
