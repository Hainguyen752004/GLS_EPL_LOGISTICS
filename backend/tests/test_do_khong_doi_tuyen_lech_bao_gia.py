# -*- coding: utf-8 -*-
"""Lệnh giao hàng sinh từ báo giá thì KHÔNG được đổi tuyến.

LỖ NÀY ĐÃ ĐO ĐƯỢC trên PostgreSQL thật, bằng đúng đường mà giao diện đi:

    DO-2026-0007-DO02 (từ QT-2026-007)
    tuyến: VSIP II-A → Cát Lái (44,7 km)  ->  Cát Lái → Amata (38,4 km)
    cước thu khách: 1.326.200  ->  1.326.200        (KHÔNG ĐỔI)

Đổi được, và không một lời cảnh báo nào.

VÌ SAO NÓ QUAN TRỌNG. Chủ dự án tự nêu ra rủi ro này khi bàn về phiếu thu/phiếu
chi: *"nếu nó lệch thì phiếu chi và cước phí báo khách đều sai hết"*. Và anh
đúng — chi phí thực tế tính trên km THẬT của tuyến mới, còn cước thu khách vẫn
là con số tính cho tuyến CŨ. Hai con số cùng nói về một lệnh giao hàng mà không
còn cùng một cơ sở.

Ba tầng của hệ thống, theo đúng định nghĩa của chủ dự án, giải thích vì sao chặn
là đúng chỗ: **Báo giá** là thoả thuận với khách (tuyến nào, loại xe gì, giá bao
nhiêu), **DO** là lệnh giao hàng cụ thể mà khách yêu cầu, **Trip** là chuyến xe
thật công ty tổ chức. Tuyến và giá thuộc tầng BÁO GIÁ, nên sửa chúng phải sửa ở
đó — không sửa lén ở tầng dưới.

VÀ VÌ SAO CHẶN chứ không tự tính lại giá: tính lại là âm thầm đổi con số đã gửi
cho khách. Bắt quay lại sửa báo giá thì chậm hơn một bước, nhưng con số nào cũng
có người chịu trách nhiệm.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Customer, DeliveryOrder, Quotation, Route


@pytest.fixture
def db(tmp_path, may_kiem):
    engine = may_kiem()
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Customer(id="CUS-RT", name="Khach kiem tuyen"))
    session.add(Route(id="RT-DAI", name="Tuyen dai", distance_km=120, segments_json="[]"))
    session.add(Route(id="RT-NGAN", name="Tuyen ngan", distance_km=40, segments_json="[]"))
    # Khach hang va tuyen duong phai VAO TRUOC bao gia. `Quotation.route_id`
    # khai `ForeignKey("routes.id")` ma khong khai `relationship()`, va
    # SQLAlchemy xep thu tu chen theo RELATIONSHIP chu khong theo cot khoa ngoai
    # tran — thieu no thi no xep theo ten bang, va `quotations` di truoc
    # `routes`. PostgreSQL cuong che khoa ngoai nen vo ngay.
    session.flush()
    session.add(Quotation(
        id="QT-RT", customer_id="CUS-RT", route_id="RT-DAI",
        canonical_status="split", status="Da tach DO",
        total_cost=3_000_000, selling_price=5_000_000,
        valid_to=(dt.date.today() + dt.timedelta(days=30)).isoformat(),
    ))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _do(db, **ghi_de):
    goi = dict(
        id="DO-RT-1", customer_id="CUS-RT", route_id="RT-DAI",
        quotation_id="QT-RT", unit_price=5_000_000, price_basis="per_trip",
        canonical_status="pending", status="Cho van chuyen",
        weight_kg=10_000, pallet_count=10,
    )
    goi.update(ghi_de)
    do = DeliveryOrder(**goi)
    db.add(do)
    # CHỐT hẳn, không chỉ `flush`. Bài "chặn nghĩa là không đổi gì" gọi
    # `db.rollback()` để dọn giao dịch lỗi, và một dòng chỉ mới `flush` sẽ biến
    # mất theo — rồi bài kiểm đỏ vì `None`, một lời báo không nói gì về điều nó
    # đang kiểm.
    db.commit()
    return do


def test_doi_tuyen_bi_chan_khi_do_sinh_tu_bao_gia(db):
    from services import workflow_service as svc
    do = _do(db)
    with pytest.raises(Exception) as loi:
        svc.update_delivery_order(db, do.id, {"route_id": "RT-NGAN"}, "nguoi-dieu-phoi")
    assert getattr(loi.value, "code", None) == "DO_ROUTE_LOCKED_BY_QUOTATION"

    # Thông báo phải NÓI RÕ CON SỐ, không nói chung. "Không đổi được tuyến" thì
    # người dùng phải đi hỏi; "120 km sang 40 km, lệch 67%, cước 5.000.000 đã
    # khoá" thì họ tự quyết được.
    chu = str(getattr(loi.value, "message", loi.value))
    assert "120,0" in chu and "40,0" in chu, chu
    assert "67%" in chu, chu
    assert "5.000.000" in chu, chu
    assert "QT-RT" in chu, chu


def test_tuyen_va_gia_KHONG_bi_doi_khi_bi_chan(db):
    """Chặn nghĩa là không đổi gì — không được đổi một nửa rồi mới bật lỗi."""
    from services import workflow_service as svc
    do = _do(db)
    with pytest.raises(Exception):
        svc.update_delivery_order(db, do.id, {"route_id": "RT-NGAN"}, "nguoi-dieu-phoi")
    db.rollback()
    lai = db.query(DeliveryOrder).filter(DeliveryOrder.id == "DO-RT-1").first()
    assert lai.route_id == "RT-DAI"
    assert float(lai.unit_price) == 5_000_000


def test_gui_lai_dung_tuyen_dang_co_thi_sua_duoc(db):
    """Giao diện gửi CẢ biểu mẫu mỗi lần lưu, nên `route_id` luôn có trong gói.

    Chặn cả trường hợp đó là chặn mọi lần sửa khối lượng hay khung giờ — tức
    biến một cửa chặn hẹp thành một lệnh cấm sửa.
    """
    from services import workflow_service as svc
    do = _do(db)
    kq = svc.update_delivery_order(
        db, do.id, {"route_id": "RT-DAI", "weight_kg": 12000}, "nguoi-dieu-phoi")
    assert kq.route_id == "RT-DAI"
    assert float(kq.weight_kg) == 12000


def test_do_tao_tay_thi_doi_tuyen_tu_do(db):
    """DO không sinh từ báo giá thì không mang lời hứa giá nào với khách."""
    from services import workflow_service as svc
    do = _do(db, id="DO-RT-TAY", quotation_id=None, unit_price=None)
    kq = svc.update_delivery_order(db, do.id, {"route_id": "RT-NGAN"}, "nguoi-dieu-phoi")
    assert kq.route_id == "RT-NGAN"


def test_khong_doi_tuyen_thi_khong_can_doc_bao_gia(db):
    """Sửa khối lượng của một DO sinh từ báo giá thì cửa chặn không được xen vào.

    Cửa chặn chỉ nói về việc ĐỔI TUYẾN; nó không được biến thành một phép kiểm
    toàn vẹn dữ liệu chặn cả những việc không liên quan.

    BÀI NÀY TRƯỚC ĐÂY DỰNG MỘT CẢNH KHÔNG TỒN TẠI. Nó tạo một DO trỏ vào
    `quotation_id="QT-DA-XOA"` — một báo giá không có thật — để giả cảnh "báo giá
    gốc đã bị xoá". Cảnh đó chạy được trên SQLite vì SQLite trong dự án tắt
    `PRAGMA foreign_keys`. Trên PostgreSQL thật thì KHÔNG:

        delivery_orders_quotation_id_fkey  FOREIGN KEY (quotation_id)
            REFERENCES quotations(id)      -- ON DELETE NO ACTION

    Nên một DO mồ côi báo giá không thể tồn tại, và một báo giá đã có DO cũng
    không thể xoá. Giữ bài kiểm cũ là chốt lại hành vi cho một trạng thái dữ
    liệu mà cơ sở dữ liệu thật không cho phép — tức chốt vào chỗ trống.

    Phần đáng chốt thì vẫn còn: cửa chặn chỉ ĐỌC báo giá khi tuyến ĐỔI. Bài này
    kiểm đúng điều đó, cộng thêm việc ghi nhận rằng trạng thái mồ côi là bất khả.
    """
    import sqlalchemy.exc
    from services import workflow_service as svc

    do = _do(db, id="DO-RT-SUA-CAN")
    kq = svc.update_delivery_order(db, do.id, {"weight_kg": 8000}, "nguoi-dieu-phoi")
    assert float(kq.weight_kg) == 8000
    assert kq.route_id == "RT-DAI", "sửa khối lượng không được đổi tuyến"

    # Và ghi lại vì sao cảnh "mồ côi báo giá" không cần bài kiểm nào: cơ sở dữ
    # liệu chặn nó. Nếu một ngày khoá ngoại này bị bỏ thì phép dưới đây đỏ, và
    # người sửa sẽ đọc được rằng phải xử lý trạng thái mồ côi ở tầng nghiệp vụ.
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        _do(db, id="DO-RT-MOCOI", quotation_id="QT-KHONG-CO-THAT")
    db.rollback()
