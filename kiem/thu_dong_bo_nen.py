# -*- coding: utf-8 -*-
"""Thử 06/10 — TỰ ĐỒNG BỘ NỀN với hệ kế toán anh Tune (services/dong_bo_nen.py, routes/dong_bo_nen.py) trên bản sao _d7.

    python kiem/thu_dong_bo_nen.py

MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK: không ghi gì vào d7. KHÔNG gọi mạng: lời gọi sang hệ kế
toán (chi_tune._goi — phiếu chi, công nợ khách / đối tác, danh mục đối tượng; so_nhien_lieu._goi) thay bằng bản giả lập; gọi
đường nào khác (tạo / xoá / upsert…) là bài hỏng. Không khởi động luồng nền (TestClient không chạy sự kiện khởi động).

Dữ liệu d7 06/10: 5 phiếu "Chi trước" chờ thủ quỹ (G4-0001, T4-0001, G4-0002, G4-0004, G4-0008), đề nghị trả chủ xe TCX-…0a07
(G4-0002 + G4-0003), 7 SO cước chưa đọc thu lần nào, SO nhiên liệu G4-0007 chưa thu. Dựng thêm trong giao dịch: một phiếu "Chi khác"
mục V (G4-0006) và một phiếu trả nhà cung cấp (phieu_tien_tune) đang chờ.
"""
import os
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["EPL_DONG_BO_CHI_LUONG"] = "0"   # 06/10: loại chi_luong có bài riêng (kiem/thu_chi_luong_tune.py); bài này giả lập đường cũ
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import types                                            # noqa: E402

from fastapi import HTTPException                       # noqa: E402
from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import ban_giao as BG                     # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import dong_bo_nen as DBN                 # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402
from services.bao_mat import nguoi_hien_tai             # noqa: E402

KQ = []
GOI = []
TRANG = {}                                              # real_id → STATUS bên kế toán (12/13 = đã ghi sổ)
LOI = {"kieu": None, "rid": None}                       # None · mang · 5xx · 4xx (một real_id)
CONG_NO = {"Debts": [], "Orders": []}


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:400]) if ct != "" else ""))


def gia_goi(method, duong, body=None):
    """Bản giả lập chi_tune._goi — CHỈ ba đường đọc mà luồng nền được phép gọi."""
    GOI.append((method, duong.split("?")[0]))
    if LOI["kieu"] == "mang":
        raise HTTPException(502, {"ma": "KHONG_GOI_DUOC", "loi": "Không gọi được hệ kế toán (giả lập mất mạng)"})
    if method == "GET" and duong.startswith("/api/v1/accounting/cmpayment-receipt/"):
        rid = int(duong.split("/")[-1].split("?")[0])
        if LOI["kieu"] == "5xx":
            raise HTTPException(502, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "Hệ kế toán trả HTTP 500: giả lập"})
        if LOI["kieu"] == "4xx" and rid == LOI["rid"]:
            raise HTTPException(422, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "Hệ kế toán từ chối: giả lập"})
        st = TRANG.get(rid, 1)
        m = {"STATUS": st}
        if st in (12, 13):
            m.update({"POSTNAME": "Thủ quỹ thử", "POSTDATE": "2026-10-06T15:00:00"})
        return {"Master": m}
    if method == "POST" and duong == "/api/v1/sales/debt/customer-detail":
        return {"Summary": {}, "Aging": [], "Debts": CONG_NO["Debts"], "Orders": CONG_NO["Orders"], "Collections": []}
    if method == "POST" and duong.startswith("/api/v1/master-data/") and duong.endswith("/list"):
        return {"Data": [{"ObjId": 7777, "ObjectNo": (body or {}).get("ObjKey")}]}
    raise AssertionError("luồng nền không được gọi %s %s" % (method, duong))


def gia_goi_nl(method, duong, body_json=None, key=None):
    GOI.append((method, duong))
    raise AssertionError("SO nhiên liệu phải đọc được qua công nợ đối tác, không gọi %s %s" % (method, duong))


def no(so, tong, con):
    return {"OrderCode": so, "RETK_PAYMENTAMOUNT": tong, "RCTD_DEBTMONEY": con, "RETK_MONEYPAID": 0, "CurrencyCode": "USD"}


def don(so, tong):
    return {"OrderCode": so, "FinalTotalAmount": tong, "CurrencyCode": "USD", "StatusName": "Hoàn tất"}


def main():
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    import _bo_cu_0610 as BO_CU                         # 06/10: d7 dọn + gieo lại → dựng bộ dữ liệu bài viết theo TRONG giao dịch
    BO_CU.dat_bo_cu(conn)
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)
    goc_goi, goc_nl, goc_ch = CHI._goi, NL._goi, DBN._co_cau_hinh
    CHI._goi, NL._goi = gia_goi, gia_goi_nl

    def tao_phien():
        return Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def phieu(so):
        return db.query(M.Trip).filter(M.Trip.doc_no == so).one()

    def chi_tu(so):
        db.expire_all()
        return db.query(M.ChiTune).filter(M.ChiTune.trip_id == phieu(so).id).one()
    try:
        print("== 0. cấu hình")
        cu = os.environ.get("EPL_DONG_BO_NEN_PHUT")
        for v, mong in (("0", 0.0), ("abc", 0.0), ("2.5", 2.5), (None, 5.0)):
            os.environ.pop("EPL_DONG_BO_NEN_PHUT", None) if v is None else os.environ.__setitem__("EPL_DONG_BO_NEN_PHUT", v)
            dung(DBN.phut() == mong, "EPL_DONG_BO_NEN_PHUT=%s → %s phút" % (v, mong))
        os.environ["EPL_DONG_BO_NEN_PHUT"] = "0"
        DBN.bat_dau()
        dung(DBN._LUONG["t"] is None, "PHUT=0 → không bật luồng nền")
        os.environ.pop("EPL_DONG_BO_NEN_PHUT") if cu is None else os.environ.__setitem__("EPL_DONG_BO_NEN_PHUT", cu)

        # dựng thêm: phiếu Chi khác mục V của G4-0006, phiếu trả nhà cung cấp — đều đang chờ thủ quỹ
        p6 = phieu("G4-0006-10/EPL")
        db.add(M.ChiMucTune(trip_id=p6.id, section="repair", lan=1, expense_ids="[]", ref_no="PCMV-THU-0610", amount_lak=1,
                            status="da_gui", real_id=99002, document_no="1368-CKH-THU-99002"))
        db.add(M.PhieuTienTune(nguon="ncc", ma_nguon="DNNCC-THU-0610", loai="PC_NCC", voucher_type="CMP", amount=100000,
                               amount_lak=100000, ref_no="DNNCC-THU-0610", status="da_gui", real_id=99001,
                               document_no="1368-CKH-THU-99001"))
        db.commit()

        print("== 1. mất mạng → dừng lượt, không đổi gì")
        LOI["kieu"] = "mang"
        GOI.clear()
        k = DBN.mot_luot(db)
        db.expire_all()
        dung(k["loi"] and "KHONG_GOI_DUOC" in k["loi"] and len(GOI) == 1 and not k["cap_nhat"]
             and all(r.status == "da_gui" for r in db.query(M.ChiTune)),
             "lỗi mạng ở bản ghi đầu: dừng cả lượt (1 lời gọi), bản ghi giữ nguyên", (k["loi"], len(GOI)))

        print("== 2. bên kia trả 5xx → KHÔNG đánh phiếu mất (trả bản ghi về như trước), dừng lượt")
        LOI["kieu"] = "5xx"
        GOI.clear()
        k = DBN.mot_luot(db)
        db.expire_all()
        mat = [r for r in db.query(M.ChiTune) if r.status != "da_gui" or r.error_code]
        dung(k["loi"] and "BEN_KE_TOAN_TU_CHOI" in k["loi"] and len(GOI) == 1 and not mat,
             "chi_tune.doc_phieu đánh PHIEU_CHI_MAT khi 5xx — luồng nền trả lại da_gui", [(r.status, r.error_code) for r in mat])

        print("== 3. giới hạn mỗi lượt, bản ghi hỏi lâu nhất trước")
        LOI["kieu"] = None
        CONG_NO["Debts"] = [no("TK-2026100%d-000%d" % (3 if s < 175 else 5, s), 1, 1) for s in range(169, 178)]   # mọi SO còn nợ đủ
        CONG_NO["Orders"] = []
        truoc =sorted(db.query(M.ChiTune).all(), key=lambda r: r.checked_at)
        k = DBN.mot_luot(db, n=2)
        db.expire_all()
        da = sorted(r.real_id for r in db.query(M.ChiTune) if r.checked_at > truoc[-1].checked_at)
        dung(k["da_hoi"].get("tam_ung") == 2 and da == sorted(r.real_id for r in truoc[:2]) and not k["loi"],
             "n=2: hỏi đúng 2 phiếu Chi trước hỏi lâu nhất", da)
        k = DBN.mot_luot(db, n=2)
        db.expire_all()
        da2 = sorted(r.real_id for r in db.query(M.ChiTune) if r.checked_at > truoc[-1].checked_at)
        dung(len(da2) == 4, "lượt sau xoay sang 2 phiếu kế tiếp", da2)

        print("== 4. thủ quỹ đã chi / khách đã trả → bên em đổi đúng")
        p8, p2, p3 = phieu("G4-0008-10/EPL"), phieu("G4-0002-10/EPL"), phieu("G4-0003-10/EPL")
        rec8 = chi_tu("G4-0008-10/EPL")
        cx = db.query(M.ChiChuXeTune).filter(M.ChiChuXeTune.ref_no == "TCX-261003140253-0a07").one()
        TRANG.update({rec8.real_id: 12, cx.real_id: 12, 99001: 13, 99002: 12})
        CONG_NO["Debts"] = [no("TK-20261003-000170", 1201.7, 1201.7), no("TK-20261003-000171", 472.5, 472.5),
                            no("TK-20261003-000173", 497.5, 497.5), no("TK-20261003-000174", 496.25, 496.25),
                            no("TK-20261005-000175", 493.75, 393.75), no("TK-20261005-000176", 470.0, 470.0)]
        CONG_NO["Orders"] = [don("TK-20261003-000169", 495.0), don("TK-20261005-000177", 1980000)]   # 169 thu đủ (05/10) · SO NL 177
        GOI.clear()
        k = DBN.mot_luot(db)
        db.expire_all()
        rec8 = chi_tu("G4-0008-10/EPL")
        iv8 = db.query(M.TripSection).filter(M.TripSection.trip_id == p8.id, M.TripSection.section == "travel").one()
        ptu = db.query(M.Voucher).filter(M.Voucher.trip_id == p8.id, M.Voucher.kind == "advance").one()
        dung(not k["loi"] and not k["loi_ban_ghi"] and k["cap_nhat"].get("tam_ung") == 1, "lượt sạch, 1 phiếu Chi trước đổi",
             {x: k[x] for x in ("da_hoi", "cap_nhat", "loi")})
        dung(rec8.status == "da_chi" and rec8.tune_status == 12 and rec8.post_by == "Thủ quỹ thử" and iv8.status == "paid"
             and ptu.status == "da_cap", "G4-0008: phiếu Chi trước ghi sổ → da_chi, mục IV đã chi, PTU đã cấp",
             (rec8.status, iv8.status, ptu.status))
        dung(sum(1 for r in db.query(M.ChiTune) if r.status == "da_gui") == 4, "4 phiếu Chi trước chưa ghi sổ vẫn chờ")
        v = BG.trang_thai_chi(db, [db.get(M.Trip, p8.id)])[p8.id]
        dung((v["lines_paid"], v["amount_open"]) == (3, 360000), "viên bàn giao G4-0008: 3 dòng đã chi, còn 360.000 (cùng lương)", v)
        cx = db.get(M.ChiChuXeTune, cx.id)
        p2, p3 = db.get(M.Trip, p2.id), db.get(M.Trip, p3.id)
        dung(cx.status == "da_chi" and p2.owner_paid and p3.owner_paid and p2.owner_payment_id == "TUNE:1368-CKH-261003-00001",
             "trả chủ xe ghi sổ → đề nghị da_chi, G4-0002 + G4-0003 đã trả (TUNE:<số phiếu>)", (cx.status, p2.owner_payment_id))
        pt = db.query(M.PhieuTienTune).filter(M.PhieuTienTune.real_id == 99001).one()
        cm = db.query(M.ChiMucTune).filter(M.ChiMucTune.real_id == 99002).one()
        v6 = db.query(M.TripSection).filter(M.TripSection.trip_id == p6.id, M.TripSection.section == "repair").one()
        dung(pt.status == "da_chi" and pt.tune_status == 13, "phiếu trả nhà cung cấp ghi sổ tạm → da_chi", pt.status)
        dung(cm.status == "da_chi" and v6.status == "paid", "phiếu Chi khác mục V ghi sổ → da_chi, mục V G4-0006 đã chi",
             (cm.status, v6.status))
        so = {b.order_code: b for b in db.query(M.GuiSoTune)}
        p1 = phieu("G4-0001-10/EPL")
        dung(so["TK-20261003-000169"].thu_trang_thai == "da_thu" and db.get(M.Trip, p1.id).finance_status == "paid",
             "SO 169 thu đủ → G4-0001 'đã thu' (finance_status paid)", so["TK-20261003-000169"].thu_trang_thai)
        dung(so["TK-20261005-000175"].thu_trang_thai == "thu_mot_phan" and abs(so["TK-20261005-000175"].thu_da_thu - 100) < 1e-6
             and db.get(M.Trip, p6.id).finance_status == "partial", "SO 175 thu 100 USD → thu một phần",
             (so["TK-20261005-000175"].thu_trang_thai, so["TK-20261005-000175"].thu_da_thu))
        dung(all(so[x].thu_trang_thai == "chua_thu" for x in ("TK-20261003-000170", "TK-20261005-000176")), "SO còn nợ đủ → chưa thu")
        nl = db.query(M.GuiSoNhienLieuTune).filter(M.GuiSoNhienLieuTune.order_code == "TK-20261005-000177").one()
        dung(nl.thu_trang_thai == "da_thu", "SO nhiên liệu 177 (G4-0007) thu đủ → da_thu", nl.thu_trang_thai)
        la = sorted({g for g in GOI if not (g[0] == "GET" and g[1].startswith("/api/v1/accounting/cmpayment-receipt/"))})
        dung(la == [("POST", "/api/v1/sales/debt/customer-detail")], "chỉ gọi đường ĐỌC (phiếu chi, công nợ) — không tạo / xoá gì", la)

        print("== 5. lượt sau bỏ bản ghi đã xong")
        GOI.clear()
        k = DBN.mot_luot(db)
        dung(k["da_hoi"].get("tam_ung") == 4 and not k["da_hoi"].get("tra_chu_xe") and not k["da_hoi"].get("phieu_tien")
             and not k["da_hoi"].get("chi_muc") and k["da_hoi"].get("so_cuoc") == 6 and not k["da_hoi"].get("so_nl")
             and not k["cap_nhat"], "chỉ hỏi 4 phiếu Chi trước + 6 SO cước còn nợ; không gì đổi", k["da_hoi"])

        print("== 6. bên kia từ chối MỘT phiếu (4xx) → bỏ qua phiếu đó, làm tiếp")
        p4 = phieu("G4-0004-10/EPL")
        LOI.update({"kieu": "4xx", "rid": chi_tu("G4-0004-10/EPL").real_id})
        k = DBN.mot_luot(db)
        LOI["kieu"] = None
        dung(not k["loi"] and len(k["loi_ban_ghi"]) == 1 and k["da_hoi"].get("tam_ung") == 3 and k["da_hoi"].get("so_cuoc") == 6,
             "lỗi một bản ghi ghi vào loi_ban_ghi, lượt chạy hết", {x: k[x] for x in ("da_hoi", "loi_ban_ghi")})
        dung(chi_tu("G4-0004-10/EPL").error_code == CHI.MAT, "phiếu bên kia từ chối đọc → PHIEU_CHI_MAT (luật sẵn có của chi_tune)",
             p4.doc_no)

        print("== 7. lượt của luồng nền: khoá, chống chạy chồng, tình trạng")
        DBN._co_cau_hinh = lambda: False
        r = DBN.chay_luot(tao_phien, ep=True)
        dung("token" in (r.get("bo_qua") or ""), "chưa cấu hình hệ kế toán → bỏ lượt, ghi lý do", r.get("bo_qua"))
        DBN._co_cau_hinh = lambda: True
        goc_luot = int(DBN.doc_tinh_trang(db).get("so_luot") or 0)     # máy khác (luồng nền thật) có thể đã chạy trên d7
        LOI["kieu"] = "mang"
        r = DBN.chay_luot(tao_phien, ep=True)
        LOI["kieu"] = None
        dung(r.get("so_luot") == goc_luot + 1 and "KHONG_GOI_DUOC" in (r.get("loi") or "") and "KHONG_GOI_DUOC" in (r.get("loi_gan_nhat") or {}).get("loi", ""),
             "lượt lỗi mạng → ghi lỗi lượt + lỗi gần nhất", {x: r.get(x) for x in ("so_luot", "loi")})
        r = DBN.chay_luot(tao_phien, ep=True)
        dung(r.get("xong") and r.get("so_luot") == goc_luot + 2 and r.get("loi") is None and r.get("da_hoi", {}).get("tam_ung") == 3
             and "KHONG_GOI_DUOC" in (r.get("loi_gan_nhat") or {}).get("loi", ""),
             "lượt sạch → lần chạy, đã hỏi, đã cập nhật; vẫn giữ lỗi gần nhất", {x: r.get(x) for x in ("so_luot", "da_hoi", "cap_nhat", "loi")})
        r = DBN.chay_luot(tao_phien)
        dung("vừa chạy" in (r.get("bo_qua") or ""), "máy khác vừa chạy chưa đủ chu kỳ → bỏ", r.get("bo_qua"))
        DBN._KHOA.acquire()
        try:
            r = DBN.chay_luot(tao_phien, ep=True)
        finally:
            DBN._KHOA.release()
        dung("trong tiến trình" in (r.get("bo_qua") or ""), "lượt khác đang chạy trong tiến trình → bỏ", r.get("bo_qua"))
        c2 = eng.connect()
        try:
            dung(c2.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": DBN.KHOA_PG}).scalar(), "worker khác giữ khoá Postgres")
            r = DBN.chay_luot(tao_phien, ep=True)
            dung("worker khác" in (r.get("bo_qua") or ""), "→ lượt ở worker này bỏ", r.get("bo_qua"))
            c2.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": DBN.KHOA_PG})
        finally:
            c2.rollback(); c2.close()

        print("== 8. đường xem tình trạng (Sếp)")
        app.dependency_overrides[nguoi_hien_tai] = lambda: types.SimpleNamespace(role="admin", full_name="Thử", username="thu", id="t",
                                                                                 driver_id=None, place_id=None)
        g = c.get("/api/dong-bo-nen")
        x = g.json() if g.status_code == 200 else {}
        dung(g.status_code == 200 and x.get("phut") == DBN.phut() and x.get("gioi_han") == DBN.gioi_han()
             and (x.get("lan_gan_nhat") or {}).get("so_luot") == goc_luot + 2 and x.get("dang_chay_luot") is False,
             "Sếp xem: chu kỳ, giới hạn, lượt gần nhất", {k_: x.get(k_) for k_ in ("bat", "phut", "gioi_han", "luong_song")})
        app.dependency_overrides[nguoi_hien_tai] = lambda: types.SimpleNamespace(role="acct", full_name="KT", username="kt", id="k",
                                                                                 driver_id=None, place_id=None)
        dung(c.get("/api/dong-bo-nen").status_code == 403, "kế toán → 403")
    finally:
        CHI._goi, NL._goi, DBN._co_cau_hinh = goc_goi, goc_nl, goc_ch
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    print("TỔNG: %d/%d đạt" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
