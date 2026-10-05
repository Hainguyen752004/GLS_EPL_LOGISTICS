# -*- coding: utf-8 -*-
"""Thử `line_key` + `settlement` từng dòng của gói bàn giao DO (02/10, màn "Tổng hợp thu chi" bên Web anh Tune) —
services/chung_tu_dong_do.py gọi từ ban_giao.dong_goi.

    python kiem/thu_chung_tu_dong_do.py [số phiếu …]

CHỈ ĐỌC bản sao DB _d7: chuỗi nối lấy từ .may_thu/url_epl_lao_d7.txt (không in ra). Bài chạy trong MỘT giao dịch rồi ROLLBACK
— không commit gì; bảng mới của đợt 02/10 tối (gui_so_nhien_lieu_tune, can_tru_tune) chưa có trên bản sao thì dựng trong chính
giao dịch đó (rollback xoá luôn). Không gọi mạng, không cần máy chủ chạy.

  A Hai phiếu mẫu THU-KBAZ (khoá 01/10): in line_key + settlement từng dòng, đối chiếu với số chứng từ thật trong DB:
      G1 xe nhà  — cước SO · dầu kho (chưa có bút toán xuất kho — khoá trước luật) · dầu mua dọc đường (ngoài tạm ứng → tất
                   toán tháng) · garage mục V (Chi khác) · ăn, điện thoại (tạm ứng) · tiền nước, tiền chuyến (cùng lương → open)
      T1 xe thuê — cước SO · dầu kho xuất bán (chưa có bút toán) · sang VN, điện thoại, cao tốc tiền mặt (tạm ứng) ·
                   chipping (ghi nợ NCC, bút toán GL) · tiền thuê: bút toán thue_xe + phiếu chi trả chủ xe
  B Mọi DO đã về + đã khoá trên bản sao: gói dựng được, line_key đúng dạng (chữ / số / :_- , ≤ 60, ghép tiền tố ≤ 100), không
    trùng trong một DO, state / kind thuộc tập đã hẹn, has_voucher có số, bỏ các khoá mới thì gói y như dong_goi(chung_tu=False).
    In bảng đếm (state, kind).
"""
import collections
import os
import re
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ đọc bản sao.")
os.environ["DATABASE_URL"] = URL                  # database.py dựng engine theo biến này — cũng là bản sao
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from sqlalchemy import create_engine          # noqa: E402
from sqlalchemy.orm import sessionmaker       # noqa: E402

from models import Trip                       # noqa: E402
from services import ban_giao as BG           # noqa: E402

LOI = []
STATE = {"has_voucher", "pending", "not_payable", "open"}
KIND = {"sales_order", "advance", "pay_now", "journal", "driver_settlement", "owner_payment", "supplier_payment", "toll_card",
        "owner_paid", "payroll", "manual", None}
KHOA = re.compile(r"^[A-Za-z0-9:_-]{1,60}$")
MOI = ("line_key", "settlement", "debt")


def dung(dk, buoc):
    print("  %s %s" % ("✓" if dk else "SAI", buoc))
    if not dk:
        LOI.append(buoc)


def in_goi(g):
    h = g["header"]
    print("  header.line_key_prefix = %s" % h.get("line_key_prefix"))
    if h.get("hire"):
        for k in ("settlement", "journal"):
            s = h["hire"].get(k) or {}
            print("  hire %-10s %-11s %-13s ref=%s doc=%s [%s] %s" % (k, s.get("state"), s.get("kind"), s.get("ref_no"),
                                                                   s.get("doc_no"), s.get("doc_status"), s.get("label")))
    for x in g["details"]:
        s = x.get("settlement") or {}
        print("  %-2s %-18s %-30.30s %-11s %-17s ref=%s doc=%s [%s]" % (
            x["line_no"], x.get("line_key"), x.get("name"), s.get("state"), s.get("kind"), s.get("ref_no"), s.get("doc_no"),
            s.get("doc_status")))
        print("      %s" % s.get("label"))
        if x.get("debt"):
            print("      debt %s" % x["debt"])


def theo_ten(g, ten):
    """Dòng chi theo item_key (hoặc tên gõ tay chứa chữ)."""
    return [x for x in g["details"] if x.get("item_key") == ten or (x.get("name") or "").lower().find(ten) >= 0]


def mot(g, ten, nguon=None):
    ds = theo_ten(g, ten)
    if nguon:
        ds = [x for x in ds if x.get("source") == nguon]
    return (ds[0].get("settlement") or {}) if len(ds) == 1 else {"state": "KHONG_THAY_HOAC_TRUNG(%d)" % len(ds)}


def kiem_g1(g, p):
    s = g["details"][0]["settlement"]
    dung(s["state"] == "has_voucher" and s["kind"] == "sales_order" and s["doc_no"] == "TK-20261001-000164",
         "G1 cước → SO TK-20261001-000164 (%s %s)" % (s["state"], s["doc_no"]))
    dung((g["details"][0].get("debt") or {}).get("order_code") == "TK-20261001-000164", "G1 cước có debt theo SO")
    s = mot(g, "diesel", "kho")
    dung(s["state"] == "pending" and s["kind"] == "journal" and (s["ref_no"] or "").startswith("EPLLAO-xuat_noi_bo-dau:"),
         "G1 dầu kho 120 l → pending journal xuất nội bộ (chưa có bút toán) (%s %s)" % (s["state"], s["ref_no"]))
    s = mot(g, "diesel", "mua")
    dung(s["kind"] == "driver_settlement" and s["state"] in ("has_voucher", "pending"),
         "G1 dầu mua dọc đường 30 l (ngoài tạm ứng 250.000) → tất toán tháng (%s %s %s)" % (s["state"], s["ref_no"], s["doc_no"]))
    s = mot(g, "garage")
    dung(s["state"] == "has_voucher" and s["kind"] == "pay_now" and s["doc_no"] == "1368-CKH-261001-00067",
         "G1 garage mục V → Chi khác 1368-CKH-261001-00067 (%s %s)" % (s["state"], s["doc_no"]))
    for k in ("x_food", "x_phone"):
        s = mot(g, k)
        dung(s["state"] == "has_voucher" and s["kind"] == "advance" and s["doc_no"] == "1368-CTR-261001-00072"
             and s["ref_no"] == "PTU-THU-KBAZ-G1/EPL", "G1 %s → tạm ứng PTU-THU-KBAZ-G1/EPL · 1368-CTR-261001-00072 (%s %s)" % (
                 k, s["state"], s["doc_no"]))
    for k in ("x_water", "x_trip"):
        s = mot(g, k)
        dung(s["state"] == "open" and s["kind"] == "payroll", "G1 %s → open payroll (%s %s)" % (k, s["state"], s["kind"]))


def kiem_t1(g, p):
    s = g["details"][0]["settlement"]
    dung(s["state"] == "has_voucher" and s["kind"] == "sales_order" and s["doc_no"] == "TK-20261001-000165",
         "T1 cước → SO TK-20261001-000165 (%s %s)" % (s["state"], s["doc_no"]))
    s = mot(g, "diesel", "kho")
    # 02/10 tối: phần bán dầu kho cho đối tác là SO nhiên liệu (services/so_nhien_lieu.py) — chưa bấm Tạo SO thì pending
    dung(s["kind"] == "sales_order" and s["state"] in ("has_voucher", "pending"),
         "T1 dầu kho 200 l → xuất bán = SO nhiên liệu (%s %s %s)" % (s["state"], s["ref_no"], s["doc_no"]))
    dung("fuel_so" in g["header"], "T1 header.fuel_so có khoá (%s)" % (g["header"].get("fuel_so"),))
    for k in ("x_vn", "x_phone", "x_toll"):
        s = mot(g, k)
        dung(s["state"] == "has_voucher" and s["kind"] == "advance" and s["doc_no"] == "1368-CTR-261001-00073"
             and s["ref_no"] == "PTU-THU-KBAZ-T1/EPL", "T1 %s → tạm ứng PTU-THU-KBAZ-T1/EPL · 1368-CTR-261001-00073 (%s %s)" % (
                 k, s["state"], s["doc_no"]))
    s = mot(g, "x_chip_lao")
    dung(s["state"] == "has_voucher" and s["kind"] == "journal" and s["doc_no"] == "GL021020269",
         "T1 chipping → no_ncc GL021020269 (%s %s)" % (s["state"], s["doc_no"]))
    h = g["header"]["hire"]
    dung(h.get("line_key") == "thue:" + p.id, "T1 hire.line_key = thue:<Trip.id>")
    dung(h["journal"]["doc_no"] == "GL021020268" and h["journal"]["state"] == "has_voucher", "T1 hire.journal → thue_xe GL021020268")
    dung(h["settlement"]["state"] == "has_voucher" and h["settlement"]["kind"] == "owner_payment"
         and h["settlement"]["doc_no"] == "1368-CKH-261001-00069", "T1 hire.settlement → trả chủ xe 1368-CKH-261001-00069 (%s)" % (
             h["settlement"]["ref_no"]))


def bo_khoa_moi(g):
    h = {k: v for k, v in g["header"].items() if k not in ("line_key_prefix", "fuel_so")}
    if isinstance(h.get("hire"), dict):
        h["hire"] = {k: v for k, v in h["hire"].items() if k not in ("line_key", "settlement", "journal")}
    return {"header": h, "details": [{k: v for k, v in x.items() if k not in MOI} for x in g["details"]]}


def kiem_mot_do(db, p, dem):
    g = BG.dong_goi(db, p)
    h = g["header"]
    tt = h.get("line_key_prefix") or ""
    sai = []
    if tt != "DO:%s:" % h["do_id"]:
        sai.append("tiền tố %r" % tt)
    khoa = [x.get("line_key") for x in g["details"]] + ([h["hire"].get("line_key")] if h.get("hire") else [])
    for k in khoa:
        if not k or not KHOA.match(k) or len(tt + k) > 100:
            sai.append("line_key %r" % k)
    if len(set(khoa)) != len(khoa):
        sai.append("line_key trùng")
    ds = [x.get("settlement") for x in g["details"]] + ([h["hire"]["settlement"], h["hire"]["journal"]] if h.get("hire") else [])
    for s in ds:
        if not s or s.get("state") not in STATE or s.get("kind") not in KIND or not s.get("label"):
            sai.append("settlement %r" % (s,))
        elif s["state"] == "has_voucher" and not (s.get("doc_no") or s.get("ref_no")):
            sai.append("has_voucher không số %r" % (s,))
    for x in g["details"]:
        s = x["settlement"]
        dem[(s["state"], s["kind"])] += 1
    if bo_khoa_moi(g) != BG.dong_goi(db, p, chung_tu=False):
        sai.append("bỏ khoá mới thì gói khác dong_goi(chung_tu=False)")
    return g, sai


def main():
    import models as M
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    from sqlalchemy import text
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))     # 8011 chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
    for t in ("gui_so_nhien_lieu_tune", "can_tru_tune"):
        M.Base.metadata.tables[t].create(bind=conn, checkfirst=True)
    sys.path.insert(0, os.path.join(GOC, "kiem"))
    import _mau_kbaz as MAU
    MAU.chan_kho_qlsx()
    MAU.dung_mau(conn)                                       # d7 đã dọn bộ mẫu cũ (03/10): dựng lại trong giao dịch, rollback xoá
    db = sessionmaker(bind=conn, autoflush=False)()
    try:
        print("A. hai phiếu mẫu THU-KBAZ")
        for so, ham in (("THU-KBAZ-G1/EPL", kiem_g1), ("THU-KBAZ-T1/EPL", kiem_t1)):
            p = db.query(Trip).filter(Trip.doc_no == so).first()
            print("-" * 110)
            if p is None or not BG.ban_giao_duoc(p):
                dung(False, "%s có trên bản sao, đã về và đã khoá" % so)
                continue
            print("%s · %s · %s" % (so, BG.ma_do(p), "xe thuê" if p.company == "joint" else "xe nhà"))
            g, sai = kiem_mot_do(db, p, collections.Counter())
            in_goi(g)
            dung(not sai, "%s: gói đúng dạng%s" % (so, (" — " + "; ".join(sai)) if sai else ""))
            ham(g, p)
        for so in sys.argv[1:]:
            p = db.query(Trip).filter(Trip.doc_no == so).first()
            print("-" * 110)
            if p is None or not BG.ban_giao_duoc(p):
                print("%s: không có / chưa về, chưa khoá" % so)
                continue
            print("%s · %s" % (so, BG.ma_do(p)))
            in_goi(kiem_mot_do(db, p, collections.Counter())[0])

        print("=" * 110)
        print("B. mọi DO đã về + đã khoá trên bản sao")
        dem, hong = collections.Counter(), []
        ds = db.query(Trip).filter(Trip.locked.is_(True), Trip.transport_status == "arrived").order_by(Trip.locked_at).all()
        for p in ds:
            try:
                _, sai = kiem_mot_do(db, p, dem)
            except Exception as e:                              # noqa: BLE001 — gói nào hỏng thì ghi, chạy tiếp
                sai = ["lỗi %s: %s" % (type(e).__name__, str(e).replace(URL, "<url>")[:200])]
            if sai:
                hong.append((p.doc_no, sai))
        for so, sai in hong[:15]:
            print("    %s: %s" % (so, "; ".join(sai)[:300]))
        dung(not hong, "%d DO: gói dựng được, line_key / settlement đúng dạng, khoá cũ không đổi (%d hỏng)" % (len(ds), len(hong)))
        print("  đếm dòng theo (state, kind):")
        for (st, k), n in sorted(dem.items(), key=lambda kv: (-kv[1], str(kv[0]))):
            print("    %-12s %-18s %d" % (st, k, n))
    finally:
        db.close()
        ngoai.rollback()
        conn.close()
    print("=" * 110)
    print("XONG — %s" % ("không có lỗi" if not LOI else "%d chỗ SAI: %s" % (len(LOI), " | ".join(LOI))))
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
