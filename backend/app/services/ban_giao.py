# -*- coding: utf-8 -*-
"""BÀN GIAO DO cho hệ kế toán của anh Tune (QLSX DemoLao) — chỉ ĐỌC.

Hệ anh Tune chọn DO làm nguồn cho phiếu thu chi (`cash-voucher-references?type=DO`) bằng cách gọi API bàn giao của
Logistics: `GET /api/handover/delivery-orders` (quét danh sách) rồi `GET /api/handover/delivery-orders/{do_id}` (header +
details). Hệ đó đang đọc EPL_System bên Việt Nam; trang điều xe Lào dựng ĐÚNG khuôn đó (EPL_System
`routes/handover_routes.py`) để bên anh chỉ việc trỏ địa chỉ sang đây — hợp đồng kế toán, mục 12.5 và 12.7.4.

Một phiếu xuất xe = một DO, mã `EPLLAO-<Trip.id>` (trùng `do_id` gửi SO ở mục 3.2). Chỉ bàn giao phiếu ĐÃ VỀ và ĐÃ KHOÁ
(kế toán Viêng Chăn khoá sau khi có biên bản giao nhận): nhả sớm hơn thì bên kia lập phiếu trên số chưa chốt. Mọi con số
đọc lại từ `tinh_phieu` và `tk_dong` — cùng nguồn với phiếu trên màn, nên không có hai con số khác nhau cho một DO.

Tiền: cước theo tiền của phiếu (USD / THB / LAK…), từng dòng chi theo tiền của dòng, kèm số quy Kíp theo tỷ giá khoá trên
phiếu. Định khoản từng dòng là mã thật trong danh mục Lào (`services/tai_khoan.py`); dòng chủ xe tự trả không có mã.
Tiền thuê xe liên kết để ở `header.hire`, KHÔNG thành dòng định khoản: tài khoản chi phí thuê xe còn chờ anh Khampla chốt
(hợp đồng kế toán, mục 8 lỗ hổng 1).

Từ 02/10 (màn "Tổng hợp thu chi" bên Web anh Tune): mỗi dòng mang `line_key` (khoá ổn định) và `settlement` (dòng đã vào chứng
từ nào, khoá hay còn lập phiếu được) — services/chung_tu_dong_do.py. Khoá cũ của gói giữ nguyên.

Từ 06/10 (chủ dự án duyệt rà Nợ/Có): dòng trả cùng lương mà DO đã ghi bút toán `cung_luong` Nợ 625 / Có 4201 lúc khoá mang thêm
`pay_acc_code` "4201/1011" — TK khi trả: phiếu chi DO bên Web ghi Nợ 4201 (API anh Tune ưu tiên trường này hơn vế Nợ của acc_code).
DO khoá trước bản đó không có trường này → phiếu chi lương vẫn Nợ 625 (chi phí chưa ghi lúc khoá) — không ghi chi phí hai lần.

Từ 06/10 (chủ dự án: hộp "Tạo phiếu chi theo DO" bên Web không thấy DO đang chạy, phiếu chi tạm ứng không có Vụ việc): bàn giao
cả DO ĐANG CHẠY — `status` nói thật DO đang ở đâu (`trang_thai_do`: delivered · arrived · in_transit), danh sách lọc theo
`scope` (routes/ban_giao.py, mặc định vẫn chỉ DO đã xong). Mỗi DO thêm `payment_status` (`trang_thai_chi`) — viên trạng thái
chi tính GỘP cho cả trang, không một câu SQL mỗi DO.
"""
import json
import os

from models import Customer, Part, Route, Trip, TripAttachment, TripExpense
from services import but_toan_cho as BTC
from services import tai_khoan as TK
from services.tinh_toan import gia_dong, la_xuat_ban, lam_tron, tien_dong, tinh_phieu, ty_gia

TIEN_TO = "EPLLAO-"
MUC = {"fuel": "III", "travel": "IV", "repair": "V", "other": "VI"}
TEN_MUC = {"fuel": "Nhiên liệu", "travel": "Chi phí đi đường", "repair": "Sửa chữa", "other": "Chi khác"}
_TU_DIEN = {}


def ma_do(p):
    return TIEN_TO + p.id


def tim(db, do_id):
    """Phiếu của một mã DO bàn giao; mã không đúng dạng `EPLLAO-…` thì không có."""
    do_id = (do_id or "").strip()
    if not do_id.startswith(TIEN_TO) or len(do_id) <= len(TIEN_TO):
        return None
    return db.get(Trip, do_id[len(TIEN_TO):])


def ban_giao_duoc(p):
    """DO đã xong (đã về + kế toán đã khoá) — điều kiện tạo SO (gui_tune.dung_goi); danh sách bàn giao `scope=done`."""
    return bool(p.locked) and p.transport_status == "arrived"


PHAM_VI = ("done", "open", "all")      # 06/10 — B1 `scope`: đã xong · chưa xong (đang chạy / đã về chờ khoá) · cả hai
TRANG_THAI_CHI = ("da_chi", "dang_chi", "chua_chi", "khong_co_khoan")


def trang_thai_do(p):
    """`status` của DO trong gói bàn giao (06/10 — trước đó chỉ bàn giao DO đã xong nên luôn "delivered"). Cùng bộ chữ
    canonical_status của EPL_System: delivered = đã về + đã khoá · arrived = đã về, chờ kế toán Viêng Chăn khoá ·
    in_transit = đang chạy (đã xuất xe). Web anh Tune vẫn lọc "delivered" thì DO chưa xong tự rơi ra như trước."""
    if ban_giao_duoc(p):
        return "delivered"
    return "arrived" if p.transport_status == "arrived" else "in_transit"


def _gio(t):
    """Giờ lưu trong DB là UTC không kèm múi — ghi rõ +00:00 cho bên kia."""
    if t is None:
        return None
    t = t.replace(microsecond=0)
    return t.isoformat() + "+00:00" if t.tzinfo is None else t.isoformat()


def _ngay(d):
    return d.isoformat() if d else None


def _so(v):
    """Số gọn cho chuỗi cách tính: 12.0 → 12, 12.5 → 12.5, nghìn có dấu phẩy (1,250,000)."""
    v = float(v or 0)
    return "{:,.0f}".format(v) if v == int(v) else "{:,.10g}".format(v)


def _tu_dien():
    """Tên khoản mục (x_toll, diesel…) lấy từ từ điển giao diện — cùng chữ người dùng thấy trên phiếu."""
    if not _TU_DIEN:
        tep = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                                            "frontend", "js", "ngon_ngu.js"))
        try:
            chu = open(tep, encoding="utf-8").read()
            _TU_DIEN.update(json.loads(chu[chu.index("{"):chu.rindex("}") + 1]))
        except (OSError, ValueError):
            _TU_DIEN["_"] = {}
    return _TU_DIEN


def _ten(db, d):
    """(tên tiếng Việt, tên tiếng Lào) của một dòng chi."""
    if d.part_id:
        pt = db.get(Part, d.part_id)
        if pt is not None and pt.name:
            return pt.name, pt.name
    if d.item_name:
        return d.item_name, d.item_name
    from services import khoan_muc
    if khoan_muc.ten(d.item_key):            # khoản thêm ở màn Khoản mục chi phí (08/10) — tên ở bảng, không ở từ điển giao diện
        return khoan_muc.ten(d.item_key)
    t = _tu_dien().get(d.item_key or "") or {}
    return t.get("vi") or d.item_key or "", t.get("lo") or t.get("vi") or d.item_key or ""


def _ma_khach(db, p):
    """Mã khách BÊN KẾ TOÁN (OBJ_OBJECTNO) — ô Mã khách ở danh mục khách; trống thì None."""
    k = db.get(Customer, p.customer_id) if p.customer_id else None
    return k.code if k else None


def _dong_chi(db, p):
    return (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())


def _chu_ky_pod(db, p):
    return db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind == "pod_sign").count()


def dong_danh_sach(p, ma_khach=None, chi=None):
    """Một dòng của danh sách — header RÚT GỌN, đúng các khoá EPL_System trả (bên anh Tune đọc `Summary` từ đây),
    thêm vài khoá đọc được bằng mắt (số phiếu, tên khách, biển số, tài xế) để thủ quỹ chọn đúng DO.

    `customer_id` = MÃ KHÁCH BÊN KẾ TOÁN (OBJ_OBJECTNO), trùng `header.customer_id` của gói tạo SO: màn "Vụ việc" bên anh
    hiện ô này làm "Khách hàng / Tên" và tìm theo nó (GLS-QLSX-APIs `CashVoucherReferenceController`). Khách chưa được
    kế toán gán mã thì null. Mã khách nội bộ bên em ở `customer_ref`.

    06/10: `status` theo `trang_thai_do` (DO đang chạy không còn giả "delivered"), thêm `transport_status` · `locked` và
    `payment_status` (`trang_thai_chi`, người gọi tính gộp cho cả trang rồi truyền vào `chi`)."""
    t = tinh_phieu(p, [])          # cước chỉ phụ thuộc tấn và đơn giá, không cần dòng chi
    return {
        "do_id": ma_do(p), "status": trang_thai_do(p), "doc_no": p.doc_no, "kind": p.kind,
        "transport_status": p.transport_status, "locked": bool(p.locked), "payment_status": chi,
        "customer_id": ma_khach, "customer_code": ma_khach, "customer_ref": p.customer_id, "customer_name": p.customer_name,
        "quotation_id": None, "contract_no": p.contract_no,
        "route_id": p.route_id, "origin": p.origin, "destination": p.destination,
        "vehicle_id": p.vehicle_id, "truck_no": p.truck_no, "plate_head": p.plate_head,
        "driver_id": p.driver_id, "driver_name": p.driver_name,
        "company": p.company, "owner_name": p.owner_name if p.company == "joint" else None,
        "selling_price": t["doanh_thu"], "customer_surcharge_total": 0, "final_selling_price": t["doanh_thu"],
        "currency": t["ccy"], "final_selling_price_lak": t["doanh_thu_lak"],
        "completed_at": _gio(p.locked_at), "completed_by": p.locked_by,
        "detail_url": "/api/handover/delivery-orders/%s" % ma_do(p),
    }


def dong_goi(db, p, chung_tu=True):
    """Gói bàn giao `{header, details}` của một phiếu — đã xong (về + khoá), hoặc từ 06/10 cả DO đang chạy (header.status nói
    rõ, số chi phí là số lúc đọc, chưa chốt).

    `chung_tu` (02/10, màn "Tổng hợp thu chi" bên Web anh Tune): mỗi dòng thêm `line_key` + `settlement` (dòng đã vào chứng từ
    nào — services/chung_tu_dong_do.py), dòng cước thêm `debt`, header thêm `line_key_prefix`, hire thêm `line_key` · `settlement`
    · `journal`. Gói tạo SO (gui_tune.dung_goi) không cần — truyền False."""
    from services import de_nghi_thu as DNT
    dong = _dong_chi(db, p)
    so = DNT.so_cua(db, p)
    co_so = so is not None and so.status == "synced"
    t = tinh_phieu(p, dong, DNT.da_thu_lak(p, so))      # đã thu: bản đọc lại thu tiền SO bên hệ anh Tune (cờ trang tạm bỏ 01/10)
    ccy = t["ccy"]
    tuyen = db.get(Route, p.route_id) if p.route_id else None
    lk = p.company == "joint"
    ma_kt = _ma_khach(db, p)
    r = ty_gia(p, ccy)
    xong = ban_giao_duoc(p)
    header = {
        # 06/10: DO đang chạy cũng có gói (Vụ việc cho phiếu chi tạm ứng / mục V–VI) — status nói thật, không giả "delivered"
        "do_id": ma_do(p), "status": trang_thai_do(p), "source_system": "EPL_LAO",
        "trip_status": "completed" if xong else "in_progress",
        "transport_status": p.transport_status, "locked": bool(p.locked),
        "trip_id": p.id, "doc_no": p.doc_no, "kind": p.kind,               # gom (đi lấy hàng) · giao (đi giao hàng)
        "doc_date": _ngay(p.doc_date), "out_date": _ngay(p.out_date), "back_date": _ngay(p.back_date),
        "company": p.company, "owner_id": p.owner_id if lk else None, "owner_name": p.owner_name if lk else None,
        # customer_id = mã bên kế toán (null khi chưa gán) — xem `dong_danh_sach`; mã nội bộ bên em ở customer_ref
        "customer_id": ma_kt, "customer_code": ma_kt, "customer_ref": p.customer_id, "customer_name": p.customer_name,
        "contract_no": p.contract_no, "hire_contract_no": p.hire_contract_no if lk else None,
        "quotation_id": None,
        "route": {"id": tuyen.id, "name": tuyen.name, "origin": tuyen.origin, "destination": tuyen.destination,
                  "distance_km": tuyen.total_km} if tuyen else None,
        "origin": p.origin, "destination": p.destination, "goods_type": p.goods_type,
        "ore_bill_no": p.ore_bill_no, "ore_bill_date": _ngay(p.ore_bill_date),
        "weight_origin_t": p.weight_origin, "weight_dest_t": p.weight_dest, "loss_pct": t["hao_hut_pct"],
        "weight_kg": round(t["tan_tinh"] * 1000, 3) if t["tan_tinh"] else None,
        "vehicle_id": p.vehicle_id, "truck_no": p.truck_no, "plate_head": p.plate_head, "plate_trailer": p.plate_trailer,
        "driver_id": p.driver_id, "driver_name": p.driver_name,
        "pod_no": p.pod_no, "pod_date": _ngay(p.pod_date), "pod_receiver": p.pod_receiver,
        "pod_condition": p.pod_condition, "pod_signed_at": _gio(p.pod_at), "pod_signature_count": _chu_ky_pod(db, p),
        # Cước — tiền của phần THU theo tiền của phiếu; chi phí từng dòng theo tiền của dòng, cộng lại bằng Kíp.
        "currency": ccy, "currency_thu": ccy, "currency_chi": "LAK",
        "fx_rate_to_lak": ty_gia(p, ccy), "fx_rates_on_trip": {m: ty_gia(p, m) for m in ("USD", "THB", "VND", "CNY")},
        "price_basis": "trip" if t["cach_tinh"] == "chuyen" else "ton",
        "billed_qty": t["tan_tinh"], "unit_price": t["don_gia"],
        "selling_price": t["doanh_thu"], "customer_surcharge_total": 0, "final_selling_price": t["doanh_thu"],
        "final_selling_price_lak": t["doanh_thu_lak"],
        "actual_cost_total_lak": t["tong_chi_lak"],
        "cost_by_section_lak": {MUC[m]: t["chi"][m] for m in MUC},
        "margin_lak": t["lai_lak"], "margin": t["lai"], "margin_currency": ccy,
        # Tên khoá màn "Vụ việc" bên anh Tune đọc (cm-source-reference-modal.js): chi phí theo currency_chi (LAK), quy đổi
        # sang tiền cước; lãi gộp theo tiền cước; fx_rate = 1 currency_chi đổi được bao nhiêu currency_thu.
        "actual_cost_total": t["tong_chi_lak"],
        "actual_cost_total_quy_doi": t["tong_chi_ccy"] if ccy != "LAK" else None,
        "margin_amount": t["lai"],
        "margin_percent": round(t["lai_lak"] * 100.0 / t["doanh_thu_lak"], 1) if t["doanh_thu_lak"] else None,
        "fx_rate": float("%.10g" % (1.0 / r)) if ccy != "LAK" and r else None,
        "fx_rate_source": "tỷ giá khoá trên phiếu" if ccy != "LAK" else None,
        # Khuôn đã công bố (hợp đồng 12.8.3) giữ TÊN khoá. Từ 01/10 hoá đơn là SO bên hệ anh Tune: `invoiced` = DO đã có SO
        # bên đó (gui_so_tune synced), `inv_no` = số SO (order_code). Cờ trips.invoiced · inv_no của trang tạm không ai ghi nữa.
        "invoiced": co_so, "inv_no": so.order_code if co_so else None,
        "completed_at": _gio(p.locked_at), "completed_by": p.locked_by,
    }
    if lk:
        h = t["hire_ccy"]
        header["hire"] = {
            "currency": h, "unit_price": t["gia_thue"], "amount": t["tien_thue"], "amount_lak": t["tien_thue_lak"],
            "fee_pct": p.fee_pct if p.fee_pct is not None else 2, "fee": t["phi"],
            "over_limit_t": p.over_limit_t if p.over_limit_t is not None else 40, "over_t": t["vuot_tan"],
            "over_deduction": t["tru_vuot"], "advanced_by_epl": t["ung_truoc"],
            "pay_owner": t["tra_chu_xe"], "pay_owner_lak": t["tra_chu_xe_lak"],
            "owner_self_paid_lak": t["chu_xe_tu_tra_lak"],
            # chủ dự án chốt 01/10: Nợ 621 / Có 4022 bằng `amount` lúc khoá phiếu (services/tai_khoan.py)
            "acc_code": "%s/%s" % (TK.CP_THUE_XE, TK.CHU_XE),
            # 06/10: phí quản lý và cắt quá tải có bút toán cùng chứng từ thue_xe (but_toan_cho.dong_khoa_phieu) — câu cũ "chưa có
            # bút toán riêng" sai từ hôm nay; acc_code giữ cặp chính 621/4022 (khuôn đã công bố)
            "acc_code_note": ("Nợ %s %s / Có %s %s bằng tiền thuê (amount), lúc khoá phiếu. Cùng chứng từ: phí quản lý (fee) Nợ %s / "
                              "Có %s %s; cắt quá tải (over_deduction) Nợ %s / Có %s %s — khoản bằng 0 thì không có dòng. Sau khoá "
                              "%s còn = amount − fee − over_deduction."
                              % (TK.CP_THUE_XE, TK.ten(TK.CP_THUE_XE), TK.CHU_XE, TK.ten(TK.CHU_XE),
                                 TK.CHU_XE, TK.DT_PHI_QUAN_LY, TK.ten(TK.DT_PHI_QUAN_LY),
                                 TK.CHU_XE, TK.TN_CAT_QUA_TAI, TK.ten(TK.TN_CAT_QUA_TAI), TK.CHU_XE)),
        }
    details = [{
        "line_no": 1, "kind": "thu", "charge_type": "freight", "section": None,
        "name": "Cước vận chuyển %s · %s" % (p.doc_no, ("trọn chuyến" if t["cach_tinh"] == "chuyen"
                                                        else "%s t × %s %s" % (t["tan_tinh"], t["don_gia"], ccy))),
        "qty": 1 if t["cach_tinh"] == "chuyen" else t["tan_tinh"], "unit_price": t["don_gia"],
        "calculation": "trọn chuyến" if t["cach_tinh"] == "chuyen" else "%s t × %s %s" % (_so(t["tan_tinh"]), _so(t["don_gia"]), ccy),
        "actual_amount": t["doanh_thu"], "currency": ccy, "amount_lak": t["doanh_thu_lak"],
        "acc_code": "%s/%s" % (TK.PHAI_THU, TK.DT_VAN_CHUYEN), "missing_acc_code": False,
        "paid_by": None, "source": "cuoc", "ref_id": p.id,
    }]
    # 06/10: dòng trả cùng lương đã ghi Nợ 625 / Có 4201 lúc khoá (but_toan_cho `cung_luong`) → TK khi trả `pay_acc_code` 4201/1011:
    # phiếu chi DO bên Web lấy vế Nợ của trường này (không lấy 625 của acc_code — chi phí đã ghi). DO khoá trước bản sửa: không có.
    luong_gl = {} if lk else BTC.cung_luong_da_ghi(db, p.id)
    for i, d in enumerate(dong, start=2):
        epl = not (lk and d.paid_by_epl is False)
        ma = TK.tk_dong(p.company, d, db) if epl else None
        gia = gia_dong(p, d)
        vi, lo = _ten(db, d)
        details.append({
            "line_no": i, "kind": "chi", "charge_type": d.item_key or d.section, "section": MUC.get(d.section),
            "section_name": TEN_MUC.get(d.section), "item_key": d.item_key, "name": vi, "name_lo": lo,
            "qty": d.qty, "unit_price": gia, "calculation": "%s × %s %s" % (_so(d.qty or 0), _so(gia), d.currency),
            "actual_amount": lam_tron((d.qty or 0) * gia, d.currency),
            "currency": d.currency, "amount_lak": round(tien_dong(p, d)),
            "acc_code": ma, "missing_acc_code": bool(epl and not ma),
            "paid_by": "epl" if epl else "chu_xe", "source": d.source,
            "sale_to_owner": bool(la_xuat_ban(p, d)), "ghi_no": bool(d.ghi_no),
            "place_id": d.place_id, "supplier_id": d.supplier_id, "part_id": d.part_id, "note": d.note, "ref_id": d.id,
        })
        if d.id in luong_gl:
            details[-1]["pay_acc_code"] = "%s/%s" % (TK.LUONG, TK.TIEN[("cash", True)])
    goi = {"header": header, "details": details}
    if chung_tu:
        from services import chung_tu_dong_do as CTD
        CTD.gan(db, p, goi, dong, so)
    return goi


# ================================================================ viên TRẠNG THÁI CHI của DO (06/10)
def _ma_chi(tong, co_ct, da_chi):
    """Mã viên: không có khoản EPL chi · mọi khoản đã chi · chưa khoản nào vào chứng từ · còn lại là đang chi."""
    if not tong:
        return "khong_co_khoan"
    if da_chi >= tong:
        return "da_chi"
    return "chua_chi" if not co_ct else "dang_chi"


def _doc_json(chu):
    try:
        v = json.loads(chu or "[]")
    except ValueError:
        return []
    return v if isinstance(v, list) else []


def trang_thai_chi(db, cac_phieu):
    """{Trip.id: payment_status} cho NHIỀU DO một lần — viên "trạng thái chi" bên Web anh Tune (06/10, giao ước với phía Web):

        {"code": da_chi | dang_chi | chua_chi | khong_co_khoan, "lines_total", "lines_with_voucher", "lines_paid",
         "amount_open", "currency": "LAK", "open_line_keys": [...], "owner_payment": {...} | None}

    DÒNG ĐẾM = dòng chi EPL ứng tiền: mục III mua ngoài (tiền mặt / ghi nợ trạm), IV, V mua ngoài, VI. KHÔNG đếm dòng lấy kho
    (phiếu kho + bút toán xuất kho; xe thuê là SO nhiên liệu — không phải chi tiền), dòng chủ xe tự trả, dòng 0 đồng, dòng trừ
    thẻ cao tốc không có bút toán — đúng các dòng `settlement.state` = not_payable của gói B2, cộng dòng kho.
      lines_with_voucher  dòng `has_voucher` (phiếu chi / bút toán đã sang kế toán)
      lines_paid          trong số đó đã xong: phiếu chi đã ghi sổ (bản đọc lại "da_chi" — tạm ứng, Chi khác mục V, tất toán) ·
                          bút toán đã nhận (ghi nợ NCC — phần của DO xong, trả nhà cung cấp theo đợt; QT_TU tất toán)
      amount_open         Σ Kíp các dòng đếm CHƯA xong (đúng amount_lak từng dòng của gói B2)
      open_line_keys      SourceLineKey ("DO:<do_id>:exp:<id>") các dòng `open` — dòng duy nhất Web tự lập phiếu chi được
                          (cùng lương, chưa vào đường nào). Bên em KHÔNG đọc lại phiếu Web lập theo DO (CM_CombinedVoucher):
                          Web gộp — khoá nào đã nằm trong phiếu chi Web còn hiệu lực thì tính "có chứng từ" (ghi sổ = đã chi).
      owner_payment       xe thuê: trả chủ xe (đề nghị TCX- / phiếu chi Chi khác) — thông tin thêm, KHÔNG gộp vào `code`.

    PHÂN DÒNG theo ĐÚNG thứ tự chung_tu_dong_do.gan (chia) cho dòng không lấy kho — cùng bản ghi thật (bút toán chờ có dòng
    `ref`, phiếu chi mục V–VI, tờ PTU + phiếu chi "Chi trước", tờ PC_TU, tất toán tháng) và cùng hàm luật (BTC.dong_khoa_phieu,
    CMT.dong_quy_chi, la_tien_mat_tai_xe, CTD._trong_tam_ung). Bản ghi nạp GỘP theo danh sách DO (mỗi bảng một câu SQL) —
    danh sách nghìn DO không thành nghìn lần hỏi. kiem/thu_ban_giao_trang_thai_chi.py đối chiếu từng dòng với gói B2.
    Chỉ ĐỌC; trạng thái là bản đọc lại gần nhất của từng đường (chi_tune.dong_bo …), không hỏi sang hệ kế toán."""
    from collections import defaultdict
    from models import ButToanCho, ChiChuXeTune, ChiMucTune, ChiTune, ChungTu, DriverSettlement, PhieuTienTune, Voucher
    from services import but_toan_cho as BTC
    from services import chi_muc_tune as CMT
    from services import chi_tat_toan_tune as CTT
    from services import chung_tu_dong_do as CTD
    from services.tinh_toan import la_tien_mat_tai_xe

    ps = {p.id: p for p in cac_phieu if p is not None}
    if not ps:
        return {}
    ids = list(ps)

    dong = defaultdict(list)
    for d in (db.query(TripExpense).filter(TripExpense.trip_id.in_(ids))
              .order_by(TripExpense.trip_id, TripExpense.section, TripExpense.line_no)):
        dong[d.trip_id].append(d)
    # phụ tùng của các dòng: nạp một lần vào phiên (giữ tham chiếu) — diễn giải bút toán no_ncc đọc bằng db.get
    ma_pt = {d.part_id for ds in dong.values() for d in ds if d.part_id}
    giu_pt = db.query(Part).filter(Part.id.in_(ma_pt)).all() if ma_pt else []

    bt = defaultdict(dict)                    # trip → {TripExpense.id: ButToanCho} — đã gửi thắng chờ gửi (CTD._but_toan_theo_dong)
    for r in (db.query(ButToanCho).filter(ButToanCho.trip_id.in_(ids), ButToanCho.nguon.in_(CTD.NGUON_DONG),
                                          ButToanCho.status != "huy").order_by(ButToanCho.created_at)):
        m = bt[r.trip_id]
        for x in _doc_json(r.dong):
            ref = x.get("ref") if isinstance(x, dict) else None
            if ref and (ref not in m or (m[ref].status != "da_gui" and r.status == "da_gui")):
                m[ref] = r
    cm = defaultdict(dict)                    # trip → {TripExpense.id: ChiMucTune} — lần đi xa nhất (CTD._chi_muc_theo_dong)
    for r in (db.query(ChiMucTune).filter(ChiMucTune.trip_id.in_(ids), ChiMucTune.status != "huy")
              .order_by(ChiMucTune.trip_id, ChiMucTune.lan)):
        m = cm[r.trip_id]
        for i in _doc_json(r.expense_ids):
            if isinstance(i, str) and (i not in m or CTD.HANG.get(r.status, 0) > CTD.HANG.get(m[i].status, 0)):
                m[i] = r
    ung = {}                                  # trip → tờ PTU còn hiệu lực (một chuyến một tờ — phieu_linh.dam_bao_tam_ung)
    for v in db.query(Voucher).filter(Voucher.trip_id.in_(ids), Voucher.kind == "advance"):
        if v.status != "huy" or v.trip_id not in ung:
            ung[v.trip_id] = v if v.status != "huy" else None
    ma_v = [v.id for v in ung.values() if v is not None]
    rec_ung = {r.voucher_id: r for r in db.query(ChiTune).filter(ChiTune.voucher_id.in_(ma_v))} if ma_v else {}
    pc_tu = {}                                # trip → tờ PC_TU mới nhất (quỹ trang điều xe chi tại chỗ — CTD._to_quy)
    for c in db.query(ChungTu).filter(ChungTu.trip_id.in_(ids), ChungTu.loai == "PC_TU").order_by(ChungTu.ts.desc()):
        pc_tu.setdefault(c.trip_id, c)
    chu = {p.owner_id for p in ps.values() if p.company == "joint" and p.owner_id}
    tra = {}                                  # trip → đề nghị trả chủ xe đi xa nhất (CTD.thue)
    if chu:
        for r in db.query(ChiChuXeTune).filter(ChiChuXeTune.owner_id.in_(chu), ChiChuXeTune.status != "huy"):
            for t in _doc_json(r.trip_ids):
                p = ps.get(t) if isinstance(t, str) else None
                if p is not None and p.owner_id == r.owner_id and (
                        t not in tra or CTD.HANG.get(r.status, 0) > CTD.HANG.get(tra[t].status, 0)):
                    tra[t] = r

    tat_toan = object()                       # dòng tài xế tự trả ngoài tạm ứng (xe nhà) — tra tất toán tháng, gộp sau
    ket, cho_tt = {}, []
    for tid, p in ps.items():
        ds, lk = dong.get(tid, []), p.company == "joint"
        bt_p, cm_p, nho = bt.get(tid, {}), cm.get(tid, {}), {}

        def mot_lan(k, ham, nho=nho):
            if k not in nho:
                nho[k] = ham()
            return nho[k]

        def tam_ung(p=p, ds=ds, tid=tid):
            """(phiếu chi "Chi trước" | None, tập dòng nằm trong số đã ứng) — CTD.gan.tam_ung."""
            v, ct = ung.get(tid), pc_tu.get(tid)
            rec = rec_ung.get(v.id) if v is not None else None
            if v is None and ct is None:
                return rec, set()
            tm = [d for d in ds if la_tien_mat_tai_xe(d, p.company)]
            return rec, CTD._trong_tam_ung(p, tm, CTD._so_ung(v, rec, ct))[0]

        def chia(d, p=p, ds=ds, lk=lk, tid=tid, bt_p=bt_p, cm_p=cm_p, mot_lan=mot_lan, tam_ung=tam_ung):
            """[state, đã xong?] của một dòng; None = không đếm. Thứ tự y chung_tu_dong_do.gan → chia."""
            if lk and d.paid_by_epl is False:
                return None                                         # chủ xe tự trả
            if d.source == "kho":
                return None                                         # lấy kho: phiếu kho / bút toán xuất kho / SO nhiên liệu
            if d.id in bt_p:
                r = bt_p[d.id]
                return ["has_voucher", not r.can_dao] if r.status == "da_gui" else ["pending", False]
            if d.id in cm_p:
                r = cm_p[d.id]
                return ["has_voucher", r.status == "da_chi"] if r.status in ("da_gui", "da_chi") else ["pending", False]
            if round(tien_dong(p, d)) <= 0:
                return None                                         # 0 đồng
            if d.id in mot_lan("no_ncc", lambda: {x["ref"] for x in BTC.dong_khoa_phieu(db, p, ds).get(BTC.NO_NCC, ([], None))[0]}):
                return ["pending", False]                           # ghi nợ NCC — bút toán ghi lúc khoá phiếu
            if d.id in mot_lan("quy_chi", lambda: {x.id for m in CMT.MUC for x in CMT.dong_quy_chi(db, p, m, ds)}):
                return ["pending", False]                           # quỹ trả ngay mục V — phiếu chi lập khi ghi sổ mục
            if la_tien_mat_tai_xe(d, p.company):
                rec, trong = mot_lan("tam_ung", tam_ung)
                if d.id in trong:
                    if rec is not None and rec.status in ("da_gui", "da_chi"):
                        return ["has_voucher", rec.status == "da_chi"]
                    return ["pending", False]
                return tat_toan if not lk else ["open", False]
            if getattr(d, "toll_card_id", None):
                return None                                         # trừ thẻ cao tốc, không bút toán
            if tid in pc_tu:
                return ["pending", False]                           # tờ chi tại quỹ trang điều xe (luật cũ) — đối soát
            return ["open", False]                                  # cùng lương / chưa vào đường nào

        cac = []
        for d in ds:
            k = chia(d)
            if k is None:
                continue
            if k is tat_toan:
                ngay = p.out_date or p.doc_date
                ky = ngay.strftime("%Y-%m") if ngay else None
                k = ["pending", False]
                if ky and p.driver_id:
                    cho_tt.append((p.driver_id, ky, k))
            cac.append((d, k))
        ket[tid] = cac

    if cho_tt:                                                      # tất toán tháng — gộp: bản chốt · phiếu · bút toán QT_TU
        ban = {(x.driver_id, x.period): x for x in db.query(DriverSettlement).filter(
            DriverSettlement.driver_id.in_({a for a, _, _ in cho_tt}), DriverSettlement.period.in_({b for _, b, _ in cho_tt}))}
        nguon = {CTT.ma_nguon_tt(x) for x in ban.values()}
        phieu, but = {}, {}
        if nguon:
            for r in db.query(PhieuTienTune).filter(PhieuTienTune.nguon == CTT.NGUON_TT, PhieuTienTune.ma_nguon.in_(nguon)):
                phieu.setdefault(r.ma_nguon, r)
            for r in db.query(ButToanCho).filter(ButToanCho.nguon == CTT.NGUON_TT, ButToanCho.ma_nguon.in_(nguon)):
                but.setdefault(r.ma_nguon, r)
        for a, b, k in cho_tt:                                      # CTD._tat_toan
            x = ban.get((a, b))
            if x is None:
                continue
            rec, r = phieu.get(CTT.ma_nguon_tt(x)), but.get(CTT.ma_nguon_tt(x))
            if rec is not None and rec.status in ("da_gui", "da_chi"):
                k[:] = ["has_voucher", rec.status == "da_chi"]
            elif rec is None and r is not None and r.status == "da_gui":
                k[:] = ["has_voucher", True]

    ra = {}
    for tid, p in ps.items():
        cac = ket[tid]
        co_ct = sum(1 for _, k in cac if k[0] == "has_voucher")
        xong = sum(1 for _, k in cac if k[0] == "has_voucher" and k[1])
        tt = None
        if p.company == "joint":                                    # trả chủ xe — CTD.thue, rút về một mã
            t = tinh_phieu(p, dong.get(tid, []))
            r = tra.get(tid)
            if r is not None and r.status in ("da_gui", "da_chi"):
                ma, so = ("da_chi" if r.status == "da_chi" else "dang_chi"), r.document_no
            elif r is None and (p.owner_payment_id or "").startswith("TUNE:"):
                ma, so = "da_chi", p.owner_payment_id[5:]
            else:
                ma, so = ("chua_chi" if r is not None or (t.get("tra_chu_xe") or 0) > 0 else "khong_co_khoan"), None
            tt = {"code": ma, "ref_no": r.ref_no if r is not None else None, "doc_no": so, "currency": t.get("hire_ccy"),
                  "amount": t.get("tra_chu_xe"), "amount_lak": t.get("tra_chu_xe_lak")}
        ra[tid] = {"code": _ma_chi(len(cac), co_ct, xong), "lines_total": len(cac), "lines_with_voucher": co_ct,
                   "lines_paid": xong, "currency": "LAK",
                   "amount_open": sum(round(tien_dong(p, d)) for d, k in cac if not (k[0] == "has_voucher" and k[1])),
                   "open_line_keys": [CTD.tien_to(ma_do(p)) + CTD.khoa_dong("exp", d.id) for d, k in cac if k[0] == "open"],
                   "owner_payment": tt}
    del giu_pt
    return ra
