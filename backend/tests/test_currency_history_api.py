import pytest


def test_currency_save_tracks_approved_and_previous_rates(app_client):
    client, _, _ = app_client

    first = client.post("/api/currencies", json={"USD": 25450, "THB": 710, "LAK": 1.18})
    second = client.post("/api/currencies", json={"USD": 26173.5, "THB": 715, "LAK": 1.2})
    history = client.get("/api/currencies/history")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert history.status_code == 200, history.text
    usd = next(item for item in history.json()["currencies"] if item["code"] == "USD")
    assert usd["current_rate"] == pytest.approx(26173.5)
    assert usd["previous_rate"] == pytest.approx(25450)
    assert usd["change"] == pytest.approx(723.5)
    assert usd["change_percent"] == pytest.approx(723.5 / 25450 * 100)
    assert usd["source"] == "APPROVED_UI"
    assert [row["rate"] for row in usd["history"][:2]] == pytest.approx([26173.5, 25450])


def test_currency_save_rejects_invalid_payload_atomically(app_client):
    client, _, _ = app_client

    assert client.post("/api/currencies", json={"USD": 25450, "THB": 710, "LAK": 1.18}).status_code == 200
    invalid = client.post("/api/currencies", json={"USD": 26000, "THB": 0, "LAK": 1.2})

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_EXCHANGE_RATE"
    current = {row["id"]: row["exchange_rate"] for row in client.get("/api/currencies").json()}
    assert current == pytest.approx({"USD": 25450, "THB": 710, "LAK": 1.18})
