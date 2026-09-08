"""Du lieu VAN HANH cho ban demo: ca truc, bao duong, va Packing List.

VI SAO CAN RIENG MOT TEP: `demo_seed_service` nap chuoi nghiep vu — bao gia →
don hang → lenh giao hang → chuyen → giao nhan → hach toan — va no neo vao NGAY
CO DINH (thang 8/2026) de cac bai kiem doi chieu duoc so tien va moc thoi gian.

Nhung ba man van hanh duoi day lai mo o TUAN HIEN TAI:

  · "Sap lich xe va tai xe" mo tuan chua ngay hom nay;
  · luoi lich xe va khoi bao duong cung theo tuan do;
  · man Dieu phoi mo ngay hom nay.

Nen du lieu neo vao thang 8/2026 khong bao gio hien ra o do. Do duoc: man xep ca
bao "Chua xep 3", luoi bao duong trong tron, va bang DO cua man Dieu phoi ghi
"Chua co lenh giao hang san sang dieu phoi ngay ..." — khong phai loi, chi la du
lieu nam o tuan khac.

Tep nay nap them mot lop du lieu neo theo NGAY HOM NAY. Hai lop tach roi han:
lop co dinh de bai kiem doi chieu, lop theo tuan de man hinh co gi ma xem.

MOT NGUYEN TAC: moi thu di qua dung tang nghiep vu, khong ghi thang vao bang.
Packing List chay qua `parking_list_service` nen may trang thai
(ready → parked → gate_in → loaded) duoc ton trong; neu mai nay quy tac quet doi
thi du lieu demo doi theo, chu khong thanh mot trang thai khong the dat duoc.
"""

import datetime as dt

from models import (
    DeliveryOrder,
    DriverShiftAssignment,
    ParkingList,
    Vehicle,
    VehicleMaintenanceRequest,
)
from services import parking_list_service


ACTOR = "demo-seed"

# Bay gio la GIO UTC. Cac man doc du lieu theo ngay dia phuong, nhung mocs demo
# dat trong khoang giua ngay nen lech mui gio khong day sang ngay khac.
def _now():
    return dt.datetime.now(dt.timezone.utc)


def dau_tuan(hom_nay=None):
    """Thu Hai cua tuan chua `hom_nay`, luc 00:00 UTC.

    Man xep ca tinh tuan bat dau tu thu Hai, nen bo nap phai dung cung moc —
    lech mot ngay la ca tuan du lieu roi ra ngoai khung dang xem.
    """
    ngay = (hom_nay or _now()).date()
    return dt.datetime.combine(
        ngay - dt.timedelta(days=ngay.weekday()), dt.time(0, 0), dt.timezone.utc
    )


# Ba ca theo gio dia phuong Viet Nam (UTC+7), doi ve UTC:
#   sang   06:00-14:00  ->  23:00 hom truoc - 07:00
#   chieu  14:00-22:00  ->  07:00 - 15:00
#   dem    22:00-06:00  ->  15:00 - 23:00
CA = {
    "morning": (dt.timedelta(hours=-1), dt.timedelta(hours=7)),
    "afternoon": (dt.timedelta(hours=7), dt.timedelta(hours=15)),
    "night": (dt.timedelta(hours=15), dt.timedelta(hours=23)),
}


def xoa_lop_van_hanh(db):
    """Xoa lop du lieu van hanh cu, de nap lai khong bi trung.

    Chi xoa nhung dong do CHINH bo nap nay tao — nhan dien bang tien to ma. Xoa
    theo khoang thoi gian thi se an luon du lieu that neu ai do dang thu tren
    cung tuan.
    """
    db.query(DriverShiftAssignment).filter(
        DriverShiftAssignment.id.like("DEMO-CA-%")
    ).delete(synchronize_session=False)
    db.query(VehicleMaintenanceRequest).filter(
        VehicleMaintenanceRequest.id.like("DEMO-BD-%")
    ).delete(synchronize_session=False)
    db.flush()


def nap_ca_truc(db, tuan=None):
    """Ca truc cho tuan hien tai, co du ba nhom ma dai loc nhanh dem den.

    Dai loc o man xep ca co ba nhom: "chua xep", "vuot gio" (tren 48 gio/tuan),
    va "co nghi". Nap phang mot ca moi nguoi moi ngay thi ca ba nhom deu bang 0
    va dai loc thanh vo nghia — nen du lieu o day co y dung du ba tinh huong.
    """
    t0 = tuan or dau_tuan()
    ke_hoach = [
        # (ma tai xe, ma xe, ca cho tung ngay trong tuan; None = nghi theo mau)
        ("DEMO-DRV-001", "DEMO-51C-268.89",
         ["morning", "morning", "afternoon", "afternoon", "night", "night", None]),
        # Nguoi thu hai lam sau ngay, moi ngay tam gio -> 48 gio, chua vuot.
        ("DEMO-DRV-002", "DEMO-61H-112.34",
         ["afternoon", "afternoon", "morning", "morning", "morning", "morning", None]),
        # Nguoi thu ba lam bay ngay -> 56 gio, VUOT nguong 48 gio/tuan.
        ("DEMO-DRV-003", None,
         ["night", "night", "night", "morning", "morning", "afternoon", "afternoon"]),
    ]

    da_tao = 0
    for i, (tai_xe, xe, tuan_ca) in enumerate(ke_hoach, start=1):
        for thu, loai in enumerate(tuan_ca):
            if loai is None:
                continue
            lech_bd, lech_kt = CA[loai]
            ngay = t0 + dt.timedelta(days=thu)
            db.merge(DriverShiftAssignment(
                id="DEMO-CA-%s-%02d%d" % (ngay.strftime("%Y%m%d"), i, thu),
                driver_id=tai_xe,
                vehicle_id=xe,
                shift_type=loai,
                availability_kind="work",
                shift_start=ngay + lech_bd,
                shift_end=ngay + lech_kt,
                work_location="Kho VSIP II-A, Binh Duong",
                notes="Ca truc theo mau tuan, du lieu demo",
                status="confirmed",
                created_by=ACTOR,
                updated_by=ACTOR,
            ))
            da_tao += 1

    # ---------------------------------------------------------------------
    # TO LAI CHO TUNG XE.
    #
    # Ba nhom tren la ba TINH HUONG can cho dai loc o man xep ca (chua xep,
    # vuot gio, co nghi). Nhung chung chi phu hai chiec xe, nen man Dieu phoi
    # cham diem cho chin chiec thi bay chiec bi tru diem vi "khong co tai xe
    # trong ca" — dung theo du lieu, sai theo nghiep vu.
    #
    # Lop nay gan cho MOI chiec con lai mot to lai co ca. Vai diem co y:
    #
    #   · Nam ngay lam, hai ngay nghi -> 40 gio/tuan. De bay ngay thi ai cung
    #     vuot 48 gio, va dai loc "vuot gio" mat y nghia vi no khong con chi ra
    #     ngoai le nao ca — chi con DEMO-DRV-003 la truong hop vuot that.
    #   · Ca xoay theo BAI, khong xoay theo thu tu bang: moi bai phai co it nhat
    #     mot chiec truc ca sang, khong thi don lay hang buoi sang o bai do
    #     khong co xe nao gan duoc tai xe.
    #   · Hai chiec co them phu xe, dung hai vai ma may chu nhan (`driver_id` va
    #     `co_driver_id`) — khong dat vai thu ba, vi khong co cho de luu.
    # ---------------------------------------------------------------------
    to_lai = [
        # (ma xe, tai xe chinh, phu xe, ca)
        ("DEMO-51C-129.03", "DEMO-DRV-004", "DEMO-DRV-007", "morning"),
        ("DEMO-51C-301.88", "DEMO-DRV-005", None, "morning"),
        ("DEMO-51C-412.09", "DEMO-DRV-008", "DEMO-DRV-013", "morning"),
        ("DEMO-61H-208.44", "DEMO-DRV-006", None, "morning"),
        ("DEMO-51C-556.12", "DEMO-DRV-009", None, "afternoon"),
        ("DEMO-61H-330.17", "DEMO-DRV-011", "DEMO-DRV-014", "afternoon"),
        ("DEMO-50H-771.25", "DEMO-DRV-010", None, "night"),
    ]
    for j, (xe, chinh, phu, loai) in enumerate(to_lai, start=4):
        lech_bd, lech_kt = CA[loai]
        for thu in range(5):  # thu Hai den thu Sau, nghi hai ngay cuoi tuan
            ngay = t0 + dt.timedelta(days=thu)
            for k, nguoi in enumerate((chinh, phu)):
                if nguoi is None:
                    continue
                db.merge(DriverShiftAssignment(
                    id="DEMO-CA-%s-%02d%d%d" % (ngay.strftime("%Y%m%d"), j, thu, k),
                    driver_id=nguoi,
                    vehicle_id=xe,
                    shift_type=loai,
                    availability_kind="work",
                    shift_start=ngay + lech_bd,
                    shift_end=ngay + lech_kt,
                    work_location=None,
                    notes="To lai theo xe, du lieu demo",
                    status="confirmed",
                    created_by=ACTOR,
                    updated_by=ACTOR,
                ))
                da_tao += 1

    # MOT ngay nghi phep, de nhom "co nghi" cua dai loc co noi dung that. Ngay
    # nghi khong tinh gio lam, nen no cung la truong hop kiem cho phep tinh gio.
    ngay_nghi = t0 + dt.timedelta(days=3)
    db.merge(DriverShiftAssignment(
        id="DEMO-CA-NGHI-%s" % ngay_nghi.strftime("%Y%m%d"),
        driver_id="DEMO-DRV-002",
        vehicle_id=None,
        shift_type="custom",
        availability_kind="leave",
        shift_start=ngay_nghi,
        shift_end=ngay_nghi + dt.timedelta(days=1),
        work_location=None,
        notes="Nghi phep da duyet",
        status="confirmed",
        created_by=ACTOR,
        updated_by=ACTOR,
    ))
    db.flush()
    return da_tao + 1


def nap_bao_duong(db, tuan=None):
    """Hai ky bao duong, CO Y hai trang thai khac nhau.

    Hai trang thai nay lam hai viec khac nhau, va man xep ca hien chung o hai
    cho khac nhau:

      · `approved` — CHAN dieu phoi. `vehicle-availability` tra ve no, nen o
        tuong ung tren luoi lich xe bi ke soc.
      · `requested` — CHUA chan gi. `vehicle-availability` co y khong tra ve no,
        nen no chi hien o khoi nhac ben phai. Neu khong co mot ky nao o trang
        thai nay thi khoi nhac do khong bao gio hien, va khong ai biet no co.
    """
    t0 = tuan or dau_tuan()
    xe = [row[0] for row in db.query(Vehicle.id).filter(
        Vehicle.id.like("DEMO-%")
    ).order_by(Vehicle.id).all()]
    if not xe:
        return 0

    # Ky da duyet: dat vao thu Sau, la ngay ma ba tai xe deu con ca — nen no la
    # mot xung dot that ma nguoi xep lich phai thay.
    thu_sau = t0 + dt.timedelta(days=4)
    db.merge(VehicleMaintenanceRequest(
        id="DEMO-BD-DA-DUYET",
        request_no="BD-%s-001" % thu_sau.strftime("%Y%m%d"),
        vehicle_id=xe[0],
        category="preventive",
        priority="normal",
        planned_start=thu_sau + dt.timedelta(hours=1),
        planned_end=thu_sau + dt.timedelta(hours=9),
        description="Bao duong dinh ky 5.000 km: dau may, loc gio, kiem tra phanh",
        workshop="Xuong EPL Song Than",
        odometer_km=125000,
        currency_code="VND",
        status="approved",
        approved_at=_now(),
        approved_by=ACTOR,
        created_by=ACTOR,
        updated_by=ACTOR,
    ))

    # Ky moi xin, chua duyet.
    thu_tu = t0 + dt.timedelta(days=2)
    db.merge(VehicleMaintenanceRequest(
        id="DEMO-BD-CHUA-DUYET",
        request_no="BD-%s-002" % thu_tu.strftime("%Y%m%d"),
        vehicle_id=xe[-1],
        category="corrective",
        priority="high",
        planned_start=thu_tu + dt.timedelta(hours=2),
        planned_end=thu_tu + dt.timedelta(hours=6),
        description="Tai xe bao co tieng lach cach o cau sau, xin kiem tra",
        workshop="Xuong EPL Song Than",
        odometer_km=131500,
        currency_code="VND",
        status="requested",
        created_by=ACTOR,
        updated_by=ACTOR,
    ))
    db.flush()
    return 2


def nap_packing_list(db, do_id):
    """Mot Packing List cho DO dang cho, va quet cho du de den `loaded`.

    VI SAO PHAI QUET DEN `loaded`: `require_loaded_for_dispatch` CHAN dieu phoi
    khi mot DO co Packing List ma chua bocc du kien. De no dung o `ready` thi ban
    demo khong xuat ben duoc, va nguoi thu se tuong he thong hong.

    Va vi sao khong ghi thang `status="loaded"` vao bang: may trang thai buoc di
    dung thu tu ready → parked → gate_in → loaded, moi buoc mot lan quet QR. Di
    qua tang nghiep vu thi du lieu demo la mot trang thai DAT DUOC THAT; ghi
    thang la dung mot trang thai ma khong luot quet nao dan tai duoc, va lich su
    su kien thi trong.
    """
    if db.query(ParkingList).filter(
        ParkingList.do_id == do_id, ParkingList.status != "cancelled"
    ).first():
        return None

    # `generate_from_do` tra ve doi tuong ORM `ParkingList`, khong phai dict —
    # nen doc bang thuoc tinh. Cac tem phai LAY RA THANH DANH SACH truoc khi
    # quet: moi lan quet lam thay doi trang thai va co the lam SQLAlchemy nap
    # lai quan he, luc do vong lap dang duyet no se doc du lieu nua vong.
    ds = parking_list_service.generate_from_do(
        db, do_id,
        {"wave": "Wave 1", "gate": "Cong B", "box_count": 3},
        ACTOR,
    )
    ma_phieu = ds.id
    tem = [row.qr_token for row in ds.labels]

    # Quet DU MOI KIEN o CA BA buoc.
    #
    # Truoc day hai buoc dau chi quet mot kien, vi luc do mot lan quet la ca
    # phieu chuyen trang thai. Quy tac da doi: ca ba buoc gio deu doi du moi
    # kien moi chuyen phieu — hai buoc dau truoc kia noi sai, ghi "da qua cong"
    # khi moi mot trong ba kien qua cong.
    for buoc in ("yard_arrival", "gate_entry", "load_package"):
        for token in tem:
            parking_list_service.scan_label(db, token, buoc, ACTOR)
    db.flush()
    return ma_phieu


def don_cho_ve_hom_nay(db):
    """Doi ngay lay hang cua cac don DANG CHO sang HOM NAY.

    VI SAO CAN: man Dieu phoi loc DO theo NGAY DANG XEM, va no mo mac dinh o
    ngay hom nay — phep loc so `pickup_window_start`. Du lieu mau neo vao thang
    8/2026, nen mo man Dieu phoi ra la "DO trong ngay = 0" va cot DO trong tron.
    Do duoc trong Chrome: dai so lieu ra sau con 0, khong the DO nao.

    Nguoi xem khong phan biet duoc "hom nay khong co don nao" voi "man nay hong"
    — va truoc mot buoi demo thi ho se doc thanh cai thu hai.

    CHI doi don o trang thai `pending`, va CHI doi ngay:

      · Don da co chuyen thi khong doi — doi ngay lay hang cua no la lam lech
        voi gio khoi hanh cua chuyen, sinh ra du lieu tu mau thuan.
      · Khong tao them hang moi, nen `_delete_seeded_workflow` van don sach va
        nap lai bao nhieu lan cung the.
    """
    hom_nay = _now().date()
    doi = 0
    for don in db.query(DeliveryOrder).filter(
        DeliveryOrder.id.like("DEMO-DO-%"),
        DeliveryOrder.canonical_status == "pending",
    ).all():
        # Giu nguyen GIO, chi doi NGAY: gio lay hang 08:00 la mot su that nghiep
        # vu, khong phai mot con so ngau nhien.
        goc = don.pickup_window_start
        if goc is None:
            continue
        moi = goc.replace(year=hom_nay.year, month=hom_nay.month, day=hom_nay.day)
        lech = moi - goc
        don.pickup_window_start = moi
        for ten in ("pickup_window_end", "pickup_date", "planned_departure_at",
                    "delivery_window_start", "delivery_window_end", "delivery_date",
                    "planned_arrival_at", "planned_return_at"):
            cu = getattr(don, ten, None)
            if cu is not None:
                setattr(don, ten, cu + lech)
        doi += 1
    db.flush()
    return doi


def nap_lop_van_hanh(db, do_ids=()):
    """Nap ca lop van hanh. Tra ve so dong da tao de goi ben ngoai bao lai."""
    xoa_lop_van_hanh(db)
    t0 = dau_tuan()
    # Doi ngay lay hang cua don dang cho sang hom nay TRUOC khi tao Packing
    # List: phieu lay ngay tu don, nen doi sau la phieu mang ngay cu.
    so_don_doi = don_cho_ve_hom_nay(db)
    ket_qua = {
        "don_doi_ve_hom_nay": so_don_doi,
        "tuan_bat_dau": t0.date().isoformat(),
        "so_ca": nap_ca_truc(db, t0),
        "so_ky_bao_duong": nap_bao_duong(db, t0),
        "packing_list": [],
    }
    for do_id in do_ids:
        ma = nap_packing_list(db, do_id)
        if ma:
            ket_qua["packing_list"].append(ma)
    return ket_qua
