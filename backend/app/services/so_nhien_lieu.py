# -*- coding: utf-8 -*-
"""SO "NHIÊN LIỆU" CHO ĐỐI TÁC (xe thuê) ở hệ kế toán anh Tune — chủ dự án chốt 02/10/2026.

Xe thuê lấy dầu (mục III) / phụ tùng (mục V) ở KHO EPL = xuất bán cho đối tác (chủ xe). Trước đây phần bán là bút toán chờ
Nợ 4022 / Có 707; nay phần bán thành MỘT SO bên anh Tune, khách của SO = đối tác (đối tượng EPLCX-<owner_id>), treo công nợ như
SO cước. Giá vốn 607 / 1371 vẫn là bút toán `xuat_ban` (services/but_toan_cho.dong_xuat_kho). Khi trả đối tác, máy tự CẤN TRỪ
phần SO còn nợ vào tiền trả (services/tra_chu_xe.py · chi_tune.de_nghi_tra_chu_xe). 06/10: doanh thu của SO này (Nợ 1211 / Có 707,
đối tượng đối tác) là bút toán chờ `doanh_thu_ban` ghi cùng nút «Tạo SO» (but_toan_cho.ghi_doanh_thu); cùng đường cấn trừ dùng cho
SO bán hàng đối tác mua ở quầy (tra_chu_xe.so_quay — goi_can_tru theo tiền của SO).

    POST {goc}/api/v1/integrations/logistics/fuel-sales-orders       tạo (Idempotency-Key logistics-fuel:EPLLAO-<Trip.id>)
    GET  {goc}/api/v1/integrations/logistics/fuel-sales-orders/{do}  đọc lại (kèm dư nợ hiện tại)

Khuôn bên đó (GLS-QLSX-APIs LogisticsFuelSalesOrderService + sp_Logistics_CreateFuelSalesOrder, 02/10): ba khoá gốc
schemaVersion / header / details; header do_id, partner_code (PUBOBJECT phải có sẵn — chưa có → 52955, nên bên em tạo đối tượng
chủ xe trước, như phiếu chi trả chủ xe), currency, total; mỗi dòng item_name ≤ 100, item_key / item_code (mã hàng EPLNL-<item_key>
· phụ tùng EPLPT-<…>), qty > 0, unit_price ≥ 0, amount > 0, cùng một tiền; Σ amount = total ĐÚNG TỪNG CHỮ SỐ. Envelope {Success,
Code, Message, Result, ErrorDetail.ErrorCode}: 201 tạo · 200 replayed · 409 52951 khác nội dung (đối soát) / 52953 bận (gửi lại
cùng khoá) · 422 52955 đối tác chưa có… Cùng luật GuiSoTune (services/gui_tune.py): kết quả CHƯA RÕ thì gửi lại đúng gói, đúng khoá.

Gửi cùng nút «Tạo SO bên kế toán» (POST /api/trips/{tid}/tao-so) sau SO cước. Tiền: Kíp — giá bán theo tiền của dòng quy Kíp
theo tỷ giá khoá trên phiếu (dòng kho luôn LAK).

05/10 (chủ dự án hỏi "anh chưa thấy xuất bán"): mỗi dòng details gửi kèm trường TUỲ CHỌN `stock_doc_no` = số phiếu xuất kho QLSX của
dòng chi (stock_move_id "qlsx:<số phiếu kho>" — dầu cấp theo phiếu đề nghị / phụ tùng xuất theo chuyến, DOTY 48 PARTNER_SALE). Bên kế
toán lưu nguyên gói tạo SO nên chi tiết SO nhiên liệu hiện đúng các phiếu xuất kho đã xuất bán cho SO. Bên đó (bản cũ lẫn mới) bỏ qua
khoá lạ ở dòng → không đổi luồng; gói đã gửi trước đó (gửi lại khi kết quả chưa rõ) giữ nguyên, không thêm trường.
"""
import datetime as dt
import json
import re
import urllib.error
import urllib.request
from decimal import Decimal
from urllib.parse import quote, urlsplit

from fastapi import HTTPException

from models import GuiSoNhienLieuTune, Owner, Part, Route, TripExpense
from services import gui_tune as GT
from services.tinh_toan import la_xuat_ban, lam_tron, ty_gia

DUONG = "/api/v1/integrations/logistics/fuel-sales-orders"
TIEN = "LAK"
# ĐVT bên kế toán tra theo TÊN (sp: không có thì Cái) — đơn vị phụ tùng bên em là khoá dịch
DVT = {"u_pc": "Cái", "u_set": "Bộ", "u_l": "Lít"}
KET_QUA_CHUA_RO = ("QLSX_KHONG_GOI_DUOC", "LOGISTICS_FUEL_52953")
MUC = {"fuel": "III", "repair": "V"}
# TripExpense.stock_move_id của dòng đã rời kho QLSX (cùng tiền tố services/kho_qlsx.TIEN_TO_MV, ban_giao_dau.TIEN_TO_MV)
TIEN_TO_KHO = "qlsx:"
# Số phiếu kho QLSX (DOC_DOCUMENTNO ≤ 50), ví dụ 1368-XKK-261005-00002 — cùng luật kiểm stock_doc_no bên kế toán
SO_PHIEU_KHO = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_./-]{0,49}\Z")


def _loi(ma, loi, http=422, **them):
    raise HTTPException(http, dict({"ma": ma, "loi": loi}, **them))


def ma_do(p):
    return "EPLLAO-" + p.id


def khoa(do_id):
    k = "logistics-fuel:%s" % do_id
    if not GT.KEY_HOP_LE.match(k):
        _loi("KEY_SAI", "Mã DO %s không dựng được Idempotency-Key hợp lệ." % do_id)
    return k


def ma_doi_tac(p):
    """Mã đối tượng đối tác bên kế toán — cùng mã phiếu chi trả chủ xe tạo (chi_tune.LOAI_DOI_TUONG chu_xe)."""
    from services.chi_tune import LOAI_DOI_TUONG
    return LOAI_DOI_TUONG["chu_xe"][1] + (p.owner_id or "")


def _dong_phieu(db, p):
    return (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())


def dong_ban(p, dong):
    """Dòng XUẤT BÁN cho đối tác của phiếu: xe thuê, dầu / phụ tùng lấy kho EPL (tinh_toan.la_xuat_ban), ĐÃ RỜI KHO (dầu đã cấp
    theo phiếu đề nghị, phụ tùng đã xuất — stock_move_id), EPL ứng, số lượng > 0. Cùng tập dòng bút toán giá vốn xuat_ban."""
    return [d for d in dong if la_xuat_ban(p, d) and d.stock_move_id and d.paid_by_epl is not False and (d.qty or 0) > 0]


def can_so(db, p, dong=None):
    """Phiếu này có phần SO nhiên liệu phải gửi không (xe thuê có dòng xuất bán)."""
    return p.company == "joint" and bool(dong_ban(p, dong if dong is not None else _dong_phieu(db, p)))


def so_cua(db, p):
    return db.get(GuiSoNhienLieuTune, ma_do(p))


def tien_dong(p, d):
    """(đơn giá bán Kíp, thành tiền Kíp) của một dòng xuất bán — đúng số trừ vào tiền trả đối tác trước đây (tinh_toan.tien_dong)."""
    r = Decimal(str(ty_gia(p, d.currency)))
    dg = (Decimal(str(d.sale_price)) * r).quantize(Decimal("0.01")).normalize()
    return dg, Decimal(lam_tron(float(Decimal(str(d.qty or 0)) * dg), TIEN))


def so_phieu_kho(d):
    """Số phiếu xuất kho QLSX của dòng chi (stock_move_id "qlsx:<số phiếu>") → gửi kèm dòng SO (stock_doc_no). Dòng không đi kho
    QLSX hoặc số phiếu không đúng dạng → None (không gửi trường; SO vẫn tạo, dòng đó hiện "chưa có liên kết")."""
    mv = (d.stock_move_id or "").strip()
    if not mv.startswith(TIEN_TO_KHO):
        return None
    so = mv[len(TIEN_TO_KHO):].strip()
    return so if SO_PHIEU_KHO.match(so) else None


def _ten_dong(db, d):
    """(mã khoá dòng gửi bên kế toán, tên mặt hàng, ĐVT): dầu theo khoản mục (diesel → mã EPLNL-diesel), phụ tùng theo mã phụ
    tùng bên em (EPLPT-<Part.id>)."""
    from services.ban_giao import _ten
    ten = (_ten(db, d)[0] or ("Dầu" if d.section == "fuel" else "Phụ tùng"))[:100]
    if d.section == "fuel":
        return {"item_key": d.item_key or "diesel"}, ten, "Lít"
    pt = db.get(Part, d.part_id) if d.part_id else None
    return ({"item_code": "EPLPT-%s" % d.part_id} if d.part_id else {"item_key": d.item_key or "phu_tung"}), ten, \
        DVT.get(getattr(pt, "unit", None) or "", "Cái")


def dung_goi(db, p, dong=None):
    """Gói SO nhiên liệu của phiếu `p` → (body, tóm tắt). Chưa đủ điều kiện thì HTTPException nói rõ phải làm gì."""
    from services import ban_giao as BG
    if not BG.ban_giao_duoc(p):
        _loi("DO_CHUA_KHOA", "Phiếu %s chưa về hoặc chưa khoá — DO xong mới tạo SO nhiên liệu." % p.doc_no, 409)
    if p.company != "joint" or not p.owner_id:
        _loi("KHONG_PHAI_XE_THUE", "Phiếu %s không phải xe thuê có đối tác — không có SO nhiên liệu." % p.doc_no, 409)
    ds = dong_ban(p, dong if dong is not None else _dong_phieu(db, p))
    if not ds:
        _loi("KHONG_CO_XUAT_BAN", "Phiếu %s không có dòng dầu / phụ tùng kho EPL xuất bán cho đối tác." % p.doc_no, 409)
    thieu = [d for d in ds if not (d.sale_price or 0) > 0]
    if thieu:
        _loi("THIEU_GIA_BAN", "Phiếu %s: %d dòng xuất bán chưa có giá bán — KT kho xăng dầu (mục III) / KT Chi phí (mục V) gõ giá bán."
             % (p.doc_no, len(thieu)), 409)
    o = db.get(Owner, p.owner_id)
    ten_dt = (p.owner_name or (o.name if o else "") or "").strip()
    details, tong = [], Decimal(0)
    for i, d in enumerate(ds, 1):
        dg, tt = tien_dong(p, d)
        if tt <= 0:
            _loi("THANH_TIEN_KHONG", "Phiếu %s: dòng xuất bán %s thành tiền 0." % (p.doc_no, d.id), 409)
        ma, ten, dvt = _ten_dong(db, d)
        x = {"line_no": i, "ref": d.id, **ma, "item_name": ten, "section": MUC.get(d.section, d.section), "qty": GT._so_json(GT._tien(d.qty, "qty")),
             "unit": dvt, "unit_price": GT._so_json(GT._tien(dg, "unit_price")), "amount": GT._so_json(GT._tien(tt, "amount")), "currency": TIEN}
        so_kho = so_phieu_kho(d)                                # 05/10: liên kết dòng SO ↔ phiếu xuất kho đã xuất bán
        if so_kho:
            x["stock_doc_no"] = so_kho
        details.append(x)
        tong += tt
    tuyen = db.get(Route, p.route_id) if p.route_id else None
    header = {"do_id": ma_do(p), "doc_no": p.doc_no, "partner_code": ma_doi_tac(p), "partner_name": ten_dt[:100] or None,
              "doc_date": (p.doc_date or dt.date.today()).isoformat(), "currency": TIEN,
              "route": {"id": tuyen.id, "name": tuyen.name} if tuyen else None, "total": GT._so_json(GT._tien(tong, "total"))}
    header = {k: v for k, v in header.items() if v is not None}
    tom = {"do_id": ma_do(p), "doc_no": p.doc_no, "partner_code": header["partner_code"], "partner_name": ten_dt, "currency": TIEN,
           "total": header["total"], "so_dong": len(details)}
    return {"schemaVersion": 1, "header": header, "details": details}, tom


def _chua_ro(b):
    """Lần trước kết quả chưa rõ (mất mạng, hết giờ, 5xx, bên đó bận) → bắt buộc gửi lại đúng gói, đúng khoá."""
    return b is not None and b.request_body and b.status != "synced" and (
        b.http_status is None or b.http_status >= 500 or (b.error_code or "") in KET_QUA_CHUA_RO)


def _goi(method, duong, body_json=None, key=None):
    """→ (http, thân dict | None, thân thô). Lỗi HTTP không ném; mất mạng ném ra ngoài."""
    goc, token = GT.cau_hinh()
    if not token:
        _loi("CHUA_CO_TOKEN", "Chưa có token hệ kế toán (QLSX_ACCESS_TOKEN / tài khoản tích hợp trong .env).", 503)
    dau = {"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "EPL-LAO-Logistics/1.0 (so nhien lieu)"}
    if body_json is not None:
        dau["Content-Type"] = "application/json"
    if key:
        dau["Idempotency-Key"] = key
    yc = urllib.request.Request(goc + duong, data=body_json.encode("utf-8") if body_json is not None else None, method=method, headers=dau)
    try:
        with urllib.request.urlopen(yc, timeout=GT.CHO_GIAY) as t:
            ma, tho = t.status, t.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        ma, tho = e.code, e.read().decode("utf-8", "replace")
    try:
        than = json.loads(tho) if tho.strip() else None
    except ValueError:
        than = None
    if ma == 401:
        GT.quen_token()
    return ma, than, tho


def doc_ket_qua(ma, than, tho):
    """→ (status, Result | None, mã lỗi, câu lỗi). 52951 = DO / khoá đã có SO khác nội dung → conflict (đối soát, không gửi lại);
    52953 = bên đó bận → failed nhưng CHƯA RÕ (gửi lại đúng gói)."""
    if isinstance(than, dict) and than.get("Success") is True and isinstance(than.get("Result"), dict) and than["Result"].get("orderCode"):
        return "synced", than["Result"], None, None
    ma_loi = None
    if isinstance(than, dict):
        ma_loi = ((than.get("ErrorDetail") or {}).get("ErrorCode") if isinstance(than.get("ErrorDetail"), dict) else None) \
            or (str(than.get("Code")) if than.get("Code") not in (None, "") else None)
    cau = (than or {}).get("Message") if isinstance(than, dict) else (tho or "")[:300]
    if ma_loi == "LOGISTICS_FUEL_52951" or (ma == 409 and not ma_loi):
        return "conflict", None, ma_loi or "LOGISTICS_FUEL_52951", cau or "Bên kế toán báo DO đã có SO nhiên liệu khác nội dung (409)."
    if ma == 401:
        return "failed", None, "QLSX_TOKEN_HET_HAN", "Token hệ kế toán sai hoặc đã hết hạn (401)."
    if ma == 403:
        return "failed", None, ma_loi or "LOGISTICS_FUEL_FORBIDDEN", cau or ("Bên kế toán chưa cho tài khoản tích hợp gọi SO nhiên "
                                                                            "liệu (403: LogisticsSalesPush.AllowedUserIds).")
    return "failed", None, ma_loi or "QLSX_HTTP_%s" % ma, cau or "Bên kế toán trả HTTP %s." % ma


def xuat(b):
    if b is None:
        return None
    return {"do_id": b.do_id, "status": b.status, "da_tao_so": b.status == "synced", "replayed": bool(b.replayed),
            "http_status": b.http_status, "order_id": b.order_id, "order_code": b.order_code, "retk_code": b.retk_code,
            "partner_code": b.partner_code, "currency": b.currency, "total_amount": b.total_amount, "error_code": b.error_code,
            "error_message": b.error_message, "attempts": b.attempts, "pushed_by": b.pushed_by,
            "last_attempt_at": b.last_attempt_at.isoformat(timespec="minutes") if b.last_attempt_at else None,
            "synced_at": b.synced_at.isoformat(timespec="minutes") if b.synced_at else None,
            "thu": {"trang_thai": b.thu_trang_thai, "tong": b.thu_tong, "da_thu": b.thu_da_thu, "con_no": b.thu_con_no,
                    "doc_luc": b.thu_doc_luc.isoformat(timespec="minutes") + "+00:00" if b.thu_doc_luc else None,
                    "loi": b.thu_loi} if b.status == "synced" else None}


def xem_truoc(db, p):
    """Phần SO nhiên liệu của màn «Tạo SO bên kế toán»: có phải gửi không, gói SẼ gửi, lần gửi trước. Không gọi mạng."""
    can = can_so(db, p)
    b = so_cua(db, p)
    ra = {"can": can, "do_id": ma_do(p), "trang_thai": xuat(b)}
    if not can and b is None:
        return ra
    if b is not None and _chua_ro(b):
        ra.update({"body": json.loads(b.request_body), "gui_lai_goi_cu": True})
        return ra
    try:
        body, tom = dung_goi(db, p)
        ra.update({"body": body, "tom_tat": tom, "gui_lai_goi_cu": False})
    except HTTPException as e:
        ra["loi"] = e.detail
    return ra


def gui(db, p, user):
    """Gửi SO nhiên liệu của một DO. → (trạng thái, đã có từ trước?) · None khi phiếu không có phần nhiên liệu. Ghi kết quả (kể cả
    khi hỏng) rồi mới trả / ném — lần sau biết gửi lại gói nào."""
    from services import chi_tune as CHI
    do_id = ma_do(p)
    b = db.get(GuiSoNhienLieuTune, do_id)
    if b is not None and b.status == "synced":
        return xuat(b), True
    if b is not None and b.status == "conflict":
        _loi("DA_XUNG_DOT", "Lần gửi SO nhiên liệu trước bên kế toán báo trùng DO (409) — hai bên đối soát, không gửi lại.", 409)
    if b is None and not can_so(db, p):
        return None
    if _chua_ro(b):
        body_json, key = b.request_body, b.idempotency_key
    else:
        body, _ = dung_goi(db, p)                               # kiểm gói TRƯỚC rồi mới tạo đối tác bên kế toán
        o = db.get(Owner, p.owner_id)
        # đối tác phải có sẵn bên đó (52955) — cùng đối tượng EPLCX-<owner_id> mà phiếu chi trả chủ xe dùng
        CHI.doi_tuong(db, "chu_xe", p.owner_id, p.owner_name or (o.name if o else None), sdt=getattr(o, "phone", None), to_chuc=False)
        db.commit()
        key = khoa(do_id)
        body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    now = dt.datetime.utcnow()
    if b is None:
        b = GuiSoNhienLieuTune(do_id=do_id, trip_id=p.id, idempotency_key=key, request_body=body_json, attempts=0, first_attempt_at=now)
        db.add(b)
    b.owner_id, b.partner_code = p.owner_id, json.loads(body_json)["header"]["partner_code"]
    b.idempotency_key, b.request_body = key, body_json
    b.attempts = (b.attempts or 0) + 1
    b.last_attempt_at, b.pushed_by = now, getattr(user, "full_name", None)
    goc, _ = GT.cau_hinh(dang_nhap=False)
    try:
        ma, than, tho = _goi("POST", DUONG, body_json, key)
    except HTTPException:
        raise
    except Exception as e:                                     # mất mạng, DNS, hết giờ — chưa rõ bên kia đã ghi chưa
        b.status, b.http_status, b.response_body = "failed", None, None
        b.error_code, b.error_message = "QLSX_KHONG_GOI_DUOC", "Không gọi được %s: %s" % (urlsplit(goc).netloc, e)
        db.commit()
        _loi("QLSX_KHONG_GOI_DUOC", "Không gọi được bên kế toán (%s): %s. Bấm lại sẽ gửi đúng gói, đúng khoá cũ." % (urlsplit(goc).netloc, e), 502)
    st, kq, ma_loi, loi = doc_ket_qua(ma, than, tho)
    b.status, b.http_status, b.response_body = st, ma, (tho or "")[:20000]
    b.error_code, b.error_message = ma_loi, loi
    if st == "synced":
        b.replayed = bool(kq.get("replayed"))
        b.order_id, b.order_code = GT._int(kq.get("orderId")), GT._chu(kq.get("orderCode"), 64)
        b.retk_auto_id, b.retk_code = GT._int(kq.get("retkAutoId")), GT._chu(kq.get("retkCode"), 64)
        b.currency, b.total_amount = GT._chu(kq.get("currency"), 3) or TIEN, GT._so(kq.get("totalAmount"))
        b.synced_at = now
        if b.thu_trang_thai is None:                              # vừa tạo: còn nợ đúng bằng tổng, chưa thu
            b.thu_tong = b.thu_con_no = b.total_amount
            b.thu_da_thu, b.thu_trang_thai, b.thu_doc_luc = 0.0, "chua_thu", now
        p.updated_at = now
    db.commit()
    if st != "synced":
        _loi(ma_loi or "BEN_KE_TOAN_TU_CHOI", "Bên kế toán chưa tạo SO nhiên liệu cho %s: %s" % (p.doc_no, loi or ma_loi),
             409 if st == "conflict" else (502 if (ma or 0) >= 500 else 422))
    return xuat(b), False


# ================================================================ thu tiền SO nhiên liệu — bản đọc lại (chỉ xem)
LECH = 0.005


def _ap_get(b, kq):
    """Áp kết quả GET fuel-sales-orders/{do} (totalAmount, remaining) lên bản ghi."""
    tong, con = GT._so(kq.get("totalAmount")), GT._so(kq.get("remaining"))
    if tong is None or con is None:
        return False
    b.thu_tong, b.thu_con_no, b.thu_da_thu = tong, con, round(tong - con, 5)
    b.thu_trang_thai = "da_thu" if con <= LECH else ("thu_mot_phan" if tong - con > LECH else "chua_thu")
    b.thu_doc_luc, b.thu_loi = dt.datetime.utcnow(), None
    return True


def doc_thu(db, cac_so, san=None):
    """Đọc lại còn nợ của các SO nhiên liệu (đã synced) từ hệ anh Tune: công nợ của từng ĐỐI TÁC (customer-detail — một lời gọi một
    đối tác, cùng cách đọc SO cước: de_nghi_thu.ap_thu), SO không thấy ở đó thì hỏi thẳng GET fuel-sales-orders/{do}. Ghi vào
    thu_*; KHÔNG commit. → {"da_doc": n, "loi": câu lỗi | None}. Hỏng thì dừng, giữ số đọc lần trước, ghi lỗi lên bản ghi.
    `san` (06/10): {owner_id: công nợ đối tác đã đọc (chi_tune.cong_no_doi_tac)} — màn Tất toán đối tác đọc một lần cho cả SO nhiên
    liệu lẫn SO bán hàng mua ở quầy, không gọi hai lần."""
    from services import chi_tune as CHI
    from services.de_nghi_thu import ap_thu
    ds = [b for b in cac_so if b is not None and b.status == "synced" and b.order_code]
    theo = {}
    for b in ds:
        theo.setdefault(b.owner_id, []).append(b)
    da, loi = 0, None
    for oid, cac in theo.items():
        o = db.get(Owner, oid) if oid else None
        try:
            kq = (san or {}).get(oid) or (CHI.cong_no_doi_tac(db, o) if o is not None else None)
            for b in cac:
                no, don = (kq or {}).get("no") or [], (kq or {}).get("don") or []
                if any((x.get("so") or "") == b.order_code for x in no + don):
                    ap_thu(b, no, don)
                else:                                           # không thấy trong công nợ đối tác: hỏi thẳng SO của DO
                    ma, than, tho = _goi("GET", DUONG + "/" + quote(b.do_id))
                    if not (isinstance(than, dict) and than.get("Success") is True and isinstance(than.get("Result"), dict)
                            and _ap_get(b, than["Result"])):
                        b.thu_loi = "Không đọc được SO nhiên liệu %s (HTTP %s)." % (b.order_code, ma)
                        continue
                da += 1
        except HTTPException as e:
            loi = (e.detail or {}).get("loi") if isinstance(e.detail, dict) else str(e.detail)
            for b in cac:
                b.thu_loi = loi
            break
        except Exception as e:                                  # noqa: BLE001 — mất mạng ở GET dự phòng
            loi = "Không gọi được hệ kế toán: %s" % e
            for b in cac:
                b.thu_loi = loi
            break
    return {"da_doc": da, "loi": loi}


def con_no_lak(b):
    """Còn nợ của SO nhiên liệu theo bản đọc lại (LAK); chưa đọc lần nào thì bằng tổng SO."""
    if b is None or b.status != "synced":
        return None
    if b.thu_con_no is not None:
        return max(0.0, float(b.thu_con_no))
    return float(b.total_amount or 0)


# ================================================================ cấn trừ SO nhiên liệu vào tiền trả đối tác (02/10)
DUONG_CAN_TRU = "/api/v1/sales/debt/collection-offset"
_KHOA_SO_TKN = ("documentNo", "DocumentNo", "offsetNo", "OffsetNo", "voucherNo", "VoucherNo", "tknNo", "TknNo", "code", "Code")
_KHOA_ID = ("documentId", "DocumentId", "offsetId", "OffsetId", "id", "Id")


def khoa_can_tru(ref_no, order_code, huy=False):
    k = "logistics-offset%s:%s:%s" % ("-cancel" if huy else "", ref_no, order_code)
    if not GT.KEY_HOP_LE.match(k):
        _loi("KEY_SAI", "Số đề nghị %s / SO %s không dựng được Idempotency-Key cấn trừ hợp lệ." % (ref_no, order_code))
    return k


def goi_can_tru(order_code, so_tien, ref_no, ly_do, ngay=None, tien=TIEN, ty_gia=None):
    """Thân lời gọi cấn trừ (giao ước 02/10): {OrderCode, Amount, CurrencyCode, RefNo, Reason, Date} — tiền SO (Kíp).
    06/10: cấn trừ cả SO BÁN HÀNG mua ở quầy (tra_chu_xe.so_quay) — tiền theo tiền của SO (`tien`; thủ tục bên kế toán chặn mã tiền
    khác tiền SO, 52789); SO không phải Kíp thì kèm ExchangeRate (Kíp / một đơn vị, ≤ 5 số lẻ — giới hạn của thủ tục). SO Kíp: thân
    y như cũ (không thêm khoá)."""
    tien = (tien or TIEN).upper()
    x = {"OrderCode": order_code, "Amount": GT._so_json(GT._tien(so_tien, "Amount")), "CurrencyCode": tien, "RefNo": ref_no,
         "Reason": (ly_do or "")[:250], "Date": (ngay or dt.date.today()).isoformat()}
    if tien != TIEN and ty_gia:
        x["ExchangeRate"] = GT._so_json(Decimal(str(round(float(ty_gia), 5))))
    return x


def ly_do_quay():
    """Lý do cấn trừ SO bán hàng mua ở quầy (06/10) — ngắn như ly_do_can_tru: bên kế toán tự ghép số đề nghị, số SO, số TKN."""
    return "Mua ở quầy"


def ly_do_can_tru(doc_no):
    """Lý do cấn trừ gửi bên kế toán — NGẮN. Bên đó ghép «Cấn trừ công nợ đối tác · <TCX> · SO <SO> · <TKN> · <lý do>» thành diễn
    giải bút toán (DOC_DESCRIPTION); UAT 03/10: lý do dài (số SO, tên đối tác, số DO, số đề nghị — 128 ký tự) làm diễn giải 229 ký tự,
    cột trên DB demo không chứa nổi → 422 DEBT_OFFSET_JOURNAL_FAILED (52508), bên đó gỡ TKN. Số đề nghị và số SO đã có trong phần bên
    đó ghép — ở đây chỉ còn số DO."""
    return ("DO %s" % (doc_no or "")).strip()[:40]


def _doc_envelope(ma, than, tho):
    """→ (thành công?, Result, mã lỗi, câu lỗi, chưa rõ?). Envelope bên anh Tune: {Success, Code, Message, Result, ErrorDetail}."""
    if isinstance(than, dict) and than.get("Success") is True:
        return True, than.get("Result"), None, None, False
    ma_loi = None
    if isinstance(than, dict):
        ma_loi = ((than.get("ErrorDetail") or {}).get("ErrorCode") if isinstance(than.get("ErrorDetail"), dict) else None) \
            or (str(than.get("Code")) if than.get("Code") not in (None, "") else None)
    cau = (than or {}).get("Message") if isinstance(than, dict) else (tho or "")[:300]
    return False, None, ma_loi or "QLSX_HTTP_%s" % ma, cau or "Bên kế toán trả HTTP %s." % ma, (ma or 0) >= 500


def _lay(r, khoa):
    if isinstance(r, dict):
        for k in khoa:
            if r.get(k) not in (None, ""):
                return r[k]
    return None


def _lam_moi_can_tru(db, ct):
    """Khoá MỚI + thân MỚI cho một lần cấn trừ mà bên kế toán đã GỠ (UAT 03/10). Bên đó: bút toán cấn trừ hỏng → tự gỡ TKN (State
    CANCELLED); gửi lại CÙNG khoá chỉ đọc lại bản đã gỡ (Replayed, vẫn Success) — không cấn trừ lại. Khoá cũ coi như đã dùng hết:
    hậu tố «:r<lần gửi>», lý do ngắn (ly_do_can_tru)."""
    from models import Trip
    p = db.get(Trip, ct.trip_id) if ct.trip_id else None
    k = "%s:r%d" % (khoa_can_tru(ct.ref_no, ct.order_code), ct.attempts or 1)
    if not GT.KEY_HOP_LE.match(k):
        _loi("KEY_SAI", "Không dựng được Idempotency-Key mới cho lần cấn trừ SO %s." % ct.order_code)
    ct.idempotency_key = k
    try:
        cu = json.loads(ct.request_body or "{}")
    except ValueError:
        cu = {}
    # 06/10: SO bán hàng mua ở quầy (không theo chuyến — trip_id trống) giữ tiền / tỷ giá / lý do của gói cũ
    ly_do = ly_do_can_tru(p.doc_no) if p is not None else (cu.get("Reason") or ly_do_quay())
    ct.request_body = json.dumps(goi_can_tru(ct.order_code, ct.amount, ct.ref_no, ly_do, tien=cu.get("CurrencyCode") or getattr(ct, "currency", None) or TIEN,
                                             ty_gia=cu.get("ExchangeRate")),
                                 ensure_ascii=False, separators=(",", ":"))


def gui_can_tru(db, ct, _lam_lai=False):
    """Gửi (lại) MỘT lần cấn trừ (CanTruTune) — cùng gói, cùng khoá đã lưu lúc lập đề nghị. Đã xong thì thôi. Ghi kết quả (kể cả
    khi hỏng) rồi mới ném. Bên kế toán trả lại một lần cấn trừ ĐÃ GỠ (State CANCELLED — lần trước bút toán hỏng, bên đó tự gỡ) thì
    KHÔNG phải đã cấn trừ (UAT 03/10: trước đây ghi "da_gui" → phiếu chi trả đối tác cả phần lẽ ra đã trừ): lập lần mới bằng khoá mới,
    gửi một lần."""
    if ct.status == "da_gui":
        return ct
    goc, _ = GT.cau_hinh(dang_nhap=False)
    ct.attempts, ct.last_attempt_at = (ct.attempts or 0) + 1, dt.datetime.utcnow()
    try:
        ma, than, tho = _goi("POST", DUONG_CAN_TRU, ct.request_body, ct.idempotency_key)
    except HTTPException:
        raise
    except Exception as e:                                     # mất mạng — chưa rõ bên kia đã cấn trừ chưa: gửi lại đúng khoá
        ct.status, ct.http_status, ct.error_code = "loi", None, "QLSX_KHONG_GOI_DUOC"
        ct.error_message = "Không gọi được %s: %s" % (urlsplit(goc).netloc, e)
        db.commit()
        _loi("QLSX_KHONG_GOI_DUOC", "Không gọi được bên kế toán để cấn trừ SO %s: %s — gửi lại đề nghị sẽ gửi đúng khoá cũ."
             % (ct.order_code, e), 502)
    ok, kq, ma_loi, cau, _ = _doc_envelope(ma, than, tho)
    ct.http_status, ct.response_body = ma, (tho or "")[:20000]
    if ok and str(_lay(kq, ("State", "state")) or "").upper() == "CANCELLED":
        so_cu = _lay(kq, _KHOA_SO_TKN)
        if _lam_lai:
            ct.status, ct.error_code = "loi", "DEBT_OFFSET_DA_GO"
            ct.error_message = "Bên kế toán trả lần cấn trừ %s đã gỡ, cả với khoá mới." % (so_cu or "")
            db.commit()
            _loi("DEBT_OFFSET_DA_GO", "Bên kế toán chưa cấn trừ %s %s: lần cấn trừ %s đã bị gỡ bên đó — báo bên kế toán."
                 % (ten_so(ct), ct.order_code, so_cu or ""), 409)
        _lam_moi_can_tru(db, ct)
        db.commit()
        return gui_can_tru(db, ct, _lam_lai=True)
    if ok:
        so = kq if isinstance(kq, str) else _lay(kq, _KHOA_SO_TKN)
        ct.status, ct.so_tkn, ct.real_id = "da_gui", GT._chu(so, 64), GT._int(_lay(kq, _KHOA_ID))
        ct.error_code = ct.error_message = None
        db.commit()
        return ct
    ct.status, ct.error_code, ct.error_message = "loi", ma_loi, cau
    db.commit()
    _loi(ma_loi, "Bên kế toán chưa cấn trừ %s %s: %s" % (ten_so(ct), ct.order_code, cau), 502 if (ma or 0) >= 500 else 422)


def huy_can_tru(db, ct, ly_do=None):
    """Bỏ một lần cấn trừ (bỏ đề nghị): POST …/collection-offset/cancel. Lần gửi trước chắc chắn hỏng (bên kia từ chối 4xx) thì
    không có gì để bỏ. Bên kia không thấy (404) cũng coi như đã bỏ. KHÔNG commit."""
    if ct.status == "huy":
        return ct
    if ct.status == "loi" and ct.http_status is not None and ct.http_status < 500:
        ct.status, ct.huy_luc = "huy", dt.datetime.utcnow()
        return ct
    than_huy = {"OrderCode": ct.order_code, "RefNo": ct.ref_no, "DocumentNo": ct.so_tkn, "DocumentId": ct.real_id,
                "Reason": (ly_do or "Bỏ đề nghị trả đối tác %s" % ct.ref_no)[:250], "Date": dt.date.today().isoformat()}
    body = json.dumps({k: v for k, v in than_huy.items() if v is not None}, ensure_ascii=False, separators=(",", ":"))
    try:
        # khoá huỷ theo khoá tạo hiện tại (lần cấn trừ làm lại có hậu tố :r<lần> — _lam_moi_can_tru)
        ma, than, tho = _goi("POST", DUONG_CAN_TRU + "/cancel", body,
                             (ct.idempotency_key or khoa_can_tru(ct.ref_no, ct.order_code)).replace("logistics-offset:", "logistics-offset-cancel:", 1))
    except HTTPException:
        raise
    except Exception as e:                                     # noqa: BLE001
        _loi("QLSX_KHONG_GOI_DUOC", "Không gọi được bên kế toán để bỏ cấn trừ SO %s: %s — đề nghị giữ nguyên, thử lại sau."
             % (ct.order_code, e), 502)
    ok, _, ma_loi, cau, _ = _doc_envelope(ma, than, tho)
    ct.huy_body = (tho or "")[:20000]
    if ok or ma == 404:
        ct.status, ct.huy_luc = "huy", dt.datetime.utcnow()
        return ct
    _loi(ma_loi, "Bên kế toán chưa bỏ cấn trừ %s %s (%s): %s" % (ten_so(ct), ct.order_code, ct.so_tkn or "—", cau),
         502 if (ma or 0) >= 500 else 409)


def ten_so(ct):
    """Tên loại SO của một lần cấn trừ cho câu báo (06/10): theo chuyến → SO nhiên liệu; không theo chuyến → SO bán hàng mua ở quầy."""
    return "SO nhiên liệu" if getattr(ct, "trip_id", None) else "SO bán hàng (mua ở quầy)"


def xuat_can_tru(ct):
    # 06/10: `loai` — so_nhien_lieu (theo chuyến) · so_quay (SO bán hàng mua ở quầy của đối tác, không theo chuyến)
    return {"order_code": ct.order_code, "so_tkn": ct.so_tkn, "tien": ct.amount, "tien_te": ct.currency, "trang_thai": ct.status,
            "trip_id": ct.trip_id, "do_id": ct.do_id, "error_code": ct.error_code, "error_message": ct.error_message,
            "loai": "so_nhien_lieu" if ct.trip_id else "so_quay"}
