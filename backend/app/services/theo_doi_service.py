"""Theo dõi xe — biết chuyến giao hàng đang ở đâu.

Nguồn vị trí có ba: GPS thật gửi lên (`gps`), người dùng ghi tay (`manual`), và
mô phỏng cho demo (`simulated`). Demo không có thiết bị GPS, nên nút "chạy
tiếp" nội suy vị trí dọc đường từ kho tới điểm giao — đủ để thấy xe nhích trên
bản đồ và hiểu màn này dùng để làm gì.
"""

import datetime
import math

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from models import Customer, Delivery, PackingList, Route, RouteSegment, SalesOrder, VehiclePosition
from services import giao_hang_service
from services.loi import LoiNghiepVu

# Kho xuất hàng mặc định nếu chưa khai kho trong danh mục: Viêng Chăn.
KHO_MAC_DINH = (17.9757, 102.6331)


def _bay_gio():
    return datetime.datetime.utcnow()


def _khoang_cach_km(a, b):
    """Haversine — đủ chính xác cho việc hiện 'còn bao xa'."""
    r = 6371.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(d))


def _huong(a, b):
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def kho_cua(db, gh=None):
    """Điểm xuất phát: ưu tiên điểm đi của TUYẾN, không có thì lấy kho mặc định."""
    if gh is not None:
        r = tuyen_cua(db, gh)
        if r:
            kh = _diem_dau_tuyen(db, r)
            if kh and kh.lat is not None and kh.lng is not None:
                return (kh.lat, kh.lng), kh.name
    kho = db.query(Customer).filter(Customer.kind == "depot", Customer.lat.isnot(None)).first()
    if kho:
        return (kho.lat, kho.lng), kho.name
    return KHO_MAC_DINH, "Kho Vientiane"


def tuyen_cua(db, gh):
    """Tuyến của chuyến = tuyến trên Packing List đầu tiên còn hiệu lực."""
    for pl in gh.packing_lists:
        if pl.status == "cancelled" or not pl.route_id:
            continue
        r = db.query(Route).filter(Route.id == pl.route_id).first()
        if r:
            return r
    return None


def lo_trinh_cua(db, gh):
    """Danh sách điểm dọc tuyến, để bản đồ vẽ đúng lộ trình A → B → C."""
    r = tuyen_cua(db, gh)
    if not r:
        return []
    chang = (
        db.query(RouteSegment)
        .filter(RouteSegment.route_id == r.id)
        .order_by(RouteSegment.seq)
        .all()
    )
    if not chang:
        return []
    can = [x for c in chang for x in (c.from_id, c.to_id) if x]
    diem = {}
    if can:
        for kh in db.query(Customer).filter(Customer.id.in_(set(can))).all():
            diem[kh.id] = kh

    ra = []
    for c in chang:
        for khoa, ten in ((c.from_id, c.from_name), (c.to_id, c.to_name)):
            kh = diem.get(khoa)
            if not kh or kh.lat is None or kh.lng is None:
                continue
            if ra and ra[-1]["lat"] == kh.lat and ra[-1]["lng"] == kh.lng:
                continue
            ra.append({"lat": kh.lat, "lng": kh.lng, "name": ten or kh.name})
    return ra


def _diem_cuoi_tuyen(db, r):
    chang = (
        db.query(RouteSegment)
        .filter(RouteSegment.route_id == r.id)
        .order_by(RouteSegment.seq.desc())
        .first()
    )
    if chang and chang.to_id:
        return db.query(Customer).filter(Customer.id == chang.to_id).first()
    return None


def _diem_dau_tuyen(db, r):
    chang = (
        db.query(RouteSegment)
        .filter(RouteSegment.route_id == r.id)
        .order_by(RouteSegment.seq)
        .first()
    )
    if chang and chang.from_id:
        return db.query(Customer).filter(Customer.id == chang.from_id).first()
    return None


def diem_giao_cua(db, gh):
    """Điểm giao: ưu tiên điểm cuối của TUYẾN, không có thì lấy toạ độ khách."""
    r = tuyen_cua(db, gh)
    if r:
        kh = _diem_cuoi_tuyen(db, r)
        if kh and kh.lat is not None and kh.lng is not None:
            return (kh.lat, kh.lng), kh.name

    for pl in gh.packing_lists:
        if pl.status == "cancelled":
            continue
        don = pl.order
        if don and don.customer_id:
            kh = db.query(Customer).filter(Customer.id == don.customer_id).first()
            if kh and kh.lat is not None and kh.lng is not None:
                return (kh.lat, kh.lng), kh.name
        if don and don.ship_to_name:
            return None, don.ship_to_name
    return None, None


def moc_moi_nhat(db, gh_id):
    return (
        db.query(VehiclePosition)
        .filter(VehiclePosition.delivery_id == gh_id)
        .order_by(VehiclePosition.recorded_at.desc(), VehiclePosition.id.desc())
        .first()
    )


def _moc_ra_dict(m):
    return {
        "lat": m.lat,
        "lng": m.lng,
        "speed_kmh": m.speed_kmh,
        "heading": m.heading,
        "progress": m.progress,
        "source": m.source,
        "note": m.note,
        "recorded_at": m.recorded_at,
    }


def tinh_trang_chuyen(db, gh):
    """Gói đủ thứ màn Theo dõi cần cho MỘT chuyến."""
    kho, ten_kho = kho_cua(db, gh)
    dich, ten_dich = diem_giao_cua(db, gh)
    moc = moc_moi_nhat(db, gh.id)

    con_km = None
    cu = None
    if moc:
        cu = (_bay_gio() - moc.recorded_at).total_seconds() > 15 * 60
        if dich:
            con_km = round(_khoang_cach_km((moc.lat, moc.lng), dich), 1)
    tong_km = round(_khoang_cach_km(kho, dich), 1) if dich else None

    r = tuyen_cua(db, gh)
    return {
        "delivery": giao_hang_service.ra_dict(gh, day_du=False),
        "route": {"code": r.code, "name": r.name, "distance_km": r.distance_km} if r else None,
        "path": lo_trinh_cua(db, gh),
        "orders": sorted({pl.so_id for pl in gh.packing_lists if pl.status != "cancelled"}),
        "packing_lists": [pl.id for pl in gh.packing_lists if pl.status != "cancelled"],
        "depot": {"lat": kho[0], "lng": kho[1], "name": ten_kho},
        "destination": {"lat": dich[0], "lng": dich[1], "name": ten_dich} if dich else {"name": ten_dich},
        "position": _moc_ra_dict(moc) if moc else None,
        "stale": cu,
        "remaining_km": con_km,
        "route_km": tong_km,
    }


def tong_quan(db):
    """Mọi chuyến đang trên đường hoặc sắp đi — đây là danh sách bên trái bản đồ."""
    ds = (
        db.query(Delivery)
        .options(selectinload(Delivery.packing_lists).selectinload(PackingList.order))
        .filter(Delivery.status.in_(["planned", "loading", "in_transit", "arrived"]))
        .order_by(Delivery.created_at.desc())
        .all()
    )
    return [tinh_trang_chuyen(db, gh) for gh in ds]


def vet_duong(db, gh_id, gioi_han=500):
    ds = (
        db.query(VehiclePosition)
        .filter(VehiclePosition.delivery_id == gh_id)
        .order_by(VehiclePosition.recorded_at.asc(), VehiclePosition.id.asc())
        .limit(gioi_han)
        .all()
    )
    return [_moc_ra_dict(m) for m in ds]


def ghi_vi_tri(db, gh_id, payload, nguon="manual"):
    """Ghi một mốc GPS. Đây cũng là điểm cuối mà thiết bị hoặc app tài xế gọi."""
    gh = giao_hang_service.nap(db, gh_id)
    if gh.status in ("delivered", "cancelled"):
        raise LoiNghiepVu("TRK_DELIVERY_CLOSED", "Chuyến đã đóng nên không ghi vị trí nữa", 409)
    try:
        lat = float(payload.get("lat"))
        lng = float(payload.get("lng"))
    except (TypeError, ValueError):
        raise LoiNghiepVu("TRK_BAD_COORD", "Toạ độ không hợp lệ")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise LoiNghiepVu("TRK_BAD_COORD", "Toạ độ ngoài phạm vi")

    kho, _ = kho_cua(db, gh)
    dich, _ = diem_giao_cua(db, gh)
    tien_do = 0.0
    if dich:
        tong = _khoang_cach_km(kho, dich) or 1
        tien_do = max(0.0, min(1.0, 1 - _khoang_cach_km((lat, lng), dich) / tong))

    m = VehiclePosition(
        delivery_id=gh.id,
        lat=lat,
        lng=lng,
        speed_kmh=float(payload.get("speed_kmh") or 0),
        heading=float(payload["heading"]) if payload.get("heading") not in (None, "") else None,
        progress=float(payload.get("progress")) if payload.get("progress") is not None else tien_do,
        source=payload.get("source") or nguon,
        note=payload.get("note"),
        recorded_at=_bay_gio(),
    )
    db.add(m)
    db.flush()
    return tinh_trang_chuyen(db, gh)


def mo_phong_chay_tiep(db, gh_id, buoc=0.15, nguoi="demo"):
    """Nhích xe thêm một đoạn dọc đường kho → điểm giao. Chỉ dùng cho demo.

    Tới đích (progress ≥ 1) thì tự đẩy chuyến sang 'đã tới nơi' nếu nó đang
    trên đường — để người xem thấy bản đồ và trạng thái khớp nhau.
    """
    gh = giao_hang_service.nap(db, gh_id)
    if gh.status in ("delivered", "cancelled"):
        raise LoiNghiepVu("TRK_DELIVERY_CLOSED", "Chuyến đã đóng nên không chạy tiếp được", 409)
    kho, _ = kho_cua(db, gh)
    dich, ten = diem_giao_cua(db, gh)
    if not dich:
        raise LoiNghiepVu(
            "TRK_NO_DESTINATION",
            "Khách của chuyến chưa có toạ độ — khai toạ độ ở danh mục khách hàng trước",
            409,
            {"destination": ten},
        )
    moc = moc_moi_nhat(db, gh.id)
    tien_do = min(1.0, (moc.progress if moc else 0.0) + buoc)
    lat = kho[0] + (dich[0] - kho[0]) * tien_do
    lng = kho[1] + (dich[1] - kho[1]) * tien_do
    toc_do = 0 if tien_do >= 1 else 45 + (hash(gh.id) % 15)

    m = VehiclePosition(
        delivery_id=gh.id,
        lat=round(lat, 6),
        lng=round(lng, 6),
        speed_kmh=toc_do,
        heading=round(_huong(kho, dich), 1),
        progress=round(tien_do, 4),
        source="simulated",
        note="Mô phỏng cho demo",
        recorded_at=_bay_gio(),
    )
    db.add(m)
    db.flush()

    if tien_do >= 1 and gh.status == "in_transit":
        giao_hang_service.doi_trang_thai(db, gh.id, "arrived", nguoi, "Xe tới điểm giao (mô phỏng)")
        gh = giao_hang_service.nap(db, gh.id)
    return tinh_trang_chuyen(db, gh)
