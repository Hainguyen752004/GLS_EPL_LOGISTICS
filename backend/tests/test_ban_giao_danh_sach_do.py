# -*- coding: utf-8 -*-
"""`GET /api/handover/delivery-orders` — DANH SÁCH DO đã hoàn tất cho bên công nợ.

Anh Khang cần hai API (ảnh chủ dự án gửi 11/09): "1 API danh sách DO" và "1 API header
và chi tiết DO". API thứ hai đã có; API này là danh sách: mỗi dòng là header rút gọn của
một DO đã `delivered`, có lọc theo khách / khoảng ngày hoàn tất và phân trang, để bên kia
quét rồi gọi API chi tiết theo từng `do_id`.
"""
import datetime as dt
import importlib

from conftest import API_TEST_HEADERS


def _closeout(db, models, ma, khach, tien, luc):
    db.add(models.Customer(id=khach, name=khach)) if db.get(models.Customer, khach) is None else None
    db.add(models.DeliveryOrder(id=ma, customer_id=khach, canonical_status="delivered", status="Đã giao"))
    db.flush()
    db.add(models.DeliveryOrderCloseout(
        id="CLO-" + ma, do_id=ma, base_selling_price_snapshot=tien, base_price_source="quotation",
        base_price_source_id="QT-" + ma, surcharge_total=0, final_selling_price=tien, currency_code="VND",
        completed_at=luc, completed_by="ops"))


def test_danh_sach_chi_gom_do_da_hoan_tat_loc_va_phan_trang(app_client, workflow_builder):
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _closeout(db, models, "DO-BG-A", "CUS-BG-1", 1_000_000, dt.datetime(2026, 9, 1, 8, tzinfo=dt.timezone.utc))
        _closeout(db, models, "DO-BG-B", "CUS-BG-1", 2_000_000, dt.datetime(2026, 9, 5, 8, tzinfo=dt.timezone.utc))
        _closeout(db, models, "DO-BG-C", "CUS-BG-2", 3_000_000, dt.datetime(2026, 9, 9, 8, tzinfo=dt.timezone.utc))
        # DO chua hoan tat: KHONG duoc xuat hien.
        db.add(models.DeliveryOrder(id="DO-BG-X", customer_id="CUS-BG-1", canonical_status="in_transit", status="Đang vận chuyển"))
        db.commit()

    r = client.get("/api/handover/delivery-orders", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    ma = [x["do_id"] for x in d["items"]]
    assert ma == ["DO-BG-C", "DO-BG-B", "DO-BG-A"]          # moi nhat truoc
    assert "DO-BG-X" not in ma and d["total"] == 3
    dong = d["items"][0]
    for k in ("do_id", "customer_id", "quotation_id", "final_selling_price", "currency", "completed_at", "detail_url"):
        assert k in dong, k
    assert dong["detail_url"].endswith("/api/handover/delivery-orders/DO-BG-C")

    r = client.get("/api/handover/delivery-orders?customer_id=CUS-BG-1&completed_from=2026-09-03",
                   headers=API_TEST_HEADERS)
    assert [x["do_id"] for x in r.json()["data"]["items"]] == ["DO-BG-B"]

    r = client.get("/api/handover/delivery-orders?page=2&page_size=2", headers=API_TEST_HEADERS)
    d = r.json()["data"]
    assert [x["do_id"] for x in d["items"]] == ["DO-BG-A"] and d["page"] == 2 and d["total"] == 3


def test_api_chi_tiet_tra_200_cho_do_da_hoan_tat_ca_vnd_va_ngoai_te(app_client, workflow_builder):
    """Đường THÀNH CÔNG của API header + chi tiết. Đo 11/09 trên 8001: sau khi đổi 83 handler sang
    `def`, `ban_giao_do` (còn async) vẫn `await get_delivery_order_closeout(...)` nay trả dict →
    TypeError → 500 cho MỌI DO. Bài cũ chỉ kiểm 404/409 nên lọt. Ở đây gọi thật qua HTTP, kèm DO
    ngoại tệ (LAK) để header mang đúng `currency`."""
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _closeout(db, models, "DO-BG-VND", "CUS-BG-9", 2_486_000, dt.datetime(2026, 9, 3, 3, tzinfo=dt.timezone.utc))
        db.add(models.Customer(id="CUS-BG-8", name="CUS-BG-8"))
        db.add(models.DeliveryOrder(id="DO-BG-LAK", customer_id="CUS-BG-8", canonical_status="delivered", status="Đã giao"))
        db.flush()
        db.add(models.DeliveryOrderCloseout(
            id="CLO-DO-BG-LAK", do_id="DO-BG-LAK", base_selling_price_snapshot=2_900_000, base_price_source="quotation",
            base_price_source_id="QT-LAK", surcharge_total=150_000, final_selling_price=3_050_000, currency_code="LAK",
            completed_at=dt.datetime(2026, 9, 9, 5, tzinfo=dt.timezone.utc), completed_by="ops"))
        db.commit()
    for ma, tien, gia in (("DO-BG-VND", "VND", 2_486_000.0), ("DO-BG-LAK", "LAK", 3_050_000.0)):
        r = client.get("/api/handover/delivery-orders/%s" % ma, headers=API_TEST_HEADERS)
        assert r.status_code == 200, (ma, r.status_code, r.text[:300])
        d = r.json()["data"]
        assert d["header"]["do_id"] == ma and d["header"]["currency"] == tien
        assert d["header"]["final_selling_price"] == gia
        assert isinstance(d["details"], list)
