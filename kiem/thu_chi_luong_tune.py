# -*- coding: utf-8 -*-
"""Thử 06/10 — TRẢ CÙNG LƯƠNG theo phiếu chi lương THẬT (services/chi_luong_tune.py, loại "chi_luong" của services/dong_bo_nen.py,
báo cáo GET /api/bao-cao/tien-tai-xe) trên bản sao _d7.

    python kiem/thu_chi_luong_tune.py

Em chính chốt 06/10: tiền chưa trả cho tài xế thì báo cáo không được ghi "đã chi" — dòng cùng lương chỉ "đã trả" khi phiếu chi lương
bên kế toán anh Tune (lập trên Web theo DO, gộp dòng theo khoá B2) đã ghi sổ; trước đó "Chờ trả cùng lương".

MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK: không ghi gì vào d7 (kể cả bảng mới chi_luong_tune — dựng
trong giao dịch nếu d7 chưa có). KHÔNG gọi mạng: chi_tune._goi thay bằng bản giả lập — đường mới POST …/line-vouchers trả phiếu
theo khoá như API thật (DO "B": 2 dòng → phiếu ST 12; DO "D1" tiền chuyến → phiếu ST 1), cùng các đường ĐỌC các loại khác của
lượt đã dùng (phiếu chi, công nợ, danh mục đối tượng); gọi đường nào khác là bài hỏng.

ĐỘC LẬP dữ liệu d7 (06/10 — d7 dọn rồi gieo lại thì bài cũ bám G4-0001 … G4-0008 hỏng): bài TỰ DỰNG DO, mục IV, dòng chi trong giao
dịch, vào một THÁNG d7 chưa có DO nào (tìm lùi từ 09/2026), như kiem/thu_kho_hang.py; dòng cùng lương của DO sẵn có trong d7 được
đánh "đã trả" TRONG giao dịch để lượt hỏi chỉ thấy dòng của bài. Bảy DO dựng (cùng khuôn bộ dữ liệu cũ):
    A  (≈ G4-0001) xe nhà, mục IV ghi sổ: nước + chuyến (mặc định luong) · điện thoại, ăn (mặc định tiền mặt) · cầu đường
    B  (≈ G4-0006) xe nhà, mục IV "đã chi" (tự qua): nước + chuyến
    C  (≈ G4-0005) xe nhà, mục IV "đã chi": nước + chuyến
    D1 (≈ G4-0004) xe nhà, mục IV ghi sổ: nước + chuyến — cùng tài xế với D2
    D2 (≈ G4-0008) xe nhà: nước mặc định + ăn chọn luong; tiền chuyến chọn tiền mặt thì không vào
    E  (≈ T4-0001) phiếu giao xe nhà: nước + chuyến
    T  (≈ G4-0002/0003/0007) xe THUÊ: nước + chuyến chọn luong — không vào (EPL không trả lương tài xế của chủ xe)
→ 12 dòng chờ hỏi, tổng 9.660.000 LAK (như bộ cũ).
"""
import os
import sys
import types

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import datetime as dt                                   # noqa: E402

from fastapi import HTTPException                       # noqa: E402
from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
import routes.bao_cao as B                              # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import chi_luong_tune as CL               # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import dong_bo_nen as DBN                 # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402
from services.bao_mat import nguoi_hien_tai             # noqa: E402

KQ = []
GOI = []
PHIEU = {}                                              # khoá dòng → [Item như API thật]
LOI = {"kieu": None}                                    # None · 5xx · 404 (đường line-vouchers)
NO = []                                                 # công nợ khách / đối tác giả lập: mọi SO (cước, nhiên liệu) còn nợ đủ
SO_6 = "1368-CKH-261006-00001"                          # số phiếu giả lập (khuôn phiếu Web lập theo DO, ghi sổ 06/10 09:04:55)


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:500]) if ct != "" else ""))


def gia_goi(method, duong, body=None):
    """Bản giả lập chi_tune._goi — đường line-vouchers + các đường ĐỌC của các loại khác trong lượt."""
    d = duong.split("?")[0]
    GOI.append((method, d, len((body or {}).get("Keys") or []) if d == CL.DUONG else None))
    if method == "POST" and d == CL.DUONG:
        if LOI["kieu"] == "5xx":
            raise HTTPException(502, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "Hệ kế toán trả HTTP 500: giả lập", "http": 500})
        if LOI["kieu"] == "404":
            raise HTTPException(422, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "Hệ kế toán trả HTTP 404: giả lập (API chưa có đường)",
                                      "http": 404})
        keys = body["Keys"]
        assert 0 < len(keys) <= CL.LO, len(keys)
        return {"KeyCount": len(set(keys)), "Items": [dict(it, Key=k) for k in keys for it in PHIEU.get(k, [])]}
    if method == "GET" and d.startswith("/api/v1/accounting/cmpayment-receipt/"):
        return {"Master": {"STATUS": 1}}                       # phiếu Chi trước / Chi khác / trả chủ xe… vẫn chờ thủ quỹ
    if method == "POST" and d == "/api/v1/sales/debt/customer-detail":
        return {"Summary": {}, "Aging": [], "Debts": NO, "Orders": [], "Collections": []}
    if method == "POST" and d.startswith("/api/v1/master-data/") and d.endswith("/list"):
        return {"Data": [{"ObjId": 7777, "ObjectNo": (body or {}).get("ObjKey")}]}
    raise AssertionError("không được gọi %s %s" % (method, duong))


def gia_goi_nl(method, duong, body_json=None, key=None):
    raise AssertionError("SO nhiên liệu đọc qua công nợ đối tác, không gọi %s %s" % (method, duong))


def item(so, doc, st, tien, luc=None):
    return {"DocumentId": doc, "VoucherNo": so, "StatusId": st, "Posted": st in (12, 13), "PostedAt": luc,
            "BaseAmount": tien, "CurrencyId": 26 if luc else None}


def dung_du_lieu(db):
    """Dựng 7 DO thử (xem đầu tệp) trong giao dịch, ở một tháng d7 chưa có DO. → ('YYYY-MM', {tên: Trip}, (ngày D1, ngày D2))."""
    co = {d.strftime("%Y-%m") for (d,) in db.query(M.Trip.doc_date).filter(M.Trip.doc_date.isnot(None)).distinct()}
    nam, th = 2026, 9
    while "%04d-%02d" % (nam, th) in co:
        nam, th = (nam, th - 1) if th > 1 else (nam - 1, 12)

    def ngay(d):
        return dt.date(nam, th, d)
    tx = {}
    for k in ("A", "B", "C", "D", "E", "T"):
        tx[k] = M.Driver(name="ທ້າວ ທົດລອງ %s" % k, name_latin="Thu luong %s" % k)
        db.add(tx[k])
    db.flush()
    khuon = {   # tên: (loại, ngày, công ty, tài xế, trạng thái mục IV, [(khoản, tiền, cách trả chọn)])
        "A": ("gom", 1, "EPL", "A", "booked", [("x_water", 60000, None), ("x_trip", 1800000, None), ("x_phone", 150000, None),
                                               ("x_food", 100000, None), ("x_bridge", 50000, None)]),
        "B": ("gom", 2, "EPL", "B", "paid", [("x_water", 60000, None), ("x_trip", 1800000, None)]),
        "D1": ("gom", 3, "EPL", "D", "booked", [("x_water", 60000, None), ("x_trip", 1800000, None)]),
        "C": ("gom", 4, "EPL", "C", "paid", [("x_water", 60000, None), ("x_trip", 1800000, None)]),
        "D2": ("gom", 5, "EPL", "D", "booked", [("x_water", 60000, None), ("x_food", 300000, "luong"),
                                                ("x_trip", 1800000, "tien_mat"), ("x_phone", 150000, None)]),
        "E": ("giao", 5, "EPL", "E", "booked", [("x_water", 60000, None), ("x_trip", 1800000, None)]),
        "T": ("gom", 2, "joint", "T", "booked", [("x_water", 60000, "luong"), ("x_trip", 1800000, "luong")]),
    }
    do = {}
    for ten, (loai, d, cty, t, st, dong) in khuon.items():
        p = M.Trip(doc_no="THU-CL-%s-%02d/%04d" % (ten, th, nam), kind=loai, doc_date=ngay(d), out_date=ngay(d), company=cty,
                   driver_id=tx[t].id, driver_name=tx[t].name, truck_no="THU-%s" % ten,
                   owner_name="ເຈົ້າຂອງລົດ ທົດລອງ" if cty == "joint" else None, transport_status="arrived")
        db.add(p)
        db.flush()
        db.add(M.TripSection(trip_id=p.id, section="travel", status=st))
        for i, (khoan, tien, cach) in enumerate(dong, 1):
            db.add(M.TripExpense(trip_id=p.id, section="travel", line_no=i, item_key=khoan, qty=1, unit_price=tien, currency="LAK",
                                 paid_by_epl=True, pay_channel=cach))
        do[ten] = p
    db.flush()
    return "%04d-%02d" % (nam, th), do, (ngay(3).isoformat(), ngay(5).isoformat())


def gac_du_lieu_san(db):
    """Dòng cùng lương của DO SẴN CÓ trong d7 (bộ gieo) → đánh "đã trả" TRONG giao dịch (ROLLBACK trả lại): lượt hỏi chỉ thấy dòng
    của bài. → số dòng đã gác."""
    ds = CL.dong_cho(db, 100000)
    co = {r.line_id: r for r in db.query(M.ChiLuongTune).filter(M.ChiLuongTune.line_id.in_([x[0] for x in ds]))} if ds else {}
    for lid, tid, _ngay in ds:
        r = co.get(lid) or M.ChiLuongTune(line_id=lid, trip_id=tid, line_key=CL.khoa_dong(tid, lid))
        r.status, r.voucher_no, r.tune_status = "da_tra", "GAC-TRUOC-BAI", 12
        db.add(r)
    db.flush()
    return len(ds)


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    M.ChiLuongTune.__table__.create(conn, checkfirst=True)    # d7 chưa chạy máy chủ bản mới thì dựng trong giao dịch (ROLLBACK)
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    goc_goi, goc_nl, goc_tn = CHI._goi, NL._goi, B._theo_ngay
    CHI._goi, NL._goi = gia_goi, gia_goi_nl
    # Bộ đệm báo cáo đọc / ghi bằng KẾT NỐI RIÊNG (ngoài giao dịch thử) — trong bài này tính thẳng từng ngày (cùng _tx_lo)
    B._theo_ngay = lambda db_, loai, cac_ngay, tinh_lo: tinh_lo(db_, cac_ngay)
    cu_bat = os.environ.get("EPL_DONG_BO_CHI_LUONG")
    gac = gac_du_lieu_san(db)
    THANG, DO, (NGAY_D1, NGAY_D2) = dung_du_lieu(db)
    db.commit()
    ID_BAI = [p.id for p in DO.values()]
    print("== chuẩn bị: 7 DO thử tháng %s, gác %d dòng cùng lương của DO sẵn có trong d7 (trong giao dịch)" % (THANG, gac))

    def phieu(ten):
        return DO[ten]

    def cua_bai():
        return db.query(M.ChiLuongTune).filter(M.ChiLuongTune.trip_id.in_(ID_BAI)).all()

    def dong(ten, khoan):
        p = phieu(ten)
        return db.query(M.TripExpense).filter(M.TripExpense.trip_id == p.id, M.TripExpense.section == "travel",
                                              M.TripExpense.item_key == khoan).one()

    def pb(ngay):
        return int(db.execute(text("SELECT so FROM phien_ban_thang WHERE khoa = :k"), {"k": ngay}).scalar() or 0)

    def bao_cao(vai="expacct"):
        app.dependency_overrides[nguoi_hien_tai] = lambda: types.SimpleNamespace(
            role=vai, full_name="Thử", username="thu", id="t", driver_id=None, place_id=None)
        g = c.get("/api/bao-cao/tien-tai-xe?thang=" + THANG)
        return g.status_code, (g.json() if g.status_code == 200 else g.text)
    try:
        print("== 0. cờ bật")
        os.environ.pop("EPL_DONG_BO_CHI_LUONG", None)
        dung(not CL.bat() and "chi_luong" not in dict(DBN._viec()), "mặc định TẮT: lượt không có loại chi_luong (API chưa có đường)")
        os.environ["EPL_DONG_BO_CHI_LUONG"] = "1"
        dung(CL.bat() and list(dict(DBN._viec()))[-1] == "chi_luong", "EPL_DONG_BO_CHI_LUONG=1 → chi_luong là loại CUỐI lượt")

        print("== 1. dòng chờ hỏi: cùng lương · xe nhà · mục IV đã ghi sổ · khoản tài xế")
        mong = {dong(s, k).id for s, k in (("A", "x_water"), ("A", "x_trip"), ("D1", "x_water"), ("D1", "x_trip"),
                                            ("C", "x_water"), ("C", "x_trip"), ("B", "x_water"), ("B", "x_trip"),
                                            ("D2", "x_water"), ("D2", "x_food"), ("E", "x_water"), ("E", "x_trip"))}
        co = {x[0] for x in CL.dong_cho(db, 500)}
        dung(co == mong, "đúng 12 dòng — không có xe thuê, tiền mặt (D2 tiền chuyến, điện thoại, ăn mặc định), cầu đường",
             sorted(co ^ mong))
        d6n, d6c = dong("B", "x_water"), dong("B", "x_trip")
        k6n, k6c = CL.khoa_dong(d6n.trip_id, d6n.id), CL.khoa_dong(d6c.trip_id, d6c.id)
        dung((k6n, k6c) == ("DO:EPLLAO-%s:exp:%s" % (d6n.trip_id, d6n.id), "DO:EPLLAO-%s:exp:%s" % (d6c.trip_id, d6c.id)),
             "khoá dòng đúng khuôn B2 DO:EPLLAO-<DO>:exp:<dòng> (trùng khoá Web gộp vào phiếu thật)", (k6n, k6c))

        # API giả lập: DO B hai dòng nằm phiếu ST 12; DO D1 tiền chuyến nằm phiếu ST 1 (lập, chưa ghi sổ)
        d4c = dong("D1", "x_trip")
        k4c = CL.khoa_dong(d4c.trip_id, d4c.id)
        PHIEU.update({k6n: [item(SO_6, 81534, 12, 60000, "2026-10-06T09:04:55.42")],
                      k6c: [item(SO_6, 81534, 12, 1800000, "2026-10-06T09:04:55.42")],
                      k4c: [item("1368-CKH-261006-00009", 99009, 1, 1800000)]})
        NO[:] = [{"OrderCode": b.order_code, "RETK_PAYMENTAMOUNT": 1, "RCTD_DEBTMONEY": 1, "RETK_MONEYPAID": 0, "CurrencyCode": "USD"}
                 for b in (db.query(M.GuiSoTune).filter(M.GuiSoTune.order_code.isnot(None)).all()
                           + db.query(M.GuiSoNhienLieuTune).filter(M.GuiSoNhienLieuTune.order_code.isnot(None)).all())]

        print("== 2. báo cáo TRƯỚC khi đồng bộ: mọi dòng chờ (kể cả C / B mục IV đã 'đã chi')")
        s, r0 = bao_cao()
        t0 = r0.get("tong", {}) if s == 200 else {}
        dung(s == 200 and t0.get("da_tra_lak") == 0 and t0.get("cho_tra_lak") == t0.get("tong_lak") == 9660000
             and all(x["trang_thai"] == "unpaid" for x in r0["rows"]),
             "chưa có phiếu đã ghi sổ → 0 đã trả, 9.660.000 chờ trả cùng lương, không tài xế nào 'đã trả'", t0)

        print("== 3. một lượt đồng bộ nền")
        GOI.clear()
        k = DBN.mot_luot(db)
        db.expire_all()
        lv = [g for g in GOI if g[1] == CL.DUONG]
        dung(not k["loi"] and not k["loi_ban_ghi"] and k["da_hoi"].get("chi_luong") == 12 and k["cap_nhat"].get("chi_luong") == 2,
             "lượt sạch: hỏi 12 dòng cùng lương, 2 dòng đổi trạng thái", {x: k[x] for x in ("da_hoi", "cap_nhat", "loi", "loi_ban_ghi")})
        dung(lv == [("POST", CL.DUONG, 12)], "MỘT lời gọi line-vouchers cho cả lô 12 khoá", lv)
        la = sorted({g[:2] for g in GOI if g[1] != CL.DUONG and not g[1].startswith("/api/v1/accounting/cmpayment-receipt/")})
        dung(set(la) <= {("POST", "/api/v1/sales/debt/customer-detail")}, "chỉ gọi đường ĐỌC — không tạo / xoá gì", la)
        r6n, r6c = db.get(M.ChiLuongTune, d6n.id), db.get(M.ChiLuongTune, d6c.id)
        dung(all(x is not None and x.status == "da_tra" and x.voucher_no == SO_6 and x.tune_status == 12
                 and x.posted_at == dt.datetime(2026, 10, 6, 2, 4, 55) for x in (r6n, r6c)),
             "DO B: phiếu %s ST 12 → hai dòng 'đã trả', lúc ghi sổ quy UTC 02:04:55" % SO_6,
             [(x.status, x.voucher_no, x.posted_at) for x in (r6n, r6c) if x])
        r4c = db.get(M.ChiLuongTune, d4c.id)
        dung(r4c is not None and r4c.status == "cho" and r4c.tune_status == 1 and r4c.posted_at is None,
             "DO D1 tiền chuyến: phiếu ST 1 (chưa ghi sổ) → vẫn chờ", (r4c.status, r4c.voucher_no, r4c.tune_status) if r4c else None)
        khac = [x for x in cua_bai() if x.line_id not in (d6n.id, d6c.id, d4c.id)]
        dung(len(khac) == 9 and all(x.status == "cho" and x.voucher_no is None and x.checked_at for x in khac),
             "9 dòng không nằm phiếu nào → chờ, có mốc hỏi", len(khac))

        print("== 4. báo cáo SAU đồng bộ: đúng hai nhóm")
        s, r1 = bao_cao()
        t1 = r1.get("tong", {}) if s == 200 else {}
        hang = {x["driver"]: x for x in r1.get("rows", [])} if s == 200 else {}
        p6 = hang.get(phieu("B").driver_name, {})
        dung(t1 == {"tong_lak": 9660000, "da_tra_lak": 1860000, "cho_tra_lak": 7800000, "so_dong_da_tra": 2, "so_dong_cho": 10},
             "tổng tách hai phần: đã trả 1.860.000 (2 dòng) · chờ trả 7.800.000 (10 dòng)", t1)
        dung(p6.get("trang_thai") == "paid" and p6["da_tra"]["tong_lak"] == 1860000 and p6["cho_tra"]["tong_lak"] == 0
             and p6["da_tra"]["phieu"] == [{"so": SO_6, "ngay": "2026-10-06", "tien_lak": 1860000}]
             and p6["da_tra"]["khoan"] == {"x_trip": 1800000, "x_water": 60000},
             "nhóm ĐÃ TRẢ: tài xế DO B — 'Đã trả (phiếu %s, ngày 06/10)'" % SO_6, p6)
        cho = {t for t, x in hang.items() if x["cho_tra"]["tong_lak"] > 0}
        da = {t for t, x in hang.items() if x["da_tra"]["tong_lak"] > 0}
        dung(da == {p6.get("driver")} and len(cho) == 4 and not (cho & da)
             and all(hang[t]["trang_thai"] == "unpaid" and not hang[t]["da_tra"]["phieu"] for t in cho),
             "nhóm CHỜ TRẢ CÙNG LƯƠNG: 4 tài xế còn lại (A, D1+D2, C, E)", sorted(cho))
        p5r = hang.get(phieu("C").driver_name, {})
        dung(p5r.get("trang_thai") == "unpaid" and p5r["cho_tra"]["tong_lak"] == 1860000,
             "DO C: mục IV 'đã chi' (tự qua lúc ghi sổ) mà chưa có phiếu chi lương → vẫn CHỜ, không ghi đã chi", p5r.get("cho_tra"))
        p8 = hang.get(phieu("D2").driver_name, {})
        dung(p8.get("tong_lak") == 2220000 and p8["cho_tra"]["khoan"] == {"x_trip": 1800000, "x_water": 120000, "x_food": 300000},
             "tài xế D1 + D2: 2.220.000 chờ (D1 tiền chuyến nằm phiếu ST 1 vẫn chờ)", p8.get("cho_tra"))
        dung(not any(phieu(x).driver_name in hang for x in ("T",)),
             "xe thuê không vào báo cáo")
        s, _ = bao_cao("yard")
        dung(s == 403, "Bãi → 403 (như cũ)", s)

        print("== 5. lượt sau: dòng 'đã trả' không hỏi lại; không đổi gì thì không làm bộ đệm tính lại")
        p3, p5 = pb(NGAY_D1), pb(NGAY_D2)
        ket = {"da_hoi": {}, "cap_nhat": {}, "loi": None, "loi_ban_ghi": []}
        GOI.clear()
        dict(DBN._viec())["chi_luong"](db, 50, ket)
        dung(ket["da_hoi"].get("chi_luong") == 10 and not ket["cap_nhat"] and [g[2] for g in GOI] == [10],
             "hỏi 10 dòng còn chờ (không hỏi lại 2 dòng đã trả), không dòng nào đổi", ket)
        dung((pb(NGAY_D1), pb(NGAY_D2)) == (p3, p5), "chỉ ghi mốc hỏi → phiên bản ngày của D1, D2 giữ nguyên",
             (p3, p5, pb(NGAY_D1), pb(NGAY_D2)))

        print("== 6. kế toán ghi sổ phiếu của D1 → lượt sau thành đã trả")
        PHIEU[k4c] = [item("1368-CKH-261006-00009", 99009, 13, 1800000, "2026-10-07T08:00:00")]
        ket = {"da_hoi": {}, "cap_nhat": {}, "loi": None, "loi_ban_ghi": []}
        dict(DBN._viec())["chi_luong"](db, 50, ket)
        db.expire_all()
        r4c = db.get(M.ChiLuongTune, d4c.id)
        dung(ket["cap_nhat"].get("chi_luong") == 1 and r4c.status == "da_tra" and r4c.tune_status == 13 and pb(NGAY_D1) == p3 + 1,
             "ST 13 (ghi sổ tạm) cũng là đã ghi sổ → đã trả; ngày của D1 tăng phiên bản", (r4c.status, r4c.tune_status))
        s, r2 = bao_cao()
        p8 = {x["driver"]: x for x in r2["rows"]}.get(phieu("D1").driver_name, {})
        dung(p8.get("trang_thai") == "partial" and p8["da_tra"]["tong_lak"] == 1800000 and p8["cho_tra"]["tong_lak"] == 420000
             and p8["da_tra"]["phieu"] == [{"so": "1368-CKH-261006-00009", "ngay": "2026-10-07", "tien_lak": 1800000}],
             "tài xế D1 + D2: một phần — đã trả 1.800.000 (phiếu …009, ngày 07/10), chờ 420.000", p8)

        print("== 7. lỗi bên kia")
        LOI["kieu"] = "5xx"
        ket = {"da_hoi": {}, "cap_nhat": {}, "loi": None, "loi_ban_ghi": []}
        try:
            dict(DBN._viec())["chi_luong"](db, 50, ket)
            dung(False, "5xx phải dừng lượt")
        except DBN._DungLuot as e:
            dung("chi_luong" in str(e) and "BEN_KE_TOAN_TU_CHOI" in str(e), "5xx / mất mạng → dừng lượt (lượt sau thử lại)", str(e))
        LOI["kieu"] = "404"
        k = DBN.mot_luot(db)
        dung(not k["loi"] and len(k["loi_ban_ghi"]) == 1 and k["loi_ban_ghi"][0].startswith("chi_luong")
             and not k["da_hoi"].get("chi_luong"),
             "API chưa có đường (404 → 4xx) → ghi loi_ban_ghi, lượt vẫn chạy hết các loại khác", k["loi_ban_ghi"])
        LOI["kieu"] = None
        db.expire_all()
        dung(sum(1 for x in cua_bai() if x.status == "da_tra") == 3, "lỗi không đổi bản ghi nào (vẫn 3 dòng đã trả)")
    finally:
        CHI._goi, NL._goi, B._theo_ngay = goc_goi, goc_nl, goc_tn
        if cu_bat is None:
            os.environ.pop("EPL_DONG_BO_CHI_LUONG", None)
        else:
            os.environ["EPL_DONG_BO_CHI_LUONG"] = cu_bat
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
