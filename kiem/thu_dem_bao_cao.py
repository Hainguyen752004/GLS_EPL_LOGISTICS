# -*- coding: utf-8 -*-
"""BỘ ĐỆM BÁO CÁO: dữ liệu đổi thì báo cáo PHẢI đổi ngay, gọi lại ra y hệt, ghép theo ngày = tính thẳng — chạy trên d7, KHÔNG ghi gì.

    python kiem/thu_dem_bao_cao.py          DB bản sao máy thử (.may_thu/url_epl_lao_d7.txt; tệp khác: biến EPL_KIEM_URL)

06/10: trước đây chạy trên epl_lao_tai, sửa một dòng chi THẬT rồi commit trả lại. Nay chạy trong tiến trình trên d7 (8011 đang dùng
để bấm tay) qua kiem/_d7_trong_gd.py: mọi ghi nằm trong giao dịch, cuối bài ROLLBACK; chỉ ghi phiếu THỬ bài tự tạo ở hai tháng
không có phiếu thật (mặc định 2020-02 · 2020-01), không sửa / xoá dòng đang có. Gộp thêm hai phần còn giá trị của
thu_bao_cao_cu_moi.py và thu_danh_muc_cu_moi.py (đã chuyển vào kiem/loi_thoi/):

  B. (chỉ đọc, tháng có phiếu mới nhất của d7) mỗi báo cáo × vai admin · yard · rev gọi hai lần → lần hai (bộ đệm) y hệt lần đầu;
     dòng tổng Theo dõi ghép theo NGÀY = cách tính cả tháng một lượt (_theo_doi_tong_tinh) với sáu bộ lọc.
  C. (chỉ đọc) tất toán tài xế: tinh_ky_lo (cả danh sách một lần) = tinh_ky từng tài xế; bảng tháng ghép theo ngày = tinh_ky.
  A. (phiếu thử, ROLLBACK) 1. tổng quan tính rồi lấy lại từ bộ đệm, y hệt · 2. mất bộ nhớ (như khởi động lại) → lấy bản lưu trong
     DB · 3. sửa +10 lít một dòng dầu → tổng chi tháng đổi đúng phần chênh · 4. tháng trước không tính lại · 5. trả về như cũ → về
     đúng số · 6. xoá hàng loạt rồi huỷ → phiên bản không đổi · 7. đổi ngày phiếu sang tháng trước → cả hai tháng tính lại ·
     8. một lần thu (trip_payments) → khoá 'thu' tăng.
"""
import datetime as dt
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _d7_trong_gd import dong, mo  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

GD = mo()
db = GD.db

from fastapi import Response  # noqa: E402
from sqlalchemy import func  # noqa: E402
from models import Driver, Trip, TripExpense, TripPayment  # noqa: E402
import routes.bao_cao as B  # noqa: E402
import routes.tat_toan as TT  # noqa: E402
from services import dem_bao_cao as DEM  # noqa: E402

NAY, TRUOC = os.environ.get("EPL_KIEM_THANG", "2020-02"), None
_y, _m = int(NAY[:4]), int(NAY[5:])
TRUOC = "%04d-%02d" % (_y - (_m == 1), (_m - 2) % 12 + 1)
DEM_SAI = []


class Vai:
    def __init__(self, role="admin"):
        self.role, self.driver_id, self.full_name, self.place_id = role, None, role, None


def phai(dk, cau):
    print(("  ✓ " if dk else "  ✗ ") + cau, flush=True)
    if not dk:
        DEM_SAI.append(cau)


def chuan(x, so=6):
    if isinstance(x, float):
        return round(x, so)
    if isinstance(x, dict):
        return {k: chuan(v, so) for k, v in x.items()}
    if isinstance(x, list):
        return [chuan(v, so) for v in x]
    return x


def goi(f):
    try:
        r = chuan(json.loads(json.dumps(f(), default=str)))
    except Exception as e:  # noqa: BLE001 — cả hai lần cùng bị chặn (403) là khớp
        r = ("LỖI", type(e).__name__, getattr(e, "status_code", None))
    db.rollback()
    return r


# ================================================================ B. chỉ đọc — gọi lại y hệt, dòng tổng theo ngày = cả tháng
def phan_b(thang):
    print("B. Chỉ đọc, tháng %s của d7 — gọi lại (bộ đệm) ra y hệt; dòng tổng Theo dõi theo ngày = cả tháng" % thang, flush=True)
    for vai in ("admin", "yard", "rev"):
        u = Vai(vai)
        viec = [("tong-quan", lambda: B.tong_quan(thang=thang, db=db, user=u)),
                ("xu-huong", lambda: B.xu_huong(thang=thang, db=db, user=u)),
                ("can-tru", lambda: B.can_tru(thang=thang, db=db, user=u)),
                ("theo-doi", lambda: B.theo_doi(response=Response(), thang=thang, trang=1, co=None, db=db, user=u)),
                ("xe-lien-ket", lambda: B.xe_lien_ket(thang=thang, db=db, user=u)),
                ("tien-tai-xe", lambda: B.tien_tai_xe(thang=thang, db=db, user=u))]
        for ten, f in viec:
            t0 = time.perf_counter(); a = goi(f); t1 = time.perf_counter() - t0
            t0 = time.perf_counter(); b = goi(f); t2 = time.perf_counter() - t0
            nhan = "chặn %s" % a[2] if isinstance(a, tuple) else "%.2f s → %.2f s" % (t1, t2)
            phai(a == b, "%-6s · %-11s gọi lại y hệt (%s)" % (vai, ten, nhan))
    u = Vai("admin")
    dau, cuoi = B._thang(thang)
    for loc in ({}, {"quy": "LAK"}, {"quy": "USD"}, {"company": "joint"}, {"transport_status": "arrived"}, {"q": "G4"}):
        a = goi(lambda: B._theo_doi_tong_tinh(db, dau, cuoi, loc.get("q"), loc.get("transport_status"), None, loc.get("company"), loc.get("quy")))
        b = goi(lambda: B.theo_doi_tong(thang=thang, q=loc.get("q"), transport_status=loc.get("transport_status"), finance_status=None,
                                        company=loc.get("company"), quy=loc.get("quy"), db=db, user=u))
        phai(a == b, "dòng tổng Theo dõi theo ngày = cả tháng · lọc %s" % json.dumps(loc))


# ================================================================ C. chỉ đọc — tất toán theo lô / theo ngày = từng tài xế
def phan_c(ky):
    print("C. Chỉ đọc, kỳ %s — tất toán tài xế: theo lô / ghép theo ngày = tính từng tài xế" % ky, flush=True)
    tx = db.query(Driver).filter(Driver.active.is_(True)).order_by(Driver.driver_code, Driver.name).all()
    sap = lambda d: sorted([dict(x, phieu=sorted(x["phieu"], key=lambda p: p["trip_id"])) for x in d], key=lambda x: x["driver_id"])  # noqa: E731
    a = sap(chuan(json.loads(json.dumps([TT.tinh_ky(db, t, ky) for t in tx], default=str)), 4)); db.rollback()
    b = sap(chuan(json.loads(json.dumps(TT.tinh_ky_lo(db, tx, ky), default=str)), 4)); db.rollback()
    phai(a == b, "tinh_ky_lo (cả %d tài xế một lần) = tinh_ky từng tài xế" % len(tx))
    cu = [{k: v for k, v in x.items() if k != "phieu"} for x in a]
    m = sorted(chuan(json.loads(json.dumps(TT.bang_thang(db, ky), default=str)), 4), key=lambda x: x["driver_id"]); db.rollback()
    phai(cu == m, "bảng tất toán tháng (ghép theo ngày, bộ đệm) = tinh_ky từng tài xế")


# ================================================================ A. phiếu thử — dữ liệu đổi thì báo cáo đổi ngay (ROLLBACK)
def tq(thang):
    t0 = time.perf_counter()
    r = B.tong_quan(thang=thang, db=db, user=Vai())
    db.rollback()
    return r, time.perf_counter() - t0


def phan_a():
    print("A. Phiếu thử ở %s · %s (trong giao dịch, ROLLBACK cuối bài)" % (NAY, TRUOC), flush=True)
    d0 = dt.date(_y - (_m == 1), (_m - 2) % 12 + 1, 1)
    d2 = dt.date(_y + (_m == 12), _m % 12 + 1, 1)
    co = db.query(func.count(Trip.id)).filter(Trip.doc_date >= d0, Trip.doc_date < d2).scalar()
    db.rollback()
    if co:
        raise SystemExit("DỪNG: tháng %s / %s đã có %d phiếu thật trên d7 — chọn tháng khác: EPL_KIEM_THANG=YYYY-MM" % (TRUOC, NAY, co))
    duoi = uuid.uuid4().hex[:8]
    p1 = Trip(doc_no="THU-DEM-%s-1" % duoi, kind="gom", doc_date=dt.date(_y, _m, 10), company="EPL", transport_status="arrived",
              customer_name="THU-DEM", note="bộ kiểm thu_dem_bao_cao — ROLLBACK")
    p2 = Trip(doc_no="THU-DEM-%s-2" % duoi, kind="gom", doc_date=dt.date(d0.year, d0.month, 20), company="EPL",
              transport_status="arrived", customer_name="THU-DEM", note="bộ kiểm thu_dem_bao_cao — ROLLBACK")
    db.add_all([p1, p2]); db.flush()
    e1 = TripExpense(trip_id=p1.id, section="fuel", line_no=1, item_key="diesel", qty=5, unit_price=1000, currency="LAK", paid_by_epl=True)
    e2 = TripExpense(trip_id=p2.id, section="fuel", line_no=1, item_key="diesel", qty=3, unit_price=1000, currency="LAK", paid_by_epl=True)
    db.add_all([e1, e2]); db.commit()

    DEM.xoa_het()                                     # chỉ bộ nhớ — bản lưu của d7 không đụng
    a, t1 = tq(NAY)
    b, t2 = tq(NAY)
    phai(a == b and t2 < t1, "gọi lại tổng quan %s lấy từ bộ đệm: %.3f s → %.3f s, y hệt" % (NAY, t1, t2))
    DEM.xoa_het()                                     # như khởi động lại máy chủ: mất bộ nhớ, bản trong DB còn
    b, t3 = tq(NAY)
    phai(a == b and t3 < t1, "mất bộ nhớ → lấy lại bản đã lưu trong DB: %.3f s (tính lần đầu %.3f s), y hệt" % (t3, t1))
    p_truoc, _ = tq(TRUOC)

    e = db.get(TripExpense, e1.id)
    e.qty = e.qty + 10
    db.commit()
    c, t4 = tq(NAY)
    phai(c.get("chi_lak", 0) - a.get("chi_lak", 0) == 10 * 1000,
         "sửa +10 lít dòng dầu → tổng chi %s tăng đúng 10.000 LAK (%s → %s, tính lại %.3f s)" % (NAY, a.get("chi_lak"), c.get("chi_lak"), t4))
    q2, t5 = tq(TRUOC)
    phai(q2 == p_truoc and t5 < 0.5, "tháng trước %s KHÔNG tính lại (%.3f s), số y nguyên" % (TRUOC, t5))

    e = db.get(TripExpense, e1.id)
    e.qty = 5
    db.commit()
    f, _ = tq(NAY)
    phai(f == a, "trả dòng dầu về như cũ → tổng quan về đúng số ban đầu")

    pb0 = DEM.phien_ban(db, [NAY]); db.rollback()
    db.query(TripExpense).filter(TripExpense.id == "__khong_co__").delete(synchronize_session=False)
    db.rollback()
    pb1 = DEM.phien_ban(db, [NAY]); db.rollback()
    phai(pb0 == pb1, "xoá hàng loạt rồi HUỶ giao dịch → số phiên bản không đổi")

    pb_nay, pb_truoc = DEM.phien_ban(db, [NAY]), DEM.phien_ban(db, [TRUOC]); db.rollback()
    p = db.get(Trip, p1.id)
    ngay_cu = p.doc_date
    p.doc_date = dt.date(d0.year, d0.month, 15)
    db.commit()
    doi = DEM.phien_ban(db, [NAY]) != pb_nay and DEM.phien_ban(db, [TRUOC]) != pb_truoc; db.rollback()
    phai(doi, "đổi ngày phiếu thử sang tháng trước → cả %s và %s đều tính lại" % (NAY, TRUOC))
    p = db.get(Trip, p1.id)
    p.doc_date = ngay_cu
    db.commit()
    g, _ = tq(NAY)
    phai(g == a, "trả ngày phiếu về như cũ → tổng quan %s về đúng số ban đầu" % NAY)

    ct0 = DEM.phien_ban(db, [NAY, "thu"]); db.rollback()
    x = TripPayment(trip_id=p2.id, pay_date=d0, amount=1, currency="LAK", rate_to_lak=1, amount_lak=1, method="offset",
                    ref="THU-DEM", by_user="thu")
    db.add(x); db.commit()
    ct1 = DEM.phien_ban(db, [NAY, "thu"]); db.rollback()
    phai(ct0 != ct1, "ghi một lần thu vào phiếu tháng trước → khoá 'thu' tăng → báo cáo đọc lần thu tính lại")


def main():
    try:
        mx = db.query(func.max(Trip.doc_date)).scalar()
        db.rollback()
        thang = (mx or dt.date.today()).strftime("%Y-%m")
        phan_b(thang)
        phan_c(thang)
        phan_a()                                       # phần ghi để cuối — giữ khoá (trong giao dịch) ngắn nhất
    finally:
        dong(GD)
    if DEM_SAI:
        print("\n❌ %d mục sai" % len(DEM_SAI))
        sys.exit(1)
    print("\n✅ BỘ ĐỆM BÁO CÁO: dữ liệu đổi là báo cáo đổi ngay; gọi lại / ghép theo ngày / theo lô ra đúng số tính thẳng")


if __name__ == "__main__":
    main()
