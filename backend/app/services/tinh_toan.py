# -*- coding: utf-8 -*-
"""Phép tính trên MỘT phiếu xuất xe — chép nguyên công thức trong Excel của họ.

NHIỀU TIỀN TỆ. Bên Lào nhận cước bằng USD, LAK, Nhân dân tệ hay Bath Thái tuỳ hợp đồng từng khách,
và chi phí dọc đường thì trộn LAK · VND · THB trong cùng một phiếu. Nên trong tệp này:

  · **LAK là tiền gốc.** Mọi tỷ giá là "bao nhiêu LAK cho một đơn vị tiền đó", khoá trên phiếu
    lúc lập (`rate_usd`, `rate_thb`, `rate_vnd`, `rate_cny`). Phiếu đã lập không đổi tỷ giá theo
    thị trường nữa — con số trên tờ giấy phải đứng yên.
  · **Tiền bán theo `price_ccy` của phiếu.** Trả về vừa số theo tiền của phiếu (`doanh_thu`,
    `lai`, …) vừa số đã quy LAK (`*_lak`) để báo cáo cộng chung được. Không có số nào tên "_usd"
    nữa: gọi một số là USD trong khi nó là Nhân dân tệ là nói dối người đọc.
  · **Chi phí luôn cộng về LAK** — mỗi dòng chi mang tiền riêng, quy về LAK rồi mới cộng.

Hai loại phiếu:

  Xe EPL      Doanh thu = tấn × đơn giá (theo price_ccy). Chi = tổng bốn mục III–VI quy về LAK.
              Lãi = doanh thu − chi (so với nhau sau khi cùng quy về LAK).

  Xe liên kết Bên A trả EPL `price` (price_ccy)/tấn; EPL trả chủ xe `hire_price` (hire_ccy)/tấn.
              Chủ xe bị trừ: phí 2% trên tiền thuê, 1 đơn vị/tấn cho phần vượt 40 tấn, và các
              khoản EPL đã ỨNG trước cho chuyến (quy về tiền thuê theo tỷ giá trên phiếu).
              Lãi của EPL = doanh thu − tiền thuê (quy LAK rồi trừ).

Tấn dùng để tính tiền là TẤN CÂN NƠI GIAO (weight_dest); chưa cân thì tạm dùng tấn đầu đi.
Phiếu `price_mode = "chuyen"` (khoán trọn chuyến — xe ngoài không hợp đồng, anh Khampla C3.6) thì
doanh thu = đơn giá, KHÔNG nhân tấn; giá thuê chủ xe cũng vậy. Phần trừ quá tải vẫn tính theo tấn.
Số LAK làm tròn đơn vị; tiền khác làm tròn hai số lẻ — đúng cách họ ghi trên giấy.
"""

TIEN_TE = ("LAK", "USD", "THB", "VND", "CNY")
MAC_DINH = {"USD": 22000.0, "THB": 700.0, "VND": 1.2, "CNY": 3000.0, "LAK": 1.0}


def chuan_tien(ma, mac_dinh="LAK"):
    """Chuẩn hoá mã tiền tệ; mã lạ thì rơi về mặc định chứ không làm hỏng phép tính."""
    m = str(ma or "").strip().upper()
    return m if m in TIEN_TE else mac_dinh


def ty_gia(phieu, ma):
    """Bao nhiêu LAK cho MỘT đơn vị `ma`, theo tỷ giá đã khoá trên phiếu."""
    return {"USD": phieu.rate_usd or MAC_DINH["USD"], "THB": phieu.rate_thb or MAC_DINH["THB"],
            "VND": phieu.rate_vnd or MAC_DINH["VND"], "CNY": getattr(phieu, "rate_cny", None) or MAC_DINH["CNY"],
            "LAK": 1.0}.get(chuan_tien(ma), 1.0)


def tien_cuoc(phieu):
    """Tiền tệ của CƯỚC trên phiếu này (mặc định USD như hợp đồng cũ của họ)."""
    return chuan_tien(getattr(phieu, "price_ccy", None), "USD")


def tien_thue_xe(phieu):
    """Tiền tệ trả chủ xe liên kết — không ghi riêng thì cùng tiền với cước."""
    return chuan_tien(getattr(phieu, "hire_ccy", None) or tien_cuoc(phieu), tien_cuoc(phieu))


def doi(phieu, so_tien, tu, sang):
    """Đổi tiền theo tỷ giá KHOÁ TRÊN PHIẾU: qua LAK rồi sang tiền đích."""
    if so_tien in (None, ""):
        return 0.0
    tu, sang = chuan_tien(tu), chuan_tien(sang)
    if tu == sang:
        return float(so_tien)
    return float(so_tien) * ty_gia(phieu, tu) / ty_gia(phieu, sang)


def lam_tron(so_tien, ma):
    """LAK không có số lẻ; VND cũng ghi tròn đồng. Tiền khác hai số lẻ."""
    return round(so_tien) if chuan_tien(ma) in ("LAK", "VND") else round(so_tien, 2)


def gia_dong(phieu, dong):
    """Đơn giá tính tiền của một dòng. Xe THUÊ: dầu lấy từ KHO là xuất BÁN cho chủ xe — tính theo giá bán KT kho xăng dầu
    gõ trên phiếu (chủ dự án 29/09); chưa gõ thì tạm theo giá vốn. Mọi dòng khác: đơn giá của dòng."""
    ban = getattr(dong, "sale_price", None)
    if ban is not None and phieu is not None and phieu.company == "joint" and dong.section == "fuel" and dong.source == "kho":
        return ban
    return dong.unit_price or 0


def tien_dong(phieu, dong):
    """Số tiền một dòng chi, quy về LAK."""
    return (dong.qty or 0) * gia_dong(phieu, dong) * ty_gia(phieu, dong.currency)


def hinh_thuc(phieu, loai):
    """Bản chất đề nghị theo LOẠI XE của DO (chủ dự án 29/09). `loai`: "tam_ung" | "xuat".
    Xe nhà → "noi_bo" (tạm ứng nội bộ · xuất nội bộ). Xe thuê, EPL ứng → tạm ứng "cong_no_chu_xe" (trừ vào tiền trả
    chủ xe) · dầu "xuat_ban" (bán cho chủ xe theo giá bán riêng)."""
    if (phieu.company or "EPL") != "joint":
        return "noi_bo"
    return "cong_no_chu_xe" if loai == "tam_ung" else "xuat_ban"


def tong_muc(phieu, cac_dong, muc, chi_epl_ung=True):
    """Tổng một mục, tính bằng LAK. Với xe liên kết, `chi_epl_ung=True` chỉ cộng những dòng EPL ứng —
    dòng chủ xe tự trả không phải chi của EPL."""
    tong = 0.0
    for d in cac_dong:
        if d.section != muc:
            continue
        if phieu.company == "joint" and chi_epl_ung and not d.paid_by_epl:
            continue
        tong += tien_dong(phieu, d)
    return tong


def tinh_phieu(phieu, cac_dong, da_thu_lak=0.0):
    """Mọi con số tiền của một phiếu.

    `da_thu_lak` là tổng các lần khách đã trả, quy về LAK (bảng `trip_payments`). Truyền vào từ
    bên gọi để tệp này không phải biết đến cơ sở dữ liệu.
    """
    w = phieu.weight_dest if phieu.weight_dest is not None else (phieu.weight_origin or 0)
    ccy = tien_cuoc(phieu)
    gia = phieu.price or 0
    khoan = (getattr(phieu, "price_mode", None) or "ton") == "chuyen"
    doanh_thu = lam_tron(gia if khoan else w * gia, ccy)
    r_ccy = ty_gia(phieu, ccy)
    muc = {m: round(tong_muc(phieu, cac_dong, m)) for m in ("fuel", "travel", "repair", "other")}
    tong_chi = sum(muc.values())
    hao_hut = None
    if phieu.weight_origin and phieu.weight_dest is not None:
        hao_hut = round((phieu.weight_origin - phieu.weight_dest) / phieu.weight_origin * 100, 2)

    doanh_thu_lak = round(doanh_thu * r_ccy)
    da_thu_lak = round(da_thu_lak or 0)
    ket = {
        "ccy": ccy, "don_gia": gia, "tan_tinh": w, "cach_tinh": "chuyen" if khoan else "ton",
        "doanh_thu": doanh_thu, "doanh_thu_lak": doanh_thu_lak,
        "chi": muc, "tong_chi_lak": tong_chi, "tong_chi_ccy": lam_tron(tong_chi / r_ccy, ccy),
        "hao_hut_pct": hao_hut, "lien_ket": phieu.company == "joint",
        # thu tiền: hoá đơn một tờ, tiền có thể về nhiều lần và bằng tiền khác
        "da_thu_lak": da_thu_lak, "da_thu": lam_tron(da_thu_lak / r_ccy, ccy),
        "con_lai_lak": max(0, doanh_thu_lak - da_thu_lak),
        "con_lai": lam_tron(max(0, doanh_thu_lak - da_thu_lak) / r_ccy, ccy),
    }
    if phieu.company != "joint":
        ket["lai_lak"] = doanh_thu_lak - tong_chi
        ket["lai"] = lam_tron(ket["lai_lak"] / r_ccy, ccy)
        return ket

    h_ccy = tien_thue_xe(phieu)
    r_h = ty_gia(phieu, h_ccy)
    gia_thue = phieu.hire_price if phieu.hire_price is not None else doi(phieu, gia, ccy, h_ccy)
    tien_thue = lam_tron(gia_thue if khoan else w * gia_thue, h_ccy)
    phi = lam_tron(tien_thue * (phieu.fee_pct if phieu.fee_pct is not None else 2) / 100, h_ccy)
    vuot_t = max(0.0, w - (phieu.over_limit_t if phieu.over_limit_t is not None else 40))
    tru_vuot = lam_tron(vuot_t * (phieu.over_price if phieu.over_price is not None else 1), h_ccy)
    ung = lam_tron(tong_chi / r_h, h_ccy)            # EPL đã ứng, quy về tiền thuê
    chu_xe_tu_tra = round(sum(tong_muc(phieu, cac_dong, m, chi_epl_ung=False) for m in muc)
                          - sum(muc.values()))
    tra_chu_xe = lam_tron(tien_thue - phi - tru_vuot - ung, h_ccy)
    lai_lak = doanh_thu_lak - round(tien_thue * r_h)
    ket.update({
        "hire_ccy": h_ccy, "gia_thue": gia_thue,
        "tien_thue": tien_thue, "tien_thue_lak": round(tien_thue * r_h),
        # tiền thuê quy về TIỀN CƯỚC — để dòng "doanh thu − tiền thuê" trên hoá đơn cùng một tiền
        "tien_thue_theo_cuoc": lam_tron(tien_thue * r_h / r_ccy, ccy),
        "phi": phi, "vuot_tan": round(vuot_t, 2), "tru_vuot": tru_vuot, "ung_truoc": ung,
        "tra_chu_xe": tra_chu_xe, "tra_chu_xe_lak": round(tra_chu_xe * r_h),
        "chu_xe_tu_tra_lak": chu_xe_tu_tra,
        "lai_lak": lai_lak, "lai": lam_tron(lai_lak / r_ccy, ccy),
        "giu_lai": lam_tron(phi + tru_vuot, h_ccy),
    })
    return ket


# CÁCH TRẢ từng dòng mục IV, VI — đúng cột ghi chú tờ ໃບເບີກລົດອອກໄປຂົນສົ່ງ của anh Khampla (chủ dự án chốt 29/09):
#   tien_mat  ຈ່າຍເລີຍຕາມໂຊເຟີອອກລົດ      trả ngay khi tài xế xuất xe → tạm ứng
#   luong     ຈ່າຍຕາມຖ້ຽວພ້ອມເງິນເດືອນ    trả theo chuyến cùng lương → màn Tiền chuyến & tiền nước
#   ncc       ຕິດໜີ້ຜູ້ສະໜອງ/ຊໍາລະເປັນງວດ  ghi nợ nhà cung cấp, trả theo đợt → công nợ nhà cung cấp
# Người lập không chọn thì theo khoản mục như Excel; khoản Excel không ghi (ăn, cầu, đỗ xe…) là tiền mặt tài xế cầm đi.
CACH_TRA = ("tien_mat", "luong", "ncc")
CACH_TRA_MAC_DINH = {"x_water": "luong", "x_trip": "luong", "x_chip_lao": "ncc", "x_chip_vn": "ncc"}


def cach_tra(d, company=None):
    """Cách trả của một dòng chi mục IV / VI: người lập chọn; không chọn thì theo khoản mục như Excel.
    Xe THUÊ không có "trả cùng lương" — EPL không trả lương cho tài xế của chủ xe (chủ dự án 30/09): khoản EPL ứng là tạm
    ứng ghi công nợ chủ xe, đưa tiền mặt lúc xe đi."""
    c = getattr(d, "pay_channel", None)
    c = c if c in CACH_TRA else CACH_TRA_MAC_DINH.get(getattr(d, "item_key", None) or "", "tien_mat")
    return "tien_mat" if (company == "joint" and c == "luong") else c


def la_tien_mat_tai_xe(d, company=None):
    """Dòng chi này có phải TIỀN MẶT tài xế cầm đi (tạm ứng) không — MỘT luật cho phiếu tạm ứng, cửa xuất phát,
    màn Tất toán và màn Phiếu của tôi.

    Có: khoản EPL ứng ở mục III (dầu mua dọc đường), IV (đi đường), VI (khác).
    Không: dầu / phụ tùng lấy từ KHO (phiếu xuất kho) · dầu trạm GHI NỢ (trạm tính nợ EPL, tài xế không trả tiền —
    anh Khampla C5.1) · phí cao tốc trừ vào THẺ (C6.1) · dòng mục IV, VI có CÁCH TRẢ không phải tiền mặt (trả cùng lương,
    ghi nợ nhà cung cấp — Excel anh Khampla, 29/09). Rà giao diện 23/09: 500 lít dầu ghi nợ bị tính vào tạm ứng."""
    return bool(d.paid_by_epl and d.source != "kho" and d.section in ("fuel", "travel", "other")
                and not getattr(d, "ghi_no", False) and not getattr(d, "toll_card_id", None)
                and (d.section == "fuel" or cach_tra(d, company) == "tien_mat"))

