# -*- coding: utf-8 -*-
"""20/10 — lập phiếu chặn xe / tài xế vướng giấy tờ (services/giay_to.py). Các bài chạy TRONG GIAO DỊCH (rollback lúc xong) mà không thử
chính luật giấy tờ thì gọi `cho_du` để xe, rơ-moóc đang lắp và tài xế bài dùng không vướng: hạn để trống (luật: chưa khai thì không chặn),
bằng còn hiệu lực, không lệch hạng. Chỉ đổi trong giao dịch của bài — không ghi gì vào DB khi bài rollback."""


def cho_du(db, M, xe=(), tai_xe=()):
    for x in xe:
        x.inspection_exp = x.insurance_exp = x.road_permit_exp = None
        rm = db.get(M.Trailer, x.trailer_id) if getattr(x, "trailer_id", None) else None
        if rm is not None:
            rm.inspection_exp = rm.insurance_exp = None
    for d in tai_xe:
        if not (d.license_no or "").strip():
            d.license_no = "THU-" + str(d.id)[-8:]
        d.license_status, d.license_valid_to, d.license_class_hr = "active", None, None
    db.flush()
