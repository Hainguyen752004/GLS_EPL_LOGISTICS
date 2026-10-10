# -*- coding: utf-8 -*-
"""Thử BỘ LỌC KHOẢNG THỜI GIAN phía máy chủ (09/10/2026) — tham số `tu`, `den` (YYYY-MM-DD) của các đường màn «khoang» gọi.

    python kiem/thu_khoang_thoi_gian.py

Anh Khampla gửi ảnh phần mềm kế toán: lọc theo Năm · Tháng · Khoảng thời gian (frontend/js/khoang_thoi_gian.js). Các đường dưới đây
nhận thêm tu/den (services/khoang_ngay.py), GIỮ `thang` cho Web C# và chỗ khác:
    /api/bao-cao/tong-quan · /api/bao-cao/xu-huong · /api/bao-cao/theo-doi · /api/bao-cao/theo-doi/tong   (tối đa 366 ngày)
    /api/de-nghi-thu (+ POST /api/de-nghi-thu/cap-nhat) · /api/ho-so-do
Phải thấy, với mỗi đường:
  · khoảng TRỌN MỘT THÁNG ra y hệt `thang=` của tháng đó (cả gói trả về);
  · khoảng hẹp hơn (đầu tháng tới ngày có phiếu ở giữa) ra ÍT HƠN, và đúng bằng số phiếu đếm thẳng trong DB của khoảng đó;
  · tu > den → 422 KHOANG_SAI (kèm bản Lào / Anh) · ngày sai dạng → 422 NGAY_SAI · thiếu một đầu → 422 KHOANG_THIEU ·
    báo cáo quá 366 ngày → 422 KHOANG_DAI; cả năm (365 ngày) chạy được, cộng đúng bằng 12 tháng;
  · vẫn chạy với `thang` như cũ; phân quyền như cũ (tài xế 403 báo cáo; Bãi 403 đề nghị thu — chặn trước khi xét ngày);
  · xu-huong: kỳ trước của một tháng là tháng liền trước (số khớp tổng quan tháng đó), của khoảng 10 ngày (vắt qua đầu tháng) là
    10 ngày liền trước.

Khung như kiem/thu_quyen_phieu.py: TestClient trên bản sao _d7, một giao dịch ngoài, phiên chạy savepoint, cuối ROLLBACK — chỉ đọc.
Bộ đệm báo cáo (services/dem_bao_cao.lay_nhieu) thay bằng TÍNH THẲNG như kiem/_khung_tien_trinh.py: không đọc / ghi bảng bao_cao_dem
(bộ đệm ghi bằng kết nối riêng — lọt ra ngoài giao dịch, và giữ khoá dòng mà máy 8011 đang dùng cũng cần). Không gọi mạng.
"""
import calendar
import datetime as dt
import json
import os
import sys
import urllib.request

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["EPL_DANG_NHAP_GLS"] = "0"
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MANG = []


def _cam_mang(yc, *a, **k):
    MANG.append(getattr(yc, "full_url", str(yc)))
    raise OSError("bài kiểm không được gọi mạng ra ngoài")


urllib.request.urlopen = _cam_mang

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import dem_bao_cao as DEM                 # noqa: E402
from services import khoang_ngay as KN                  # noqa: E402

KQ = []


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))
    sys.stdout.flush()
    return bool(dk)


def _khong_dem(db, viec, theo_ngay=False, tinh_lo=None):
    """Thay DEM.lay_nhieu: tính thẳng, không đọc / ghi bao_cao_dem (như kiem/_khung_tien_trinh._khong_dem)."""
    kq = tinh_lo(list(range(len(viec)))) if tinh_lo is not None else [t() for _, _, t in viec]
    return [json.loads(json.dumps(v, default=str)) for v in kq]


def cuoi_thang(th):
    y, m = int(th[:4]), int(th[5:7])
    return "%s-%02d" % (th, calendar.monthrange(y, m)[1])


def ma(r):
    d = r.get("detail") if isinstance(r, dict) else None
    return d.get("ma", "") if isinstance(d, dict) else ""


def main():
    DEM.lay_nhieu = _khong_dem
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '5s'"))
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    TK = {}

    def goi(u, duong, method="GET", body=None):
        r = c.request(method, duong, json=body, headers={"Authorization": "Bearer " + TK[u]})
        try:
            return r.status_code, r.json(), r.headers
        except ValueError:
            return r.status_code, None, r.headers

    def dem_db(tu, den, *them):
        return conn.execute(text("SELECT count(*) FROM trips WHERE doc_date BETWEEN :a AND :b" + "".join(them)),
                            {"a": tu, "b": den}).scalar()
    try:
        for u in ("admin", "doanhthu", "thabok", "tx01"):
            TK[u] = c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"]

        # tháng nhiều phiếu nhất của d7 (báo cáo, hồ sơ DO) và tháng nhiều DO đã về / đã khoá nhất (đề nghị thu)
        th = conn.execute(text("SELECT to_char(doc_date, 'YYYY-MM') FROM trips WHERE doc_date IS NOT NULL "
                               "GROUP BY 1 ORDER BY count(*) DESC, 1 DESC LIMIT 1")).scalar()
        th2 = conn.execute(text("SELECT to_char(doc_date, 'YYYY-MM') FROM trips WHERE doc_date IS NOT NULL "
                                "AND (transport_status = 'arrived' OR locked) GROUP BY 1 ORDER BY count(*) DESC, 1 DESC LIMIT 1")).scalar()
        tu, den = th + "-01", cuoi_thang(th)
        n_thang = dem_db(tu, den)
        # khoảng HẸP: đầu tháng tới ngày có phiếu ở giữa — bỏ ra ít nhất một ngày có phiếu (d7 ít phiếu, dồn vài ngày đầu tháng 10)
        def hep(thang, *them):
            ngay = [r[0].isoformat() for r in conn.execute(text("SELECT DISTINCT doc_date FROM trips WHERE doc_date BETWEEN :a AND :b"
                                                                + "".join(them) + " ORDER BY 1"), {"a": thang + "-01", "b": cuoi_thang(thang)})]
            return ngay[max(0, len(ngay) // 2 - 1)], len(ngay) > 1
        tu_h = th + "-01"
        den_h, tach = hep(th)
        dung(n_thang > 0 and th2, "d7 có phiếu: tháng %s (%d phiếu) · tháng có DO đã về %s · khoảng hẹp %s – %s" % (th, n_thang, th2, tu_h, den_h))
        it_hon = (lambda x, y: x < y) if tach else (lambda x, y: x <= y)      # có từ hai ngày có phiếu thì khoảng hẹp phải ÍT HƠN hẳn

        print("== 0. services/khoang_ngay — kỳ trước")
        D = dt.date.fromisoformat
        dung(KN.ky_truoc(D("2026-09-01"), D("2026-09-30")) == (D("2026-08-01"), D("2026-08-31")), "tháng 9 → tháng 8")
        dung(KN.ky_truoc(D("2026-01-01"), D("2026-01-31")) == (D("2025-12-01"), D("2025-12-31")), "tháng 1 → tháng 12 năm trước")
        dung(KN.ky_truoc(D("2026-01-01"), D("2026-12-31")) == (D("2025-01-01"), D("2025-12-31")), "cả năm → năm trước")
        dung(KN.ky_truoc(D("2026-03-01"), D("2026-04-30")) == (D("2026-01-01"), D("2026-02-28")), "hai tháng → hai tháng liền trước")
        dung(KN.ky_truoc(D("2026-09-11"), D("2026-09-20")) == (D("2026-09-01"), D("2026-09-10")), "10 ngày → 10 ngày liền trước")
        dung(KN.khoang("", "") is None and KN.khoang(None, None) is None, "không gửi tu / den → None (route dùng thang)")

        print("== 1. /api/bao-cao/tong-quan")
        s1, a, _ = goi("admin", "/api/bao-cao/tong-quan?thang=" + th)
        s2, b, _ = goi("admin", "/api/bao-cao/tong-quan?tu=%s&den=%s" % (tu, den))
        dung(s1 == 200 and s2 == 200 and a == b, "khoảng trọn tháng %s = thang=%s (cả gói)" % (th, th), (a or {}).get("so_phieu"))
        dung(a and a["so_phieu"] == n_thang, "số phiếu tháng = đếm thẳng trong DB", (a or {}).get("so_phieu"))
        s, h, _ = goi("admin", "/api/bao-cao/tong-quan?tu=%s&den=%s" % (tu_h, den_h))
        dung(s == 200 and it_hon(h["so_phieu"], a["so_phieu"]) and h["so_phieu"] == dem_db(tu_h, den_h) and (h["tu"], h["den"]) == (tu_h, den_h),
             "khoảng hẹp: ít hơn, đúng số đếm thẳng, tu / den trả lại đúng", (h.get("so_phieu"), a["so_phieu"]))
        nam = th[:4]
        s, y, _ = goi("admin", "/api/bao-cao/tong-quan?tu=%s-01-01&den=%s-12-31" % (nam, nam))
        tong12 = sum(goi("admin", "/api/bao-cao/tong-quan?thang=%s-%02d" % (nam, m_))[1]["so_phieu"] for m_ in range(1, 13))
        dung(s == 200 and y["so_phieu"] == tong12 == dem_db(nam + "-01-01", nam + "-12-31"), "cả năm %s (365 ngày) = cộng 12 tháng" % nam,
             (y.get("so_phieu"), tong12))
        s, e, _ = goi("admin", "/api/bao-cao/tong-quan?tu=%s&den=%s" % (den, tu))
        dung(s == 422 and ma(e) == "KHOANG_SAI" and e["detail"].get("loi_lo") and e["detail"].get("loi_en"),
             "tu > den → 422 KHOANG_SAI, có bản Lào / Anh", e)
        s, e, _ = goi("admin", "/api/bao-cao/tong-quan?tu=2026-13-01&den=2026-12-31")
        dung(s == 422 and ma(e) == "NGAY_SAI" and e["detail"].get("loi_lo"), "tháng 13 → 422 NGAY_SAI", e)
        s, e, _ = goi("admin", "/api/bao-cao/tong-quan?tu=" + tu)
        dung(s == 422 and ma(e) == "KHOANG_THIEU" and e["detail"].get("loi_en"), "chỉ gửi tu → 422 KHOANG_THIEU", e)
        s, e, _ = goi("admin", "/api/bao-cao/tong-quan?tu=2025-01-01&den=2026-01-02")
        dung(s == 422 and ma(e) == "KHOANG_DAI" and e["detail"].get("loi_lo"), "quá 366 ngày → 422 KHOANG_DAI", e)
        s, e, _ = goi("tx01", "/api/bao-cao/tong-quan?tu=%s&den=%s" % (den, tu))
        dung(s == 403, "tài xế: 403 (phân quyền chặn trước khi xét ngày)", (s, ma(e)))
        s, e, _ = goi("thabok", "/api/bao-cao/tong-quan?tu=%s&den=%s" % (tu_h, den_h))
        dung(s == 200 and "doanh_thu_lak" not in e and "chi_lak" not in e, "Bãi xem được khoảng, vẫn không có tiền bán / tiền chi", sorted(e)[:6])

        print("== 2. /api/bao-cao/xu-huong")
        s1, a, _ = goi("admin", "/api/bao-cao/xu-huong?thang=" + th)
        s2, b, _ = goi("admin", "/api/bao-cao/xu-huong?tu=%s&den=%s" % (tu, den))
        dung(s1 == 200 and s2 == 200 and a == b, "khoảng trọn tháng = thang= (cả gói: theo ngày, xe, Gantt, sáu tháng…)",
             (a or {}).get("dong_thoi_gian_tong"))
        y_, m_ = int(th[:4]), int(th[5:7])
        truoc = "%04d-%02d" % (y_ - (m_ == 1), (m_ - 2) % 12 + 1)
        tq_truoc = goi("admin", "/api/bao-cao/tong-quan?thang=" + truoc)[1]
        dung(a["ky_truoc"] == {"tu": truoc + "-01", "den": cuoi_thang(truoc)}
             and all(a["thang_truoc"][k] == tq_truoc[k2] for k, k2 in (("doanh_thu_lak", "doanh_thu_lak"), ("chi_lak", "chi_lak"),
                                                                       ("tan_giao", "tan_giao"), ("chua_thu_lak", "chua_thu_lak"))),
             "kỳ trước của tháng %s = tháng %s, số khớp tổng quan tháng đó" % (th, truoc), a["ky_truoc"])
        d10 = D(den_h)                                           # 10 ngày kết thúc ở ngày giữa (thường vắt qua đầu tháng)
        t10, k1, k2 = (d10 - dt.timedelta(days=9)).isoformat(), (d10 - dt.timedelta(days=19)).isoformat(), (d10 - dt.timedelta(days=10)).isoformat()
        s, h, _ = goi("admin", "/api/bao-cao/xu-huong?tu=%s&den=%s" % (t10, den_h))
        dung(s == 200 and h["ky_truoc"] == {"tu": k1, "den": k2} and all(t10 <= x["ngay"] <= den_h for x in h["theo_ngay"])
             and h["dong_thoi_gian_tong"] == dem_db(t10, den_h),
             "10 ngày %s – %s: kỳ trước %s – %s, theo ngày trong khoảng, số chuyến đúng đếm thẳng" % (t10, den_h, k1, k2),
             (h.get("ky_truoc"), h.get("dong_thoi_gian_tong")))
        dung(h["sau_thang"]["nhan"] == a["sau_thang"]["nhan"], "sáu tháng gần nhất tính tới tháng của ngày cuối kỳ", h["sau_thang"]["nhan"])
        s, e, _ = goi("admin", "/api/bao-cao/xu-huong?tu=%s&den=%s" % (den, tu))
        dung(s == 422 and ma(e) == "KHOANG_SAI", "tu > den → 422", ma(e))

        print("== 3. /api/bao-cao/theo-doi + /tong")
        s1, a, h1 = goi("admin", "/api/bao-cao/theo-doi?thang=%s&co=500" % th)
        s2, b, h2 = goi("admin", "/api/bao-cao/theo-doi?tu=%s&den=%s&co=500" % (tu, den))
        dung(s1 == 200 and s2 == 200 and [x["id"] for x in a] == [x["id"] for x in b] and h1.get("x-tong") == h2.get("x-tong") == str(n_thang),
             "danh sách khoảng trọn tháng = thang= (cùng phiếu, cùng thứ tự, X-Tong)", h2.get("x-tong"))
        s, hh, h3 = goi("admin", "/api/bao-cao/theo-doi?tu=%s&den=%s&co=500" % (tu_h, den_h))
        dung(s == 200 and int(h3.get("x-tong")) == dem_db(tu_h, den_h) and it_hon(int(h3.get("x-tong")), n_thang)
             and all(tu_h <= x["doc_date"][:10] <= den_h for x in hh), "khoảng hẹp: X-Tong ít hơn = đếm thẳng, mọi dòng trong khoảng", h3.get("x-tong"))
        for loc in ("", "&transport_status=arrived", "&quy=LAK"):
            s1, a, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=%s%s" % (th, loc))
            s2, b, _ = goi("admin", "/api/bao-cao/theo-doi/tong?tu=%s&den=%s%s" % (tu, den, loc))
            dung(s1 == 200 and s2 == 200 and a == b, "dòng tổng khoảng trọn tháng = thang= (lọc «%s»)" % (loc or "không"), a.get("so_phieu"))
        s, b, _ = goi("admin", "/api/bao-cao/theo-doi/tong?tu=%s&den=%s" % (tu_h, den_h))
        dung(s == 200 and b["so_phieu"] == dem_db(tu_h, den_h), "dòng tổng khoảng hẹp = đếm thẳng", b.get("so_phieu"))
        s, e, _ = goi("admin", "/api/bao-cao/theo-doi?tu=%s&den=%s" % (den, tu))
        s2, e2, _ = goi("admin", "/api/bao-cao/theo-doi/tong?tu=%s&den=%s" % (den, tu))
        dung(s == 422 and s2 == 422 and ma(e) == ma(e2) == "KHOANG_SAI", "tu > den → 422 cả hai đường", (ma(e), ma(e2)))
        s, e, _ = goi("admin", "/api/bao-cao/theo-doi?tu=01/09/2026&den=2026-09-30")
        dung(s == 422 and ma(e) == "NGAY_SAI", "ngày dd/mm/yyyy → 422 NGAY_SAI", ma(e))
        s, e, _ = goi("tx01", "/api/bao-cao/theo-doi?tu=%s&den=%s" % (tu, den))
        dung(s == 403, "tài xế: 403 như cũ", s)

        print("== 4. /api/de-nghi-thu")
        tu2, den2 = th2 + "-01", cuoi_thang(th2)
        s1, a, _ = goi("doanhthu", "/api/de-nghi-thu?thang=" + th2)
        s2, b, _ = goi("doanhthu", "/api/de-nghi-thu?tu=%s&den=%s" % (tu2, den2))
        dung(s1 == 200 and s2 == 200 and a == b and len(a["ds"]) > 0, "khoảng trọn tháng %s = thang= (cả gói)" % th2, len((a or {}).get("ds") or []))
        dv = " AND (transport_status = 'arrived' OR locked)"
        den2h, tach2 = hep(th2, dv)
        n_dnt = dem_db(tu2, den2h, dv)
        s, h, _ = goi("doanhthu", "/api/de-nghi-thu?tu=%s&den=%s" % (tu2, den2h))
        dung(s == 200 and (len(h["ds"]) < len(a["ds"]) if tach2 else len(h["ds"]) <= len(a["ds"])) and len(h["ds"]) == min(n_dnt, 400)
             and all(tu2 <= x["doc_date"] <= den2h for x in h["ds"]) and (h["tu"], h["den"]) == (tu2, den2h),
             "khoảng hẹp %s – %s: ít hơn, đúng số DO đã về / đã khoá trong khoảng" % (tu2, den2h), (len(h["ds"]), n_dnt))
        s, e, _ = goi("doanhthu", "/api/de-nghi-thu?tu=%s&den=%s" % (den2, tu2))
        dung(s == 422 and ma(e) == "KHOANG_SAI", "tu > den → 422", ma(e))
        s, e, _ = goi("doanhthu", "/api/de-nghi-thu/cap-nhat", "POST", {"tu": den2, "den": tu2})
        dung(s == 422 and ma(e) == "KHOANG_SAI", "Cập nhật (POST) tu > den → 422, không gọi sang kế toán", ma(e))
        s, e, _ = goi("thabok", "/api/de-nghi-thu?tu=%s&den=%s" % (den2, tu2))
        dung(s == 403, "Bãi: 403 như cũ (chặn trước khi xét ngày)", (s, ma(e)))
        s, e, _ = goi("doanhthu", "/api/de-nghi-thu?thang=" + th2)
        dung(s == 200, "vẫn chạy với thang", s)

        print("== 5. /api/ho-so-do")
        s1, a, _ = goi("admin", "/api/ho-so-do?thang=" + th)
        s2, b, _ = goi("admin", "/api/ho-so-do?tu=%s&den=%s" % (tu, den))
        dung(s1 == 200 and s2 == 200 and a == b and len(a["ds"]) > 0, "khoảng trọn tháng = thang= (cả gói)", len((a or {}).get("ds") or []))
        s, h, _ = goi("admin", "/api/ho-so-do?tu=%s&den=%s" % (tu_h, den_h))
        dung(s == 200 and it_hon(len(h["ds"]), len(a["ds"])) and len(h["ds"]) == min(dem_db(tu_h, den_h), 400)
             and all(tu_h <= x["doc_date"] <= den_h for x in h["ds"]), "khoảng hẹp: ít hơn, đúng số DO", len(h["ds"]))
        s, e, _ = goi("admin", "/api/ho-so-do?tu=%s&den=%s" % (den, tu))
        dung(s == 422 and ma(e) == "KHOANG_SAI", "tu > den → 422", ma(e))
        s, e, _ = goi("tx01", "/api/ho-so-do?tu=%s&den=%s" % (tu, den))
        dung(s == 403, "tài xế: 403 như cũ", s)

        print("== 6. đường đã có tu / den từ trước: /api/trips · /api/but-toan-cho")
        s1, a, h1 = goi("admin", "/api/trips?thang=%s&co=1" % th)
        s2, b, h2 = goi("admin", "/api/trips?tu=%s&den=%s&co=1" % (tu, den))
        dung(s1 == s2 == 200 and h1.get("x-tong") == h2.get("x-tong"), "/api/trips: khoảng trọn tháng = thang=", h2.get("x-tong"))
        s1, a, _ = goi("admin", "/api/but-toan-cho?thang=" + th)
        s2, b, _ = goi("admin", "/api/but-toan-cho?tu=%s&den=%s" % (tu, den))
        dung(s1 == s2 == 200 and [x["id"] for x in a["ds"]] == [x["id"] for x in b["ds"]], "/api/but-toan-cho: khoảng trọn tháng = thang=",
             len(a["ds"]))
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("\n(đã ROLLBACK — bản sao d7 không đổi; lời gọi mạng bị chặn: %d)" % len(MANG))
    print("%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if KQ and all(KQ) and not MANG else 1)


if __name__ == "__main__":
    main()
