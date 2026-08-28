import os
from pathlib import Path

from sqlalchemy import create_engine, text


ENV_FILE = Path(os.environ.get("EPL_ENV_FILE") or r"D:\Demo_Lao\.env")
PREFIX = "E2E-STRESS-%"


def load_database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("Không tìm thấy DATABASE_URL.")


def main():
    apply = "--apply" in {arg.lower() for arg in os.sys.argv[1:]}
    engine = create_engine(load_database_url(), pool_pre_ping=True)
    ordered_tables = [
        ("gl_transactions", "invoice_id"),
        ("ar_invoices", "id"),
        ("pod", "do_id"),
        ("vehicle_tracking", "do_id"),
        ("delivery_orders", "id"),
        ("sales_orders", "id"),
        ("quotations", "id"),
        ("routes", "id"),
        ("customers", "id"),
    ]

    with engine.begin() as conn:
        print("=== E2E-STRESS CLEANUP ===")
        total = 0
        counts = {}
        for table, column in ordered_tables:
            exists = conn.execute(text("select to_regclass(:name)"), {"name": table}).scalar()
            if not exists:
                continue
            count = conn.execute(
                text(f'SELECT count(*) FROM "{table}" WHERE "{column}" LIKE :prefix'),
                {"prefix": PREFIX},
            ).scalar()
            counts[table] = count
            total += count
            print(f"{table}: {count}")

        if not apply:
            print(f"DRY-RUN: sẽ xóa {total} dòng nếu chạy thêm --apply.")
            return

        for table, column in ordered_tables:
            if counts.get(table, 0) <= 0:
                continue
            conn.execute(
                text(f'DELETE FROM "{table}" WHERE "{column}" LIKE :prefix'),
                {"prefix": PREFIX},
            )
        print(f"APPLIED: đã xóa {total} dòng E2E-STRESS.")


if __name__ == "__main__":
    main()
