import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "connect_timeout": 10,
        # Múi giờ phiên PHẢI là UTC. Máy chủ PostgreSQL của dự án đặt TimeZone
        # là Asia/Ho_Chi_Minh; ghi một mốc có múi giờ UTC vào cột timestamp trần
        # thì PostgreSQL đổi sang giờ phiên rồi mới bỏ nhãn, nên mọi mốc lệch
        # đúng bảy giờ. EPL_System đã cắn lỗi này hai lần.
        "options": "-c timezone=UTC",
    },
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=5,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def tao_luoc_do():
    """Dựng bảng từ model. Demo nhỏ nên không cần bộ migration riêng."""
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Đã dựng lược đồ cho parking_list_demo")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
