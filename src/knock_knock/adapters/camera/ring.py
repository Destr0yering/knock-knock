from __future__ import annotations

import asyncio
import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from knock_knock.adapters.camera.payloads import parse_ring_event
from knock_knock.domain.models import CameraEvent, MediaFrame
from knock_knock.ports.camera import (
    AccessTokenProvider,
    CameraAdapter,
    CameraMediaError,
)


@dataclass(frozen=True, slots=True)
class RingAdapterConfig:
    api_base_url: str
    hmac_signing_key: str
    request_timeout_seconds: float = 15.0
    max_attempts: int = 3


class EnvironmentAccessTokenProvider(AccessTokenProvider):
    """Development-only token source; replace with an encrypted OAuth token store."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    async def get_access_token(self, account_id: str) -> str:
        del account_id
        if not self._access_token:
            raise CameraMediaError("No Ring access token is configured")
        return self._access_token


class RingCameraAdapter(CameraAdapter):
    name = "ring-partner-api"

    def __init__(
        self,
        config: RingAdapterConfig,
        token_provider: AccessTokenProvider,
        client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._token_provider = token_provider
        self._client = client

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
        token = await self._token_provider.get_access_token(event.account_id)
        url = (
            f"{self._config.api_base_url.rstrip('/')}"
            f"/v1/devices/{event.device_id}/media/image/download"
        )
        payload: dict[str, Any] = {
            "type": "at_timestamp",
            "timestamp": int(event.occurred_at.timestamp() * 1000),
            "image_options": {
                "format": "jpeg",
                "resolution": {"width": 1920, "height": 1080},
            },
        }
        if event.component_ids:
            payload["components"] = [{"component_id": event.component_ids[0]}]

        redirect = await self._post_with_backoff(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        if redirect.status_code != 303:
            raise CameraMediaError(
                f"Ring snapshot request returned HTTP {redirect.status_code} instead of 303"
            )
        location = redirect.headers.get("Location")
        if not location or urlparse(location).scheme != "https":
            raise CameraMediaError("Ring snapshot response did not include a safe HTTPS location")

        media = await self._client.get(
            location,
            follow_redirects=False,
            timeout=self._config.request_timeout_seconds,
        )
        try:
            media.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise CameraMediaError(
                f"Ring snapshot download returned HTTP {media.status_code}"
            ) from exc
        return MediaFrame(
            content=media.content,
            content_type=media.headers.get("Content-Type", "image/jpeg"),
            captured_at=event.occurred_at,
            source_event_id=event.event_id,
            device_id=event.device_id,
        )

    async def _post_with_backoff(self, url: str, **kwargs: Any) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self._config.max_attempts):
            try:
                response = await self._client.post(
                    url,
                    follow_redirects=False,
                    timeout=self._config.request_timeout_seconds,
                    **kwargs,
                )
            except httpx.HTTPError as exc:
                if attempt + 1 == self._config.max_attempts:
                    raise CameraMediaError("Ring snapshot request failed") from exc
            else:
                last_response = response
                if response.status_code not in {429, 500, 502, 503, 504}:
                    return response
            await asyncio.sleep(0.25 * (2**attempt))
        if last_response is None:
            raise CameraMediaError("Ring snapshot request failed without a response")
        return last_response

