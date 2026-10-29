import httpx
import pytest

from knock_knock.services.nebius_demo import NebiusDemoError, summarize_synthetic_visit


def test_sends_only_synthetic_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.tokenfactory.us-central1.nebius.com"
        assert b"nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B" in request.content
        assert b"3 people detected" in request.content
        assert b"Taylor" not in request.content
        return httpx.Response(200, json={"choices": [{"message": {"content": "Three visitors."}}]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert summarize_synthetic_visit(3, client) == "Three visitors."


def test_rejects_unresolved_credential_and_invalid_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_API_KEY", "{{resolve:secretsmanager:example}}")
    with pytest.raises(RuntimeError):
        summarize_synthetic_visit(3)
    with pytest.raises(ValueError):
        summarize_synthetic_visit(21)


def test_requires_nvidia_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("NEBIUS_MODEL", "other/model")
    with pytest.raises(ValueError, match="NVIDIA"):
        summarize_synthetic_visit(3)


@pytest.mark.parametrize("response", [
    httpx.Response(200, json={}),
    httpx.Response(200, json={"choices": [{"message": {"content": " "}}]}),
    httpx.Response(401, text="sensitive server response"),
])
def test_failures_do_not_expose_response_or_key(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> None:
    monkeypatch.setenv("NEBIUS_API_KEY", "secret-test-key")
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        with pytest.raises(NebiusDemoError) as error:
            summarize_synthetic_visit(3, client)
    assert "secret-test-key" not in str(error.value)
    assert "sensitive server response" not in str(error.value)
