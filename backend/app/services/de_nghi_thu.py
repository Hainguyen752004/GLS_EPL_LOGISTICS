# -*- coding: utf-8 -*-
"""PHIẾU ĐỀ NGHỊ THU — ໃບສະເໜີຮັບເງິນ (sếp 30/09).

Bên mình chỉ làm logistics: phiếu của mình là phiếu ĐỀ NGHỊ. Đề nghị CHI đi theo từng bước của chuyến (tạm ứng, nhiên liệu,
chi các mục); đề nghị THU sinh MỘT lần khi DO xong — xe về, có biên bản giao nhận, kế toán Viêng Chăn KHOÁ phiếu. Tờ này gửi
sang bên công nợ (anh Tune) để bên đó lập SO, xuất hoá đơn và thu tiền khách. Bên mình không thu tiền, không ghi công nợ —
chỉ xem lại trạng thái bên đó chép sang (đã xuất hoá đơn, đã thu bao nhiêu).

Số tiền là CƯỚC của phiếu theo đúng tiền tệ của phiếu (USD / THB / LAK…), kèm số quy Kíp theo tỷ giá khoá trên phiếu.
Một phiếu một tờ (nguồn trips:<id>, loại PDT). Mở khoá phiếu → rút tờ chưa gửi; khoá lại → tờ mới theo số mới.
"""
import json

from models import ChungTu, TripAttachment, TripExpense
from services import chung_tu as CT
from services.tinh_toan import tinh_phieu, ty_gia

LOAI = "PDT"


def _dong(db, p):
    return db.query(TripExpense).filter(TripExpense.trip_id == p.id).all()


def noi_dung(db, p, dong=None):
    """(tính tiền của phiếu, payload tờ đề nghị thu)."""
    t = tinh_phieu(p, dong if dong is not None else _dong(db, p), p.collected_lak or 0)
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


def ghi(db, p, user=None):
    """Ghi (hoặc lấy lại) tờ đề nghị thu của phiếu. Tờ còn chưa gửi thì số theo phiếu lúc này."""
    t, pl = noi_dung(db, p)
    mo_ta = "Đề nghị thu cước phiếu %s · %s → %s" % (p.doc_no, p.origin or "", p.destination or "")
    c = cua(db, p)
    if c is not None:
        if not c.da_day:
            c.tien, c.tien_te, c.tien_lak, c.mo_ta = t["doanh_thu"], t["ccy"], t["doanh_thu_lak"], mo_ta
            c.doi_tuong_ten = p.customer_name
            c.payload = json.dumps(pl, ensure_ascii=False, default=str)
        return c
    return CT.ghi(db, LOAI, nguon_bang="trips", nguon_id=p.id, trip=p, ngay=(p.locked_at.date() if p.locked_at else None),
                  doi_tuong_loai="khach", doi_tuong_ten=p.customer_name, tien=t["doanh_thu"], tien_te=t["ccy"],
                  tien_lak=t["doanh_thu_lak"], by_user=getattr(user, "full_name", None), mo_ta=mo_ta, payload=pl)


def rut(db, p):
    """Mở khoá phiếu → rút tờ CHƯA gửi. Trả số tờ đã rút (0 hoặc 1)."""
    return (db.query(ChungTu).filter(ChungTu.loai == LOAI, ChungTu.nguon_bang == "trips", ChungTu.nguon_id == p.id,
                                     ChungTu.da_day.is_(False)).delete(synchronize_session=False))


def trang_thai(p, c):
    """Một chữ cho cột trạng thái: cho_khoa · chua_lap · cho_gui · da_gui · da_hoa_don · da_thu."""
    if not p.locked:
        return "cho_khoa"
    if p.finance_status == "paid":
        return "da_thu"
    if p.invoiced:
        return "da_hoa_don"
    if c is None:
        return "chua_lap"
    return "da_gui" if c.da_day else "cho_gui"
