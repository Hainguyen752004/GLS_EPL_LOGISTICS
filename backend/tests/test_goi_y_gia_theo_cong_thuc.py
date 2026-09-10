# -*- coding: utf-8 -*-
"""Dòng THU của công thức loại xe ("Cước phí vận chuyển /kg") là MỐC GỢI Ý giá.

Chủ dự án hỏi (10/09) dòng 25,65 triệu trong bảng "5. Cước và giá thành" đi đâu:
trước đây nó không đi đâu cả — không cộng vào giá thành, không thành cước, chỉ
để xem. Chốt: theo cơ chế biểu cước ngành vận tải, dòng thu = đơn giá × số lượng
là mốc gợi ý "Theo công thức" đứng đầu; người bán bấm thì điền, không bấm thì
không con số nào tự chảy vào báo giá. Ba điều khoá:
1. có dòng thu → `goi_y_gia.theo_cong_thuc.gia` = tổng dòng thu (làm tròn nghìn);
2. giá thành KHÔNG đổi vì dòng thu (vẫn chỉ cộng dòng chi);
3. không có dòng thu → không có mốc này (không bịa).
"""
import importlib

from conftest import API_TEST_HEADERS


def _du_lieu_goc(workflow_builder):
    """Loai xe rieng (du tai 15 tan) va tuyen RT-T1 co so km — nhung thu xem-truoc-gia doi."""
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        if db.get(models.VehicleType, "VT-GY") is None:
            db.add(models.VehicleType(id="VT-GY", name="Xe tải 20 tấn", max_weight=20000,
                                      volume_capacity_m3=60, pallet_capacity=24))
        tuyen = db.get(models.Route, "RT-T1")
        tuyen.distance_km = 100
        tuyen.segments_json = '[{"origin": "Kho A", "destination": "Kho B", "distance_km": 100}]'
        db.commit()


def _cong_thuc(client, loai, co_thu=True):
    terms = [
        {"key": "fuel", "label": "Chi phí xăng dầu /km", "kind": "cost", "factor": "per_km", "rate": 5000},
        {"key": "driver", "label": "Phụ cấp chuyến tài xế", "kind": "cost", "factor": "per_trip", "rate": 400000},
    ]
    if co_thu:
        terms.append({"key": "rate", "label": "Cước phí vận chuyển /kg", "kind": "revenue", "factor": "per_kg", "rate": 1200})
    r = client.post("/api/cost-formulas", json={"vehicle_type_id": loai, "currency": "VND", "terms": terms},
                    headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text


def _xem_truoc(client, loai, kg=15000):
    r = client.post("/api/quotations/price-preview", json={
        "route_id": "RT-T1", "vehicle_type_id": loai, "weight_kg": kg, "volume_m3": 10, "pallet_count": 5,
    }, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    return r.json()["data"] if "data" in r.json() else r.json()


def test_dong_thu_thanh_moc_goi_y_va_khong_cong_vao_gia_thanh(app_client, workflow_builder):
    client, _, _ = app_client
    _du_lieu_goc(workflow_builder)
    _cong_thuc(client, "VT-GY", co_thu=True)
    xt = _xem_truoc(client, "VT-GY", kg=15000)
    assert xt["tinh_duoc"] is True, xt.get("viec_con_thieu")
    thu = [d for d in xt["cac_dong"] if d["loai"] == "thu"]
    chi = [d for d in xt["cac_dong"] if d["loai"] == "chi"]
    assert thu and chi
    assert abs(xt["gia_thanh"] - sum(d["thanh_tien"] for d in chi)) < 1  # gia thanh chi cong dong chi
    moc = xt["goi_y_gia"]["theo_cong_thuc"]
    assert moc["gia"] == 18_000_000  # 1.200 d/kg x 15.000 kg
    assert "Cước phí vận chuyển /kg" in moc["mo_ta"]


def test_khong_co_dong_thu_thi_khong_co_moc(app_client, workflow_builder):
    client, _, _ = app_client
    _du_lieu_goc(workflow_builder)
    _cong_thuc(client, "VT-GY", co_thu=False)
    xt = _xem_truoc(client, "VT-GY")
    assert xt["tinh_duoc"] is True, xt.get("viec_con_thieu")
    assert "theo_cong_thuc" not in xt["goi_y_gia"]
    assert "bien_muc_tieu" in xt["goi_y_gia"]  # moc cu van con
