# -*- coding: utf-8 -*-
"""BỘ ĐỆM BÁO CÁO: sửa dữ liệu thì báo cáo PHẢI đổi ngay — không bao giờ hiện số cũ.

    python kiem/thu_dem_bao_cao.py [db]          mặc định epl_lao_tai (DB thử tải). KHÔNG chạy trên epl_lao thật:
                                                  bài sửa một dòng chi rồi trả lại như cũ.

  1. Gọi tổng quan tháng này → lưu; gọi lại → lấy từ bộ đệm (nhanh, y hệt).
  2. Sửa số lượng MỘT dòng chi của một phiếu tháng này, commit → tổng quan tháng này ĐỔI đúng bằng phần chênh.
  3. Tháng khác (tháng trước) KHÔNG bị tính lại (vẫn từ bộ đệm), số không đổi.
  4. Trả dòng chi về như cũ → tổng quan về đúng số ban đầu.
  5. Xoá hàng loạt (query().delete()) trong một giao dịch rồi HUỶ → số phiên bản không tăng (huỷ là không có gì đổi).
  6. Sửa ngày phiếu sang tháng trước → CẢ HAI tháng tính lại; trả ngày về như cũ.
"""
import datetime as dt
import os
import re
import sys
import time

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = sys.argv[1] if len(sys.argv) > 1 else "epl_lao_tai"
if DB == "epl_lao":
    raise SystemExit("Bài này sửa rồi trả lại một dòng chi — không chạy trên DB thật epl_lao.")
u = re.search(r"^DATABASE_URL\s*=\s*(\S+)", open(os.path.join(GOC, ".env"), encoding="utf-8").read(), re.M).group(1).strip("\"'")
os.environ["DATABASE_URL"] = u.rsplit("/", 1)[0] + "/" + DB
os.environ["EPL_LAO_CHAM_MS"] = "999999"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))

from database import SessionLocal  # noqa: E402
from models import Trip, TripExpense  # noqa: E402
import routes.bao_cao as B  # noqa: E402
from services import dem_bao_cao as DEM  # noqa: E402


class Vai:
    role, driver_id, full_name, place_id = "admin", None, "admin", None


def tq(db, thang):
    t0 = time.perf_counter()
    r = B.tong_quan(thang=thang, db=db, user=Vai())
    db.rollback()
    return r, time.perf_counter() - t0


def phai(dk, cau):
    print(("✓ " if dk else "✗ ") + cau, flush=True)
    if not dk:
        raise SystemExit(1)


def main():
    db = SessionLocal()
    nay = dt.date.today().strftime("%Y-%m")
    y, m = int(nay[:4]), int(nay[5:])
    truoc = "%04d-%02d" % (y - (m == 1), (m - 2) % 12 + 1)
    DEM.xoa_het(db)
    a, t1 = tq(db, nay)
    b, t2 = tq(db, nay)
    phai(a == b and t2 < t1, "gọi lại tổng quan %s lấy từ bộ đệm: %.2f s → %.3f s, y hệt" % (nay, t1, t2))
    DEM.xoa_het()                            # như khởi động lại máy chủ: mất bộ nhớ, bản trong DB còn
    b, t2 = tq(db, nay)
    phai(a == b and t2 < t1 / 3, "khởi động lại máy chủ (mất bộ nhớ) → lấy lại bản đã tính trong DB: %.3f s, y hệt" % t2)
    p_truoc, _ = tq(db, truoc)

    dau = dt.date(y, m, 1)
    d = (db.query(TripExpense).join(Trip, Trip.id == TripExpense.trip_id)
         .filter(Trip.doc_date >= dau, Trip.company != "joint", TripExpense.currency == "LAK",
                 TripExpense.unit_price > 0, TripExpense.section == "fuel").first())
    phai(d is not None, "có dòng chi dầu (LAK) của phiếu xe nhà tháng này để thử")
    cu_qty = d.qty
    d.qty = (d.qty or 0) + 10
    db.commit()
    c, t3 = tq(db, nay)
    chenh = round(10 * d.unit_price)
    phai(c["chi_lak"] - a["chi_lak"] == chenh,
         "sửa +10 lít một dòng dầu → tổng chi tháng này tăng đúng %s LAK (tính lại %.2f s)" % (f"{chenh:,}", t3))
    q2, t4 = tq(db, truoc)
    phai(q2 == p_truoc and t4 < 0.5, "tháng trước %s KHÔNG tính lại (%.3f s), số y nguyên" % (truoc, t4))

    d = db.get(TripExpense, d.id)
    d.qty = cu_qty
    db.commit()
    e, _ = tq(db, nay)
    phai(e == a, "trả dòng chi về như cũ → tổng quan về đúng số ban đầu")

    pb0 = DEM.phien_ban(db, [nay]); db.rollback()
    db.query(TripExpense).filter(TripExpense.id == "__khong_co__").delete(synchronize_session=False)
    db.rollback()
    pb1 = DEM.phien_ban(db, [nay]); db.rollback()
    phai(pb0 == pb1, "xoá hàng loạt rồi HUỶ giao dịch → số phiên bản không đổi")

    p = db.query(Trip).filter(Trip.doc_date >= dau).first()
    ngay_cu = p.doc_date
    pb_nay, pb_truoc = DEM.phien_ban(db, [nay]), DEM.phien_ban(db, [truoc])
    p.doc_date = dt.date(y - (m == 1), (m - 2) % 12 + 1, 15)
    db.commit()
    phai(DEM.phien_ban(db, [nay]) != pb_nay and DEM.phien_ban(db, [truoc]) != pb_truoc,
         "đổi ngày phiếu %s sang tháng trước → cả tháng %s và %s đều tính lại" % (p.doc_no, nay, truoc))
    p = db.get(Trip, p.id)
    p.doc_date = ngay_cu
    db.commit()
    f, _ = tq(db, nay)
    phai(f == a, "trả ngày phiếu về như cũ → tổng quan tháng này về đúng số ban đầu")
    # khoá riêng: một lần thu (trip_payments) làm cấn trừ tính lại, dù lần thu đó thuộc phiếu tháng khác
    from models import TripPayment
    ct0 = DEM.phien_ban(db, [nay, "thu"]); db.rollback()
    p = db.query(Trip).filter(Trip.doc_date < dau).first()
    x = TripPayment(trip_id=p.id, pay_date=dt.date.today(), amount=1, currency="LAK", rate_to_lak=1, amount_lak=1,
                    method="offset", ref="THU-DEM", by_user="thu")
    db.add(x); db.commit()
    ct1 = DEM.phien_ban(db, [nay, "thu"]); db.rollback()
    db.delete(db.get(TripPayment, x.id)); db.commit()
    phai(ct0 != ct1, "ghi một lần thu vào phiếu tháng trước → khoá 'thu' tăng → cấn trừ tháng này tính lại")
    print("\n✅ BỘ ĐỆM BÁO CÁO: dữ liệu đổi là báo cáo đổi ngay; tháng không đụng tới thì dùng lại")


if __name__ == "__main__":
    main()
