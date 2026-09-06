"""Ap cac migration con thieu len co so du lieu that (Postgres).

Chay khong tham so:

    python scripts/ap_migration.py

Script tu doc `DATABASE_URL` trong `.env` o goc du an, kiem may chu co toi
duoc khong TRUOC khi goi SQLAlchemy — vi khi may chu tat, `create_engine` chi
treo den luc timeout roi nem mot loi socket dai dong, khong noi ro la loi
mang hay loi luoc do.

Them `--kiem-thu` de chi XEM danh sach ban con thieu, khong ghi gi ca.
"""
import argparse
import io
import os
import socket
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "app"))

from migrations.runner import MIGRATIONS, upgrade  # noqa: E402


def doc_database_url():
    duong_dan = os.path.join(os.path.dirname(GOC), ".env")
    if not os.path.exists(duong_dan):
        raise SystemExit("Khong thay tep .env o %s" % duong_dan)
    for dong in io.open(duong_dan, encoding="utf-8"):
        dong = dong.strip()
        if dong.startswith("DATABASE_URL="):
            return dong.split("=", 1)[1].split("#")[0].strip()
    raise SystemExit("Trong .env khong co DATABASE_URL")


def tach_host_cong(url):
    """Lay host va cong de thu ket noi, khong keo them thu vien nao."""
    if "@" not in url or "/" not in url.split("@", 1)[1]:
        return None, None
    dia_chi = url.split("@", 1)[1].split("/", 1)[0]
    if ":" not in dia_chi:
        return dia_chi, 5432
    host, cong = dia_chi.rsplit(":", 1)
    return host, int(cong)


def kiem_toi_duoc(host, cong, giay=8):
    s = socket.socket()
    s.settimeout(giay)
    try:
        s.connect((host, cong))
        return True, None
    except Exception as loi:
        return False, loi
    finally:
        s.close()


def main():
    bo = argparse.ArgumentParser()
    bo.add_argument("--kiem-thu", action="store_true",
                    help="Chi xem con thieu ban nao, khong ghi gi")
    bo.add_argument("--database-url",
                    help="Dung URL nay thay vi doc .env (de thu tren SQLite)")
    tham_so = bo.parse_args()

    url = tham_so.database_url or doc_database_url()
    host, cong = tach_host_cong(url)
    if host:
        toi_duoc, loi = kiem_toi_duoc(host, cong)
        if not toi_duoc:
            raise SystemExit(
                "Khong ket noi duoc toi %s:%s — %s\n"
                "May chu co so du lieu dang tat hoac khong cung mang. "
                "Khong phai loi luoc do." % (host, cong, loi)
            )
        print("Ket noi duoc %s:%s" % (host, cong))

    if tham_so.kiem_thu:
        from sqlalchemy import create_engine, text
        may = create_engine(url)
        with may.connect() as ket_noi:
            ket_noi.execute(text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY,"
                " applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            ))
            ket_noi.commit()
            da_ap = {r[0] for r in ket_noi.execute(text("SELECT version FROM schema_migrations"))}
        thieu = [m.VERSION for m in MIGRATIONS if m.VERSION not in da_ap]
        print("Da ap: %d ban. Con thieu: %d ban." % (len(da_ap), len(thieu)))
        for v in thieu:
            print("  -", v)
        return

    xong = upgrade(url)
    if not xong:
        print("Co so du lieu da o moc moi nhat, khong co gi de ap.")
    else:
        print("Da ap %d ban:" % len(xong))
        for v in xong:
            print("  -", v)


if __name__ == "__main__":
    main()
