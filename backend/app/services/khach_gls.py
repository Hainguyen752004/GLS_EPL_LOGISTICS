# -*- coding: utf-8 -*-
"""KHÁCH HÀNG = ĐỐI TƯỢNG GLS (Việc 9 chuyển trang điều xe sang module Vận tải C#, 08/10/2026).

Vỏ mỏng của services/doi_tuong_gls cho loại "khach" (Việc 10 gom chung khách · nhà cung cấp · chủ xe vào một chỗ) — giữ nguyên tên
hàm / hằng mà routes/danh_muc.py, services/dong_bo_nen.py, tools/chuyen_csharp/doi_chieu_khach_gls.py và kiem/thu_khach_gls.py đang
dùng. Luật, đường danh mục chung, cờ EPL_KHACH_GLS: xem docstring services/doi_tuong_gls.py.
"""
from services import doi_tuong_gls as DT

L = "khach"
DUONG_DS = DT.duong(L, "list")
DUONG_CT = DT.duong(L, "detail")
DUONG_GHI = DT.duong(L, "upsert")
TIEN_TO_MA = DT.LOAI[L]["tien_to"]
O_CHUNG = DT.O_CHUNG
quen = DT.quen


def bat():
    return DT.bat(L)


def tim(q="", trang=1, nho=True):
    return DT.tim(L, q, trang, nho)


def mot(obj_id):
    return DT.mot(L, obj_id)


def _chep(k, g):
    return DT._chep(L, k, g)[0]


def _nho_doi_tuong(db, k):
    DT._nho_doi_tuong(db, L, k)


def lien_ket(db, obj_id):
    return DT.lien_ket(db, L, obj_id)


def tao(data, ma=None):
    return DT.tao(L, data, ma)


def dong_bo(db, n=None, cu_hon_phut=None):
    return DT.dong_bo(db, L, n, cu_hon_phut)
