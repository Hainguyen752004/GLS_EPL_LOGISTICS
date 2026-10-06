# -*- coding: utf-8 -*-
"""ĐO BÁO CÁO ĐÚNG NHƯ NGOÀI ĐỜI — bộ đệm đang có, rồi có người GHI vào phiếu hôm nay, rồi có người mở báo cáo.

    python kiem/do_bao_cao_that.py [db]          mặc định epl_lao_tai (DB thử). Sửa +1 lít một dòng dầu phiếu HÔM NAY
                                                  rồi trả về như cũ — không chạy trên epl_lao thật.

In ra thời gian mở từng báo cáo: (1) lúc bộ đệm đã có · (2) ngay sau một lần ghi vào phiếu hôm nay · (3) mở lại lần nữa.

DB / cách chạy (ghi 06/10): công cụ ĐO, chạy trong tiến trình. DB = tên truyền vào, mặc định epl_lao_tai (DB thử tải, dữ liệu một năm
gieo bằng tools/gieo_tai_thu.py) trên cùng máy PostgreSQL với DATABASE_URL trong .env (chỉ thay tên DB). GHI THẬT: +1 lít một dòng
dầu phiếu ngày mới nhất, COMMIT, đo, rồi trả về — chỉ chạy trên DB thử tải khi không ai dùng; không chạy trên epl_lao, epl_lao_d7
(8011 bấm tay) hay DB dùng chung. Kiểm đúng / sai của bộ đệm: kiem/thu_dem_bao_cao.py (d7, ROLLBACK).
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

from fastapi import Response  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import Trip, TripExpense  # noqa: E402
import routes.bao_cao as B  # noqa: E402
import routes.nha_cung_cap as N  # noqa: E402
import routes.tat_toan as TT  # noqa: E402


class Vai:
    role, driver_id, full_name, place_id = "admin", None, "admin", None


BAO_CAO = [("Tổng quan", lambda db: B.tong_quan(thang=None, db=db, user=Vai())),
           ("Xu hướng (6 tháng)", lambda db: B.xu_huong(thang=None, db=db, user=Vai())),
           ("Tiền chuyến tài xế", lambda db: B.tien_tai_xe(thang=None, db=db, user=Vai())),
           ("Cấn trừ", lambda db: B.can_tru(thang=None, db=db, user=Vai())),
           ("Theo dõi · dòng tổng", lambda db: B.theo_doi_tong(thang=None, db=db, user=Vai())),
           ("Tất toán", lambda db: TT.bang_thang(db, __import__("datetime").date.today().strftime("%Y-%m"))),
           ("Nhà cung cấp (cả 4 năm)", lambda db: N.ds(db=db, user=Vai()))]


def mo_het(db, nhan):
    out = []
    for ten, f in BAO_CAO:
        t0 = time.perf_counter(); f(db); db.rollback()
        out.append(time.perf_counter() - t0)
    print("%-34s " % nhan + " · ".join("%s %.2f s" % (t, x) for (t, _), x in zip(BAO_CAO, out)), flush=True)
    return out


def main():
    db = SessionLocal()
    print("DB %s · %d phiếu\n" % (DB, db.query(Trip).count()), flush=True)
    mo_het(db, "(0) làm nóng nếu còn thiếu")
    mo_het(db, "(1) bộ đệm đã có")
    from sqlalchemy import func
    hom_nay = db.query(func.max(Trip.doc_date)).scalar() or dt.date.today()   # ngày gần nhất có phiếu (ngày đang bị ghi)
    d = (db.query(TripExpense).join(Trip, Trip.id == TripExpense.trip_id)
         .filter(Trip.doc_date == hom_nay, TripExpense.section == "fuel", TripExpense.unit_price > 0).first())
    if d is None:
        raise SystemExit("không có dòng dầu nào của phiếu hôm nay để thử")
    cu = d.qty
    d.qty = (d.qty or 0) + 1; db.commit()
    try:
        mo_het(db, "(2) ngay sau 1 lần ghi phiếu " + hom_nay.strftime("%d/%m"))
        mo_het(db, "(3) mở lại")
    finally:
        d = db.get(TripExpense, d.id); d.qty = cu; db.commit()
    print("\n(đã trả dòng dầu về như cũ)")


if __name__ == "__main__":
    main()
