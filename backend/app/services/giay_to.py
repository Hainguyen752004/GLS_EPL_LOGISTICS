# -*- coding: utf-8 -*-
"""Cửa chặn GIẤY TỜ khi xếp xe vào phiếu (20/10, anh Hải chọn bổ sung theo EPL_System: «Điều phối chặn tài xế không đủ bằng lái»).

Trước đây màn Tài xế đã xét «đủ điều kiện» nhưng phiếu xuất xe vẫn chọn được tài xế hết hạn bằng, xe hết hạn đăng kiểm / bảo hiểm.

Luật BẰNG LÁI = luật màn Tài xế (frontend/modules/tai-xe/tai-xe.js ketLuan) — hai nơi phải khớp:
  thiếu bằng · bằng không hiệu lực (treo / thu hồi) · hết hạn tại ngày phiếu · lệch hạng (hạng trên hồ sơ ≠ hạng trên bằng) → CHẶN;
  còn ≤ NGUONG_TX ngày → nhắc.
Luật XE = ngưỡng màn Xe (frontend/modules/xe/xe.js NGUONG_GIAY_TO): hạn đăng kiểm, bảo hiểm, giấy phép lưu hành / phù hiệu của đầu kéo
và rơ-moóc đang lắp — quá hạn tại ngày phiếu → CHẶN; còn ≤ NGUONG_XE ngày → nhắc. Hạn để trống (chưa khai) thì không chặn — chỉ chặn điều
đã biết là sai.
Sếp (admin) lưu được dù vướng, phải ghi lý do — vào nhật ký phiếu (routes/phieu.py).
"""
import datetime as dt

from fastapi import HTTPException

from models import Driver, Trailer, Vehicle

NGUONG_TX = 60
NGUONG_XE = 30


def _ngay(v):
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _han(ten, doi_tuong, giay, han, ngay, nguong):
    """Một hạn giấy tờ → mục chặn / nhắc / None."""
    h = _ngay(han)
    if h is None:
        return None
    con = (h - ngay).days
    if con < 0:
        return {"muc": "chan", "doi_tuong": doi_tuong, "ten": ten, "giay": giay, "ly_do": "het_han", "han": h.isoformat(), "con_ngay": con}
    if con <= nguong:
        return {"muc": "nhac", "doi_tuong": doi_tuong, "ten": ten, "giay": giay, "ly_do": "sap_het", "han": h.isoformat(), "con_ngay": con}
    return None


def tai_xe(d, ngay):
    """Kết luận bằng lái của một tài xế tại ngày phiếu → danh sách mục (rỗng = đủ điều kiện)."""
    if d is None:
        return []
    ten = d.name or ""
    if not (d.license_no or "").strip():
        return [{"muc": "chan", "doi_tuong": "tai_xe", "ten": ten, "giay": "bang_lai", "ly_do": "thieu"}]
    if (d.license_status or "active") != "active":
        return [{"muc": "chan", "doi_tuong": "tai_xe", "ten": ten, "giay": "bang_lai", "ly_do": "khong_hieu_luc",
                 "trang_thai": d.license_status}]
    m = _han(ten, "tai_xe", "bang_lai", d.license_valid_to, ngay, NGUONG_TX)
    if m and m["muc"] == "chan":
        return [m]
    if d.license_class_hr and d.license_type and d.license_class_hr.strip().upper() != d.license_type.strip().upper():
        return [{"muc": "chan", "doi_tuong": "tai_xe", "ten": ten, "giay": "bang_lai", "ly_do": "lech_hang",
                 "hang_ho_so": d.license_class_hr, "hang_bang": d.license_type}]
    return [m] if m else []


def xe(x, rm, ngay):
    """Hạn giấy tờ đầu kéo + rơ-moóc đang lắp tại ngày phiếu → danh sách mục."""
    ra = []
    if x is not None:
        for giay, han in (("dang_kiem", x.inspection_exp), ("bao_hiem", x.insurance_exp), ("phu_hieu", x.road_permit_exp)):
            m = _han(x.truck_no or "", "dau_keo", giay, han, ngay, NGUONG_XE)
            if m:
                ra.append(m)
    if rm is not None:
        for giay, han in (("dang_kiem", rm.inspection_exp), ("bao_hiem", rm.insurance_exp)):
            m = _han(rm.plate or "", "ro_mooc", giay, han, ngay, NGUONG_XE)
            if m:
                ra.append(m)
    return ra


def kiem(db, vehicle_id, driver_id, ngay=None):
    """{"ngay", "chan": [...], "nhac": [...]} cho xe + tài xế tại ngày phiếu (trống = hôm nay)."""
    ngay = _ngay(ngay) or dt.date.today()
    x = db.get(Vehicle, vehicle_id) if vehicle_id else None
    rm = db.get(Trailer, x.trailer_id) if x is not None and x.trailer_id else None
    d = db.get(Driver, driver_id) if driver_id else None
    ds = xe(x, rm, ngay) + tai_xe(d, ngay)
    return {"ngay": ngay.isoformat(), "chan": [m for m in ds if m["muc"] == "chan"], "nhac": [m for m in ds if m["muc"] == "nhac"]}


def chan(db, vehicle_id, driver_id, ngay, user, bo_qua=None):
    """Chặn lưu khi xe / tài xế vướng giấy tờ tại ngày phiếu. Sếp (admin) gửi kèm lý do (`bo_qua`) thì cho qua → trả lý do để ghi nhật
    ký; không vướng → None."""
    kq = kiem(db, vehicle_id, driver_id, ngay)
    if not kq["chan"]:
        return None
    ly_do = str(bo_qua or "").strip()
    if ly_do and getattr(user, "role", None) == "admin":
        return ly_do[:300]
    raise HTTPException(422, {"ma": "GIAY_TO_CHUA_DU",
                              "loi": "Tài xế hoặc xe chưa đủ giấy tờ tại ngày phiếu (xem dòng đỏ dưới ô Xe / Tài xế). Gia hạn ở màn Tài xế / Xe, "
                                     "hoặc nhờ Sếp lưu kèm lý do.",
                              "giay_to": kq})
