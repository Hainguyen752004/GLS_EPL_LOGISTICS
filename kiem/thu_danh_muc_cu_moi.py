# -*- coding: utf-8 -*-
"""SO DANH MỤC CŨ ↔ MỚI — nạp theo lô (24/09, dữ liệu cả năm) không được đổi một con số nào.

    python kiem/thu_danh_muc_cu_moi.py <db> [<ky> ...]          ví dụ: python kiem/thu_danh_muc_cu_moi.py epl_lao 2026-09

So bản trước đợt dữ liệu cả năm (commit b6dc7cb; đổi bằng biến REF) với bản đang sửa, trên cùng DB, cho: danh sách chủ xe (kèm tiền chờ trả), nhà cung cấp
(phát sinh · ghi nợ · đã trả), hoá đơn gộp (danh sách · chờ gộp), tài xế (xe mặc định · nơi cấp bằng · phiếu đang chạy), phiếu lĩnh đang chờ, và bảng
tất toán tháng — tinh_ky_lo (mới, cả danh sách một lần) so với tinh_ky (từng tài xế, như cũ). Chỉ ĐỌC.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = sys.argv[1] if len(sys.argv) > 1 else "epl_lao"
KY = sys.argv[2:] or [time.strftime("%Y-%m")]
u = re.search(r"^DATABASE_URL\s*=\s*(\S+)", open(os.path.join(GOC, ".env"), encoding="utf-8").read(), re.M).group(1).strip("\"'")
os.environ["DATABASE_URL"] = u.rsplit("/", 1)[0] + "/" + DB
os.environ["EPL_LAO_CHAM_MS"] = "999999"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))

from fastapi import Response  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import Driver  # noqa: E402
import routes.chu_xe as CX  # noqa: E402
import routes.danh_muc as DM  # noqa: E402
import routes.nha_cung_cap as NCC  # noqa: E402
import routes.phieu_linh as PL  # noqa: E402
import routes.tat_toan as TT  # noqa: E402
import routes.hoa_don as HD  # noqa: E402


def ban_cu(duong, ten):
    ma = subprocess.run(["git", "show", os.environ.get("REF", "b6dc7cb") + ":" + duong], cwd=GOC, capture_output=True, text=True, encoding="utf-8").stdout
    tep = os.path.join(tempfile.gettempdir(), ten + "_cu.py")
    open(tep, "w", encoding="utf-8").write(ma)
    spec = importlib.util.spec_from_file_location(ten + "_cu", tep)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Vai:
    def __init__(self, role, driver_id=None):
        self.role, self.driver_id, self.full_name, self.place_id = role, driver_id, role, None


class Yeu:
    base_url = "http://thu/"


def chuan(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: chuan(v) for k, v in x.items()}
    if isinstance(x, list):
        return [chuan(v) for v in x]
    return x


def so(ten, a, b, ta, tb, sap=None):
    a, b = chuan(json.loads(json.dumps(a, default=str))), chuan(json.loads(json.dumps(b, default=str)))
    if sap:
        a, b = sap(a), sap(b)
    ok = a == b
    print("%s %-34s cũ %6.2f s · mới %6.2f s" % ("✓" if ok else "✗", ten, ta, tb), flush=True)
    if not ok:
        if isinstance(a, list) and isinstance(b, list):
            print("      %d dòng ↔ %d dòng" % (len(a), len(b)))
            for x, y in zip(a, b):
                if x != y:
                    for k in sorted(set(x) | set(y)):
                        if x.get(k) != y.get(k):
                            print("      %s: %r ≠ %r" % (k, x.get(k), y.get(k)))
                    break
        else:
            print("      %r\n      %r" % (str(a)[:300], str(b)[:300]))
    return ok


def do(f):
    t0 = time.perf_counter()
    r = f()
    return r, time.perf_counter() - t0


def main():
    db = SessionLocal()
    HDc = ban_cu("backend/app/routes/hoa_don.py", "hoa_don")
    CXc, DMc, NCCc, PLc = (ban_cu("backend/app/routes/chu_xe.py", "chu_xe"), ban_cu("backend/app/routes/danh_muc.py", "danh_muc"),
                           ban_cu("backend/app/routes/nha_cung_cap.py", "nha_cung_cap"), ban_cu("backend/app/routes/phieu_linh.py", "phieu_linh"))
    loi = 0
    for vai in ("admin", "yard"):
        u_ = Vai(vai)
        (a, ta), (b, tb) = do(lambda: CXc.ds_chu_xe(db=db, user=u_)), do(lambda: CX.ds_chu_xe(db=db, user=u_))
        db.rollback(); loi += not so("chủ xe · %s" % vai, a, b, ta, tb, sap=lambda d: [dict(x, so_xe=sorted(x["so_xe"])) for x in d])
        (a, ta), (b, tb) = do(lambda: NCCc.ds(db=db, user=u_)), do(lambda: NCC.ds(db=db, user=u_))
        db.rollback(); loi += not so("nhà cung cấp · %s" % vai, a, b, ta, tb)
        (a, ta), (b, tb) = do(lambda: PLc.ds_cho_cap(request=Yeu(), db=db, user=u_)), do(lambda: PL.ds_cho_cap(request=Yeu(), response=Response(), db=db, user=u_))
        db.rollback(); loi += not so("phiếu lĩnh chờ · %s" % vai, a, b, ta, tb)
    (a, ta), (b, tb) = do(lambda: DMc.ds_tai_xe(db=db, _=None)), do(lambda: DM.ds_tai_xe(db=db, _=None))
    db.rollback(); loi += not so("tài xế", a, b, ta, tb)
    ke = Vai("rev")
    (a, ta), (b, tb) = do(lambda: HDc.ds_hoa_don(period="", customer_id="", db=db, user=ke)), do(lambda: HD.ds_hoa_don(period="", customer_id="", db=db, user=ke))
    db.rollback(); loi += not so("hoá đơn gộp · mọi tháng", a, b, ta, tb)
    for ky in KY:
        (a, ta), (b, tb) = do(lambda: HDc.cho_gop(period=ky, customer_id="", db=db, user=ke)), do(lambda: HD.cho_gop(period=ky, customer_id="", db=db, user=ke))
        db.rollback(); loi += not so("hoá đơn · chờ gộp %s" % ky, a, b, ta, tb)
    tx = db.query(Driver).filter(Driver.active.is_(True)).order_by(Driver.driver_code, Driver.name).all()
    for ky in KY:
        (a, ta) = do(lambda: [TT.tinh_ky(db, t, ky) for t in tx])
        (b, tb) = do(lambda: TT.tinh_ky_lo(db, tx, ky))
        db.rollback()
        sap = lambda d: [dict(x, phieu=sorted(x["phieu"], key=lambda p: p["trip_id"])) for x in d]
        loi += not so("tất toán %s (%d tài xế)" % (ky, len(tx)), a, b, ta, tb, sap=sap)
    print("\n%s" % ("✅ KHỚP HẾT — nạp theo lô cho ra đúng từng con số như cũ" if not loi else "❌ %d mục lệch" % loi))
    sys.exit(1 if loi else 0)


if __name__ == "__main__":
    main()
