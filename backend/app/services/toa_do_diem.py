"""Toa do cua cac diem tren mang van chuyen — MOT nguon duy nhat.

VI SAO TEP NAY TON TAI. Bang toa do nay truoc day nam BEN TRONG
`tracking_control_service.py`, va chi man "Theo doi va kiem soat" doc duoc no.
Man "Tuyen duong" thi di hoi `nominatim.openstreetmap.org` qua Internet cho
tung diem — mot loi goi ra ngoai, tu trinh duyet cua nguoi dung.

Hau qua do duoc tren man hinh that: man Tuyen duong bao "Khong xac dinh duoc
toa do tuyen duong" va o ban do trang tron, TRONG KHI he thong da biet toa do
cua dung nhung diem do va man Theo doi dang ve duoc tuyen bang chinh chung. Hai
man noi hai dieu trai nguoc ve cung mot tuyen.

Ba ly do khong the dua vao Nominatim cho viec nay:
  · No la mot dich vu NGOAI. May demo khong co mang, hoac mang bi chan, la ban
    do trang — va khong co thong bao nao noi ra vi sao.
  · No chan dung theo kieu dung luong tu trinh duyet, nen cang nhieu chang thi
    cang de bi tu choi.
  · No tra ve mot diem cho MOT CHUOI TU DO. "Bai Song Than" la ten noi bo cua
    doi xe, khong phai mot dia danh — mot dich vu ban do ngoai khong co nghia vu
    biet no o dau, va khi no doan sai thi khong ai phat hien ra.

Nen co che that la BA TANG (xem `toa_do_day_du` o cuoi tep):

  1. Bang `locations` — du lieu goc, sua duoc, tra ve tu may chu.
  2. Bang moi `DIEM_THAM_CHIEU` duoi day — cho cac ten noi bo, va duoc ghi vao
     `locations` ngay lan dau dung.
  3. Mot dich vu tra toa do ngoai, goi TU MAY CHU, ket qua ghi lai vao
     `locations`.

Bang moi o duoi KHONG phai co che — no chi la diem khoi dau. Nho tang 3 thi mot
tuyen MOI voi mot kho MOI van ve duoc; nho tang 1 thi lan sau khong can mang.
"""

import json
import math
import unicodedata
import urllib.parse
import urllib.request

# Nap `Location` o TANG MODULE, khong nap trong than tung ham.
#
# LOI DA XAY RA THAT, va no la mot loi that chu khong phai chuyen rieng cua bo
# kiem: `from models import Location` dat trong than ham se nap LAI module
# `models` neu mot ai do da xoa no khoi `sys.modules` — va luc do lop `Location`
# moi la MOT LOP KHAC lop ma phan con lai cua tien trinh dang dung. Truy van
# bang lop khac tra ve nhung doi tuong khac, nen mot phep ghi toa do "thanh
# cong" ma khong ai thay ket qua. Moi service khac trong du an nap models o tang
# module; nap khac di la tu tao ra mot duong rieng de sai.
from models import Location


#: Toa do cua cac diem trong mang van chuyen cua doi xe.
#:
#: Day la du lieu NOI BO, khong phai mot ban sao cua ban do the gioi. Cac ten o
#: day la ten doi xe dung khi noi chuyen ("Bai Song Than"), va nhieu ten trong
#: so do khong tra duoc tren mot dich vu ban do cong cong.
#:
#: Moi diem khai NHIEU CACH VIET, co y: nguoi nhap lieu viet "VSIP II-A",
#: "KCN VSIP II-A" va "Kho VSIP II-A, Binh Duong" cho cung mot cho, va bat ho
#: viet dung mot cach thi som muon se co mot tuyen khong ve duoc.
DIEM_THAM_CHIEU = {
    'kho vsip ii-a binh duong': (11.0497, 106.7428),
    'kho vsip ii a binh duong': (11.0497, 106.7428),
    'kcn vsip ii-a': (11.0497, 106.7428),
    'vsip ii-a': (11.0497, 106.7428),
    'vsip ii a': (11.0497, 106.7428),
    'vanh dai 3': (10.8769, 106.7734),
    'cang cat lai tp thu duc': (10.7567, 106.7828),
    'cang cat lai': (10.7567, 106.7828),
    'cong giao nhan cang cat lai': (10.7567, 106.7828),
    'bai song than': (10.8894, 106.7294),
    'kcn song than': (10.8894, 106.7294),
    'song than': (10.8894, 106.7294),
    'cang cai mep': (10.5303, 107.0302),
    'kcn amata': (10.9458, 106.8671),
    'kho long an': (10.6086, 106.4692),
    'long an': (10.6086, 106.4692),
    'amata': (10.9458, 106.8671),
    'cai mep': (10.5303, 107.0302),
    'tan cang': (10.7789, 106.7231),
    'hiep phuoc': (10.6394, 106.7431),
}


def chuan_hoa(gia_tri):
    """Bo dau, bo ky tu la, gom khoang trang — de so hai cach viet voi nhau.

    "Cảng Cát Lái, TP. Thủ Đức" va "cang cat lai tp thu duc" phai ra cung mot
    khoa, neu khong thi moi dau phay trong du lieu nhap tay lai lam mat mot
    diem tren ban do.
    """
    text = unicodedata.normalize('NFKD', str(gia_tri or ''))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = text.replace('đ', 'd')
    return ' '.join(''.join(ch if ch.isalnum() else ' ' for ch in text).split())


def toa_do(nhan):
    """Toa do `(lat, lng)` cua mot diem, hoac `None` khi khong biet.

    Tra ve `None` chu khong doan: mot diem sai cho tren ban do con te hon khong
    co diem nao. Nguoi truc thay mot chiec xe o giua Dong Nai se goi tai xe hoi
    vi sao, va cau tra loi la khong ai dat no o do ca.

    Khop CHUA nhau (`in`) la co y, va no la ly do bang tren khai nhieu cach
    viet: "Kho VSIP II-A, Binh Duong" chua "vsip ii a", nen mot ten dai hon
    trong du lieu that van tra ve dung diem.
    """
    khoa = chuan_hoa(nhan)
    if not khoa:
        return None
    if khoa in DIEM_THAM_CHIEU:
        return DIEM_THAM_CHIEU[khoa]
    for biet, diem in DIEM_THAM_CHIEU.items():
        if biet in khoa or khoa in biet:
            return diem
    return None


def gan_toa_do_cho_chang(cac_chang):
    """Them `from_lat/from_lng/to_lat/to_lng` vao tung chang cua mot tuyen.

    Chang nao khong tra duoc toa do thi GIU NGUYEN, khong dien khoa rong: giao
    dien phan biet "chua biet toa do diem nay" voi "toa do bang 0", va mot cap
    `(0, 0)` se dat chang do o ngoai khoi bo bien chau Phi.
    """
    ra = []
    for chang in cac_chang if isinstance(cac_chang, list) else []:
        if not isinstance(chang, dict):
            continue
        dong = dict(chang)
        di = dong.get('from') or dong.get('origin')
        den = dong.get('to') or dong.get('destination')
        diem_di = toa_do(di)
        diem_den = toa_do(den)
        if diem_di:
            dong.setdefault('from_lat', diem_di[0])
            dong.setdefault('from_lng', diem_di[1])
        if diem_den:
            dong.setdefault('to_lat', diem_den[0])
            dong.setdefault('to_lng', diem_den[1])
        ra.append(dong)
    return ra


# ===========================================================================
# BO TRA TOA DO BA TANG.
#
# Bang `DIEM_THAM_CHIEU` o tren KHONG con la co che — no chi la BANG MOI cho
# nhung ten noi bo ma khong dich vu ban do cong cong nao biet ("Bai Song Than"
# la ten doi xe dung, khong phai mot dia danh). Co che that la ba tang:
#
#   1. Bang `locations` — du lieu goc, sua duoc, tra ve tu may chu.
#   2. Bang moi o tren — cho cac ten noi bo, va duoc GHI VAO `locations` ngay
#      lan dau dung, nen tu do tro di no cung sua duoc nhu moi dia diem khac.
#   3. Mot dich vu tra toa do NGOAI, goi tu MAY CHU (khong tu trinh duyet), va
#      ket qua duoc GHI LAI vao `locations`.
#
# Nho tang 3 thi mot tuyen MOI voi mot kho MOI van ve duoc ban do. Nho viec ghi
# lai o tang 1 thi lan sau khong can mang nua.
#
# VI SAO GOI TU MAY CHU, khong tu trinh duyet. Do duoc tren mang cua du an:
# `nominatim.openstreetmap.org` KHONG TOI DUOC, nen duong cu (trinh duyet goi
# Nominatim) luon that bai va man hinh bao "Khong xac dinh duoc toa do". Goi tu
# may chu thi doi duoc nha cung cap mot cho, khong phai sua tung man, va ket qua
# vao thang co so du lieu.
# ===========================================================================

def _duong_photon(cau):
    return "https://photon.komoot.io/api/?limit=1&q=" + urllib.parse.quote(cau)


def _doc_photon(goi):
    ds = (goi or {}).get("features") or []
    if not ds:
        return None
    toa = ((ds[0] or {}).get("geometry") or {}).get("coordinates") or []
    if len(toa) < 2:
        return None
    return (float(toa[1]), float(toa[0]))


def _duong_arcgis(cau):
    return ("https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer"
            "/findAddressCandidates?f=json&maxLocations=1&outFields=&singleLine="
            + urllib.parse.quote(cau))


def _doc_arcgis(goi):
    ds = (goi or {}).get("candidates") or []
    if not ds:
        return None
    vt = (ds[0] or {}).get("location") or {}
    if vt.get("y") is None or vt.get("x") is None:
        return None
    return (float(vt["y"]), float(vt["x"]))


#: Cac nha cung cap tra toa do, thu theo thu tu. HAI nha, khong mot: mot nha
#: chet thi con duong khac, va do la truong hop da xay ra that voi Nominatim.
NHA_CUNG_CAP = (
    ("photon", _duong_photon, _doc_photon),
    ("arcgis", _duong_arcgis, _doc_arcgis),
)

#: Hop ranh cua Viet Nam. Mot dich vu tra toa do tra ve dung dinh dang nhung
#: SAI CHO la truong hop nguy hiem nhat: khong co loi nao bao, va ban do dat mot
#: kho o Bo Dao Nha. Chan o day chu khong tin nha cung cap.
HOP_VIET_NAM = (8.0, 24.0, 102.0, 110.0)  # lat_min, lat_max, lng_min, lng_max

THOI_GIAN_CHO = 6  # giay


def _trong_viet_nam(diem):
    if not diem:
        return False
    lat, lng = diem
    a, b, c, d = HOP_VIET_NAM
    return a <= lat <= b and c <= lng <= d


def tra_ngoai(nhan, ghi_log=None):
    """Tra toa do bang dich vu ngoai. Tra ve `(lat, lng)` hoac `None`.

    Them ", Viet Nam" vao cau tra: mot ten nhu "Cang Cat Lai" co the trung voi
    dia danh o nuoc khac, va dich vu se tra ve cai no thay truoc — tuc la o dau
    cung duoc.
    """
    ten = str(nhan or "").strip()
    if not ten:
        return None
    thap = ten.lower()
    cau = ten if ("việt nam" in thap or "viet nam" in thap or "vietnam" in thap) else ten + ", Việt Nam"
    for ten_nha, dung_duong, doc in NHA_CUNG_CAP:
        try:
            yeu_cau = urllib.request.Request(
                dung_duong(cau),
                # Photon va Nominatim tu choi yeu cau khong co User-Agent that.
                headers={"User-Agent": "EPL-Logistics-TMS/1.0 (route map geocoder)"},
            )
            with urllib.request.urlopen(yeu_cau, timeout=THOI_GIAN_CHO) as tra:
                goi = json.loads(tra.read().decode("utf-8", "replace"))
            diem = doc(goi)
            if _trong_viet_nam(diem):
                if ghi_log is not None:
                    ghi_log.append({"nhan": ten, "nha": ten_nha, "diem": diem})
                return diem
        except Exception:
            # Mot nha khong tra duoc thi thu nha ke tiep. KHONG nem loi: mot dia
            # diem khong tra duoc khong duoc lam vo ca man hinh — cac chang khac
            # van phai ve duoc.
            continue
    return None


def _diem_tu_bang(db, nhan):
    """Toa do tu bang `locations`, khop theo ten, ma hoac dia chi da chuan hoa."""
    khoa = chuan_hoa(nhan)
    if not khoa:
        return None
    for row in db.query(Location).filter(
        Location.latitude.is_not(None), Location.longitude.is_not(None)
    ).all():
        for ten in (row.name, row.id, row.address):
            k = chuan_hoa(ten)
            if k and (k == khoa or k in khoa or khoa in k):
                return (float(row.latitude), float(row.longitude))
    return None


def _ghi_vao_bang(db, nhan, diem):
    """Ghi toa do vua tra duoc vao `locations`, de lan sau khong can mang.

    KHONG tao dia diem moi neu chua co: mot ban ghi dia diem la du lieu goc, va
    sinh no tu mot chuoi nguoi dung go vao o "Diem den" se lam bang dia diem day
    nhung dong rac. Chi DIEN toa do cho dia diem DA CO ma con thieu.
    """
    khoa = chuan_hoa(nhan)
    if not khoa:
        return False
    for row in db.query(Location).all():
        for ten in (row.name, row.id):
            k = chuan_hoa(ten)
            if k and (k == khoa or k in khoa or khoa in k):
                if row.latitude is None or row.longitude is None:
                    row.latitude, row.longitude = diem
                    db.flush()
                return True
    return False


def toa_do_day_du(db, nhan, cho_phep_ngoai=True, ghi_log=None):
    """Toa do cua mot diem, thu ba tang: bang dia diem, bang moi, dich vu ngoai.

    Tra ve `(diem, nguon)` voi `nguon` la `'bang'`, `'moi'` hoac `'ngoai'`, hoac
    `(None, None)`. NGUON la thong tin PHAI co: mot diem tu bang dia diem la do
    NGUOI khai va duoc tin; mot diem tu dich vu ngoai la do may DOAN va phai
    kiem lai (xem `_hop_ly_theo_km`).

    `cho_phep_ngoai=False` de goi trong nhung duong khong duoc phep cho mang —
    ham nay co the mat vai giay khi phai goi ra ngoai.
    """
    diem = _diem_tu_bang(db, nhan)
    if diem:
        return diem, 'bang'
    diem = toa_do(nhan)
    if diem:
        # Bang moi biet, nhung bang dia diem thi chua — dien vao de tu day tro
        # di no la du lieu sua duoc, khong phai mot dong trong ma nguon.
        _ghi_vao_bang(db, nhan, diem)
        return diem, 'moi'
    if not cho_phep_ngoai:
        return None, None
    diem = tra_ngoai(nhan, ghi_log)
    if diem:
        _ghi_vao_bang(db, nhan, diem)
        return diem, 'ngoai'
    return None, None


def khoang_cach_km(a, b):
    """Khoang cach duong chim bay giua hai diem, tinh bang km."""
    lat1, lng1 = a
    lat2, lng2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


#: Duong chim bay bao gio cung NGAN hon duong bo. Mot chang 12 km ma hai diem
#: cach nhau 1.600 km thi mot trong hai diem sai — khong co cach doc nao khac.
#: He so 1.15 la biên cho chieu nguoc lai: duong bo dai hon duong chim bay,
#: nen chim bay LON HON km khai la dau hieu sai; nho hon thi binh thuong.
HE_SO_CHIM_BAY = 1.15
#: Duoi nguong nay thi khong xet: mot chang 3 km ma lech 2 km la chuyen thuong
#: (diem khai la mot khu, khong phai mot cong).
SAI_SO_TOI_THIEU_KM = 25.0


def _hop_ly_theo_km(diem_di, diem_den, km_khai):
    """Hai diem vua tra co khop voi so km NGUOI DUNG KHAI khong.

    VI SAO PHEP KIEM NAY PHAI CO. Da xay ra that: mot dich vu tra toa do nhan
    ten "Bai tap ket noi bo so 7 EPL" — mot ten noi bo khong dich vu nao biet —
    va tra ve mot diem o Bac Ninh. Diem do NAM TRONG Viet Nam nen phep kiem hop
    ranh khong bat duoc, va ban do dat mot chang 12 km thanh mot duong dai 1.600
    km chay suot ca nuoc. Mot diem sai cho ma khong co canh bao nao te hon han
    mot o ban do trong: nguoi dung tin vao no.

    So voi con so KM NGUOI DUNG KHAI, khong voi mot danh sach ten — nen phep
    kiem nay dung cho moi dia diem, ke ca dia diem chua ai nghe ten.
    """
    try:
        km = float(km_khai)
    except (TypeError, ValueError):
        return True  # khong khai km thi khong co gi de doi chieu
    if km <= 0:
        return True
    thuc = khoang_cach_km(diem_di, diem_den)
    return thuc <= max(km * HE_SO_CHIM_BAY, km + SAI_SO_TOI_THIEU_KM)


def gan_toa_do_cho_chang_db(db, cac_chang, cho_phep_ngoai=True):
    """Nhu `gan_toa_do_cho_chang` nhung tra qua ca ba tang.

    Tra ve `(cac_chang, cac_diem_khong_tra_duoc)`. Danh sach thu hai la de man
    hinh NOI RA diem nao chua biet toa do — bao "khong ve duoc ban do" ma khong
    noi diem nao thi nguoi dung khong biet phai sua gi.

    Toa do nguoi dung da khai TAY thi khong ghi de: mot con so nguoi khai bao
    gio cung thang mot con so may doan.
    """
    ra = []
    thieu = []
    bo_dem = {}
    for chang in cac_chang if isinstance(cac_chang, list) else []:
        if not isinstance(chang, dict):
            continue
        dong = dict(chang)
        vua_tra = {}
        for phia, khoa_lat, khoa_lng in (
            (dong.get("from") or dong.get("origin"), "from_lat", "from_lng"),
            (dong.get("to") or dong.get("destination"), "to_lat", "to_lng"),
        ):
            if dong.get(khoa_lat) is not None and dong.get(khoa_lng) is not None:
                # Toa do da co san — nguoi dung khai tay, hoac lan luu truoc da
                # ghi. Khong tra lai va khong ghi de.
                vua_tra[khoa_lat] = ((dong[khoa_lat], dong[khoa_lng]), 'san')
                continue
            if not phia:
                continue
            k = chuan_hoa(phia)
            if k not in bo_dem:
                bo_dem[k] = toa_do_day_du(db, phia, cho_phep_ngoai)
            diem, nguon = bo_dem[k]
            if diem:
                dong[khoa_lat], dong[khoa_lng] = diem
                vua_tra[khoa_lat] = (diem, nguon)
            elif phia not in thieu:
                thieu.append(phia)

        # ĐỐI CHIẾU với số km người dùng khai. Chỉ nghi ngờ điểm do DỊCH VỤ
        # NGOÀI đoán; điểm từ bảng địa điểm là do người khai và được tin.
        di = vua_tra.get("from_lat")
        den = vua_tra.get("to_lat")
        km_khai = dong.get("dist_km") or dong.get("distance_km") or dong.get("distance") or dong.get("km")
        if di and den and 'ngoai' in (di[1], den[1]) and not _hop_ly_theo_km(di[0], den[0], km_khai):
            # Không biết điểm nào sai trong hai điểm, nên BỎ CẢ HAI điểm do máy
            # đoán và nói tên chúng ra. Giữ lại một điểm rồi vẽ nửa tuyến là
            # trình bày một suy đoán như một sự thật.
            for phia, khoa_lat, khoa_lng in (
                (dong.get("from") or dong.get("origin"), "from_lat", "from_lng"),
                (dong.get("to") or dong.get("destination"), "to_lat", "to_lng"),
            ):
                muc = vua_tra.get(khoa_lat)
                if muc and muc[1] == 'ngoai':
                    dong.pop(khoa_lat, None)
                    dong.pop(khoa_lng, None)
                    if phia and phia not in thieu:
                        thieu.append(phia)
                    # Xoá khỏi cả bộ đệm và bảng địa điểm: một toạ độ sai đã ghi
                    # vào `locations` sẽ được tin ở tang 1 mãi về sau.
                    bo_dem.pop(chuan_hoa(phia), None)
                    _xoa_toa_do_da_ghi(db, phia)
        ra.append(dong)
    return ra, thieu


def _xoa_toa_do_da_ghi(db, nhan):
    """Xoa mot toa do da ghi vao `locations` khi phat hien no vo ly.

    Khong lam viec nay thi phep kiem km chi cuu duoc lan dau: toa do sai da nam
    trong bang dia diem, va tu lan sau no duoc tra ve o tang 1 — tang duoc TIN
    va khong bi kiem lai nua.
    """
    khoa = chuan_hoa(nhan)
    if not khoa:
        return
    for row in db.query(Location).filter(
        Location.latitude.is_not(None), Location.longitude.is_not(None)
    ).all():
        for ten in (row.name, row.id):
            k = chuan_hoa(ten)
            if k and (k == khoa or k in khoa or khoa in k):
                row.latitude, row.longitude = None, None
                db.flush()
                return
