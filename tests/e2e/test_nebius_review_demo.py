from fastapi.testclient import TestClient

from scripts import nebius_review_demo


def test_synthetic_review_uses_fixed_fixture_and_nebius_summary(monkeypatch):
    calls = []
    monkeypatch.setattr(nebius_review_demo, "summarize_synthetic_visit",
                        lambda count: calls.append(count) or "Three people need review.")
    with TestClient(nebius_review_demo.app) as client:
        assert "Simulated data only" in client.get("/").text
        response = client.post("/demo", json={"name": "ignored"})
    assert response.status_code == 200
    result = response.json()
    assert calls == [3]
    assert result["member_denied"] is True
    assert result["decision"]["person"]["review_state"] == "confirmed"
    assert result["summary"] == "Three people need review."


def test_nebius_error_is_safe_to_display(monkeypatch):
    def fail(_count):
        raise nebius_review_demo.NebiusDemoError("private diagnostic")

    monkeypatch.setattr(nebius_review_demo, "summarize_synthetic_visit", fail)
    with TestClient(nebius_review_demo.app) as client:
        response = client.post("/demo")
    assert response.status_code == 503
    assert "private diagnostic" not in response.text


def test_untrusted_browser_origin_cannot_trigger_inference(monkeypatch):
    def fail(_count):
        raise AssertionError("inference must not run")

    monkeypatch.setattr(nebius_review_demo, "summarize_synthetic_visit", fail)
    with TestClient(nebius_review_demo.app) as client:
        response = client.post("/demo", headers={"Origin": "https://example.com"})
    assert response.status_code == 403
