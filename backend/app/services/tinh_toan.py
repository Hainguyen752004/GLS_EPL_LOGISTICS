# -*- coding: utf-8 -*-
"""Phép tính trên MỘT phiếu xuất xe — chép nguyên công thức trong Excel của họ.

Hai loại phiếu:

  Xe EPL      Doanh thu = tấn × giá (USD). Chi = tổng bốn mục III–VI quy về LAK.
              Lãi = doanh thu − chi.

  Xe liên kết Bên A trả EPL `price` USD/tấn; EPL trả chủ xe `hire_price` USD/tấn.
              Chủ xe bị trừ: phí 2% trên tiền thuê, 1 USD/tấn cho phần vượt 40 tấn, và
              các khoản EPL đã ỨNG trước cho chuyến (quy USD theo tỷ giá trên phiếu).
              Lãi của EPL = (price − hire) × tấn  (+ phần trừ chủ xe là tiền EPL giữ lại).

Tấn dùng để tính tiền là TẤN CÂN NƠI GIAO (weight_dest); chưa cân thì tạm dùng tấn đầu đi.
Mọi số tiền LAK làm tròn đơn vị, USD hai số lẻ — đúng cách họ ghi trên giấy.
"""


def ty_gia(phieu, ma):
    return {"USD": phieu.rate_usd or 22000, "THB": phieu.rate_thb or 700,
            "VND": phieu.rate_vnd or 1.2, "LAK": 1.0}.get((ma or "LAK").upper(), 1.0)


def tien_dong(phieu, dong):
    """Số tiền một dòng chi, quy về LAK."""
    return (dong.qty or 0) * (dong.unit_price or 0) * ty_gia(phieu, dong.currency)


def tong_muc(phieu, cac_dong, muc, chi_epl_ung=True):
    """Tổng một mục. Với xe liên kết, `chi_epl_ung=True` chỉ cộng những dòng EPL ứng —
    dòng chủ xe tự trả không phải chi của EPL."""
    tong = 0.0
    for d in cac_dong:
        if d.section != muc:
            continue
        if phieu.company == "joint" and chi_epl_ung and not d.paid_by_epl:
            continue
        tong += tien_dong(phieu, d)
    return tong


def tinh_phieu(phieu, cac_dong):
    w = phieu.weight_dest if phieu.weight_dest is not None else (phieu.weight_origin or 0)
    gia = phieu.price_usd or 0
    doanh_thu_usd = round(w * gia, 2)
    r_usd = ty_gia(phieu, "USD")
    muc = {m: round(tong_muc(phieu, cac_dong, m)) for m in ("fuel", "travel", "repair", "other")}
    tong_chi = sum(muc.values())
    hao_hut = None
    if phieu.weight_origin and phieu.weight_dest is not None:
        hao_hut = round((phieu.weight_origin - phieu.weight_dest) / phieu.weight_origin * 100, 2)

    ket = {
        "tan_tinh": w, "doanh_thu_usd": doanh_thu_usd, "doanh_thu_lak": round(doanh_thu_usd * r_usd),
        "chi": muc, "tong_chi_lak": tong_chi, "tong_chi_usd": round(tong_chi / r_usd, 2),
        "hao_hut_pct": hao_hut, "lien_ket": phieu.company == "joint",
    }
    if phieu.company != "joint":
        ket["lai_usd"] = round(doanh_thu_usd - tong_chi / r_usd, 2)
        ket["lai_lak"] = round(doanh_thu_usd * r_usd - tong_chi)
        return ket

    gia_thue = phieu.hire_price_usd if phieu.hire_price_usd is not None else gia
    tien_thue = round(w * gia_thue, 2)
    phi = round(tien_thue * (phieu.fee_pct if phieu.fee_pct is not None else 2) / 100, 2)
    vuot_t = max(0.0, w - (phieu.over_limit_t if phieu.over_limit_t is not None else 40))
    tru_vuot = round(vuot_t * (phieu.over_price_usd if phieu.over_price_usd is not None else 1), 2)
    ung_usd = round(tong_chi / r_usd, 2)
    chu_xe_tu_tra = round(sum(tong_muc(phieu, cac_dong, m, chi_epl_ung=False) for m in muc)
                          - sum(muc.values()))
    ket.update({
        "gia_thue_usd": gia_thue, "tien_thue_usd": tien_thue, "phi_usd": phi,
        "vuot_tan": round(vuot_t, 2), "tru_vuot_usd": tru_vuot, "ung_truoc_usd": ung_usd,
        "tra_chu_xe_usd": round(tien_thue - phi - tru_vuot - ung_usd, 2),
        "chu_xe_tu_tra_lak": chu_xe_tu_tra,
        "lai_usd": round(doanh_thu_usd - tien_thue, 2),
        "lai_lak": round((doanh_thu_usd - tien_thue) * r_usd),
        "giu_lai_usd": round(phi + tru_vuot, 2),
    })
    return ket
