from __future__ import annotations

import asyncio
import hashlib
import hmac
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from knock_knock.adapters.camera.payloads import parse_ring_event
from knock_knock.domain.models import CameraEvent, MediaClip, MediaFrame
from knock_knock.ports.camera import (
    AccessTokenProvider,
    CameraAdapter,
    CameraAuthenticationError,
    CameraMediaError,
    CameraMediaUnavailableError,
    CameraRateLimitError,
)

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class RingAdapterConfig:
    api_base_url: str
    hmac_signing_key: str
    request_timeout_seconds: float = 15.0
    max_attempts: int = 3
    max_retry_after_seconds: float = 5.0
    max_snapshot_bytes: int = 12 * 1024 * 1024
    max_clip_bytes: int = 80 * 1024 * 1024
    max_clip_duration_ms: int = 30_000
    allowed_media_host_suffixes: tuple[str, ...] = (
        "amazonvision.com",
        "amazonaws.com",
        "ring.com",
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if not 1 <= self.max_clip_duration_ms <= 900_000:
            raise ValueError("max_clip_duration_ms must be between 1 and 900000")


@dataclass(frozen=True, slots=True)
class RingOAuthToken:
    access_token: str
    refresh_token: str
    expires_at: datetime


class RingOAuthTokenStore(Protocol):
    """Persistence boundary; production implementations must encrypt tokens at rest."""

    async def load(self, account_id: str) -> RingOAuthToken | None: ...

    async def save(self, account_id: str, token: RingOAuthToken) -> None: ...


class InMemoryRingOAuthTokenStore:
    """Local/staging store. Process-local by design; never a production token database."""

    def __init__(self, initial: Mapping[str, RingOAuthToken] | None = None) -> None:
        self._tokens = dict(initial or {})
        self._lock = asyncio.Lock()

    async def load(self, account_id: str) -> RingOAuthToken | None:
        async with self._lock:
            return self._tokens.get(account_id)

    async def save(self, account_id: str, token: RingOAuthToken) -> None:
        async with self._lock:
            self._tokens[account_id] = token


class RefreshingRingAccessTokenProvider(AccessTokenProvider):
    """Returns valid per-account tokens and persists refresh-token rotation."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        store: RingOAuthTokenStore,
        client: httpx.AsyncClient,
        timeout_seconds: float = 15.0,
        refresh_skew_seconds: int = 60,
        clock: Clock | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._store = store
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._refresh_skew = timedelta(seconds=refresh_skew_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._refresh_lock = asyncio.Lock()

    async def get_access_token(self, account_id: str) -> str:
        token = await self._store.load(account_id)
        if token is None:
            raise CameraAuthenticationError("No Ring OAuth token exists for this account")
        if token.access_token and token.expires_at > self._clock() + self._refresh_skew:
            return token.access_token

        async with self._refresh_lock:
            token = await self._store.load(account_id)
            if token is None:
                raise CameraAuthenticationError("No Ring OAuth token exists for this account")
            if token.access_token and token.expires_at > self._clock() + self._refresh_skew:
                return token.access_token
            if not token.refresh_token or not self._client_id or not self._client_secret:
                raise CameraAuthenticationError("Ring OAuth refresh credentials are incomplete")

            try:
                response = await self._client.post(
                    self._token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": token.refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                    timeout=self._timeout_seconds,
                )
            except httpx.HTTPError as exc:
                raise CameraAuthenticationError("Ring OAuth refresh request failed") from exc
            if response.status_code == 429:
                raise CameraRateLimitError(
                    "Ring OAuth refresh was rate limited",
                    retry_after_seconds=_retry_after(response),
                )
            if response.status_code in {400, 401, 403}:
                raise CameraAuthenticationError("Ring OAuth refresh token was rejected")
            if response.status_code >= 400:
                raise CameraAuthenticationError(
                    f"Ring OAuth refresh returned HTTP {response.status_code}"
                )
            try:
                body = response.json()
                access_token = str(body["access_token"])
                refresh_token = str(body.get("refresh_token") or token.refresh_token)
                expires_in = int(body["expires_in"])
            except (KeyError, TypeError, ValueError) as exc:
                raise CameraAuthenticationError("Ring OAuth refresh response was invalid") from exc
            if not access_token or expires_in <= 0:
                raise CameraAuthenticationError("Ring OAuth refresh response was incomplete")

            refreshed = RingOAuthToken(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=self._clock() + timedelta(seconds=expires_in),
            )
            await self._store.save(account_id, refreshed)
            return refreshed.access_token


class EnvironmentAccessTokenProvider(AccessTokenProvider):
    """Development-only static token source; never use for multi-user production."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    async def get_access_token(self, account_id: str) -> str:
        del account_id
        if not self._access_token:
            raise CameraAuthenticationError("No Ring access token is configured")
        return self._access_token


class RingCameraAdapter(CameraAdapter):
    name = "ring-partner-api"

    def __init__(
        self,
        config: RingAdapterConfig,
        token_provider: AccessTokenProvider,
        client: httpx.AsyncClient,
        *,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._config = config
        self._token_provider = token_provider
        self._client = client
        self._sleep = sleep

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature or not self._config.hmac_signing_key:
            return False
        received = signature.removeprefix("sha256=").strip()
        expected = hmac.new(
            self._config.hmac_signing_key.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, received)

    def parse_event(self, payload: Mapping[str, Any]) -> CameraEvent | None:
        return parse_ring_event(payload)

    async def fetch_frame(self, event: CameraEvent) -> MediaFrame:
        payload: dict[str, Any] = {
            "type": "at_timestamp",
            "timestamp": int(event.occurred_at.timestamp() * 1000),
            "image_options": {
                "format": "jpeg",
                "resolution": {"width": 1920, "height": 1080},
            },
        }
        _add_component(payload, event)
        response = await self._download_media(
            event,
            endpoint="image/download",
            payload=payload,
            accepted_statuses={200},
            max_bytes=self._config.max_snapshot_bytes,
            media_name="snapshot",
        )
        return MediaFrame(
            content=response.content,
            content_type=response.headers.get("Content-Type", "image/jpeg"),
            captured_at=_media_timestamp(response, event.occurred_at),
            source_event_id=event.event_id,
            device_id=event.device_id,
        )

    async def fetch_clip(self, event: CameraEvent, *, duration_ms: int = 10_000) -> MediaClip:
        if not 1 <= duration_ms <= self._config.max_clip_duration_ms:
            raise ValueError(
                f"duration_ms must be between 1 and {self._config.max_clip_duration_ms}"
            )
        payload: dict[str, Any] = {
            "timestamp": int(event.occurred_at.timestamp() * 1000),
            "duration": duration_ms,
            "video_options": {
                "codec": "avc",
                "frame_rate": 15,
                "resolution": {"width": 1280, "height": 720},
            },
            "audio_options": {"audio_enabled": False},
        }
        _add_component(payload, event)
        response = await self._download_media(
            event,
            endpoint="video/download",
            payload=payload,
            accepted_statuses={200, 206},
            max_bytes=self._config.max_clip_bytes,
            media_name="clip",
        )
        actual_duration = response.headers.get("X-Media-Length")
        return MediaClip(
            content=response.content,
            content_type=response.headers.get("Content-Type", "video/mp4"),
            captured_at=_media_timestamp(response, event.occurred_at),
            source_event_id=event.event_id,
            device_id=event.device_id,
            requested_duration_ms=duration_ms,
            actual_duration_ms=int(actual_duration) if actual_duration else None,
            partial=response.status_code == 206,
        )

    async def _download_media(
        self,
        event: CameraEvent,
        *,
        endpoint: str,
        payload: Mapping[str, Any],
        accepted_statuses: set[int],
        max_bytes: int,
        media_name: str,
    ) -> httpx.Response:
        token = await self._token_provider.get_access_token(event.account_id)
        url = (
            f"{self._config.api_base_url.rstrip('/')}"
            f"/v1/devices/{event.device_id}/media/{endpoint}"
        )
        response = await self._request_with_backoff(
            "POST",
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location or not self._is_trusted_media_url(location):
                raise CameraMediaError(
                    f"Ring {media_name} response did not include a trusted HTTPS location"
                )
            response = await self._request_with_backoff("GET", location)

        self._raise_for_status(response, media_name, accepted_statuses)
        _enforce_media_size(response, max_bytes, media_name)
        return response

    async def _request_with_backoff(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self._config.max_attempts):
            try:
                response = await self._client.request(
                    method,
                    url,
                    follow_redirects=False,
                    timeout=self._config.request_timeout_seconds,
                    **kwargs,
                )
            except httpx.HTTPError as exc:
                if attempt + 1 == self._config.max_attempts:
                    raise CameraMediaError("Ring media request failed") from exc
            else:
                last_response = response
                if response.status_code not in {429, 500, 502, 503, 504}:
                    return response
            if attempt + 1 < self._config.max_attempts:
                retry_after = _retry_after(last_response) if last_response is not None else None
                delay = retry_after if retry_after is not None else 0.25 * (2**attempt)
                await self._sleep(min(delay, self._config.max_retry_after_seconds))
        if last_response is None:
            raise CameraMediaError("Ring media request failed without a response")
        return last_response

    def _raise_for_status(
        self,
        response: httpx.Response,
        media_name: str,
        accepted_statuses: set[int],
    ) -> None:
        if response.status_code in accepted_statuses:
            return
        if response.status_code in {401, 403}:
            raise CameraAuthenticationError(f"Ring {media_name} request was not authorized")
        if response.status_code == 429:
            raise CameraRateLimitError(
                f"Ring {media_name} request exhausted rate-limit retries",
                retry_after_seconds=_retry_after(response),
            )
        if response.status_code in {404, 410, 416}:
            raise CameraMediaUnavailableError(
                f"Ring {media_name} is not available (HTTP {response.status_code})"
            )
        raise CameraMediaError(f"Ring {media_name} request returned HTTP {response.status_code}")

    def _is_trusted_media_url(self, location: str) -> bool:
        parsed = urlparse(location)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().rstrip(".")
        return any(
            host == suffix or host.endswith(f".{suffix}")
            for suffix in self._config.allowed_media_host_suffixes
        )


def _add_component(payload: dict[str, Any], event: CameraEvent) -> None:
    if event.component_ids:
        payload["components"] = [{"component_id": event.component_ids[0]}]


def _retry_after(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _enforce_media_size(response: httpx.Response, max_bytes: int, media_name: str) -> None:
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                raise CameraMediaError(f"Ring {media_name} exceeds the configured size limit")
        except ValueError:
            pass
    if len(response.content) > max_bytes:
        raise CameraMediaError(f"Ring {media_name} exceeds the configured size limit")


def _media_timestamp(response: httpx.Response, fallback: datetime) -> datetime:
    value = response.headers.get("X-Media-Timestamp")
    if value is None:
        return fallback
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (ValueError, OSError):
        return fallback
