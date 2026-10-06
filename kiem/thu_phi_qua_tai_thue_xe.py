# -*- coding: utf-8 -*-
"""Thử 06/10: bút toán PHÍ QUẢN LÝ 2 % và CẮT QUÁ TẢI xe thuê — ghi lúc khoá DO, CÙNG chứng từ nguồn thue_xe.

    python kiem/thu_phi_qua_tai_thue_xe.py

Chủ dự án giao 06/10, mã đã chốt:
  · phí quản lý (Excel «ຫັກຄ່າທຳນຽມ 2%/ບິນ») ..... Nợ 4022 / Có 715 doanh thu tiền hoa hồng
  · cắt quá tải (Excel «ຫັກແກ່ເກີນ 1$/ໂຕນ») ...... Nợ 4022 / Có 758 thu nhập từ hoạt động thông thường khác
  Số = đúng tinh_phieu mà tất toán đối tác trừ (phi, tru_vuot; ô trống = mặc định 2 % · 40 t · 1/t), cùng tiền thuê + tỷ giá khoá;
  số 0 thì không có dòng. Sau khoá 4022 còn = tiền thuê − phí − quá tải.

Chạy trên bản sao _d7, MỌI THỨ trong giao dịch ngoài, cuối ROLLBACK (không ghi gì vào d7); mọi lời gọi mạng bị chặn (urllib), hệ
kế toán anh Tune giả lập (bộ giả của kiem/thu_tat_toan_doi_tac.py). Hai phần:

  A. TestClient (đường API thật): Sếp lập phiếu xe thuê 45 t × 30 USD, phí 2 %, ngưỡng 40 t, 1 USD/t → khoá: gói thue_xe đủ 3 dòng
     (621/4022 1.350 · 4022/715 27 · 4022/758 5 USD, tỷ giá phiếu, quy Kíp, đối tượng chủ xe); sửa phí sau khoá bị chặn DA_KHOA; mở
     khoá → huỷ; phí 0 → không dòng 715; không quá tải → không dòng 758; ô trống → mặc định; 4022 ròng (thue_xe − nợ NCC) = số trả
     chủ xe của màn Tất toán đối tác cho cùng chuyến.
  B. Chuyến mẫu THU-KBAZ-T1 (đủ tạm ứng, nợ NCC, SO nhiên liệu): khoá lại theo luật mới, lập đề nghị trả đối tác (cấn trừ SO + phiếu
     chi Nợ 4022 / Có tiền) → cộng mọi vế 4022 của chuyến: về 0 (chỉ còn phần lẻ đổi Kíp → USD hai số lẻ); gói gửi bên kế toán
     (journal-entries) mang đủ 3 dòng.
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
os.environ.pop("QLSX_GUI_BUT_TOAN", None)                  # cờ gửi tắt: bút toán chỉ nằm chờ gửi
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
sys.path.insert(0, os.path.join(GOC, "kiem"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _cam_mang(*a, **k):
    raise OSError("bài kiểm không được gọi mạng ra ngoài")


urllib.request.urlopen = _cam_mang

KQ = []
SO_A = "THU-PQT-A/EPL"


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:400]) if ct != "" else ""))
    sys.stdout.flush()


def phai(s, mong, buoc, g=None):
    if s != mong:
        raise RuntimeError("%s trả %s, mong %s — %s" % (buoc, s, mong, json.dumps(g, ensure_ascii=False)[:400]))


def theo_co(bt):
    """{mã Có: dòng} của gói thue_xe."""
    return {x["co"]: x for x in (bt or {}).get("dong") or []}


# ================================================================ A. đường API (TestClient)
class May:
    """TestClient trên _d7: một kết nối, một giao dịch ngoài, phiên chạy savepoint; hết bài ROLLBACK (như thu_but_toan_cho)."""

    def __enter__(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        import models as M
        from database import get_db
        from main import app
        from services import dem_bao_cao as DEM
        self.eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
        self.conn = self.eng.connect()
        self.ngoai = self.conn.begin()
        self.conn.execute(text("SET LOCAL lock_timeout = '10s'"))
        M.Base.metadata.create_all(bind=self.conn, checkfirst=True)
        self.conn.execute(text(DEM._BANG_SQL))
        if not DEM._CO_BANG:
            DEM._CO_BANG.append(True)

        def _khong_dem(db, viec, theo_ngay=False, tinh_lo=None):
            kq = tinh_lo(list(range(len(viec)))) if tinh_lo is not None else [t() for _, _, t in viec]
            return [json.loads(json.dumps(v, default=str)) for v in kq]
        DEM.lay_nhieu = _khong_dem
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint", autoflush=False)

        def _db():
            try:
                yield self.db
            finally:
                self.db.rollback()
        self.app = app
        app.dependency_overrides[get_db] = _db
        self.c = TestClient(app, raise_server_exceptions=False)
        self.tk = {}
        for u in ("admin", "ketoan"):
            s, g = self.goi("/api/dang-nhap", {"username": u, "password": "1234"})
            phai(s, 200, "đăng nhập " + u, g)
            self.tk[u] = g["token"]
        return self

    def goi(self, duong, body=None, u=None, method=None):
        r = self.c.request(method or ("POST" if body is not None else "GET"), duong, json=body,
                           headers={"Authorization": "Bearer " + self.tk[u]} if u else {})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}

    def __exit__(self, *a):
        self.app.dependency_overrides.clear()
        self.db.close()
        self.ngoai.rollback()
        self.conn.close()
        self.eng.dispose()
        return False


def _thue_xe(m, tid):
    s, bt = m.goi("/api/but-toan-cho?trip_id=" + tid, u="ketoan")
    phai(s, 200, "đọc bút toán chờ", bt)
    return next((b for b in bt["ds"] if b["nguon"] == "thue_xe"), None)


def _khoa(m, tid):
    s, g = m.goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan")
    phai(s, 200, "KT Thu/Chi khoá phiếu", g)
    s, p = m.goi("/api/trips/" + tid, u="ketoan")
    return p


def _mo(m, tid):
    s, g = m.goi("/api/trips/%s/mo-khoa" % tid, {}, u="ketoan")
    phai(s, 200, "KT Thu/Chi mở khoá", g)


def _sua(m, tid, **truong):
    s, g = m.goi("/api/trips/" + tid, truong, u="admin", method="PUT")
    phai(s, 200, "Sếp sửa %s" % truong, g)


def phan_a():
    print("A. Khoá DO xe thuê → gói thue_xe (API, TestClient)")
    import models as M
    with May() as m:
        s, xe = m.goi("/api/vehicles", u="admin"); s, tx = m.goi("/api/drivers", u="admin"); s, kh = m.goi("/api/customers", u="admin")
        thue = next(v for v in xe if v["owner_type"] == "joint" and v["active"] and v.get("owner_id"))
        taixe = next(t for t in tx if t["active"])
        body = {"doc_no": SO_A, "kind": "giao", "company": "joint", "vehicle_id": thue["id"], "driver_id": taixe["id"],
                "customer_id": kh[0]["id"], "doc_date": "2026-09-27", "out_date": "2026-09-27", "weight_origin": 45, "odo_out": 1000,
                "price": 40, "price_ccy": "USD", "hire_price": 30, "hire_ccy": "USD", "fee_pct": 2, "over_limit_t": 40, "over_price": 1,
                "pod_no": "PQT-POD",
                "expenses": [
                    # chipping Lào: ghi nợ NCC trả theo đợt → no_ncc Nợ 4022 / Có 4021 (EPL trả thay, trừ vào tiền trả đối tác)
                    {"section": "travel", "item_key": "x_chip_lao", "qty": 1, "unit_price": 150000, "currency": "LAK"},
                    # tiền ăn giá 0: không sinh tạm ứng bên kế toán
                    {"section": "travel", "item_key": "x_food", "qty": 1, "unit_price": 0, "currency": "LAK"}]}
        s, p = m.goi("/api/trips", body, u="admin")
        phai(s, 200, "Sếp lập phiếu thử", p)
        tid = p["id"]
        s, g = m.goi("/api/trips/%s/transport-status" % tid, {"status": "arrived", "weight_dest": 45, "odo_back": 1500,
                                                             "back_date": "2026-09-28"}, u="admin")
        phai(s, 200, "Sếp báo xe tới, cân cuối 45 t", g)
        dung(_thue_xe(m, tid) is None, "chưa khoá: chưa có bút toán thue_xe")

        # ---- 1. phí 2 % + quá tải 5 t → 3 dòng
        p = _khoa(m, tid)
        t = p["tinh"]
        b = _thue_xe(m, tid)
        d = theo_co(b)
        r_usd = p["rate_usd"]
        print("    tinh: tiền thuê %s %s · phí %s · quá tải %s t → %s · trả chủ xe %s" % (
            t["tien_thue"], t["hire_ccy"], t["phi"], t["vuot_tan"], t["tru_vuot"], t["tra_chu_xe"]))
        dung(t["tien_thue"] == 1350 and t["phi"] == 27 and t["tru_vuot"] == 5 and t["hire_ccy"] == "USD",
             "phiếu mẫu: 45 t × 30 = 1.350 USD · phí 2 % = 27 · quá tải 5 t × 1 = 5", (t["tien_thue"], t["phi"], t["tru_vuot"]))
        dung(b and b["status"] == "cho_gui" and len(b["dong"]) == 3 and set(d) == {"4022", "715", "758"},
             "gói thue_xe một chứng từ, đủ 3 dòng (Có 4022 · 715 · 758)", [(x["no"], x["co"], x["tien"]) for x in (b or {}).get("dong", [])])
        chu = {"loai": "chu_xe", "ref_id": p["owner_id"]}
        dong_dung = all(x["ccy"] == "USD" and x["ty_gia"] == r_usd and x["doi_tuong"] == chu for x in d.values())
        dung(d.get("4022", {}).get("no") == "621" and d["4022"]["tien"] == 1350 and d["4022"]["tien_lak"] == round(1350 * r_usd),
             "dòng 1: Nợ 621 / Có 4022 = 1.350 USD (quy Kíp %s)" % d.get("4022", {}).get("tien_lak"))
        dung(d.get("715", {}).get("no") == "4022" and d["715"]["tien"] == t["phi"] == 27 and d["715"]["tien_lak"] == round(27 * r_usd)
             and d["715"].get("ve") == "phi_quan_ly" and "715" not in str(d["715"].get("canh_bao_tk") or ""),
             "dòng 2: Nợ 4022 / Có 715 = phí quản lý 27 USD — tài khoản lá, không cảnh báo", d.get("715", {}).get("dien_giai"))
        dung(d.get("758", {}).get("no") == "4022" and d["758"]["tien"] == t["tru_vuot"] == 5 and d["758"]["tien_lak"] == round(5 * r_usd)
             and d["758"].get("ve") == "cat_qua_tai" and not d["758"].get("canh_bao_tk"),
             "dòng 3: Nợ 4022 / Có 758 = cắt quá tải 5 USD — tài khoản lá, không cảnh báo", d.get("758", {}).get("dien_giai"))
        dung(dong_dung, "cả 3 dòng: cùng tiền thuê USD, tỷ giá khoá trên phiếu %s, đối tượng chủ xe" % r_usd)
        dung(b["dong"][0]["co"] == "4022" and b["dong"][0]["no"] == "621" and ("phiếu " + SO_A) in (b["dien_giai"] or ""),
             "dòng tiền thuê đứng đầu; diễn giải chứng từ giữ cụm «phiếu <số DO>» (Web tách số DO)", b["dien_giai"])
        rong = round(d["4022"]["tien"] - d["715"]["tien"] - d["758"]["tien"], 2)
        dung(rong == round(t["tien_thue"] - t["phi"] - t["tru_vuot"], 2) == 1318,
             "4022 ròng của chứng từ = tiền thuê − phí − quá tải = 1.318 USD", rong)
        # gói bàn giao DO: acc_code_note nói đúng (không còn "chưa có bút toán riêng")
        from services import ban_giao as BG
        tr = m.db.get(M.Trip, tid)
        goi = BG.dong_goi(m.db, tr) if hasattr(BG, "dong_goi") else None
        note = (((goi or {}).get("header") or {}).get("hire") or {}).get("acc_code_note") or ""
        dung("715" in note and "758" in note and "chưa có bút toán" not in note, "gói bàn giao DO: hire.acc_code_note có 715 · 758", note)

        # ---- 2. 4022 ròng = số trả chủ xe của màn Tất toán đối tác (cùng chuyến)
        s, tt = m.goi("/api/tat-toan-doi-tac?ky=2026-09&owner_id=%s&cap_nhat=0" % p["owner_id"], u="ketoan")
        phai(s, 200, "KT Thu/Chi đọc Tất toán đối tác", tt)
        ct = next((x for x in tt.get("chi_tiet") or [] if x["trip_id"] == tid), None)
        s, bt = m.goi("/api/but-toan-cho?trip_id=" + tid, u="ketoan")
        ncc = next((x for x in bt["ds"] if x["nguon"] == "no_ncc"), None)
        ncc_lak = sum(x["tien"] for x in (ncc or {}).get("dong") or [] if x["no"] == "4022")
        dung(ct and ct["phi"] == d["715"]["tien"] and ct["qua_tai"] == d["758"]["tien"] and ct["tien_thue"] == d["4022"]["tien"],
             "Tất toán đối tác trừ đúng số của bút toán: phí %s · quá tải %s · tiền thuê %s" % (
                 ct and ct["phi"], ct and ct["qua_tai"], ct and ct["tien_thue"]))
        con = rong - ncc_lak / r_usd - (ct["tam_ung"]["tien"] or 0) if ct else None
        dung(ct and ncc_lak == 150000 and abs(con - ct["con_tra"]) < 0.01,
             "4022 ròng (thue_xe 1.318 − nợ NCC 150.000 Kíp − tạm ứng) = số còn trả chủ xe %s USD → phiếu chi Nợ 4022 / Có tiền "
             "đưa 4022 về 0, không trừ phí / quá tải hai lần" % (ct and ct["con_tra"]), "%.4f vs %s" % (con or 0, ct and ct["con_tra"]))

        # ---- 3. sửa phí sau khoá → chặn
        s, g = m.goi("/api/trips/" + tid, {"fee_pct": 3}, u="admin", method="PUT")
        g = (g.get("detail") if isinstance(g, dict) and isinstance(g.get("detail"), dict) else g) or {}
        dung(s == 409 and g.get("ma") in ("DA_KHOA", "PHIEU_DA_KHOA"), "phiếu đang khoá: sửa phí bị chặn 409 %s" % g.get("ma"),
             str(g.get("loi") or g)[:160])
        id_cu = b["id"]

        # ---- 4. mở khoá → huỷ; phí 0 → chỉ 621 + 758
        _mo(m, tid)
        b = _thue_xe(m, tid)
        dung(b and b["status"] == "huy", "mở khoá: gói thue_xe (cả 3 dòng) huỷ", b and b["status"])
        _sua(m, tid, fee_pct=0)
        p = _khoa(m, tid)
        b = _thue_xe(m, tid)
        d = theo_co(b)
        dung(b["id"] == id_cu and b["status"] == "cho_gui" and set(d) == {"4022", "758"} and p["tinh"]["phi"] == 0,
             "phí 0 %: khoá lại cùng bản ghi, KHÔNG có dòng 715 (còn 621/4022 + 4022/758)", [(x["no"], x["co"], x["tien"]) for x in b["dong"]])

        # ---- 5. không quá tải → chỉ 621 + 715
        _mo(m, tid)
        _sua(m, tid, fee_pct=2, weight_dest=38)
        p = _khoa(m, tid)
        b = _thue_xe(m, tid)
        d = theo_co(b)
        dung(set(d) == {"4022", "715"} and p["tinh"]["tru_vuot"] == 0 and d["715"]["tien"] == p["tinh"]["phi"] == round(38 * 30 * 0.02, 2),
             "38 t ≤ 40 t: KHÔNG có dòng 758; phí 2 %% × 1.140 = %s" % p["tinh"]["phi"], [(x["no"], x["co"], x["tien"]) for x in b["dong"]])

        # ---- 6. ô trống → mặc định 2 % · 40 t · 1/t (đúng tinh_phieu)
        _mo(m, tid)
        _sua(m, tid, weight_dest=46)
        tr = m.db.get(M.Trip, tid)
        tr.fee_pct = tr.over_limit_t = tr.over_price = None
        m.db.commit()
        p = _khoa(m, tid)
        b = _thue_xe(m, tid)
        d = theo_co(b)
        dung(p["fee_pct"] is None and p["over_limit_t"] is None and set(d) == {"4022", "715", "758"}
             and d["715"]["tien"] == p["tinh"]["phi"] == round(46 * 30 * 0.02, 2) and d["758"]["tien"] == p["tinh"]["tru_vuot"] == 6,
             "ô phí / ngưỡng / giá quá tải trống: mặc định 2 %% · 40 t · 1/t → phí %s · quá tải %s" % (p["tinh"]["phi"], p["tinh"]["tru_vuot"]),
             [(x["no"], x["co"], x["tien"]) for x in b["dong"]])

        # ---- 7. phí 0 + không quá tải → chỉ dòng tiền thuê
        _mo(m, tid)
        _sua(m, tid, fee_pct=0, over_limit_t=40, over_price=1, weight_dest=40)
        p = _khoa(m, tid)
        b = _thue_xe(m, tid)
        dung(len(b["dong"]) == 1 and b["dong"][0]["no"] == "621" and b["dong"][0]["co"] == "4022" and "trừ" not in (b["dien_giai"] or ""),
             "phí 0 và đúng 40 t: chỉ còn Nợ 621 / Có 4022", [(x["no"], x["co"], x["tien"]) for x in b["dong"]])
    print("  · phần A: đã ROLLBACK")


# ================================================================ B. chuyến mẫu T1: 4022 về 0
def phan_b():
    print("B. Chuyến mẫu THU-KBAZ-T1: khoá theo luật mới → đề nghị trả đối tác → cộng mọi vế 4022")
    import thu_tat_toan_doi_tac as TTD          # bộ giả hệ kế toán anh Tune + kho tạm, ca giao dịch ROLLBACK
    import models as M
    from services import but_toan_cho as BTC
    from services import chi_tune as CHI
    from services import gui_but_toan_tune as GBT
    from services import tra_chu_xe as TC
    with TTD.Phien() as db:
        t1 = TTD.phieu(db, "THU-KBAZ-T1/EPL")
        cu = db.query(M.ButToanCho).filter(M.ButToanCho.nguon == BTC.THUE_XE, M.ButToanCho.ma_nguon == t1.id).first()
        dung(cu is not None and len(json.loads(cu.dong)) == 1, "mẫu cũ (khoá trước 06/10): thue_xe chỉ một dòng 621/4022", cu and cu.status)
        db.delete(cu)                           # trong giao dịch: coi như phiếu khoá SAU 06/10
        db.flush()
        BTC.ghi_khoa_phieu(db, t1, "thu 06/10")
        db.commit()
        bt = db.query(M.ButToanCho).filter(M.ButToanCho.nguon == BTC.THUE_XE, M.ButToanCho.ma_nguon == t1.id).one()
        dong = json.loads(bt.dong)
        d = {x["co"]: x for x in dong}
        dung(set(d) == {"4022", "715"} and d["4022"]["tien"] == 741 and d["715"]["tien"] == 14.82,
             "T1 24,7 t × 30 USD: Nợ 621 / Có 4022 = 741 · Nợ 4022 / Có 715 = 14,82 (2 %) · không quá tải → không dòng 758",
             [(x["no"], x["co"], x["tien"], x["ccy"]) for x in dong])
        # gói gửi bên kế toán (journal-entries) — màn «Bút toán từ Logistics» bên Web đọc chứng từ này
        body = GBT.dung_goi(db, bt)
        e = body["Entries"]
        dung(len(e) == 2 and [(x["DebitAccount"], x["CreditAccount"], x["Amount"]) for x in e] == [("621", "4022", 741), ("4022", "715", 14.82)]
             and all(x["ExchangeRate"] == t1.rate_usd and x["ObjectId"] for x in e) and body["SourceRef"] == "EPLLAO-thue_xe-" + t1.id,
             "gói journal-entries: 2 dòng đúng mã / tiền / tỷ giá, đối tượng chủ xe, SourceRef EPLLAO-thue_xe-<trip>",
             [(x["DebitAccount"], x["CreditAccount"], x["Amount"], x["ExchangeRate"]) for x in e])

        TTD._co_so(db, t1)                      # T1 chưa trả + SO nhiên liệu đã tạo (máy giả, còn nợ đủ 6.600.000)
        x = TC.dong_phieu(db, t1)
        r = CHI.de_nghi_tra_chu_xe(db, t1.owner_id, [t1.id], "cash", TTD.ACCT)
        pc = TTD.GIA.phieu[r.real_id]["body"] if r.real_id else None
        cts = [c for c in CHI._can_tru_cua(db, r) if c.status == "da_gui"]
        v = db.query(M.Voucher).filter(M.Voucher.trip_id == t1.id, M.Voucher.kind == "advance").one()
        tu = CHI.dung_goi(db, t1, v, 7777)      # phiếu chi «Chi trước» của tờ tạm ứng: Nợ 4022 / Có 1011 (Kíp)
        ncc = db.query(M.ButToanCho).filter(M.ButToanCho.nguon == BTC.NO_NCC, M.ButToanCho.ma_nguon == t1.id).one()
        r_h = TC.phan_tra(t1, db.query(M.TripExpense).filter(M.TripExpense.trip_id == t1.id).all(), None)["ty_gia_thue"]

        # mọi vế 4022 của chuyến: (tên, Có − Nợ theo tiền thuê USD, theo Kíp)
        ve = []
        for y in dong:                          # chứng từ thue_xe (USD)
            dau = 1 if y["co"] == "4022" else -1 if y["no"] == "4022" else 0
            ve.append(("thue_xe %s/%s" % (y["no"], y["co"]), dau * y["tien"], dau * y["tien_lak"]))
        n_ncc = sum(y["tien"] for y in json.loads(ncc.dong) if y["no"] == "4022")
        ve.append(("no_ncc 4022/4021", -n_ncc / r_h, -n_ncc))
        n_tu = sum(y["Amount"] for y in tu["Entries"] if y["DebitAccount"] == "4022")
        ve.append(("tạm ứng CTR 4022/1011", -n_tu / r_h, -n_tu))
        n_ct = sum(c.amount for c in cts)
        ve.append(("cấn trừ SO 4022/1211", -n_ct / r_h, -n_ct))
        pc_usd = sum(y["Amount"] for y in (pc or {}).get("Entries", []) if y["DebitAccount"] == "4022")
        pc_lak = sum(y["BaseAmount"] for y in (pc or {}).get("Entries", []) if y["DebitAccount"] == "4022")
        ve.append(("phiếu chi trả đối tác 4022/tiền", -pc_usd, -pc_lak))
        for ten, usd, lak in ve:
            print("    %-34s %12.4f USD %14s Kíp" % (ten, usd, "{:,}".format(round(lak)).replace(",", ".")))
        con_usd, con_lak = sum(v_[1] for v_ in ve), sum(v_[2] for v_ in ve)
        print("    %-34s %12.4f USD %14s Kíp" % ("= 4022 còn", con_usd, "{:,}".format(round(con_lak)).replace(",", ".")))
        dung(pc and r.status == "da_gui" and n_ct > 0 and n_tu == 4247000 and n_ncc == 620000,
             "đề nghị trả đối tác: cấn trừ SO %s Kíp + phiếu chi %s USD (tạm ứng 4.247.000 · nợ NCC 620.000 trừ sẵn)" % (n_ct, pc_usd))
        dung(abs(pc_usd - x["con_tra"]) < 0.011, "phiếu chi = số còn trả của tất toán đối tác (đã trừ phí, tạm ứng, nợ NCC, cấn trừ SO)",
             (pc_usd, x["con_tra"]))
        dung(abs(con_usd) < 0.005, "4022 của chuyến về 0 (chỉ còn phần lẻ đổi Kíp → USD hai số lẻ: %.4f USD ≈ %s Kíp)" % (con_usd, round(con_lak)))
        truoc = con_usd + d["715"]["tien"]
        dung(abs(truoc - 14.82) < 0.005, "trước 06/10 (không có dòng 715) 4022 treo đúng phí 14,82 USD — đã khép", round(truoc, 4))


def main():
    for phan in (phan_a, phan_b):
        try:
            phan()
        except Exception as e:                  # noqa: BLE001 — một phần vỡ thì ghi, chạy phần sau
            import traceback
            traceback.print_exc()
            dung(False, "%s vỡ: %s" % (phan.__name__, str(e).replace(URL, "<url>")[:300]))
    print("đã ROLLBACK mọi phần — bản sao d7 không đổi")
    print("PHÍ / QUÁ TẢI XE THUÊ: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
