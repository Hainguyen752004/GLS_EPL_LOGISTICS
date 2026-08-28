def test_domain_errors_use_canonical_error_envelope(app_client):
    client, _, _ = app_client
    response = client.get("/api/tracking/DO-NOT-FOUND")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "TRACKING_NOT_FOUND",
        "message": "Chưa có dữ liệu GPS cho lệnh giao hàng DO-NOT-FOUND. Vui lòng điều phối xe hoặc cập nhật thiết bị GPS trước.",
        "fields": [],
        "links": ["dispatch", "master-data/vehicles"],
    }


def test_validation_errors_identify_rejected_fields(app_client):
    client, _, _ = app_client
    response = client.post("/api/delivery-orders", json={"so_id": "SO-X", "approved": True})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Dữ liệu gửi lên không hợp lệ."
    assert "body.approved" in error["fields"]
    assert error["links"] == []
