# -*- coding: utf-8 -*-
"""Công cụ cho tác tử: mỗi công cụ là MỘT câu hỏi nghiệp vụ nối vào API EPL đang chạy.

Nguyên tắc:

- Mô hình không được đoán số. Mọi con số trong câu trả lời phải đi qua một công cụ ở đây,
  và công cụ chỉ đọc API thật (`GET`), không ghi. Bản này CHỈ ĐỌC — hành động (điều xe,
  duyệt báo giá…) để pha sau, khi có bước xác nhận đàng hoàng.
- Dữ liệu trả về được CẮT GỌN trước khi đưa cho mô hình. Một dòng của bảng theo dõi mang
  cả đường bộ, mốc, sự kiện, POD — vài chục nghìn ký tự cho một chuyến. Đưa nguyên là ngốn
  token và làm mô hình lạc trong rác. Mỗi công cụ chọn đúng trường người quản lý cần.
- Tiền phải kèm mã tiền tệ CỦA CHỨNG TỪ. Dòng DO không có cột tiền tệ (nó nằm trên báo
  giá), nên công cụ DO tự nối sang báo giá để gắn mã tiền vào — không để mô hình mặc định
  VND rồi nói sai với khách dùng LAK.
"""
import datetime as dt
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

GOC_API = "http://127.0.0.1:8001"
TOKEN = ""
VN = dt.timezone(dt.timedelta(hours=7))


def cau_hinh(goc_api, token):
    global GOC_API, TOKEN
    GOC_API = goc_api.rstrip("/")
    TOKEN = token or ""


class LoiAPI(Exception):
    pass


def goi_api(duong, tham_so=None, timeout=60):
    """GET một đường của EPL, trả JSON. Lỗi nghiệp vụ (4xx) trả về dạng chữ để mô hình
    đọc được lý do — không nuốt."""
    if tham_so:
        sach = {k: v for k, v in tham_so.items() if v not in (None, "", [])}
        if sach:
            duong += ("&" if "?" in duong else "?") + urllib.parse.urlencode(sach)
    yeu_cau = urllib.request.Request(GOC_API + duong, headers={
        "Accept": "application/json",
        **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
    })
    try:
        with urllib.request.urlopen(yeu_cau, timeout=timeout) as tra:
            return json.loads(tra.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as loi:
        than = loi.read().decode("utf-8", "replace")
        try:
            chi_tiet = json.loads(than).get("detail") or json.loads(than)
        except Exception:
            chi_tiet = than[:300]
        raise LoiAPI("HTTP %s tại %s: %s" % (loi.code, duong, chi_tiet))
    except Exception as loi:
        raise LoiAPI("Không gọi được máy chủ EPL (%s): %s" % (GOC_API, loi))


# ------------------------------------------------------------------ cắt gọn
def rut_gon(x, toi_da_muc=40, toi_da_chu=200, sau=0):
    """Thu nhỏ một cấu trúc bất kỳ: bỏ ô trống, chặt danh sách dài, cắt chuỗi dài,
    không đi quá 5 tầng. Dùng cho các điểm cuối chưa có bộ chọn trường riêng."""
    if sau > 5:
        return "…"
    if isinstance(x, dict):
        ra = {}
        for k, v in x.items():
            if v in (None, "", [], {}):
                continue
            if k in ("duong_bo", "segments_geo", "cost_breakdown_json", "events", "legs",
                     "pods", "milestones", "route_segments", "html", "photo_url", "image_url"):
                continue          # hình học, sự kiện thô, ảnh: mô hình không cần
            ra[k] = rut_gon(v, toi_da_muc, toi_da_chu, sau + 1)
        return ra
    if isinstance(x, list):
        phan = [rut_gon(v, toi_da_muc, toi_da_chu, sau + 1) for v in x[:toi_da_muc]]
        if len(x) > toi_da_muc:
            phan.append("… và %d mục nữa (tổng %d)" % (len(x) - toi_da_muc, len(x)))
        return phan
    if isinstance(x, str) and len(x) > toi_da_chu:
        return x[:toi_da_chu] + "…"
    return x


def chon(dong, *truong):
    return {t: dong.get(t) for t in truong if dong.get(t) not in (None, "", [], {})}


def _khop(dong, tim, *truong):
    if not tim:
        return True
    t = tim.lower()
    return any(t in str(dong.get(k) or "").lower() for k in truong)


def _cat(ds, gioi_han):
    gioi_han = max(1, min(int(gioi_han or 30), 200))
    return ds[:gioi_han], len(ds)


def _muc(d):
    """Nhiều điểm cuối bọc danh sách trong `items` hoặc `data`; lấy ra cho gọn."""
    if isinstance(d, dict):
        if isinstance(d.get("items"), list):
            return d["items"]
        if isinstance(d.get("data"), list):
            return d["data"]
        if isinstance(d.get("data"), dict) and isinstance(d["data"].get("items"), list):
            return d["data"]["items"]
    return d if isinstance(d, list) else []


def _lay_het(duong, tham_so=None, co_trang=200, toi_da_trang=10):
    """Đọc HẾT một danh sách phân trang. API EPL chặn `page_size` trên 200 (trả 422), nên
    xin một lần 500 là lỗi ngay — đã vấp thật khi hỏi 'báo giá nào gấp'. Đi từng trang 200
    cho tới khi trang trả ít hơn cỡ trang hoặc đủ `total`."""
    ra, trang = [], 1
    while trang <= toi_da_trang:
        d = goi_api(duong, dict(tham_so or {}, page=trang, page_size=co_trang))
        muc = _muc(d)
        ra.extend(muc)
        tong = d.get("total") if isinstance(d, dict) else None
        if len(muc) < co_trang or (isinstance(tong, int) and len(ra) >= tong):
            break
        trang += 1
    return ra


# ------------------------------------------------------------------ bộ đệm ngắn
_dem = {}
_khoa_dem = threading.Lock()


def _dem_lay(khoa, ham, giay=45):
    """Bộ đệm 45 giây: một câu hỏi thường kéo 2–3 công cụ cùng đọc một danh sách."""
    with _khoa_dem:
        co = _dem.get(khoa)
        if co and time.time() - co[0] < giay:
            return co[1]
    gia_tri = ham()
    with _khoa_dem:
        _dem[khoa] = (time.time(), gia_tri)
    return gia_tri


def _bao_gia_tat_ca():
    return _dem_lay("bao_gia", lambda: _lay_het("/api/quotations"))


def _tien_theo_bao_gia():
    return {q.get("id"): q.get("currency_code") for q in _bao_gia_tat_ca()}


def _khach_hang_ten():
    return _dem_lay("khach", lambda: {c.get("id"): c.get("name")
                                      for c in _muc(goi_api("/api/crm/customers"))})


def _tuyen_ten():
    return _dem_lay("tuyen", lambda: {r.get("id"): r.get("name") for r in goi_api("/api/routes")})


# ================================================================== các công cụ
def tong_quan_hom_nay(_=None):
    """Một lần gọi cho câu 'hôm nay thế nào': số liệu chung, DO theo mức khẩn, sự cố đang
    mở, nguồn lực đội xe, báo giá, cơ hội."""
    stats = goi_api("/api/dashboard/stats")
    pt = goi_api("/api/delivery-orders/analysis")
    doi_xe = (goi_api("/api/fleet/resource-summary") or {}).get("data") or {}
    bg = (goi_api("/api/quotations/summary") or {}).get("data") or {}
    ch = (goi_api("/api/crm/opportunities/summary") or {}).get("data") or {}
    su_co_mo = [i for i in goi_api("/api/incidents") or []
                if str(i.get("status", "")).lower() not in ("resolved", "closed", "completed")]
    # Mỗi lệnh trong nhóm khẩn kèm KHÁCH, TUYẾN, XE, TÀI XẾ ngay tại đây. Đã đo (12/09): khối
    # tổng quan chỉ có mã lệnh, người hỏi tiếp "hai lệnh quá hạn của khách nào" là mô hình bịa
    # ra một tên công ty không tồn tại thay vì gọi công cụ. Có sẵn tên thì không còn chỗ để bịa.
    theo_ma_do = {d.get("id"): d for d in _dem_lay("do", lambda: _lay_het("/api/delivery-orders"))}
    ten_khach = _khach_hang_ten()
    nhom = {}
    for ma, b in (pt.get("buckets") or {}).items():
        lenh = []
        for ma_lenh in (b.get("record_ids") or [])[:8]:
            d = theo_ma_do.get(ma_lenh, {})
            lenh.append({"ma": ma_lenh, "khach": ten_khach.get(d.get("customer_id"), d.get("customer_id")),
                         "tuyen": d.get("origin"), "xe": d.get("vehicle_id"), "tai_xe": d.get("driver_id"),
                         "han_giao": d.get("delivery_window_end")})
        nhom[ma] = {"nhan": b.get("label"), "so": b.get("count"), "lenh": lenh}
    return {
        "thoi_diem": dt.datetime.now(VN).isoformat(timespec="minutes"),
        "so_lieu_chung": stats,
        "lenh_giao_hang_theo_muc_khan": nhom,
        "su_co_dang_mo": [chon(i, "id", "do_id", "vehicle_id", "incident_type", "severity",
                               "location", "status", "reported_at") for i in su_co_mo],
        "doi_xe": {k: doi_xe.get(k) for k in ("vehicles", "drivers", "vehicles_expiring_soon",
                                                 "drivers_expiring_soon", "warn_within_days")},
        "bao_gia": bg,
        "co_hoi": ch,
    }


def phan_tich_lenh_giao_hang(_=None):
    pt = goi_api("/api/delivery-orders/analysis")
    return {"giai_thich": pt.get("logic"), "nhom": {
        ma: {"nhan": b.get("label"), "so": b.get("count"), "ma_lenh": b.get("record_ids"),
             **{k: v for k, v in b.items() if k not in ("label", "count", "record_ids")}}
        for ma, b in (pt.get("buckets") or {}).items()}}


def lenh_giao_hang(a):
    ds = _dem_lay("do", lambda: _lay_het("/api/delivery-orders"))
    ten_khach = _khach_hang_ten()
    # Gắn tên khách TRƯỚC khi lọc: mô hình tìm theo tên ("Samsung Electronics HCMC CE") chứ
    # không biết mã khách ("DEMO-CUS-SAMSUNG") — đã đo thấy trả rỗng oan ngày 12/09.
    ds = [dict(d, customer_name=ten_khach.get(d.get("customer_id"))) for d in ds]
    tt = (a.get("trang_thai") or "all").lower()
    if tt != "all":
        # `arrived` (xe đã tới, chờ ký) vẫn là hàng ĐANG trên đường về nghĩa quản lý.
        nhom = {"in_transit": ("in_transit", "arrived", "dispatched")}.get(tt, (tt,))
        ds = [d for d in ds if (d.get("canonical_status") or "").lower() in nhom]
    ds = [d for d in ds if _khop(d, a.get("tim"), "id", "customer_id", "customer_name", "route_id",
                                 "origin", "destination", "vehicle_id", "driver_id", "quotation_id")]
    tien = _tien_theo_bao_gia()
    ra = []
    for d in ds:
        r = chon(d, "id", "customer_id", "quotation_id", "canonical_status", "status", "origin",
                 "destination", "weight_kg", "volume_m3", "unit_price", "vehicle_id", "driver_id",
                 "pickup_window_start", "pickup_window_end", "delivery_window_start",
                 "delivery_window_end", "seal_no", "cancel_reason")
        r["customer_name"] = d.get("customer_name")
        r["currency_code"] = tien.get(d.get("quotation_id"))
        ra.append(r)
    ra.sort(key=lambda r: r.get("delivery_window_end") or "", reverse=False)
    phan, tong = _cat(ra, a.get("gioi_han"))
    return {"tong_khop": tong, "tra_ve": len(phan), "lenh": phan}


def theo_doi_lenh(a):
    ma = (a.get("do_id") or "").strip()
    if not ma:
        raise LoiAPI("Cần mã lệnh giao hàng (do_id).")
    dong = [d for d in _dem_lay("do", lambda: _lay_het("/api/delivery-orders")) if d.get("id") == ma]
    ket = {"lenh": rut_gon(dong[0]) if dong else "không thấy lệnh %s" % ma}
    if dong:
        ket["lenh"]["currency_code"] = _tien_theo_bao_gia().get(dong[0].get("quotation_id"))
    try:
        theo_doi = goi_api("/api/tracking/%s" % urllib.parse.quote(ma))
        ket["theo_doi"] = rut_gon(theo_doi, toi_da_muc=15)
    except LoiAPI as loi:
        ket["theo_doi"] = str(loi)
    cac_hang = [x for x in (goi_api("/api/tracking/control-tower") or {}).get("items", [])
                if x.get("do_id") == ma]
    ket["chuyen_dang_chay"] = [_dong_thap(x) for x in cac_hang]
    return ket


def _dong_thap(x):
    r = chon(x, "do_id", "trip_id", "trip_status", "status", "customer_name", "route_name",
             "vehicle_id", "driver_id", "driver_name", "driver_phone", "co_driver_name",
             "route_distance_km", "delivery_due", "predicted_eta", "planned_arrival_at",
             "overdue", "awaiting_pod", "open_incident_count", "deviation_km")
    nm = x.get("next_milestone") or {}
    r["moc_ke_tiep"] = nm.get("ten") or nm.get("ma")
    gps = x.get("gps") or {}
    r["gps"] = chon(gps, "status", "observed_at", "speed_kmh", "note")
    r["su_co"] = [chon(i, "incident_type", "severity", "status", "location")
                  for i in (x.get("incidents") or [])[:5]]
    return r


def chuyen_dang_chay(a):
    bang = goi_api("/api/tracking/control-tower") or {}
    ds = bang.get("items") or []
    ds = [x for x in ds if _khop(x, a.get("tim"), "do_id", "trip_id", "customer_name",
                                 "route_name", "vehicle_id", "driver_id", "driver_name")]
    if a.get("chi_tre"):
        ds = [x for x in ds if x.get("overdue")]
    if a.get("chi_cho_ky"):
        ds = [x for x in ds if x.get("awaiting_pod")]
    phan, tong = _cat(ds, a.get("gioi_han"))
    return {"tong_khop": tong, "chi_so": bang.get("kpis"),
            "gps_cu_sau_giay": bang.get("gps_stale_after_seconds"),
            "chuyen": [_dong_thap(x) for x in phan]}


def su_co(a):
    ds = goi_api("/api/incidents") or []
    tt = (a.get("trang_thai") or "open").lower()
    if tt == "open":
        ds = [i for i in ds if str(i.get("status", "")).lower() not in ("resolved", "closed", "completed")]
    elif tt != "all":
        ds = [i for i in ds if str(i.get("status", "")).lower() == tt]
    ds = [i for i in ds if _khop(i, a.get("tim"), "do_id", "vehicle_id", "incident_type",
                                 "location", "description", "severity")]
    ds.sort(key=lambda i: str(i.get("reported_at") or ""), reverse=True)
    phan, tong = _cat(ds, a.get("gioi_han"))
    return {"tong_khop": tong, "su_co": [chon(i, "id", "do_id", "vehicle_id", "incident_type",
                                                 "severity", "status", "location", "description",
                                                 "reporter", "reported_at") for i in phan]}


def bao_gia(a):
    ten_khach = _khach_hang_ten()
    ds = [dict(q, customer_name=ten_khach.get(q.get("customer_id"))) for q in _bao_gia_tat_ca()]
    tt = (a.get("trang_thai") or "all").lower()
    if tt != "all":
        ds = [q for q in ds if (q.get("canonical_status") or "").lower() == tt]
    ds = [q for q in ds if _khop(q, a.get("tim"), "id", "quote_no", "customer_id", "customer_name",
                                 "route_id", "origin", "destination", "cargo_type", "sales_rep")]
    if a.get("tien_te"):
        ds = [q for q in ds if (q.get("currency_code") or "").upper() == a["tien_te"].upper()]
    if a.get("het_han_trong_ngay"):
        han = (dt.datetime.now(VN).date() + dt.timedelta(days=int(a["het_han_trong_ngay"]))).isoformat()
        ds = [q for q in ds if (q.get("valid_to") or "9999") <= han
              and (q.get("canonical_status") or "") not in ("split", "rejected", "expired", "cancelled")]
    ra = []
    for q in ds:
        r = chon(q, "id", "quote_no", "customer_id", "route_id", "origin", "destination",
                 "vehicle_type_id", "cargo_type", "weight_kg", "canonical_status", "status",
                 "currency_code", "selling_price", "total_cost", "discount_percent", "fx_rate",
                 "valid_to", "sent_at", "accepted_at", "close_reason", "sales_rep",
                 "payment_terms", "pickup_window_start", "delivery_window_end")
        r["customer_name"] = q.get("customer_name")
        try:
            gb, gt = float(q.get("selling_price") or 0), float(q.get("total_cost") or 0)
            if gb > 0:
                r["bien_loi_nhuan"] = round((gb - gt) / gb, 3)
        except (TypeError, ValueError):
            pass
        ra.append(r)
    ra.sort(key=lambda r: r.get("valid_to") or "", reverse=False)
    phan, tong = _cat(ra, a.get("gioi_han"))
    tom = (goi_api("/api/quotations/summary") or {}).get("data") or {}
    return {"tong_khop": tong, "tom_luoc": tom, "bao_gia": phan}


def co_hoi(a):
    ds = _lay_het("/api/crm/opportunities", {"stage": a.get("giai_doan"), "q": a.get("tim")})
    ra = [chon(o, "id", "customer_name", "prospect_name", "contact_name", "contact_phone",
               "source", "route_name", "cargo_type", "est_weight_kg", "est_trips_per_month",
               "expected_price", "stage", "owner", "lost_reason", "quotation_id",
               "quotation_status", "next_action_at", "created_at") for o in ds]
    phan, tong = _cat(ra, a.get("gioi_han"))
    tom = (goi_api("/api/crm/opportunities/summary") or {}).get("data") or {}
    return {"tong_khop": tong, "tom_luoc": tom, "co_hoi": phan}


def nguon_luc_doi_xe(_=None):
    return (goi_api("/api/fleet/resource-summary") or {}).get("data") or {}


def xe(a):
    ds = goi_api("/api/vehicles") or []
    ds = [v for v in ds if _khop(v, a.get("tim"), "id", "type", "vehicle_type_name", "brand",
                                 "operational_status", "operational_ref", "depot_code")]
    tt = (a.get("trang_thai") or "all").lower()
    if tt != "all":
        ds = [v for v in ds if (v.get("operational_status") or "").lower() == tt]
    ra = [chon(v, "id", "brand", "vehicle_type_name", "vehicle_type_id", "weight_capacity",
               "volume_capacity_m3", "operational_status", "operational_status_label",
               "operational_ref", "operational_note", "depot_code", "inspection_exp",
               "insurance_date", "maintenance_date", "odometer_km", "dang_quay_ve") for v in ds]
    phan, tong = _cat(ra, a.get("gioi_han"))
    return {"tong_khop": tong, "xe": phan}


def tai_xe(a):
    ds = goi_api("/api/drivers") or []
    ds = [d for d in ds if _khop(d, a.get("tim"), "id", "name", "role", "operational_status",
                                 "assigned_vehicle", "phone")]
    tt = (a.get("trang_thai") or "all").lower()
    if tt != "all":
        ds = [d for d in ds if (d.get("operational_status") or "").lower() == tt]
    ra = [chon(d, "id", "name", "role", "phone", "license_type", "operational_status",
               "operational_status_label", "operational_ref", "assigned_vehicle", "shift",
               "depot_code", "team_code") for d in ds]
    phan, tong = _cat(ra, a.get("gioi_han"))
    return {"tong_khop": tong, "tai_xe": phan}


def khach_hang(a):
    ds = _muc(goi_api("/api/crm/customers"))
    ds = [c for c in ds if _khop(c, a.get("tim"), "id", "name", "contact_person", "address")]
    phan, tong = _cat(ds, a.get("gioi_han"))
    return {"tong_khop": tong, "khach_hang": [rut_gon(c) for c in phan]}


def ho_so_khach_hang(a):
    ma = (a.get("customer_id") or "").strip()
    if not ma:
        raise LoiAPI("Cần mã khách hàng (customer_id).")
    return rut_gon(goi_api("/api/crm/customers/%s/profile" % urllib.parse.quote(ma)), toi_da_muc=20)


def tuyen_duong(a):
    ds = goi_api("/api/routes") or []
    ds = [r for r in ds if _khop(r, a.get("tim"), "id", "name")]
    ra = []
    for r in ds:
        try:
            chang = json.loads(r.get("segments_json") or "[]")
        except Exception:
            chang = []
        ra.append({**chon(r, "id", "name", "distance_km", "bot_fee", "km_duong_bo"),
                   "chang": [{"tu": c.get("from"), "den": c.get("to"), "km": c.get("dist_km")}
                             for c in chang],
                   "diem_thieu_toa_do": r.get("diem_thieu_toa_do") or []})
    return {"tong": len(ra), "tuyen": ra}


def chuyen(a):
    # Bộ giám sát đã làm nóng danh sách chuyến mỗi 15 giây → đọc bộ đệm rồi lọc tại đây.
    ds = _dem_lay("chuyen", lambda: _lay_het("/api/tms/trips"))
    if a.get("trang_thai"):
        ds = [t for t in ds if (t.get("status") or "").lower() == a["trang_thai"].lower()]
    ds = [t for t in ds if _khop(t, a.get("tim"), "id", "vehicle_id", "driver_id",
                                 "freight_order_id")]
    ra = [chon(t, "id", "status", "trip_type", "vehicle_id", "driver_id", "co_driver_id",
               "delivery_order_ids", "planned_departure_at", "planned_arrival_at",
               "actual_departure_at", "actual_arrival_at", "delivery_due_at", "is_late",
               "late_minutes", "behind_plan_minutes", "total_distance_km") for t in ds]
    phan, tong = _cat(ra, a.get("gioi_han"))
    return {"tong_khop": tong, "chuyen": phan}


def doanh_thu(a):
    d = goi_api("/api/tms/reporting/transport-revenue", {
        "date_from": a.get("tu_ngay"), "date_to": a.get("den_ngay"),
        "customer_id": a.get("customer_id"), "vehicle_id": a.get("vehicle_id"),
        "currency_code": a.get("currency_code")})
    return rut_gon(d, toi_da_muc=25)


def ho_so_hoan_tat(a):
    d = goi_api("/api/handover/delivery-orders")
    ds = _muc(d)
    ds = [h for h in ds if _khop(h, a.get("tim"), "do_id", "customer_id", "customer_name",
                                 "route_name", "quotation_id")]
    phan, tong = _cat(ds, a.get("gioi_han"))
    return {"tong_khop": tong, "ghi_chu": (d or {}).get("message"),
            "ho_so": [rut_gon(h, toi_da_muc=10) for h in phan]}


def chi_tiet_hoan_tat(a):
    ma = (a.get("do_id") or "").strip()
    if not ma:
        raise LoiAPI("Cần mã lệnh giao hàng (do_id).")
    return rut_gon(goi_api("/api/handover/delivery-orders/%s" % urllib.parse.quote(ma)), toi_da_muc=30)


def _moc_ngay(gia_tri, cuoi_ngay=False):
    """'2026-09-12' → '2026-09-12T00:00:00+07:00' (hoặc 23:59:59 nếu là mốc cuối).

    Máy chủ EPL từ chối mốc thời gian KHÔNG có múi giờ bằng `TIMEZONE_REQUIRED` — đo thật
    trên `/api/vehicle-maintenance-requests` ngày 12/09. Mô hình thì luôn sinh ngày trần kiểu
    YYYY-MM-DD, nên phải bù múi giờ ở đây chứ không thể trông vào lời dẫn.
    """
    if not gia_tri:
        return None
    chu = str(gia_tri).strip()
    if len(chu) == 10 and chu[4] == "-" and chu[7] == "-":
        return chu + ("T23:59:59+07:00" if cuoi_ngay else "T00:00:00+07:00")
    return chu


def bao_duong(a):
    return rut_gon(goi_api("/api/vehicle-maintenance-requests",
                           {"start": _moc_ngay(a.get("tu_ngay")),
                            "end": _moc_ngay(a.get("den_ngay"), cuoi_ngay=True)}), toi_da_muc=40)


def lich_tai_xe(a):
    ds = goi_api("/api/tms/scheduling/driver-shifts",
                 {"start": a.get("tu_ngay"), "end": a.get("den_ngay")})
    ds = _muc(ds) if not isinstance(ds, list) else ds
    if a.get("driver_id"):
        ds = [s for s in ds if s.get("driver_id") == a["driver_id"]]
    phan, tong = _cat(ds, a.get("gioi_han"))
    return {"tong_khop": tong, "ca": [rut_gon(s) for s in phan]}


def ty_gia(_=None):
    return {"ty_gia_hien_tai": goi_api("/api/currencies"),
            "ghi_chu": "exchange_rate = số VNĐ cho 1 đơn vị tiền đó."}


# ================================================================== khai báo cho Gemini
def _S(mo_ta, **them):
    return {"type": "STRING", "description": mo_ta, **them}


def _I(mo_ta):
    return {"type": "INTEGER", "description": mo_ta}


def _B(mo_ta):
    return {"type": "BOOLEAN", "description": mo_ta}


GIOI_HAN = _I("Số dòng tối đa trả về (mặc định 30, tối đa 200).")
TIM = _S("Chuỗi tìm trong mã, tên khách, tuyến, xe, tài xế… (không phân biệt hoa thường).")

CONG_CU = [
    dict(ten="tong_quan_hom_nay", chay=tong_quan_hom_nay,
         mo_ta="Bức tranh toàn cảnh hôm nay: số liệu chung, lệnh giao hàng theo mức khẩn "
               "(quá hạn, gần trễ, chờ xe, đang chạy, gặp sự cố), sự cố đang mở, xe và tài xế "
               "rảnh/bận, giấy tờ sắp hết hạn, báo giá, cơ hội. GỌI ĐẦU TIÊN khi người dùng hỏi "
               "chung chung kiểu 'hôm nay thế nào', 'có gì cần lo', 'tình hình'.",
         tham_so={}),
    dict(ten="phan_tich_lenh_giao_hang", chay=phan_tich_lenh_giao_hang,
         mo_ta="Lệnh giao hàng (DO) chia theo mức khẩn kèm mã từng lệnh: quá hạn, thiếu hạn, "
               "gần trễ (24 giờ tới), chờ vận chuyển, đang vận chuyển, gặp sự cố.", tham_so={}),
    dict(ten="lenh_giao_hang", chay=lenh_giao_hang,
         mo_ta="Danh sách lệnh giao hàng (DO) kèm khách, tuyến, khung giờ, giá và MÃ TIỀN TỆ của "
               "báo giá gốc, xe và tài xế đã gán.",
         tham_so={"trang_thai": _S("Lọc trạng thái: in_transit gồm cả xe đã tới chờ ký (arrived)",
                                   enum=["all", "pending", "in_transit", "arrived", "delivered", "cancelled"]),
                  "tim": _S("Chuỗi tìm trong mã lệnh, TÊN khách hoặc mã khách, tuyến, xe, tài xế, mã báo giá "
                            "(không phân biệt hoa thường)."),
                  "gioi_han": GIOI_HAN}),
    dict(ten="theo_doi_lenh", chay=theo_doi_lenh,
         mo_ta="Chi tiết MỘT lệnh giao hàng: hồ sơ lệnh, vết GPS và mốc đã ghi, chuyến đang chở "
               "nó (tài xế, xe, mốc kế tiếp, ETA, sự cố).",
         tham_so={"do_id": _S("Mã lệnh, ví dụ DO-2026-0050-DO01")}, bat_buoc=["do_id"]),
    dict(ten="chuyen_dang_chay", chay=chuyen_dang_chay,
         mo_ta="Tháp kiểm soát: mọi chuyến ĐANG CHẠY với tài xế, xe, mốc kế tiếp, ETA, trễ hạn, "
               "chờ ký POD, tình trạng GPS, sự cố. Dùng cho 'xe nào đang ở đâu', 'chuyến nào trễ', "
               "'tài xế X đang chở gì'.",
         tham_so={"tim": TIM, "chi_tre": _B("Chỉ lấy chuyến đã trễ hạn giao"),
                  "chi_cho_ky": _B("Chỉ lấy chuyến đã tới nơi, chờ ký nhận POD"),
                  "gioi_han": GIOI_HAN}),
    dict(ten="su_co", chay=su_co,
         mo_ta="Sự cố trên đường (hư hỏng hàng, tai nạn, kẹt xe, hỏng xe…): loại, mức độ, vị trí, "
               "lệnh và xe liên quan, trạng thái xử lý.",
         tham_so={"trang_thai": _S("open = đang mở (mặc định), all = tất cả, hoặc một trạng thái cụ thể",
                                   enum=["open", "all", "in_progress", "resolved"]),
                  "tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="bao_gia", chay=bao_gia,
         mo_ta="Báo giá cước: khách, tuyến, loại xe, giá bán, giá thành, biên lợi nhuận, TIỀN TỆ, "
               "hạn hiệu lực, trạng thái (draft nháp · pending_approval chờ duyệt · sent đã gửi "
               "khách · split khách đã chấp nhận và đã tách DO · rejected khách từ chối). Kèm tóm "
               "lược: đang mở, chờ khách, hết hạn trong 7 ngày, biên dưới ngưỡng, tỉ lệ chốt.",
         tham_so={"trang_thai": _S("Lọc trạng thái", enum=["all", "draft", "pending_approval",
                                                            "sent", "split", "rejected", "expired"]),
                  "het_han_trong_ngay": _I("Chỉ lấy báo giá còn mở sẽ hết hạn trong N ngày tới"),
                  "tien_te": _S("Chỉ lấy báo giá lập bằng tiền tệ này (Lào Kip = LAK, đô = USD, "
                                "baht = THB, đồng = VND)", enum=["VND", "USD", "THB", "LAK"]),
                  "tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="co_hoi", chay=co_hoi,
         mo_ta="Cơ hội bán hàng (CRM): khách/khách tiềm năng, tuyến, khối lượng dự kiến, giá khách "
               "mong đợi, giai đoạn (new, contacted, negotiating, quoted, won, lost), người phụ trách.",
         tham_so={"giai_doan": _S("Lọc giai đoạn", enum=["new", "contacted", "negotiating",
                                                          "quoted", "won", "lost"]),
                  "tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="nguon_luc_doi_xe", chay=nguon_luc_doi_xe,
         mo_ta="Đội xe và tài xế: tổng, rảnh, đang chạy, bảo dưỡng, ngưng chạy; giấy tờ xe và bằng "
               "lái sắp hết hạn hoặc đã hết hạn (chặn điều phối).", tham_so={}),
    dict(ten="xe", chay=xe,
         mo_ta="Danh sách xe: loại, tải trọng, tình trạng vận hành (available rảnh · on_trip đang "
               "chạy · maintenance xưởng · out_of_service), chuyến đang giữ xe, bãi, hạn đăng kiểm, "
               "bảo hiểm, bảo dưỡng.",
         tham_so={"trang_thai": _S("Lọc tình trạng", enum=["all", "available", "on_trip",
                                                            "maintenance", "out_of_service"]),
                  "tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="tai_xe", chay=tai_xe,
         mo_ta="Danh sách tài xế và phụ xe: vai trò, hạng bằng, tình trạng (available rảnh · on_trip "
               "đang chạy · off_duty nghỉ), chuyến đang giữ, xe được gán, ca.",
         tham_so={"trang_thai": _S("Lọc tình trạng", enum=["all", "available", "on_trip",
                                                            "off_duty", "inactive"]),
                  "tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="khach_hang", chay=khach_hang,
         mo_ta="Danh mục khách hàng kèm số cơ hội đang mở, báo giá đã gửi/chấp nhận, doanh thu đã "
               "chấp nhận, DO đang chạy/đã giao.", tham_so={"tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="ho_so_khach_hang", chay=ho_so_khach_hang,
         mo_ta="Hồ sơ 360° của MỘT khách: cơ hội, báo giá, lệnh giao hàng, doanh thu.",
         tham_so={"customer_id": _S("Mã khách, ví dụ DEMO-CUS-VINAMILK")}, bat_buoc=["customer_id"]),
    dict(ten="tuyen_duong", chay=tuyen_duong,
         mo_ta="Tuyến đường vận chuyển: các chặng, km, phí cầu đường, điểm còn thiếu toạ độ.",
         tham_so={"tim": TIM}),
    dict(ten="chuyen", chay=chuyen,
         mo_ta="Danh sách chuyến (trip) mọi trạng thái: planned, dispatched, in_transit, completed, "
               "cancelled; kèm xe, tài xế, các DO, giờ kế hoạch/thực tế, trễ hay không.",
         tham_so={"trang_thai": _S("Lọc trạng thái", enum=["planned", "dispatched", "in_transit",
                                                            "completed", "cancelled"]),
                  "tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="doanh_thu", chay=doanh_thu,
         mo_ta="Báo cáo doanh thu vận tải theo chuyến đã hoàn tất: doanh thu, giá thành, lãi gộp, "
               "biên; theo ngày, khách, tuyến, loại hàng, tiền tệ. Lọc theo khoảng ngày (YYYY-MM-DD).",
         tham_so={"tu_ngay": _S("Từ ngày YYYY-MM-DD"), "den_ngay": _S("Đến ngày YYYY-MM-DD"),
                  "customer_id": _S("Mã khách"), "vehicle_id": _S("Biển số xe"),
                  "currency_code": _S("Mã tiền tệ", enum=["VND", "USD", "THB", "LAK"])}),
    dict(ten="ho_so_hoan_tat", chay=ho_so_hoan_tat,
         mo_ta="Hồ sơ đã hoàn tất giao hàng (đã ký POD, đã chốt giá) — bộ số liệu bàn giao cho "
               "kế toán.", tham_so={"tim": TIM, "gioi_han": GIOI_HAN}),
    dict(ten="chi_tiet_hoan_tat", chay=chi_tiet_hoan_tat,
         mo_ta="Chi tiết hồ sơ hoàn tất của MỘT lệnh: giá cuối, phụ phí khách trả, giá thành, lợi "
               "nhuận, từng khoản thu chi kèm Acc code, POD.",
         tham_so={"do_id": _S("Mã lệnh giao hàng")}, bat_buoc=["do_id"]),
    dict(ten="bao_duong", chay=bao_duong,
         mo_ta="Phiếu bảo dưỡng / lịch xưởng của xe trong khoảng ngày.",
         tham_so={"tu_ngay": _S("Từ ngày YYYY-MM-DD"), "den_ngay": _S("Đến ngày YYYY-MM-DD")},
         bat_buoc=["tu_ngay", "den_ngay"]),
    dict(ten="lich_tai_xe", chay=lich_tai_xe,
         mo_ta="Ca làm việc / ca nghỉ của tài xế trong khoảng ngày.",
         tham_so={"tu_ngay": _S("Từ ngày YYYY-MM-DD"), "den_ngay": _S("Đến ngày YYYY-MM-DD"),
                  "driver_id": _S("Mã tài xế, ví dụ DEMO-DRV-015"), "gioi_han": GIOI_HAN},
         bat_buoc=["tu_ngay", "den_ngay"]),
    dict(ten="ty_gia", chay=ty_gia,
         mo_ta="Tỷ giá đang áp dụng của các tiền tệ (VND, USD, THB, LAK) so với VNĐ.", tham_so={}),
]

THEO_TEN = {c["ten"]: c for c in CONG_CU}

# Nhãn nghiệp vụ để giao diện hiện "Đã xem: …" — không lộ tên hàm hay đường API.
NHAN = {
    "tong_quan_hom_nay": {"vi": "Tổng quan hôm nay", "en": "Today's overview", "lo": "ພາບລວມມື້ນີ້"},
    "phan_tich_lenh_giao_hang": {"vi": "Phân tích lệnh giao hàng", "en": "Delivery-order analysis", "lo": "ວິເຄາະ DO"},
    "lenh_giao_hang": {"vi": "Lệnh giao hàng", "en": "Delivery orders", "lo": "ໃບສັ່ງປ່ອຍສິນຄ້າ"},
    "theo_doi_lenh": {"vi": "Theo dõi lệnh", "en": "Order tracking", "lo": "ຕິດຕາມ DO"},
    "chuyen_dang_chay": {"vi": "Chuyến đang chạy", "en": "Trips in progress", "lo": "ຖ້ຽວທີ່ກຳລັງແລ່ນ"},
    "su_co": {"vi": "Sự cố", "en": "Incidents", "lo": "ເຫດການ"},
    "bao_gia": {"vi": "Báo giá", "en": "Quotations", "lo": "ໃບສະເໜີລາຄາ"},
    "co_hoi": {"vi": "Cơ hội", "en": "Opportunities", "lo": "ໂອກາດ"},
    "nguon_luc_doi_xe": {"vi": "Nguồn lực đội xe", "en": "Fleet resources", "lo": "ຊັບພະຍາກອນກອງລົດ"},
    "xe": {"vi": "Xe", "en": "Vehicles", "lo": "ລົດ"},
    "tai_xe": {"vi": "Tài xế", "en": "Drivers", "lo": "ຄົນຂັບ"},
    "khach_hang": {"vi": "Khách hàng", "en": "Customers", "lo": "ລູກຄ້າ"},
    "ho_so_khach_hang": {"vi": "Hồ sơ khách hàng", "en": "Customer profile", "lo": "ໂປຣໄຟລ໌ລູກຄ້າ"},
    "tuyen_duong": {"vi": "Tuyến đường", "en": "Routes", "lo": "ເສັ້ນທາງ"},
    "chuyen": {"vi": "Chuyến", "en": "Trips", "lo": "ຖ້ຽວລົດ"},
    "doanh_thu": {"vi": "Doanh thu", "en": "Revenue", "lo": "ລາຍຮັບ"},
    "ho_so_hoan_tat": {"vi": "Hồ sơ hoàn tất", "en": "Completed records", "lo": "ບັນທຶກສຳເລັດ"},
    "chi_tiet_hoan_tat": {"vi": "Chi tiết hoàn tất", "en": "Completion detail", "lo": "ລາຍລະອຽດສຳເລັດ"},
    "bao_duong": {"vi": "Bảo dưỡng xe", "en": "Vehicle maintenance", "lo": "ບຳລຸງຮັກສາລົດ"},
    "lich_tai_xe": {"vi": "Lịch tài xế", "en": "Driver shifts", "lo": "ກະວຽກຄົນຂັບ"},
    "ty_gia": {"vi": "Tỷ giá", "en": "Exchange rates", "lo": "ອັດຕາແລກປ່ຽນ"},
}


def khai_bao_gemini():
    """Danh sách functionDeclarations theo đúng khuôn Gemini."""
    ra = []
    for c in CONG_CU:
        kb = {"name": c["ten"], "description": c["mo_ta"]}
        if c["tham_so"]:
            kb["parameters"] = {"type": "OBJECT", "properties": c["tham_so"]}
            if c.get("bat_buoc"):
                kb["parameters"]["required"] = c["bat_buoc"]
        ra.append(kb)
    return ra


def chay_cong_cu(ten, doi_so):
    """Chạy một công cụ; lỗi trả về dạng chữ để mô hình đọc và nói lại cho người dùng."""
    c = THEO_TEN.get(ten)
    if not c:
        return {"loi": "Không có công cụ tên %s" % ten}
    try:
        return c["chay"](doi_so or {})
    except LoiAPI as loi:
        return {"loi": str(loi)}
    except Exception as loi:                       # lỗi lập trình: vẫn không được sập cả câu
        return {"loi": "Công cụ %s gặp lỗi: %s" % (ten, loi)}
