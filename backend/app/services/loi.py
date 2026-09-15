"""Lỗi nghiệp vụ — tách khỏi lỗi kỹ thuật.

Máy chủ trả mã lỗi ổn định để giao diện dịch được sang bốn thứ tiếng, kèm một
câu tiếng Việt để lập trình viên đọc log. Giao diện KHÔNG in mã lỗi thô lên màn
nghiệp vụ; nó tra mã trong lang.json rồi hiện câu đã dịch.
"""

from fastapi import HTTPException


class LoiNghiepVu(Exception):
    def __init__(self, ma, thong_diep, trang_thai=400, chi_tiet=None):
        super().__init__(thong_diep)
        self.ma = ma
        self.thong_diep = thong_diep
        self.trang_thai = trang_thai
        self.chi_tiet = chi_tiet or {}


def nem_http(loi):
    raise HTTPException(
        status_code=loi.trang_thai,
        detail={"code": loi.ma, "message": loi.thong_diep, "detail": loi.chi_tiet},
    )
