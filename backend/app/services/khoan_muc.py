# -*- coding: utf-8 -*-
"""KHOẢN MỤC CHI PHÍ trên phiếu xuất xe — danh mục cấu hình được (08/10, anh Khampla: "chi phí khác cho gõ tay → thêm một trang cấu hình
chi phí để sau này dùng lại"; chủ dự án chốt: cách trả mặc định lấy theo khoản mục, cấu hình ở đây).

Trước 08/10 danh sách ghi cứng: routes/phieu.KHOAN_MUC (mục → khoản) và tinh_toan.CACH_TRA_MAC_DINH (khoản → cách trả mặc định khác
"tiền mặt"). Nay bảng cost_items là gốc; hai từ điển đó vẫn là CHỖ MỌI NƠI ĐỌC (tinh_toan.cach_tra, tat_toan, chi_luong_tune, phieu,
tuyen) — nap() ghi lại nội dung của chúng TẠI CHỖ từ bảng, nên mã tính tiền không phải đổi. Gọi nap() lúc khởi động, sau mỗi lần sửa
và mỗi lần màn hỏi /api/khoan-muc (máy chạy nhiều tiến trình thì tiến trình nào cũng tự nạp lại khi có người mở phiếu).

Đổi cách trả mặc định của một khoản: dòng chi CŨ đang theo mặc định (pay_channel trống) được ghi rõ cách trả cũ trước khi đổi
(doi_cach_tra_mac_dinh) — phiếu đã kiểm / ghi sổ / chi không đổi nghĩa; chỉ dòng khai từ nay mới theo mặc định mới.

Khoản có sẵn (built_in) giữ tên theo từ điển giao diện (frontend/js/ngon_ngu.js); khoản thêm mới mang tên ba thứ tiếng ở bảng — TEN.
Không thêm khoản mục III (dầu): mã hàng kho bên Web là EPLNL-<khoản> (ban_giao_dau.MA_HANG), khoản dầu mới không có hàng bên kho.
"""
import datetime as dt
import threading

from sqlalchemy import or_

from models import CostItem, TripExpense, ma_moi
from services import tinh_toan as TT

MUC = ("fuel", "travel", "repair", "other")
MUC_THEM = ("travel", "repair", "other")
MUC_CACH_TRA = ("travel", "other")                 # cách trả chỉ có ở mục IV, VI (chi tiền mặt / cùng lương / nợ NCC)
# bộ gốc trước 08/10 — gieo vào bảng lần đầu (thứ tự = thứ tự trên ô chọn)
GOC = {
    "fuel":   ["diesel"],
    "travel": ["x_water", "x_vn", "x_chip_lao", "x_chip_vn", "x_bridge", "x_toll", "x_trip",
               "x_phone", "x_food", "x_parking", "x_border"],
    "repair": ["x_tire", "x_air", "x_oil", "x_brake", "x_tow"],
    "other":  ["x_misc"],
}
GOC_CACH_TRA = dict(TT.CACH_TRA_MAC_DINH)          # chụp lúc nạp mô-đun, trước khi nap() ghi đè từ bảng
KHONG_TAT = ("diesel", "x_toll")                   # máy dùng: dòng dầu mục III, phí cao tốc tự thêm theo tuyến
VAI_SUA = ("expacct", "admin")                     # KT Chi phí VC (người kiểm mục IV–VI) và Sếp

KHOAN_MUC = {m: list(v) for m, v in GOC.items()}   # mục → khoản ĐANG DÙNG — routes/phieu, routes/tuyen đọc chỗ này
TAT_CA = {m: list(v) for m, v in GOC.items()}      # mục → mọi khoản (kể cả đã ngưng) — dòng cũ vẫn hiện đúng tên
TEN = {}                                           # khoản thêm mới → {"vi", "lo", "en"}
_KHOA = threading.Lock()


def dam_bao(db):
    """Bảng trống (lần đầu chạy bản 08/10) → gieo bộ gốc, cách trả mặc định như trước."""
    if db.query(CostItem.id).first() is not None:
        return
    for m, ds in GOC.items():
        for i, k in enumerate(ds):
            db.add(CostItem(key=k, section=m, built_in=True, sort=(i + 1) * 10, active=True,
                            pay_default=GOC_CACH_TRA.get(k, "tien_mat") if m in MUC_CACH_TRA else None, updated_by="gieo 08/10"))
    db.commit()


def nap(db):
    """Đọc bảng → ghi lại KHOAN_MUC, TAT_CA, TEN và tinh_toan.CACH_TRA_MAC_DINH tại chỗ."""
    dam_bao(db)
    dang, tat_ca, ten, cach = {m: [] for m in MUC}, {m: [] for m in MUC}, {}, {}
    for r in db.query(CostItem).order_by(CostItem.section, CostItem.sort, CostItem.key).all():
        if r.section not in MUC:
            continue
        tat_ca[r.section].append(r.key)
        if r.active:
            dang[r.section].append(r.key)
        if r.section in MUC_CACH_TRA and r.pay_default in TT.CACH_TRA and r.pay_default != "tien_mat":
            cach[r.key] = r.pay_default
        if not r.built_in:
            vi = r.name_vi or r.name_lo or r.name_en or r.key
            ten[r.key] = {"vi": vi, "lo": r.name_lo or vi, "en": r.name_en or vi}
    with _KHOA:
        KHOAN_MUC.clear(); KHOAN_MUC.update(dang)                                   # noqa: E702
        TAT_CA.clear(); TAT_CA.update(tat_ca)                                       # noqa: E702
        TEN.clear(); TEN.update(ten)                                                # noqa: E702
        TT.CACH_TRA_MAC_DINH.clear(); TT.CACH_TRA_MAC_DINH.update(cach)             # noqa: E702


def xuat(r):
    return {"id": r.id, "key": r.key, "section": r.section, "name_vi": r.name_vi, "name_lo": r.name_lo, "name_en": r.name_en,
            "pay_default": r.pay_default, "sort": r.sort, "active": bool(r.active), "built_in": bool(r.built_in),
            "khong_tat": r.key in KHONG_TAT, "updated_by": r.updated_by,
            "updated_at": r.updated_at.isoformat(timespec="minutes") if r.updated_at else None}


def so_dong(db, key):
    """Số dòng chi trên phiếu đang dùng khoản này (màn cấu hình hiện để người sửa biết khoản đang được dùng)."""
    return db.query(TripExpense.id).filter(TripExpense.item_key == key).count()


def doi_cach_tra_mac_dinh(db, r, moi):
    """Trước khi đổi cách trả mặc định của khoản `r` sang `moi`: dòng chi cũ đang THEO MẶC ĐỊNH (pay_channel trống / lạ) ghi rõ cách
    trả cũ — phiếu cũ (đã kiểm, ghi sổ, chi, trả cùng lương) giữ đúng nghĩa. → số dòng đã ghi rõ."""
    cu = TT.CACH_TRA_MAC_DINH.get(r.key, "tien_mat")
    if r.section not in MUC_CACH_TRA or (moi or "tien_mat") == cu:
        return 0
    return db.query(TripExpense).filter(
        TripExpense.item_key == r.key, TripExpense.section.in_(MUC_CACH_TRA),
        or_(TripExpense.pay_channel.is_(None), TripExpense.pay_channel.notin_(TT.CACH_TRA))
    ).update({TripExpense.pay_channel: cu}, synchronize_session=False)


def ten(key):
    """(tên tiếng Việt, tên tiếng Lào) của một khoản thêm mới — None nếu là khoản có sẵn (tên ở từ điển giao diện)."""
    t = TEN.get(key or "")
    return (t["vi"], t["lo"]) if t else None


def moi_khoa():
    return "km_" + ma_moi()[:8]


def gio():
    return dt.datetime.utcnow()
