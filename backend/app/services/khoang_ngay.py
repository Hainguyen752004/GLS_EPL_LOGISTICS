# -*- coding: utf-8 -*-
"""KHOẢNG NGÀY cho bộ lọc thời gian của các màn danh sách / báo cáo (09/10/2026).

Anh Khampla (kế toán bên Lào) gửi ảnh phần mềm kế toán của anh ấy: lọc theo Năm · Tháng · Khoảng thời gian (từ ngày … đến ngày)
và nút nhanh Hôm qua · Hôm nay · Tuần này · Tháng này · Năm này (frontend/js/khoang_thoi_gian.js). Các màn đó gửi `tu`, `den`
(YYYY-MM-DD); Web C# và chỗ khác vẫn gửi `thang` (YYYY-MM) — route GIỮ NGUYÊN tham số `thang`: có tu/den thì dùng tu/den, không
thì như cũ (hàm tháng riêng của route đó).

    khoang(tu, den, toi_da=None) → (đầu, cuối) kiểu date, hoặc None khi không gửi cả hai.

Lỗi (422, dạng {ma, loi} như mọi route): ngày sai dạng (NGAY_SAI) · gửi một đầu (KHOANG_THIEU) · tu sau den (KHOANG_SAI) ·
dài quá `toi_da` ngày (KHOANG_DAI — báo cáo đệm theo từng ngày, services/dem_bao_cao: khoảng vài chục năm là vài chục nghìn bản đệm).
Câu lỗi có bản Lào / Anh ở services/loi_dich.json.
"""
import datetime as dt
import re

from fastapi import HTTPException

# Báo cáo (Tổng quan, Theo dõi phiếu): một năm là khoảng dài nhất màn chọn được bằng nút (Năm · Năm này) — 366 ngày cho năm nhuận
TOI_DA_BAO_CAO = 366
_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ngay(v, ten):
    s = str(v).strip()
    try:
        if not _RE.match(s):
            raise ValueError(s)
        return dt.date.fromisoformat(s)
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "%s phải dạng YYYY-MM-DD." % ten})


def khoang(tu, den, toi_da=None):
    """(đầu, cuối) của khoảng `tu` … `den` (cả hai đầu tính vào); không gửi cả hai → None (route dùng `thang` như cũ)."""
    tu = (tu or "").strip() if isinstance(tu, str) else tu
    den = (den or "").strip() if isinstance(den, str) else den
    if not tu and not den:
        return None
    if not tu or not den:
        raise HTTPException(422, {"ma": "KHOANG_THIEU", "loi": "Gửi đủ hai ngày tu và den (YYYY-MM-DD), hoặc bỏ cả hai."})
    a, b = _ngay(tu, "Từ ngày"), _ngay(den, "Đến ngày")
    if a > b:
        raise HTTPException(422, {"ma": "KHOANG_SAI", "loi": "Từ ngày (%s) không được sau Đến ngày (%s)." % (a.isoformat(), b.isoformat())})
    n = (b - a).days + 1
    if toi_da and n > toi_da:
        raise HTTPException(422, {"ma": "KHOANG_DAI", "loi": "Khoảng thời gian tối đa %s ngày — đang chọn %s ngày." % (toi_da, n)})
    return a, b


def ky_truoc(dau, cuoi):
    """Kỳ đứng ngay trước (đầu, cuối), cùng độ dài — để so «kỳ trước» ở Tổng quan. Khoảng TRỌN THÁNG (một hay nhiều tháng liền)
    thì kỳ trước là chừng ấy tháng liền trước (tháng 9 → tháng 8, như so «tháng trước» lâu nay); còn lại lùi đúng số ngày."""
    sau = cuoi + dt.timedelta(days=1)
    if dau.day == 1 and sau.day == 1:
        so_thang = (sau.year * 12 + sau.month) - (dau.year * 12 + dau.month)
        k = dau.year * 12 + (dau.month - 1) - so_thang
        a = dt.date(k // 12, k % 12 + 1, 1)
        return a, dau - dt.timedelta(days=1)
    n = (cuoi - dau).days + 1
    return dau - dt.timedelta(days=n), dau - dt.timedelta(days=1)
