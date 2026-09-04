"""Xoa bo du lieu demo `demo_26_8*` khoi co so du lieu.

VI SAO XOA: cong thuc gia thanh cua loai xe "Container 20FT - demo_26_8_p3" co
don gia xang dau 550.000 d/km va cuoc phi 3.600.000 d/kg. Hai con so do sai vai
tram lan, nen the loai xe hien ra 54 ti dong cho mot chuyen mau. Chu du an da
xac nhan day la du lieu nhap sai va cho xoa ca bo demo nay.

Bo demo khong khep kin theo TEN. Vi du hoa don cua no mang ma
`INV-20260826-...` chu khong chua "demo_26_8", va `journal_batches` /
`journal_lines` sinh ra tu hoa don do cung vay. Nen xoa theo ten don thuan se
dung lai o giua: mot bang khong xoa duoc la ca chuoi khoa ngoai dung lai.

CACH LAM: xoa theo THU TU TUONG MINH, tu con len cha, theo do thi khoa ngoai
thuc te da tra trong co so du lieu. Viet ra tung buoc thay vi de may tu do:
thu tu nay la thong tin can kiem duoc bang mat, va mot vong lap tu do se lang
le bo qua nhung dong no khong xoa noi.

AN TOAN:
  · Sao luu moi dong NGAY TRUOC khi xoa no, roi ghi tep truoc khi chot giao
    dich. Dong bi xoa theo khoa ngoai khong khop ten, nen mot luot sao luu
    theo ten se bo sot chung.
  · Ca viec nam trong MOT giao dich. Con mot dong khong xoa duoc thi lat lai
    toan bo — khong chap nhan de co so du lieu nua voi.

Cach dung:
    python scripts/xoa_du_lieu_demo_26_8.py --xem-truoc
    python scripts/xoa_du_lieu_demo_26_8.py --xoa
"""
import argparse
import datetime
import io
import json
import os
import sys

from sqlalchemy import create_engine, text

MAU = "%demo_26_8%"

#: Dong demo trong bang `delivery_orders`, `sales_orders`, ... nhan ra bang ma.
#: Con hoa don thi nhan ra qua `do_id`, vi ma hoa don khong chua "demo_26_8".
DEMO_DO = "SELECT id FROM delivery_orders WHERE CAST(id AS text) LIKE :mau"
DEMO_SO = "SELECT id FROM sales_orders WHERE CAST(id AS text) LIKE :mau"
DEMO_QT = "SELECT id FROM quotations WHERE CAST(id AS text) LIKE :mau"
DEMO_INV = ("SELECT id FROM ar_invoices WHERE CAST(do_id AS text) LIKE :mau"
            " OR CAST(id AS text) LIKE :mau")
DEMO_BATCH = "SELECT id FROM journal_batches WHERE invoice_id IN (%s)" % DEMO_INV
DEMO_FO = "SELECT id FROM freight_orders WHERE CAST(id AS text) LIKE :mau"
DEMO_TRIP = "SELECT id FROM transport_trips WHERE CAST(id AS text) LIKE :mau"
#: Xe va tai xe cua bo demo. Nhieu ban ghi noi VE chung (giam sat hanh trinh,
#: POD, phan cong) lai mang ma khong chua "demo_26_8", nen phai tim theo day.
DEMO_VEH = "SELECT id FROM vehicles WHERE CAST(id AS text) LIKE :mau"
DEMO_DRV = "SELECT id FROM drivers WHERE CAST(id AS text) LIKE :mau"

#: Cac buoc xoa, TU CON LEN CHA. Moi buoc: (bang, dieu kien).
#:
#: Thu tu nay lay tu do thi khoa ngoai thuc te:
#:   journal_lines -> journal_batches -> ar_invoices -> delivery_orders
#:   delivery_orders -> sales_orders -> quotations -> routes
#:   delivery_orders -> vehicles / drivers -> vehicle_types
BUOC = [
    # -- So sach ke toan sinh ra tu hoa don cua bo demo ---------------------
    ("journal_lines", '"batch_id" IN (%s)' % DEMO_BATCH),
    ("journal_batches", '"invoice_id" IN (%s)' % DEMO_INV),
    ("gl_transactions", '"invoice_id" IN (%s)' % DEMO_INV),
    ("ar_invoices", 'CAST("do_id" AS text) LIKE :mau OR CAST("id" AS text) LIKE :mau'),

    # -- Moi thu treo vao lenh giao hang ------------------------------------
    ("shipment_costs", '"do_id" IN (%s)' % DEMO_DO),
    ("vehicle_tracking",
     '"do_id" IN (%s) OR "vehicle_id" IN (%s)' % (DEMO_DO, DEMO_VEH)),
    ("pod", '"do_id" IN (%s)' % DEMO_DO),
    ("freight_order_legacy_links", '"delivery_order_id" IN (%s)' % DEMO_DO),
    ("delivery_pod_documents",
     '"pod_record_id" IN (SELECT id FROM delivery_pod_records'
     ' WHERE do_id IN (%s) OR vehicle_id IN (%s) OR driver_id IN (%s))'
     % (DEMO_DO, DEMO_VEH, DEMO_DRV)),
    ("delivery_pod_records",
     '"do_id" IN (%s) OR "vehicle_id" IN (%s) OR "driver_id" IN (%s)'
     % (DEMO_DO, DEMO_VEH, DEMO_DRV)),
    # Rang buoc (trip_id, do_id) tro vao `trip_delivery_orders`, nen chan
    # phai xoa truoc.
    ("transport_trip_legs", '"trip_id" IN (%s)' % DEMO_TRIP),
    ("trip_delivery_orders", '"do_id" IN (%s)' % DEMO_DO),
    ("delivery_order_closeouts", '"do_id" IN (%s)' % DEMO_DO),
    ("epl_expense_vouchers", '"do_id" IN (%s)' % DEMO_DO),
    ("parking_events",
     '"parking_list_id" IN (SELECT id FROM parking_lists WHERE do_id IN (%s) OR so_id IN (%s))'
     % (DEMO_DO, DEMO_SO)),
    ("parking_lists", '"do_id" IN (%s) OR "so_id" IN (%s)' % (DEMO_DO, DEMO_SO)),

    # -- Chuyen van chuyen va chi phi cuoc ---------------------------------
    #
    # Thu tu o day lay tu cot khoa THUC TE da tra trong co so du lieu, khong
    # phai doan theo ten: `freight_charge_items` noi qua `cost_id` (khong phai
    # `freight_order_id`), va `resource_assignments` khong co cot `do_id`.
    ("freight_charge_items",
     '"cost_id" IN (SELECT id FROM freight_actual_costs WHERE freight_order_id IN (%s))'
     % DEMO_FO),
    ("resource_assignments",
     '"trip_id" IN (%s) OR "freight_order_id" IN (%s)'
     ' OR "vehicle_id" IN (%s) OR "driver_id" IN (%s) OR "co_driver_id" IN (%s)'
     % (DEMO_TRIP, DEMO_FO, DEMO_VEH, DEMO_DRV, DEMO_DRV)),
    ("driver_shift_assignments",
     '"trip_id" IN (%s) OR "vehicle_id" IN (%s) OR "driver_id" IN (%s)'
     % (DEMO_TRIP, DEMO_VEH, DEMO_DRV)),
    # `freight_actual_costs` tro vao ca `freight_orders` lan `transport_trips`,
    # nen phai xoa truoc ca hai bang do.
    ("freight_actual_costs",
     '"freight_order_id" IN (%s) OR "trip_id" IN (%s)' % (DEMO_FO, DEMO_TRIP)),
    ("transport_trips",
     'CAST("id" AS text) LIKE :mau OR "freight_order_id" IN (%s)'
     ' OR "vehicle_id" IN (%s) OR "driver_id" IN (%s) OR "co_driver_id" IN (%s)'
     % (DEMO_FO, DEMO_VEH, DEMO_DRV, DEMO_DRV)),
    ("freight_orders", 'CAST("id" AS text) LIKE :mau'),
    ("delivery_orders", 'CAST("id" AS text) LIKE :mau'),

    # -- Chuoi bao gia -> don hang -----------------------------------------
    ("sales_orders", 'CAST("id" AS text) LIKE :mau'),
    ("quotations", 'CAST("id" AS text) LIKE :mau'),

    # -- Go tham chieu TU du lieu THAT vao danh muc demo (khong xoa dong) --
    #
    # Vi du: mot DO thu nghiem tai (E2E-STRESS-...) dang muon xe/tai xe demo,
    # va mot bao gia that (QT-2026-001) dang muon tuyen demo. Day KHONG phai
    # rac demo — xoa ca dong la mat du lieu that. Chi go tham chieu ve NULL.
    # -- Danh muc goc ------------------------------------------------------
    ("driver_qualifications",
     '"driver_id" IN (SELECT id FROM drivers WHERE CAST(id AS text) LIKE :mau)'),
    ("driver_shift_assignments",
     '"driver_id" IN (SELECT id FROM drivers WHERE CAST(id AS text) LIKE :mau)'),
    ("drivers", 'CAST("id" AS text) LIKE :mau'),
    ("vehicles", 'CAST("id" AS text) LIKE :mau'),
    ("routes", 'CAST("id" AS text) LIKE :mau'),
    ("cost_formulas", 'CAST("id" AS text) LIKE :mau'),
    ("vehicle_types", 'CAST("id" AS text) LIKE :mau'),

    # -- Vet: nhat ky va ban ghi phu tro -----------------------------------
    ("locations", 'CAST("id" AS text) LIKE :mau OR "name" LIKE :mau'),
    ("idempotency_records",
     '"idempotency_key" LIKE :mau OR "response_json" LIKE :mau OR "path" LIKE :mau'),
    ("audit_logs", 'CAST("record_id" AS text) LIKE :mau'),
]


def doc_url():
    duong_dan = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    for dong in io.open(duong_dan, encoding="utf-8"):
        if dong.startswith("DATABASE_URL="):
            return dong.split("=", 1)[1].strip()
    raise SystemExit("Khong tim thay DATABASE_URL trong .env")


def bang_co_that(ket_noi):
    return {
        hang[0]
        for hang in ket_noi.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
    }


def xem_truoc(ket_noi):
    co = bang_co_that(ket_noi)
    tong = 0
    for bang, dieu_kien in BUOC:
        if bang not in co:
            print("  %-30s (khong co bang nay)" % bang)
            continue
        so = list(ket_noi.execute(
            text('SELECT count(*) FROM "%s" WHERE %s' % (bang, dieu_kien)),
            {"mau": MAU},
        ))[0][0]
        if so:
            print("  %-30s %d" % (bang, so))
            tong += so
    print("  TONG: %d dong" % tong)
    return tong


#: Cap nhat GO THAM CHIEU, chay TRUOC danh sach BUOC xoa. Moi phan tu:
#: (bang, cot, dieu_kien_tim_dong_can_sua).
#:
#: Khac voi BUOC (xoa han dong), day chi dat MOT cot ve NULL — dong van con,
#: chi la khong con tro vao danh muc demo sap bi xoa nua.
GO_THAM_CHIEU = [
    ("delivery_orders", "driver_id",
     'CAST("driver_id" AS text) LIKE :mau AND CAST("id" AS text) NOT LIKE :mau'),
    ("delivery_orders", "vehicle_id",
     'CAST("vehicle_id" AS text) LIKE :mau AND CAST("id" AS text) NOT LIKE :mau'),
    ("delivery_orders", "route_id",
     'CAST("route_id" AS text) LIKE :mau AND CAST("id" AS text) NOT LIKE :mau'),
    ("quotations", "route_id",
     'CAST("route_id" AS text) LIKE :mau AND CAST("id" AS text) NOT LIKE :mau'),
    ("sales_orders", "route_id",
     'CAST("route_id" AS text) LIKE :mau AND CAST("id" AS text) NOT LIKE :mau'),
    ("vehicles", "type",
     'CAST("type" AS text) LIKE :mau AND CAST("id" AS text) NOT LIKE :mau'),
]


def go_tham_chieu(ket_noi, ban_sao):
    """Dat ve NULL cac tham chieu tu du lieu THAT vao danh muc demo.

    Sao luu GIA TRI CU truoc khi ghi de, duoi khoa rieng
    "<bang>.<cot> (go tham chieu)", de phan biet voi cac dong bi XOA han.
    """
    co = bang_co_that(ket_noi)
    da_sua = {}
    for bang, cot, dieu_kien in GO_THAM_CHIEU:
        if bang not in co:
            continue
        dong = list(ket_noi.execute(
            text('SELECT * FROM "%s" WHERE %s' % (bang, dieu_kien)), {"mau": MAU}
        ))
        if not dong:
            continue
        khoa = "%s.%s (go tham chieu)" % (bang, cot)
        ban_sao.setdefault(khoa, []).extend(dict(hang._mapping) for hang in dong)
        ket_qua = ket_noi.execute(
            text('UPDATE "%s" SET "%s" = NULL WHERE %s' % (bang, cot, dieu_kien)),
            {"mau": MAU},
        )
        da_sua[khoa] = ket_qua.rowcount
    return da_sua


def xoa(ket_noi, ban_sao):
    co = bang_co_that(ket_noi)
    da_xoa = {}
    for bang, dieu_kien in BUOC:
        if bang not in co:
            continue
        dong = list(ket_noi.execute(
            text('SELECT * FROM "%s" WHERE %s' % (bang, dieu_kien)), {"mau": MAU}
        ))
        if not dong:
            continue
        ban_sao.setdefault(bang, []).extend(dict(hang._mapping) for hang in dong)
        ket_qua = ket_noi.execute(
            text('DELETE FROM "%s" WHERE %s' % (bang, dieu_kien)), {"mau": MAU}
        )
        da_xoa[bang] = ket_qua.rowcount
    return da_xoa


def con_sot(ket_noi):
    """Con dong nao chua "demo_26_8" khong, tren toan bo co so du lieu."""
    sot = {}
    bangs = sorted(bang_co_that(ket_noi))
    for bang in bangs:
        cot = [
            hang[0]
            for hang in ket_noi.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                  AND data_type IN ('character varying', 'text')
            """), {"t": bang})
        ]
        if not cot:
            continue
        dieu_kien = " OR ".join('"%s" LIKE :mau' % ten for ten in cot)
        try:
            so = list(ket_noi.execute(
                text('SELECT count(*) FROM "%s" WHERE %s' % (bang, dieu_kien)),
                {"mau": MAU},
            ))[0][0]
        except Exception:
            continue
        if so:
            sot[bang] = so
    return sot


def main():
    bo_doc = argparse.ArgumentParser()
    bo_doc.add_argument("--xem-truoc", action="store_true")
    bo_doc.add_argument("--xoa", action="store_true")
    doi_so = bo_doc.parse_args()
    if not (doi_so.xem_truoc or doi_so.xoa):
        bo_doc.error("Chon --xem-truoc hoac --xoa")

    engine = create_engine(doc_url())

    if doi_so.xem_truoc:
        with engine.connect() as ket_noi:
            print("Se xoa:")
            xem_truoc(ket_noi)
            print("Con sot theo ten (sau khi xoa se kiem lai):")
            for bang, so in sorted(con_sot(ket_noi).items()):
                print("  %-30s %d" % (bang, so))
        return

    dau_thoi_gian = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tep_sao_luu = os.path.join(
        os.path.dirname(__file__), "sao_luu_demo_26_8_%s.json" % dau_thoi_gian
    )

    ban_sao = {}
    with engine.begin() as ket_noi:
        da_sua = go_tham_chieu(ket_noi, ban_sao)
        if da_sua:
            print("Da go tham chieu (dong van con, chi mat lien ket toi du lieu demo):")
            for khoa, so in da_sua.items():
                print("  %-40s %d" % (khoa, so))
        da_xoa = xoa(ket_noi, ban_sao)
        # Ghi tep TRUOC khi chot giao dich: chot xong moi ghi thi loi ghi tep
        # se lam mat duong ve.
        io.open(tep_sao_luu, "w", encoding="utf-8").write(
            json.dumps(ban_sao, ensure_ascii=False, indent=2, default=str)
        )
        print("Da sao luu %d dong ra %s"
              % (sum(len(v) for v in ban_sao.values()), tep_sao_luu))
        print("Da xoa:")
        for bang, so in da_xoa.items():
            print("  %-30s %d" % (bang, so))
        print("  TONG: %d dong" % sum(da_xoa.values()))

    with engine.connect() as ket_noi:
        sot = con_sot(ket_noi)
    if sot:
        print("Con sot lai (can xem tay):")
        for bang, so in sorted(sot.items()):
            print("  %-30s %d" % (bang, so))
    else:
        print("Khong con dong nao chua 'demo_26_8'.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
