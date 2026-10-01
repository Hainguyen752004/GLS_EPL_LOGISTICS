# -*- coding: utf-8 -*-
"""PHIẾU ĐỀ NGHỊ THU — ໃບສະເໜີຮັບເງິນ (sếp 30/09).

Bên mình chỉ làm logistics: phiếu của mình là phiếu ĐỀ NGHỊ. Đề nghị CHI đi theo từng bước của chuyến (tạm ứng, nhiên liệu,
chi các mục); đề nghị THU sinh MỘT lần khi DO xong — xe về, có biên bản giao nhận, kế toán Viêng Chăn KHOÁ phiếu. Tờ này gửi
sang bên công nợ (anh Tune) để bên đó lập SO, xuất hoá đơn và thu tiền khách. Bên mình không thu tiền, không ghi công nợ.

Trạng thái thu (chủ dự án 01/10 — bỏ trang kế toán tạm, số bên đó là số thử): "đã tạo SO" lấy theo lần gửi SO (gui_so_tune),
"đã thu" ĐỌC LẠI từ hệ anh Tune — `POST /api/v1/sales/debt/customer-detail` của khách, dòng nợ có `OrderCode` = SO của DO.
Chỉ xem: không ghi gì sang bên đó. Bản đọc lại nằm trên gui_so_tune.thu_* (và trips.finance_status) để màn hình đọc nhanh;
đọc lại khi người dùng bấm Cập nhật (`cap_nhat`), không hỏi sang mỗi lần mở danh sách.

Số tiền là CƯỚC của phiếu theo đúng tiền tệ của phiếu (USD / THB / LAK…), kèm số quy Kíp theo tỷ giá khoá trên phiếu.
Một phiếu một tờ (nguồn trips:<id>, loại PDT). Mở khoá phiếu → rút tờ khi bên kế toán chưa có SO; khoá lại → tờ mới theo số mới.
"""
import datetime as dt
import json
import time

from fastapi import HTTPException

from models import ChungTu, Customer, GuiSoTune, Trip, TripAttachment, TripExpense
from services import chung_tu as CT
from services.tinh_toan import tinh_phieu, ty_gia

LOAI = "PDT"
TRANG_THAI = ("cho_khoa", "chua_lap", "cho_gui", "da_tao_so", "thu_mot_phan", "da_thu")
LECH = 0.005                       # dưới nửa xu theo tiền SO: coi là hết nợ (làm tròn bên kia)
GIU_GIAY = 60                      # một khách đọc công nợ một lần trong 60 giây — bấm Cập nhật liên tục không hỏi sang liên tục
_DOC = {}                          # khách.id → (lúc, kết quả customer-detail)


def _dong(db, p):
    return db.query(TripExpense).filter(TripExpense.trip_id == p.id).all()


def so_cua(db, p):
    """Lần gửi SO của phiếu (GuiSoTune) hoặc None."""
    return db.get(GuiSoTune, "EPLLAO-" + p.id)


def da_thu_lak(p, so):
    """Tiền khách đã trả cho SO của phiếu, quy Kíp theo tỷ giá khoá trên phiếu — từ bản đọc lại bên kế toán; chưa có thì 0."""
    if so is None or so.status != "synced" or not so.thu_da_thu:
        return 0.0
    return float(so.thu_da_thu) * ty_gia(p, so.currency or p.price_ccy)


def noi_dung(db, p, dong=None, so=None):
    """(tính tiền của phiếu, payload tờ đề nghị thu)."""
    so = so if so is not None else so_cua(db, p)
    t = tinh_phieu(p, dong if dong is not None else _dong(db, p), da_thu_lak(p, so))
    ky = db.query(TripAttachment).filter(TripAttachment.trip_id == p.id, TripAttachment.kind == "pod_sign").count() > 0
    pl = {
        "doc_no": p.doc_no, "kind": p.kind, "company": p.company, "owner_name": p.owner_name if p.company == "joint" else None,
        "customer_id": p.customer_id, "customer_name": p.customer_name, "contract_no": p.contract_no,
        "origin": p.origin, "destination": p.destination, "goods_type": p.goods_type,
        "truck_no": p.truck_no, "plate_head": p.plate_head, "plate_trailer": p.plate_trailer, "driver_name": p.driver_name,
        "out_date": p.out_date.isoformat() if p.out_date else None, "back_date": p.back_date.isoformat() if p.back_date else None,
        "weight_origin": p.weight_origin, "weight_dest": p.weight_dest, "tan_tinh": t["tan_tinh"], "cach_tinh": t["cach_tinh"],
        "don_gia": t["don_gia"], "ccy": t["ccy"], "rate_to_lak": ty_gia(p, t["ccy"]),
        "doanh_thu": t["doanh_thu"], "doanh_thu_lak": t["doanh_thu_lak"],
        "pod_no": p.pod_no, "pod_date": p.pod_date.isoformat() if p.pod_date else None, "pod_receiver": p.pod_receiver,
        "pod_signed": ky, "ore_bill_no": p.ore_bill_no,
    }
    return t, pl


def cua(db, p):
    return CT.tim(db, LOAI, "trips", p.id)


def _co_so(db, p, so=None):
    so = so if so is not None else so_cua(db, p)
    return so is not None and so.status == "synced"


def ghi(db, p, user=None):
    """Ghi (hoặc lấy lại) tờ đề nghị thu của phiếu. Bên kế toán chưa có SO thì số theo phiếu lúc này."""
    t, pl = noi_dung(db, p)
    mo_ta = "Đề nghị thu cước phiếu %s · %s → %s" % (p.doc_no, p.origin or "", p.destination or "")
    c = cua(db, p)
    if c is not None:
        if not _co_so(db, p):
            c.tien, c.tien_te, c.tien_lak, c.mo_ta = t["doanh_thu"], t["ccy"], t["doanh_thu_lak"], mo_ta
            c.doi_tuong_ten = p.customer_name
            c.payload = json.dumps(pl, ensure_ascii=False, default=str)
        return c
    return CT.ghi(db, LOAI, nguon_bang="trips", nguon_id=p.id, trip=p, ngay=(p.locked_at.date() if p.locked_at else None),
                  doi_tuong_loai="khach", doi_tuong_ten=p.customer_name, tien=t["doanh_thu"], tien_te=t["ccy"],
                  tien_lak=t["doanh_thu_lak"], by_user=getattr(user, "full_name", None), mo_ta=mo_ta, payload=pl)


def rut(db, p):
    """Mở khoá phiếu → rút tờ khi bên kế toán CHƯA có SO của DO (có SO thì tờ là căn cứ của SO đó, giữ). Trả số tờ đã rút.
    Cờ `da_day` (trang tạm đã kéo tờ về) không còn ý nghĩa từ 01/10."""
    if _co_so(db, p):
        return 0
    return (db.query(ChungTu).filter(ChungTu.loai == LOAI, ChungTu.nguon_bang == "trips", ChungTu.nguon_id == p.id)
            .delete(synchronize_session=False))


def trang_thai(p, c, so=None):
    """Một chữ cho cột trạng thái: cho_khoa · chua_lap · cho_gui · da_tao_so · thu_mot_phan · da_thu.
    `so` = lần gửi SO (GuiSoTune) của phiếu; thu tiền theo bản đọc lại từ hệ anh Tune."""
    if not p.locked:
        return "cho_khoa"
    if so is not None and so.status == "synced":
        if so.thu_trang_thai == "da_thu":
            return "da_thu"
        if so.thu_trang_thai == "thu_mot_phan":
            return "thu_mot_phan"
        return "da_tao_so"
    if c is None:
        return "chua_lap"
    return "cho_gui"


# ================================================================ đọc thu tiền bên hệ anh Tune — chỉ xem
def _cong_no_khach(db, k, ep=False):
    """customer-detail của một khách (chi_tune.cong_no_khach đã dịch gọn) — nhớ GIU_GIAY giây theo khách."""
    from services import chi_tune as CHI
    v = _DOC.get(k.id)
    if v and not ep and time.time() - v[0] < GIU_GIAY:
        return v[1]
    kq = CHI.cong_no_khach(db, k)
    _DOC[k.id] = (time.time(), kq)
    return kq


def ap_thu(so, no, don):
    """Một SO: dòng nợ có cùng OrderCode → số đã thu / còn nợ. Không còn trong danh sách nợ (bên đó chỉ liệt kê chứng từ còn nợ)
    mà vẫn có trong đơn hàng của khách → đã thu đủ. Không thấy ở cả hai → khong_thay (giữ "đã tạo SO")."""
    d = next((x for x in no if (x.get("so") or "") == so.order_code), None)
    if d is not None:
        so.thu_tong, so.thu_da_thu, so.thu_con_no = d.get("tien"), d.get("da_tra"), d.get("con_no")
        con, da = float(d.get("con_no") or 0), float(d.get("da_tra") or 0)
        so.thu_trang_thai = "da_thu" if con <= LECH else ("thu_mot_phan" if da > LECH else "chua_thu")
    else:
        o = next((x for x in don if (x.get("so") or "") == so.order_code), None)
        if o is not None:
            so.thu_tong = so.thu_da_thu = o.get("tien")
            so.thu_con_no, so.thu_trang_thai = 0.0, "da_thu"
        else:
            so.thu_trang_thai = so.thu_trang_thai or "khong_thay"
    so.thu_doc_luc, so.thu_loi = dt.datetime.utcnow(), None


TAI_CHINH = {"chua_thu": "unpaid", "thu_mot_phan": "partial", "da_thu": "paid"}


def doc_thu_tune(db, cac_so, ep=False):
    """Đọc lại thu tiền của các SO (GuiSoTune đã synced) từ hệ anh Tune, theo từng khách. Ghi bản đọc vào gui_so_tune.thu_* và
    trips.finance_status; KHÔNG commit (người gọi commit). Trả {"da_doc": số SO, "loi": câu lỗi | None}.
    Bên kia không vào được thì dừng ở khách đầu tiên hỏng, ghi lỗi lên các SO của khách đó, giữ số đọc lần trước."""
    so = [b for b in cac_so if b is not None and b.status == "synced" and b.order_code and b.trip_id]
    if not so:
        return {"da_doc": 0, "loi": None}
    trip = {p.id: p for p in db.query(Trip).filter(Trip.id.in_({b.trip_id for b in so})).all()}
    theo_khach = {}
    for b in so:
        p = trip.get(b.trip_id)
        if p is not None and p.customer_id:
            theo_khach.setdefault(p.customer_id, []).append(b)
    da, loi = 0, None
    for kid, ds in theo_khach.items():
        k = db.get(Customer, kid)
        try:
            kq = _cong_no_khach(db, k, ep) if k is not None else None
        except HTTPException as e:
            loi = (e.detail or {}).get("loi") if isinstance(e.detail, dict) else str(e.detail)
            for b in ds:
                b.thu_loi = loi
            break
        if kq is None:                                  # khách chưa có mã bên kế toán: không có SO nào bên đó để đọc
            continue
        for b in ds:
            cu = (b.thu_trang_thai, b.thu_da_thu, b.thu_con_no)
            ap_thu(b, kq.get("no") or [], kq.get("don") or [])
            p = trip[b.trip_id]
            if b.thu_trang_thai in TAI_CHINH:
                p.finance_status = TAI_CHINH[b.thu_trang_thai]
            if (b.thu_trang_thai, b.thu_da_thu, b.thu_con_no) != cu:
                p.updated_at = dt.datetime.utcnow()     # số thu đổi: chạm phiếu để bộ đệm báo cáo tháng tính lại
            da += 1
    return {"da_doc": da, "loi": loi}
