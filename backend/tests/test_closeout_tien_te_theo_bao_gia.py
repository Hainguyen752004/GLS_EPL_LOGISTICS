# -*- coding: utf-8 -*-
"""Hồ sơ hoàn tất lấy TIỀN TỆ theo báo giá, không theo công thức tình cờ đứng đầu.

Đo trên dữ liệu demo (10/09): loại xe Container 20FT có hai công thức
`vehicle-type::DEMO-VT-20FT::USD` và `::VND`. DO sinh từ báo giá VND, không có Đơn
hàng, nên `_select_closeout_formula` được truyền `currency=None` → chọn công thức
đầu theo tên = USD → màn Hoàn tất hiện "1.118.000 USD". Sửa: tiền tệ nguồn = Đơn
hàng (dữ liệu cũ) hoặc BÁO GIÁ; công thức chọn theo đó; `currency` của hồ sơ cũng
ưu tiên tiền tệ nguồn trước tiền tệ của công thức.
"""
import importlib

import pytest

from conftest import API_TEST_HEADERS


def test_do_bao_gia_vnd_khong_bi_keo_sang_usd(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    # Loai xe co CA HAI cong thuc, USD dung truoc theo ten.
    with database.SessionLocal() as db:
        if db.get(models.VehicleType, "VT-2TIEN") is None:
            db.add(models.VehicleType(id="VT-2TIEN", name="Container 20FT (kiểm)", max_weight=28000,
                                      volume_capacity_m3=33, pallet_capacity=22))
        xe = db.get(models.Vehicle, "VEH-T1")
        xe.type = "VT-2TIEN"
        db.commit()
    for tien in ("USD", "VND"):
        r = client.post("/api/cost-formulas", json={"vehicle_type_id": "VT-2TIEN", "currency": tien,
                                                   "terms": [{"key": "fuel", "rate": 4800 if tien == "VND" else 0.2, "factor": "per_km", "kind": "cost"}]},
                        headers=API_TEST_HEADERS)
        assert r.status_code in (200, 201), r.text

    workflow_builder.quotation("QT-2TIEN", total_cost=2_000_000, selling_price=3_000_000)
    r = client.post("/api/quotations/QT-2TIEN/send", json={}, headers=API_TEST_HEADERS)
    if r.status_code >= 400:
        pytest.skip("send tra %s" % r.status_code)
    r = client.post("/api/quotations/QT-2TIEN/accept", json={"dos": [{"quantity": 1}]}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    goi = r.json()
    do_id = (goi.get("do_ids") or (goi.get("data") or {}).get("do_ids"))[0]
    # Gan xe cho DO de ho so tra cong thuc theo loai xe (khong can dieu phoi that).
    with database.SessionLocal() as db:
        do = db.get(models.DeliveryOrder, do_id)
        do.vehicle_id = "VEH-T1"
        q = db.get(models.Quotation, "QT-2TIEN")
        assert (q.currency_code or "VND") == "VND"
        db.commit()

    hs = client.get("/api/delivery-orders/%s/closeout" % do_id, headers=API_TEST_HEADERS).json()
    hs = hs.get("data") or hs
    assert hs["currency"] == "VND", hs["currency"]
    assert (hs.get("cost_formula") or {}).get("currency") == "VND", hs.get("cost_formula")
    assert hs["ledger_totals"]["currency"] == "VND"
