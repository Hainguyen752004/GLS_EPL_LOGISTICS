import argparse
import sqlite3
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from . import v001_workflow, v002_canonical_status_constraints, v003_tms_core_planning, v004_tms_tendering, v005_tms_dispatch_eligibility, v006_tms_execution_events, v007_tms_freight_settlement, v008_driver_vehicle_images, v009_delivery_pod_eta, v010_route_context_flow, v011_transport_trips, v012_vehicle_speed_profile, v013_demo_stabilization, v014_trip_cost_rows, v015_trip_stop_recipient, v016_delivery_completion_closeout, v017_driver_shift_turnaround, v018_dispatch_crew, v019_driver_availability, v020_epl_expense_vouchers, v021_vehicle_maintenance, v022_vehicle_type_capacity, v023_parking_list, v024_money_numeric, v025_vehicle_depot, v026_sales_order_lines, v027_vehicle_cost_overrides, v028_shipping_spec, v029_sales_order_cargo_type, v030_workflow_notes, v031_sales_order_documents, v032_delivery_order_arrived_status, v033_delivery_order_seal_no, v034_driver_depot_team_pattern, v035_vehicle_odometer, v036_location_coordinates, v037_route_road_geometry, v038_bao_gia_theo_spec_moi, v039_quotation_competitor_price, v040_quotation_flow_statuses, v041_phieu_thu_chi_theo_do, v042_bo_rang_buoc_charge_type_trung, v043_bo_bang_phieu_thu_chi, v044_ma_costindex, v045_trang_thai_van_hanh, v046_mui_gio_11_cot, v047_co_hoi_khach_hang, v048_ly_do_huy_do, v049_truc_xuat_don_hang

MIGRATIONS = (v001_workflow, v002_canonical_status_constraints, v003_tms_core_planning, v004_tms_tendering, v005_tms_dispatch_eligibility, v006_tms_execution_events, v007_tms_freight_settlement, v008_driver_vehicle_images, v009_delivery_pod_eta, v010_route_context_flow, v011_transport_trips, v012_vehicle_speed_profile, v013_demo_stabilization, v014_trip_cost_rows, v015_trip_stop_recipient, v016_delivery_completion_closeout, v017_driver_shift_turnaround, v018_dispatch_crew, v019_driver_availability, v020_epl_expense_vouchers, v021_vehicle_maintenance, v022_vehicle_type_capacity, v023_parking_list, v024_money_numeric, v025_vehicle_depot, v026_sales_order_lines, v027_vehicle_cost_overrides, v028_shipping_spec, v029_sales_order_cargo_type, v030_workflow_notes, v031_sales_order_documents, v032_delivery_order_arrived_status, v033_delivery_order_seal_no, v034_driver_depot_team_pattern, v035_vehicle_odometer, v036_location_coordinates, v037_route_road_geometry, v038_bao_gia_theo_spec_moi, v039_quotation_competitor_price, v040_quotation_flow_statuses, v041_phieu_thu_chi_theo_do, v042_bo_rang_buoc_charge_type_trung, v043_bo_bang_phieu_thu_chi, v044_ma_costindex, v045_trang_thai_van_hanh, v046_mui_gio_11_cot, v047_co_hoi_khach_hang, v048_ly_do_huy_do, v049_truc_xuat_don_hang)
POSTGRES_MIGRATION_LOCK_KEY = 1567831245


def required_migration_head():
    return MIGRATIONS[-1].VERSION


def _dialect(url):
    if "://" not in url:
        return "sqlite"
    scheme = url.split(":", 1)[0]
    if scheme != scheme.lower():
        raise ValueError("database URL scheme must be lowercase sqlite or postgresql")
    try:
        backend = make_url(url).get_backend_name()
    except Exception as error:
        raise ValueError("invalid database URL") from error
    if backend not in {"sqlite", "postgresql"}:
        raise ValueError("unsupported database URL; expected sqlite or postgresql")
    return backend


def _sqlite_path(url):
    return url[10:] if url.startswith("sqlite:///") else url


def dry_run(database_url, direction="upgrade"):
    sql = ["CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"]
    for migration in (MIGRATIONS if direction == "upgrade" else reversed(MIGRATIONS)):
        sql.extend(migration.statements(_dialect(database_url), direction))
    return ";\n".join(item.rstrip(";") for item in sql) + ";\n"


def _postgres(database_url, direction, engine=None, restore_from=None):
    owned = engine is None
    engine = engine or create_engine(database_url)
    completed = []
    try:
        with engine.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": POSTGRES_MIGRATION_LOCK_KEY},
            )
            connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
            applied = {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
            for migration in (MIGRATIONS if direction == "upgrade" else reversed(MIGRATIONS)):
                should_run = migration.VERSION not in applied if direction == "upgrade" else migration.VERSION in applied
                if should_run:
                    if direction == "rollback" and hasattr(migration, "pre_rollback_validate"):
                        migration.pre_rollback_validate(connection, "postgresql", restore_from)
                    for sql in migration.statements("postgresql", direction):
                        connection.execute(text(sql))
                    if direction == "upgrade" and hasattr(migration, "validate_postgresql"):
                        migration.validate_postgresql(connection)
                    marker = "INSERT INTO schema_migrations(version) VALUES (:version)" if direction == "upgrade" else "DELETE FROM schema_migrations WHERE version=:version"
                    connection.execute(text(marker), {"version": migration.VERSION})
                    completed.append(migration.VERSION)
    finally:
        if owned:
            engine.dispose()
    return completed


def applied_versions(database_url, engine=None):
    """Các phiên bản đã được ghi nhận, hoặc None nếu chưa có schema_migrations."""
    if _dialect(database_url) == "postgresql":
        owned = engine is None
        engine = engine or create_engine(database_url)
        try:
            with engine.connect() as connection:
                exists = connection.execute(text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='schema_migrations'"
                )).first()
                if not exists:
                    return None
                return {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
        finally:
            if owned:
                engine.dispose()
    connection = sqlite3.connect(_sqlite_path(database_url))
    try:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if not exists:
            return None
        return {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    finally:
        connection.close()


def baseline(database_url, engine=None):
    """Ghi nhận toàn bộ MIGRATIONS là đã áp dụng, KHÔNG chạy một câu DDL nào.

    Dùng cho database vừa được dựng từ model (Base.metadata.create_all). Các
    migration lịch sử là lệnh *sửa* bảng: v001 ALTER các bảng nghiệp vụ được
    giả định đã tồn tại, còn v006 đòi các bảng TMS khớp đúng DDL viết tay của
    nó. Trên một lược đồ vừa dựng từ model, cả hai đều không chạy được — đó
    chính là lý do đường khởi tạo SQLite luôn thất bại.

    Đây là cách làm chuẩn cho cài đặt mới: dựng lược đồ từ model, rồi đánh dấu
    lịch sử migration là đã xong. Các migration về sau (v024+) chạy bình thường.

    Từ chối nếu đã có lịch sử migration: một database đang dùng dở phải đi qua
    upgrade() để không bỏ sót bước nào.
    """
    existing = applied_versions(database_url, engine)
    if existing:
        raise RuntimeError(
            "baseline() chỉ dành cho database mới: đã có "
            f"{len(existing)} phiên bản được ghi nhận, hãy dùng upgrade()"
        )

    versions = [migration.VERSION for migration in MIGRATIONS]
    if _dialect(database_url) == "postgresql":
        owned = engine is None
        engine = engine or create_engine(database_url)
        try:
            with engine.begin() as connection:
                connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": POSTGRES_MIGRATION_LOCK_KEY})
                connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
                # Kiểm lại BÊN TRONG khóa: một tiến trình khác có thể vừa
                # baseline hoặc migrate xong ngay trước khi ta lấy được khóa.
                already = {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
                if already:
                    return []
                for version in versions:
                    connection.execute(
                        text("INSERT INTO schema_migrations(version) VALUES (:version)"),
                        {"version": version},
                    )
        finally:
            if owned:
                engine.dispose()
        return versions

    connection = sqlite3.connect(_sqlite_path(database_url), isolation_level=None)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        already = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
        if already:
            connection.rollback()
            return []
        connection.executemany(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            [(version,) for version in versions],
        )
        connection.commit()
        return versions
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def upgrade(database_url, engine=None, failure_hook=None):
    if _dialect(database_url) == "postgresql":
        return _postgres(database_url, "upgrade", engine)
    connection = sqlite3.connect(_sqlite_path(database_url), isolation_level=None)
    try:
        # Legacy databases can contain historical FK violations. Schema rebuilds
        # must preserve those rows without guessing; constraints remain in the
        # rebuilt schema and are enforced again after the atomic migration.
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
        completed = []
        for migration in MIGRATIONS:
            if migration.VERSION not in applied:
                migration.upgrade_sqlite(connection)
                if failure_hook:
                    failure_hook()
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (migration.VERSION,))
                completed.append(migration.VERSION)
        connection.commit()
        connection.execute("PRAGMA foreign_keys=ON")
        return completed
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def rollback(database_url, restore_from=None, engine=None):
    if _dialect(database_url) == "postgresql":
        if not restore_from:
            raise RuntimeError("rollback requires --restore-from authorization")
        return _postgres(database_url, "rollback", engine, restore_from)
    connection = sqlite3.connect(_sqlite_path(database_url), isolation_level=None)
    try:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchone():
            return []
        if not connection.execute("SELECT 1 FROM schema_migrations WHERE version=?", (v001_workflow.VERSION,)).fetchone():
            return []
        populated = any(
            connection.execute(f'SELECT EXISTS(SELECT 1 FROM "{table}" LIMIT 1)').fetchone()[0]
            for table in ("journal_lines", "journal_batches", "accounting_periods", "account_mappings", "idempotency_records", "migration_quarantine",
                          "transport_demands", "freight_units", "freight_orders", "freight_order_units", "carriers", "tenders", "tender_offers",
                          "driver_qualifications", "warehouse_appointments", "resource_assignments", "transport_events",
                          "transport_event_documents", "freight_order_legacy_links", "delivery_pod_records",
                          "transport_trips", "trip_delivery_orders", "transport_trip_legs",
                          "vehicle_maintenance_requests", "vehicle_maintenance_cost_lines")
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        )
        valuable_columns = _has_valuable_added_values(connection)
        if (populated or valuable_columns) and not restore_from:
            raise RuntimeError("destructive rollback refused: supply --restore-from")
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
        completed = []
        for migration in reversed(MIGRATIONS):
            if migration.VERSION in applied:
                if hasattr(migration, "pre_rollback_validate"):
                    migration.pre_rollback_validate(connection, "sqlite", restore_from)
                migration.rollback_sqlite(connection)
                connection.execute("DELETE FROM schema_migrations WHERE version=?", (migration.VERSION,))
                completed.append(migration.VERSION)
        connection.commit()
        return completed
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _has_valuable_added_values(connection):
    """Return true when rollback would discard post-migration information."""
    for table, column in (("vehicles", "image_url"), ("drivers", "photo_url")):
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            continue
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        if column in columns and connection.execute(
            f'SELECT EXISTS(SELECT 1 FROM "{table}" WHERE "{column}" IS NOT NULL AND trim("{column}") <> "")'
        ).fetchone()[0]:
            return True
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='vehicles'").fetchone():
        columns = {row[1] for row in connection.execute('PRAGMA table_info("vehicles")')}
        if "min_speed_kmh" in columns and connection.execute(
            'SELECT EXISTS(SELECT 1 FROM "vehicles" WHERE min_speed_kmh IS NOT NULL AND min_speed_kmh <> 35)'
        ).fetchone()[0]:
            return True
        if "max_speed_kmh" in columns and connection.execute(
            'SELECT EXISTS(SELECT 1 FROM "vehicles" WHERE max_speed_kmh IS NOT NULL AND max_speed_kmh <> 80)'
        ).fetchone()[0]:
            return True
    marker = connection.execute("SELECT applied_at FROM schema_migrations WHERE version=?", (v001_workflow.VERSION,)).fetchone()
    applied_at = marker[0] if marker else None
    for table in ("quotations", "delivery_orders", "ar_invoices"):
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        required = {"status", "canonical_status", "created_at", "updated_at", "created_by", "updated_by", "version"}
        if not required <= columns:
            continue
        connection.row_factory = sqlite3.Row
        rows = connection.execute(f'SELECT * FROM "{table}"').fetchall()
        connection.row_factory = None
        for row in rows:
            expected_status = v001_workflow.STATUS_MAP.get((row["status"] or "").strip().lower(), "unknown")
            if row["canonical_status"] != expected_status:
                return True
            if row["created_by"] != "migration" or row["updated_by"] != "migration" or row["version"] != 1:
                return True
            if applied_at and (row["created_at"] != applied_at or row["updated_at"] != applied_at):
                return True
            if table == "ar_invoices":
                if row["reversal_of_invoice_id"] is not None or not bool(row["is_active"]) or row["currency_code"] != "VND" or float(row["exchange_rate_snapshot"]) != 1:
                    return True
                if row["tax_rate_snapshot"] != row["vat_pct"]:
                    return True
    return False


def main(argv=None):
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("upgrade", "rollback"))
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--restore-from")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run:
        print(dry_run(args.database_url, args.command), end="")
    else:
        result = upgrade(args.database_url) if args.command == "upgrade" else rollback(args.database_url, args.restore_from)
        print("\n".join(result))


if __name__ == "__main__":
    main()
