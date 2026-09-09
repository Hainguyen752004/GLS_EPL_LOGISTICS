# -*- coding: utf-8 -*-
"""Danh muc KHOAN MUC CHI PHI, va phep suy ra ma phan loai cho mot dong chi phi.

MOT NGUON SU THAT cho ma khoan muc. Ba cho doc no:

  · `models.FreightChargeItem.charge_type` — rang buoc CHECK cua bang chi phi
    thuc te dung dung danh sach nay;
  · `tms_cost_service` — dat `charge_type` cho tung dong khi lap bang chi phi;
  · `routes/delivery_routes.py` — tra `charge_type` trong ho so chot cua lenh
    giao hang, tuc trong goi du lieu ma he cong no khach hang doc.

VI SAO PHAI LA MOT CHO. Truoc day khong co cho nao: `tms_cost_service` VIET CUNG
`charge_type="other"` cho MOI dong, va ho so chot thi dung mot bo ma thu hai
(`code` cua cau phan cong thuc, trong do "Phi bai & luu kho" la `warehouse` chu
khong phai `yard`). Ket qua do duoc tren du lieu that: ca bon dong chi phi cua
mot chuyen deu ra "Khoan khac", nen he cong no khong tach duoc xang dau voi cau
duong — dung cai ma chu du an can. Hai bo ma song song thi ai doc cung anh xa
theo mot bo roi lech bo kia, va lech IM LANG vi ca hai ma deu "trong dung".
"""

#: Danh sach khoan muc, PHAI giong `models.FreightChargeItem` va giong moc 041.
#: Them mot khoan muc moi thi phai sua ca ba cho, va phai viet mot moc nang cap.
KHOAN_MUC = ("fuel", "toll", "driver", "yard", "waiting", "loading", "unloading",
             "carrier_base", "surcharge", "discount", "other")

#: Ten tieng Viet de hien tren man hinh. Chi la NHAN, khong phai nguon su that —
#: nguon su that la ma o tren.
TEN_KHOAN_MUC = {
    "fuel": "Chi phí xăng dầu",
    "toll": "Phí cầu đường / BOT",
    "driver": "Phụ cấp chuyến tài xế",
    "yard": "Phí bãi & lưu kho",
    "waiting": "Phí chờ",
    "loading": "Phí bốc hàng",
    "unloading": "Phí dỡ hàng",
    "carrier_base": "Cước nhà xe thuê ngoài",
    "surcharge": "Phụ phí",
    "discount": "Giảm trừ",
    "other": "Khoản khác",
}

#: Khoan muc phat sinh o tang CHUYEN, khong rieng cua mot lenh giao hang.
#:
#: Xang dau va cau duong ti le voi DUONG CHAY, phu cap tai xe la cua ca chuyen.
#: Nhung khoan con lai (boc, do, cho, bai) gan voi tung lo hang. Danh sach nay
#: la thu ai muon phan bo chi phi chuyen ve tung DO se can.
KHOAN_MUC_CHUNG_CHUYEN = ("fuel", "toll", "driver")

#: Khoa cua CONG THUC GIA THANH -> ma khoan muc.
#:
#: Cong thuc dung bo khoa rieng cua no (`frontend/js/formula-model.js`): fuel,
#: driver, toll, `wh` cho phi bai & luu kho, `rate` cho cuoc thu khach. Ba khoa
#: dau trung ten voi `charge_type`, nhung `wh` thi khong — no la `yard`. Do
#: chinh la cho da lech.
KHOA_CONG_THUC = {
    "fuel": "fuel",
    "driver": "driver",
    "toll": "toll",
    "wh": "yard",
    "yard": "yard",
    "warehouse": "yard",
    "rate": "carrier_base",     # cuoc thu khach, khong phai khoan chi
}

#: Nhan tieng Viet -> ma khoan muc, dung khi ben goi chi gui TEN chu khong gui khoa.
#:
#: Doi chieu theo TU KHOA chu khong theo chuoi day du: nhan that co the la
#: "Chi phi xang dau /km" hay "Chi phí xăng dầu" tuy man hinh.
TU_KHOA_NHAN = (
    ("xăng", "fuel"), ("dầu", "fuel"), ("nhiên liệu", "fuel"),
    ("cầu đường", "toll"), ("bot", "toll"), ("phí đường", "toll"),
    ("tài xế", "driver"), ("phụ cấp", "driver"), ("lương", "driver"),
    ("bãi", "yard"), ("lưu kho", "yard"), ("kho", "yard"),
    ("bốc", "loading"), ("xếp hàng", "loading"),
    ("dỡ", "unloading"), ("hạ hàng", "unloading"),
    ("chờ", "waiting"), ("lưu ca", "waiting"),
    ("thuê ngoài", "carrier_base"), ("nhà xe", "carrier_base"),
    ("phụ phí", "surcharge"),
    ("giảm", "discount"), ("chiết khấu", "discount"),
)


def khoan_muc_tu(khoa=None, ten=None, mac_dinh="other"):
    """Suy ra ma KHOAN MUC tu khoa cong thuc hoac tu ten hien thi.

    Thu tu tin cay: KHOA cong thuc truoc (tuong minh), roi den TEN (phai doan),
    cuoi cung la `other`. Doan theo ten la duong DOI LUI cho nhung ben goi chua
    gui khoa — khong phai duong chinh, va no khong bao gio ghi de mot khoa da co.

    Khoan muc do NGUOI DUNG TU THEM tren man cong thuc thi khong co khoa nao
    quen biet; luc do ho phai tu chon khoan muc, va do la viec cua giao dien.
    Ham nay khong doan bua cho chung — tra `other` va de nguoi dung sua.
    """
    ma = str(khoa or "").strip().lower()
    if ma in KHOAN_MUC:
        return ma
    if ma in KHOA_CONG_THUC:
        return KHOA_CONG_THUC[ma]
    chu = str(ten or "").strip().lower()
    if chu:
        for tu, km in TU_KHOA_NHAN:
            if tu in chu:
                return km
    return mac_dinh if mac_dinh in KHOAN_MUC else "other"
