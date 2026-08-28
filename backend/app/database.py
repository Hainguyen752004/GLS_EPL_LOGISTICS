import logging
import os

from sqlalchemy import create_engine, event
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
            connect_args={"connect_timeout": 2},
            pool_pre_ping=True,
        )
    except Exception:
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


def auto_migrate_db():
    completed = upgrade(DATABASE_URL, engine=engine)
    runtime_state.record_migration_success()
    return completed


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
