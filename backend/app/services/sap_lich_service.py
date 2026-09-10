"""Bang sap lich xe va tai xe — mot lan doc cho ca man hinh.

Man "Sap lich xe va tai xe" dung theo ban mau
`nhap_UI__duan/shift-schedule-v5-staff-vehicle.html`. Ban mau co hai luoi cung
mot ngon ngu (nguoi va xe), mot dai DO PHU tren dau moi luoi, va mot cot phai
liet ke VIEC CAN LAM. Tep nay tra ve tat ca trong MOT loi goi.

VI SAO MOT LOI GOI, KHONG PHAI NAM. Ba khoi tren man phai NHAT QUAN voi nhau:
o do cua luoi nguoi ("thieu 2 nguoi ca dem T2") va o do cua luoi xe ("xe nay co
Trip dem T2 ma khong co to lai") phai la HAI MAT CUA MOT SU THAT. Goi nam lan
thi nam lan doc o nam thoi diem khac nhau, va man hinh tu mau thuan: ben nay
bao thieu, ben kia bao du. Tinh mot lan tu mot anh chup cua co so du lieu thi
khong the lech.

BA TRANG THAI KHONG DUOC LAN NHAU, va day la phan de sai nhat:

  · `lock` — ca DA CO Trip tu man Dieu phoi. Sua o day la sua sau lung Dieu
    phoi, nen man nay chi doc.
  · `conf` — xe CO Trip ma KHONG co ai trong ca. Day la loi nang nhat cua ca
    man: Dieu phoi da hua mot chuyen ma khong ai lai. Ban mau ve no do, va
    dung vay.
  · `need` — mot ca CON THIEU nguoi so voi so xe phai chay. Khac `conf`: `conf`
    la mot xe cu the dang treo, `need` la mot con so con thieu.

"CAN BAO NHIEU NGUOI" khong bia ra. No la SO CHUYEN co gio xuat ben roi vao
khung ca do — moi xe chay thi phai co it nhat mot nguoi lai. Dat mot con so co
dinh (ban mau ghi "S 12 · C 12 · D 8") thi con so do dung cho mot bai va sai
cho muoi bon bai con lai.
"""

import datetime as dt

from sqlalchemy import func, or_

from models import (
    AuditLog,
    Driver,
    DriverShiftAssignment,
    ResourceAssignment,
    TransportTrip,
    Vehicle,
    VehicleMaintenanceRequest,
    VehicleType,
)
from services.errors import DomainError


# Viet Nam khong co gio mua he, nen mot do lech co dinh la dung — khong can
# thu vien mui gio. Ca ba khung ca duoi day la gio DIA PHUONG.
LECH_GIO = dt.timedelta(hours=7)

# Ba ca, va khung gio dia phuong cua tung ca. `dem` vat qua nua dem nen gio ket
# thuc nho hon gio bat dau — cac phep tinh duoi day xu ly rieng truong hop do.
CA = (
    {"ma": "morning", "ten": "Sáng", "ky_hieu": "S", "tu": 6, "den": 14},
    {"ma": "afternoon", "ten": "Chiều", "ky_hieu": "C", "tu": 14, "den": 22},
    {"ma": "night", "ten": "Đêm", "ky_hieu": "Đ", "tu": 22, "den": 6},
)
MA_CA = tuple(c["ma"] for c in CA)
# Chu cai trong mau xoay (`SSCCDD--`) ung voi ca nao. `-` la nghi.
CHU_MAU = {"S": "morning", "C": "afternoon", "D": "night", "Đ": "night"}

TEN_THU = ("Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN")

# Nghi phep va nghi om deu la "khong the xep ca", nhung phai phan biet voi `off`
# (nghi theo mau xoay): mot nguoi nghi phep thi KHONG duoc xep bu, con nguoi
# nghi theo mau thi xep bu duoc khi thieu nguoi.
NGHI_PHEP = ("leave", "sick")

# Tran gio lam mot tuan. Vuot tran khong phai loi cua he thong — no la mot viec
# can nguoi duyet, nen man hinh chi danh dau.
TRAN_GIO_TUAN = 48

# Trip da xong hoac da doi soat thi khong con la viec phai xep.
TRIP_DA_XONG = ("completed", "settled")
TRIP_BO = ("cancelled",)


def _ngay(gia_tri, ten="ngày"):
    if isinstance(gia_tri, dt.date) and not isinstance(gia_tri, dt.datetime):
        return gia_tri
    try:
        return dt.date.fromisoformat(str(gia_tri)[:10])
    except ValueError:
        raise DomainError("INVALID_DATE", "Không đọc được %s: %s" % (ten, gia_tri), 422)


def _utc(ngay_dia_phuong, gio):
    """Mot moc gio DIA PHUONG doi ve UTC khong mui gio.

    Toan bo cot thoi gian trong du an luu UTC. Bo qua buoc nay thi ca sang
    06:00 gio Viet Nam bi tim o 06:00 UTC — tuc 13:00 gio dia phuong, giua ca
    chieu — va man hinh bao ca sang trong tron.
    """
    return dt.datetime.combine(ngay_dia_phuong, dt.time(0)) + dt.timedelta(hours=gio) - LECH_GIO


def khung_ca(ngay_dia_phuong, ma_ca):
    """Khoang [bat dau, ket thuc) theo UTC cua mot ca trong mot ngay."""
    ca = next(c for c in CA if c["ma"] == ma_ca)
    tu = _utc(ngay_dia_phuong, ca["tu"])
    den = _utc(ngay_dia_phuong, ca["den"])
    if ca["den"] <= ca["tu"]:  # ca dem vat qua nua dem
        den += dt.timedelta(days=1)
    return tu, den


def _bo_mui(gia_tri):
    """Moc thoi gian ve UTC khong mui gio, de so sanh duoc voi nhau.

    PostgreSQL tra ve moc CO mui gio con cac moc tinh trong tep nay la naive.
    So hai loai voi nhau thi Python nem TypeError — loi nay da lam vo ca mot
    duong ghi su kien o cho khac trong du an.
    """
    if gia_tri is None:
        return None
    if gia_tri.tzinfo is None:
        return gia_tri
    return gia_tri.astimezone(dt.timezone.utc).replace(tzinfo=None)


def _giao_nhau(a1, a2, b1, b2):
    return a1 is not None and a2 is not None and a1 < b2 and a2 > b1


def _chu_cai_dau(ten):
    phan = [x for x in str(ten or "").split() if x]
    return "".join(x[0] for x in phan[-2:]).upper() or "?"


def _ma_ca_cua(row):
    """Ca cua mot ban ghi lich, suy tu GIO neu cot `shift_type` khong noi ro.

    Ban ghi cu trong bo du lieu co `shift_type='custom'`, va bo chung thi lich
    da xep bi mat khoi man hinh — nguoi dung tuong minh chua xep gi.
    """
    if row.shift_type in MA_CA:
        return row.shift_type
    bat_dau = _bo_mui(row.shift_start)
    if bat_dau is None:
        return None
    gio = (bat_dau + LECH_GIO).hour
    if 6 <= gio < 14:
        return "morning"
    if 14 <= gio < 22:
        return "afternoon"
    return "night"


def _ngay_cua(row):
    """Ngay DIA PHUONG mot ca thuoc ve, tinh theo gio BAT DAU.

    Ca dem 22:00–06:00 thuoc ngay bat dau, khong phai ngay ket thuc — nguoi
    truc goi no la "ca dem thu Hai" du phan lon gio nam sang thu Ba.
    """
    bat_dau = _bo_mui(row.shift_start)
    return None if bat_dau is None else (bat_dau + LECH_GIO).date()


def _gio_lam(row):
    tu, den = _bo_mui(row.shift_start), _bo_mui(row.shift_end)
    if tu is None or den is None or den <= tu:
        return 0.0
    return round((den - tu).total_seconds() / 3600.0, 2)


def ten_ca(ma_ca):
    """Ten doc duoc cua mot ca. Ma la thi tra ve chinh no chu khong nem loi."""
    return next((c["ten"] for c in CA if c["ma"] == ma_ca), str(ma_ca or "?"))


def ket_thuc_hanh_trinh(trip, ket_thuc_phan_cong=None):
    """Moc xe va to lai duoc THA: muon nhat trong gio ve, gio toi va phan cong."""
    ung_vien = [_bo_mui(trip.planned_return_at), _bo_mui(trip.planned_arrival_at),
                _bo_mui(ket_thuc_phan_cong)]
    ung_vien = [x for x in ung_vien if x is not None]
    return max(ung_vien) if ung_vien else None


def _trang_thai_trip(trip):
    if trip.status in TRIP_DA_XONG:
        return "done"
    if trip.status == "in_transit":
        return "run"
    return "trip"


def bang_sap_lich(db, start, so_ngay=7, depot=None, team=None):
    """Toan bo du lieu cua man xep ca cho mot khoang ngay.

    `depot` va `team` la bo loc — o quy mo hang tram tai xe thi khong loc la
    khong dung duoc. `team` de rong nhung `depot` co gia tri thi tra ve ca bai,
    gom ca nhom "chua phan tổ".
    """
    ngay_dau = _ngay(start, "ngày bắt đầu")
    so_ngay = max(1, min(int(so_ngay or 7), 31))
    cac_ngay = [ngay_dau + dt.timedelta(days=i) for i in range(so_ngay)]
    tu_utc = _utc(ngay_dau, 0)
    # Cong them mot ngay: ca dem cua ngay cuoi keo sang 06:00 ngay ke tiep.
    den_utc = _utc(cac_ngay[-1] + dt.timedelta(days=1), 6)
    hom_nay = (dt.datetime.utcnow() + LECH_GIO).date()

    # ---- danh sach bai va to, dung cho dai dieu huong o dau man ----
    bai, to = _bai_va_to(db)

    # ---- nhan su va xe trong pham vi loc ----
    q_tx = db.query(Driver)
    if depot:
        q_tx = q_tx.filter(Driver.depot_code == depot)
    if team:
        q_tx = q_tx.filter(Driver.team_code == team)
    tai_xe = q_tx.order_by(Driver.name).all()

    q_xe = db.query(Vehicle)
    if depot:
        q_xe = q_xe.filter(Vehicle.depot_code == depot)
    xe = q_xe.order_by(Vehicle.id).all()
    depot_cua_xe = dict(db.query(Vehicle.id, Vehicle.depot_code).all())
    # `vehicles.type` giu MA loai xe (`DEMO-VT-REEFER5`), khong phai ten. Hien
    # ma tho tren luoi thi nguoi dieu do khong doc duoc xe do la loai gi — cung
    # loi da phai sua mot lan o man Dieu phoi.
    ten_loai = {}
    for t in db.query(VehicleType).all():
        ten_loai[t.id] = t.name
        ten_loai[t.name] = t.name

    # ---- lich da xep ----
    lich = db.query(DriverShiftAssignment).filter(
        DriverShiftAssignment.status != "cancelled",
        DriverShiftAssignment.shift_start < den_utc,
        DriverShiftAssignment.shift_end > tu_utc,
    ).all()

    # ---- chuyen va bao duong ----
    # Mot chuyen GIU xe va to lai tu luc xuat ben den luc XE VE BAI, khong phai
    # den luc toi noi giao. Chuyen 3 ngay di 07:00 ngay 1, giao ngay 2, ve
    # 15:00 ngay 3: ca ba ngay deu phai khoa. Ban truoc chi doc
    # `planned_arrival_at` nen chang ve (va ca thoi gian giao/do hang) khong
    # khoa — xe hien "ranh" trong khi dang tren duong ve. Ket thuc lay MUON
    # NHAT trong: gio ve ke hoach, gio toi ke hoach, va `assignment_end` cua
    # phan cong dang mo (Dieu phoi da tinh no = max cua ca ba, xem
    # `tms_dispatch_service.dispatch_trip`).
    chuyen = db.query(TransportTrip).filter(
        TransportTrip.status.notin_(TRIP_BO),
        TransportTrip.planned_departure_at < den_utc,
        or_(
            TransportTrip.planned_return_at > tu_utc,
            TransportTrip.planned_arrival_at > tu_utc,
        ),
    ).all()
    ket_thuc_phan_cong = {}
    if chuyen:
        for ma_trip, ket_thuc in db.query(ResourceAssignment.trip_id, ResourceAssignment.assignment_end).filter(
                ResourceAssignment.status == "active",
                ResourceAssignment.trip_id.in_([t.id for t in chuyen])).all():
            ket_thuc_phan_cong[ma_trip] = _bo_mui(ket_thuc)
    bao_duong = db.query(VehicleMaintenanceRequest).filter(
        VehicleMaintenanceRequest.status.in_(("requested", "approved", "in_progress")),
        VehicleMaintenanceRequest.planned_start < den_utc,
        VehicleMaintenanceRequest.planned_end > tu_utc,
    ).all()

    # ---- xep lich, chuyen va bao duong vao tung o (ngay, ca) ----
    o_lich = {}      # (driver_id, ngay, ca) -> ban ghi lich
    o_lich_xe = {}   # (vehicle_id, ngay, ca) -> [ban ghi lich]
    for row in lich:
        ngay, ma = _ngay_cua(row), _ma_ca_cua(row)
        if ngay is None or ma is None:
            continue
        o_lich.setdefault((row.driver_id, ngay, ma), row)
        if row.vehicle_id and row.availability_kind == "work":
            o_lich_xe.setdefault((row.vehicle_id, ngay, ma), []).append(row)

    o_chuyen = {}    # (vehicle_id, ngay, ca) -> chuyen
    o_chuyen_nguoi = {}  # (driver_id, ngay, ca) -> chuyen
    can_theo_bai = {}    # (depot_code, ngay, ca) -> so xe phai chay
    can_theo_ca = {} # (ngay, ca) -> so xe phai chay
    for trip in chuyen:
        di = _bo_mui(trip.planned_departure_at)
        den = ket_thuc_hanh_trinh(trip, ket_thuc_phan_cong.get(trip.id)) or di
        if di is None:
            continue
        for ngay in cac_ngay:
            for ma in MA_CA:
                a, b = khung_ca(ngay, ma)
                if not _giao_nhau(di, den, a, b):
                    continue
                # "Can bao nhieu nguoi" dem theo GIO XUAT BEN, khong theo toan
                # bo hanh trinh: mot chuyen hai ngay chi can mot nguoi nhan xe
                # o ca xuat ben, khong phai moi ca no di qua.
                if a <= di < b and trip.status not in TRIP_DA_XONG:
                    can_theo_ca[(ngay, ma)] = can_theo_ca.get((ngay, ma), 0) + 1
                    ma_bai_chuyen = depot_cua_xe.get(trip.vehicle_id)
                    khoa_bai = (ma_bai_chuyen, ngay, ma)
                    can_theo_bai[khoa_bai] = can_theo_bai.get(khoa_bai, 0) + 1
                if trip.vehicle_id:
                    o_chuyen.setdefault((trip.vehicle_id, ngay, ma), trip)
                # Nguoi lai va lai phu cua chuyen bi KHOA o o nay. Suy tu chuyen
                # chu khong doc `driver_shift_assignments.trip_id`: khong duong
                # nao trong he thong dien cot do, nen doc no thi trang thai
                # "khoa" khong bao gio xuat hien va chu giai cua luoi noi doi.
                # Suy tu chuyen cung lam luoi NGUOI va luoi XE thanh hai mat cua
                # mot su that — cung mot chuyen sinh ra o khoa ben nay va o Trip
                # ben kia.
                for ma_nguoi in (trip.driver_id, trip.co_driver_id):
                    if ma_nguoi:
                        o_chuyen_nguoi.setdefault((ma_nguoi, ngay, ma), trip)

    o_bao_duong = {}
    for bd in bao_duong:
        a0, b0 = _bo_mui(bd.planned_start), _bo_mui(bd.planned_end)
        for ngay in cac_ngay:
            for ma in MA_CA:
                a, b = khung_ca(ngay, ma)
                if _giao_nhau(a0, b0, a, b) and bd.vehicle_id:
                    o_bao_duong.setdefault((bd.vehicle_id, ngay, ma), bd)

    # ---- do phu nhan su: bao nhieu nguoi TRUC tung ca ----
    truc_theo_ca = {}
    for (ma_tx, ngay, ma) in o_lich:
        row = o_lich[(ma_tx, ngay, ma)]
        if row.availability_kind == "work":
            truc_theo_ca[(ngay, ma)] = truc_theo_ca.get((ngay, ma), 0) + 1
    # Nguoi dang chay mot chuyen thi DANG TRUC, du chua co ban ghi ca nao. Bo
    # ho ra thi do phu bao thieu nguoi trong khi ho dang tren duong — va con so
    # "thieu" do lai sinh ra nhung o "can xep" do o dung nhung ca da co nguoi.
    ma_trong_pham_vi = {d.id for d in tai_xe}
    for (ma_tx, ngay, ma) in o_chuyen_nguoi:
        if ma_tx not in ma_trong_pham_vi:
            continue
        row = o_lich.get((ma_tx, ngay, ma))
        if row is None or row.availability_kind != "work":
            truc_theo_ca[(ngay, ma)] = truc_theo_ca.get((ngay, ma), 0) + 1

    # ---- luoi nhan su ----
    nhan_su = []
    for d in tai_xe:
        mau = (d.rotation_pattern or "").upper()
        cac_ngay_ra = []
        tong_gio = 0.0
        for ngay in cac_ngay:
            cac_o = []
            for ma in MA_CA:
                row = o_lich.get((d.id, ngay, ma))
                chuyen_o_day = o_chuyen_nguoi.get((d.id, ngay, ma))
                if row is not None:
                    if row.availability_kind in NGHI_PHEP:
                        trang_thai = "leave"
                    elif row.availability_kind in ("off", "unavailable"):
                        trang_thai = "off"
                    elif row.trip_id or chuyen_o_day is not None:
                        trang_thai = "lock"
                    else:
                        trang_thai = "on"
                    if row.availability_kind == "work":
                        tong_gio += _gio_lam(row)
                    cac_o.append({
                        "ca": ma, "trang_thai": trang_thai, "shift_id": row.id,
                        "version": row.version,
                        "trip_id": row.trip_id or (chuyen_o_day.id if chuyen_o_day is not None else None),
                        "vehicle_id": row.vehicle_id, "ghi_chu": row.notes,
                        "khac_mau": bool(mau) and _khac_mau(mau, ngay, ma),
                        "gio": _gio_lam(row),
                    })
                    continue
                # Chua co ban ghi ca. Bon kha nang, theo thu tu uu tien:
                # nguoi da co chuyen (khoa), mau xoay noi la nghi, ca dang thieu
                # nguoi, hoac o trong binh thuong.
                if chuyen_o_day is not None:
                    # Dieu phoi gan tai xe vao chuyen TRUOC khi co ban ghi ca,
                    # nen o nay nhin nhu trong trong khi nguoi do da co viec.
                    # Xep them ai vao day la xep trung nguoi.
                    cac_o.append({
                        "ca": ma, "trang_thai": "lock", "shift_id": None, "version": None,
                        "trip_id": chuyen_o_day.id, "vehicle_id": chuyen_o_day.vehicle_id,
                        "ghi_chu": None, "khac_mau": False, "gio": 0.0,
                    })
                    continue
                thieu = max(0, can_theo_ca.get((ngay, ma), 0) - truc_theo_ca.get((ngay, ma), 0))
                trang_thai = "free"
                if mau and _mau_noi_nghi(mau, ngay):
                    trang_thai = "off"
                elif thieu > 0:
                    trang_thai = "need"
                cac_o.append({
                    "ca": ma, "trang_thai": trang_thai, "shift_id": None, "version": None,
                    "trip_id": None, "vehicle_id": None, "ghi_chu": None,
                    "khac_mau": False, "gio": 0.0, "thieu": thieu,
                })
            cac_ngay_ra.append({"ngay": ngay.isoformat(), "cac_o": cac_o})
        nhan_su.append({
            "driver_id": d.id, "ten": d.name, "chu_cai": _chu_cai_dau(d.name),
            "vai_tro": d.role, "hang_bang": d.license_type,
            "depot_code": d.depot_code, "team_code": d.team_code,
            "mau_xoay": d.rotation_pattern,
            "xe_mac_dinh": d.assigned_vehicle if d.assigned_vehicle and d.assigned_vehicle != "Chưa gán" else None,
            "gio_tuan": round(tong_gio, 1),
            "vuot_gio": tong_gio > TRAN_GIO_TUAN,
            "cac_ngay": cac_ngay_ra,
        })

    # ---- luoi xe ----
    # Tra ten mot lan cho moi tai xe co ten trong luoi xe: nguoi co ban ghi ca
    # gan voi xe, va nguoi ghi thang tren chuyen.
    bang_ten = _bang_ten(db, (
        [r.driver_id for ds in o_lich_xe.values() for r in ds]
        + [t.driver_id for t in chuyen] + [t.co_driver_id for t in chuyen]
    ))
    danh_sach_xe = []
    for v in xe:
        cac_ngay_ra = []
        ngay_ranh = 0
        for ngay in cac_ngay:
            cac_o = []
            co_viec = False
            for ma in MA_CA:
                trip = o_chuyen.get((v.id, ngay, ma))
                bd = o_bao_duong.get((v.id, ngay, ma))
                to_lai = o_lich_xe.get((v.id, ngay, ma), [])
                nhan = [_chu_cai_dau(_ten_tai_xe(bang_ten, r.driver_id)) for r in to_lai]
                if trip is not None:
                    co_viec = True
                    # `conf` la loi nang nhat cua man: Dieu phoi da hua mot
                    # chuyen ma khong ai lai. Chuyen da xong thi khong con la
                    # loi — khong the doi to lai cho mot viec da lam roi.
                    thieu_to_lai = not to_lai and not (trip.driver_id or trip.co_driver_id)
                    trang_thai = "conf" if (thieu_to_lai and trip.status not in TRIP_DA_XONG) else _trang_thai_trip(trip)
                    cac_o.append({
                        "ca": ma, "trang_thai": trang_thai, "trip_id": trip.id,
                        "nhan": trip.id, "to_lai": nhan or _to_lai_cua_trip(bang_ten, trip),
                        "trip_status": trip.status,
                    })
                    continue
                if bd is not None:
                    co_viec = True
                    cac_o.append({
                        "ca": ma, "trang_thai": "mt", "trip_id": None,
                        "nhan": bd.description or bd.request_no, "to_lai": [],
                        "maintenance_request_id": bd.id,
                    })
                    continue
                if to_lai:
                    cac_o.append({"ca": ma, "trang_thai": "ready", "trip_id": None,
                                  "nhan": "sẵn sàng", "to_lai": nhan})
                    continue
                cac_o.append({"ca": ma, "trang_thai": "free", "trip_id": None,
                              "nhan": "", "to_lai": []})
            if not co_viec:
                ngay_ranh += 1
            cac_ngay_ra.append({"ngay": ngay.isoformat(), "cac_o": cac_o})
        danh_sach_xe.append({
            "vehicle_id": v.id, "loai": ten_loai.get(v.type) or v.type,
            "ma_loai": v.type, "depot_code": v.depot_code,
            "depot": v.depot, "trang_thai_xe": v.status,
            "ngay_bao_duong": v.maintenance_date, "han_dang_kiem": v.inspection_exp or v.inspection_date,
            "so_km": v.odometer_km, "moc_bao_duong_km": v.next_service_odometer_km,
            # `None` khi CHUA KHAI so km — khac han voi 0. Giao dien phai noi
            # "chua khai so km" chu khong ve mot thanh 0%, vi thanh do doc ra
            # nhu xe den han bao duong gap.
            "con_km_bao_duong": (
                round(v.next_service_odometer_km - v.odometer_km, 1)
                if v.odometer_km is not None and v.next_service_odometer_km is not None
                else None
            ),
            "ngay_ranh": ngay_ranh,
            "cac_ngay": cac_ngay_ra,
        })

    # ---- dai do phu ----
    do_phu = []
    for ngay in cac_ngay:
        muc = {"ngay": ngay.isoformat(), "thu": TEN_THU[ngay.weekday()],
               "hom_nay": ngay == hom_nay, "cac_ca": []}
        for ma in MA_CA:
            can = can_theo_ca.get((ngay, ma), 0)
            truc = truc_theo_ca.get((ngay, ma), 0)
            xe_san_sang = sum(
                1 for item in danh_sach_xe
                for d in item["cac_ngay"] if d["ngay"] == ngay.isoformat()
                for o in d["cac_o"] if o["ca"] == ma and o["trang_thai"] in ("ready", "trip", "run", "done")
            )
            muc["cac_ca"].append({
                "ca": ma, "truc": truc, "can": can, "thieu": max(0, can - truc),
                "xe_san_sang": xe_san_sang,
            })
        do_phu.append(muc)

    return {
        "pham_vi": {
            "tu": ngay_dau.isoformat(),
            "den": cac_ngay[-1].isoformat(),
            "so_ngay": so_ngay,
            "depot_code": depot,
            "team_code": team,
            "cac_ngay": [
                {"ngay": n.isoformat(), "thu": TEN_THU[n.weekday()], "hom_nay": n == hom_nay}
                for n in cac_ngay
            ],
        },
        "cac_ca": [dict(c) for c in CA],
        "cac_bai": bai,
        "cac_to": to,
        "nhan_su": nhan_su,
        "xe": danh_sach_xe,
        "do_phu": do_phu,
        "do_phu_theo_bai": _do_phu_theo_bai(bai, cac_ngay, nhan_su, danh_sach_xe, can_theo_bai),
        "viec_can_lam": _viec_can_lam(nhan_su, danh_sach_xe, do_phu),
    }


def _bang_ten(db, ma_can):
    """Bang tra ten tai xe, doc MOT LAN cho ca man hinh.

    Luoi xe can ten cho tung o — bay ngay nhan ba ca nhan hang tram xe la hang
    nghin lan tra. Doc tung lan thi mot man hinh mo ra thanh hang nghin cau
    truy van.

    Bang nay la CUC BO cua moi loi goi, khong phai bien cap module: mot bo dem
    song lau hon mot yeu cau se tra ve ten cu sau khi nguoi dung doi ten tai
    xe, va no lon dan khong gioi han theo so tai xe da tung xuat hien.
    """
    ma_can = {m for m in ma_can if m}
    if not ma_can:
        return {}
    return {
        d.id: d.name
        for d in db.query(Driver).filter(Driver.id.in_(ma_can)).all()
    }


def _ten_tai_xe(bang_ten, ma):
    if ma is None:
        return None
    return bang_ten.get(ma) or ma


def _to_lai_cua_trip(bang_ten, trip):
    """To lai ghi thang tren chuyen, dung khi chua co ban ghi lich nao.

    Dieu phoi gan tai xe vao `transport_trips.driver_id` truoc khi co ban ghi
    ca. Bo qua thi mot chuyen da co nguoi lai bi bao la thieu to lai.
    """
    ra = []
    for ma in (trip.driver_id, trip.co_driver_id):
        if ma:
            ra.append(_chu_cai_dau(_ten_tai_xe(bang_ten, ma)))
    return ra


# Moc NEO cua mau xoay: mot ngay thu Hai co dinh. Mau phai neo vao mot moc
# TUYET DOI, khong vao o dau cua khung dang xem — neo vao khung xem thi xem tuan
# sau se thay mau chay lai tu dau, va mot chu ky tam ngay bong nhien thanh chu ky
# bay ngay. Nguoi dung doi tuan qua tuan lai thi thay mau nhay lung tung.
NEO_MAU = dt.date(2024, 1, 1)  # thu Hai


def _chi_so_mau(mau, ngay):
    return (ngay - NEO_MAU).days % len(mau)


def _mau_noi_nghi(mau, ngay):
    if not mau:
        return False
    return mau[_chi_so_mau(mau, ngay)] in ("-", "O", "N")


def _khac_mau(mau, ngay, ma_ca):
    """Ca da xep co LECH mau xoay khong.

    Ban mau ve vien cam quanh nhung o "sua tay khac mau". Dau hieu do co ich
    that: no cho nguoi xem biet cho nao lich khong con theo chu ky, tuc cho nao
    can doc lai bang tay.
    """
    if not mau:
        return False
    return CHU_MAU.get(mau[_chi_so_mau(mau, ngay)]) != ma_ca


def ca_theo_mau(mau, ngay):
    """Ca ma mau xoay noi cho mot ngay, hoac `None` khi mau noi la nghi."""
    if not mau:
        return None
    return CHU_MAU.get(mau[_chi_so_mau(mau, ngay)])


def _bai_va_to(db):
    """Danh sach bai va to, dem tu ca hai bang nguoi va xe.

    Dem ca hai la co y: mot bai co xe ma chua khai tai xe nao van phai hien ra,
    vi day chinh la truong hop nguoi dung can thay — bai co xe ma khong co
    nguoi thi khong chay duoc chuyen nao.
    """
    dem_tx = dict(db.query(Driver.depot_code, func.count(Driver.id))
                  .group_by(Driver.depot_code).all())
    dem_xe = dict(db.query(Vehicle.depot_code, func.count(Vehicle.id))
                  .group_by(Vehicle.depot_code).all())
    ten_bai = dict(db.query(Vehicle.depot_code, func.min(Vehicle.depot))
                   .group_by(Vehicle.depot_code).all())
    ma_bai = [m for m in set(list(dem_tx) + list(dem_xe)) if m]
    bai = sorted(({
        "depot_code": m,
        "ten": ten_bai.get(m) or m,
        "so_tai_xe": int(dem_tx.get(m) or 0),
        "so_xe": int(dem_xe.get(m) or 0),
    } for m in ma_bai), key=lambda x: x["ten"])
    chua_phan = int(dem_tx.get(None) or 0) + int(dem_xe.get(None) or 0)
    if chua_phan:
        bai.append({
            "depot_code": None, "ten": "Chưa phân bãi",
            "so_tai_xe": int(dem_tx.get(None) or 0), "so_xe": int(dem_xe.get(None) or 0),
        })

    to = []
    for ma_to, ma_bai_cua_to, so in db.query(
        Driver.team_code, func.min(Driver.depot_code), func.count(Driver.id)
    ).group_by(Driver.team_code).all():
        to.append({
            "team_code": ma_to, "ten": ma_to or "Chưa phân tổ",
            "depot_code": ma_bai_cua_to, "so_tai_xe": int(so or 0),
        })
    to.sort(key=lambda x: (x["team_code"] is None, x["ten"]))
    return bai, to


def _viec_can_lam(nhan_su, xe, do_phu):
    """Cot phai cua man: nhung viec CU THE, xep viec nang truoc.

    Ban mau viet san bon dong o day. Bon dong do la vi du, khong phai danh
    sach: cai man hinh can la nhung viec THAT dang treo, va moi dong phai chi
    duoc vao mot o cu the tren luoi de bam vao la tới do.
    """
    viec_nhan_su = []
    for muc in do_phu:
        for c in muc["cac_ca"]:
            if c["thieu"] > 0:
                viec_nhan_su.append({
                    "loai": "thieu_nguoi", "muc": "cao",
                    "tieu_de": "Ca %s %s · thiếu %d người" % (ten_ca(c["ca"]).lower(), muc["thu"], c["thieu"]),
                    "mo_ta": "%d xe phải chạy, %d người trực" % (c["can"], c["truc"]),
                    "ngay": muc["ngay"], "ca": c["ca"], "so_luong": c["thieu"],
                })
    for p in nhan_su:
        if p["vuot_gio"]:
            viec_nhan_su.append({
                "loai": "vuot_gio", "muc": "vua",
                "tieu_de": "%s · %sh/tuần" % (p["ten"], p["gio_tuan"]),
                "mo_ta": "Vượt trần %dh — cần trưởng bãi duyệt" % TRAN_GIO_TUAN,
                "driver_id": p["driver_id"],
            })
    chua_phan_to = [p for p in nhan_su if not p["team_code"]]
    if chua_phan_to:
        viec_nhan_su.append({
            "loai": "chua_phan_to", "muc": "thap",
            "tieu_de": "%d người chưa phân tổ" % len(chua_phan_to),
            "mo_ta": "Chưa thuộc tổ nào nên không tính vào độ phủ của tổ",
            "so_luong": len(chua_phan_to),
        })

    viec_xe = []
    for v in xe:
        for d in v["cac_ngay"]:
            for o in d["cac_o"]:
                if o["trang_thai"] == "conf":
                    viec_xe.append({
                        "loai": "trip_thieu_to_lai", "muc": "cao",
                        "tieu_de": "%s · %s ca %s không có tổ lái" % (v["vehicle_id"], o["trip_id"], ten_ca(o["ca"]).lower()),
                        "mo_ta": "Điều phối đã hứa chuyến này mà chưa ai lái",
                        "vehicle_id": v["vehicle_id"], "ngay": d["ngay"], "ca": o["ca"],
                        "trip_id": o["trip_id"],
                    })
    for v in xe:
        if v["ngay_ranh"] == len(v["cac_ngay"]) and v["cac_ngay"]:
            viec_xe.append({
                "loai": "xe_ranh_ca_tuan", "muc": "thap",
                "tieu_de": "%s rảnh cả kỳ" % v["vehicle_id"],
                "mo_ta": "Không có chuyến, không bảo dưỡng, không tổ lái trong ca nào",
                "vehicle_id": v["vehicle_id"],
            })
    thu_tu = {"cao": 0, "vua": 1, "thap": 2}
    viec_nhan_su.sort(key=lambda x: thu_tu[x["muc"]])
    viec_xe.sort(key=lambda x: thu_tu[x["muc"]])
    return {"nhan_su": viec_nhan_su, "xe": viec_xe}


# ===========================================================================
# HAI DUONG GHI cua man xep ca. Ca hai deu di qua `tms_scheduling_service`
# cho phan luu ca, de moi rang buoc nghiep vu da co — khong trung ca, nghi
# giua hai ca, tran gio tuan — van duoc kiem. Viet lai phep kiem o day la tao
# ra mot duong thu hai long hon duong cu, va nguoi dung se di duong long.
# ===========================================================================

MAU_HOP_LE = set("SCDĐ-ON")


def kiem_mau(mau):
    """Mau xoay hop le, hoac nem loi noi ro ky tu nao sai.

    Mau la thu ma chuc nang sinh lich doc de sinh ca cho ca thang, nen mot ky
    tu la trong mau se lang le tao ra mot ngay khong co ca — va nguoi xep lich
    khong biet vi sao ngay do trong.
    """
    chuoi = str(mau or "").strip().upper()
    if not chuoi:
        raise DomainError("PATTERN_REQUIRED", "Mẫu xoay ca không được để trống.", 422)
    if len(chuoi) > 31:
        raise DomainError("PATTERN_TOO_LONG", "Mẫu xoay ca dài quá 31 ngày.", 422)
    la = sorted({c for c in chuoi if c not in MAU_HOP_LE})
    if la:
        raise DomainError(
            "PATTERN_INVALID",
            "Mẫu xoay chỉ nhận S (sáng), C (chiều), Đ hoặc D (đêm) và - (nghỉ). "
            "Ký tự không hiểu: %s" % " ".join(la),
            422,
        )
    if not any(c in ("S", "C", "D", "Đ") for c in chuoi):
        raise DomainError("PATTERN_ALL_REST", "Mẫu xoay toàn ngày nghỉ thì không sinh được ca nào.", 422)
    return chuoi


def gan_phan_to(db, driver_id, data, actor="system"):
    """Gan bai, to va mau xoay cho mot tai xe.

    Ban mau co dong "Bam ma mau o cot trai de doi mau cho nguoi do". Khong co
    duong ghi nay thi ba cot moi mai mai rong va man hinh chi co mot nhom "chua
    phan to" — tuc dung nhu truoc khi lam man nay.
    """
    d = db.get(Driver, driver_id)
    if d is None:
        raise DomainError("DRIVER_NOT_FOUND", "Không tìm thấy tài xế cần phân tổ.", 404)
    la = set(data) - {"depot_code", "team_code", "rotation_pattern"}
    if la:
        raise DomainError("FIELD_NOT_ALLOWED", "Trường không hợp lệ: %s" % ", ".join(sorted(la)), 422)
    if "depot_code" in data:
        d.depot_code = str(data["depot_code"] or "").strip() or None
    if "team_code" in data:
        d.team_code = str(data["team_code"] or "").strip() or None
    if "rotation_pattern" in data:
        gia_tri = data["rotation_pattern"]
        # Chuoi rong la CO Y: bo mau xoay cua nguoi nay, tro lai xep tay.
        d.rotation_pattern = kiem_mau(gia_tri) if str(gia_tri or "").strip() else None
    db.add(AuditLog(
        user_id=actor, action="ASSIGN_DRIVER_TEAM", table_name="drivers",
        record_id=d.id, ip_address=db.info.get("audit_ip"),
    ))
    db.flush()
    return {
        "driver_id": d.id, "ten": d.name, "depot_code": d.depot_code,
        "team_code": d.team_code, "mau_xoay": d.rotation_pattern,
    }


def sinh_lich_theo_mau(db, data, actor="system"):
    """Sinh ca cho ca mot to tu mau xoay cua tung nguoi.

    KHONG GHI DE. O nao da co ban ghi lich thi bo qua — ke ca ca da khoa vi co
    Trip, ca sua tay, va ca nghi phep. Sinh lich la viec LAP CHO NHUNG NGAY CON
    TRONG; ghi de len lich da co nghia la xoa mot quyet dinh ma nguoi nao do da
    ra, va o day thi quyet dinh do co the la "nguoi nay dang nghi phep".

    Tra ve dem theo tung ly do, khong chi mot con so: nguoi xep lich phai biet
    vi sao 40 ca sinh ra chu khong phai 294, neu khong ho tuong chuc nang vo.
    """
    from services import tms_scheduling_service as dich_vu_ca

    ngay_dau = _ngay(data.get("start"), "ngày bắt đầu")
    so_ngay = max(1, min(int(data.get("days") or 7), 62))
    depot = str(data.get("depot") or "").strip() or None
    team = str(data.get("team") or "").strip() or None
    mau_chung = str(data.get("rotation_pattern") or "").strip() or None
    if mau_chung:
        mau_chung = kiem_mau(mau_chung)
    chi_thu = bool(data.get("dry_run"))

    q = db.query(Driver)
    if depot:
        q = q.filter(Driver.depot_code == depot)
    if team:
        q = q.filter(Driver.team_code == team)
    tai_xe = q.order_by(Driver.name).all()
    if not tai_xe:
        raise DomainError("NO_DRIVER_IN_SCOPE", "Không có tài xế nào trong phạm vi đã chọn.", 422)

    cac_ngay = [ngay_dau + dt.timedelta(days=i) for i in range(so_ngay)]
    tu_utc = _utc(ngay_dau, 0)
    den_utc = _utc(cac_ngay[-1] + dt.timedelta(days=1), 6)
    da_co = set()
    for row in db.query(DriverShiftAssignment).filter(
        DriverShiftAssignment.status != "cancelled",
        DriverShiftAssignment.shift_start < den_utc,
        DriverShiftAssignment.shift_end > tu_utc,
    ).all():
        ngay = _ngay_cua(row)
        if ngay is not None:
            da_co.add((row.driver_id, ngay))

    dem = {"da_sinh": 0, "bo_qua_da_co": 0, "bo_qua_nghi_theo_mau": 0,
           "khong_co_mau": 0, "loi": 0}
    loi = []
    for d in tai_xe:
        mau = (d.rotation_pattern or mau_chung or "").upper()
        if not mau:
            dem["khong_co_mau"] += 1
            continue
        xe = d.assigned_vehicle if d.assigned_vehicle and d.assigned_vehicle != "Chưa gán" else None
        for ngay in cac_ngay:
            if (d.id, ngay) in da_co:
                dem["bo_qua_da_co"] += 1
                continue
            ma_ca = ca_theo_mau(mau, ngay)
            if ma_ca is None:
                dem["bo_qua_nghi_theo_mau"] += 1
                continue
            tu, den = khung_ca(ngay, ma_ca)
            try:
                if not chi_thu:
                    dich_vu_ca.save_driver_shift(db, {
                        "id": "MAU-%s-%s-%s" % (d.id, ngay.strftime("%Y%m%d"), ma_ca),
                        "driver_id": d.id,
                        "vehicle_id": xe,
                        "shift_type": ma_ca,
                        "availability_kind": "work",
                        "shift_start": tu.replace(tzinfo=dt.timezone.utc),
                        "shift_end": den.replace(tzinfo=dt.timezone.utc),
                        "notes": "Sinh từ mẫu xoay %s" % mau,
                        "status": "planned",
                    }, actor=actor, shift_id="MAU-%s-%s-%s" % (d.id, ngay.strftime("%Y%m%d"), ma_ca))
                dem["da_sinh"] += 1
                da_co.add((d.id, ngay))
            except DomainError as e:
                # Mot nguoi vuong rang buoc thi KHONG duoc lam vo ca lan sinh.
                # Ghi lai ly do va di tiep — nguoi xep lich can biet ai vuong
                # va vuong gi, chu khong phai mot thong bao "sinh lich that bai".
                dem["loi"] += 1
                if len(loi) < 20:
                    loi.append({"driver_id": d.id, "ten": d.name,
                                "ngay": ngay.isoformat(), "ca": ma_ca,
                                "ma_loi": e.code, "thong_diep": e.message})
    return {
        "pham_vi": {"tu": ngay_dau.isoformat(), "den": cac_ngay[-1].isoformat(),
                    "so_ngay": so_ngay, "depot_code": depot, "team_code": team,
                    "so_tai_xe": len(tai_xe), "chi_thu": chi_thu},
        "dem": dem,
        "loi": loi,
    }


def _do_phu_theo_bai(bai, cac_ngay, nhan_su, xe, can_theo_bai):
    """Do phu tach RIENG cho tung bai.

    Man "Toan bai" ve mot dai nhiet moi bai mot hang. Truoc day ca ba bai dung
    CHUNG mot dai — do phu cua toan pham vi — nen ba hang giong nhau y het va
    dai nhiet khong noi duoc dieu duy nhat no ton tai de noi: bai nao dang
    thieu. Ba hang giong nhau con te hon khong co dai nao, vi nguoi xem tin la
    ba bai deu du.

    "Can" dem theo bai CUA CHIEC XE phai chay, khong theo bai cua nguoi: mot
    chuyen can mot xe cu the, va xe do dau o mot bai cu the.
    """
    truc = {}
    for p in nhan_su:
        for d in p["cac_ngay"]:
            for o in d["cac_o"]:
                if o["trang_thai"] in ("on", "lock"):
                    khoa = (p["depot_code"], d["ngay"], o["ca"])
                    truc[khoa] = truc.get(khoa, 0) + 1
    san_sang = {}
    for v in xe:
        for d in v["cac_ngay"]:
            for o in d["cac_o"]:
                if o["trang_thai"] in ("ready", "trip", "run", "done"):
                    khoa = (v["depot_code"], d["ngay"], o["ca"])
                    san_sang[khoa] = san_sang.get(khoa, 0) + 1

    ra = []
    for b in bai:
        ma_bai = b["depot_code"]
        cac_ngay_ra = []
        for ngay in cac_ngay:
            iso = ngay.isoformat()
            cac_ca = []
            for ma in MA_CA:
                can = can_theo_bai.get((ma_bai, ngay, ma), 0)
                co_nguoi = truc.get((ma_bai, iso, ma), 0)
                cac_ca.append({
                    "ca": ma, "truc": co_nguoi, "can": can,
                    "thieu": max(0, can - co_nguoi),
                    "xe_san_sang": san_sang.get((ma_bai, iso, ma), 0),
                })
            cac_ngay_ra.append({"ngay": iso, "thu": TEN_THU[ngay.weekday()], "cac_ca": cac_ca})
        ra.append({
            "depot_code": ma_bai, "ten": b["ten"],
            "so_tai_xe": b["so_tai_xe"], "so_xe": b["so_xe"],
            "cac_ngay": cac_ngay_ra,
            "thieu": sum(c["thieu"] for d in cac_ngay_ra for c in d["cac_ca"]),
        })
    return ra


def ung_vien_lap_ca(db, ngay, ma_ca, depot=None, team=None):
    """Nhung nguoi CO THE nhan mot ca dang thieu, xep de truoc kho sau.

    VI SAO CHI MOT PHUONG AN, KHONG PHAI BON. Ban mau ve bon cach xu ly mot ca
    thieu nguoi: doi ca, muon nguoi to khac, tang ca cho duyet, va dang ca mo
    tren app. Ba cach sau khong co co so nao trong he thong nay — khong co bang
    dang ky nhan ca, khong co luong duyet tang ca, va "muon to khac" chi la doi
    ca voi mot bo loc rong hon. Ve bon nut ma ba nut khong lam gi thi nguoi dung
    bam thu ba lan roi thoi tin ca man hinh.

    Con MOT phuong an la that va tinh duoc: ai dang ranh ca do, va nhan ho vao
    thi co vuot rang buoc nao khong. Bam mot nguoi la GHI THAT qua duong luu ca
    da co, nen moi phep kiem cua may chu van chan.

    BA MUC DO KHO, va thu tu nay la phan co ich nhat cua ham:
      · `ranh`     — hom do khong co ca nao. Nhan them mot ca, khong anh huong ai.
      · `doi_ca`   — hom do dang co ca KHAC. Nhan ca nay thi phai bo ca kia, tuc
                     ca kia lai thieu nguoi. Nguoi xep lich phai biet truoc.
      · `qua_gio`  — nhan vao thi vuot tran gio tuan. Khong chan, nhung phai noi.

    Nguoi NGHI PHEP khong xuat hien trong danh sach. De ho vao roi ghi mot dong
    "dang nghi phep" thi som muon cung co nguoi bam.
    """
    ngay_dp = _ngay(ngay, "ngày")
    if ma_ca not in MA_CA:
        raise DomainError("SHIFT_CODE_INVALID", "Mã ca không hợp lệ: %s" % ma_ca, 422)
    tu, den = khung_ca(ngay_dp, ma_ca)

    q = db.query(Driver)
    if depot:
        q = q.filter(Driver.depot_code == depot)
    if team:
        q = q.filter(Driver.team_code == team)
    tai_xe = q.order_by(Driver.name).all()
    if not tai_xe:
        return {"ngay": ngay_dp.isoformat(), "ca": ma_ca, "ung_vien": []}

    ma_tx = {d.id for d in tai_xe}
    # Gio tuan tinh tren TUAN CHUA NGAY DO, khong phai bay ngay ke tu ngay do:
    # tran 48h la tran cua mot tuan lam viec, va nguoi xep lich doc theo tuan.
    dau_tuan = ngay_dp - dt.timedelta(days=ngay_dp.weekday())
    tuan_tu = _utc(dau_tuan, 0)
    tuan_den = _utc(dau_tuan + dt.timedelta(days=7), 6)

    gio_tuan = {}
    ca_trong_ngay = {}
    nghi_phep = set()
    for row in db.query(DriverShiftAssignment).filter(
        DriverShiftAssignment.status != "cancelled",
        DriverShiftAssignment.driver_id.in_(ma_tx),
        DriverShiftAssignment.shift_start < tuan_den,
        DriverShiftAssignment.shift_end > tuan_tu,
    ).all():
        if row.availability_kind == "work":
            gio_tuan[row.driver_id] = gio_tuan.get(row.driver_id, 0.0) + _gio_lam(row)
        if _ngay_cua(row) == ngay_dp:
            if row.availability_kind in NGHI_PHEP:
                nghi_phep.add(row.driver_id)
            else:
                ma_cua_row = _ma_ca_cua(row)
                if ma_cua_row:
                    ca_trong_ngay.setdefault(row.driver_id, []).append(ma_cua_row)

    # Nguoi dang co chuyen trong dung khung gio nay thi KHONG ranh — du chua co
    # ban ghi ca nao. Dieu phoi gan tai xe vao chuyen truoc khi co ban ghi ca.
    dang_co_chuyen = set()
    for trip in db.query(TransportTrip).filter(
        TransportTrip.status.notin_(TRIP_BO),
        TransportTrip.planned_departure_at < den,
        TransportTrip.planned_arrival_at > tu,
    ).all():
        for ma_nguoi in (trip.driver_id, trip.co_driver_id):
            if ma_nguoi in ma_tx:
                dang_co_chuyen.add(ma_nguoi)

    do_dai = round((den - tu).total_seconds() / 3600.0, 2)
    ra = []
    for d in tai_xe:
        if d.id in nghi_phep:
            continue
        cac_ca = ca_trong_ngay.get(d.id, [])
        if ma_ca in cac_ca or d.id in dang_co_chuyen:
            continue  # da truc dung ca nay roi
        gio = round(gio_tuan.get(d.id, 0.0), 1)
        sau_khi_nhan = round(gio + do_dai, 1)
        if sau_khi_nhan > TRAN_GIO_TUAN:
            muc, ly_do = "qua_gio", "Nhận vào là %sh/tuần, vượt trần %dh" % (sau_khi_nhan, TRAN_GIO_TUAN)
        elif cac_ca:
            muc, ly_do = "doi_ca", "Hôm đó đang trực ca %s — nhận ca này thì ca kia lại thiếu" % (
                ", ".join(ten_ca(x).lower() for x in cac_ca))
        else:
            muc, ly_do = "ranh", "Hôm đó chưa có ca nào · %sh/tuần" % gio
        ra.append({
            "driver_id": d.id, "ten": d.name, "chu_cai": _chu_cai_dau(d.name),
            "vai_tro": d.role, "hang_bang": d.license_type,
            "team_code": d.team_code, "depot_code": d.depot_code,
            "xe_mac_dinh": d.assigned_vehicle if d.assigned_vehicle and d.assigned_vehicle != "Chưa gán" else None,
            "gio_tuan": gio, "gio_sau_khi_nhan": sau_khi_nhan,
            "muc": muc, "ly_do": ly_do,
        })
    thu_tu = {"ranh": 0, "doi_ca": 1, "qua_gio": 2}
    ra.sort(key=lambda x: (thu_tu[x["muc"]], x["gio_tuan"]))
    return {
        "ngay": ngay_dp.isoformat(), "ca": ma_ca,
        "ten_ca": ten_ca(ma_ca),
        "so_gio_ca": do_dai,
        "ung_vien": ra,
    }
