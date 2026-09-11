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
    python ..\\scripts\\dung_lai_du_lieu_demo.py --gieo-nhieu     # gieo THÊM nhiều dữ liệu
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

KHÔNG CÒN MỘT CON SỐ TIỀN NÀO GÕ TAY TRONG SCRIPT NÀY
-----------------------------------------------------
Chủ dự án (11/09/2026) mở báo giá Unilever và hỏi cước 4.900.000 đ ở đâu ra. Không
ở đâu cả: nó là con số viết cứng trong script, cạnh một giá thành cũng viết cứng
(2.950.000 đ) lệch hẳn với công thức thật (2.082.425 đ). Trên màn hình, cước đọc từ
cơ sở dữ liệu còn giá thành tính tươi từ công thức, nên hai số không cùng gốc và
không kiểm chứng được nhau. Anh chốt: *"bỏ hết ... rõ sát triệt để giúp anh"*.

Nên giờ mọi con số tiền đều suy ra từ công thức loại xe qua `price-preview`, đúng
điểm cuối mà màn báo giá đang gọi:

  · `gia_that()` cho giá thành và cước. Cước = giá thành / (1 − biên). Mỗi case
    chỉ chọn MỨC BIÊN, không chọn số tiền. Case Pou Yuen cố ý lấy biên 9% để có
    mẫu báo giá phải qua trưởng phòng.
  · `dong_chi_phi()` cho bảng chi phí thực tế. Cột "chốt ban đầu" bằng đúng cấu
    phần công thức, cột "thực tế" suy ra theo tỉ lệ vượt của từng khoản.

Hệ quả: sửa đơn giá trong Dữ liệu gốc → Công thức giá thành rồi gieo lại thì toàn
bộ dữ liệu demo đi theo, và mọi con số trên màn đều tra ngược được về công thức.
"""
import argparse
import datetime as dt
import io
import json
import math
import mimetypes
import os
import sys
import time
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
    # Máy chủ 8001 chạy `--reload`: sửa một tệp backend là nó khởi động lại và cắt kết nối
    # đang mở (`ConnectionResetError`). Gieo mấy trăm lệnh thì gặp là chuyện thường, nên
    # THỬ LẠI ở tầng mạng — và IN RA mỗi lần thử lại, không lặng lẽ.
    ma = noi = None
    for lan in range(4):
        try:
            with urlopen(req, timeout=120) as r:
                ma, noi = r.status, r.read().decode("utf-8")
            break
        except HTTPError as e:
            ma, noi = e.code, e.read().decode("utf-8", "replace")
            break
        except Exception as loi_mang:
            if lan == 3:
                raise
            _in("  … mất kết nối (%s), thử lại lần %d sau 4 giây" % (type(loi_mang).__name__, lan + 2))
            time.sleep(4)
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


def lam_tron_tien(gia_tri, tien):
    """Làm tròn cho số tiền dễ đọc mà không làm nó lệch khỏi giá thành thật.

    VND luôn tròn nghìn: đó là cách người bán đọc giá, và một nghìn đồng trên vài
    triệu là không đáng kể.

    Ngoại tệ thì phải theo ĐỘ LỚN của con số, không theo tên đồng tiền. Lần đầu
    viết hàm này tôi làm tròn nghìn cho mọi đồng không phải đô la, và hai báo giá
    bằng Baht Thái lệch thật: giá thành 2.860 THB bị làm tròn thành 3.000 THB, tức
    lệch 5% so với công thức, vì một Baht đáng 710 đồng nên "nghìn Baht" là một
    bậc quá thô. Giữ năm chữ số ý nghĩa thì đúng cho cả đồng lớn như đô la và
    đồng nhỏ như Kip Lào.
    """
    if tien == "VND":
        return round(gia_tri, -3)
    if gia_tri <= 0:
        return 0.0
    bac = 4 - int(math.floor(math.log10(abs(gia_tri))))
    return round(gia_tri, max(-3, min(2, bac)))


def gia_that(route_id, vehicle_type_id, weight_kg, volume_m3=None, pallet_count=None,
             tien="VND", ty_gia=1.0, bien=None, chiet_khau=0.0, im=False):
    """Giá thành và cước của MỘT chuyến, không có con số nào gõ tay.

    Chủ dự án (11/09/2026) mở màn báo giá của Unilever và hỏi cước 4.900.000 đ ở
    đâu ra. Không ở đâu cả: nó là một con số viết cứng ngay trong script này, cạnh
    một `total_cost` cũng viết cứng và lệch với công thức thật. Nên trên màn hình,
    cước đọc từ cơ sở dữ liệu còn giá thành lại tính tươi từ công thức, hai số
    không cùng gốc và không kiểm chứng được nhau. Anh chốt bỏ hết cách gieo đó.

    Giờ cả hai số đều có nguồn:

    · `gia_thanh` lấy từ chính điểm cuối `price-preview` mà màn báo giá đang gọi,
      nên con số lưu vào báo giá bằng đúng con số màn hình tính lại.
    · `cuoc` suy ra từ giá thành đó theo biên: `gia_thanh / (1 - bien)`. Không có
      `bien` truyền vào thì lấy biên mục tiêu do máy chủ trả về, tức chính sách
      công ty — không phải một hệ số đoán.
    · `chiet_khau` nâng giá niêm yết lên trước, để sau khi trừ chiết khấu cho
      khách thì biên còn lại vẫn đúng mức đã định.

    Trả `(gia_thanh, cuoc)` CÙNG đơn vị tiền của báo giá, vì máy chủ so hai số này
    với nhau. Giá thành trong công thức là VND, nên báo giá ngoại tệ thì chia
    `ty_gia` (số VND cho một đơn vị ngoại tệ).
    """
    than = {"route_id": route_id, "vehicle_type_id": vehicle_type_id, "weight_kg": weight_kg}
    if volume_m3 is not None:
        than["volume_m3"] = volume_m3
    if pallet_count is not None:
        than["pallet_count"] = pallet_count
    xt = xem_truoc(than)
    if not xt.get("tinh_duoc"):
        raise SystemExit("Không xem trước được giá cho %s / %s: %s"
                         % (route_id, vehicle_type_id, xt.get("viec_con_thieu")))
    gia_thanh_vnd = float(xt.get("gia_thanh") or 0)
    if gia_thanh_vnd <= 0:
        raise SystemExit("Công thức của %s ra giá thành 0 — chưa khai đơn giá." % vehicle_type_id)
    muc = float(bien if bien is not None else (xt.get("bien_muc_tieu") or 0.20))
    if not 0 < muc < 1:
        raise SystemExit("Biên %r không dùng được." % (bien,))
    cuoc_vnd = gia_thanh_vnd / (1 - muc)
    if chiet_khau:
        cuoc_vnd = cuoc_vnd / (1 - float(chiet_khau))
    ty = 1.0 if tien == "VND" else (float(ty_gia or 1) or 1)
    gia_thanh = lam_tron_tien(gia_thanh_vnd / ty, tien)
    cuoc = lam_tron_tien(cuoc_vnd / ty, tien)
    if not im:
        _in("     giá từ công thức: giá thành %s %s → cước %s %s (biên %.0f%%%s)"
            % (gia_thanh, tien, cuoc, tien, muc * 100,
               ", chiết khấu %.0f%%" % (chiet_khau * 100) if chiet_khau else ""))
    return gia_thanh, cuoc


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
    g = goi("POST", "/api/tms/scheduling/driver-shifts", than, cho_phep=(200, 201, 409))
    # KHÔNG nuốt 409: ca mới CHỒNG ca đã có cũng trả 409, và nuốt nó nghĩa là tin rằng tài xế
    # đã có lịch trong khi thực tế chưa — điều phối sẽ chặn DRIVER_WORK_SCHEDULE_REQUIRED ở
    # một ngày mình tưởng đã phủ. Đã đo đúng lỗi này ngày 11/09.
    if isinstance(g, dict) and (g.get("detail") or {}).get("code"):
        _in("     ca %s không lưu được: %s" % (ma, (g["detail"] or {}).get("message", "")[:90]))
    return g


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
    """Ghi lần lượt các mốc (loại, giờ); toa_do = (lat, lng) điểm đầu → điểm cuối.

    ĐỌC PHIÊN BẢN MỘT LẦN rồi tự tăng: mỗi mốc ghi thành công tăng `version` đúng 1.
    Bản đầu gọi `GET /api/tms/freight-orders` (trả tới 100 lệnh) trước TỪNG mốc, nên
    gieo 30 chuyến là hơn 150 lần đọc toàn danh sách. Lệch phiên bản (ai đó vừa ghi)
    thì máy chủ trả 409 và ở đây đọc lại rồi thử tiếp — không đoán.
    """
    fo_id = trip["freight_order_id"]
    ban = _lenh_van_chuyen(fo_id)["version"]
    for i, (loai, luc) in enumerate(cac_moc):
        fo = {"version": ban}
        t = i / max(1, len(cac_moc) - 1)
        lat = toa_do[0][0] + (toa_do[1][0] - toa_do[0][0]) * t
        lng = toa_do[0][1] + (toa_do[1][1] - toa_do[0][1]) * t
        than = {
            "event_type": loai, "event_time": _iso(luc),
            "vehicle_id": xe, "driver_id": tai_xe, "lat": round(lat, 5), "lng": round(lng, 5),
            "speed_kmh": 0 if loai in ("check_in", "pickup", "arrival", "unloading", "delivered") else 45,
            "distance_km": 0, "location_text": None, "source": "device", "device_id": "GPS-" + xe,
            "reason": None, "note": None, "documents": [],
        }
        dau = {"Idempotency-Key": "moc-%s-%s" % (fo_id, loai)}
        g = goi("POST", "/api/tms/freight-orders/%s/events" % fo_id,
                dict(than, expected_version=fo["version"]), headers=dau, cho_phep=(200, 201, 409))
        if isinstance(g, dict) and (g.get("detail") or {}).get("code") == "VERSION_CONFLICT":
            ban = _lenh_van_chuyen(fo_id)["version"]
            goi("POST", "/api/tms/freight-orders/%s/events" % fo_id,
                dict(than, expected_version=ban), headers=dau)
        ban += 1


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


def dong_chi_phi(tuyen, loai, kg, the_tich=None, lech=None, ghi=None):
    """Dòng chi phí thực tế của một chuyến, cột "chốt ban đầu" LẤY TỪ CÔNG THỨC.

    Bảng "Chốt giá cuối cùng" ở màn Hoàn tất giao hàng đặt ba cột cạnh nhau: chi
    phí chốt ban đầu, chi phí thực tế, và phần khách trả thêm. Cột đầu là con số
    công ty đã tính khi nhận chuyến, nên nó phải bằng đúng cấu phần của công thức
    loại xe. Trước đây script gõ tay cả cột đó, và nó lệch thật: chuyến Unilever
    ghi chốt ban đầu 776.825 đ tiền dầu trong khi công thức ra 712.425 đ. Hồ sơ
    bàn giao cho bên công nợ vì thế mang một con số không ai tra ngược được.

    Giờ cột chốt ban đầu hỏi thẳng `price-preview`, còn cột thực tế suy ra từ nó
    theo `lech` — tỉ lệ vượt của từng khoản (0,04 là thực tế cao hơn 4%). Khoản
    nào không khai trong `lech` thì thực tế bằng chốt ban đầu, đúng như phần lớn
    chuyến chạy đúng kế hoạch.
    """
    than = {"route_id": tuyen, "vehicle_type_id": loai, "weight_kg": kg}
    if the_tich is not None:
        than["volume_m3"] = the_tich
    xt = xem_truoc(than)
    if not xt.get("tinh_duoc"):
        raise SystemExit("Không lấy được cấu phần chi phí cho %s / %s: %s"
                         % (tuyen, loai, xt.get("viec_con_thieu")))
    ra = []
    for d in xt.get("cac_dong") or []:
        khoa = d.get("khoa") or ""
        chot = round(float(d.get("thanh_tien") or 0))
        if chot <= 0:
            continue
        ty_le = float((lech or {}).get(khoa) or 0)
        thuc_te = round(chot * (1 + ty_le), -3) if ty_le else chot
        ra.append((khoa, d.get("nhan") or khoa, chot, thuc_te, (ghi or {}).get(khoa, "")))
    if not ra:
        raise SystemExit("Công thức của %s không có cấu phần chi nào." % loai)
    return ra


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
    gtA, cuocA = gia_that("DEMO-RT-VSIP2A-CATLAI", "DEMO-VT-20FT", 18000, 28, 20, bien=0.24)
    # Giá khách mong đợi đặt thấp hơn cước mình sẽ báo, đúng thế đàm phán thường
    # gặp; con số vẫn neo vào cước thật nên không lệch khi công thức đổi.
    oA = co_hoi(customer_id="DEMO-CUS-NIDEC", contact_name="Anh Tuấn (Logistics)", source="email",
                route_id="DEMO-RT-VSIP2A-CATLAI", cargo_type="Linh kiện điện tử đóng cont",
                est_weight_kg=54000, est_trips_per_month=12, expected_price=round(cuocA * 0.94, -3),
                owner="sales.hoa", notes="Khách quen, cần giá cho quý 4")
    oA = doi_giai_doan(oA, "contacted")
    oA = doi_giai_doan(oA, "negotiating")
    lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 3), 7, 13)
    qA = bao_gia_tu_co_hoi(oA, vehicle_type_id="DEMO-VT-20FT", cargo_type="Linh kiện điện tử",
                           packaging_spec="Container nguyên khối 20FT", weight_kg=18000, volume_m3=28,
                           pallet_count=20, price_basis="per_trip", unit_price=cuocA, currency_code="VND",
                           total_cost=gtA, selling_price=cuocA, valid_to=_han(45),
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
    chi_phi_thuc_te(tA1, "COST-NIDEC-01", dong_chi_phi(
        "DEMO-RT-VSIP2A-CATLAI", "DEMO-VT-20FT", 18000, 28,
        lech={"fuel": 0.08, "toll": 0.10},
        ghi={"fuel": "Giá dầu tăng giữa kỳ", "toll": "Thêm trạm Phú Mỹ"}))

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
    gtB, cuocB = gia_that("DEMO-RT-VSIP2A-CAIMEP", "DEMO-VT-TRACTOR40", 26000, 60, 22,
                          bien=0.20, chiet_khau=0.05)
    oB = co_hoi(customer_id="DEMO-CUS-UNILEVER", contact_name="Chị Hạnh", source="referral",
                route_id="DEMO-RT-VSIP2A-CAIMEP", cargo_type="Hàng tiêu dùng đóng cont 40'",
                est_weight_kg=52000, est_trips_per_month=8,
                expected_price=round(cuocB * 0.93, -3), owner="sales.minh")
    lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 5), 6, 16)
    qB = bao_gia_tu_co_hoi(oB, vehicle_type_id="DEMO-VT-TRACTOR40", cargo_type="Hàng tiêu dùng",
                           packaging_spec="Container nguyên khối 40FT", weight_kg=26000, volume_m3=60, pallet_count=22,
                           price_basis="per_trip", unit_price=cuocB, currency_code="VND", discount_percent=0.05,
                           total_cost=gtB, selling_price=cuocB, valid_to=_han(60),
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
    chi_phi_thuc_te(tB, "COST-UNILEVER-01", dong_chi_phi(
        "DEMO-RT-VSIP2A-CAIMEP", "DEMO-VT-TRACTOR40", 26000, 60,
        lech={"fuel": 0.03, "wh": 0.20},
        ghi={"fuel": "2 cont chung chuyến", "driver": "Có phụ xe", "wh": "Phí nâng hạ 2 cont"}))

    # ------------------------------------------------------------ C. Colgate — hàng KIỆN → Packing List
    _in("\n[C] Colgate — Xe tải 10 tấn, hàng đếm theo kiện (Packing List + quét QR), Sóng Thần → Cát Lái (31,2 km)")
    gtC, cuocC = gia_that("DEMO-RT-SONGTHAN-CATLAI", "DEMO-VT-TRUCK10", 7800, 30, 10, bien=0.30)
    oC = co_hoi(customer_id="DEMO-CUS-COLGATE", contact_name="Anh Dũng", source="web",
                route_id="DEMO-RT-SONGTHAN-CATLAI", cargo_type="Kem đánh răng đóng kiện",
                est_weight_kg=8000, est_trips_per_month=20,
                expected_price=round(cuocC * 0.96, -3), owner="sales.hoa")
    lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 8), 8, 14)
    qC = bao_gia_tu_co_hoi(oC, vehicle_type_id="DEMO-VT-TRUCK10", cargo_type="Hàng tiêu dùng",
                           packaging_spec="Kiện lẻ 120 kiện, xếp pallet", weight_kg=7800, volume_m3=30, pallet_count=10,
                           price_basis="per_trip", unit_price=cuocC, currency_code="VND",
                           total_cost=gtC, selling_price=cuocC, valid_to=_han(30),
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
    chi_phi_thuc_te(tC, "COST-COLGATE-01", dong_chi_phi(
        "DEMO-RT-SONGTHAN-CATLAI", "DEMO-VT-TRUCK10", 7800, 30, lech={"fuel": 0.02}),
        gui_duyet=False)  # còn NHÁP: kế toán chưa gửi duyệt

    # ------------------------------------------------------------ D. Pou Yuen — biên mỏng, duyệt nội bộ, chưa điều phối
    _in("\n[D] Pou Yuen — Xe tải 15 tấn, biên mỏng → duyệt nội bộ, DO đã lập chuyến chờ điều phối, Cát Lái → Amata (38,4 km)")
    # Biên 9% là CỐ Ý dưới ngưỡng duyệt của công ty, để có mẫu báo giá phải qua
    # trưởng phòng. Vẫn suy từ giá thành thật, chỉ khác chỗ chọn mức biên.
    gtD, cuocD = gia_that("DEMO-RT-CATLAI-AMATA", "DEMO-VT-TRUCK15", 14000, 40, 0, bien=0.09)
    oD = co_hoi(customer_id="DEMO-CUS-POUYUEN", contact_name="Chị Mai", source="phone",
                route_id="DEMO-RT-CATLAI-AMATA", cargo_type="Nguyên liệu giày", est_weight_kg=14000,
                est_trips_per_month=6, expected_price=round(cuocD * 0.97, -3), owner="sales.minh")
    lay1, lay2, giao1, giao2 = _khung(hom_nay + dt.timedelta(days=4), 7, 15)
    qD = bao_gia_tu_co_hoi(oD, vehicle_type_id="DEMO-VT-TRUCK15", cargo_type="Nguyên liệu giày",
                           packaging_spec="Hàng rời đóng bao", weight_kg=14000, volume_m3=40, pallet_count=0,
                           price_basis="per_trip", unit_price=cuocD, currency_code="VND",
                           total_cost=gtD, selling_price=cuocD, valid_to=_han(20),
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
    gtE, cuocE = gia_that("DEMO-RT-LONGAN-CAIMEP", "DEMO-VT-REEFER5", 4500, 20, 8,
                          tien="USD", ty_gia=26173.5, bien=0.26)
    # Cơ hội ghi giá mong đợi bằng VND vì khách hỏi giá trước khi chốt hợp đồng USD.
    oE = co_hoi(customer_id="DEMO-CUS-SGNFOOD", contact_name="Anh Khoa", source="tender",
                route_id="DEMO-RT-LONGAN-CAIMEP", cargo_type="Thực phẩm đông lạnh", est_weight_kg=4500,
                est_trips_per_month=10, expected_price=round(cuocE * 26173.5 * 0.95, -3),
                owner="sales.hoa")
    lay1, lay2, giao1, giao2 = _khung(hom_nay + dt.timedelta(days=10), 5, 14)
    qE = bao_gia_tu_co_hoi(oE, vehicle_type_id="DEMO-VT-REEFER5", cargo_type="Thực phẩm đông lạnh",
                           packaging_spec="Thùng lạnh nguyên khối", weight_kg=4500, volume_m3=20, pallet_count=8,
                           price_basis="per_trip", unit_price=cuocE, currency_code="USD", fx_rate=26173.5,
                           total_cost=gtE, selling_price=cuocE, valid_to=_han(30),   # cả hai bằng USD
                           temperature_requirement="-18°C", pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
                           delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
                           payment_terms="Trả trước 50%", sales_rep="Hoa")
    hang_hoa(qE, [{"name": "Chuyến xe lạnh hàng đông", "quantity": 2, "uom": "Chuyến"}])
    gui(qE)   # chờ khách

    # E2: báo giá thứ hai (tạo thẳng, không qua cơ hội) → gửi → khách từ chối
    lay1b, lay2b, giao1b, giao2b = _khung(hom_nay + dt.timedelta(days=6), 6, 15)
    gtE2, cuocE2 = gia_that("DEMO-RT-SONGTHAN-CATLAI", "DEMO-VT-REEFER5", 3000, pallet_count=6, bien=0.32)
    qE2 = _du_lieu(goi("POST", "/api/quotations", {
        "customer_id": "DEMO-CUS-SGNFOOD", "route_id": "DEMO-RT-SONGTHAN-CATLAI", "vehicle_type_id": "DEMO-VT-REEFER5",
        "cargo_type": "Rau quả tươi", "packaging_spec": "Thùng lạnh nguyên khối", "weight_kg": 3000, "pallet_count": 6,
        "price_basis": "per_trip", "unit_price": cuocE2, "currency_code": "VND",
        "total_cost": gtE2, "selling_price": cuocE2, "valid_to": _han(15),
        "pickup_window_start": _iso(lay1b), "pickup_window_end": _iso(lay2b),
        "delivery_window_start": _iso(giao1b), "delivery_window_end": _iso(giao2b)}))["id"]
    hang_hoa(qE2, [{"name": "Chuyến rau quả", "quantity": 1, "uom": "Chuyến"}])
    gui(qE2)
    # Lý do từ chối nhắc lại giá đối thủ, tính từ chính cước mình báo nên câu chữ
    # không lệch con số trên báo giá khi công thức đổi.
    tu_choi(qE2, "Khách chọn nhà xe khác, giá thấp hơn khoảng %s đ." % format(int(cuocE2 * 0.1), ",d").replace(",", "."))

    # E3: nháp có đính kèm, chưa gửi
    gtE3, cuocE3 = gia_that("DEMO-RT-LONGAN-CAIMEP", "DEMO-VT-REEFER5", 4800, pallet_count=8, bien=0.27)
    qE3 = _du_lieu(goi("POST", "/api/quotations", {
        "customer_id": "DEMO-CUS-SGNFOOD", "route_id": "DEMO-RT-LONGAN-CAIMEP", "vehicle_type_id": "DEMO-VT-REEFER5",
        "cargo_type": "Hải sản đông lạnh", "packaging_spec": "Thùng lạnh nguyên khối", "weight_kg": 4800, "pallet_count": 8,
        "price_basis": "per_trip", "unit_price": cuocE3, "currency_code": "VND",
        "total_cost": gtE3, "selling_price": cuocE3, "valid_to": _han(30),
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
        # Tỷ giá bảng currencies: 1 LAK = 1,18 VND, nên giá thành VND của công thức
        # chia 1,18 là ra Kip. Quy cách KHÔNG dùng chữ "thùng": cửa Packing List
        # coi "thùng" là hàng đếm kiện.
        _in("\n[G] SGN Food — báo giá LAK, Xe lạnh 5 tấn, Long An → Cái Mép (112 km), hoàn tất trọn luồng")
        gtG, cuocG = gia_that("DEMO-RT-LONGAN-CAIMEP", "DEMO-VT-REEFER5", 4200, 20, 8,
                              tien="LAK", ty_gia=1.18, bien=0.28)
        oG = co_hoi(customer_id="DEMO-CUS-SGNFOOD", contact_name="Anh Khoa", source="email",
                    route_id="DEMO-RT-LONGAN-CAIMEP", cargo_type="Thực phẩm đông lạnh xuất Lào", est_weight_kg=4200,
                    est_trips_per_month=6, expected_price=round(cuocG * 1.18 * 0.95, -3),
                    owner="sales.hoa", notes="Khách thanh toán bằng Kip Lào")
        lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 9), 5, 15)
        qG = bao_gia_tu_co_hoi(oG, vehicle_type_id="DEMO-VT-REEFER5", cargo_type="Thực phẩm đông lạnh",
                               packaging_spec="Container lạnh nguyên khối", weight_kg=4200, volume_m3=20, pallet_count=8,
                               price_basis="per_trip", unit_price=cuocG, currency_code="LAK", fx_rate=1.18,
                               total_cost=gtG, selling_price=cuocG, valid_to=_han(30),
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
        chi_phi_thuc_te(tG, "COST-SGN-LAK-01", dong_chi_phi(
            "DEMO-RT-LONGAN-CAIMEP", "DEMO-VT-REEFER5", 4200, 20,
            lech={"fuel": 0.06, "wh": 0.50},
            ghi={"fuel": "Xe lạnh chạy máy lạnh cả chuyến", "wh": "Phí bãi lạnh"}))
    if "H" in cac_case:
        # ------------------------------------------------------------ H. Pou Yuen — USD, đầu kéo 20'
        # Tỷ giá 1 USD = 26.173,5 VND; giá thành và cước quy từ công thức VND sang USD.
        _in("\n[H] Pou Yuen — báo giá USD, Đầu kéo 20', Cát Lái → Amata (38,4 km), hoàn tất trọn luồng")
        gtH, cuocH = gia_that("DEMO-RT-CATLAI-AMATA", "DEMO-VT-TRACTOR20", 18000, 28, 16,
                              tien="USD", ty_gia=26173.5, bien=0.25)
        oH = co_hoi(customer_id="DEMO-CUS-POUYUEN", contact_name="Chị Mai", source="referral",
                    route_id="DEMO-RT-CATLAI-AMATA", cargo_type="Nguyên liệu giày nhập khẩu (cont 20')", est_weight_kg=18000,
                    est_trips_per_month=10, expected_price=round(cuocH * 0.95, 2),
                    owner="sales.minh", notes="Khách FDI thanh toán USD")
        lay1, lay2, giao1, giao2 = _khung(dt.date(2026, 9, 10), 8, 16)
        qH = bao_gia_tu_co_hoi(oH, vehicle_type_id="DEMO-VT-TRACTOR20", cargo_type="Nguyên liệu giày",
                               packaging_spec="Container nguyên khối 20FT", weight_kg=18000, volume_m3=28, pallet_count=16,
                               price_basis="per_trip", unit_price=cuocH, currency_code="USD", fx_rate=26173.5,
                               total_cost=gtH, selling_price=cuocH, valid_to=_han(30),
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
        chi_phi_thuc_te(tH, "COST-PY-USD-01", dong_chi_phi(
            "DEMO-RT-CATLAI-AMATA", "DEMO-VT-TRACTOR20", 18000, 28, lech={"fuel": 0.02},
            ghi={"fuel": "Xe này có đơn giá dầu riêng"}))

    _in("\nXONG case ngoại tệ. Kiểm qua API bàn giao:")
    for do_id in (doG[0], doH[0]):
        if not do_id:
            continue
        ct = _du_lieu(goi("GET", "/api/handover/delivery-orders/%s" % do_id))
        h = ct["header"]
        _in("   %s: %s  cước %s + trả thêm %s = giá cuối %s %s · giá thành thực tế %s · %d dòng, thiếu Acc code %d" % (
            h["do_id"], h["customer_id"], h["selling_price"], h["customer_surcharge_total"], h["final_selling_price"],
            h["currency"], h["actual_cost_total"], len(ct["details"]), sum(1 for x in ct["details"] if x["missing_acc_code"])))


# ================================================================ BƯỚC 3: GIEO SỐ LƯỢNG LỚN
#: Xe ↔ loại xe (báo giá chốt theo LOẠI, điều phối chặn nếu xe khác loại).
XE_THEO_LOAI = {
    "DEMO-VT-REEFER5": ["DEMO-50H-771.25"],
    "DEMO-VT-TRACTOR20": ["DEMO-51C-129.03", "DEMO-51C-301.88"],
    "DEMO-VT-20FT": ["DEMO-51C-268.89", "DEMO-61H-112.34"],
    "DEMO-VT-TRACTOR40": ["DEMO-51C-412.09", "DEMO-51C-556.12"],
    "DEMO-VT-TRUCK15": ["DEMO-61H-208.44"],
    "DEMO-VT-TRUCK10": ["DEMO-61H-330.17"],
}
#: Tải trọng tối đa từng loại (kg) — khai hàng quá tải là bị chặn CAPACITY_EXCEEDED.
TAI_TOI_DA = {"DEMO-VT-REEFER5": 5000, "DEMO-VT-TRUCK10": 10000, "DEMO-VT-TRUCK15": 15000,
              "DEMO-VT-TRACTOR20": 24000, "DEMO-VT-20FT": 28000, "DEMO-VT-TRACTOR40": 30000}
#: SỐ CHẶNG của tuyến — chỉ còn để mô tả. Từ 11/09 máy chủ cho mọi DO trong chuyến một chặng
#: HẠ HÀNG riêng tại điểm cuối (xem `tms_trip_service._xep_chang_cho_do`), nên ghép 2 DO lên
#: tuyến một chặng cũng hoàn tất được — bộ gieo cố ý làm thế để đường đó được đi thật.
SO_CHANG = {"DEMO-RT-VSIP2A-CATLAI": 2, "DEMO-RT-VSIP2A-CAIMEP": 2, "DEMO-RT-SONGTHAN-CATLAI": 1,
            "DEMO-RT-CATLAI-AMATA": 2, "DEMO-RT-LONGAN-CAIMEP": 3}
#: Thể tích tối đa từng loại (m³) — cửa năng lực xét CẢ tải trọng và thể tích.
THE_TICH_TOI_DA = {"DEMO-VT-REEFER5": 22.0, "DEMO-VT-TRUCK10": 45.0, "DEMO-VT-TRUCK15": 60.0,
                   "DEMO-VT-TRACTOR20": 33.0, "DEMO-VT-20FT": 33.2, "DEMO-VT-TRACTOR40": 67.0}
#: Tài xế chính (bằng còn hạn, có ca) — phụ xe để riêng.
TAI_XE_CHINH = ["DEMO-DRV-001", "DEMO-DRV-002", "DEMO-DRV-004", "DEMO-DRV-005",
                "DEMO-DRV-006", "DEMO-DRV-008", "DEMO-DRV-009", "DEMO-DRV-010",
                "DEMO-DRV-011", "DEMO-DRV-012"]
#: Tuyến ↔ (km, toạ độ đầu, toạ độ cuối) để mốc thực thi có GPS vẽ được.
TUYEN_DEMO = {
    "DEMO-RT-VSIP2A-CATLAI": (44.7, "VSIP2A", "CATLAI"),
    "DEMO-RT-VSIP2A-CAIMEP": (96.5, "VSIP2A", "CAIMEP"),
    "DEMO-RT-SONGTHAN-CATLAI": (31.2, "SONGTHAN", "CATLAI"),
    "DEMO-RT-CATLAI-AMATA": (38.4, "CATLAI", "AMATA"),
    "DEMO-RT-LONGAN-CAIMEP": (112.0, "LONGAN", "CAIMEP"),
}
#: Khách thêm cho đủ mặt hàng và đủ đầu mối (gieo qua POST /api/customers).
KHACH_THEM = [
    ("DEMO-CUS-VINAMILK", "Vinamilk Bình Dương", "Chị Ngân", "0903111222", "KCN Mỹ Phước, Bình Dương"),
    ("DEMO-CUS-SAMSUNG", "Samsung Electronics HCMC CE", "Anh Hoàng", "0903222333", "KCN Cao, TP. Thủ Đức"),
    ("DEMO-CUS-ACECOOK", "Acecook Việt Nam", "Chị Thảo", "0903333444", "KCN Tân Bình, TP.HCM"),
    ("DEMO-CUS-BIDRICO", "Nước giải khát Bidrico", "Anh Kiệt", "0903444555", "KCN Vĩnh Lộc, TP.HCM"),
    ("DEMO-CUS-TAEKWANG", "Taekwang Vina", "Chị Hà", "0903555666", "KCN Amata, Biên Hoà"),
    ("DEMO-CUS-DUCGIANG", "Hoá chất Đức Giang", "Anh Sơn", "0903666777", "KCN Long Thành, Đồng Nai"),
    ("DEMO-CUS-THACO", "THACO Auto Chu Lai", "Anh Bình", "0903777888", "KCN Chu Lai, Quảng Nam"),
    ("DEMO-CUS-LOTTE", "Lotte Mart Việt Nam", "Chị Quyên", "0903888999", "Quận 7, TP.HCM"),
]
#: Loại hàng theo khách — để màn nào cũng đọc ra nghiệp vụ thật, không phải chữ mẫu.
HANG_THEO_KHACH = {
    "DEMO-CUS-NIDEC": "Linh kiện điện tử", "DEMO-CUS-UNILEVER": "Hàng tiêu dùng",
    "DEMO-CUS-COLGATE": "Hoá mỹ phẩm", "DEMO-CUS-POUYUEN": "Nguyên liệu giày",
    "DEMO-CUS-SGNFOOD": "Thực phẩm đông lạnh", "DEMO-CUS-VINAMILK": "Sữa và sản phẩm sữa",
    "DEMO-CUS-SAMSUNG": "Hàng điện tử gia dụng", "DEMO-CUS-ACECOOK": "Mì ăn liền",
    "DEMO-CUS-BIDRICO": "Nước giải khát", "DEMO-CUS-TAEKWANG": "Nguyên phụ liệu may",
    "DEMO-CUS-DUCGIANG": "Hoá chất công nghiệp (không nguy hại)", "DEMO-CUS-THACO": "Phụ tùng ô tô",
    "DEMO-CUS-LOTTE": "Hàng bán lẻ siêu thị",
}
#: Nhãn của LƯỢT GIEO này, để mã chuyến và mã phiếu chi phí không trùng lượt trước
#: (`TRIP_IDEMPOTENCY_CONFLICT`: cùng mã Trip mà danh sách DO khác thì máy chủ từ chối).
NHAN_LUOT = dt.datetime.now(VN).strftime("%d%H%M") + uuid.uuid4().hex[:4].upper()
NGUOI_NHAN = ["Anh Nam (cảng)", "Chị Thu (kho)", "Anh Phong (CMIT)", "Anh Dũng (Amata)",
              "Chị Loan (kho Long An)", "Anh Tuấn (Sóng Thần)"]
TIEN_VA_TY_GIA = [("VND", 1.0)] * 7 + [("USD", 26173.5), ("LAK", 1.18), ("THB", 710.0)]


def bo_sung_du_lieu_goc():
    """Thêm khách và ca trực — KHÔNG sửa khách/xe/tài xế/tuyến/công thức đang có."""
    _in("[0] Bổ sung dữ liệu gốc (chỉ THÊM, không sửa cái đang có)")
    for ma, ten, lh, dt_, dc in KHACH_THEM:
        goi("POST", "/api/customers", {"id": ma, "name": ten, "type": "Account",
                                       "contact_person": lh, "phone": dt_, "address": dc},
            cho_phep=(200, 201, 409))
    # Ca trực phủ rộng: gieo case ở nhiều ngày nên thiếu ca là bị chặn ngay. Chia thành các
    # khoảng KHÔNG chồng nhau, vì ca chồng ca bị từ chối (và bộ dữ liệu đã có ca tháng 9–10).
    khoang = [(dt.datetime(2026, 7, 1, 0, 0, tzinfo=VN), dt.datetime(2026, 8, 31, 23, 58, tzinfo=VN), "CA-T7T8"),
              (dt.datetime(2026, 11, 1, 0, 0, tzinfo=VN), dt.datetime(2026, 12, 31, 23, 58, tzinfo=VN), "CA-T11T12")]
    for tx in TAI_XE_CHINH:
        ca_truc("CA-T9T10-" + tx, tx, dt.datetime(2026, 9, 1, 0, 0, tzinfo=VN),
                dt.datetime(2026, 10, 31, 23, 59, tzinfo=VN))
        for d1, d2, ten in khoang:
            ca_truc("%s-%s" % (ten, tx), tx, d1, d2)


def _gia(tuyen, loai, kg, tien, ty_gia, bien=0.28, the_tich=None, im=True):
    """Giá thành và cước của một case gieo hàng loạt, lấy từ công thức thật.

    Trước đây hàm này tự bịa giá thành bằng `km × 7000 + 450000`, một công thức
    không có ở đâu trong hệ thống. Nghĩa là hàng chục báo giá demo mang giá thành
    không khớp công thức loại xe của chính chúng, và màn báo giá tính lại thì ra
    số khác. Giờ hỏi thẳng máy chủ như màn hình vẫn làm.
    """
    return gia_that(tuyen, loai, kg, volume_m3=the_tich, tien=tien, ty_gia=ty_gia,
                    bien=bien, im=im)


def _mot_case(chi_so, khach, tuyen, loai, xe, tai_xe, ngay, tien, ty_gia, giai_doan,
              phu_xe=None, bien=0.28, so_cont=1):
    """Gieo MỘT case tới `giai_doan`: bao_gia | do | trip | dang_chay | hoan_tat.

    Trả `(qid, [do_id], trip_id|None)`. Mỗi giai đoạn là một điểm dừng thật của luồng, nên
    dữ liệu gieo ra nằm đúng màn mà người vận hành sẽ thấy nó.
    """
    km, diem_dau, diem_cuoi = TUYEN_DEMO[tuyen]
    kg = int(TAI_TOI_DA[loai] * 0.7)
    the_tich = round(THE_TICH_TOI_DA[loai] * 0.7, 1)
    gia_thanh, cuoc = _gia(tuyen, loai, kg, tien, ty_gia, bien, the_tich=the_tich)
    hang = HANG_THEO_KHACH.get(khach, "Hàng tổng hợp")
    lay1, lay2, giao1, giao2 = _khung(ngay, 6 + (chi_so % 4), 15 + (chi_so % 4))
    o = co_hoi(customer_id=khach, contact_name="Liên hệ %s" % khach.split("-")[-1].title(),
               source=("email", "phone", "referral", "web")[chi_so % 4], route_id=tuyen,
               cargo_type=hang, est_weight_kg=kg, est_trips_per_month=4 + chi_so % 12,
               expected_price=cuoc, owner=("sales.hoa", "sales.minh")[chi_so % 2])
    if giai_doan == "co_hoi":
        return None, [], None
    qid = bao_gia_tu_co_hoi(
        o, vehicle_type_id=loai, cargo_type=hang,
        packaging_spec="Nguyên khối, niêm phong tại kho", weight_kg=kg,
        volume_m3=round(THE_TICH_TOI_DA[loai] * 0.7, 1), pallet_count=0,
        price_basis="per_trip", unit_price=cuoc, currency_code=tien,
        fx_rate=ty_gia, total_cost=gia_thanh, selling_price=cuoc, valid_to=_han(30 + chi_so % 30),
        pickup_window_start=_iso(lay1), pickup_window_end=_iso(lay2),
        delivery_window_start=_iso(giao1), delivery_window_end=_iso(giao2),
        payment_terms=("30 ngày", "45 ngày", "15 ngày", "Trả ngay")[chi_so % 4],
        sales_rep=("Hoa", "Minh")[chi_so % 2], trips_per_month=4 + chi_so % 12,
        notes_customer="Giá gồm phí nâng hạ tại cảng." if chi_so % 3 == 0 else None,
        notes_ops="Liên hệ bảo vệ cổng %d trước khi vào." % (1 + chi_so % 3))
    hang_hoa(qid, [{"name": "%s (%s)" % (hang, tien), "quantity": so_cont,
                    "uom": "Cont" if "TRACTOR" in loai or "20FT" in loai else "Chuyến"}])
    if giai_doan == "bao_gia_nhap":
        return qid, [], None
    kq = gui(qid)
    if (kq or {}).get("canonical_status") == "pending_approval":
        if giai_doan == "cho_duyet":
            return qid, [], None
        duyet_noi_bo(qid)
    if giai_doan == "bao_gia":
        return qid, [], None
    if giai_doan == "tu_choi":
        tu_choi(qid, ("Khách chọn nhà xe khác.", "Khách lùi kế hoạch sang quý sau.",
                      "Giá cao hơn ngân sách khách.")[chi_so % 3])
        return qid, [], None
    ds = chap_nhan(qid, [{"pickup_at": _iso(lay1 + dt.timedelta(hours=i)), "due_at": _iso(giao2),
                          "seal_no": "SL-%s-%04d" % (khach.split("-")[-1][:3].upper(), chi_so * 10 + i)}
                         for i in range(so_cont)])
    if giai_doan == "do":
        return qid, ds, None
    ma_trip = "TRIP-%s-%03d" % (NHAN_LUOT, chi_so)
    trip = lap_chuyen(ma_trip, ds, lay1 + dt.timedelta(hours=1),
                      [{"sequence_no": 1, "stop_name": diem_cuoi.title(),
                        "receiver_name": NGUOI_NHAN[chi_so % len(NGUOI_NHAN)],
                        "receiver_phone": "09090%05d" % chi_so, "delivery_note": "Hạ hàng đúng cổng đã hẹn"}])
    if giai_doan == "trip":
        return qid, ds, ma_trip
    if giai_doan == "huy_trip":
        goi("POST", "/api/tms/trips/%s/cancel" % ma_trip,
            {"expected_version": trip["version"],
             "reason": ("Khách lùi ngày lấy hàng.", "Xe vào xưởng đột xuất.",
                        "Kho đóng cửa kiểm kê.")[chi_so % 3]},
            headers={"Idempotency-Key": "huy-" + ma_trip})
        return qid, ds, ma_trip
    trip = dieu_phoi(trip, xe, tai_xe, lay1, giao2, phu_xe=phu_xe)
    g0 = lay1
    day_du = [("check_in", g0), ("pickup", g0 + dt.timedelta(minutes=40 + chi_so % 30)),
              ("departure", g0 + dt.timedelta(hours=1, minutes=chi_so % 30)),
              ("arrival", g0 + dt.timedelta(hours=2 + int(km // 45), minutes=chi_so % 40)),
              ("unloading", g0 + dt.timedelta(hours=2 + int(km // 45), minutes=25 + chi_so % 20))]
    if giai_doan == "dang_chay":
        # Xe đang trên đường: chỉ ghi tới mốc tương ứng, KHÔNG hoàn tất.
        moc_thuc_thi(trip, xe, tai_xe, day_du[:1 + chi_so % 4], (TOA_DO[diem_dau], TOA_DO[diem_cuoi]))
        return qid, ds, ma_trip
    moc_thuc_thi(trip, xe, tai_xe, day_du, (TOA_DO[diem_dau], TOA_DO[diem_cuoi]))
    giao_luc = g0 + dt.timedelta(hours=3 + int(km // 45), minutes=chi_so % 45)
    phu = ()
    if chi_so % 3 == 0:
        muc = round((cuoc * 0.06) if tien != "VND" else round(cuoc * 0.06, -3), 2)
        phu = ((("Chờ bãi quá giờ", "Cảng kẹt, xe chờ hạ hàng", muc),)
               if chi_so % 6 == 0 else (("Bốc xếp thêm tại kho", "Kho không có xe nâng", muc),))
    for do_id in ds:
        hoan_tat(do_id, trip, xe, giao_luc, NGUOI_NHAN[chi_so % len(NGUOI_NHAN)],
                 phu_phi=phu, tien=tien)
    # Chi phí thực tế LUÔN bằng VNĐ (tiền chức năng): dầu, BOT, phụ cấp đều chi bằng đồng.
    # Cột chốt ban đầu lấy từ công thức; phần vượt xoay theo chỉ số case để mỗi
    # chuyến lệch một kiểu, có chuyến đúng kế hoạch, có chuyến vượt dầu hoặc bãi.
    chi_phi_thuc_te(trip, "COST-%s-%03d" % (NHAN_LUOT, chi_so), dong_chi_phi(
        tuyen, loai, kg, the_tich,
        lech={"fuel": (chi_so % 5) * 0.02, "toll": (chi_so % 4) * 0.05,
              "wh": (chi_so % 3) * 0.15},
        ghi={"fuel": "%.1f km" % km, "driver": "Có phụ xe" if phu_xe else ""}),
        gui_duyet=(chi_so % 5 != 0))   # một phần năm để NHÁP, cho kế toán thấy việc còn phải làm
    return qid, ds, ma_trip


def _nguon_luc_dang_bi_chiem():
    """Xe / tài xế đang giữ một chuyến CHƯA hoàn tất — điều thêm là 409 RESOURCE_BUSY.

    Cửa này KHÁC cửa trùng giờ: nó không xét khung thời gian, chỉ cần người đó còn một
    chuyến chưa đóng là chặn. Nên lịch gieo phải đọc trạng thái thật trước, không đoán.
    """
    ds = _du_lieu(goi("GET", "/api/tms/trips?limit=200"))
    ds = ds if isinstance(ds, list) else (ds.get("items") or [])
    xe, tx = set(), set()
    for t in ds:
        if str(t.get("status") or "") in ("completed", "cancelled"):
            continue
        if t.get("vehicle_id"):
            xe.add(t["vehicle_id"])
        for k in ("driver_id", "co_driver_id"):
            if t.get(k):
                tx.add(t[k])
    return xe, tx


def gieo_nhieu(so_hoan_tat=22, so_dang_chay=6):
    """Gieo dày dữ liệu qua API thật: nhiều đơn đã xong, đang chạy, chờ điều phối, báo giá mở.

    Chủ dự án (11/09): *"thêm cho anh nhiều dữ liệu hơn đi hiện tại ít dữ liệu quá"* — màn
    Theo dõi chỉ có MỘT chuyến. Gieo THÊM, không xoá dữ liệu đang có.

    RÀNG BUỘC THẬT phải tôn trọng, nên lịch xếp tay chứ không random:
      · xe/tài xế đang giữ chuyến CHƯA hoàn tất thì không điều thêm (RESOURCE_BUSY) — nên
        các case ĐÃ HOÀN TẤT gieo TRƯỚC (hoàn tất là nhả nguồn lực), các case ĐANG CHẠY gieo
        SAU CÙNG (chúng giữ xe lại vĩnh viễn), và nguồn lực đang bị chiếm sẵn bị loại ra;
      · mỗi case hoàn tất một NGÀY riêng → không trùng giờ phân công trên cùng một xe;
      · xe phải đúng LOẠI của báo giá (VEHICLE_TYPE_MISMATCH) → chọn từ `XE_THEO_LOAI`;
      · hàng không vượt tải và không vượt thể tích (CAPACITY_EXCEEDED) → khai 70% cả hai;
      · quy cách phải "nguyên khối" và có số niêm phong, không thì cửa Packing List chặn —
        và không được chứa chữ "kiện/thùng/pallet/bao" vì mẫu đếm kiện thắng trước;
      · báo giá lỗ không gửi được → giá thành và cước CÙNG đơn vị tiền, biên 28%.
    """
    hom_nay = dt.datetime.now(VN).date()
    bo_sung_du_lieu_goc()
    khach = [k for k, _, _, _, _ in KHACH_THEM] + [
        "DEMO-CUS-NIDEC", "DEMO-CUS-UNILEVER", "DEMO-CUS-COLGATE", "DEMO-CUS-POUYUEN", "DEMO-CUS-SGNFOOD"]
    tuyen = list(TUYEN_DEMO)
    xe_bi_chiem, tx_bi_chiem = _nguon_luc_dang_bi_chiem()
    _in("   Đang bị chiếm bởi chuyến chưa xong: xe %s · tài xế %s"
        % (sorted(xe_bi_chiem) or "(không)", sorted(tx_bi_chiem) or "(không)"))
    cap_xe = [(loai, x) for loai, ds in XE_THEO_LOAI.items() for x in ds if x not in xe_bi_chiem]
    tx_ranh = [t for t in TAI_XE_CHINH if t not in tx_bi_chiem]
    if not cap_xe or not tx_ranh:
        raise SystemExit("Hết xe hoặc tài xế rảnh — hoàn tất vài chuyến đang chạy rồi gieo lại.")

    # MỘT XE MỘT CHUYẾN MỖI NGÀY, và xe thứ j luôn đi với tài xế thứ j trong ngày đó — nếu
    # ghép lệch nhau thì cùng một tài xế có thể nhận hai chuyến trùng giờ trong một ngày
    # (RESOURCE_TIME_OVERLAP). Ngày lùi dần từ hôm qua, nằm trong khoảng ca tháng 9 đã có.
    if len(tx_ranh) < len(cap_xe):
        cap_xe = cap_xe[:len(tx_ranh)]
    _in("\n[1] %d đơn ĐÃ HOÀN TẤT (%d xe × nhiều ngày, mỗi xe một chuyến mỗi ngày)"
        % (so_hoan_tat, len(cap_xe)))
    for i in range(so_hoan_tat):
        vi_tri = i % len(cap_xe)
        loai, xe = cap_xe[vi_tri]
        tien, ty_gia = TIEN_VA_TY_GIA[i % len(TIEN_VA_TY_GIA)]
        rt = tuyen[i % len(tuyen)]
        so_cont = 2 if (i % 7 == 0 and TAI_TOI_DA[loai] >= 24000) else 1   # kể cả tuyến 1 chặng
        _mot_case(100 + i, khach[i % len(khach)], rt, loai, xe,
                  tx_ranh[vi_tri], hom_nay - dt.timedelta(days=1 + i // len(cap_xe)),
                  tien, ty_gia, "hoan_tat", so_cont=so_cont)
    _in("   → %d đơn hoàn tất" % so_hoan_tat)

    _in("\n[2] Chuyến ĐÃ LẬP chờ điều phối, DO chờ lập chuyến, chuyến bị huỷ (không giữ xe)")
    for i in range(4):
        loai, xe = cap_xe[i % len(cap_xe)]
        _mot_case(300 + i, khach[(i + 1) % len(khach)], tuyen[i % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=2 + i), "VND", 1.0, "trip")
    for i in range(5):
        loai, xe = cap_xe[(i + 2) % len(cap_xe)]
        _mot_case(320 + i, khach[(i + 5) % len(khach)], tuyen[(i + 1) % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=4 + i), "VND", 1.0, "do")
    for i in range(2):
        loai, xe = cap_xe[(i + 4) % len(cap_xe)]
        _mot_case(340 + i, khach[(i + 7) % len(khach)], tuyen[(i + 2) % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=6 + i), "VND", 1.0, "huy_trip")

    _in("\n[3] Báo giá đang mở: chờ khách, chờ duyệt nội bộ (biên mỏng), nháp, bị từ chối")
    for i in range(5):
        loai, xe = cap_xe[i % len(cap_xe)]
        tien, ty_gia = TIEN_VA_TY_GIA[(i + 2) % len(TIEN_VA_TY_GIA)]
        _mot_case(400 + i, khach[(i + 2) % len(khach)], tuyen[i % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=8 + i), tien, ty_gia, "bao_gia")
    for i in range(3):
        loai, xe = cap_xe[i % len(cap_xe)]
        _mot_case(420 + i, khach[(i + 4) % len(khach)], tuyen[i % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=10 + i), "VND", 1.0,
                  "cho_duyet", bien=0.10)      # biên 10% < ngưỡng 15% → chờ duyệt nội bộ
    for i in range(3):
        loai, xe = cap_xe[i % len(cap_xe)]
        _mot_case(440 + i, khach[(i + 6) % len(khach)], tuyen[i % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=12 + i), "VND", 1.0, "bao_gia_nhap")
    for i in range(3):
        loai, xe = cap_xe[i % len(cap_xe)]
        _mot_case(460 + i, khach[(i + 8) % len(khach)], tuyen[i % len(tuyen)], loai, xe,
                  tx_ranh[i % len(tx_ranh)], hom_nay + dt.timedelta(days=14 + i), "VND", 1.0, "tu_choi")

    _in("\n[4] Cơ hội CRM chưa lập báo giá, ở các giai đoạn")
    for i, gd in enumerate(["new", "contacted", "negotiating", "contacted", "new", "negotiating"]):
        o = co_hoi(prospect_name=("Cơ khí Đại Dũng", "Gỗ An Cường", "Thép Hoà Phát Dung Quất",
                                  "Bia Sài Gòn Miền Tây", "Nhựa Duy Tân", "Giấy Sài Gòn")[i],
                   contact_name=("Anh Tú", "Chị Yến", "Anh Khánh", "Chị Diệp", "Anh Lộc", "Chị Vy")[i],
                   source=("phone", "web", "tender", "referral", "email", "other")[i],
                   route_id=tuyen[i % len(tuyen)],
                   cargo_type=("Kết cấu thép", "Tấm gỗ MDF", "Thép cuộn", "Bia lon",
                               "Hạt nhựa", "Giấy cuộn")[i],
                   est_weight_kg=8000 + i * 2500, est_trips_per_month=3 + i * 2,
                   expected_price=1200000 + i * 300000, owner=("sales.hoa", "sales.minh")[i % 2])
        if gd in ("contacted", "negotiating"):
            o = doi_giai_doan(o, "contacted")
        if gd == "negotiating":
            doi_giai_doan(o, "negotiating")

    # ĐANG CHẠY gieo SAU CÙNG: mỗi chuyến giữ một xe và một tài xế cho tới khi hoàn tất, nên
    # gieo trước sẽ làm mọi case sau đó hết nguồn lực.
    _in("\n[5] %d chuyến ĐANG CHẠY hôm nay (mỗi chuyến một xe riêng, dừng ở mốc khác nhau)"
        % min(so_dang_chay, len(cap_xe), len(tx_ranh)))
    for i in range(min(so_dang_chay, len(cap_xe), len(tx_ranh))):
        loai, xe = cap_xe[i]
        tien, ty_gia = TIEN_VA_TY_GIA[i % len(TIEN_VA_TY_GIA)]
        _mot_case(200 + i, khach[(i + 3) % len(khach)], tuyen[i % len(tuyen)], loai, xe,
                  tx_ranh[i], hom_nay, tien, ty_gia, "dang_chay")

    _in("\n[6] Sự cố trên các chuyến đang chạy")
    ds_trip = _du_lieu(goi("GET", "/api/tms/trips?limit=200"))
    dang = [t for t in (ds_trip if isinstance(ds_trip, list) else ds_trip.get("items") or [])
            if t.get("status") == "in_transit"][:4]
    loai_su_co = [("Kẹt xe", "Low", "QL51 đoạn Long Thành", "Kẹt 40 phút do tai nạn phía trước."),
                  ("Hỏng hóc", "High", "Vành đai 3", "Nổ lốp sau bên phải, đã gọi cứu hộ."),
                  ("Thời tiết", "Medium", "Cầu Phú Mỹ", "Mưa lớn, giảm tốc độ để an toàn."),
                  ("Giấy tờ", "Low", "Cổng cảng Cát Lái", "Thiếu một bản sao tờ khai, đã bổ sung.")]
    for i, t in enumerate(dang):
        ma_do = (t.get("delivery_order_ids") or [None])[0]
        if not ma_do or not t.get("vehicle_id"):
            continue
        ten, muc, vi_tri, mo_ta = loai_su_co[i % len(loai_su_co)]
        su_co(ma_do, t["vehicle_id"], ten, vi_tri, mo_ta, muc)

    _in("\nXONG. Đếm lại:")
    kiem()


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
    p.add_argument("--gieo-nhieu", action="store_true", help="gieo THÊM nhiều dữ liệu (không xoá cái đang có)")
    p.add_argument("--so-hoan-tat", type=int, default=22)
    p.add_argument("--so-dang-chay", type=int, default=6)
    a = p.parse_args()
    if not (a.xoa or a.gieo or a.gieo_ngoai_te or a.gieo_nhieu or a.kiem):
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
    if a.gieo_nhieu:
        if not TOKEN:
            sys.exit("Thiếu EPL_TMS_API_TOKEN (trong .env hoặc biến môi trường).")
        gieo_nhieu(a.so_hoan_tat, a.so_dang_chay)
    if a.kiem:
        kiem()
