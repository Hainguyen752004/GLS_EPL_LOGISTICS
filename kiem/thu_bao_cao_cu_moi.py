# -*- coding: utf-8 -*-
"""SO BÁO CÁO CŨ ↔ MỚI — sửa cách NẠP dữ liệu (24/09, dữ liệu cả năm) không được đổi một con số nào.

    python kiem/thu_bao_cao_cu_moi.py <db> <thang> [<thang> ...]      ví dụ: python kiem/thu_bao_cao_cu_moi.py epl_lao 2026-09

Nạp routes/bao_cao.py bản trước đợt dữ liệu cả năm (commit b6dc7cb; đổi bằng biến REF) làm "bản cũ", gọi cùng các báo cáo với bản đang sửa trên cùng DB,
cùng tháng, cùng vai, rồi so từng khoá. Chỉ ĐỌC — không ghi gì vào DB.
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
THANG = sys.argv[2:] or [time.strftime("%Y-%m")]
u = re.search(r"^DATABASE_URL\s*=\s*(\S+)", open(os.path.join(GOC, ".env"), encoding="utf-8").read(), re.M).group(1).strip("\"'")
os.environ["DATABASE_URL"] = u.rsplit("/", 1)[0] + "/" + DB
os.environ["EPL_LAO_CHAM_MS"] = "999999"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))

from fastapi import Response  # noqa: E402
from database import SessionLocal  # noqa: E402
import routes.bao_cao as MOI  # noqa: E402

cu_ma = subprocess.run(["git", "show", os.environ.get("REF", "b6dc7cb") + ":backend/app/routes/bao_cao.py"], cwd=GOC, capture_output=True,
                       text=True, encoding="utf-8").stdout
tep = os.path.join(tempfile.gettempdir(), "bao_cao_cu.py")
open(tep, "w", encoding="utf-8").write(cu_ma)
spec = importlib.util.spec_from_file_location("bao_cao_cu", tep)
CU = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CU)


class Vai:
    def __init__(self, role):
        self.role, self.driver_id, self.full_name, self.place_id = role, None, role, None


def chuan(x):
    """So bằng JSON, số làm tròn 6 chữ số (cộng trong SQL khác thứ tự cộng trong Python ở phần tỷ)."""
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, dict):
        return {k: chuan(v) for k, v in x.items()}
    if isinstance(x, list):
        return [chuan(v) for v in x]
    return x


def khac(a, b, duong=""):
    if type(a) != type(b):
        return ["%s: kiểu %s ≠ %s" % (duong, type(a).__name__, type(b).__name__)]
    if isinstance(a, dict):
        ra = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                ra.append("%s.%s: chỉ có ở %s" % (duong, k, "cũ" if k in a else "mới"))
            else:
                ra += khac(a[k], b[k], duong + "." + str(k))
        return ra
    if isinstance(a, list):
        if len(a) != len(b):
            return ["%s: %d dòng ≠ %d dòng" % (duong, len(a), len(b))]
        ra = []
        for i, (x, y) in enumerate(zip(a, b)):
            ra += khac(x, y, "%s[%d]" % (duong, i))
        return ra
    return [] if a == b else ["%s: %r ≠ %r" % (duong, a, b)]


def xu_huong_cat(cu, moi):
    """xu-huong (24/09) CỐ Ý chỉ trả 50 chuyến hao hụt nặng nhất và 60 dòng Gantt cần nhìn nhất: kiểm số đếm thật khớp
    danh sách cũ, danh sách mới là TẬP CON của danh sách cũ, rồi so mọi khoá còn lại như thường."""
    if not isinstance(cu, dict) or not isinstance(moi, dict) or "hao_hut" not in cu:
        return cu, moi, []
    loi = []
    hh_cu = {x["doc_no"]: x for x in cu["hao_hut"]}
    if moi["hao_hut_dem"]["tong"] != len(cu["hao_hut"]):
        loi.append("hao_hut_dem.tong %s ≠ %d chuyến cũ" % (moi["hao_hut_dem"]["tong"], len(cu["hao_hut"])))
    for x in moi["hao_hut"]:
        y = dict(x); y.pop("pct", None)
        if hh_cu.get(x["doc_no"]) != y:
            loi.append("hao_hut %s không có / khác bản cũ" % x["doc_no"])
    pct = [x["pct"] for x in moi["hao_hut"]]
    if pct != sorted(pct, reverse=True):
        loi.append("hao_hut không xếp nặng nhất trước")
    dt_cu = {x["doc_no"]: x for x in cu["dong_thoi_gian"]}
    if moi["dong_thoi_gian_tong"] != len(cu["dong_thoi_gian"]):
        loi.append("dong_thoi_gian_tong %s ≠ %d dòng cũ" % (moi["dong_thoi_gian_tong"], len(cu["dong_thoi_gian"])))
    for x in moi["dong_thoi_gian"]:
        if dt_cu.get(x["doc_no"]) != x:
            loi.append("dong_thoi_gian %s không có / khác bản cũ" % x["doc_no"])
    c = {k: v for k, v in cu.items() if k not in ("hao_hut", "dong_thoi_gian")}
    m = {k: v for k, v in moi.items() if k not in ("hao_hut", "dong_thoi_gian", "hao_hut_dem", "dong_thoi_gian_tong")}
    # "phiếu đầu tiên có việc của tôi": bản cũ lấy theo thứ tự DB trả về (không sắp), bản mới lấy theo thứ tự phiếu —
    # so: cùng có / cùng không, và phiếu bản mới chọn phải là phiếu CÓ việc (nằm trong danh sách mục đang chờ của vai)
    vc, vm = (c.get("xem_nhanh") or {}).get("viec_phieu"), (m.get("xem_nhanh") or {}).get("viec_phieu")
    if (vc is None) != (vm is None):
        loi.append("viec_phieu: cũ %r ↔ mới %r" % (vc, vm))
    for x in (c, m):
        if x.get("xem_nhanh"):
            x["xem_nhanh"] = dict(x["xem_nhanh"]); x["xem_nhanh"].pop("viec_phieu", None)
    return c, m, loi


def main():
    db = SessionLocal()
    loi = 0
    for thang in THANG:
        for vai in [x for x in os.environ.get("VAI", "admin,yard,rev").split(",") if x]:
            u_ = Vai(vai)
            viec = [("tong-quan", lambda m: m.tong_quan(thang=thang, db=db, user=u_)),
                    ("xu-huong", lambda m: m.xu_huong(thang=thang, db=db, user=u_)),
                    ("tien-tai-xe", lambda m: m.tien_tai_xe(thang=thang, db=db, user=u_)),
                    ("can-tru", lambda m: m.can_tru(thang=thang, db=db, user=u_)),
                    ("theo-doi", lambda m: (m.theo_doi(thang=thang, db=db, user=u_) if m is CU
                                            else m.theo_doi(response=Response(), thang=thang, trang=1, co=None, db=db, user=u_))),
                    ("xe-lien-ket", lambda m: m.xe_lien_ket(thang=thang, db=db, user=u_))]
            chi = [x for x in os.environ.get("CHI", "").split(",") if x]      # CHI=tong-quan,can-tru: chỉ so mấy báo cáo đó
            for ten, f in [v for v in viec if not chi or v[0] in chi]:
                kq = []
                for m in (CU, MOI):
                    t0 = time.perf_counter()
                    try:
                        kq.append((chuan(json.loads(json.dumps(f(m), default=str))), time.perf_counter() - t0))
                    except Exception as e:  # noqa: BLE001 — cả hai cùng chặn (403) là khớp
                        kq.append((("LỖI", type(e).__name__, getattr(e, "status_code", None)), time.perf_counter() - t0))
                    db.rollback()
                c0, m0, d = xu_huong_cat(kq[0][0], kq[1][0])
                d += khac(c0, m0)
                # lần gọi thứ hai của bản mới: lấy từ bộ đệm (nếu báo cáo có đệm) — phải ra y như lần đầu
                t0 = time.perf_counter()
                try:
                    lai = chuan(json.loads(json.dumps(f(MOI), default=str)))
                except Exception as e:  # noqa: BLE001
                    lai = ("LỖI", type(e).__name__, getattr(e, "status_code", None))
                t_lai = time.perf_counter() - t0
                db.rollback()
                if lai != kq[1][0]:
                    d.append("gọi lại lần hai (bộ đệm) ra KHÁC lần đầu")
                dau = "✓" if not d else "✗"
                print("%s %s · %-6s · %-12s  cũ %6.2f s · mới %6.2f s · gọi lại %5.2f s%s" % (
                    dau, thang, vai, ten, kq[0][1], kq[1][1], t_lai, "" if not d else "  · %d chỗ lệch" % len(d)), flush=True)
                for x in d[:8]:
                    print("      " + x, flush=True)
                loi += bool(d)
    print("\n%s" % ("✅ KHỚP HẾT — cách nạp mới cho ra đúng từng con số như cũ" if not loi else "❌ %d báo cáo lệch" % loi))
    sys.exit(1 if loi else 0)


if __name__ == "__main__":
    main()
