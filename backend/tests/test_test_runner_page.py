from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_test_runner_page_is_available_from_backend():
    response = client.get("/test-runner")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "5,000" in response.text or "5000" in response.text
    assert "kịch bản" in response.text.lower()
    assert "Kiểm thử API, không thay thế kiểm thử giao diện" in response.text


def test_test_runner_page_has_friendly_alias():
    response = client.get("/kich-ban-test")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "kịch bản" in response.text.lower()
    assert "Kiểm thử API, không thay thế kiểm thử giao diện" in response.text
