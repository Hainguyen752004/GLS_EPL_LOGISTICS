"""Don ba dong con sot sau khi xoa bo du lieu demo `demo_26_8*`.

Ba dong nay la du lieu THAT, khong phai rac demo — nen khong xoa. Van de la
chung dang tro vao thu vua bi xoa:

  1. `drivers.DEMO-DRV-002.status`  = "Dang thuc hien demo_26_8-TRIP"
  2. `vehicles.DEMO-61H-112.34.status` = "Dang thuc hien demo_26_8-TRIP"

     Hai dong nay la mot LOI THAT vua lo ra: trang thai xe va tai xe duoc luu
     bang chuoi tu do co nhac ten mot chuyen cu the. Chuyen bi xoa thi trang
     thai noi doi — no bao "dang thuc hien" mot chuyen khong con ton tai, va
     xe/tai xe se hien la dang ban mai mai, khong bao gio duoc dieu di nua.

     Tra ve dung gia tri luc gieo du lieu (xem demo_seed_service.py).

  3. `delivery_orders.E2E-STRESS-...-DO.co_driver` = "demo_26_8_p3-DRV-02"

     O phu xe la chuoi tu do (khong phai khoa ngoai) nen no khong bi rang
     buoc nao chan, va giu lai thi no chi ten mot tai xe khong con ton tai.

Cach dung:
    python scripts/don_vet_demo_26_8.py --xem-truoc
    python scripts/don_vet_demo_26_8.py --don
"""
import argparse
import io
import os
import sys

from sqlalchemy import create_engine, text

#: (bang, cot, gia tri moi, dieu kien). Gia tri moi lay tu demo_seed_service.py
#: — dung gia tri luc gieo du lieu, khong tu dat ra mot chuoi moi.
SUA = [
    ("drivers", "status", "Rảnh - sẵn sàng",
     "id = 'DEMO-DRV-002' AND status LIKE '%demo_26_8%'"),
    ("vehicles", "status", "Sẵn sàng",
     "id = 'DEMO-61H-112.34' AND status LIKE '%demo_26_8%'"),
    ("delivery_orders", "co_driver", None,
     "co_driver LIKE '%demo_26_8%'"),
]


def doc_url():
    duong_dan = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    for dong in io.open(duong_dan, encoding="utf-8"):
        if dong.startswith("DATABASE_URL="):
            return dong.split("=", 1)[1].strip()
    raise SystemExit("Khong tim thay DATABASE_URL trong .env")


def main():
    bo_doc = argparse.ArgumentParser()
    bo_doc.add_argument("--xem-truoc", action="store_true")
    bo_doc.add_argument("--don", action="store_true")
    doi_so = bo_doc.parse_args()
    if not (doi_so.xem_truoc or doi_so.don):
        bo_doc.error("Chon --xem-truoc hoac --don")

    engine = create_engine(doc_url())

    with engine.connect() as ket_noi:
        for bang, cot, gia_tri_moi, dieu_kien in SUA:
            for hang in ket_noi.execute(text(
                'SELECT id, "%s" FROM "%s" WHERE %s' % (cot, bang, dieu_kien)
            )):
                print("  %s.%s  id=%s" % (bang, cot, hang[0]))
                print("      cu : %r" % hang[1])
                print("      moi: %r" % gia_tri_moi)

    if doi_so.xem_truoc:
        return

    with engine.begin() as ket_noi:
        for bang, cot, gia_tri_moi, dieu_kien in SUA:
            ket_qua = ket_noi.execute(
                text('UPDATE "%s" SET "%s" = :gia_tri WHERE %s' % (bang, cot, dieu_kien)),
                {"gia_tri": gia_tri_moi},
            )
            if ket_qua.rowcount:
                print("Da sua %s.%s: %d dong" % (bang, cot, ket_qua.rowcount))

    # Kiem lai tren toan bo co so du lieu: khong con dong nao nhac "demo_26_8".
    with engine.connect() as ket_noi:
        con = []
        bangs = [
            hang[0]
            for hang in ket_noi.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            """))
        ]
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
                    {"mau": "%demo_26_8%"},
                ))[0][0]
            except Exception:
                continue
            if so:
                con.append((bang, so))
        if con:
            print("Con sot:", con)
        else:
            print("Khong con dong nao nhac 'demo_26_8' trong co so du lieu.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
