# -*- coding: utf-8 -*-
"""DO đã huỷ phải ra khỏi hàng đợi điều phối, không bị đo hạn giao nữa.

LỖI ĐO ĐƯỢC TRÊN DỮ LIỆU THẬT của bộ demo: một DO khách đã huỷ vẫn hiện ở tab
"Gần trễ" của màn Lệnh giao hàng. Nhánh cuối của hàm phân loại coi mọi trạng
thái không phải đã-giao / đang-chạy là "chờ vận chuyển" rồi so hạn lấy/giao của
nó với hiện tại — nên một đơn đã chết vẫn báo sắp trễ, và người điều phối thấy
một việc không có gì để làm.

Rổ đúng là một rổ RIÊNG (`cancelled`), xếp cuối thang cấp bách.
"""
import datetime as dt

from conftest import API_TEST_HEADERS


def _phan_tich(client):
    tra = client.get("/api/delivery-orders/analysis")
    assert tra.status_code == 200, tra.text
    return tra.json()


def test_do_da_huy_vao_ro_rieng_khong_phai_gan_tre(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    workflow_builder.quotation("QT-HUY", total_cost=2_000_000, selling_price=3_000_000)
    r = client.put("/api/quotations/QT-HUY/items", json={"items": [
        {"line_no": 1, "name": "Cont hàng khô", "quantity": 2, "uom": "20'", "note": ""},
    ]}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    assert client.post("/api/quotations/QT-HUY/send", json={},
                       headers=API_TEST_HEADERS).status_code == 200

    # Khung giờ SẮP TỚI HẠN — đúng cái làm lộ ra lỗi: đơn đã huỷ mà vẫn "gần trễ".
    sap = (dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
           + dt.timedelta(hours=3)).replace(microsecond=0).isoformat()
    r = client.post("/api/quotations/QT-HUY/accept", json={"dos": [
        {"pickup_at": sap, "due_at": sap}, {"pickup_at": sap, "due_at": sap},
    ]}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    ds_do = r.json()["do_ids"]
    assert len(ds_do) == 2, r.text

    goi = _phan_tich(client)
    assert set(ds_do) <= set(goi["buckets"]["near_late"]["record_ids"]), goi["buckets"]

    # Huỷ MỘT DO.
    r = client.put("/api/delivery-orders/%s/status" % ds_do[0],
                   json={"status": "cancelled", "reason": "khách huỷ (kiểm)"}, headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text

    goi = _phan_tich(client)
    ro = goi["buckets"]
    assert "cancelled" in ro, "phải có rổ Đã huỷ: %s" % list(ro)
    assert ro["cancelled"]["label"] == "Đã huỷ"
    assert ds_do[0] in ro["cancelled"]["record_ids"], ro
    # Và nó KHÔNG còn ở bất kỳ rổ nào của hàng đợi điều phối.
    for ten in ("near_late", "overdue", "pending", "undated", "active", "completed"):
        assert ds_do[0] not in ro[ten]["record_ids"], "%s còn ở rổ %s" % (ds_do[0], ten)
    # DO còn lại vẫn nằm nguyên ở hàng đợi.
    assert ds_do[1] in ro["near_late"]["record_ids"], ro

    dong = {x["id"]: x for x in goi["records"]}
    assert dong[ds_do[0]]["stage"] == "cancelled"
    assert dong[ds_do[0]]["is_overdue"] is False
    assert dong[ds_do[0]]["is_near_late"] is False
    assert "đã huỷ" in dong[ds_do[0]]["reason"]
    # Thang cấp bách phải kể cả rổ mới, nếu không màn hình mở tab theo một
    # danh sách thiếu rổ.
    assert goi["urgency"][-1] == "cancelled", goi["urgency"]
