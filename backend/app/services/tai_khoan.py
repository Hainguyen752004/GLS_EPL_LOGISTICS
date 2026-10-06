# -*- coding: utf-8 -*-
"""BẢNG ĐỊNH KHOẢN — chỗ DUY NHẤT trang điều xe lấy mã tài khoản: dòng chi trên phiếu xuất xe, tờ gợi ý gửi bên kế toán
(services/chung_tu.py), danh mục dự phòng (routes/acc_code.py), màn Quy trình.

Rà ngày 30/09/2026 theo ba nguồn (chủ dự án: "phải là số thật … theo file excel và theo cái API … đúng luật pháp"):
  1. Excel của khách — DOCS/ຂົນສົ່ງ EPL.xlsx, tờ ໃບບິນອອກລົດ, cột ເດີນບັນຊີ:
       1211/70 cước · 625/371 dầu qua kho · 625/402 khoản đi đường · 614/402 sửa ngoài · 614/371 phụ tùng kho.
  2. Quy trình kế toán của khách — EPL flow of Logistics.docx:
       625/37 · 4022/37 dầu kho · 614/4021 · 4022/4021 sửa ngoài · 614/37 · 4022/37 phụ tùng kho · 1211/70 hoá đơn.
  3. Danh mục THẬT của bên kế toán — API country-accounts quốc gia 11 (Lào), chụp vào danh_muc_tai_khoan_lao.json.

Luật rút ra:
  · Mã in ra phải là tài khoản LÁ (ghi sổ được) của danh mục thật. "70" là tài khoản NHÓM (Bán sản phẩm, hàng hoá,
    dịch vụ) — không hạch toán được — nên cước vận chuyển ghi 708 (bán dịch vụ khác), bán dầu / phụ tùng ghi 707
    (bán hàng hoá). "37" / "371" trong giấy tờ cũ của khách là 137 của danh mục hiện hành (hàng hoá tồn kho).
  · Ba MÃ CON anh Khampla đặt (22/09), chủ dự án chốt giữ (23/09): 1371 (con của 137), 4021 và 4022 (con của 402).
    Ngày 01/10 đã mở cả ba trong danh mục Lào bên anh Tune (chủ dự án cho phép): 137 và 402 chuyển thành tài khoản
    TỔNG HỢP, ba mã con là tài khoản lá. Bản chụp danh_muc_tai_khoan_lao.json chụp lại ngày đó. MA_CON_KHACH giữ lại
    để có tên Việt gọn, và để máy khác (danh mục chưa mở) vẫn hiện nhãn "chưa mở" đúng.
    Đổi mã thì đổi ở MA_CON_KHACH / các hằng số dưới đây, KHÔNG sửa rải rác.
  · Vế CÓ của một dòng chi đi theo CÁCH TRẢ, vì mỗi cách trả là một đối tượng nợ khác nhau:
        lấy kho ..................................... kho 1371
        ghi nợ trạm dầu · nhà cung cấp · thẻ cao tốc · sửa ngoài ... phải trả nhà cung cấp 4021
        tiền mặt tài xế cầm đi (tạm ứng) · xe nhà .... 1601 tạm ứng nhân viên (quyết toán lúc tất toán tài xế)
        tiền mặt tài xế cầm đi · xe thuê ............. 1011 tiền mặt — EPL chi hộ, ghi công nợ chủ xe (Nợ 4022)
        trả cùng lương (xe nhà) ...................... 4201 phải trả nhân viên — tiền lương, tiền công
    Trước 30/09 mọi dòng không lấy kho đều ghi Có 4021 — tức tạm ứng tài xế bị ghi thành nợ nhà cung cấp: sai đối tượng
    (tài xế là nhân viên, không phải nhà cung cấp) và sai tài khoản (tạm ứng là tiền EPL còn đòi lại, luật kế toán Lào
    đặt ở 160 — ພະນັກງານ ຕິດໜີ້). Chủ dự án 30/09: "xe nhà ứng tiền trước thì tính vào tài xế để sau này tất toán".
  · Xe thuê (liên kết) EPL ứng: Nợ 4022 — trừ vào tiền trả chủ xe. Dầu (chốt 29/09) và phụ tùng (chốt 30/09) lấy kho cho
    xe thuê là XUẤT BÁN theo giá bán riêng → Có 707 doanh thu bán hàng hoá; phía kho ghi giá vốn 607 / kho 1371.
  · Chủ dự án 30/09: phải thu cước giữ 1211 như Excel; dầu xe chạy giữ 625 như anh Khampla — làm theo Excel, anh Khampla.
  · Chủ xe tự chi (paid_by_epl = False): không phải tiền của EPL → KHÔNG định khoản.
  · Tiền thuê xe liên kết (chủ dự án chốt 01/10): lúc khoá phiếu Nợ 621 chi phí vận chuyển / Có 4022 phải trả chủ xe,
    bằng tiền thuê. 621 khớp dòng "ຄ່າຂົນສົ່ງນອກ" trong Excel (Excel ghi vế có 402 — 4022 là mã con của nó). Bên kế
    toán chưa có API bút toán tổng hợp nên bên em chỉ đưa cặp này ra bàn giao (hire.acc_code), chưa gửi được.
  · 06/10 (chủ dự án giao, chốt mã): cùng chứng từ thuê xe lúc khoá phiếu, hai khoản EPL GIỮ LẠI của tiền thuê thành thu nhập
    của EPL — trước đây chỉ trừ vào tiền trả đối tác mà không có bút toán, nên 4022 treo đúng phần đó sau khi trả đối tác:
        phí quản lý (Excel «ຫັກຄ່າທຳນຽມ 2%/ບິນ») ......... Nợ 4022 / Có 715 doanh thu tiền hoa hồng (ຮັບຄ່ານາຍໜ້າ)
        cắt quá tải (Excel «ຫັກແກ່ເກີນ 1$/ໂຕນ») .......... Nợ 4022 / Có 758 thu nhập từ hoạt động thông thường khác
    Cả hai là tài khoản LÁ của danh mục Lào (nhóm 71 · 75 là tài khoản tổng hợp, không ghi sổ được).
"""
import json
import os

_TEP = os.path.join(os.path.dirname(__file__), "danh_muc_tai_khoan_lao.json")
with open(_TEP, encoding="utf-8") as _f:
    _BAN = json.load(_f)
DANH_MUC = {x["code"]: x for x in _BAN["tai_khoan"]}
CHUP_NGAY = _BAN["chup_ngay"]

# ------------------------------------------------------------------ mã theo vai trò
CP_DI_LAI = "625"     # ຄ່າເດີນທາງ … — khách dùng cho dầu và khoản đi đường (Excel, quy trình)
CP_SUA = "614"        # ຄ່າບົວລະບັດ, ບຳລຸງຮັກສາ ແລະ ສ້ອມແປງ
CP_THUE_XE = "621"    # ຄ່າຂົນສົ່ງ — tiền thuê xe liên kết; Excel ghi "ຄ່າຂົນສົ່ງນອກ" (chủ dự án chốt 01/10)
GIA_VON = "607"       # ສິນຄ້າ (nhóm 60 — giá vốn hàng bán) — chủ dự án chốt 23/09
KHO = "1371"          # mã con của 137 (anh Khampla) — mở 01/10
NCC = "4021"          # mã con của 402 (anh Khampla) — mở 01/10
CHU_XE = "4022"       # mã con của 402 (quy trình khách) — mở 01/10
TAM_UNG = "1601"      # ພະນັກງານ - ເງິນລ່ວງໜ້າ … (tạm ứng nhân viên)
LUONG = "4201"        # ພະນັກງານ - ຄ່າທົດແທນແຮງງານຕ້ອງສະສາງ (phải trả nhân viên)
PHAI_THU = "1211"     # ລູກຄ້າ-ຄ່າສິນຄ້າ — khách ghi 1211 cho cả cước (Excel, quy trình); 1213 là "khách hàng - dịch vụ"
DT_VAN_CHUYEN = "708"  # ຂາຍການບໍລິການອື່ນໆ — "70" của khách là mã nhóm
DT_BAN_HANG = "707"   # ຂາຍສິນຄ້າ
# 06/10: phí và quá tải EPL giữ lại của tiền thuê xe liên kết — ghi cùng chứng từ thue_xe lúc khoá phiếu (but_toan_cho)
DT_PHI_QUAN_LY = "715"   # ຮັບຄ່ານາຍໜ້າ (con của 71) — phí quản lý 2 %/bill trên tiền thuê: Nợ 4022 / Có 715
TN_CAT_QUA_TAI = "758"   # ລາຍຮັບອື່ນໆ ຈາກການຄຸ້ມຄອງ - ບໍລິຫານ ປົກກະຕິ (con của 75) — cắt quá tải 1/tấn vượt: Nợ 4022 / Có 758
TIEN = {("cash", True): "1011", ("cash", False): "1012", ("bank", True): "1021", ("bank", False): "1022"}

# Mã con của khách chưa có trong danh mục thật: mã → (mã cha, tên Việt, tên Lào). Tên Lào ráp từ cụm đã có.
MA_CON_KHACH = {
    "1371": ("137", "Kho hàng, vật tư", "ສາງສິນຄ້າ, ວັດຖຸ"),
    "4021": ("402", "Phải trả nhà cung cấp", "ໜີ້ຕ້ອງສົ່ງ ຜູ້ສະໜອງ"),
    "4022": ("402", "Phải trả chủ xe liên kết", "ເຈົ້າໜີ້ເຈົ້າຂອງລົດຮ່ວມ"),
}

# Tên Việt gọn cho các mã trang điều xe dùng (tên Việt trong danh mục thật là bản dịch máy, dấu cách lộn xộn).
TEN_VI = {
    "625": "Chi phí đi lại, công tác phí", "614": "Chi phí bảo trì, sửa chữa", "621": "Chi phí vận chuyển (thuê xe ngoài)", "607": "Giá vốn hàng hoá đã bán",
    "1601": "Tạm ứng nhân viên", "4201": "Phải trả nhân viên — tiền lương, tiền công",
    "1211": "Phải thu khách hàng — hàng hoá", "1213": "Phải thu khách hàng — dịch vụ",
    "708": "Doanh thu bán dịch vụ khác (vận chuyển)", "707": "Doanh thu bán hàng hoá",
    "715": "Doanh thu tiền hoa hồng", "758": "Thu nhập từ các hoạt động thông thường khác",
    "1011": "Tiền mặt bằng Kíp", "1012": "Tiền mặt ngoại tệ", "1021": "Tiền gửi ngân hàng bằng Kíp",
    "1022": "Tiền gửi ngân hàng ngoại tệ", "137": "Hàng hoá tồn kho", "401": "Phải trả nhà cung cấp hàng hoá, vật tư",
    "402": "Phải trả nhà cung cấp dịch vụ",
}


def trang_thai(ma):
    """"that" (tài khoản lá của danh mục thật) · "nhom" (có nhưng là tài khoản nhóm — không ghi sổ được) ·
    "ma_con_khach" (mã con của khách, chưa mở trong danh mục) · "khong_co"."""
    x = DANH_MUC.get(str(ma or ""))
    if x:
        return "that" if x["postable"] else "nhom"
    return "ma_con_khach" if ma in MA_CON_KHACH else "khong_co"


def ten(ma, ngon="vi"):
    """Tên tài khoản. Tiếng Lào lấy nguyên danh mục thật; tiếng Việt lấy TEN_VI, không có thì bản dịch của danh mục."""
    ma = str(ma or "")
    if ma in MA_CON_KHACH:
        cha, vi, lo = MA_CON_KHACH[ma]
        return lo if ngon == "lo" else vi
    x = DANH_MUC.get(ma)
    if not x:
        return None
    if ngon == "lo":
        return x["name_lo"].replace("​", "").strip()
    return TEN_VI.get(ma) or " ".join(x["name_vi"].replace(" ,", ",").split())


def ve(ma):
    """(mã, tên Việt) — dạng hai vế services/chung_tu.py dùng."""
    return (ma, ten(ma))


def ma_tien(phuong_thuc=None, tien_te=None):
    """Vế tiền theo CÁCH thu/chi và TIỀN TỆ. Không ghi cách thì là tiền mặt (quỹ Thà Bốc, thủ quỹ Viêng Chăn đều là quỹ
    tiền mặt). `offset` (cấn trừ), `other` không vào tay quỹ nên xếp ngân hàng — bên kế toán đối chiếu lại nếu cần."""
    pt = "bank" if (phuong_thuc or "cash") in ("bank", "offset", "other") else "cash"
    return TIEN[(pt, (tien_te or "LAK").upper() == "LAK")]


def chi_phi(company="EPL", section=None):
    """Vế NỢ của một khoản chi: xe thuê là công nợ chủ xe (trừ vào tiền trả), xe nhà là chi phí theo mục."""
    if company == "joint":
        return CHU_XE
    return CP_SUA if section == "repair" else CP_DI_LAI


def dinh_khoan_dong(company, section, source=None, *, place=None, paid_by_epl=True, ghi_no=False, the=False, cach=None):
    """Cặp "NỢ/CÓ" mặc định của MỘT dòng chi phiếu xuất xe; None khi dòng không phải tiền của EPL (chủ xe tự chi).

    `cach`: cách trả mục IV / VI (services/tinh_toan.cach_tra — đã tính mặc định theo khoản mục và luật xe thuê)."""
    if not paid_by_epl:
        return None
    thue = company == "joint"
    if section == "fuel" and source is None:
        source = "kho" if (place or "fp_yard") == "fp_yard" else "mua"
    no = chi_phi(company, section)
    if source == "kho":
        co = DT_BAN_HANG if (thue and section in ("fuel", "repair")) else KHO   # xe thuê: dầu, phụ tùng kho là xuất bán
    elif ghi_no or the or section == "repair":
        co = NCC
    else:
        c = "tien_mat" if section == "fuel" else (cach or "tien_mat")
        if thue and c == "luong":
            c = "tien_mat"          # EPL không trả lương cho tài xế của chủ xe (30/09)
        co = NCC if c == "ncc" else LUONG if c == "luong" else (TIEN[("cash", True)] if thue else TAM_UNG)
    return "%s/%s" % (no, co)


# Mọi cặp mà LUẬT (cũ và mới) có thể sinh ra cho một dòng chi. Mã trên dòng nằm trong tập này là mã MẶC ĐỊNH do máy
# đặt — hiện và gửi theo luật hiện hành; mã ngoài tập này là người dùng tự chọn (ô Định khoản) — giữ nguyên.
_NO_HE = (CP_DI_LAI, CP_SUA, CHU_XE)
_CO_HE = (KHO, NCC, TAM_UNG, LUONG, DT_BAN_HANG, "1011", "1012", "402", "371", "37")
MA_HE_THONG = frozenset("%s/%s" % (n, c) for n in _NO_HE for c in _CO_HE)


def la_ma_he_thong(ma):
    return (ma or "") in MA_HE_THONG


def tk_dong(company, d):
    """Định khoản ĐANG CÓ HIỆU LỰC của một dòng chi (TripExpense): mã người dùng tự chọn thì giữ, còn lại tính theo luật
    hiện hành — nên dòng cũ mang mã theo luật cũ (625/4021 cho tiền tạm ứng…) tự hiện đúng mà không phải sửa dữ liệu."""
    ma = getattr(d, "acct_code", None)
    if ma and not la_ma_he_thong(ma):
        return ma
    from services.tinh_toan import cach_tra
    cach = cach_tra(d, company) if d.section in ("travel", "other") else None
    return dinh_khoan_dong(company, d.section, d.source, place=getattr(d, "place", None),
                           paid_by_epl=d.paid_by_epl is not False, ghi_no=bool(getattr(d, "ghi_no", False)),
                           the=bool(getattr(d, "toll_card_id", None)), cach=cach)


def luat_cho_giao_dien():
    """Bảng mã phiếu xuất xe dùng để tính mặc định ngay trên màn (soi gương dinh_khoan_dong) + tên từng mã."""
    dung = [CP_DI_LAI, CP_SUA, CHU_XE, KHO, NCC, TAM_UNG, LUONG, DT_BAN_HANG, TIEN[("cash", True)]]
    return {"cp_di_lai": CP_DI_LAI, "cp_sua": CP_SUA, "chu_xe": CHU_XE, "kho": KHO, "ncc": NCC, "tam_ung": TAM_UNG,
            "luong": LUONG, "ban_hang": DT_BAN_HANG, "tien_mat": TIEN[("cash", True)],
            "he_thong": sorted(MA_HE_THONG),
            "ten": {m: {"vi": ten(m), "lo": ten(m, "lo"), "trang_thai": trang_thai(m)} for m in dung}}


def ma_con_chua_mo(co):
    """Ba mã con của khách mà danh mục `co` (tập mã) CHƯA có — vẫn cho chọn (phiếu đang dùng) nhưng ghi rõ "chưa mở".
    01/10: mở trong DB bên anh Tune mà API ở máy em nối; bản đang host nối DB khác, chưa có — nên phải xét theo từng danh mục."""
    return [{"code": ma, "name": lo, "description": "%s — mã con của %s, bên kế toán chưa mở trong danh mục" % (vi, cha),   # câu cho người đọc: không tên người, không ngày chốt
             "parent": cha, "postable": True, "ma_con_khach": True}
            for ma, (cha, vi, lo) in MA_CON_KHACH.items() if ma not in co]


def danh_muc_du_phong():
    """Danh mục khi chưa nối được API bên kế toán: CHÍNH bản chụp danh mục thật, cộng mã con của khách chưa mở (đánh dấu)."""
    ds = [{"code": x["code"], "name": x["name_lo"].replace("​", "").strip(), "description": ten(x["code"]) or x["name_vi"],
           "parent": x["parent"], "postable": x["postable"]} for x in _BAN["tai_khoan"]]
    return sorted(ds + ma_con_chua_mo(DANH_MUC), key=lambda x: x["code"])
