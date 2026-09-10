# -*- coding: utf-8 -*-
"""Hai duong cu cua bao gia phai noi cung mot cau voi duong moi.

Ra soat tron luong (docs/ra-soat-backend-tron-luong.md §9.4, §9.5) do duoc:

  · `PUT /api/quotations/{id}/approve` (va `PUT …/status`) duyet thang sang
    `approved` du bien duoi nguong — trong khi "Gui khach" thi giu lai o
    `pending_approval`. Mot bao gia bien 5 % co the duoc khach chap nhan va tach
    DO ma khong ai duyet noi bo.
  · `PUT /api/quotations/{id}` sua duoc bao gia dang `sent` ma van de `sent` —
    khach cam ban cu, he tach DO theo ban moi.
"""
from conftest import API_TEST_HEADERS, bao_gia_hop_le


def test_duyet_duong_cu_bien_mong_thi_ve_CHO_DUYET_NOI_BO(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    # Bien 5 %: tren gia thanh (khong lo) nhung duoi nguong 15 %.
    r = client.post("/api/quotations", json=bao_gia_hop_le(id="QT-MONG", total_cost=2_000_000, selling_price=2_100_000),
                    headers={"X-User-Id": "tester"})
    assert r.status_code == 200, r.text
    r = client.put("/api/quotations/QT-MONG/approve", headers={"X-User-Id": "tester"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["canonical_status"] == "pending_approval"
    # Va khach KHONG chap nhan duoc mot bao gia dang cho duyet noi bo.
    r = client.post("/api/quotations/QT-MONG/accept", json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text


def test_duyet_duong_cu_bien_du_thi_van_APPROVED(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    client.post("/api/quotations", json=bao_gia_hop_le(id="QT-DAY"), headers={"X-User-Id": "tester"})  # 33 %
    r = client.put("/api/quotations/QT-DAY/approve", headers={"X-User-Id": "tester"})
    assert r.status_code == 200 and r.json()["data"]["canonical_status"] == "approved", r.text


def test_sua_bao_gia_DA_GUI_thi_ve_nhap_va_phai_gui_lai(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    client.post("/api/quotations", json=bao_gia_hop_le(id="QT-SUA"), headers={"X-User-Id": "tester"})
    r = client.post("/api/quotations/QT-SUA/send", json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 200 and r.json()["data"]["canonical_status"] == "sent", r.text
    ma_khach_thay = r.json()["data"]["quote_no"]

    r = client.put("/api/quotations/QT-SUA", json={"selling_price": 3_300_000}, headers={"X-User-Id": "tester"})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["canonical_status"] == "draft", d
    # Chua gui lai thi khach KHONG chap nhan duoc ban moi.
    assert client.post("/api/quotations/QT-SUA/accept", json={}, headers=API_TEST_HEADERS).status_code == 409
    # Gui lai: ve `sent`, cung ma khach thay (van la cung mot bao gia voi khach).
    r = client.post("/api/quotations/QT-SUA/send", json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["canonical_status"] == "sent"
    assert r.json()["data"]["quote_no"] == ma_khach_thay
    assert float(r.json()["data"]["selling_price"]) == 3_300_000
