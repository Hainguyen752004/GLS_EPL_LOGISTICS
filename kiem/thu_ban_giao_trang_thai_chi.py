# -*- coding: utf-8 -*-
"""Thử 06/10 — bàn giao DO B1 / B2 trả cả DO ĐANG CHẠY (`scope`) và viên TRẠNG THÁI CHI (`payment_status`) cho Web anh Tune
(routes/ban_giao.py, services/ban_giao.py: trang_thai_do · trang_thai_chi) trên bản sao _d7.

    python kiem/thu_ban_giao_trang_thai_chi.py

MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK: không ghi gì vào d7. Gọi qua FastAPI TestClient
(khoá máy thật: đặt khoá thử TRONG giao dịch), không chạy sự kiện khởi động, không gọi mạng. Dữ liệu dựa trên d7 ngày 06/10:
  G4-0008 xe nhà đang chạy (tạm ứng 202.222 LAK → phiếu chi "Chi trước" chờ thủ quỹ; tiền nước, tiền ăn cùng lương; 360 L kho)
  G4-0006 xe nhà đã khoá (dầu + lốp kho có bút toán; tiền nước, tiền chuyến cùng lương — chưa vào chứng từ nào bên em)
  G4-0007 xe thuê đã khoá (dầu kho xuất bán → SO nhiên liệu; chưa đề nghị trả chủ xe)
Phần 5 dựng trạng thái trong giao dịch (thủ quỹ đã chi, phiếu chi lỗi, phiếu mục V–VI, đề nghị trả chủ xe) để thấy viên đổi.
"""
import os
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ.setdefault("EPL_LAO_LAM_NONG", "0")
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import json                                             # noqa: E402

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, event, text       # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import ban_giao as BG                     # noqa: E402
from services import day_ke_toan as DK                  # noqa: E402

KQ = []
KHOA = "khoa-thu-trang-thai-chi-0610"
B1 = "/api/handover/delivery-orders"
CHU_VIEN = {"code", "lines_total", "lines_with_voucher", "lines_paid", "amount_open", "currency", "open_line_keys", "owner_payment"}


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:400]) if ct != "" else ""))


def tu_goi(goi):
    """payment_status suy NGƯỢC từ settlement từng dòng của gói B2 — để đối chiếu với bản tính gộp (trang_thai_chi).
    Dòng đếm: dòng chi không lấy kho, state ≠ not_payable. Xong: phiếu chi "da_chi", bút toán đã nhận (journal da_gui)."""
    p = goi["header"]["line_key_prefix"]
    dem = [x for x in goi["details"] if x["kind"] == "chi" and x.get("source") != "kho" and x["settlement"]["state"] != "not_payable"]

    def xong(s):
        return s["state"] == "has_voucher" and (s["doc_status"] == "da_chi" or (s["kind"] == "journal" and s["doc_status"] == "da_gui"))
    co = sum(1 for x in dem if x["settlement"]["state"] == "has_voucher")
    da = sum(1 for x in dem if xong(x["settlement"]))
    return {"code": BG._ma_chi(len(dem), co, da), "lines_total": len(dem), "lines_with_voucher": co, "lines_paid": da,
            "amount_open": sum(x["amount_lak"] for x in dem if not xong(x["settlement"])),
            "open_line_keys": sorted(p + x["line_key"] for x in dem if x["settlement"]["state"] == "open")}


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))   # 8011 chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
    import _bo_cu_0610 as BO_CU                         # 06/10: d7 dọn + gieo lại → dựng bộ dữ liệu bài viết theo TRONG giao dịch
    BO_CU.dat_bo_cu(conn)
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)
    dem_sql = [0]
    event.listen(conn, "before_cursor_execute", lambda *a, **k: dem_sql.__setitem__(0, dem_sql[0] + 1))

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    H = {"Authorization": "Bearer " + KHOA}

    def ds(**tham):
        r = c.get(B1, params=dict({"page_size": 200}, **tham), headers=H)
        return r, (r.json().get("data") or {}) if r.status_code == 200 else {}

    def theo_so(items):
        return {x["doc_no"]: x for x in items}
    try:
        DK.dat_cau_hinh(db, "token_nhan_qlsx", KHOA)
        db.commit()
        tat_ca = db.query(M.Trip).all()
        xong = [p for p in tat_ca if BG.ban_giao_duoc(p)]
        p8 = db.query(M.Trip).filter(M.Trip.doc_no == "G4-0008-10/EPL").one()
        p6 = db.query(M.Trip).filter(M.Trip.doc_no == "G4-0006-10/EPL").one()
        p7 = db.query(M.Trip).filter(M.Trip.doc_no == "G4-0007-10/EPL").one()

        print("== 1. khoá máy")
        dung(c.get(B1, params={"scope": "all"}).status_code == 401, "B1 scope=all không khoá → 401")
        dung(c.get(B1 + "/EPLLAO-" + p8.id).status_code == 401, "B2 DO đang chạy không khoá → 401")

        print("== 2. scope")
        r, d = ds()
        so = theo_so(d["items"])
        dung(r.status_code == 200 and d["total"] == len(xong) and d["scope"] == "done"
             and all(x["status"] == "delivered" for x in d["items"]) and "G4-0008-10/EPL" not in so,
             "mặc định = done: chỉ DO đã về + đã khoá, như trước 06/10", (d.get("total"), len(xong)))
        ngay = [x["completed_at"] for x in d["items"]]
        dung(ngay == sorted(ngay, reverse=True), "mặc định vẫn mới khoá trước")
        r, d = ds(scope="all")
        so_all = theo_so(d["items"])
        x8 = so_all.get("G4-0008-10/EPL") or {}
        dung(r.status_code == 200 and d["total"] == len(tat_ca) and x8.get("status") == "in_transit"
             and x8.get("transport_status") == "dispatched" and x8.get("locked") is False and x8.get("completed_at") is None,
             "scope=all: mọi DO; G4-0008 status in_transit, chưa khoá", {k: x8.get(k) for k in ("status", "transport_status", "locked")})
        chua = [x["locked"] for x in d["items"]]
        dung(chua == sorted(chua), "scope=all: DO chưa khoá đứng trước DO đã khoá", chua)
        r, d = ds(scope="open")
        dung(r.status_code == 200 and d["total"] == len(tat_ca) - len(xong) and all(x["status"] != "delivered" for x in d["items"])
             and "G4-0008-10/EPL" in theo_so(d["items"]), "scope=open: chỉ DO chưa xong", d.get("total"))
        r, _ = ds(scope="xyz")
        dung(r.status_code == 422 and r.json()["detail"]["ma"] == "SCOPE_SAI", "scope lạ → 422 SCOPE_SAI", r.status_code)
        r, d = ds(scope="ALL", q="G4-0008")
        dung([x["doc_no"] for x in d.get("items", [])] == ["G4-0008-10/EPL"] and d["total"] == 1, "q + scope (không phân biệt hoa thường)",
             d.get("total"))
        r, d = ds(scope="all", completed_from="2026-01-01")
        dung(r.status_code == 200 and all(x["locked"] for x in d["items"]) and d["total"] == len(xong),
             "lọc ngày khoá trên scope=all: DO chưa khoá rơi ra", d.get("total"))

        print("== 3. viên trạng thái chi trên từng dòng B1")
        r, d = ds(scope="all")
        so_all = theo_so(d["items"])
        hong = [x["doc_no"] for x in d["items"] if not (
            set(x["payment_status"] or {}) == CHU_VIEN and x["payment_status"]["code"] in BG.TRANG_THAI_CHI
            and x["payment_status"]["currency"] == "LAK"
            and 0 <= x["payment_status"]["lines_paid"] <= x["payment_status"]["lines_with_voucher"] <= x["payment_status"]["lines_total"]
            and x["payment_status"]["code"] == BG._ma_chi(x["payment_status"]["lines_total"], x["payment_status"]["lines_with_voucher"],
                                                          x["payment_status"]["lines_paid"]))]
        dung(not hong, "mọi dòng có đủ khoá giao ước, mã khớp số đếm", hong)
        v8 = so_all["G4-0008-10/EPL"]["payment_status"]
        e8 = {d_.item_key: d_ for d_ in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p8.id)}
        mo8 = sorted("DO:EPLLAO-%s:exp:%s" % (p8.id, e8[k].id) for k in ("x_water", "x_food"))
        dung(v8["code"] == "dang_chi" and (v8["lines_total"], v8["lines_with_voucher"], v8["lines_paid"]) == (5, 3, 0)
             and v8["amount_open"] == 562222 and sorted(v8["open_line_keys"]) == mo8 and v8["owner_payment"] is None,
             "G4-0008: đang chi — 3 dòng tạm ứng có phiếu Chi trước (chưa ghi sổ), 2 dòng cùng lương mở; dầu kho không đếm",
             {k: v8[k] for k in ("code", "lines_total", "lines_with_voucher", "lines_paid", "amount_open")})
        v6 = so_all["G4-0006-10/EPL"]["payment_status"]
        dung(v6["code"] == "chua_chi" and (v6["lines_total"], v6["lines_with_voucher"]) == (2, 0) and v6["amount_open"] == 1860000
             and len(v6["open_line_keys"]) == 2,
             "G4-0006: bên em chưa chi (2 dòng cùng lương mở) — phiếu Web lập theo DO, Web tự gộp qua open_line_keys", v6["code"])
        v7 = so_all["G4-0007-10/EPL"]["payment_status"]
        o7 = v7["owner_payment"] or {}
        dung(v7["code"] == "khong_co_khoan" and v7["lines_total"] == 0 and o7.get("code") == "chua_chi"
             and o7.get("currency") == "USD" and abs((o7.get("amount") or 0) - 352.18) < 0.005,
             "G4-0007 xe thuê: không có khoản EPL chi (dầu kho xuất bán); trả chủ xe 352,18 USD chưa đề nghị", o7)

        print("== 4. B2 chi tiết — DO đang chạy, đối chiếu từng dòng với bản tính gộp")
        r = c.get(B1 + "/EPLLAO-" + p8.id, headers=H)
        h8 = (r.json().get("data") or {}).get("header") or {}
        dung(r.status_code == 200 and h8.get("status") == "in_transit" and h8.get("trip_status") == "in_progress"
             and h8.get("payment_status") == v8, "G4-0008 → 200 (trước 06/10: 409), in_transit, payment_status = dòng B1",
             (r.status_code, h8.get("status")))
        kho8 = [x["settlement"] for x in r.json()["data"]["details"] if x.get("source") == "kho"]
        dung(kho8 and all(s["state"] == "pending" and "ghi lúc khoá DO" in s["label"] and "đối soát" not in s["label"] for s in kho8),
             "G4-0008 dầu kho: nhãn 'bút toán xuất kho ghi lúc khoá DO' (không còn 'khoá trước luật… đối soát')",
             [s["label"] for s in kho8])
        r = c.get(B1 + "/EPLLAO-" + p6.id, headers=H)
        h6 = r.json()["data"]["header"]
        dung(h6["status"] == "delivered" and h6["trip_status"] == "completed", "DO đã khoá vẫn delivered / completed")
        lech = []
        for x in d["items"]:
            g = c.get(x["detail_url"], headers=H).json()["data"]
            ps = x["payment_status"]
            mong = tu_goi(g)
            co = {k: (sorted(ps[k]) if k == "open_line_keys" else ps[k]) for k in mong}
            if co != mong or g["header"]["payment_status"] != ps or g["header"]["status"] != x["status"]:
                lech.append((x["doc_no"], co, mong))
        dung(not lech, "mọi DO: viên B1 = suy từ settlement từng dòng của B2 (%d DO)" % len(d["items"]), lech[:2])
        dung(c.get(B1 + "/EPLLAO-khongco", headers=H).status_code == 404, "mã không có → 404")

        print("== 4b. hai phiếu mẫu THU-KBAZ (kiem/_mau_kbaz.py, dựng trong giao dịch): mục V Chi khác, tất toán tháng, ghi nợ NCC")
        for t in ("gui_so_nhien_lieu_tune", "can_tru_tune"):
            M.Base.metadata.tables[t].create(bind=conn, checkfirst=True)
        sys.path.insert(0, os.path.join(GOC, "kiem"))
        import _mau_kbaz as MAU
        MAU.dung_mau(conn)
        r, dm = ds(scope="all", q="THU-KBAZ")
        lech, loai = [], set()
        for x in dm.get("items", []):
            g = c.get(x["detail_url"], headers=H).json()["data"]
            mong, ps = tu_goi(g), x["payment_status"]
            loai |= {(z["settlement"]["state"], z["settlement"]["kind"]) for z in g["details"] if z["kind"] == "chi"}
            if {k: (sorted(ps[k]) if k == "open_line_keys" else ps[k]) for k in mong} != mong:
                lech.append((x["doc_no"], ps, mong))
        dung(len(dm.get("items", [])) == 2 and not lech and {("has_voucher", "pay_now"), ("pending", "driver_settlement"),
                                                             ("has_voucher", "journal"), ("open", "payroll")} <= loai,
             "THU-KBAZ G1 / T1: viên B1 = suy từ settlement B2 — có cả Chi khác mục V, tất toán, ghi nợ NCC, cùng lương",
             lech[:1] or sorted(loai, key=str))

        print("== 5. trạng thái đổi theo chứng từ (dựng trong giao dịch)")
        rec8 = db.query(M.ChiTune).filter(M.ChiTune.trip_id == p8.id).one()
        rec8.status, rec8.tune_status = "da_chi", 12
        db.commit()
        v = theo_so(ds(scope="all", q="G4-0008")[1]["items"])["G4-0008-10/EPL"]["payment_status"]
        dung((v["code"], v["lines_paid"], v["amount_open"]) == ("dang_chi", 3, 360000),
             "thủ quỹ ghi sổ phiếu Chi trước → 3 dòng đã chi, còn 360.000 (cùng lương)", v)
        rec8.status = "loi"
        db.commit()
        v = theo_so(ds(scope="all", q="G4-0008")[1]["items"])["G4-0008-10/EPL"]["payment_status"]
        dung((v["code"], v["lines_with_voucher"], v["amount_open"]) == ("chua_chi", 0, 562222),
             "phiếu Chi trước lỗi (chưa tạo được) → chưa chi", v)
        e6 = [d_.id for d_ in db.query(M.TripExpense).filter(M.TripExpense.trip_id == p6.id, M.TripExpense.section == "travel")]
        cm = M.ChiMucTune(trip_id=p6.id, section="other", lan=1, expense_ids=json.dumps(e6), ref_no="PCMV-THU-0610",
                          amount_lak=1860000, status="da_gui", document_no="1368-CKH-THU-0610", real_id=1)
        db.add(cm)
        db.commit()
        v = theo_so(ds(q="G4-0006")[1]["items"])["G4-0006-10/EPL"]["payment_status"]
        dung((v["code"], v["lines_with_voucher"], v["lines_paid"], v["open_line_keys"]) == ("dang_chi", 2, 0, []),
             "phiếu Chi khác chờ thủ quỹ → đang chi, không còn dòng mở", v)
        cm.status = "da_chi"
        db.commit()
        v = theo_so(ds(q="G4-0006")[1]["items"])["G4-0006-10/EPL"]["payment_status"]
        dung((v["code"], v["lines_paid"], v["amount_open"]) == ("da_chi", 2, 0), "ghi sổ → đã chi, 0 đồng còn mở", v)
        g6 = c.get(B1 + "/EPLLAO-" + p6.id, headers=H).json()["data"]
        dung(g6["header"]["payment_status"] == v and tu_goi(g6)["code"] == "da_chi", "B2 cùng số với B1 sau khi đổi")
        cx = M.ChiChuXeTune(owner_id=p7.owner_id, trip_ids=json.dumps([p7.id]), currency="USD", amount=352.18,
                            ref_no="TCX-THU-0610", status="da_gui", document_no="1368-CKH-THU-0611")
        db.add(cx)
        db.commit()
        o = theo_so(ds(q="G4-0007")[1]["items"])["G4-0007-10/EPL"]["payment_status"]["owner_payment"]
        dung(o["code"] == "dang_chi" and o["doc_no"] == "1368-CKH-THU-0611" and o["ref_no"] == "TCX-THU-0610",
             "xe thuê: đề nghị trả chủ xe có phiếu chi → owner_payment đang chi", o)
        cx.status = "da_chi"
        db.commit()
        o = theo_so(ds(q="G4-0007")[1]["items"])["G4-0007-10/EPL"]["payment_status"]["owner_payment"]
        dung(o["code"] == "da_chi", "thủ quỹ ghi sổ → owner_payment đã chi", o["code"])

        print("== 6. lọc payment_status")
        r, d = ds(scope="all")
        ma = {x["doc_no"]: x["payment_status"]["code"] for x in d["items"]}
        for loc in ("dang_chi", "chua_chi,khong_co_khoan", "da_chi"):
            r, dl = ds(scope="all", payment_status=loc)
            mong = [k for k in (x["doc_no"] for x in d["items"]) if ma[k] in loc.split(",")]
            dung(r.status_code == 200 and [x["doc_no"] for x in dl["items"]] == mong and dl["total"] == len(mong)
                 and dl["payment_status"] == sorted(loc.split(",")), "payment_status=%s → %d DO, đúng thứ tự" % (loc, len(mong)),
                 [x["doc_no"] for x in dl.get("items", [])])
        r, d1 = ds(scope="all", payment_status="dang_chi,chua_chi,khong_co_khoan,da_chi", page_size=1)
        r2, d2 = ds(scope="all", payment_status="dang_chi,chua_chi,khong_co_khoan,da_chi", page_size=1, page=2)
        dung(d1["total"] == d2["total"] == len(ma) and d1["items"][0]["doc_no"] != d2["items"][0]["doc_no"],
             "lọc + chia trang: total giữ, trang 2 khác trang 1", d1.get("total"))
        r, _ = ds(payment_status="xong_roi")
        dung(r.status_code == 422 and r.json()["detail"]["ma"] == "TRANG_THAI_CHI_SAI", "mã lạ → 422", r.status_code)

        print("== 7. không N+1: số câu SQL không tăng theo số DO trên trang")
        so_cau = {}
        for co in (2, 200):
            ds(scope="all", page_size=co)                   # lần đầu nạp bộ nhớ một yêu cầu (danh mục NCC…) — đếm lần sau
            dem_sql[0] = 0
            r, d = ds(scope="all", page_size=co)
            so_cau[co] = (dem_sql[0], len(d["items"]))
        # chênh tối đa 6 câu có điều kiện, không theo số DO: phụ tùng · phiếu Chi trước · đề nghị trả chủ xe (trang có xe thuê) ·
        # tất toán (bản chốt · phiếu · bút toán QT_TU) — N+1 thì trang 9 DO hơn trang 2 DO hàng chục câu
        dung(so_cau[200][0] - so_cau[2][0] <= 6, "trang 2 DO: %d câu · trang %d DO: %d câu" % (
            so_cau[2][0], so_cau[200][1], so_cau[200][0]), so_cau)
        dem_sql[0] = 0
        r, d = ds(scope="all", payment_status="dang_chi")
        dung(dem_sql[0] <= so_cau[200][0] + 2, "lọc payment_status trên mọi DO: %d câu" % dem_sql[0])
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
