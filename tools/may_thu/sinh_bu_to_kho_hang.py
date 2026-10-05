# -*- coding: utf-8 -*-
"""SINH BÙ TỜ KHO HÀNG khách gửi cho DO cũ (05/10) — DO gom đã có dòng goods_moves `in` mà thiếu PNK_HH, DO giao đã có `out` mà thiếu
PXK_HH (DO nhập / xuất trước khi máy tự tạo phiếu, hoặc sổ chép từ kho tạm bằng chuyen_ton_dau_qlsx.py --hang-khach).

    python tools/may_thu/sinh_bu_to_kho_hang.py                    CHỈ LIỆT KÊ, không ghi gì (bản sao .may_thu/url_epl_lao_d7.txt)
    python tools/may_thu/sinh_bu_to_kho_hang.py --that             sinh tờ, một giao dịch, hỏng ở đâu rollback cả
    python tools/may_thu/sinh_bu_to_kho_hang.py --url-tep <tệp>    tệp chứa chuỗi nối khác (phải là bản sao …_d<số>)
    python tools/may_thu/sinh_bu_to_kho_hang.py --db-that [--that] DB THẬT theo DATABASE_URL trong .env — phải gõ rõ cờ này, có cảnh báo

  · Tờ sinh từ CHÍNH dòng sổ đang có (services/kho_hang_dia.dam_bao_to): không nhập / xuất lại, không đổi tồn. Ngày tờ = ngày dòng sổ,
    người = người ghi dòng sổ (trống thì --nguoi), payload đánh dấu `sinh_bu`. Số tờ theo quy ước chứng từ (LOAI/YYMM/0001).
  · Chạy lại không sinh trùng (một DO một tờ — khoá nguồn của chung_tu). Không in chuỗi nối, chỉ in tên DB.
  · Hàm lõi `liet_ke(db)` / `sinh_bu(db, nguoi)` dùng phiên của người gọi, không commit — kiem/thu_kho_hang.py gọi trong giao dịch ROLLBACK.
"""
import argparse
import os
import re
import sys

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
APP = os.path.join(GOC, "backend", "app")
NGUOI_MAC_DINH = "Sinh bù tờ kho hàng (công cụ 05/10)"
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def liet_ke(db):
    """DO thiếu tờ kho hàng: [{trip_id, do_no, kind, loai, tan, ngay}] — gom thiếu PNK_HH trước, giao thiếu PXK_HH sau."""
    from sqlalchemy import and_, exists, func

    from models import ChungTu, GoodsMove, Trip
    G = GoodsMove
    ra = []
    for kind, mv, loai in (("gom", "in", "PNK_HH"), ("giao", "out", "PXK_HH")):
        co_to = exists().where(and_(ChungTu.loai == loai, ChungTu.nguon_bang == "trips", ChungTu.nguon_id == Trip.id))
        q = (db.query(Trip.id, Trip.doc_no, func.sum(G.qty_t).label("tan"), func.min(G.move_date).label("ngay"))
             .join(G, and_(G.trip_id == Trip.id, G.kind == mv))
             .filter(Trip.kind == kind, ~co_to)
             .group_by(Trip.id, Trip.doc_no).order_by(func.min(G.move_date), Trip.doc_no))
        for r in q.all():
            ra.append({"trip_id": r.id, "do_no": r.doc_no, "kind": kind, "loai": loai, "tan": round(float(r.tan or 0), 3),
                       "ngay": r.ngay.isoformat() if r.ngay else None})
    return ra


def sinh_bu(db, nguoi=NGUOI_MAC_DINH):
    """Sinh tờ cho mọi DO `liet_ke` trả về (flush, KHÔNG commit). → {so_thieu, da_sinh: [{do_no, loai, so}], bo_qua: [...]}."""
    from models import Trip
    from services import kho_hang_dia as KHD
    ds = liet_ke(db)
    da, bo = [], []
    for x in ds:
        p = db.get(Trip, x["trip_id"])
        to = KHD.dam_bao_to(db, p, nguoi) if p is not None else None
        if to is None:
            bo.append(dict(x, ly_do="không có dòng sổ / DO không còn"))
        else:
            da.append({"do_no": x["do_no"], "loai": x["loai"], "so": to.so, "tan": x["tan"], "ngay": x["ngay"]})
    db.flush()
    return {"so_thieu": len(ds), "da_sinh": da, "bo_qua": bo}


def _url(a):
    if a.db_that:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(GOC, ".env"))
        u = (os.getenv("DATABASE_URL") or "").strip()
        if not u:
            sys.exit("--db-that: .env không có DATABASE_URL — dừng.")
        return u, True
    tep = a.url_tep or os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt")
    u = open(tep, encoding="utf-8").read().strip()
    if not re.search(r"_d\d+$", u.rsplit("/", 1)[-1].split("?")[0]):
        sys.exit("Chuỗi nối trong %s không trỏ bản sao (…_d<số>) — dừng. DB thật thì phải gõ rõ --db-that." % tep)
    return u, False


def main():
    ap = argparse.ArgumentParser(description="Sinh bù tờ PNK_HH / PXK_HH cho DO cũ (mặc định chỉ liệt kê).")
    ap.add_argument("--that", action="store_true", help="ghi thật (mặc định chỉ liệt kê)")
    ap.add_argument("--url-tep", help="tệp chứa chuỗi nối (mặc định .may_thu/url_epl_lao_d7.txt)")
    ap.add_argument("--db-that", action="store_true", help="dùng DB THẬT theo DATABASE_URL trong .env (cảnh báo)")
    ap.add_argument("--nguoi", default=NGUOI_MAC_DINH, help="người ghi trên tờ khi dòng sổ không ghi người làm")
    a = ap.parse_args()
    url, that_db = _url(a)
    os.environ["DATABASE_URL"] = url                 # trước khi nạp database.py (load_dotenv không ghi đè)
    if (os.getenv("KHO_NGUON") or "qlsx").strip().lower() == "kho_tam":
        sys.exit("KHO_NGUON=kho_tam: sổ kho hàng đang ở kho tạm, không sinh tờ ở trang điều xe — dừng.")
    sys.path.insert(0, APP)
    from database import SessionLocal, engine
    ten_db = engine.url.database
    if that_db:
        print("!!! CẢNH BÁO: đang nối DB THẬT «%s» (--db-that)%s." % (ten_db, " — SẼ GHI TỜ" if a.that else ", chỉ liệt kê"))
    print("DB: %s · %s" % (ten_db, "GHI THẬT" if a.that else "chỉ liệt kê (thêm --that để ghi)"))
    db = SessionLocal()
    try:
        ds = liet_ke(db)
        for x in ds:
            print("  %-7s %-18s %-6s %9.3f t  %s" % (x["loai"], x["do_no"], x["kind"], x["tan"], x["ngay"] or ""))
        print("Thiếu tờ: %d DO (gom thiếu PNK_HH %d · giao thiếu PXK_HH %d)" % (
            len(ds), sum(1 for x in ds if x["loai"] == "PNK_HH"), sum(1 for x in ds if x["loai"] == "PXK_HH")))
        if not a.that or not ds:
            db.rollback()
            print("Không ghi gì." if not a.that else "Không có gì để sinh.")
            return
        kq = sinh_bu(db, a.nguoi)
        db.commit()
        for x in kq["da_sinh"]:
            print("  + %-18s %s" % (x["do_no"], x["so"]))
        for x in kq["bo_qua"]:
            print("  ! bỏ qua %-18s %s" % (x["do_no"], x["ly_do"]))
        print("TỔNG KẾT: thiếu %d · đã sinh %d · bỏ qua %d" % (kq["so_thieu"], len(kq["da_sinh"]), len(kq["bo_qua"])))
    except Exception as e:                               # noqa: BLE001 — không in chuỗi nối
        db.rollback()
        sys.exit("HỎNG, đã rollback, không ghi gì: %s" % str(e).replace(url, "<url>")[:500])
    finally:
        db.close()


if __name__ == "__main__":
    main()
