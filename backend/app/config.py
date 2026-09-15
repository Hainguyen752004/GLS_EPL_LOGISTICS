"""Cấu hình của bản demo Packing List.

Bản demo này CÓ CƠ SỞ DỮ LIỆU RIÊNG, không dùng chung với EPL_System. Tệp .env
nằm ở gốc `parking_list_demo/` và trỏ vào database `parking_list_demo`.
"""

import os

from dotenv import load_dotenv

GOC_DU_AN = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEP_ENV = os.path.join(GOC_DU_AN, ".env")
if os.path.exists(TEP_ENV):
    load_dotenv(TEP_ENV)

DATABASE_URL = os.getenv("DATABASE_URL", "").split("#")[0].strip()
if not DATABASE_URL:
    raise ValueError("Thiếu DATABASE_URL trong parking_list_demo/.env")

# Chỉ chấp nhận PostgreSQL. Dự án đã chốt ngưng SQLite hoàn toàn.
if not DATABASE_URL.startswith(("postgresql:", "postgresql+")):
    raise ValueError("DATABASE_URL phải là PostgreSQL")

# Chặn dùng nhầm database của EPL_System — đây là bản demo tách riêng.
if DATABASE_URL.rstrip("/").endswith("/epl_logistics"):
    raise ValueError(
        "parking_list_demo không được dùng database epl_logistics; hãy trỏ vào database riêng"
    )

NGUOI_DUNG_DEMO = os.getenv("PL_DEMO_PRINCIPAL", "demo-warehouse")
CONG = int(os.getenv("PL_DEMO_PORT", "8042"))
