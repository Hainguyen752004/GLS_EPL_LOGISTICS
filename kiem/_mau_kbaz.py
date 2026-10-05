# -*- coding: utf-8 -*-
"""Phụ trợ bài kiểm trên bản sao d7 (03/10–05/10).

  dung_mau(conn)    dựng hai phiếu mẫu THU-KBAZ-T1/EPL (xe thuê giao, 200 L dầu kho xuất bán 33.000, tạm ứng 3 dòng tiền mặt, chipping
                    ghi nợ NCC GL021020269) và THU-KBAZ-G1/EPL (xe nhà gom, tạm ứng 250.000 đã chi, dầu mua dọc đường 30 L tự chi) TRONG
                    giao dịch đang mở, từ kiem/mau_thu_kbaz.json (tách từ bản sao d7 trước lần dọn 02/10 22:12). Rollback cuối ca xoá luôn.
  chan_kho_qlsx()   bài cũ kiểm việc khác bằng bộ giả kho tạm: ghim KHO_NGUON=kho_tam và chặn mọi lời gọi thật sang kho QLSX anh Tune.
"""
import datetime as dt
import json
import os

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BANG = ("trips", "trip_sections", "trip_expenses", "trip_goods", "trip_events", "vouchers", "chi_tune", "chi_muc_tune", "gui_so_tune",
        "but_toan_cho")


def _gia_tri(cot, v):
    """Chữ trong bản dump (định dạng COPY) → giá trị theo kiểu cột."""
    from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric
    if v is None:
        return None
    k = cot.type
    if isinstance(k, Boolean):
        return v in ("t", "true", "1")
    if isinstance(k, Integer):
        return int(v)
    if isinstance(k, (Float, Numeric)):
        return float(v)
    if isinstance(k, DateTime):
        v = v.replace(" ", "T").split("+")[0]
        if "." in v:                                            # Python 3.10: phần lẻ giây phải đủ 6 chữ số
            v = v.split(".")[0] + "." + v.split(".")[1].ljust(6, "0")[:6]
        return dt.datetime.fromisoformat(v)
    if isinstance(k, Date):
        return dt.date.fromisoformat(v)
    return v


def dung_mau(conn):
    import models as M
    from sqlalchemy import text
    if conn.execute(text("select 1 from trips where doc_no = 'THU-KBAZ-T1/EPL'")).first():
        return
    mau = json.load(open(os.path.join(GOC, "kiem", "mau_thu_kbaz.json"), encoding="utf-8"))
    for ten in BANG:
        bang = M.Base.metadata.tables[ten]
        dong = [{c: _gia_tri(bang.c[c], v) for c, v in r.items() if c in bang.c} for r in mau.get(ten) or []]
        if dong:
            conn.execute(bang.insert(), dong)


def chan_kho_qlsx():
    os.environ["KHO_NGUON"] = "kho_tam"
    from services import kho_qlsx as KQ

    def _cam(*a, **k):
        raise AssertionError("bài kiểm không được gọi kho QLSX thật")
    KQ._goi = _cam
