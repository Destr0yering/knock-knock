from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from time import perf_counter

import httpx
import pytest
from fastapi.testclient import TestClient

import knock_knock.api.main as main_module
from knock_knock.adapters.camera.ring import (
    EnvironmentAccessTokenProvider,
    RingAdapterConfig,
    RingCameraAdapter,
)
from knock_knock.infrastructure.config import Settings
from knock_knock.infrastructure.container import build_container as real_build_container

FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "ring"
HMAC_KEY = "contract-test-hmac-key"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    settings = Settings(
        camera_backend="simulator",
        vision_backend="stub",
        ring_hmac_signing_key=HMAC_KEY,
        profile_config_path=tmp_path / "known_faces.yaml",
        visitor_log_path=tmp_path / "visitors.jsonl",
        shared_state_path=tmp_path / "household-state.json",
    )

    def build_test_container(resolved: Settings):
        container = real_build_container(resolved)
        ring_client = httpx.AsyncClient()
        container.camera = RingCameraAdapter(
            RingAdapterConfig(
                api_base_url="https://api.amazonvision.com",
                hmac_signing_key=HMAC_KEY,
            ),
            EnvironmentAccessTokenProvider("contract-test-token"),
            ring_client,
        )
        container.http_client = ring_client
        return container

    monkeypatch.setattr(main_module, "build_container", build_test_container)
    return TestClient(main_module.create_app(settings))


@pytest.mark.parametrize("fixture_name", ["motion-v1.1.json", "button-press-v1.1.json"])
def test_sanitized_official_payload_is_accepted_within_five_seconds(
    client: TestClient,
    fixture_name: str,
) -> None:
    raw_body = (FIXTURE_DIR / fixture_name).read_bytes()
    signature = hmac.new(HMAC_KEY.encode(), raw_body, hashlib.sha256).hexdigest()

    with client:
        started = perf_counter()
        response = client.post(
            "/v1/webhooks/ring",
            content=raw_body,
            headers={"X-Signature": signature},
        )
        elapsed = perf_counter() - started

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert elapsed < 5.0


def test_invalid_signature_fails_before_invalid_json_is_parsed(client: TestClient) -> None:
    with client:
        response = client.post(
            "/v1/webhooks/ring",
            content=b"this-is-not-json",
            headers={"X-Signature": "not-valid"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid Ring webhook signature"


def test_duplicate_request_is_acknowledged_without_reprocessing(client: TestClient) -> None:
    raw_body = (FIXTURE_DIR / "motion-v1.1.json").read_bytes()
    signature = hmac.new(HMAC_KEY.encode(), raw_body, hashlib.sha256).hexdigest()

    with client:
        first = client.post(
            "/v1/webhooks/ring",
            content=raw_body,
            headers={"X-Signature": signature},
        )
        second = client.post(
            "/v1/webhooks/ring",
            content=raw_body,
            headers={"X-Signature": signature},
        )

    assert first.json()["status"] == "accepted"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
