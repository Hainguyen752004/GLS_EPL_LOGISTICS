# -*- coding: utf-8 -*-
"""Thử tốc độ các nút mục («Gửi kiểm tra», «Xác nhận kiểm tra», «Ghi sổ», «Trả lại») và lưu phiếu — 02/10 tối, chủ dự án than chậm.

    python kiem/thu_nut_muc_nhanh.py

Bản sao _d7, mỗi ca một giao dịch ngoài ROLLBACK (phiên chạy savepoint). Kho tạm và hệ anh Tune GIẢ LẬP (đếm lời gọi, có độ trễ
giả 200–300 ms như đo thật). Đi đúng lượt giao diện làm (frontend phieu-xuat-xe.js · duyet): «Gửi kiểm tra» = PUT phiếu (luu) rồi
POST send. In thời gian, số câu SQL, lời gọi mạng; kiểm:

  · lưu phiếu không đổi gì: không câu INSERT / UPDATE / DELETE nào trên dòng chi, mã dòng giữ nguyên, không hỏi giá kho tạm,
    không gọi kho tạm thay phần xuất kho hàng (phiếu giao), không hỏi "đã nhập kho" (phiếu gom) — phiếu gom đã vào kho vẫn gửi
    kiểm được (trước 02/10: 409 HANG_DA_NHAP_KHO vì bản phiếu gửi lên mang cả ô cân);
  · đổi số lượng dòng dầu kho → hỏi giá bình quân kho tạm đúng một lần; đổi đơn giá (KT kiểm) → đúng một UPDATE; bỏ một dòng →
    DELETE; thêm dòng → INSERT;
  · số câu SQL mỗi lượt dưới ngưỡng (trước sửa: Gửi kiểm 66–89 câu, Kiểm 67–70, Trả lại 31, Ghi sổ IV 56, Ghi sổ III 29).
"""
import collections
import os
import sys
import time
import types

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7.")
os.environ["DATABASE_URL"] = URL
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi import HTTPException                       # noqa: E402
from sqlalchemy import create_engine, event             # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from routes import phieu as R                           # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import goi_ke_toan as KT                  # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402
from services.phan_quyen import duoc_sua_muc, duoc_sua_tien  # noqa: E402

KQ, MANG = [], collections.Counter()
SQL = {"n": 0, "cau": []}


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))


def gia_kho(db, pt, duong, body=None, nguoi=None, het_gio=15):
    MANG["kho %s %s" % (pt, duong.split("?")[0].rsplit("/", 1)[0] if "/kho-hang/phieu/" in duong else duong)] += 1
    time.sleep(0.2 if pt == "GET" else 0.3)
    if "/kho-hang/phieu/" in duong:
        return {"da_nhap": True, "ton_lo": 10, "lay_boi": [], "xuat": []}
    if duong.endswith("/nhien-lieu/kho"):
        return {}
    return {"cu": []}


def gia_tune(method, duong, body=None):
    MANG["tune %s %s" % (method, duong.split("?")[0])] += 1
    time.sleep(0.3)
    if "/list" in duong and "master-data" in duong:
        return {"Data": [{"ObjId": 777, "ObjectNo": body.get("ObjKey")}]}
    if "GetAllCurrency" in duong:
        return [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}]
    if "GetFinancyCicle" in duong:
        return [{"FICI_AUTOID": 77, "FICI_DATEFROM": "2026-01-01", "FICI_DATETO": "2026-12-31", "FICI_ISACTIVE": True, "FICI_ISCLOSE": False}]
    if duong.endswith("cmpayment-receipt/list"):
        return {"Rows": []}
    if duong.endswith("save-and-commit"):
        return {"RealId": 990001}
    if "cmpayment-receipt/990001" in duong:
        return {"Master": {"DOCUMENTNO": "GIA-CTR-0001", "STATUS": 1}}
    return {}


KT.goi = gia_kho
sys.path.insert(0, os.path.join(GOC, "kiem"))
import _mau_kbaz as MAU  # noqa: E402
MAU.chan_kho_qlsx()                # bài này dùng bộ giả kho tạm; không gọi kho QLSX thật
CHI._goi = gia_tune
ENG = create_engine(URL, connect_args={"options": "-c timezone=UTC"})


@event.listens_for(ENG, "after_cursor_execute")
def _dem(conn, cursor, statement, parameters, context, executemany):
    SQL["n"] += 1
    SQL["cau"].append(" ".join(statement.split())[:80])


COT_INFO = ['kind', 'company', 'owner_name', 'vehicle_id', 'brand_model', 'plate_head', 'plate_trailer', 'driver_id', 'doc_date',
            'out_date', 'back_date', 'odo_out', 'odo_back']
COT_TRANS = ['customer_id', 'route_id', 'goods_type', 'ore_bill_no', 'ore_bill_date', 'origin', 'destination', 'weight_origin',
             'weight_dest', 'price', 'price_ccy', 'price_mode', 'hire_price', 'hire_ccy', 'fee_pct', 'over_limit_t', 'over_price']
COT_TIEN = ['price', 'price_ccy', 'price_mode', 'hire_price', 'hire_ccy', 'fee_pct', 'over_limit_t', 'over_price']


def than_luu(P, vai):
    """Gói PUT giống luu() của màn phiếu (vai đó, các mục còn mở)."""
    st = P.get("sections") or {}
    sua = lambda m: vai == "admin" or duoc_sua_muc(vai, m, st.get(m, "wait"))       # noqa: E731
    gia = lambda m: duoc_sua_tien(vai, m, st.get(m, "wait"))                       # noqa: E731
    b = {c: P.get(c) for c in ("doc_no", "truck_no", "driver_name")} if sua("info") else {}
    for c in COT_INFO + COT_TRANS:
        if vai == "yard" and c in COT_TIEN:
            continue
        m = "info" if c in COT_INFO else "trans"
        if c in P and (sua(m) or (c in COT_TIEN and gia(m))):
            b[c] = P[c]
    if sua("trans") and P.get("kind") == "giao":
        b["goods"] = [{"loai": "hang", "goods_name": g["goods_name"], "qty_t": g["qty_t"], "tu_phieu_id": g.get("tu_phieu_id"),
                       "note": g.get("note")} for g in (P.get("goods") or []) if g["loai"] != "hao_hut"]
    b["expenses"] = [dict(e) for e in (P.get("expenses") or []) if sua(e["section"]) or gia(e["section"])]
    return b


class Ca:
    def __enter__(self):
        self.c = ENG.connect()
        self.ng = self.c.begin()
        from sqlalchemy import text
        self.c.execute(text("SET LOCAL lock_timeout = '10s'"))     # 8011 chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
        for t in ("gui_so_nhien_lieu_tune", "can_tru_tune"):
            M.Base.metadata.tables[t].create(bind=self.c, checkfirst=True)
        self.db = Session(bind=self.c, join_transaction_mode="create_savepoint", autoflush=False)
        return self.db

    def __exit__(self, *a):
        self.db.close(); self.ng.rollback(); self.c.close()
        return False


def nguoi(db, vai):
    u = db.query(M.User).filter(M.User.role == vai, M.User.active.is_(True)).first()
    return u or types.SimpleNamespace(role=vai, full_name="Thử " + vai, username="thu_" + vai, id="thu")


def tim(db, muc, kind=None, co_hang=False, company=None):
    q = db.query(M.Trip).filter(M.Trip.locked.is_(False))
    if kind:
        q = q.filter(M.Trip.kind == kind)
    if company:
        q = q.filter(M.Trip.company == company)
    for p in q.order_by(M.Trip.doc_date.desc()).limit(80):
        if not db.query(M.TripExpense.id).filter(M.TripExpense.trip_id == p.id, M.TripExpense.section == muc).first():
            continue
        if co_hang and not db.query(M.TripGoods.id).filter(M.TripGoods.trip_id == p.id, M.TripGoods.loai == "hang").first():
            continue
        return p.id
    return None


def dat_muc(db, tid, ds):
    for s in db.query(M.TripSection).filter(M.TripSection.trip_id == tid, M.TripSection.section.in_(list(ds))):
        s.status = ds[s.section]
    db.commit()


def luot(ten, tid, muc, hd, vai, co_luu, chuan_bi=None, nguong=None):
    """Một lượt bấm như giao diện; trả (giây, số câu, lời gọi mạng)."""
    with Ca() as db:
        u = nguoi(db, vai)
        if chuan_bi:
            chuan_bi(db, tid)
        p = db.get(M.Trip, tid)
        body = than_luu(R.xuat_phieu(db, p, vai=vai), vai) if co_luu else None
        db.expire_all()
        SQL.update(n=0, cau=[]); MANG.clear()
        t0, loi = time.perf_counter(), None
        try:
            if co_luu:
                R.sua_phieu(tid, body, db=db, user=u)
            R.duyet_muc(tid, muc, hd, db=db, user=u)
        except HTTPException as e:
            loi = (e.detail or {}).get("ma") if isinstance(e.detail, dict) else e.detail
        tg = time.perf_counter() - t0
        print("  · %-36s %-16s %5.0f ms · %3d câu SQL · mạng %s%s" % (ten, p.doc_no, tg * 1000, SQL["n"], dict(MANG) or "-",
                                                                     (" · LỖI " + str(loi)) if loi else ""))
        if nguong is not None:
            dung(loi is None and SQL["n"] <= nguong, "%s: ≤ %d câu SQL, không lỗi" % (ten, nguong), (SQL["n"], loi))
        return tg, SQL["n"], dict(MANG), loi


def main():
    with Ca() as db:
        giao_hang = tim(db, "travel", kind="giao", co_hang=True)
        gom_hang = tim(db, "travel", kind="gom", co_hang=True)
        giao_dau = tim(db, "fuel", kind="giao")
        nha_iv = tim(db, "travel", company="EPL")
        nha_iii = tim(db, "fuel", company="EPL")

    def mo(*muc):
        return lambda db, tid: dat_muc(db, tid, {m: "wait" for m in muc})

    def gia(muc, tt):
        def lam(db, tid):
            dat_muc(db, tid, {muc: tt})
            for d in db.query(M.TripExpense).filter(M.TripExpense.trip_id == tid, M.TripExpense.section == muc):
                if (d.unit_price or 0) <= 0:
                    d.unit_price = 10000
                if d.source == "kho" and d.section == "fuel" and not d.stock_move_id:
                    d.stock_move_id = "gia-" + d.id[:8]
            db.commit()
        return lam

    print("1. Các nút mục — lượt bấm như giao diện (kho tạm / hệ kế toán giả, trễ 200–300 ms)")
    if giao_hang:
        tg, n, mang, _ = luot("Gửi kiểm IV · phiếu giao có hàng", giao_hang, "travel", "send", "yard", True, mo("travel", "trans"), 60)
        dung(not mang, "Gửi kiểm phiếu giao (hàng không đổi): không lời gọi kho tạm nào (trước: thay phần xuất kho hàng + hỏi giá dầu)", mang)
    if gom_hang:
        _, _, mang, loi = luot("Gửi kiểm IV · phiếu gom đã vào kho", gom_hang, "travel", "send", "yard", True, mo("travel", "trans"), 50)
        dung(loi is None and not any("kho-hang/phieu" in k for k in mang), "phiếu gom đã vào kho, cân không đổi: gửi kiểm được, không hỏi "
             "kho tạm (trước: 409 HANG_DA_NHAP_KHO)", (loi, mang))
    if giao_dau:
        luot("Gửi kiểm III · phiếu giao", giao_dau, "fuel", "send", "yard", True, mo("fuel"), 50)
    if nha_iv:
        luot("Kiểm IV (lưu giá rồi kiểm)", nha_iv, "travel", "verify", "expacct", True, gia("travel", "entered"), 55)
        luot("Trả lại IV", nha_iv, "travel", "return", "expacct", False, gia("travel", "entered"), 28)
        _, _, mang, _ = luot("Ghi sổ IV (lập phiếu chi tạm ứng)", nha_iv, "travel", "book", "expacct", False, gia("travel", "verified"), 48)
        dung(mang.get("tune POST /api/v1/accounting/cmpayment-receipt/save-and-commit") == 1,
             "Ghi sổ IV: một phiếu chi tạm ứng (chống trùng list + tạo + đọc số — bắt buộc)", mang)
    if nha_iii:
        luot("Kiểm III (lưu giá rồi kiểm)", nha_iii, "fuel", "verify", "fuel", True, gia("fuel", "entered"), 55)
        luot("Ghi sổ III", nha_iii, "fuel", "book", "fuel", False, gia("fuel", "verified"), 25)

    print("2. Lưu dòng chi giữ mã, không ghi lại dòng không đổi")
    tid = giao_dau or nha_iii
    with Ca() as db:
        dat_muc(db, tid, {"fuel": "wait", "travel": "wait", "other": "wait"})
        u = nguoi(db, "yard")
        p = db.get(M.Trip, tid)
        P = R.xuat_phieu(db, p, vai="yard")
        body = than_luu(P, "yard")
        ids = [e["id"] for e in body["expenses"]]
        SQL.update(n=0, cau=[]); MANG.clear()
        R.sua_phieu(tid, body, db=db, user=u)
        ghi = [c for c in SQL["cau"] if c.split(" ")[0] in ("INSERT", "UPDATE", "DELETE") and "trip_expenses" in c]
        dung(not ghi, "lưu lại y nguyên: không câu INSERT / UPDATE / DELETE nào trên trip_expenses", ghi)
        dung(not any("nhien-lieu/kho" in k for k in MANG), "dòng dầu kho không đổi: không hỏi giá bình quân kho tạm", dict(MANG))
        con = [e.id for e in db.query(M.TripExpense).filter(M.TripExpense.trip_id == tid).all()]
        dung(set(ids) <= set(con), "mã dòng giữ nguyên")
        kho = next((e for e in body["expenses"] if e["section"] == "fuel" and e.get("source") == "kho" and not e.get("stock_move_id")), None)
        if kho is not None:
            kho["qty"] = (kho["qty"] or 0) + 5
            MANG.clear()
            R.sua_phieu(tid, body, db=db, user=u)
            dung(MANG.get("kho GET /api/lien-thong/nhien-lieu/kho") == 1, "đổi số lượng dòng dầu kho → hỏi giá kho tạm đúng một lần", dict(MANG))
        tv = [e for e in body["expenses"] if e["section"] == "travel"]
        if len(tv) >= 2:
            bo = tv[-1]
            body["expenses"] = [e for e in body["expenses"] if e is not bo] + [{"section": "travel", "item_key": "x_misc", "qty": 1}]
            SQL.update(n=0, cau=[])
            R.sua_phieu(tid, body, db=db, user=u)
            cau = [c.split(" ")[0] for c in SQL["cau"] if "trip_expenses" in c and c.split(" ")[0] in ("INSERT", "DELETE")]
            con = {e.id for e in db.query(M.TripExpense).filter(M.TripExpense.trip_id == tid).all()}
            dung("DELETE" in cau and "INSERT" in cau and bo["id"] not in con, "bỏ một dòng → DELETE, thêm dòng → INSERT", cau)
    with Ca() as db:                                            # KT Chi phí sửa một đơn giá → đúng một UPDATE
        tid = nha_iv
        dat_muc(db, tid, {"travel": "entered"})
        u = nguoi(db, "expacct")
        body = than_luu(R.xuat_phieu(db, db.get(M.Trip, tid), vai="expacct"), "expacct")
        e = next(x for x in body["expenses"] if x["section"] == "travel")
        e["unit_price"] = (e.get("unit_price") or 0) + 1234
        SQL.update(n=0, cau=[])
        R.sua_phieu(tid, body, db=db, user=u)
        up = [c for c in SQL["cau"] if c.startswith("UPDATE trip_expenses")]
        # dòng khác chỉ được chạm khi mã định khoản lưu theo luật cũ (tai_khoan.tk_dong / _gan_tk chép mã hiện hành) — một lần
        dung(len([c for c in up if "unit_price" in c]) == 1 and all("unit_price" in c or c.startswith("UPDATE trip_expenses SET acct_code=")
                                                                     for c in up),
             "KT Chi phí đổi một đơn giá → đúng một UPDATE đơn giá (dòng khác chỉ cập nhật mã định khoản cũ)", up)
    print("TỔNG: %d/%d đạt — đã ROLLBACK mọi ca" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
