# -*- coding: utf-8 -*-
"""Khách chấp nhận báo giá → hệ thống SINH LỆNH GIAO HÀNG ngay, không qua SO.

Chủ dự án chốt: "cái DO kế thừa từ cái QT — gen tự động khi QT được duyệt hết".
Trước đây chấp nhận xong còn một bước tách tay; quên bước đó thì báo giá nằm ở
`accepted` mãi và màn Lệnh giao hàng trống. Ba điều phải đúng:

1. `POST /accept` trả `do_ids`, báo giá sang `split`, DO mang `quotation_id`,
   `so_id` trống, giá khoá theo báo giá.
2. Không truyền dòng thì số DO = tổng số lượng ở bảng Hàng hoá (1 DO = 1 cont).
3. Truyền `dos` thì dùng đúng các dòng đó (giờ lấy, số seal).
"""
from conftest import API_TEST_HEADERS


def _bao_gia(client, workflow_builder, ma, so_luong):
    workflow_builder.master_data()
    workflow_builder.quotation(ma, total_cost=2_000_000, selling_price=3_000_000)
    r = client.put("/api/quotations/%s/items" % ma, json={"items": [
        {"line_no": 1, "name": "Cont hàng khô", "quantity": so_luong, "uom": "20'", "note": ""},
    ]}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    r = client.post("/api/quotations/%s/send" % ma, json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text


def test_chap_nhan_sinh_do_theo_so_luong_hang_hoa(app_client, workflow_builder):
    client, _, _ = app_client
    _bao_gia(client, workflow_builder, "QT-SINH-DO", so_luong=3)

    r = client.post("/api/quotations/QT-SINH-DO/accept", json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    goi = r.json()
    assert len(goi["do_ids"]) == 3, goi
    assert goi["data"]["canonical_status"] == "split"
    assert len(goi["data"]["delivery_orders"]) == 3
    assert "sinh 3 lệnh giao hàng" in goi["message"]

    # DO kế thừa báo giá, không dính SO.
    r = client.get("/api/delivery-orders?page=1&page_size=50")
    assert r.status_code == 200, r.text
    ds = r.json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    cua_bao_gia = [d for d in ds if d["id"] in goi["do_ids"]]
    assert len(cua_bao_gia) == 3
    for d in cua_bao_gia:
        assert d["quotation_id"] == "QT-SINH-DO"
        assert d["canonical_status"] == "pending"
        assert float(d.get("unit_price") or 0) == float(goi["gia_moi_chuyen"])

    # Chấp nhận lần hai bị chặn — báo giá đã tách.
    r = client.post("/api/quotations/QT-SINH-DO/accept", json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text


def test_chap_nhan_voi_dong_tu_khai_giu_so_seal(app_client, workflow_builder):
    client, _, _ = app_client
    _bao_gia(client, workflow_builder, "QT-SINH-SEAL", so_luong=2)

    r = client.post("/api/quotations/QT-SINH-SEAL/accept", json={"dos": [
        {"pickup_at": "2026-12-01T07:00:00+07:00", "due_at": "2026-12-01T17:00:00+07:00",
         "seal_no": "SL-0001", "driver_note": "Gọi trước 30 phút"},
    ]}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    goi = r.json()
    # Truyền một dòng thì sinh MỘT DO, không phải hai — người dùng tự quyết.
    assert len(goi["do_ids"]) == 1, goi
    r = client.get("/api/delivery-orders?page=1&page_size=50")
    assert r.status_code == 200, r.text
    ds = r.json()
    ds = ds.get("items") if isinstance(ds, dict) else ds
    d = next(x for x in ds if x["id"] == goi["do_ids"][0])
    assert d.get("seal_no") == "SL-0001"
    assert d.get("driver_note") == "Gọi trước 30 phút"
