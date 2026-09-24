# -*- coding: utf-8 -*-
"""Kết nối PostgreSQL cho bản Lào — cơ sở dữ liệu RIÊNG `epl_lao`.

Vì sao tách DB: bên Lào làm việc theo Excel của họ, mô hình dữ liệu khác hẳn EPL_System
(không Trip, không báo giá, không công thức giá thành). Dùng chung DB là mang toàn bộ
ràng buộc của hệ lớn vào một hệ cố ý đơn giản. Cùng máy chủ PostgreSQL, khác DB.

Không có tầng migration: bảng dựng từ model bằng create_all. Đây là quyết định có chủ ý —
hệ "năm 2016" thì cách vận hành cũng phải đơn giản tương xứng. Thêm cột thì thêm vào
model rồi chạy `python -m app.seed --dung-lai` trên máy dev.
"""
import logging
import os
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

GOC_DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(GOC_DU_AN, ".env"))

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if not DATABASE_URL.startswith(("postgresql:", "postgresql+")):
    raise RuntimeError("DATABASE_URL trong .env phải là PostgreSQL (postgresql+psycopg2://…/epl_lao)")

# Pool 15 + 10 dự phòng (trước 5 + 5): nghìn chuyến / ngày, vài chục người dùng cùng lúc và điện thoại tài xế gửi GPS
# 25 giây một lần — pool 5 là người thứ sáu đứng chờ. statement_timeout 60 s: một câu SQL chạy hỏng không được giữ
# kết nối hàng giờ làm cả hệ đứng theo.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("EPL_LAO_POOL", "15")),
    max_overflow=int(os.getenv("EPL_LAO_POOL_THEM", "10")),
    pool_recycle=1800,
    # Phiên ở UTC để cột timestamp trần không bị PostgreSQL đổi múi giờ lặng lẽ —
    # cùng bài học đã trả giá ở EPL_System.
    connect_args={"connect_timeout": 10, "options": "-c timezone=UTC -c statement_timeout=%s" % os.getenv("EPL_LAO_SQL_TOI_DA_MS", "60000")},
)

# NHẬT KÝ CÂU CHẬM: câu SQL nào quá EPL_LAO_CHAM_MS (mặc định 500 ms) thì ghi vào logs/cham.log — thời gian + câu
# lệnh, KHÔNG ghi tham số (có thể là tên đăng nhập, số tiền). Không cần bật gì trên máy chủ PostgreSQL dùng chung.
CHAM_MS = float(os.getenv("EPL_LAO_CHAM_MS", "500"))
_nk = logging.getLogger("epl_lao.cham")
if not _nk.handlers:
    os.makedirs(os.path.join(GOC_DU_AN, "logs"), exist_ok=True)
    _h = logging.FileHandler(os.path.join(GOC_DU_AN, "logs", "cham.log"), encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _nk.addHandler(_h); _nk.setLevel(logging.INFO); _nk.propagate = False


@event.listens_for(engine, "before_cursor_execute")
def _bat_dau(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("_t0", []).append(time.perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _xong(conn, cursor, statement, parameters, context, executemany):
    ms = (time.perf_counter() - conn.info["_t0"].pop()) * 1000
    if ms >= CHAM_MS:
        _nk.info("%7.0f ms  %s", ms, " ".join(statement.split())[:1500])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Cột ĐỔI TÊN theo thời gian. Chạy TRƯỚC create_all, nên dữ liệu cũ đi theo tên mới thay vì nằm lại
# trong một cột mồ côi. Chỉ đổi khi cột cũ còn và cột mới chưa có, nên chạy lại bao nhiêu lần cũng được.
#   21/09/2026: cước không còn mặc định USD (khách trả USD · LAK · CNY · THB), nên bỏ hậu tố "_usd"
#   khỏi tên cột tiền — cột tên `price_usd` mà chứa Nhân dân tệ là cột nói dối.
DOI_TEN_COT = [
    ("trips", "price_usd", "price"),
    ("trips", "hire_price_usd", "hire_price"),
    ("trips", "over_price_usd", "over_price"),
    ("customer_rates", "price_usd", "price"),
    ("customer_rates", "hire_price_usd", "hire_price"),
]


def _doi_ten_cot(c, insp):
    co_bang = set(insp.get_table_names())
    for bang, cu, moi in DOI_TEN_COT:
        if bang not in co_bang:
            continue
        cot = {x["name"] for x in insp.get_columns(bang)}
        if cu in cot and moi not in cot:
            from sqlalchemy import text
            c.execute(text('ALTER TABLE %s RENAME COLUMN "%s" TO "%s"' % (bang, cu, moi)))
            print("  đổi tên cột %s.%s → %s" % (bang, cu, moi))


def tao_bang():
    """Dựng bảng còn thiếu, ĐỔI TÊN cột đã đổi tên, và THÊM CỘT còn thiếu vào bảng đã có.

    create_all không thêm cột vào bảng đã tồn tại. Không có tầng migration nên khi model có thêm
    cột (ví dụ trips.route_id), ta so cột trong model với cột thật trong DB rồi ALTER TABLE ADD
    COLUMN cho phần thiếu. Chỉ THÊM, ĐỔI TÊN theo danh sách trên, không đổi kiểu, không xoá — đủ
    cho hệ này, và không bao giờ làm mất dữ liệu.
    """
    import models  # noqa: F401 — nạp để Base biết hết bảng
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.begin() as c:          # đổi tên trước, không create_all sẽ dựng thêm cột mới rỗng
        _doi_ten_cot(c, insp)
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
    tao_chi_muc()


# CHỈ MỤC — create_all chỉ dựng chỉ mục khi dựng bảng MỚI, bảng đã có thì không; nên liệt kê ở đây và tạo
# `IF NOT EXISTS` mỗi lần khởi động (đã có thì bỏ qua ngay). Chọn theo đúng các câu lọc / sắp của màn hình.
CHI_MUC = [
    ("ix_trips_ngay", "trips", "(doc_date DESC, doc_no DESC)"),              # danh sách phiếu: mới nhất trước
    ("ix_trips_tai_xe", "trips", "(driver_id, doc_date DESC)"),              # "Phiếu của tôi"
    ("ix_trips_xe", "trips", "(vehicle_id, doc_date DESC)"),
    ("ix_trips_khach", "trips", "(customer_id, doc_date DESC)"),
    ("ix_trips_chu_xe", "trips", "(owner_id, doc_date DESC)"),
    ("ix_trips_van_chuyen", "trips", "(transport_status, doc_date DESC)"),
    ("ix_trips_thu", "trips", "(finance_status, doc_date DESC)"),
    ("ix_trips_hoa_don", "trips", "(invoice_id)"),
    # tập "phiếu còn việc" của màn Theo dõi — chỉ mục MỘT PHẦN: cả năm 365.000 phiếu mà chỉ vài nghìn còn việc
    ("ix_trips_con_viec", "trips", "(doc_date DESC, doc_no DESC) WHERE (transport_status <> 'arrived' OR finance_status <> 'paid')"),
    ("ix_trips_tuyen", "trips", "(route_id)"),
    ("ix_vp_phieu_luc", "vehicle_positions", "(trip_id, ts DESC)"),          # điểm mới nhất của phiếu
    ("ix_vp_xe_luc", "vehicle_positions", "(vehicle_id, ts DESC)"),
    ("ix_fuel_moves_phieu_linh", "fuel_moves", "(voucher_id)"),
    ("ix_fuel_moves_dong_chi", "fuel_moves", "(expense_id)"),
    ("ix_fuel_moves_ngay", "fuel_moves", "(move_date DESC)"),
    ("ix_vouchers_ngay", "vouchers", "(doc_date DESC)"),
    ("ix_vouchers_cho", "vouchers", "(trip_id) WHERE status = 'cho'"),
    ("ix_trip_expenses_ncc", "trip_expenses", "(supplier_id)"),
    ("ix_trip_payments_ngay", "trip_payments", "(pay_date)"),
    ("ix_chung_tu_ngay", "chung_tu", "(ngay DESC)"),
    ("ix_trip_events_luc", "trip_events", "(ts DESC)"),
]


# Ô TÌM phiếu (số phiếu, tài xế, số xe, khách, biển số, nơi đi / đến, số phiếu quặng) — gộp thành MỘT biểu thức
# để một chỉ mục trigram (pg_trgm) phục vụ được "chứa chữ …" trên 365.000 phiếu. Câu tìm ở routes/phieu.py phải
# dùng ĐÚNG biểu thức này thì PostgreSQL mới dùng chỉ mục.
TIM_PHIEU_COT = ("doc_no", "driver_name", "truck_no", "customer_name", "plate_head", "plate_trailer",
                 "origin", "destination", "ore_bill_no")
BIEU_THUC_TIM_PHIEU = " || ' ' || ".join("coalesce(%s, '')" % c for c in TIM_PHIEU_COT)
CO_TRGM = {"co": False}


def tao_chi_muc():
    from sqlalchemy import inspect, text
    co_bang = set(inspect(engine).get_table_names())
    with engine.begin() as c:
        for ten, bang, cot in CHI_MUC:
            if bang in co_bang:
                c.execute(text("CREATE INDEX IF NOT EXISTS %s ON %s %s" % (ten, bang, cot)))
    _gps_thang_toi()
    try:                     # pg_trgm cài THEO TỪNG DB (không đụng cấu hình chung của máy chủ); không cài được thì tìm vẫn chạy, chỉ chậm hơn
        with engine.begin() as c:
            c.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            c.execute(text("CREATE INDEX IF NOT EXISTS ix_trips_tim ON trips USING gin ((%s) gin_trgm_ops)" % BIEU_THUC_TIM_PHIEU))
        CO_TRGM["co"] = True
    except Exception as e:  # noqa: BLE001
        print("  (không dựng được chỉ mục tìm pg_trgm: %s)" % str(e).splitlines()[0])


def _gps_thang_toi():
    """Bảng GPS đã chia theo tháng (tools/gps_thang.py chia) thì dựng sẵn bảng con tháng này + 2 tháng tới — điểm mới
    luôn có chỗ ghi, không rơi vào bảng DEFAULT. Chưa chia thì không làm gì."""
    import datetime as dt
    from sqlalchemy import text
    try:
        with engine.begin() as c:
            if c.execute(text("SELECT relkind FROM pg_class WHERE relname = 'vehicle_positions' "
                              "AND relnamespace = 'public'::regnamespace")).scalar() != "p":
                return
            h = dt.date.today()
            for k in range(3):
                t = h.year * 12 + h.month - 1 + k
                a, b = dt.date(t // 12, t % 12 + 1, 1), dt.date((t + 1) // 12, (t + 1) % 12 + 1, 1)
                c.execute(text("CREATE TABLE IF NOT EXISTS vehicle_positions_%04d_%02d PARTITION OF vehicle_positions "
                               "FOR VALUES FROM ('%s') TO ('%s')" % (a.year, a.month, a.isoformat(), b.isoformat())))
    except Exception as e:  # noqa: BLE001 — không dựng được thì điểm rơi vào bảng DEFAULT, vẫn không mất
        print("  (không dựng được bảng con GPS tháng tới: %s)" % str(e).splitlines()[0])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Bộ đệm báo cáo theo tháng (services/dem_bao_cao.py) gắn hook vào MỌI phiên ORM — nạp ở đây để máy chủ lẫn công cụ
# dùng database.SessionLocal đều tăng số phiên bản tháng khi ghi, không phụ thuộc thứ tự import ở nơi khác.
import services.dem_bao_cao  # noqa: E402,F401
