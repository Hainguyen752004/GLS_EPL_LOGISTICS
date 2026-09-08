"""Vi tri MO PHONG cua xe dang chay, tinh doc theo tuyen tai luc DOC du lieu.

VAN DE. Thap kiem soat so moc `last_update` cua GPS voi gio hien tai va coi cu
hon muoi lam phut la "mat tin hieu". Bo du lieu mau ghi mot moc GPS luc NAP, nen
sau muoi lam phut ngoi xem la ca hai xe deu chuyen thanh "GPS cu" va hai diem
tren ban do dung yen mot cho. Do duoc tren man hinh that: "GPS thieu / cu 2", ca
hai diem to xam, va chu thich ghi "Xam: vi tri cu".

Voi mot ban demo thi do la mot man hinh CHET. Va no khong the sua bang cach nap
lai du lieu thuong xuyen hon: bao nhieu lan nap cung se cu di sau muoi lam phut.

CACH LAM. Khong ghi mot moc GPS vao co so du lieu roi de no gia di, ma TINH vi
tri tai luc doc: xe di duoc bao nhieu phan tuyen thi dat diem o dung cho do tren
duong. Tuyen trong `routes.segments_json` da co toa do hai dau moi chang (nho
`enrich_route_segments`), nen noi suy duoc mot duong gap khuc that — diem chay
doc theo hanh lang that cua tuyen, khong nhay lung tung giua hai dau.

TRUNG THUC. Vi tri nay la MO PHONG, va no phai duoc noi ra dung nhu vay. Ham
tra ve co `mo_phong=True`, va ben goi phai danh dau rieng tren giao dien — mot
diem mo phong ma man hinh bao la "GPS thiet bi" thi nguoi truc se tin vao mot
vi tri khong ai do duoc, va do la kieu nham lan dat nhat trong dieu do.

Vi tri THAT, khi thiet bi co gui, LUON DUOC UU TIEN. Mo phong chi lap vao cho
trong.
"""

import datetime as dt
import math


def _phan_tram_da_di(trip, now):
    """Xe da di duoc bao nhieu phan chuyen, tinh theo thoi gian.

    Lay moc bat dau la gio xuat ben THUC TE neu co, khong thi gio ke hoach. Lay
    moc ket thuc la gio du kien den. Ke ngoai khoang thi kep lai 0 hoac 1: xe
    chua chay thi dung o diem lay hang, xe qua gio du kien thi dung o diem giao
    — khong cho diem troi ra ngoai tuyen.
    """
    bat_dau = getattr(trip, "actual_departure_at", None) or getattr(trip, "planned_departure_at", None)
    ket_thuc = getattr(trip, "planned_arrival_at", None)
    if not bat_dau or not ket_thuc:
        return None

    def _utc(x):
        if x is None:
            return None
        return x.replace(tzinfo=dt.timezone.utc) if x.tzinfo is None else x.astimezone(dt.timezone.utc)

    bat_dau, ket_thuc, now = _utc(bat_dau), _utc(ket_thuc), _utc(now)
    tong = (ket_thuc - bat_dau).total_seconds()
    if tong <= 0:
        return None
    return max(0.0, min(1.0, (now - bat_dau).total_seconds() / tong))


def _duong_gap_khuc(segments):
    """Chuoi diem cua tuyen, kem do dai tung chang.

    Doc toa do do `enrich_route_segments` da gan (`from_lat`/`to_lat`...). Chang
    nao thieu toa do thi BO QUA chang do chu khong bo ca tuyen: mot tuyen bon
    chang ma thieu toa do mot chang van ve duoc ba chang con lai, con bo het thi
    khong con gi de ve.
    """
    diem = []
    for s in segments if isinstance(segments, list) else []:
        if not isinstance(s, dict):
            continue
        a_lat = s.get("from_lat", s.get("origin_lat"))
        a_lng = s.get("from_lng", s.get("origin_lng"))
        b_lat = s.get("to_lat", s.get("destination_lat"))
        b_lng = s.get("to_lng", s.get("destination_lng"))
        if None in (a_lat, a_lng, b_lat, b_lng):
            continue
        km = float(s.get("dist_km") or s.get("distance_km") or 0) or 1.0
        if not diem:
            diem.append((float(a_lat), float(a_lng), 0.0))
        diem.append((float(b_lat), float(b_lng), km))
    return diem


def duong_gap_khuc_tu_duong_bo(cac_diem):
    """Doi hinh duong BO that thanh chuoi diem kem do dai tung doan.

    VI SAO CAN. `_duong_gap_khuc` chi biet cac DIEM TRAM cua tuyen, nen xe mo
    phong chay tren duong THANG noi cac tram — va mot duong thang tu Long An
    sang Cai Mep di xuyen qua song. Tren man Theo doi thi cai xe do dang dung
    giua song, va do la thu chu du an bao la mang di demo khong duoc.

    Voi hinh duong bo that (hang tram diem doc theo duong nhua) thi xe chay dung
    tren duong. Do dai tung doan tinh bang duong chim bay giua hai diem lien
    tiep — o khoang cach vai chuc met thi do chinh la do dai doan duong.
    """
    diem = [(float(d[0]), float(d[1])) for d in (cac_diem or [])
            if d and len(d) >= 2 and d[0] is not None and d[1] is not None]
    if len(diem) < 2:
        return []
    ra = [(diem[0][0], diem[0][1], 0.0)]
    for truoc_d, sau_d in zip(diem, diem[1:]):
        ra.append((sau_d[0], sau_d[1], _chim_bay_km(truoc_d, sau_d)))
    return ra


def _chim_bay_km(a, b):
    lat1, lng1 = a
    lat2, lng2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _noi_suy(diem, ti_le):
    """Diem nam o `ti_le` cua duong gap khuc, can theo DO DAI tung chang.

    Can theo do dai, khong can deu theo so chang: mot tuyen co chang 34 km va
    chang 6 km thi chia deu se lam xe di het chang ngan trong nua thoi gian —
    diem se nhay giat va nguoi xem thay ngay la khong that.
    """
    if len(diem) < 2:
        return None
    tong = sum(d[2] for d in diem[1:]) or 1.0
    can = ti_le * tong
    da_qua = 0.0
    for i in range(1, len(diem)):
        km = diem[i][2] or 0.0
        if da_qua + km >= can or i == len(diem) - 1:
            trong_chang = 0.0 if km <= 0 else max(0.0, min(1.0, (can - da_qua) / km))
            a_lat, a_lng = diem[i - 1][0], diem[i - 1][1]
            b_lat, b_lng = diem[i][0], diem[i][1]
            return (a_lat + (b_lat - a_lat) * trong_chang,
                    a_lng + (b_lng - a_lng) * trong_chang)
        da_qua += km
    return (diem[-1][0], diem[-1][1])


def vi_tri_mo_phong(trip, segments, now, tong_km=None, trang_thai_don=None,
                    duong_bo=None):
    """Vi tri mo phong cua mot chuyen, hoac `None` neu khong tinh duoc.

    Tra ve dict: `lat`, `lng`, `speed_kmh`, `con_lai_km`, `phan_tram`,
    `quan_sat_luc` (= `now`, vi vi tri duoc tinh BAY GIO), va `mo_phong=True`.

    Khong tinh duoc thi tra ve `None` — khong doan bua mot diem giua ban do.
    Thieu toa do hay thieu moc thoi gian thi noi "khong biet" con dung hon.
    """
    # HINH DUONG BO THAT truoc, cac diem tram sau.
    #
    # Chi co diem tram thi xe chay tren duong THANG noi chung — va mot duong
    # thang tu Long An sang Cai Mep di xuyen qua song, nen tren ban do cai xe
    # dang dung giua song. Co hinh duong bo thi xe chay dung tren duong nhua.
    diem = duong_gap_khuc_tu_duong_bo(duong_bo) or _duong_gap_khuc(segments)
    if len(diem) < 2:
        return None

    # Don DA DEN NOI thi ghim o diem cuoi, toc do 0. Xe da do o cong cang cho ky
    # nhan — de no van "dang chay" o giua duong la noi sai trang thai.
    if str(trang_thai_don or "") == "arrived":
        ti_le = 1.0
    else:
        ti_le = _phan_tram_da_di(trip, now)
        if ti_le is None:
            return None

    toa_do = _noi_suy(diem, ti_le)
    if not toa_do:
        return None

    km = float(tong_km or 0) or sum(d[2] for d in diem[1:])
    con_lai = max(0.0, km * (1.0 - ti_le))

    # Toc do suy tu chinh khung gio ke hoach, khong dat mot so co dinh: mot
    # chuyen 112 km trong ba gio va mot chuyen 44 km trong hai gio la hai toc do
    # khac nhau, va con so phai noi dung dieu do.
    toc_do = 0.0
    if ti_le < 1.0:
        bat_dau = getattr(trip, "actual_departure_at", None) or getattr(trip, "planned_departure_at", None)
        ket_thuc = getattr(trip, "planned_arrival_at", None)
        if bat_dau and ket_thuc:
            gio = (ket_thuc - bat_dau).total_seconds() / 3600.0
            if gio > 0:
                toc_do = round(km / gio, 1)

    return {
        "lat": round(toa_do[0], 6),
        "lng": round(toa_do[1], 6),
        "speed_kmh": toc_do,
        "con_lai_km": round(con_lai, 1),
        "phan_tram": round(ti_le * 100, 1),
        "quan_sat_luc": now,
        "mo_phong": True,
    }
