"""Doi don gia cuoc theo don vi cua khach thanh `d/chuyen`.

VI SAO LA MOT TEP RIENG, khong nam trong `bao_gia_service.py`.

Hai duong can dung phep doi nay:

  · `bao_gia_service.tach_thanh_do` — khoa gia cho tung lenh giao hang.
  · `workflow_service.create_quotation` / `update_quotation` — suy ra
    `selling_price` tu `unit_price` khi luu, de hai cot khong troi khoi nhau.

`bao_gia_service` da nap `workflow_service` (de dung mot cach doc moc thoi
gian), nen `workflow_service` khong nap nguoc lai duoc. Neu moi ben tu viet
mot ban phep doi thi som muon man Bao gia hien mot con so con lenh giao hang
mang mot con so khac cho cung mot chuyen — dung loi ma ca hai duong nay ton
tai de tranh.

Tep nay CO Y khong nap gi ngoai `errors`: khong mo hinh, khong phien co so du
lieu. Nho vay khong ai tao ra duoc vong nap moi.
"""

from services.errors import DomainError


def _so(gia_tri, mac_dinh=0.0):
    """Doc mot so tu du lieu nguoi dung, tra ve `mac_dinh` khi khong doc duoc."""
    if gia_tri is None or gia_tri == "":
        return float(mac_dinh)
    try:
        return float(gia_tri)
    except (TypeError, ValueError):
        return float(mac_dinh)


#: Don vi bao gia cho khach. `doi` tra ve so luong nhan voi don gia de ra tien
#: cua MOT chuyen.
#:
#: `per_trip` la 1 vi don gia da la tien mot chuyen. `per_km` nhan so km cua
#: tuyen. Ba don vi con lai nhan so luong hang CUA MOT CHUYEN — va do la cho
#: `min_qty_per_trip` chen vao: mo xuc thieu tai thi tinh theo muc toi thieu,
#: khong tinh theo so thuc, vi gia thanh khong giam mot dong nao khi xe cho it.
DON_VI_CUOC = {
    "per_trip": {"ten": "mỗi chuyến", "nhan": "chuyến", "doi": lambda t, sl: 1},
    "per_tonne": {"ten": "mỗi tấn", "nhan": "tấn", "doi": lambda t, sl: sl},
    "per_m3": {"ten": "mỗi m³", "nhan": "m³", "doi": lambda t, sl: sl},
    "per_kg": {"ten": "mỗi kg", "nhan": "kg", "doi": lambda t, sl: sl},
    "per_km": {"ten": "mỗi km", "nhan": "km", "doi": lambda t, sl: t["km"]},
}


def gia_moi_chuyen(price_basis, unit_price, so_luong_moi_chuyen, min_qty_per_trip=None,
                   km=0):
    """Doi don gia theo don vi cua khach thanh `d/chuyen`.

    `min_qty_per_trip` la thu chan mo da xuc thieu tai lam mot chuyen lai thanh
    lo: gia thanh khong giam mot dong nao khi xe cho it hon, nen so luong tinh
    tien khong duoc thap hon muc toi thieu da thoa thuan.
    """
    don_vi = str(price_basis or "per_trip")
    if don_vi not in DON_VI_CUOC:
        raise DomainError("PRICE_BASIS_INVALID",
                          "Đơn vị tính cước không hợp lệ: %s. Nhận: %s."
                          % (don_vi, ", ".join(DON_VI_CUOC)), 422)
    gia = _so(unit_price)
    if gia <= 0:
        raise DomainError("UNIT_PRICE_REQUIRED", "Chưa khai đơn giá cước.", 422)
    sl = _so(so_luong_moi_chuyen)
    toi_thieu = _so(min_qty_per_trip)
    if don_vi in ("per_tonne", "per_m3", "per_kg") and toi_thieu > 0:
        sl = max(sl, toi_thieu)
    he_so = DON_VI_CUOC[don_vi]["doi"]({"km": _so(km)}, sl)
    return round(gia * _so(he_so), 2)
