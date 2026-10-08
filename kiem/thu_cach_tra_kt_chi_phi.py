# -*- coding: utf-8 -*-
"""Thử 08/10 (góp ý anh Khampla, chủ dự án chốt) — CÁCH TRẢ dòng chi mục IV / VI: Admin Thà Bốc (người lập phiếu) không quyết;
dòng mang mặc định (bộ gợi ý tuyến · khoản mục); KT Chi phí VC đổi lúc kiểm mục; Sếp đổi được. Kèm quyen.cach_tra cho màn Web.

    python kiem/thu_cach_tra_kt_chi_phi.py

Chạy trong một giao dịch trên bản sao _d7, cuối ROLLBACK — không ghi gì. Phiếu mẫu G4-0007-10/EPL (xe nhà, mục IV "đã nhập": x_food ·
x_phone mặc định chi ngay 625/1601, x_water · x_trip mặc định cùng lương 625/4201)."""
import os
import sys

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

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from routes import phieu as RP                          # noqa: E402

KQ = []
PHIEU, DA_KHOA = "ab65dc282091", "934aef04961a"


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    TK = {}

    def goi(u, method, duong, body=None):
        r = c.request(method, duong, json=body, headers={"Authorization": "Bearer " + TK[u]})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, None

    def dong_iv():
        db.expire_all()
        return {e.item_key: e for e in db.query(M.TripExpense).filter_by(trip_id=PHIEU, section="travel").all()}

    def gui_iv(u, doi=None, them=None):
        """Gửi lại đủ dòng mục IV như màn (mỗi dòng mang id, giá, cách trả đang có); `doi` = {item_key: cách trả}; `them` = dòng mới."""
        ds = []
        for e in sorted(dong_iv().values(), key=lambda x: x.line_no):
            ds.append({"id": e.id, "section": "travel", "item_key": e.item_key, "qty": e.qty, "unit_price": e.unit_price,
                       "currency": e.currency, "paid_by_epl": e.paid_by_epl, "acct_code": e.acct_code,
                       "pay_channel": (doi or {}).get(e.item_key, e.pay_channel)})
        ds += them or []
        return goi(u, "PUT", "/api/trips/" + PHIEU, {"expenses": ds})

    try:
        for u in ("thabok", "ketoancp", "admin"):
            TK[u] = c.post("/api/dang-nhap", json={"username": u, "password": "1234"}).json()["token"]
        d = dong_iv()
        dung(db.get(M.Trip, PHIEU) is not None and {"x_food", "x_water"} <= set(d) and d["x_food"].pay_channel is None,
             "d7 có phiếu mẫu, mục IV có x_food (chi ngay) · x_water (cùng lương)", {k: (v.pay_channel, v.acct_code) for k, v in d.items()})

        print("== 1. quyền ô Cách trả (quyen.cach_tra)")
        q = goi("thabok", "GET", "/api/trips/" + PHIEU)[1]["quyen"]["cach_tra"]
        dung(q == {"travel": False, "other": False}, "Admin Thà Bốc: không đổi cách trả mục IV / VI", q)
        q = goi("ketoancp", "GET", "/api/trips/" + PHIEU)[1]["quyen"]["cach_tra"]
        dung(q == {"travel": True, "other": True}, "KT Chi phí VC: đổi được khi mục còn chờ / đã nhập", q)
        q = goi("ketoancp", "GET", "/api/trips/" + DA_KHOA)[1]["quyen"]["cach_tra"]
        dung(q["travel"] is False, "KT Chi phí VC: mục IV đã ghi sổ → không đổi nữa", q)
        q = goi("admin", "GET", "/api/trips/" + PHIEU)[1]["quyen"]["cach_tra"]
        dung(q == {"travel": True, "other": True}, "Sếp: đổi được", q)

        print("== 2. Admin Thà Bốc gửi cách trả khác → bỏ qua")
        s, r = gui_iv("thabok", doi={"x_food": "luong", "x_water": "ncc"})
        d = dong_iv()
        dung(s == 200 and d["x_food"].pay_channel is None and d["x_food"].acct_code == "625/1601"
             and d["x_water"].pay_channel is None and d["x_water"].acct_code == "625/4201",
             "lưu được, cách trả giữ mặc định (x_food chi ngay 625/1601 · x_water cùng lương 625/4201)",
             (s, {k: (v.pay_channel, v.acct_code) for k, v in d.items()}))
        mong = RP._cach_tra_gui("travel", {"item_key": "x_parking", "pay_channel": RP.cach_tra_goi_y(db, db.get(M.Trip, PHIEU).route_id, "travel",
                                                                                                         {"item_key": "x_parking"})}, "EPL")
        s, r = gui_iv("thabok", them=[{"section": "travel", "item_key": "x_parking", "qty": 1, "paid_by_epl": True, "pay_channel": "ncc"}])
        d = dong_iv()
        dung(s == 200 and "x_parking" in d and d["x_parking"].pay_channel == mong,
             "dòng mới Bãi khai: cách trả theo bộ gợi ý tuyến / khoản mục, không theo ô gửi lên", (s, d.get("x_parking") and d["x_parking"].pay_channel, mong))

        print("== 3. KT Chi phí VC đổi lúc kiểm mục IV")
        s, r = gui_iv("ketoancp", doi={"x_food": "luong", "x_water": "tien_mat"})
        d = dong_iv()
        dung(s == 200 and d["x_food"].pay_channel == "luong" and d["x_food"].acct_code == "625/4201",
             "x_food → trả cùng lương: định khoản theo (625/4201)", (s, d["x_food"].pay_channel, d["x_food"].acct_code, r if s != 200 else ""))
        dung(d["x_water"].pay_channel == "tien_mat" and d["x_water"].acct_code == "625/1601",
             "x_water → chi ngay khi xe đi: định khoản theo (625/1601)", (d["x_water"].pay_channel, d["x_water"].acct_code))
        s, r = gui_iv("thabok", doi={"x_food": None, "x_water": None})
        d = dong_iv()
        dung(s == 200 and d["x_food"].pay_channel == "luong" and d["x_water"].pay_channel == "tien_mat",
             "Bãi lưu lại phiếu sau đó: giữ cách trả KT Chi phí đã đổi", (s, d["x_food"].pay_channel, d["x_water"].pay_channel))
        s, r = gui_iv("ketoancp", doi={"x_food": "vi_du_sai"})
        dung(s == 422 and (r.get("detail") or {}).get("ma") == "CACH_TRA_SAI", "cách trả không có trong danh sách → 422", (s, r))

        print("== 4. Sếp đổi được")
        s, r = gui_iv("admin", doi={"x_food": "ncc"})
        d = dong_iv()
        dung(s == 200 and d["x_food"].pay_channel == "ncc", "Sếp: x_food → nợ nhà cung cấp", (s, d["x_food"].pay_channel, d["x_food"].acct_code))
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("\n%d/%d đúng" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
