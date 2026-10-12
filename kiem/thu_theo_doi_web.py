# -*- coding: utf-8 -*-
"""Thử hai tham số mới của bảng Theo dõi phiếu cho màn Web C# (Việc 12a, 12/10/2026) — routes/bao_cao.py:

    python kiem/thu_theo_doi_web.py

  · GET /api/bao-cao/theo-doi?quy=LAK|USD… — mỗi dòng thêm khối "quy" (_quy_dong): số tiền quy theo tỷ giá khoá trên phiếu;
    cộng cả kỳ khớp dòng tổng /theo-doi/tong?quy= (cùng cách quy); tiền lạ → không có khối "quy"; Bãi (không thấy tiền bán) →
    doanh thu / lãi trong "quy" là None; không gửi quy → gói như cũ (trang điều xe cũ không đổi).
  · GET /api/bao-cao/theo-doi/tong?tu_tim=1 — kỳ trống → "gan" = tháng gần nhất có phiếu khớp bộ lọc (_thang_gan, như
    khoang_thoi_gian.js gan của màn cũ); kỳ có phiếu hoặc không gửi tu_tim → không có "gan".

Khung như kiem/thu_khoang_thoi_gian.py: TestClient trên bản sao _d7, một giao dịch ngoài, cuối ROLLBACK — chỉ đọc; bộ đệm báo cáo
tính thẳng; không gọi mạng.
"""
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

    def goi(u, duong):
        r = c.get(duong, headers={"Authorization": "Bearer " + TK[u]})
        try:
            return r.status_code, r.json(), r.headers
        except ValueError:
            return r.status_code, None, r.headers
    try:
        for u in ("admin", "thabok"):
            TK[u] = c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"]
        th = conn.execute(text("SELECT to_char(doc_date, 'YYYY-MM') FROM trips WHERE doc_date IS NOT NULL "
                               "GROUP BY 1 ORDER BY count(*) DESC, 1 DESC LIMIT 1")).scalar()
        dau, cuoi = conn.execute(text("SELECT to_char(min(doc_date), 'YYYY-MM'), to_char(max(doc_date), 'YYYY-MM') FROM trips")).one()
        print("== 0. dữ liệu: tháng nhiều phiếu %s · phiếu từ %s tới %s" % (th, dau, cuoi))

        print("== 1. quy từng dòng (?quy=)")
        s, cu, h = goi("admin", "/api/bao-cao/theo-doi?thang=%s&trang=1&co=20" % th)
        dung(s == 200 and cu and all("quy" not in r for r in cu) and h.get("x-tong"), "không gửi quy: gói như cũ, có X-Tong", h.get("x-tong"))
        for dich in ("LAK", "USD"):
            s, ds, _ = goi("admin", "/api/bao-cao/theo-doi?thang=%s&quy=%s" % (th, dich))
            s2, tong, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=%s&quy=%s" % (th, dich))
            dung(s == 200 and all((r.get("quy") or {}).get("ccy") == dich for r in ds), "quy=%s: mọi dòng có khối quy, ccy=%s" % (dich, dich), len(ds))
            # 12/10: DO chưa có cân cuối là TẠM TÍNH — không vào dòng tổng, cộng riêng ở tong.tam_tinh
            tam = lambda r: (r.get("tinh") or {}).get("tam_tinh")
            cong = sum((r["quy"].get("doanh_thu") or 0) for r in ds if not tam(r))
            cong_tam = sum((r["quy"].get("doanh_thu") or 0) for r in ds if tam(r))
            ky = (tong.get("doanh_thu") or {}).get(dich, 0)
            ky_tam = (tong.get("tam_tinh") or {}).get(dich, 0)
            sai = 1 + len(ds) * (0.5 if dich == "LAK" else 0.01)          # mỗi dòng làm tròn riêng
            dung(s2 == 200 and abs(cong - ky) <= sai, "quy=%s: cộng doanh thu các dòng ĐÃ CÓ CÂN CUỐI = dòng tổng /tong?quy=%s" % (dich, dich),
                 (round(cong, 2), ky))
            dung(abs(cong_tam - ky_tam) <= sai and tong.get("so_phieu_tam") == sum(1 for r in ds if tam(r)),
                 "quy=%s: dòng tạm tính (chưa có cân cuối) cộng riêng ở tam_tinh, đếm đúng so_phieu_tam" % dich,
                 (round(cong_tam, 2), ky_tam, tong.get("so_phieu_tam")))
            cung = [r for r in ds if (r.get("tinh") or {}).get("ccy") == dich and r["tinh"].get("doanh_thu") is not None]
            dung(all(abs(r["quy"]["doanh_thu"] - r["tinh"]["doanh_thu"]) < 0.011 for r in cung),
                 "quy=%s: dòng vốn tính bằng %s giữ nguyên số" % (dich, dich), len(cung))
        s, ds, _ = goi("admin", "/api/bao-cao/theo-doi?thang=%s&co=5&quy=xyz" % th)
        dung(s == 200 and all("quy" not in r for r in ds), "tiền lạ → không có khối quy", s)
        s, ds, _ = goi("thabok", "/api/bao-cao/theo-doi?thang=%s&co=10&quy=LAK" % th)
        dung(s == 200 and ds and all(r["quy"]["doanh_thu"] is None and r["quy"]["lai"] is None for r in ds),
             "Bãi: khối quy không có doanh thu / lãi", ds[0]["quy"] if ds else None)

        print("== 2. tháng gần nhất có phiếu (?tu_tim=1)")
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=%s&tu_tim=1" % th)
        dung(s == 200 and t["so_phieu"] > 0 and "gan" not in t, "kỳ có phiếu: không có gan", t.get("so_phieu"))
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=2019-01")
        dung(s == 200 and t["so_phieu"] == 0 and "gan" not in t, "không gửi tu_tim: không có gan", t)
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=2019-01&tu_tim=1")
        dung(s == 200 and t.get("gan") == dau, "kỳ trước mọi phiếu → tháng phiếu sớm nhất", t.get("gan"))
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=2099-12&tu_tim=1")
        dung(s == 200 and t.get("gan") == cuoi, "kỳ sau mọi phiếu → tháng phiếu muộn nhất", t.get("gan"))
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=2099-12&tu_tim=1&q=khong-co-phieu-nao-zzz")
        dung(s == 200 and t.get("gan") is None and "gan" in t, "bộ lọc không khớp phiếu nào → gan = None", t)
        jo = conn.execute(text("SELECT to_char(max(doc_date), 'YYYY-MM') FROM trips WHERE company = 'joint'")).scalar()
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?thang=2099-12&tu_tim=1&company=joint")
        dung(s == 200 and t.get("gan") == jo, "giữ bộ lọc khác (xe liên kết) khi tìm tháng", (t.get("gan"), jo))
        s, t, _ = goi("admin", "/api/bao-cao/theo-doi/tong?tu=2099-11-01&den=2099-12-31&tu_tim=1")
        dung(s == 200 and t.get("gan") == cuoi, "kỳ là khoảng ngày cũng tìm được", t.get("gan"))

        print("== 3. Tổng quan (?tu_tim=1, Việc 12b)")
        s, t, _ = goi("admin", "/api/bao-cao/tong-quan?thang=%s&tu_tim=1" % th)
        dung(s == 200 and t["so_phieu"] > 0 and "gan" not in t, "kỳ có phiếu: không có gan", t.get("so_phieu"))
        s, t, _ = goi("admin", "/api/bao-cao/tong-quan?thang=2099-12&tu_tim=1")
        dung(s == 200 and t["so_phieu"] == 0 and t.get("gan") == cuoi, "kỳ trống → tháng gần nhất có phiếu", t.get("gan"))
        s, t, _ = goi("admin", "/api/bao-cao/tong-quan?thang=2099-12")
        dung(s == 200 and "gan" not in t, "không gửi tu_tim: gói như cũ", sorted(t)[:6])
        s, t, _ = goi("thabok", "/api/bao-cao/tong-quan?thang=2019-01&tu_tim=1")
        dung(s == 200 and t.get("gan") == dau and "doanh_thu_lak" not in t, "Bãi: có gan, vẫn không có tiền bán", t.get("gan"))
        # 12/10: ô Doanh thu chỉ tính DO đã có cân cuối; DO chưa cân là tạm tính (tam_tinh_*), cộng riêng
        s, t, _ = goi("admin", "/api/bao-cao/tong-quan?thang=%s" % th)
        s2, ds, _ = goi("admin", "/api/bao-cao/theo-doi?thang=%s&quy=LAK" % th)
        that = sum(r["tinh"]["doanh_thu_lak"] for r in ds if not r["tinh"].get("tam_tinh"))
        tam = sum(r["tinh"]["doanh_thu_lak"] for r in ds if r["tinh"].get("tam_tinh"))
        dung(s == 200 and abs(t["doanh_thu_lak"] - that) <= 1 + len(ds) and abs(t["tam_tinh_lak"] - tam) <= 1 + len(ds)
             and t["tam_tinh_so"] == sum(1 for r in ds if r["tinh"].get("tam_tinh")),
             "Tổng quan: Doanh thu chỉ DO có cân cuối, tạm tính cộng riêng", (t["doanh_thu_lak"], round(that), t["tam_tinh_lak"], round(tam)))
        s, t, _ = goi("thabok", "/api/bao-cao/tong-quan?thang=%s" % th)
        s2, tg, _ = goi("thabok", "/api/bao-cao/theo-doi/tong?thang=%s" % th)
        dung(s == 200 and not any(k.startswith("tam_tinh") for k in t) and "tam_tinh" not in tg and "tam_con_lai" not in tg,
             "Bãi: không nhận số tạm tính (tiền bán)", [k for k in list(t) + list(tg) if k.startswith("tam")])

        print("== 4. quyền màn Theo dõi tuyến (/api/theo-doi/quyen, Việc 12c)")
        s, q, _ = goi("admin", "/api/theo-doi/quyen")
        dung(s == 200 and q["xac_nhan_diem"] and q["ghi_chu"] and q["bao_su_co"] and q["khai_sua"] and all(q["duyet"].values())
             and q["nhap_gia"] and q["xem_tien_ban"], "Sếp: làm được hết", q)
        s, q, _ = goi("thabok", "/api/theo-doi/quyen")
        dung(s == 200 and q["xac_nhan_diem"] and q["bao_su_co"] and not q["khai_sua"]
             and q["duyet"] == {"fuel": True, "repair": False, "other": True} and not q["nhap_gia"] and not q["xem_tien_ban"],
             "Bãi: tới điểm · ghi chú · báo sự cố; duyệt dầu dọc đường + chi khác; không khai sửa, không nhập tiền, không thấy cước", q)
        TK["ketoancp"] = c.post("/api/dang-nhap", json={"username": "ketoancp", "password": "1234"}).json()["token"]
        s, q, _ = goi("ketoancp", "/api/theo-doi/quyen")
        dung(s == 200 and not q["xac_nhan_diem"] and not q["bao_su_co"] and not any(q["duyet"].values()) and q["nhap_gia"],
             "KT Chi phí VC: không ghi diễn biến, không duyệt khai báo, có ô giá", q)
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
