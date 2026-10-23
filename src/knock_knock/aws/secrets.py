from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from knock_knock.adapters.camera.ring import RingOAuthToken, RingOAuthTokenStore


def load_secret_json(client: Any, secret_id: str) -> dict[str, Any]:
    response = client.get_secret_value(SecretId=secret_id)
    value = response.get("SecretString")
    if not value:
        raise ValueError("Secret must contain a JSON SecretString")
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Secret JSON must be an object")
    return parsed


def load_optional_secret_json(client: Any, secret_id: str) -> dict[str, Any]:
    """Load a JSON secret, treating an uninitialized secret as empty.

    CloudFormation deliberately creates the Ring secret without a value so that
    credentials never pass through a template.  The API must still be able to
    serve health and demo routes before the owner configures that value.
    """
    try:
        return load_secret_json(client, secret_id)
    except client.exceptions.ResourceNotFoundException:
        return {}


class SecretsManagerRingOAuthTokenStore(RingOAuthTokenStore):
    """Persists Ring refresh-token rotation in the encrypted Ring secret."""

    def __init__(self, secret_id: str, *, client: Any) -> None:
        self._secret_id = secret_id
        self._client = client
        self._lock = asyncio.Lock()

    async def load(self, account_id: str) -> RingOAuthToken | None:
        secret = await asyncio.to_thread(load_secret_json, self._client, self._secret_id)
        if str(secret.get("account_id", "")) != account_id:
            return None
        expires_at = _parse_expiry(secret.get("expires_at"))
        return RingOAuthToken(
            access_token=str(secret.get("access_token", "")),
            refresh_token=str(secret.get("refresh_token", "")),
            expires_at=expires_at,
        )

    async def save(self, account_id: str, token: RingOAuthToken) -> None:
        async with self._lock:
            secret = await asyncio.to_thread(load_secret_json, self._client, self._secret_id)
            secret.update(
                {
                    "account_id": account_id,
                    "access_token": token.access_token,
                    "refresh_token": token.refresh_token,
                    "expires_at": token.expires_at.astimezone(UTC).isoformat(),
                }
            )
            await asyncio.to_thread(
                self._client.put_secret_value,
                SecretId=self._secret_id,
                SecretString=json.dumps(secret, separators=(",", ":"), sort_keys=True),
            )


def _parse_expiry(value: Any) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, UTC)
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
