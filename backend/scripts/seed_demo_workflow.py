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

    print("Demo workflow seeded to PostgreSQL.")
    for name, values in scenarios.items():
        print(
            f"{name}: DO={values['delivery_order_id']} "
            f"Trip={values.get('trip_id', 'not-created')}"
        )


if __name__ == "__main__":
    main()
