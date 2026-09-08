"""Bao gia cuoc: tinh gia thanh, doi don vi cuoc, va tach thang thanh DO.

LUONG MOI, theo chot cua chu du an: *"tu gio chung ta se di tu QT sang cai DO
luon"* — bo han buoc Don hang (SO). Bao gia tro thanh chung tu thuong mai dau
vao duy nhat cua van hanh: no khoa gia cuoc cho tung chuyen, va DO ke thua chu
khong nhap lai.

BA VIEC CUA TEP NAY

1. TINH GIA THANH MOT CHUYEN — doc CONG THUC THAT cua loai xe o Du lieu goc,
   khong ghi cung nam khoan nhu ban mau. Ban mau dung `fuel×km + dep×km + drv +
   bot + yard`; do la mot vi du, con cong thuc that do nguoi dung tu soan bang
   trinh soan cong thuc (`services/cost_expression.py`, `js/formula-model.js`)
   va co the co bat cu hang tu nao. Ghi cung nam khoan o day nghia la mot cong
   thuc nguoi dung vua sua o Du lieu goc khong anh huong gi tới bao gia — hai
   man se noi hai con so khac nhau cho cung mot chuyen.

2. DOI DON VI CUOC VE `d/chuyen`. Chot voi chu du an sau khi ban bai toan mo da:
   bao gia theo don vi cua KHACH (chuyen / tan / m3 / kg / km) nhung DO luon
   khoa MOT con so d/chuyen. Ly do khong phai cho gon — neu co so du lieu luu
   d/kg thi moi con so phia sau phu thuoc CAN THUC TE, ma can thuc te luon khac
   can khai, nghia la gia khach da dong y se tu doi sau khi xe chay.

3. TACH DO trong MOT giao dich. N dong hang hoa -> N lenh giao hang, moi lenh
   ke thua gia da khoa, tuyen, loai xe, han giao va ghi chu van hanh.

KHONG DOAN KHI THIEU DU LIEU. Thieu tuyen, thieu loai xe, thieu tai trong hay
thieu cong thuc thi tra ve DANH SACH VIEC CON THIEU, khong tra ve mot con so
gia thanh doan. Mot con so gia thanh sai la mot bao giá sai, va bao gia sai thi
di het duong xuong DO, quyet toan va hoa don ma khong ai phat hien.
"""

import datetime as dt
import json

from sqlalchemy import func

from models import (
    CostFormula,
    DeliveryOrder,
    Quotation,
    QuotationAttachment,
    QuotationItem,
    QuotationVersion,
    Route,
    VehicleType,
)
from services.errors import DomainError, conflict


# ===========================================================================
# HE SO NHAN — khop DUNG voi `FACTORS` trong `js/formula-model.js`.
#
# Hai ban sao thi de troi khoi nhau, va luc do man Du lieu goc hien mot con so
# con man Bao gia hien mot con so khac cho cung mot cong thuc. Co mot bai kiem
# doi chieu hai danh sach nay.
# ===========================================================================
HE_SO = {
    "per_km": ("mỗi km", lambda t: t["km"]),
    "per_kg": ("mỗi kg hàng", lambda t: t["tan"] * 1000),
    "per_tonne": ("mỗi tấn hàng", lambda t: t["tan"]),
    "per_trip": ("mỗi chuyến", lambda t: 1),
    "per_stop": ("mỗi điểm giao", lambda t: t["diem_giao"]),
}

#: Don vi bao gia cho khach. `doi` tra ve so luong nhan voi don gia de ra
#: `d/chuyen` cua MOT chuyen.
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

#: Nguong bien loi nhuan mac dinh. LA CAU HINH, khong phai luat: spec ghi ro
#: "nguong 15% va muc tieu 20/25% la config theo cong ty, co the override theo
#: khach". Cot `quotations.target_margin` la cho ghi de theo khach.
NGUONG_BIEN_PHAI_DUYET = 0.15
BIEN_MUC_TIEU = 0.20

#: Trang thai bao gia theo spec. `approved` cua ban cu duoc giu lam bi danh cua
#: `sent` — bo du lieu dang chay co ban ghi mang no, va doi ma cu thanh mot
#: trang thai khong ton tai thi nhung ban ghi do bien mat khoi moi bo loc.
TRANG_THAI = ("draft", "pending_approval", "sent", "approved",
              "accepted", "split", "rejected", "expired")
#: Trang thai coi la DA DONG — khong con la viec dang mo.
DA_DONG = ("rejected", "expired")


def _so(gia_tri, mac_dinh=0.0):
    try:
        x = float(gia_tri if gia_tri not in (None, "") else mac_dinh)
    except (TypeError, ValueError):
        return float(mac_dinh)
    return x if x == x and x not in (float("inf"), float("-inf")) else float(mac_dinh)


def _ngay(gia_tri):
    if not gia_tri:
        return None
    if isinstance(gia_tri, dt.datetime):
        return gia_tri.date()
    if isinstance(gia_tri, dt.date):
        return gia_tri
    try:
        return dt.date.fromisoformat(str(gia_tri)[:10])
    except ValueError:
        return None


# ===========================================================================
# GIA THANH
# ===========================================================================

def cong_thuc_loai_xe(db, ma_loai_xe):
    """Cong thuc gia thanh cua mot loai xe, hoac `None`.

    Lay ban co ID LON NHAT khop loai xe — dung cach chon nhu danh muc cong thuc
    o man Du lieu goc. Bo du lieu cu co ban ghi trung loai xe, va lay ban dau
    tien tim thay se ra mot cong thuc khac voi cai nguoi dung dang thay tren
    man hinh.
    """
    if not ma_loai_xe:
        return None
    for row in db.query(CostFormula).order_by(CostFormula.id.desc()).all():
        try:
            goi = json.loads(row.formula_expression or "{}")
        except (ValueError, TypeError):
            continue
        if str(goi.get("vehicle_type_id") or "") != str(ma_loai_xe):
            continue
        if str(goi.get("currency") or "VND") != "VND":
            continue
        hang_tu = goi.get("terms")
        return {
            "id": row.id,
            "name": row.name,
            "terms": hang_tu if isinstance(hang_tu, list) else [],
            "components": goi.get("components") if isinstance(goi.get("components"), dict) else {},
        }
    return None


def _boi_canh_chuyen(route, khoi_luong_kg, so_diem_giao=None):
    """Cac con so cua MOT chuyen ma cong thuc nhan vao."""
    km = _so(getattr(route, "road_distance_km", None) or getattr(route, "distance_km", 0))
    diem = so_diem_giao
    if diem is None:
        try:
            chang = json.loads(getattr(route, "segments_json", None) or "[]")
            diem = max(1, len(chang)) if isinstance(chang, list) else 1
        except (ValueError, TypeError):
            diem = 1
    return {"km": km, "tan": _so(khoi_luong_kg) / 1000.0, "diem_giao": max(1, int(diem or 1))}


def bang_cau_phan(db, route, loai_xe, khoi_luong_kg, gia_tri_hang=0):
    """Bang cau phan gia thanh cua mot chuyen.

    Tra ve `(cac_dong, gia_thanh, cach_lay_bot)`. Moi dong la mot dict co
    `nhan`, `don_gia`, `nhan_voi`, `thanh_tien`, `loai` (`chi` / `thu`).

    BA DIEU QUAN TRONG:

    · Hang tu `kind='revenue'` KHONG duoc cong vao gia thanh. Cong ca vao thi
      ket qua khong phai gia thanh, cung khong phai gia ban — no la chi phi cong
      doanh thu. Trinh soan cong thuc da tach hai loai nay tu truoc.
    · BOT uu tien lay theo TUYEN (`routes.bot_fee`) roi moi den hang tu cua cong
      thuc, vi BOT thuoc DUONG chu khong thuoc xe. Tra ve `cach_lay_bot` de giao
      dien noi ra minh dang lay tu dau.
    · Khau hao va bao duong /km lay tu `vehicle_types.dep_cost_per_km`, va chi
      them khi cong thuc CHUA co hang tu nao lam viec do — neu khong thi khoan
      do bi tinh hai lan.
    """
    boi_canh = _boi_canh_chuyen(route, khoi_luong_kg)
    cong_thuc = cong_thuc_loai_xe(db, loai_xe.id) if loai_xe else None
    cac_dong = []
    da_co_khau_hao = False
    da_co_bot = False

    for ht in (cong_thuc or {}).get("terms", []):
        if not isinstance(ht, dict):
            continue
        khoa = str(ht.get("key") or "")
        he_so = str(ht.get("factor") or "per_trip")
        if he_so not in HE_SO:
            continue
        don_gia = _so(ht.get("rate"))
        if don_gia <= 0:
            continue
        ten_he_so, lay_so = HE_SO[he_so]
        so_luong = _so(lay_so(boi_canh))
        la_thu = str(ht.get("kind") or "cost") == "revenue"
        if khoa in ("dep", "depreciation", "khau_hao"):
            da_co_khau_hao = True
        if khoa in ("toll", "bot"):
            da_co_bot = True
            # BOT theo tuyen thang BOT theo loai xe — xem ghi chu tren.
            if _so(getattr(route, "bot_fee", None)) > 0:
                continue
        cac_dong.append({
            "khoa": khoa,
            "nhan": ht.get("label") or khoa,
            "don_gia": don_gia,
            "he_so": he_so,
            "nhan_voi": ("1 chuyến" if he_so == "per_trip"
                         else "× %s %s" % (_dep_so(so_luong), ten_he_so.replace("mỗi ", ""))),
            "thanh_tien": don_gia * so_luong,
            "loai": "thu" if la_thu else "chi",
        })

    # Khau hao va bao duong /km — cau phan duy nhat trong spec ma cong thuc cu
    # chua co. Chi them khi cong thuc chua lam viec do.
    khau_hao = _so(getattr(loai_xe, "dep_cost_per_km", None)) if loai_xe else 0
    if khau_hao > 0 and not da_co_khau_hao:
        cac_dong.append({
            "khoa": "dep", "nhan": "Khấu hao và bảo dưỡng /km",
            "don_gia": khau_hao, "he_so": "per_km",
            "nhan_voi": "× %s km" % _dep_so(boi_canh["km"]),
            "thanh_tien": khau_hao * boi_canh["km"], "loai": "chi",
        })

    # BOT theo tuyen.
    bot = _so(getattr(route, "bot_fee", None)) if route else 0
    cach_lay_bot = "khong_co"
    if bot > 0:
        cac_dong.append({
            "khoa": "toll", "nhan": "Phí cầu đường / BOT",
            "don_gia": bot, "he_so": "per_trip",
            "nhan_voi": "%d chặng" % boi_canh["diem_giao"],
            "thanh_tien": bot, "loai": "chi",
        })
        cach_lay_bot = "tuyen"
    elif da_co_bot:
        cach_lay_bot = "loai_xe"

    gia_thanh = sum(d["thanh_tien"] for d in cac_dong if d["loai"] == "chi")
    return cac_dong, round(gia_thanh, 2), cach_lay_bot


def _dep_so(x):
    """So doc duoc theo kieu Viet Nam: 31,2 chu khong phai 31.2."""
    if float(x) == int(x):
        return "{:,}".format(int(x)).replace(",", ".")
    return "{:,.1f}".format(float(x)).replace(",", "X").replace(".", ",").replace("X", ".")


def do_vua_tai(loai_xe, khoi_luong_kg):
    """Do phu hop cua mot loai xe voi tai trong hang.

    Ba muc dung nhu spec: phu hop (<= 90% suc tai) · vua sat tai (90-100%) ·
    khong du tai (> 100%, khong chon duoc). Chua nhap tai trong thi tra ve
    `chua_biet` — moi the chon duoc va khong hien badge, thay vi bao "phu hop"
    cho mot dieu chua ai kiem.
    """
    suc_tai = _so(getattr(loai_xe, "max_weight", 0))
    kg = _so(khoi_luong_kg)
    if kg <= 0 or suc_tai <= 0:
        return "chua_biet"
    if kg > suc_tai:
        return "khong_du_tai"
    if kg > suc_tai * 0.9:
        return "sat_tai"
    return "phu_hop"


def xem_truoc_gia(db, data):
    """Bang cau phan gia thanh, do vua tai cua tung loai xe, va goi y gia.

    Day la CHO TINH GIA — giao dien khong tu tinh. Spec ghi ro dieu do, va no
    dung: mot cong thuc nam o hai cho se troi khoi nhau, roi man Bao gia va man
    Du lieu goc noi hai con so khac nhau cho cung mot chuyen.
    """
    ma_tuyen = str(data.get("route_id") or "").strip()
    ma_loai_xe = str(data.get("vehicle_type_id") or "").strip()
    kg = _so(data.get("weight_kg"))

    route = db.get(Route, ma_tuyen) if ma_tuyen else None
    loai_xe = db.get(VehicleType, ma_loai_xe) if ma_loai_xe else None

    # DANH SACH VIEC CON THIEU, khong phai mot cau "thieu du lieu". Tuyen ba
    # chang thi nguoi dung khong biet phai sua cho nao neu chi noi chung.
    thieu = []
    if not route:
        thieu.append("Chưa chọn tuyến đường nên chưa có số km.")
    elif _so(getattr(route, "road_distance_km", None) or getattr(route, "distance_km", 0)) <= 0:
        thieu.append("Tuyến %s chưa có số km — khai ở Dữ liệu gốc → Tuyến đường." % route.id)
    if not loai_xe:
        thieu.append("Chưa chọn loại xe nên chưa biết áp công thức giá thành nào.")
    if kg <= 0:
        thieu.append("Chưa nhập tổng tải trọng — không kiểm tra được xe có đủ tải.")

    cac_loai_xe = [{
        "id": v.id, "ten": v.name, "suc_tai_kg": _so(v.max_weight),
        "the_tich_m3": _so(v.volume_capacity_m3), "so_pallet": int(_so(v.pallet_capacity)),
        "do_vua_tai": do_vua_tai(v, kg),
        "co_cong_thuc": cong_thuc_loai_xe(db, v.id) is not None,
    } for v in db.query(VehicleType).order_by(VehicleType.name).all()]

    if loai_xe and cong_thuc_loai_xe(db, loai_xe.id) is None:
        thieu.append("Loại xe %s chưa cấu hình công thức giá thành — khai ở Dữ liệu gốc → "
                     "Công thức giá thành." % loai_xe.name)
    if loai_xe and do_vua_tai(loai_xe, kg) == "khong_du_tai":
        thieu.append("Loại xe %s không đủ tải cho %s kg (sức tải %s kg)."
                     % (loai_xe.name, _dep_so(kg), _dep_so(_so(loai_xe.max_weight))))

    if thieu:
        return {
            "tinh_duoc": False, "viec_con_thieu": thieu,
            "cac_dong": [], "gia_thanh": None, "cach_lay_bot": None,
            "cac_loai_xe": cac_loai_xe,
            "nguong_bien": NGUONG_BIEN_PHAI_DUYET, "bien_muc_tieu": BIEN_MUC_TIEU,
            "goi_y_gia": {},
        }

    cac_dong, gia_thanh, cach_lay_bot = bang_cau_phan(
        db, route, loai_xe, kg, _so(data.get("cargo_value")))
    boi_canh = _boi_canh_chuyen(route, kg)
    return {
        "tinh_duoc": True, "viec_con_thieu": [],
        "cac_dong": cac_dong, "gia_thanh": gia_thanh, "cach_lay_bot": cach_lay_bot,
        "km": boi_canh["km"], "so_chang": boi_canh["diem_giao"],
        "cac_loai_xe": cac_loai_xe,
        "nguong_bien": NGUONG_BIEN_PHAI_DUYET, "bien_muc_tieu": BIEN_MUC_TIEU,
        "goi_y_gia": goi_y_gia(db, data, gia_thanh),
    }


def goi_y_gia(db, data, gia_thanh):
    """Ba moc gia goi y, THAY cho he so nhan bua.

    Ban mau dien san `gia thanh × 3,9`. Spec cua chu du an tu ghi rang he so do
    "la so demo, khong co y nghia nghiep vu". Ba moc duoi day deu co nguon:

      · `bien_muc_tieu` — tu chinh sach cong ty (hoac muc tieu rieng cua khach).
      · `hop_dong` — bang gia da ky voi khach cho tuyen nay.
      · `lan_truoc` — bao gia gan nhat cung khach + cung tuyen.

    Moc nao khong co nguon thi KHONG tra ve, thay vi tra mot con so doan: mot
    goi y khong co nguon la mot con so nguoi dung se tin ma khong kiem lai.
    """
    ra = {}
    if gia_thanh and gia_thanh > 0:
        muc_tieu = _so(data.get("target_margin"), BIEN_MUC_TIEU)
        if 0 < muc_tieu < 1:
            ra["bien_muc_tieu"] = {
                "gia": round(gia_thanh / (1 - muc_tieu), -3),
                "mo_ta": "để đạt biên %d%%" % round(muc_tieu * 100),
            }
    ma_khach = str(data.get("customer_id") or "").strip()
    ma_tuyen = str(data.get("route_id") or "").strip()
    if ma_khach and ma_tuyen:
        truoc = (db.query(Quotation)
                 .filter(Quotation.customer_id == ma_khach,
                         Quotation.route_id == ma_tuyen,
                         Quotation.selling_price.is_not(None))
                 .order_by(Quotation.created_at.desc()).first())
        if truoc and _so(truoc.selling_price) > 0:
            ra["lan_truoc"] = {
                "gia": _so(truoc.selling_price),
                "mo_ta": "báo giá %s ngày %s" % (
                    truoc.quote_no or truoc.id,
                    truoc.created_at.date().isoformat() if truoc.created_at else "—"),
            }
    return ra


# ===========================================================================
# DOI DON VI CUOC VE MOT CHUYEN
# ===========================================================================

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


def bien_loi_nhuan(cuoc, gia_thanh):
    """Bien = (cuoc - gia thanh) / cuoc. `None` khi cuoc bang khong.

    Chia cho CUOC chu khong chia cho gia thanh: day la bien tren doanh thu, con
    so nguoi kinh doanh doc. Cuoc bang khong thi khong co bien nao ca — tra ve
    `None` chu khong tra ve 0, vi 0% doc ra la "khong lai" con thuc te la "chua
    biet".
    """
    c = _so(cuoc)
    if c <= 0:
        return None
    return (c - _so(gia_thanh)) / c


# ===========================================================================
# TACH BAO GIA THANH N LENH GIAO HANG
# ===========================================================================

def dong_hang_hoa(db, qid):
    """Cac dong hang hoa cua mot bao gia, theo thu tu dong."""
    return (db.query(QuotationItem)
            .filter(QuotationItem.quotation_id == qid)
            .order_by(QuotationItem.line_no, QuotationItem.id).all())


def so_do_du_kien(db, qid):
    """So DO se tach ra = tong so luong o bang Hang hoa.

    Mot DO = mot cont (hoac mot xe) = mot chuyen — dung nhu spec. Nen so DO la
    tong so luong, khong phai so DONG hang hoa: ba cont cung loai la mot dong
    nhung ba chuyen.
    """
    tong = sum(int(_so(x.quantity)) for x in dong_hang_hoa(db, qid))
    return max(0, tong)


def _moc_thoi_gian(gia_tri):
    """Doc mot moc thoi gian, dung CHUNG ham voi duong tao DO cu.

    LOI DA XAY RA THAT: lan dau tach DO tra ve 500 voi "SQLite DateTime type
    only accepts Python datetime and date objects" — vi o day truyen mot CHUOI
    ISO vao cot kieu thoi gian. Nhung sua bang mot phep doc RIENG thi te hon:
    hai duong tao DO se hieu cung mot chuoi theo hai cach, va mot DO co the ra
    doi voi gio lay hang lech bay tieng so voi DO ben canh. Nen goi dung ham ma
    `create_delivery_order` dang dung.
    """
    from services.workflow_service import _parse_business_datetime
    return _parse_business_datetime(gia_tri)


def _mot_do(db, q, chi_so, dong, gia_khoa, tong_do):
    """Mot lenh giao hang tach tu bao gia."""
    ma = "%s-DO%02d" % ((q.quote_no or q.id).replace("QT-", "").replace("DEMO-", ""), chi_so + 1)
    ma = ("DO-%s" % ma)[:64]
    if db.get(DeliveryOrder, ma):
        # Trung ma nghia la da tach roi. Noi ra chu khong ghi de: ghi de mot DO
        # dang chay se doi gia va han giao cua mot chuyen da dieu phoi.
        raise conflict("DELIVERY_ORDER_EXISTS",
                       "Lệnh giao hàng %s đã tồn tại — báo giá này có thể đã được tách." % ma)
    return DeliveryOrder(
        id=ma,
        quotation_id=q.id,
        so_id=None,
        customer_id=q.customer_id,
        route_id=q.route_id,
        origin=q.origin,
        destination=q.destination,
        pickup_window_start=_moc_thoi_gian(dong.get("pickup_at")),
        pickup_window_end=_moc_thoi_gian(dong.get("pickup_at")),
        delivery_window_start=_moc_thoi_gian(dong.get("due_at")),
        delivery_window_end=_moc_thoi_gian(dong.get("due_at")),
        pickup_date=_moc_thoi_gian(dong.get("pickup_at")),
        delivery_date=_moc_thoi_gian(dong.get("due_at")),
        weight_kg=_so(q.weight_kg) / max(1, tong_do),
        pallet_count=int(_so(q.pallet_count) / max(1, tong_do)),
        volume_m3=_so(q.volume_m3) / max(1, tong_do),
        packaging_spec=q.packaging_spec,
        # GIA DA KHOA. DO khong nhap lai gia, va khong ai sua duoc gia o buoc
        # van hanh — do la ca ly do luong moi bo buoc Don hang.
        unit_price=gia_khoa,
        price_basis=q.price_basis or "per_trip",
        driver_note=dong.get("driver_note") or q.notes_ops,
        status="Chờ xử lý",
        canonical_status="pending",
        created_by=dong.get("actor") or "system",
        updated_by=dong.get("actor") or "system",
    )


def tach_thanh_do(db, qid, cac_dong, actor="system"):
    """Tach mot bao gia DA CHAP NHAN thanh N lenh giao hang. MOT giao dich.

    MOT giao dich la yeu cau nghiep vu, khong phai chi tiet ky thuat: tach ba
    DO ma dong thu ba vo thi hai DO dau da nam trong hang doi cua Dieu phoi, va
    khong ai biet bao gia nay da tach mot phan. Nen hoac ca N, hoac khong DO
    nao — nguoi goi (`_scheduling_command` hoac tuong duong) chiu phan commit.

    CHOT TRUOC KHI TACH: bao gia phai o trang thai `accepted`. Tach mot bao gia
    con dang cho khach la dua vao san xuat mot don hang khach chua dong y.
    """
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    if q.canonical_status == "split":
        raise conflict("QUOTATION_ALREADY_SPLIT",
                       "Báo giá %s đã tách thành lệnh giao hàng. Khách tăng hàng thì thêm "
                       "dòng hàng hoá rồi tách tiếp — các DO cũ giữ nguyên."
                       % (q.quote_no or q.id))
    if q.canonical_status != "accepted":
        raise conflict("QUOTATION_NOT_ACCEPTED",
                       "Chỉ tách được báo giá KHÁCH ĐÃ CHẤP NHẬN. Báo giá %s đang ở trạng "
                       "thái %s — ghi nhận khách chấp nhận trước đã."
                       % (q.quote_no or q.id, q.canonical_status))
    if not q.route_id:
        raise DomainError("ROUTE_REQUIRED",
                          "Báo giá chưa có tuyến đường nên không tách DO được.", 422)

    dong = [d for d in (cac_dong or []) if isinstance(d, dict)]
    if not dong:
        raise DomainError("SPLIT_ROWS_REQUIRED",
                          "Chưa có dòng nào để tách. Số DO gợi ý = tổng số lượng ở bảng "
                          "Hàng hoá.", 422)

    # Gia khoa cho MOT chuyen. Tinh mot lan roi gan cho moi DO — tinh lai tung
    # dong thi mot lan doi don gia giua vong lap se cho ra hai muc gia trong
    # cung mot lan tach.
    thung = dong_hang_hoa(db, q.id)
    so_luong_moi_chuyen = (_so(thung[0].quantity) if len(thung) == 1 else 1)
    gia_khoa = _so(q.selling_price)
    if gia_khoa <= 0:
        gia_khoa = gia_moi_chuyen(
            q.price_basis, q.unit_price, so_luong_moi_chuyen, q.min_qty_per_trip,
            km=_so(getattr(db.get(Route, q.route_id), "distance_km", 0)))
    if gia_khoa <= 0:
        raise DomainError("PRICE_REQUIRED",
                          "Báo giá chưa có giá cước nên DO sẽ không có giá để quyết toán.", 422)

    ra = []
    for i, d in enumerate(dong):
        d = dict(d)
        d.setdefault("actor", actor)
        do = _mot_do(db, q, i, d, gia_khoa, len(dong))
        db.add(do)
        ra.append(do.id)
    db.flush()

    q.canonical_status = "split"
    q.status = "Đã tách DO"
    q.updated_by = actor
    q.updated_at = dt.datetime.utcnow()
    q.version = (q.version or 1) + 1
    db.flush()
    return {"quotation_id": q.id, "quote_no": q.quote_no, "do_ids": ra,
            "gia_moi_chuyen": gia_khoa, "so_do": len(ra)}


# ===========================================================================
# DONG HANG HOA
# ===========================================================================

def thay_dong_hang_hoa(db, qid, cac_dong, actor="system"):
    """Ghi lai TOAN BO cac dong hang hoa cua mot bao gia.

    Thay ca bang thay vi sua tung dong: giao dien la mot bang nguoi dung them va
    xoa dong tu do, nen gui ca bang len la cach duy nhat khong sinh ra trang
    thai nua voi — sua dong 2, xoa dong 3, them dong 4 trong mot lan bam Luu.

    TOI THIEU MOT DONG: so DO tach ra bang tong so luong o bang nay, nen bang
    rong nghia la khong tach duoc DO nao, va mot bao gia khong tach duoc DO thi
    khong dung de lam gi.
    """
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    if q.canonical_status in ("split",) + DA_DONG:
        raise conflict("LOCKED_RECORD",
                       "Báo giá %s đã %s — không sửa được bảng hàng hoá."
                       % (q.quote_no or q.id,
                          "tách DO" if q.canonical_status == "split" else "đóng"))
    dong = [d for d in (cac_dong or []) if isinstance(d, dict)]
    if not dong:
        raise DomainError("ITEMS_REQUIRED",
                          "Bảng hàng hoá phải có ít nhất một dòng — số DO tách ra bằng "
                          "tổng số lượng ở bảng này.", 422)

    db.query(QuotationItem).filter(QuotationItem.quotation_id == q.id).delete(
        synchronize_session=False)
    ra = []
    for i, d in enumerate(dong, start=1):
        so_luong = _so(d.get("quantity"), 1)
        if so_luong < 0:
            raise DomainError("ITEM_QTY_INVALID",
                              "Số lượng dòng %d không được âm." % i, 422)
        row = QuotationItem(
            id="%s-IT%02d" % (q.id, i),
            quotation_id=q.id,
            line_no=i,
            name=(d.get("name") or "").strip() or None,
            quantity=so_luong,
            uom=(d.get("uom") or "Chuyến").strip() or "Chuyến",
            note=(d.get("note") or "").strip() or None,
        )
        db.add(row)
        ra.append(row)
    q.updated_by = actor
    q.updated_at = dt.datetime.utcnow()
    db.flush()
    return [{"line_no": x.line_no, "name": x.name, "quantity": _so(x.quantity),
             "uom": x.uom, "note": x.note} for x in ra]


# ===========================================================================
# CHUYEN TRANG THAI
# ===========================================================================

def _ghi_phien_ban(db, q, ghi_chu, actor):
    """Chot mot phien ban gia.

    Khong co bang nay thi khong ai doi soat duoc voi ban PDF khach dang giu:
    khach noi "anh bao toi 3,9 trieu" ma he thong chi con con so hien tai.
    """
    so = int(_so(q.version, 1))
    da_co = (db.query(QuotationVersion)
             .filter(QuotationVersion.quotation_id == q.id,
                     QuotationVersion.version == so).first())
    if da_co:
        return da_co
    row = QuotationVersion(
        id="%s-V%02d" % (q.id, so), quotation_id=q.id, version=so,
        selling_price=q.selling_price, unit_price=q.unit_price,
        price_basis=q.price_basis, total_cost=q.total_cost,
        currency_code=q.currency_code, fx_rate=q.fx_rate,
        note=ghi_chu, created_by=actor,
    )
    db.add(row)
    db.flush()
    return row


def _ma_bao_gia_moi(db):
    """Ma bao gia hien cho khach: `QT-<nam>-<so tang dan>`."""
    nam = dt.datetime.now().year
    dau = "QT-%d-" % nam
    lon_nhat = 0
    for (ma,) in db.query(Quotation.quote_no).filter(
            Quotation.quote_no.like(dau + "%")).all():
        try:
            lon_nhat = max(lon_nhat, int(str(ma).rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return "%s%04d" % (dau, lon_nhat + 1)


def _ty_gia(db, ma_tien):
    from models import Currency
    row = db.get(Currency, str(ma_tien).upper())
    ty = _so(getattr(row, "exchange_rate", 0))
    if ty <= 0:
        raise DomainError("FX_RATE_MISSING",
                          "Chưa có tỷ giá cho %s — khai ở Dữ liệu gốc → Tỷ giá. Không có "
                          "tỷ giá thì số tiền trên PDF và số lưu trong hệ thống sẽ lệch "
                          "nhau." % ma_tien, 422)
    return ty


def gui_khach(db, qid, actor="system"):
    """Gui bao gia cho khach: cap MA hien cho khach, chot phien ban gia.

    BIEN DUOI NGUONG THI KHONG SANG `sent` ma sang `pending_approval`. Do la
    chot cua spec, va no KHAC chot "khong duyet bao gia lo": lo la duoi gia
    thanh — chan han; con duoi nguong bien la con lai nhung mong, do la mot
    quyet dinh kinh doanh nen di qua nguoi duyet chu khong bi chan.
    """
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    if q.canonical_status not in ("draft", "pending_approval", "sent", "approved"):
        raise conflict("INVALID_TRANSITION",
                       "Báo giá %s đang ở trạng thái %s — không gửi được."
                       % (q.quote_no or q.id, q.canonical_status))

    # Cac chot cua duong DUYET ap luon o day: gui cho khach mot bao gia het han
    # hoac dang lo thi te hon la khong gui.
    from services.workflow_service import kiem_bao_gia_truoc_khi_duyet
    kiem_bao_gia_truoc_khi_duyet(q)

    bien = bien_loi_nhuan(q.selling_price, q.total_cost)
    nguong = _so(q.target_margin, NGUONG_BIEN_PHAI_DUYET)
    if bien is not None and bien < nguong:
        q.canonical_status = "pending_approval"
        q.status = "Chờ duyệt nội bộ"
    else:
        q.canonical_status = "sent"
        q.status = "Đã gửi · chờ khách"
        q.sent_at = dt.datetime.utcnow()

    # MA HIEN CHO KHACH cap o day, khong phai luc tao: spec doi "nhap chua co
    # ma", ma khoa chinh thi khong the rong.
    if not q.quote_no and q.canonical_status == "sent":
        q.quote_no = _ma_bao_gia_moi(db)
    # TY GIA LUC GUI.
    if q.currency_code and q.currency_code != "VND" and not _so(q.fx_rate):
        q.fx_rate = _ty_gia(db, q.currency_code)
    _ghi_phien_ban(db, q, "Gửi khách", actor)
    q.updated_by = actor
    q.updated_at = dt.datetime.utcnow()
    db.flush()
    return q


def khach_chap_nhan(db, qid, actor="system"):
    """Ghi nhan khach chap nhan. Buoc nay MO KHOA muc tach DO."""
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    if q.canonical_status not in ("sent", "approved"):
        raise conflict("INVALID_TRANSITION",
                       "Chỉ báo giá ĐÃ GỬI mới ghi nhận được khách chấp nhận. Báo giá %s "
                       "đang ở trạng thái %s." % (q.quote_no or q.id, q.canonical_status))
    han = _ngay(q.valid_to)
    hom_nay = dt.datetime.now().date()
    if han and han < hom_nay:
        raise conflict("QUOTATION_EXPIRED",
                       "Báo giá hết hạn ngày %s — không ghi nhận chấp nhận được. Gia hạn "
                       "hoặc soát lại giá rồi gửi lại." % han.isoformat())
    q.canonical_status = "accepted"
    q.status = "Đã chấp nhận"
    q.accepted_at = dt.datetime.utcnow()
    q.updated_by = actor
    q.updated_at = dt.datetime.utcnow()
    db.flush()
    return q


def khach_tu_choi(db, qid, ly_do="", actor="system"):
    """Dong bao gia. KHONG dong duoc bao gia da tach DO.

    Da tach nghia la co xe da duoc xep va co the dang chay. Dong bao gia luc do
    de lai nhung DO mo coi — con so tien cua chung tro vao mot chung tu da dong.
    """
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    if q.canonical_status == "split":
        raise conflict("QUOTATION_ALREADY_SPLIT",
                       "Báo giá đã tách thành lệnh giao hàng — không đóng được. Nếu khách "
                       "rút thì huỷ từng lệnh giao hàng ở màn Giao hàng.")
    q.canonical_status = "rejected"
    q.status = "Từ chối"
    q.closed_at = dt.datetime.utcnow()
    q.close_reason = (ly_do or "").strip() or None
    q.updated_by = actor
    q.updated_at = dt.datetime.utcnow()
    db.flush()
    return q


def gia_han(db, qid, han_moi, actor="system"):
    """Gia han hieu luc, va MO LAI mot bao gia da het han.

    Het han khong phai loi cua nguoi dung — gia dau va phi duong doi theo thang.
    Viec dung la soat lai gia roi gia han, chu khong phai tao mot bao gia moi va
    mat lich su cua cai cu.
    """
    q = db.query(Quotation).filter(Quotation.id == qid).with_for_update().first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    ngay = _ngay(han_moi)
    if ngay is None:
        raise DomainError("INVALID_DATE",
                          "Ngày hiệu lực mới không đọc được: %r" % han_moi, 422)
    if ngay < dt.datetime.now().date():
        raise DomainError("VALIDITY_IN_PAST",
                          "Ngày hiệu lực mới (%s) đã qua — gia hạn như vậy thì báo giá vẫn "
                          "hết hạn." % ngay.isoformat(), 422)
    q.valid_to = ngay.isoformat()
    if q.canonical_status == "expired":
        q.canonical_status = "sent"
        q.status = "Đã gửi · chờ khách"
    q.updated_by = actor
    q.updated_at = dt.datetime.utcnow()
    db.flush()
    return q


# ===========================================================================
# DOC: MOT BAO GIA, DANH SACH, VA DAI SO LIEU
# ===========================================================================

def _con_lai_ngay(valid_to, hom_nay=None):
    """So ngay con lai cua hieu luc. `None` khi chua khai han.

    Tra ve `None` chu khong tra ve 0: 0 nghia la "het han hom nay" con chua khai
    nghia la "chua gui" — hai tinh huong khac nhau va cot Hieu luc phai hien
    khac nhau.
    """
    ngay = _ngay(valid_to)
    if ngay is None:
        return None
    return (ngay - (hom_nay or dt.datetime.now().date())).days


def _da_het_han(q, hom_nay=None):
    con = _con_lai_ngay(q.valid_to, hom_nay)
    return con is not None and con < 0


def mot_bao_gia(db, qid, kem_chi_tiet=True):
    """Mot bao gia kem moi thu man chi tiet can, trong MOT loi goi."""
    q = db.query(Quotation).filter(Quotation.id == qid).first()
    if not q:
        raise DomainError("QUOTATION_NOT_FOUND", "Không tìm thấy báo giá %s." % qid, 404)
    return _bung_bao_gia(db, q, kem_chi_tiet)


def _bung_bao_gia(db, q, kem_chi_tiet=False, hom_nay=None):
    bien = bien_loi_nhuan(q.selling_price, q.total_cost)
    con_lai = _con_lai_ngay(q.valid_to, hom_nay)
    # HET HAN TINH TAI LUC DOC, khong luu thanh trang thai.
    #
    # Spec ghi ro tab "Sap het han" la bo loc dong chu khong phai trang thai
    # trong co so du lieu. Luu thanh trang thai thi phai co mot tien trinh chay
    # nen doi no moi dem, va khong co tien trinh do thi mot bao gia het han hom
    # qua van hien la "cho khach" cho tới khi ai do bam vao.
    trang_thai = q.canonical_status
    if trang_thai in ("sent", "approved", "pending_approval") and _da_het_han(q, hom_nay):
        trang_thai = "expired"
    ra = {
        "id": q.id,
        "quote_no": q.quote_no,
        "canonical_status": trang_thai,
        "trang_thai_luu": q.canonical_status,
        "status": q.status,
        "version": int(_so(q.version, 1)),
        "customer_id": q.customer_id,
        "route_id": q.route_id,
        "vehicle_type_id": q.vehicle_type_id,
        "origin": q.origin,
        "destination": q.destination,
        "pickup_window_start": q.pickup_window_start,
        "pickup_window_end": q.pickup_window_end,
        "delivery_window_start": q.delivery_window_start,
        "delivery_window_end": q.delivery_window_end,
        "weight_kg": _so(q.weight_kg),
        "volume_m3": _so(q.volume_m3),
        "pallet_count": int(_so(q.pallet_count)),
        "cargo_type": q.cargo_type,
        "cargo_value": _so(q.cargo_value),
        "packaging_spec": q.packaging_spec,
        "temperature_requirement": q.temperature_requirement,
        "stacking": q.stacking,
        "sealing": q.sealing,
        "recipient_contact": q.recipient_contact,
        "valid_to": q.valid_to,
        "con_lai_ngay": con_lai,
        "price_basis": q.price_basis or "per_trip",
        "unit_price": _so(q.unit_price),
        "min_qty_per_trip": _so(q.min_qty_per_trip),
        "selling_price": _so(q.selling_price),
        "total_cost": _so(q.total_cost),
        "bien": bien,
        "loi_nhuan": _so(q.selling_price) - _so(q.total_cost),
        "currency_code": q.currency_code or "VND",
        "fx_rate": _so(q.fx_rate, 1),
        "payment_terms": q.payment_terms,
        "waiting_surcharge": _so(q.waiting_surcharge),
        "sales_rep": q.sales_rep,
        "trips_per_month": int(_so(q.trips_per_month)),
        "target_margin": _so(q.target_margin) or None,
        "notes_customer": q.notes_customer,
        "notes_ops": q.notes_ops,
        "notes_internal": q.notes_internal,
        "sent_at": q.sent_at.isoformat() if q.sent_at else None,
        "accepted_at": q.accepted_at.isoformat() if q.accepted_at else None,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "created_by": q.created_by,
    }
    if not kem_chi_tiet:
        return ra
    ra["items"] = [{"line_no": x.line_no, "name": x.name, "quantity": _so(x.quantity),
                    "uom": x.uom, "note": x.note} for x in dong_hang_hoa(db, q.id)]
    ra["so_do_du_kien"] = so_do_du_kien(db, q.id)
    ra["attachments"] = [{
        "id": a.id, "doc_type": a.doc_type, "file_name": a.file_name,
        "storage_url": a.storage_url, "size_bytes": a.size_bytes, "note": a.note,
        "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
        "uploaded_by": a.uploaded_by,
    } for a in db.query(QuotationAttachment).filter(
        QuotationAttachment.quotation_id == q.id).order_by(
        QuotationAttachment.uploaded_at.desc()).all()]
    ra["versions"] = [{
        "version": v.version, "selling_price": _so(v.selling_price),
        "unit_price": _so(v.unit_price), "price_basis": v.price_basis,
        "total_cost": _so(v.total_cost), "note": v.note,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    } for v in db.query(QuotationVersion).filter(
        QuotationVersion.quotation_id == q.id).order_by(
        QuotationVersion.version.desc()).all()]
    cac_do = db.query(DeliveryOrder).filter(
        DeliveryOrder.quotation_id == q.id).order_by(DeliveryOrder.id).all()
    ra["delivery_orders"] = [{
        "id": d.id, "canonical_status": d.canonical_status, "status": d.status,
        "unit_price": _so(d.unit_price), "pickup_date": str(d.pickup_date or ""),
        "delivery_date": str(d.delivery_date or ""), "driver_note": d.driver_note,
    } for d in cac_do]
    ra["so_do"] = len(cac_do)
    ra["so_do_xong"] = sum(1 for d in cac_do if d.canonical_status in ("delivered", "completed"))
    return ra


def danh_sach(db, loc=None):
    """Danh sach bao gia cho man danh sach, kem bien va so ngay con lai."""
    loc = loc or {}
    truy_van = db.query(Quotation)
    if loc.get("customer_id"):
        truy_van = truy_van.filter(Quotation.customer_id == loc["customer_id"])
    if loc.get("route_id"):
        truy_van = truy_van.filter(Quotation.route_id == loc["route_id"])
    if loc.get("owner"):
        truy_van = truy_van.filter(Quotation.created_by == loc["owner"])
    hom_nay = dt.datetime.now().date()
    cac_q = truy_van.order_by(Quotation.created_at.desc()).limit(500).all()
    # DEM MOT LAN cho ca danh sach, khong dem trong vong lap: cot "Lenh giao
    # hang" cua man danh sach can ca so DO du kien va so DO da tach, va dem
    # tung dong nghia la hai truy van moi bao gia — o quy mo hang nghin bao gia
    # thi man danh sach khong mo duoc.
    ma_qs = [q.id for q in cac_q]
    du_kien, da_tach, da_xong = {}, {}, {}
    if ma_qs:
        for ma, tong in db.query(
            QuotationItem.quotation_id, func.sum(QuotationItem.quantity)
        ).filter(QuotationItem.quotation_id.in_(ma_qs)).group_by(
                QuotationItem.quotation_id).all():
            du_kien[ma] = int(_so(tong))
        for ma, dem in db.query(
            DeliveryOrder.quotation_id, func.count(DeliveryOrder.id)
        ).filter(DeliveryOrder.quotation_id.in_(ma_qs)).group_by(
                DeliveryOrder.quotation_id).all():
            da_tach[ma] = int(dem or 0)
        for ma, dem in db.query(
            DeliveryOrder.quotation_id, func.count(DeliveryOrder.id)
        ).filter(DeliveryOrder.quotation_id.in_(ma_qs),
                 DeliveryOrder.canonical_status.in_(("delivered", "completed"))
                 ).group_by(DeliveryOrder.quotation_id).all():
            da_xong[ma] = int(dem or 0)
    ds = []
    for q in cac_q:
        x = _bung_bao_gia(db, q, False, hom_nay)
        x["so_do_du_kien"] = du_kien.get(q.id, 0)
        x["so_do"] = da_tach.get(q.id, 0)
        x["so_do_xong"] = da_xong.get(q.id, 0)
        ds.append(x)

    tim = str(loc.get("q") or "").strip().lower()
    if tim:
        ds = [x for x in ds if tim in " ".join(str(x.get(k) or "").lower() for k in (
            "id", "quote_no", "customer_id", "route_id", "vehicle_type_id",
            "origin", "destination"))]
    trang_thai = str(loc.get("status") or "all")
    if trang_thai == "sap_het_han":
        ds = [x for x in ds if x["con_lai_ngay"] is not None
              and 0 <= x["con_lai_ngay"] <= 7 and x["canonical_status"] not in DA_DONG]
    elif trang_thai == "dang_mo":
        ds = [x for x in ds if x["canonical_status"] not in DA_DONG]
    elif trang_thai != "all":
        ds = [x for x in ds if x["canonical_status"] == trang_thai]
    return ds


def dai_so_lieu(db):
    """Sau con so cua dai KPI — CHINH LA sau bo loc cua man danh sach.

    Con so nao cung phai bam duoc de xem dung nhung dong da dem ra no. Mot con
    so KPI khong bam duoc la mot con so nguoi dung phai tin ma khong kiem lai
    duoc — va luc do khong ai phat hien khi no dem sai.
    """
    hom_nay = dt.datetime.now().date()
    ds = [_bung_bao_gia(db, q, False, hom_nay)
          for q in db.query(Quotation).limit(2000).all()]
    dang_mo = [x for x in ds if x["canonical_status"] not in DA_DONG]
    cho_khach = [x for x in dang_mo if x["canonical_status"] in ("sent", "pending_approval")]
    sap_het = [x for x in dang_mo if x["con_lai_ngay"] is not None
               and 0 <= x["con_lai_ngay"] <= 7]
    da_nhan_chua_tach = [x for x in ds if x["canonical_status"] == "accepted"]
    duoi_nguong = [x for x in dang_mo if x["bien"] is not None
                   and x["bien"] < NGUONG_BIEN_PHAI_DUYET]
    # Ty le chot 30 ngay: mau so la nhung bao gia DA CO KET QUA trong 30 ngay,
    # khong phai moi bao gia da gui — mot bao gia gui hom qua chua co ket qua,
    # dem no vao mau so thi ty le chot luon bi keo xuong mot cach vo co.
    moc = dt.datetime.now() - dt.timedelta(days=30)
    xong = [q for q in db.query(Quotation).filter(Quotation.updated_at >= moc).all()
            if q.canonical_status in ("accepted", "split", "rejected")]
    chot = [q for q in xong if q.canonical_status in ("accepted", "split")]
    return {
        "dang_mo": len(dang_mo),
        "cho_khach_phan_hoi": len(cho_khach),
        "het_han_trong_7_ngay": len(sap_het),
        "da_chap_nhan_chua_tach": len(da_nhan_chua_tach),
        "tien_da_chap_nhan": sum(x["selling_price"] for x in da_nhan_chua_tach),
        "bien_duoi_nguong": len(duoi_nguong),
        "ty_le_chot_30_ngay": (len(chot) / len(xong)) if xong else None,
        "so_chot_30_ngay": len(chot),
        "so_co_ket_qua_30_ngay": len(xong),
        "nguong_bien": NGUONG_BIEN_PHAI_DUYET,
    }


def gia_da_bao_cho_khach(db, ma_khach, ma_tuyen=None, so_ban=3):
    """Vai bao gia gan nhat da bao cho MOT khach — cot phai cua man chi tiet.

    Nguoi ban can biet lan truoc bao bao nhieu truoc khi go mot con so moi. Do
    la thu chan viec bao 3,9 trieu hom nay cho mot khach thang truoc da bao 4,1
    trieu cung tuyen.
    """
    tv = db.query(Quotation).filter(Quotation.customer_id == ma_khach,
                                    Quotation.selling_price.is_not(None))
    if ma_tuyen:
        tv = tv.filter(Quotation.route_id == ma_tuyen)
    ra = []
    for q in tv.order_by(Quotation.created_at.desc()).limit(int(so_ban) + 5).all():
        if _so(q.selling_price) <= 0:
            continue
        ra.append({
            "id": q.id, "quote_no": q.quote_no, "route_id": q.route_id,
            "selling_price": _so(q.selling_price),
            "price_basis": q.price_basis or "per_trip",
            "canonical_status": q.canonical_status,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        })
        if len(ra) >= int(so_ban):
            break
    return ra
