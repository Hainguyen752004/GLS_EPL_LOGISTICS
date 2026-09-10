# -*- coding: utf-8 -*-
"""Huỷ DO phải ghi LÝ DO; DO đã huỷ thì xoá được.

Chủ dự án hỏi (10/09): *"khi huỷ báo giá hay DO gì đó thì có ghi nhận lại lý do
không"* và chốt *"đã huỷ thì cho phép xoá"*. Trước đó: báo giá có `close_reason`,
DO thì huỷ trắng — không tra lại được "vì sao". Khoá:

1. huỷ không lý do → 422 `CANCEL_REASON_REQUIRED`; có lý do → lưu `cancel_reason`,
   trả về trong bản ghi DO;
2. DO đã huỷ → DELETE được (trước chỉ cho `pending`); DO đang chạy vẫn bị chặn;
3. báo giá từ chối vẫn giữ `close_reason` (không hồi quy).
"""
from conftest import API_TEST_HEADERS


def _do_cho(client, workflow_builder, hau_to):
    workflow_builder.master_data()
    workflow_builder.quotation(f"QT-{hau_to}", approve=True)
    return workflow_builder.delivery_order(f"DO-{hau_to}", f"QT-{hau_to}", approve=True)


def test_huy_khong_ly_do_bi_chan_co_ly_do_thi_luu(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do_cho(client, workflow_builder, "LD1")
    r = client.put(f"/api/delivery-orders/{do_id}/status", json={"status": "cancelled"}, headers=API_TEST_HEADERS)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "CANCEL_REASON_REQUIRED", r.text
    r = client.put(f"/api/delivery-orders/{do_id}/status",
                   json={"status": "cancelled", "reason": "Khách dời sang tuần sau"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["canonical_status"] == "cancelled" and d["cancel_reason"] == "Khách dời sang tuần sau"


def test_do_da_huy_xoa_duoc_do_dang_cho_cung_xoa_duoc(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do_cho(client, workflow_builder, "LD2")
    client.put(f"/api/delivery-orders/{do_id}/status",
               json={"status": "cancelled", "reason": "Trùng lệnh"}, headers=API_TEST_HEADERS)
    r = client.delete(f"/api/delivery-orders/{do_id}", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    ds = client.get("/api/delivery-orders", headers=API_TEST_HEADERS).json()
    ds = (ds.get("items") or ds.get("data") or []) if isinstance(ds, dict) else ds   # goi phan trang {items,total,...}
    assert all(str(x.get("id")) != do_id for x in ds), "DO đã xoá vẫn còn trong danh sách"


def test_do_dang_chay_khong_xoa_duoc(app_client, workflow_builder):
    client, _, _ = app_client
    do_id = _do_cho(client, workflow_builder, "LD3")
    workflow_builder.dieu_phoi_qua_chuyen(do_id, ma_trip="TRIP-LD3")
    r = client.delete(f"/api/delivery-orders/{do_id}", headers=API_TEST_HEADERS)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "LOCKED_RECORD", r.text


def test_bao_gia_tu_choi_van_giu_ly_do(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-LD4", approve=True)
    r = client.post("/api/quotations/QT-LD4/send", json={}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    r = client.post("/api/quotations/QT-LD4/reject", json={"reason": "Khách chọn đối thủ"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    q = client.get("/api/quotations/QT-LD4/detail", headers=API_TEST_HEADERS).json()["data"]
    assert q["close_reason"] == "Khách chọn đối thủ"
