import os
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_DIR / "backend" / "app"
sys.path.insert(0, str(APP_DIR))

os.environ.setdefault("EPL_ENV_FILE", str(PROJECT_DIR / ".env"))

from database import SessionLocal, auto_migrate_db  # noqa: E402
from services.demo_seed_service import seed_demo  # noqa: E402


def main():
    auto_migrate_db()
    with SessionLocal() as db:
        scenarios = seed_demo(db, reset=True, verify=True)

    # NOI RA co so du lieu THAT vua ghi vao, khong ghi cung "PostgreSQL".
    #
    # Khi may chua PostgreSQL khong toi duoc, du an chay tam bang SQLite qua
    # `EPL_ENV_FILE=.env.sqlite`. Luc do dong thong bao cung se noi la da nap
    # vao PostgreSQL — va nguoi doc tin rang du lieu da nam tren co so du lieu
    # that. Mot cau bao sai o dung buoc xac nhan la cho de sai nhat.
    from database import engine as _engine
    duong = str(_engine.url)
    if "@" in duong:  # che thong tin dang nhap neu la PostgreSQL
        duong = duong.split("://")[0] + "://***@" + duong.rsplit("@", 1)[1]
    print("Demo workflow seeded to:", duong)
    for name, values in scenarios.items():
        print(
            f"{name}: DO={values['delivery_order_id']} "
            f"Trip={values.get('trip_id', 'not-created')}"
        )


if __name__ == "__main__":
    main()
