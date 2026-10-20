# -*- coding: utf-8 -*-
"""Thử 12/10 — KHO BÃI: xe về bãi chọn kho nhận, sổ nhập / xuất / điều chỉnh đi theo kho (services/kho_hang_dia.py, routes/kho_hang.py,
routes/phieu.py) trên bản sao _d7. Mọi thứ trong một giao dịch ngoài, cuối ROLLBACK; gọi qua FastAPI TestClient, không gọi mạng.

    python kiem/thu_kho_bai.py

  1 Danh mục kho bãi: kho mặc định (Thà Bốc) đứng đầu; thêm (Bãi / KT Thu/Chi / Sếp), sai mã · trùng mã · thiếu tên → lỗi rõ;
    KT Chi phí / tài xế → 403; kho mặc định không ngừng dùng được.
  2 Xe đã tới chọn kho B2 → sổ nhập ghi kho_id + tên kho, PNK_HH ghi kho; kho sai → 422 KHO_SAI, không ghi gì; không chọn → kho mặc định.
  3 Tồn lọc theo kho; dòng cũ (kho_id trống) thuộc kho mặc định.
  4 Giao lấy từ lô kho B2 → sổ xuất ghi kho B2, PXK_HH dòng ghi kho; điều chỉnh duyệt → sổ adj ghi kho B2.
  5 Ngừng dùng B2 → danh mục bỏ B2 (ca_ngung=1 vẫn thấy), chọn B2 lúc xe tới → 422 KHO_SAI.
"""
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
os.environ["KHO_NGUON"] = "qlsx"
os.environ.pop("QLSX_WEB_URL", None)
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _cam_mang(*a, **k):
    raise AssertionError("bài kho bãi không được gọi mạng")


urllib.request.urlopen = _cam_mang

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from _giay_to_thu import cho_du                         # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import goi_ke_toan as KT                  # noqa: E402
from services import kho_hang_dia as KHD                # noqa: E402
from services import kho_qlsx as KQ                     # noqa: E402
from services.bao_mat import ky_phien                   # noqa: E402

KQUA = []


def dung(dk, ten, ct=""):
    KQUA.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


KT.goi = lambda *a, **k: _cam_mang()
KQ._goi = lambda *a, **k: _cam_mang()


def ma(r):
    try:
        d = r.json().get("detail")
    except ValueError:
        return None
    return d.get("ma") if isinstance(d, dict) else d


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    M.DieuChinhHang.__table__.create(bind=conn, checkfirst=True)
    M.KhoBai.__table__.create(bind=conn, checkfirst=True)
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    try:
        H = {}
        for vai in ("yard", "acct", "expacct", "admin", "driver"):
            u = db.query(M.User).filter(M.User.role == vai, M.User.active.is_(True)).order_by(M.User.username).first()
            assert u is not None, "d7 thiếu người dùng vai %s" % vai
            H[vai] = {"Authorization": "Bearer " + ky_phien(u.username)}
        BAI, KT_VC, KT_CP, SEP, TX = H["yard"], H["acct"], H["expacct"], H["admin"], H["driver"]
        hom_nay = dt.date.today()
        xe = db.query(M.Vehicle).filter(M.Vehicle.owner_type == "EPL").order_by(M.Vehicle.truck_no).all()
        tx = db.query(M.Driver).order_by(M.Driver.id).all()
        kh = db.query(M.Customer).order_by(M.Customer.id).first()
        assert len(xe) >= 3 and len(tx) >= 3 and kh is not None, "d7 thiếu xe / tài xế / khách"
        cho_du(db, M, xe, tx)                             # 20/10: lập phiếu chặn giấy tờ — bài không thử luật đó (rollback lúc xong)
        QUANG = "ແຮ່ເຫຼັກ (quặng sắt)"

        def lap(kind, i, **them):
            d = {"kind": kind, "vehicle_id": xe[i].id, "driver_id": tx[i].id, "customer_id": kh.id, "doc_date": hom_nay.isoformat(),
                 "out_date": hom_nay.isoformat(), "goods_type": "iron_ore"}
            d.update(them)
            return c.post("/api/trips", json=d, headers=BAI)

        # ================================================================ 1. danh mục
        print("== 1. Danh mục kho bãi")
        url_k = "/api/kho-hang/kho-bai"
        r = c.get(url_k, headers=BAI)
        ds = r.json() if r.status_code == 200 else []
        dung(r.status_code == 200 and ds and ds[0]["id"] == KHD.KHO_MAC_DINH and ds[0]["mac_dinh"] and ds[0]["ten"] == KHD.DEPOT,
             "kho mặc định Thà Bốc đứng đầu danh mục", ds[:2])
        dung(c.get(url_k, headers=TX).status_code == 403, "tài xế xem danh mục → 403")
        for ten, h in (("KT Chi phí", KT_CP), ("tài xế", TX)):
            r = c.post(url_k, json={"ma": "ZZ", "ten": "x"}, headers=h)
            dung(r.status_code == 403, ten + " thêm kho bãi → 403", r.status_code)
        for ten, body, mong, http in (("mã có dấu cách", {"ma": "B 2", "ten": "Bãi 2"}, "MA_KHO_SAI", 422),
                                      ("thiếu mã", {"ma": " ", "ten": "Bãi 2"}, "MA_KHO_SAI", 422),
                                      ("thiếu tên", {"ma": "B2", "ten": "  "}, "THIEU_TEN_KHO", 422),
                                      ("trùng mã kho mặc định", {"ma": "tb", "ten": "Trùng"}, "TRUNG_MA_KHO", 409)):
            r = c.post(url_k, json=body, headers=BAI)
            dung(r.status_code == http and ma(r) == mong, "thêm: %s → %d %s" % (ten, http, mong), (r.status_code, r.json().get("detail")))
        r = c.post(url_k, json={"ma": "b2", "ten": "Bãi Nòng Khai", "ten_lo": "ບ່ອນໜອງຄາຍ"}, headers=BAI)
        B2 = r.json()
        dung(r.status_code == 200 and B2["ma"] == "B2" and B2["ten"] == "Bãi Nòng Khai" and B2["active"] and not B2["mac_dinh"],
             "Bãi thêm kho B2 (mã viết hoa)", B2)
        r = c.post(url_k, json={"ma": "B3", "ten": "Bãi 3"}, headers=KT_VC)
        dung(r.status_code == 200, "KT Thu/Chi thêm kho B3", r.status_code)
        r = c.put(url_k + "/" + KHD.KHO_MAC_DINH, json={"active": False}, headers=SEP)
        dung(r.status_code == 409 and ma(r) == "KHO_MAC_DINH", "ngừng dùng kho mặc định → 409", r.status_code)
        r = c.put(url_k + "/khongco", json={"ten": "x"}, headers=SEP)
        dung(r.status_code == 404, "sửa kho không có → 404", r.status_code)

        # ================================================================ 2. xe tới chọn kho
        print("== 2. Xe đã tới · chọn kho nhận")
        A = db.get(M.Trip, lap("gom", 0, weight_origin=20).json()["id"])
        B = db.get(M.Trip, lap("gom", 1, weight_origin=15).json()["id"])
        r = c.post("/api/trips/%s/transport-status" % A.id, json={"status": "arrived", "weight_dest": 19.6, "kho_id": "khongco"}, headers=BAI)
        db.expire_all()
        dung(r.status_code == 422 and ma(r) == "KHO_SAI" and db.get(M.Trip, A.id).transport_status != "arrived"
             and not db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == A.id).count(),
             "kho không có → 422 KHO_SAI, phiếu chưa tới, sổ chưa ghi", (r.status_code, r.json().get("detail")))
        r = c.post("/api/trips/%s/transport-status" % A.id, json={"status": "arrived", "weight_dest": 19.6, "kho_id": B2["id"],
                                                                    "back_date": hom_nay.isoformat()}, headers=BAI)
        db.expire_all()
        mv = db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == A.id, M.GoodsMove.kind == "in").all()
        to = db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_bang == "trips", M.ChungTu.nguon_id == A.id).all()
        pl = json.loads(to[0].payload) if to else {}
        dung(r.status_code == 200 and len(mv) == 1 and mv[0].kho_id == B2["id"] and mv[0].depot == "Bãi Nòng Khai",
             "chọn B2: sổ nhập ghi kho_id B2 + tên kho", (r.status_code, [(m.kho_id, m.depot) for m in mv]))
        dung(len(to) == 1 and pl.get("kho_id") == B2["id"] and pl.get("kho") == "Bãi Nòng Khai" and to[0].doi_tuong_ten == "Bãi Nòng Khai",
             "PNK_HH ghi kho nhận B2", (pl, to and to[0].doi_tuong_ten))
        r = c.get("/api/trips/%s/to-kho-hang" % A.id, headers=BAI)
        dung(r.status_code == 200 and r.json().get("kho") == "Bãi Nòng Khai", "tờ để in ghi kho B2", r.json().get("kho"))
        r = c.post("/api/trips/%s/transport-status" % B.id, json={"status": "arrived", "weight_dest": 14.8}, headers=BAI)
        db.expire_all()
        mb = db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == B.id, M.GoodsMove.kind == "in").all()
        dung(r.status_code == 200 and len(mb) == 1 and mb[0].kho_id == KHD.KHO_MAC_DINH and mb[0].depot == KHD.DEPOT,
             "không chọn kho → kho mặc định Thà Bốc", [(m.kho_id, m.depot) for m in mb])

        # ================================================================ 3. tồn theo kho
        print("== 3. Tồn theo kho")
        r = c.get("/api/kho-hang/ton", params={"kho": B2["id"]}, headers=BAI)
        it = r.json().get("items", [])
        dung(r.status_code == 200 and [x["lo_id"] for x in it] == [A.id] and it[0]["kho_id"] == B2["id"] and it[0]["kho"] == "Bãi Nòng Khai",
             "lọc kho B2: chỉ lô A", [(x["lo_doc_no"], x["kho"]) for x in it])
        r = c.get("/api/kho-hang/ton", params={"kho": KHD.KHO_MAC_DINH, "chi_con": 0}, headers=BAI)
        it = r.json().get("items", [])
        cu_null = db.query(M.GoodsMove.lo_trip_id).filter(M.GoodsMove.kind == "in", M.GoodsMove.kho_id.is_(None)).distinct().all()
        ids = {x["lo_id"] for x in it}
        dung(B.id in ids and A.id not in ids and {x[0] for x in cu_null} <= ids and all(x["kho_id"] == KHD.KHO_MAC_DINH for x in it),
             "lọc kho mặc định: có lô B + mọi lô cũ chưa ghi kho, không có lô A", (len(it), len(cu_null)))
        r = c.get("/api/kho-hang/ton", headers=BAI)
        d = r.json()
        dung(r.status_code == 200 and {k["ma"] for k in d.get("kho_bai", [])} >= {"TB", "B2", "B3"} and d["quyen"]["sua_kho"],
             "tồn kèm danh mục kho + quyền sửa kho (Bãi)", [k["ma"] for k in d.get("kho_bai", [])])
        r = c.get("/api/kho-hang/ton", headers=KT_CP)
        dung(r.status_code == 200 and r.json()["quyen"]["sua_kho"] is False, "KT Chi phí: không có quyền sửa kho", r.json().get("quyen"))

        # ================================================================ 4. xuất · điều chỉnh theo kho
        print("== 4. Giao lấy lô · điều chỉnh đi theo kho")
        r = lap("giao", 2, goods=[{"loai": "hang", "goods_name": QUANG, "qty_t": 5, "tu_phieu_id": A.id},
                                  {"loai": "hang", "goods_name": QUANG, "qty_t": 4, "tu_phieu_id": B.id}])
        dung(r.status_code == 200, "Bãi lập DO giao lấy A 5 t + B 4 t", (r.status_code, r.json().get("detail")))
        G = r.json()["id"]
        db.expire_all()
        out = {m.lo_trip_id: m for m in db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == G, M.GoodsMove.kind == "out").all()}
        dung(out.get(A.id) is not None and out[A.id].kho_id == B2["id"] and out[A.id].depot == "Bãi Nòng Khai"
             and out.get(B.id) is not None and out[B.id].kho_id == KHD.KHO_MAC_DINH,
             "sổ xuất mỗi lô ghi kho của lô (A → B2, B → Thà Bốc)", {k: (m.kho_id, m.depot) for k, m in out.items()})
        tg = db.query(M.ChungTu).filter(M.ChungTu.loai == "PXK_HH", M.ChungTu.nguon_id == G).first()
        plg = json.loads(tg.payload) if tg else {}
        dung(sorted((x["lo"], x["kho"]) for x in plg.get("dong", [])) == sorted([(A.id, "Bãi Nòng Khai"), (B.id, KHD.DEPOT)]),
             "PXK_HH dòng ghi kho từng lô", plg.get("dong"))
        dung(KHD.ton_lo(db, A.id) == 14.6, "lô A (kho B2) còn 14,6 t", KHD.ton_lo(db, A.id))
        r = c.post("/api/kho-hang/dieu-chinh", json={"lo_id": A.id, "tan": -0.6, "ly_do": "Hao ở bãi B2"}, headers=BAI)
        dc = r.json()
        r = c.post("/api/kho-hang/dieu-chinh/%s/duyet" % dc.get("id"), json={"dong_y": True}, headers=KT_VC)
        db.expire_all()
        adj = db.query(M.GoodsMove).filter(M.GoodsMove.lo_trip_id == A.id, M.GoodsMove.kind == "adj").all()
        dung(r.status_code == 200 and len(adj) == 1 and adj[0].kho_id == B2["id"] and adj[0].depot == "Bãi Nòng Khai"
             and KHD.ton_lo(db, A.id) == 14.0, "điều chỉnh −0,6 t duyệt → sổ adj ghi kho B2, tồn 14 t",
             (r.status_code, [(m.kho_id, m.qty_t) for m in adj]))
        r = c.get("/api/kho-hang/ton", params={"kho": B2["id"]}, headers=BAI)
        it = r.json().get("items", [])
        dung(len(it) == 1 and it[0]["ton"] == 14.0 and it[0]["tan_xuat"] == 5 and it[0]["tan_dieu_chinh"] == -0.6,
             "tồn kho B2: nhập 19,6 − xuất 5 − 0,6 = 14", it and (it[0]["tan_nhap"], it[0]["tan_xuat"], it[0]["tan_dieu_chinh"]))

        # ================================================================ 5. ngừng dùng
        print("== 5. Ngừng dùng kho")
        r = c.put(url_k + "/" + B2["id"], json={"active": False}, headers=SEP)
        dung(r.status_code == 200 and r.json()["active"] is False, "Sếp ngừng dùng B2", r.status_code)
        dung(B2["id"] not in {k["id"] for k in c.get(url_k, headers=BAI).json()}
             and B2["id"] in {k["id"] for k in c.get(url_k, params={"ca_ngung": 1}, headers=BAI).json()},
             "danh mục bỏ B2, ca_ngung=1 vẫn thấy")
        C = db.get(M.Trip, lap("gom", 1, weight_origin=10).json()["id"])
        r = c.post("/api/trips/%s/transport-status" % C.id, json={"status": "arrived", "weight_dest": 9.9, "kho_id": B2["id"]}, headers=BAI)
        dung(r.status_code == 422 and ma(r) == "KHO_SAI", "chọn kho đã ngừng dùng → 422 KHO_SAI", r.status_code)
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQUA), len(KQUA)))
    sys.exit(0 if all(KQUA) else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:                       # noqa: BLE001 — không in chuỗi nối
        import traceback
        print(traceback.format_exc().replace(URL, "<url>"))
        print("TỔNG: %d/%d đạt — bài vỡ: %s" % (sum(KQUA), len(KQUA) + 1, str(e).replace(URL, "<url>")[:300]))
        sys.exit(1)
