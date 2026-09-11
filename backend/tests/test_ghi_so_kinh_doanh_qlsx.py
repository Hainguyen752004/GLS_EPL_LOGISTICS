# -*- coding: utf-8 -*-
"""GHI SỔ KINH DOANH — đẩy DO đã giao sang QLSX (hệ công nợ của anh Khang) tạo đơn hàng bán.

Hợp đồng: `docs/logistics-sales-orders-api-guide.md`. Bài này KHÔNG gọi QLSX thật (không có
token trong bộ kiểm, và gọi thật là ghi chứng từ thật) — thay `goi_qlsx` bằng hàm giả có kịch
bản, rồi khoá những điều hợp đồng đòi mà mã mình phải giữ:

1. Body đúng BA khoá gốc, `status = delivered`, tiền là số, tổng khớp CHÍNH XÁC.
2. 201 → synced, lưu mã SO / công nợ; bấm lần hai KHÔNG gọi QLSX nữa (trả kết quả cũ).
3. HTTP 200 nhưng thân `Success: false, Code: 401` → là LỖI. Đo được trên máy chủ thật 11/09:
   lớp xác thực QLSX bọc lỗi trong phong bì 200.
4. Gửi lại sau lỗi dùng CÙNG Idempotency-Key và CÙNG body đã lưu — không dựng body mới.
5. 409 → conflict, không tự gửi lại.
6. Chặn tại chỗ, không gọi QLSX: tiền THB (QLSX chỉ nhận VND/LAK/USD), thiếu token.
"""
import datetime as dt
import importlib
import json
from decimal import Decimal

import pytest

from conftest import API_TEST_HEADERS


def _do_da_giao(db, models, ma, khach, tien, gia, phu=0):
    """Một DO đã giao có hồ sơ chốt giá — đúng đầu vào của bước bàn giao."""
    if db.get(models.Customer, khach) is None:
        db.add(models.Customer(id=khach, name=khach))
    db.add(models.DeliveryOrder(id=ma, customer_id=khach, route_id="RT-T1",
                                canonical_status="delivered", status="Đã giao"))
    db.flush()
    db.add(models.DeliveryOrderCloseout(
        id="CLO-" + ma, do_id=ma, base_selling_price_snapshot=gia, base_price_source="quotation",
        base_price_source_id="QT-" + ma, surcharge_total=phu, final_selling_price=gia + phu,
        currency_code=tien, completed_at=dt.datetime(2026, 9, 10, 8, tzinfo=dt.timezone.utc),
        completed_by="ops"))
    db.flush()    # khoá ngoại: dòng phụ thu trỏ vào hồ sơ chốt, hồ sơ phải xuống DB trước
    if phu:
        db.add(models.DeliveryOrderChargeAdjustment(
            id="ADJ-" + ma, closeout_id="CLO-" + ma, line_no=1, name="Phụ thu khách",
            original_amount=0, actual_amount=phu, increase_amount=phu, note="thử", created_by="ops"))


@pytest.fixture
def san(app_client, workflow_builder, monkeypatch):
    """Sân: một DO LAK, một DO USD có phụ thu, một DO THB; token QLSX giả; QLSX giả có kịch bản."""
    client, _, _ = app_client
    workflow_builder.master_data()
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    with database.SessionLocal() as db:
        _do_da_giao(db, models, "DO-GS-LAK", "DEMO-CUS-UNILEVER", "LAK", 2000000, 200000)
        _do_da_giao(db, models, "DO-GS-USD", "DEMO-CUS-UNILEVER", "USD", Decimal("100.25"), Decimal("5.5"))
        _do_da_giao(db, models, "DO-GS-THB", "DEMO-CUS-UNILEVER", "THB", 3000)
        db.commit()
    monkeypatch.setenv("QLSX_ACCESS_TOKEN", "token-thu")
    gs = importlib.import_module("services.ghi_so_kinh_doanh")
    nhat_ky = []

    def gia(body_json, key, goc=None, token=None):
        nhat_ky.append({"key": key, "body": body_json, "token": token})
        kich_ban = gia.kich_ban.pop(0) if gia.kich_ban else (201, {"replayed": False, "data": {
            "doId": json.loads(body_json)["header"]["do_id"], "orderId": 501, "orderCode": "SO-501",
            "orderStatus": "5", "retkAutoId": 601, "retkCode": "SALE-601",
            "itemCode": "DEMO-CUS-UNILEVER_RT-T1", "totalAmount": 2200000,
            "initialDebtAmount": 2200000, "currency": "LAK"}})
        ma, than = kich_ban
        return ma, than, json.dumps(than) if than is not None else ""
    gia.kich_ban = []
    monkeypatch.setattr(gs, "goi_qlsx", gia)
    return client, gia, nhat_ky


def test_xem_truoc_dung_body_dung_hop_dong(san):
    client, gia, nhat_ky = san
    r = client.post("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh?xem_truoc=1",
                    headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["xem_truoc"] is True and d["idempotency_key"] == "logistics:DO-GS-LAK"
    body = d["body"]
    # Ba khoá gốc, không hơn — hợp đồng nói rõ "không gửi nguyên envelope message/data".
    assert sorted(body) == ["details", "header", "schemaVersion"]
    assert body["schemaVersion"] == 1
    h = body["header"]
    assert h["status"] == "delivered" and h["currency"] == h["currency_thu"] == "LAK"
    assert h["customer_id"] == "DEMO-CUS-UNILEVER" and h["route"]["id"] == "RT-T1"
    # Tiền là SỐ, và cộng khớp chính xác.
    assert isinstance(h["selling_price"], (int, float)) and not isinstance(h["selling_price"], bool)
    assert h["selling_price"] + h["customer_surcharge_total"] == h["final_selling_price"] == 2200000
    thu = [x for x in body["details"] if x["kind"] == "thu"]
    assert thu and sum(Decimal(str(x["actual_amount"])) for x in thu) == Decimal(2200000)
    assert all(x["currency"] == "LAK" for x in thu)
    so = [x["line_no"] for x in body["details"]]
    assert len(so) == len(set(so)) and all(isinstance(n, int) and n > 0 for n in so)
    assert "ledger_totals" not in h, "object tổng nội bộ không thuộc hợp đồng"
    assert nhat_ky == [], "xem trước thì KHÔNG được gọi QLSX"


def test_ghi_so_thanh_cong_luu_ket_qua_va_lan_hai_khong_goi_lai(san):
    client, gia, nhat_ky = san
    r = client.post("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["da_ghi_so"] is True and d["status"] == "synced" and d["da_co_truoc"] is False
    assert d["order_code"] == "SO-501" and d["retk_code"] == "SALE-601"
    assert d["initial_debt_amount"] == 2200000 and d["currency"] == "LAK"
    assert "SO-501" in r.json()["message"]
    assert len(nhat_ky) == 1
    assert nhat_ky[0]["key"] == "logistics:DO-GS-LAK" and nhat_ky[0]["token"] == "token-thu"

    # Lần hai: đã synced → trả kết quả cũ, KHÔNG gọi QLSX. Bên đó không có API sửa/xoá.
    r2 = client.post("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r2.status_code == 200
    assert r2.json()["data"]["da_co_truoc"] is True and r2.json()["data"]["order_code"] == "SO-501"
    assert len(nhat_ky) == 1, "đã ghi sổ rồi mà vẫn gọi QLSX lần nữa"

    # Trạng thái hiện cả ở API riêng và trong gói closeout (màn hình đọc từ đây).
    assert client.get("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh",
                      headers=API_TEST_HEADERS).json()["data"]["order_code"] == "SO-501"
    co = client.get("/api/delivery-orders/DO-GS-LAK/closeout", headers=API_TEST_HEADERS).json()
    assert co["ghi_so_kinh_doanh"]["da_ghi_so"] is True


def test_http_200_nhung_Success_false_la_loi_va_gui_lai_dung_key_dung_body(san):
    """Đo trên máy chủ thật 11/09: chưa xác thực → HTTP 200, thân {Success:false, Code:401}."""
    client, gia, nhat_ky = san
    gia.kich_ban = [(200, {"Success": False, "Code": 401,
                           "Message": "Chưa đăng nhập hoặc chưa xác thực, không được truy cập!",
                           "Result": None})]
    r = client.post("/api/handover/delivery-orders/DO-GS-USD/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    loi = r.json()["error"]
    assert loi["code"] == "QLSX_401" and "xác thực" in loi["message"]
    tt = client.get("/api/handover/delivery-orders/DO-GS-USD/ghi-so-kinh-doanh", headers=API_TEST_HEADERS).json()["data"]
    assert tt["status"] == "failed" and tt["da_ghi_so"] is False and tt["attempts"] == 1
    assert tt["error_code"] == "QLSX_401"

    # Gửi lại: CÙNG key, CÙNG body — tài liệu: "Retry cùng key và body, không tạo key mới."
    r2 = client.post("/api/handover/delivery-orders/DO-GS-USD/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r2.status_code == 200, r2.text
    assert len(nhat_ky) == 2
    assert nhat_ky[0]["key"] == nhat_ky[1]["key"] == "logistics:DO-GS-USD"
    assert nhat_ky[0]["body"] == nhat_ky[1]["body"], "lần gửi lại phải dùng nguyên body đã lưu"
    h = json.loads(nhat_ky[1]["body"])["header"]
    # USD 100.25 + 5.5 = 105.75 — không mất phần lẻ, không thành chuỗi.
    assert h["selling_price"] == 100.25 and h["customer_surcharge_total"] == 5.5
    assert h["final_selling_price"] == 105.75
    assert client.get("/api/handover/delivery-orders/DO-GS-USD/ghi-so-kinh-doanh",
                      headers=API_TEST_HEADERS).json()["data"]["attempts"] == 2


def test_409_la_conflict_khong_tu_gui_lai(san):
    client, gia, nhat_ky = san
    gia.kich_ban = [(409, {"code": "LOGISTICS_52901", "message": "DO đã liên kết SO khác."})]
    r = client.post("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "LOGISTICS_52901"
    tt = client.get("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh", headers=API_TEST_HEADERS).json()["data"]
    assert tt["status"] == "conflict" and tt["da_ghi_so"] is False


def test_thb_bi_chan_tai_cho_khong_goi_qlsx(san):
    client, gia, nhat_ky = san
    r = client.post("/api/handover/delivery-orders/DO-GS-THB/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "GHI_SO_TIEN_TE_CHUA_HO_TRO"
    assert "THB" in r.json()["error"]["message"]
    assert nhat_ky == []


def test_thieu_token_thi_noi_ro_va_khong_goi(san, monkeypatch):
    client, gia, nhat_ky = san
    monkeypatch.delenv("QLSX_ACCESS_TOKEN", raising=False)
    r = client.post("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh", headers=API_TEST_HEADERS)
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] == "QLSX_TOKEN_CHUA_CAU_HINH"
    assert nhat_ky == []
    # Xem trước vẫn được dù chưa có token — để đối soát body với bên QLSX trước khi họ cấp token.
    assert client.post("/api/handover/delivery-orders/DO-GS-LAK/ghi-so-kinh-doanh?xem_truoc=1",
                       headers=API_TEST_HEADERS).status_code == 200


def test_dung_body_tu_choi_tong_lech_va_so_json_gon():
    gs = importlib.import_module("services.ghi_so_kinh_doanh")
    from services.errors import DomainError

    goi = {"header": {"do_id": "DO-X", "status": "delivered", "customer_id": "KH", "route": {"id": "RT"},
                      "currency": "VND", "currency_thu": "VND", "selling_price": 100,
                      "customer_surcharge_total": 0, "final_selling_price": 100},
           "details": [{"line_no": 1, "kind": "thu", "name": "Cước", "actual_amount": 90, "currency": "VND"}]}
    with pytest.raises(DomainError) as loi:
        gs.dung_body(goi)
    assert loi.value.code == "GHI_SO_TONG_THU_KHONG_KHOP"

    goi["details"][0]["actual_amount"] = 100
    body, tom_tat = gs.dung_body(goi)
    assert body["header"]["selling_price"] == 100 and isinstance(body["header"]["selling_price"], int)
    assert tom_tat["so_dong_thu"] == 1

    # Số JSON gọn: 1918000.0 → 1918000, 105.75 giữ nguyên, không đuôi .00000.
    assert gs._so_json(Decimal("1918000.00000")) == 1918000
    assert gs._so_json(Decimal("105.75000")) == 105.75

    # Phân loại phản hồi.
    assert gs.doc_ket_qua(200, {"Success": False, "Code": 401, "Message": "x"}, "")[0] == "failed"
    assert gs.doc_ket_qua(201, {"replayed": False, "data": {"orderId": 1}}, "")[0] == "synced"
    assert gs.doc_ket_qua(200, {"replayed": True, "data": {"orderId": 1}}, "")[0] == "synced"
    assert gs.doc_ket_qua(409, {"code": "LOGISTICS_52901"}, "")[0] == "conflict"
    assert gs.doc_ket_qua(502, None, "<html>bad gateway</html>")[0] == "failed"
