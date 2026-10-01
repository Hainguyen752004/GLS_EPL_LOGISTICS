# -*- coding: utf-8 -*-
"""GỬI ĐỀ NGHỊ THU sang hệ kế toán anh Tune: một DO đã về + đã khoá → SO + công nợ khách bên đó.

    POST {goc}/api/v1/integrations/logistics/sales-orders          (hợp đồng kế toán, mục 3.2)

Hướng dẫn của anh Tune (EPL_System `docs/logistics-sales-orders-api-guide.md`, 11/09) và bộ gửi đã chạy được của
EPL_System (`services/ghi_so_kinh_doanh.py`) là khuôn. NHỮNG ĐIỀU PHẢI GIỮ:

* Token nằm ở máy chủ (biến môi trường), không xuống trình duyệt. Dùng lại token đã có của cùng hệ (`EPL_ACC_CODE_TOKEN`,
  API danh mục tài khoản) nếu không đặt riêng `QLSX_ACCESS_TOKEN`.
* Gói đúng BA khoá gốc `schemaVersion / header / details`. `header.customer_id` là mã khách ĐÃ CÓ trong danh mục bên anh
  Tune (PUBOBJECT.OBJ_OBJECTNO) — bên đó không tự tạo khách (lỗi 52905). Bên mình lấy ở ô "Mã khách" của danh mục khách.
* Tiền là số JSON, tổng khớp CHÍNH XÁC: selling_price + customer_surcharge_total = final_selling_price = Σ dòng thu. Kiểm
  bằng Decimal trước khi gửi. Chỉ VND / LAK / USD — cước THB, CNY chặn ở đây (câu hỏi 10.3 của hợp đồng).
* Một dòng THU (cước) như hợp đồng 3.2. Đọc mã nguồn bên anh (01/10): dòng `chi` được nhận nhưng chỉ ghép thành chữ vào
  mô tả mặt hàng và ghi chú dòng SO của KHÁCH (không thành bút toán chi), quá sức chứa cột thì 52909 — nên không gửi.
* Idempotency-Key ổn định `logistics:EPLLAO-<Trip.id>`. Lần gửi mà kết quả CHƯA RÕ (mất mạng, hết giờ, 5xx, 52903) thì gửi
  lại ĐÚNG gói và khoá đã lưu. Bị từ chối rõ ràng (4xx dữ liệu) thì dựng gói mới theo số hiện tại — bên đó không ghi gì.
* Lỗi có thể về dưới dạng HTTP 200 kèm `Success: false` — đọc cả thân, không tin mỗi mã HTTP.
* Chỉ `synced` khi 201, hoặc 200 `replayed: true`, kèm `data` hợp lệ.
"""
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from fastapi import HTTPException

from models import GuiSoTune, ma_moi
from services import ban_giao as BG

TIEN_NHAN = ("VND", "LAK", "USD")
GOC_MAC_DINH = "https://demo-lao-api.goldensme.com"
DUONG = "/api/v1/integrations/logistics/sales-orders"
CHO_GIAY = 60
# Luật mã của bên anh Tune (GLS-QLSX-APIs `LogisticsPushValidator.Code` + `sp_Logistics_CreateSalesOrder`): mở đầu bằng
# chữ Latinh / số, sau đó chỉ chữ, số và _ . - ; mã khách và mã tuyến ghép "<khách>_<tuyến>" thành mã mặt hàng ≤ 50.
# Mã tuyến bên em dài 12 (`models.ma_moi`) → mã khách tối đa 37. Danh mục khách dùng chung luật này để chặn từ lúc gán mã.
MA_HOP_LE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
DAI_MA_TUYEN = len(ma_moi())
MA_KHACH_TOI_DA = 50 - 1 - DAI_MA_TUYEN
KEY_HOP_LE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,99}$")
GIOI_HAN = Decimal("9999999999999")
# khoá header gửi đi: khoá bắt buộc + khoá "nên gửi nếu có" của hướng dẫn. Bỏ các khối lồng không thuộc hợp đồng
# (hire, fx_rates_on_trip, cost_by_section_lak) — không thử vận may với bộ kiểm bên đó.
KHOA_HEADER = ("do_id", "status", "customer_id", "route", "currency", "currency_thu", "currency_chi", "selling_price",
               "customer_surcharge_total", "final_selling_price", "billed_qty", "quotation_id", "origin", "destination",
               "trip_id", "vehicle_id", "driver_id", "weight_kg", "pod_receiver", "pod_signed_at")
KET_QUA_CHUA_RO = ("QLSX_KHONG_GOI_DUOC", "LOGISTICS_52903")


def _loi(ma, loi, http=422):
    raise HTTPException(http, {"ma": ma, "loi": loi})


def loi_ma_khach(ma):
    """Câu lỗi nếu `ma` không gửi được sang bên kế toán; hợp lệ thì None."""
    if len(ma) > MA_KHACH_TOI_DA or not MA_HOP_LE.match(ma):
        return ("Mã khách phải mở đầu bằng chữ Latinh hoặc số, chỉ gồm chữ Latinh, số và - _ . (không dấu cách, không /), "
                "tối đa %d ký tự — bên kế toán ghép mã khách với mã tuyến thành mã mặt hàng ≤ 50 ký tự." % MA_KHACH_TOI_DA)
    return None


def cau_hinh():
    """(gốc, token). `EPL_ACC_CODE_API` có thể là cả đường country-accounts — chỉ lấy giao thức + tên máy."""
    goc = (os.getenv("QLSX_BASE_URL") or "").strip()
    if not goc:
        acc = (os.getenv("EPL_ACC_CODE_API") or "").strip()
        if acc:
            u = urlsplit(acc)
            goc = "%s://%s" % (u.scheme, u.netloc) if u.scheme and u.netloc else ""
    goc = (goc or GOC_MAC_DINH).rstrip("/")
    token = (os.getenv("QLSX_ACCESS_TOKEN") or os.getenv("EPL_ACC_CODE_TOKEN") or "").strip()
    return goc, token


def khoa(do_id):
    k = "logistics:%s" % do_id
    if not KEY_HOP_LE.match(k):
        _loi("KEY_SAI", "Mã DO %s không dựng được Idempotency-Key hợp lệ." % do_id)
    return k


def _tien(v, ten):
    if v is None:
        _loi("THIEU_TIEN", "Thiếu %s." % ten)
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        _loi("TIEN_SAI", "%s không phải số: %r." % (ten, v))
    if not d.is_finite():
        _loi("TIEN_SAI", "%s không phải số hữu hạn." % ten)
    d = d.quantize(Decimal("0.00001"))
    if d < 0 or d > GIOI_HAN:
        _loi("TIEN_NGOAI_KHOANG", "%s = %s nằm ngoài khoảng bên kế toán nhận (0 … 9.999.999.999.999)." % (ten, d))
    return d


def _so_json(d):
    """Số JSON đúng từng chữ số: bên kia đọc bằng decimal(18,5) và so tổng bằng dấu "=" — số lẻ mà float làm tròn
    (quá ~15 chữ số có nghĩa) thì chặn, không gửi một con số khác."""
    d = d.normalize()
    if d == d.to_integral_value():
        return int(d)
    f = float(d)
    if Decimal(repr(f)) != d:
        _loi("TIEN_QUA_NHIEU_SO", "Số %s có quá nhiều chữ số lẻ để gửi chính xác — làm tròn trên phiếu rồi gửi lại." % d)
    return f


def dung_goi(db, p):
    """Gói gửi từ chính gói bàn giao DO (một nguồn số với `GET /api/handover/delivery-orders/{do_id}`).
    Trả (body, tom_tat); vi phạm luật thì HTTPException 422 với câu nói rõ phải sửa gì."""
    if not BG.ban_giao_duoc(p):
        _loi("DO_CHUA_KHOA", "Phiếu %s chưa về hoặc chưa khoá — DO xong mới đề nghị thu." % p.doc_no, 409)
    g = BG.dong_goi(db, p)
    h0 = g["header"]
    do_id = h0["do_id"]
    if len(do_id) > 100 or not MA_HOP_LE.match(do_id):
        _loi("MA_DO_SAI", "Mã DO %r không hợp lệ với bên kế toán." % do_id)
    ma_khach = (h0.get("customer_code") or "").strip()
    if not ma_khach:
        _loi("THIEU_MA_KHACH_KE_TOAN", "Khách %s chưa có mã khách bên kế toán. KT Thu/Chi Viêng Chăn ghi ở danh mục Khách hàng "
                                       "— mã phải có sẵn trong danh mục khách bên kế toán." % (p.customer_name or "—"))
    if loi_ma_khach(ma_khach):
        _loi("MA_KHACH_SAI", "Mã khách %r: %s" % (ma_khach, loi_ma_khach(ma_khach)))
    tuyen = h0.get("route") or None
    if not tuyen or not tuyen.get("id"):
        _loi("THIEU_TUYEN", "Phiếu %s chưa gắn tuyến — bên kế toán tạo mặt hàng theo khách + tuyến nên bắt buộc có tuyến." % p.doc_no)
    ma_tuyen = str(tuyen["id"])
    if len(ma_tuyen) > 50 or not MA_HOP_LE.match(ma_tuyen):
        _loi("MA_TUYEN_SAI", "Mã tuyến %r không hợp lệ với bên kế toán." % ma_tuyen)
    if len(ma_khach) + 1 + len(ma_tuyen) > 50:
        _loi("MA_GHEP_QUA_DAI", "Mã mặt hàng %s_%s dài %d ký tự, bên kế toán chỉ nhận tới 50 — rút ngắn mã khách."
             % (ma_khach, ma_tuyen, len(ma_khach) + 1 + len(ma_tuyen)))
    tien = str(h0.get("currency") or "").upper()
    if tien not in TIEN_NHAN:
        _loi("TIEN_TE_CHUA_NHAN", "Bên kế toán mới nhận cước VND, LAK, USD — cước phiếu %s bằng %s. Chờ anh Tune mở thêm tiền "
                                  "này (câu hỏi 10.3)." % (p.doc_no, tien or "?"))
    gia = _tien(h0.get("final_selling_price"), "Cước (final_selling_price)")
    if gia <= Decimal("0.01"):
        _loi("CUOC_BANG_KHONG", "Cước phiếu %s là %s %s — bên kế toán đòi lớn hơn 0.01." % (p.doc_no, _so_json(gia), tien))
    thu = next((d for d in g["details"] if d.get("kind") == "thu"), None) or {}

    header = {k: h0.get(k) for k in KHOA_HEADER if h0.get(k) is not None}
    header.update({"status": "delivered", "customer_id": ma_khach, "currency": tien, "currency_thu": tien,
                   "selling_price": _so_json(gia), "customer_surcharge_total": 0, "final_selling_price": _so_json(gia),
                   "route": {k: v for k, v in (("id", ma_tuyen), ("name", tuyen.get("name")),
                                               ("distance_km", tuyen.get("distance_km"))) if v is not None}})
    details = [{"line_no": 1, "kind": "thu", "charge_type": "freight",
                "name": thu.get("name") or "Cước vận chuyển %s" % p.doc_no, "actual_amount": _so_json(gia), "currency": tien}]
    body = {"schemaVersion": 1, "header": header, "details": details}
    tom_tat = {"do_id": do_id, "doc_no": p.doc_no, "customer_code": ma_khach, "customer_name": p.customer_name,
               "route_id": ma_tuyen, "route_name": tuyen.get("name"), "currency": tien, "final_selling_price": _so_json(gia),
               "item_code": "%s_%s" % (ma_khach, ma_tuyen)}
    return body, tom_tat


def goi(body_json, key, goc, token):
    """POST sang bên kế toán. Trả (http, thân_dict | None, thân_thô). Lỗi HTTP không ném."""
    yc = urllib.request.Request(goc + DUONG, data=body_json.encode("utf-8"), method="POST",
                                headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                                         "Accept": "application/json", "Idempotency-Key": key,
                                         "User-Agent": "EPL-LAO-Logistics/1.0 (de nghi thu)"})
    try:
        with urllib.request.urlopen(yc, timeout=CHO_GIAY) as t:
            ma, tho = t.status, t.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        ma, tho = e.code, e.read().decode("utf-8", "replace")
    try:
        than = json.loads(tho) if tho.strip() else None
    except ValueError:
        than = None
    return ma, than, tho


def doc_ket_qua(ma, than, tho):
    """→ (status, kết quả | None, mã lỗi, câu lỗi)."""
    if isinstance(than, dict) and than.get("Success") is False:
        m = str(than.get("Code") or ma)
        return "failed", None, "QLSX_%s" % m, str(than.get("Message") or "Bên kế toán từ chối (Code %s)." % m)
    if ma in (200, 201) and isinstance(than, dict) and isinstance(than.get("data"), dict):
        return "synced", than, None, None
    if ma == 409:
        return ("conflict", None, (than or {}).get("code") if isinstance(than, dict) else "LOGISTICS_52901",
                (than or {}).get("message") if isinstance(than, dict) else
                "Bên kế toán báo trùng DO / khoá (409) — hai bên đối soát, không tự gửi lại.")
    if isinstance(than, dict) and (than.get("code") or than.get("message")):
        return "failed", None, str(than.get("code") or "QLSX_%s" % ma), str(than.get("message") or "")
    # [Authorize] / Forbid() bên kia trả thân rỗng
    if ma == 401:
        return "failed", None, "QLSX_TOKEN_HET_HAN", ("Token hệ kế toán sai hoặc đã hết hạn (401) — xin token mới, đặt vào "
                                                      "QLSX_ACCESS_TOKEN trong .env rồi khởi động lại.")
    if ma == 403:
        return "failed", None, "QLSX_CHUA_CHO_PHEP", ("Bên kế toán chưa cho tài khoản của token gọi tạo SO (403): anh Tune thêm "
                                                      "UserId vào LogisticsSalesPush.AllowedUserIds, và tài khoản phải gắn nhân viên.")
    return "failed", None, "QLSX_HTTP_%s" % ma, "Bên kế toán trả HTTP %s: %s" % (ma, (tho or "")[:300])


def _chua_ro(b):
    """Lần trước kết quả chưa rõ → bắt buộc gửi lại đúng gói, đúng khoá."""
    return b is not None and b.request_body and b.status != "synced" and (
        b.http_status is None or b.http_status >= 500 or (b.error_code or "") in KET_QUA_CHUA_RO)


def xuat(b):
    if b is None:
        return None
    return {"do_id": b.do_id, "status": b.status, "da_tao_so": b.status == "synced", "replayed": bool(b.replayed),
            "http_status": b.http_status, "order_id": b.order_id, "order_code": b.order_code, "order_status": b.order_status,
            "retk_code": b.retk_code, "item_code": b.item_code, "currency": b.currency, "total_amount": b.total_amount,
            "initial_debt_amount": b.initial_debt_amount, "error_code": b.error_code, "error_message": b.error_message,
            "attempts": b.attempts, "pushed_by": b.pushed_by,
            "last_attempt_at": b.last_attempt_at.isoformat(timespec="minutes") if b.last_attempt_at else None,
            "synced_at": b.synced_at.isoformat(timespec="minutes") if b.synced_at else None}


def xem_truoc(db, p):
    """Gói SẼ gửi (không gọi mạng) + trạng thái lần gửi trước. Lỗi dữ liệu trả trong `loi`, không ném."""
    b = db.get(GuiSoTune, BG.ma_do(p))
    goc, token = cau_hinh()
    ra = {"do_id": BG.ma_do(p), "trang_thai": xuat(b), "co_token": bool(token), "may": urlsplit(goc).netloc}
    if b is not None and _chua_ro(b):
        body = json.loads(b.request_body)
        ra.update({"body": body, "gui_lai_goi_cu": True, "tom_tat": {"do_id": b.do_id, "customer_code": body["header"]["customer_id"],
                   "currency": body["header"]["currency"], "final_selling_price": body["header"]["final_selling_price"],
                   "route_id": body["header"]["route"]["id"]}})
        return ra
    try:
        body, tom = dung_goi(db, p)
        ra.update({"body": body, "tom_tat": tom, "gui_lai_goi_cu": False})
    except HTTPException as e:
        ra["loi"] = e.detail
    return ra


def gui(db, p, user):
    """Gửi một DO. Ghi lại kết quả (kể cả khi hỏng) rồi mới trả / ném, để lần sau biết gửi lại gói nào."""
    do_id = BG.ma_do(p)
    b = db.get(GuiSoTune, do_id)
    if b is not None and b.status == "synced":
        return xuat(b), True                                   # đã có SO: không gọi lại
    if b is not None and b.status == "conflict":
        _loi("DA_XUNG_DOT", "Lần gửi trước bên kế toán báo trùng DO (409) — hai bên đối soát trước, không gửi lại.", 409)
    if _chua_ro(b):
        body_json, key = b.request_body, b.idempotency_key
    else:
        body, _ = dung_goi(db, p)
        key = khoa(do_id)
        body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    if len(body_json.encode("utf-8")) > 1024 * 1024:
        _loi("GOI_QUA_LON", "Gói vượt 1 MiB — bên kế toán từ chối.", 413)
    goc, token = cau_hinh()
    if not token:
        _loi("CHUA_CO_TOKEN", "Chưa có token hệ kế toán (QLSX_ACCESS_TOKEN hoặc EPL_ACC_CODE_TOKEN trong .env).", 503)

    now = dt.datetime.utcnow()
    if b is None:
        b = GuiSoTune(do_id=do_id, trip_id=p.id, idempotency_key=key, request_body=body_json, attempts=0, first_attempt_at=now)
        db.add(b)
    b.idempotency_key, b.request_body = key, body_json
    b.attempts = (b.attempts or 0) + 1
    b.last_attempt_at, b.pushed_by = now, getattr(user, "full_name", None)
    try:
        ma, than, tho = goi(body_json, key, goc, token)
    except Exception as e:                                     # mất mạng, DNS, hết giờ — chưa rõ bên kia đã ghi chưa
        b.status, b.http_status, b.response_body = "failed", None, None
        b.error_code, b.error_message = "QLSX_KHONG_GOI_DUOC", "Không gọi được %s: %s" % (urlsplit(goc).netloc, e)
        db.commit()
        _loi("QLSX_KHONG_GOI_DUOC", "Không gọi được bên kế toán (%s): %s. Bấm lại sẽ gửi đúng gói, đúng khoá cũ."
             % (urlsplit(goc).netloc, e), 502)
    st, kq, ma_loi, loi = doc_ket_qua(ma, than, tho)
    b.status, b.http_status, b.response_body = st, ma, (tho or "")[:20000]
    b.error_code, b.error_message = ma_loi, loi
    if st == "synced":
        d = kq["data"]
        b.replayed = bool(kq.get("replayed"))
        b.order_id, b.order_code, b.order_status = _int(d.get("orderId")), _chu(d.get("orderCode"), 64), _chu(d.get("orderStatus"), 16)
        b.retk_auto_id, b.retk_code, b.item_code = _int(d.get("retkAutoId")), _chu(d.get("retkCode"), 64), _chu(d.get("itemCode"), 128)
        b.currency = _chu(d.get("currency"), 3) or json.loads(body_json)["header"]["currency"]
        b.total_amount, b.initial_debt_amount = _so(d.get("totalAmount")), _so(d.get("initialDebtAmount"))
        b.synced_at = now
    db.commit()
    if st != "synced":
        _loi(ma_loi or "BEN_KE_TOAN_TU_CHOI", "Bên kế toán chưa tạo SO cho %s: %s" % (p.doc_no, loi or ma_loi),
             409 if st == "conflict" else (502 if ma >= 500 else 422))
    return xuat(b), False


def cua_nhieu(db, trip_ids):
    """{trip_id: trạng thái gửi} cho danh sách."""
    if not trip_ids:
        return {}
    return {b.trip_id: xuat(b) for b in db.query(GuiSoTune).filter(GuiSoTune.trip_id.in_(list(trip_ids))).all()}


def _int(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _chu(v, dai):
    return str(v)[:dai] if v is not None else None


def _so(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None

