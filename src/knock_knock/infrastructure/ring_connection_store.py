"""Encrypted durable linking store for single-host development, NOT Lambda /tmp.

Provision the 256-bit encryption key outside the database and source control.
AWS deployment must use a shared store with equivalent conditional transactions.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from knock_knock.adapters.camera.ring_linking import PendingRingTokens, verify_link_nonce
from knock_knock.services.ring_connection import PendingConnection


class EncryptedRingConnectionStore:
    def __init__(self, path: Path, *, encryption_key: bytes, signing_key: str) -> None:
        if len(encryption_key) != 32 or not signing_key:
            raise ValueError("A 256-bit encryption key and signing key are required")
        self._path, self._cipher, self._signing_key = path, AESGCM(encryption_key), signing_key
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS ring_links (
                account TEXT PRIMARY KEY, ciphertext BLOB NOT NULL,
                expires INTEGER NOT NULL, owner TEXT, nonce TEXT UNIQUE,
                state TEXT NOT NULL CHECK(state IN ('pending','claimed','completed')),
                privacy_consent_version TEXT, privacy_consented_at TEXT
            )""")
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ring_links)")}
            if "privacy_consent_version" not in columns:
                db.execute("ALTER TABLE ring_links ADD COLUMN privacy_consent_version TEXT")
            if "privacy_consented_at" not in columns:
                db.execute("ALTER TABLE ring_links ADD COLUMN privacy_consented_at TEXT")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=10)

    async def stage(self, pending: PendingConnection, *, expires_ms: int) -> None:
        await asyncio.to_thread(self._stage, pending, expires_ms)

    def _stage(self, pending: PendingConnection, expires_ms: int) -> None:
        iv = os.urandom(12)
        payload = json.dumps(
            {
                "access": pending.tokens.access_token,
                "refresh": pending.tokens.refresh_token,
                "lifetime": pending.tokens.expires_in,
            }
        ).encode()
        sealed = iv + self._cipher.encrypt(iv, payload, pending.account_id.encode())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT state FROM ring_links WHERE account=?", (pending.account_id,)
            ).fetchone()
            # A new code must never overwrite an existing owner's claim.
            if row and row[0] != "pending":
                raise ValueError("Ring account already claimed; explicit relinking required")
            db.execute(
                """INSERT INTO ring_links
                (account, ciphertext, expires, owner, nonce, state)
                VALUES (?, ?, ?, NULL, NULL, 'pending')
                ON CONFLICT(account) DO UPDATE SET ciphertext=excluded.ciphertext,
                expires=excluded.expires WHERE ring_links.state='pending'""",
                (pending.account_id, sealed, expires_ms),
            )

    async def claim(
        self, nonce: str, timestamp_ms: str, owner_subject: str, *, now_ms: int
    ) -> PendingConnection | None:
        return await asyncio.to_thread(self._claim, nonce, timestamp_ms, owner_subject, now_ms)

    def _claim(
        self, nonce: str, timestamp_ms: str, owner: str, now_ms: int
    ) -> PendingConnection | None:
        if not owner.strip():
            return None
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT account,ciphertext FROM ring_links WHERE state='pending' AND expires>?",
                (now_ms,),
            ).fetchall()
            for account, sealed in rows:
                if not verify_link_nonce(
                    nonce, timestamp_ms, account, self._signing_key, now_ms=now_ms
                ):
                    continue
                # Verify ciphertext before claiming so corruption cannot bind an owner.
                try:
                    body = json.loads(
                        self._cipher.decrypt(sealed[:12], sealed[12:], account.encode())
                    )
                except Exception:
                    # No ciphertext, token, or crypto diagnostics in public errors.
                    raise ValueError("Ring credentials could not be decrypted") from None
                changed = db.execute(
                    "UPDATE ring_links SET owner=?,nonce=?,state='claimed' "
                    "WHERE account=? AND state='pending'",
                    (owner, nonce, account),
                ).rowcount
                if changed != 1:
                    return None
                return PendingConnection(
                    account, PendingRingTokens(body["access"], body["refresh"], body["lifetime"])
                )
        return None

    async def complete(
        self,
        account_id: str,
        owner_subject: str,
        *,
        privacy_consent_version: str,
        privacy_consented_at: str,
    ) -> None:
        await asyncio.to_thread(
            self._complete, account_id, owner_subject,
            privacy_consent_version, privacy_consented_at,
        )

    def _complete(
        self, account: str, owner: str,
        privacy_consent_version: str, privacy_consented_at: str,
    ) -> None:
        with self._connect() as db:
            changed = db.execute(
                "UPDATE ring_links SET state='completed', privacy_consent_version=?, "
                "privacy_consented_at=? "
                "WHERE account=? AND owner=? AND state='claimed'",
                (privacy_consent_version, privacy_consented_at, account, owner),
            ).rowcount
            if changed != 1:
                raise ValueError("No matching claimed Ring connection")
