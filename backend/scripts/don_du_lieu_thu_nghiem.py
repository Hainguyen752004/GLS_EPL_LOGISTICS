"""Don du lieu THU NGHIEM con sot trong co so du lieu that.

Vi sao can: cac lan chay kiem end-to-end va cac lan soi bang tay de lai nhung
dong mang ma `E2E-*`, `*-PROBE-*`, `*-STRESS-*` trong cung bang voi du lieu
demo. Chung khong lam vo gi ca, nhung chung HIEN RA tren man hinh: danh sach
bao gia co dong "E2E-QT-20260805090149-HKJ7", danh sach khach hang co
"CUS-PROBE-1788405635". Trong mot ban demo cho nguoi khac xem thi may dong do
noi rang he thong day rac.

CAI GI XOA, va vi sao:

  · `E2E-*`, `*-PROBE-*`, `*-STRESS-*`: rac may sinh tu cac lan chay kiem.
  · `LIVE-*`: nhung dong do NGUOI dung bam ra khi thu ung dung. Ban dau tap
    lenh nay CO Y giu chung lai, vi xoa du lieu cua nguoi khac la viec khong
    duoc tu y lam. Chu du an da yeu cau ro "xoa du lieu cu roi nap bo mau moi",
    nen gio chung nam trong danh sach — va do duoc la chung lam ban man hinh
    that: `LIVE-TRIP-20260822-001` hien trong bang chuyen, `LIVE-DO-20260822-001`
    hien trong danh sach theo doi, ca hai mang ngay thang 8.
  · `QT-2026-001`: bao gia sot lai tu bo nap CU `seed_full_demo.py`. No khong
    co tuyen, tong chi phi bang 0, va khong bo nap nao dang dung con sinh ra no.

CAI GI KHONG XOA:

  · Moi dong `DEMO-*`: day chinh la bo du lieu mau, do `seed_demo` quan ly. Nap
    lai bo mau se tu dung lai chung.
  · Danh muc nen: loai xe, dia diem, cong thuc gia thanh. Chung khong mang tien
    to nao trong danh sach tren nen khong bi cham tay.

Chay:  python scripts/don_du_lieu_thu_nghiem.py [--that]

Khong co `--that` thi chi DEM va in ra, khong xoa gi — de xem truoc se mat
nhung dong nao. Xoa la viec khong lui lai duoc, nen mac dinh phai la khong xoa.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlalchemy import text  # noqa: E402

from database import SessionLocal  # noqa: E402

#: Cac ma duoc coi la du lieu cu can don. Khop theo TIEN TO hoac theo mot manh
#: RIENG BIET, khong khop lung chung: `LIKE '%TEST%'` se bat ca ten khach hang
#: thuc co chu "test" trong do.
#:
#: `DEMO-%` CO Y khong nam day: do la bo du lieu mau, `seed_demo` dung lai no.
MAU_RAC = (
    "E2E-%",
    "%-PROBE-%",
    "CUS-PROBE-%",
    "%-STRESS-%",
    "LIVE-%",
    # Bao gia sot lai tu bo nap cu `seed_full_demo.py`. Ghi day du, khong dung
    # `QT-%`: mot ngay nao do ma bao gia that co the mang dung tien to do.
    "QT-2026-001",
)

#: Thu tu xoa, TU CON LEN CHA. Doi thu tu la vo khoa ngoai.
#:
#: Moi dong: (bang, cot khoa, bang cha de doi chieu). `None` o cot cha nghia la
#: doi chieu truc tiep vao `id` cua chinh bang do.
THU_TU = [
    # Tang chung tu ke toan, sau cung ve khoa nhung dau tien ve thu tu xoa.
    ("journal_lines", "batch_id", "journal_batches"),
    ("journal_batches", "invoice_id", "ar_invoices"),
    ("gl_transactions", "invoice_id", "ar_invoices"),
    ("epl_expense_vouchers", "cost_id", "freight_actual_costs"),
    ("freight_charge_items", "cost_id", "freight_actual_costs"),
    ("freight_actual_costs", "trip_id", "transport_trips"),
    ("transport_event_documents", "event_id", "transport_events"),
    ("transport_events", "freight_order_id", "freight_orders"),
    ("delivery_pod_documents", "pod_record_id", "delivery_pod_records"),
    ("delivery_pod_records", "do_id", "delivery_orders"),
    ("delivery_order_charge_adjustments", "closeout_id", "delivery_order_closeouts"),
    ("delivery_order_closeouts", "do_id", "delivery_orders"),
    # Packing List phai di TRUOC `delivery_orders`: `parking_lists.do_id` tro
    # vao chinh bang do.
    ("parking_events", "parking_list_id", "parking_lists"),
    ("parking_labels", "parking_list_id", "parking_lists"),
    ("parking_list_items", "parking_list_id", "parking_lists"),
    ("parking_lists", "do_id", "delivery_orders"),
    ("vehicle_tracking", "do_id", "delivery_orders"),
    ("shipment_costs", "do_id", "delivery_orders"),
    ("freight_order_legacy_links", "delivery_order_id", "delivery_orders"),
    ("ar_invoices", "do_id", "delivery_orders"),
    ("resource_assignments", "trip_id", "transport_trips"),
    ("transport_trip_legs", "trip_id", "transport_trips"),
    ("trip_delivery_orders", "trip_id", "transport_trips"),
    ("transport_trips", "id", None),
    ("delivery_orders", "id", None),
    ("freight_orders", "id", None),
    ("delivery_order_details", "so_id", "sales_orders"),
    ("sales_orders", "id", None),
    ("quotations", "id", None),
    ("routes", "id", None),
    ("customers", "id", None),
]


def _dieu_kien(cot, bang_cha):
    """Cau WHERE khop cac ma rac, truc tiep hoac qua bang cha."""
    # `CAST(... AS TEXT)` o CA hai cho: cot doi chieu VA cot trong cau con. Mot
    # vai bang dung khoa so nguyen, va PostgreSQL tu choi `LIKE` tren so nguyen
    # bang loi "operator does not exist: integer ~".
    khop = " OR ".join("CAST(x.%s AS TEXT) LIKE :m%d" % ("id" if bang_cha else cot, i)
                       for i in range(len(MAU_RAC)))
    if bang_cha is None:
        return "(%s)" % khop.replace("x.", "")
    # Ep sang chu truoc khi so: mot vai bang con dung khoa SO NGUYEN
    # (`delivery_pod_documents.pod_record_id`), va PostgreSQL tu choi `LIKE`
    # tren so nguyen bang loi "operator does not exist: integer ~". Ep o day de
    # cau lenh chay duoc bat ke bang cha dung kieu khoa nao.
    return "CAST(%s AS TEXT) IN (SELECT CAST(x.id AS TEXT) FROM %s x WHERE %s)" % (
        cot, bang_cha, khop)


def _tham_so():
    return {"m%d" % i: mau for i, mau in enumerate(MAU_RAC)}


def main():
    that = "--that" in sys.argv
    db = SessionLocal()
    tong = 0
    try:
        for bang, cot, cha in THU_TU:
            dk = _dieu_kien(cot, cha)
            try:
                so = db.execute(
                    text("SELECT COUNT(*) FROM %s WHERE %s" % (bang, dk)), _tham_so()
                ).scalar() or 0
            except Exception as loi:
                # Bang co the khong ton tai o ban nay. Bao ra roi di tiep, chu
                # khong dung ca don dep vi mot bang thieu.
                db.rollback()
                print("  bo qua %-38s (%s)" % (bang, str(loi).split("\n")[0][:70]))
                continue
            if not so:
                continue
            tong += so
            print("  %-38s %4d dong" % (bang, so))
            if that:
                db.execute(text("DELETE FROM %s WHERE %s" % (bang, dk)), _tham_so())
        if that:
            db.commit()
            print("\nDa xoa %d dong rac thu nghiem." % tong)
        else:
            print("\nSe xoa %d dong. Chay lai voi --that de xoa thuc su." % tong)
    finally:
        db.close()


if __name__ == "__main__":
    main()
