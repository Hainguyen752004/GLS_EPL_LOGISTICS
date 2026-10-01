# -*- coding: utf-8 -*-
"""Sổ chứng từ — mỗi bước nghiệp vụ bỏ vào một tờ (phiếu thu / chi / nhập kho / xuất kho…) kèm định khoản gợi ý.

Bên mình không có sổ kế toán. Tờ để in / xem và định khoản cho màn Quy trình; `da-day` đánh tay khi bên kế toán đã
nhận / đối chiếu. Từ 01/10 KHÔNG còn đẩy tờ sang trang kế toán tạm (services/day_ke_toan.py) — đường đẩy hết còn giữ
chỗ cho công cụ gieo mẫu, không gửi gì ra ngoài. Cấu hình nối KHO TẠM (máy EPL_KETOAN) cũng ở đây: `/api/kho-tam/cau-hinh`.
Xem services/chung_tu.py.
"""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ChungTu
from services import chung_tu as CT
from services import day_ke_toan as DK
from services import goi_ke_toan as KT
from services.bao_mat import can_vai, nguoi_hien_tai

router = APIRouter()
XEM = ("acct", "expacct", "rev", "treasury", "cash", "fuel", "admin")    # thủ kho (depot) không có màn sổ chứng từ — API cũng không cho đọc


def _ngay(s, ten):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        raise HTTPException(422, {"ma": "NGAY_SAI", "loi": "%s phải dạng YYYY-MM-DD." % ten})


@router.get("/api/chung-tu/loai")
def ds_loai(user=Depends(nguoi_hien_tai)):
    """Danh mục loại chứng từ kèm hai vế định khoản gợi ý (xe nhà · mục vận chuyển)."""
    ra = []
    for ma, (ten, ten_lo, co_dk) in CT.LOAI.items():
        no, no_ten, co, co_ten = CT.dinh_khoan(ma) if co_dk else (None, None, None, None)
        ra.append({"ma": ma, "ten": ten, "ten_lo": ten_lo, "dinh_khoan": co_dk,
                   "no": no, "no_ten": no_ten, "co": co, "co_ten": co_ten})
    return ra


@router.get("/api/chung-tu")
def ds_chung_tu(loai: str = "", tu: str = "", den: str = "", trip_id: str = "", chua_day: int = 0,
                doi_tuong: str = "", limit: int = 500, db: Session = Depends(get_db), user=Depends(can_vai(*XEM))):
    q = db.query(ChungTu)
    if loai:
        q = q.filter(ChungTu.loai.in_([x.strip().upper() for x in loai.split(",") if x.strip()]))
    if tu:
        q = q.filter(ChungTu.ngay >= _ngay(tu, "Từ ngày"))
    if den:
        q = q.filter(ChungTu.ngay <= _ngay(den, "Đến ngày"))
    if trip_id:
        q = q.filter(ChungTu.trip_id == trip_id)
    if doi_tuong:
        q = q.filter(ChungTu.doi_tuong_loai == doi_tuong)
    if chua_day:
        q = q.filter(ChungTu.da_day.is_(False))
    q = q.order_by(ChungTu.ngay.desc(), ChungTu.ts.desc()).limit(max(1, min(limit, 2000)))
    ds = [CT.xuat(c) for c in q.all()]
    tong = {}
    for c in ds:
        t = tong.setdefault(c["loai"], {"so_to": 0, "tien_lak": 0.0, "chua_day": 0})
        t["so_to"] += 1
        t["tien_lak"] += c["tien_lak"] or 0
        t["chua_day"] += 0 if c["da_day"] else 1
    return {"ds": ds, "tong": tong}


@router.get("/api/chung-tu/{cid}")
def mot_chung_tu(cid: str, db: Session = Depends(get_db), user=Depends(can_vai(*XEM))):
    c = db.get(ChungTu, cid)
    if not c:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chứng từ này."})
    return CT.xuat(c)


@router.post("/api/chung-tu/{cid}/da-day")
def danh_dau_da_day(cid: str, d: dict = Body(default={}), db: Session = Depends(get_db),
                    user=Depends(can_vai("acct", "expacct", "rev", "treasury", "cash", "admin"))):
    """Bên kế toán (hoặc người đối chiếu) báo đã nhận tờ này. Gửi {"da_day": false} để mở lại."""
    c = db.get(ChungTu, cid)
    if not c:
        raise HTTPException(404, {"ma": "KHONG_THAY", "loi": "Không có chứng từ này."})
    c.da_day = bool(d.get("da_day", True))
    c.day_luc = dt.datetime.utcnow() if c.da_day else None
    db.commit()
    return CT.xuat(c)


# ================================================================ đẩy sang trang kế toán tạm — ĐÃ BỎ 01/10
# Còn MỘT đường giữ chỗ: tools/gieo_demo_2609.py vẫn gọi POST /api/chung-tu/day (đọc xong / loi). `/api/ke-toan/trang-thai`
# và `/api/chung-tu/{id}/day` không còn ai gọi (giao diện đã bỏ nút Đẩy) — xoá ở đợt dọn dẹp 01/10.
DAY = ("acct", "admin")


@router.post("/api/chung-tu/day")
def day_tat_ca(d: dict = Body(default={}), db: Session = Depends(get_db), user=Depends(can_vai(*DAY))):
    """Không đẩy nữa — trả tóm tắt rỗng đúng kiểu cũ ({thu, xong, loi} = 0), không gửi gì ra ngoài."""
    return DK.day_hang_loat(db, user, loai=(d.get("loai") or None))


# ================================================================ cấu hình nối KHO TẠM + hai mã bên kế toán cấp sau
# Tên mới (01/10): kho_api · kho_web · kho_token (services/goi_ke_toan.py). Tên cũ ke_toan_api · ke_toan_web ·
# ke_toan_token · co_token và đường /api/ke-toan/cau-hinh vẫn nhận / trả song song cho tới khi giao diện đổi xong
# (màn Tài khoản → Liên thông, Sổ chứng từ → Cấu hình) — bỏ ở đợt dọn dẹp.
def _xem_cau_hinh(db):
    """Token chỉ báo có hay không, không bao giờ trả ra trình duyệt."""
    from services.bao_mat import token_nhan_ke_toan
    api, web, co = KT.doc_kho(db, "api"), KT.doc_kho(db, "web"), bool(KT.doc_kho(db, "token"))
    return {"kho_api": api, "kho_web": web, "co_token_kho": co,
            "co_token_nhan_ke_toan": bool(token_nhan_ke_toan(db)),
            # Hai mã bên kế toán cấp sau: hàng khách gửi (ngoài bảng) và giá vốn hàng bán
            "ma_hang_khach_gui": DK.cau_hinh(db, "ma_hang_khach_gui"), "ma_gia_von": DK.cau_hinh(db, "ma_gia_von"),
            "ke_toan_api": api, "ke_toan_web": web, "co_token": co}          # tên cũ — bỏ ở đợt dọn dẹp


@router.get("/api/kho-tam/cau-hinh")
@router.get("/api/ke-toan/cau-hinh")
def xem_cau_hinh(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Sếp xem cấu hình nối kho tạm và hai mã bên kế toán cấp sau."""
    return _xem_cau_hinh(db)


@router.put("/api/kho-tam/cau-hinh")
@router.put("/api/ke-toan/cau-hinh")
def dat_cau_hinh(d: dict = Body(...), db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Sếp đặt địa chỉ API kho, địa chỉ mở bằng trình duyệt và khoá kho (gửi khoá rỗng = giữ khoá cũ; gửi "-" = xoá).
    Nhận tên mới (kho_*) lẫn tên cũ (ke_toan_*); gửi cả hai thì tên mới thắng."""
    for vai in ("api", "web"):
        moi, cu = KT.KHOA_KHO[vai]
        if moi in d or cu in d:
            KT.dat_kho(db, vai, (d.get(moi) if moi in d else d.get(cu)) or "", user)
    moi, cu = KT.KHOA_KHO["token"]
    tk = d.get(moi) or d.get(cu)
    if tk == "-":
        KT.dat_kho(db, "token", "", user)
    elif tk:
        KT.dat_kho(db, "token", tk, user)
    for k in ("ma_hang_khach_gui", "ma_gia_von"):
        if k in d:
            DK.dat_cau_hinh(db, k, str(d.get(k) or "").strip(), user)
    db.commit()
    return _xem_cau_hinh(db)


@router.post("/api/ke-toan/bo-sung-gia-von")
def bo_sung_gia_von(db: Session = Depends(get_db), user=Depends(can_vai("admin"))):
    """Tờ xuất kho bán (PXK_BAN) ghi TRƯỚC khi chốt mã giá vốn 607 (23/09) thiếu vế Nợ: điền mã giá vốn hiện hành vào
    các tờ đó để định khoản đủ hai vế (màn Quy trình, bản in). Từ 01/10 không đẩy lại sang trang kế toán tạm nữa —
    cờ đã nhận của tờ giữ nguyên. Kiểu trả về giữ như cũ (`da_day` luôn 0)."""
    ma = DK.cau_hinh(db, "ma_gia_von") or CT.GIA_VON[0]
    ds = db.query(ChungTu).filter(ChungTu.loai == "PXK_BAN", ChungTu.no.is_(None)).order_by(ChungTu.ngay).all()
    for c in ds:
        c.no, c.no_ten = ma, CT.GIA_VON[1]
    db.commit()
    return {"ma_gia_von": ma, "so_to": len(ds), "da_day": 0, "loi": [], "khong_day_nua": True}
