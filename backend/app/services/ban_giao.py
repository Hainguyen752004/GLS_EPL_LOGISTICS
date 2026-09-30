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
"""
import json
import os

from models import Part, Route, Trip, TripAttachment, TripExpense
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
    return bool(p.locked) and p.transport_status == "arrived"


def _gio(t):
    """Giờ lưu trong DB là UTC không kèm múi — ghi rõ +00:00 cho bên kia."""
    if t is None:
        return None
    t = t.replace(microsecond=0)
    return t.isoformat() + "+00:00" if t.tzinfo is None else t.isoformat()


def _ngay(d):
    return d.isoformat() if d else None


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
    t = _tu_dien().get(d.item_key or "") or {}
    return t.get("vi") or d.item_key or "", t.get("lo") or t.get("vi") or d.item_key or ""


def _dong_chi(db, p):
    return (db.query(TripExpense).filter(TripExpense.trip_id == p.id)
            .order_by(TripExpense.section, TripExpense.line_no).all())


def _chu_ky_pod(db, p):
    return db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind == "pod_sign").count()


def dong_danh_sach(p):
    """Một dòng của danh sách — header RÚT GỌN, đúng các khoá EPL_System trả (bên anh Tune đọc `Summary` từ đây),
    thêm vài khoá đọc được bằng mắt (số phiếu, tên khách, biển số, tài xế) để thủ quỹ chọn đúng DO."""
    t = tinh_phieu(p, [])          # cước chỉ phụ thuộc tấn và đơn giá, không cần dòng chi
    return {
        "do_id": ma_do(p), "status": "delivered", "doc_no": p.doc_no, "kind": p.kind,
        "customer_id": p.customer_id, "customer_name": p.customer_name,
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


def dong_goi(db, p):
    """Gói bàn giao `{header, details}` của một phiếu đã về và đã khoá."""
    dong = _dong_chi(db, p)
    t = tinh_phieu(p, dong, p.collected_lak or 0)
    ccy = t["ccy"]
    tuyen = db.get(Route, p.route_id) if p.route_id else None
    lk = p.company == "joint"
    header = {
        "do_id": ma_do(p), "status": "delivered", "source_system": "EPL_LAO",
        "trip_id": p.id, "doc_no": p.doc_no, "kind": p.kind,               # gom (đi lấy hàng) · giao (đi giao hàng)
        "doc_date": _ngay(p.doc_date), "out_date": _ngay(p.out_date), "back_date": _ngay(p.back_date),
        "company": p.company, "owner_id": p.owner_id if lk else None, "owner_name": p.owner_name if lk else None,
        "customer_id": p.customer_id, "customer_name": p.customer_name,
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
        "invoiced": bool(p.invoiced), "inv_no": p.inv_no,
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
            "acc_code": None, "acc_code_note": "Tài khoản chi phí thuê xe liên kết chờ anh Khampla chốt (621 / 611 / theo Excel).",
        }
    details = [{
        "line_no": 1, "kind": "thu", "charge_type": "freight", "section": None,
        "name": "Cước vận chuyển %s · %s" % (p.doc_no, ("trọn chuyến" if t["cach_tinh"] == "chuyen"
                                                        else "%s t × %s %s" % (t["tan_tinh"], t["don_gia"], ccy))),
        "qty": 1 if t["cach_tinh"] == "chuyen" else t["tan_tinh"], "unit_price": t["don_gia"],
        "actual_amount": t["doanh_thu"], "currency": ccy, "amount_lak": t["doanh_thu_lak"],
        "acc_code": "%s/%s" % (TK.PHAI_THU, TK.DT_VAN_CHUYEN), "missing_acc_code": False,
        "paid_by": None, "source": "cuoc", "ref_id": p.id,
    }]
    for i, d in enumerate(dong, start=2):
        epl = not (lk and d.paid_by_epl is False)
        ma = TK.tk_dong(p.company, d) if epl else None
        gia = gia_dong(p, d)
        vi, lo = _ten(db, d)
        details.append({
            "line_no": i, "kind": "chi", "charge_type": d.item_key or d.section, "section": MUC.get(d.section),
            "section_name": TEN_MUC.get(d.section), "item_key": d.item_key, "name": vi, "name_lo": lo,
            "qty": d.qty, "unit_price": gia, "actual_amount": lam_tron((d.qty or 0) * gia, d.currency),
            "currency": d.currency, "amount_lak": round(tien_dong(p, d)),
            "acc_code": ma, "missing_acc_code": bool(epl and not ma),
            "paid_by": "epl" if epl else "chu_xe", "source": d.source,
            "sale_to_owner": bool(la_xuat_ban(p, d)), "ghi_no": bool(d.ghi_no),
            "place_id": d.place_id, "supplier_id": d.supplier_id, "part_id": d.part_id, "note": d.note, "ref_id": d.id,
        })
    return {"header": header, "details": details}
