# -*- coding: utf-8 -*-
"""Chiết khấu trên báo giá (v050) — lưu được, đọc lại được, KHÔNG đổi giá cuối.

Chủ dự án chốt phiếu gửi khách phải in "giá gốc" và "giá gốc sau chiết khấu".
Quy ước: `unit_price`/`selling_price` vẫn là giá CUỐI (DO khoá giá, biên, hoá đơn
không đổi); `discount_percent` (0..1) chỉ để suy ngược giá gốc trên phiếu.
"""
from conftest import API_TEST_HEADERS


def test_moc_050_la_dau_chuoi():
    from migrations import runner, v050_chiet_khau_bao_gia
    assert v050_chiet_khau_bao_gia.VERSION in [m.VERSION for m in runner.MIGRATIONS]
    assert "ADD COLUMN IF NOT EXISTS discount_percent" in " ".join(
        v050_chiet_khau_bao_gia.statements("postgresql"))


def test_luu_va_doc_lai_chiet_khau_khong_doi_gia_cuoi(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-CK1", total_cost=2_000_000, selling_price=3_000_000)

    r = client.put("/api/quotations/QT-CK1", json={"discount_percent": 0.05, "unit_price": 3_000_000},
                   headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert abs(d["discount_percent"] - 0.05) < 1e-9
    assert d["unit_price"] == 3_000_000 and d["selling_price"] == 3_000_000  # gia cuoi giu nguyen

    r = client.get("/api/quotations/QT-CK1/detail", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert abs(r.json()["data"]["discount_percent"] - 0.05) < 1e-9

    # Khong chiet khau -> null, khong phai 0 (giao dien doc null la "de trong").
    r = client.put("/api/quotations/QT-CK1", json={"discount_percent": 0}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["discount_percent"] is None

    # Am -> 422 nhu moi so tien khac.
    r = client.put("/api/quotations/QT-CK1", json={"discount_percent": -1}, headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
