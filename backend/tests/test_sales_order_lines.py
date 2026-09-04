"""Dòng hàng hóa vận chuyển của đơn hàng vận chuyển.

Màn "Chi tiết đơn hàng" từ trước tới nay có một bảng dòng hàng đầy đủ — mã mục,
mô tả, số lượng, đơn vị tính, đơn giá cước, thành tiền — nhưng **không có bảng
nào để chứa nó**, và `saveOracleSO` chỉ gửi lên đúng ba trường. Người dùng nhập
xong, bấm Lưu, nhận thông báo thành công, và không một dòng nào được ghi lại.

Quan trọng hơn phép cộng: đơn vị tính của từng dòng được quy đổi ra khối lượng
và thể tích, vốn chính là hai con số mà `vehicle_capacity_policy` dùng để chặn
điều xe quá tải.
"""
from decimal import Decimal

import pytest

from services import workflow_service as svc
from services.errors import DomainError


# --------------------------------------------------------------------------
# Quy đổi đơn vị tính ra tải trọng
# --------------------------------------------------------------------------

@pytest.mark.parametrize("uom,quantity,kg,m3", [
    ("Tấn", Decimal(15), Decimal(15000), Decimal(0)),
    ("tấn", Decimal(2), Decimal(2000), Decimal(0)),
    ("Kg", Decimal(850), Decimal(850), Decimal(0)),
    ("Khối (m³)", Decimal(33), Decimal(0), Decimal(33)),
    ("m3", Decimal(5), Decimal(0), Decimal(5)),
    # "Chuyến" và "Km" là cách tính cước theo lần đi, không nói gì về khối
    # lượng — cố ý không quy đổi, nếu không sẽ bịa ra tải trọng không có thật.
    ("Chuyến", Decimal(3), Decimal(0), Decimal(0)),
    ("Km", Decimal(200), Decimal(0), Decimal(0)),
    ("", Decimal(9), Decimal(0), Decimal(0)),
])
def test_uom_maps_to_weight_or_volume(uom, quantity, kg, m3):
    assert svc._line_quantity_split(uom, quantity) == (kg, m3)


# --------------------------------------------------------------------------
# Ghi và tính lại
# --------------------------------------------------------------------------

class _Line:
    """Đủ để đóng vai một hàng đã ghi mà không cần cơ sở dữ liệu thật."""


class _FakeQuery:
    def __init__(self, store):
        self.store = store

    def filter(self, *_args):
        return self

    def delete(self, **_kwargs):
        self.store.clear()
        return 0


class _FakeDb:
    def __init__(self):
        self.rows = []

    def query(self, *_args):
        return _FakeQuery(self.rows)

    def add(self, row):
        self.rows.append(row)


class _FakeSO:
    id = "SO-TEST-001"
    total_amount = Decimal(0)
    weight_kg = 0.0
    volume_m3 = 0.0


def _run(rows):
    db, so = _FakeDb(), _FakeSO()
    svc._replace_sales_order_lines(db, so, rows)
    return db, so


def test_total_is_recomputed_from_the_lines():
    """Tổng do máy chủ TÍNH LẠI, không nhận từ giao diện.

    Nhận tổng từ giao diện thì tổng và các dòng có thể nói hai con số khác nhau
    — đúng kiểu mâu thuẫn mà cả màn hình này sinh ra để tránh.
    """
    db, so = _run([
        {"description": "Gạo", "quantity": 15, "uom": "Tấn", "unit_price": 1075000},
        {"description": "Đường", "quantity": 2, "uom": "Tấn", "unit_price": 500000},
    ])
    assert so.total_amount == Decimal(15) * Decimal(1075000) + Decimal(2) * Decimal(500000)
    assert [row.line_no for row in db.rows] == [1, 2]
    assert [row.amount for row in db.rows] == [Decimal(16125000), Decimal(1000000)]


def test_weight_and_volume_feed_the_capacity_check():
    db, so = _run([
        {"quantity": 15, "uom": "Tấn", "unit_price": 1000},
        {"quantity": 500, "uom": "Kg", "unit_price": 1000},
        {"quantity": 12, "uom": "Khối (m³)", "unit_price": 1000},
    ])
    assert so.weight_kg == 15500.0, "15 tấn + 500 kg"
    assert so.volume_m3 == 12.0


def test_lines_are_replaced_not_merged():
    """Gửi lại bảng ngắn hơn thì các dòng cũ phải biến mất.

    Ghép từng dòng sẽ để lại dòng mồ côi khi người dùng xóa bớt hàng.
    """
    db, so = _FakeDb(), _FakeSO()
    svc._replace_sales_order_lines(db, so, [{"quantity": 1, "uom": "Tấn", "unit_price": 10}] * 3)
    assert len(db.rows) == 3
    svc._replace_sales_order_lines(db, so, [{"quantity": 1, "uom": "Tấn", "unit_price": 10}])
    assert len(db.rows) == 1


def test_missing_lines_key_leaves_the_order_untouched():
    """Không gửi `lines` nghĩa là "không đụng tới", khác hẳn gửi mảng rỗng."""
    db, so = _FakeDb(), _FakeSO()
    so.total_amount = Decimal(999)
    svc._replace_sales_order_lines(db, so, None)
    assert so.total_amount == Decimal(999)
    assert db.rows == []


def test_negative_quantity_or_price_is_rejected():
    for row in ({"quantity": -1, "uom": "Tấn", "unit_price": 10},
                {"quantity": 1, "uom": "Tấn", "unit_price": -10}):
        with pytest.raises(DomainError) as error:
            _run([row])
        assert error.value.code == "SO_LINE_NEGATIVE"


def test_shape_and_size_are_bounded():
    with pytest.raises(DomainError) as error:
        _run("khong phai mang")
    assert error.value.code == "SO_LINES_INVALID"

    with pytest.raises(DomainError) as error:
        _run(["khong phai doi tuong"])
    assert error.value.code == "SO_LINES_INVALID"

    with pytest.raises(DomainError) as error:
        _run([{"quantity": 1, "uom": "Tấn", "unit_price": 1}] * 201)
    assert error.value.code == "SO_LINES_TOO_MANY"


def test_text_fields_are_bounded():
    db, _so = _run([{"description": "x" * 900, "quantity": 1, "uom": "y" * 90, "unit_price": 1}])
    assert len(db.rows[0].description) == 500
    assert len(db.rows[0].uom) == 32


def test_empty_list_zeroes_the_total():
    db, so = _FakeDb(), _FakeSO()
    so.total_amount = Decimal(500)
    svc._replace_sales_order_lines(db, so, [])
    assert so.total_amount == Decimal(0)
    assert db.rows == []
