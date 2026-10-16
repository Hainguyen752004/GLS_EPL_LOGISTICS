# -*- coding: utf-8 -*-
"""Trạm thu phí dọc tuyến (16/10, anh Hải: «anh đi đường container — tính trạm thu phí các thứ để phiếu xuất xe có sẵn phí»).

Anh chọn 16/10:
  · MỘT giá cho xe của EPL ở mỗi trạm (đầu kéo + rơ-moóc / container; bên Việt Nam là xe loại 5) — giá ở danh mục trạm;
  · tuyến có km chiều về thì cộng cả lượt về, trừ trạm chỉ thu một chiều (`one_way`);
  · phiếu xuất xe có MỖI TRẠM MỘT DÒNG mục IV «Phí cao tốc · tên trạm», số lượng = số lượt, tiền tệ của trạm.

VỊ TRÍ TRẠM lấy từ OpenStreetMap (barrier=toll_booth) của Lào và Việt Nam, tải một lần và đóng gói ở tram_thu_phi_osm.json — máy chủ
Overpass công cộng chậm (40–50 giây một lần hỏi, hay báo 502) nên không hỏi lúc người dùng bấm. Mỗi trạm OSM thường là hai điểm (mỗi
chiều một điểm) — đã gộp sẵn. Giá trong OSM chỉ có lẻ tẻ cho xe con nên KHÔNG lấy; kế toán nhập giá cho xe EPL.

TÌM TRẠM DỌC TUYẾN: màn Tuyến đường gửi lên đường xe tải đã vẽ (Valhalla, chế độ xe tải); trạm nằm cách đường ≤ NGUONG_M mét là xe đi
qua. Ngưỡng nhỏ có chủ ý: trạm ở nút giao cao tốc nằm trên đường nhánh, cách đường chính vài chục mét trở lên — ngưỡng rộng là kéo
nhầm trạm của nút giao xe chỉ chạy ngang qua.
"""
import json
import math
import os

from models import RouteToll, TollStation

TEP_OSM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tram_thu_phi_osm.json")
NGUONG_M = 45                 # trạm cách đường xe đi tối đa (mét)
GAN_M = 1500                  # trạm cách đường ≤ 1,5 km: GỢI Ý «gần đường» — máy chỉ đường có khi chọn đường tắt khác đường xe hay chạy
GHEP_M = 300                  # trạm OSM cách trạm đã có trong danh mục ≤ 300 m → cùng một trạm
TIEN_TE_NUOC = {"LA": "LAK", "VN": "VND", "TH": "THB"}
NUOC = tuple(TIEN_TE_NUOC)
_OSM = {}


def ds_osm():
    """Các trạm OSM đã gộp: [{ref, name, lat, lng, country}]. Không có tệp → rỗng (tìm trạm chỉ dò trong danh mục)."""
    if "ds" not in _OSM:
        try:
            with open(TEP_OSM, encoding="utf-8") as f:
                _OSM["ds"] = json.load(f).get("tram", [])
        except (OSError, ValueError):
            _OSM["ds"] = []
    return _OSM["ds"]


def m_giua(a, b):
    """Khoảng cách (mét) giữa hai điểm (lat, lng) — phép chiếu phẳng, đủ đúng ở khoảng vài trăm km."""
    x = math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
    y = math.radians(b[0] - a[0])
    return 6371000.0 * math.hypot(x, y)


def _chieu(p, a, b):
    """(khoảng cách mét từ p tới đoạn ab, tỷ lệ t trên đoạn)."""
    kx = math.cos(math.radians(p[0])) * 111320.0
    ky = 110540.0
    ax, ay = (a[1] - p[1]) * kx, (a[0] - p[0]) * ky
    bx, by = (b[1] - p[1]) * kx, (b[0] - p[0]) * ky
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / l2))
    return math.hypot(ax + t * dx, ay + t * dy), t


def doc_tuyen(duong, ung_vien, nguong=NGUONG_M):
    """Ứng viên cách đường xe đi ≤ `nguong` mét. `duong` = [[lat, lng], …] theo chiều đi; `ung_vien` = [{lat, lng, …}].
    Trả [(ứng viên, km tính từ đầu đường, cách đường mét)] theo thứ tự xe đi qua."""
    diem = [(float(p[0]), float(p[1])) for p in duong if p and len(p) >= 2]
    if len(diem) < 2:
        return []
    # km cộng dồn tới từng điểm của đường + khung bao từng khúc 64 điểm (lọc nhanh trước khi đo từng đoạn)
    cong = [0.0]
    for i in range(1, len(diem)):
        cong.append(cong[-1] + m_giua(diem[i - 1], diem[i]))
    dem = max(0.0006, nguong / 100000.0)                 # khung bao nới ra bằng ngưỡng (≈ độ)
    khuc = []
    for s in range(0, len(diem) - 1, 64):
        e = min(len(diem) - 1, s + 64)
        la = [p[0] for p in diem[s:e + 1]]; lo = [p[1] for p in diem[s:e + 1]]
        khuc.append((s, e, min(la) - dem, max(la) + dem, min(lo) - dem, max(lo) + dem))
    ra = []
    for u in ung_vien:
        if u.get("lat") is None or u.get("lng") is None:
            continue
        p = (float(u["lat"]), float(u["lng"]))
        tot = None
        for s, e, la0, la1, lo0, lo1 in khuc:
            if not (la0 <= p[0] <= la1 and lo0 <= p[1] <= lo1):
                continue
            for i in range(s, e):
                d, t = _chieu(p, diem[i], diem[i + 1])
                if d <= nguong and (tot is None or d < tot[0]):
                    tot = (d, cong[i] + t * (cong[i + 1] - cong[i]))
        if tot is not None:
            ra.append((u, tot[1] / 1000.0, tot[0]))
    ra.sort(key=lambda x: x[1])
    return ra


def _ref(s):
    return set(str(s or "").split())


def ghep(db, ung_vien, ten_tuyen=""):
    """Ứng viên OSM (đã nằm trên tuyến) → trạm trong danh mục: cùng điểm OSM, hoặc cách trạm đã có ≤ GHEP_M mét → dùng trạm đó; chưa
    có → thêm trạm mới (chưa có giá). Trả [(TollStation, km)] theo thứ tự cũ."""
    co = db.query(TollStation).all()
    ra = []
    for u, km, *_ in ung_vien:
        st = next((s for s in co if u.get("_id") and s.id == u["_id"]), None)             or next((s for s in co if _ref(s.osm_ref) & _ref(u.get("ref"))), None)
        if st is None:
            gan = [(m_giua((s.lat, s.lng), (u["lat"], u["lng"])), s) for s in co if s.lat is not None and s.lng is not None]
            gan = [x for x in gan if x[0] <= GHEP_M]
            st = min(gan, key=lambda x: x[0])[1] if gan else None
        if st is None:
            nuoc = u.get("country") if u.get("country") in NUOC else "LA"
            # trạm chưa có tên trên bản đồ: tên ngắn theo km dọc tuyến, tuyến nào dò ra thì ghi vào ghi chú (người dùng đổi tên sau)
            ten = (u.get("name") or "").strip() or (("ດ່ານເກັບຄ່າທາງ km %d" if nuoc == "LA" else "Trạm thu phí km %d") % round(km))
            ghi = (("ເພີ່ມຕອນຊອກດ່ານເສັ້ນທາງ %s" if nuoc == "LA" else "Thêm khi dò tuyến %s") % ten_tuyen) if ten_tuyen else None
            st = TollStation(name=ten[:200], country=nuoc, currency=TIEN_TE_NUOC[nuoc], lat=u["lat"], lng=u["lng"],
                             osm_ref=u.get("ref"), note=ghi, one_way=False, active=True)
            db.add(st); db.flush(); co.append(st)
        elif u.get("ref") and not (_ref(u.get("ref")) <= _ref(st.osm_ref)):
            st.osm_ref = " ".join(sorted(_ref(st.osm_ref) | _ref(u.get("ref"))))
        if all(x[0].id != st.id for x in ra):
            ra.append((st, km))
    return ra


def luot(r, st):
    """Số lượt qua trạm của một chuyến: chiều đi 1; tuyến có km chiều về và trạm thu cả hai chiều thì thêm lượt về."""
    return 1 + (1 if (r.return_km or 0) > 0 and not st.one_way else 0)


def tram_cua(db, r):
    """[(RouteToll, TollStation)] của tuyến, theo thứ tự xe đi qua; bỏ trạm đã ngưng dùng."""
    if r is None or not getattr(r, "id", None):
        return []
    return [(rt, st) for rt, st in db.query(RouteToll, TollStation).join(TollStation, TollStation.id == RouteToll.station_id)
            .filter(RouteToll.route_id == r.id).order_by(RouteToll.seq).all() if st.active]


def xuat_tram(st, thay_gia=True, so_tuyen=None):
    ra = {"id": st.id, "name": st.name, "country": st.country, "currency": st.currency, "lat": st.lat, "lng": st.lng,
          "one_way": bool(st.one_way), "osm_ref": st.osm_ref, "note": st.note, "active": bool(st.active), "co_gia": st.fee is not None}
    if thay_gia:
        ra["fee"] = st.fee
    if so_tuyen is not None:
        ra["so_tuyen"] = so_tuyen
    return ra


def dong_phieu(db, r):
    """Dòng mục IV của phiếu theo trạm trên tuyến — mỗi trạm một dòng (anh Hải 16/10). Đơn giá trống khi trạm chưa có giá (kế toán
    nhập lúc kiểm). Có `toll_station_id` để máy chủ tự lấy giá trạm khi Bãi lập phiếu (Bãi không gửi giá)."""
    ra = []
    for _rt, st in tram_cua(db, r):
        ra.append({"section": "travel", "item_key": "x_toll", "item_name": st.name, "qty": luot(r, st),
                   "unit_price": st.fee or 0, "currency": st.currency or TIEN_TE_NUOC.get(st.country, "LAK"),
                   "toll_station_id": st.id})
    return ra


def gia_tram(db, station_id):
    """(đơn giá, tiền tệ) của trạm — dòng phí cao tốc theo trạm mà người lập không được đặt giá. Không có trạm / chưa có giá → None."""
    st = db.get(TollStation, station_id) if station_id else None
    if st is None or st.fee is None:
        return None
    return float(st.fee), st.currency or "LAK"
