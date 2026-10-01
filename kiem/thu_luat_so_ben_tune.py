# -*- coding: utf-8 -*-
"""Chạy LUẬT KIỂM của bên anh Tune trên gói tạo SO của MỌI DO đã khoá — không gọi sang máy bên đó, không ghi DB.

    python kiem/thu_luat_so_ben_tune.py            (DATABASE_URL trỏ DB thử)

Luật chép từ mã nguồn anh Tune (đọc 01/10/2026, nhánh feat/DemoLao):
  * GLS-QLSX-APIs/Backend.API/Modules/Sales/Sales/Application/LogisticsPushValidator.cs
  * GLS-QLSX-APIs/Backend.API/Database/Scripts/20260911_logistics_sales_push.sql (sp_Logistics_CreateSalesOrder)
Khách chưa có mã bên kế toán thì dùng tạm mã thử 37 ký tự (dài nhất được phép) để kiểm phần còn lại của gói.
"""
import json
import os
import re
import sys
from decimal import Decimal

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
sys.path.insert(0, GOC)
os.chdir(GOC)

from fastapi import HTTPException  # noqa: E402

from database import SessionLocal  # noqa: E402
from models import Trip  # noqa: E402
from services import ban_giao as BG  # noqa: E402
from services import gui_tune as GT  # noqa: E402

MA = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
KEY = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}\Z")
LOI = []


class Sai(Exception):
    pass


def chuoi(o, k):
    v = o.get(k)
    if not isinstance(v, str) or not v.strip():
        raise Sai("Thiếu chuỗi %s." % k)
    return v


def ma(o, k, dai):
    v = chuoi(o, k)
    if len(v) > dai or not MA.match(v):
        raise Sai("%s sai định dạng mã hoặc vượt %d ký tự." % (k, dai))
    return v


def tien(o, k):
    v = o.get(k)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise Sai("%s phải là số JSON." % k)
    d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
    if d < 0 or d > Decimal("9999999999999") or round(d, 5) != d:
        raise Sai("%s phải là số không âm trong decimal(18,5)." % k)
    return d


def luat_tune(than_json, khoa):
    """= LogisticsPushValidator.Validate + phần kiểm đầu của sp_Logistics_CreateSalesOrder."""
    if not KEY.match(khoa):
        raise Sai("IDEMPOTENCY_KEY_REQUIRED")
    if len(than_json.encode("utf-8")) > 1048576:
        raise Sai("RequestSizeLimit 1 MiB")
    b = json.loads(than_json, object_pairs_hook=_khong_trung)
    if not isinstance(b, dict) or set(b) - {"schemaVersion", "header", "details"}:
        raise Sai("Chỉ gửi schemaVersion, header, details.")
    if b.get("schemaVersion") != 1 or isinstance(b.get("schemaVersion"), bool):
        raise Sai("schemaVersion phải bằng 1.")
    h = b.get("header")
    if not isinstance(h, dict):
        raise Sai("Thiếu object header.")
    ma(h, "do_id", 100)
    kh = ma(h, "customer_id", 50)
    r = h.get("route")
    if not isinstance(r, dict):
        raise Sai("Thiếu object route.")
    tuyen = ma(r, "id", 50)
    if len("%s_%s" % (kh, tuyen)) > 50:
        raise Sai("Mã ghép customer_id_route.id vượt varchar(50).")
    if chuoi(h, "status") != "delivered":
        raise Sai("Chỉ nhận DO delivered.")
    cur = chuoi(h, "currency_thu")
    if cur not in ("VND", "LAK", "USD") or chuoi(h, "currency") != cur:
        raise Sai("Tổng bán hỗ trợ VND, LAK, USD; currency phải cùng currency_thu.")
    tong = tien(h, "final_selling_price")
    if tong <= Decimal("0.01"):
        raise Sai("Tổng bán phải lớn hơn 0.01.")
    if tien(h, "selling_price") + tien(h, "customer_surcharge_total") != tong:
        raise Sai("Tổng bán không khớp giá bán + phụ thu khách.")
    ds = b.get("details")
    if not isinstance(ds, list) or not ds:
        raise Sai("details phải có ít nhất một dòng.")
    thu, so = Decimal(0), set()
    for d in ds:
        n = d.get("line_no") if isinstance(d, dict) else None
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0 or n in so:
            raise Sai("line_no phải dương và duy nhất.")
        so.add(n)
        loai = chuoi(d, "kind")
        if loai not in ("thu", "chi"):
            raise Sai("kind phải là thu hoặc chi.")
        st = tien(d, "actual_amount")
        if loai == "thu":
            if chuoi(d, "currency") != cur:
                raise Sai("Dòng thu phải cùng loại tiền Tổng bán.")
            thu += st
    if thu != tong:
        raise Sai("Tổng actual_amount các dòng thu không khớp final_selling_price.")
    # phần SQL: tên tuyến cắt 200, mô tả mặt hàng ghép từ các dòng
    if r.get("name") is not None and not isinstance(r.get("name"), str):
        raise Sai("route.name phải là chuỗi.")
    return "%s_%s" % (kh, tuyen), tong, cur


def _khong_trung(cap):
    ra = {}
    for k, v in cap:
        if k in ra:
            raise Sai("Thuộc tính JSON bị trùng: %s." % k)
        ra[k] = v
    return ra


def main():
    db = SessionLocal()
    goc_ma = BG._ma_khach
    tam = "KIEM-" + "X" * (GT.MA_KHACH_TOI_DA - 5)
    try:
        BG._ma_khach = lambda db_, p: goc_ma(db_, p) or tam
        ps = (db.query(Trip).filter(Trip.locked.is_(True), Trip.transport_status == "arrived")
              .order_by(Trip.doc_no).all())
        print("%d DO đã về, đã khoá" % len(ps))
        dat = 0
        for p in ps:
            try:
                body, tom = GT.dung_goi(db, p)
            except HTTPException as e:
                d = e.detail if isinstance(e.detail, dict) else {}
                print("  · %-18s bên em chặn trước: %s — %s" % (p.doc_no, d.get("ma"), (d.get("loi") or "")[:90]))
                continue
            than = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
            try:
                hang, tong, cur = luat_tune(than, GT.khoa(tom["do_id"]))
                dat += 1
                print("  ✓ %-18s qua luật bên anh Tune · %s %s · mặt hàng %s (%d ký tự)"
                      % (p.doc_no, _gon(tong), cur, hang[:20] + "…", len(hang)))
            except Sai as e:
                LOI.append("%s: %s" % (p.doc_no, e))
                print("  SAI %-16s %s" % (p.doc_no, e))
        print("\n%d/%d gói qua luật bên anh Tune" % (dat, len(ps)))
    finally:
        BG._ma_khach = goc_ma
        db.close()
    print("ĐẠT hết" if not LOI else "SAI %d gói:\n  - %s" % (len(LOI), "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


def _gon(d):
    return format(d.normalize(), "f")


if __name__ == "__main__":
    main()
