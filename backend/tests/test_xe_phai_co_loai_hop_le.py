# -*- coding: utf-8 -*-
"""`POST /api/vehicles`: `type` phai la MA loai xe co that khi danh muc da co.

LOI DA GAP TREN DU LIEU THAT: hai xe ghi "Container 20FT" (ten hien thi) thay
vi "DEMO-VT-20FT" (ma). Moi phep tra theo ma, nen hai xe do khong khop loai nao
— dieu phoi khong so duoc nang luc, gia thanh khong tim duoc cong thuc — va
khong co thong bao nao vi chuoi nao cung luu duoc. Bo gieo demo da phai co
rieng mot buoc "chuan lai" chi de sua viec nay.

Ba hanh vi:
  1. Danh muc con TRONG (dang dung du lieu goc) -> cho qua, giu nguyen chuoi.
  2. Gui TEN loai xe -> tu doi ve MA.
  3. Gui chuoi khong khop gi -> 422 kem danh muc de chon, khong luu.
"""
from conftest import API_TEST_HEADERS


def test_danh_muc_trong_thi_cho_qua(app_client):
    client, _, _ = app_client
    r = client.post("/api/vehicles", json={"id": "XE-TRONG", "type": "Xe tải"}, headers=API_TEST_HEADERS)
    assert r.status_code in (200, 201), r.text
    xe = next(x for x in client.get("/api/vehicles").json() if x["id"] == "XE-TRONG")
    assert xe["type"] == "Xe tải"


def test_gui_ten_thi_doi_ve_ma_gui_ma_la_thi_422(app_client):
    client, _, _ = app_client
    assert client.post("/api/vehicle-types", json={"id": "VT-20FT", "name": "Container 20FT", "maxWeight": 28000},
                       headers=API_TEST_HEADERS).status_code in (200, 201)

    # Ten -> ma.
    r = client.post("/api/vehicles", json={"id": "XE-TEN", "type": "container 20ft"}, headers=API_TEST_HEADERS)
    assert r.status_code in (200, 201), r.text
    xe = next(x for x in client.get("/api/vehicles").json() if x["id"] == "XE-TEN")
    assert xe["type"] == "VT-20FT"

    # Ma dung -> giu.
    r = client.post("/api/vehicles", json={"id": "XE-MA", "type": "VT-20FT"}, headers=API_TEST_HEADERS)
    assert r.status_code in (200, 201), r.text

    # Chuoi la -> 422, khong luu, va noi ro danh muc.
    r = client.post("/api/vehicles", json={"id": "XE-LA", "type": "Xe gì đó"}, headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    than = r.json()["detail"]
    assert than["code"] == "VEHICLE_TYPE_UNKNOWN"
    assert [t["id"] for t in than["vehicle_types"]] == ["VT-20FT"]
    assert all(x["id"] != "XE-LA" for x in client.get("/api/vehicles").json())
