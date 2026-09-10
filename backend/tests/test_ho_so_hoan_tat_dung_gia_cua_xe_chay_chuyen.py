# -*- coding: utf-8 -*-
"""Hồ sơ hoàn tất tính CHI PHÍ theo đơn giá của CHIẾC XE chạy chuyến.

Chủ dự án lo: *"những chiếc xe có thể có giá khác nhau"* — báo giá chọn LOẠI xe,
nhưng chiếc thật sự chạy có thể hao dầu hơn chuẩn của loại. Công thức hai tầng
đã lo việc này: loại xe giữ công thức, từng chiếc ghi đè vài con số
(`vehicle_cost_overrides`), và `_configured_delivery_cost_lines` áp phần ghi đè
khi lập dòng chi phí của hồ sơ. Đo trên dữ liệu demo (10/09): xe 129.03 ghi đè
dầu 7.728 đ/km → hồ sơ ghi `96,5 km × 7.728`, không phải 8.050 của loại.

Bài kiểm khoá ba điều, vì đây là đúng con số anh Khang lập phiếu chi:
  1. có ghi đè → dùng đơn giá của xe, `rate_source = "vehicle"`;
  2. không ghi đè → kế thừa loại xe, `rate_source = "vehicle_type"`;
  3. ghi đè chỉ đổi SỐ của đúng khoản đó — mã costindex và các khoản khác giữ nguyên.
"""
from decimal import Decimal
from types import SimpleNamespace

from routes.delivery_routes import _configured_delivery_cost_lines

CONG_THUC = {
    "id": "CT-20FT", "name": "Đầu kéo 20'", "currency": "VND", "components": {},
    "terms": [
        {"key": "fuel", "rate": "6,900", "factor": "per_km", "kind": "cost", "cost_index": "621-FUEL"},
        {"key": "driver", "rate": "600000", "factor": "per_trip", "kind": "cost", "cost_index": "622-DRV"},
        {"key": "rate", "rate": "1350", "factor": "per_kg", "kind": "revenue"},
    ],
}
TUYEN = SimpleNamespace(distance_km=Decimal("100"), segments_json="[]")
DO = SimpleNamespace(weight_kg=Decimal("19000"))


def _dong(ghi_de):
    ds = _configured_delivery_cost_lines(CONG_THUC, DO, TUYEN, ghi_de)
    return {d["key"]: d for d in ds}


def test_xe_co_ghi_de_thi_dong_chi_phi_lay_don_gia_cua_xe():
    d = _dong({"fuel": Decimal("7728")})
    assert d["fuel"]["unit_rate"] == 7728.0
    assert d["fuel"]["original_amount"] == 772800.0
    assert d["fuel"]["rate_source"] == "vehicle"
    assert "7.728" in d["fuel"]["calculation"]


def test_xe_khong_ghi_de_thi_ke_thua_loai_xe():
    d = _dong({})
    assert d["fuel"]["unit_rate"] == 6900.0 and d["fuel"]["rate_source"] == "vehicle_type"
    assert d["driver"]["original_amount"] == 600000.0


def test_ghi_de_chi_doi_so_cua_dung_khoan_do():
    d = _dong({"fuel": Decimal("7728")})
    assert d["fuel"]["cost_index"] == "621-FUEL", "mã costindex vẫn kế thừa từ loại xe"
    assert d["driver"]["unit_rate"] == 600000.0 and d["driver"]["rate_source"] == "vehicle_type"
    assert "rate" not in d, "cấu phần doanh thu không vào dòng chi"
