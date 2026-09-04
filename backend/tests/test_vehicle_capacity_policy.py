"""Ràng buộc năng lực xe khi điều phối.

Ba điều rà soát được ở lớp này:

  1. Kiểm tra bị VIẾT HAI LẦN trong `tms_dispatch_service`: gọi
     `require_vehicle_capacity()` rồi ngay sau đó lặp lại đúng phép so sánh đó
     bằng tay. Khối thứ hai là code chết — khối trên đã ném lỗi — và câu thông
     báo của nó lại không có con số nào. Hai bản sao sẽ trôi khỏi nhau.
  2. Xe CHƯA KHAI năng lực thì so với 0 ra câu "8.500/0 kg": đúng về số nhưng
     không nói được phải sửa ở đâu.
  3. Đơn hàng chưa khai khối lượng thì phép kiểm không kiểm được gì cả — một
     container 30 tấn vẫn lọt lên xe tải 2 tấn.
"""
import pytest

from services.errors import DomainError
from services.vehicle_capacity_policy import (
    declares_no_cargo,
    require_vehicle_capacity,
    undeclared_vehicle_capacity,
)


class _Vehicle:
    def __init__(self, weight=10000, volume=30, pallet=20, vid="51C-123.45"):
        self.id = vid
        self.weight_capacity = weight
        self.volume_capacity_m3 = volume
        self.pallet_capacity = pallet


def _raises(vehicle, **kwargs):
    with pytest.raises(DomainError) as error:
        require_vehicle_capacity(vehicle, **kwargs)
    return error.value


# --------------------------------------------------------------------------
# Vừa xe thì cho qua
# --------------------------------------------------------------------------

def test_cargo_that_fits_is_allowed():
    require_vehicle_capacity(_Vehicle(), weight_kg=9000, volume_m3=25, pallet_count=18)


def test_cargo_exactly_at_capacity_is_allowed():
    """Đúng bằng năng lực là vừa, không phải vượt."""
    require_vehicle_capacity(_Vehicle(), weight_kg=10000, volume_m3=30, pallet_count=20)


# --------------------------------------------------------------------------
# Vượt năng lực
# --------------------------------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("weight_kg", 10001),
    ("volume_m3", 31),
    ("pallet_count", 21),
])
def test_each_dimension_is_checked(field, value):
    error = _raises(_Vehicle(), **{field: value})
    assert error.code == "CAPACITY_EXCEEDED"


def test_message_names_every_dimension_that_failed_with_numbers():
    """Câu lỗi phải nói vượt bao nhiêu trên bao nhiêu.

    Bản trùng lặp bị dỡ chỉ nói "vượt năng lực tải trọng, thể tích hoặc pallet"
    — người điều phối đọc xong vẫn không biết phải đổi xe cỡ nào.
    """
    error = _raises(_Vehicle(), weight_kg=12000, volume_m3=45, pallet_count=25, subject="Trip T-1")
    assert error.code == "CAPACITY_EXCEEDED"
    assert "Trip T-1" in error.message
    assert "51C-123.45" in error.message
    assert "12.000/10.000 kg" in error.message
    assert "45/30 m³" in error.message
    assert "25/20 pallet" in error.message


# --------------------------------------------------------------------------
# Xe chưa khai năng lực
# --------------------------------------------------------------------------

def test_undeclared_vehicle_capacity_points_at_master_data():
    error = _raises(_Vehicle(weight=0), weight_kg=8500)
    assert error.code == "VEHICLE_CAPACITY_UNDECLARED"
    assert "chưa khai báo tải trọng" in error.message
    assert "51C-123.45" in error.message


def test_undeclared_capacity_still_blocks_the_dispatch():
    """Thiếu dữ liệu phải chặn, không được cho qua.

    Không kiểm được không có nghĩa là an toàn.
    """
    with pytest.raises(DomainError):
        require_vehicle_capacity(_Vehicle(weight=0, volume=0, pallet=0), weight_kg=1, volume_m3=1, pallet_count=1)


def test_undeclared_capacity_is_ignored_when_nothing_needs_it():
    """Xe không khai số pallet vẫn chở được hàng không tính theo pallet."""
    require_vehicle_capacity(_Vehicle(pallet=0), weight_kg=9000, volume_m3=25, pallet_count=0)


def test_undeclared_vehicle_capacity_lists_what_is_missing():
    assert undeclared_vehicle_capacity(_Vehicle(weight=0, volume=0)) == ["tải trọng", "thể tích"]
    assert undeclared_vehicle_capacity(_Vehicle()) == []
    assert undeclared_vehicle_capacity(_Vehicle(weight=None, volume=None, pallet=None)) == [
        "tải trọng", "thể tích", "số pallet"
    ]


# --------------------------------------------------------------------------
# Đơn hàng chưa khai hàng hóa
# --------------------------------------------------------------------------

def test_no_declared_cargo_is_reported_not_silently_accepted():
    """Cả ba con số bằng 0 gần như luôn nghĩa là "chưa ai điền".

    Phép kiểm năng lực lúc đó không kiểm được gì: mọi xe đều "vừa". Hàm này để
    chỗ gọi biết mà cảnh báo — cố ý KHÔNG tự chặn, vì chuyến chạy rỗng là có
    thật trong vận tải.
    """
    assert declares_no_cargo() is True
    assert declares_no_cargo(weight_kg=0, volume_m3=0, pallet_count=0) is True
    assert declares_no_cargo(weight_kg=None, volume_m3=None, pallet_count=None) is True
    assert declares_no_cargo(weight_kg=1) is False
    assert declares_no_cargo(volume_m3=0.5) is False
    assert declares_no_cargo(pallet_count=1) is False


def test_zero_cargo_passes_every_vehicle():
    """Ghi lại sự thật hiện tại: chưa khai hàng thì xe nào cũng lọt."""
    require_vehicle_capacity(_Vehicle(weight=1, volume=1, pallet=1), weight_kg=0, volume_m3=0, pallet_count=0)


# --------------------------------------------------------------------------
# Không được để phép kiểm bị viết lại lần hai
# --------------------------------------------------------------------------

def test_dispatch_service_does_not_duplicate_the_check():
    import inspect

    from services import tms_dispatch_service

    source = inspect.getsource(tms_dispatch_service)
    assert "require_vehicle_capacity(" in source, "điều phối phải dùng chính sách chung"
    assert "total_weight_kg > (vehicle.weight_capacity" not in source, (
        "phép kiểm năng lực không được viết lại bằng tay bên cạnh chính sách chung"
    )
