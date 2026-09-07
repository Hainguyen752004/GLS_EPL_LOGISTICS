"""Danh muc DU LIEU GOC mo rong cho ban demo: loai xe, xe, tuyen, khach hang.

VI SAO CAN: ban demo truoc chi co MOT loai xe, MOT tuyen, HAI xe va MOT khach.
Voi bay nhieu thi phan lon man hinh khong the hien duoc dieu chung sinh ra de
lam: bang so sanh gia thanh giua cac loai xe chi co mot dong, o chon tuyen chi
co mot lua chon, va luoi lich xe hai hang. Nguoi xem khong phan biet duoc
"man nay chi hien it nhu vay" voi "man nay hong".

BA NGUYEN TAC khi dat so, de con so nao cung tra nguoc lai duoc:

1. CHI PHI XANG DAU tinh RA tu dinh muc, khong bia:
       chi phi /km = fuel_norm (lit/100km) / 100 x gia dau (d/lit)
   Voi gia dau 23.000 d/lit. Nen "Dau keo 40 feet an 35 lit/100km" ra dung
   8.050 d/km, va ai cung kiem lai duoc bang may tinh.

2. CHI PHI VA GIA BAN LA HAI LOAI KHAC NHAU, khong cong chung. Bon cau phan
   `fuel`, `driver`, `toll`, `wh` la tien CHI ra; `rate` la CUOC THU cua khach.
   Cong ca nam thi ket qua khong phai gia thanh, cung khong phai gia ban.

3. KHONG DUNG VAO `DEMO-VT-20FT`. Loai xe do va cong thuc cua no dang duoc cac
   bai kiem doi chieu so tien (bao gia `DEMO-QT-2026-001` ra dung
   2.132.200 d gia thanh va 3.600.000 d cuoc). Doi mot con so trong do la lam
   do mot loat bai kiem o cho khac.
"""

import json

from models import (
    CostFormula,
    Customer,
    Driver,
    Location,
    Route,
    Vehicle,
    VehicleType,
)


# Gia dau diesel dung de suy ra chi phi xang dau tren 1 km. De o mot cho de khi
# gia doi thi sua mot dong, va moi loai xe tinh lai theo dung dinh muc cua no.
GIA_DAU_VND_LIT = 23000


def chi_phi_dau_moi_km(fuel_norm_lit_100km):
    """Tien xang dau cho 1 km, suy ra tu dinh muc lit/100km.

    `fuel_norm` la lit tren 100 km — quy uoc nganh, va cac gia tri that (18, 26,
    35) chi hop ly o don vi do; 26 lit cho 1 km la vo ly. Nen phai CHIA CHO 100
    truoc roi moi nhan gia dau, de ket qua van la tien tren 1 km.
    """
    return round(float(fuel_norm_lit_100km) / 100.0 * GIA_DAU_VND_LIT)


# (ma, ten, tai trong kg, m3, pallet, dinh muc lit/100km, van toc TB,
#  phu cap tai xe/chuyen, phi cau duong/chuyen, phi bai/chuyen, cuoc d/kg,
#  chi phi bao duong/thang)
LOAI_XE = [
    ("DEMO-VT-TRACTOR40", "Đầu kéo 40'", 30000, 67.0, 24, 35, 45,
     700000, 420000, 250000, 1200, 1200000),
    ("DEMO-VT-TRACTOR20", "Đầu kéo 20'", 24000, 33.0, 18, 30, 48,
     600000, 320000, 220000, 1350, 950000),
    ("DEMO-VT-TRUCK15", "Xe tải thùng 15 tấn", 15000, 60.0, 18, 22, 50,
     500000, 260000, 180000, 1500, 600000),
    ("DEMO-VT-TRUCK10", "Xe tải thùng 10 tấn", 10000, 45.0, 12, 18, 55,
     420000, 200000, 150000, 1750, 450000),
    # Xe lanh an dau hon vi may lanh chay lien tuc, va cuoc cung cao hon.
    ("DEMO-VT-REEFER5", "Xe lạnh 5 tấn", 5000, 22.0, 8, 20, 50,
     450000, 180000, 320000, 3200, 900000),
]


def _cong_thuc(ma_loai, ten_loai, dau_km, tai_xe, cau_duong, bai, cuoc):
    """Mot cong thuc gia thanh day du cho mot loai xe.

    `components` la chuoi de HIEN RA; `terms` moi la cho tinh that. Hai cho phai
    khop nhau — lech thi man hinh noi mot dang ma phep tinh ra mot dang khac.
    """
    return {
        "currency": "VND",
        "components": {
            "fuel": str(dau_km),
            "driver": str(tai_xe),
            "toll": str(cau_duong),
            "warehouse": str(bai),
            "freight_rate": str(cuoc),
        },
        "terms": [
            {"key": "fuel", "label": "Chi phí xăng dầu /km", "operator": "add",
             "factor": "per_km", "kind": "cost", "rate": dau_km, "builtin": True},
            {"key": "driver", "label": "Phụ cấp chuyến tài xế", "operator": "add",
             "factor": "per_trip", "kind": "cost", "rate": tai_xe, "builtin": True},
            {"key": "toll", "label": "Phí cầu đường / BOT", "operator": "add",
             "factor": "per_trip", "kind": "cost", "rate": cau_duong, "builtin": True},
            {"key": "wh", "label": "Phí bãi & lưu kho", "operator": "add",
             "factor": "per_trip", "kind": "cost", "rate": bai, "builtin": True},
            # `rate` la CUOC THU cua khach, khong phai mot khoan chi. Danh dau
            # `kind: revenue` de phep tinh khong cong no vao gia thanh.
            {"key": "rate", "label": "Cước phí vận chuyển /kg", "operator": "add",
             "factor": "per_kg", "kind": "revenue", "rate": cuoc, "builtin": True},
        ],
    }


def nap_loai_xe(db):
    for (ma, ten, tai, m3, pallet, dinh_muc, toc_do,
         tai_xe, cau_duong, bai, cuoc, bao_duong) in LOAI_XE:
        dau_km = chi_phi_dau_moi_km(dinh_muc)
        db.merge(VehicleType(
            id=ma, name=ten, icon="fa-truck",
            max_weight=tai, volume_capacity_m3=m3, pallet_capacity=pallet,
            fuel_norm=dinh_muc, avg_speed_kmh=toc_do,
            # `base_rate` la don gia TREN 1 KM, dung bang chi phi xang dau /km.
            base_rate=dau_km,
            maint_cost=bao_duong, fuel_type="Diesel",
            notes="Dữ liệu mẫu — chi phí xăng dầu suy ra từ %d lít/100km × %s đ/lít"
                  % (dinh_muc, "{:,}".format(GIA_DAU_VND_LIT).replace(",", ".")),
        ))
        db.merge(CostFormula(
            id="DEMO-CF-%s" % ma.replace("DEMO-VT-", ""),
            name="%s — Tiêu chuẩn" % ten,
            formula_expression=json.dumps(
                _cong_thuc(ma, ten, dau_km, tai_xe, cau_duong, bai, cuoc),
                ensure_ascii=False),
        ))
    db.flush()
    return len(LOAI_XE)


# (ma dia diem, ten, loai, dia chi, suc chua)
DIA_DIEM = [
    ("DEMO-LOC-SONGTHAN", "Bãi Sóng Thần", "Warehouse",
     "KCN Sóng Thần, Dĩ An, Bình Dương", 18000),
    ("DEMO-LOC-CAIMEP", "Cảng Cái Mép", "Port",
     "Thị xã Phú Mỹ, Bà Rịa – Vũng Tàu", 60000),
    ("DEMO-LOC-AMATA", "KCN Amata", "Warehouse",
     "Phường Long Bình, Biên Hòa, Đồng Nai", 15000),
    ("DEMO-LOC-LONGAN", "Kho Long An", "Warehouse",
     "Bến Lức, Long An", 22000),
    ("DEMO-LOC-VANHDAI3", "Vành đai 3", "Waypoint",
     "Nút giao Vành đai 3, TP. Thủ Đức", 0),
]

# (ma tuyen, ten, cac chang [(tu, den, km)])
TUYEN = [
    ("DEMO-RT-SONGTHAN-CATLAI", "Sóng Thần → Cảng Cát Lái", [
        ("Bãi Sóng Thần", "Cảng Cát Lái, TP. Thủ Đức", 31.2),
    ]),
    ("DEMO-RT-LONGAN-CAIMEP", "Long An → Cảng Cái Mép", [
        ("Kho Long An", "Vành đai 3", 34.5),
        ("Vành đai 3", "Cảng Cát Lái, TP. Thủ Đức", 26.5),
        ("Cảng Cát Lái, TP. Thủ Đức", "Cảng Cái Mép", 51.0),
    ]),
    ("DEMO-RT-CATLAI-AMATA", "Cảng Cát Lái → KCN Amata", [
        ("Cảng Cát Lái, TP. Thủ Đức", "Vành đai 3", 12.6),
        ("Vành đai 3", "KCN Amata", 25.8),
    ]),
    ("DEMO-RT-VSIP2A-CAIMEP", "VSIP II-A → Cảng Cái Mép", [
        ("Kho VSIP II-A, Bình Dương", "Vành đai 3", 18.2),
        ("Vành đai 3", "Cảng Cái Mép", 78.3),
    ]),
]


def nap_dia_diem_va_tuyen(db):
    for ma, ten, loai, dia_chi, suc_chua in DIA_DIEM:
        db.merge(Location(id=ma, name=ten, type=loai, address=dia_chi, capacity=suc_chua))

    for ma, ten, chang in TUYEN:
        # Tong km la TONG CAC CHANG, khong phai mot so nhap tay: nhap tay thi
        # tong va cac chang lech nhau, va ETA tinh ra sai ma khong ai thay.
        tong = round(sum(c[2] for c in chang), 1)
        db.merge(Route(
            id=ma, name=ten, distance_km=tong,
            segments_json=json.dumps(
                [{"from": a, "to": b, "dist_km": km} for a, b, km in chang],
                ensure_ascii=False),
        ))
    db.flush()
    return len(TUYEN)


# (bien so, hang, ma loai xe, bai, ma bai)
XE = [
    ("DEMO-51C-412.09", "Hyundai", "DEMO-VT-TRACTOR40", "Bãi Sóng Thần", "DEMO-LOC-SONGTHAN"),
    ("DEMO-51C-556.12", "Hyundai", "DEMO-VT-TRACTOR40", "Bãi Sóng Thần", "DEMO-LOC-SONGTHAN"),
    ("DEMO-51C-301.88", "Hino", "DEMO-VT-TRACTOR20", "Kho VSIP II-A, Bình Dương", "DEMO-LOC-VSIP2A"),
    ("DEMO-51C-129.03", "Hino", "DEMO-VT-TRACTOR20", "Kho Long An", "DEMO-LOC-LONGAN"),
    ("DEMO-61H-208.44", "Isuzu", "DEMO-VT-TRUCK15", "Kho VSIP II-A, Bình Dương", "DEMO-LOC-VSIP2A"),
    ("DEMO-61H-330.17", "Isuzu", "DEMO-VT-TRUCK10", "Bãi Sóng Thần", "DEMO-LOC-SONGTHAN"),
    ("DEMO-50H-771.25", "Thaco", "DEMO-VT-REEFER5", "Kho Long An", "DEMO-LOC-LONGAN"),
]


def nap_xe(db):
    # Hai xe co san chua duoc gan bai. Khong gan thi bo loc "Bai" o man lich xe
    # chi co dung mot lua chon that va mot nhom "chua gan bai" — nhin nhu bo loc
    # hong, trong khi no dang noi that.
    for bien, ma_bai, ten_bai in (
        ("DEMO-51C-268.89", "DEMO-LOC-VSIP2A", "Kho VSIP II-A, Bình Dương"),
        ("DEMO-61H-112.34", "DEMO-LOC-SONGTHAN", "Bãi Sóng Thần"),
    ):
        xe_co = db.get(Vehicle, bien)
        if xe_co is not None and not xe_co.depot_code:
            xe_co.depot = ten_bai
            xe_co.depot_code = ma_bai

    loai = {x[0]: x for x in LOAI_XE}
    for i, (bien, hang, ma_loai, bai, ma_bai) in enumerate(XE, start=1):
        L = loai[ma_loai]
        db.merge(Vehicle(
            id=bien, brand=hang, type=ma_loai,
            weight_capacity=L[2], volume_capacity_m3=L[3], pallet_capacity=L[4],
            fuel_norm=L[5], avg_speed_kmh=L[6],
            min_speed_kmh=25, max_speed_kmh=80,
            status="active",
            depot=bai, depot_code=ma_bai,
            # Ba moc giay to phai co GIA TRI KHAC NHAU: man danh muc xe canh bao
            # theo han sap het, va de tat ca cung mot ngay thi khong phan biet
            # duoc xe nao gap hon.
            inspection_exp="2027-%02d-15" % (((i * 2) % 12) + 1),
            insurance_date="2027-%02d-01" % (((i * 3) % 12) + 1),
            maintenance_date="2026-%02d-20" % (((i + 8) % 12) + 1),
            engine_no="ENG-DEMO-%03d" % i,
            chassis_no="CHS-DEMO-%03d" % i,
        ))
    db.flush()
    return len(XE)


# (ma, ten, dien thoai, dia chi)
KHACH = [
    ("DEMO-CUS-NIDEC", "Nidec Việt Nam", "02838123456",
     "KCN Cao, TP. Thủ Đức, TP.HCM"),
    ("DEMO-CUS-COLGATE", "Colgate Palmolive VN", "02838234567",
     "KCN Mỹ Phước, Bến Cát, Bình Dương"),
    ("DEMO-CUS-POUYUEN", "Pou Yuen Việt Nam", "02838345678",
     "Quận Bình Tân, TP.HCM"),
    ("DEMO-CUS-UNILEVER", "Unilever Việt Nam", "02838456789",
     "KCN Tây Bắc Củ Chi, TP.HCM"),
]

# (ma, ten, hang bang, dien thoai, vai tro)
TAI_XE = [
    ("DEMO-DRV-004", "Phạm Hữu Long", "FC", "0901234004", "Lái xe chính"),
    ("DEMO-DRV-005", "Ngô Hữu Phúc", "FC", "0901234005", "Lái xe chính"),
    ("DEMO-DRV-006", "Huỳnh Văn Kiên", "C", "0901234006", "Lái xe chính"),
    ("DEMO-DRV-007", "Bùi Văn Nam", "B2", "0901234007", "Phụ xe"),
]


def nap_khach_va_tai_xe(db):
    for ma, ten, dt, dia_chi in KHACH:
        db.merge(Customer(id=ma, name=ten, phone=dt, address=dia_chi))
    for ma, ten, bang, dt, vai_tro in TAI_XE:
        db.merge(Driver(
            id=ma, name=ten, license_type=bang, phone=dt,
            role=vai_tro, status="active",
        ))
    db.flush()
    return len(KHACH), len(TAI_XE)


def nap_danh_muc(db):
    """Nap ca danh muc mo rong. Tra ve so dong de goi ben ngoai bao lai."""
    so_loai = nap_loai_xe(db)
    so_tuyen = nap_dia_diem_va_tuyen(db)
    so_xe = nap_xe(db)
    so_khach, so_tai_xe = nap_khach_va_tai_xe(db)
    return {
        "loai_xe": so_loai,
        "tuyen": so_tuyen,
        "xe": so_xe,
        "khach_hang": so_khach,
        "tai_xe": so_tai_xe,
    }
