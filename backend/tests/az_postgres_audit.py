import json
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = Path(os.environ.get("EPL_ENV_FILE") or r"D:\Demo_Lao\.env")
BAD_TOKENS = ["Ã", "Ä", "áº", "á»", "âœ", "âš", "ðŸ", "VNÄ", "Kh?", "B?", "?ang"]


def load_database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("Không tìm thấy DATABASE_URL. Hãy set EPL_ENV_FILE hoặc DATABASE_URL.")


def fail(message):
    raise AssertionError(message)


def main():
    engine = create_engine(load_database_url(), pool_pre_ping=True)
    with engine.connect() as conn:
        insp = inspect(engine)
        tables = set(insp.get_table_names())

        required_tables = [
            "customers",
            "routes",
            "vehicles",
            "drivers",
            "quotations",
            "sales_orders",
            "delivery_orders",
        ]
        missing_tables = [table for table in required_tables if table not in tables]
        if missing_tables:
            fail(f"Thiếu bảng bắt buộc: {missing_tables}")

        print("=== 1. MASTER DATA COUNTS ===")
        counts = {}
        for table in [
            "customers",
            "routes",
            "vehicles",
            "drivers",
            "quotations",
            "sales_orders",
            "delivery_orders",
            "vehicle_tracking",
            "pod",
            "ar_invoices",
            "gl_transactions",
        ]:
            if table in tables:
                counts[table] = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
                print(f"{table}: {counts[table]}")

        for table in ["customers", "routes", "vehicles", "drivers"]:
            if counts.get(table, 0) <= 0:
                fail(f"Master Data thiếu dữ liệu: {table}=0")

        print("=== 2. VIETNAMESE / MOJIBAKE CHECK ===")
        bad_rows = []
        for table in sorted(tables):
            cols = [
                col["name"]
                for col in insp.get_columns(table)
                if any(kind in str(col["type"]).lower() for kind in ["char", "text", "varchar", "string"])
            ]
            if not cols:
                continue
            quoted_cols = ", ".join(f'"{col}"' for col in cols)
            rows = conn.execute(text(f'SELECT {quoted_cols} FROM "{table}" LIMIT 1000')).mappings().all()
            for row in rows:
                joined = " | ".join(str(row.get(col) or "") for col in cols)
                if any(token in joined for token in BAD_TOKENS):
                    bad_rows.append(f"{table}: {joined[:240]}")
        print(f"bad_rows: {len(bad_rows)}")
        for sample in bad_rows[:10]:
            print("  ", sample)
        if bad_rows:
            fail("DB còn dữ liệu lỗi tiếng Việt/mojibake.")

        print("=== 3. ROUTE SEGMENT DISTANCE CHECK ===")
        bad_routes = []
        routes = conn.execute(text('SELECT id, distance_km, segments_json FROM routes LIMIT 1000')).mappings().all()
        for route in routes:
            raw = route["segments_json"] or "[]"
            try:
                segments = json.loads(raw)
            except Exception:
                bad_routes.append((route["id"], "segments_json không phải JSON hợp lệ"))
                continue
            if not isinstance(segments, list) or not segments:
                continue
            segment_total = 0.0
            missing_distance = 0
            for segment in segments:
                if not isinstance(segment, dict):
                    continue
                km = float(segment.get("distance_km") or segment.get("dist_km") or segment.get("distance") or segment.get("km") or 0)
                if km <= 0:
                    missing_distance += 1
                segment_total += km
            route_total = float(route["distance_km"] or 0)
            if missing_distance or (segment_total and abs(route_total - segment_total) > 0.2):
                bad_routes.append((route["id"], f"route_total={route_total}, segment_total={segment_total}, missing={missing_distance}"))
        print(f"bad_routes: {len(bad_routes)}")
        for sample in bad_routes[:10]:
            print("  ", sample)
        if bad_routes:
            fail("Có tuyến đường bị lệch tổng km/chặng.")

        print("=== 4. STRESS DATA WARNING ===")
        stress_counts = {}
        for table in ["customers", "routes", "quotations", "sales_orders", "delivery_orders"]:
            if table in tables:
                id_col = "id"
                stress_counts[table] = conn.execute(
                    text(f'SELECT count(*) FROM "{table}" WHERE "{id_col}" LIKE :prefix'),
                    {"prefix": "E2E-STRESS-%"},
                ).scalar()
                print(f"{table}: {stress_counts[table]}")
        total_stress = sum(stress_counts.values())
        if total_stress:
            print(f"WARNING: Có {total_stress} dòng E2E-STRESS trong DB. Nên dọn trước demo nếu thấy danh sách bị loãng.")

        print("=== 5. A-Z POSTGRES AUDIT RESULT ===")
        print("PASS")


if __name__ == "__main__":
    main()
