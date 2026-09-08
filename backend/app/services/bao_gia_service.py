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

from models import (
    CostFormula,
    DeliveryOrder,
    Quotation,
    QuotationItem,
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
        pickup_window_start=dong.get("pickup_at"),
        pickup_window_end=dong.get("pickup_at"),
        delivery_window_start=dong.get("due_at"),
        delivery_window_end=dong.get("due_at"),
        pickup_date=dong.get("pickup_at"),
        delivery_date=dong.get("due_at"),
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
