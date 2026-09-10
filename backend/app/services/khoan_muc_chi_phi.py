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


def bang_costindex(terms):
    """Tu danh sach khoan muc cua MOT cong thuc gia thanh, lap bang tra ma costindex.

    Tra ve `{"theo_khoan_muc": {charge_type: cost_index},
             "theo_ten":       {ten thuong: cost_index},
             "theo_khoa":      {key: cost_index}}`.

    Ba cach tra vi ba noi goi biet ba thu khac nhau ve dong tien: bang chi phi
    thuc te biet `charge_type`, khoan khach tra them chi biet TEN, cong thuc
    biet `key`. Cung mot ma phai tra duoc tu ca ba, neu khong thi cung mot
    khoan muc ra hai ma tuy noi goi.
    """
    theo_khoan_muc, theo_ten, theo_khoa = {}, {}, {}
    for t in terms if isinstance(terms, list) else []:
        if not isinstance(t, dict):
            continue
        ma = str(t.get("cost_index") or "").strip()
        if not ma:
            continue
        khoa = str(t.get("key") or "").strip()
        ten = str(t.get("label") or "").strip().lower()
        if khoa:
            theo_khoa.setdefault(khoa, ma)
            theo_khoan_muc.setdefault(khoan_muc_tu(khoa, ten), ma)
        if ten:
            theo_ten.setdefault(ten, ma)
    return {"theo_khoan_muc": theo_khoan_muc, "theo_ten": theo_ten, "theo_khoa": theo_khoa}


def costindex_cho(bang, khoa=None, charge_type=None, ten=None):
    """Ma costindex cho mot dong tien, hoac "" neu cong thuc chua gan ma.

    Thu tu tin cay: KHOA cong thuc (tuong minh nhat), roi `charge_type`, roi
    TEN. Tra "" chu khong bia — ho so hoan tat se noi "chua gan ma", va nguoi
    lam tai chinh biet phai vao cong thuc gia thanh de gan. Danh sach ma la cua
    ben cong no cung cap, khong phai cua he nay dat.
    """
    if not bang:
        return ""
    khoa = str(khoa or "").strip()
    if khoa and khoa in bang.get("theo_khoa", {}):
        return bang["theo_khoa"][khoa]
    ct = str(charge_type or "").strip().lower()
    if ct and ct in bang.get("theo_khoan_muc", {}):
        return bang["theo_khoan_muc"][ct]
    chu = str(ten or "").strip().lower()
    if chu and chu in bang.get("theo_ten", {}):
        return bang["theo_ten"][chu]
    # Ten khong trung tuyet doi (vi du "Chi phi xang dau /km" so voi "Chi phi
    # xang dau"): suy charge_type tu ten roi tra theo do.
    if chu:
        return bang.get("theo_khoan_muc", {}).get(khoan_muc_tu(None, chu, mac_dinh=""), "")
    return ""


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
    if mac_dinh == "":
        return ""
    return mac_dinh if mac_dinh in KHOAN_MUC else "other"


def bang_costindex_cua_xe(db, vehicle_id):
    """Bang tra ma costindex cua CHIEC XE dang chay chuyen, hoac {} neu khong co.

    Duong di: xe -> loai xe (theo id, roi theo ten) -> cong thuc gia thanh cua
    loai xe -> `bang_costindex(terms)`. Ma costindex gan o tang LOAI XE (cong
    thuc), khong gan o tang xe: ghi de theo xe chi doi DON GIA, khoan muc va ma
    cua no ke thua tu loai — nen mot xe cu ton dau hon van mang cung ma xang
    dau voi ca doi.

    Nap model va dich vu trong ham de khong tao vong nap: `bao_gia_service` nap
    module nay, va module nay khong duoc nap nguoc lai o tang module.
    """
    if not db or not vehicle_id:
        return {}
    from sqlalchemy import func
    from models import Vehicle, VehicleType
    from services.bao_gia_service import cong_thuc_loai_xe

    xe = db.get(Vehicle, vehicle_id)
    if xe is None or not str(xe.type or "").strip():
        return {}
    loai = db.get(VehicleType, xe.type)
    if loai is None:
        loai = (db.query(VehicleType)
                .filter(func.lower(VehicleType.name) == str(xe.type).lower())
                .first())
    if loai is None:
        return {}
    cong_thuc = cong_thuc_loai_xe(db, loai.id)
    return bang_costindex((cong_thuc or {}).get("terms"))
