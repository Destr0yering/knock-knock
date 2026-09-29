from __future__ import annotations

import hashlib
import hmac

import httpx

from knock_knock.adapters.camera.ring import (
    EnvironmentAccessTokenProvider,
    RingAdapterConfig,
    RingCameraAdapter,
)
from knock_knock.domain.models import CameraEventType


def _adapter(key: str = "test-key") -> RingCameraAdapter:
    return RingCameraAdapter(
        RingAdapterConfig(api_base_url="https://api.amazonvision.com", hmac_signing_key=key),
        EnvironmentAccessTokenProvider("test-token"),
        httpx.AsyncClient(),
    )


def test_ring_hmac_verification_uses_raw_body() -> None:
    raw_body = b'{"data":{"type":"motion_detected"}}'
    signature = hmac.new(b"test-key", raw_body, hashlib.sha256).hexdigest()

    adapter = _adapter()

    assert adapter.verify_webhook(raw_body, f"sha256={signature}")
    assert not adapter.verify_webhook(raw_body + b" ", f"sha256={signature}")


def test_ring_motion_event_is_normalized() -> None:
    adapter = _adapter()
    payload = {
        "meta": {
            "version": "1.1",
            "request_id": "request-1",
            "account_id": "account-1",
        },
        "data": {
            "id": "device-1_motion_1786715596787",
            "type": "motion_detected",
            "attributes": {
                "source": "device-1",
                "timestamp": 1786715596787,
                "sub_type": "human",
                "component_ids": ["0"],
            },
        },
    }

    event = adapter.parse_event(payload)

    assert event is not None
    assert event.event_type is CameraEventType.MOTION
    assert event.device_id == "device-1"
    assert event.component_ids == ("0",)


def test_unrelated_ring_event_is_ignored() -> None:
    adapter = _adapter()
    payload = {
        "meta": {"request_id": "request-1", "account_id": "account-1"},
        "data": {"type": "device_online", "attributes": {}},
    }

    assert adapter.parse_event(payload) is None

