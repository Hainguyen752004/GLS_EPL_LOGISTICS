# -*- coding: utf-8 -*-
"""Kết nối PostgreSQL cho bản Lào — cơ sở dữ liệu RIÊNG `epl_lao`.

Vì sao tách DB: bên Lào làm việc theo Excel của họ, mô hình dữ liệu khác hẳn EPL_System
(không Trip, không báo giá, không công thức giá thành). Dùng chung DB là mang toàn bộ
ràng buộc của hệ lớn vào một hệ cố ý đơn giản. Cùng máy chủ PostgreSQL, khác DB.

Không có tầng migration: bảng dựng từ model bằng create_all. Đây là quyết định có chủ ý —
hệ "năm 2016" thì cách vận hành cũng phải đơn giản tương xứng. Thêm cột thì thêm vào
model rồi chạy `python -m app.seed --dung-lai` trên máy dev.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

GOC_DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(GOC_DU_AN, ".env"))

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if not DATABASE_URL.startswith(("postgresql:", "postgresql+")):
    raise RuntimeError("DATABASE_URL trong .env phải là PostgreSQL (postgresql+psycopg2://…/epl_lao)")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("EPL_LAO_POOL", "5")),
    max_overflow=5,
    # Phiên ở UTC để cột timestamp trần không bị PostgreSQL đổi múi giờ lặng lẽ —
    # cùng bài học đã trả giá ở EPL_System.
    connect_args={"connect_timeout": 10, "options": "-c timezone=UTC"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def tao_bang():
    """Dựng bảng còn thiếu, và THÊM CỘT còn thiếu vào bảng đã có.

    create_all không thêm cột vào bảng đã tồn tại. Không có tầng migration nên khi model có thêm
    cột (ví dụ trips.route_id), ta so cột trong model với cột thật trong DB rồi ALTER TABLE ADD
    COLUMN cho phần thiếu. Chỉ THÊM, không đổi kiểu, không xoá — đủ cho hệ này, và không bao giờ
    làm mất dữ liệu.
    """
    import models  # noqa: F401 — nạp để Base biết hết bảng
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    with engine.begin() as c:
        for bang in Base.metadata.sorted_tables:
            co = {col["name"] for col in insp.get_columns(bang.name)}
            for col in bang.columns:
                if col.name in co:
                    continue
                kieu = col.type.compile(dialect=engine.dialect)
                c.execute(text('ALTER TABLE %s ADD COLUMN IF NOT EXISTS "%s" %s' % (bang.name, col.name, kieu)))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
