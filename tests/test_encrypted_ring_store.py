import asyncio
import sqlite3

import pytest
from test_ring_linking import ACCOUNT, KEY, NONCE, STAMP

from knock_knock.adapters.camera.ring_linking import PendingRingTokens
from knock_knock.infrastructure.ring_connection_store import EncryptedRingConnectionStore
from knock_knock.services.ring_connection import PendingConnection


async def test_encrypted_persistence_single_claim_and_owner_completion(tmp_path):
    path = tmp_path / "links.db"
    store = EncryptedRingConnectionStore(path, encryption_key=b"k" * 32, signing_key=KEY)
    await store.stage(
        PendingConnection(
            ACCOUNT, PendingRingTokens("private-access-token", "private-refresh-token", 14400)
        ),
        expires_ms=int(STAMP) + 600000,
    )
    assert b"private-access-token" not in path.read_bytes()
    assert b"private-refresh-token" not in path.read_bytes()
    results = await asyncio.gather(
        *[store.claim(NONCE, STAMP, owner, now_ms=int(STAMP)) for owner in ["one", "two"]]
    )
    assert sum(result is not None for result in results) == 1
    with sqlite3.connect(path) as db:
        owner = db.execute("SELECT owner FROM ring_links").fetchone()[0]
    with pytest.raises(ValueError):
        await store.complete(
            ACCOUNT,
            "wrong-owner",
            privacy_consent_version="2026-10-15-v1",
            privacy_consented_at="2026-10-15T12:00:00+00:00",
        )
    await store.complete(
        ACCOUNT,
        owner,
        privacy_consent_version="2026-10-15-v1",
        privacy_consented_at="2026-10-15T12:00:00+00:00",
    )
    reopened = EncryptedRingConnectionStore(path, encryption_key=b"k" * 32, signing_key=KEY)
    assert await reopened.claim(NONCE, STAMP, owner, now_ms=int(STAMP)) is None


async def test_invalid_nonce_does_not_consume_pending_connection(tmp_path):
    store = EncryptedRingConnectionStore(
        tmp_path / "links.db", encryption_key=b"k" * 32, signing_key=KEY
    )
    await store.stage(
        PendingConnection(ACCOUNT, PendingRingTokens("a", "r", 14400)), expires_ms=int(STAMP) + 1
    )
    assert await store.claim("wrong", STAMP, "owner", now_ms=int(STAMP)) is None
    assert await store.claim(NONCE, STAMP, "owner", now_ms=int(STAMP)) is not None


async def test_expired_pending_tokens_cannot_be_claimed(tmp_path):
    store = EncryptedRingConnectionStore(
        tmp_path / "links.db", encryption_key=b"k" * 32, signing_key=KEY
    )
    await store.stage(
        PendingConnection(ACCOUNT, PendingRingTokens("a", "r", 14400)), expires_ms=int(STAMP)
    )
    assert await store.claim(NONCE, STAMP, "owner", now_ms=int(STAMP)) is None
