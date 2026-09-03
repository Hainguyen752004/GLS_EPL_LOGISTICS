import logging
import os

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_MODE, DATABASE_URL
from migrations.runner import upgrade
from runtime_state import runtime_state


logger = logging.getLogger(__name__)


class DatabaseUnavailableError(RuntimeError):
    """Stable, credential-safe PostgreSQL startup error."""


def _sqlite_url():
    if DATABASE_URL:
        if not DATABASE_URL.startswith("sqlite:"):
            raise ValueError("DATABASE_URL must be a SQLite URL in sqlite mode")
        return DATABASE_URL

    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epl_logistics.db")
    return f"sqlite:///{database_path}"


if DATABASE_MODE == "postgres":
    try:
        if not DATABASE_URL:
            raise ValueError("missing URL")
        if not DATABASE_URL.startswith(("postgresql:", "postgresql+")):
            raise ValueError("invalid URL scheme")

        logger.info("Configuring PostgreSQL database")
        engine = create_engine(
            DATABASE_URL,
            # connect_timeout=2 gây lỗi giả qua WAN và trong lúc Postgres
            # failover; 10 giây là mức chịu đựng được mà vẫn phát hiện nhanh.
            connect_args={"connect_timeout": int(os.getenv("EPL_DB_CONNECT_TIMEOUT", "10"))},
            pool_pre_ping=True,
            pool_size=int(os.getenv("EPL_DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("EPL_DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("EPL_DB_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv("EPL_DB_POOL_RECYCLE", "1800")),
        )
    except Exception as error:
        # Thông báo trả ra ngoài vẫn phải đục để không rò connection string,
        # nhưng nguyên nhân gốc phải vào log: trước đây `from None` xóa sạch
        # nó, nên sai driver, sai scheme và database chết thật đều cho ra cùng
        # một dòng lỗi không thể phân biệt.
        # CHỈ ghi loại exception, không ghi thông báo: thông báo của SQLAlchemy
        # thường chứa nguyên connection string kèm mật khẩu. Riêng tên loại đã
        # phân biệt được ModuleNotFoundError (thiếu driver) với ArgumentError
        # (sai scheme) và OperationalError (database chết) — đó chính là thứ
        # trước đây `from None` làm mất.
        logger.error(
            "PostgreSQL engine configuration failed code=DATABASE_UNAVAILABLE error_type=%s",
            type(error).__name__,
        )
        raise DatabaseUnavailableError("DATABASE_UNAVAILABLE") from None
else:
    logger.info("Using explicitly configured SQLite database")
    engine = create_engine(
        _sqlite_url(),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _needs_baseline():
    """Database này có phải là cài đặt MỚI, cần dựng từ model rồi đánh mốc?

    Ba tình huống phải phân biệt cho đúng, vì chọn sai là hoặc bỏ sót migration
    hoặc làm ứng dụng không khởi động được:

    1. Đã có lịch sử migration (production PostgreSQL hiện tại: 23 bản đã ghi)
       → upgrade() như bình thường; nó sẽ là lệnh rỗng nếu đã đủ.

    2. Database trắng, chưa có bảng nào
       → dựng từ model rồi đánh mốc. Không thể chạy migration lịch sử vì v001
       ALTER những bảng chưa tồn tại.

    3. Có bảng nhưng KHÔNG có lịch sử migration — hai khả năng khác nhau hẳn:
       a. Lược đồ vừa dựng từ model (create_all): các bảng đã có cột
          canonical_status mà v001 sinh ra → chỉ cần đánh mốc.
       b. Database cũ từ thời chưa có migration: thiếu cột đó → PHẢI chạy
          upgrade() để không bỏ sót bước nào.
    """
    from migrations.runner import applied_versions

    url = engine.url.render_as_string(hide_password=False)
    if applied_versions(url, engine=engine):
        return False  # tình huống 1

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not tables:
        return True  # tình huống 2

    # Tình huống 3: dùng cột canonical_status trên quotations làm dấu nhận biết —
    # v001 là bản migration sinh ra nó.
    if "quotations" not in tables:
        return True
    columns = {column["name"] for column in inspector.get_columns("quotations")}
    return "canonical_status" in columns


def auto_migrate_db():
    # Cài đặt mới: dựng lược đồ từ model rồi đánh mốc lịch sử migration. Chạy
    # migration lịch sử trên một database mới là không thể — chúng là lệnh sửa
    # bảng, không phải lệnh tạo lược đồ từ đầu.
    if _needs_baseline():
        import models  # noqa: F401  (nạp muộn để tránh import vòng)
        from migrations.runner import baseline

        Base.metadata.create_all(bind=engine)
        completed = baseline(engine.url.render_as_string(hide_password=False), engine=engine)
        logger.info("Database baseline established versions=%s", len(completed))
        runtime_state.record_migration_success()
        return completed

    # Phải dùng URL của chính engine, không dùng DATABASE_URL thô: ở chế độ
    # sqlite mà biến đó trống thì _sqlite_url() tự tính đường dẫn, còn
    # upgrade("") lại đi qua sqlite3.connect("") — lệnh này KHÔNG báo lỗi, nó
    # mở một database tạm rồi vứt đi. Migration "thành công" trong khi
    # epl_logistics.db chưa hề được nâng cấp.
    completed = upgrade(engine.url.render_as_string(hide_password=False), engine=engine)
    runtime_state.record_migration_success()
    return completed


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
