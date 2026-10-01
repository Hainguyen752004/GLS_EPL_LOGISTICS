# -*- coding: utf-8 -*-
"""BỎ HẾT số tiền của TRANG KẾ TOÁN TẠM trên trang điều xe — chủ dự án chốt 01/10/2026: số tiền bên trang tạm là SỐ THỬ,
bỏ hết; cắt sổ hôm nay, từ giờ mọi việc tiền ở hệ kế toán anh Tune. Trang tạm chỉ còn làm KHO TẠM.

    python tools/bo_tien_trang_tam.py          # chỉ ĐẾM, không sửa gì
    python tools/bo_tien_trang_tam.py --ghi    # xoá thật (một giao dịch, lỗi là trả lại hết)

DB lấy theo DATABASE_URL (biến môi trường, không thì .env) — chạy trên máy thật thì phải được chủ dự án cho phép.

Làm gì:
  · phiếu (trips): bỏ cờ hoá đơn / đã thu của trang tạm — invoiced, inv_no, invoiced_date, invoice_id, collected_lak,
    finance_status về "unpaid"; bỏ owner_payment_id của các đợt trả chủ xe ở trang tạm (mã "TUNE:…" của hệ anh Tune giữ)
  · xoá bản chép: hoá đơn gộp + các lần thu (invoices, invoice_payments), đợt trả chủ xe trang tạm (owner_payments),
    bản chốt tất toán (driver_settlements); hàng bán cho chủ xe bỏ trỏ tới đợt trả trang tạm (sales.owner_payment_id)
KHÔNG đụng: phần kho (dầu, phụ tùng, quặng, cấp phát), SO / phiếu chi đã gửi anh Tune (GuiSoTune, ChiTune, ChiChuXeTune),
chứng từ (ChungTu) — vẫn in / xem được.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))

from sqlalchemy import or_  # noqa: E402

from database import SessionLocal  # noqa: E402
from models import DriverSettlement, Invoice, InvoicePayment, OwnerPayment, Sale, Trip  # noqa: E402


def main(ghi):
    db = SessionLocal()
    try:
        cu_tra = or_(Trip.owner_payment_id.is_(None), ~Trip.owner_payment_id.like("TUNE:%"))
        phieu = db.query(Trip).filter(or_(Trip.invoiced.is_(True), Trip.inv_no.isnot(None), Trip.invoice_id.isnot(None),
                                          Trip.collected_lak > 0, Trip.finance_status != "unpaid",
                                          (Trip.owner_payment_id.isnot(None) & cu_tra))).all()
        dem = {
            "phiếu có dấu tiền trang tạm": len(phieu),
            "  · đã hoá đơn": sum(1 for p in phieu if p.invoiced),
            "  · đã thu (một phần / đủ)": sum(1 for p in phieu if (p.collected_lak or 0) > 0 or p.finance_status != "unpaid"),
            "  · đã trả chủ xe ở trang tạm": sum(1 for p in phieu if p.owner_payment_id and not p.owner_payment_id.startswith("TUNE:")),
            "hoá đơn gộp (invoices)": db.query(Invoice).count(),
            "lần thu (invoice_payments)": db.query(InvoicePayment).count(),
            "đợt trả chủ xe trang tạm (owner_payments)": db.query(OwnerPayment).count(),
            "bản chốt tất toán (driver_settlements)": db.query(DriverSettlement).count(),
            "hàng bán trỏ đợt trả trang tạm (sales)": db.query(Sale).filter(Sale.owner_payment_id.isnot(None)).count(),
        }
        for k, v in dem.items():
            print("%-45s %s" % (k, v))
        if not ghi:
            print("\nCHỈ ĐẾM — chưa sửa gì. Thêm --ghi để xoá thật.")
            return
        for p in phieu:
            p.invoiced, p.inv_no, p.invoiced_date, p.invoice_id = False, None, None, None
            p.collected_lak, p.finance_status = 0, "unpaid"
            if p.owner_payment_id and not p.owner_payment_id.startswith("TUNE:"):
                p.owner_payment_id = None
        db.query(Sale).filter(Sale.owner_payment_id.isnot(None)).update({Sale.owner_payment_id: None}, synchronize_session=False)
        db.query(InvoicePayment).delete(synchronize_session=False)
        db.query(Invoice).delete(synchronize_session=False)
        db.query(OwnerPayment).delete(synchronize_session=False)
        db.query(DriverSettlement).delete(synchronize_session=False)
        db.commit()
        print("\nĐÃ XOÁ. Mọi DO đã khoá giờ gửi SO sang hệ anh Tune từ đầu; trả chủ xe, tất toán làm lại ở hệ anh Tune.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main("--ghi" in sys.argv[1:])
