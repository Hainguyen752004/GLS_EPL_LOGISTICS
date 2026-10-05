# -*- coding: utf-8 -*-
"""Thử 05/10 — KHO HÀNG KHÁCH GỬI ở bãi, máy tự tạo phiếu theo DO (services/kho_hang_dia.py, routes/kho_hang.py) trên bản sao _d7.
MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK: không ghi gì vào d7. Gọi qua FastAPI TestClient bằng
phiên đăng nhập thật của người dùng có sẵn trong d7 (thabok · ketoan · ketoancp · admin · tài xế), không chạy sự kiện khởi động,
KHÔNG gọi mạng (urlopen bị chặn — gọi là hỏng bài) và không gọi kho tạm.

    python kiem/thu_kho_hang.py

Bảng mới `dieu_chinh_hang` dựng TRONG giao dịch (không khoá ngoại → không khoá bảng trips), rollback là mất.
DO thử lập mới trong giao dịch (Bãi lập, xe nhà, không dòng chi): gom A 20 t mỏ / 19,6 t bãi, gom B 15 t / 14,8 t, giao G lấy từ A + B.
  1 Nhập: thiếu cân bãi → 422 THIEU_CAN_BAI (không ghi gì); có cân bãi → sổ in theo cân bãi + PNK_HH (tiền 0, một tờ / DO gom);
    báo tới lại không sinh trùng; tờ để in.
  2 Giao: lấy quá tồn lô → 409, không lập phiếu; lập → PXK_HH theo lô; sửa phiếu giao → thay nội dung tờ (giữ số); vượt tồn khi sửa
    → 409 tờ nguyên; tờ đã đối chiếu → 409 TO_DA_DOI_CHIEU.
  3 Tồn / lô / đối soát đúng số (so với cách tính cũ từng lô), cờ quyền, tài xế 403.
  4 Điều chỉnh: lập (sai vai 403, lỗi đầu vào 422, giảm quá tồn 409) · duyệt (adj + DC_HH) · từ chối (phải ghi lý do) · duyệt lại 409
    · duyệt làm tồn âm 409 · sai vai 403.
  5 Xoá DO: lô đã có phiếu giao lấy → 409; xoá giao → rút PXK_HH, trả tồn; xoá gom → rút PNK_HH + DC_HH, xoá đơn điều chỉnh; tờ đã
    đối chiếu giữ lại.
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
    raise AssertionError("bài kho hàng không được gọi mạng")


urllib.request.urlopen = _cam_mang

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, func, text        # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
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


def _cam_kho_tam(*a, **k):
    raise AssertionError("KHO_NGUON=qlsx mà vẫn gọi kho tạm")


KT.goi = _cam_kho_tam
KQ._goi = lambda *a, **k: _cam_mang()


def ma(r):
    try:
        d = r.json().get("detail")
    except ValueError:
        return None
    return d.get("ma") if isinstance(d, dict) else d


def ton_cu(db, lo):
    """Cách tính CŨ (trước 05/10) từng lô bằng Python — để so với câu GROUP BY mới."""
    ds = db.query(M.GoodsMove).filter(M.GoodsMove.lo_trip_id == lo).all()
    return round(sum(m.qty_t for m in ds if m.kind in ("in", "adj")) - sum(m.qty_t for m in ds if m.kind == "out"), 3)


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))   # máy thử chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
    M.DieuChinhHang.__table__.create(bind=conn, checkfirst=True)
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    try:
        def nguoi(vai):
            return db.query(M.User).filter(M.User.role == vai, M.User.active.is_(True)).order_by(M.User.username).first()
        H = {}
        for vai in ("yard", "acct", "expacct", "admin", "driver"):
            u = nguoi(vai)
            assert u is not None, "d7 thiếu người dùng vai %s" % vai
            H[vai] = {"Authorization": "Bearer " + ky_phien(u.username)}
        BAI, KT_VC, KT_CP, SEP, TX = H["yard"], H["acct"], H["expacct"], H["admin"], H["driver"]
        hom_nay = dt.date.today()
        xe = [v for v in db.query(M.Vehicle).filter(M.Vehicle.owner_type == "EPL").order_by(M.Vehicle.truck_no).all()]
        tx = db.query(M.Driver).order_by(M.Driver.id).all()
        kh = db.query(M.Customer).order_by(M.Customer.id).first()
        assert len(xe) >= 3 and len(tx) >= 3 and kh is not None, "d7 thiếu xe / tài xế / khách"
        QUANG = "ແຮ່ເຫຼັກ (quặng sắt)"

        def lap(kind, i, **them):
            d = {"kind": kind, "vehicle_id": xe[i].id, "driver_id": tx[i].id, "customer_id": kh.id, "doc_date": hom_nay.isoformat(),
                 "out_date": hom_nay.isoformat(), "goods_type": "iron_ore"}
            d.update(them)
            return c.post("/api/trips", json=d, headers=BAI)

        # ================================================================ 1. nhập
        print("== 1. DO gom báo Xe đã tới → nhập kho + PNK_HH")
        r = lap("gom", 0, weight_origin=20)
        dung(r.status_code == 200, "Bãi lập DO gom A (cân mỏ 20 t)", (r.status_code, r.json().get("detail")))
        A = db.get(M.Trip, r.json()["id"])
        r = lap("gom", 1, weight_origin=15)
        B = db.get(M.Trip, r.json()["id"])
        url_a = "/api/trips/%s/transport-status" % A.id
        r = c.post(url_a, json={"status": "arrived", "back_date": hom_nay.isoformat()}, headers=BAI)
        db.expire_all()
        dung(r.status_code == 422 and ma(r) == "THIEU_CAN_BAI" and "cân" in r.json()["detail"]["loi"],
             "thiếu cân bãi → 422 THIEU_CAN_BAI, câu rõ", r.json().get("detail"))
        dung(db.get(M.Trip, A.id).transport_status != "arrived" and not db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == A.id).count(),
             "bị chặn: phiếu chưa tới, sổ chưa ghi")
        r = c.post(url_a, json={"status": "arrived", "weight_dest": "0", "back_date": hom_nay.isoformat()}, headers=BAI)
        dung(r.status_code == 422 and ma(r) == "THIEU_CAN_BAI", "cân bãi 0 → 422 THIEU_CAN_BAI", r.status_code)
        r = c.post(url_a, json={"status": "arrived", "weight_dest": 19.6, "back_date": hom_nay.isoformat()}, headers=BAI)
        db.expire_all()
        mv = db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == A.id, M.GoodsMove.kind == "in").all()
        to_a = db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_bang == "trips", M.ChungTu.nguon_id == A.id).all()
        pl = json.loads(to_a[0].payload) if to_a else {}
        dung(r.status_code == 200 and len(mv) == 1 and abs(mv[0].qty_t - 19.6) < 1e-9 and mv[0].lo_trip_id == A.id,
             "có cân bãi: sổ nhập 19,6 t theo cân bãi, lô = DO gom", (r.status_code, [(m.qty_t, m.kind) for m in mv]))
        dung(len(to_a) == 1 and to_a[0].so.startswith("PNK_HH/" + hom_nay.strftime("%y%m") + "/") and to_a[0].tien == 0
             and to_a[0].tien_lak == 0 and to_a[0].trip_id == A.id and pl.get("tan") == 19.6 and pl.get("boc_len") == 20
             and abs(pl.get("hao_hut") - 0.4) < 1e-9 and to_a[0].co is None,
             "PNK_HH: số theo quy ước, tiền 0, chỉ tấn (19,6 · mỏ 20 · hao 0,4), một vế ngoài bảng",
             to_a and (to_a[0].so, to_a[0].tien, pl))
        hao = db.query(M.TripGoods).filter(M.TripGoods.trip_id == A.id, M.TripGoods.loai == "hao_hut").all()
        dung(len(hao) == 1 and abs(hao[0].qty_t - 0.4) < 1e-9, "dòng hao hụt trên DO gom 0,4 t", [(h.qty_t, h.note) for h in hao])
        r = c.post(url_a, json={"status": "arrived", "weight_dest": 19.6}, headers=BAI)
        db.expire_all()
        dung(r.status_code == 200 and db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_id == A.id).count() == 1
             and db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == A.id, M.GoodsMove.kind == "in").count() == 1,
             "báo tới lại: không nhập trùng, không sinh tờ thứ hai", r.status_code)
        r = c.post("/api/trips/%s/transport-status" % B.id, json={"status": "arrived", "weight_dest": 14.8,
                                                                    "back_date": hom_nay.isoformat()}, headers=BAI)
        dung(r.status_code == 200, "DO gom B tới bãi 14,8 t", r.status_code)
        r = c.get("/api/trips/%s/to-kho-hang" % A.id, headers=BAI)
        t = r.json()
        dung(r.status_code == 200 and t["loai"] == "PNK_HH" and t["so"] == to_a[0].so and t["do_no"] == A.doc_no
             and t["dong"] == [{"lo_doc_no": A.doc_no, "tan": 19.6, "loai_hang": QUANG, "lo_id": A.id}] and t["can_mo"] == 20
             and t["can_bai"] == 19.6 and t["can_noi_giao"] is None and abs(t["hao_hut"] - 0.4) < 1e-9 and t["xe"] == A.truck_no
             and t["tai_xe"] and t["nguoi_xac_nhan"] and t["khach"] == A.customer_name,
             "tờ để in PNK_HH: số, DO, dòng lô, cân mỏ / cân bãi / hao hụt, xe, tài xế, người xác nhận", t)
        r = c.get("/api/trips/%s/to-kho-hang" % A.id, headers=TX)
        dung(r.status_code == 403, "tài xế xem tờ kho hàng → 403", r.status_code)
        cu = db.query(M.Trip).filter(M.Trip.doc_no == "G4-0001-10/EPL").first()
        if cu is not None:
            r = c.get("/api/trips/%s/to-kho-hang" % cu.id, headers=BAI)
            dung(r.status_code == 404 and ma(r) == "CHUA_CO_TO", "DO chưa có tờ (dữ liệu chép từ kho tạm) → 404 CHUA_CO_TO", r.status_code)

        # ================================================================ 2. giao
        print("== 2. DO giao lấy lô → PXK_HH; sửa phiếu giao thay tờ")
        so_trip = db.query(func.count(M.Trip.id)).scalar()
        r = lap("giao", 2, goods=[{"loai": "hang", "goods_name": QUANG, "qty_t": 25, "tu_phieu_id": A.id}])
        db.expire_all()
        dung(r.status_code == 409 and ma(r) == "VUOT_TON" and db.query(func.count(M.Trip.id)).scalar() == so_trip,
             "lấy 25 t từ lô A (còn 19,6) → 409 VUOT_TON, không lập phiếu", (r.status_code, r.json().get("detail")))
        r = lap("giao", 2, goods=[{"loai": "hang", "goods_name": QUANG, "qty_t": 12, "tu_phieu_id": A.id}])
        dung(r.status_code == 200, "Bãi lập DO giao G lấy 12 t lô A", (r.status_code, r.json().get("detail")))
        G = db.get(M.Trip, r.json()["id"])
        db.expire_all()
        to_g = db.query(M.ChungTu).filter(M.ChungTu.loai == "PXK_HH", M.ChungTu.nguon_bang == "trips", M.ChungTu.nguon_id == G.id).all()
        plg = json.loads(to_g[0].payload) if to_g else {}
        so_g = to_g[0].so if to_g else None
        dung(len(to_g) == 1 and so_g.startswith("PXK_HH/") and to_g[0].tien == 0 and to_g[0].no is None
             and plg.get("dong") == [{"hang": QUANG, "tan": 12.0, "lo": A.id, "lo_doc_no": A.doc_no}] and plg.get("tan") == 12,
             "PXK_HH: một tờ / DO giao, dòng theo lô, tiền 0, một vế", (so_g, plg))
        dung(KHD.ton_lo(db, A.id) == 7.6, "lô A còn 7,6 t", KHD.ton_lo(db, A.id))
        url_g = "/api/trips/%s" % G.id
        r = c.put(url_g, json={"goods": [{"loai": "hang", "goods_name": QUANG, "qty_t": 10, "tu_phieu_id": A.id},
                                         {"loai": "hang", "goods_name": QUANG, "qty_t": 5, "tu_phieu_id": B.id}]}, headers=BAI)
        db.expire_all()
        to_g2 = db.query(M.ChungTu).filter(M.ChungTu.loai == "PXK_HH", M.ChungTu.nguon_id == G.id).all()
        plg = json.loads(to_g2[0].payload) if to_g2 else {}
        dung(r.status_code == 200 and len(to_g2) == 1 and to_g2[0].so == so_g and plg.get("tan") == 15
             and sorted((x["lo_doc_no"], x["tan"]) for x in plg.get("dong") or []) == sorted([(A.doc_no, 10.0), (B.doc_no, 5.0)]),
             "sửa phiếu giao (A 10 + B 5) → thay nội dung tờ, GIỮ số", (r.status_code, to_g2 and to_g2[0].so, plg.get("dong")))
        dung(KHD.ton_lo(db, A.id) == 9.6 and KHD.ton_lo(db, B.id) == 9.8
             and db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == G.id, M.GoodsMove.kind == "out").count() == 2,
             "sổ: phần xuất của G thay toàn bộ — A còn 9,6 · B còn 9,8", (KHD.ton_lo(db, A.id), KHD.ton_lo(db, B.id)))
        r = c.put(url_g, json={"goods": [{"loai": "hang", "goods_name": QUANG, "qty_t": 20, "tu_phieu_id": A.id}]}, headers=BAI)
        db.expire_all()
        dung(r.status_code == 409 and ma(r) == "VUOT_TON" and json.loads(db.get(M.ChungTu, to_g2[0].id).payload)["tan"] == 15
             and KHD.ton_lo(db, A.id) == 9.6, "sửa vượt tồn lô → 409, sổ và tờ nguyên", (r.status_code, r.json().get("detail")))
        x = db.get(M.ChungTu, to_g2[0].id)
        x.da_day = True
        db.commit()
        r = c.put(url_g, json={"goods": [{"loai": "hang", "goods_name": QUANG, "qty_t": 9, "tu_phieu_id": A.id},
                                         {"loai": "hang", "goods_name": QUANG, "qty_t": 5, "tu_phieu_id": B.id}]}, headers=BAI)
        db.expire_all()
        dung(r.status_code == 409 and ma(r) == "TO_DA_DOI_CHIEU" and KHD.ton_lo(db, A.id) == 9.6,
             "tờ PXK_HH đã đối chiếu → sửa phần xuất 409 TO_DA_DOI_CHIEU, sổ nguyên", (r.status_code, ma(r)))
        x = db.get(M.ChungTu, to_g2[0].id)
        x.da_day = False
        db.commit()
        r = c.get("/api/trips/%s/to-kho-hang" % G.id, headers=KT_VC)
        t = r.json()
        dung(r.status_code == 200 and t["loai"] == "PXK_HH" and t["so"] == so_g and t["can_bai"] == 15 and t["can_mo"] is None
             and t["can_noi_giao"] is None and t["hao_hut"] is None
             and sorted((z["lo_doc_no"], z["tan"]) for z in t["dong"]) == sorted([(A.doc_no, 10.0), (B.doc_no, 5.0)]),
             "tờ để in PXK_HH: dòng theo lô, cân bãi = tấn xuất", t)

        # ================================================================ 3. tồn / lô / đối soát
        print("== 3. Tồn · lô · đối soát")
        r = c.get("/api/kho-hang/ton", params={"q": A.doc_no}, headers=BAI)
        d = r.json()
        it = [z for z in d.get("items", []) if z["lo_id"] == A.id]
        dung(r.status_code == 200 and len(it) == 1 and it[0]["tan_nhap"] == 19.6 and it[0]["tan_xuat"] == 10 and it[0]["tan_dieu_chinh"] == 0
             and it[0]["ton"] == 9.6 and it[0]["trang_thai"] == "con" and it[0]["so_phieu_nhap"] == to_a[0].so and it[0]["so_ngay_ton"] == 0
             and it[0]["lo_doc_no"] == A.doc_no and it[0]["loai_hang"] == QUANG and it[0]["khach"] == A.customer_name
             and it[0]["ngay_nhap"] == hom_nay.isoformat(), "tồn lô A: nhập 19,6 · xuất 10 · tồn 9,6 · số PNK · còn", it)
        dung(all(A.doc_no in (z["lo_doc_no"] or "") for z in d["items"]) and d["tong"]["so_lo"] == len(d["items"]), "lọc q theo số DO", d["tong"])
        dung(d["quyen"] == {"lap_dieu_chinh": True, "duyet_dieu_chinh": False}, "Bãi: được lập, không duyệt", d["quyen"])
        r = c.get("/api/kho-hang/ton", headers=KT_VC)
        d = r.json()
        dung(d["quyen"] == {"lap_dieu_chinh": False, "duyet_dieu_chinh": True}, "KT Thu/Chi VC: duyệt, không lập", d["quyen"])
        ds_api = {z["lo_id"]: z for z in d["items"]}
        dung(all(z["trang_thai"] == "con" for z in d["items"]) and abs(d["tong"]["tan_ton"] - sum(z["ton"] for z in d["items"])) < 1e-6
             and d["tong"]["so_lo"] == len(d["items"]), "chi_con mặc định: chỉ lô còn, tổng tấn = Σ tồn", d["tong"])
        r = c.get("/api/kho-hang/ton", params={"chi_con": 0}, headers=SEP)
        tat = r.json()["items"]
        lo_all = {m.lo_trip_id for m in db.query(M.GoodsMove).filter(M.GoodsMove.kind == "in").all()}
        dung({z["lo_id"] for z in tat} == lo_all and all(abs(z["ton"] - ton_cu(db, z["lo_id"])) < 1e-6 for z in tat)
             and all(z["lo_id"] in ds_api for z in tat if z["ton"] > 0.0005),
             "chi_con=0: đủ mọi lô, tồn từng lô = cách tính cũ, lô còn ⊂ danh sách mặc định", len(tat))
        cu_lo = KHD.danh_sach_lo(db, con_hang=True, tru_phieu_id=G.id)
        a_lo = next((z for z in cu_lo if z["lo_trip_id"] == A.id), None)
        dung(a_lo is not None and a_lo["con_t"] == 19.6 and set(a_lo) == {"lo_trip_id", "doc_no", "goods_name", "ngay", "nhap_t", "dieu_chinh_t",
                                                                         "con_t", "customer_name", "origin", "truck_no"},
             "danh_sach_lo khuôn cũ, tru_phieu bỏ phần G đang giữ (A 19,6)", a_lo)
        r = c.get("/api/kho-hang/lo", params={"tru_phieu": G.id}, headers=BAI)
        dung(r.status_code == 200 and any(z["lo_trip_id"] == A.id and z["con_t"] == 19.6 for z in r.json()), "ô chọn lô phiếu giao vẫn chạy")
        r = c.get("/api/kho-hang/ton", headers=TX)
        dung(r.status_code == 403, "tài xế xem tồn kho hàng → 403", r.status_code)
        r = c.get("/api/kho-hang/lo/" + A.id, headers=KT_VC)
        d = r.json()
        dung(r.status_code == 200 and d["lo"]["ton"] == 9.6 and d["nhap"]["so_phieu"] == to_a[0].so and d["nhap"]["can_mo"] == 20
             and d["nhap"]["can_bai"] == 19.6 and abs(d["nhap"]["hao_hut"] - 0.4) < 1e-9 and d["nhap"]["do_no"] == A.doc_no
             and d["nhap"]["xe"] == A.truck_no
             and [(z["so_phieu"], z["do_no"], z["tan"]) for z in d["xuat"]] == [(so_g, G.doc_no, 10.0)] and d["dieu_chinh"] == [],
             "chi tiết lô A: phiếu nhập (cân mỏ/bãi/hao), xuất theo DO giao + số PXK", d)
        r = c.get("/api/kho-hang/lo/khong-co", headers=KT_VC)
        dung(r.status_code == 404, "lô không có → 404", r.status_code)
        r = c.get("/api/kho-hang/doi-soat", params={"ngay": hom_nay.isoformat()}, headers=KT_VC)
        d = r.json()
        gom_hn = db.query(M.Trip).filter(M.Trip.kind == "gom", M.Trip.transport_status == "arrived",
                                         func.coalesce(M.Trip.back_date, M.Trip.doc_date) == hom_nay).all()
        pnk_hn = db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.ngay == hom_nay).count()
        lech = {(z["do_no"], z["thieu"]) for z in d.get("lech", [])}
        dung(r.status_code == 200 and d["do_gom_da_toi"] == len(gom_hn) and d["phieu_nhap"] == pnk_hn and d["do_giao"] >= 1
             and d["phieu_xuat"] >= 1 and (A.doc_no, "PNK_HH") not in lech and (B.doc_no, "PNK_HH") not in lech
             and (G.doc_no, "PXK_HH") not in lech, "đối soát hôm nay: số DO gom tới = số tính tay, DO thử không lệch", d)
        cu_toi = [p for p in gom_hn if not db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_id == p.id).count()]
        dung(all((p.doc_no, "PNK_HH") in lech for p in cu_toi) and len(lech) >= len(cu_toi),
             "DO gom tới hôm nay mà chưa có tờ (dữ liệu chép) → nằm trong lệch", sorted(lech))
        r = c.get("/api/kho-hang/doi-soat", params={"ngay": "05-10-2026"}, headers=KT_VC)
        dung(r.status_code == 422 and ma(r) == "NGAY_SAI", "ngày sai dạng → 422", r.status_code)

        # ================================================================ 4. điều chỉnh
        print("== 4. Phiếu điều chỉnh DC_HH")
        url_dc = "/api/kho-hang/dieu-chinh"
        r = c.post(url_dc, json={"lo_id": A.id, "tan": -0.5, "ly_do": "Hao ở bãi do mưa"}, headers=KT_VC)
        dung(r.status_code == 403 and ma(r) == "KHONG_CO_QUYEN", "KT Thu/Chi VC lập → 403 (Bãi lập)", r.status_code)
        r = c.post(url_dc, json={"lo_id": A.id, "tan": -0.5, "ly_do": "Hao ở bãi do mưa"}, headers=TX)
        dung(r.status_code == 403, "tài xế lập → 403", r.status_code)
        for ten, body, mong, http in (("lô không có", {"lo_id": "khongco", "tan": 1, "ly_do": "abc"}, "LO_SAI", 422),
                                      ("tấn = 0", {"lo_id": A.id, "tan": 0, "ly_do": "Kiểm kê"}, "SO_KHONG", 422),
                                      ("tấn không phải số", {"lo_id": A.id, "tan": "abc", "ly_do": "Kiểm kê"}, "SO_SAI", 422),
                                      ("thiếu lý do", {"lo_id": A.id, "tan": 1, "ly_do": "  "}, "THIEU_LY_DO", 422),
                                      ("giảm quá tồn", {"lo_id": A.id, "tan": -100, "ly_do": "Đóng lô"}, "VUOT_TON", 409)):
            r = c.post(url_dc, json=body, headers=BAI)
            dung(r.status_code == http and ma(r) == mong, "lập: " + ten + " → %d %s" % (http, mong), (r.status_code, r.json().get("detail")))
        r = c.post(url_dc, json={"lo_id": A.id, "tan": -0.5, "ly_do": "Hao ở bãi do mưa"}, headers=BAI)
        dc1 = r.json()
        db.expire_all()
        dung(r.status_code == 200 and dc1["trang_thai"] == "cho" and dc1["tan"] == -0.5 and dc1["lo_doc_no"] == A.doc_no
             and dc1["nguoi_lap"] and dc1["so_phieu"] is None and KHD.ton_lo(db, A.id) == 9.6
             and not db.query(M.GoodsMove).filter(M.GoodsMove.lo_trip_id == A.id, M.GoodsMove.kind == "adj").count(),
             "Bãi lập −0,5 t → chờ duyệt, CHƯA đổi tồn", dc1)
        r = c.get(url_dc, params={"trang_thai": "cho"}, headers=KT_VC)
        dung(r.status_code == 200 and any(z["id"] == dc1["id"] for z in r.json()["items"])
             and all(z["trang_thai"] == "cho" for z in r.json()["items"]), "danh sách chờ duyệt có đơn", len(r.json().get("items", [])))
        r = c.get(url_dc, params={"trang_thai": "xyz"}, headers=KT_VC)
        dung(r.status_code == 422, "trang_thai lạ → 422", r.status_code)
        url_d1 = "%s/%s/duyet" % (url_dc, dc1["id"])
        r = c.post(url_d1, json={"dong_y": True}, headers=BAI)
        dung(r.status_code == 403 and ma(r) == "KHONG_CO_QUYEN", "Bãi duyệt → 403", r.status_code)
        r = c.post(url_d1, json={"dong_y": True}, headers=KT_CP)
        dung(r.status_code == 403, "KT Chi phí (expacct) duyệt → 403", r.status_code)
        r = c.post(url_d1, json={}, headers=KT_VC)
        dung(r.status_code == 422, "thiếu dong_y → 422", r.status_code)
        r = c.post(url_d1, json={"dong_y": True, "ghi_chu": "Đúng, mưa to 03/10"}, headers=KT_VC)
        x = r.json()
        db.expire_all()
        adj = db.query(M.GoodsMove).filter(M.GoodsMove.lo_trip_id == A.id, M.GoodsMove.kind == "adj").all()
        dc_to = db.query(M.ChungTu).filter(M.ChungTu.loai == "DC_HH", M.ChungTu.nguon_bang == "goods_moves",
                                           M.ChungTu.nguon_id == (adj[0].id if adj else "")).all()
        dung(r.status_code == 200 and x["trang_thai"] == "da_duyet" and x["so_phieu"] and x["so_phieu"].startswith("DC_HH/")
             and x["nguoi_duyet"] and x["ngay"] == hom_nay.isoformat() and x["ton_lo"] == 9.1,
             "KT Thu/Chi VC duyệt → đã duyệt, số DC_HH, tồn lô 9,1", x)
        dung(len(adj) == 1 and adj[0].qty_t == -0.5 and adj[0].note == "Hao ở bãi do mưa" and len(dc_to) == 1 and dc_to[0].so == x["so_phieu"]
             and dc_to[0].tien == 0 and dc_to[0].trip_id == A.id and json.loads(dc_to[0].payload)["chieu"] == "giam",
             "sổ: một dòng adj −0,5 có lý do + tờ DC_HH (tiền 0, chiều giảm)", [(m.qty_t, m.note) for m in adj])
        r = c.post(url_d1, json={"dong_y": True}, headers=SEP)
        dung(r.status_code == 409 and ma(r) == "DA_XU_LY", "duyệt lại → 409 DA_XU_LY", r.status_code)
        r = c.post(url_dc, json={"lo_id": A.id, "tan": 1.0, "ly_do": "Cân bãi ghi thiếu"}, headers=BAI)
        dc2 = r.json()
        url_d2 = "%s/%s/duyet" % (url_dc, dc2["id"])
        r = c.post(url_d2, json={"dong_y": False}, headers=KT_VC)
        dung(r.status_code == 422 and ma(r) == "THIEU_GHI_CHU", "từ chối không ghi lý do → 422", r.status_code)
        r = c.post(url_d2, json={"dong_y": False, "ghi_chu": "Phiếu cân bãi khớp, không thiếu"}, headers=KT_VC)
        db.expire_all()
        dung(r.status_code == 200 and r.json()["trang_thai"] == "tu_choi" and r.json()["ghi_chu"] and r.json()["so_phieu"] is None
             and KHD.ton_lo(db, A.id) == 9.1, "từ chối → tu_choi, tồn không đổi, không tờ", r.json())
        r = c.post(url_dc, json={"lo_id": A.id, "tan": -9.0, "ly_do": "Đóng lô dư lẻ"}, headers=BAI)
        dc3 = r.json()
        dung(r.status_code == 200 and dc3["trang_thai"] == "cho", "lập giảm −9 t (lúc lập lô còn 9,1)", r.status_code)
        r = c.put(url_g, json={"goods": [{"loai": "hang", "goods_name": QUANG, "qty_t": 11, "tu_phieu_id": A.id},
                                         {"loai": "hang", "goods_name": QUANG, "qty_t": 5, "tu_phieu_id": B.id}]}, headers=BAI)
        db.expire_all()
        dung(r.status_code == 200 and KHD.ton_lo(db, A.id) == 8.1, "trong lúc chờ, phiếu giao lấy thêm 1 t → lô A còn 8,1", r.status_code)
        r = c.post("%s/%s/duyet" % (url_dc, dc3["id"]), json={"dong_y": True}, headers=SEP)
        db.expire_all()
        dung(r.status_code == 409 and ma(r) == "VUOT_TON" and db.get(M.DieuChinhHang, dc3["id"]).trang_thai == "cho"
             and KHD.ton_lo(db, A.id) == 8.1, "duyệt mà tồn lô âm → 409, đơn vẫn chờ, sổ nguyên", r.json().get("detail"))
        r = c.get("/api/kho-hang/lo/" + A.id, headers=BAI)
        d = r.json()
        dung(r.status_code == 200 and [z["trang_thai"] for z in d["dieu_chinh"]] == ["da_duyet", "tu_choi", "cho"]
             and d["lo"]["tan_dieu_chinh"] == -0.5 and d["lo"]["ton"] == 8.1 and d["xuat"][0]["tan"] == 11
             and d["dieu_chinh"][0]["so_phieu"] == x["so_phieu"], "chi tiết lô: 3 đơn (duyệt · từ chối · chờ), điều chỉnh −0,5, tồn 8,1",
             [(z["trang_thai"], z["tan"]) for z in d["dieu_chinh"]])
        r = c.get("/api/kho-hang/ton", params={"q": A.doc_no}, headers=BAI)
        it = [z for z in r.json()["items"] if z["lo_id"] == A.id]
        dung(it and it[0]["tan_dieu_chinh"] == -0.5 and it[0]["ton"] == 8.1 and it[0]["ton"] == ton_cu(db, A.id),
             "tồn: điều chỉnh vào tồn lô, khớp cách tính cũ", it)

        # ================================================================ 5. xoá DO
        print("== 5. Xoá DO → rút tờ")
        r = c.delete("/api/trips/" + A.id, headers=SEP)
        dung(r.status_code == 409 and ma(r) == "LO_DA_XUAT", "xoá DO gom A khi G đã lấy hàng → 409 LO_DA_XUAT", (r.status_code, ma(r)))
        r = c.delete("/api/trips/" + G.id, headers=BAI)
        db.expire_all()
        dung(r.status_code == 200 and not db.query(M.ChungTu).filter(M.ChungTu.loai == "PXK_HH", M.ChungTu.nguon_id == G.id).count()
             and not db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == G.id).count()
             and KHD.ton_lo(db, A.id) == 19.1 and KHD.ton_lo(db, B.id) == 14.8,
             "xoá DO giao G → rút PXK_HH, gỡ phần xuất, lô A về 19,1 · B về 14,8", (r.status_code, r.json().get("detail")))
        to_dc_id = dc_to[0].id
        r = c.delete("/api/trips/" + A.id, headers=SEP)
        db.expire_all()
        dung(r.status_code == 200 and not db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_id == A.id).count()
             and db.get(M.ChungTu, to_dc_id) is None and not db.query(M.GoodsMove).filter(M.GoodsMove.lo_trip_id == A.id).count()
             and not db.query(M.DieuChinhHang).filter(M.DieuChinhHang.lo_trip_id == A.id).count(),
             "xoá DO gom A → rút PNK_HH + DC_HH, xoá dòng sổ + đơn điều chỉnh của lô", (r.status_code, r.json().get("detail")))
        to_b = db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_id == B.id).one()
        to_b.da_day = True
        db.commit()
        r = c.delete("/api/trips/" + B.id, headers=BAI)
        db.expire_all()
        giu = db.get(M.ChungTu, to_b.id)
        dung(r.status_code == 200 and giu is not None and giu.trip_id is None and not db.query(M.GoodsMove).filter(M.GoodsMove.lo_trip_id == B.id).count(),
             "xoá DO gom B có PNK_HH đã đối chiếu → tờ giữ lại (như mọi tờ đã đối chiếu), sổ gỡ", (r.status_code, giu and giu.so))

        # ================================================================ 6. DO cũ thiếu tờ: báo tới lại / lưu lại · công cụ sinh bù
        print("== 6. Tờ theo DO idempotent · công cụ sinh bù (tools/may_thu/sinh_bu_to_kho_hang.py)")
        import importlib.util
        spec = importlib.util.spec_from_file_location("sinh_bu_to_kho_hang", os.path.join(GOC, "tools", "may_thu", "sinh_bu_to_kho_hang.py"))
        SB = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(SB)

        def so_to(loai, tid):
            return db.query(M.ChungTu).filter(M.ChungTu.loai == loai, M.ChungTu.nguon_bang == "trips", M.ChungTu.nguon_id == tid).count()
        g1 = db.query(M.Trip).filter(M.Trip.doc_no == "G4-0001-10/EPL").one()
        t1 = db.query(M.Trip).filter(M.Trip.doc_no == "T4-0001-10/EPL").one()
        ton_g1 = KHD.ton_lo(db, g1.id)
        n_in = db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == g1.id, M.GoodsMove.kind == "in").count()
        dung(so_to("PNK_HH", g1.id) == 0 and so_to("PXK_HH", t1.id) == 0 and n_in == 1, "d7: G4-0001 đã nhập, T4-0001 đã xuất, chưa có tờ")
        url1 = "/api/trips/%s/transport-status" % g1.id
        r = c.post(url1, json={"status": "arrived", "weight_dest": g1.weight_dest}, headers=SEP)
        db.expire_all()
        pl1 = json.loads(db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_id == g1.id).one().payload) \
            if so_to("PNK_HH", g1.id) == 1 else {}
        dung(r.status_code == 200 and so_to("PNK_HH", g1.id) == 1 and pl1.get("sinh_bu") is True and pl1.get("tan") == 39.6
             and db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == g1.id, M.GoodsMove.kind == "in").count() == 1
             and KHD.ton_lo(db, g1.id) == ton_g1, "báo tới lại DO gom đã nhập → sinh PNK_HH từ sổ (39,6 t), KHÔNG nhập trùng, tồn nguyên",
             (r.status_code, r.json().get("detail"), pl1))
        r = c.post(url1, json={"status": "arrived", "weight_dest": g1.weight_dest}, headers=SEP)
        db.expire_all()
        dung(r.status_code == 200 and so_to("PNK_HH", g1.id) == 1, "báo tới lần nữa → vẫn một tờ", r.status_code)
        r = c.put("/api/trips/" + t1.id, json={}, headers=SEP)
        db.expire_all()
        to1 = db.query(M.ChungTu).filter(M.ChungTu.loai == "PXK_HH", M.ChungTu.nguon_id == t1.id).all()
        pl = json.loads(to1[0].payload) if to1 else {}
        dung(r.status_code == 200 and len(to1) == 1 and pl.get("tan") == 39.6 and pl.get("sinh_bu") is True
             and db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == t1.id, M.GoodsMove.kind == "out").count() == 1,
             "lưu lại DO giao đã xuất → sinh PXK_HH từ sổ, phần xuất nguyên", (r.status_code, r.json().get("detail"), pl.get("dong")))
        r = c.put("/api/trips/" + t1.id, json={}, headers=SEP)
        db.expire_all()
        dung(r.status_code == 200 and so_to("PXK_HH", t1.id) == 1, "lưu lại lần nữa → vẫn một tờ", r.status_code)

        lk = SB.liet_ke(db)
        so_lk = {x["do_no"]: x["loai"] for x in lk}
        dung(so_lk.get("G4-0006-10/EPL") == "PNK_HH" and so_lk.get("G4-0007-10/EPL") == "PNK_HH"
             and "G4-0001-10/EPL" not in so_lk and "T4-0001-10/EPL" not in so_lk, "công cụ liệt kê: G4-0006 / G4-0007 thiếu PNK_HH", so_lk)
        dem_truoc = db.query(M.ChungTu).count()
        db.expire_all()
        dung(db.query(M.ChungTu).count() == dem_truoc, "liệt kê không ghi gì")
        kq = SB.sinh_bu(db)
        db.commit()
        db.expire_all()
        sinh = {x["do_no"]: x for x in kq["da_sinh"]}
        ok = True
        for so, tan, boc in (("G4-0006-10/EPL", 39.5, 40.0), ("G4-0007-10/EPL", 37.6, 38.0)):
            p = db.query(M.Trip).filter(M.Trip.doc_no == so).one()
            ds = db.query(M.ChungTu).filter(M.ChungTu.loai == "PNK_HH", M.ChungTu.nguon_id == p.id).all()
            x = json.loads(ds[0].payload) if len(ds) == 1 else {}
            mv = db.query(M.GoodsMove).filter(M.GoodsMove.trip_id == p.id, M.GoodsMove.kind == "in").all()
            ok = ok and so in sinh and len(ds) == 1 and ds[0].so == sinh[so]["so"] and x.get("tan") == tan and x.get("boc_len") == boc \
                and abs((x.get("hao_hut") or 0) - round(boc - tan, 3)) < 1e-9 and x.get("sinh_bu") is True and ds[0].tien == 0 \
                and ds[0].ngay == mv[0].move_date and ds[0].by_user and len(mv) == 1
        dung(ok and kq["so_thieu"] == len(lk) and len(kq["da_sinh"]) == len(lk) and not kq["bo_qua"],
             "sinh bù: G4-0006 (39,5 · mỏ 40) / G4-0007 (37,6 · mỏ 38) đủ tờ, ngày = ngày sổ, tiền 0", sinh)
        dem = db.query(M.ChungTu).count()
        lk2 = SB.liet_ke(db)
        kq2 = SB.sinh_bu(db)
        db.expire_all()
        dung(lk2 == [] and kq2["so_thieu"] == 0 and not kq2["da_sinh"] and db.query(M.ChungTu).count() == dem,
             "chạy lại: không còn DO thiếu, không sinh trùng", (len(lk2), kq2["so_thieu"]))
        for ngay in (hom_nay.isoformat(), "2026-10-03"):
            r = c.get("/api/kho-hang/doi-soat", params={"ngay": ngay}, headers=KT_VC)
            d = r.json()
            dung(r.status_code == 200 and d["lech"] == [] and d["phieu_nhap"] >= 1 and d["do_gom_da_toi"] >= 1,
                 "đối soát %s: hết lệch" % ngay, d)
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
