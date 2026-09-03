import pytest


def test_reference_refresh_requires_provider_key(app_client, monkeypatch):
    client, _, _ = app_client

    monkeypatch.delenv("OPEN_EXCHANGE_RATES_APP_ID", raising=False)
    response = client.post("/api/currencies/reference-rates/refresh")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EXCHANGE_RATE_PROVIDER_NOT_CONFIGURED"


def test_reference_refresh_converts_usd_cross_rates_without_overwriting_approved_rates(
    app_client, monkeypatch
):
    client, _, _ = app_client
    import database
    from routes import currency_routes
    import models

    monkeypatch.setenv("OPEN_EXCHANGE_RATES_APP_ID", "test-key")
    provider_calls = []

    def provider_response(_app_id):
        provider_calls.append(_app_id)
        return {
            "timestamp": 1_777_000_000,
            "base": "USD",
            "rates": {"USD": 1, "VND": 25_000, "THB": 35, "LAK": 21_000},
        }

    # Phần tỷ giá đã chuyển từ main.py sang routes/currency_routes.py, nên
    # phải patch đúng module đang giữ hàm gọi nhà cung cấp.
    monkeypatch.setattr(
        currency_routes,
        "_request_open_exchange_rates",
        provider_response,
    )

    with database.SessionLocal() as db:
        db.merge(models.Currency(id="USD", exchange_rate=25_450))
        db.commit()

    refreshed = client.post("/api/currencies/reference-rates/refresh")
    refreshed_again = client.post("/api/currencies/reference-rates/refresh")
    cached = client.get("/api/currencies/reference-rates")

    assert refreshed.status_code == 200, refreshed.text
    assert cached.status_code == 200, cached.text
    payload = refreshed.json()
    assert payload["status"] == "ready"
    assert payload["provider"] == "openexchangerates.org"
    assert payload["rates"]["USD"] == pytest.approx(25_000)
    assert payload["rates"]["THB"] == pytest.approx(25_000 / 35)
    assert payload["rates"]["LAK"] == pytest.approx(25_000 / 21_000)
    assert payload["applied"] is False
    assert refreshed_again.status_code == 200
    assert len(provider_calls) == 1
    assert cached.json()["rates"] == payload["rates"]

    with database.SessionLocal() as db:
        assert db.get(models.Currency, "USD").exchange_rate == pytest.approx(25_450)


def test_reference_refresh_rejects_incomplete_provider_payload(app_client, monkeypatch):
    client, _, _ = app_client
    from routes import currency_routes

    monkeypatch.setenv("OPEN_EXCHANGE_RATES_APP_ID", "test-key")
    # Phần tỷ giá đã chuyển từ main.py sang routes/currency_routes.py, nên
    # phải patch đúng module đang giữ hàm gọi nhà cung cấp.
    monkeypatch.setattr(
        currency_routes,
        "_request_open_exchange_rates",
        lambda _app_id: {"base": "USD", "rates": {"USD": 1, "VND": 25_000}},
    )

    response = client.post("/api/currencies/reference-rates/refresh")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "EXCHANGE_RATE_PROVIDER_INVALID_RESPONSE"
