# -*- coding: utf-8 -*-
"""Quy trình & trách nhiệm — dữ liệu cho màn "Quy trình" và "Tài khoản".

Mọi thứ ở đây là IN RA từ luật đang chạy, không phải bảng viết tay:
  · ma trận ai nhập / kiểm / ghi sổ / chi mục nào  ← services/phan_quyen.QUYEN
  · vai nào thấy tiền bán, tiền chi, được nhập giá  ← thay_tien_ban · thay_tien_chi · nhap_gia_chi
  · mỗi loại chứng từ ghi Nợ / Có gì              ← services/chung_tu.dinh_khoan (đúng hàm lúc ghi sổ),
    tính cho mọi biến thể: xe nhà / xe liên kết · tiền mặt / ngân hàng · Kíp / ngoại tệ · bán cho chủ xe.
Sửa luật thì sửa ở hai tệp kia, màn tự đổi theo — không để màn hình nói một đằng máy làm một nẻo.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services import chung_tu as CT
from services import tai_khoan as TK
from services.bao_mat import nguoi_hien_tai
from services.phan_quyen import thay_gia_kho, QUYEN, nhap_gia_chi, thay_tien_ban, thay_tien_chi

router = APIRouter()

XE = (("EPL", "xe nhà"), ("joint", "xe liên kết"))
TIEN = (("cash", "LAK", "tiền mặt Kíp"), ("cash", "USD", "tiền mặt ngoại tệ"),
        ("bank", "LAK", "ngân hàng Kíp"), ("bank", "USD", "ngân hàng ngoại tệ"))

# loại chứng từ → các biến thể cần in: (điều kiện đọc được, company, section, tiền tệ, cách chi, loại đối tượng)
def _bien_the(loai):
    if loai in ("PXK_NL",):
        return [(x, c, "fuel", None, None, None) for c, x in XE]
    if loai in ("PXK_PT",):
        return [(x, c, "repair", None, None, None) for c, x in XE]
    if loai == "PC_TU":          # quỹ luôn chi tạm ứng bằng tiền mặt Kíp
        return [("%s · tiền mặt Kíp" % x, c, "travel", "LAK", "cash", None) for c, x in XE]
    if loai in ("QT_TU", "TT_CHI", "TT_THU"):   # tất toán tài xế (chỉ xe nhà): tiền mặt Kíp
        return [("tiền mặt Kíp", "EPL", "travel", "LAK", "cash", None)]
    if loai == "PC_SC":
        return [("%s · %s · tiền mặt Kíp" % (x, m), c, s, "LAK", "cash", None) for c, x in XE for s, m in (("repair", "sửa chữa"), ("other", "chi khác"))]
    if loai in ("PC_NCC", "PC_CX", "PT", "PT_BAN"):
        return [(t, "EPL", None, tt, pt, None) for pt, tt, t in TIEN]
    if loai == "HD_BAN":
        return [("bán cho khách", "EPL", None, None, None, "khach"), ("bán cho chủ xe liên kết — trừ vào tiền trả", "EPL", None, None, None, "chu_xe")]
    return [("", "EPL", None, None, None, None)]


def _dinh_khoan(db, loai):
    ra = []
    for dieu_kien, cty, muc, tt, pt, dt_loai in _bien_the(loai):
        no, no_ten, co, co_ten = CT.dinh_khoan(loai, cty, muc, tt, pt)
        no, co = CT._dien_ma_cau_hinh(db, loai, no, co)
        # tên tiếng Lào của hai vế lấy nguyên danh mục bên kế toán — màn Quy trình đổi tiếng Lào thì đổi theo (rà 01/10)
        no_lo, co_lo = (TK.ten(no, "lo") if no else None), (TK.ten(co, "lo") if co else None)
        if loai == "HD_BAN" and dt_loai == "chu_xe":
            no, no_ten = TK.CHU_XE, "%s (trừ vào tiền trả)" % TK.ten(TK.CHU_XE)
            no_lo = "%s (ຫັກຈາກເງິນທີ່ຈະຈ່າຍ)" % TK.ten(TK.CHU_XE, "lo")
        ra.append({"khi": dieu_kien, "no": no, "no_ten": no_ten, "co": co, "co_ten": co_ten, "no_ten_lo": no_lo, "co_ten_lo": co_lo,
                   "no_tt": TK.trang_thai(no) if no else None, "co_tt": TK.trang_thai(co) if co else None})
    return ra


# Định khoản từng DÒNG CHI trên phiếu xuất xe — đúng hàm tai_khoan.dinh_khoan_dong, cho mọi cách trả (rà 30/09).
DONG_CHI = (("fuel", "kho", None, False, "dk_dau_kho"), ("fuel", "mua", None, True, "dk_dau_ghi_no"),
            ("fuel", "mua", None, False, "dk_dau_tien_mat"), ("travel", None, "tien_mat", False, "dk_tien_mat"),
            ("travel", None, "luong", False, "dk_luong"), ("travel", None, "ncc", False, "dk_ncc"),
            ("repair", "kho", None, False, "dk_pt_kho"), ("repair", "mua", None, False, "dk_sua_ngoai"))


def _dong_chi():
    ra = []
    for muc, nguon, cach, ghi_no, nhan in DONG_CHI:
        o = {"nhan": nhan, "muc": muc}
        for cty in ("EPL", "joint"):
            cap = TK.dinh_khoan_dong(cty, muc, nguon, ghi_no=ghi_no, cach=cach)
            no, co = cap.split("/")
            o[cty] = {"cap": cap, "no": no, "no_ten": TK.ten(no), "no_ten_lo": TK.ten(no, "lo"), "no_tt": TK.trang_thai(no),
                      "co": co, "co_ten": TK.ten(co), "co_ten_lo": TK.ten(co, "lo"), "co_tt": TK.trang_thai(co)}
        ra.append(o)
    return ra


@router.get("/api/quy-trinh")
def quy_trinh(db: Session = Depends(get_db), _=Depends(nguoi_hien_tai)):
    vai = [v for v in QUYEN if v != "admin"] + ["admin"]
    return {
        "vai": vai,
        "quyen": {v: {k: sorted(s) for k, s in QUYEN[v].items()} for v in vai},
        "tien": {v: {"thay_tien_ban": thay_tien_ban(v), "thay_tien_chi": thay_tien_chi(v), "thay_gia_kho": thay_gia_kho(v),
                     "nhap_gia": nhap_gia_chi(v)} for v in vai},
        "chung_tu": [{"ma": ma, "ten": ten, "ten_lo": lo, "dinh_khoan": co_dk,
                      "bien_the": _dinh_khoan(db, ma) if co_dk else []}
                     for ma, (ten, lo, co_dk) in CT.LOAI.items()],
        "dong_chi": _dong_chi(),
        "danh_muc": {"chup_ngay": TK.CHUP_NGAY, "so_ma": len(TK.DANH_MUC),
                     # chỉ những mã con bên kế toán CHƯA mở (01/10 đã mở đủ ba → rỗng)
                     "ma_con_khach": [{"ma": m, "cha": c, "ten": v} for m, (c, v, _l) in TK.MA_CON_KHACH.items()
                                      if TK.trang_thai(m) == "ma_con_khach"]},
    }
