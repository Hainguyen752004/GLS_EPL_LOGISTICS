# -*- coding: utf-8 -*-
"""ĐIỀN BẢN CHÉP DOANH THU lên phiếu — đợt 7a (28/09): hoá đơn, thu tiền dời sang trang kế toán.

    python tools/ban_chep_doanh_thu.py          chạy thử: in ra sẽ điền gì — KHÔNG ghi
    python tools/ban_chep_doanh_thu.py that     ghi thật

Chạy SAU tools/doi_doanh_thu.py bên EPL_KETOAN. Từ ngày dời, mỗi lần xuất hoá đơn / thu tiền trang kế toán tự ghi bản chép
sang phiếu. Công cụ này điền bản chép cho dữ liệu CŨ, lấy từ chính các bảng bên này (trip_payments · invoices · tờ HD đã
đẩy) — đúng các số màn phiếu vẫn hiện trước ngày dời:

    trips.collected_lak   = Σ trip_payments.amount_lak của phiếu
    trips.last_paid_date  = ngày lần thu gần nhất
    trips.invoiced_date   = ngày tờ HD của phiếu (hoá đơn riêng) · ngày tờ gộp (phiếu trong tờ gộp)
    trips.inv_no          = số tờ gộp

Chỉ điền ô đang trống hoặc đang khác; không đụng invoiced / invoice_id / finance_status (đã đúng từ trước). Cột mới do máy
chủ tự thêm lúc khởi động bằng mã đợt 7a — ghi thật thì công cụ gọi đúng hàm đó trước; chạy thử chỉ đọc, không thêm cột.
"""
import os
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
from sqlalchemy import inspect, text  # noqa: E402

from database import SessionLocal, engine, tao_bang  # noqa: E402

THAT = len(sys.argv) > 1 and sys.argv[1] == "that"


def main():
    # chạy thử là CHỈ ĐỌC: không thêm cột trên DB thật — cột chưa có thì coi như bản chép đang trống
    co_cot = "collected_lak" in {c["name"] for c in inspect(engine).get_columns("trips")}
    if THAT:
        tao_bang(); co_cot = True
    print("DB:", engine.url.database, "" if co_cot else "(chưa có cột bản chép — máy chủ mã đợt 7a sẽ thêm)")
    db = SessionLocal()
    cot = ("t.collected_lak, t.last_paid_date, t.invoiced_date, t.inv_no" if co_cot
           else "NULL AS collected_lak, NULL AS last_paid_date, NULL AS invoiced_date, NULL AS inv_no")
    cau = text("""
        SELECT t.id, t.doc_no, """ + cot + """,
               COALESCE(p.tong, 0) AS tong, p.cuoi,
               COALESCE(i.inv_date, h.ngay) AS ngay_hd, i.inv_no AS so_gop
        FROM trips t
        LEFT JOIN (SELECT trip_id, SUM(amount_lak) AS tong, MAX(pay_date) AS cuoi FROM trip_payments GROUP BY trip_id) p ON p.trip_id = t.id
        LEFT JOIN invoices i ON i.id = t.invoice_id
        LEFT JOIN (SELECT nguon_id, MIN(ngay) AS ngay FROM chung_tu WHERE loai = 'HD' AND nguon_bang = 'trips' GROUP BY nguon_id) h ON h.nguon_id = t.id
        WHERE t.invoiced IS TRUE OR t.invoice_id IS NOT NULL OR p.tong IS NOT NULL
        ORDER BY t.doc_date, t.doc_no""")
    doi = []
    for r in db.execute(cau).mappings():
        moi = {"collected_lak": round(float(r["tong"] or 0)), "last_paid_date": r["cuoi"], "invoiced_date": r["ngay_hd"], "inv_no": r["so_gop"]}
        cu = {"collected_lak": round(float(r["collected_lak"] or 0)), "last_paid_date": r["last_paid_date"],
              "invoiced_date": r["invoiced_date"], "inv_no": r["inv_no"]}
        if moi != cu:
            doi.append((r["id"], r["doc_no"], cu, moi))
    print("%s bản chép cho %d phiếu:" % ("ĐIỀN" if THAT else "SẼ ĐIỀN", len(doi)))
    print("   %-18s %14s %12s %12s %16s" % ("phiếu", "đã thu LAK", "thu gần nhất", "ngày HĐ", "tờ gộp"))
    for _i, so, _cu, m in doi:
        print("   %-18s %14s %12s %12s %16s" % (so, m["collected_lak"], m["last_paid_date"] or "—", m["invoiced_date"] or "—", m["inv_no"] or "—"))
    if THAT:
        for i, _so, _cu, m in doi:
            db.execute(text("UPDATE trips SET collected_lak = :c, last_paid_date = :d, invoiced_date = :h, inv_no = :n WHERE id = :i"),
                       {"c": m["collected_lak"], "d": m["last_paid_date"], "h": m["invoiced_date"], "n": m["inv_no"], "i": i})
        # phiếu chưa thu đồng nào: 0 thay vì trống, để mọi phép cộng bên báo cáo đọc thẳng
        db.execute(text("UPDATE trips SET collected_lak = 0 WHERE collected_lak IS NULL"))
        db.commit()
        print("\nĐÃ GHI — bản chép trên phiếu khớp sổ thu tiền (nay ở trang kế toán).")
    else:
        db.rollback(); print("\n(chạy thử — chưa ghi gì; thêm tham số 'that' để ghi thật)")
    db.close()


if __name__ == "__main__":
    main()
