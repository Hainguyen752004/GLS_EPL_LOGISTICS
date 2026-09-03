import logging
import builtins
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError

from database import engine
from migrations.runner import required_migration_head
from migrations import v006_tms_execution_events, v007_tms_freight_settlement, v008_driver_vehicle_images, v009_delivery_pod_eta, v010_route_context_flow, v011_transport_trips, v012_vehicle_speed_profile, v015_trip_stop_recipient, v016_delivery_completion_closeout, v017_driver_shift_turnaround, v018_dispatch_crew, v019_driver_availability, v020_epl_expense_vouchers
from runtime_state import runtime_state


router = APIRouter()
logger = logging.getLogger(__name__)
REQUIRED_TABLES = frozenset({
    "customers", "routes", "vehicles", "drivers", "quotations",
    "sales_orders", "delivery_orders",
    "transport_demands", "freight_units", "freight_orders", "freight_order_units",
    "carriers", "tenders", "tender_offers",
    "driver_qualifications", "warehouse_appointments", "resource_assignments",
    "transport_events", "transport_event_documents", "freight_order_legacy_links",
    "currency_definitions", "currency_rate_history", "tax_codes", "finance_control_config",
    "freight_actual_costs", "freight_charge_items", "freight_cost_documents",
    "ap_invoices", "ap_invoice_lines", "freight_settlements", "settlement_payments",
    "delivery_pod_records", "delivery_order_closeouts",
    "delivery_order_charge_adjustments", "delivery_pod_documents",
    "transport_trips", "trip_delivery_orders", "transport_trip_legs",
    "driver_shift_assignments",
    "epl_expense_vouchers",
})


class DatabaseSchemaError(RuntimeError):
    pass


class DatabaseReadinessChecker:
    def __init__(self, database_engine):
        self.engine = database_engine

    def _dialect_name(self):
        """Tên dialect, mặc định về nhánh nghiêm ngặt nhất khi không đọc được.

        Engine thật của SQLAlchemy luôn có ``.dialect``, nên nhánh mặc định chỉ
        chạm tới các test double. Mặc định là "postgresql" — đường kiểm tra
        đầy đủ nhất — để việc thiếu thuộc tính không bao giờ làm *yếu* phần
        xác thực lược đồ.
        """
        dialect = getattr(self.engine, "dialect", None)
        return getattr(dialect, "name", None) or "postgresql"

    def _table_query(self):
        """Câu truy vấn liệt kê bảng, theo đúng dialect đang dùng.

        information_schema không tồn tại trên SQLite, nên probe sâu trước đây
        luôn báo DATABASE_UNAVAILABLE ở chế độ sqlite — tức chốt kiểm tra duy
        nhất có ý nghĩa thì vô dụng đúng lúc cần nhất.
        """
        if self._dialect_name() == "sqlite":
            return "SELECT name FROM sqlite_master WHERE type = 'table'"
        return (
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )

    def check(self):
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
            tables = {
                row[0] for row in connection.execute(text(self._table_query()))
            }
            if "schema_migrations" not in tables or not REQUIRED_TABLES <= tables:
                raise DatabaseSchemaError("required database schema is incomplete")
            versions = {
                row[0] for row in connection.execute(
                    text("SELECT version FROM schema_migrations")
                )
            }
            if required_migration_head() not in versions:
                raise DatabaseSchemaError("required database schema is incomplete")
            if self._dialect_name() != "postgresql":
                return  # các validator dưới đây chỉ đọc được catalog của Postgres
            try:
                v006_tms_execution_events.validate_postgresql(connection)
                v007_tms_freight_settlement.validate_postgresql(connection)
                v008_driver_vehicle_images.validate_postgresql(connection)
                v009_delivery_pod_eta.validate_postgresql(connection)
                v010_route_context_flow.validate_postgresql(connection)
                v011_transport_trips.validate_postgresql(connection)
                v012_vehicle_speed_profile.validate_postgresql(connection)
                v015_trip_stop_recipient.validate_postgresql(connection)
                v016_delivery_completion_closeout.validate_postgresql(connection)
                v017_driver_shift_turnaround.validate_postgresql(connection)
                v018_dispatch_crew.validate_postgresql(connection)
                v019_driver_availability.validate_postgresql(connection)
                v020_epl_expense_vouchers.validate_postgresql(connection)
            except RuntimeError as error:
                raise DatabaseSchemaError("required database schema is incomplete") from error


database_checker = DatabaseReadinessChecker(engine)


def get_database_checker():
    return database_checker


def get_runtime_state():
    return runtime_state


def _failure(error):
    if isinstance(error, TimeoutError):
        return "DATABASE_TIMEOUT", "Cơ sở dữ liệu phản hồi quá thời gian cho phép."
    if isinstance(error, DatabaseSchemaError):
        return "DATABASE_SCHEMA_INVALID", "Lược đồ cơ sở dữ liệu chưa sẵn sàng."
    if isinstance(error, OperationalError):
        original = getattr(error, "orig", None)
        sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
        if sqlstate == "28P01":
            return "DATABASE_AUTH_FAILED", "Xác thực cơ sở dữ liệu thất bại."
        if (
            sqlstate == "57014"
            or getattr(original, "errno", None) in {110, 60, 10060}
            or getattr(original, "timeout", False) is True
            or isinstance(original, (builtins.TimeoutError, TimeoutError))
        ):
            return "DATABASE_TIMEOUT", "Cơ sở dữ liệu phản hồi quá thời gian cho phép."
    return "DATABASE_UNAVAILABLE", "Cơ sở dữ liệu tạm thời không khả dụng."


@router.get("/api/health")
async def health():
    """Liveness: tiến trình còn sống. Cố tình KHÔNG chạm cơ sở dữ liệu.

    Đây không phải readiness — dùng /api/health/database cho việc đó. Trộn hai
    khái niệm sẽ khiến orchestrator restart một tiến trình vẫn khỏe chỉ vì
    database tạm thời chập, tức biến sự cố DB thành sự cố mất hẳn dịch vụ.

    Việc một instance có schema lỗi không được nhận traffic đã được chặn ở
    tầng cao hơn: main.on_startup bật lỗi và tiến trình không khởi động nổi.
    """
    return {"status": "ok"}


@router.get("/api/health/database")
def database_health(
    checker=Depends(get_database_checker), state=Depends(get_runtime_state)
):
    failure = state.migration_failure
    correlation_id = failure[1] if failure and failure[1] else uuid4().hex
    try:
        if failure:
            raise DatabaseSchemaError("startup migration failed")
        checker.check()
        state.record_database_success()
        return {"status": "ok", "database": "postgresql"}
    except Exception as error:
        code, message = _failure(error)
        logger.warning("Database readiness failed code=%s correlation_id=%s", code, correlation_id)
        raise HTTPException(status_code=503, detail={
            "code": code, "message": message, "correlation_id": correlation_id,
        }) from None
