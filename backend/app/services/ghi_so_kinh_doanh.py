# -*- coding: utf-8 -*-
"""GHI SỔ KINH DOANH: đẩy một DO đã giao sang QLSX (hệ công nợ của anh Khang) để tạo đơn hàng bán.

Hợp đồng: `docs/logistics-sales-orders-api-guide.md` — POST
`/api/v1/integrations/logistics/sales-orders`, body đúng BA khoá gốc `schemaVersion / header /
details`, header + details lấy từ chính gói bàn giao (`dong_goi_ban_giao`).

NHỮNG ĐIỀU TÀI LIỆU ĐÒI MÀ CODE NÀY PHẢI GIỮ, không phải chi tiết trình bày:

* Token QLSX nằm ở BACKEND (biến môi trường), không bao giờ xuống trình duyệt. Vì vậy nút
  trên màn hình gọi API của mình, và mình mới gọi sang QLSX.
* Idempotency-Key ỔN ĐỊNH theo DO, và lần gửi lại phải dùng CÙNG key + CÙNG body. Tài liệu nói
  thẳng: timeout không chứng minh thất bại, DB bên đó có thể đã commit. Nên body đã gửi được
  LƯU LẠI và lần sau dùng lại nguyên văn — dựng body mới có thể đổi hash (thứ tự dòng, số
  thực) và ăn 409.
* Tiền là JSON number, tổng phải khớp CHÍNH XÁC, không dung sai: `selling_price +
  customer_surcharge_total = final_selling_price` và `SUM(thu) = final_selling_price`. Kiểm
  bằng Decimal trước khi gửi — để lỗi dữ liệu nổ ở đây với lời rõ ràng, thay vì một 400 từ xa.
* Chỉ VND / LAK / USD. Bộ dữ liệu có báo giá THB: chặn tại đây, nói thẳng lý do.
* Chỉ `synced` khi nhận 201 (tạo mới) hoặc 200 `replayed: true` kèm `data` hợp lệ.

ĐO ĐƯỢC TRÊN MÁY CHỦ THẬT (11/09): gọi không token, QLSX trả **HTTP 200** với thân
`{"Success": false, "Code": 401, "Message": "Chưa đăng nhập..."}`. Tức lớp xác thực bên đó bọc
lỗi trong một phong bì 200. Nên đọc mã HTTP một mình là KHÔNG ĐỦ — phải nhìn cả `Success` trong
thân. Phản hồi thành công theo hợp đồng có dạng `{replayed, data}` và không có khoá `Success`.
"""
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from models import DeliveryOrder, SalesOrderPush
from services.errors import DomainError, conflict

TIEN_QLSX_NHAN = ("VND", "LAK", "USD")
GOC_MAC_DINH = "https://demo-lao-api.goldensme.com"
DUONG_TAO_SO = "/api/v1/integrations/logistics/sales-orders"
THOI_GIAN_CHO = 60
#: Mã DO / khách / tuyến chỉ gồm ASCII chữ số `_ - .`, bắt đầu bằng chữ hoặc số.
MA_HOP_LE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
#: Idempotency-Key: 1–100 ký tự, bắt đầu chữ/số, còn lại chữ/số `_ . : -`.
KEY_HOP_LE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,99}$")
GIOI_HAN_TIEN = Decimal("9999999999999")


def _now():
    return dt.datetime.now(dt.timezone.utc)


def cau_hinh():
    """Gốc và token QLSX từ môi trường. Thiếu token thì nói ra ngay, không gọi mò."""
    goc = (os.getenv("QLSX_BASE_URL") or GOC_MAC_DINH).strip().rstrip("/")
    token = (os.getenv("QLSX_ACCESS_TOKEN") or "").strip()
    return goc, token


def idempotency_key(do_id):
    """Key ổn định theo DO: cùng DO luôn cùng key, đúng như hợp đồng đòi."""
    key = "logistics:%s" % do_id
    if not KEY_HOP_LE.match(key):
        raise DomainError("GHI_SO_KEY_INVALID",
                          "Mã DO %s không dựng được Idempotency-Key hợp lệ cho QLSX." % do_id, 422)
    return key


# ------------------------------------------------------------------ dựng & kiểm body
def _tien(gia_tri, ten):
    """Đọc một số tiền thành Decimal, tối đa 5 chữ số lẻ, trong khoảng validator QLSX chấp nhận."""
    if gia_tri is None:
        raise DomainError("GHI_SO_THIEU_TIEN", "Thiếu %s trong hồ sơ bàn giao." % ten, 422)
    try:
        d = Decimal(str(gia_tri))
    except InvalidOperation:
        raise DomainError("GHI_SO_TIEN_KHONG_HOP_LE", "%s không phải số: %r." % (ten, gia_tri), 422)
    if d != d or d in (Decimal("Infinity"), Decimal("-Infinity")):
        raise DomainError("GHI_SO_TIEN_KHONG_HOP_LE", "%s không phải số hữu hạn." % ten, 422)
    d = d.quantize(Decimal("0.00001"))
    if d < 0 or d > GIOI_HAN_TIEN:
        raise DomainError("GHI_SO_TIEN_NGOAI_KHOANG",
                          "%s = %s nằm ngoài khoảng QLSX chấp nhận (0 … 9.999.999.999.999)." % (ten, d), 422)
    return d


def _so_json(d):
    """Decimal → số JSON gọn (không đuôi .00000), giữ nguyên phần lẻ có nghĩa."""
    d = d.normalize()
    return int(d) if d == d.to_integral_value() else float(d)


def dung_body(goi_ban_giao):
    """Từ gói bàn giao `{header, details}` dựng body gửi QLSX, KIỂM đủ luật trước khi trả.

    Trả `(body, tom_tat)`; ném DomainError 422 với lời cụ thể khi vi phạm. Mọi số tiền được
    chuẩn hoá qua Decimal rồi mới đưa vào body, để phép cộng bên QLSX khớp chính xác.
    """
    h = dict(goi_ban_giao.get("header") or {})
    ds = [dict(x) for x in (goi_ban_giao.get("details") or [])]
    do_id = str(h.get("do_id") or "")
    if not do_id or len(do_id) > 100 or not MA_HOP_LE.match(do_id):
        raise DomainError("GHI_SO_MA_DO_INVALID", "Mã DO %r không hợp lệ theo QLSX." % do_id, 422)
    if str(h.get("status") or "").lower() != "delivered":
        raise conflict("GHI_SO_DO_CHUA_GIAO",
                       "Chỉ ghi sổ được DO đã giao (delivered); %s đang là %s." % (do_id, h.get("status")))
    khach = str(h.get("customer_id") or "")
    if not khach or len(khach) > 50 or not MA_HOP_LE.match(khach):
        raise DomainError("GHI_SO_MA_KHACH_INVALID",
                          "Mã khách %r không hợp lệ theo QLSX (ASCII, ≤50 ký tự)." % khach, 422)
    tuyen = dict(h.get("route") or {})
    ma_tuyen = str(tuyen.get("id") or "")
    if not ma_tuyen or len(ma_tuyen) > 50 or not MA_HOP_LE.match(ma_tuyen):
        raise DomainError("GHI_SO_MA_TUYEN_INVALID", "Mã tuyến %r không hợp lệ theo QLSX." % ma_tuyen, 422)
    if len(khach) + 1 + len(ma_tuyen) > 50:
        raise DomainError("GHI_SO_MA_GHEP_QUA_DAI",
                          "Mã mặt hàng gộp %s_%s dài %d ký tự, QLSX chỉ nhận tới 50."
                          % (khach, ma_tuyen, len(khach) + 1 + len(ma_tuyen)), 422)

    tien = str(h.get("currency") or "").upper()
    tien_thu = str(h.get("currency_thu") or tien).upper()
    if tien not in TIEN_QLSX_NHAN:
        raise DomainError("GHI_SO_TIEN_TE_CHUA_HO_TRO",
                          "QLSX chỉ nhận VND, LAK, USD — báo giá của %s bằng %s. Cần thống nhất với bên "
                          "công nợ cách ghi nhận đơn %s trước khi ghi sổ." % (do_id, tien or "?", tien or "?"),
                          422)
    if tien_thu != tien:
        raise DomainError("GHI_SO_TIEN_THU_LECH",
                          "currency_thu (%s) phải bằng currency (%s)." % (tien_thu, tien), 422)

    gia_ban = _tien(h.get("selling_price"), "selling_price")
    phu_thu = _tien(h.get("customer_surcharge_total") if h.get("customer_surcharge_total") is not None else 0,
                    "customer_surcharge_total")
    gia_cuoi = _tien(h.get("final_selling_price"), "final_selling_price")
    if gia_cuoi <= Decimal("0.01"):
        raise DomainError("GHI_SO_TONG_BAN_KHONG_DUONG",
                          "Tổng bán của %s là %s — QLSX đòi lớn hơn 0.01." % (do_id, gia_cuoi), 422)
    if gia_ban + phu_thu != gia_cuoi:
        raise DomainError("GHI_SO_TONG_KHONG_KHOP",
                          "selling_price + customer_surcharge_total = %s + %s = %s ≠ final_selling_price %s."
                          % (gia_ban, phu_thu, gia_ban + phu_thu, gia_cuoi), 422)

    if not ds:
        raise DomainError("GHI_SO_THIEU_DONG", "Hồ sơ %s không có dòng thu/chi nào." % do_id, 422)
    tong_thu = Decimal(0)
    so_dong = set()
    dong_gui = []
    for x in ds:
        n = x.get("line_no")
        if not isinstance(n, int) or n <= 0 or n in so_dong:
            raise DomainError("GHI_SO_LINE_NO_INVALID", "line_no %r trùng hoặc không phải số nguyên dương." % n, 422)
        so_dong.add(n)
        loai = str(x.get("kind") or "").lower()
        if loai not in ("thu", "chi"):
            raise DomainError("GHI_SO_KIND_INVALID", "Dòng %s có kind %r, chỉ nhận thu/chi." % (n, x.get("kind")), 422)
        so = _tien(x.get("actual_amount") if x.get("actual_amount") is not None else 0,
                   "actual_amount dòng %s" % n)
        tien_dong = str(x.get("currency") or ("" if loai == "chi" else tien)).upper()
        if loai == "thu":
            if tien_dong != tien:
                raise DomainError("GHI_SO_DONG_THU_LECH_TIEN",
                                  "Dòng thu %s ghi bằng %s trong khi cước bằng %s — QLSX không nhận thu trộn tiền."
                                  % (n, tien_dong, tien), 422)
            tong_thu += so
        x["kind"] = loai
        x["actual_amount"] = _so_json(so)
        if tien_dong:
            x["currency"] = tien_dong
        for k in ("planned_amount", "customer_extra", "variance"):
            if x.get(k) is not None:
                try:
                    x[k] = _so_json(_tien(x[k], "%s dòng %s" % (k, n)))
                except DomainError:
                    x[k] = None
        dong_gui.append(x)
    if tong_thu != gia_cuoi:
        raise DomainError("GHI_SO_TONG_THU_KHONG_KHOP",
                          "Tổng các dòng thu = %s ≠ final_selling_price %s. Hồ sơ này chưa ghi sổ được."
                          % (tong_thu, gia_cuoi), 422)

    h["status"] = "delivered"
    h["currency"], h["currency_thu"] = tien, tien
    h["selling_price"] = _so_json(gia_ban)
    h["customer_surcharge_total"] = _so_json(phu_thu)
    h["final_selling_price"] = _so_json(gia_cuoi)
    # `ledger_totals` là object tổng nội bộ, không thuộc hợp đồng — bỏ để khỏi thử vận may với
    # validator bên đó. Mọi trường phẳng khác giữ nguyên: tài liệu bảo "nên gửi nếu có".
    h.pop("ledger_totals", None)
    body = {"schemaVersion": 1, "header": h, "details": dong_gui}
    tom_tat = {"do_id": do_id, "customer_id": khach, "route_id": ma_tuyen, "currency": tien,
               "final_selling_price": _so_json(gia_cuoi), "so_dong": len(dong_gui),
               "so_dong_thu": sum(1 for x in dong_gui if x["kind"] == "thu")}
    return body, tom_tat


# ------------------------------------------------------------------ gọi QLSX
def goi_qlsx(body_json, key, goc=None, token=None):
    """POST sang QLSX. Trả `(http_status, than_dict_hoac_None, than_tho)`. Không ném vì lỗi HTTP."""
    goc = goc or cau_hinh()[0]
    yeu_cau = urllib.request.Request(
        goc + DUONG_TAO_SO, data=body_json.encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + (token or ""), "Content-Type": "application/json",
                 "Accept": "application/json", "Idempotency-Key": key,
                 "User-Agent": "EPL-Logistics-TMS/1.0 (ghi so kinh doanh)"})
    try:
        with urllib.request.urlopen(yeu_cau, timeout=THOI_GIAN_CHO) as tra:
            ma, tho = tra.status, tra.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as loi:
        ma, tho = loi.code, loi.read().decode("utf-8", "replace")
    try:
        than = json.loads(tho) if tho.strip() else None
    except ValueError:
        than = None
    return ma, than, tho


def doc_ket_qua(ma, than, tho):
    """Phân loại phản hồi QLSX → `(status, ket_qua|None, error_code, error_message)`.

    * 201 hoặc 200 với `data` → synced (200 kèm `replayed: true` là gửi lại đúng yêu cầu cũ).
    * Thân có `Success: false` → lỗi theo `Code`/`Message` bên đó, DÙ mã HTTP là 200.
    * 409 → conflict, không tự gửi lại.
    * Còn lại → failed, kèm code/message nếu có, không thì ghi mã HTTP và 300 ký tự đầu.
    """
    if isinstance(than, dict) and than.get("Success") is False:
        ma_loi = str(than.get("Code") or ma)
        return ("failed", None, "QLSX_%s" % ma_loi,
                str(than.get("Message") or "QLSX từ chối (Code %s)." % ma_loi))
    if ma in (200, 201) and isinstance(than, dict) and isinstance(than.get("data"), dict):
        return "synced", than, None, None
    if ma == 409:
        code = (than or {}).get("code") if isinstance(than, dict) else None
        return ("conflict", None, code or "LOGISTICS_52901",
                (than or {}).get("message") if isinstance(than, dict) else
                "QLSX báo trùng DO/key (409) — cần đối soát với bên công nợ, không tự gửi lại.")
    if isinstance(than, dict) and (than.get("code") or than.get("message")):
        return "failed", None, str(than.get("code") or "QLSX_%s" % ma), str(than.get("message") or "")
    return "failed", None, "QLSX_HTTP_%s" % ma, "QLSX trả HTTP %s: %s" % (ma, (tho or "")[:300])


# ------------------------------------------------------------------ luồng chính
def ghi_so(db, do_id, goi_ban_giao, actor, xem_truoc=False):
    """Ghi sổ kinh doanh cho một DO. Trả dict kết quả cho màn hình.

    `xem_truoc=True`: chỉ dựng và kiểm body, KHÔNG gửi — để người dùng (và anh Khang) nhìn
    đúng thứ sẽ đi trước khi bấm thật.
    """
    ban_ghi = db.get(SalesOrderPush, do_id)
    if ban_ghi is not None and ban_ghi.status == "synced" and not xem_truoc:
        # Đã ghi sổ rồi: trả lại kết quả cũ, không gọi QLSX nữa. Bên đó cũng không có API
        # update — gửi lại chỉ để nhận 200 replayed, tốn một vòng mạng vô ích.
        return tom_tat_ban_ghi(ban_ghi, da_co=True)

    # BODY: nếu đã từng gửi thì DÙNG LẠI NGUYÊN VĂN (cùng key, cùng body); chưa thì dựng mới.
    if ban_ghi is not None and ban_ghi.request_body and not xem_truoc:
        body_json, key = ban_ghi.request_body, ban_ghi.idempotency_key
        body = json.loads(body_json)
        _, tom_tat = dung_body({"header": body["header"], "details": body["details"]})
    else:
        body, tom_tat = dung_body(goi_ban_giao)
        key = idempotency_key(do_id)
        body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    if len(body_json.encode("utf-8")) > 1024 * 1024:
        raise DomainError("GHI_SO_BODY_QUA_LON", "Body vượt 1 MiB — QLSX từ chối.", 413)

    if xem_truoc:
        return {"do_id": do_id, "xem_truoc": True, "idempotency_key": key, "tom_tat": tom_tat,
                "body": body, "da_ghi_so": bool(ban_ghi and ban_ghi.status == "synced"),
                "trang_thai_truoc": ban_ghi.status if ban_ghi else None}

    goc, token = cau_hinh()
    if not token:
        raise DomainError("QLSX_TOKEN_CHUA_CAU_HINH",
                          "Chưa cấu hình QLSX_ACCESS_TOKEN cho máy chủ EPL. Token do đội QLSX cấp; đặt vào .env "
                          "rồi khởi động lại — token không được nhúng vào trình duyệt.", 503,
                          ["settings"])

    bay_gio = _now()
    if ban_ghi is None:
        ban_ghi = SalesOrderPush(do_id=do_id, idempotency_key=key, request_body=body_json,
                                 attempts=0, first_attempt_at=bay_gio)
        db.add(ban_ghi)
    ban_ghi.attempts = (ban_ghi.attempts or 0) + 1
    ban_ghi.last_attempt_at = bay_gio
    ban_ghi.pushed_by = actor

    try:
        ma, than, tho = goi_qlsx(body_json, key, goc, token)
    except Exception as loi:                          # mất mạng, DNS, hết giờ
        ban_ghi.status, ban_ghi.http_status = "failed", None
        ban_ghi.error_code, ban_ghi.error_message = "QLSX_KHONG_GOI_DUOC", "Không gọi được %s: %s" % (goc, loi)
        ban_ghi.response_body = None
        db.flush()
        raise DomainError("QLSX_KHONG_GOI_DUOC",
                          "Không gọi được QLSX (%s): %s. Hồ sơ chưa được ghi sổ; bấm lại sẽ gửi cùng key "
                          "và body." % (goc, loi), 502)

    trang_thai, ket_qua, ma_loi, loi_chu = doc_ket_qua(ma, than, tho)
    ban_ghi.status, ban_ghi.http_status, ban_ghi.response_body = trang_thai, ma, (tho or "")[:20000]
    ban_ghi.error_code, ban_ghi.error_message = ma_loi, loi_chu
    if trang_thai == "synced":
        d = ket_qua["data"]
        ban_ghi.replayed = bool(ket_qua.get("replayed"))
        ban_ghi.order_id = _int(d.get("orderId"))
        ban_ghi.order_code = _chuoi(d.get("orderCode"), 64)
        ban_ghi.order_status = _chuoi(d.get("orderStatus"), 16)
        ban_ghi.retk_auto_id = _int(d.get("retkAutoId"))
        ban_ghi.retk_code = _chuoi(d.get("retkCode"), 64)
        ban_ghi.item_code = _chuoi(d.get("itemCode"), 128)
        ban_ghi.currency = _chuoi(d.get("currency"), 3) or tom_tat["currency"]
        ban_ghi.total_amount = _decimal(d.get("totalAmount"))
        ban_ghi.initial_debt_amount = _decimal(d.get("initialDebtAmount"))
        ban_ghi.synced_at = bay_gio
    db.flush()
    if trang_thai != "synced":
        ma_http = 409 if trang_thai == "conflict" else (502 if ma >= 500 else 422)
        raise DomainError(ma_loi or "QLSX_TU_CHOI",
                          "QLSX chưa ghi sổ %s: %s" % (do_id, loi_chu or ma_loi), ma_http)
    return tom_tat_ban_ghi(ban_ghi, da_co=False)


def tom_tat_ban_ghi(b, da_co=False):
    """Bản ghi → dict cho màn hình. Chỉ có ở đây một chỗ, để hai đường trả (mới/cũ) không lệch."""
    if b is None:
        return None
    return {
        "do_id": b.do_id, "status": b.status, "da_ghi_so": b.status == "synced", "da_co_truoc": da_co,
        "replayed": bool(b.replayed), "idempotency_key": b.idempotency_key, "http_status": b.http_status,
        "order_id": b.order_id, "order_code": b.order_code, "order_status": b.order_status,
        "retk_auto_id": b.retk_auto_id, "retk_code": b.retk_code, "item_code": b.item_code,
        "currency": b.currency,
        "total_amount": float(b.total_amount) if b.total_amount is not None else None,
        "initial_debt_amount": float(b.initial_debt_amount) if b.initial_debt_amount is not None else None,
        "error_code": b.error_code, "error_message": b.error_message,
        "attempts": b.attempts, "pushed_by": b.pushed_by,
        "first_attempt_at": b.first_attempt_at.isoformat() if b.first_attempt_at else None,
        "last_attempt_at": b.last_attempt_at.isoformat() if b.last_attempt_at else None,
        "synced_at": b.synced_at.isoformat() if b.synced_at else None,
    }


def _int(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _chuoi(v, dai):
    return str(v)[:dai] if v is not None else None


def _decimal(v):
    try:
        return Decimal(str(v)) if v is not None else None
    except InvalidOperation:
        return None
