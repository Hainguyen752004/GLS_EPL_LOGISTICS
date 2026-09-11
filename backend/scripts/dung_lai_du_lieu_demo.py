# -*- coding: utf-8 -*-
"""Dựng lại dữ liệu demo từ con số 0 — giữ dữ liệu gốc, gieo lại qua API THẬT.

Chủ dự án (11/09/2026): *"xóa hết dựng từ con số 0 đi nhé chỉ giữ lại dữ liệu gốc
(khách, tuyến, loại xe, xe, tài xế, công thức, Acc code) — sau khi xóa xong em import
dữ liệu chuẩn cho anh nhé đa dạng loại và dữ liệu"*.

HAI BƯỚC, chạy tách nhau để nhìn được từng bước:

    cd backend\\app
    python ..\\scripts\\dung_lai_du_lieu_demo.py --xoa      # bước 1: xoá dữ liệu vận hành
    python ..\\scripts\\dung_lai_du_lieu_demo.py --gieo     # bước 2: gieo case qua API 8001
    python ..\\scripts\\dung_lai_du_lieu_demo.py --gieo-ngoai-te  # thêm 2 case LAK/USD trọn luồng
    python ..\\scripts\\dung_lai_du_lieu_demo.py --kiem     # đếm lại từng bảng

BƯỚC 1 (--xoa) nối thẳng PostgreSQL (database.py của ứng dụng), TRUNCATE mọi bảng
vận hành trong MỘT giao dịch, trả xe và tài xế về trạng thái rảnh, xoá tệp đính kèm
báo giá trong `uploads/quotations`. Bảng GIỮ: customers, locations, routes,
vehicle_types, vehicles, vehicle_cost_overrides, drivers, driver_qualifications,
carriers, cost_formulas, account_mappings, currencies*, finance_control_config,
roles, users, schema_migrations.

BƯỚC 2 (--gieo) KHÔNG ghi thẳng vào DB. Mọi bản ghi đi qua API của máy chủ đang chạy
(mặc định http://127.0.0.1:8001, token đọc từ `.env` — không in ra), đúng đường người
dùng bấm trên màn: cơ hội → báo giá → gửi → (duyệt nội bộ) → khách chấp nhận → DO
sinh tự động → lập chuyến → điều phối → mốc thực thi → POD + hoàn tất → chi phí thực
tế. Vì thế mọi cửa chặn (bằng lái, ca trực, hạn xe, tải trọng, Packing List) đều bị
thử thật; một case rớt là script dừng và in nguyên phản hồi.

Các case cố ý ĐA DẠNG (xem `gieo()` để biết từng case làm gì):
  A  Nidec      Container 20FT, 3 cont → 3 DO: 1 đã hoàn tất (có khách trả thêm + chi
                phí thực tế đã gửi duyệt), 1 đang chạy giữa đường, 1 chờ điều phối
                (đã lập chuyến rồi HUỶ chuyến để có mẫu huỷ).
  B  Unilever   Đầu kéo 40', 2 cont đi CHUNG MỘT CHUYẾN có phụ xe, chiết khấu 5%,
                cả hai hoàn tất, có sự cố ghi trên đường, chi phí thực tế có Acc code.
  C  Colgate    Xe tải 10 tấn, hàng đếm theo KIỆN → lập Packing List, quét QR 3 bước
                rồi mới điều phối được; hoàn tất không phụ phí.
  D  Pou Yuen   Xe tải 15 tấn, biên MỎNG (<15%) → chờ duyệt nội bộ → duyệt → gửi →
                khách chấp nhận → 1 DO đã lập chuyến, CHƯA điều phối (nằm ở Điều phối).
  E  SGN Food   Xe lạnh 5 tấn, báo giá USD đang CHỜ KHÁCH; một báo giá khác bị khách
                TỪ CHỐI; một báo giá còn NHÁP có tệp đính kèm.
  F  CRM        Cơ hội ở đủ giai đoạn: mới, đã liên hệ, đang đàm phán, mất.
  G  SGN Food   (--gieo-ngoai-te) báo giá bằng LAK, xe lạnh, đi trọn luồng tới hoàn tất; hồ sơ
                bàn giao bằng LAK, chi phí thực tế bằng VND.
  H  Pou Yuen   (--gieo-ngoai-te) báo giá bằng USD, đầu kéo 20' có đơn giá dầu riêng của xe, đi
                trọn luồng tới hoàn tất; hồ sơ bàn giao bằng USD.

Chi phí thực tế dừng ở `submitted`: cấu hình bốn mắt đang BẬT và máy chủ 8001 chạy
với một danh tính duy nhất (EPL_TMS_API_PRINCIPAL), nên người duyệt phải là người
khác — đúng luật, không lách.
"""
import argparse
import datetime as dt
import io
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

GOC = Path(__file__).resolve().parents[2]
APP = GOC / "backend" / "app"
sys.path.insert(0, str(APP))
os.chdir(APP)

BASE = os.getenv("EPL_API_BASE", "http://127.0.0.1:8001")
VN = dt.timezone(dt.timedelta(hours=7))

# ---------------------------------------------------------------- bảng
BANG_GIU = (
    "customers", "locations", "routes", "vehicle_types", "vehicles", "vehicle_cost_overrides",
    "drivers", "driver_qualifications", "carriers", "cost_formulas", "account_mappings",
    "currencies", "currency_definitions", "currency_rate_history", "finance_control_config",
    "roles", "users", "schema_migrations",
)
#: Thứ tự không quan trọng vì TRUNCATE cả danh sách trong một câu; nhưng danh sách
#: phải ĐỦ mọi bảng có khoá ngoại trỏ vào nhau, không thì PostgreSQL từ chối.
BANG_XOA = (
    "audit_logs", "idempotency_records", "migration_quarantine",
    "crm_opportunities",
    "quotation_attachments", "quotation_items", "quotation_versions", "quotations",
    "delivery_order_charge_adjustments", "delivery_order_closeouts",
    "delivery_pod_documents", "delivery_pod_records", "delivery_orders",
    "trip_delivery_orders", "transport_trip_legs", "transport_trips", "transport_demands",
    "freight_order_units", "freight_units", "freight_order_legacy_links", "freight_orders",
    "resource_assignments", "driver_shift_assignments",
    "transport_event_documents", "transport_events", "vehicle_tracking", "incidents",
    "freight_charge_items", "freight_cost_documents", "freight_actual_costs", "epl_expense_vouchers",
    "parking_events", "parking_labels", "parking_list_items", "parking_lists",
    "warehouse_appointments", "tender_offers", "tenders",
    "vehicle_maintenance_cost_lines", "vehicle_maintenance_requests",
)


def _in(*a):
    print(*a, flush=True)


# ================================================================ BƯỚC 1
def xoa():
    import database
    from sqlalchemy import text

    with database.engine.connect() as c:
        co = {r[0] for r in c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))}
    la = co - set(BANG_GIU) - set(BANG_XOA)
    if la:
        raise SystemExit("Bảng chưa được xếp vào GIỮ hay XOÁ: %s — bổ sung rồi chạy lại." % sorted(la))
    xoa_that = [b for b in BANG_XOA if b in co]

    with database.engine.begin() as c:
        truoc = {b: c.execute(text('SELECT count(*) FROM "%s"' % b)).scalar() for b in xoa_that}
        _in("Trước khi xoá (%d bảng vận hành, %d dòng):" % (len(xoa_that), sum(truoc.values())))
        for b, n in truoc.items():
            if n:
                _in("   %-38s %6d" % (b, n))
        c.execute(text("TRUNCATE TABLE %s" % ", ".join('"%s"' % b for b in xoa_that)))
        # Xe / tài xế đang ghi "Đang thực hiện TRIP-..." của chuyến vừa xoá → trả về rảnh.
        c.execute(text("UPDATE vehicles SET status='Sẵn sàng', operational_status='available', "
                       "operational_ref=NULL, operational_note=NULL, operational_updated_at=NULL"))
        c.execute(text("UPDATE drivers SET status='🟢 Rảnh (Sẵn sàng)', operational_status='available', "
                       "operational_ref=NULL, operational_note=NULL, operational_updated_at=NULL, "
                       "assigned_vehicle='Chưa gán'"))
        sau = sum(c.execute(text('SELECT count(*) FROM "%s"' % b)).scalar() for b in xoa_that)
        _in("Sau khi xoá: %d dòng trong các bảng vận hành." % sau)
        giu = {b: c.execute(text('SELECT count(*) FROM "%s"' % b)).scalar() for b in BANG_GIU if b in co}
        _in("Dữ liệu gốc GIỮ:", ", ".join("%s=%d" % kv for kv in giu.items()))

    tep = GOC / "backend" / "uploads" / "quotations"
    n = 0
    if tep.is_dir():
        for f in tep.iterdir():
            if f.is_file():
                f.unlink()
                n += 1
    _in("Đã xoá %d tệp đính kèm báo giá trong uploads/quotations." % n)


# ================================================================ HTTP
def _env(ten):
    for dong in (GOC / ".env").read_text(encoding="utf-8").splitlines():
        if dong.strip().startswith(ten + "="):
            return dong.split("=", 1)[1].strip()
    return os.getenv(ten, "")


TOKEN = os.getenv("EPL_TMS_API_TOKEN") or _env("EPL_TMS_API_TOKEN")


class LoiAPI(Exception):
    pass


def goi(method, path, body=None, headers=None, files=None, form=None, cho_phep=(200, 201)):
    """Gọi API, in một dòng tóm tắt; lỗi thì in nguyên phản hồi và dừng."""
    h = {"Accept": "application/json", "Authorization": "Bearer " + TOKEN}
    h.update(headers or {})
    data = None
    if files is not None or form is not None:
        ranh = "----epl" + uuid.uuid4().hex
        buf = io.BytesIO()
        for k, v in (form or {}).items():
            buf.write(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n" % (ranh, k)).encode())
            buf.write((v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)).encode("utf-8"))
            buf.write(b"\r\n")
        for k, (ten, noi_dung, mime) in (files or {}).items():
            buf.write(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                       "Content-Type: %s\r\n\r\n" % (ranh, k, ten, mime)).encode())
            buf.write(noi_dung)
            buf.write(b"\r\n")
        buf.write(("--%s--\r\n" % ranh).encode())
        data = buf.getvalue()
        h["Content-Type"] = "multipart/form-data; boundary=" + ranh
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urlopen(req, timeout=120) as r:
            ma = r.status
            noi = r.read().decode("utf-8")
    except HTTPError as e:
        ma = e.code
        noi = e.read().decode("utf-8", "replace")
    try:
        goi_tra = json.loads(noi) if noi else {}
    except ValueError:
        goi_tra = {"raw": noi}
    tom = goi_tra.get("message") if isinstance(goi_tra, dict) else ""
    _in("  %s %-62s → %s %s" % (method, path, ma, (tom or "")[:90]))
    if ma not in cho_phep:
        _in("  PHẢN HỒI:", json.dumps(goi_tra, ensure_ascii=False)[:1500])
        raise LoiAPI("%s %s → %s" % (method, path, ma))
    return goi_tra


def _du_lieu(goi_tra):
    return goi_tra.get("data") if isinstance(goi_tra, dict) and "data" in goi_tra else goi_tra


def _iso(t):
    return t.isoformat()


def _png(nhan):
    return (nhan + ".png", b"\x89PNG\r\n\x1a\n" + nhan.encode("utf-8"), "image/png")


# ================================================================ các bước nghiệp vụ
def co_hoi(**than):
    mau = {"contact_name": "Chị Lan", "contact_phone": "0901234567", "source": "phone",
           "cargo_type": "Hàng khô", "est_weight_kg": 10000, "est_trips_per_month": 4}
    mau.update(than)
    return _du_lieu(goi("POST", "/api/crm/opportunities", mau))


def doi_giai_doan(o, stage, lost_reason=None):
    than = {"stage": stage, "expected_version": o["version"]}
    if lost_reason:
        than["lost_reason"] = lost_reason
    return _du_lieu(goi("PUT", "/api/crm/opportunities/%s/stage" % o["id"], than))


def bao_gia_tu_co_hoi(o, **sua):
    d = _du_lieu(goi("POST", "/api/crm/opportunities/%s/quotation" % o["id"], {"expected_version": o["version"]}))
    qid = d["quotation_id"]
    goi("PUT", "/api/quotations/%s" % qid, sua)
    return qid


def hang_hoa(qid, dong):
    goi("PUT", "/api/quotations/%s/items" % qid, {"items": dong})


def xem_truoc(qid_than):
    return _du_lieu(goi("POST", "/api/quotations/price-preview", qid_than))


def gui(qid):
    return _du_lieu(goi("POST", "/api/quotations/%s/send" % qid, {}))


def duyet_noi_bo(qid):
    return _du_lieu(goi("POST", "/api/quotations/%s/internal-approve" % qid, {}))


def chap_nhan(qid, dos=None):
    g = goi("POST", "/api/quotations/%s/accept" % qid, {"dos": dos} if dos else {})
    ds = g.get("do_ids") or (_du_lieu(g) or {}).get("do_ids") or []
    _in("     → DO sinh tự động:", ds)
    return ds


def tu_choi(qid, ly_do):
    return goi("POST", "/api/quotations/%s/reject" % qid, {"reason": ly_do})


def ca_truc(ma, tai_xe, dau, cuoi, xe=None):
    than = {"id": ma, "driver_id": tai_xe, "shift_type": "custom", "availability_kind": "work",
            "shift_start": _iso(dau), "shift_end": _iso(cuoi), "status": "confirmed"}
    if xe:
        than["vehicle_id"] = xe
    goi("POST", "/api/tms/scheduling/driver-shifts", than, cho_phep=(200, 201, 409))


def sua_khung_do(do_id, lay1, lay2, giao1, giao2):
    """DO chờ điều phối được dời khung giờ (khách đổi ngày) — tuyến và giá KHÔNG đổi."""
    goi("PUT", "/api/delivery-orders/%s" % do_id, {
        "pickup_window_start": _iso(lay1), "pickup_window_end": _iso(lay2),
        "delivery_window_start": _iso(giao1), "delivery_window_end": _iso(giao2)})


def lap_chuyen(ma, do_ids, khoi_hanh, stop_plan=None):
    than = {"id": ma, "do_ids": do_ids, "trip_type": "one_way", "planned_departure_at": _iso(khoi_hanh),
            "avg_speed_kmh": 40, "dwell_minutes": 30, "return_purpose": "none"}
    if stop_plan:
        than["stop_plan"] = stop_plan
    return _du_lieu(goi("POST", "/api/tms/trips/from-delivery-orders", than,
                        headers={"Idempotency-Key": "lap-" + ma}))


def dieu_phoi(trip, xe, tai_xe, dau, cuoi, phu_xe=None):
    return _du_lieu(goi("PUT", "/api/tms/trips/%s/dispatch" % trip["id"], {
        "vehicle_id": xe, "driver_id": tai_xe, "co_driver_id": phu_xe, "expected_version": trip["version"],
        "assignment_start": _iso(dau), "assignment_end": _iso(cuoi)}))


def _lenh_van_chuyen(ma):
    for fo in goi("GET", "/api/tms/freight-orders"):
        if fo.get("id") == ma:
            return fo
    raise LoiAPI("không thấy lệnh vận chuyển " + ma)


def moc_thuc_thi(trip, xe, tai_xe, cac_moc, toa_do):
    """Ghi lần lượt các mốc (loại, giờ); toa_do = (lat, lng) điểm đầu → điểm cuối."""
    fo_id = trip["freight_order_id"]
    for i, (loai, luc) in enumerate(cac_moc):
        fo = _lenh_van_chuyen(fo_id)
        t = i / max(1, len(cac_moc) - 1)
        lat = toa_do[0][0] + (toa_do[1][0] - toa_do[0][0]) * t
        lng = toa_do[0][1] + (toa_do[1][1] - toa_do[0][1]) * t
        goi("POST", "/api/tms/freight-orders/%s/events" % fo_id, {
            "event_type": loai, "event_time": _iso(luc), "expected_version": fo["version"],
            "vehicle_id": xe, "driver_id": tai_xe, "lat": round(lat, 5), "lng": round(lng, 5),
            "speed_kmh": 0 if loai in ("check_in", "pickup", "arrival", "unloading", "delivered") else 45,
            "distance_km": 0, "location_text": None, "source": "device", "device_id": "GPS-" + xe,
            "reason": None, "note": None, "documents": [],
        }, headers={"Idempotency-Key": "moc-%s-%s" % (fo_id, loai)})


def hoan_tat(do_id, trip, xe, giao_luc, nguoi_nhan, phu_phi=(), tien="VND"):
    chuyen = _du_lieu(goi("GET", "/api/tms/trips/%s" % trip["id"]))
    dong, tep = [], {}
    # Chuyến chở nhiều DO: mỗi DO chỉ nộp POD cho CHẶNG GIAO của chính nó.
    chang = [l for l in chuyen["legs"] if l.get("do_id") == do_id and l.get("leg_type") == "delivery"]
    for leg in chang or chuyen["legs"]:
        f, s = "pod_%s" % leg["sequence_no"], "sig_%s" % leg["sequence_no"]
        dong.append({"leg_id": leg["id"], "vehicle_id": xe, "stop_no": leg["sequence_no"],
                     "delivery_time": _iso(giao_luc), "location_text": leg.get("destination") or "",
                     "receiver_name": nguoi_nhan, "receiver_phone": "0909000111",
                     "delivery_result": "delivered_full", "cargo_condition": "Nguyên niêm phong",
                     "file_field": f, "signature_file_field": s, "note": "POD demo"})
        tep[f] = _png("pod-%s-%s" % (do_id, leg["sequence_no"]))
        tep[s] = _png("chu-ky-%s-%s" % (do_id, leg["sequence_no"]))
    return _du_lieu(goi("POST", "/api/delivery-orders/%s/complete-delivery" % do_id,
                        form={"payload": {"trip_id": trip["id"], "currency_code": tien, "pod_entries": dong,
                                          "charge_adjustments": [{"name": ten, "note": ly_do, "original_amount": "0",
                                                                  "actual_amount": str(tien)}
                                                                 for ten, ly_do, tien in phu_phi]}},
                        files=tep, headers={"Idempotency-Key": "hoan-tat-" + do_id}))


def chi_phi_thuc_te(trip, ma, dong, gui_duyet=True):
    d = _du_lieu(goi("PUT", "/api/tms/finance/trips/%s/actual-cost" % trip["id"], {
        "id": ma, "currency_code": "VND", "carrier_id": "DEMO-CARRIER-INTERNAL",
        "lines": [{"id": "%s-%d" % (ma, i + 1), "name": ten, "key": khoa, "charge_type": khoa,
                   "original_amount": str(kh), "actual_amount": str(tt), "note": ghi}
                  for i, (khoa, ten, kh, tt, ghi) in enumerate(dong)],
    }, headers={"Idempotency-Key": "chi-phi-" + ma}))
    if gui_duyet:
        d = _du_lieu(goi("POST", "/api/tms/finance/costs/%s/submit" % d["id"], {"expected_version": d["version"]},
                         headers={"Idempotency-Key": "gui-duyet-" + ma}))
    return d


def packing_list(do_id):
    g = _du_lieu(goi("POST", "/api/parking-lists/auto-from-do/%s" % do_id, {"list_count": 1}))
    ds = g if isinstance(g, list) else (g.get("items") or g.get("lists") or [g])
    for phieu in ds:
        for buoc in ("yard_arrival", "gate_entry", "load_package"):
            for nhan in phieu.get("labels") or []:
                goi("POST", "/api/parking-qr/%s/scan" % nhan["qr_token"], {"action": buoc, "note": "quét demo"})


def su_co(do_id, xe, loai, vi_tri, mo_ta, muc="Medium"):
    goi("POST", "/api/incidents", {"do_id": do_id, "vehicle_id": xe, "incident_type": loai, "severity": muc,
                                   "location": vi_tri, "description": mo_ta, "reporter": "Tài xế"})


def dinh_kem(qid, ten, loai, noi_dung):
    goi("POST", "/api/quotations/%s/attachments" % qid, form={"doc_type": loai, "note": "Đính kèm demo"},
        files={"file": (ten, noi_dung, mimetypes.guess_type(ten)[0] or "application/octet-stream")})


# toạ độ gần đúng các điểm (để mốc thực thi có GPS vẽ được trên bản đồ)
TOA_DO = {
    "VSIP2A": (11.0930, 106.6510), "CATLAI": (10.7590, 106.7920), "CAIMEP": (10.5280, 107.0260),
    "SONGTHAN": (10.8930, 106.7530), "AMATA": (10.9530, 106.8760), "LONGAN": (10.5400, 106.4100),
}


def _khung(ngay, gio_lay, gio_giao):
    """(lấy từ, lấy đến, giao từ, giao đến) trong giờ VN của một ngày."""
    d = dt.datetime.combine(ngay, dt.time(0), VN)
    return (d + dt.timedelta(hours=gio_lay), d + dt.timedelta(hours=gio_lay + 2),
            d + dt.timedelta(hours=gio_lay + 2), d + dt.timedelta(hours=gio_giao))


def _han(ngay=30):
    return (dt.datetime.now(VN).date() + dt.timedelta(days=ngay)).isoformat()


# ================================================================ BƯỚC 2
def gieo():
    hom_nay = dt.datetime.now(VN).date()
    _in("Gieo dữ liệu qua API %s — hôm nay %s (giờ VN)" % (BASE, hom_nay))

    # Ca trực cho các tài xế sẽ dùng: phủ từ đầu tháng tới cuối tháng sau, để mọi case
    # (quá khứ, hôm nay, tương lai) đều qua cửa "tài xế có ca".
    dau_ca = dt.datetime(2026, 9, 1, 0, 0, tzinfo=VN)
    cuoi_ca = dt.datetime(2026, 10, 31, 23, 59, tzinfo=VN)
    _in("\n[0] Ca trực tài xế")
    for tx in ("DEMO-DRV-010", "DEMO-DRV-002", "DEMO-DRV-008", "DEMO-DRV-003", "DEMO-DRV-006",
               "DEMO-DRV-005", "DEMO-DRV-001"):
        ca_truc("CA-T9T10-" + tx, tx, dau_ca, cuoi_ca)

    # ------------------------------------------------------------ A. Nidec
    _in("\n[A] Nidec — Container 20FT, 3 cont, tuyến VSIP II-A → Cát Lái (44,7 km)")
    oA = co_hoi(customer_id="DEMO-CUS-NIDEC", contact_name="Anh Tuấn (Logistics)", source="email",
                route_id="DEMO-RT-VSIP2A-CATLAI", cargo_type="Linh kiện điện tử đóng cont",
                est_weight_kg=54000, est_trips_per_month=12, expected_price=2500000, owner="sales.hoa",
                notes="Khách quen, cần giá cho quý 4")
    oA = doi_giai_doan(oA, "contacted")
    oA = doi_giai_doan(oA, "negotiating")
    lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 3), 7, 13)
    xt = xem_truoc({"route_id": "DEMO-RT-VSIP2A-CATLAI", "vehicle_type_id": "DEMO-VT-20FT",
                    "weight_kg": 18000, "volume_m3": 28, "pallet_count": 20})
    _in("     xem trước giá: giá thành %s, gợi ý %s" % (
        xt.get("gia_thanh"), {k: v.get("gia") for k, v in (xt.get("goi_y_gia") or {}).items() if isinstance(v, dict)}))
    qA = bao_gia_tu_co_hoi(oA, vehicle_type_id="DEMO-VT-20FT", cargo_type="Linh kiện điện tử",
                           packaging_spec="Container nguyên khối 20FT", weight_kg=18000, volume_m3=28,
                           pallet_count=20, price_basis="per_trip", unit_price=2486000, currency_code="VND",
                           total_cost=xt.get("gia_thanh") or 1714540, selling_price=2486000, valid_to=_han(45),
                           pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                           delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                           payment_terms="30 ngày", sales_rep="Hoa", trips_per_month=12,
                           notes_customer="Giá đã gồm phí nâng hạ tại cảng.",
                           notes_ops="Lấy hàng cổng 2 kho VSIP II-A, liên hệ anh Tuấn.",
                           notes_internal="Khách quen, biên chấp nhận được.")
    hang_hoa(qA, [{"name": "Cont 20FT linh kiện điện tử", "quantity": 3, "uom": "Cont"}])
    dinh_kem(qA, "po-nidec-q4-2026.pdf", "PO của khách", b"%PDF-1.4\n% demo Nidec RFQ\n%%EOF\n")
    gui(qA)
    doA = chap_nhan(qA, [{"pickup_at": _iso(lay1), "due_at": _iso(giao2), "seal_no": "SL-NIDEC-0001"},
                         {"pickup_at": _iso(lay1 + dt.timedelta(hours=1)), "due_at": _iso(giao2), "seal_no": "SL-NIDEC-0002"},
                         {"pickup_at": _iso(lay1 + dt.timedelta(hours=2)), "due_at": _iso(giao2), "seal_no": "SL-NIDEC-0003"}])
    assert len(doA) == 3, doA

    # A1: hoàn tất trọn vẹn ngày 03/09
    xe, tx = "DEMO-51C-268.89", "DEMO-DRV-010"
    tA1 = lap_chuyen("TRIP-NIDEC-01", [doA[0]], lay1 + dt.timedelta(hours=1),
                     [{"sequence_no": 1, "stop_name": "Cảng Cát Lái", "receiver_name": "Anh Nam (Cát Lái)",
                       "receiver_phone": "0909000001", "delivery_note": "Hạ cont bãi B2"}])
    tA1 = dieu_phoi(tA1, xe, tx, lay1, giao2)
    g0 = lay1
    moc_thuc_thi(tA1, xe, tx, [("check_in", g0), ("pickup", g0 + dt.timedelta(minutes=40)),
                               ("departure", g0 + dt.timedelta(hours=1)), ("arrival", g0 + dt.timedelta(hours=2, minutes=30)),
                               ("unloading", g0 + dt.timedelta(hours=2, minutes=50))],
                 (TOA_DO["VSIP2A"], TOA_DO["CATLAI"]))
    hoan_tat(doA[0], tA1, xe, g0 + dt.timedelta(hours=3, minutes=20), "Anh Nam (Cát Lái)",
             phu_phi=[("Chờ bãi quá 2 giờ", "Cảng kẹt, xe chờ hạ cont 2h15", 180000)])
    chi_phi_thuc_te(tA1, "COST-NIDEC-01", [
        ("fuel", "Chi phí xăng dầu /km", 214560, 231800, "44,7 km, giá dầu tăng"),
        ("driver", "Phụ cấp chuyến tài xế", 400000, 400000, ""),
        ("toll", "Phí cầu đường / BOT", 150000, 165000, "Thêm trạm Phú Mỹ"),
        ("wh", "Phí bãi / kho", 100000, 100000, ""),
    ])

    # A2: đang chạy giữa đường HÔM NAY (check_in, pickup, departure), chưa tới
    bay_gio = dt.datetime.now(VN).replace(microsecond=0)
    lay = bay_gio - dt.timedelta(hours=3)
    sua_khung_do(doA[1], lay, lay + dt.timedelta(hours=2), lay + dt.timedelta(hours=2), bay_gio + dt.timedelta(hours=6))
    tA2 = lap_chuyen("TRIP-NIDEC-02", [doA[1]], lay + dt.timedelta(hours=1))
    xe2, tx2 = "DEMO-61H-112.34", "DEMO-DRV-002"
    tA2 = dieu_phoi(tA2, xe2, tx2, lay, bay_gio + dt.timedelta(hours=6))
    moc_thuc_thi(tA2, xe2, tx2, [("check_in", lay), ("pickup", lay + dt.timedelta(minutes=45)),
                                 ("departure", lay + dt.timedelta(hours=1, minutes=10))],
                 (TOA_DO["VSIP2A"], TOA_DO["VSIP2A"]))

    # A3: lập chuyến rồi HUỶ (khách lùi ngày) → DO quay về chờ điều phối
    l1, l2, g1, g2 = _khung(hom_nay + dt.timedelta(days=2), 7, 13)
    sua_khung_do(doA[2], l1, l2, g1, g2)
    tA3 = lap_chuyen("TRIP-NIDEC-03-HUY", [doA[2]], l1 + dt.timedelta(hours=1))
    goi("POST", "/api/tms/trips/%s/cancel" % tA3["id"],
        {"expected_version": tA3["version"], "reason": "Khách lùi ngày lấy cont 3 sang tuần sau."},
        headers={"Idempotency-Key": "huy-" + tA3["id"]})

    # ------------------------------------------------------------ B. Unilever
    _in("\n[B] Unilever — Đầu kéo 40', 2 cont chung một chuyến, tuyến VSIP II-A → Cái Mép (96,5 km)")
    oB = co_hoi(customer_id="DEMO-CUS-UNILEVER", contact_name="Chị Hạnh", source="referral",
                route_id="DEMO-RT-VSIP2A-CAIMEP", cargo_type="Hàng tiêu dùng đóng cont 40'",
                est_weight_kg=52000, est_trips_per_month=8, expected_price=4800000, owner="sales.minh")
    lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 5), 6, 16)
    qB = bao_gia_tu_co_hoi(oB, vehicle_type_id="DEMO-VT-TRACTOR40", cargo_type="Hàng tiêu dùng",
                           packaging_spec="Container nguyên khối 40FT", weight_kg=26000, volume_m3=60, pallet_count=22,
                           price_basis="per_trip", unit_price=4900000, currency_code="VND", discount_percent=0.05,
                           total_cost=2950000, selling_price=4900000, valid_to=_han(60),
                           pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                           delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                           payment_terms="45 ngày", sales_rep="Minh", trips_per_month=8,
                           notes_customer="Chiết khấu 5% cho hợp đồng 6 tháng.")
    hang_hoa(qB, [{"name": "Cont 40FT hàng tiêu dùng", "quantity": 2, "uom": "Cont"}])
    gui(qB)
    doB = chap_nhan(qB, [{"pickup_at": _iso(lay1), "due_at": _iso(giao2), "seal_no": "SL-UNI-0001"},
                         {"pickup_at": _iso(lay1 + dt.timedelta(hours=1)), "due_at": _iso(giao2), "seal_no": "SL-UNI-0002"}])
    assert len(doB) == 2, doB
    xe, tx, phu = "DEMO-51C-556.12", "DEMO-DRV-008", "DEMO-DRV-003"
    tB = lap_chuyen("TRIP-UNILEVER-01", doB, lay1 + dt.timedelta(hours=1),
                    [{"sequence_no": 1, "stop_name": "Cảng Cái Mép", "receiver_name": "Anh Phong (CMIT)",
                      "receiver_phone": "0909000002", "delivery_note": "Hạ 2 cont bãi xuất"}])
    tB = dieu_phoi(tB, xe, tx, lay1, giao2, phu_xe=phu)
    g0 = lay1
    moc_thuc_thi(tB, xe, tx, [("check_in", g0), ("pickup", g0 + dt.timedelta(hours=1)),
                              ("departure", g0 + dt.timedelta(hours=1, minutes=30)),
                              ("arrival", g0 + dt.timedelta(hours=4, minutes=40)),
                              ("unloading", g0 + dt.timedelta(hours=5))],
                 (TOA_DO["VSIP2A"], TOA_DO["CAIMEP"]))
    su_co(doB[0], xe, "Kẹt xe", "QL51 đoạn Long Thành", "Kẹt xe 40 phút do tai nạn phía trước, không ảnh hưởng hàng.", "Low")
    for i, do_id in enumerate(doB):
        hoan_tat(do_id, tB, xe, g0 + dt.timedelta(hours=5, minutes=45), "Anh Phong (CMIT)",
                 phu_phi=[("Phí lưu ca đêm", "Xe về sau 22h", 250000)] if i == 1 else ())
    chi_phi_thuc_te(tB, "COST-UNILEVER-01", [
        ("fuel", "Chi phí xăng dầu /km", 776825, 802000, "96,5 km × 2 cont chung chuyến"),
        ("driver", "Phụ cấp chuyến tài xế", 600000, 600000, "Có phụ xe"),
        ("toll", "Phí cầu đường / BOT", 320000, 320000, ""),
        ("wh", "Phí bãi / kho", 200000, 240000, "Phí nâng hạ 2 cont"),
    ])

    # ------------------------------------------------------------ C. Colgate — hàng KIỆN → Packing List
    _in("\n[C] Colgate — Xe tải 10 tấn, hàng đếm theo kiện (Packing List + quét QR), Sóng Thần → Cát Lái (31,2 km)")
    oC = co_hoi(customer_id="DEMO-CUS-COLGATE", contact_name="Anh Dũng", source="web",
                route_id="DEMO-RT-SONGTHAN-CATLAI", cargo_type="Kem đánh răng đóng kiện",
                est_weight_kg=8000, est_trips_per_month=20, expected_price=1300000, owner="sales.hoa")
    lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 8), 8, 14)
    qC = bao_gia_tu_co_hoi(oC, vehicle_type_id="DEMO-VT-TRUCK10", cargo_type="Hàng tiêu dùng",
                           packaging_spec="Kiện lẻ 120 kiện, xếp pallet", weight_kg=7800, volume_m3=30, pallet_count=10,
                           price_basis="per_trip", unit_price=1350000, currency_code="VND",
                           total_cost=780000, selling_price=1350000, valid_to=_han(30),
                           pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                           delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                           payment_terms="15 ngày", sales_rep="Hoa", trips_per_month=20)
    hang_hoa(qC, [{"name": "Kiện kem đánh răng (120 kiện/xe)", "quantity": 1, "uom": "Chuyến"}])
    gui(qC)
    doC = chap_nhan(qC)
    xe, tx = "DEMO-61H-330.17", "DEMO-DRV-006"
    tC = lap_chuyen("TRIP-COLGATE-01", doC, lay1 + dt.timedelta(hours=1))
    packing_list(doC[0])
    tC = dieu_phoi(tC, xe, tx, lay1, giao2)
    g0 = lay1
    moc_thuc_thi(tC, xe, tx, [("check_in", g0), ("pickup", g0 + dt.timedelta(minutes=50)),
                              ("departure", g0 + dt.timedelta(hours=1, minutes=10)),
                              ("arrival", g0 + dt.timedelta(hours=2, minutes=20)),
                              ("unloading", g0 + dt.timedelta(hours=2, minutes=30))],
                 (TOA_DO["SONGTHAN"], TOA_DO["CATLAI"]))
    hoan_tat(doC[0], tC, xe, g0 + dt.timedelta(hours=3), "Chị Thu (kho Cát Lái)")
    chi_phi_thuc_te(tC, "COST-COLGATE-01", [
        ("fuel", "Chi phí xăng dầu /km", 149760, 152000, ""),
        ("driver", "Phụ cấp chuyến tài xế", 300000, 300000, ""),
        ("toll", "Phí cầu đường / BOT", 80000, 80000, ""),
    ], gui_duyet=False)  # còn NHÁP: kế toán chưa gửi duyệt

    # ------------------------------------------------------------ D. Pou Yuen — biên mỏng, duyệt nội bộ, chưa điều phối
    _in("\n[D] Pou Yuen — Xe tải 15 tấn, biên mỏng → duyệt nội bộ, DO đã lập chuyến chờ điều phối, Cát Lái → Amata (38,4 km)")
    oD = co_hoi(customer_id="DEMO-CUS-POUYUEN", contact_name="Chị Mai", source="phone",
                route_id="DEMO-RT-CATLAI-AMATA", cargo_type="Nguyên liệu giày", est_weight_kg=14000,
                est_trips_per_month=6, expected_price=1200000, owner="sales.minh")
    lay1, lay2, giao1, giao2 = _khung(hom_nay + dt.timedelta(days=4), 7, 15)
    qD = bao_gia_tu_co_hoi(oD, vehicle_type_id="DEMO-VT-TRUCK15", cargo_type="Nguyên liệu giày",
                           packaging_spec="Hàng rời đóng bao", weight_kg=14000, volume_m3=40, pallet_count=0,
                           price_basis="per_trip", unit_price=1180000, currency_code="VND",
                           total_cost=1075000, selling_price=1180000, valid_to=_han(20),
                           pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                           delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                           payment_terms="30 ngày", sales_rep="Minh",
                           notes_internal="Giá sát sàn để giữ khách — cần trưởng phòng duyệt.")
    hang_hoa(qD, [{"name": "Chuyến nguyên liệu giày", "quantity": 1, "uom": "Chuyến"}])
    kq = gui(qD)
    _in("     sau khi gửi:", (kq or {}).get("canonical_status"))
    if (kq or {}).get("canonical_status") == "pending_approval":
        duyet_noi_bo(qD)
    doD = chap_nhan(qD)
    lap_chuyen("TRIP-POUYUEN-01", doD, lay1 + dt.timedelta(hours=1))   # planned, CHƯA điều phối

    # ------------------------------------------------------------ E. SGN Food — USD chờ khách; từ chối; nháp
    _in("\n[E] SGN Food — Xe lạnh 5 tấn, Long An → Cái Mép (112 km): báo giá USD chờ khách, một bị từ chối, một nháp")
    oE = co_hoi(customer_id="DEMO-CUS-SGNFOOD", contact_name="Anh Khoa", source="tender",
                route_id="DEMO-RT-LONGAN-CAIMEP", cargo_type="Thực phẩm đông lạnh", est_weight_kg=4500,
                est_trips_per_month=10, expected_price=3200000, owner="sales.hoa")
    lay1, lay2, giao1, giao2 = _khung(hom_nay + dt.timedelta(days=10), 5, 14)
    qE = bao_gia_tu_co_hoi(oE, vehicle_type_id="DEMO-VT-REEFER5", cargo_type="Thực phẩm đông lạnh",
                           packaging_spec="Thùng lạnh nguyên khối", weight_kg=4500, volume_m3=20, pallet_count=8,
                           price_basis="per_trip", unit_price=140, currency_code="USD", fx_rate=26173.5,
                           total_cost=94, selling_price=140, valid_to=_han(30),   # cả hai bằng USD (2.450.000 đ ≈ 94 USD)
                           temperature_requirement="-18°C", pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                           delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                           payment_terms="Trả trước 50%", sales_rep="Hoa")
    hang_hoa(qE, [{"name": "Chuyến xe lạnh hàng đông", "quantity": 2, "uom": "Chuyến"}])
    gui(qE)   # chờ khách

    # E2: báo giá thứ hai (tạo thẳng, không qua cơ hội) → gửi → khách từ chối
    lay1b, lay2b, giao1b, giao2b = _khung(hom_nay + dt.timedelta(days=6), 6, 15)
    qE2 = _du_lieu(goi("POST", "/api/quotations", {
        "customer_id": "DEMO-CUS-SGNFOOD", "route_id": "DEMO-RT-SONGTHAN-CATLAI", "vehicle_type_id": "DEMO-VT-REEFER5",
        "cargo_type": "Rau quả tươi", "packaging_spec": "Thùng lạnh nguyên khối", "weight_kg": 3000, "pallet_count": 6,
        "price_basis": "per_trip", "unit_price": 1650000, "currency_code": "VND",
        "total_cost": 690000, "selling_price": 1650000, "valid_to": _han(15),
        "pickup_window_start": _iso(lay1b), "pickup_window_end": _iso(lay2b),
        "delivery_window_start": _iso(giao1b), "delivery_window_end": _iso(giao2b)}))["id"]
    hang_hoa(qE2, [{"name": "Chuyến rau quả", "quantity": 1, "uom": "Chuyến"}])
    gui(qE2)
    tu_choi(qE2, "Khách chọn nhà xe khác giá 1.500.000.")

    # E3: nháp có đính kèm, chưa gửi
    qE3 = _du_lieu(goi("POST", "/api/quotations", {
        "customer_id": "DEMO-CUS-SGNFOOD", "route_id": "DEMO-RT-LONGAN-CAIMEP", "vehicle_type_id": "DEMO-VT-REEFER5",
        "cargo_type": "Hải sản đông lạnh", "packaging_spec": "Thùng lạnh nguyên khối", "weight_kg": 4800, "pallet_count": 8,
        "price_basis": "per_trip", "unit_price": 3400000, "currency_code": "VND",
        "total_cost": 2450000, "selling_price": 3400000, "valid_to": _han(30),
        "pickup_window_start": _iso(lay1), "pickup_window_end": _iso(lay2),
        "delivery_window_start": _iso(giao1), "delivery_window_end": _iso(giao2),
        "notes_internal": "Đang chờ khách xác nhận sản lượng tháng 10."}))["id"]
    hang_hoa(qE3, [{"name": "Chuyến hải sản đông lạnh", "quantity": 3, "uom": "Chuyến"}])
    dinh_kem(qE3, "bang-gia-doi-thu.png", "Khác", b"\x89PNG\r\n\x1a\n demo")

    # ------------------------------------------------------------ F. CRM các giai đoạn
    _in("\n[F] Cơ hội CRM ở các giai đoạn khác")
    co_hoi(prospect_name="Công ty May Hưng Thịnh", contact_name="Chị Lan", source="phone",
           origin_text="KCN Tân Bình", destination_text="Cảng Cát Lái", cargo_type="Vải cuộn",
           est_weight_kg=12000, est_trips_per_month=8, owner="sales.hoa", notes="Mới gọi hỏi giá, chưa có tuyến chuẩn")
    o2 = co_hoi(prospect_name="Nhựa Bình Minh Demo", contact_name="Anh Thắng", source="referral",
                route_id="DEMO-RT-SONGTHAN-CATLAI", cargo_type="Ống nhựa", est_weight_kg=9000,
                est_trips_per_month=15, expected_price=1400000, owner="sales.minh")
    doi_giai_doan(o2, "contacted")
    o3 = co_hoi(customer_id="DEMO-CUS-POUYUEN", contact_name="Chị Mai", source="phone",
                route_id="DEMO-RT-LONGAN-CAIMEP", cargo_type="Giày thành phẩm xuất khẩu", est_weight_kg=20000,
                est_trips_per_month=4, expected_price=3800000, owner="sales.minh")
    o3 = doi_giai_doan(o3, "contacted")
    doi_giai_doan(o3, "negotiating")
    o4 = co_hoi(prospect_name="Gạch Đồng Tâm Demo", contact_name="Anh Bảo", source="web",
                route_id="DEMO-RT-CATLAI-AMATA", cargo_type="Gạch men", est_weight_kg=25000,
                est_trips_per_month=6, expected_price=1000000, owner="sales.hoa")
    o4 = doi_giai_doan(o4, "contacted")
    doi_giai_doan(o4, "lost", lost_reason="Khách yêu cầu xe 30 tấn, đội xe chưa có.")

    _in("\nXONG. Kiểm nhanh qua API bàn giao:")
    ds = _du_lieu(goi("GET", "/api/handover/delivery-orders?page_size=50"))
    for d in ds["items"]:
        _in("   %-22s %-20s %12s → %12s %s" % (d["do_id"], d["customer_id"], d["selling_price"],
                                              d["final_selling_price"], d["completed_at"]))
    if ds["items"]:
        ct = _du_lieu(goi("GET", "/api/handover/delivery-orders/%s" % ds["items"][0]["do_id"]))
        _in("   chi tiết %s: %d dòng thu/chi, thiếu Acc code: %d" % (
            ct["header"]["do_id"], len(ct["details"]), sum(1 for x in ct["details"] if x["missing_acc_code"])))


# ================================================================ BƯỚC 2b: NGOẠI TỆ
def gieo_ngoai_te(cac_case=("G", "H")):
    """Hai case báo giá NGOẠI TỆ (LAK, USD) đi trọn luồng tới hoàn tất — để bên công nợ kiểm tiền tệ.

    Chủ dự án (11/09): *"thêm cho anh 2 cái case … tiền tệ Lào, 1 case tiền tệ USD … đến khi nó
    hoàn thành luôn — để cho ông anh của anh test"*. Điều khoá: giá của báo giá khai bằng CHÍNH tiền
    của báo giá (cả `unit_price` và `total_cost`), phụ phí khách trả thêm và hồ sơ hoàn tất cũng bằng
    tiền đó (máy chủ chặn CURRENCY_MISMATCH nếu lệch), còn chi phí thực tế của chuyến là VND (tiền
    chức năng của công ty). Chạy bổ sung được, không cần xoá dữ liệu đang có; `--case G` hoặc `--case H`
    để chạy riêng một case.
    """
    _in("Gieo case ngoại tệ %s qua API %s" % (",".join(cac_case), BASE))
    dau_ca = dt.datetime(2026, 9, 1, 0, 0, tzinfo=VN)
    cuoi_ca = dt.datetime(2026, 10, 31, 23, 59, tzinfo=VN)
    for tx in ("DEMO-DRV-001", "DEMO-DRV-005"):
        ca_truc("CA-T9T10-" + tx, tx, dau_ca, cuoi_ca)
    doG = doH = [""]
    if "G" in cac_case:
        # ------------------------------------------------------------ G. SGN Food — LAK (Kip Lào), xe lạnh 5 tấn
        # Tỷ giá bảng currencies: 1 LAK = 1,18 VND. Giá thành ~2.480.000 VND ≈ 2.100.000 LAK; cước 2.900.000 LAK ≈ 3.422.000 VND.
        # Quy cách KHÔNG dùng chữ "thùng": cửa Packing List coi "thùng" là hàng đếm kiện.
        _in("\n[G] SGN Food — báo giá LAK, Xe lạnh 5 tấn, Long An → Cái Mép (112 km), hoàn tất trọn luồng")
        oG = co_hoi(customer_id="DEMO-CUS-SGNFOOD", contact_name="Anh Khoa", source="email",
                    route_id="DEMO-RT-LONGAN-CAIMEP", cargo_type="Thực phẩm đông lạnh xuất Lào", est_weight_kg=4200,
                    est_trips_per_month=6, expected_price=2900000, owner="sales.hoa", notes="Khách thanh toán bằng Kip Lào")
        lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 9), 5, 15)
        qG = bao_gia_tu_co_hoi(oG, vehicle_type_id="DEMO-VT-REEFER5", cargo_type="Thực phẩm đông lạnh",
                               packaging_spec="Container lạnh nguyên khối", weight_kg=4200, volume_m3=20, pallet_count=8,
                               price_basis="per_trip", unit_price=2900000, currency_code="LAK", fx_rate=1.18,
                               total_cost=2100000, selling_price=2900000, valid_to=_han(30),
                               temperature_requirement="-18°C", pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                               delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                               payment_terms="Trả trước 50% bằng LAK", sales_rep="Hoa",
                               notes_customer="Giá bằng Kip Lào, tỷ giá 1 LAK = 1,18 VND tại ngày báo giá.")
        hang_hoa(qG, [{"name": "Chuyến xe lạnh hàng đông (LAK)", "quantity": 1, "uom": "Chuyến"}])
        gui(qG)
        doG = chap_nhan(qG, [{"pickup_at": _iso(lay1), "due_at": _iso(giao2), "seal_no": "SL-SGN-LAK-0001"}])
        xe, tx = "DEMO-50H-771.25", "DEMO-DRV-001"
        tG = lap_chuyen("TRIP-SGN-LAK-01", doG, lay1 + dt.timedelta(hours=1),
                        [{"sequence_no": 1, "stop_name": "Cảng Cái Mép", "receiver_name": "Anh Phong (CMIT)",
                          "receiver_phone": "0909000002", "delivery_note": "Hàng lạnh -18°C, hạ thẳng bãi lạnh"}])
        tG = dieu_phoi(tG, xe, tx, lay1, giao2)
        g0 = lay1
        moc_thuc_thi(tG, xe, tx, [("check_in", g0), ("pickup", g0 + dt.timedelta(minutes=50)),
                                  ("departure", g0 + dt.timedelta(hours=1, minutes=20)),
                                  ("arrival", g0 + dt.timedelta(hours=4, minutes=30)),
                                  ("unloading", g0 + dt.timedelta(hours=4, minutes=50))],
                     (TOA_DO["LONGAN"], TOA_DO["CAIMEP"]))
        hoan_tat(doG[0], tG, xe, g0 + dt.timedelta(hours=5, minutes=30), "Anh Phong (CMIT)",
                 phu_phi=[("Chạy máy lạnh chờ bãi", "Chờ bãi lạnh 1h40, máy lạnh chạy liên tục", 150000)], tien="LAK")
        chi_phi_thuc_te(tG, "COST-SGN-LAK-01", [
            ("fuel", "Chi phí xăng dầu /km", 515200, 548000, "112 km, xe lạnh chạy máy lạnh"),
            ("driver", "Phụ cấp chuyến tài xế", 350000, 350000, ""),
            ("toll", "Phí cầu đường / BOT", 200000, 200000, ""),
            ("wh", "Phí bãi / kho", 120000, 180000, "Phí bãi lạnh"),
        ])
    if "H" in cac_case:
        # ------------------------------------------------------------ H. Pou Yuen — USD, đầu kéo 20'
        # Tỷ giá 1 USD = 26.173,5 VND. Giá thành ~1.180.000 VND ≈ 45 USD; cước 120 USD ≈ 3.141.000 VND.
        _in("\n[H] Pou Yuen — báo giá USD, Đầu kéo 20', Cát Lái → Amata (38,4 km), hoàn tất trọn luồng")
        oH = co_hoi(customer_id="DEMO-CUS-POUYUEN", contact_name="Chị Mai", source="referral",
                    route_id="DEMO-RT-CATLAI-AMATA", cargo_type="Nguyên liệu giày nhập khẩu (cont 20')", est_weight_kg=18000,
                    est_trips_per_month=10, expected_price=120, owner="sales.minh", notes="Khách FDI thanh toán USD")
        lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 10), 8, 16)
        qH = bao_gia_tu_co_hoi(oH, vehicle_type_id="DEMO-VT-TRACTOR20", cargo_type="Nguyên liệu giày",
                               packaging_spec="Container nguyên khối 20FT", weight_kg=18000, volume_m3=28, pallet_count=16,
                               price_basis="per_trip", unit_price=120, currency_code="USD", fx_rate=26173.5,
                               total_cost=45, selling_price=120, valid_to=_han(30),
                               pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                               delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                               payment_terms="30 ngày, chuyển khoản USD", sales_rep="Minh",
                               notes_customer="Giá bằng USD, tỷ giá 26.173,5 VND/USD tại ngày báo giá.")
        hang_hoa(qH, [{"name": "Cont 20FT nguyên liệu giày (USD)", "quantity": 1, "uom": "Cont"}])
        gui(qH)
        doH = chap_nhan(qH, [{"pickup_at": _iso(lay1), "due_at": _iso(giao2), "seal_no": "SL-PY-USD-0001"}])
        xe, tx = "DEMO-51C-129.03", "DEMO-DRV-005"   # xe có đơn giá dầu ghi đè riêng (7.728 đ/km)
        tH = lap_chuyen("TRIP-PY-USD-01", doH, lay1 + dt.timedelta(hours=1),
                        [{"sequence_no": 1, "stop_name": "KCN Amata", "receiver_name": "Anh Dũng (kho Amata)",
                          "receiver_phone": "0909000003", "delivery_note": "Hạ cont cổng 1"}])
        tH = dieu_phoi(tH, xe, tx, lay1, giao2)
        g0 = lay1
        moc_thuc_thi(tH, xe, tx, [("check_in", g0), ("pickup", g0 + dt.timedelta(minutes=45)),
                                  ("departure", g0 + dt.timedelta(hours=1, minutes=10)),
                                  ("arrival", g0 + dt.timedelta(hours=2, minutes=30)),
                                  ("unloading", g0 + dt.timedelta(hours=2, minutes=45))],
                     (TOA_DO["CATLAI"], TOA_DO["AMATA"]))
        hoan_tat(doH[0], tH, xe, g0 + dt.timedelta(hours=3, minutes=15), "Anh Dũng (kho Amata)",
                 phu_phi=[("Bốc xếp thêm tại kho", "Kho không có xe nâng, tổ lái hỗ trợ dỡ", 15)], tien="USD")
        chi_phi_thuc_te(tH, "COST-PY-USD-01", [
            ("fuel", "Chi phí xăng dầu /km", 296755, 301000, "38,4 km × 7.728 đ (đơn giá riêng của xe)"),
            ("driver", "Phụ cấp chuyến tài xế", 400000, 400000, ""),
            ("toll", "Phí cầu đường / BOT", 150000, 150000, ""),
        ])

    _in("\nXONG case ngoại tệ. Kiểm qua API bàn giao:")
    for do_id in (doG[0], doH[0]):
        if not do_id:
            continue
        ct = _du_lieu(goi("GET", "/api/handover/delivery-orders/%s" % do_id))
        h = ct["header"]
        _in("   %s: %s  cước %s + trả thêm %s = giá cuối %s %s · giá thành thực tế %s · %d dòng, thiếu Acc code %d" % (
            h["do_id"], h["customer_id"], h["selling_price"], h["customer_surcharge_total"], h["final_selling_price"],
            h["currency"], h["actual_cost_total"], len(ct["details"]), sum(1 for x in ct["details"] if x["missing_acc_code"])))


# ================================================================ KIỂM
def kiem():
    import database
    from sqlalchemy import text
    with database.engine.connect() as c:
        ten = [r[0] for r in c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1"))]
        for t in ten:
            n = c.execute(text('SELECT count(*) FROM "%s"' % t)).scalar()
            if n:
                _in("   %-38s %6d %s" % (t, n, "" if t in BANG_GIU else "◄ vận hành"))
        _in("\n   Trạng thái báo giá:", dict(c.execute(text(
            "SELECT canonical_status, count(*) FROM quotations GROUP BY 1 ORDER BY 1")).fetchall()))
        _in("   Trạng thái DO:", dict(c.execute(text(
            "SELECT canonical_status, count(*) FROM delivery_orders GROUP BY 1 ORDER BY 1")).fetchall()))
        _in("   Trạng thái chuyến:", dict(c.execute(text(
            "SELECT status, count(*) FROM transport_trips GROUP BY 1 ORDER BY 1")).fetchall()))
        _in("   Chi phí thực tế:", dict(c.execute(text(
            "SELECT status, count(*) FROM freight_actual_costs GROUP BY 1 ORDER BY 1")).fetchall()))
        _in("   Cơ hội:", dict(c.execute(text(
            "SELECT stage, count(*) FROM crm_opportunities GROUP BY 1 ORDER BY 1")).fetchall()))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--xoa", action="store_true")
    p.add_argument("--gieo", action="store_true")
    p.add_argument("--gieo-ngoai-te", action="store_true", help="chỉ gieo thêm hai case LAK/USD đi trọn luồng")
    p.add_argument("--kiem", action="store_true")
    p.add_argument("--case", default="G,H", help="với --gieo-ngoai-te: chạy case nào, vd G hoặc H")
    a = p.parse_args()
    if not (a.xoa or a.gieo or a.gieo_ngoai_te or a.kiem):
        p.print_help()
        sys.exit(1)
    if a.xoa:
        xoa()
    if a.gieo:
        if not TOKEN:
            sys.exit("Thiếu EPL_TMS_API_TOKEN (trong .env hoặc biến môi trường).")
        gieo()
    if a.gieo_ngoai_te:
        if not TOKEN:
            sys.exit("Thiếu EPL_TMS_API_TOKEN (trong .env hoặc biến môi trường).")
        gieo_ngoai_te(tuple(x.strip().upper() for x in a.case.split(",") if x.strip()))
    if a.kiem:
        kiem()
