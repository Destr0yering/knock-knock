from unittest.mock import AsyncMock

import pytest
from test_ring_linking import ACCOUNT, KEY, NONCE, STAMP

from knock_knock.adapters.camera.ring_linking import PendingRingTokens
from knock_knock.ports.camera import CameraAuthenticationError
from knock_knock.services.ring_connection import PendingConnection, RingConnectionService


def setup_service():
    client, store = AsyncMock(), AsyncMock()
    store.claim.return_value = PendingConnection(ACCOUNT, PendingRingTokens("a", "r", 14400))
    return RingConnectionService(client, store, signing_key=KEY), client, store


async def test_unauthenticated_confirmation_never_claims_tokens():
    service, client, store = setup_service()
    with pytest.raises(CameraAuthenticationError):
        await service.confirm(
            nonce=NONCE,
            timestamp_ms=STAMP,
            owner_subject="",
            masked_owner_identifier="owner",
            privacy_consent_version="2026-10-21-v1",
            now_ms=int(STAMP),
        )
    store.claim.assert_not_called()
    client.confirm_link.assert_not_called()


async def test_success_marks_complete_only_after_ring_confirmation():
    service, client, store = setup_service()
    await service.confirm(
        nonce=NONCE,
        timestamp_ms=STAMP,
        owner_subject="verified-sub",
        masked_owner_identifier="o***r",
        privacy_consent_version="2026-10-21-v1",
        now_ms=int(STAMP),
    )
    client.confirm_link.assert_awaited_once()
    complete = store.complete.await_args.kwargs
    assert complete["privacy_consent_version"] == "2026-10-21-v1"
    assert complete["privacy_consented_at"]


async def test_failed_ring_confirmation_does_not_mark_connected():
    service, client, store = setup_service()
    client.confirm_link.side_effect = CameraAuthenticationError("Ring unavailable")
    with pytest.raises(CameraAuthenticationError):
        await service.confirm(
            nonce=NONCE,
            timestamp_ms=STAMP,
            owner_subject="verified-sub",
            masked_owner_identifier="o***r",
            privacy_consent_version="2026-10-21-v1",
            now_ms=int(STAMP),
        )
    store.complete.assert_not_called()


async def test_replayed_or_unknown_claim_never_calls_ring():
    service, client, store = setup_service()
    store.claim.return_value = None
    with pytest.raises(CameraAuthenticationError):
        await service.confirm(
            nonce=NONCE,
            timestamp_ms=STAMP,
            owner_subject="verified-sub",
            masked_owner_identifier="o***r",
            privacy_consent_version="2026-10-21-v1",
            now_ms=int(STAMP),
        )
    client.confirm_link.assert_not_called()
