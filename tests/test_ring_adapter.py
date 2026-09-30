from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from knock_knock.adapters.camera.ring import (
    EnvironmentAccessTokenProvider,
    InMemoryRingOAuthTokenStore,
    RefreshingRingAccessTokenProvider,
    RingAdapterConfig,
    RingCameraAdapter,
    RingOAuthToken,
)
from knock_knock.domain.models import CameraEvent, CameraEventType
from knock_knock.ports.camera import (
    CameraAuthenticationError,
    CameraMediaError,
    CameraMediaUnavailableError,
    CameraRateLimitError,
)

WATERMARKED_BYTES = b"sanitized-ring-media-with-visible-watermark"


def _event(event_type: CameraEventType = CameraEventType.MOTION) -> CameraEvent:
    return CameraEvent(
        event_id=f"device-1_{event_type.value}_1786715596787",
        request_id=f"request-{event_type.value}",
        account_id="account-1",
        device_id="device-1",
        event_type=event_type,
        occurred_at=datetime.fromtimestamp(1786715596787 / 1000, tz=UTC),
        component_ids=("0",),
    )


def _adapter(
    client: httpx.AsyncClient,
    *,
    key: str = "test-key",
    max_attempts: int = 3,
    max_snapshot_bytes: int = 1024,
    sleep: Any = None,
) -> RingCameraAdapter:
    config = RingAdapterConfig(
        api_base_url="https://api.amazonvision.com",
        hmac_signing_key=key,
        max_attempts=max_attempts,
        max_snapshot_bytes=max_snapshot_bytes,
        allowed_media_host_suffixes=("media.example",),
    )
    kwargs = {} if sleep is None else {"sleep": sleep}
    return RingCameraAdapter(
        config,
        EnvironmentAccessTokenProvider("test-token"),
        client,
        **kwargs,
    )


def test_ring_hmac_verification_uses_raw_body() -> None:
    raw_body = b'{"data":{"type":"motion_detected"}}'
    signature = hmac.new(b"test-key", raw_body, hashlib.sha256).hexdigest()

    adapter = _adapter(httpx.AsyncClient())

    assert adapter.verify_webhook(raw_body, f"sha256={signature}")
    assert not adapter.verify_webhook(raw_body + b" ", f"sha256={signature}")


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        ("motion_detected", CameraEventType.MOTION),
        ("button_press", CameraEventType.DOORBELL),
    ],
)
def test_ring_supported_events_are_normalized(
    event_type: str,
    expected: CameraEventType,
) -> None:
    adapter = _adapter(httpx.AsyncClient())
    payload = {
        "meta": {
            "version": "1.1",
            "request_id": f"request-{event_type}",
            "account_id": "account-1",
        },
        "data": {
            "id": f"device-1_{event_type}_1786715596787",
            "type": event_type,
            "attributes": {
                "source": "device-1",
                "source_type": "devices",
                "timestamp": 1786715596787,
                "sub_type": "human" if event_type == "motion_detected" else None,
                "component_ids": ["0"],
            },
        },
    }

    event = adapter.parse_event(payload)

    assert event is not None
    assert event.event_type is expected
    assert event.device_id == "device-1"
    assert event.component_ids == ("0",)


def test_unrelated_ring_event_is_ignored() -> None:
    adapter = _adapter(httpx.AsyncClient())
    payload = {
        "meta": {"request_id": "request-1", "account_id": "account-1"},
        "data": {"type": "device_online", "attributes": {}},
    }

    assert adapter.parse_event(payload) is None


async def test_oauth_provider_refreshes_and_persists_rotated_token() -> None:
    now = datetime(2026, 9, 29, tzinfo=UTC)
    store = InMemoryRingOAuthTokenStore(
        {
            "account-1": RingOAuthToken(
                access_token="expired",
                refresh_token="refresh-old",
                expires_at=now - timedelta(seconds=1),
            )
        }
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://oauth.ring.com/oauth/token")
        assert b"refresh_token=refresh-old" in request.content
        assert b"client_secret=client-secret" in request.content
        return httpx.Response(
            200,
            json={
                "access_token": "access-new",
                "refresh_token": "refresh-new",
                "expires_in": 14400,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = RefreshingRingAccessTokenProvider(
            token_url="https://oauth.ring.com/oauth/token",
            client_id="client-id",
            client_secret="client-secret",
            store=store,
            client=client,
            clock=lambda: now,
        )

        assert await provider.get_access_token("account-1") == "access-new"

    stored = await store.load("account-1")
    assert stored is not None
    assert stored.refresh_token == "refresh-new"
    assert stored.expires_at == now + timedelta(seconds=14400)


async def test_oauth_provider_raises_typed_authentication_error() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(401))
    ) as client:
        provider = RefreshingRingAccessTokenProvider(
            token_url="https://oauth.ring.com/oauth/token",
            client_id="client-id",
            client_secret="client-secret",
            store=InMemoryRingOAuthTokenStore(
                {
                    "account-1": RingOAuthToken(
                        access_token="",
                        refresh_token="bad-refresh",
                        expires_at=datetime.fromtimestamp(0, tz=UTC),
                    )
                }
            ),
            client=client,
        )

        with pytest.raises(CameraAuthenticationError):
            await provider.get_access_token("account-1")


async def test_snapshot_redirect_preserves_watermarked_bytes_and_component() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(303, headers={"Location": "https://media.example/snapshot"})
        return httpx.Response(
            200,
            content=WATERMARKED_BYTES,
            headers={
                "Content-Type": "image/jpeg",
                "X-Media-Timestamp": "1786715596787",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        frame = await _adapter(client).fetch_frame(_event())

    assert frame.content == WATERMARKED_BYTES
    assert requests[0].headers["Authorization"] == "Bearer test-token"
    assert b'"components":[{"component_id":"0"}]' in requests[0].content
    assert requests[1].url == httpx.URL("https://media.example/snapshot")


async def test_clip_accepts_partial_content_and_preserves_watermarked_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/media/video/download")
        assert b'"duration":5000' in request.content
        return httpx.Response(
            206,
            content=WATERMARKED_BYTES,
            headers={
                "Content-Type": "video/mp4",
                "X-Media-Length": "3200",
                "X-Media-Timestamp": "1786715596787",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        clip = await _adapter(client).fetch_clip(_event(), duration_ms=5000)

    assert clip.content == WATERMARKED_BYTES
    assert clip.partial is True
    assert clip.actual_duration_ms == 3200


@pytest.mark.parametrize(
    ("first_status", "headers", "expected_delay"),
    [(429, {"Retry-After": "0.01"}, 0.01), (503, {}, 0.25)],
)
async def test_media_retries_transient_status_then_succeeds(
    first_status: int,
    headers: dict[str, str],
    expected_delay: float,
) -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(first_status, headers=headers)
        if request.method == "POST":
            return httpx.Response(303, headers={"Location": "https://media.example/snapshot"})
        return httpx.Response(200, content=WATERMARKED_BYTES)

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        frame = await _adapter(client, sleep=fake_sleep).fetch_frame(_event())

    assert frame.content == WATERMARKED_BYTES
    assert calls == 3
    assert sleeps == [expected_delay]


async def test_exhausted_rate_limit_is_typed() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, headers={"Retry-After": "3"})
    )

    async def no_sleep(seconds: float) -> None:
        del seconds

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(CameraRateLimitError) as raised:
            await _adapter(client, max_attempts=2, sleep=no_sleep).fetch_frame(_event())

    assert raised.value.retry_after_seconds == 3


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [(401, CameraAuthenticationError), (416, CameraMediaUnavailableError)],
)
async def test_media_statuses_map_to_typed_errors(
    status_code: int,
    error_type: type[Exception],
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status_code))
    ) as client:
        with pytest.raises(error_type):
            await _adapter(client).fetch_frame(_event())


async def test_untrusted_redirect_and_oversized_media_are_rejected() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                303,
                headers={"Location": "https://attacker.example/private"},
            )
        )
    ) as client:
        with pytest.raises(CameraMediaError, match="trusted HTTPS"):
            await _adapter(client).fetch_frame(_event())

    def oversized(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(303, headers={"Location": "https://media.example/snapshot"})
        return httpx.Response(200, content=b"x" * 11, headers={"Content-Length": "11"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(oversized)) as client:
        with pytest.raises(CameraMediaError, match="size limit"):
            await _adapter(client, max_snapshot_bytes=10).fetch_frame(_event())
