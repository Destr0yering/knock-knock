"""Durable, conditional Ring account-link token store for AWS.

The DynamoDB table must have server-side encryption enabled. Token attributes are
never returned by this adapter except to the authenticated confirmation service.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from knock_knock.adapters.camera.ring import RingOAuthToken, RingOAuthTokenStore
from knock_knock.adapters.camera.ring_linking import PendingRingTokens, verify_link_nonce
from knock_knock.services.ring_connection import PendingConnection


class DynamoRingConnectionStore:
    def __init__(
        self, table_name: str, *, household_table_name: str, dynamodb: Any, signing_key: str
    ) -> None:
        if not table_name or not household_table_name or not signing_key:
            raise ValueError("Ring connection table, household table, and signing key are required")
        self._table = dynamodb.Table(table_name)
        self._household_table_name = household_table_name
        self._signing_key = signing_key

    async def stage(self, pending: PendingConnection, *, expires_ms: int) -> None:
        await asyncio.to_thread(self._stage, pending, expires_ms)

    def _stage(self, pending: PendingConnection, expires_ms: int) -> None:
        from boto3.dynamodb.conditions import Attr

        tokens = pending.tokens
        try:
            self._table.put_item(
                Item={
                    "account_id": pending.account_id,
                    "state": "pending",
                    "state_partition": "pending",
                    "expires_ms": expires_ms,
                    "expires_at": expires_ms // 1000,
                    "tokens": {
                        "access_token": tokens.access_token,
                        "refresh_token": tokens.refresh_token,
                        "expires_in": tokens.expires_in,
                    },
                    "token_expires_at_ms": expires_ms - 600_000 + tokens.expires_in * 1000,
                },
                ConditionExpression=Attr("account_id").not_exists() | Attr("state").eq("pending"),
            )
        except self._table.meta.client.exceptions.ConditionalCheckFailedException:
            raise ValueError(
                "Ring account is already linked; explicit relinking is required"
            ) from None

    async def claim(
        self, nonce: str, timestamp_ms: str, owner_subject: str, *, now_ms: int
    ) -> PendingConnection | None:
        return await asyncio.to_thread(self._claim, nonce, timestamp_ms, owner_subject, now_ms)

    def _claim(
        self, nonce: str, timestamp_ms: str, owner_subject: str, now_ms: int
    ) -> PendingConnection | None:
        from boto3.dynamodb.conditions import Key

        cursor: dict[str, Any] | None = None
        while True:
            args: dict[str, Any] = {
                "IndexName": "state-index",
                "KeyConditionExpression": Key("state_partition").eq("pending"),
                "ProjectionExpression": "account_id, expires_ms",
            }
            if cursor:
                args["ExclusiveStartKey"] = cursor
            page = self._table.query(**args)
            for item in page.get("Items", []):
                account_id = str(item.get("account_id", ""))
                expires_ms = int(item.get("expires_ms", 0))
                if expires_ms <= now_ms or not verify_link_nonce(
                    nonce, timestamp_ms, account_id, self._signing_key, now_ms=now_ms
                ):
                    continue
                try:
                    claimed = self._table.update_item(
                        Key={"account_id": account_id},
                        UpdateExpression=(
                            "SET #state = :claimed, state_partition = :claimed_partition, "
                            "owner_subject = :owner, nonce = :nonce"
                        ),
                        ConditionExpression="#state = :pending AND expires_ms > :now",
                        ExpressionAttributeNames={"#state": "state"},
                        ExpressionAttributeValues={
                            ":claimed": "claimed",
                            ":claimed_partition": "claimed",
                            ":owner": owner_subject,
                            ":nonce": nonce,
                            ":pending": "pending",
                            ":now": now_ms,
                        },
                        ReturnValues="ALL_OLD",
                    )["Attributes"]
                except self._table.meta.client.exceptions.ConditionalCheckFailedException:
                    return None
                tokens = claimed.get("tokens", {})
                return PendingConnection(
                    account_id,
                    PendingRingTokens(
                        str(tokens["access_token"]),
                        str(tokens["refresh_token"]),
                        int(tokens["expires_in"]),
                    ),
                )
            cursor = page.get("LastEvaluatedKey")
            if not cursor:
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
        self, account_id: str, owner_subject: str,
        privacy_consent_version: str, privacy_consented_at: str,
    ) -> None:
        from boto3.dynamodb.types import TypeSerializer

        now = datetime.now(UTC)
        serializer = TypeSerializer()
        try:
            self._table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self._table.name,
                            "Key": {"account_id": serializer.serialize(account_id)},
                            "UpdateExpression": (
                                "SET #state = :completed, state_partition = :completed_partition "
                                "REMOVE expires_at"
                            ),
                            "ConditionExpression": "#state = :claimed AND owner_subject = :owner",
                            "ExpressionAttributeNames": {"#state": "state"},
                            "ExpressionAttributeValues": {
                                ":claimed": serializer.serialize("claimed"),
                                ":completed": serializer.serialize("completed"),
                                ":completed_partition": serializer.serialize("completed"),
                                ":owner": serializer.serialize(owner_subject),
                            },
                        }
                    },
                    {
                        "Update": {
                            "TableName": self._household_table_name,
                            "Key": {
                                "household_id": serializer.serialize(owner_subject),
                            },
                            "UpdateExpression": (
                                "SET ring_account_subject = :account, owner_subject = :owner, "
                                "privacy_consent_version = :consent_version, "
                                "privacy_consented_at = :consented_at, "
                                "created_at = if_not_exists(created_at, :created), "
                                "learning_ends_at = if_not_exists(learning_ends_at, :learning_ends)"
                            ),
                            "ConditionExpression": (
                                "attribute_not_exists(deletion_status) AND "
                                "(attribute_not_exists(ring_account_subject) "
                                "OR ring_account_subject = :account"
                                ")"
                            ),
                            "ExpressionAttributeValues": {
                                ":account": serializer.serialize(account_id),
                                ":owner": serializer.serialize(owner_subject),
                                ":consent_version": serializer.serialize(privacy_consent_version),
                                ":consented_at": serializer.serialize(privacy_consented_at),
                                ":created": serializer.serialize(now.isoformat()),
                                ":learning_ends": serializer.serialize(
                                    (now + timedelta(days=30)).isoformat()
                                ),
                            },
                        }
                    },
                ]
            )
        except self._table.meta.client.exceptions.TransactionCanceledException:
            raise ValueError("No matching claimed Ring connection") from None


class DynamoRingOAuthTokenStore(RingOAuthTokenStore):
    """Per-account rotating token store backed by the SSE-enabled link table."""

    def __init__(self, table_name: str, *, dynamodb: Any) -> None:
        self._table = dynamodb.Table(table_name)

    async def load(self, account_id: str) -> RingOAuthToken | None:
        return await asyncio.to_thread(self._load, account_id)

    def _load(self, account_id: str) -> RingOAuthToken | None:
        item = self._table.get_item(Key={"account_id": account_id}, ConsistentRead=True).get("Item")
        if not item or item.get("state") != "completed":
            return None
        tokens = item.get("tokens", {})
        expiry = datetime.fromtimestamp(int(item.get("token_expires_at_ms", 0)) / 1000, UTC)
        return RingOAuthToken(
            access_token=str(tokens.get("access_token", "")),
            refresh_token=str(tokens.get("refresh_token", "")),
            expires_at=expiry,
        )

    async def save(self, account_id: str, token: RingOAuthToken) -> None:
        await asyncio.to_thread(self._save, account_id, token)

    def _save(self, account_id: str, token: RingOAuthToken) -> None:
        self._table.update_item(
            Key={"account_id": account_id},
            UpdateExpression="SET tokens = :tokens, token_expires_at_ms = :expiry",
            ConditionExpression="#state = :completed",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={
                ":completed": "completed",
                ":tokens": {
                    "access_token": token.access_token,
                    "refresh_token": token.refresh_token,
                },
                ":expiry": int(token.expires_at.timestamp() * 1000),
            },
        )
