# -*- coding: utf-8 -*-
"""DomainError ném ở tầng route (ngoài khối try của lệnh) phải thành phong bì lỗi, không 500.

Đo được 11/09 khi gieo dữ liệu qua máy chủ thật: huỷ chuyến thiếu `Idempotency-Key`
→ máy chủ trả `500 Internal Server Error` trống, vì `_idempotency_key()` ném
DomainError trước khi vào `_trip_command`. Bộ kiểm cũ không thấy vì TestClient mặc
định ném lại ngoại lệ. Ở đây tắt `raise_server_exceptions` để đo đúng như người gọi
HTTP thấy.
"""
import importlib

from fastapi.testclient import TestClient

from conftest import API_TEST_HEADERS


def test_thieu_idempotency_key_khi_huy_chuyen_tra_422_co_ma(app_client):
    main = importlib.import_module("main")
    client = TestClient(main.app, raise_server_exceptions=False)
    r = client.post("/api/tms/trips/TRIP-KHONG-CO/cancel",
                    json={"expected_version": 1, "reason": "thử"}, headers=API_TEST_HEADERS)
    assert r.status_code == 422, r.text
    than = r.json()
    assert than["detail"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert than["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert "Idempotency-Key" in than["detail"]["message"]
