# -*- coding: utf-8 -*-
"""GIEO BỘ DỮ LIỆU CHUẨN cho MÁY THỬ 8011 (bản 06/10/2026 — hệ hiện tại: kho EPL ở QLSX anh Tune 5090 / 5014, KHÔNG còn kho tạm 8031).

    python tools/may_thu/gieo_bo_sach.py --chi-in                 in kế hoạch (bước · vai · việc) + danh sách ca, KHÔNG gọi máy nào
    python tools/may_thu/gieo_bo_sach.py                          gieo thật qua HTTP của trang điều xe 8011
    python tools/may_thu/gieo_bo_sach.py --cho-thu-quy 10         như trên, nhưng ở bước xuất phát / xe tới bị chặn vì tạm ứng ĐỢI tối đa
                                                                   10 phút để người thử ghi sổ phiếu chi tạm ứng bên Web anh Tune

Tham số khác: --dx URL (trang điều xe, mặc định EPL_DX hoặc http://127.0.0.1:8011) · --ngay YYYY-MM-DD (ngày lập / xe đi / xe về,
mặc định hôm nay) · --khong-can-sach (cho chạy khi máy còn phiếu — mặc định dừng: số PTU trùng thì phiếu chi tạm ứng bên anh Tune
bị dùng lại).

LUẬT CỦA CÔNG CỤ
  · CHỈ đi qua HTTP của 8011, MỖI BƯỚC ĐÚNG VAI theo bảng Nhiệm Vụ (services/phan_quyen.py), mật khẩu demo 1234. 8011 tự gọi API
    anh Tune 5090 như vận hành thật (phiếu chi tạm ứng / chi mục V, phiếu xuất kho phụ tùng theo chuyến, bút toán, SO) — đó là GHI
    THẬT trên DB demo, đúng như người bấm.
  · KHÔNG đăng nhập Web 5014, KHÔNG gọi 5090 bằng token người dùng, KHÔNG ghi thẳng DB nào. Việc chỉ làm được trên Web (thủ kho Cấp
    dầu theo phiếu đề nghị, thủ quỹ ghi sổ phiếu chi, thu nợ, Tạo phiếu chi DO, Xuất kho bán) → ca dừng ĐÚNG ở đó và bảng cuối in
    «→ SANG WEB ANH TUNE: …»; ca cần đi xong thì chọn đường không cần Web (dầu trạm ngoài, chủ xe tự trả, phụ tùng theo chuyến).
  · Xuất phát / xe tới mà tạm ứng tiền mặt chưa ghi sổ bên anh Tune: luật chặn 409 CHUA_NHAN_TAM_UNG — công cụ thử đúng vai trước;
    bị chặn ĐÚNG LUẬT thì Sếp bấm thay và in «THAY VAI» (hoặc --cho-thu-quy: đợi người thử ghi sổ).
  · Chỉ chạy khi 8011 báo DB bản sao (…_d<số>) và d7 chưa có phiếu (trừ --khong-can-sach). Kho EPL bên anh Tune phải có tồn (kiểm ở
    bước 0.5): thiếu thì dừng, in việc nhập tồn trên Web.

TRƯỚC KHI CHẠY (em chính / chủ dự án): dọn d7 (tools/may_thu/don_may_thu.py that) và DB demo anh Tune (script dọn của đợt 06/10);
8011 (QLSX_GUI_BUT_TOAN=1, EPL_DONG_BO_CHI_LUONG=1), 5090, 5014 bật; script 20261006_logistics_stock_sales_issue.sql đã áp (cho CA-5).

BỘ A — CA ĐÃ GIEO (mọi trường điền đủ: cân mỏ / bãi / cảng, km, ngày, hợp đồng + tệp, phiếu quặng ảnh, POD ký + ảnh, GPS, ghi chú)
  A1  Xe nhà GOM, trọn luồng: tạm ứng tiền mặt NHIỀU DÒNG (phiếu chi "Chi trước") · app tài xế báo cân mỏ (ảnh phiếu cân), GPS dọc
      đường, khai đổ dầu trạm VN-01 trạm GHI NỢ (nợ NCC 625/4021) · tiền nước + tiền chuyến cùng lương · xe tới → PNK_HH · khoá ·
      Tạo SO (SO cước + doanh thu 1211/708). Dừng ở Web: thủ quỹ ghi sổ tạm ứng, thu nợ, Tạo phiếu chi DO (cùng lương).
  A2  Xe nhà GIAO lấy trọn lô của A1 → PXK_HH · dầu trạm VN-01 ghi nợ · phí cao tốc tự thêm theo tuyến (tạm ứng) · Tổ sửa thay lốp
      LẤY KHO (phiếu 48 xuất nội bộ, 614/1371) · người nhận KÝ POD trên máy tài xế + Bãi đính kèm biên bản · khoá · Tạo SO.
  A3  Xe nhà GOM thứ hai của cùng tài xế A1 (đủ chuyến để tất toán): chỉ khoản cùng lương (không tạm ứng → tài xế tự xuất phát qua
      app, không bị chặn) · khai đổ trạm LA-02 TÀI XẾ TRẢ TIỀN TÚI (chi bù lúc tất toán) · báo hỏng có chi tiền "Tôi đã tự trả" → Tổ
      sửa duyệt mua ngoài → phiếu chi mục V (Chi khác) · khoá · Tạo SO.
  A4  Xe THUÊ ຮ່ວມ-07 (app tx03): dầu trạm chủ xe tự trả · Tổ sửa lấy bầu hơi KHO = XUẤT BÁN cho đối tác (giá bán) · cân bãi 42,6 t
      (QUÁ TẢI 2,6 t) · khoá → thuê xe 621/4022 + phí quản lý 4022/715 + cắt quá tải 4022/758 + giá vốn 607/1371 · Tạo SO → SO cước +
      SO nhiên liệu (dòng phụ tùng) + doanh thu 708 / 707. Dừng: Tất toán đối tác (anh bấm).
  A5  Xe THUÊ ຮ່ວມ-08 đối tác TỰ LO HẾT (dầu, tiền ăn chủ xe tự trả) · khoá → 621/4022 + 4022/715 · Tạo SO. Dừng: Tất toán đối tác.
  A6  Xe THUÊ ຮ່ວມ-09 lấy DẦU KHO EPL (xuất bán, giá bán 33.000) — DỪNG Ở WEB: thủ kho «Cấp dầu theo phiếu đề nghị».
  A7  Xe THUÊ ຮ່ວມ-07 (tx03) ĐANG TRÊN ĐƯỜNG: báo cân mỏ qua app, GPS sống, một báo sự cố "bị giữ xe" CHỜ Bãi duyệt.
  A8  Xe nhà 344 ĐANG CHỜ KIỂM: đã lập, in phiếu đề nghị xuất kho nhiên liệu + tạm ứng, gửi kiểm mục I – IV, chưa ai kiểm.
  A9  Kho hàng quặng: một phiếu điều chỉnh ĐÃ DUYỆT (DC_HH, lô A3 −0,3 t) + một phiếu CHỜ DUYỆT (lô A5 +0,2 t).

BỘ B — CHỪA CHO CHỦ DỰ ÁN BẤM TỪ ĐẦU (công cụ chỉ kiểm điều kiện, KHÔNG lập DO): xem CA_B bên dưới / bảng cuối.

Dừng NGAY ở bước hỏng: in bước · vai · việc · HTTP · mã lỗi · câu lỗi, rồi in bảng những gì đã gieo. Cuối cùng in bảng từng DO / ca:
trạng thái, số chứng từ (bên điều xe và bên anh Tune), việc còn chờ ai bấm ở đâu.
"""
import argparse
import datetime as dt
import io
import json
import math
import os
import random
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MAT_KHAU = "1234"
VAI_DX = ("admin", "thabok", "ketoan", "ketoancp", "khonl", "totsua", "tx01", "tx02", "tx03")
TEN_VAI = {"admin": "Sếp", "thabok": "Admin Thà Bốc (Bãi)", "ketoan": "KT Thu/Chi VC", "ketoancp": "KT Chi phí VC",
           "khonl": "KT kho xăng dầu", "totsua": "Tổ sửa chữa", "tx01": "Tài xế tx01 (app)", "tx02": "Tài xế tx02 (app)",
           "tx03": "Tài xế tx03 (app)", "—": "máy"}

# ---------------------------------------------------------------- danh mục giữ lại sau dọn — đối chiếu theo mã / tên
TUYEN_GOM = ("ກາສີ", "ທ່າບົກ")                 # mỏ → bãi, không BOT
TUYEN_GOM_2 = ("ຊຽງຂວາງ", "ທ່າບົກ")             # mỏ thứ hai → bãi
TUYEN_GIAO = ("ທ່າບົກ", "ທ່າເຮືອກະລໍ")          # bãi → cảng, có BOT (máy tự thêm dòng phí cao tốc)
KHACH = "EPLKH-0834a9e9606b"                     # ຄຳຕຸ້ຍ — hợp đồng HDVC-2026-001, bảng giá các tuyến
CHU_XE = "0a073ea75bb3"                          # ທ້າວ ຄຳຫລ້າ — xe ຮ່ວມ-07/08/09, hợp đồng thuê HDTX-2026-001
HOP_DONG = ("HDVC-2026-001", "HDTX-2026-001")
PT_LOP, PT_BAU_HOI = "12R22.5", "bầu hơi"        # chữ trong tên phụ tùng (danh mục bản chép, tồn ở kho QLSX)
GIA_IV = {"x_food": 100000, "x_phone": 150000, "x_bridge": 50000, "x_parking": 30000, "x_vn": 430000, "x_water": 60000,
          "x_trip": 1800000}
GIA_BAN_DAU = 33000                              # giá bán dầu kho cho đối tác (KT kho xăng dầu gõ lúc kiểm mục III)
GIA_BAN_BAU_HOI = 700000                         # giá bán bầu hơi cho đối tác (KT Chi phí gõ lúc kiểm mục V)
# tồn tối thiểu ở kho EPL bên anh Tune: TOI_THIEU cho bộ A (thiếu thì dừng), NEN_CO cho cả bộ B (thiếu thì cảnh báo)
TON_TOI_THIEU = {PT_LOP: 1, PT_BAU_HOI: 1, "KHO-TB": 140}
TON_NEN_CO = {PT_LOP: 2, PT_BAU_HOI: 4, "KHO-TB": 220}

# iii: (điểm, lít, kiểu) — kiểu "kho" (lĩnh kho EPL) · "ghi_no" (trạm ngoài, trạm ghi nợ EPL) · "chu_xe" (chủ xe tự trả)
# iv: (khoản, cách) — "tien_mat" (Chi ngay khi xe đi → tạm ứng) · "luong" (trả cùng lương) · "chu_xe" (chủ xe tự trả)
DO = {
    "A1": {"ten": "Xe nhà GOM trọn luồng — tạm ứng nhiều dòng, nợ NCC trạm VN-01, app tài xế", "kind": "gom", "xe": "341",
           "tai_xe": "DRV-01", "tk": "tx01", "tuyen": TUYEN_GOM, "can_mo_app": 40.0, "can_ve": 39.6,
           "iv": [("x_food", "tien_mat"), ("x_phone", "tien_mat"), ("x_bridge", "tien_mat"), ("x_parking", "tien_mat"),
                  ("x_water", "luong"), ("x_trip", "luong")],
           "khai_do": ("VN-01", 40, 27000, "VND", True), "gps": 10,
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A1: xe nhà gom, tạm ứng 4 dòng, đổ dầu trạm VN-01 ghi nợ",
           "con_cho": ["→ SANG WEB ANH TUNE: thủ quỹ GHI SỔ phiếu chi tạm ứng (Kế toán → Danh sách phiếu chi, tham chiếu PTU-…)",
                       "→ SANG WEB ANH TUNE: Tạo phiếu chi DO cho tiền nước + tiền chuyến (cùng lương) → Ghi sổ",
                       "→ SANG WEB ANH TUNE: thu nợ SO cước (Kế toán → Danh sách công nợ → Tạo phiếu thu → Ghi sổ)",
                       "8011 ketoancp: Tất toán tài xế ທ້າວ ທັດສະດາພອນ cùng A3 (CA-4)"]},
    "A2": {"ten": "Xe nhà GIAO lấy lô A1 — dầu trạm ghi nợ, sửa xe lấy lốp kho, ký POD trên máy", "kind": "giao", "xe": "342",
           "tai_xe": "DRV-02", "tk": "tx02", "tuyen": TUYEN_GIAO, "lo": "A1", "can_ve": 39.4,
           "iii": [("VN-01", 200, "ghi_no")], "gia_iii": (27000, "VND"),
           "iv": [("x_vn", "tien_mat"), ("x_water", "luong"), ("x_trip", "luong")],
           "sua_kho": (PT_LOP, 1, "tire", "Thay lốp nổ dọc đường (gieo bộ chuẩn)"), "pod": True, "gps": 12,
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A2: giao bãi → cảng, lấy trọn lô A1",
           "con_cho": ["→ SANG WEB ANH TUNE: thủ quỹ GHI SỔ phiếu chi tạm ứng (sang VN + phí cao tốc tiền mặt)",
                       "→ SANG WEB ANH TUNE: thu nợ SO cước", "→ SANG WEB ANH TUNE: Tạo phiếu chi DO cho tiền nước + tiền chuyến"]},
    "A3": {"ten": "Xe nhà GOM thứ hai cùng tài xế A1 — dầu trả tiền túi, báo hỏng tự trả (đủ để tất toán)", "kind": "gom",
           "xe": "341", "tai_xe": "DRV-01", "tk": "tx01", "tuyen": TUYEN_GOM_2, "can_mo": 41.0, "can_ve": 40.6,
           "iv": [("x_water", "luong"), ("x_trip", "luong")],
           "khai_do": ("LA-02", 50, 21500, "LAK", False),
           "bao_hong": ("tire", "Vá lốp ở garage dọc đường — tài xế trả trước", 150000), "gps": 8,
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A3: chuyến thứ hai của ທ້າວ ທັດສະດາພອນ, không tạm ứng",
           "con_cho": ["→ SANG WEB ANH TUNE: thủ quỹ chi + GHI SỔ phiếu chi mục V (vá lốp, tham chiếu PCSC-V-…)",
                       "→ SANG WEB ANH TUNE: thu nợ SO cước · Tạo phiếu chi DO (cùng lương)",
                       "8011 ketoancp: Tất toán tài xế (CA-4) — dầu trả túi thành chi bù"]},
    "A4": {"ten": "Xe THUÊ ຮ່ວມ-07 — bầu hơi lấy kho (xuất bán), QUÁ TẢI, phí 2 %, SO nhiên liệu", "kind": "gom",
           "xe": "ຮ່ວມ-07", "tai_xe": "DRV-LK-01", "tk": "tx03", "tuyen": TUYEN_GOM, "can_mo_app": 43.0, "can_ve": 42.6,
           "iii": [("LA-02", 150, "chu_xe")], "iv": [("x_food", "chu_xe")],
           "sua_kho": (PT_BAU_HOI, 1, "breakdown", "Thay bầu hơi bị rò (gieo bộ chuẩn)"), "gia_ban_v": GIA_BAN_BAU_HOI, "gps": 8,
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A4: xe thuê chở 42,6 t (vượt ngưỡng 40 t), bầu hơi lấy kho EPL",
           "con_cho": ["8011 ketoan: Tất toán đối tác ທ້າວ ຄຳຫລ້າ → Lập đề nghị trả (máy cấn trừ SO nhiên liệu) → Web ghi sổ phiếu chi",
                       "→ SANG WEB ANH TUNE: thu nợ SO cước"]},
    "A5": {"ten": "Xe THUÊ ຮ່ວມ-08 đối tác tự lo hết", "kind": "gom", "xe": "ຮ່ວມ-08", "tai_xe": "DRV-LK-02", "tuyen": TUYEN_GOM,
           "can_mo": 40.0, "can_ve": 39.8, "iii": [("LA-02", 200, "chu_xe")], "iv": [("x_food", "chu_xe")],
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A5: xe thuê, chủ xe tự trả dầu và tiền ăn",
           "con_cho": ["8011 ketoan: Tất toán đối tác (trả đủ tiền thuê − phí quản lý)", "→ SANG WEB ANH TUNE: thu nợ SO cước"]},
    "A6": {"ten": "Xe THUÊ ຮ່ວມ-09 lấy dầu KHO EPL (xuất bán) — dừng chờ thủ kho cấp dầu trên Web", "kind": "gom",
           "xe": "ຮ່ວມ-09", "tai_xe": "DRV-LK-03", "tuyen": TUYEN_GOM, "can_mo": 42.0, "iii": [("KHO-TB", 60, "kho")],
           "gia_ban_iii": GIA_BAN_DAU,
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A6: xe thuê lĩnh 60 L dầu kho Thà Bốc (xuất bán cho đối tác)",
           "con_cho": ["→ SANG WEB ANH TUNE: thủ kho Quản lý kho → Danh sách chứng từ → Cấp dầu theo phiếu đề nghị → PLNL-…",
                       "rồi 8011: khonl ghi sổ mục III · Bãi xuất phát / xe tới (cân bãi > 40 t để thấy dòng 758) · ketoan khoá + Tạo SO"]},
    "A7": {"ten": "Xe THUÊ ຮ່ວມ-07 ĐANG TRÊN ĐƯỜNG — GPS sống, báo sự cố chờ duyệt", "kind": "gom", "xe": "ຮ່ວມ-07",
           "tai_xe": "DRV-LK-01", "tk": "tx03", "tuyen": TUYEN_GOM, "can_mo_app": 41.5, "iii": [("LA-02", 120, "chu_xe")],
           "gps": 10, "gps_song": True, "su_co_cho": ("held", "Bị giữ xe kiểm tra giấy tờ ở trạm cân"),
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A7: xe thuê đang chạy về bãi",
           "con_cho": ["8011 thabok: Theo dõi tuyến → Diễn biến → Duyệt / Từ chối báo sự cố «bị giữ xe»",
                       "CA-6: Tổ sửa lấy phụ tùng kho cho xe này (xuất bán đối tác)", "tài xế tx03: Báo đã về · Bãi: Xe đã tới"]},
    "A8": {"ten": "Xe nhà 344 ĐANG CHỜ KIỂM — đã gửi kiểm mục I – IV", "kind": "gom", "xe": "344", "tai_xe": "DRV-04",
           "tuyen": TUYEN_GOM, "can_mo": 40.0, "iii": [("KHO-TB", 80, "kho")],
           "iv": [("x_food", "tien_mat"), ("x_phone", "tien_mat"), ("x_water", "luong"), ("x_trip", "luong")],
           "ghi_chu": "Gieo bộ chuẩn 06/10 — A8: chờ ba kế toán kiểm",
           "con_cho": ["8011 ketoan: kiểm mục I, II (nhập số phiếu quặng)", "8011 khonl: kiểm mục III · ketoancp: giá + kiểm + ghi sổ mục IV",
                       "→ SANG WEB ANH TUNE: Cấp dầu PLNL · ghi sổ phiếu chi tạm ứng"]},
}

# Bộ B — chừa cho chủ dự án bấm từ đầu. "dk": điều kiện công cụ kiểm (xe / tài xế rảnh, tồn kho, DO nguồn).
CA_B = [
    {"ma": "CA-1", "ten": "Xe nhà GOM trọn luồng có dầu kho + tạm ứng + app tài xế (tracking: cân, GPS, khai dầu, mất mạng)",
     "xe": "345", "tai_xe": "DRV-02", "tk": "tx02", "ton": {"KHO-TB": 50},
     "vai": "thabok lập → ketoan · khonl · ketoancp kiểm → Web tune Cấp dầu + ghi sổ phiếu chi tạm ứng → tx02 app → thabok Xe đã tới "
            "→ ketoan Khoá + Tạo SO → Web thu nợ",
     "tu_dau": "8011 thabok → Phiếu xuất xe → + Phiếu mới → Gom (mỏ → bãi): xe 345, ທ້າວ ບຸນມີ, ກາສີ → ທ່າບົກ, dầu KHO-TB 50 L, "
               "tiền ăn + điện thoại (Chi ngay khi xe đi) + tiền nước + tiền chuyến",
     "muc": "HUONG_DAN_BAM_TAY_3_MODULE mục 1 + mục 5"},
    {"ma": "CA-2", "ten": "Xe nhà GIAO lấy lô của CA-1, người nhận ký POD trên máy tài xế",
     "xe": "342", "tai_xe": "DRV-02", "tk": "tx02", "ton": {},
     "vai": "thabok lập (chọn lô CA-1) → kiểm như CA-1 → tx02 Giao hàng hoàn tất · ký nhận → thabok Xe đã tới (cân cảng, số POD) "
            "→ ketoan Khoá + Tạo SO",
     "tu_dau": "sau khi CA-1 xe tới: 8011 thabok → Phiếu xuất xe → + Phiếu mới → Giao (bãi → khách) → Lấy từ lô (phiếu gom) = lô CA-1",
     "muc": "mục 2"},
    {"ma": "CA-3", "ten": "Xe THUÊ lấy dầu kho EPL (xuất bán) + quá tải + tất toán đối tác (gộp cả A4, A5 đang chờ trả)",
     "xe": "ຮ່ວມ-08", "tai_xe": "DRV-LK-02", "ton": {"KHO-TB": 30},
     "vai": "thabok lập → khonl Giá bán cho chủ xe 33.000 → Web tune Cấp dầu → Bãi xuất phát / xe tới (cân bãi > 40 t) → ketoan "
            "Khoá (621/4022 · 4022/715 · 4022/758 · 607/1371) + Tạo SO (SO nhiên liệu) → ketoan Tất toán đối tác → Web ghi sổ phiếu chi",
     "tu_dau": "8011 thabok → + Phiếu mới → Gom: xe ຮ່ວມ-08, ທ້າວ ຄຳສີ, dầu KHO-TB 30 L (Ai chi = EPL ứng)",
     "muc": "mục 3"},
    {"ma": "CA-4", "ten": "Tất toán tài xế ທ້າວ ທັດສະດາພອນ (A1 + A3) + tiền chuyến & nước trả cùng lương",
     "tai_xe_tt": "DRV-01", "ton": {},
     "vai": "Web tune ghi sổ phiếu chi tạm ứng của A1 → (tuỳ) ketoancp sửa Chi thật mục IV của A1 → ketoancp Tất toán tài xế → "
            "Chốt tất toán → Web ghi sổ phiếu chi bù · Web Tạo phiếu chi DO (cùng lương) A1 / A3 → ghi sổ → 8011 Tiền chuyến & "
            "tiền nước tài xế = Đã trả",
     "tu_dau": "8011 ketoancp → Mô-đun vận tải → Tất toán tài xế → kỳ tháng gieo → ທ້າວ ທັດສະດາພອນ",
     "muc": "mục 4 + 4B (chốt trên 8011 là KHÔNG lùi được — làm cuối)"},
    {"ma": "CA-5", "ten": "Bán quầy phụ tùng — đối tác ທ້າວ ຄຳຫລ້າ mua 1 bầu hơi (cấn trừ vào tiền trả đối tác)",
     "ton": {PT_BAU_HOI: 1},
     "vai": "Web: KT Doanh thu (máy thử tune) Đơn hàng bán → Tạo thủ công (chi nhánh EPL, tiền LAK) → Duyệt → Chuyển sản xuất → thủ kho "
            "(tune) Xuất kho bán KHO-PT → bút toán 607/1371 · 1211/707 → 8011 ketoan Tất toán đối tác (khung Mua ở quầy)",
     "tu_dau": "Web https://localhost:5014 → Bán hàng → Đơn hàng bán → Tạo thủ công (cần script 20261006_logistics_stock_sales_issue.sql)",
     "muc": "mục 7B"},
    {"ma": "CA-6", "ten": "Sửa chữa: theo chuyến cho xe thuê A7 (lấy kho = xuất bán) + ngoài chuyến phiếu 48 trên Web",
     "do_nguon": "A7", "ton": {PT_BAU_HOI: 2},
     "vai": "8011 totsua Theo dõi tuyến → A7 → Báo sự cố / sửa xe → Lấy từ kho (xuất kho) → ketoancp Giá bán + ghi sổ mục V · Web "
            "thủ kho Tạo phiếu xuất → Xuất dùng / sửa chữa (nội bộ) → bút toán 614/1371",
     "tu_dau": "8011 totsua → Theo dõi tuyến → xe ຮ່ວມ-07 (DO A7 đang chạy) · Web → Quản lý kho → Tạo phiếu xuất",
     "muc": "mục 6 + 7A"},
]


class Hong(Exception):
    """Một lời gọi trả mã không mong đợi — runner in bước / vai / lỗi rồi dừng."""
    def __init__(self, vai, method, duong, ma, than):
        d = (than or {}).get("detail") if isinstance(than, dict) else None
        d = d if isinstance(d, dict) else ({"loi": str(d or than)[:400]} if d or than else {})
        self.vai, self.http, self.ma, self.loi = vai, ma, d.get("ma"), d.get("loi") or json.dumps(than, ensure_ascii=False)[:400]
        self.duong = "%s %s" % (method, duong)
        super().__init__("%s → HTTP %s %s: %s" % (self.duong, ma, self.ma or "", self.loi))


class May:
    """Trang điều xe 8011: đăng nhập từng vai, gọi API JSON hoặc multipart (ảnh, chữ ký, tệp)."""

    def __init__(self, goc):
        self.goc, self.token = goc.rstrip("/"), {}

    def tho(self, method, duong, body=None, vai=None, het_gio=180, du=None, kieu=None):
        dau = {"Accept": "application/json"}
        if du is None and body is not None:
            du, kieu = json.dumps(body).encode("utf-8"), "application/json"
        if kieu:
            dau["Content-Type"] = kieu
        if vai:
            dau["Authorization"] = "Bearer " + self.token[vai]
        yc = urllib.request.Request(self.goc + duong, data=du, method=method, headers=dau)
        try:
            with urllib.request.urlopen(yc, timeout=het_gio) as t:
                tho = t.read()
                return t.status, (json.loads(tho) if tho else None), dict(t.headers)
        except urllib.error.HTTPError as e:
            tho = e.read()
            try:
                return e.code, (json.loads(tho) if tho else None), dict(e.headers)
            except ValueError:
                return e.code, {"detail": tho.decode("utf-8", "replace")[:400]}, dict(e.headers)

    def vao(self, vai):
        s, g, _ = self.tho("POST", "/api/dang-nhap", {"username": vai, "password": MAT_KHAU})
        if s != 200:
            raise Hong(vai, "POST", "/api/dang-nhap", s, g)
        self.token[vai] = g["token"]
        return g.get("user") or {}

    def goi(self, vai, method, duong, body=None, mong=(200,)):
        s, g, _ = self.tho(method, duong, body, vai)
        if s not in mong:
            raise Hong(vai, method, duong, s, g)
        return g

    def goi_tep(self, vai, duong, truong, tep, mong=(200,)):
        """POST multipart/form-data: `truong` {tên: chữ}, `tep` [(tên ô, tên tệp, kiểu, bytes)]."""
        ranh = "----EPLgieo%016x" % random.getrandbits(64)
        b = io.BytesIO()
        for k, v in truong.items():
            b.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (ranh, k, v)).encode("utf-8"))
        for o, ten, kieu, du in tep:
            b.write(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n'
                     % (ranh, o, ten, kieu)).encode("utf-8"))
            b.write(du)
            b.write(b"\r\n")
        b.write(("--%s--\r\n" % ranh).encode("utf-8"))
        s, g, _ = self.tho("POST", duong, vai=vai, du=b.getvalue(), kieu="multipart/form-data; boundary=" + ranh)
        if s not in mong:
            raise Hong(vai, "POST", duong, s, g)
        return g


# ================================================================ tệp mẫu (ảnh phiếu cân, chữ ký, biên bản, hợp đồng) — dựng trong máy
def _png(w, h, den):
    """PNG xám 8 bit: `den(x, y)` True → điểm đen. Đủ hợp lệ cho ô ảnh / chữ ký (kiểu image/png)."""
    tho = b"".join(b"\x00" + bytes(0 if den(x, y) else 255 for x in range(w)) for y in range(h))

    def khoi(loai, du):
        return struct.pack(">I", len(du)) + loai + du + struct.pack(">I", zlib.crc32(loai + du) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + khoi(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + khoi(b"IDAT", zlib.compress(tho, 9)) + khoi(b"IEND", b""))


def anh_phieu(so):
    """'Ảnh' một tờ phiếu: khung + các dòng kẻ, độ dày dòng theo `so` để mỗi ảnh khác nhau."""
    return _png(240, 160, lambda x, y: x in (4, 235) or y in (4, 155) or (y % 18 == 0 and 20 < x < 20 + (so * 37) % 200 + 20))


def chu_ky():
    """Chữ ký: một nét lượn sóng."""
    return _png(300, 90, lambda x, y: abs(y - (45 + 22 * math.sin(x / 17.0) * math.cos(x / 53.0))) < 1.6 and 15 < x < 285)


def pdf(dong):
    """PDF một trang, chữ ASCII (Helvetica) — bản scan giả cho hợp đồng / biên bản."""
    noi = "BT /F1 13 Tf 56 780 Td " + " ".join("(%s) Tj 0 -22 Td" % s.replace("(", "[").replace(")", "]") for s in dong) + " ET"
    ds = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
          "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
          "<< /Length %d >>\nstream\n%s\nendstream" % (len(noi), noi),
          "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    ra, vt = b"%PDF-1.4\n", []
    for i, o in enumerate(ds, 1):
        vt.append(len(ra))
        ra += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("latin-1")
    x = len(ra)
    ra += ("xref\n0 %d\n0000000000 65535 f \n" % (len(ds) + 1)).encode() + b"".join(("%010d 00000 n \n" % v).encode() for v in vt)
    return ra + ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(ds) + 1, x)).encode()


# ================================================================ ngữ cảnh + tiện ích
class Ngu:
    def __init__(self, a):
        self.a = a
        self.dx = May(a.dx)
        self.ngay = a.ngay
        self.ky = a.ngay[:7]
        self.user = {}                  # vai → người dùng (driver_id…)
        self.dm = {}                    # danh mục đã chọn
        self.do = {}                    # "A1" → {"id", "doc_no", …}
        self.ghi_chu = []               # THAY VAI, cảnh báo tồn…
        self.ca_b = []                  # kết quả kiểm điều kiện bộ B


def dx(n, vai, method, duong, body=None, mong=(200,)):
    return n.dx.goi(vai, method, duong, body, mong)


def phieu(n, k, vai="admin"):
    return dx(n, vai, "GET", "/api/trips/%s" % n.do[k]["id"])


def dong_muc(p, muc):
    return [e for e in (p.get("expenses") or []) if e.get("section") == muc]


def can(dk, cau):
    if not dk:
        raise Hong("—", "KIỂM", "", "-", {"detail": {"ma": "KHONG_DUNG_KY_VONG", "loi": cau}})


def tuyen_cua(n, k):
    return n.dm["tuyen"][DO[k]["tuyen"]]


def gio_may(phut_truoc=0.0):
    """Giờ máy điện thoại (UTC, ISO 'Z') lùi `phut_truoc` phút — điểm GPS / thao tác ghi theo giờ này."""
    return (dt.datetime.utcnow() - dt.timedelta(minutes=phut_truoc)).replace(microsecond=0).isoformat() + "Z"


def _pt(n, chu):
    return next(p for p in n.dm["pt"] if chu in (p.get("name") or ""))


def _ma_ngan(n, k):
    return n.do[k]["doc_no"].split("/")[0]


# ---------------------------------------------------------------- khối 0: máy, vai, danh mục, tồn kho, hợp đồng
def b_kiem_may(n):
    s, g, _ = n.dx.tho("GET", "/api/suc-khoe")
    if s != 200 or not g or not g.get("ok"):
        raise Hong("—", "GET", "/api/suc-khoe", s, g)
    ten = g.get("db") or ""
    if not re.search(r"_d\d+$", ten):
        raise Hong("—", "GET", "/api/suc-khoe", s, {"detail": {"ma": "KHONG_PHAI_BAN_SAO",
                   "loi": "%s đang nối DB «%s» — công cụ chỉ gieo vào bản sao của máy thử (tên …_d<số>)." % (n.dx.goc, ten)}})
    print("      trang điều xe %s → DB %s" % (n.dx.goc, ten))


def b_dang_nhap(n):
    for v in VAI_DX:
        n.user[v] = n.dx.vao(v)
    print("      đăng nhập %d vai (mật khẩu demo): %s" % (len(VAI_DX), ", ".join(VAI_DX)))


def b_may_sach(n):
    s, g, h = n.dx.tho("GET", "/api/trips?co=1", vai="admin")
    tong = int(h.get("X-Tong") or h.get("x-tong") or len(g or []))
    if tong and not n.a.khong_can_sach:
        raise Hong("admin", "GET", "/api/trips", s, {"detail": {"ma": "MAY_CHUA_SACH", "loi": "d7 còn %d phiếu — dọn d7 "
                   "(tools/may_thu/don_may_thu.py that) và DB demo anh Tune trước, hoặc chạy với --khong-can-sach." % tong}})
    g = dx(n, "ketoan", "GET", "/api/but-toan-cho?gioi_han=1")
    n.dm["gui_bt"] = bool(g.get("co_duong_gui"))
    print("      phiếu đang có: %d · gửi bút toán sang kế toán: %s" % (tong, "BẬT" if n.dm["gui_bt"] else "TẮT (bút toán nằm chờ)"))
    if not n.dm["gui_bt"]:
        n.ghi_chu.append("8011 chưa bật QLSX_GUI_BUT_TOAN — bút toán khoá phiếu / doanh thu nằm 'chờ gửi', không có số GL.")


def b_danh_muc(n):
    xe = {v["truck_no"]: v for v in dx(n, "admin", "GET", "/api/vehicles")}
    tx = {t.get("driver_code"): t for t in dx(n, "admin", "GET", "/api/drivers")}
    kh = [k for k in dx(n, "admin", "GET", "/api/customers") if (k.get("code") or "") == KHACH]
    tuyen = dx(n, "admin", "GET", "/api/routes")
    diem = {d.get("code"): d for d in dx(n, "admin", "GET", "/api/fuel-places")}
    pt = dx(n, "admin", "GET", "/api/parts")

    def tim_tuyen(di, den):
        song = [t for t in tuyen if t.get("active") is not False]
        r = [t for t in song if (t.get("name") or "").strip() == "%s → %s" % (di, den)] or \
            [t for t in song if di in (t.get("origin") or "") and den in (t.get("destination") or "")]
        can(r, "không có tuyến %s → %s đang dùng" % (di, den))
        return r[0]

    can(kh, "không có khách mã kế toán %s" % KHACH)
    n.dm.update({"xe": xe, "tx": tx, "khach": kh[0], "diem": diem, "pt": pt,
                 "tuyen": {t: tim_tuyen(*t) for t in (TUYEN_GOM, TUYEN_GOM_2, TUYEN_GIAO)}})
    dung = {(d["xe"], d["tai_xe"]) for d in DO.values()} | {(c["xe"], c["tai_xe"]) for c in CA_B if c.get("xe")}
    for so_xe, ma_tx in dung:
        can(so_xe in xe and ma_tx in tx, "không có xe %s hoặc tài xế %s" % (so_xe, ma_tx))
        if not n.a.khong_can_sach:
            can(xe[so_xe].get("status") in (None, "available") and tx[ma_tx].get("status") in (None, "available"),
                "xe %s (%s) / tài xế %s (%s) chưa rảnh — dọn d7 trước" % (so_xe, xe[so_xe].get("status"), ma_tx, tx[ma_tx].get("status")))
    for vai in ("tx01", "tx02", "tx03"):
        can(n.user[vai].get("driver_id"), "tài khoản %s chưa gắn tài xế" % vai)
    for ma in ("KHO-TB", "VN-01", "LA-02"):
        can(ma in diem, "không có điểm dầu %s" % ma)
    can(diem["VN-01"].get("supplier_id"), "trạm VN-01 chưa gắn nhà cung cấp — khai đổ trạm ghi nợ sẽ bị chặn")
    for chu in (PT_LOP, PT_BAU_HOI):
        can(any(chu in (p.get("name") or "") for p in pt), "không có phụ tùng tên chứa «%s»" % chu)
    print("      khách %s · %d tuyến · %d xe · %d tài xế · tài xế có app: tx01, tx02, tx03" % (
        kh[0]["name"], len(n.dm["tuyen"]), len(xe), len(tx)))


def b_ton_kho(n):
    """Tồn kho EPL bên anh Tune (đọc qua 8011). Công cụ KHÔNG nhập kho — thiếu cho bộ A thì dừng và nói việc phải làm trên Web."""
    pt = {chu: (_pt(n, chu).get("qty") or 0) for chu in (PT_LOP, PT_BAU_HOI)}
    nl = {x.get("code"): (x.get("ton_lit") or 0) for x in (dx(n, "admin", "GET", "/api/kho-xem").get("nhien_lieu") or [])}
    ton = dict(pt, **{"KHO-TB": nl.get("KHO-TB", 0)})
    n.dm["ton"] = ton
    thieu = ["%s: có %s, cần ≥ %s" % (k, ton.get(k, 0), v) for k, v in TON_TOI_THIEU.items() if (ton.get(k) or 0) < v]
    if thieu:
        raise Hong("admin", "GET", "/api/kho-xem", "-", {"detail": {"ma": "THIEU_TON_KHO", "loi": (
            "Kho EPL bên anh Tune thiếu tồn cho bộ A — " + "; ".join(thieu) + ". → SANG WEB ANH TUNE: Quản lý kho → Tạo phiếu nhập → "
            "Nhập kho tổng hợp (53), chi nhánh EPL: lốp 12R22.5 (KHO-PT), bầu hơi (KHO-PT), dầu EPLNL-diesel (KHO-TB) có giá vốn; "
            "hoặc em chính chạy tools/may_thu/chuyen_ton_dau_qlsx.py --that. Rồi chạy lại công cụ.")}})
    it = ["%s: có %s, nên ≥ %s" % (k, ton.get(k, 0), v) for k, v in TON_NEN_CO.items() if (ton.get(k) or 0) < v]
    if it:
        n.ghi_chu.append("Tồn kho đủ cho bộ A nhưng ít cho bộ B (CA-1…CA-6): " + "; ".join(it) + " — nhập thêm trên Web trước khi bấm.")
    print("      tồn kho EPL: lốp %s · bầu hơi %s · KHO-TB %s L" % (ton[PT_LOP], ton[PT_BAU_HOI], ton["KHO-TB"]))


def b_hop_dong(n):
    """Hợp đồng vận chuyển + hợp đồng thuê xe: chưa có bản scan thì KT Thu/Chi đính kèm (PDF một trang)."""
    for hd in dx(n, "ketoan", "GET", "/api/hop-dong"):
        if hd.get("contract_no") not in HOP_DONG:
            continue
        if "files" not in hd:
            print("      %s: vai KT Thu/Chi không thấy tệp hợp đồng — bỏ qua" % hd["contract_no"])
            continue
        if hd.get("files"):
            print("      %s đã có %d tệp — giữ" % (hd["contract_no"], len(hd["files"])))
            continue
        du = pdf(["EPL LOGISTICS - %s" % hd["contract_no"], "Hop dong %s" % ("van chuyen quang" if hd["kind"] == "khach" else "thue xe lien ket"),
                  "Hieu luc %s - %s" % (hd.get("valid_from"), hd.get("valid_to")), "Ban scan mau (gieo bo chuan 06/10)"])
        n.dx.goi_tep("ketoan", "/api/hop-dong/%s/tep" % hd["id"], {}, [("tep", "%s.pdf" % hd["contract_no"], "application/pdf", du)])
        print("      đính kèm bản scan %s.pdf" % hd["contract_no"])


# ---------------------------------------------------------------- phiếu xuất xe: các bước dùng chung
def _dong_lap(n, k):
    d, diem = DO[k], n.dm["diem"]
    ra = []
    for ma, lit, kieu in d.get("iii", []):
        x = {"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": diem[ma]["id"]}
        if kieu == "ghi_no":
            x["ghi_no"] = True
        if kieu == "chu_xe":
            x["paid_by_epl"] = False
        ra.append(x)
    for khoan, cach in d.get("iv", []):
        x = {"section": "travel", "item_key": khoan, "qty": 1}
        if cach == "chu_xe":
            x["paid_by_epl"] = False
        else:
            x["pay_channel"] = cach
        ra.append(x)
    return ra


def lap(k):
    def f(n):
        d = DO[k]
        xe = dx(n, "admin", "GET", "/api/vehicles/%s" % n.dm["xe"][d["xe"]]["id"])        # công-tơ-mét mới nhất (xe chạy nhiều chuyến)
        tx = n.dm["tx"][d["tai_xe"]]
        body = {"kind": d["kind"], "vehicle_id": xe["id"], "driver_id": tx["id"], "customer_id": n.dm["khach"]["id"],
                "route_id": tuyen_cua(n, k)["id"], "goods_type": "iron_ore", "doc_date": n.ngay, "out_date": n.ngay,
                "odo_out": round(xe.get("odometer_km") or 100000), "note": d["ghi_chu"], "expenses": _dong_lap(n, k)}
        if d["kind"] == "gom" and d.get("can_mo"):
            body["weight_origin"] = d["can_mo"]
        if d["kind"] == "giao":
            lo = [x for x in dx(n, "thabok", "GET", "/api/kho-hang/lo") if x.get("lo_trip_id") == n.do[d["lo"]]["id"]]
            can(lo and (lo[0].get("con_t") or 0) > 0, "lô của %s không còn hàng để giao" % d["lo"])
            body["goods"] = [{"loai": "hang", "goods_name": lo[0]["goods_name"], "qty_t": round(lo[0]["con_t"], 3),
                              "tu_phieu_id": n.do[d["lo"]]["id"]}]
        p = dx(n, "thabok", "POST", "/api/trips", body)
        n.do[k] = {"id": p["id"], "doc_no": p["doc_no"], "odo_out": body["odo_out"]}
        print("      %s · xe %s · %s · %s" % (p["doc_no"], d["xe"], p.get("driver_name"),
                                           ("xe thuê của " + (p.get("owner_name") or "")) if p.get("company") == "joint" else "xe nhà"))
    return f


def dinh_kem(k, loai):
    """Bãi đính kèm ảnh phiếu quặng của khách (ore_bill) hoặc biên bản giao nhận đã ký (pod)."""
    def f(n):
        ten = "%s-%s.png" % ("phieu-quang" if loai == "ore_bill" else "bien-ban-POD", _ma_ngan(n, k))
        n.dx.goi_tep("thabok", "/api/trips/%s/tep" % n.do[k]["id"], {"kind": loai, "note": "Gieo bộ chuẩn — ảnh %s" % ten},
                     [("tep", ten, "image/png", anh_phieu(len(ten) + (3 if loai == "pod" else 0)))])
        print("      đính kèm %s (%s)" % (ten, loai))
    return f


def gui_kiem(k, muc):
    def f(n):
        p = phieu(n, k)
        da = []
        for m in muc:
            if m in ("fuel", "travel", "repair", "other") and not dong_muc(p, m):
                continue
            if (p["sections"].get(m) or "wait") == "wait":
                dx(n, "totsua" if m == "repair" else "thabok", "POST", "/api/trips/%s/sections/%s/send" % (n.do[k]["id"], m))
                da.append(m)
        print("      gửi kiểm: %s" % (", ".join(da) or "(không mục nào)"))
    return f


def de_nghi(k, loai):
    def f(n):
        vs = dx(n, "thabok", "POST", "/api/trips/%s/vouchers" % n.do[k]["id"], {"kind": loai})
        n.do[k].setdefault("phieu_dn", []).extend(v["doc_no"] for v in vs)
        print("      " + " · ".join("%s%s" % (v["doc_no"], (" %s L" % v["qty_l"]) if loai == "fuel" else "") for v in vs))
    return f


def kiem_i(k):
    def f(n):
        dx(n, "ketoan", "POST", "/api/trips/%s/sections/info/verify" % n.do[k]["id"])
    return f


def kiem_ii(k):
    def f(n):
        tid = n.do[k]["id"]
        dx(n, "ketoan", "PUT", "/api/trips/%s" % tid, {"ore_bill_no": "PQ-%s" % _ma_ngan(n, k), "ore_bill_date": n.ngay})
        dx(n, "ketoan", "POST", "/api/trips/%s/sections/trans/verify" % tid)
        p = phieu(n, k)
        print("      phiếu quặng PQ-%s · giá cước %s %s/%s%s" % (_ma_ngan(n, k), p.get("price"), p.get("price_ccy"), p.get("price_mode"),
              (" · giá thuê %s %s · phí %s %% · ngưỡng %s t" % (p.get("hire_price"), p.get("hire_ccy"), p.get("fee_pct"), p.get("over_limit_t")))
              if p.get("company") == "joint" else ""))
    return f


def _day_muc(n, k, muc, vai, ghi_so=True):
    """Đưa một mục tới đã kiểm (và đã ghi sổ nếu `ghi_so`): đã nhập → kiểm → ghi sổ. Mục trống / chưa gửi thì bỏ qua."""
    tid = n.do[k]["id"]
    st = phieu(n, k)["sections"].get(muc)
    if st == "entered":
        dx(n, vai, "POST", "/api/trips/%s/sections/%s/verify" % (tid, muc))
        st = "verified"
    if st == "verified" and ghi_so:
        dx(n, vai, "POST", "/api/trips/%s/sections/%s/book" % (tid, muc))
        st = phieu(n, k)["sections"].get(muc)
    return st


def kiem_iii(k, ghi_so=True):
    def f(n):
        d, tid, p = DO[k], n.do[k]["id"], phieu(n, k)
        dong = []
        for e in dong_muc(p, "fuel"):
            if e.get("source") == "kho" and d.get("gia_ban_iii"):
                dong.append({"id": e["id"], "section": "fuel", "sale_price": d["gia_ban_iii"]})
            elif e.get("source") != "kho" and e.get("paid_by_epl") is not False and d.get("gia_iii"):
                dong.append({"id": e["id"], "section": "fuel", "unit_price": d["gia_iii"][0], "currency": d["gia_iii"][1]})
        if dong:
            dx(n, "khonl", "PUT", "/api/trips/%s" % tid, {"expenses": dong})
        st = _day_muc(n, k, "fuel", "khonl", ghi_so)
        print("      mục III → %s%s" % (st, ("" if not dong else " · " + ", ".join(
            ("giá bán %s LAK/L" % x["sale_price"]) if "sale_price" in x else ("đơn giá %s %s/L" % (x["unit_price"], x["currency"])) for x in dong))))
    return f


def kiem_iv(k):
    def f(n):
        tid, p = n.do[k]["id"], phieu(n, k)
        dong = [{"id": e["id"], "section": "travel", "unit_price": GIA_IV[e["item_key"]], "currency": "LAK"}
                for e in dong_muc(p, "travel")
                if e.get("paid_by_epl") is not False and e.get("item_key") in GIA_IV]
        if dong:
            dx(n, "ketoancp", "PUT", "/api/trips/%s" % tid, {"expenses": dong})
        st = _day_muc(n, k, "travel", "ketoancp")
        c = dx(n, "ketoancp", "GET", "/api/trips/%s/chi-ke-toan" % tid)
        if c.get("status"):
            can(c["status"] in ("da_gui", "da_chi"), "phiếu chi tạm ứng chưa sang được kế toán: %s" % (c.get("error_message") or c.get("error_code")))
            n.do[k]["ctr"] = c.get("document_no")
            print("      mục IV → %s · phiếu chi tạm ứng bên kế toán %s (%s, nhiều dòng tiền mặt)" % (st, c.get("document_no"), c.get("status")))
        else:
            print("      mục IV → %s · không có tiền mặt tài xế cầm đi — không có phiếu chi tạm ứng" % st)
    return f


def kiem_v(k):
    def f(n):
        d, tid, p = DO[k], n.do[k]["id"], phieu(n, k)
        if d.get("gia_ban_v"):
            dong = [{"id": e["id"], "section": "repair", "sale_price": d["gia_ban_v"]} for e in dong_muc(p, "repair") if e.get("source") == "kho"]
            if dong:
                dx(n, "ketoancp", "PUT", "/api/trips/%s" % tid, {"expenses": dong})
                print("      giá bán phụ tùng cho đối tác %s LAK (%d dòng kho)" % ("{:,}".format(d["gia_ban_v"]), len(dong)))
        st = _day_muc(n, k, "repair", "ketoancp")
        g = dx(n, "ketoan", "GET", "/api/trips/%s/chi-muc-ke-toan" % tid)
        so = so_chung_tu(g)
        print("      mục V → %s%s" % (st, (" · phiếu chi bên kế toán " + ", ".join(so)) if so else " · không có khoản quỹ trả ngay"))
    return f


def bao_can(k):
    """Tài xế báo cân ở mỏ trên app (kèm ảnh phiếu cân) — rồi Bãi gửi kiểm mục II."""
    def f(n):
        d = DO[k]
        n.dx.goi_tep(d["tk"], "/api/trips/%s/bao-can-mo" % n.do[k]["id"],
                     {"tan": str(d["can_mo_app"]), "ghi_chu": "Phiếu cân mỏ số PC-%s" % _ma_ngan(n, k), "luc": gio_may(1),
                      "ma_gui": "gieo-cm-%s" % _ma_ngan(n, k)},
                     [("anh", "phieu-can-mo-%s.png" % _ma_ngan(n, k), "image/png", anh_phieu(11))])
        print("      %s báo cân mỏ %s t (ảnh phiếu cân)" % (d["tk"], d["can_mo_app"]))
    return f


def _thu_doi(n, k, vai, body, ten_viec):
    """Đổi trạng thái vận chuyển bằng đúng vai; bị chặn ĐÚNG LUẬT vì tạm ứng chưa ghi sổ → đợi thủ quỹ (--cho-thu-quy) hoặc Sếp bấm thay."""
    tid = n.do[k]["id"]
    s, g, _ = n.dx.tho("POST", "/api/trips/%s/transport-status" % tid, body, vai)
    ma = ((g or {}).get("detail") or {}).get("ma") if isinstance((g or {}).get("detail"), dict) else None
    if s == 409 and ma == "CHUA_NHAN_TAM_UNG":
        if n.a.cho_thu_quy and _doi_thu_quy(n, k):
            dx(n, vai, "POST", "/api/trips/%s/transport-status" % tid, body)
            print("      %s (%s, sau khi thủ quỹ ghi sổ)" % (ten_viec, vai))
            return
        dx(n, "admin", "POST", "/api/trips/%s/transport-status" % tid, body)
        cau = "%s %s: %s bị chặn đúng luật (phiếu chi tạm ứng %s chưa ghi sổ bên kế toán — bấm tay) → Sếp bấm thay" % (
            n.do[k]["doc_no"], ten_viec, vai, n.do[k].get("ctr") or "")
        n.ghi_chu.append("THAY VAI · " + cau)
        print("      ! THAY VAI — " + cau)
        return
    if s != 200:
        raise Hong(vai, "POST", "/api/trips/%s/transport-status" % tid, s, g)
    print("      %s (%s)" % (ten_viec, vai))


def _doi_thu_quy(n, k):
    het = time.time() + n.a.cho_thu_quy * 60
    while time.time() < het:
        c = dx(n, "ketoancp", "GET", "/api/trips/%s/chi-ke-toan?cap_nhat=1" % n.do[k]["id"])
        if c.get("status") == "da_chi":
            return True
        print("      … chờ thủ quỹ ghi sổ phiếu chi %s bên kế toán (%s)" % (c.get("document_no"), c.get("status")))
        time.sleep(15)
    return False


def xuat_phat(k):
    def f(n):
        d = DO[k]
        _thu_doi(n, k, d.get("tk") or "thabok", {"status": "transit"}, "xuất phát")
    return f


def gps(k):
    """App tài xế gửi bù một lô điểm GPS dọc tuyến (giờ máy lùi dần, cách 90 giây) — như điện thoại mất sóng rồi có sóng lại;
    `gps_song` thì gửi thêm một điểm 'bây giờ' (bản đồ thấy vị trí GPS thật, chưa cũ)."""
    def f(n):
        d = DO[k]
        diem = [(s["lat"], s["lng"]) for s in tuyen_cua(n, k).get("stops") or [] if s.get("lat") is not None]
        if len(diem) < 2:
            diem = [(19.15, 102.25), (18.44, 103.15)]
        so = d["gps"]
        ds = []
        for i in range(so):
            t = (i + 1) / (so + 1.0) * (len(diem) - 1)
            j = min(int(t), len(diem) - 2)
            r = t - j
            lat = diem[j][0] + (diem[j + 1][0] - diem[j][0]) * r
            lng = diem[j][1] + (diem[j + 1][1] - diem[j][1]) * r
            huong = (math.degrees(math.atan2(diem[j + 1][1] - diem[j][1], diem[j + 1][0] - diem[j][0])) + 360) % 360
            ds.append({"lat": round(lat, 6), "lng": round(lng, 6), "ts": gio_may(1.5 * (so - i) + (0 if d.get("gps_song") else 2)),
                       "accuracy_m": 8 + i % 7, "speed_kmh": 38 + (i * 7) % 20, "heading": round(huong)})
        g = dx(n, d["tk"], "POST", "/api/trips/%s/vi-tri/lo" % n.do[k]["id"], {"diem": ds})
        cau = "      %s gửi bù %d điểm GPS → ghi %s%s" % (d["tk"], len(ds), g.get("ghi"), (" · bỏ %s" % g["bo"]) if g.get("bo") else "")
        if d.get("gps_song"):
            cuoi = ds[-1]
            dx(n, d["tk"], "POST", "/api/trips/%s/vi-tri" % n.do[k]["id"],
               {"lat": round(cuoi["lat"] - 0.004, 6), "lng": round(cuoi["lng"] + 0.006, 6), "ts": gio_may(0), "accuracy_m": 6,
                "speed_kmh": 46, "heading": cuoi["heading"]})
            cau += " · + 1 điểm sống (bây giờ)"
        print(cau)
    return f


def khai_do(k):
    def f(n):
        ma, lit, gia, tt, ghi_no = DO[k]["khai_do"]
        tk = DO[k]["tk"]
        p = dx(n, tk, "POST", "/api/trips/%s/bao-nhien-lieu" % n.do[k]["id"],
               {"qty_l": lit, "place_id": n.dm["diem"][ma]["id"], "currency": tt, "note": "Đổ dầu ở %s (gieo bộ chuẩn)" % ma,
                "luc": gio_may(5), "ma_gui": "gieo-kd-%s" % _ma_ngan(n, k)})
        e = [x for x in p.get("events") or [] if x.get("kind") == "refuel" and x.get("status") == "reported"]
        can(e, "không thấy khai đổ vừa gửi")
        n.do[k]["khai_do"] = e[-1]["id"]
        print("      %s khai đổ %s L ở %s (không ghi giá)" % (tk, lit, ma))
    return f


def duyet_do(k):
    def f(n):
        ma, lit, gia, tt, ghi_no = DO[k]["khai_do"]
        dx(n, "khonl", "POST", "/api/trips/%s/events/%s/duyet" % (n.do[k]["id"], n.do[k]["khai_do"]),
           {"qty_l": lit, "unit_price": gia, "currency": tt, "ghi_no": "1" if ghi_no else "0"})
        print("      duyệt: %s · %s %s/L → mục III mở lại" % (
            "Có — trạm ghi nợ EPL (nợ nhà cung cấp, Có 4021)" if ghi_no else "Không — tài xế trả tiền túi (chi bù lúc tất toán)",
            "{:,}".format(gia), tt))
    return f


def bao_hong(k):
    def f(n):
        loai, ghi, tien = DO[k]["bao_hong"]
        tk = DO[k]["tk"]
        p = dx(n, tk, "POST", "/api/trips/%s/bao-hong" % n.do[k]["id"],
               {"incident_type": loai, "note": ghi, "reported_cost": tien, "currency": "LAK", "paid_by_driver": True, "can_run": True,
                "luc": gio_may(3), "ma_gui": "gieo-bh-%s" % _ma_ngan(n, k)})
        e = [x for x in p.get("events") or [] if x.get("kind") in ("incident", "repair") and x.get("status") == "reported"]
        can(e, "không thấy báo hỏng vừa gửi")
        n.do[k]["bao_hong"] = e[-1]["id"]
        print("      %s báo hỏng «%s» · %s LAK · Tôi đã tự trả" % (tk, ghi, "{:,}".format(tien)))
    return f


def duyet_hong(k):
    def f(n):
        loai, ghi, tien = DO[k]["bao_hong"]
        dx(n, "totsua", "POST", "/api/trips/%s/events/%s/duyet" % (n.do[k]["id"], n.do[k]["bao_hong"]),
           {"source": "mua", "item_name": "Vá lốp garage dọc đường", "qty": 1, "unit_price": tien, "currency": "LAK"})
        print("      Tổ sửa duyệt: Mua ngoài / garage (chi tiền) %s LAK → dòng mục V" % "{:,}".format(tien))
    return f


def sua_kho(k):
    def f(n):
        chu, sl, loai, ghi = DO[k]["sua_kho"]
        p = _pt(n, chu)
        tuyen = tuyen_cua(n, k)
        seq = max([s["seq"] for s in tuyen.get("stops") or []] or [1])
        dx(n, "totsua", "POST", "/api/trips/%s/events" % n.do[k]["id"],
           {"kind": "repair", "incident_type": loai, "note": ghi, "stop_seq": max(1, seq - 1),
            "repair": {"source": "kho", "part_id": p["id"], "qty": sl}})
        q = phieu(n, k)
        x = [e for e in dong_muc(q, "repair") if e.get("source") == "kho"]
        so = (x[-1].get("stock_move_id") or "") if x else ""
        print("      Tổ sửa lấy %s × %s từ KHO-PT → phiếu xuất kho bên anh Tune %s (%s)" % (
            sl, p["name"], so.replace("qlsx:", "") or "?", "xuất bán đối tác" if q.get("company") == "joint" else "xuất nội bộ"))
    return f


def su_co_cho(k):
    def f(n):
        loai, ghi = DO[k]["su_co_cho"]
        dx(n, DO[k]["tk"], "POST", "/api/trips/%s/bao-hong" % n.do[k]["id"],
           {"incident_type": loai, "note": ghi, "can_run": True, "luc": gio_may(2), "ma_gui": "gieo-sc-%s" % _ma_ngan(n, k)})
        print("      %s báo sự cố «%s» — ĐỂ CHỜ Bãi duyệt" % (DO[k]["tk"], ghi))
    return f


def ky_pod(k):
    def f(n):
        tk = DO[k]["tk"]
        cuoi = (tuyen_cua(n, k).get("stops") or [{}])[-1]
        n.dx.goi_tep(tk, "/api/trips/%s/giao-nhan" % n.do[k]["id"],
                     {"nguoi_nhan": "ທ້າວ ສົມຊາຍ (cảng)", "sdt": "020 5512 3344", "tinh_trang": "du",
                      "ghi_chu": "Nhận đủ hàng, cân cảng %s t" % DO[k]["can_ve"], "luc": gio_may(1),
                      "lat": str(cuoi.get("lat") or ""), "lng": str(cuoi.get("lng") or ""), "ma_gui": "gieo-pod-%s" % _ma_ngan(n, k),
                      "pod_no": "POD-%s" % _ma_ngan(n, k)},
                     [("chu_ky", "chu-ky.png", "image/png", chu_ky()),
                      ("anh", "bien-ban-can-cang-%s.png" % _ma_ngan(n, k), "image/png", anh_phieu(23))])
        print("      %s: người nhận ký trên máy (chữ ký + ảnh biên bản) · số POD POD-%s" % (tk, _ma_ngan(n, k)))
    return f


def _km_ve(n, k):
    """Km về = km lúc đi + km cả chuyến của tuyến (đi + về) + 2 % — khớp ước tính của màn khoá phiếu (không cảnh báo KM_LECH)."""
    t = tuyen_cua(n, k)
    ca = t.get("round_km") or 2 * (t.get("total_km") or 100)
    return round(n.do[k]["odo_out"] + ca * 1.02)


def bao_ve(k):
    def f(n):
        d = DO[k]
        km = _km_ve(n, k)
        n.do[k]["odo_back"] = km
        dx(n, d["tk"], "POST", "/api/trips/%s/bao-ve" % n.do[k]["id"], {"back_date": n.ngay, "odo_back": km})
        print("      %s báo đã về · ngày %s · km %s" % (d["tk"], n.ngay, km))
    return f


def xe_toi(k):
    def f(n):
        d = DO[k]
        km = n.do[k].get("odo_back") or _km_ve(n, k)
        body = {"status": "arrived", "back_date": n.ngay, "odo_back": km, "weight_dest": d["can_ve"]}
        if d["kind"] == "gom":
            body["weight_origin"] = d.get("can_mo_app") or d.get("can_mo")
        else:
            body.update({"pod_no": "POD-%s" % _ma_ngan(n, k), "pod_receiver": "ທ້າວ ສົມຊາຍ (cảng)"})
        _thu_doi(n, k, "thabok", body, "xe tới — %s" % ("cân bãi %s t, hàng vào kho bãi" % d["can_ve"] if d["kind"] == "gom"
                                                          else "cân cảng %s t, chốt hao hụt" % d["can_ve"]))
        to = dx(n, "thabok", "GET", "/api/trips/%s/to-kho-hang" % n.do[k]["id"])
        so = so_chung_tu(to)
        print("      tờ kho hàng: %s" % (", ".join(so) or "—"))
    return f


def khoa(k):
    def f(n):
        p = dx(n, "ketoan", "POST", "/api/trips/%s/khoa" % n.do[k]["id"], {"xac_nhan": True})
        cb = [c.get("ma") for c in p.get("canh_bao") or []]
        print("      đã khoá%s" % ((" — cảnh báo đã xác nhận: " + ", ".join(cb)) if cb else ""))
    return f


def tao_so(k):
    def f(n):
        g = dx(n, "ketoan", "POST", "/api/trips/%s/tao-so" % n.do[k]["id"])
        so = (g.get("trang_thai") or {}).get("order_code")
        nl = g.get("nhien_lieu") or {}
        nl = (nl.get("trang_thai") or {}).get("order_code") or nl.get("order_code")
        can(so, "không có số SO cước")
        dt_ = ["%s %s %s" % (b.get("nguon"), b.get("status"), b.get("so_ben_ke_toan") or "") for b in g.get("but_toan_doanh_thu") or []]
        print("      SO cước %s%s%s" % (so, (" · SO nhiên liệu %s" % nl) if nl else "", (" · doanh thu: " + "; ".join(dt_)) if dt_ else ""))
    return f


def but_toan(k):
    def f(n):
        tid = n.do[k]["id"]
        ds = dx(n, "ketoan", "GET", "/api/but-toan-cho?trip_id=%s" % tid)["ds"]
        if n.dm.get("gui_bt") and any(b["status"] == "cho_gui" or b.get("can_dao") for b in ds):
            dx(n, "ketoan", "POST", "/api/but-toan-cho/gui-het")
            ds = dx(n, "ketoan", "GET", "/api/but-toan-cho?trip_id=%s" % tid)["ds"]
        if n.dm.get("gui_bt"):
            hong = [b for b in ds if b["status"] == "cho_gui"]
            can(not hong, "bút toán chưa sang kế toán: %s" % "; ".join("%s: %s" % (b["nguon"], b.get("loi_gui") or b.get("error_code")) for b in hong))
        print("      " + (" · ".join("%s %s %s" % (b["nguon"], b["status"], b.get("so_ben_ke_toan") or "") for b in ds if b["status"] != "huy")
                          or "không có bút toán"))
    return f


def dieu_chinh(k_lo, tan, ly_do, duyet):
    def f(n):
        don = dx(n, "thabok", "POST", "/api/kho-hang/dieu-chinh", {"lo_id": n.do[k_lo]["id"], "tan": tan, "ly_do": ly_do})
        did = don.get("id")
        if duyet:
            don = dx(n, "ketoan", "POST", "/api/kho-hang/dieu-chinh/%s/duyet" % did, {"dong_y": True, "ghi_chu": "Đã kiểm lại ở bãi"})
        n.do[k_lo].setdefault("dieu_chinh", []).append(don.get("so_phieu") or ("chờ duyệt" if not duyet else "?"))
        print("      lô %s %+.1f t «%s» → %s" % (n.do[k_lo]["doc_no"], tan, ly_do,
                                               ("đã duyệt · " + (don.get("so_phieu") or "")) if duyet else "CHỜ DUYỆT (KT Thu/Chi)"))
    return f


# ---------------------------------------------------------------- bộ B: kiểm điều kiện, không lập DO
def kiem_ca_b(n):
    xe = {v["truck_no"]: v for v in dx(n, "admin", "GET", "/api/vehicles")}
    tx = {t.get("driver_code"): t for t in dx(n, "admin", "GET", "/api/drivers")}
    pt = {chu: (next((p for p in dx(n, "admin", "GET", "/api/parts") if chu in (p.get("name") or "")), {}).get("qty") or 0)
          for chu in (PT_LOP, PT_BAU_HOI)}
    nl = {x.get("code"): (x.get("ton_lit") or 0) for x in (dx(n, "admin", "GET", "/api/kho-xem").get("nhien_lieu") or [])}
    ton = dict(pt, **{"KHO-TB": nl.get("KHO-TB", 0)})
    for c in CA_B:
        thieu = []
        if c.get("xe"):
            v = xe.get(c["xe"]) or {}
            if v.get("status") not in (None, "available"):
                thieu.append("xe %s đang %s" % (c["xe"], v.get("status")))
        if c.get("tai_xe"):
            t = tx.get(c["tai_xe"]) or {}
            if t.get("status") not in (None, "available"):
                thieu.append("tài xế %s đang %s" % (c["tai_xe"], t.get("status")))
        for k, v in (c.get("ton") or {}).items():
            if (ton.get(k) or 0) < v:
                thieu.append("tồn %s %s < %s" % (k, ton.get(k), v))
        if c.get("do_nguon") and c["do_nguon"] not in n.do:
            thieu.append("chưa có DO %s" % c["do_nguon"])
        if c.get("tai_xe_tt"):
            tt = dx(n, "ketoancp", "GET", "/api/tat-toan/%s?ky=%s" % (tx[c["tai_xe_tt"]]["id"], n.ky))
            so_phieu = len(tt.get("phieu") or tt.get("rows") or [])
            if so_phieu < 2:
                thieu.append("tài xế %s mới có %d phiếu trong kỳ %s" % (c["tai_xe_tt"], so_phieu, n.ky))
        n.ca_b.append((c, thieu))
        print("      %s %s — %s" % (c["ma"], c["ten"], "SẴN SÀNG" if not thieu else "THIẾU: " + "; ".join(thieu)))


# ---------------------------------------------------------------- kế hoạch
def ke_hoach():
    """[(mã bước, vai, việc, hàm)] — thứ tự chạy. «a→admin» = vai a bấm trước; bị chặn ĐÚNG LUẬT tạm ứng thì Sếp bấm thay."""
    K = [("0.1", "—", "kiểm 8011 đang nối DB bản sao (…_d<số>)", b_kiem_may),
         ("0.2", "—", "đăng nhập các vai ở trang điều xe (mật khẩu 1234)", b_dang_nhap),
         ("0.3", "admin", "d7 sạch (chưa có phiếu) · cờ gửi bút toán", b_may_sach),
         ("0.4", "admin", "đọc danh mục: xe / tài xế rảnh, khách, tuyến, điểm dầu, phụ tùng, tài khoản tài xế có app", b_danh_muc),
         ("0.5", "admin", "đọc tồn kho EPL bên anh Tune qua 8011 (lốp, bầu hơi, KHO-TB) — KHÔNG nhập kho", b_ton_kho),
         ("0.6", "ketoan", "hợp đồng HDVC-2026-001 · HDTX-2026-001: chưa có bản scan thì đính kèm PDF", b_hop_dong)]

    def chuyen(k, viec):
        return [("%s.%d" % (k, i), v, t, f) for i, (v, t, f) in enumerate(viec, 1)]

    K += chuyen("A1", [
        ("thabok", "lập DO gom ກາສີ→ທ່າບົກ, xe 341 / ທ້າວ ທັດສະດາພອນ (chưa cân mỏ) · mục IV: ăn, điện thoại, cầu đường, đỗ xe (Chi ngay "
                   "khi xe đi) + tiền nước, tiền chuyến (cùng lương)", lap("A1")),
        ("thabok", "đính kèm ảnh phiếu quặng của khách", dinh_kem("A1", "ore_bill")),
        ("thabok", "gửi kiểm mục I, IV (mục II gửi sau khi tài xế báo cân)", gui_kiem("A1", ("info", "travel"))),
        ("thabok", "in phiếu đề nghị tạm ứng", de_nghi("A1", "advance")),
        ("ketoan", "kiểm mục I", kiem_i("A1")),
        ("ketoancp", "đơn giá mục IV · kiểm · ghi sổ → phiếu chi «Chi trước» NHIỀU DÒNG sang hệ anh Tune (GHI THẬT)", kiem_iv("A1")),
        ("tx01", "app: báo cân ở mỏ 40 t + ảnh phiếu cân", bao_can("A1")),
        ("thabok", "gửi kiểm mục II", gui_kiem("A1", ("trans",))),
        ("ketoan", "nhập số / ngày phiếu quặng · kiểm mục II (giá cước theo bảng giá)", kiem_ii("A1")),
        ("tx01→admin", "app: Xuất phát (tạm ứng chưa ghi sổ → chặn đúng luật → Sếp bấm thay)", xuat_phat("A1")),
        ("tx01", "app: gửi bù 10 điểm GPS dọc tuyến", gps("A1")),
        ("tx01", "app: khai đổ dầu 40 L ở trạm VN-01", khai_do("A1")),
        ("khonl", "duyệt khai đổ: Có — trạm ghi nợ EPL, 27.000 VND/L", duyet_do("A1")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_iii("A1")),
        ("tx01", "app: Báo đã về (ngày, km)", bao_ve("A1")),
        ("thabok→admin", "Xe đã tới · cân bãi 39,6 t → phiếu nhập kho hàng PNK_HH", xe_toi("A1")),
        ("ketoan", "Khoá phiếu → bút toán nợ NCC trạm VN-01 (625/4021, VND)", khoa("A1")),
        ("ketoan", "Tạo SO bên kế toán → SO cước + bút toán doanh thu 1211/708", tao_so("A1")),
        ("ketoan", "bút toán của phiếu đã sang kế toán (còn chờ thì Gửi hết)", but_toan("A1"))])
    K += chuyen("A2", [
        ("thabok", "lập DO giao ທ່າບົກ→ທ່າເຮືອກະລໍ, xe 342 / ທ້າວ ບຸນມີ: lấy trọn lô A1 · mục III trạm VN-01 200 L ghi nợ · mục IV: "
                   "sang VN (tiền mặt) + nước, chuyến (cùng lương) · phí cao tốc máy tự thêm", lap("A2")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("A2", ("info", "trans", "fuel", "travel"))),
        ("thabok", "in phiếu đề nghị tạm ứng", de_nghi("A2", "advance")),
        ("ketoan", "kiểm mục I", kiem_i("A2")),
        ("ketoan", "số phiếu quặng · kiểm mục II", kiem_ii("A2")),
        ("khonl", "đơn giá dầu trạm 27.000 VND/L · kiểm + ghi sổ mục III", kiem_iii("A2")),
        ("ketoancp", "đơn giá mục IV · kiểm · ghi sổ → phiếu chi tạm ứng (sang VN + phí cao tốc)", kiem_iv("A2")),
        ("tx02→admin", "app: Xuất phát (chặn đúng luật → Sếp bấm thay)", xuat_phat("A2")),
        ("tx02", "app: gửi bù 12 điểm GPS", gps("A2")),
        ("totsua", "Báo sự cố / sửa xe: thay 1 lốp LẤY KHO → phiếu 48 xuất nội bộ bên anh Tune (GHI THẬT)", sua_kho("A2")),
        ("ketoancp", "kiểm + ghi sổ mục V", kiem_v("A2")),
        ("tx02", "app: Giao hàng hoàn tất · ký nhận (chữ ký + ảnh biên bản)", ky_pod("A2")),
        ("thabok", "đính kèm scan biên bản giao nhận (POD)", dinh_kem("A2", "pod")),
        ("tx02", "app: Báo đã về", bao_ve("A2")),
        ("thabok→admin", "Xe đã tới · cân cảng 39,4 t · số POD → PXK_HH", xe_toi("A2")),
        ("ketoan", "Khoá phiếu → nợ NCC 625/4021 + xuất nội bộ lốp 614/1371", khoa("A2")),
        ("ketoan", "Tạo SO bên kế toán → SO cước + doanh thu", tao_so("A2")),
        ("ketoan", "bút toán đã sang kế toán", but_toan("A2"))])
    K += chuyen("A3", [
        ("thabok", "lập DO gom ຊຽງຂວາງ→ທ່າບົກ, xe 341 / ທ້າວ ທັດສະດາພອນ (chuyến 2): cân mỏ 41 t · mục IV chỉ tiền nước + tiền chuyến "
                   "(cùng lương)", lap("A3")),
        ("thabok", "đính kèm ảnh phiếu quặng", dinh_kem("A3", "ore_bill")),
        ("thabok", "gửi kiểm mục I, II, IV", gui_kiem("A3", ("info", "trans", "travel"))),
        ("ketoan", "kiểm mục I", kiem_i("A3")),
        ("ketoan", "số phiếu quặng · kiểm mục II", kiem_ii("A3")),
        ("ketoancp", "đơn giá · kiểm · ghi sổ mục IV (chỉ cùng lương → tự qua bước Chi, không phiếu chi)", kiem_iv("A3")),
        ("tx01", "app: Xuất phát (không tạm ứng → không bị chặn)", xuat_phat("A3")),
        ("tx01", "app: gửi bù 8 điểm GPS", gps("A3")),
        ("tx01", "app: khai đổ 50 L ở trạm LA-02", khai_do("A3")),
        ("khonl", "duyệt khai đổ: Không — tài xế trả tiền túi, 21.500 LAK/L", duyet_do("A3")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_iii("A3")),
        ("tx01", "app: báo hỏng (vá lốp 150.000 LAK, Tôi đã tự trả)", bao_hong("A3")),
        ("totsua", "duyệt báo hỏng: Mua ngoài / garage 150.000 LAK → mục V", duyet_hong("A3")),
        ("ketoancp", "kiểm + ghi sổ mục V → phiếu chi «Chi khác» (quỹ trả ngay) sang hệ anh Tune (GHI THẬT)", kiem_v("A3")),
        ("tx01", "app: Báo đã về", bao_ve("A3")),
        ("thabok", "Xe đã tới · cân bãi 40,6 t → PNK_HH", xe_toi("A3")),
        ("ketoan", "Khoá phiếu", khoa("A3")),
        ("ketoan", "Tạo SO bên kế toán → SO cước + doanh thu", tao_so("A3")),
        ("ketoan", "bút toán đã sang kế toán", but_toan("A3"))])
    K += chuyen("A4", [
        ("thabok", "lập DO gom, xe thuê ຮ່ວມ-07 / ທ້າວ ສົມພອນ: dầu trạm LA-02 150 L CHỦ XE TỰ TRẢ · tiền ăn chủ xe tự trả", lap("A4")),
        ("thabok", "đính kèm ảnh phiếu quặng", dinh_kem("A4", "ore_bill")),
        ("thabok", "gửi kiểm mục I, III, IV", gui_kiem("A4", ("info", "fuel", "travel"))),
        ("ketoan", "kiểm mục I", kiem_i("A4")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_iii("A4")),
        ("ketoancp", "kiểm + ghi sổ mục IV (không tạm ứng)", kiem_iv("A4")),
        ("tx03", "app: báo cân ở mỏ 43 t + ảnh phiếu cân", bao_can("A4")),
        ("thabok", "gửi kiểm mục II", gui_kiem("A4", ("trans",))),
        ("ketoan", "số phiếu quặng · kiểm mục II (giá cước + giá thuê, phí 2 %, ngưỡng 40 t)", kiem_ii("A4")),
        ("tx03", "app: Xuất phát", xuat_phat("A4")),
        ("tx03", "app: gửi bù 8 điểm GPS", gps("A4")),
        ("totsua", "Báo sự cố / sửa xe: thay bầu hơi LẤY KHO → phiếu 48 XUẤT BÁN ĐỐI TÁC bên anh Tune (GHI THẬT)", sua_kho("A4")),
        ("ketoancp", "giá bán bầu hơi 700.000 LAK · kiểm + ghi sổ mục V", kiem_v("A4")),
        ("tx03", "app: Báo đã về", bao_ve("A4")),
        ("thabok", "Xe đã tới · cân bãi 42,6 t (vượt ngưỡng 40 t) → PNK_HH", xe_toi("A4")),
        ("ketoan", "Khoá phiếu → thuê xe 621/4022 · phí 4022/715 · quá tải 4022/758 · giá vốn 607/1371", khoa("A4")),
        ("ketoan", "Tạo SO bên kế toán → SO cước + SO NHIÊN LIỆU (dòng phụ tùng) + doanh thu 708 / 707", tao_so("A4")),
        ("ketoan", "bút toán đã sang kế toán — KHÔNG lập đề nghị trả (chủ dự án bấm Tất toán đối tác)", but_toan("A4"))])
    K += chuyen("A5", [
        ("thabok", "lập DO gom, xe thuê ຮ່ວມ-08 / ທ້າວ ຄຳສີ: cân mỏ 40 t · dầu LA-02 200 L + tiền ăn CHỦ XE TỰ TRẢ", lap("A5")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("A5", ("info", "trans", "fuel", "travel"))),
        ("ketoan", "kiểm mục I", kiem_i("A5")),
        ("ketoan", "số phiếu quặng · kiểm mục II", kiem_ii("A5")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_iii("A5")),
        ("ketoancp", "kiểm + ghi sổ mục IV", kiem_iv("A5")),
        ("thabok", "Xe đã lăn bánh (tài xế không có app)", xuat_phat("A5")),
        ("thabok", "Xe đã tới · cân bãi 39,8 t → PNK_HH", xe_toi("A5")),
        ("ketoan", "Khoá phiếu → thuê xe 621/4022 + phí quản lý 4022/715", khoa("A5")),
        ("ketoan", "Tạo SO bên kế toán", tao_so("A5")),
        ("ketoan", "bút toán đã sang kế toán", but_toan("A5"))])
    K += chuyen("A6", [
        ("thabok", "lập DO gom, xe thuê ຮ່ວມ-09 / ທ້າວ ພູວົງ: cân mỏ 42 t · dầu KHO-TB 60 L (xuất bán cho đối tác)", lap("A6")),
        ("thabok", "gửi kiểm mục I, II, III", gui_kiem("A6", ("info", "trans", "fuel"))),
        ("thabok", "in phiếu đề nghị xuất kho nhiên liệu (PLNL, nhãn Xuất bán)", de_nghi("A6", "fuel")),
        ("ketoan", "kiểm mục I", kiem_i("A6")),
        ("ketoan", "số phiếu quặng · kiểm mục II", kiem_ii("A6")),
        ("khonl", "giá bán cho chủ xe 33.000 LAK/L · kiểm mục III (CHƯA ghi sổ — chờ kho cấp)", kiem_iii("A6", ghi_so=False))])
    K += chuyen("A7", [
        ("thabok", "lập DO gom, xe thuê ຮ່ວມ-07 / ທ້າວ ສົມພອນ (chuyến 2): dầu LA-02 120 L chủ xe tự trả", lap("A7")),
        ("thabok", "gửi kiểm mục I, III", gui_kiem("A7", ("info", "fuel"))),
        ("ketoan", "kiểm mục I", kiem_i("A7")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_iii("A7")),
        ("tx03", "app: báo cân ở mỏ 41,5 t + ảnh", bao_can("A7")),
        ("thabok", "gửi kiểm mục II", gui_kiem("A7", ("trans",))),
        ("ketoan", "số phiếu quặng · kiểm mục II", kiem_ii("A7")),
        ("tx03", "app: Xuất phát → ĐANG TRÊN ĐƯỜNG", xuat_phat("A7")),
        ("tx03", "app: gửi bù 10 điểm GPS + 1 điểm sống", gps("A7")),
        ("tx03", "app: báo sự cố «bị giữ xe» — để CHỜ DUYỆT", su_co_cho("A7"))])
    K += chuyen("A8", [
        ("thabok", "lập DO gom, xe 344 / ທ້າວ ບຸນເຫຼືອ: cân mỏ 40 t · dầu KHO-TB 80 L · ăn, điện thoại (tiền mặt) + nước, chuyến", lap("A8")),
        ("thabok", "in phiếu đề nghị xuất kho nhiên liệu", de_nghi("A8", "fuel")),
        ("thabok", "in phiếu đề nghị tạm ứng", de_nghi("A8", "advance")),
        ("thabok", "gửi kiểm mục I, II, III, IV → CHỜ KIỂM (dừng ở đây)", gui_kiem("A8", ("info", "trans", "fuel", "travel")))])
    K += [("A9.1", "thabok→ketoan", "lô A3: phiếu điều chỉnh −0,3 t «Hao hụt ở bãi do mưa» → KT Thu/Chi duyệt → DC_HH",
           dieu_chinh("A3", -0.3, "Hao hụt ở bãi do mưa", True)),
          ("A9.2", "thabok", "lô A5: phiếu điều chỉnh +0,2 t «Cân lại lô ở bãi» — để CHỜ DUYỆT", dieu_chinh("A5", 0.2, "Cân lại lô ở bãi", False)),
          ("B", "admin", "bộ B (CA-1 … CA-6): kiểm điều kiện — xe / tài xế rảnh, tồn kho, DO nguồn; KHÔNG lập DO", kiem_ca_b)]
    return K


# ---------------------------------------------------------------- bảng cuối
SO_RE = re.compile(r"(?:1368-[A-Z]{2,5}-\d{6}-\d{5}|TK-\d{8}-\d{6}|GL\d{8,}|P[NX]K_HH/\d{4}/\d{4}|DC_HH/\d{4}/\d{4}|PTU-[A-Z]\d-\d{4}-\d{2}/EPL"
                   r"|PLNL-[A-Z]\d-\d{4}-\d{2}/EPL-\d+|PDT/\d{4}/\d+|PCSC-[A-Z]+-[A-Z]\d-\d{4}-\d{2}/EPL-\d+|TCX-[\w-]+|4-TKN-[\w-]+)")


def so_chung_tu(*goc):
    """Mọi số chứng từ (bên điều xe và bên anh Tune) có trong các gói JSON — theo thứ tự gặp, không trùng."""
    ra = []
    for g in goc:
        for s in SO_RE.findall(json.dumps(g, ensure_ascii=False)):
            if s not in ra:
                ra.append(s)
    return ra


def bang_cuoi(n):
    if not n.do:
        return
    print("\n" + "=" * 140)
    print("BẢNG BỘ A — máy %s · kỳ %s" % (n.a.dx, n.ky))
    print("%-3s %-15s %-9s %-34s %s" % ("Ca", "Số phiếu", "Loại", "Trạng thái · mục I II III IV V VI", "Chứng từ (điều xe · anh Tune)"))
    for k, x in n.do.items():
        try:
            p = phieu(n, k)
            goi = [p]
            for duong in ("/api/trips/%s/chi-ke-toan", "/api/trips/%s/chi-muc-ke-toan", "/api/trips/%s/vouchers", "/api/trips/%s/to-kho-hang"):
                s, g, _ = n.dx.tho("GET", duong % x["id"], vai="ketoan")
                if s == 200:
                    goi.append(g)
            s, g, _ = n.dx.tho("GET", "/api/trips/%s/tao-so" % x["id"], vai="ketoan")
            if s == 200:
                goi.append(g)
            s, g, _ = n.dx.tho("GET", "/api/but-toan-cho?trip_id=%s" % x["id"], vai="ketoan")
            if s == 200:
                goi.append([b for b in g.get("ds") or [] if b.get("status") != "huy"])
            goi.append(x.get("dieu_chinh") or [])
            tt = "%s%s · %s" % (p["transport_status"], " · KHOÁ" if p.get("locked") else "",
                                "".join({"wait": "○", "entered": "◐", "verified": "◑", "booked": "●", "paid": "✓"}.get(p["sections"].get(m), "?")
                                        for m in ("info", "trans", "fuel", "travel", "repair", "other")))
            loai = ("thuê " if p.get("company") == "joint" else "nhà ") + p["kind"]
            print("%-3s %-15s %-9s %-34s %s" % (k, p["doc_no"], loai, tt, " · ".join(so_chung_tu(*goi)) or "—"))
            for c in DO[k].get("con_cho") or []:
                print("      chờ: %s" % c)
        except Hong as e:
            print("%-3s %-15s (không đọc được: %s)" % (k, x.get("doc_no"), e))
    print("      mục: ○ chờ · ◐ đã gửi kiểm · ◑ đã kiểm · ● đã ghi sổ · ✓ đã chi / tự qua bước chi")
    try:
        b = dx(n, "ketoan", "GET", "/api/tat-toan-doi-tac?ky=%s&owner_id=%s&cap_nhat=1" % (n.ky, CHU_XE))
        for d in b.get("doi_tac") or []:
            print("\nTẤT TOÁN ĐỐI TÁC (chưa lập đề nghị — chủ dự án bấm): %s · tiền thuê %s · phí %s · quá tải %s · nhiên liệu còn nợ %s · "
                  "CÒN TRẢ %s %s" % (d.get("ten"), d.get("tien_thue"), d.get("phi"), d.get("qua_tai"), d.get("nhien_lieu_con_no"),
                                    d.get("con_tra"), d.get("tien_te")))
        tx = n.dm["tx"]["DRV-01"]
        t = dx(n, "ketoancp", "GET", "/api/tat-toan/%s?ky=%s" % (tx["id"], n.ky))
        print("TẤT TOÁN TÀI XẾ ທ້າວ ທັດສະດາພອນ (để nguyên — CA-4): " + json.dumps(
            {k: t.get(k) for k in ("so_phieu", "tong_ung_lak", "tong_chi_lak", "chenh_lech_lak", "da_ung_lak", "da_chi_that_lak",
                                   "chenh_lak") if k in t}, ensure_ascii=False)
              + ((" · còn chặn: " + "; ".join(z.get("loi") or "" for z in t.get("chan_chot") or [])) if t.get("chan_chot") else ""))
        ttx = dx(n, "ketoan", "GET", "/api/bao-cao/tien-tai-xe?thang=%s" % n.ky).get("tong") or {}
        print("TIỀN CHUYẾN & NƯỚC (trả cùng lương): tổng %s · đã trả %s · chờ trả %s LAK" % (
            ttx.get("tong_lak"), ttx.get("da_tra_lak"), ttx.get("cho_tra_lak")))
    except Hong as e:
        print("  (không đọc được tất toán / báo cáo: %s)" % e)
    if n.ca_b:
        print("\n" + "=" * 140)
        print("BỘ B — CHỪA CHO CHỦ DỰ ÁN BẤM TỪ ĐẦU")
        for c, thieu in n.ca_b:
            print("%-5s %s — %s" % (c["ma"], c["ten"], "SẴN SÀNG" if not thieu else "THIẾU: " + "; ".join(thieu)))
            print("      bấm từ: %s" % c["tu_dau"])
            print("      vai   : %s" % c["vai"])
            print("      hướng dẫn: %s" % c["muc"])
    for c in n.ghi_chu:
        print("  ! " + c)


def in_ke_hoach(K, a):
    print("KẾ HOẠCH GIEO — %d bước (không gọi máy nào). Máy: trang điều xe %s · ngày %s · kỳ %s" % (len(K), a.dx, a.ngay, a.ngay[:7]))
    khoi = None
    for ma, vai, viec, _ in K:
        k = ma.split(".")[0]
        if k != khoi:
            khoi = k
            ten = {"0": "CHUẨN BỊ (máy, vai, danh mục, tồn kho EPL bên anh Tune, hợp đồng)",
                   "A9": "Kho hàng quặng — phiếu điều chỉnh", "B": "BỘ B — chỉ kiểm điều kiện"}.get(k) or DO[k]["ten"]
            print("\n%s  %s" % (k, ten))
        ten_vai = " / ".join(TEN_VAI.get(v, v) for v in re.split(r"[·→]", vai))
        print("  %-6s %-14s %-36s %s" % (ma, vai, "(" + ten_vai + ")", viec))
    print("\n«a→admin»: vai a bấm trước; bị chặn ĐÚNG LUẬT vì phiếu chi tạm ứng chưa ghi sổ bên anh Tune (bước bấm tay) thì Sếp bấm thay "
          "và in «THAY VAI» — hoặc chạy với --cho-thu-quy PHUT để đợi người thử ghi sổ.")
    print("\nCA DỪNG Ở WEB / VIỆC CÒN CHỜ (in lại ở bảng cuối kèm số chứng từ thật):")
    for k, d in DO.items():
        for c in d.get("con_cho") or []:
            print("  %-3s %s" % (k, c))
    print("\nBỘ B — CHỪA CHO CHỦ DỰ ÁN BẤM TỪ ĐẦU (công cụ chỉ kiểm điều kiện, không lập DO):")
    for c in CA_B:
        print("  %-5s %s" % (c["ma"], c["ten"]))
        print("        bấm từ: %s" % c["tu_dau"])
        print("        vai   : %s" % c["vai"])
        print("        hướng dẫn: %s" % c["muc"])


def main():
    ap = argparse.ArgumentParser(description="Gieo bộ dữ liệu chuẩn cho máy thử 8011 (đi HTTP, đúng vai).")
    ap.add_argument("--chi-in", action="store_true", help="in kế hoạch, không gọi máy nào")
    ap.add_argument("--dx", default=os.getenv("EPL_DX", "http://127.0.0.1:8011"))
    ap.add_argument("--ngay", default=dt.date.today().isoformat())
    ap.add_argument("--cho-thu-quy", type=float, default=0, metavar="PHUT",
                    help="đợi tối đa PHUT phút ở bước xuất phát / xe tới cho thủ quỹ ghi sổ phiếu chi tạm ứng bên Web anh Tune")
    ap.add_argument("--khong-can-sach", action="store_true", help="cho chạy khi d7 còn phiếu / xe chưa rảnh")
    a = ap.parse_args()
    dt.date.fromisoformat(a.ngay)
    K = ke_hoach()
    if a.chi_in:
        in_ke_hoach(K, a)
        return
    n = Ngu(a)
    try:
        for ma, vai, viec, ham in K:
            print("· %-6s [%s] %s" % (ma, vai, viec))
            sys.stdout.flush()
            try:
                ham(n)
            except Hong as e:
                v = e.vai if e.vai != "—" else vai
                print("\nDỪNG ở bước %s — vai %s (%s) — %s" % (ma, v, TEN_VAI.get(v, v), viec))
                print("      %s → HTTP %s · mã %s\n      %s" % (e.duong, e.http, e.ma or "—", e.loi))
                raise SystemExit(1)
            except (urllib.error.URLError, OSError) as e:
                print("\nDỪNG ở bước %s — vai %s — %s\n      không gọi được máy: %s" % (ma, vai, viec, e))
                raise SystemExit(1)
        print("\nXONG — gieo đủ %d bước." % len(K))
    finally:
        try:
            bang_cuoi(n)
        except Exception as e:                                  # noqa: BLE001 — bảng cuối hỏng không che lỗi chính
            print("  (không in được bảng cuối: %s)" % e)


if __name__ == "__main__":
    main()
