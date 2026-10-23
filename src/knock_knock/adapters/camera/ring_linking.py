"""Server-side Ring linking primitives; no media, recognition or visitor storage.

Not mounted as public endpoints. The caller must authenticate the partner user,
atomically claim an encrypted pending-token record and prevent nonce replay before
calling confirm_link. A valid nonce alone is NOT partner authentication.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from knock_knock.ports.camera import CameraAuthenticationError, CameraRateLimitError

API_BASE = "https://api.amazonvision.com"


@dataclass(frozen=True, slots=True)
class PendingRingTokens:
    """Transient server-only result; caller must encrypt before persistence."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_in: int


def verify_link_nonce(
    nonce: str, timestamp_ms: str, account_id: str, signing_key: str, *, now_ms: int
) -> bool:
    """Validate Ring's URL-safe HMAC nonce and strict ten-minute freshness window."""
    if not account_id or not signing_key:
        return False
    if not re.fullmatch(r"[0-9]{13}", timestamp_ms):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", nonce):
        return False
    age = now_ms - int(timestamp_ms)
    if not 0 <= age <= 600_000:
        return False
    digest = hmac.new(
        signing_key.encode(), f"{timestamp_ms}:{account_id}".encode(), hashlib.sha256
    ).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(expected, nonce)


class RingLinkingClient:
    """Uses only fixed official HTTPS endpoints; never returns profile contact fields."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def exchange_code(
        self, code: str, *, client_id: str, client_secret: str
    ) -> PendingRingTokens:
        """Ring-driven flow only. Never retry a single-use code automatically.

        Receiving a code does not authenticate a Knock Knock owner. Tokens remain
        pending until authenticated account linking and replay-safe claiming.
        """
        if not all(value.strip() for value in (code, client_id, client_secret)):
            raise CameraAuthenticationError("Ring exchange credentials are incomplete")
        try:
            response = await self._client.post(
                "https://oauth.ring.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=10.0,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            raise CameraAuthenticationError("Ring token exchange failed") from None
        if response.status_code == 429:
            raise CameraRateLimitError("Ring token exchange is rate limited")
        if response.status_code != 200:
            raise CameraAuthenticationError("Ring token exchange was rejected")
        try:
            body = response.json()
        except ValueError:
            raise CameraAuthenticationError("Invalid Ring token response") from None
        if not isinstance(body, dict):
            raise CameraAuthenticationError("Invalid Ring token response")
        access, refresh, lifetime = (
            body.get("access_token"),
            body.get("refresh_token"),
            body.get("expires_in"),
        )
        if (
            not isinstance(access, str)
            or not access.strip()
            or not isinstance(refresh, str)
            or not refresh.strip()
            or type(lifetime) is not int
            or lifetime <= 0
            or body.get("token_type") != "Bearer"
        ):
            raise CameraAuthenticationError("Incomplete Ring token response")
        return PendingRingTokens(access, refresh, lifetime)

    async def account_id(self, access_token: str) -> str:
        body = await self._request("GET", "/v1/users/me", access_token)
        data = body.get("data")
        if not isinstance(data, dict) or data.get("type") != "users":
            raise CameraAuthenticationError("Invalid Ring account response")
        account = data.get("id")
        if not isinstance(account, str) or not account.strip():
            raise CameraAuthenticationError("Ring response omitted account identity")
        return account

    async def devices(self, access_token: str) -> list[dict[str, Any]]:
        """First device discovery page; caller must handle documented pagination."""
        body = await self._request("GET", "/v1/devices", access_token)
        data = body.get("data")
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise CameraAuthenticationError("Invalid Ring device response")
        return data

    async def confirm_link(
        self, access_token: str, nonce: str, *, masked_account_identifier: str
    ) -> None:
        """Caller must supply a nonce already verified/claimed after partner sign-in.

        Do not automatically retry mutation requests. If PATCH fails, retain a
        recoverable pending state rather than reporting the account as connected.
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", nonce):
            raise CameraAuthenticationError("Invalid Ring link nonce")
        if not masked_account_identifier.strip():
            raise CameraAuthenticationError("Authenticated partner identity is required")
        path = "/v1/accounts/me/app-integrations"
        await self._request(
            "POST",
            path,
            access_token,
            {
                "nonce": nonce,
                "account_identifier": masked_account_identifier,
            },
        )
        body = await self._request("PATCH", path, access_token, {"status": "completed"})
        data = body.get("data", {})
        attributes = data.get("attributes", {}) if isinstance(data, dict) else {}
        if not isinstance(attributes, dict) or attributes.get("status") != "completed":
            raise CameraAuthenticationError("Ring has not confirmed completed integration")

    async def _request(
        self, method: str, path: str, token: str, payload: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        if not token.strip():
            raise CameraAuthenticationError("Ring access token is missing")
        try:
            response = await self._client.request(
                method,
                API_BASE + path,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=10.0,
                follow_redirects=False,
            )
        except httpx.HTTPError:
            # Do not leak token-bearing requests or provider response bodies.
            raise CameraAuthenticationError("Ring connection request failed") from None
        if response.status_code == 429:
            raise CameraRateLimitError("Ring connection is rate limited")
        if not 200 <= response.status_code < 300:
            raise CameraAuthenticationError(f"Ring connection returned HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError:
            raise CameraAuthenticationError("Invalid Ring JSON response") from None
        if not isinstance(body, dict):
            raise CameraAuthenticationError("Invalid Ring response structure")
        return body
