"""Sua `routes.distance_km` cho khop tong quang duong cac chang.

VI SAO CAN SUA
--------------
`create_trip_from_delivery_orders` tu choi lap Trip khi `routes.distance_km`
lech voi tong cac chang trong `segments_json` qua 0,05 km
(`ROUTE_DISTANCE_MISMATCH`). Trong co so du lieu that co hai tuyen bi lech —
ke ca tuyen demo chinh — nen KHONG DO NAO lap duoc Trip tren chung.

CON SO NAO DUNG
---------------
Tong cac chang. Ly do: `segments_json` la phan CHI TIET, con `distance_km`
chi la con so tong hop. Mot con so tong hop khong khop voi chi tiet cua no
thi con so tong hop la cai sai. Chinh giao dien Tuyen duong cung tinh tu
chang: man do ghi "Tong quang duong: 44,7 km" trong khi cot `distance_km`
ghi 44,0.

Doc `distance_km` theo DUNG thu tu khoa ma `_route_segments` cua backend dung
(`distance_km` -> `dist_km` -> `distance` -> `km`), de script nay va may chu
khong bao gio doc ra hai con so khac nhau tu cung mot ban ghi.

CACH DUNG
---------
    python scripts/sua_quang_duong_tuyen_lech.py --kiem-thu   # chi xem
    python scripts/sua_quang_duong_tuyen_lech.py              # sua that

Script LUON ghi ban sao gia tri cu ra tep JSON truoc khi commit, va in ra
cau lenh SQL de hoan lai.
"""
import argparse
import datetime as dt
import io
import json
import os
import socket
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "app"))

#: Lech duoi nguong nay thi coi la khop — dung dung con so cua backend.
NGUONG_KM = 0.05

#: Thu tu khoa PHAI khop `_route_segments` trong tms_trip_service.py.
KHOA_KM = ("distance_km", "dist_km", "distance", "km")


def doc_database_url():
    duong_dan = os.path.join(os.path.dirname(GOC), ".env")
    if not os.path.exists(duong_dan):
        raise SystemExit("Khong thay tep .env o %s" % duong_dan)
    for dong in io.open(duong_dan, encoding="utf-8"):
        dong = dong.strip()
        if dong.startswith("DATABASE_URL="):
            return dong.split("=", 1)[1].split("#")[0].strip()
    raise SystemExit("Trong .env khong co DATABASE_URL")


def kiem_toi_duoc(url):
    """Thu socket TRUOC khi goi SQLAlchemy.

    May chu tat thi `create_engine` treo den luc timeout roi nem mot loi
    socket dai dong, doc vao khong biet la loi mang hay loi luoc do.
    """
    if "@" not in url:
        return
    dia_chi = url.split("@", 1)[1].split("/", 1)[0]
    host, cong = (dia_chi.rsplit(":", 1) + ["5432"])[:2] if ":" in dia_chi else (dia_chi, "5432")
    s = socket.socket()
    s.settimeout(8)
    try:
        s.connect((host, int(cong)))
    except Exception as loi:
        raise SystemExit(
            "Khong ket noi duoc toi %s:%s — %s\n"
            "May chu co so du lieu dang tat hoac khong cung mang."
            % (host, cong, loi)
        )
    finally:
        s.close()
    print("Ket noi duoc %s:%s" % (host, cong))


def km_cua_chang(chang):
    for khoa in KHOA_KM:
        if khoa in chang:
            try:
                return float(chang[khoa])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def ra_soat(ket_noi, text):
    """Cac tuyen bi lech, kem ca chi tiet de in ra cho nguoi doc."""
    lech = []
    rows = ket_noi.execute(text(
        "SELECT id, name, distance_km, segments_json FROM routes ORDER BY id"
    )).fetchall()
    for ma, ten, khai_bao, segments_json in rows:
        try:
            chang = json.loads(segments_json or "[]")
        except (TypeError, ValueError):
            chang = []
        if not isinstance(chang, list) or not chang:
            # Chua co chang thi khong co gi de doi chieu — de nguyen.
            continue
        tong = sum(km_cua_chang(c) for c in chang if isinstance(c, dict))
        cu = float(khai_bao or 0)
        if abs(tong - cu) < NGUONG_KM:
            continue
        lech.append({
            "id": ma, "name": ten,
            "distance_km_cu": cu, "distance_km_moi": round(tong, 3),
            "so_chang": len(chang),
        })
    return len(rows), lech


def main():
    bo = argparse.ArgumentParser()
    bo.add_argument("--kiem-thu", action="store_true",
                    help="Chi xem tuyen nao lech, khong ghi gi")
    tham_so = bo.parse_args()

    url = doc_database_url()
    kiem_toi_duoc(url)

    from sqlalchemy import create_engine, text

    may = create_engine(url)
    with may.connect() as ket_noi:
        tong_tuyen, lech = ra_soat(ket_noi, text)
        print("Ra soat %d tuyen. Lech: %d." % (tong_tuyen, len(lech)))
        if not lech:
            print("Khong co gi phai sua.")
            return
        for t in lech:
            print("  %-42s %s km -> %s km  (%d chang)"
                  % (t["id"][:42], t["distance_km_cu"], t["distance_km_moi"], t["so_chang"]))

        if tham_so.kiem_thu:
            print()
            print("Che do kiem thu: KHONG ghi gi.")
            return

        # Ban sao TRUOC khi commit. Khong co ban sao thi khong co duong lui.
        dau_thoi_gian = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        tep_sao = os.path.join(
            GOC, "scripts", "sao_luu_quang_duong_tuyen-%s.json" % dau_thoi_gian)
        io.open(tep_sao, "w", encoding="utf-8").write(
            json.dumps(lech, ensure_ascii=False, indent=2))
        print()
        print("Da ghi ban sao:", tep_sao)

        for t in lech:
            ket_noi.execute(
                text("UPDATE routes SET distance_km = :km WHERE id = :ma"),
                {"km": t["distance_km_moi"], "ma": t["id"]},
            )
        ket_noi.commit()
        print("Da cap nhat %d tuyen." % len(lech))

        # Doc lai tu co so du lieu de xac nhan, khong tin vao so dong da ghi.
        _, con_lech = ra_soat(ket_noi, text)
        if con_lech:
            print("CANH BAO: van con lech:", [t["id"] for t in con_lech])
        else:
            print("Doc lai: moi tuyen da khop tong cac chang.")

        print()
        print("Muon hoan lai thi chay:")
        for t in lech:
            print("  UPDATE routes SET distance_km = %s WHERE id = '%s';"
                  % (t["distance_km_cu"], t["id"]))


if __name__ == "__main__":
    main()
