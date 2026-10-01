# -*- coding: utf-8 -*-
"""GỌI SANG KHO TẠM (máy EPL_KETOAN) — một chỗ cho mọi lời gọi LÀM VIỆC từ trang điều xe sang.

Từ 28/09 kho (điểm đổ, dầu, phụ tùng, lô hàng bãi, lệnh sửa chữa, bán hàng) nằm bên máy EPL_KETOAN. Từ 01/10 (chủ dự án
chốt) máy đó bỏ phần TIỀN, chỉ còn làm **KHO TẠM** — cấp dầu QR, phụ tùng, sổ quặng gửi bãi, giá vốn, sửa chữa xe; mọi
việc tiền đi qua hệ anh Tune (services/gui_tune.py, chi_tune.py). Phiếu xuất xe vẫn ở đây, nên khi phiếu cần kho (ghi
sổ mục III xuất dầu, lấy phụ tùng mục V, gom về bãi nhập lô…) thì gọi sang qua hàm `goi`, kèm `X-Nguoi-Dung` là tên
đăng nhập người đang bấm — hai bên dùng cùng tên đăng nhập.

CẤU HÌNH KHO RIÊNG (01/10): địa chỉ `kho_api`, khoá `kho_token`, địa chỉ mở bằng trình duyệt `kho_web` (bảng `cau_hinh`,
không có thì biến môi trường EPL_KHO_API / EPL_KHO_TOKEN / EPL_KHO_WEB). Trước đây kho đọc chung `ke_toan_api` /
`ke_toan_token` / `ke_toan_web` với đường đẩy chứng từ — đường đó đã bỏ (services/day_ke_toan.py).
TƯƠNG THÍCH: khoá mới CHƯA TỪNG LƯU (bảng chưa có dòng `kho_*`, biến EPL_KHO_* cũng trống) thì ĐỌC KHOÁ CŨ (bảng rồi
EPL_KE_TOAN_*), để máy thật 8020 khởi động lại với cấu hình cũ vẫn nối kho như trước. Sếp lưu cấu hình kho một lần (màn
Tài khoản → Liên thông, `PUT /api/kho-tam/cau-hinh`) là có dòng `kho_*` — từ đó chỉ đọc khoá mới, kể cả khi Sếp cố ý để
trống (xoá khoá kho thì khoá cũ không "sống lại"). Khoá cũ trong bảng không bị đụng (quay về mã cũ vẫn chạy). Bỏ phần đọc
khoá cũ ở đợt dọn dẹp.

Không nối được thì **chặn và báo rõ** (chủ dự án chốt 28/09): 503 `CHUA_NOI_KE_TOAN`, việc đó không làm được, không
xếp hàng gửi sau — hai bên không bao giờ lệch số. Lỗi nghiệp vụ bên kia (409 không đủ tồn…) trả lại nguyên mã và câu.
"""
import json
import urllib.error
import urllib.request

from fastapi import HTTPException

from models import CauHinh
from services import day_ke_toan as DK
from services import mang as MANG

HET_GIO = 15

# vai → (khoá mới, khoá cũ dùng chung với đường đẩy chứng từ đã bỏ 01/10)
KHOA_KHO = {"api": ("kho_api", "ke_toan_api"), "token": ("kho_token", "ke_toan_token"), "web": ("kho_web", "ke_toan_web")}


def doc_kho(db, vai):
    """Một giá trị cấu hình kho: khoá mới (bảng → EPL_KHO_*); khoá mới chưa từng lưu thì khoá cũ (bảng → EPL_KE_TOAN_*).
    Nhớ trong phiên (một yêu cầu): dòng `kho_*` chưa có thì mỗi lần hỏi là một lần đọc bảng, mà một lần lưu phiếu gọi kho
    nhiều lần."""
    nho = db.info.setdefault("_cau_hinh_kho", {})
    if vai not in nho:
        moi, cu = KHOA_KHO[vai]
        v = DK.cau_hinh(db, moi)
        nho[vai] = v if (v or db.get(CauHinh, moi) is not None) else DK.cau_hinh(db, cu)
    return nho[vai]


def dat_kho(db, vai, gia_tri, user=None):
    """Ghi khoá mới (rỗng = cố ý để trống). Khoá cũ không đụng — xem ghi chú đầu tệp."""
    db.info.pop("_cau_hinh_kho", None)
    return DK.dat_cau_hinh(db, KHOA_KHO[vai][0], gia_tri, user)


def cau_hinh(db):
    """(địa chỉ API kho, khoá) — mọi lời gọi kho đọc ở đây (cả nút "Kiểm kết nối", routes/lien_thong.py)."""
    return doc_kho(db, "api").rstrip("/"), doc_kho(db, "token")


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
        ct = {"ma": (chi or {}).get("ma") or "LOI_KE_TOAN",
              "loi": (chi or {}).get("loi") or (chi or {}).get("message") or "Trang kế toán báo lỗi HTTP %d." % e.code}
        # 01/10: kho tạm chặn vượt tồn — 409 VUOT_TON kèm `tham` (kho, tồn còn, số định lấy, đơn vị, việc; không có giá).
        # Giữ nguyên `tham` để màn Cấp phát bên kho tạm (gọi lồng kho → đây → kho) dịch được câu; màn bên này hiện `loi`.
        if isinstance((chi or {}).get("tham"), dict):
            ct["tham"] = chi["tham"]
        raise HTTPException(e.code, ct)
    except (urllib.error.URLError, OSError, ValueError):
        raise HTTPException(503, {"ma": "CHUA_NOI_KE_TOAN", "loi": "Chưa nối được trang kế toán — thử lại sau."})
