# -*- coding: utf-8 -*-
"""GỌI SANG TRANG KẾ TOÁN (EPL_KETOAN) — một chỗ cho mọi lời gọi LÀM VIỆC từ trang điều xe sang.

Từ 28/09 kho (điểm đổ, dầu, phụ tùng, lô hàng bãi, lệnh sửa chữa, bán hàng) và tiền vận chuyển nằm bên trang kế toán.
Phiếu xuất xe vẫn ở đây, nên khi phiếu cần kho (ghi sổ mục III xuất dầu, lấy phụ tùng mục V, gom về bãi nhập lô…)
thì gọi sang qua hàm `goi`. Cùng địa chỉ và khoá với đường đẩy chứng từ (`ke_toan_api`, `ke_toan_token`), kèm
`X-Nguoi-Dung` là tên đăng nhập người đang bấm — hai trang dùng cùng tên đăng nhập.

Không nối được thì **chặn và báo rõ** (chủ dự án chốt 28/09): 503 `CHUA_NOI_KE_TOAN`, việc đó không làm được, không
xếp hàng gửi sau — hai bên không bao giờ lệch số. Lỗi nghiệp vụ bên kia (409 không đủ tồn…) trả lại nguyên mã và câu.
"""
import json
import urllib.error
import urllib.request

from fastapi import HTTPException

from services import day_ke_toan as DK
from services import mang as MANG

HET_GIO = 15


def cau_hinh(db):
    return DK.cau_hinh(db, "ke_toan_api").rstrip("/"), DK.cau_hinh(db, "ke_toan_token")


def goi(db, phuong_thuc, duong, body=None, nguoi=None, het_gio=HET_GIO):
    goc, token = cau_hinh(db)
    if not goc or not token:
        raise HTTPException(503, {"ma": "CHUA_NOI_KE_TOAN",
                                  "loi": "Chưa đặt địa chỉ hoặc khoá nối trang kế toán — Sếp vào cấu hình kết nối kế toán."})
    du = json.dumps(body).encode("utf-8") if body is not None else None
    dau = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
    if nguoi is not None:
        dau["X-Nguoi-Dung"] = getattr(nguoi, "username", str(nguoi))
    r = urllib.request.Request(goc + duong, data=du, method=phuong_thuc, headers=dau)
    try:
        with MANG.mo(r, het_gio) as t:
            tho = t.read()
            return json.loads(tho) if tho else None
    except urllib.error.HTTPError as e:
        try:
            g = json.loads(e.read() or b"null") or {}
        except ValueError:
            g = {}
        chi = g.get("detail") if isinstance(g.get("detail"), dict) else g
        raise HTTPException(e.code, {"ma": (chi or {}).get("ma") or "LOI_KE_TOAN",
                                     "loi": (chi or {}).get("loi") or (chi or {}).get("message")
                                     or "Trang kế toán báo lỗi HTTP %d." % e.code})
    except (urllib.error.URLError, OSError, ValueError):
        raise HTTPException(503, {"ma": "CHUA_NOI_KE_TOAN", "loi": "Chưa nối được trang kế toán — thử lại sau."})
