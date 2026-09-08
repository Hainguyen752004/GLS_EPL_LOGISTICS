"""Hinh duong BO that cua mot tuyen — lay tu dich vu dan duong, luu lai.

VI SAO TEP NAY TON TAI. So do lo trinh truoc day ve mot DUONG THANG noi cac
diem tram. Chu du an noi thang: *"tui muon cai tuyen duong di la su that nen ve
cai duong thang mang di demo ky lam"*. Va do la mot loi that chu khong phai
chuyen tham my: mot duong thang tu Long An sang Cai Mep di xuyen qua song va qua
khu dan cu, noi sai ca hai dieu quan trong nhat cua mot tuyen — xe di duong nao,
va tuyen dai bao nhieu. Do duoc: duong thang cua tuyen do la 112 km theo so
nguoi khai, con duong bo that la 129,1 km.

BA QUYET DINH cua tep nay, va vi sao:

  1. GOI TU MAY CHU, khong tu trinh duyet. Cung ly do voi viec tra toa do: mot
     loi goi ra ngoai tu may nguoi dung la mot thu khong ai kiem soat duoc, va
     tren mang cua du an thi phan lon nhung host do khong toi duoc.

  2. LUU LAI kem DAU VAN cua danh sach diem. Mot tuyen bon diem tra ve hon hai
     nghin diem hinh; lay lai moi lan mo man la mot giay cho cho mot thu khong
     bao gio doi. Dau van la de biet khi nao PHAI lay lai: nguoi dung them mot
     chang thi hinh cu khong con dung, va ve lai hinh cu la ve mot tuyen khong
     con ton tai.

  3. GIAN LUOC hinh truoc khi luu. Hai nghin diem cho mot tuyen la hon 60 KB
     JSON moi lan tai man, va o moi muc thu phong cua ban do thi mat thuong
     khong phan biet duoc no voi ba tram diem. Giu nguyen la tra tien bang bang
     thong cho mot thu khong ai thay.

KHONG BAO GIO tra ve mot duong thang ma noi rang do la duong bo. Khong lay duoc
hinh thi tra ve `None` va de giao dien noi ro "chua co duong bo that" — mot
duong thang duoc trinh bay nhu tuyen di la dieu chu du an vua bao la khong dung
duoc.
"""

import hashlib
import json
import math
import urllib.request


#: Dich vu dan duong. Duong cong khai cua OSRM — do duoc la toi duoc tu mang cua
#: du an, khac voi `nominatim.openstreetmap.org`.
MAY_DAN_DUONG = "https://router.project-osrm.org/route/v1/driving/"
THOI_GIAN_CHO = 12  # giay; hai nghin diem hinh mat khoang mot giay

#: Sai so cho phep khi gian luoc hinh, tinh bang DO (~11 m tren mot do vi do).
#: 0.0001 do la khoang 11 m — nho hon do rong cua mot lan duong, nen mat thuong
#: khong phan biet duoc hinh da gian luoc voi hinh goc.
SAI_SO_GIAN_LUOC = 0.0001
#: Tran so diem sau khi gian luoc. Mot tuyen 500 km van du hinh voi 600 diem.
TRAN_SO_DIEM = 600


def dau_van(cac_diem):
    """Dau van cua danh sach diem, de biet hinh da luu con dung khong.

    Lam tron ve nam chu so thap phan (~1 m) truoc khi bam: mot thay doi duoi
    met la nhieu do lam tron, khong phai mot tuyen khac, va de nguyen thi hinh
    bi lay lai vo co.
    """
    chuoi = ";".join("%.5f,%.5f" % (float(lat), float(lng)) for lat, lng in cac_diem)
    return hashlib.sha256(chuoi.encode("utf-8")).hexdigest()[:16]


def _khoang_cach_den_doan(diem, dau, cuoi):
    """Khoang cach tu mot diem den doan thang `dau`-`cuoi`, theo do."""
    (x, y), (x1, y1), (x2, y2) = diem, dau, cuoi
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def gian_luoc(cac_diem, sai_so=SAI_SO_GIAN_LUOC):
    """Bo cac diem khong lam doi hinh dang (Ramer–Douglas–Peucker).

    Viet vong lap thay vi de quy: mot tuyen dai co the co hang chuc nghin diem,
    va de quy tren do sau do lam vo ngan xep Python.
    """
    diem = [tuple(map(float, d)) for d in cac_diem if d and len(d) >= 2]
    if len(diem) < 3:
        return diem
    giu = [False] * len(diem)
    giu[0] = giu[-1] = True
    ngan_xep = [(0, len(diem) - 1)]
    while ngan_xep:
        dau, cuoi = ngan_xep.pop()
        if cuoi <= dau + 1:
            continue
        xa_nhat, chi_so = -1.0, dau
        for i in range(dau + 1, cuoi):
            d = _khoang_cach_den_doan(diem[i], diem[dau], diem[cuoi])
            if d > xa_nhat:
                xa_nhat, chi_so = d, i
        if xa_nhat > sai_so:
            giu[chi_so] = True
            ngan_xep.append((dau, chi_so))
            ngan_xep.append((chi_so, cuoi))
    ra = [d for d, k in zip(diem, giu) if k]
    if len(ra) > TRAN_SO_DIEM:
        # Van qua nhieu thi gian luoc them voi sai so lon hon, khong cat bot
        # dau duoi: cat bot lam MAT mot doan tuyen, con gian luoc manh hon chi
        # lam duong bot muot.
        return gian_luoc(ra, sai_so * 4)
    return ra


def lay_hinh_duong_bo(cac_diem):
    """Hinh duong bo that di qua danh sach diem. Tra ve `(cac_diem, km)`.

    Tra ve `(None, None)` khi khong lay duoc — va nguoi goi PHAI xu ly truong
    hop do bang cach noi ra, khong bang cach ve mot duong thang thay the.
    """
    diem = [d for d in (cac_diem or []) if d and len(d) >= 2]
    if len(diem) < 2:
        return None, None
    toa_do = ";".join("%s,%s" % (lng, lat) for lat, lng in diem)
    duong = MAY_DAN_DUONG + toa_do + "?overview=full&geometries=geojson"
    try:
        yeu_cau = urllib.request.Request(
            duong, headers={"User-Agent": "EPL-Logistics-TMS/1.0 (route shape)"})
        with urllib.request.urlopen(yeu_cau, timeout=THOI_GIAN_CHO) as tra:
            goi = json.loads(tra.read().decode("utf-8", "replace"))
    except Exception:
        return None, None
    if goi.get("code") != "Ok":
        return None, None
    tuyen = (goi.get("routes") or [{}])[0]
    toa = ((tuyen.get("geometry") or {}).get("coordinates") or [])
    if len(toa) < 2:
        return None, None
    # OSRM tra ve (kinh do, vi do); ca ung dung dung (vi do, kinh do).
    hinh = gian_luoc([(c[1], c[0]) for c in toa])
    km = round((tuyen.get("distance") or 0) / 1000.0, 1)
    return hinh, (km if km > 0 else None)


def hinh_da_luu(route):
    """Hinh duong bo da luu cua mot tuyen, hoac `None`.

    Tra ve ca `dau_van` de nguoi goi doi chieu: hinh dung nhung cua mot danh
    sach diem KHAC thi khong dung duoc, va dung no la ve mot tuyen khong con
    ton tai.
    """
    if not route or not getattr(route, "road_geometry_json", None):
        return None
    try:
        goi = json.loads(route.road_geometry_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(goi, dict) or not goi.get("diem"):
        return None
    return goi


def duong_bo_cua_tuyen(db, route, cac_diem, cho_phep_ngoai=True):
    """Hinh duong bo cua tuyen: doc ban da luu, chi lay lai khi can.

    Tra ve `{'diem': [...], 'km': ..., 'nguon': 'da_luu' | 'moi_lay' | None}`.
    `nguon=None` nghia la KHONG CO duong bo that — giao dien phai noi ra dieu
    do, khong duoc ve duong thang roi de nguoi xem tuong day la tuyen di.
    """
    diem_moc = [(float(a), float(b)) for a, b in (cac_diem or [])
                if a is not None and b is not None]
    if len(diem_moc) < 2:
        return {"diem": None, "km": None, "nguon": None}

    van = dau_van(diem_moc)
    da_co = hinh_da_luu(route)
    if da_co and da_co.get("dau_van") == van:
        return {"diem": da_co["diem"], "km": da_co.get("km"), "nguon": "da_luu"}

    if not cho_phep_ngoai:
        # Khong duoc goi ra ngoai thi tra ban da luu KEM canh bao la no cu, chu
        # khong tra ve rong: mot hinh cu lech mot chang van dung hon mot duong
        # thang, va giao dien noi ro no cu.
        if da_co:
            return {"diem": da_co["diem"], "km": da_co.get("km"), "nguon": "da_luu_cu"}
        return {"diem": None, "km": None, "nguon": None}

    hinh, km = lay_hinh_duong_bo(diem_moc)
    if not hinh:
        if da_co:
            return {"diem": da_co["diem"], "km": da_co.get("km"), "nguon": "da_luu_cu"}
        return {"diem": None, "km": None, "nguon": None}

    route.road_geometry_json = json.dumps(
        {"diem": hinh, "km": km, "dau_van": van}, ensure_ascii=False)
    route.road_distance_km = km
    db.flush()
    return {"diem": hinh, "km": km, "nguon": "moi_lay"}
