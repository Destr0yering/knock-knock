"""Account-link orchestration independent of media and recognition pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from knock_knock.adapters.camera.ring_linking import (
    PendingRingTokens,
    RingLinkingClient,
    verify_link_nonce,
)
from knock_knock.ports.camera import CameraAuthenticationError


@dataclass(frozen=True, slots=True)
class PendingConnection:
    account_id: str
    tokens: PendingRingTokens = field(repr=False)


class ConnectionStore(Protocol):
    """Production store must encrypt tokens and implement durable atomic claims.

    Each claim must check expiry, prevent replay, and reject a Ring account
    already assigned to another owner. Failure must remain recoverable only by
    that same owner, never release the nonce for a different user to claim.
    """

    async def stage(self, pending: PendingConnection, *, expires_ms: int) -> None: ...

    async def claim(
        self, nonce: str, timestamp_ms: str, owner_subject: str, *, now_ms: int
    ) -> PendingConnection | None: ...

    async def complete(
        self,
        account_id: str,
        owner_subject: str,
        *,
        privacy_consent_version: str,
        privacy_consented_at: str,
    ) -> None: ...


class RingConnectionService:
    """Never treats Ring's redirect alone as authenticated owner consent."""

    def __init__(
        self, client: RingLinkingClient, store: ConnectionStore, *, signing_key: str
    ) -> None:
        if not signing_key:
            raise ValueError("Ring signing key is required")
        self._client = client
        self._store = store
        self._signing_key = signing_key

    async def receive_code(
        self, code: str, *, client_id: str, client_secret: str, now_ms: int
    ) -> None:
        tokens = await self._client.exchange_code(
            code, client_id=client_id, client_secret=client_secret
        )
        account = await self._client.account_id(tokens.access_token)
        await self._store.stage(PendingConnection(account, tokens), expires_ms=now_ms + 600_000)

    async def confirm(
        self,
        *,
        nonce: str,
        timestamp_ms: str,
        owner_subject: str,
        masked_owner_identifier: str,
        privacy_consent_version: str,
        now_ms: int,
    ) -> None:
        # These identity fields must come from verified server-side auth, not
        # request JSON, query parameters, or arbitrary forwarded headers.
        if (
            not owner_subject.strip()
            or not masked_owner_identifier.strip()
            or privacy_consent_version != "2026-10-21-v1"
        ):
            raise CameraAuthenticationError("Authenticated owner is required")
        pending = await self._store.claim(nonce, timestamp_ms, owner_subject, now_ms=now_ms)
        if pending is None or not verify_link_nonce(
            nonce, timestamp_ms, pending.account_id, self._signing_key, now_ms=now_ms
        ):
            raise CameraAuthenticationError("Ring connection is invalid or expired")
        await self._client.confirm_link(
            pending.tokens.access_token,
            nonce,
            masked_account_identifier=masked_owner_identifier,
        )
        # Do not mark connected on a failed POST/PATCH or run any media worker.
        await self._store.complete(
            pending.account_id,
            owner_subject,
            privacy_consent_version=privacy_consent_version,
            privacy_consented_at=datetime.now(UTC).isoformat(),
        )
